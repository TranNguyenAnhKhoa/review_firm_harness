"""Hard-cut shot planning on a video-frame timeline, driven by measured narration."""
from __future__ import annotations
import math
import tempfile
from pathlib import Path
from harness.schema import ReviewShot
from harness.video.clipper import match_duration, cut_clip


def plan_shots(shots: list[dict], duration: float, fps: float, settings: dict | None = None,
               unit_timings: list[dict] | None = None) -> list[dict]:
    if not shots or not math.isfinite(duration) or duration <= 0 or not math.isfinite(fps) or fps <= 0:
        raise ValueError("Positive measured duration, FPS and at least one shot are required")
    validated = [ReviewShot.model_validate(s) for s in shots]
    total_frames = round(duration * fps)
    if total_frames < len(shots):
        raise ValueError("Not enough video frames for the requested shots")
    if any(s.speech_unit_id is not None for s in validated):
        if not unit_timings:
            raise ValueError('Anchored shots need measured speech-unit timings')
        ids = [u['id'] for u in unit_timings]
        anchors = [s.speech_unit_id for s in validated]
        groups = [a for i,a in enumerate(anchors) if i == 0 or a != anchors[i-1]]
        if groups != ids:
            raise ValueError('Shot anchors must follow and cover measured speech units')
        plans = []
        cursor = 0
        for i, unit_id in enumerate(ids):
            stop = round(unit_timings[i+1]['start']*fps) if i+1 < len(ids) else total_frames
            subset = [s.model_dump(exclude={'speech_unit_id'}) for s in validated if s.speech_unit_id == unit_id]
            chunk = plan_shots(subset,(stop-cursor)/fps,fps,settings)
            for p in chunk:
                p['timeline_start'] += cursor/fps
                p['speech_unit_id'] = unit_id
            plans.extend(chunk)
            cursor = stop
        return plans
    # Reserve one frame per shot; distribute remaining frames using largest remainders.
    weights = [s.weight for s in validated]
    maximum = max(weights)
    weights = [w / maximum for w in weights]
    ideal = [(total_frames - len(shots)) * w / sum(weights) for w in weights]
    frames = [1 + math.floor(n) for n in ideal]
    remaining = total_frames - sum(frames)
    for i in sorted(range(len(shots)), key=lambda i: ideal[i] % 1, reverse=True)[:remaining]:
        frames[i] += 1
    cursor = 0
    plans = []
    for shot, count in zip(validated, frames):
        actual = count / fps
        choice = match_duration(shot.source_start, shot.source_end, actual, settings)
        plans.append({**shot.model_dump(), **choice, 'duration':actual,
                      'timeline_start':cursor / fps, 'frames':count})
        cursor += count
    return plans


def cut_montage(video: str, shots: list[dict], duration: float, output_path: str, *, fps: float,
                unit_timings: list[dict] | None = None, **options) -> Path:
    from harness.video.renderer import concat_clips
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plans = plan_shots(shots, duration, fps, options.get('duration_matching'),unit_timings)
    with tempfile.TemporaryDirectory(prefix='montage-', dir=target.parent) as temp:
        parts = []
        for i, plan in enumerate(plans):
            part = Path(temp) / f'shot_{i:03d}.mp4'
            cut_clip(video, plan['source_start'], plan['source_end'], plan['duration'], str(part), fps=fps, **options)
            parts.append(str(part))
        encoding = {k:options[k] for k in ('codec','crf','preset') if k in options}
        pending = concat_clips(parts, str(Path(temp) / 'montage.mp4'), **encoding)
        pending.replace(target)
    return target
