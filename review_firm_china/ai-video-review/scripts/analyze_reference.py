"""Measure reference shot cuts, picture bounds and transcript cadence locally."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import cv2
import numpy as np
from scenedetect import open_video, SceneManager, ContentDetector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def analyze(video: Path, transcript: Path | None) -> dict:
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    width, height = int(capture.get(3)), int(capture.get(4))
    bounds = []
    for t in np.linspace(1, duration - 1, 40):
        capture.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = capture.read()
        if not ok:
            continue
        light = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        active = np.flatnonzero((light > 12).mean(axis=1) > .15)
        if len(active):
            bounds.append([int(active[0]), int(height - 1 - active[-1])])
    capture.release()
    stream = open_video(str(video))
    manager = SceneManager()
    manager.auto_downscale = False
    manager.downscale = 6
    manager.add_detector(ContentDetector(threshold=24, min_scene_len=6))
    manager.detect_scenes(stream)
    scenes = [{'start':a.seconds, 'end':b.seconds,
               'duration':(b-a).seconds} for a,b in manager.get_scene_list(start_in_scene=True)]
    result = {'reference':str(video), 'duration':duration, 'width':width, 'height':height, 'fps':fps,
              'letterbox_median_px':np.median(bounds, axis=0).tolist(),
              'detected_shot_count':len(scenes), 'shots':scenes,
              'shot_duration_percentiles':np.percentile([s['duration'] for s in scenes],[10,50,90]).tolist(),
              'notes':['Cuts are detector estimates, not an original edit project.',
                       'Cadence uses ASR text/timestamps; no direct audio listening or stem balance verification.']}
    if transcript:
        data = json.loads(transcript.read_text(encoding='utf-8'))
        rows = data['segments']
        tokens = sum(len(s['text'].split()) for s in rows)
        gaps = [b['start']-a['end'] for a,b in zip(rows,rows[1:]) if b['start']-a['end'] > .05]
        speech = sum(s['end']-s['start'] for s in rows)
        result['cadence'] = {'approx_syllables':tokens, 'syllables_per_second_overall':tokens/duration,
                             'syllables_per_second_in_segments':tokens/speech,
                             'median_segment_gap_seconds':float(np.median(gaps))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--transcript', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'data/reference/1004.analysis.json')
    args = parser.parse_args()
    data = analyze(args.video, args.transcript)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in data.items() if k!='shots'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
