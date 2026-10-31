from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.audio.narration_builder import NarrationBuilder
from src.audio.speech import SpeechUnit, EMOTIONS
from src.pipeline.build_review import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview a Vietnamese speech unit with emotion and measured timing.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--emotion", choices=EMOTIONS)
    parser.add_argument("--voice", help="Voice ID/name for the provider selected by --config")
    parser.add_argument("--rate", type=int)
    parser.add_argument("--pitch", type=int)
    parser.add_argument("--volume", type=int)
    parser.add_argument("--pause", type=int, help="Pause after the unit, milliseconds")
    parser.add_argument("--config", default=str(ROOT / "config/config.yaml"))
    parser.add_argument("--output", default=str(ROOT / "output/audio/preview.wav"))
    parser.add_argument("--no-variation", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = load_config(args.config)
    if args.voice:
        config["tts"]["voice"] = args.voice
    if args.no_variation:
        config["tts"]["natural_variation"]["enabled"] = False
    values = {"text": args.text}
    for argument, field in (("emotion", "emotion"), ("rate", "rate_percent"), ("pitch", "pitch_hz"),
                            ("volume", "volume_percent"), ("pause", "pause_after_ms")):
        value = getattr(args, argument)
        if value is not None:
            values[field] = value
    try:
        result = NarrationBuilder(config["tts"], config["audio"]["narration"],
                                  cache_dir=ROOT / "output/cache/silence").build(
            [SpeechUnit.model_validate(values)], args.output)
    except Exception as error:
        parser.exit(1, f"Preview failed: {error}\n")
    print(f"PASS: {result.path} ({result.duration:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
