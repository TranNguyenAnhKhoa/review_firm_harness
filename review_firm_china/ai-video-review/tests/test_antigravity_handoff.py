"""Offline contract checks; no app launch or actual message submission."""
import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from scripts import antigravity_handoff as handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.mock_root = patch.object(handoff, "ROOT", self.root)
        self.mock_root.start()
        self.addCleanup(self.mock_root.stop)
        self.folder, self.output = handoff.job_paths("sample")
        self.folder.mkdir(parents=True)
        self.output.parent.mkdir(parents=True)
        self.manifest = {"request_id": "sample-123", "source_video": str(self.root / "input/videos/movie.mp4"),
                         "metadata": {"duration": 60}, "delivery_status": "ui_submitted"}
        handoff.save_manifest(self.folder, self.manifest)

    def write_return(self, **changes):
        header = {"request_id": "sample-123", "source_video": self.manifest["source_video"],
                  "source_duration_seconds": 60, "analysis_status": "complete"}
        header.update(changes)
        self.output.write_text("---\n" + yaml.safe_dump(header) + "---\n# Timeline\n", encoding="utf-8")

    def test_reject_path_traversal(self):
        for name in ("../other", "C:/outside", "two/parts", "UPPER", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                handoff.job_paths(name)

    def test_expected_return_location(self):
        self.assertEqual(self.output, self.root / "data/timeline/sample/timeline.md")

    def test_waiting_partial_blocked_and_complete(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(handoff.check("sample"), 2)
            for status, result in (("partial", 2), ("blocked", 2), ("complete", 0)):
                self.write_return(analysis_status=status)
                self.assertEqual(handoff.check("sample"), result)

    def test_reject_mismatched_return(self):
        for changes in ({"request_id": "wrong"}, {"source_video": "another.mp4"},
                        {"source_duration_seconds": 1}, {"analysis_status": "done"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.write_return(**changes)
                handoff.check("sample")

    def test_no_duplicate_or_uncertain_send(self):
        for status in ("ui_submitted", "submission_in_progress"):
            self.manifest["delivery_status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, "already submitted"):
                asyncio.run(handoff.send(self.folder, self.manifest))


if __name__ == "__main__":
    unittest.main()
