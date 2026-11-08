"""Deterministic local tests; real FFmpeg with synthetic audio, no network."""
from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock
from pydantic import ValidationError

from harness.audio.speech import SpeechUnit, VoiceConfig
from harness.audio.emotion_planner import HeuristicEmotionPlanner, resolve_units
from harness.audio.narration_segmenter import NarrationSegmenter
from harness.audio.narration_builder import NarrationBuilder
from harness.audio.silence import boundary_pause, generate_silence
from harness.audio.speech_metrics import speech_metrics
from harness.audio.tts import TTSProvider, edge_parameters, create_tts_provider
from harness.config import load_config, merge
from harness.schema import ReviewScript
from harness.subtitle import generate_ass
from harness.video.clipper import match_duration, cut_clip
from harness.video.probe import probe_video, probe_audio
from harness.utils import executable, run_command


def voice_config():
    config = load_config()["tts"]
    config["natural_variation"]["enabled"] = False
    config["target_speech"]["enabled"] = False
    return config


class VoiceTests(unittest.TestCase):
    def test_preset_override_and_safe_clamp(self):
        config = VoiceConfig.model_validate(voice_config())
        unit = SpeechUnit(text="Ví dụ", emotion="suspense", rate_percent=6)
        result = resolve_units([unit], config)[0]
        self.assertEqual((result.rate_percent, result.pitch_hz, result.pause_after_ms), (6, 0, 160))
        with self.assertLogs("harness.audio.speech", level="WARNING"):
            unsafe = SpeechUnit(text="Test", rate_percent=99, pitch_hz=-40, volume_percent=20, pause_after_ms=4000)
        self.assertEqual((unsafe.rate_percent, unsafe.pitch_hz, unsafe.volume_percent, unsafe.pause_after_ms),
                         (30, -25, 10, 2000))

    def test_segmentation_preserves_text_decimal_and_short_punchline(self):
        text = "Anh ta bước vào căn phòng. Mọi thứ đã biến mất. Nhưng không."
        units = NarrationSegmenter().segment(text)
        self.assertEqual(len(units), 3)
        self.assertEqual(" ".join(u.text for u in units), text)
        self.assertEqual(len(NarrationSegmenter().segment("Giá là 1.5 đồng.")), 1)
        self.assertEqual(len(NarrationSegmenter().segment("Mọi thứ... đã biến mất.")), 2)
        text = " ".join(["Câu dài có giải thích,"] * 8)
        result = NarrationSegmenter().segment(text)
        self.assertEqual(" ".join(u.text for u in result), text)
        self.assertGreater(len(result), 1)
        self.assertTrue(all(len(u.text.split()) >= 8 for u in result[:-1]))

    def test_emotion_heuristic_and_explicit_normal(self):
        planner = HeuristicEmotionPlanner()
        inputs = ["Anh ta bước vào căn phòng.", "Mọi thứ đã biến mất.", "Nhưng không.",
                  "Cánh cửa bất ngờ bật tung!", "Điểm yếu của phim là gì?", "Cuối cùng, mọi chuyện bình thường."]
        expected = ["normal", "suspense", "punchline", "excited", "serious", "calm"]
        self.assertEqual([u.emotion for u in planner.plan([SpeechUnit(text=t) for t in inputs])], expected)
        self.assertEqual(planner.plan([SpeechUnit(text=inputs[1], emotion="normal")])[0].emotion, "normal")
        self.assertEqual(planner.infer("Chúng ta chạy thử phần đánh số."), "normal")
        self.assertEqual(planner.plan([SpeechUnit(text="Bộ phim kể chuyện gia đình.")], section="assessment")[0].emotion, "serious")

    def test_variation_deterministic_nonidentical_and_overrides(self):
        config = VoiceConfig.model_validate(voice_config())
        config.natural_variation.enabled = True
        units = [SpeechUnit(text="Đây là một câu kể bình thường.", emotion="normal") for _ in range(10)]
        first = resolve_units(units, config)
        second = resolve_units(units, config)
        self.assertEqual(first, second)
        signatures = [(u.rate_percent, u.pitch_hz, u.pause_after_ms) for u in first]
        self.assertTrue(all(a != b for a, b in zip(signatures, signatures[1:])))
        explicit = SpeechUnit(text="Custom", rate_percent=6, pitch_hz=-12, pause_after_ms=555)
        result = resolve_units([explicit], config)[0]
        self.assertEqual((result.rate_percent, result.pitch_hz, result.pause_after_ms), (6, -12, 555))

    def test_edge_numeric_format_and_unsupported_zero_pitch(self):
        self.assertEqual(edge_parameters(12, -3, 2), {"rate": "+12%", "pitch": "-3Hz", "volume": "+2%"})
        with self.assertRaisesRegex(ValueError, "pitch_hz"):
            create_tts_provider({"provider": "zerotts"}).synthesize("Test", "unused.mp3", pitch_hz=5)

    def test_speech_metrics(self):
        result = speech_metrics("Đây là một câu tiếng Việt.", 2)
        self.assertEqual(result["tokens"], 6)
        self.assertEqual(result["syllables_per_second"], 3)
        with self.assertRaises(ValueError):
            speech_metrics("Test", 0)

    def test_backward_compatible_schema(self):
        base = {"title": "Test", "segments": [{"id": 1, "source_start": 0, "source_end": 5, "narration": "Câu cũ."}]}
        self.assertEqual(ReviewScript.model_validate(base).segments[0].narration_text, "Câu cũ.")
        base["segments"][0]["narration"] = [{"text": "Câu mới.", "emotion": "suspense"}]
        self.assertEqual(ReviewScript.model_validate(base).segments[0].narration_text, "Câu mới.")
        for invalid in ([], "", "  ", [{"text": ""}], [{"text": "Test", "emotion": "unknown"}]):
            base["segments"][0]["narration"] = invalid
            with self.assertRaises(ValidationError):
                ReviewScript.model_validate(base)

    def test_pause_boundary_and_safe_speed(self):
        self.assertEqual(boundary_pause(500, 100), 500)
        self.assertEqual(boundary_pause(500, 100, "additive"), 600)
        plan = match_duration(10, 15.2, 5.6, {"enabled": True})
        self.assertAlmostEqual(plan["speed"], 5.2 / 5.6)
        self.assertEqual(plan["freeze_duration"], 0)
        self.assertAlmostEqual(plan["start"] + plan["source_duration"], 15.2)
        with self.assertRaisesRegex(ValueError, "source_end"):
            match_duration(0, 3, 7, {"enabled": True, "fallback": "error"})

    def test_partial_nested_config_preserves_other_presets(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.yaml"
            path.write_text("tts:\n  presets:\n    normal:\n      rate_percent: 14\n", encoding="utf-8")
            config = load_config(path)
            self.assertEqual(merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3}}), {"a": {"b": 3, "c": 2}})
            self.assertEqual(config["tts"]["presets"]["normal"]["rate_percent"], 14)
            self.assertEqual(config["tts"]["presets"]["normal"]["pitch_hz"], 0)
            self.assertEqual(len(config["tts"]["presets"]), 6)


class SyntheticProvider(TTSProvider):
    def __init__(self):
        self.calls = []

    def synthesize(self, text, output_path, voice=None, *, rate_percent=0, pitch_hz=0, volume_percent=0):
        self.calls.append({"rate": rate_percent, "pitch": pitch_hz, "volume": volume_percent})
        duration = 2 / (1 + rate_percent / 100)
        run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-y",
                     "-f", "lavfi", "-i", f"sine=frequency=700:sample_rate=48000:duration={duration}",
                     "-ac", "2", "-c:a", "libmp3lame", output_path])
        return output_path


class VoiceMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def builder(self, config=None, provider=None):
        return NarrationBuilder(config or voice_config(), cache_dir=self.folder / "cache",
                                provider=provider or SyntheticProvider())

    def test_assembly_normalization_subtitle_gaps_and_clip_duration(self):
        units = [SpeechUnit(text="Đây là câu thứ nhất.", emotion="suspense", pause_before_ms=100, pause_after_ms=500),
                 SpeechUnit(text="Đây là câu thứ hai.", emotion="normal", pause_before_ms=100, pause_after_ms=220)]
        result = self.builder().build(units, self.folder / "narration.wav")
        self.assertAlmostEqual(result.units[0]["start"], .1, places=6)
        self.assertAlmostEqual(result.units[1]["start"] - result.units[0]["end"], .5, places=6)
        self.assertAlmostEqual(result.duration - result.speech_duration, .82, places=5)
        self.assertAlmostEqual(probe_audio(result.path), result.duration, places=5)
        with wave.open(str(result.path), "rb") as audio:
            audio.setpos(round((result.units[0]["end"] + .15) * 48000))
            self.assertEqual(audio.readframes(4800), bytes(4800 * 4))
        ass = self.folder / "review.ass"
        generate_ass([{"narration": u["text"], "start": u["start"], "duration": u["end"]-u["start"]}
                      for u in result.units], str(ass), max_chars_per_line=100)
        events = [line.split(",") for line in ass.read_text(encoding="utf-8-sig").splitlines() if line.startswith("Dialogue")]
        def seconds(value):
            h, m, s = map(float, value.split(":"))
            return h*3600+m*60+s
        self.assertAlmostEqual(seconds(events[0][2]), result.units[0]["end"], delta=.006)
        self.assertGreater(seconds(events[1][1]) - seconds(events[0][2]), .48)
        source = self.folder / "source.mp4"
        run_command([executable("ffmpeg", "FFMPEG_BINARY"), "-v", "error", "-y",
                     "-f", "lavfi", "-i", "color=blue:s=128x72:r=30:d=10",
                     "-c:v", "libx264", str(source)])
        output = self.folder / "clip.mp4"
        cut_clip(str(source), 0, 10, result.duration, str(output), preset="ultrafast")
        self.assertAlmostEqual(probe_video(output)["duration"], result.duration, delta=.04)
        debug = json.loads(result.path.with_suffix(".tts.json").read_text(encoding="utf-8"))
        self.assertIn("normalization", debug)

    def test_silence_cache(self):
        path = generate_silence(220, self.folder / "cache.wav")
        modified = path.stat().st_mtime_ns
        generate_silence(220, path)
        self.assertEqual(path.stat().st_mtime_ns, modified)
        self.assertAlmostEqual(probe_audio(path), .22, places=6)

    def test_actual_safe_slowdown_preserves_source_range(self):
        ffmpeg = executable("ffmpeg", "FFMPEG_BINARY")
        source = self.folder / "speed_source.mp4"
        run_command([ffmpeg, "-v", "error", "-y",
                     "-f", "lavfi", "-i", "color=red:s=128x72:r=30:d=0.8",
                     "-f", "lavfi", "-i", "color=blue:s=128x72:r=30:d=1.2",
                     "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                     "-map", "[v]", "-c:v", "libx264", str(source)])
        output = self.folder / "slower.mp4"
        duration = 26 / 30
        cut_clip(str(source), 0, .8, duration, str(output), preset="ultrafast",
                 duration_matching={"enabled": True, "fallback": "error"})
        self.assertAlmostEqual(probe_video(output)["duration"], duration, delta=.001)
        rgb = self.folder / "last.rgb"
        run_command([ffmpeg, "-v", "error", "-y", "-ss", "0.82", "-i", str(output),
                     "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24",
                     "-f", "rawvideo", str(rgb)])
        red, green, blue = rgb.read_bytes()[:3]
        self.assertGreater(red, blue + 100)

    def test_retry_cap_adjustment_budget_and_explicit_rate(self):
        config = voice_config()
        config["target_speech"]["enabled"] = True
        provider = SyntheticProvider()
        builder = self.builder(config, provider)
        builder.build([SpeechUnit(text="Nhưng không.", emotion="punchline")], self.folder / "retry.wav")
        self.assertLessEqual(len(provider.calls), 3)
        initial_rate = config['presets']['punchline']['rate_percent']
        self.assertTrue(all(abs(c["rate"] - initial_rate) <= 8 for c in provider.calls))
        provider.calls.clear()
        builder.build([SpeechUnit(text="Nhưng không.", emotion="punchline", rate_percent=0)], self.folder / "explicit.wav")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0]["rate"], 0)

    def test_failure_names_unit_and_segment_without_silent_fallback(self):
        provider = Mock()
        provider.synthesize.side_effect = RuntimeError("Edge-TTS requires network")
        with self.assertRaisesRegex(RuntimeError, "segment 3, unit 1.*requires network"):
            self.builder(provider=provider).build([SpeechUnit(text="Test")], self.folder / "failed.wav", segment_id=3)
        self.assertFalse((self.folder / "failed.wav").exists())
