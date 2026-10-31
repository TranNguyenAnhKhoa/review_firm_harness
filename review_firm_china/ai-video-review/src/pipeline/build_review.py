from __future__ import annotations

import json
import math
import warnings
from pathlib import Path

import yaml

from src.audio.mixer import extract_audio
from src.audio.separator import separate_audio
from src.audio.narration_builder import NarrationBuilder
from src.audio.speech import VoiceConfig, LoudnessConfig
from src.pipeline.schema import ReviewScript
from src.pipeline.editorial import EditorialPolicy, require_timing
from src.subtitle.generator import generate_ass
from src.video.clipper import cut_clip, DurationMatching
from src.video.probe import probe_video
from src.video.renderer import concat_clips, render_final
from src.video.montage import cut_montage, plan_shots
from src.video.picture_style import PictureStyle


def _merge_config(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_config(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path) -> dict:
    default_path = Path(__file__).resolve().parents[2] / "config" / "config.yaml"
    defaults = yaml.safe_load(default_path.read_text(encoding="utf-8-sig"))
    custom = yaml.safe_load(Path(path).read_text(encoding="utf-8-sig")) or {}
    _merge_config(defaults, custom)
    defaults["tts"] = VoiceConfig.model_validate(defaults["tts"]).model_dump()
    defaults["audio"]["narration"] = LoudnessConfig.model_validate(defaults["audio"].get("narration", {})).model_dump()
    defaults["video"]["duration_matching"] = DurationMatching.model_validate(defaults["video"].get("duration_matching", {})).model_dump()
    if defaults["subtitle"].get("format", "ass") != "ass":
        raise ValueError("MVP subtitle.format supports only 'ass'")
    if defaults["subtitle"].get("position", "bottom") not in ("bottom", "top"):
        raise ValueError("subtitle.position must be 'bottom' or 'top'")
    if any(int(defaults["subtitle"][key]) < 1 for key in ("font_size", "max_chars_per_line")):
        raise ValueError("Subtitle font_size and max_chars_per_line must be positive")
    for key in ("narration_volume", "background_volume"):
        value = float(defaults["audio"][key])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"audio.{key} must be finite and >= 0")
    defaults["editorial"] = EditorialPolicy.model_validate(defaults.get("editorial", {})).model_dump()
    defaults['render']['picture_style'] = PictureStyle.model_validate(defaults['render'].get('picture_style', {})).model_dump()
    return defaults


def build_review(video_path: str, review_path: str, config_path: str = "config/config.yaml",
                 *, output_dir: str = "output", tts_only: bool = False) -> Path:
    """Build a review video from a validated manual review.json and source video."""
    video = Path(video_path)
    review_file = Path(review_path)
    if not video.exists():
        raise FileNotFoundError(f"Source video not found: {video}")
    if not review_file.exists():
        raise FileNotFoundError(f"Review JSON not found: {review_file}")
    config = load_config(config_path)
    encoding = {key: config["video"][key] for key in ("codec", "crf", "preset")}
    policy = EditorialPolicy.model_validate(config["editorial"])
    output_root = Path(output_dir)
    outputs = {
        "audio": output_root / "audio", "clips": output_root / "clips", "subtitles": output_root / "subtitles",
        "tmp": Path(config["project"]["temp_dir"]) if output_root == Path("output") else output_root / "tmp",
        "final": output_root / "final",
        "edl": Path("data/edl") if output_root == Path("output") else output_root / "edl",
        "debug": output_root / "debug",
    }
    for directory in outputs.values():
        directory.mkdir(parents=True, exist_ok=True)

    print("[1/8] Probing video")
    metadata = probe_video(video)
    if not metadata["duration"]:
        raise ValueError(f"Could not read video duration: {video}")
    print(f"      {metadata['width']}x{metadata['height']} / {metadata['duration']:.2f}s")

    print("[2/8] Loading review script")
    review = ReviewScript.load(review_file)
    budget = policy.validate_structure(review, metadata["duration"])
    print(f"      Review: {budget['total_min']:.2f}-{budget['total_max']:.2f}s "
          f"(target {budget['total_target']:.2f}s, INCLUDING final assessment "
          f"{budget['assessment_min']:g}-{budget['assessment_max']:g}s)", flush=True)
    for segment in review.segments:
        if segment.source_end > metadata["duration"] + 0.001:
            raise ValueError(f"Segment {segment.id} ends beyond source video duration")
    fps = float(config["render"].get("fps") or metadata["fps"] or 30)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("render.fps must be positive and finite")
    resolution = None
    if not config["render"].get("keep_source_resolution", True):
        resolution = (1080, 1920) if metadata["height"] > metadata["width"] else (1920, 1080)
    width, height = resolution or (metadata["width"] // 2 * 2, metadata["height"] // 2 * 2)
    picture_style = PictureStyle.model_validate(config['render']['picture_style'])
    if picture_style.enabled:
        width, height = picture_style.width, picture_style.height
        resolution = None  # Composition happens once, after source shot cutting.

    print("[3/8] Generating TTS")
    builder = NarrationBuilder(config["tts"], config["audio"]["narration"],
                               cache_dir=output_root / "cache" / "silence")
    narration_files: list[str] = []
    measured: list[float] = []
    audio_durations: list[float] = []
    narrations = []
    for segment in review.segments:
        result = builder.build(segment.narration, outputs["audio"] / f"segment_{segment.id:03d}.wav",
                               segment_id=segment.id, section=segment.section,
                               debug_path=outputs["debug"] / f"segment_{segment.id:03d}_tts.json")
        narration_files.append(str(result.path))
        measured.append(result.speech_duration)
        audio_durations.append(result.duration)
        narrations.append(result)

    # Round up to whole video frames so narration is never cut short.
    edit_durations = [math.ceil(duration * fps - 1e-6) / fps for duration in audio_durations]
    timing = policy.timing_report(review, metadata["duration"], measured, edit_durations)
    timing_path = output_root / "review_timing.json"
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    require_timing(timing)
    print(f"      Timing PASS: {timing['review_duration']:.2f}s "
          f"({timing['source_ratio']:.1%} of source); assessment "
          f"{timing['assessment_narration_duration']:.2f}s", flush=True)
    if tts_only:
        print(f"TTS timing check complete: {timing_path}")
        return timing_path

    print("[4/8] Building clips")
    clip_files: list[str] = []
    for segment, duration, narration in zip(review.segments, edit_durations, narrations):
        clip_file = outputs["clips"] / f"clip_{segment.id:03d}.mp4"
        if segment.shots:
            cut_montage(str(video), [s.model_dump() for s in segment.shots], duration, str(clip_file),
                        keep_original_audio=segment.keep_original_audio, **encoding, fps=fps, resolution=resolution,
                        duration_matching=config['video']['duration_matching'],unit_timings=narration.units)
        else:
            cut_clip(
                str(video), segment.source_start, segment.source_end, duration, str(clip_file),
                keep_original_audio=segment.keep_original_audio, **encoding, fps=fps, resolution=resolution,
                duration_matching=config["video"]["duration_matching"],
            )
        actual = probe_video(clip_file)["duration"]
        if abs(actual - duration) > 1 / fps + 0.03:
            raise RuntimeError(f"Clip {segment.id} duration mismatch: {actual} vs {duration}")
        clip_files.append(str(clip_file))

    concatenated = outputs["tmp"] / "concatenated.mp4"
    concat_clips(clip_files, str(concatenated), **encoding)

    print("[5/8] Processing background audio")
    background_audio: str | None = None
    if config["audio"].get("use_demucs", False):
        extracted = extract_audio(str(concatenated), str(outputs["tmp"] / "concat_audio.wav"))
        try:
            stems = separate_audio(str(extracted), str(outputs["tmp"] / "demucs"))
            background_audio = stems["no_vocals"]
        except (RuntimeError, OSError) as error:
            warnings.warn(f"Demucs failed; falling back to lowered original background: {error}")

    offsets, cursor = [], 0.0
    for duration in edit_durations:
        offsets.append(cursor)
        cursor += duration
    edl = [{**segment.model_dump(), "tts_duration": narration.duration,
            "speech_duration": narration.speech_duration, "speech_units": narration.units,
            "edit_duration": duration, "timeline_start": offset}
           for segment, narration, duration, offset in zip(review.segments, narrations, edit_durations, offsets)]
    (outputs["edl"] / "review.json").write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
    shot_durations = [p['duration'] for s,d,n in zip(review.segments,edit_durations,narrations) for p in
                      (plan_shots([x.model_dump() for x in s.shots], d, fps, config['video']['duration_matching'],n.units)
                       if s.shots else [{'duration':d}])]
    flow_report = {'voice':config['tts']['voice'], 'reference':'1004.mp4', 'shot_count':len(shot_durations),
                   'shot_durations':shot_durations, 'picture_style':picture_style.model_dump(),
                   'subtitles_enabled':config['subtitle']['enabled'],
                   'segment_cadence':[n.metrics for n in narrations],
                   'legacy_single_range_segments':[s.id for s in review.segments if not s.shots],
                   'limitations':['Shot/content matching and audible mix still require review.',
                                  'A single-range legacy segment is not a reference-style shot montage.']}
    (output_root/'flow_report.json').write_text(json.dumps(flow_report,ensure_ascii=False,indent=2),encoding='utf-8')

    print("[6/8] Building subtitles")
    subtitles: str | None = None
    if config["subtitle"].get("enabled", True):
        subtitle_file = outputs["subtitles"] / "review.ass"
        generate_ass(
            [{"narration": unit["text"], "duration": unit["end"] - unit["start"],
              "start": offset + unit["start"]}
             for narration, offset in zip(narrations, offsets) for unit in narration.units],
            str(subtitle_file), font_size=int(config["subtitle"].get("font_size", 48)),
            max_chars_per_line=int(config["subtitle"].get("max_chars_per_line", 35)),
            width=width, height=height, position=config["subtitle"].get("position", "bottom"),
        )
        subtitles = str(subtitle_file)

    print("[7/8] Rendering")
    final = outputs["final"] / "final_review.mp4"
    candidate = outputs["final"] / "final_review.pending.mp4"
    render_final(
        str(concatenated), narration_files, offsets, str(candidate), background_audio=background_audio,
        subtitles_path=subtitles, background_volume=float(config["audio"].get("background_volume", 0.18)),
        narration_volume=float(config["audio"].get("narration_volume", 1.0)),
        **encoding, fps=fps, picture_style=picture_style.model_dump(),
    )

    final_metadata = probe_video(candidate)
    if (abs(final_metadata["duration"] - cursor) > 0.15 or
        final_metadata["video_codec"] != "h264" or final_metadata["audio_codec"] != "aac" or
        (final_metadata["width"], final_metadata["height"]) != (width, height)):
        raise RuntimeError(f"Final render failed duration/codec/dimensions validation: {final_metadata}")
    timing = policy.timing_report(review, metadata["duration"], measured, edit_durations,
                                  rendered_duration=final_metadata["duration"])
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    require_timing(timing)
    candidate.replace(final)
    print("[8/8] Validation complete")
    print(f"      Output: {final} ({final_metadata['duration']:.2f}s)")
    return final
