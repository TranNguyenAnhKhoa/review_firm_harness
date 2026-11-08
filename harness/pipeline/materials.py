"""READ materials an agent can look at, every one stamped with source timestamps.

agy (Gemini) views video files: the film is cut into small proxy chunks (low resolution, mono audio)
with the source timecode burned into the top-left corner, so a chunk's local time never leaks into
the timeline. claude/codex see images only: one FFmpeg decode pass samples frames every N seconds and
the bottom subtitle band every S seconds; OpenCV tiles them into sheets with the source time on each
tile. Scene cuts (PySceneDetect) are listed for both, to keep shots inside one camera take.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import cv2
import numpy as np

from harness.utils import ffmpeg, format_seconds, read_json, run_command, sha256_text, write_json

LABEL_BAND = 24
FONT = cv2.FONT_HERSHEY_SIMPLEX


def frame_interval(duration: float, settings: dict) -> float:
    fixed = float(settings.get("frame_interval") or 0)
    if fixed > 0:
        return fixed
    raw = duration / max(1, int(settings.get("max_frames", 480)))
    for nice in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 30, 45, 60):
        if raw <= nice:
            return float(nice)
    return float(math.ceil(raw))


def _label(image: np.ndarray, text: str) -> np.ndarray:
    band = np.zeros((LABEL_BAND, image.shape[1], 3), dtype=np.uint8)
    cv2.putText(band, text, (6, LABEL_BAND - 7), FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([band, image])


def _sheet(tiles: list[np.ndarray], columns: int) -> np.ndarray:
    height, width = tiles[0].shape[:2]
    rows = math.ceil(len(tiles) / columns)
    canvas = np.full((rows * height, columns * width, 3), 32, dtype=np.uint8)
    for index, tile in enumerate(tiles):
        r, c = divmod(index, columns)
        canvas[r * height:(r + 1) * height, c * width:c * width + tile.shape[1]] = tile[:height, :width]
    return canvas


def _clock(seconds: float) -> str:
    return f"{format_seconds(seconds)} ({seconds:.0f}s)"


def _font() -> str | None:
    from harness import ROOT
    for candidate in (ROOT / ".tools/conda/fonts/DejaVuSans.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                      Path("/usr/share/fonts/TTF/DejaVuSans.ttf")):
        if candidate.is_file():
            return str(candidate)
    return None


def build_proxies(job, duration: float, settings: dict, folder: Path, log=print) -> list[dict]:
    """Proxy chunks for a video-native agent: small enough for its file reader, timecode burned in."""
    conf = settings.get("proxy") or {}
    height = int(conf.get("height", 360)) // 2 * 2
    chunk = max(60.0, float(conf.get("chunk_minutes", 10)) * 60)
    fps = float(conf.get("fps", 10))
    target = folder / "proxy"
    target.mkdir(parents=True, exist_ok=True)
    font = _font()
    chunks, start = [], 0.0
    while start < duration - 0.5:
        length = min(chunk, duration - start)
        name = f"part_{len(chunks) + 1:02d}.mp4"
        offset = f"{start:.3f}"
        stamp = (f"drawtext={'fontfile=' + font + ':' if font else ''}"
                 f"text='%{{pts\\:hms\\:{offset}}}  %{{eif\\:t+{offset}\\:d}}s':x=8:y=8:fontsize={max(14, height // 18)}:"
                 "fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=4")
        run_command([ffmpeg(), "-hide_banner", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                     "-i", str(job.source), "-vf", f"scale=-2:{height},fps={fps:g},{stamp}",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", str(int(conf.get("crf", 32))),
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", f"{int(conf.get('audio_kbps', 48))}k", "-ac", "1",
                     "-movflags", "+faststart", str(target / name)])
        size = (target / name).stat().st_size
        chunks.append({"file": f"02_read/materials/proxy/{name}", "start": round(start, 3),
                       "end": round(start + length, 3), "bytes": size})
        log(f"Proxy {name}: {format_seconds(start)}-{format_seconds(start + length)} ({size / 1e6:.1f} MB)")
        start += length
    return chunks


def build(job, metadata: dict, settings: dict, engine: str = "claude", log=print, force: bool = False) -> dict:
    """Create or reuse 02_read/materials/ for this source, engine and settings; return the manifest."""
    folder = job.stage_dir("read") / "materials"
    manifest_path = folder / "materials.json"
    duration = float(metadata["duration"])
    interval = frame_interval(duration, settings)
    strip_interval = float(settings.get("strip_interval", 2.0))
    video_agent = engine == "agy"
    keys = ("sheet_columns", "sheet_rows", "frame_width", "subtitle_strips", "strip_height_ratio", "scene_detect",
            "transcript", "whisper_model", "whisper_language", "proxy")
    signature = sha256_text(json.dumps({"source": job.manifest()["source"], "interval": interval, "video": video_agent,
                                        "strip_interval": strip_interval,
                                        **{k: settings.get(k) for k in keys}}, sort_keys=True))
    previous = read_json(manifest_path, {}) or {}
    files = previous.get("sheets", []) + previous.get("strip_sheets", []) + previous.get("proxy", [])
    if not force and previous.get("signature") == signature and all((job.root / s["file"]).is_file() for s in files):
        log(f"Materials up to date: {len(previous.get('proxy', []))} proxy chunks, {len(previous.get('sheets', []))} "
            f"frame sheets, {len(previous.get('strip_sheets', []))} subtitle sheets")
        return previous
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    if video_agent:
        proxy = build_proxies(job, duration, settings, folder, log)
        scenes_file, scene_count = _scenes(job, folder, settings, log)
        manifest = {"signature": signature, "duration": duration, "engine": engine, "proxy": proxy,
                    "sheets": [], "strip_sheets": [], "frame_interval": None, "strip_interval": None,
                    "scenes": scenes_file, "scene_count": scene_count,
                    "transcript": _transcript(job, folder, settings, log) if settings.get("transcript") == "whisper" else None}
        write_json(manifest_path, manifest)
        return manifest
    raw_frames, raw_strips = folder / "raw_frames", folder / "raw_strips"
    raw_frames.mkdir(parents=True)
    width = int(settings.get("frame_width", 384)) // 2 * 2
    strips = bool(settings.get("subtitle_strips", True))
    ratio = float(settings.get("strip_height_ratio", 0.2))
    log(f"Sampling frames every {interval:g}s" + (f" and subtitle strips every {strip_interval:g}s" if strips else "")
        + " (one decode pass)")
    graph = f"[0:v]fps=1/{interval},scale={width}:-2[f]"
    outputs = ["-map", "[f]", "-q:v", "4", "-start_number", "0", str(raw_frames / "f_%05d.jpg")]
    if strips:
        raw_strips.mkdir()
        graph = (f"[0:v]split=2[a][b];[a]fps=1/{interval},scale={width}:-2[f];"
                 f"[b]fps=1/{strip_interval},crop=iw:trunc(ih*{ratio}/2)*2:0:ih-trunc(ih*{ratio}/2)*2,scale=960:-2[s]")
        outputs += ["-map", "[s]", "-q:v", "4", "-start_number", "0", str(raw_strips / "s_%05d.jpg")]
    run_command([ffmpeg(), "-hide_banner", "-v", "error", "-y", "-i", str(job.source),
                 "-filter_complex", graph, *outputs])

    columns, rows = int(settings.get("sheet_columns", 4)), int(settings.get("sheet_rows", 4))
    per_sheet = columns * rows
    frames = sorted(raw_frames.glob("f_*.jpg"))
    sheets_dir = folder / "sheets"
    sheets_dir.mkdir()
    sheets = []
    for start in range(0, len(frames), per_sheet):
        batch = frames[start:start + per_sheet]
        tiles, times = [], []
        for path in batch:
            t = int(path.stem.split("_")[1]) * interval
            image = cv2.imread(str(path))
            if image is None:
                continue
            tiles.append(_label(image, _clock(t)))
            times.append(t)
        if not tiles:
            continue
        name = f"sheet_{len(sheets) + 1:03d}.jpg"
        cv2.imwrite(str(sheets_dir / name), _sheet(tiles, columns), [cv2.IMWRITE_JPEG_QUALITY, 82])
        sheets.append({"file": f"02_read/materials/sheets/{name}", "start": times[0],
                       "end": min(duration, times[-1] + interval), "frames": len(tiles)})
    log(f"{len(frames)} frames -> {len(sheets)} frame sheets ({columns}x{rows}, {interval:g}s apart)")

    strip_sheets = []
    if strips:
        strip_sheets = _strip_sheets(sorted(raw_strips.glob("s_*.jpg")), strip_interval, duration, folder / "subtitles")
        log(f"Subtitle band -> {len(strip_sheets)} strip sheets (unchanged strips merged)")
    shutil.rmtree(raw_frames, ignore_errors=True)
    shutil.rmtree(raw_strips, ignore_errors=True)

    scenes_file, scene_count = _scenes(job, folder, settings, log)
    transcript_file = None
    if settings.get("transcript") == "whisper":
        transcript_file = _transcript(job, folder, settings, log)

    manifest = {"signature": signature, "duration": duration, "engine": engine, "proxy": [], "frame_interval": interval,
                "strip_interval": strip_interval if strips else None, "frames": len(frames),
                "sheets": sheets, "strip_sheets": strip_sheets, "scenes": scenes_file, "scene_count": scene_count,
                "transcript": transcript_file}
    write_json(manifest_path, manifest)
    return manifest


def _scenes(job, folder: Path, settings: dict, log) -> tuple[str | None, int | None]:
    if not settings.get("scene_detect", True):
        return None, None
    from harness.video.scene_detect import detect_scenes
    log("Detecting scene cuts (PySceneDetect)")
    scenes = detect_scenes(str(job.source), threshold=float(settings.get("scene_threshold", 27.0)))
    write_json(folder / "scenes.json", scenes)
    log(f"{len(scenes)} scenes")
    return "02_read/materials/scenes.json", len(scenes)


def _strip_sheets(paths: list[Path], interval: float, duration: float, target: Path, per_sheet: int = 14) -> list[dict]:
    target.mkdir(parents=True)
    groups: list[dict] = []   # consecutive strips with (nearly) the same pixels become one row
    previous = None
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            continue
        t = int(path.stem.split("_")[1]) * interval
        small = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (96, 12)).astype(np.int16)
        if previous is not None and float(np.abs(small - previous).mean()) < 4.0:
            groups[-1]["end"] = min(duration, t + interval)
        else:
            groups.append({"image": image, "start": t, "end": min(duration, t + interval)})
        previous = small
    sheets = []
    for start in range(0, len(groups), per_sheet):
        batch = groups[start:start + per_sheet]
        rows = []
        for group in batch:
            image = group["image"]
            label = np.zeros((image.shape[0], 150, 3), dtype=np.uint8)
            cv2.putText(label, format_seconds(group["start"]), (6, image.shape[0] // 2 - 4), FONT, 0.6,
                        (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(label, f"{group['start']:.0f}-{group['end']:.0f}s", (6, image.shape[0] // 2 + 18), FONT, 0.45,
                        (190, 190, 190), 1, cv2.LINE_AA)
            row = np.hstack([label, image])
            rows.append(np.vstack([row, np.full((2, row.shape[1], 3), 90, dtype=np.uint8)]))
        name = f"subs_{len(sheets) + 1:03d}.jpg"
        cv2.imwrite(str(target / name), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
        sheets.append({"file": f"02_read/materials/subtitles/{name}", "start": batch[0]["start"],
                       "end": batch[-1]["end"], "rows": len(batch)})
    return sheets


def _transcript(job, folder: Path, settings: dict, log) -> str | None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("read.transcript=whisper but faster-whisper is missing: ./setup.sh --with-optional. Skipped.")
        return None
    from harness.utils import project_path
    audio = folder / "audio_16k.wav"
    run_command([ffmpeg(), "-v", "error", "-y", "-i", str(job.source), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
    log(f"Whisper {settings.get('whisper_model', 'small')} transcript (CPU)")
    model = WhisperModel(settings.get("whisper_model", "small"), device="cpu", compute_type="int8",
                         download_root=str(project_path("models/whisper")))
    segments, info = model.transcribe(str(audio), language=settings.get("whisper_language") or None,
                                      vad_filter=True, beam_size=3, condition_on_previous_text=False)
    lines = [f"[{s.start:8.2f} - {s.end:8.2f}] {s.text.strip()}" for s in segments]
    path = folder / "transcript.txt"
    path.write_text(f"# language={info.language} p={info.language_probability:.2f}\n" + "\n".join(lines) + "\n",
                    encoding="utf-8")
    audio.unlink(missing_ok=True)
    log(f"Transcript: {len(lines)} lines")
    return "02_read/materials/transcript.txt"


def zoom_frames(job, times: list[float], width: int = 1280) -> list[Path]:
    """Full-size frames at exact times (an agent tool: ./run.sh frame <job> <seconds>...)."""
    folder = job.stage_dir("read") / "materials" / "zoom"
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for t in times:
        if not math.isfinite(t) or t < 0:
            raise ValueError(f"Bad time {t}")
        path = folder / f"t_{t:09.2f}.jpg"
        if not path.is_file():
            run_command([ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(job.source), "-frames:v", "1",
                         "-vf", f"scale={width}:-2", "-q:v", "3", str(path)])
        out.append(path)
    return out
