"""Small shared helpers: tool discovery, subprocess calls, atomic JSON, hashing."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from harness import ROOT


class ExternalToolError(RuntimeError):
    """Raised when FFmpeg/FFprobe (or another external tool) returns a non-zero exit code."""


def project_path(path: str | Path) -> Path:
    """Resolve a configured path against the harness root, independent of the caller's cwd."""
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else ROOT / candidate


# Project-local tool folders, searched before PATH. setup.sh puts FFmpeg in .tools/conda/bin.
LOCAL_TOOL_DIRS = (".tools/conda/bin", ".tools/ffmpeg", ".tools/bin")


def executable(name: str, env_name: str | None = None) -> str:
    """Find an executable: explicit environment override, project-local tools, then PATH."""
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    for folder in LOCAL_TOOL_DIRS:
        candidate = ROOT / folder / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    hint = f" or set {env_name}" if env_name else ""
    raise FileNotFoundError(f"{name} not found. Run ./setup.sh (installs FFmpeg into .tools/){hint}.")


def ffmpeg() -> str:
    return executable("ffmpeg", "FFMPEG_BINARY")


def ffprobe() -> str:
    return executable("ffprobe", "FFPROBE_BINARY")


def run_command(command: Sequence[str | os.PathLike], *, capture_output: bool = True,
                timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run an external command without a shell and surface stderr on failure."""
    result = subprocess.run(
        [str(part) for part in command], check=False, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None, timeout=timeout,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise ExternalToolError(f"Command failed ({result.returncode}): {' '.join(map(str, command))}\n{detail[-4000:]}")
    return result


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, value: Any) -> Path:
    """Write JSON atomically (temp file + rename), so readers never see half a file."""
    target = ensure_parent(path)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(target)
    return target


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def sha256_file(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
