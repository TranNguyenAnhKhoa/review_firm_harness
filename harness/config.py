"""Configuration: config/default.yaml, then an optional per-job config.yaml merged on top."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from harness import ROOT

DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
# ZeroTTS voice packs in the pinned model (id: name, gender). Bảo Trang is the reference voice of the 1004 flow.
VOICE_NAMES = {"baotrang": "Bảo Trang (nữ)", "maichi": "Mai Chi (nữ)", "kimoanh": "Kim Oanh (nữ)", "hamy": "Hà My (nữ)",
               "giahuy": "Gia Huy (nam)", "huuduc": "Hữu Đức (nam)", "quangminh": "Quang Minh (nam)",
               "tiendat": "Tiến Đạt (nam)"}
VOICES = tuple(VOICE_NAMES)
READ_ENGINES = ("claude", "agy", "codex", "manual")
WRITE_ENGINES = ("claude", "agy", "codex", "manual")


def merge(base: dict, override: dict) -> dict:
    """Recursive dict merge; override wins, nested dicts are merged, lists are replaced."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def read_yaml(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def load_config(*overlays: str | Path | dict | None) -> dict:
    """Default config merged with each overlay (a YAML path or a dict), in order."""
    config = read_yaml(DEFAULT_CONFIG)
    for overlay in overlays:
        if overlay is None:
            continue
        config = merge(config, overlay if isinstance(overlay, dict) else read_yaml(overlay))
    validate(config)
    return config


def validate(config: dict) -> None:
    """Fail early on settings the dashboard or a hand edit can get wrong."""
    from harness.audio.speech import VoiceConfig, LoudnessConfig
    from harness.editorial import EditorialPolicy
    from harness.video.picture_style import PictureStyle
    VoiceConfig.model_validate(config["tts"])
    LoudnessConfig.model_validate(config["audio"]["narration"])
    EditorialPolicy.model_validate(config["editorial"])
    PictureStyle.model_validate(config["render"]["picture_style"])
    agents = config.get("agents", {})
    for stage, engines in (("read", READ_ENGINES), ("write", WRITE_ENGINES)):
        engine = agents.get(stage, {}).get("engine")
        if engine not in engines:
            raise ValueError(f"agents.{stage}.engine must be one of {', '.join(engines)} (got {engine!r})")
    gates = config.get("gates", [])
    if not isinstance(gates, list) or any(g not in ("read", "write") for g in gates):
        raise ValueError("gates: a list containing read and/or write")
