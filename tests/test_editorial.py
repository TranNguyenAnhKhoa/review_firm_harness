from __future__ import annotations

import unittest

from pydantic import ValidationError

from harness.editorial import EditorialPolicy, require_timing
from harness.schema import ReviewScript


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

    def test_require_timing_raises_with_reasons(self):
        report = self.policy.timing_report(self.review, 500, [100, 15], [100, 15])
        with self.assertRaisesRegex(ValueError, "too short"):
            require_timing(report)


if __name__ == "__main__":
    unittest.main()
