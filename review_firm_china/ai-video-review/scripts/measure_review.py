"""Resumable TTS-only editorial measurement; never renders or pads to meet quota."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import logging
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audio.narration_builder import NarrationBuilder
from src.pipeline.build_review import load_config
from src.pipeline.editorial import EditorialPolicy, require_timing
from src.pipeline.schema import ReviewScript
from src.video.probe import probe_audio, probe_video


def audio_input(segment) -> dict:
    """Visual edits cannot change synthesized audio; text, section and seed ID can."""
    return {'id': segment.id, 'section': segment.section, 'narration': segment.model_dump()['narration']}


def cache_signatures(segment, config: dict, code_hash: str, prior: dict) -> tuple[str, set[str]]:
    def digest(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    common = {'tts': config['tts'], 'loudness': config['audio']['narration'], 'code': code_hash}
    signature = digest({'segment': audio_input(segment), **common})
    allowed = {signature}
    if segment.id in prior and audio_input(prior[segment.id]) == audio_input(segment):
        allowed.add(digest({'segment': prior[segment.id].model_dump(), **common}))
    return signature, allowed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--config', default=str(ROOT / 'config/config.yaml'))
    parser.add_argument('--workers', type=int, choices=(1, 2, 3), default=2)
    parser.add_argument('--ids', type=int, nargs='+', help='Measure a subset only; does not certify the whole review')
    parser.add_argument('--reuse-review', help='Previous review for strictly verified migration of legacy audio cache')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    review = ReviewScript.load(args.review)
    review_hash = hashlib.sha256(Path(args.review).read_bytes()).hexdigest()
    prior = {s.id: s for s in ReviewScript.load(args.reuse_review).segments} if args.reuse_review else {}
    config = load_config(args.config)
    metadata = probe_video(args.video)
    policy = EditorialPolicy.model_validate(config['editorial'])
    policy.validate_structure(review, metadata['duration'])
    if any(s.source_end > metadata['duration'] + .001 for s in review.segments):
        raise ValueError('Source range exceeds source video')
    if review.source_video and Path(review.source_video).resolve() != Path(args.video).resolve():
        raise ValueError('Review source differs from supplied video')
    selected = [s for s in review.segments if args.ids is None or s.id in args.ids]
    if args.ids and set(args.ids) != {s.id for s in selected}:
        raise ValueError('Unknown segment ID')
    root = Path(args.output_dir)
    for name in ('audio', 'debug', 'cache'):
        (root / name).mkdir(parents=True, exist_ok=True)
    code_hash = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'src/audio').glob('*.py')))).hexdigest()

    def measure(segment):
        audio = root / 'audio' / f'segment_{segment.id:03d}.wav'
        debug = root / 'debug' / f'segment_{segment.id:03d}_tts.json'
        marker = root / 'debug' / f'segment_{segment.id:03d}.cache.json'
        signature, signatures = cache_signatures(segment, config, code_hash, prior)
        if marker.exists() and audio.exists() and debug.exists():
            cached = json.loads(marker.read_text(encoding='utf-8'))
            if (cached['signature'] in signatures and cached['audio_sha256'] == hashlib.sha256(audio.read_bytes()).hexdigest()
                    and cached['debug_sha256'] == hashlib.sha256(debug.read_bytes()).hexdigest()):
                record = json.loads(debug.read_text(encoding='utf-8'))
                if abs(probe_audio(audio) - record['duration']) < .001:
                    cached['signature'] = signature
                    marker.write_text(json.dumps(cached, indent=2), encoding='utf-8')
                    print(f'[CACHE] Segment {segment.id}: {record["duration"]:.3f}s', flush=True)
                    return record
        # Per-segment silence cache avoids parallel writers touching the same WAV.
        builder = NarrationBuilder(config['tts'], config['audio']['narration'],
                                   cache_dir=root/'cache'/f'segment_{segment.id:03d}')
        builder.build(segment.narration, audio, segment_id=segment.id,
                      section=segment.section, debug_path=debug)
        marker.write_text(json.dumps({'signature': signature,
            'audio_sha256': hashlib.sha256(audio.read_bytes()).hexdigest(),
            'debug_sha256': hashlib.sha256(debug.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
        return json.loads(debug.read_text(encoding='utf-8'))

    completed, errors = {}, {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(measure, s): s for s in selected}
        for future in as_completed(pending):
            segment = pending[future]
            try:
                completed[segment.id] = future.result()
                print(f'[PROGRESS] {len(completed)}/{len(selected)} complete', flush=True)
            except Exception as error:
                errors[segment.id] = str(error)
                print(f'[FAILED] Segment {segment.id}: {error}', flush=True)
                for other in pending:
                    other.cancel()
            (root/'measurement_progress.json').write_text(json.dumps({
                'review': str(Path(args.review).resolve()), 'completed_ids': sorted(completed),
                'errors': errors, 'selected_count': len(selected), 'total_count': len(review.segments)
            }, indent=2, ensure_ascii=False), encoding='utf-8')
    if errors:
        raise RuntimeError('TTS measurement incomplete; inspect measurement_progress.json. Rerun to reuse verified audio.')
    if args.ids is not None:
        print('Subset measured; no whole-review timing claim.', flush=True)
        return 0
    if hashlib.sha256(Path(args.review).read_bytes()).hexdigest() != review_hash:
        raise RuntimeError('Review changed during measurement; rerun using verified cache before certifying timing')
    fps = float(config['render'].get('fps') or metadata['fps'])
    records = [completed[s.id] for s in review.segments]
    report = policy.timing_report(review, metadata['duration'], [r['speech_duration'] for r in records],
        [math.ceil(r['duration']*fps-1e-6)/fps for r in records])
    report.update(review_sha256=review_hash,
                  measurement_only=True, rendered=False)
    destination = root/'review_timing.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Measured: {report["review_duration"]:.3f}s ({report["source_ratio"]:.2%}); report: {destination}', flush=True)
    require_timing(report)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f'Measurement failed: {error}')
