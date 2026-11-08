"""Numeric speech contracts, validated configuration, and safe parameter limits."""
from __future__ import annotations

import logging
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

log = logging.getLogger(__name__)
Emotion = Literal["normal", "suspense", "excited", "serious", "punchline", "calm"]
EMOTIONS = ("normal", "suspense", "excited", "serious", "punchline", "calm")
LIMITS = {"rate_percent": (-20, 30), "pitch_hz": (-25, 20),
          "volume_percent": (-10, 10), "pause_before_ms": (0, 2000),
          "pause_after_ms": (0, 2000)}


def clamp(value: int | float, low: int | float, high: int | float, name: str):
    bounded = max(low, min(high, value))
    if bounded != value:
        log.warning("%s=%s outside safe range; clamped to %s", name, value, bounded)
    return bounded


class SpeechUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    id: str | None = None
    text: str = Field(min_length=1)
    emotion: Emotion = "normal"
    rate_percent: int | None = None
    pitch_hz: int | None = None
    volume_percent: int | None = None
    pause_before_ms: int | None = None
    pause_after_ms: int | None = None

    @field_validator(*LIMITS)
    @classmethod
    def safe_numeric(cls, value, info):
        return None if value is None else int(clamp(value, *LIMITS[info.field_name], info.field_name))


class Preset(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    rate_percent: int
    pitch_hz: int
    volume_percent: int = 0
    pause_before_ms: int = 0
    pause_after_ms: int = 0

    @field_validator(*LIMITS)
    @classmethod
    def safe_numeric(cls, value, info):
        return int(clamp(value, *LIMITS[info.field_name], info.field_name))


class NaturalVariation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    rate_jitter_percent: int = 2
    pitch_jitter_hz: int = 2
    pause_jitter_ms: int = 30
    seed: int = 42

    @field_validator("rate_jitter_percent", "pitch_jitter_hz", "pause_jitter_ms")
    @classmethod
    def safe_jitter(cls, value, info):
        maximum = 100 if info.field_name == "pause_jitter_ms" else 5
        return int(clamp(value, 0, maximum, info.field_name))


class RateRange(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    min: float = Field(gt=0, le=15)
    max: float = Field(gt=0, le=15)

    @model_validator(mode="after")
    def ordered(self):
        if self.min > self.max:
            raise ValueError("Speech rate min must not exceed max")
        return self


class TargetSpeech(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    enabled: bool = True
    target_syllables_per_second: float = Field(default=4.2, gt=0, le=15)
    min_syllables_per_second: float = Field(default=3.7, gt=0, le=15)
    max_syllables_per_second: float = Field(default=4.8, gt=0, le=15)
    retry_limit: int = 2
    max_rate_adjustment_percent: int = 8

    @field_validator("retry_limit", "max_rate_adjustment_percent")
    @classmethod
    def safe_retry(cls, value, info):
        return int(clamp(value, 0, 2 if info.field_name == "retry_limit" else 8, info.field_name))

    @model_validator(mode="after")
    def ordered(self):
        if not self.min_syllables_per_second <= self.target_syllables_per_second <= self.max_syllables_per_second:
            raise ValueError("Target speech must satisfy min <= target <= max")
        return self


class MicroPause(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    comma_ms: int = 90
    semicolon_ms: int = 150
    colon_ms: int = 120
    ellipsis_ms: int = 300

    @field_validator("comma_ms", "semicolon_ms", "colon_ms", "ellipsis_ms")
    @classmethod
    def safe_pause(cls, value, info):
        return int(clamp(value, 0, 2000, info.field_name))


class ZeroTTSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    # A local folder of real files (setup.sh downloads repo@revision there). onnxruntime >= 1.31 refuses
    # the symlinked Hugging Face cache layout on Linux, so the folder must not be a cache snapshot.
    model: str = "models/zerotts/ZeroTTS-c2bfbd67"
    repo: str = "zeroweight-ai/ZeroTTS"
    revision: str | None = "c2bfbd67dc648cac455077333f7cf5c18a2e3bb4"
    cache_dir: str = "models/zerotts/hf-cache"
    local_files_only: bool = True
    threads: int = Field(default=4, ge=1, le=32)
    seed: int = Field(default=42, ge=0, le=4294967295)
    max_chunk_seconds: float = Field(default=15, gt=0, le=30)


class VoiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["edge", "zerotts"] = "zerotts"
    language: str = "vi-VN"
    voice: str | None = None
    zerotts: ZeroTTSConfig = Field(default_factory=ZeroTTSConfig)
    # Legacy direct-provider settings; planned speech uses numeric presets instead.
    rate: str = "+0%"
    pitch: str = "+0Hz"
    presets: dict[Emotion, Preset]
    natural_variation: NaturalVariation = Field(default_factory=NaturalVariation)
    target_speech: TargetSpeech = Field(default_factory=TargetSpeech)
    speech_rate_ranges: dict[Emotion, RateRange] = Field(default_factory=dict)
    micro_pause: MicroPause = Field(default_factory=MicroPause)
    pause_boundary: Literal["max", "additive"] = "max"

    @model_validator(mode="after")
    def complete_presets(self):
        missing = set(EMOTIONS) - self.presets.keys()
        if missing:
            raise ValueError(f"Missing emotion presets: {sorted(missing)}")
        return self


class LoudnessConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    loudness_lufs: float = -16
    true_peak_db: float = -1.5

    @field_validator("loudness_lufs", "true_peak_db")
    @classmethod
    def safe_loudness(cls, value, info):
        bounds = (-30, -10) if info.field_name == "loudness_lufs" else (-9, -1)
        return float(clamp(value, *bounds, info.field_name))
