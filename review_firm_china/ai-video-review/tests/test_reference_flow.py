"""Reference flow regression: shot bounds, frame totals, bars, watermark and audio."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from pydantic import ValidationError
from src.pipeline.schema import ReviewSegment
from src.video.montage import plan_shots, cut_montage
from src.video.picture_style import PictureStyle
from src.video.renderer import render_measured_segment
from src.video.probe import probe_video
from src.utils import executable, run_command


class ReferenceTests(unittest.TestCase):
    def test_shot_changes_can_follow_measured_speech_units(self):
        shots = [{'source_start':0,'source_end':4,'speech_unit_id':'first'},
                 {'source_start':4,'source_end':8,'speech_unit_id':'first'},
                 {'source_start':8,'source_end':12,'speech_unit_id':'second'}]
        timings = [{'id':'first','start':0,'end':2.8}, {'id':'second','start':3,'end':4}]
        plans = plan_shots(shots,4,30,{'enabled':False,'fallback':'error'},timings)
        self.assertEqual([p['frames'] for p in plans],[45,45,30])
        self.assertEqual(plans[-1]['timeline_start'],3)
        with self.assertRaisesRegex(ValueError,'measured'):
            plan_shots(shots,4,30)
        with self.assertRaises(ValidationError):
            ReviewSegment(id=1,narration='No anchored units.',source_start=0,source_end=12,shots=shots)

    def test_long_dynamic_normalization_preserves_sample_timeline(self):
        import wave
        from src.audio.normalizer import normalize_loudness
        from src.audio.speech import LoudnessConfig
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp)/'speech.wav', Path(temp)/'normalized.wav'
            samples = round(16.06875 * 48000)
            t = np.arange(samples) / 48000
            envelope = .03 + .3 * (np.sin(t * 2) ** 8)
            audio = envelope * np.sin(2*np.pi*440*t)
            audio[samples//2:samples//2+32] = .95
            with wave.open(str(source),'wb') as wav:
                wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(48000)
                pcm = (audio*32767).astype('<i2')
                wav.writeframes(np.column_stack([pcm,pcm]).tobytes())
            normalize_loudness(source,target,LoudnessConfig())
            with wave.open(str(target),'rb') as wav:
                self.assertEqual(wav.getnframes(),samples)
                wav.setpos(samples-4800)
                tail = np.frombuffer(wav.readframes(4800),dtype='<i2')
                self.assertGreater(float(np.abs(tail.astype(float)).mean()),10)

    def test_shot_order_bounds_weight_and_exact_frame_total(self):
        shots = [{'source_start':0,'source_end':3,'weight':1},
                 {'source_start':5,'source_end':8,'weight':2}]
        plans = plan_shots(shots, 2.5, 30, {'enabled':False,'fallback':'error'})
        self.assertEqual(sum(p['frames'] for p in plans), 75)
        self.assertEqual([p['source_start'] for p in plans], [0,5])
        self.assertAlmostEqual(sum(p['duration'] for p in plans), 2.5)
        self.assertTrue(all(p['start']+p['source_duration'] <= p['source_end'] for p in plans))
        for invalid in ([{'source_start':0,'source_end':1,'weight':0}],
                        [{'source_start':0,'source_end':1,'weight':float('inf')}]):
            with self.assertRaises(ValidationError):
                plan_shots(invalid, 2, 30)
        with self.assertRaisesRegex(ValueError, 'Footage'):
            plan_shots([{'source_start':0,'source_end':.1}], 2, 30, {'enabled':False,'fallback':'error'})
        with self.assertRaises(ValidationError):
            ReviewSegment(id=1,narration='Câu kể.',source_start=2,source_end=5,
                          shots=[{'source_start':0,'source_end':3}])

    def test_real_montage_cuts_and_composition_with_existing_source_bars(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            ffmpeg = executable('ffmpeg','FFMPEG_BINARY')
            video, voice = directory/'source.mp4', directory/'voice.wav'
            run_command([ffmpeg,'-v','error','-y',
                         '-f','lavfi','-i','color=red:s=320x144:r=30:d=2',
                         '-f','lavfi','-i','color=blue:s=320x144:r=30:d=2',
                         '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0,pad=320:180:0:18[v]',
                         '-map','[v]','-c:v','libx264',str(video)])
            run_command([ffmpeg,'-v','error','-y','-f','lavfi','-i',
                         'sine=frequency=440:sample_rate=48000:duration=2','-ac','2',str(voice)])
            shots = [{'source_start':0,'source_end':2}, {'source_start':2,'source_end':4}]
            montage = cut_montage(str(video),shots,2,str(directory/'cut.mp4'),fps=30,
                                  duration_matching={'enabled':False,'fallback':'error'},preset='ultrafast')
            capture = cv2.VideoCapture(str(montage))
            colors = []
            for t in (.5,1.5):
                capture.set(cv2.CAP_PROP_POS_MSEC,t*1000)
                ok,frame = capture.read()
                self.assertTrue(ok)
                colors.append(frame[90,160])
            capture.release()
            self.assertGreater(int(colors[0][2]),200)
            self.assertGreater(int(colors[1][0]),200)
            style = PictureStyle(enabled=True,width=320,height=180,top_bar=18,bottom_bar=18,
                                 font_size=14,margin_right=8,margin_bottom=30,watermark='Review Phim')
            rendered = render_measured_segment(str(video),str(voice),0,4,2,str(directory/'styled.mkv'),
                shots=shots,fps=30,preset='ultrafast',duration_matching={'enabled':False,'fallback':'error'},
                picture_style=style.model_dump())
            meta = probe_video(rendered)
            self.assertEqual((meta['width'],meta['height'],meta['audio_codec']), (320,180,'pcm_s16le'))
            self.assertAlmostEqual(meta['duration'],2,delta=.002)
            capture = cv2.VideoCapture(str(rendered))
            capture.set(cv2.CAP_PROP_POS_MSEC,500)
            ok,frame = capture.read()
            capture.release()
            self.assertTrue(ok)
            self.assertLess(float(frame[:15].mean()),2)
            self.assertLess(float(frame[-15:].mean()),2)
            # Already encoded source bars must not shrink the active area a second time.
            self.assertGreater(float(frame[20:35,:,2].mean()),150)
            # White text in the lower right, rather than a large narration subtitle.
            self.assertGreater(int((frame[115:155,190:315].min(axis=2)>190).sum()),10)


if __name__ == '__main__':
    unittest.main()
