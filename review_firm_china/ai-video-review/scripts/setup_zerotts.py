"""Download ZeroTTS into the project, then check the requested voice packs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='c2bfbd67dc648cac455077333f7cf5c18a2e3bb4')
    args = parser.parse_args()
    from zerotts.hub import resolve_model_dir
    from zerotts.voices import load_voice

    print('Downloading ZeroTTS model and voice packs...', flush=True)
    model = resolve_model_dir('zeroweight-ai/ZeroTTS', revision=args.revision,
                              cache_dir=str(ROOT / 'data/models/zerotts'))
    voices = []
    for name in ('maichi', 'baotrang', 'kimoanh'):
        voice = load_voice(model / 'voices', name)
        voices.append({'id': name, 'name': voice.display_name, 'gender': voice.gender})
    result = {'model': str(model), 'revision': model.name, 'voices': voices}
    destination = ROOT / 'output/zerotts_smoke/model_manifest.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
