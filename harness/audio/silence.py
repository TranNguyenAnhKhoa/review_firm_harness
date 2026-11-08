"""48 kHz stereo PCM silence, reusable by duration and sample rate."""
from __future__ import annotations

from pathlib import Path
import wave
from harness.utils import ensure_parent, executable, run_command


def generate_silence(duration_ms: int, output_path: str | Path, sample_rate: int = 48000) -> Path:
    if duration_ms <= 0 or duration_ms > 4000 or sample_rate <= 0:
        raise ValueError("Silence requires 0 < duration_ms <= 4000 and positive sample_rate")
    output = ensure_parent(output_path)
    if output.exists():
        try:
            with wave.open(str(output), "rb") as wav:
                if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()) == (
                    sample_rate, 2, 2, round(duration_ms * sample_rate / 1000)):
                    return output
        except (wave.Error, EOFError):
            pass
    temporary = output.with_suffix(".partial.wav")
    run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-y",
                 "-f", "lavfi", "-i", f"anullsrc=r={sample_rate}:cl=stereo",
                 "-t", f"{duration_ms / 1000:.6f}", "-c:a", "pcm_s16le", str(temporary)])
    temporary.replace(output)
    return output


def boundary_pause(after_ms: int, before_ms: int, mode: str = "max") -> int:
    if mode not in ("max", "additive") or min(after_ms, before_ms) < 0:
        raise ValueError("Invalid pause boundary settings")
    return max(after_ms, before_ms) if mode == "max" else after_ms + before_ms
