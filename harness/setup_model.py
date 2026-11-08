"""Download the pinned ZeroTTS model + voice packs into a plain folder (called by setup.sh).

The files land as real files in tts.zerotts.model (default models/zerotts/ZeroTTS-c2bfbd67), not in a
symlinked Hugging Face cache: onnxruntime >= 1.31 rejects an ONNX model whose external .data file
resolves to another directory, which is exactly what the cache's blob symlinks do on Linux.
"""
from __future__ import annotations

import sys

from harness.config import load_config
from harness.utils import project_path


def main() -> int:
    settings = load_config()["tts"]["zerotts"]
    from huggingface_hub import snapshot_download
    from zerotts.hub import _ALLOW_PATTERNS
    from zerotts.voices import load_voice
    target = project_path(settings["model"])
    target.mkdir(parents=True, exist_ok=True)
    print(f"ZeroTTS {settings['repo']}@{settings['revision'][:12]} -> {target}", flush=True)
    snapshot_download(repo_id=settings["repo"], revision=settings["revision"], local_dir=str(target),
                      allow_patterns=_ALLOW_PATTERNS)
    links = [p for p in target.rglob("*") if p.is_symlink()]
    if links:
        raise SystemExit(f"{len(links)} symlinks in {target}; onnxruntime will refuse them. Remove the folder and retry.")
    from harness.config import VOICES
    for name in VOICES:
        voice = load_voice(target / "voices", name)
        print(f"  voice {name}: {voice.display_name} ({voice.gender})")
    print(f"Model: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
