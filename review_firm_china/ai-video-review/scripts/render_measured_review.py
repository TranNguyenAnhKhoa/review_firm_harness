"""Render a checked review from verified measured TTS, without network or regeneration."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.measure_review import cache_signatures
from src.pipeline.build_review import load_config
from src.pipeline.editorial import EditorialPolicy, require_timing
from src.pipeline.schema import ReviewScript
from src.subtitle.generator import generate_ass
from src.utils import executable, run_command
from src.video.clipper import match_duration
from src.video.probe import probe_audio, probe_video
from src.video.renderer import render_measured_segment, concat_measured_segments
from src.video.montage import plan_shots
from src.video.picture_style import PictureStyle


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def render(args: argparse.Namespace) -> Path:
    started = time.monotonic()
    config = load_config(args.config)
    if config["audio"].get("use_demucs"):
        raise ValueError("Cached single-pass renderer uses original background; set use_demucs=false")
    picture_style = PictureStyle.model_validate(config['render']['picture_style'])
    if not config["render"].get("keep_source_resolution", True) and not picture_style.enabled:
        raise ValueError("Cached renderer currently preserves source resolution only")
    video, review_file = Path(args.video).resolve(), Path(args.review).resolve()
    tts_root, output = Path(args.tts_dir).resolve(), Path(args.output_dir).resolve()
    if tts_root == output:
        raise ValueError("Use a separate output directory to preserve measurement results")
    metadata = probe_video(video)
    review = ReviewScript.load(review_file)
    review_hash = sha256(review_file)
    measured_report = json.loads((tts_root / "review_timing.json").read_text(encoding="utf-8"))
    require_timing(measured_report)
    if measured_report["review_sha256"] != review_hash:
        raise ValueError("Measured timing belongs to another review revision")
    if abs(measured_report["budget"]["source_duration"] - metadata["duration"]) > .001:
        raise ValueError("Measured timing belongs to a different source duration")
    if review.source_video and Path(review.source_video).resolve() != video:
        raise ValueError("Source video path does not match review.json")
    policy = EditorialPolicy.model_validate(config["editorial"])
    policy.validate_structure(review, metadata["duration"])
    fps = float(config["render"].get("fps") or metadata["fps"] or 30)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be positive and finite")
    audio_code_hash = hashlib.sha256(b"".join(
        p.read_bytes() for p in sorted((ROOT / "src/audio").glob("*.py")))).hexdigest()
    print("[1/8] Verifying source, review and all measured TTS caches", flush=True)
    entries, speech_durations, edit_durations, all_subtitles = [], [], [], []
    cursor = 0.0
    for index, segment in enumerate(review.segments):
        if segment.source_end > metadata["duration"] + .001:
            raise ValueError(f"Segment {segment.id}: range exceeds source")
        wav = tts_root / "audio" / f"segment_{segment.id:03d}.wav"
        debug_file = tts_root / "debug" / f"segment_{segment.id:03d}_tts.json"
        marker = json.loads((tts_root / "debug" / f"segment_{segment.id:03d}.cache.json").read_text(encoding="utf-8"))
        expected, _ = cache_signatures(segment, config, audio_code_hash, {})
        if (marker["signature"] != expected or marker["audio_sha256"] != sha256(wav)
                or marker["debug_sha256"] != sha256(debug_file)):
            raise ValueError(f"Segment {segment.id}: stale or modified TTS cache")
        debug = json.loads(debug_file.read_text(encoding="utf-8"))
        duration = probe_audio(wav)
        if abs(duration - debug["duration"]) > .001:
            raise ValueError(f"Segment {segment.id}: measured duration mismatch")
        edit_duration = math.ceil(duration * fps - 1e-6) / fps
        selection = (plan_shots([s.model_dump() for s in segment.shots], edit_duration, fps,
                               config['video']['duration_matching'],debug['units']) if segment.shots else
                     match_duration(segment.source_start, segment.source_end, edit_duration,
                                    config["video"]["duration_matching"]))
        for unit in debug["units"]:
            if not 0 <= unit["start"] < unit["end"] <= duration + .001:
                raise ValueError(f"Segment {segment.id}: invalid speech-unit timestamps")
            all_subtitles.append({"narration": unit["text"], "start": cursor + unit["start"],
                                  "duration": unit["end"] - unit["start"]})
        entries.append({"index": index, "segment": segment.model_dump(), "audio": str(wav),
                        "audio_sha256": marker["audio_sha256"], "tts_duration": duration,
                        "speech_duration": debug["speech_duration"], "speech_units": debug["units"],
                        "edit_duration": edit_duration, "timeline_start": cursor, "selection": selection})
        speech_durations.append(debug["speech_duration"])
        edit_durations.append(edit_duration)
        cursor += edit_duration
    timing = policy.timing_report(review, metadata["duration"], speech_durations, edit_durations)
    require_timing(timing)
    print(f"[2/8] Timing PASS: {cursor:.3f}s ({timing['source_ratio']:.2%}); "
          f"assessment speech {speech_durations[-1]:.3f}s", flush=True)
    implementation_files = [Path(__file__), ROOT / "src/video/renderer.py", ROOT / "src/video/clipper.py",
                            ROOT / "src/subtitle/generator.py", ROOT/'src/video/montage.py',
                            ROOT/'src/video/picture_style.py']
    signature_data = {"source_sha256": sha256(video), "review_sha256": review_hash,
                      "config": config, "entries": entries, "source_metadata": metadata,
                      "implementation": {str(p.relative_to(ROOT)): sha256(p) for p in implementation_files}}
    fingerprint = hashlib.sha256(json.dumps(signature_data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    manifest = output / "render_manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8"))["fingerprint"] != fingerprint:
            raise ValueError("Output directory belongs to different inputs/settings/code; choose a new directory")
    elif output.exists() and any(output.iterdir()):
        raise FileExistsError("Nonempty output directory without matching manifest; choose a new directory")
    else:
        write_json(manifest, {"fingerprint": fingerprint, **signature_data,
                              "editorial_status": "partial: picture/voice review still required"})
    final = output / "final/final_review.mp4"
    report_path = output / "review_timing.json"
    if final.exists():
        if report_path.exists():
            previous = json.loads(report_path.read_text(encoding="utf-8"))
            if previous.get("full_decode_passed") and previous.get("final_sha256") == sha256(final):
                print(f"Already rendered and verified: {final}", flush=True)
                return final
        raise FileExistsError("Existing final is not verified; preserve it and use another output directory")
    subtitle_options = {key: config["subtitle"][key] for key in
                        ("font_size", "max_chars_per_line", "position", "margin_vertical")
                        if key in config["subtitle"]}
    subtitle_options.update(width=metadata["width"] // 2 * 2, height=metadata["height"] // 2 * 2)
    if picture_style.enabled:
        subtitle_options.update(width=picture_style.width,height=picture_style.height)
    if config["subtitle"].get("enabled", True):
        generate_ass(all_subtitles, str(output / "subtitles/review.ass"), **subtitle_options)
    write_json(output / "edl/review.json", entries)
    print("[3/8] Subtitles use speech-unit timing plus frame-rounded video offsets", flush=True)
    print("[4/8] Rendering bounded segments; original background lowered; no TTS regeneration", flush=True)
    encoding = {key: config["video"][key] for key in ("codec", "crf", "preset")}

    def build(entry: dict) -> Path:
        segment = entry["segment"]
        # Index, not segment ID, preserves editorial list order.
        name = f"part_{entry['index'] + 1:03d}"
        clip = output / "clips" / f"{name}.mkv"
        cache = clip.with_suffix(".json")
        if clip.exists() and cache.exists():
            record = json.loads(cache.read_text(encoding="utf-8"))
            if record.get("fingerprint") == fingerprint and record.get("sha256") == sha256(clip):
                return clip
        subtitle = None
        if config["subtitle"].get("enabled", True):
            subtitle = generate_ass([
                {"narration": unit["text"], "start": unit["start"], "duration": unit["end"] - unit["start"]}
                for unit in entry["speech_units"]], str(output / "subtitles" / f"{name}.ass"), **subtitle_options)
        pending = clip.with_name(f"{name}.pending.mkv")
        render_measured_segment(str(video), entry["audio"], segment["source_start"], segment["source_end"],
            entry["edit_duration"], str(pending), metadata=metadata,
            subtitles_path=str(subtitle) if subtitle else None,
            keep_original_audio=segment["keep_original_audio"],
            background_volume=config["audio"]["background_volume"],
            narration_volume=config["audio"]["narration_volume"], **encoding, fps=fps,
            duration_matching=config["video"]["duration_matching"], threads=args.threads,
            shots=segment.get('shots'), picture_style=picture_style.model_dump(),unit_timings=entry['speech_units'])
        result = probe_video(pending)
        if (abs(result["duration"] - entry["edit_duration"]) > .002 or
                result["video_codec"] != "h264" or result["audio_codec"] != "pcm_s16le"):
            raise RuntimeError(f"Part {name}: invalid intermediate {result}")
        pending.replace(clip)
        write_json(cache, {"fingerprint": fingerprint, "sha256": sha256(clip), "metadata": result})
        return clip

    clips: list[Path | None] = [None] * len(entries)
    completed = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(build, entry): entry for entry in entries}
        try:
            for future in as_completed(futures):
                entry = futures[future]
                clips[entry["index"]] = future.result()
                completed.append(entry["index"] + 1)
                elapsed = time.monotonic() - started
                print(f"  [{len(completed)}/{len(entries)}] Part {entry['index']+1:03d} / "
                      f"segment {entry['segment']['id']}: {entry['edit_duration']:.2f}s; elapsed {elapsed:.0f}s", flush=True)
                write_json(output / "render_progress.json", {"status": "rendering", "completed": sorted(completed),
                           "total": len(entries), "elapsed_seconds": elapsed})
        except Exception:
            for future in futures:
                future.cancel()
            raise
    print("[5/8] Sequential concat: copy video, encode AAC once", flush=True)
    candidate = final.with_name("final_review.pending.mp4")
    concat_measured_segments(clips, edit_durations, str(candidate))
    result = probe_video(candidate)
    if (abs(result["duration"] - cursor) > .15 or result["video_codec"] != "h264"
            or result["audio_codec"] != "aac" or abs(result["fps"] - fps) > .001
            or (result["width"], result["height"]) != (subtitle_options["width"], subtitle_options["height"])):
        raise RuntimeError(f"Final metadata validation failed: {result}")
    timing = policy.timing_report(review, metadata["duration"], speech_durations, edit_durations,
                                  rendered_duration=result["duration"])
    require_timing(timing)
    print("[6/8] Full video/audio decode validation (no output rewrite)", flush=True)
    run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-xerror", "-threads", "3",
                 "-i", str(candidate), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    if sha256(review_file) != review_hash or sha256(video) != signature_data["source_sha256"]:
        raise RuntimeError("Source/review changed during render; refusing to certify")
    print("[7/8] Duration, editorial timing and complete decode PASS", flush=True)
    final_hash = sha256(candidate)
    timing.update(review_sha256=review_hash, source_sha256=signature_data["source_sha256"],
                  rendered=True, measurement_only=False, full_decode_passed=True,
                  final_sha256=final_hash, final_metadata=result, render_fingerprint=fingerprint,
                  editorial_status="partial: picture/voice review still required")
    write_json(report_path, timing)
    candidate.replace(final)
    write_json(output / "render_progress.json", {"status": "complete", "completed": sorted(completed),
               "total": len(entries), "elapsed_seconds": time.monotonic() - started, "output": str(final)})
    print(f"[8/8] Validation complete: {final} ({result['duration']:.3f}s)", flush=True)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("video", "review", "tts-dir", "output-dir"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--threads", type=int, choices=range(1, 9), default=3)
    args = parser.parse_args()
    try:
        render(args)
    except Exception as error:
        print(f"Render failed: {error}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
