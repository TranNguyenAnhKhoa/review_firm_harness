from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.video.scene_detect import detect_scenes, export_scenes


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect scene timestamps without splitting video files.")
    parser.add_argument("video")
    parser.add_argument("--threshold", type=float, default=27.0)
    parser.add_argument("--output", default=str(ROOT / "data" / "timeline" / "scenes.json"))
    args = parser.parse_args()
    scenes = detect_scenes(args.video, args.threshold)
    output = export_scenes(scenes, args.output)
    print(f"Detected {len(scenes)} scenes -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
