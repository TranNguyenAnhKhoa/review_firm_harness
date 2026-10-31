from __future__ import annotations

from pathlib import Path
import tempfile

from src.audio.mixer import build_mix_filter
from src.utils import ensure_parent, executable, run_command
from src.video.probe import probe_video, probe_audio
from src.video.clipper import match_duration


def concat_clips(clips: list[str], output_path: str, *, codec: str = "libx264", crf: int = 20, preset: str = "medium") -> Path:
    """Reset timestamps and concatenate normalized clips, avoiding AAC packet gaps."""
    if not clips:
        raise ValueError("At least one clip is required")
    output = ensure_parent(output_path)
    inputs, graph, labels = [], [], []
    for index, clip in enumerate(clips):
        inputs.extend(["-i", clip])
        duration = probe_video(clip)["duration"]
        graph.extend([
            f"[{index}:v]setpts=PTS-STARTPTS[v{index}]",
            f"[{index}:a]asetpts=PTS-STARTPTS,apad,atrim=duration={duration:.6f}[a{index}]",
        ])
        labels.append(f"[v{index}][a{index}]")
    graph.append(f"{''.join(labels)}concat=n={len(clips)}:v=1:a=1[v][a]")
    run_command(
        [
            executable("ffmpeg", "FFMPEG_BINARY"), "-hide_banner", "-y", *inputs,
            "-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]",
            "-c:v", codec, "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", str(output),
        ]
    )
    return output


def render_measured_segment(
    video_path: str, narration_path: str, start: float, end: float,
    duration: float, output_path: str, *, metadata: dict | None = None,
    subtitles_path: str | None = None, keep_original_audio: bool = True,
    background_volume: float = 0.18, narration_volume: float = 1.0,
    codec: str = "libx264", crf: int = 20, preset: str = "veryfast",
    fps: float | None = None, duration_matching: dict | None = None,
    threads: int = 3,
    shots: list[dict] | None = None,
    picture_style: dict | None = None,
    unit_timings: list[dict] | None = None,
) -> Path:
    """Encode one bounded shot, measured narration and subtitles in one pass.

    Matroska/PCM intermediates avoid AAC priming at every segment boundary.
    The final concat copies H.264 and encodes AAC once, with bounded memory.
    """
    output = ensure_parent(output_path)
    if shots:
        from src.video.montage import cut_montage
        with tempfile.TemporaryDirectory(prefix='measured-montage-', dir=output.parent) as folder:
            montage = cut_montage(video_path, shots, duration, str(Path(folder) / 'picture.mp4'),
                                  fps=fps or (metadata or probe_video(video_path))['fps'] or 30,
                                  keep_original_audio=keep_original_audio, codec=codec, crf=crf,
                                  preset=preset, duration_matching=duration_matching,unit_timings=unit_timings)
            return render_measured_segment(str(montage), narration_path, 0, duration, duration,
                output_path, subtitles_path=subtitles_path, keep_original_audio=keep_original_audio,
                background_volume=background_volume, narration_volume=narration_volume,
                codec=codec, crf=crf, preset=preset, fps=fps, threads=threads,
                duration_matching={'enabled':False, 'fallback':'error'}, picture_style=picture_style)
    if output.suffix.lower() != ".mkv":
        raise ValueError("Measured segment intermediate must be .mkv (H.264 + PCM)")
    if codec != "libx264":
        raise ValueError("Measured renderer currently supports libx264 only")
    metadata = metadata or probe_video(video_path)
    if end > metadata["duration"] + 0.001:
        raise ValueError("Source range exceeds video duration")
    if probe_audio(narration_path) > duration + 0.001:
        raise ValueError("Clip duration would truncate narration")
    choice = match_duration(start, end, duration, duration_matching)
    used, speed = choice["source_duration"], choice["speed"]
    fps = fps or metadata["fps"] or 30.0
    command = [executable("ffmpeg", "FFMPEG_BINARY"), "-hide_banner", "-v", "warning", "-y",
               "-threads", str(threads), "-ss", f"{choice['start']:.6f}", "-t", f"{used:.6f}",
               "-i", video_path, "-i", narration_path]
    audio_label = "0:a"
    if not metadata["audio_codec"]:
        command += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio_label = "2:a"
    picture = (f"[0:v]trim=duration={used:.6f},setpts=(PTS-STARTPTS)/{speed:.9f},"
               f"fps={fps},tpad=stop_mode=clone:stop_duration={choice['freeze_duration'] + 1/fps:.6f},"
               f"trim=duration={duration:.6f},scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1")
    from src.video.picture_style import PictureStyle, picture_filters
    visual, overlay = picture_filters(PictureStyle.model_validate(picture_style or {}), video_path,
                                      duration, output.parent / (output.stem + '.style'))
    if overlay:
        visual.append(_subtitle_filter(str(overlay)))
    if visual:
        picture += ',' + ','.join(visual)
    if subtitles_path:
        picture += "," + _subtitle_filter(subtitles_path)
    graph = [picture + "[v]",
             f"[{audio_label}]atrim=duration={used:.6f},asetpts=PTS-STARTPTS,atempo={speed:.9f},"
             f"aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration:.6f},"
             f"afade=t=out:st={max(0, duration-.02):.6f}:d=0.02[base]",
             f"[1:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
             f"afade=t=in:d=0.01,apad,atrim=duration={duration:.6f}[n0]"]
    mix, label = build_mix_filter("base", 1, background_volume if keep_original_audio else 0,
                                  narration_volume)
    graph += [mix, f"{label}alimiter=limit=.95:level=false:latency=true,"
                   f"apad,atrim=duration={duration:.6f}[a]"]
    command += ["-filter_complex_threads", "1", "-filter_complex", ";".join(graph),
                "-map", "[v]", "-map", "[a]", "-t", f"{duration:.6f}",
                "-c:v", codec, "-threads", str(threads), "-crf", str(crf), "-preset", preset,
                "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                str(output)]
    run_command(command)
    return output


def concat_measured_segments(clips: list[Path], durations: list[float], output_path: str) -> Path:
    """Sequential demuxer concat: no 99-input filter graph or video re-encoding."""
    if not clips or len(clips) != len(durations):
        raise ValueError("One measured duration is required per clip")
    directory = clips[0].resolve().parent
    if any(p.resolve().parent != directory for p in clips):
        raise ValueError("Intermediates must share a directory")
    # Only generated ASCII names are accepted in the concat manifest.
    if any(not all(c.isascii() and (c.isalnum() or c in "_.-") for c in p.name) for p in clips):
        raise ValueError("Use safe ASCII intermediate filenames")
    manifest = directory / "concat.ffconcat"
    lines = ["ffconcat version 1.0"]
    for clip, duration in zip(clips, durations):
        lines += [f"file '{clip.name}'", f"duration {duration:.6f}"]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output = ensure_parent(output_path)
    run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-hide_banner", "-v", "warning", "-y",
                 "-f", "concat", "-safe", "1", "-i", str(manifest.resolve()),
                 "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac",
                 "-ar", "48000", "-b:a", "192k", "-movflags", "+faststart", str(output)])
    return output


def _subtitle_filter(path: str) -> str:
    value = Path(path).resolve().as_posix().replace("'", r"\\'").replace(":", r"\:")
    return f"ass=filename='{value}'"


def render_final(
    concatenated_video: str,
    narration_files: list[str],
    narration_offsets: list[float],
    output_path: str,
    *,
    background_audio: str | None = None,
    subtitles_path: str | None = None,
    background_volume: float = 0.18,
    narration_volume: float = 1.0,
    codec: str = "libx264",
    crf: int = 20,
    preset: str = "medium",
    fps: float | None = None,
    picture_style: dict | None = None,
) -> Path:
    """Mix original/clean background with timed narration and burn ASS subtitles."""
    if len(narration_files) != len(narration_offsets):
        raise ValueError("narration_files and narration_offsets must have equal length")
    output = ensure_parent(output_path)
    command = [executable("ffmpeg", "FFMPEG_BINARY"), "-y", "-i", concatenated_video]
    background_input = 0
    if background_audio:
        command += ["-i", background_audio]
        background_input = 1
    narration_base = background_input + 1
    for narration in narration_files:
        command += ["-i", narration]

    graph_parts = []
    total_duration = probe_video(concatenated_video)["duration"]
    graph_parts.append(f"[{background_input}:a]asetpts=PTS-STARTPTS,apad,atrim=duration={total_duration}[base]")
    for index, offset in enumerate(narration_offsets):
        delay = max(0, round(offset * 1000))
        duration = probe_audio(narration_files[index])
        graph_parts.append(
            f"[{narration_base + index}:a]asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=0.01,afade=t=out:st={max(0, duration - 0.01)}:d=0.01,"
            f"adelay={delay}:all=1[n{index}]"
        )
    mix_graph, mix_label = build_mix_filter("base", len(narration_files), background_volume, narration_volume)
    graph_parts.append(mix_graph)
    graph_parts.append(f'{mix_label}alimiter=limit=.95:level=false:latency=true,apad,atrim=duration={total_duration}[finalmix]')
    command += ["-filter_complex", ";".join(graph_parts), "-map", "0:v:0", "-map", '[finalmix]']
    from src.video.picture_style import PictureStyle, picture_filters
    visual, overlay = picture_filters(PictureStyle.model_validate(picture_style or {}), concatenated_video,
                                      total_duration, output.parent / (output.stem + '.style'))
    if overlay:
        visual.append(_subtitle_filter(str(overlay)))
    if subtitles_path:
        visual.append(_subtitle_filter(subtitles_path))
    if visual:
        command += ['-vf', ','.join(visual)]
    if fps:
        command += ["-r", str(fps)]
    command += [
        "-c:v", codec, "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(output),
    ]
    run_command(command)
    return output
