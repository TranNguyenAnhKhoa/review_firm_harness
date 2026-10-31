from __future__ import annotations

from pathlib import Path
import logging
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Literal
from src.audio.speech import clamp

from src.utils import ensure_parent, executable, run_command
from src.video.probe import probe_video

log = logging.getLogger(__name__)


class DurationMatching(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    enabled: bool = True
    min_speed: float = 0.90
    max_speed: float = 1.10
    fallback: Literal["freeze", "error"] = "freeze"

    @field_validator("min_speed", "max_speed")
    @classmethod
    def safe_speed(cls, value, info):
        limits = (0.90, 1.0) if info.field_name == "min_speed" else (1.0, 1.10)
        return float(clamp(value, *limits, info.field_name))


def match_duration(start: float, end: float, target: float, settings: dict | None = None) -> dict:
    selected, used, padding = choose_centered_range(start, end, target)
    config = DurationMatching.model_validate(settings or {"enabled": False})
    speed = 1.0
    available = end - start
    if config.enabled:
        ratio = available / target
        if config.min_speed <= ratio <= config.max_speed:
            selected, used, speed, padding = start, available, ratio, 0.0
        elif available < target:
            selected, used, speed = start, available, config.min_speed
            padding = max(0.0, target - available / speed)
    if padding > 1e-6:
        message = (f"Footage {available:.3f}s cannot cover narration {target:.3f}s at speed {speed:.3f}; "
                   f"source_end is preserved; last-frame hold required: {padding:.3f}s")
        if config.fallback == "error":
            raise ValueError(message)
        log.warning(message)
    return {"start": selected, "source_duration": used, "speed": speed, "freeze_duration": padding}


def choose_centered_range(source_start: float, source_end: float, target_duration: float) -> tuple[float, float, float]:
    """MVP selection policy; replace this function with an AI best-shot selector later."""
    if source_start < 0 or source_end <= source_start or target_duration <= 0:
        raise ValueError("Require 0 <= start < end and target_duration > 0")
    available = source_end - source_start
    used_duration = min(available, target_duration)
    start = source_start + (available - used_duration) / 2
    return start, used_duration, max(0.0, target_duration - used_duration)


def cut_clip(
    video_path: str,
    start: float,
    end: float,
    target_duration: float,
    output_path: str,
    *,
    keep_original_audio: bool = True,
    codec: str = "libx264",
    crf: int = 20,
    preset: str = "medium",
    fps: float | None = None,
    resolution: tuple[int, int] | None = None,
    duration_matching: dict | None = None,
) -> Path:
    """Cut a center-selected range and freeze its last frame if narration is longer."""
    if target_duration <= 0:
        raise ValueError("target_duration must be positive")
    metadata = probe_video(video_path)
    if end > metadata["duration"] + 0.001:
        raise ValueError("Source range exceeds video duration")
    selection = match_duration(start, end, target_duration, duration_matching)
    selected_start, used_duration = selection["start"], selection["source_duration"]
    pad_duration, speed = selection["freeze_duration"], selection["speed"]
    fps = fps or metadata["fps"] or 30.0
    output = ensure_parent(output_path)
    audio_volume = "1" if keep_original_audio else "0"
    video_filter = (
        f"trim=duration={used_duration:.6f},setpts=(PTS-STARTPTS)/{speed:.9f},"
        f"fps={fps},tpad=stop_mode=clone:stop_duration={pad_duration + 1 / fps:.6f},"
        f"trim=duration={target_duration:.6f},scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1"
    )
    if resolution:
        width, height = resolution
        video_filter += (f",scale={width}:{height}:force_original_aspect_ratio=decrease,"
                         f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1")
    audio_filter = (
        f"atrim=duration={used_duration:.6f},asetpts=PTS-STARTPTS,atempo={speed:.9f},volume={audio_volume},"
        f"aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={target_duration:.6f},"
        f"afade=t=in:d=0.02,afade=t=out:st={max(0, target_duration - 0.02):.6f}:d=0.02"
    )
    inputs = ["-ss", f"{selected_start:.6f}", "-t", f"{used_duration:.6f}", "-i", video_path]
    audio_label = "0:a"
    if not metadata["audio_codec"]:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio_label = "1:a"
    run_command(
        [
            executable("ffmpeg", "FFMPEG_BINARY"), "-hide_banner", "-y", *inputs,
            "-t", f"{target_duration:.6f}",
            "-filter_complex", f"[0:v]{video_filter}[v];[{audio_label}]{audio_filter}[a]",
            "-map", "[v]", "-map", "[a]", "-c:v", codec, "-crf", str(crf),
            "-preset", preset, "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000",
            "-movflags", "+faststart", str(output),
        ]
    )
    return output
