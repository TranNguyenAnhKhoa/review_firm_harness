from __future__ import annotations

import sys
import warnings
from pathlib import Path

from src.utils import run_command


def demucs_device() -> str:
    """Prefer CUDA only when PyTorch says it is usable; otherwise safely use CPU."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except (ImportError, OSError, RuntimeError):
        return "cpu"


def separate_audio(input_audio: str, output_dir: str) -> dict[str, str]:
    """Create vocals/no_vocals stems with Demucs' two-stem mode."""
    source = Path(input_audio)
    if not source.exists():
        raise FileNotFoundError(source)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    device = demucs_device()
    command = [sys.executable, "-m", "demucs.separate", "--two-stems", "vocals",
               "-n", "htdemucs", "--device", device, "-o", str(destination), str(source)]
    try:
        run_command(command)
    except RuntimeError:
        if device != "cuda":
            raise
        warnings.warn("Demucs CUDA execution failed; retrying on CPU.")
        device = "cpu"
        command[command.index("--device") + 1] = device
        run_command(command)
    stem_dir = destination / "htdemucs" / source.stem
    vocals = stem_dir / "vocals.wav"
    no_vocals = stem_dir / "no_vocals.wav"
    if not vocals.exists() or not no_vocals.exists():
        raise RuntimeError(f"Demucs output was incomplete: {stem_dir}")
    return {"vocals": str(vocals), "no_vocals": str(no_vocals), "device": device}
