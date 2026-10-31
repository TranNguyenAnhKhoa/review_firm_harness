"""Test media format, timing, and error handling without downloading a TTS model."""
from __future__ import annotations

import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.audio.tts import ZeroTTSProvider, create_tts_provider
from src.pipeline.build_review import load_config
from src.utils import executable, run_command
from src.video.probe import probe_audio


class TestModel:
    def list_voices(self):
        return ['maichi', 'baotrang', 'kimoanh']

    def synthesize(self, text, voice):
        return (.2 * np.sin(2 * np.pi * 220 * np.arange(48000) / 48000)).astype(np.float32)[None, :]

    def save_audio(self, audio, path):
        with wave.open(path, 'wb') as wav:
            wav.setnchannels(1)
            wav.setframerate(48000)
            wav.setsampwidth(2)
            wav.writeframes((audio.reshape(-1) * 32767).astype('<i2').tobytes())


class ZeroTTSTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.model = TestModel()
        self.load = patch.object(ZeroTTSProvider, '_load_model', return_value=self.model)
        self.load.start()
        module = types.ModuleType('zerotts')
        module.normalize_vi_text = lambda text: text
        chunking = types.ModuleType('zerotts.chunking')
        chunking.chunk_text = lambda text, max_chunk_sec: [text]
        self.modules = patch.dict('sys.modules', {'zerotts': module, 'zerotts.chunking': chunking})
        self.modules.start()

    def tearDown(self):
        self.modules.stop()
        self.load.stop()
        self.temp.cleanup()

    def test_wav_and_mp3_are_real_formats_with_measured_tempo(self):
        provider = ZeroTTSProvider()
        slow = self.folder / 'normal.wav'
        fast = self.folder / 'fast.mp3'
        provider.synthesize('Xin chào.', str(slow))
        provider.synthesize('Xin chào.', str(fast), rate_percent=20)
        with wave.open(str(slow), 'rb') as wav:
            self.assertEqual((wav.getframerate(), wav.getnchannels(), wav.getsampwidth()), (48000, 2, 2))
            self.assertGreater(wav.getnframes(), 45000)
        # Compressed output must decode successfully, rather than WAV data renamed .mp3.
        decoded = self.folder / 'decoded.wav'
        run_command([executable('ffmpeg', 'FFMPEG_BINARY'), '-v', 'error', '-y', '-i', str(fast),
                     '-c:a', 'pcm_s16le', str(decoded)])
        self.assertAlmostEqual(probe_audio(decoded), probe_audio(slow) / 1.2, delta=.06)

    def test_unknown_voice_and_generation_failure_preserve_existing_file(self):
        path = self.folder / 'existing.wav'
        path.write_bytes(b'existing output')
        with self.assertRaisesRegex(ValueError, 'Unknown ZeroTTS voice'):
            ZeroTTSProvider().synthesize('Xin chào.', str(path), voice='vi-VN-HoaiMyNeural')
        self.assertEqual(path.read_bytes(), b'existing output')
        with patch.object(self.model, 'synthesize', side_effect=RuntimeError('model failed')):
            with self.assertRaisesRegex(RuntimeError, 'model failed'):
                ZeroTTSProvider().synthesize('Xin chào.', str(path))
        self.assertEqual(path.read_bytes(), b'existing output')
        self.assertFalse(list(self.folder.glob('.zerotts-*')))

    def test_silent_empty_or_nonfinite_audio_is_not_accepted(self):
        for audio in (np.zeros((1, 48000)), np.zeros((1, 0)), np.array([[np.nan]])):
            with self.subTest(shape=audio.shape), patch.object(self.model, 'synthesize', return_value=audio):
                path = self.folder / 'bad.wav'
                with self.assertRaises(RuntimeError):
                    ZeroTTSProvider().synthesize('Xin chào.', str(path))
                self.assertFalse(path.exists())

    def test_named_voices_resolve_and_select_correct_pack(self):
        for name, voice in [('Mai Chi', 'maichi'), ('Bảo Trang', 'baotrang'), ('Kim Oanh', 'kimoanh')]:
            with self.subTest(voice=voice), patch.object(self.model, 'synthesize', wraps=self.model.synthesize) as call:
                provider = create_tts_provider({'provider': 'zerotts', 'voice': name})
                provider.synthesize('Xin chào.', str(self.folder / f'{voice}.wav'))
                self.assertEqual(call.call_args.kwargs['voice'], voice)

    def test_each_config_is_usable_for_all_emotions_without_pitch_override(self):
        from src.audio.emotion_planner import resolve_units
        from src.audio.speech import EMOTIONS, SpeechUnit, VoiceConfig
        for voice in ('maichi', 'baotrang', 'kimoanh'):
            config = VoiceConfig.model_validate(load_config(f'config/zerotts.{voice}.yaml')['tts'])
            units = resolve_units([SpeechUnit(text='Đây là câu thử.', emotion=e) for e in EMOTIONS], config)
            self.assertEqual(config.voice, voice)
            self.assertTrue(config.zerotts.local_files_only)
            self.assertTrue(all(u.pitch_hz == 0 for u in units))

    def test_default_flow_and_inherited_movie_configs_use_baotrang(self):
        for path in ('config/config.yaml', 'config/review.movie.yaml', 'config/moana.v3.yaml',
                     'config/moana.render.yaml', 'examples/config.example.yaml'):
            with self.subTest(config=path):
                config = load_config(path)['tts']
                self.assertEqual((config['provider'], config['voice']), ('zerotts', 'baotrang'))
                self.assertTrue(config['zerotts']['local_files_only'])
                provider = create_tts_provider(config)
                with patch.object(self.model, 'synthesize', wraps=self.model.synthesize) as call:
                    provider.synthesize('Xin chào.', str(self.folder / 'default.wav'))
                    self.assertEqual(call.call_args.kwargs['voice'], 'baotrang')
        implicit = create_tts_provider({})
        self.assertIsInstance(implicit, ZeroTTSProvider)
        self.assertEqual(implicit.voice, 'baotrang')


if __name__ == '__main__':
    unittest.main()
