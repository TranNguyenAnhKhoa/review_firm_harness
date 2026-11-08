from __future__ import annotations

import json
from pathlib import Path

from scenedetect import ContentDetector, detect


def detect_scenes(video_path: str, threshold: float = 27.0) -> list[dict]:
    """Detect cuts and return timestamps only; no clips are generated."""
    scenes = detect(video_path, ContentDetector(threshold=threshold), start_in_scene=True)
    return [
        {
            "scene_id": f"scene_{index:04d}",
            "start": round(start.seconds, 3),
            "end": round(end.seconds, 3),
            "duration": round(end.seconds - start.seconds, 3),
        }
        for index, (start, end) in enumerate(scenes, start=1)
    ]


def export_scenes(scenes: list[dict], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
