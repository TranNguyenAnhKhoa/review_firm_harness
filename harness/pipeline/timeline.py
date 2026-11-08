"""Check a READ result (timeline.md): front matter contract, timestamp tables, coverage.

This checks form, not truth: a timeline that passes still needs a human read (the READ gate).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import yaml

STATUSES = ("complete", "partial", "blocked")
NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")
CLOCK = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2}(?:[.,]\d+)?)$")
START_NAMES = ("source_start", "start", "bắt đầu", "bat dau", "từ", "tu")
END_NAMES = ("source_end", "end", "kết thúc", "ket thuc", "đến", "den")


def _seconds(cell: str) -> float | None:
    value = re.sub(r"[*`_]", "", cell).strip().rstrip("s").strip()
    if NUMBER.match(value):
        return float(value.replace(",", "."))
    match = CLOCK.match(value)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds.replace(",", "."))
    return None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    try:
        data = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        data = {}
    return (data if isinstance(data, dict) else {}), text[end + 4:]


def tables(body: str) -> list[dict]:
    """Every markdown table with a start and an end column, as {header, rows:[{start,end,cells}]}."""
    found, lines, i = [], body.splitlines(), 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.lower() for c in _cells(lines[i])]
            start = next((k for k, h in enumerate(header) if any(n in h for n in START_NAMES)), None)
            end = next((k for k, h in enumerate(header) if any(n in h for n in END_NAMES) and k != start), None)
            rows, j = [], i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = _cells(lines[j])
                if start is not None and end is not None and max(start, end) < len(cells):
                    a, b = _seconds(cells[start]), _seconds(cells[end])
                    if a is not None and b is not None:
                        rows.append({"start": a, "end": b, "cells": cells})
                j += 1
            if rows:
                found.append({"header": _cells(lines[i]), "rows": rows})
            i = j
        else:
            i += 1
    return found


def coverage(intervals: list[tuple[float, float]], duration: float) -> float:
    merged: list[list[float]] = []
    for a, b in sorted((max(0, a), min(duration, b)) for a, b in intervals if b > a):
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return sum(b - a for a, b in merged) / duration if duration > 0 else 0.0


def check(path: str | Path, *, request_id: str | None = None, duration: float | None = None) -> dict:
    """Return {ok, status, errors, warnings, front, rows, clips, coverage}; ok means usable for WRITE."""
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "status": None, "errors": [f"{path.name} chưa có"], "warnings": []}
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    front, body = front_matter(text)
    errors, warnings = [], []
    status = str(front.get("analysis_status", "")).strip().lower() or None
    if not front:
        errors.append("Thiếu YAML front matter (--- request_id / analysis_status / source_duration_seconds ---)")
    elif status not in STATUSES:
        errors.append(f"analysis_status phải là complete, partial hoặc blocked (đang là {status!r})")
    if request_id and front and str(front.get("request_id", "")).strip() != request_id:
        errors.append(f"request_id {front.get('request_id')!r} không khớp yêu cầu {request_id!r} (timeline của job khác?)")
    if duration and front.get("source_duration_seconds") is not None:
        try:
            if abs(float(front["source_duration_seconds"]) - duration) > 1.0:
                errors.append(f"source_duration_seconds {front['source_duration_seconds']} khác thời lượng video {duration:.3f}")
        except (TypeError, ValueError):
            errors.append("source_duration_seconds không phải số")
    found = tables(body)
    rows = [r for t in found for r in t["rows"]]
    bad = [r for r in rows if not (0 <= r["start"] < r["end"]) or (duration and r["end"] > duration + 1.0)]
    for r in bad[:5]:
        errors.append(f"Timestamp sai: {r['start']} - {r['end']} (cần 0 <= start < end <= {duration})")
    timeline_rows = found[0]["rows"] if found else []
    clip_rows = [r for t in found[1:] for r in t["rows"]]
    cover = coverage([(r["start"], r["end"]) for r in timeline_rows], duration) if duration else None
    if not timeline_rows:
        errors.append("Không thấy bảng timeline có cột start/end (giây hoặc mm:ss)")
    elif cover is not None and cover < 0.9 and status == "complete":
        warnings.append(f"Bảng timeline chỉ phủ {cover:.0%} thời lượng nhưng tự khai complete")
    if status == "blocked":
        errors.append("Agent báo blocked: không đọc được video. Xem lý do trong timeline.md")
    elif status == "partial":
        warnings.append("Agent báo partial: còn khoảng chưa phân tích (xem mục I của timeline.md)")
    if len(timeline_rows) and duration and len(timeline_rows) < max(3, duration / 180):
        warnings.append(f"Chỉ {len(timeline_rows)} dòng timeline cho {duration / 60:.0f} phút phim: quá thưa để chọn shot")
    if not clip_rows:
        warnings.append("Không thấy bảng đoạn hình gợi ý (mục E) có start/end")
    return {"ok": not errors, "status": status, "errors": errors, "warnings": warnings, "front": front,
            "rows": len(timeline_rows), "clips": len(clip_rows),
            "coverage": None if cover is None or math.isnan(cover) else round(cover, 4)}
