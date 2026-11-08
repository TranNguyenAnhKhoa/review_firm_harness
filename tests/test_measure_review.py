"""MEASURE cache keys: visual edits reuse audio, anything audible re-synthesizes."""
import copy
import unittest

from harness.audio.speech import SpeechUnit
from harness.pipeline.stages import cache_signature
from harness.schema import ReviewSegment


class MeasurementCacheTests(unittest.TestCase):
    def setUp(self):
        self.segment = ReviewSegment(id=1, narration=[SpeechUnit(text='Example sentence.', emotion='normal')],
                                     source_start=0, source_end=10)
        self.config = {'tts': {'voice': 'test', 'rate': 12}, 'audio': {'narration': {'loudness_lufs': -16}}}

    def signature(self, segment=None, config=None, code='hash'):
        return cache_signature(segment or self.segment, config or self.config, code)

    def test_visual_changes_reuse_same_audio_key(self):
        revised = self.segment.model_copy(update={'source_start': 20, 'source_end': 40, 'visual_intent': 'new'})
        self.assertEqual(self.signature(), self.signature(revised))

    def test_text_emotion_id_section_invalidate_audio(self):
        for change in ({'narration': 'Different words.'}, {'id': 2}, {'section': 'assessment'},
                       {'narration': [SpeechUnit(text='Example sentence.', emotion='excited')]}):
            with self.subTest(change=change):
                self.assertNotEqual(self.signature(), self.signature(self.segment.model_copy(update=change)))

    def test_config_and_code_invalidate_audio(self):
        config = copy.deepcopy(self.config)
        config['audio']['narration']['loudness_lufs'] = -18
        self.assertNotEqual(self.signature(), self.signature(config=config))
        self.assertNotEqual(self.signature(), self.signature(code='new'))
        for change in ({'voice': 'baotrang'}, {'provider': 'zerotts'}):
            config = copy.deepcopy(self.config)
            config['tts'].update(change)
            self.assertNotEqual(self.signature(), self.signature(config=config))


if __name__ == '__main__':
    unittest.main()
