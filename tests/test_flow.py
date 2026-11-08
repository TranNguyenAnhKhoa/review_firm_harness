"""Whole pipeline on a synthetic film: probe, manual READ/WRITE with gates, measure (synthetic voice),
render, QC, then stale detection. Real FFmpeg, no network, no agent CLI, no TTS model."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.audio.tts import TTSProvider
from harness.pipeline import stages
from harness.pipeline.job import Job
from harness.pipeline.runner import run, stale
from harness.utils import ffmpeg, run_command
from harness.video.probe import probe_video


class FakeVoice(TTSProvider):
    """Speaks at exactly 5 tokens/s (inside every emotion's accepted range): no retries, known durations."""

    def synthesize(self, text, output_path, voice=None, *, rate_percent=0, pitch_hz=0, volume_percent=0):
        tokens = sum(any(c.isalnum() for c in w) for w in text.split())
        run_command([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                     f"sine=frequency=500:sample_rate=48000:duration={tokens / 5:.3f}", "-ac", "2",
                     "-c:a", "libmp3lame", output_path])
        return output_path


def words(n, seed):
    return " ".join(f"tiếng{seed}{i}" for i in range(n)) + "."


class FlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="flow ")
        cls.root = Path(cls.temp.name)
        cls.video = cls.root / "film.mp4"
        colors = ["red", "green", "blue", "yellow", "purple", "orange"]
        inputs, labels = [], ""
        for i, color in enumerate(colors):
            inputs += ["-f", "lavfi", "-i", f"color={color}:s=320x180:r=25:d=10"]
            labels += f"[{i}:v]"
        run_command([ffmpeg(), "-v", "error", "-y", *inputs, "-f", "lavfi", "-i", "sine=frequency=220:duration=60",
                     "-filter_complex", f"{labels}concat=n=6:v=1:a=0[v]", "-map", "[v]", "-map", "6:a",
                     "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                     str(cls.video)])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_flow(self):
        jobs = self.root / "jobs"
        overrides = {"agents": {"read": {"engine": "manual"}, "write": {"engine": "manual"}, "revise_rounds": 0},
                     "render": {"workers": 2, "threads": 1, "picture_style": {
                         "width": 320, "height": 180, "top_bar": 18, "bottom_bar": 18, "font_size": 12,
                         "margin_right": 8, "margin_bottom": 30}},
                     "video": {"preset": "ultrafast"}, "measure": {"workers": 2}}
        job = Job.create("synthetic-film", self.video, title="Phim thử", overrides=overrides, jobs_dir=jobs)

        with patch("harness.audio.narration_builder.create_tts_provider", return_value=FakeVoice()):
            # probe runs, READ waits for a manual timeline
            self.assertEqual(run(job), "waiting")
            state = job.state()["stages"]
            self.assertEqual(state["probe"]["status"], "done")
            self.assertAlmostEqual(state["probe"]["metrics"]["duration"], 60, delta=.1)
            self.assertTrue(state["read"].get("needs_input"))
            self.assertTrue((job.stage_dir("read") / "request.md").is_file())

            job.timeline.write_text(f"""---
request_id: "{stages._request_id(job)}"
analysis_status: complete
source_duration_seconds: 60.0
---
| ID | source_start | source_end | Diễn biến |
| --- | --- | --- | --- |
| TL01 | 0 | 30 | Màu đỏ, xanh lá, xanh dương |
| TL02 | 30 | 60 | Màu vàng, tím, cam |

| clip_id | timeline_id | source_start | source_end | Nội dung |
| --- | --- | --- | --- | --- |
| C1 | TL01 | 1 | 4 | đỏ |
""", encoding="utf-8")
            self.assertEqual(run(job), "waiting")                 # READ passes its check, stops at the gate
            self.assertEqual(job.state()["stages"]["read"]["status"], "waiting")
            self.assertEqual(run(job), "waiting")                 # still not approved: nothing moves
            job.set_gate("read", True, by="test")
            self.assertEqual(run(job), "waiting")                 # WRITE waits for a manual review.json
            self.assertTrue(job.state()["stages"]["write"].get("needs_input"))

            review = {"title": "Thử", "segments": [
                {"id": 1, "section": "story", "source_start": 0, "source_end": 40,
                 "narration": [{"id": f"u{k}", "text": words(25, k), "emotion": "normal"} for k in range(3)],
                 "shots": [{"source_start": s, "source_end": s + 3, "speech_unit_id": f"u{k}"}
                           for k, pair in enumerate(((1, 5), (11, 15), (21, 31))) for s in pair]},
                {"id": 2, "section": "assessment", "source_start": 40, "source_end": 60,
                 "narration": [{"id": "a1", "text": words(30, 8), "emotion": "serious"},
                               {"id": "a2", "text": words(30, 9), "emotion": "serious"}],
                 "shots": [{"source_start": 41, "source_end": 44.5, "speech_unit_id": "a1"},
                           {"source_start": 45, "source_end": 48.5, "speech_unit_id": "a1"},
                           {"source_start": 50, "source_end": 53.5, "speech_unit_id": "a2"},
                           {"source_start": 55, "source_end": 58.5, "speech_unit_id": "a2"}]}]}
            job.review.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run(job), "waiting")                 # WRITE gate
            job.set_gate("write", True, by="test")
            self.assertEqual(run(job), "finished")                # measure, render, qc

        state = job.state()["stages"]
        for stage in ("measure", "render", "qc"):
            self.assertEqual(state[stage]["status"], "done", state[stage])
        measured = state["measure"]["metrics"]
        self.assertTrue(measured["passed"])
        self.assertTrue(.40 <= measured["source_ratio"] <= .50)
        self.assertTrue(job.final_video.is_file())
        final = probe_video(job.final_video)
        self.assertEqual((final["width"], final["height"], final["video_codec"], final["audio_codec"]), (320, 180, "h264", "aac"))
        self.assertAlmostEqual(final["duration"], measured["review_duration"], delta=.2)
        qc = json.loads((job.stage_dir("qc") / "qc.json").read_text(encoding="utf-8"))
        self.assertTrue(qc["passed"])
        self.assertTrue((job.stage_dir("qc") / "thumbs.jpg").is_file())
        log = (job.root / "runs").glob("*.log")
        self.assertTrue(any("QC ĐẠT" in p.read_text(encoding="utf-8") for p in log))

        # a second run reuses everything; editing the approved review invalidates the gate and measure
        self.assertEqual(run(job), "finished")
        review["segments"][0]["narration"][0]["text"] = words(26, 0)
        job.review.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(stale(job, "measure"))
        self.assertFalse(job.gate_ok("write"))
        self.assertEqual(run(job), "waiting")
        self.assertEqual(job.state()["stages"]["write"]["status"], "waiting")

    def test_reject_records_note_and_stage_fails(self):
        job = Job.create("reject-me", self.video, jobs_dir=self.root / "jobs2",
                         overrides={"agents": {"read": {"engine": "manual"}}})
        run(job, only="probe")
        job.timeline.write_text(f'---\nrequest_id: "{stages._request_id(job)}"\nanalysis_status: complete\n'
                                'source_duration_seconds: 60\n---\n| ID | start | end |\n|-|-|-|\n| 1 | 0 | 60 |\n',
                                encoding="utf-8")
        self.assertEqual(run(job, only="read"), "waiting")
        job.set_gate("read", False, note="Thiếu thoại", by="test")
        self.assertEqual(job.state()["stages"]["read"]["status"], "failed")
        self.assertIn("Thiếu thoại", stages._reviewer_note(job, "read"))
        with self.assertRaises(ValueError):
            job.set_gate("measure", True)


if __name__ == "__main__":
    unittest.main()
