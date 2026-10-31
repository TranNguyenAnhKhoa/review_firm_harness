"""Punctuation-first Vietnamese segmentation; no LLM dependency."""
from __future__ import annotations

import re
from src.audio.speech import SpeechUnit


class NarrationSegmenter:
    def __init__(self, min_words: int = 8, max_words: int = 25):
        self.min_words, self.max_words = min_words, max_words

    def segment(self, text: str) -> list[SpeechUnit]:
        text = " ".join(text.split())
        if not text:
            raise ValueError("Narration must not be empty")
        # Split only when punctuation is followed by whitespace: decimals remain intact.
        sentences = re.split(r'(?<=[.!?…])\s+(?=[^”"’])', text)
        chunks: list[str] = []
        for sentence in sentences:
            if len(sentence.split()) <= self.max_words:
                chunks.append(sentence)
                continue
            clauses = re.split(r'(?<=[,;:])\s+', sentence)
            pending = ""
            for clause in clauses:
                candidate = f"{pending} {clause}".strip()
                if pending and len(pending.split()) >= self.min_words and len(candidate.split()) > self.max_words:
                    chunks.append(pending)
                    pending = clause
                else:
                    pending = candidate
            if pending:
                chunks.append(pending)
        # Short complete sentences/punchlines remain intact; no word-count hard slicing.
        return [SpeechUnit(id=f"unit_{i:03d}", text=chunk) for i, chunk in enumerate(chunks, 1)]

