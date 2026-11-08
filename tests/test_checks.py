"""READ/WRITE result checks: timeline.md contract and review.json validation + estimate."""
import json
import tempfile
import unittest
from pathlib import Path

from harness.config import load_config
from harness.pipeline import review_check, timeline

TIMELINE = """---
request_id: "demo-123"
analysis_status: {status}
source_duration_seconds: 600.0
---
# Demo

## D. Timeline
| ID | source_start | source_end | Nhân vật | Diễn biến | Bằng chứng | Chắc chắn |
| :-- | --: | --: | --- | --- | --- | --- |
| TL01 | 0 | 120.5 | NV01 | Mở đầu | Hình | Cao |
| TL02 | 120.5 | 02:40 | NV01 | Gặp nhau | Thoại "chào" | Cao |
| TL03 | 160 | 600 | NV02 | Kết | Hình | Vừa |

## E. Shot
| clip_id | timeline_id | source_start | source_end | Nội dung hình | Dùng cho ý kể | Âm gốc |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | TL01 | 10 | 12 | Cửa mở | hook | giữ |
"""


class TimelineTests(unittest.TestCase):
    def write(self, text):
        folder = tempfile.mkdtemp()
        path = Path(folder) / "timeline.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_complete_contract_passes_and_counts_tables(self):
        result = timeline.check(self.write(TIMELINE.format(status="complete")), request_id="demo-123", duration=600)
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["rows"], result["clips"]), (3, 1))
        self.assertAlmostEqual(result["coverage"], 1.0)

    def test_wrong_request_blocked_and_bad_times_fail(self):
        self.assertFalse(timeline.check(self.write(TIMELINE.format(status="complete")), request_id="other", duration=600)["ok"])
        blocked = timeline.check(self.write(TIMELINE.format(status="blocked")), request_id="demo-123", duration=600)
        self.assertFalse(blocked["ok"])
        bad = TIMELINE.format(status="complete").replace("| TL03 | 160 | 600 |", "| TL03 | 700 | 650 |")
        self.assertFalse(timeline.check(self.write(bad), request_id="demo-123", duration=600)["ok"])
        self.assertFalse(timeline.check(self.write("no front matter"), duration=600)["ok"])
        self.assertFalse(timeline.check(Path("/nonexistent/timeline.md"))["ok"])

    def test_partial_warns_and_low_coverage_warns(self):
        partial = timeline.check(self.write(TIMELINE.format(status="partial")), request_id="demo-123", duration=600)
        self.assertTrue(partial["ok"])
        self.assertTrue(any("partial" in w for w in partial["warnings"]))
        sparse = TIMELINE.format(status="complete").replace("| TL03 | 160 | 600 |", "| TL03 | 160 | 200 |")
        result = timeline.check(self.write(sparse), request_id="demo-123", duration=600)
        self.assertTrue(any("phủ" in w for w in result["warnings"]))


class ReviewCheckTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.folder = Path(tempfile.mkdtemp())

    def write(self, data):
        path = self.folder / "review.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_example_is_valid_and_estimated(self):
        example = json.loads((Path(__file__).parents[1] / "examples/review.anchored.example.json").read_text(encoding="utf-8"))
        result = review_check.check(self.write(example), self.config, 60.0, [{"start": 0, "end": 20}, {"start": 20, "end": 60}])
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["segments"], 2)
        self.assertGreater(result["estimate_seconds"], 5)
        self.assertIn("ước tính", review_check.format_report(result))

    def test_errors_are_reported_not_raised(self):
        self.assertFalse(review_check.check(self.folder / "missing.json", self.config, 60)["ok"])
        (self.folder / "bad.json").write_text("{not json", encoding="utf-8")
        self.assertFalse(review_check.check(self.folder / "bad.json", self.config, 60)["ok"])
        no_assessment = {"title": "x", "segments": [{"id": 1, "narration": "Một câu.", "source_start": 0, "source_end": 10}]}
        result = review_check.check(self.write(no_assessment), self.config, 600)
        self.assertFalse(result["ok"])
        beyond = {"title": "x", "segments": [
            {"id": 1, "narration": "Một câu.", "source_start": 0, "source_end": 10},
            {"id": 2, "section": "assessment", "narration": "Nhận xét.", "source_start": 10, "source_end": 700}]}
        self.assertTrue(any("vượt" in e for e in review_check.check(self.write(beyond), self.config, 600)["errors"]))

    def test_shot_across_scene_cut_warns(self):
        data = {"title": "x", "segments": [
            {"id": 1, "narration": [{"id": "a", "text": "Một câu kể khá dài để đủ thời lượng đọc thử."}],
             "source_start": 0, "source_end": 30,
             "shots": [{"source_start": 4, "source_end": 8, "speech_unit_id": "a"}]},
            {"id": 2, "section": "assessment", "narration": "Nhận xét ngắn.", "source_start": 30, "source_end": 50}]}
        result = review_check.check(self.write(data), self.config, 100, [{"start": 0, "end": 6}, {"start": 6, "end": 100}])
        self.assertTrue(any("cắt cảnh" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
