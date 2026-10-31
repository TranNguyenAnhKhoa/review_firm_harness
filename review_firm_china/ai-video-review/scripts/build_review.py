from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline.build_review import build_review


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Create a narrated review video using FFmpeg.")
    parser.add_argument("--video", required=True, help="Path to source movie/video")
    parser.add_argument("--review", required=True, help="Path to validated review.json")
    parser.add_argument("--config", default=str(ROOT / "config" / "config.yaml"))
    parser.add_argument("--output-dir", default="output", help="Separate artifact directory (e.g. for test runs)")
    parser.add_argument("--tts-only", action="store_true", help="Generate TTS and validate measured editorial duration; do not render")
    args = parser.parse_args()
    try:
        build_review(args.video, args.review, args.config, output_dir=args.output_dir, tts_only=args.tts_only)
    except Exception as error:
        raise SystemExit(f"Build failed: {error}") from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
