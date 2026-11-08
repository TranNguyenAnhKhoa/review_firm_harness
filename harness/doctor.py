"""Environment check used by ./run.sh doctor, ./start.sh and the dashboard's System panel."""
from __future__ import annotations

import importlib
import shutil
import sys

from harness import ROOT
from harness.utils import project_path, run_command


def _ffmpeg() -> tuple[bool, str]:
    try:
        from harness.utils import ffmpeg, ffprobe
        binary, probe = ffmpeg(), ffprobe()
    except FileNotFoundError as error:
        return False, str(error)
    version = run_command([binary, "-hide_banner", "-version"]).stdout.splitlines()[0]
    config = run_command([binary, "-hide_banner", "-buildconf"]).stdout
    filters = run_command([binary, "-hide_banner", "-filters"]).stdout
    missing = [n for n in ("libx264", "libass", "libmp3lame") if f"enable-{n}" not in config]
    missing += [n for n in ("loudnorm", "atempo", "ass", "drawtext") if f" {n} " not in filters]
    if missing:
        return False, f"{binary}: thiếu {', '.join(missing)} ({version})"
    return True, f"{binary} ({version.split(' Copyright')[0]})"


def _model(config: dict) -> tuple[bool, str]:
    folder = project_path(config["tts"]["zerotts"]["model"])
    if not (folder / "config.json").is_file():
        return False, f"chưa có model ZeroTTS tại {folder} (./setup.sh)"
    links = sum(1 for p in folder.rglob("*") if p.is_symlink())
    if links:
        return False, f"{folder} chứa {links} symlink: onnxruntime sẽ từ chối, xoá thư mục rồi chạy ./setup.sh"
    return True, str(folder.relative_to(ROOT) if ROOT in folder.parents else folder)


def report() -> list[tuple[str, bool, str]]:
    from harness.config import load_config
    rows = [("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0] + " " + sys.executable)]
    for module, label in (("pydantic", "pydantic"), ("yaml", "PyYAML"), ("numpy", "numpy"), ("cv2", "opencv-python"),
                          ("scenedetect", "scenedetect"), ("zerotts", "zerotts"), ("onnxruntime", "onnxruntime")):
        try:
            mod = importlib.import_module(module)
            rows.append((label, True, getattr(mod, "__version__", "ok")))
        except Exception as error:
            rows.append((label, False, f"{error} (./setup.sh)"))
    rows.append(("FFmpeg", *_ffmpeg()))
    try:
        config = load_config()
        rows.append(("Model ZeroTTS", *_model(config)))
    except Exception as error:
        config = None
        rows.append(("config/default.yaml", False, str(error)))
    for engine in ("claude", "agy", "codex"):
        binary = shutil.which(engine)
        used = bool(config) and engine in (config["agents"]["read"]["engine"], config["agents"]["write"]["engine"])
        label = f"CLI {engine}" if used else f"(tuỳ chọn) CLI {engine}"
        rows.append((label, bool(binary), binary or "không có trên PATH"))
    free = shutil.disk_usage(ROOT).free / 1e9
    rows.append(("Ổ đĩa trống >= 20 GB", free >= 20, f"{free:.0f} GB tại {ROOT}"))
    return rows
