from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pipeline.build_review import load_config
from src.pipeline.editorial import EditorialPolicy
from src.video.probe import probe_video


def main() -> int:
    parser = argparse.ArgumentParser(description="Print source-specific duration budget for manual script writing.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--config", default=str(ROOT / "config/config.yaml"))
    args = parser.parse_args()
    policy = EditorialPolicy.model_validate(load_config(args.config)["editorial"])
    print(json.dumps(policy.budget(probe_video(args.video)["duration"]), indent=2, ensure_ascii=False))
    print("Total includes the final assessment. TTS measurement, not word count, decides compliance.")
    print("Writing instructions: prompts/write_review.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
