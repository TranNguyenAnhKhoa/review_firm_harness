from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.audio.speech import SpeechUnit


class ReviewShot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    weight: float = Field(default=1, gt=0)
    speech_unit_id: str | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.source_end <= self.source_start:
            raise ValueError("Shot source_end must exceed source_start")
        return self


class ReviewSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)
    id: int = Field(gt=0)
    narration: str | list[SpeechUnit] = Field(min_length=1)
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    visual_intent: str = ""
    target_duration: float | None = Field(default=None, gt=0)
    keep_original_audio: bool = True
    section: Literal["story", "assessment"] = "story"
    shots: list[ReviewShot] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def validate_range(self) -> "ReviewSegment":
        if self.source_end <= self.source_start:
            raise ValueError("source_end must be greater than source_start")
        if any(s.source_start < self.source_start or s.source_end > self.source_end for s in self.shots):
            raise ValueError("Every shot must lie within its segment's source_start/source_end")
        if any(s.speech_unit_id is not None for s in self.shots):
            if not isinstance(self.narration, list) or any(u.id is None for u in self.narration):
                raise ValueError('Anchored shots require narration units with explicit IDs')
            unit_ids = [u.id for u in self.narration]
            anchors = [s.speech_unit_id for s in self.shots]
            groups = [a for i,a in enumerate(anchors) if i == 0 or a != anchors[i-1]]
            if groups != unit_ids:
                raise ValueError('Shot anchors must cover every narration unit in narration order')
        if isinstance(self.narration, list):
            ids = [u.id for u in self.narration if u.id is not None]
            if len(ids) != len(set(ids)):
                raise ValueError("Speech unit IDs must be unique within a segment")
        return self

    @property
    def narration_text(self) -> str:
        return self.narration if isinstance(self.narration, str) else " ".join(u.text for u in self.narration)


class ReviewScript(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)
    title: str = Field(min_length=1)
    source_video: str | None = None
    segments: list[ReviewSegment] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> "ReviewScript":
        ids = [segment.id for segment in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("Segment IDs must be unique")
        assessments = [i for i, s in enumerate(self.segments) if s.section == "assessment"]
        if assessments and assessments != [len(self.segments) - 1]:
            raise ValueError("The assessment must appear exactly once, at the end")
        return self

    @classmethod
    def load(cls, path: str | Path) -> "ReviewScript":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8-sig"))
