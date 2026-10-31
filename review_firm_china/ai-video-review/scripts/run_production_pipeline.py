"""
Automated production runner for ga_kim_thoa_ep01:
Stage 4 (MEASURE & ZeroTTS) -> Stage 5 & 6 (Render Measured Review) -> Stage 7 (QC Certification)
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PYTHON = sys.executable
VIDEO = ROOT / "input" / "videos" / "ga_kim_thoa_ep01.mp4"
REVIEW = ROOT / "input" / "scripts" / "review.ga_kim_thoa_ep01.json"
TTS_DIR = ROOT / "output" / "ga_kim_thoa_ep01_tts"
RENDER_DIR = ROOT / "output" / "ga_kim_thoa_ep01_render"
CONFIG = ROOT / "config" / "config.yaml"


def log(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def run_stage_4() -> bool:
    log("=== STAGE 4: MEASURE & ZeroTTS (Offline Bảo Trang) ===")
    cmd = [
        PYTHON,
        str(ROOT / "scripts" / "measure_review.py"),
        "--video", str(VIDEO),
        "--review", str(REVIEW),
        "--output-dir", str(TTS_DIR),
        "--config", str(CONFIG),
        "--workers", "2",
    ]
    log(f"Executing: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    for line in iter(process.stdout.readline, ""):
        line_clean = line.rstrip()
        if line_clean:
            print(f"  [TTS] {line_clean}", flush=True)
    process.wait()
    if process.returncode != 0:
        log(f"Stage 4 FAILED with exit code {process.returncode}")
        return False
    log("Stage 4 COMPLETED successfully.")
    return True


def check_timing_report() -> bool:
    timing_file = TTS_DIR / "review_timing.json"
    if not timing_file.exists():
        log(f"ERROR: Timing file not found: {timing_file}")
        return False
    data = json.loads(timing_file.read_text(encoding="utf-8"))
    log("=== TIMING REPORT AUDIT ===")
    log(f"  Passed: {data.get('passed')}")
    log(f"  Review Duration: {data.get('review_duration', 0):.2f}s")
    log(f"  Source Ratio: {data.get('source_ratio', 0):.2%}")
    log(f"  Assessment Narration: {data.get('assessment_narration_duration', 0):.2f}s")
    if not data.get("passed"):
        log(f"  Errors: {data.get('errors')}")
        return False
    return True


def run_stage_5_6_7() -> bool:
    log("=== STAGE 5, 6 & 7: Shot Fitting, FFmpeg Render & QC Certification ===")
    cmd = [
        PYTHON,
        str(ROOT / "scripts" / "render_measured_review.py"),
        "--video", str(VIDEO),
        "--review", str(REVIEW),
        "--tts-dir", str(TTS_DIR),
        "--output-dir", str(RENDER_DIR),
        "--config", str(CONFIG),
        "--workers", "2",
        "--threads", "3",
    ]
    log(f"Executing: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    for line in iter(process.stdout.readline, ""):
        line_clean = line.rstrip()
        if line_clean:
            print(f"  [RENDER] {line_clean}", flush=True)
    process.wait()
    if process.returncode != 0:
        log(f"Stage 5/6/7 FAILED with exit code {process.returncode}")
        return False
    log("Stage 5/6/7 COMPLETED successfully.")
    return True


def main() -> int:
    log("Starting end-to-end production pipeline...")
    if not run_stage_4():
        return 1
    if not check_timing_report():
        return 1
    if not run_stage_5_6_7():
        return 1
    log("ALL STAGES COMPLETED SUCCESSFULLY!")
    final_video = RENDER_DIR / "final" / "final_review.mp4"
    if final_video.exists():
        stat = final_video.stat()
        log(f"Final Video: {final_video} ({stat.st_size / (1024*1024):.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

