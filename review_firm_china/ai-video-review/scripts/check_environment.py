from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import executable, run_command


def status(label: str, action) -> bool:
    try:
        value = action()
        print(f"[PASS] {label}: {value}")
        return True
    except Exception as error:
        print(f"[FAIL] {label}: {error}")
        return False


def main() -> int:
    checks = [
        status("Python", lambda: sys.version.split()[0]),
        status("FFmpeg", lambda: run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-version"], capture_output=True).stdout.splitlines()[0]),
        status("FFprobe", lambda: run_command([executable("ffprobe", "FFPROBE_BINARY"), "-version"], capture_output=True).stdout.splitlines()[0]),
    ]
    for package in ("scenedetect", "edge_tts", "zerotts", "demucs", "pydantic", "yaml"):
        checks.append(status(package, lambda package=package: importlib.import_module(package).__name__))
    try:
        import torch
        print(f"[INFO] PyTorch: {torch.__version__}; CUDA available: {torch.cuda.is_available()}")
        import demucs.separate
        checks.append(status("Demucs runtime", lambda: str(torch.ones(2).sum().item())))
    except Exception as error:
        print(f"[INFO] PyTorch/CUDA status unavailable: {error}")
        checks.append(False)
    print(json.dumps({"platform": platform.platform(), "ok": all(checks)}, ensure_ascii=False))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
