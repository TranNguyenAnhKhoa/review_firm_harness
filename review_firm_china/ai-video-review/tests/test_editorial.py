from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from pydantic import ValidationError

from src.pipeline.editorial import EditorialPolicy, require_timing
from src.pipeline.schema import ReviewScript
from src.pipeline.build_review import build_review
from src.audio.narration_builder import NarrationResult


def fake_builder(*durations):
    builder = Mock()
    builder.build.side_effect = [
        NarrationResult(Path("fake.wav"), d, d, [{"text": "Test", "start": 0, "end": d}], {})
        for d in durations
    ]
    return builder


def script():
    return ReviewScript.model_validate({
        "title": "Policy fixture",
        "segments": [
            {"id": 1, "section": "story", "narration": "Nội dung câu chuyện.",
             "source_start": 0, "source_end": 300},
            {"id": 2, "section": "assessment", "narration": "Nhận xét tác phẩm.",
             "source_start": 300, "source_end": 500},
        ],
    })


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.policy = EditorialPolicy()
        self.review = script()

    def test_budget_includes_assessment(self):
        b = self.policy.budget(1193.033333)
        self.assertAlmostEqual(b["total_min"], 477.2133332)
        self.assertAlmostEqual(b["total_max"], 596.5166665)
        self.assertAlmostEqual(b["story_target"] + b["assessment_target"], b["total_target"])

    def test_total_duration_boundaries(self):
        for total, expected in [(199.99, False), (200, True), (225, True), (250, True), (250.01, False)]:
            report = self.policy.timing_report(self.review, 500, [total - 15, 15], [total - 15, 15])
            self.assertEqual(report["passed"], expected, report)
        report = self.policy.timing_report(self.review, 500, [235, 15], [235, 15], rendered_duration=250.01)
        self.assertFalse(report["passed"])

    def test_assessment_uses_real_voice_not_padded_duration(self):
        for seconds, expected in [(9.99, False), (10, True), (15, True), (20, True), (20.01, False)]:
            report = self.policy.timing_report(self.review, 500, [210, seconds], [210, seconds])
            self.assertEqual(report["passed"], expected, report)
        padded = self.policy.timing_report(self.review, 500, [210, 5], [210, 15])
        self.assertFalse(padded["passed"])
        # Container extending the final section past 20s must fail too.
        extended = self.policy.timing_report(self.review, 500, [210, 20], [210, 20], rendered_duration=230.1)
        self.assertFalse(extended["passed"])

    def test_structure_requires_one_final_assessment_and_story(self):
        legacy = self.review.model_copy(deep=True)
        legacy.segments[-1].section = "story"
        with self.assertRaisesRegex(ValueError, "assessment"):
            self.policy.validate_structure(legacy, 500)
        invalid = self.review.model_dump()
        invalid["segments"].reverse()
        with self.assertRaises(ValidationError):
            ReviewScript.model_validate(invalid)
        invalid = self.review.model_dump()
        invalid["segments"][0]["section"] = "assessment"
        with self.assertRaises(ValidationError):
            ReviewScript.model_validate(invalid)
        with self.assertRaisesRegex(ValueError, "too short"):
            self.policy.validate_structure(self.review, 10)

    def test_invalid_config_and_timings_rejected(self):
        with self.assertRaises(ValidationError):
            EditorialPolicy(min_source_ratio=.6, max_source_ratio=.4)
        with self.assertRaises(ValidationError):
            EditorialPolicy(assessment_min_seconds=25)
        for values in ([210], [210, float("nan")], [210, 0]):
            with self.assertRaises(ValueError):
                self.policy.timing_report(self.review, 500, values, values)

    def test_invalid_tts_stops_before_clips_and_preserves_final(self):
        Path("output/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir="output/tmp") as temp:
            directory = Path(temp)
            source = directory / "source.mp4"
            source.touch()
            review = directory / "review.json"
            review.write_text(self.review.model_dump_json(), encoding="utf-8")
            out = directory / "artifacts"
            final = out / "final/final_review.mp4"
            final.parent.mkdir(parents=True)
            final.write_bytes(b"previous successful render")
            meta = {"duration": 500, "width": 720, "height": 1280, "fps": 30}
            with patch("src.pipeline.build_review.probe_video", return_value=meta), \
                 patch("src.pipeline.build_review.NarrationBuilder", return_value=fake_builder(4, 2)), \
                 patch("src.pipeline.build_review.cut_clip") as cut, \
                 patch("src.pipeline.build_review.render_final") as render:
                with self.assertRaisesRegex(ValueError, "too short"):
                    build_review(str(source), str(review), output_dir=str(out))
                cut.assert_not_called()
                render.assert_not_called()
            self.assertEqual(final.read_bytes(), b"previous successful render")
            report = json.loads((out / "review_timing.json").read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])

    def test_valid_tts_only_skips_video_rendering(self):
        with tempfile.TemporaryDirectory(dir="output/tmp") as temp:
            directory = Path(temp)
            source = directory / "source.mp4"
            source.touch()
            review = directory / "review.json"
            review.write_text(self.review.model_dump_json(), encoding="utf-8")
            meta = {"duration": 500, "width": 720, "height": 1280, "fps": 30}
            with patch("src.pipeline.build_review.probe_video", return_value=meta), \
                 patch("src.pipeline.build_review.NarrationBuilder", return_value=fake_builder(210, 15)), \
                 patch("src.pipeline.build_review.cut_clip") as cut:
                report_path = build_review(str(source), str(review), output_dir=str(directory / "artifacts"), tts_only=True)
                cut.assert_not_called()
            self.assertTrue(json.loads(report_path.read_text(encoding="utf-8"))["passed"])

    def test_container_over_limit_does_not_replace_existing_video(self):
        with tempfile.TemporaryDirectory(dir="output/tmp") as temp:
            directory = Path(temp)
            source = directory / "source.mp4"
            source.touch()
            review = directory / "review.json"
            review.write_text(self.review.model_dump_json(), encoding="utf-8")
            out = directory / "artifacts"
            final = out / "final/final_review.mp4"
            final.parent.mkdir(parents=True)
            final.write_bytes(b"previous successful render")
            meta = {"duration": 500, "width": 720, "height": 1280, "fps": 30}
            final_meta = {**meta, "width":1920, "height":1080, "duration": 250.033333, "video_codec": "h264", "audio_codec": "aac"}

            def render_candidate(*args, **kwargs):
                Path(args[3]).write_bytes(b"candidate outside editorial range")

            with patch("src.pipeline.build_review.probe_video", side_effect=[meta, {"duration": 235}, {"duration": 15}, final_meta]), \
                 patch("src.pipeline.build_review.NarrationBuilder", return_value=fake_builder(235, 15)), \
                 patch("src.pipeline.build_review.cut_clip"), \
                 patch("src.pipeline.build_review.concat_clips"), \
                 patch("src.pipeline.build_review.render_final", side_effect=render_candidate):
                with self.assertRaisesRegex(ValueError, "too long"):
                    build_review(str(source), str(review), output_dir=str(out))
            self.assertEqual(final.read_bytes(), b"previous successful render")
            self.assertTrue((final.parent / "final_review.pending.mp4").exists())
