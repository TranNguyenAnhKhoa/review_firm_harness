"""Real FFmpeg tests of single-pass picture/voice and PCM concat boundaries."""
from pathlib import Path
import json
import tempfile
import unittest

from harness.subtitle import generate_ass
from harness.utils import executable, run_command
from harness.video.probe import probe_video
from harness.video.renderer import render_measured_segment, concat_measured_segments


class MeasuredRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="measured render ")
        cls.root = Path(cls.temp.name)
        cls.ffmpeg = executable("ffmpeg", "FFMPEG_BINARY")
        cls.video = cls.root / "source.mp4"
        cls.voice = cls.root / "voice.wav"
        run_command([cls.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                     "color=red:s=240x426:r=25:d=1", "-f", "lavfi", "-i",
                     "color=blue:s=240x426:r=25:d=1", "-filter_complex",
                     "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264",
                     "-pix_fmt", "yuv420p", str(cls.video)])
        run_command([cls.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                     "sine=frequency=600:sample_rate=48000:duration=0.95", "-ac", "2", str(cls.voice)])

    def test_pcm_concat_exact_frame_duration_and_source_boundary(self):
        subtitles = generate_ass([{"narration": "Tiếng Việt", "start": .2, "duration": .5}],
            str(self.root / "captions.ass"), width=240, height=426, font_size=20,
            position="top", margin_vertical=30)
        text = subtitles.read_text(encoding="utf-8-sig")
        self.assertIn(",8,30,30,30,1", text)
        self.assertIn("0:00:00.20,0:00:00.70", text)
        clips = []
        for index, (start, end) in enumerate(((0, .94), (1, 2))):
            clip = self.root / f"part_{index:03d}.mkv"
            render_measured_segment(str(self.video), str(self.voice), start, end, 1.0, str(clip),
                subtitles_path=str(subtitles), fps=25, preset="ultrafast", threads=1,
                duration_matching={"enabled": True, "fallback": "error"})
            self.assertAlmostEqual(probe_video(clip)["duration"], 1.0, delta=.002)
            clips.append(clip)
        final = concat_measured_segments(clips, [1.0, 1.0], str(self.root / "final.mp4"))
        metadata = probe_video(final)
        self.assertAlmostEqual(metadata["duration"], 2, delta=.04)
        self.assertEqual((metadata["width"], metadata["height"]), (240, 426))
        self.assertEqual((metadata["video_codec"], metadata["audio_codec"]), ("h264", "aac"))
        for timestamp, channel in ((.92, 0), (1.12, 2)):
            rgb = self.root / f"frame_{channel}.rgb"
            run_command([self.ffmpeg, "-v", "error", "-y", "-ss", str(timestamp), "-i", str(final),
                         "-frames:v", "1", "-vf", "scale=1:1", "-pix_fmt", "rgb24", "-f", "rawvideo", str(rgb)])
            values = rgb.read_bytes()[:3]
            self.assertGreater(values[channel], values[2-channel] + 100)
        run_command([self.ffmpeg, "-v", "error", "-xerror", "-i", str(final), "-f", "null", "-"])
        frames = json.loads(run_command([executable("ffprobe", "FFPROBE_BINARY"), "-v", "error",
            "-select_streams", "v", "-show_frames", "-show_entries", "frame=best_effort_timestamp_time",
            "-of", "json", str(final)]).stdout)["frames"]
        times = [float(f["best_effort_timestamp_time"]) for f in frames]
        self.assertEqual(len(times), 50)
        for index, timestamp in enumerate(times):
            self.assertAlmostEqual(timestamp, index / 25, delta=.001)

    def test_refuses_truncated_voice_or_insufficient_footage(self):
        for source_end, target in ((1.0, .5), (.2, 1.0)):
            with self.assertRaises(ValueError):
                render_measured_segment(str(self.video), str(self.voice), 0, source_end, target,
                    str(self.root / "invalid.mkv"), duration_matching={"enabled": True, "fallback": "error"})


if __name__ == "__main__":
    unittest.main()
