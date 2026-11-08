"""The six pipeline stages. Each takes a StageContext and returns metrics for state.json.

    probe    ffprobe the source, compute the 40-50 % budget
    read     agent (or you) writes 02_read/timeline.md from proxy chunks / frame sheets   [gate]
    write    agent (or you) writes 03_write/review.json from the approved timeline       [gate]
    measure  ZeroTTS speaks every segment; the real durations must pass the editorial rules
    render   montage + voice mix per segment (parallel, cached per part), then concat
    qc       metadata + full decode check, then publish jobs/<job>/final_review.mp4

A stage raises StageError (failed), NeedsInput (waiting for a manual file) or TimingFailed
(measure: the runner may hand the report back to WRITE for a revision).
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from harness import ROOT
from harness.editorial import EditorialPolicy, require_timing
from harness.pipeline import materials as mat
from harness.pipeline import review_check, timeline as tl
from harness.pipeline.agents import run_agent
from harness.pipeline.job import Job, file_signature
from harness.schema import ReviewScript
from harness.utils import (ffmpeg, format_seconds, now_iso, read_json, run_command, sha256_file, sha256_text,
                           write_json)


class StageError(RuntimeError):
    pass


class NeedsInput(RuntimeError):
    """A manual step: the stage waits until a file is supplied (dashboard upload or CLI import)."""


class TimingFailed(StageError):
    def __init__(self, message: str, report: dict):
        super().__init__(message)
        self.report = report


@dataclass
class StageContext:
    job: Job
    config: dict
    log: Callable[[str], None] = print
    force: bool = False
    stop: threading.Event = field(default_factory=threading.Event)
    revision: dict | None = None      # measure report handed to WRITE for an automatic revision

    def progress(self, stage: str, **metrics) -> None:
        self.job.update_stage(stage, metrics=metrics)

    def check_stop(self) -> None:
        if self.stop.is_set():
            raise StageError("Đã dừng theo yêu cầu")


def _template(name: str, values: dict) -> str:
    text = (ROOT / "prompts" / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def _metadata(ctx: StageContext) -> dict:
    data = read_json(ctx.job.stage_dir("probe") / "metadata.json")
    if not data:
        raise StageError("Chưa có metadata: chạy bước probe trước")
    return data


def _budget(ctx: StageContext) -> dict:
    return read_json(ctx.job.stage_dir("probe") / "budget.json") or EditorialPolicy.model_validate(
        ctx.config["editorial"]).budget(_metadata(ctx)["duration"])


def _request_id(job: Job) -> str:
    return f"{job.slug}-{sha256_text(json.dumps(job.manifest()['source'], sort_keys=True))[:12]}"


def _backup(path: Path) -> None:
    if path.is_file():
        history = path.parent / "history"
        history.mkdir(exist_ok=True)
        shutil.copy2(path, history / f"{path.stem}.{now_iso().replace(':', '')}{path.suffix}")


def _reviewer_note(job: Job, stage: str) -> str:
    gate = job.state()["gates"].get(stage) or {}
    if gate and not gate.get("approved") and gate.get("note"):
        return f"\n## Yêu cầu của người duyệt lần trước\n\n{gate['note']}\n\nSửa theo yêu cầu này.\n"
    return ""


def _usage(results: list) -> dict:
    usage = {"agent_seconds": 0.0, "cost_usd": 0.0, "tokens": 0, "calls": 0}
    for r in results:
        usage["agent_seconds"] += r.seconds
        usage["cost_usd"] += r.cost_usd or 0
        usage["tokens"] += int(r.usage.get("total_tokens") or 0)   # cache reads are not counted
        usage["calls"] += 1
    usage["agent_seconds"] = round(usage["agent_seconds"], 1)
    usage["cost_usd"] = round(usage["cost_usd"], 4)
    return usage


# ---- 1. probe -------------------------------------------------------------------------------------------
def probe(ctx: StageContext) -> dict:
    from harness.video.probe import probe_video
    source = ctx.job.source
    if not source.is_file():
        raise StageError(f"Không thấy video nguồn: {source}")
    recorded = ctx.job.manifest()["source"]
    stat = source.stat()
    if (stat.st_size, stat.st_mtime_ns) != (recorded.get("size"), recorded.get("mtime_ns")):
        ctx.log("Cảnh báo: video nguồn đã đổi kích thước/thời gian sửa so với lúc tạo job")
    ctx.log(f"ffprobe {source.name}")
    metadata = probe_video(source)
    if not metadata["duration"]:
        raise StageError("Không đọc được thời lượng video")
    policy = EditorialPolicy.model_validate(ctx.config["editorial"])
    budget = policy.budget(metadata["duration"])
    folder = ctx.job.stage_dir("probe")
    write_json(folder / "metadata.json", {**metadata, "source": str(source), "size": stat.st_size})
    write_json(folder / "budget.json", budget)
    ctx.log(f"{metadata['width']}x{metadata['height']} {metadata['fps']} fps, {format_seconds(metadata['duration'])}; "
            f"review {budget['total_min']:.0f}-{budget['total_max']:.0f}s, mục tiêu {budget['total_target']:.0f}s")
    return {"duration": metadata["duration"], "width": metadata["width"], "height": metadata["height"],
            "fps": metadata["fps"], "video_codec": metadata["video_codec"], "audio_codec": metadata["audio_codec"],
            "total_min": round(budget["total_min"], 1), "total_max": round(budget["total_max"], 1),
            "total_target": round(budget["total_target"], 1)}


# ---- 2. read --------------------------------------------------------------------------------------------
def _materials_text(job: Job, manifest: dict) -> str:
    lines = []
    if manifest.get("proxy"):
        lines.append("Video proxy (xem lần lượt, đủ hết):")
        lines += [f"- {job.root / p['file']}  (nguồn {p['start']:.0f}-{p['end']:.0f}s)" for p in manifest["proxy"]]
    if manifest.get("sheets"):
        lines.append(f"Sheet khung hình, mỗi ô cách nhau {manifest['frame_interval']:g}s (xem lần lượt, đủ hết):")
        lines += [f"- {job.root / s['file']}  (nguồn {s['start']:.0f}-{s['end']:.0f}s)" for s in manifest["sheets"]]
    if manifest.get("strip_sheets"):
        lines.append("Sheet dải phụ đề cứng (cột trái ghi khoảng giây nguồn):")
        lines += [f"- {job.root / s['file']}  ({s['start']:.0f}-{s['end']:.0f}s)" for s in manifest["strip_sheets"]]
    if manifest.get("scenes"):
        lines.append(f"Điểm cắt cảnh ({manifest['scene_count']} cảnh, JSON start/end giây): {job.root / manifest['scenes']}")
    if manifest.get("transcript"):
        lines.append(f"Transcript Whisper (máy nghe, có thể sai): {job.root / manifest['transcript']}")
    return "\n".join(lines)


AGY_TOOLS = ("Chỉ dùng các tool đọc/ghi file (read_file, view_file, list_dir, write_to_file, replace_file_content). "
             "KHÔNG gọi run_command hay bất kỳ lệnh shell nào (kể cả ls, ffprobe): phiên chạy nền không có quyền "
             "shell, gọi là bị dừng ngay và mất hết kết quả. Mọi đường dẫn cần dùng đã có sẵn trong yêu cầu này.")


def _worth_retry(result) -> bool:
    """Retry a session that ended early because of a tool refusal, not one that cannot start (login, missing CLI)."""
    text = f"{result.error} {result.text}".lower()
    return not any(k in text for k in ("authenticate", "auth login", "not logged", "unauthorized", "not found"))


def _denied_retry(prompt: str, result) -> str:
    """Prompt for one more attempt after the agent stopped without writing its file."""
    reason = (f"bị chặn tool {', '.join(map(str, result.denied))}" if result.denied else (result.error or "không rõ lý do"))
    return (f"LẦN TRƯỚC PHIÊN DỪNG MÀ CHƯA GHI FILE ({reason}). Không dùng lệnh shell hay tool bị chặn; chỉ đọc file "
            f"đã nêu và ghi đúng file kết quả.\n\n{prompt}")


ENGINE_READ = {
    "agy": ("Mở từng file proxy bằng read_file để xem hình và nghe tiếng. Góc trái trên mỗi khung có timecode "
            "NGUỒN (hh:mm:ss.mmm và số giây): mọi thời gian trong timeline phải lấy theo timecode đó, "
            "không dùng thời gian bên trong file proxy. Xem đủ mọi proxy trước khi ghi file.\n\n" + AGY_TOOLS),
    "claude": ("Bạn không nghe được âm thanh. Đọc lần lượt mọi sheet khung hình (mỗi ô ghi thời điểm nguồn) và mọi "
               "sheet phụ đề (thoại lấy từ phụ đề đọc được; transcript nếu có). Cần xem rõ một thời điểm thì chạy "
               "`./run.sh frame {job} <giây> [<giây> ...]` rồi Read các file ảnh nó in ra. Không suy ra thoại "
               "khi không đọc được chữ: ghi là không rõ."),
}
ENGINE_READ["codex"] = ENGINE_READ["claude"]


def read(ctx: StageContext) -> dict:
    job, conf = ctx.job, ctx.config["agents"]["read"]
    metadata, budget = _metadata(ctx), _budget(ctx)
    engine = conf["engine"]
    request_id = _request_id(job)
    folder = job.stage_dir("read")
    folder.mkdir(parents=True, exist_ok=True)
    duration = metadata["duration"]
    manifest = {"proxy": [], "sheets": [], "strip_sheets": [], "scenes": None}
    if engine != "manual":
        manifest = mat.build(job, metadata, ctx.config["read"], engine=engine, log=ctx.log, force=ctx.force)
    target_seconds = budget["story_target"]
    values = {
        "job": job.slug, "title": job.title, "request_id": request_id, "source_name": job.source.name,
        "duration": f"{duration:.3f}", "duration_hms": format_seconds(duration), "width": metadata["width"],
        "height": metadata["height"], "fps": metadata["fps"], "output_file": job.timeline,
        "materials": _materials_text(job, manifest) or "(chế độ thủ công: tải video lên công cụ bạn dùng)",
        "engine_instructions": ENGINE_READ.get(engine, "").replace("{job}", job.slug),
        "total_min": f"{budget['total_min']:.0f}", "total_max": f"{budget['total_max']:.0f}",
        "total_target": f"{budget['total_target']:.0f}", "story_target": f"{target_seconds:.0f}",
        "story_words": f"{target_seconds * 5.4:.0f}", "min_rows": max(8, round(duration / 120)),
        "min_shots": max(20, round(budget["total_target"] / 3)),
        "reviewer_note": _reviewer_note(job, "read"),
    }
    prompt = _template("read.md", values)
    (folder / "request.md").write_text(prompt, encoding="utf-8")
    write_json(folder / "request.json", {"request_id": request_id, "engine": engine, "created": now_iso()})

    if engine == "manual":
        result = tl.check(job.timeline, request_id=request_id, duration=duration)
        if not result["ok"]:
            raise NeedsInput("Chờ timeline.md: dùng prompt 02_read/request.md với công cụ bạn chọn, rồi dán/tải "
                             "kết quả trong dashboard (hoặc ./run.sh import " + job.slug + " timeline <file>)")
        return _read_metrics(result, [])

    _backup(job.timeline)
    job.timeline.unlink(missing_ok=True)
    runs = []
    for attempt in range(2):   # one correction round for contract errors (front matter, tables)
        ctx.check_stop()
        runs.append(run_agent(engine, prompt, settings=ctx.config["agents"], model=conf.get("model") or "",
                              effort=conf.get("effort") or "", job_root=job.root,
                              log_path=folder / f"agent_{attempt + 1}.jsonl",
                              timeout_minutes=float(conf.get("timeout_minutes", 90)), echo=ctx.log))
        ctx.progress("read", usage=_usage(runs))
        result = tl.check(job.timeline, request_id=request_id, duration=duration)
        if not job.timeline.is_file():
            if attempt == 0 and _worth_retry(runs[-1]):
                ctx.log("Agent dừng mà chưa ghi timeline.md, thử lại một lần")
                prompt = _denied_retry(prompt, runs[-1])
                continue
            break
        if result["ok"] or result["status"] == "blocked":
            break
        ctx.log("timeline.md chưa đạt hợp đồng, yêu cầu agent sửa: " + "; ".join(result["errors"]))
        prompt = (f"File {job.timeline} bạn vừa ghi chưa đạt kiểm tra tự động:\n- " + "\n- ".join(result["errors"])
                  + f"\n\nSửa đúng file đó theo yêu cầu gốc dưới đây (giữ nội dung đúng, chỉ sửa phần sai).\n\n{prompt}")
    if not job.timeline.is_file():
        raise StageError(f"Agent không ghi {job.timeline.name}. "
                         + (f"Bị chặn tool: {runs[-1].denied}. " if runs[-1].denied else "")
                         + (runs[-1].error or runs[-1].text[:300]))
    for warning in result["warnings"]:
        ctx.log("Cảnh báo: " + warning)
    if not result["ok"]:
        raise StageError("timeline.md chưa đạt: " + "; ".join(result["errors"]))
    return _read_metrics(result, runs)


def _read_metrics(result: dict, runs: list) -> dict:
    return {"analysis_status": result["status"], "rows": result["rows"], "clips": result["clips"],
            "coverage": result["coverage"], "warnings": result["warnings"], "usage": _usage(runs)}


# ---- 3. write -------------------------------------------------------------------------------------------
def write(ctx: StageContext) -> dict:
    job, conf = ctx.job, ctx.config["agents"]["write"]
    if "read" in ctx.config.get("gates", []) and not job.gate_ok("read"):
        raise StageError("READ chưa được duyệt (hoặc timeline.md đã sửa sau khi duyệt): duyệt bước READ trước")
    if not job.timeline.is_file():
        raise StageError("Chưa có timeline.md")
    metadata, budget = _metadata(ctx), _budget(ctx)
    duration = metadata["duration"]
    engine = conf["engine"]
    folder = job.stage_dir("write")
    folder.mkdir(parents=True, exist_ok=True)
    scenes_path = job.stage_dir("read") / "materials" / "scenes.json"
    scenes = review_check.load_scenes(scenes_path)
    revision = ""
    if ctx.revision:
        report_copy = folder / "revise_report.json"
        write_json(report_copy, ctx.revision)
        revision = ("\n## Sửa theo số đo giọng đọc thật\n\n"
                    f"Bản hiện tại ({job.review}) đã được đọc bằng TTS và CHƯA đạt:\n- "
                    + "\n- ".join(ctx.revision.get("errors", []))
                    + f"\n\nSố đo từng segment (giây đọc thật): {report_copy}\n"
                    f"Tổng đo được {ctx.revision.get('review_duration', 0):.1f}s; cần "
                    f"{budget['total_min']:.0f}-{budget['total_max']:.0f}s (mục tiêu {budget['total_target']:.0f}s). "
                    "Sửa file đó tại chỗ: thiếu thì thêm câu kể có căn cứ vào các segment, dư thì bỏ ý lặp; "
                    "đánh giá cuối phải đọc 10-20 giây. Giữ id segment/unit đã có khi không cần đổi, "
                    "chỉnh shots cho khớp unit mới. Không thêm khoảng lặng.\n")
    self_check = f"\n{AGY_TOOLS}\n" if engine == "agy" else ""
    if engine == "claude":
        self_check = (f"\nTự kiểm tra trước khi kết thúc: chạy `./run.sh check {job.slug}` (in lỗi, cảnh báo và ước tính "
                      "giây theo tốc độ đọc), sửa đến khi in OK và ước tính nằm trong ngân sách.\n")
    values = {
        "job": job.slug, "title": job.title, "output_file": job.review, "timeline": job.timeline,
        "guidelines": ROOT / "docs" / "editorial-guidelines.md", "example": ROOT / "examples" / "review.anchored.example.json",
        "scenes": scenes_path if scenes else "(không có)", "duration": f"{duration:.3f}",
        "total_min": f"{budget['total_min']:.0f}", "total_max": f"{budget['total_max']:.0f}",
        "total_target": f"{budget['total_target']:.0f}", "story_target": f"{budget['story_target']:.0f}",
        "story_words": f"{budget['story_target'] * 5.4:.0f}", "self_check": self_check,
        "reviewer_note": _reviewer_note(job, "write"), "revision": revision,
    }
    prompt = _template("write.md", values)
    (folder / "request.md").write_text(prompt, encoding="utf-8")

    if engine == "manual":
        result = review_check.check(job.review, ctx.config, duration, scenes)
        if not result["ok"]:
            raise NeedsInput("Chờ review.json: dùng prompt 03_write/request.md, rồi dán/tải kết quả trong dashboard "
                             f"(hoặc ./run.sh import {job.slug} review <file>)")
        return _write_metrics(result, [])

    _backup(job.review)
    if not ctx.revision:
        job.review.unlink(missing_ok=True)
    runs = []
    for attempt in range(int(conf.get("fix_rounds", 2)) + 1):
        ctx.check_stop()
        runs.append(run_agent(engine, prompt, settings=ctx.config["agents"], model=conf.get("model") or "",
                              effort=conf.get("effort") or "", job_root=job.root,
                              log_path=folder / f"agent_{len(list(folder.glob('agent_*.jsonl'))) + 1}.jsonl",
                              timeout_minutes=float(conf.get("timeout_minutes", 60)), echo=ctx.log))
        ctx.progress("write", usage=_usage(runs))
        result = review_check.check(job.review, ctx.config, duration, scenes)
        write_json(folder / "check.json", result)
        if result["ok"]:
            break
        if not job.review.is_file():
            if attempt == 0 and _worth_retry(runs[-1]):
                ctx.log("Agent dừng mà chưa ghi review.json, thử lại một lần")
                prompt = _denied_retry(prompt, runs[-1])
                continue
            raise StageError(f"Agent không ghi review.json. {runs[-1].error or runs[-1].text[:300]}")
        ctx.log("review.json chưa đạt, yêu cầu agent sửa: " + "; ".join(result["errors"][:6]))
        prompt = (f"File {job.review} chưa đạt kiểm tra tự động:\n- " + "\n- ".join(result["errors"])
                  + f"\n\nSửa đúng file đó (giữ nội dung đúng, chỉ sửa phần sai). Yêu cầu gốc:\n\n{prompt}")
    for warning in result["warnings"]:
        ctx.log("Cảnh báo: " + warning)
    if not result["ok"]:
        raise StageError("review.json chưa đạt: " + "; ".join(result["errors"][:6]))
    return _write_metrics(result, runs)


def _write_metrics(result: dict, runs: list) -> dict:
    return {"segments": result["segments"], "units": result.get("units"), "shots": result.get("shots"),
            "estimate_seconds": result.get("estimate_seconds"), "estimate_ratio": result.get("estimate_ratio"),
            "assessment_estimate": result.get("assessment_estimate"), "warnings": result["warnings"],
            "title": result.get("title"), "usage": _usage(runs)}


# ---- 4. measure -----------------------------------------------------------------------------------------
def _audio_code_hash() -> str:
    return hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "harness/audio").glob("*.py")))).hexdigest()


def audio_input(segment) -> dict:
    """Visual edits cannot change synthesized audio; text, section and ID can."""
    return {"id": segment.id, "section": segment.section, "narration": segment.model_dump()["narration"]}


def cache_signature(segment, config: dict, code_hash: str) -> str:
    payload = {"segment": audio_input(segment), "tts": config["tts"], "loudness": config["audio"]["narration"],
               "code": code_hash}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def measure(ctx: StageContext) -> dict:
    from harness.audio.narration_builder import NarrationBuilder
    from harness.video.probe import probe_audio
    job, config = ctx.job, ctx.config
    if "write" in config.get("gates", []) and not job.gate_ok("write"):
        raise StageError("WRITE chưa được duyệt (hoặc review.json đã sửa sau khi duyệt): duyệt bước WRITE trước")
    metadata = _metadata(ctx)
    review = ReviewScript.load(job.review)
    review_hash = sha256_file(job.review)
    policy = EditorialPolicy.model_validate(config["editorial"])
    try:
        policy.validate_structure(review, metadata["duration"])
    except ValueError as error:
        raise StageError(str(error)) from error
    root = job.stage_dir("measure")
    for name in ("audio", "debug", "cache"):
        (root / name).mkdir(parents=True, exist_ok=True)
    code_hash = _audio_code_hash()
    total = len(review.segments)
    ctx.log(f"TTS {config['tts']['provider']}/{config['tts']['voice']}: {total} segment, "
            f"{config['measure']['workers']} luồng")

    def one(segment):
        ctx.check_stop()
        audio = root / "audio" / f"segment_{segment.id:03d}.wav"
        debug = root / "debug" / f"segment_{segment.id:03d}_tts.json"
        marker = root / "debug" / f"segment_{segment.id:03d}.cache.json"
        signature = cache_signature(segment, config, code_hash)
        cached = read_json(marker)
        if (cached and not ctx.force and cached.get("signature") == signature and audio.is_file() and debug.is_file()
                and cached.get("audio_sha256") == sha256_file(audio) and cached.get("debug_sha256") == sha256_file(debug)):
            record = read_json(debug)
            if abs(probe_audio(audio) - record["duration"]) < .001:
                return record, True
        builder = NarrationBuilder(config["tts"], config["audio"]["narration"], cache_dir=root / "cache" / f"segment_{segment.id:03d}")
        builder.build(segment.narration, audio, segment_id=segment.id, section=segment.section, debug_path=debug)
        write_json(marker, {"signature": signature, "audio_sha256": sha256_file(audio), "debug_sha256": sha256_file(debug)})
        return read_json(debug), False

    completed, errors, reused = {}, {}, 0
    started = time.monotonic()
    pool = ThreadPoolExecutor(max_workers=int(config["measure"].get("workers", 2)))
    futures = {pool.submit(one, s): s for s in review.segments}
    try:
        for future in as_completed(futures):
            segment = futures[future]
            try:
                record, was_cached = future.result()
            except Exception as error:   # report every failed segment, keep the others
                errors[segment.id] = str(error)
                ctx.log(f"[LỖI] segment {segment.id}: {error}")
                continue
            completed[segment.id] = record
            reused += was_cached
            ctx.log(f"[{len(completed)}/{total}] segment {segment.id}: {record['duration']:.2f}s"
                    + (" (cache)" if was_cached else ""))
            ctx.progress("measure", done=len(completed), total=total, elapsed=round(time.monotonic() - started))
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)   # a stop must not wait for running TTS
        raise
    pool.shutdown()
    if errors:
        raise StageError(f"TTS lỗi ở {len(errors)} segment: " + "; ".join(f"{k}: {v[:160]}" for k, v in list(errors.items())[:3]))
    if sha256_file(job.review) != review_hash:
        raise StageError("review.json đổi trong lúc đo: chạy lại measure")
    fps = float(config["render"].get("fps") or metadata["fps"])
    records = [completed[s.id] for s in review.segments]
    report = policy.timing_report(review, metadata["duration"], [r["speech_duration"] for r in records],
                                  [math.ceil(r["duration"] * fps - 1e-6) / fps for r in records])
    report.update(review_sha256=review_hash, measured_at=now_iso(), voice=config["tts"]["voice"],
                  provider=config["tts"]["provider"], fps=fps)
    write_json(job.timing_report, report)
    metrics = {"done": total, "total": total, "cached": reused, "review_duration": round(report["review_duration"], 2),
               "source_ratio": round(report["source_ratio"], 4),
               "assessment": round(report["assessment_narration_duration"] or 0, 2), "passed": report["passed"],
               "errors": report["errors"]}
    ctx.progress("measure", **metrics)
    ctx.log(f"Đo được {report['review_duration']:.1f}s = {report['source_ratio']:.1%} nguồn; "
            f"đánh giá cuối {report['assessment_narration_duration'] or 0:.1f}s; {'ĐẠT' if report['passed'] else 'CHƯA ĐẠT'}")
    if not report["passed"]:
        raise TimingFailed("Số đo chưa đạt: " + " ".join(report["errors"]), report)
    return metrics


# ---- 5. render ------------------------------------------------------------------------------------------
RENDER_CODE = ("harness/video/renderer.py", "harness/video/clipper.py", "harness/video/montage.py",
               "harness/video/picture_style.py", "harness/subtitle.py", "harness/pipeline/stages.py")


def _render_plan(ctx: StageContext) -> dict:
    """Verify the measured audio still belongs to this review and build the edit decision list."""
    from harness.video.clipper import match_duration
    from harness.video.montage import plan_shots
    from harness.video.probe import probe_audio
    job, config = ctx.job, ctx.config
    metadata = _metadata(ctx)
    review = ReviewScript.load(job.review)
    review_hash = sha256_file(job.review)
    report = read_json(job.timing_report)
    if not report:
        raise StageError("Chưa có review_timing.json: chạy measure trước")
    try:
        require_timing(report)
    except ValueError as error:
        raise StageError(str(error)) from error
    if report.get("review_sha256") != review_hash:
        raise StageError("Số đo thuộc bản review.json khác: chạy lại measure")
    fps = float(config["render"].get("fps") or metadata["fps"] or 30)
    code_hash = _audio_code_hash()
    root = job.stage_dir("measure")
    entries, speech, edits, cursor = [], [], [], 0.0
    for index, segment in enumerate(review.segments):
        wav = root / "audio" / f"segment_{segment.id:03d}.wav"
        debug_file = root / "debug" / f"segment_{segment.id:03d}_tts.json"
        marker = read_json(root / "debug" / f"segment_{segment.id:03d}.cache.json") or {}
        if (marker.get("signature") != cache_signature(segment, config, code_hash) or not wav.is_file()
                or marker.get("audio_sha256") != sha256_file(wav) or marker.get("debug_sha256") != sha256_file(debug_file)):
            raise StageError(f"Segment {segment.id}: audio đo đã cũ hoặc bị sửa: chạy lại measure")
        debug = read_json(debug_file)
        duration = probe_audio(wav)
        if abs(duration - debug["duration"]) > .001:
            raise StageError(f"Segment {segment.id}: thời lượng audio không khớp số đo")
        edit = math.ceil(duration * fps - 1e-6) / fps
        try:
            selection = (plan_shots([s.model_dump() for s in segment.shots], edit, fps,
                                    config["video"]["duration_matching"], debug["units"]) if segment.shots else
                         match_duration(segment.source_start, segment.source_end, edit, config["video"]["duration_matching"]))
        except ValueError as error:
            raise StageError(f"Segment {segment.id}: {error}") from error
        entries.append({"index": index, "segment": segment.model_dump(), "audio": str(wav),
                        "audio_sha256": marker["audio_sha256"], "tts_duration": duration,
                        "speech_duration": debug["speech_duration"], "speech_units": debug["units"],
                        "edit_duration": edit, "timeline_start": cursor, "selection": selection})
        speech.append(debug["speech_duration"])
        edits.append(edit)
        cursor += edit
    policy = EditorialPolicy.model_validate(config["editorial"])
    timing = policy.timing_report(review, metadata["duration"], speech, edits)
    try:
        require_timing(timing)
    except ValueError as error:
        raise StageError(str(error)) from error
    return {"metadata": metadata, "review": review, "review_hash": review_hash, "fps": fps, "entries": entries,
            "speech": speech, "edits": edits, "total": cursor, "policy": policy}


def _canvas(config: dict, metadata: dict) -> tuple[int, int]:
    style = config["render"]["picture_style"]
    if style.get("enabled"):
        return int(style["width"]), int(style["height"])
    return metadata["width"] // 2 * 2, metadata["height"] // 2 * 2


def render(ctx: StageContext) -> dict:
    from harness.subtitle import generate_ass
    from harness.video.probe import probe_video
    from harness.video.renderer import concat_measured_segments, render_measured_segment
    from harness.video.picture_style import PictureStyle
    job, config = ctx.job, ctx.config
    plan = _render_plan(ctx)
    metadata, fps, entries = plan["metadata"], plan["fps"], plan["entries"]
    out = job.stage_dir("render")
    (out / "clips").mkdir(parents=True, exist_ok=True)
    style = PictureStyle.model_validate(config["render"]["picture_style"])
    width, height = _canvas(config, metadata)
    sub_conf = config["subtitle"]
    subtitle_options = {k: sub_conf[k] for k in ("font_size", "max_chars_per_line", "position", "margin_vertical") if k in sub_conf}
    subtitle_options.update(width=width, height=height)
    implementation = {p: sha256_file(ROOT / p) for p in RENDER_CODE}
    shared = {"source": file_signature(job.source), "render": config["render"], "video": config["video"],
              "audio": config["audio"], "subtitle": sub_conf, "fps": fps, "implementation": implementation}
    write_json(out / "edl.json", entries)
    encoding = {k: config["video"][k] for k in ("codec", "crf", "preset")}
    total = len(entries)
    ctx.log(f"Dựng {total} phần ({width}x{height} {fps:g} fps), {config['render']['workers']} luồng; phần nào không đổi thì dùng lại")

    def part_fingerprint(entry: dict) -> str:
        return sha256_text(json.dumps({**shared, "entry": entry}, sort_keys=True, ensure_ascii=False, default=str))

    def build(entry: dict) -> tuple[Path, bool]:
        ctx.check_stop()
        name = f"part_{entry['index'] + 1:03d}"
        clip, record_path = out / "clips" / f"{name}.mkv", out / "clips" / f"{name}.json"
        fingerprint = part_fingerprint(entry)
        record = read_json(record_path) or {}
        if clip.is_file() and record.get("fingerprint") == fingerprint and record.get("sha256") == sha256_file(clip):
            return clip, True
        subtitle = None
        if sub_conf.get("enabled"):
            subtitle = generate_ass([{"narration": u["text"], "start": u["start"], "duration": u["end"] - u["start"]}
                                     for u in entry["speech_units"]], str(out / "subtitles" / f"{name}.ass"), **subtitle_options)
        pending = clip.with_name(f"{name}.pending.mkv")
        segment = entry["segment"]
        render_measured_segment(str(job.source), entry["audio"], segment["source_start"], segment["source_end"],
                                entry["edit_duration"], str(pending), metadata=metadata,
                                subtitles_path=str(subtitle) if subtitle else None,
                                keep_original_audio=segment["keep_original_audio"],
                                background_volume=config["audio"]["background_volume"],
                                narration_volume=config["audio"]["narration_volume"], **encoding, fps=fps,
                                duration_matching=config["video"]["duration_matching"],
                                threads=int(config["render"].get("threads", 3)), shots=segment.get("shots"),
                                picture_style=style.model_dump(), unit_timings=entry["speech_units"])
        result = probe_video(pending)
        if (abs(result["duration"] - entry["edit_duration"]) > .002 or result["video_codec"] != "h264"
                or result["audio_codec"] != "pcm_s16le"):
            raise StageError(f"{name}: file trung gian sai {result}")
        pending.replace(clip)
        write_json(record_path, {"fingerprint": fingerprint, "sha256": sha256_file(clip), "metadata": result})
        return clip, False

    clips: list[Path | None] = [None] * total
    done, reused, started = 0, 0, time.monotonic()
    pool = ThreadPoolExecutor(max_workers=int(config["render"].get("workers", 2)))
    futures = {pool.submit(build, e): e for e in entries}
    try:
        for future in as_completed(futures):
            entry = futures[future]
            clips[entry["index"]], was_cached = future.result()
            done += 1
            reused += was_cached
            ctx.log(f"[{done}/{total}] part {entry['index'] + 1:03d} / segment {entry['segment']['id']}: "
                    f"{entry['edit_duration']:.2f}s" + (" (cache)" if was_cached else ""))
            ctx.progress("render", done=done, total=total, cached=reused, elapsed=round(time.monotonic() - started))
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    for stale in (out / "clips").glob("part_*.mkv"):
        if stale not in clips:
            stale.unlink()
            stale.with_suffix(".json").unlink(missing_ok=True)
    pending = out / "final_review.pending.mp4"
    ctx.log("Ghép các phần: copy H.264, mã hoá AAC một lần")
    concat_measured_segments(clips, plan["edits"], str(pending))
    write_json(out / "render.json", {"rendered_at": now_iso(), "review_sha256": plan["review_hash"], "fps": fps,
                                    "width": width, "height": height, "expected_duration": plan["total"],
                                    "parts": total, "source": shared["source"]})
    return {"done": total, "total": total, "cached": reused, "duration": round(plan["total"], 2),
            "width": width, "height": height}


# ---- 6. qc ----------------------------------------------------------------------------------------------
def qc(ctx: StageContext) -> dict:
    from harness.video.probe import probe_video
    job, config = ctx.job, ctx.config
    out, folder = job.stage_dir("render"), job.stage_dir("qc")
    folder.mkdir(parents=True, exist_ok=True)
    pending, info = out / "final_review.pending.mp4", read_json(out / "render.json")
    if not pending.is_file() or not info:
        if job.final_video.is_file() and read_json(folder / "qc.json", {}).get("passed"):
            ctx.log("Bản cuối đã kiểm định, không có bản dựng mới")
            return read_json(folder / "qc.json")["metrics"]
        raise StageError("Chưa có bản dựng: chạy render trước")
    plan = _render_plan(ctx)
    if plan["review_hash"] != info["review_sha256"]:
        raise StageError("Bản dựng thuộc review.json cũ: chạy lại render")
    result = probe_video(pending)
    problems = []
    if abs(result["duration"] - plan["total"]) > .15:
        problems.append(f"thời lượng {result['duration']:.3f}s khác dự kiến {plan['total']:.3f}s")
    if (result["video_codec"], result["audio_codec"]) != ("h264", "aac"):
        problems.append(f"codec {result['video_codec']}/{result['audio_codec']}")
    if abs((result["fps"] or 0) - plan["fps"]) > .001:
        problems.append(f"fps {result['fps']}")
    if (result["width"], result["height"]) != (info["width"], info["height"]):
        problems.append(f"kích thước {result['width']}x{result['height']}")
    timing = plan["policy"].timing_report(plan["review"], plan["metadata"]["duration"], plan["speech"], plan["edits"],
                                          rendered_duration=result["duration"])
    problems += timing["errors"]
    ctx.log("Giải mã toàn bộ video + audio (không ghi file)")
    try:
        run_command([ffmpeg(), "-v", "error", "-xerror", "-threads", "4", "-i", str(pending),
                     "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
        decode_ok = True
    except Exception as error:
        decode_ok = False
        problems.append(f"giải mã lỗi: {str(error)[-300:]}")
    metrics = {"duration": round(result["duration"], 2), "source_ratio": round(timing["source_ratio"], 4),
               "assessment": round(timing["assessment_timeline_duration"] or 0, 2), "decode_ok": decode_ok,
               "width": result["width"], "height": result["height"], "size_bytes": pending.stat().st_size,
               "problems": problems}
    qc_record = {"passed": not problems, "checked_at": now_iso(), "metrics": metrics, "final_metadata": result,
                 "timing": timing, "review_sha256": plan["review_hash"],
                 "editorial_status": "cần xem/nghe duyệt hình và giọng trước khi đăng"}
    if problems:
        write_json(folder / "qc.json", qc_record)
        raise StageError("QC chưa đạt: " + "; ".join(problems))
    if job.final_video.is_file():
        job.final_video.replace(job.root / "final_review.prev.mp4")
    pending.replace(job.final_video)
    qc_record["final_sha256"] = sha256_file(job.final_video)
    _thumbs(job.final_video, folder / "thumbs.jpg", result["duration"])
    write_json(folder / "qc.json", qc_record)
    ctx.log(f"QC ĐẠT: {job.final_video} ({format_seconds(result['duration'])}, {timing['source_ratio']:.1%} nguồn)")
    return metrics


def _thumbs(video: Path, target: Path, duration: float, count: int = 8) -> None:
    """A strip of frames across the final video for the dashboard."""
    import cv2
    import numpy as np
    tiles = []
    for i in range(count):
        t = duration * (i + .5) / count
        frame = target.with_name(f".thumb_{i}.jpg")
        try:
            run_command([ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                         "-vf", "scale=320:-2", str(frame)])
            image = cv2.imread(str(frame))
            if image is not None:
                tiles.append(mat._label(image, format_seconds(t)))
        finally:
            frame.unlink(missing_ok=True)
    if tiles:
        cv2.imwrite(str(target), mat._sheet(tiles, 4), [cv2.IMWRITE_JPEG_QUALITY, 85])


STAGE_FUNCS = {"probe": probe, "read": read, "write": write, "measure": measure, "render": render, "qc": qc}
