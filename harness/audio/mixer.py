from __future__ import annotations

from pathlib import Path

from harness.utils import ensure_parent, executable, run_command


def extract_audio(video_path: str, audio_path: str) -> Path:
    """Extract 48 kHz stereo PCM WAV via FFmpeg."""
    output = ensure_parent(audio_path)
    run_command(
        [
            executable("ffmpeg", "FFMPEG_BINARY"), "-y", "-i", video_path, "-vn",
            "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output),
        ]
    )
    return output


def build_mix_filter(background_label: str, narration_count: int, background_volume: float, narration_volume: float) -> tuple[str, str]:
    """Return an FFmpeg filter graph and final audio label for delayed voice-over mixing."""
    filters = [f"[{background_label}]volume={background_volume},afade=t=in:d=0.04[bg]"]
    mix_inputs = ["[bg]"]
    for index in range(narration_count):
        filters.append(f"[n{index}]volume={narration_volume}[voice{index}]")
        mix_inputs.append(f"[voice{index}]")
    filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[mix]")
    return ";".join(filters), "[mix]"
