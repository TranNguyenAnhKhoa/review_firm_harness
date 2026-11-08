"""Review harness: turn a source film into a measured, narrated Vietnamese review video.

Stages (see harness.pipeline.stages): probe, read, write, measure, render, qc.
READ and WRITE run through an agent CLI (claude, agy, codex) or by hand, each followed by a
human approval gate; the other stages are local Python + FFmpeg + ZeroTTS.
"""
from pathlib import Path

__version__ = "2.0.0"
ROOT = Path(__file__).resolve().parents[1]
