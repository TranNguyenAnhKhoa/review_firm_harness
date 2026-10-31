from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.audio.separator import demucs_device, separate_audio
from src.video.probe import probe_audio


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Demucs or separate a supplied WAV/audio file.")
    parser.add_argument("audio", nargs="?", help="Optional audio source, e.g. input/audio/test.wav")
    args = parser.parse_args()
    importlib.import_module("demucs")
    importlib.import_module("demucs.separate")
    print(f"PASS: Demucs import; device={demucs_device()}")
    if args.audio:
        stems = separate_audio(args.audio, str(ROOT / "output" / "audio" / "demucs"))
        for name in ("vocals", "no_vocals"):
            duration = probe_audio(stems[name])
            if abs(duration - probe_audio(args.audio)) > 0.1:
                raise RuntimeError(f"Invalid duration for {name}: {duration}")
        print(f"PASS: stems -> {stems}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
