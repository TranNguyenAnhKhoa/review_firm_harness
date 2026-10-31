from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio.narration_builder import NarrationBuilder
from src.audio.speech import SpeechUnit
from src.pipeline.build_review import load_config

SAMPLES = [
    ("normal", "Anh ta bắt đầu tiến sâu hơn vào căn nhà."),
    ("suspense", "Nhưng ngay lúc này, một điều kỳ lạ xảy ra."),
    ("excited", "Cánh cửa phía sau bất ngờ bật tung!"),
    ("serious", "Vấn đề lớn nhất của bộ phim nằm ở cách xử lý nhân vật."),
    ("punchline", "Nhưng không."),
    ("calm", "Cuối cùng, mọi chuyện cũng dần trở lại bình thường."),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Six presets in order: normal, suspense, excited, serious, punchline, calm.")
    parser.add_argument("--config", default=str(ROOT / "config/config.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output/audio/emotion_demo.wav"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = load_config(args.config)
    # A/B demo isolates preset rate/pitch/volume: no jitter or automatic rate retries.
    config["tts"]["natural_variation"]["enabled"] = False
    config["tts"]["target_speech"]["enabled"] = False
    units = [SpeechUnit(text=text, emotion=emotion, **({"pause_before_ms": 1000} if i else {}))
             for i, (emotion, text) in enumerate(SAMPLES)]
    print("A/B demo: one second between presets (explicit demo pause override).")
    result = NarrationBuilder(config["tts"], config["audio"]["narration"],
                              cache_dir=ROOT / "output/cache/silence").build(units, args.output)
    print(f"PASS: {result.path} ({result.duration:.3f}s); unit timing: {result.path.with_suffix('.tts.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

