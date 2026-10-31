"""Exercise all three ZeroTTS voices through the real narration pipeline offline."""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio.narration_builder import NarrationBuilder
from src.audio.speech import SpeechUnit
from src.pipeline.build_review import load_config


def main() -> int:
    text = 'Cô gái vừa tỉnh lại trong bệnh viện, nhưng đã quên mất mình là ai. Câu chuyện bất ngờ bắt đầu từ đây.'
    output = ROOT / 'output/zerotts_smoke'
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for voice in ('maichi', 'baotrang', 'kimoanh'):
        print(f'Generating {voice} offline...', flush=True)
        config = load_config(ROOT / f'config/zerotts.{voice}.yaml')
        config['tts']['natural_variation']['enabled'] = False
        builder = NarrationBuilder(config['tts'], config['audio']['narration'],
                                   cache_dir=output / 'silence')
        result = builder.build(text, output / f'{voice}.wav')
        with wave.open(str(result.path), 'rb') as wav:
            assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (48000, 2, 2)
            assert len(wav.readframes(wav.getnframes())) > 0
        rows.append({'voice': voice, 'path': str(result.path), 'duration': result.duration,
                     'speech_only_syllables_per_second': result.metrics['speech_only_syllables_per_second'],
                     'model_revision': config['tts']['zerotts']['revision'], 'offline': True})
        print(f'PASS: {voice}: {result.duration:.3f}s', flush=True)
    (output / 'validation.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
