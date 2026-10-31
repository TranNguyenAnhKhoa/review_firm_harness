"""Export frame-aligned picture and separate narration from verified measured TTS."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.measure_review import cache_signatures
from src.pipeline.build_review import load_config
from src.pipeline.editorial import EditorialPolicy, require_timing
from src.pipeline.schema import ReviewScript
from src.utils import executable, run_command
from src.video.montage import plan_shots
from src.video.probe import probe_video


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def assemble_narration(entries, target, fps):
    """Only pad sub-frame rounding gaps; retain every measured PCM speech sample."""
    elapsed_frames = 0
    with wave.open(str(target), 'wb') as output:
        output.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        for entry in entries:
            stop = round((elapsed_frames + entry['frames']) * 48000 / fps)
            begin = round(elapsed_frames * 48000 / fps)
            with wave.open(str(entry['audio']), 'rb') as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getcomptype()) != (2, 2, 48000, 'NONE'):
                    raise ValueError('Measured narration must be stereo 48 kHz 16-bit PCM')
                count = source.getnframes()
                gap = stop - begin - count
                if gap < 0 or gap > math.ceil(48000 / fps) + 1:
                    raise ValueError('Narration would be truncated or padded beyond one frame')
                output.writeframesraw(source.readframes(count))
                output.writeframesraw(bytes(gap * 4))
            elapsed_frames += entry['frames']


def export(args):
    source, review_path = Path(args.video).resolve(), Path(args.review).resolve()
    measured, output = Path(args.tts_dir).resolve(), Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ('video_cut.mp4', 'narration.wav')):
        raise FileExistsError('Preserve existing handoff files; choose a new output directory')
    config = load_config(args.config)
    review = ReviewScript.load(review_path)
    metadata = probe_video(source)
    report = json.loads((measured / 'review_timing.json').read_text(encoding='utf-8'))
    require_timing(report)
    review_hash, source_hash = digest(review_path), digest(source)
    if report['review_sha256'] != review_hash or abs(report['budget']['source_duration'] - metadata['duration']) > .001:
        raise ValueError('Measured timing belongs to another review or source duration')
    if review.source_video and Path(review.source_video).resolve() != source:
        raise ValueError('Review source path does not match video')
    policy = EditorialPolicy.model_validate(config['editorial'])
    policy.validate_structure(review, metadata['duration'])
    fps = float(config['render'].get('fps') or metadata['fps'])
    audio_code = hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT / 'src/audio').glob('*.py')))).hexdigest()
    entries, cursor_frames = [], 0
    for segment in review.segments:
        if not segment.shots or segment.source_end > metadata['duration'] + .001:
            raise ValueError(f'Segment {segment.id}: real bounded shots are required')
        audio = measured / 'audio' / f'segment_{segment.id:03d}.wav'
        debug_path = measured / 'debug' / f'segment_{segment.id:03d}_tts.json'
        marker = json.loads((measured / 'debug' / f'segment_{segment.id:03d}.cache.json').read_text(encoding='utf-8'))
        expected, _ = cache_signatures(segment, config, audio_code, {})
        if marker['signature'] != expected or marker['audio_sha256'] != digest(audio) or marker['debug_sha256'] != digest(debug_path):
            raise ValueError(f'Segment {segment.id}: stale or changed measured audio')
        debug = json.loads(debug_path.read_text(encoding='utf-8'))
        with wave.open(str(audio), 'rb') as pcm:
            duration = pcm.getnframes() / pcm.getframerate()
        if abs(debug['duration'] - duration) > 1 / 48000 + 1e-6:
            raise ValueError('Measured audio duration mismatch')
        frames = math.ceil(duration * fps - 1e-6)
        plans = plan_shots([s.model_dump() for s in segment.shots], frames / fps, fps,
                           config['video']['duration_matching'], debug['units'])
        if any(p['freeze_duration'] > 1e-6 for p in plans):
            raise ValueError('CapCut export refuses insufficient footage')
        entries.append(dict(id=segment.id, section=segment.section, narration=segment.narration_text,
                            audio=str(audio), audio_sha256=digest(audio), frames=frames,
                            timeline_start=cursor_frames / fps, duration=frames / fps,
                            speech_duration=debug['speech_duration'], units=debug['units'], shots=plans))
        cursor_frames += frames
    timing = policy.timing_report(review, metadata['duration'], [e['speech_duration'] for e in entries],
                                  [e['duration'] for e in entries])
    require_timing(timing)
    working = output / '_work'
    working.mkdir(exist_ok=True)
    signature = hashlib.sha256(json.dumps(dict(source_sha256=source_hash, review_sha256=review_hash,
        entries=entries, fps=fps, exporter_sha256=digest(__file__)), sort_keys=True).encode()).hexdigest()
    manifest = working / 'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())['signature'] != signature:
        raise ValueError('Working directory belongs to different inputs; choose a new directory')
    manifest.write_text(json.dumps(dict(signature=signature), indent=2), encoding='utf-8')
    ffmpeg = executable('ffmpeg', 'FFMPEG_BINARY')

    def render(entry):
        target = working / f"part_{entry['id']:03d}.mkv"
        marker = target.with_suffix('.json')
        if target.exists() and marker.exists() and json.loads(marker.read_text())['sha256'] == digest(target):
            return target
        command = [ffmpeg, '-v', 'error', '-y']
        filters = []
        for i, shot in enumerate(entry['shots']):
            command += ['-threads', '1', '-ss', f"{shot['start']:.9f}", '-t',
                        f"{shot['source_duration']:.9f}", '-i', str(source)]
            filters.append(f"[{i}:v]trim=duration={shot['source_duration']:.9f},"
                f"setpts=(PTS-STARTPTS)/{shot['speed']:.9f},fps={fps},"
                f"tpad=stop_mode=clone:stop_duration={1/fps:.9f},trim=end_frame={shot['frames']},"
                f"setpts=PTS-STARTPTS,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1[v{i}]")
        filters.append(''.join(f'[v{i}]' for i in range(len(entry['shots']))) +
                       f"concat=n={len(entry['shots'])}:v=1:a=0[v]")
        pending = target.with_suffix('.pending.mkv')
        command += ['-filter_complex_threads', '1', '-filter_complex', ';'.join(filters), '-map', '[v]',
                    '-an', '-frames:v', str(entry['frames']), '-c:v', 'libx264', '-crf', '20',
                    '-preset', 'veryfast', '-threads', '2', '-pix_fmt', 'yuv420p', str(pending)]
        run_command(command)
        actual = probe_video(pending)
        if abs(actual['duration'] - entry['duration']) > .003 or actual['audio_codec']:
            raise RuntimeError(f'Unexpected picture duration: {actual}')
        pending.replace(target)
        marker.write_text(json.dumps(dict(sha256=digest(target))), encoding='utf-8')
        return target

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(render, e): e for e in entries}
        for i, future in enumerate(as_completed(futures), 1):
            future.result()
            print(f"Picture {i}/{len(entries)}: segment {futures[future]['id']}", flush=True)
    listing = working / 'concat.txt'
    # MKV timestamps have millisecond precision. Explicit durations prevent
    # their rounding errors from accumulating across the concatenated parts.
    listing.write_text(''.join("file '" + (working / f"part_{e['id']:03d}.mkv").as_posix().replace("'", "'\\''") +
                              f"'\nduration {e['duration']:.9f}\n" for e in entries), encoding='utf-8')
    video_pending = output / 'video_cut.pending.mp4'
    voice_pending = output / 'narration.pending.wav'
    frame_rate = Fraction(str(fps)).limit_denominator(1000000)
    packet_clock = (f'setts=pts=round(PTS*TB*{fps}):dts=round(DTS*TB*{fps}):'
                    f'duration=1:time_base={frame_rate.denominator}/{frame_rate.numerator}')
    run_command([ffmpeg, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
                 '-map', '0:v:0', '-c:v', 'copy', '-an', '-r', str(fps),
                 '-bsf:v', packet_clock,
                 '-video_track_timescale', '90000', '-movflags', '+faststart', str(video_pending)])
    assemble_narration(entries, voice_pending, fps)
    actual = probe_video(video_pending)
    duration = cursor_frames / fps
    if abs(actual['duration'] - duration) > 1 / 48000 + 1e-6:
        raise RuntimeError('Final picture does not match narration timeline')
    run_command([ffmpeg, '-v', 'error', '-xerror', '-threads', '2', '-i', str(video_pending), '-f', 'null', '-'])
    run_command([ffmpeg, '-v', 'error', '-xerror', '-i', str(voice_pending), '-f', 'null', '-'])
    if digest(source) != source_hash or digest(review_path) != review_hash or any(digest(e['audio']) != e['audio_sha256'] for e in entries):
        raise RuntimeError('Inputs changed during export')
    video_pending.replace(output / 'video_cut.mp4')
    voice_pending.replace(output / 'narration.wav')
    with (output / 'timing.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['segment', 'section', 'start_seconds', 'end_seconds', 'narration'])
        for e in entries:
            writer.writerow([e['id'], e['section'], f"{e['timeline_start']:.6f}",
                             f"{e['timeline_start']+e['duration']:.6f}", e['narration']])
    (output / 'review.json').write_bytes(review_path.read_bytes())
    timing.update(rendered=True, full_decode_passed=True, export_type='capcut_separate_tracks',
        source_sha256=source_hash, review_sha256=review_hash, duration=duration, fps=fps,
        video_sha256=digest(output / 'video_cut.mp4'), narration_sha256=digest(output / 'narration.wav'),
        shot_count=sum(len(e['shots']) for e in entries), editorial_status='human picture/audio review required')
    (output / 'review_timing.json').write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'edl.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'CapCut export PASS: {duration:.3f}s; {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('video', 'review', 'tts-dir', 'output-dir'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--config', default=str(ROOT / 'config/config.yaml'))
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    export(parser.parse_args())
