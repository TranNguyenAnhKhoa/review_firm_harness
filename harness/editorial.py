"""Measured runtime rules; editorial tone itself still requires a human review."""
from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field, model_validator
from harness.schema import ReviewScript


class EditorialPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    min_source_ratio: float = Field(default=0.40, gt=0, le=1)
    max_source_ratio: float = Field(default=0.50, gt=0, le=1)
    preferred_source_ratio: float = Field(default=0.45, gt=0, le=1)
    assessment_min_seconds: float = Field(default=10, gt=0)
    assessment_max_seconds: float = Field(default=20, gt=0)
    assessment_target_seconds: float = Field(default=15, gt=0)
    tone: str = "humorous_youthful_contextual"

    @model_validator(mode="after")
    def ordered_bounds(self) -> "EditorialPolicy":
        if not self.min_source_ratio <= self.preferred_source_ratio <= self.max_source_ratio:
            raise ValueError("Require min_source_ratio <= preferred_source_ratio <= max_source_ratio")
        if not self.assessment_min_seconds <= self.assessment_target_seconds <= self.assessment_max_seconds:
            raise ValueError("Require assessment_min_seconds <= assessment_target_seconds <= assessment_max_seconds")
        return self

    def budget(self, source_duration: float) -> dict:
        if not math.isfinite(source_duration) or source_duration <= 0:
            raise ValueError("Source duration must be positive and finite")
        minimum = source_duration * self.min_source_ratio
        maximum = source_duration * self.max_source_ratio
        preferred = source_duration * self.preferred_source_ratio
        return {
            "source_duration": source_duration,
            "total_min": minimum,
            "total_max": maximum,
            "total_target": preferred,
            "assessment_min": self.assessment_min_seconds,
            "assessment_max": self.assessment_max_seconds,
            "assessment_target": self.assessment_target_seconds,
            "story_target": preferred - self.assessment_target_seconds,
        }

    def structure_errors(self, review: ReviewScript, source_duration: float) -> list[str]:
        budget = self.budget(source_duration)
        errors = []
        if budget["total_max"] <= self.assessment_min_seconds:
            errors.append("Source is too short for a story plus a 10-20s assessment within the configured ratio.")
        if len(review.segments) < 2 or not any(s.section == "story" for s in review.segments):
            errors.append("Review must contain a story followed by a separate assessment segment.")
        positions = [i for i, segment in enumerate(review.segments) if segment.section == "assessment"]
        if positions != [len(review.segments) - 1]:
            errors.append("Add exactly one final segment with section='assessment'; it must evaluate the work.")
        return errors

    def validate_structure(self, review: ReviewScript, source_duration: float) -> dict:
        errors = self.structure_errors(review, source_duration)
        if errors:
            raise ValueError("Editorial structure invalid: " + " ".join(errors))
        return self.budget(source_duration)

    def timing_report(self, review: ReviewScript, source_duration: float,
                      narration_durations: list[float], edit_durations: list[float],
                      *, rendered_duration: float | None = None) -> dict:
        if len(narration_durations) != len(review.segments) or len(edit_durations) != len(review.segments):
            raise ValueError("Timing count must match review segments")
        timings = [*narration_durations, *edit_durations]
        if rendered_duration is not None:
            timings.append(rendered_duration)
        if any(not math.isfinite(t) or t <= 0 for t in timings):
            raise ValueError("All measured durations must be positive and finite")
        budget = self.budget(source_duration)
        total = sum(edit_durations) if rendered_duration is None else rendered_duration
        errors = self.structure_errors(review, source_duration)
        epsilon = 1e-6
        if total < budget["total_min"] - epsilon:
            errors.append(f"Review is too short: {total:.2f}s; need at least {budget['total_min']:.2f}s. "
                          "Expand the story narration using verified plot details; regenerate TTS.")
        if total > budget["total_max"] + epsilon:
            errors.append(f"Review is too long: {total:.2f}s; limit is {budget['total_max']:.2f}s. "
                          "Shorten the story narration; regenerate TTS.")
        assessment_voice = assessment_edit = None
        if review.segments[-1].section == "assessment":
            assessment_voice = narration_durations[-1]
            assessment_edit = (edit_durations[-1] if rendered_duration is None
                               else total - sum(edit_durations[:-1]))
            for label, duration in (("narration", assessment_voice), ("timeline", assessment_edit)):
                if not self.assessment_min_seconds - epsilon <= duration <= self.assessment_max_seconds + epsilon:
                    errors.append(f"Final assessment {label} is {duration:.2f}s; required "
                                  f"{self.assessment_min_seconds:g}-{self.assessment_max_seconds:g}s. "
                                  "Rewrite the assessment; do not add silence or slow down speech to meet the limit.")
        return {
            "passed": not errors, "errors": errors, "budget": budget,
            "review_duration": total, "source_ratio": total / source_duration,
            "assessment_narration_duration": assessment_voice,
            "assessment_timeline_duration": assessment_edit,
            "segments": [{"id": segment.id, "section": segment.section,
                          "narration_duration": voice, "edit_duration": edit}
                         for segment, voice, edit in zip(review.segments, narration_durations, edit_durations)],
        }


def require_timing(report: dict) -> None:
    if not report["passed"]:
        raise ValueError("Editorial timing failed: " + " ".join(report["errors"]))
