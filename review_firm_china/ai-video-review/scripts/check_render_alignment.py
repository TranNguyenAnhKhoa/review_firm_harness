"""Check rendered narration alignment against original WAVs and subtitle cue bounds.

This is a technical waveform/timestamp check, not an assessment of voice acting or
whether an image semantically matches a line. Requires the project's existing numpy.
"""
from __future__ import annotations
import argparse
import bisect
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import executable


def samples(path: Path, start: float, duration: float) -> np.ndarray:
    command = [executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-threads", "1",
               "-ss", f"{start:.6f}", "-i", str(path), "-t", f"{duration:.6f}",
               "-vn", "-ar", "8000", "-ac", "1", "-f", "f32le", "pipe:1"]
    result = subprocess.run(command, capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype="<f4").astype(np.float64)


def alignment(reference: np.ndarray, candidate: np.ndarray) -> dict:
    count = min(len(reference), len(candidate))
    reference, candidate = reference[:count], candidate[:count]
    scores = []
    # Search +/-20ms. Original background and AAC alter samples, but the voice
    # should remain strongly correlated at zero lag (within resampling tolerance).
    for lag in range(-160, 161):
        first = reference[max(0, -lag):min(count, count - lag)]
        second = candidate[max(0, lag):min(count, count + lag)]
        denominator = np.linalg.norm(first) * np.linalg.norm(second)
        score = float(np.dot(first, second) / denominator) if denominator else 0.0
        scores.append((score, lag))
    correlation, lag = max(scores)
    return {"lag_ms": lag / 8, "correlation": correlation,
            "passed": abs(lag / 8) <= 3 and correlation >= .70}


def seconds(value: str) -> float:
    hour, minute, sec = value.split(":")
    return int(hour) * 3600 + int(minute) * 60 + float(sec)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--parts", action="store_true", help="Inspect completed MKV parts instead of final")
    parser.add_argument("--indexes", type=int, nargs="+", default=[1, 17, 33, 49, 65, 81, 99])
    args = parser.parse_args()
    output = Path(args.output_dir)
    entries = json.loads((output / "edl/review.json").read_text(encoding="utf-8"))
    intervals = sorted((e["timeline_start"] + u["start"], e["timeline_start"] + u["end"])
                       for e in entries for u in e["speech_units"])
    starts = [item[0] for item in intervals]
    count, bad = 0, []
    for line in (output / "subtitles/review.ass").read_text(encoding="utf-8-sig").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        start, end = seconds(fields[1]), seconds(fields[2])
        unit = bisect.bisect_right(starts, start + .011) - 1
        count += 1
        if unit < 0 or start < intervals[unit][0] - .011 or end > intervals[unit][1] + .011:
            bad.append({"event": count, "start": start, "end": end})
    results = []
    for index in args.indexes:
        entry = entries[index - 1]
        media = (output / "clips" / f"part_{index:03d}.mkv" if args.parts
                 else output / "final/final_review.mp4")
        sample_duration = min(6.0, entry["tts_duration"])
        reference = samples(Path(entry["audio"]), 0, sample_duration)
        candidate = samples(media, 0 if args.parts else entry["timeline_start"], sample_duration)
        result = {"index": index, "segment_id": entry["segment"]["id"], **alignment(reference, candidate)}
        results.append(result)
        print(json.dumps(result), flush=True)
    report = {"subtitle_events": count, "subtitle_errors": bad, "audio_checks": results,
              "passed": not bad and all(r["passed"] for r in results),
              "scope": "sampled waveform alignment + all ASS boundaries; not editorial approval"}
    target = output / "qc" / ("part_alignment.json" if args.parts else "final_alignment.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Subtitle events: {count}; errors: {len(bad)}. Report: {target}", flush=True)
    if not report["passed"]:
        raise SystemExit("Alignment check failed; inspect report")


if __name__ == "__main__":
    main()
