from __future__ import annotations

import asyncio
import hashlib
import logging
import tempfile
import threading
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Provider boundary. The pipeline only uses this contract."""

    @abstractmethod
    def synthesize(self, text: str, output_path: str, voice: str | None = None, *,
                   rate_percent: int = 0, pitch_hz: int = 0, volume_percent: int = 0) -> str:
        raise NotImplementedError


class EdgeTTSProvider(TTSProvider):
    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"

    def __init__(self, *, rate: str = "+0%", pitch: str = "+0Hz", language: str = "vi-VN"):
        self.rate = rate
        self.pitch = pitch
        self.language = language
        self._detected_voice: str | None = None

    async def _save(self, text: str, output_path: Path, voice: str | None,
                    rate: int, pitch: int, volume: int) -> None:
        import edge_tts

        if voice is None:
            if self._detected_voice is None:
                for attempt in range(3):
                    try:
                        voices = await edge_tts.list_voices()
                        break
                    except Exception as error:
                        if attempt == 2:
                            raise RuntimeError("Edge-TTS requires network; unable to discover voices after 3 attempts. Check connection or set tts.voice.") from error
                        logging.getLogger(__name__).warning("Edge-TTS voice discovery retry %s/2: %s", attempt + 1, error)
                        await asyncio.sleep(attempt + 1)
                available = [v["ShortName"] for v in voices if v["Locale"] == self.language]
                if not available:
                    raise RuntimeError(f"No Edge-TTS voice for {self.language}")
                self._detected_voice = self.DEFAULT_VOICE if self.DEFAULT_VOICE in available else available[0]
            voice = self._detected_voice
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(text, voice, **edge_parameters(rate, pitch, volume))
                await communicate.save(str(output_path))
                return
            except Exception as error:
                if attempt == 2:
                    raise RuntimeError(f"Edge-TTS requires network; synthesis failed for voice {voice}: {error}") from error
                logging.getLogger(__name__).warning("Edge-TTS retry %s/2: %s", attempt + 1, error)
                await asyncio.sleep(attempt + 1)

    def synthesize(self, text: str, output_path: str, voice: str | None = None, *,
                   rate_percent: int | None = None, pitch_hz: int | None = None,
                   volume_percent: int = 0) -> str:
        if not text.strip():
            raise ValueError("TTS text cannot be empty")
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.stem + '.partial.mp3')
        rate = int(self.rate.rstrip("%")) if rate_percent is None else rate_percent
        pitch = int(self.pitch.removesuffix("Hz")) if pitch_hz is None else pitch_hz
        asyncio.run(self._save(text, temporary, voice, rate, pitch, volume_percent))
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError("Edge-TTS did not create an audio file")
        temporary.replace(target)
        return str(target)


class ZeroTTSProvider(TTSProvider):
    """Local ONNX synthesis; tempo/volume processing preserves the chosen voice."""

    DEFAULT_VOICE = "baotrang"
    _models: dict[tuple, object] = {}
    _model_lock = threading.RLock()

    def __init__(self, *, voice: str | None = None, settings: dict | None = None):
        from harness.audio.speech import ZeroTTSConfig
        self.voice = voice or self.DEFAULT_VOICE
        self.settings = ZeroTTSConfig.model_validate(settings or {})

    def _load_model(self):
        from harness.utils import project_path
        settings = self.settings
        cache = project_path(settings.cache_dir)
        candidate = project_path(settings.model)
        # A local folder is used as-is; anything else is a Hugging Face repo id fetched into cache_dir.
        model_id = str(candidate) if candidate.is_dir() else (settings.model if "/" in settings.model and not
                                                              settings.model.startswith(("models/", "/", ".")) else settings.repo)
        key = (model_id, settings.revision, str(cache), settings.local_files_only, settings.threads)
        with self._model_lock:
            if key not in self._models:
                try:
                    from zerotts import ZeroTTS
                except ImportError as error:
                    raise RuntimeError("ZeroTTS runtime is missing; run ./setup.sh.") from error
                try:
                    self._models[key] = ZeroTTS.from_pretrained(
                        model_id, revision=settings.revision, cache_dir=str(cache),
                        local_files_only=settings.local_files_only,
                        intra_op_num_threads=settings.threads,
                        codec_intra_op_num_threads=settings.threads)
                except Exception as error:
                    raise RuntimeError(
                        "ZeroTTS model could not be loaded. Run ./setup.sh "
                        f"to download the weights first. Details: {error}") from error
            return self._models[key]

    @staticmethod
    def _voice_id(voice: str) -> str:
        text = unicodedata.normalize("NFD", voice.strip().casefold())
        return "".join(c for c in text if not unicodedata.combining(c) and not c.isspace())

    def synthesize(self, text: str, output_path: str, voice: str | None = None, *,
                   rate_percent: int = 0, pitch_hz: int = 0, volume_percent: int = 0) -> str:
        from harness.audio.speech import SpeechUnit
        from harness.utils import executable, run_command
        safe = SpeechUnit(text=text, rate_percent=rate_percent, pitch_hz=pitch_hz,
                          volume_percent=volume_percent)
        if safe.pitch_hz:
            raise ValueError("ZeroTTS does not support pitch_hz; use a config/zerotts.*.yaml preset with pitch_hz: 0.")
        target = Path(output_path)
        if target.suffix.lower() not in (".mp3", ".wav"):
            raise ValueError("ZeroTTS output must be .wav or .mp3")
        selected = self._voice_id(voice or self.voice)
        target.parent.mkdir(parents=True, exist_ok=True)
        # A unique workspace prevents collisions and keeps an existing output intact on failure.
        with tempfile.TemporaryDirectory(prefix=".zerotts-", dir=target.parent) as folder:
            raw = Path(folder) / "raw.wav"
            encoded = Path(folder) / ("encoded" + target.suffix.lower())
            with self._model_lock:
                model = self._load_model()
                if selected not in model.list_voices():
                    raise ValueError(f"Unknown ZeroTTS voice {selected!r}; available: {', '.join(model.list_voices())}")
                import numpy as np
                from zerotts import normalize_vi_text
                from zerotts.chunking import chunk_text
                # Keep retries at another tempo on the same generated utterance/voice.
                seed = int.from_bytes(hashlib.sha256(
                    f"{self.settings.seed}:{selected}:{safe.text}".encode("utf-8")).digest()[:4], "big")
                state = np.random.get_state()
                try:
                    np.random.seed(seed)
                    chunks = chunk_text(normalize_vi_text(safe.text), max_chunk_sec=self.settings.max_chunk_seconds)
                    parts = [model.synthesize(chunk, voice=selected) for chunk in chunks]
                finally:
                    np.random.set_state(state)
                if not parts or any(p.size == 0 or not np.isfinite(p).all() for p in parts):
                    raise RuntimeError("ZeroTTS returned empty or invalid audio")
                audio = np.concatenate(parts, axis=-1)
                if not np.any(audio):
                    raise RuntimeError("ZeroTTS returned silent audio")
                model.save_audio(audio, str(raw))
            # atempo changes duration without changing pitch; no quota padding/slowdown is added.
            filters = f"atempo={1 + safe.rate_percent / 100:.6f},volume={1 + safe.volume_percent / 100:.6f}"
            codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if target.suffix.lower() == ".mp3" else ["-c:a", "pcm_s16le"]
            run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-y", "-i", str(raw),
                         "-af", filters, "-ar", "48000", "-ac", "2", *codec, str(encoded)])
            if not encoded.exists() or encoded.stat().st_size <= 44:
                raise RuntimeError("ZeroTTS did not create an audio file")
            encoded.replace(target)
        return str(target)


def edge_parameters(rate: int, pitch: int, volume: int) -> dict[str, str]:
    from harness.audio.speech import SpeechUnit
    safe = SpeechUnit(text="validation", rate_percent=rate, pitch_hz=pitch, volume_percent=volume)
    return {"rate": f"{safe.rate_percent:+d}%", "pitch": f"{safe.pitch_hz:+d}Hz",
            "volume": f"{safe.volume_percent:+d}%"}


def get_tts_provider(config: dict) -> TTSProvider:
    provider = config.get("provider", "zerotts").lower()
    if provider == "edge":
        return EdgeTTSProvider(
            rate=config.get("rate", "+0%"),
            pitch=config.get("pitch", "+0Hz"),
            language=config.get("language", "vi-VN"),
        )
    if provider == "zerotts":
        return ZeroTTSProvider(voice=config.get("voice"), settings=config.get("zerotts"))
    raise ValueError(f"Unknown TTS provider: {provider}")


create_tts_provider = get_tts_provider
