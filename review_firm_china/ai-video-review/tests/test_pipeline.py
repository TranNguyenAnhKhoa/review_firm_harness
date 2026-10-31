"""Local regression tests; no network or model downloads."""
from __future__ import annotations

import math
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.pipeline.schema import ReviewScript
from src.pipeline.build_review import load_config
from src.video.clipper import choose_centered_range, cut_clip
from src.video.probe import probe_video, probe_audio
from src.video.scene_detect import detect_scenes
from src.video.renderer import concat_clips, render_final
from src.subtitle.generator import generate_ass
from src.utils import executable, run_command


class SchemaTests(unittest.TestCase):
    def script(self):
        return {"title": "Demo", "segments": [
            {"id": 1, "narration": "Tiếng Việt", "source_start": 0, "source_end": 2}
        ]}

    def test_reject_invalid_range_nan_empty_and_duplicate_ids(self):
        for field, value in (("source_end", 0), ("source_start", math.nan), ("narration", "  ")):
            data = self.script()
            data["segments"][0][field] = value
            with self.assertRaises(ValidationError):
                ReviewScript.model_validate(data)
        data = self.script()
        data["segments"] *= 2
        with self.assertRaises(ValidationError):
            ReviewScript.model_validate(data)

    def test_centered_selection_stays_inside_range(self):
        self.assertEqual(choose_centered_range(10, 24, 6), (14, 6, 0))
        self.assertEqual(choose_centered_range(10, 12, 5), (10, 2, 3))
        with self.assertRaises(ValueError):
            choose_centered_range(0, 2, -1)

    def test_partial_config_has_defaults(self):
        config = load_config("examples/config.example.yaml")
        self.assertIn("temp_dir", config["project"])
        self.assertEqual(config["video"]["codec"], "libx264")


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path("output/tmp/regression tests")
        cls.directory.mkdir(parents=True, exist_ok=True)
        cls.video = cls.directory / "vertical no audio.mp4"
        cls.ffmpeg = executable("ffmpeg", "FFMPEG_BINARY")
        # A known hard cut from red to blue, with no source audio.
        run_command([cls.ffmpeg, "-v", "error", "-y",
                     "-f", "lavfi", "-i", "color=red:s=240x426:r=25:d=1",
                     "-f", "lavfi", "-i", "color=blue:s=240x426:r=25:d=1",
                     "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                     "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.video)])

    def test_detect_known_cut_and_single_scene(self):
        scenes = detect_scenes(str(self.video))
        self.assertEqual(len(scenes), 2)
        self.assertAlmostEqual(scenes[0]["end"], 1.0, delta=0.08)
        one = self.directory / "single.mp4"
        cut_clip(str(self.video), 0, 0.8, 0.8, str(one), preset="ultrafast", fps=25)
        scenes = detect_scenes(str(one))
        self.assertEqual(len(scenes), 1)
        self.assertAlmostEqual(scenes[0]["duration"], 0.8, delta=0.04)

    def test_padding_vertical_subtitles_and_full_render(self):
        clip = self.directory / "padded.mp4"
        cut_clip(str(self.video), 0.2, 0.8, 2.2, str(clip), preset="ultrafast", fps=25)
        meta = probe_video(clip)
        self.assertAlmostEqual(meta["duration"], 2.2, delta=0.04)
        self.assertEqual((meta["width"], meta["height"]), (240, 426))
        self.assertEqual(meta["audio_codec"], "aac")
        # The padded frame must still be red; reading outside source_end would turn it blue.
        rgb = self.directory / "last.rgb"
        run_command([self.ffmpeg, "-v", "error", "-y", "-ss", "2.1", "-i", str(clip),
                     "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24",
                     "-f", "rawvideo", str(rgb)])
        red, green, blue = rgb.read_bytes()[:3]
        self.assertGreater(red, blue + 100)

        narration = self.directory / "voice.wav"
        run_command([self.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                     "sine=frequency=600:sample_rate=48000:duration=2.1", "-ac", "2", str(narration)])
        self.assertAlmostEqual(probe_audio(narration), 2.1, delta=0.01)
        combined = self.directory / "combined.mp4"
        concat_clips([str(clip), str(clip)], str(combined), preset="ultrafast")
        subtitle = self.directory / "review.ass"
        generate_ass([
            {"narration": "Đây là phụ đề tiếng Việt để kiểm tra xuống dòng.", "duration": 2.1, "start": 0},
            {"narration": "Cảnh tiếp theo.", "duration": 2.1, "start": 2.2}
        ], str(subtitle), width=240, height=426, font_size=20, max_chars_per_line=20)
        contents = subtitle.read_text(encoding="utf-8-sig")
        self.assertIn(r"\N", contents)
        self.assertNotIn(r"\\N", contents)
        final = self.directory / "final.mp4"
        render_final(str(combined), [str(narration), str(narration)], [0, 2.2], str(final),
                     subtitles_path=str(subtitle), preset="ultrafast", fps=25)
        result = probe_video(final)
        self.assertAlmostEqual(result["duration"], 4.4, delta=0.08)
        self.assertEqual((result["width"], result["height"]), (240, 426))
        self.assertEqual((result["video_codec"], result["audio_codec"]), ("h264", "aac"))
        run_command([self.ffmpeg, "-v", "error", "-i", str(final), "-f", "null", "-"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

