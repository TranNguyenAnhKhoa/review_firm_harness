from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.audio.narration_builder import NarrationBuilder
from src.pipeline.build_review import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the configured flow voice through the narration pipeline.")
    parser.add_argument("--config", default=str(ROOT / "config/config.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output/tts_default_smoke/narration.wav"))
    args = parser.parse_args()
    config = load_config(args.config)
    result = NarrationBuilder(config["tts"], config["audio"]["narration"],
                              cache_dir=ROOT / "output/tts_default_smoke/silence").build(
        "Đây là bài kiểm tra hệ thống tạo giọng đọc tiếng Việt.", args.output)
    if result.duration <= 0:
        raise RuntimeError("No valid TTS audio duration")
    print(f"PASS: {config['tts']['provider']} / {config['tts']['voice']}: {result.path} ({result.duration:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
