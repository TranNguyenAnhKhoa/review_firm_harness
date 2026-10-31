import copy
import hashlib
import json
import unittest

from scripts.measure_review import cache_signatures
from scripts.revise_moana import split_balanced
from src.audio.speech import SpeechUnit
from src.pipeline.schema import ReviewSegment


class MeasurementCacheTests(unittest.TestCase):
    def setUp(self):
        self.segment = ReviewSegment(id=1, narration=[SpeechUnit(text='Example sentence.', emotion='normal')],
                                     source_start=0, source_end=10)
        self.config = {'tts': {'voice': 'test', 'rate': 12}, 'audio': {'narration': {'loudness_lufs': -16}}}

    def signature(self, segment=None, config=None, code='hash'):
        return cache_signatures(segment or self.segment, config or self.config, code, {})[0]

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

    def test_legacy_cache_only_migrates_unchanged_audio_inputs(self):
        payload = {'segment': self.segment.model_dump(), 'tts': self.config['tts'],
                   'loudness': self.config['audio']['narration'], 'code': 'hash'}
        old_key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        visual = self.segment.model_copy(update={'source_start': 10, 'source_end': 20})
        self.assertIn(old_key, cache_signatures(visual, self.config, 'hash', {1:self.segment})[1])
        changed = visual.model_copy(update={'narration': 'New narration.'})
        self.assertNotIn(old_key, cache_signatures(changed, self.config, 'hash', {1:self.segment})[1])

    def test_split_preserves_unit_order_and_text(self):
        units = [SpeechUnit(text='word '*n) for n in (8, 12, 20, 9, 18, 14, 7)]
        groups = split_balanced(units, 4)
        self.assertEqual(len(groups), 4)
        self.assertTrue(all(groups))
        self.assertEqual([u.text for g in groups for u in g], [u.text for u in units])


if __name__ == '__main__': unittest.main()
