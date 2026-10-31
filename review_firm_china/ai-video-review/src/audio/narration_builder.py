"""Plan, synthesize, measure and assemble speech units on a sample-accurate timeline."""
from __future__ import annotations

import json
import logging
import wave
from dataclasses import dataclass
from pathlib import Path

from src.audio.emotion_planner import EmotionPlanner, HeuristicEmotionPlanner, resolve_units
from src.audio.mixer import extract_audio
from src.audio.narration_segmenter import NarrationSegmenter
from src.audio.normalizer import normalize_loudness
from src.audio.silence import boundary_pause, generate_silence
from src.audio.speech import SpeechUnit, VoiceConfig, LoudnessConfig, RateRange
from src.audio.speech_metrics import speech_metrics
from src.audio.tts import TTSProvider, create_tts_provider
from src.video.probe import probe_audio

log = logging.getLogger(__name__)
SAMPLE_RATE = 48000


@dataclass
class NarrationResult:
    path: Path
    duration: float
    speech_duration: float
    units: list[dict]
    metrics: dict


def _pcm_info(path: Path) -> tuple[int, float]:
    with wave.open(str(path), "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 2, 2):
            raise ValueError(f"Expected 48 kHz stereo PCM16: {path}")
        return wav.getnframes(), wav.getnframes() / SAMPLE_RATE


def concatenate_pcm(parts: list[Path], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        for path in parts:
            _pcm_info(path)
            with wave.open(str(path), "rb") as source:
                while chunk := source.readframes(65536):
                    output.writeframesraw(chunk)
    return output_path


class NarrationBuilder:
    def __init__(self, tts_config: dict, audio_config: dict | None = None, *,
                 cache_dir: str | Path = "output/cache/silence",
                 provider: TTSProvider | None = None, planner: EmotionPlanner | None = None):
        self.config = VoiceConfig.model_validate(tts_config)
        self.loudness = LoudnessConfig.model_validate(audio_config or {})
        self.provider = provider or create_tts_provider(self.config.model_dump())
        self.planner = planner or HeuristicEmotionPlanner()
        self.cache_dir = Path(cache_dir)
        if self.config.micro_pause.enabled:
            log.info("Micro-pauses: punctuation retained for native TTS prosody; exact intra-unit milliseconds are TODO.")

    def plan(self, narration: str | list[SpeechUnit], *, section: str = "story",
             segment_id: int = 1) -> tuple[list[SpeechUnit], list[SpeechUnit]]:
        raw = NarrationSegmenter().segment(narration) if isinstance(narration, str) else narration
        if not raw:
            raise ValueError("At least one speech unit is required")
        planned = self.planner.plan(raw, section=section)
        if len({u.id for u in planned}) != len(planned):
            raise ValueError("Speech unit IDs collide after assigning automatic IDs")
        return planned, resolve_units(planned, self.config, seed_offset=segment_id)

    def _unit_audio(self, unit: SpeechUnit, original: SpeechUnit, folder: Path, index: int) -> tuple[Path, dict]:
        target = self.config.target_speech
        allowed = self.config.speech_rate_ranges.get(unit.emotion, RateRange(
            min=target.min_syllables_per_second, max=target.max_syllables_per_second))
        # Emotion bounds win over the global target.
        desired = max(allowed.min, min(allowed.max, target.target_syllables_per_second))
        initial_rate = int(unit.rate_percent)
        rate = initial_rate
        attempts = []
        explicit_rate = original.rate_percent is not None
        for attempt in range(target.retry_limit + 1):
            mp3 = folder / f"unit_{index:03d}_attempt_{attempt + 1}.mp3"
            try:
                self.provider.synthesize(unit.text, str(mp3), voice=self.config.voice,
                                         rate_percent=rate, pitch_hz=int(unit.pitch_hz),
                                         volume_percent=int(unit.volume_percent))
                wav = extract_audio(str(mp3), str(mp3.with_suffix(".wav")))
                _, duration = _pcm_info(wav)
                metrics = speech_metrics(unit.text, duration)
            except Exception as error:
                raise RuntimeError(f"Speech unit {unit.id} ({unit.emotion}) failed: {error}") from error
            speed = metrics["syllables_per_second"]
            accepted = allowed.min <= speed <= allowed.max
            attempts.append({"attempt": attempt + 1, "rate_percent": rate, "metrics": metrics,
                             "within_range": accepted, "path": str(wav)})
            if not target.enabled or accepted or explicit_rate or attempt == target.retry_limit:
                break
            delta = round((100 + rate) * (desired / speed - 1))
            if delta == 0:
                delta = 1 if speed < allowed.min else -1
            limit = target.max_rate_adjustment_percent
            adjusted = max(-20, min(30, max(initial_rate-limit, min(initial_rate+limit, rate+delta))))
            if adjusted == rate:
                break
            log.info("  %s speaking rate %.2f outside %.2f-%.2f; retry rate %+d%% -> %+d%%",
                     unit.id, speed, allowed.min, allowed.max, rate, adjusted)
            rate = adjusted
        if target.enabled and not accepted:
            log.warning("  %s speech rate %.2f outside %.2f-%.2f; retained after %d attempt(s)%s",
                        unit.id, speed, allowed.min, allowed.max, len(attempts),
                        " (explicit rate respected)" if explicit_rate else "")
        return wav, {**unit.model_dump(), "rate_percent": rate, "duration": duration,
                     "metrics": metrics, "attempts": attempts, "speech_rate_accepted": accepted,
                     "rate_range": allowed.model_dump()}

    def build(self, narration: str | list[SpeechUnit], output_path: str | Path, *,
              segment_id: int = 1, section: str = "story",
              debug_path: str | Path | None = None) -> NarrationResult:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        folder = output.parent / output.stem
        folder.mkdir(parents=True, exist_ok=True)
        originals, units = self.plan(narration, section=section, segment_id=segment_id)
        log.info("[TTS] Segment %02d - Units: %d", segment_id, len(units))
        audio_parts, records = [], []
        for index, (unit, original) in enumerate(zip(units, originals), 1):
            try:
                path, record = self._unit_audio(unit, original, folder, index)
            except Exception as error:
                raise RuntimeError(f"TTS segment {segment_id}, unit {index}: {error}") from error
            audio_parts.append(path)
            records.append(record)
            log.info("  Unit %d: %s | rate %+d%% | pitch %+dHz | volume %+d%% | after %dms | %.3fs",
                     index, unit.emotion, record["rate_percent"], unit.pitch_hz,
                     unit.volume_percent, unit.pause_after_ms, record["duration"])

        assembled: list[Path] = []
        cursor_frames = 0
        boundaries = []

        def append_pause(milliseconds: int) -> None:
            nonlocal cursor_frames
            if milliseconds:
                path = generate_silence(milliseconds, self.cache_dir / f"48000_{milliseconds}ms.wav")
                frames, _ = _pcm_info(path)
                assembled.append(path)
                cursor_frames += frames

        for index, (unit, audio_path, record) in enumerate(zip(units, audio_parts, records)):
            gap = int(unit.pause_before_ms) if index == 0 else boundary_pause(
                int(units[index-1].pause_after_ms), int(unit.pause_before_ms), self.config.pause_boundary)
            before = cursor_frames / SAMPLE_RATE
            append_pause(gap)
            boundaries.append({"before_unit": unit.id, "duration_ms": gap, "start": before,
                               "end": cursor_frames / SAMPLE_RATE})
            record["start"] = cursor_frames / SAMPLE_RATE
            frames, _ = _pcm_info(audio_path)
            assembled.append(audio_path)
            cursor_frames += frames
            record["end"] = cursor_frames / SAMPLE_RATE
        final_pause = int(units[-1].pause_after_ms)
        append_pause(final_pause)
        raw_path = concatenate_pcm(assembled, folder / "assembled.wav")
        normalization = normalize_loudness(raw_path, output, self.loudness)
        duration = probe_audio(output)
        if abs(duration - cursor_frames / SAMPLE_RATE) > 1 / SAMPLE_RATE + 1e-6:
            raise RuntimeError("Assembled narration duration differs from speech unit timeline")
        speech_duration = sum(record["duration"] for record in records)
        text = " ".join(unit.text for unit in units)
        metrics = {**speech_metrics(text, duration), "speech_duration": speech_duration,
                   "inserted_pause_duration": duration - speech_duration,
                   "speech_only_syllables_per_second": speech_metrics(text, speech_duration)["syllables_per_second"]}
        debug = {"segment_id": segment_id, "section": section, "duration": duration,
                 "speech_duration": speech_duration, "units": records, "boundaries": boundaries,
                 "final_pause_ms": final_pause, "metrics": metrics, "normalization": normalization,
                 "seed": self.config.natural_variation.seed, "output": str(output)}
        destination = Path(debug_path) if debug_path else output.with_suffix(".tts.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Segment duration: %.3fs | Speech: %.3fs | Rate: %.2f syllables/s (pauses included)",
                 duration, speech_duration, metrics["syllables_per_second"])
        return NarrationResult(output, duration, speech_duration, records, metrics)
