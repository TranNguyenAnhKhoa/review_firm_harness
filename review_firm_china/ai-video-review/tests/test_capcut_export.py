"""Real media regression: separate tracks keep exact frame boundaries and speech samples."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave

from scripts.export_capcut import assemble_narration, export
from scripts.measure_review import cache_signatures
from src.pipeline.build_review import load_config
from src.pipeline.editorial import EditorialPolicy
from src.pipeline.schema import ReviewScript
from src.utils import executable, run_command
from src.video.probe import probe_video


class CapCutExportTests(unittest.TestCase):
    def test_actual_picture_and_pcm_stay_aligned_and_preserve_voice(self):
        ffmpeg = executable('ffmpeg', 'FFMPEG_BINARY')
        with tempfile.TemporaryDirectory(dir='output/tmp') as directory:
            root = Path(directory).resolve()
            source = root / 'source.mp4'
            run_command([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                         'color=red:s=160x90:r=30:d=30', '-f', 'lavfi', '-i',
                         'color=blue:s=160x90:r=30:d=30', '-filter_complex',
                         '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]',
                         '-c:v', 'libx264', '-preset', 'ultrafast', str(source)])
            script = root / 'review.json'
            script.write_text(json.dumps(dict(title='Synthetic export fixture', source_video=str(source), segments=[
                dict(id=1, section='story', narration='Synthetic red fixture', source_start=0, source_end=30,
                     shots=[dict(source_start=2, source_end=18)]),
                dict(id=2, section='assessment', narration='Synthetic blue fixture', source_start=30, source_end=60,
                     shots=[dict(source_start=32, source_end=48)])])), encoding='utf-8')
            review = ReviewScript.load(script)
            config_path = Path('config/config.yaml').resolve()
            config = load_config(config_path)
            measured = root / 'measured'
            (measured / 'audio').mkdir(parents=True)
            (measured / 'debug').mkdir()
            code_hash = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('src/audio').glob('*.py')))).hexdigest()
            # Fractional frame durations expose drift from MKV's millisecond
            # timebase when many parts are joined without explicit durations.
            duration = 14.02
            frame_count = 421
            edit_duration = frame_count / 30
            for segment in review.segments:
                audio = measured / 'audio' / f'segment_{segment.id:03d}.wav'
                run_command([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                             f'sine=frequency={400*segment.id}:sample_rate=48000:duration={duration}',
                             '-ac', '2', '-c:a', 'pcm_s16le', str(audio)])
                debug_path = measured / 'debug' / f'segment_{segment.id:03d}_tts.json'
                debug_path.write_text(json.dumps(dict(duration=duration, speech_duration=duration,
                    units=[dict(id='u1', text=segment.narration, start=0, end=duration)])), encoding='utf-8')
                signature, _ = cache_signatures(segment, config, code_hash, {})
                (measured / 'debug' / f'segment_{segment.id:03d}.cache.json').write_text(json.dumps(dict(
                    signature=signature, audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
                    debug_sha256=hashlib.sha256(debug_path.read_bytes()).hexdigest())), encoding='utf-8')
            policy = EditorialPolicy.model_validate(config['editorial'])
            timing = policy.timing_report(review, 60, [duration, duration], [edit_duration, edit_duration])
            timing['review_sha256'] = hashlib.sha256(script.read_bytes()).hexdigest()
            (measured / 'review_timing.json').write_text(json.dumps(timing), encoding='utf-8')
            output = root / 'handoff'
            args = argparse.Namespace(video=str(source), review=str(script), tts_dir=str(measured),
                                      output_dir=str(output), config=str(config_path), workers=1)
            export(args)
            metadata = probe_video(output / 'video_cut.mp4')
            self.assertEqual(metadata['audio_codec'], None)
            self.assertAlmostEqual(metadata['duration'], 2*edit_duration, delta=1/48000)
            with wave.open(str(output / 'narration.wav'), 'rb') as narration:
                self.assertEqual(narration.getnframes(), 2*frame_count*1600)
                for index in range(2):
                    narration.setpos(index*frame_count*1600)
                    with wave.open(str(measured / 'audio' / f'segment_{index+1:03d}.wav'), 'rb') as voice:
                        self.assertEqual(narration.readframes(voice.getnframes()), voice.readframes(voice.getnframes()))
            for timestamp, channel in ((14.0, 0), (14.07, 2)):
                rgb = run_command([ffmpeg, '-v', 'error', '-ss', str(timestamp), '-i',
                    str(output / 'video_cut.mp4'), '-frames:v', '1', '-vf', 'scale=1:1',
                    '-pix_fmt', 'rgb24', '-f', 'rawvideo', str(root / 'frame.rgb'), '-y'])
                pixel = (root / 'frame.rgb').read_bytes()
                self.assertGreater(pixel[channel], pixel[2-channel] + 100)
            with self.assertRaises(FileExistsError):
                export(args)

    def test_refuses_speech_truncation_and_long_silence_padding(self):
        with tempfile.TemporaryDirectory(dir='output/tmp') as directory:
            voice = Path(directory) / 'voice.wav'
            with wave.open(str(voice), 'wb') as stream:
                stream.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
                stream.writeframes(bytes(48000*4))
            for frames in (20, 40):
                with self.assertRaises(ValueError):
                    assemble_narration([dict(audio=str(voice), frames=frames)], Path(directory) / 'out.wav', 30)
