import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'packages'))
from faster_whisper import WhisperModel

print('Loading local recognition model...', flush=True)
model = WhisperModel('base', device='cpu', compute_type='int8', cpu_threads=6,
                     download_root=str(ROOT / 'models'))
segments, info = model.transcribe(str(ROOT / 'audio.wav'), language='vi',
                                  beam_size=3, word_timestamps=True,
                                  vad_filter=True, condition_on_previous_text=False)
rows = []
for s in segments:
    row = {'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(),
           'avg_logprob': round(s.avg_logprob, 3),
           'words': [{'start':round(w.start,2), 'end':round(w.end,2),
                      'word':w.word, 'probability':round(w.probability,3)} for w in (s.words or [])]}
    rows.append(row)
    print(json.dumps({k:v for k,v in row.items() if k != 'words'}, ensure_ascii=False), flush=True)
result = {'duration': info.duration, 'duration_after_vad': info.duration_after_vad,
          'segments': rows}
(ROOT / 'transcript.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('DONE', flush=True)
