"""Validate a WRITE result (review.json) and estimate its spoken length before any TTS runs.

Errors block the pipeline; warnings show in the dashboard. The estimate uses the voice's target
speaking rate, so it is only a forecast: MEASURE (real TTS) decides.
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

from pydantic import ValidationError

from harness.editorial import EditorialPolicy
from harness.schema import ReviewScript

PAUSE_PER_UNIT = 0.12   # seconds of preset pause per speech unit, on average


def _tokens(text: str) -> int:
    return sum(any(c.isalnum() for c in word) for word in text.split())


def _pydantic_errors(error: ValidationError) -> list[str]:
    out = []
    for item in error.errors()[:12]:
        where = ".".join(str(p) for p in item.get("loc", ()))
        out.append(f"{where}: {item.get('msg')}")
    return out


def check(path: str | Path, config: dict, duration: float, scenes: list[dict] | None = None) -> dict:
    path = Path(path)
    result = {"ok": False, "errors": [], "warnings": [], "segments": 0}
    if not path.is_file():
        result["errors"].append(f"{path.name} chưa có")
        return result
    try:
        review = ReviewScript.load(path)
    except ValidationError as error:
        result["errors"] += _pydantic_errors(error)
        return result
    except ValueError as error:
        result["errors"].append(f"JSON không hợp lệ: {error}")
        return result
    policy = EditorialPolicy.model_validate(config["editorial"])
    result["errors"] += policy.structure_errors(review, duration)
    rate = float(config["tts"]["target_speech"]["target_syllables_per_second"])
    cuts = sorted(s["start"] for s in scenes or [] if s.get("start", 0) > 0)
    per_segment, total, shots_total, units_total, crossing = [], 0.0, 0, 0, 0
    for segment in review.segments:
        if segment.source_end > duration + 0.001:
            result["errors"].append(f"Segment {segment.id}: source_end {segment.source_end} vượt thời lượng {duration:.3f}")
        units = segment.narration if isinstance(segment.narration, list) else None
        tokens = _tokens(segment.narration_text)
        estimate = tokens / rate + PAUSE_PER_UNIT * (len(units) if units else max(1, tokens // 18))
        footage = sum(s.source_end - s.source_start for s in segment.shots) or (segment.source_end - segment.source_start)
        if footage < estimate * 1.05:
            result["warnings"].append(f"Segment {segment.id}: footage {footage:.1f}s ngắn hơn lời đọc ước tính {estimate:.1f}s")
        for shot in segment.shots:
            i = bisect.bisect_right(cuts, shot.source_start + 0.05)
            if i < len(cuts) and cuts[i] < shot.source_end - 0.05:
                crossing += 1
        if not segment.shots:
            result["warnings"].append(f"Segment {segment.id}: không có shots (dựng một khoảng hình liền, không theo mẫu 1004)")
        shots_total += len(segment.shots)
        units_total += len(units) if units else 0
        total += estimate
        per_segment.append({"id": segment.id, "section": segment.section, "tokens": tokens,
                            "estimate_seconds": round(estimate, 2), "shots": len(segment.shots),
                            "footage_seconds": round(footage, 2)})
    budget = policy.budget(duration)
    assessment = per_segment[-1]["estimate_seconds"] if per_segment and per_segment[-1]["section"] == "assessment" else None
    if not budget["total_min"] * 0.92 <= total <= budget["total_max"] * 1.05:
        result["warnings"].append(f"Ước tính {total:.0f}s ({total / duration:.0%} nguồn) lệch ngân sách "
                                  f"{budget['total_min']:.0f}-{budget['total_max']:.0f}s; MEASURE sẽ đo thật")
    if assessment is not None and not 9 <= assessment <= 21:
        result["warnings"].append(f"Đánh giá cuối ước tính {assessment:.1f}s (cần 10-20s khi đọc)")
    if crossing:
        result["warnings"].append(f"{crossing} shot vắt qua điểm cắt cảnh (hình sẽ nhảy giữa shot)")
    result.update(ok=not result["errors"], segments=len(review.segments), units=units_total, shots=shots_total,
                  estimate_seconds=round(total, 1), estimate_ratio=round(total / duration, 4),
                  assessment_estimate=assessment, budget=budget, per_segment=per_segment, title=review.title)
    return result


def format_report(result: dict) -> str:
    lines = []
    if result.get("segments"):
        lines.append(f"{result['segments']} segment, {result.get('units', 0)} unit, {result.get('shots', 0)} shot; "
                     f"ước tính {result['estimate_seconds']:.0f}s = {result['estimate_ratio']:.1%} nguồn "
                     f"(cần {result['budget']['total_min']:.0f}-{result['budget']['total_max']:.0f}s, "
                     f"mục tiêu {result['budget']['total_target']:.0f}s); đánh giá cuối ~{result.get('assessment_estimate') or 0:.1f}s")
    lines += [f"LỖI: {e}" for e in result["errors"]]
    lines += [f"Cảnh báo: {w}" for w in result["warnings"]]
    lines.append("OK" if result["ok"] else "CHƯA ĐẠT")
    return "\n".join(lines)


def load_scenes(path: Path | None) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path and path.is_file() else []
    except (OSError, ValueError):
        return []
