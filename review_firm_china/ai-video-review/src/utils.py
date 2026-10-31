from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class ExternalToolError(RuntimeError):
    """Raised when FFmpeg/FFprobe returns a non-zero exit code."""


def project_path(path: str | Path) -> Path:
    """Resolve project configuration paths independently of the caller's cwd."""
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else Path(__file__).resolve().parents[1] / candidate


def _ensure_local_paths() -> None:
    """Prepend project-local tool directories to PATH so subprocesses can locate them."""
    tool_dirs = [
        project_path(".tools/ffmpeg"),
        project_path(".venv/Scripts" if os.name == "nt" else ".venv/bin"),
    ]
    current_path = os.environ.get("PATH", "")
    for d in tool_dirs:
        if d.is_dir():
            d_str = str(d)
            if d_str not in current_path:
                current_path = f"{d_str}{os.pathsep}{current_path}"
    os.environ["PATH"] = current_path


_ensure_local_paths()


def executable(name: str, env_name: str) -> str:
    """Find a media executable, allowing an explicit environment override."""
    configured = os.environ.get(env_name)
    if configured:
        return configured

    # 1. Check project-local tool directories first (sandbox safe)
    if os.name == "nt":
        local_candidates = [
            project_path(f".tools/ffmpeg/{name}.exe"),
            project_path(f".venv/Scripts/{name}.exe"),
            project_path(f".tools/{name}.exe"),
            project_path(f"tools/{name}.exe"),
        ]
    else:
        local_candidates = [
            project_path(f".tools/ffmpeg/{name}"),
            project_path(f".venv/bin/{name}"),
            project_path(f".tools/{name}"),
            project_path(f"tools/{name}"),
        ]
    for candidate in local_candidates:
        if candidate.is_file():
            return str(candidate)

    # 2. Check system PATH
    found = shutil.which(name)
    if found:
        return found

    # 3. Check system/user tool installations if accessible
    if os.name == "nt":
        winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet"
        candidates = [winget / "Links" / f"{name}.exe"]
        try:
            candidates.extend(winget.glob(f"Packages/Gyan.FFmpeg*/*/bin/{name}.exe"))
        except (OSError, PermissionError):
            pass
        hermes_tools = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "tools"
        try:
            candidates.extend(sorted(hermes_tools.glob(f"ffmpeg-*/bin/{name}.exe"), reverse=True))
        except (OSError, PermissionError):
            pass
        for candidate in candidates:
            try:
                if candidate.is_file():
                    return str(candidate)
            except (OSError, PermissionError):
                continue

    raise FileNotFoundError(
        f"{name} was not found on PATH. Install FFmpeg or set {env_name}."
    )



def run_command(command: Sequence[str], *, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    """Run an external command without a shell and surface useful stderr."""
    result = subprocess.run(
        [str(part) for part in command],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise ExternalToolError(
            f"Command failed ({result.returncode}): {' '.join(map(str, command))}\n{detail}"
        )
    return result


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target
