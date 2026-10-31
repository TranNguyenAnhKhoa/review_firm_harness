from __future__ import annotations

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import executable, run_command
from src.video.probe import probe_video


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=10, help="Use 60 for editorial smoke test")
    args = parser.parse_args()
    if not 0 < args.duration <= 3600:
        parser.error("--duration must be between 0 and 3600 seconds")
    output = ROOT / "input" / "videos" / "test_synthetic.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command([
        executable("ffmpeg", "FFMPEG_BINARY"), "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", str(args.duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output),
    ])
    metadata = probe_video(output)
    if not metadata["duration"] or metadata["width"] != 1280:
        raise RuntimeError(f"Invalid synthetic test video: {metadata}")
    print(f"PASS: {output} -> {metadata}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
