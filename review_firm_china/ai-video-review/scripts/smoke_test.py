"""Run reproducible setup checks; writes output/smoke_results.json."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demucs", action="store_true", help="Also separate the synthetic WAV (may download model)")
    args = parser.parse_args()
    os.chdir(ROOT)
    from src.audio.mixer import extract_audio

    results = {}
    checks = [
        ("environment", ["scripts/check_environment.py"]),
        ("regressions", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("ffmpeg", ["scripts/test_ffmpeg.py", "--duration", "60"]),
        ("scenedetect", ["scripts/detect_scenes.py", "input/videos/test_synthetic.mp4"]),
        ("tts", ["scripts/test_tts.py"]),
        ("demucs_import", ["scripts/test_demucs.py"]),
        ("end_to_end", ["scripts/build_review.py", "--video", "input/videos/test_synthetic.mp4",
                       "--review", "examples/review.example.json", "--output-dir", "output/editorial_smoke"]),
    ]
    for label, command in checks:
        print(f"Testing {label}...", flush=True)
        result = subprocess.run([sys.executable, "-u", *command], text=True, encoding="utf-8",
                                errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        results[label] = {"status": "PASS" if result.returncode == 0 else "FAIL", "log": result.stdout}
        print(result.stdout, flush=True)
    if args.demucs:
        extract_audio("input/videos/test_synthetic.mp4", "input/audio/test.wav")
        result = subprocess.run([sys.executable, "-u", "scripts/test_demucs.py", "input/audio/test.wav"],
                                text=True, encoding="utf-8", errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        results["demucs_separation"] = {"status": "PASS" if result.returncode == 0 else "FAIL", "log": result.stdout}
        print(result.stdout, flush=True)
    Path("output").mkdir(exist_ok=True)
    Path("output/smoke_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if all(item["status"] == "PASS" for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
