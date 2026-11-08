from __future__ import annotations

import json
from pathlib import Path

from harness.utils import executable, run_command


def _probe(path: str | Path) -> dict:
    result = run_command(
        [
            executable("ffprobe", "FFPROBE_BINARY"),
            "-v", "error",
            "-show_entries", "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,duration:stream_side_data=rotation",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
    )
    return json.loads(result.stdout)


def _fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    numerator, denominator = value.split("/", 1)
    return round(float(numerator) / float(denominator), 6) if float(denominator) else None


def probe_video(path: str | Path) -> dict:
    """Read lightweight video/audio metadata through ffprobe."""
    data = _probe(path)
    streams = data.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    audio = next((item for item in streams if item.get("codec_type") == "audio"), {})
    if not video:
        raise ValueError(f"No video stream found: {path}")
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    rotation = next((s.get("rotation", 0) for s in video.get("side_data_list", []) if "rotation" in s), 0)
    if abs(rotation) % 180 == 90:
        width, height = height, width
    return {
        "duration": round(float(data.get("format", {}).get("duration", 0.0)), 6),
        "width": width,
        "height": height,
        "fps": _fps(video.get("r_frame_rate")),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
    }


def probe_audio(path: str | Path) -> float:
    """Return audio/container duration in seconds."""
    data = _probe(path)
    if not any(s.get("codec_type") == "audio" for s in data.get("streams", [])):
        raise ValueError(f"No audio stream found: {path}")
    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration <= 0:
        raise ValueError(f"Invalid audio duration: {path}")
    return duration
