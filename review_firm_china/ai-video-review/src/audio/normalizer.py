"""Two-pass FFmpeg loudnorm on the assembled segment, not individual units."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from src.audio.speech import LoudnessConfig
from src.utils import ensure_parent, executable, run_command
from src.video.probe import probe_audio


def normalize_loudness(source: str | Path, output_path: str | Path,
                       settings: LoudnessConfig) -> dict:
    ffmpeg = executable("ffmpeg", "FFMPEG_BINARY")
    duration = probe_audio(source)
    base = f"loudnorm=I={settings.loudness_lufs}:TP={settings.true_peak_db}:LRA=11"
    first = run_command([ffmpeg, "-hide_banner", "-i", str(source), "-af",
                         base + ":print_format=json", "-f", "null", "-"])
    match = re.search(r'\{\s*"input_i".*?\}', first.stderr, re.S)
    if not match:
        raise RuntimeError("FFmpeg loudnorm did not return measurement data")
    measured = json.loads(match.group())
    keys = {"input_i": "measured_I", "input_tp": "measured_TP",
            "input_lra": "measured_LRA", "input_thresh": "measured_thresh",
            "target_offset": "offset"}
    if any(not math.isfinite(float(measured[key])) for key in keys):
        raise RuntimeError("Narration has no measurable loudness; refusing silent audio fallback")
    measured_options = ":".join(f"{option}={measured[key]}" for key, option in keys.items())
    # Preserve the PCM timeline exactly despite loudnorm's internal resampling.
    filters = base + ":" + measured_options + ":linear=true"
    frames = round(duration * 48000)
    # Dynamic loudnorm can return an offset PTS on long speech. Reset it before
    # trimming and preserve the original PCM sample count, not offset timestamps.
    filters += f",aresample=48000,asetpts=PTS-STARTPTS,apad=whole_len={frames},atrim=end_sample={frames}"
    output = ensure_parent(output_path)
    temporary = output.with_suffix(".partial.wav")
    run_command([ffmpeg, "-v", "error", "-y", "-i", str(source), "-af", filters,
                 "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(temporary)])
    actual = probe_audio(temporary)
    if abs(actual - duration) > 1 / 48000 + 1e-6:
        raise RuntimeError(f"Loudnorm changed narration timeline: {duration} -> {actual}")
    temporary.replace(output)
    return {"target": settings.model_dump(), "input_measurement": measured,
            "duration": actual}
