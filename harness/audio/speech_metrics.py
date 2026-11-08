"""Whitespace-token approximation, not a linguistic Vietnamese syllable parser."""
from __future__ import annotations
import math


def speech_metrics(text: str, duration: float) -> dict:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Audio duration must be finite and positive")
    words = text.split()
    tokens = sum(any(c.isalnum() for c in word) for word in words)
    return {"character_count": len(text), "word_count": len(words),
            "syllable_approximation": tokens, "tokens": tokens, "duration": duration,
            "syllables_per_second": tokens / duration}

