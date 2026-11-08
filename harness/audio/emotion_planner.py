"""Replaceable planner interface; conservative, local heuristics only."""
from __future__ import annotations

from abc import ABC, abstractmethod
import random
import re

from harness.audio.speech import SpeechUnit, VoiceConfig, LIMITS, clamp


class EmotionPlanner(ABC):
    @abstractmethod
    def plan(self, units: list[SpeechUnit], *, section: str = "story") -> list[SpeechUnit]:
        ...


class HeuristicEmotionPlanner(EmotionPlanner):
    def infer(self, text: str, section: str = "story") -> str:
        value = text.casefold().strip()
        if section == "assessment":
            return "serious"
        if re.match(r"^(nhưng không|và rồi|chưa hết|sai hoàn toàn|đó mới là vấn đề)[.!…]*$", value):
            return "punchline"
        if any(term in value for term in ("đánh giá", "nhận xét", "điểm yếu", "điểm mạnh", "đáng tiếc", "vấn đề")):
            return "serious"
        if value.count("!") >= 2 or re.search(r"\b(lao tới|tấn công|ngay lập tức|bật tung|nổ tung|bắn|đâm|bất ngờ xuất hiện)\b", value):
            return "excited"
        if any(term in value for term in ("bí mật", "kỳ lạ", "không ngờ", "đáng sợ", "chưa biết", "không hề biết", "biến mất")):
            return "suspense"
        if ("..." in value or "…" in value) or (value.startswith("nhưng ") and any(w in value for w in ("phía sau", "lúc này", "bất ngờ"))):
            return "suspense"
        if value.startswith(("cuối cùng", "sáng hôm sau", "chiều xuống", "nói cách khác")):
            return "calm"
        return "normal"

    def plan(self, units: list[SpeechUnit], *, section: str = "story") -> list[SpeechUnit]:
        result = []
        for index, unit in enumerate(units, 1):
            updates = {"id": unit.id or f"unit_{index:03d}"}
            if "emotion" not in unit.model_fields_set:
                updates["emotion"] = self.infer(unit.text, section)
            result.append(unit.model_copy(update=updates))
        return result


def resolve_units(units: list[SpeechUnit], config: VoiceConfig, *, seed_offset: int = 0) -> list[SpeechUnit]:
    """Explicit numeric overrides win over presets, jitter and speaking-rate adaptation."""
    rng = random.Random(config.natural_variation.seed + seed_offset)
    result = []
    variation = config.natural_variation
    jitters = {"rate_percent": variation.rate_jitter_percent,
               "pitch_hz": variation.pitch_jitter_hz,
               "pause_after_ms": variation.pause_jitter_ms}
    previous = None
    for unit in units:
        values = config.presets[unit.emotion].model_dump()
        for field in values:
            custom = getattr(unit, field)
            if custom is not None:
                values[field] = custom
            elif variation.enabled and field in jitters:
                values[field] += rng.randint(-jitters[field], jitters[field])
            values[field] = int(clamp(values[field], *LIMITS[field], field))
        signature = tuple(values[k] for k in jitters)
        if variation.enabled and previous == (unit.emotion, signature):
            # Avoid identical consecutive automatic deliveries, even after a random collision.
            for field, jitter in jitters.items():
                if jitter and getattr(unit, field) is None:
                    low, high = LIMITS[field]
                    base = getattr(config.presets[unit.emotion], field)
                    options = [n for n in range(max(low, base-jitter), min(high, base+jitter)+1) if n != values[field]]
                    if options:
                        values[field] = rng.choice(options)
                        break
        previous = (unit.emotion, tuple(values[k] for k in jitters))
        result.append(unit.model_copy(update=values))
    return result

