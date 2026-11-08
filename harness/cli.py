"""Command line: ./run.sh <command> (same as .venv/bin/python -m harness <command>).

    new <job> <video> [--title T] [--voice V] [--read claude|agy|codex|manual] [--write ...]
    run <job> [--from STAGE] [--to STAGE] [--only STAGE] [--force]
    status [<job>]                 list jobs, or one job's stages
    approve <job> read|write [--note N]
    reject  <job> read|write --note N
    import  <job> timeline|review <file>     (manual READ/WRITE)
    check   <job>                  validate review.json and estimate its spoken length
    frame   <job> <seconds>...     save full-size frames (a READ agent tool)
    brief   <video>                duration budget of a video
    voice   --text T [--voice V] [--emotion E] [--out file.wav]
    doctor                         check Python packages, FFmpeg, model, agent CLIs
    serve   [--host H] [--port P] [--no-browser]   dashboard (default 127.0.0.1:8790)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from harness import ROOT
from harness.config import READ_ENGINES, VOICES, WRITE_ENGINES
from harness.pipeline.job import STAGE_IDS, Job, list_jobs
from harness.utils import format_seconds


def _run_id(value: str) -> str:
    if not re.fullmatch(r"[0-9]{8}-[0-9]{6}(-[0-9]{1,3})?", value):
        raise argparse.ArgumentTypeError("run id: YYYYMMDD-HHMMSS")
    return value


def _job(slug: str) -> Job:
    job = Job(slug)
    if not job.exists():
        raise SystemExit(f"Không có job {slug!r} (./run.sh status để xem danh sách)")
    return job


def cmd_new(args) -> int:
    overrides: dict = {}
    if args.voice:
        overrides.setdefault("tts", {})["voice"] = args.voice
    if args.read:
        overrides.setdefault("agents", {}).setdefault("read", {})["engine"] = args.read
    if args.write:
        overrides.setdefault("agents", {}).setdefault("write", {})["engine"] = args.write
    job = Job.create(args.job, args.video, title=args.title or "", overrides=overrides or None)
    print(f"Đã tạo {job.root}\nTiếp: ./run.sh run {job.slug}")
    return 0


def cmd_run(args) -> int:
    from harness.pipeline.runner import RunLocked, run
    try:
        status = run(_job(args.job), start=args.start, end=args.end, only=args.only, force=args.force,
                     run_id=args.run_id)
    except RunLocked as error:
        print(error, file=sys.stderr)
        return 3
    if status == "stopped":
        # State is saved; worker threads still inside TTS/ONNX cannot be interrupted, so leave now.
        sys.stdout.flush()
        os._exit(130)
    return {"finished": 0, "waiting": 0}.get(status, 1)


def cmd_status(args) -> int:
    from harness.pipeline.runner import is_running, stale
    if not args.job:
        jobs = list_jobs()
        if not jobs:
            print("Chưa có job. Tạo: ./run.sh new <job> <video>")
        for job in jobs:
            state = job.state()
            marks = "".join({"done": "#", "running": ">", "waiting": "?", "failed": "x", "stopped": "!"}
                            .get(state["stages"][s].get("status"), ".") for s in STAGE_IDS)
            print(f"{job.slug:28} [{marks}] {'RUNNING ' if is_running(job) else ''}{job.title}")
        return 0
    job = _job(args.job)
    state = job.state()
    print(f"{job.slug}: {job.title}\nNguồn: {job.source}")
    for stage in STAGE_IDS:
        record = state["stages"][stage]
        flag = " (cũ, cần chạy lại)" if stale(job, stage, record) else ""
        print(f"  {stage:8} {record.get('status', 'pending'):8} {record.get('message') or ''}{flag}")
    if job.final_video.is_file():
        print(f"Video cuối: {job.final_video}")
    return 0


def cmd_gate(args, approved: bool) -> int:
    job = _job(args.job)
    job.set_gate(args.stage, approved, note=args.note or "", by="cli")
    print(f"{args.stage}: {'đã duyệt' if approved else 'từ chối'}. Tiếp: ./run.sh run {job.slug}")
    return 0


def cmd_import(args) -> int:
    job = _job(args.job)
    source = Path(args.file).expanduser()
    target = job.timeline if args.kind == "timeline" else job.review
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        from harness.pipeline.stages import _backup
        _backup(target)
    shutil.copyfile(source, target)
    stage = "read" if args.kind == "timeline" else "write"
    job.update_stage(stage, status="pending", message="Đã nhập file tay, chạy run để kiểm tra", needs_input=None)
    job.event("import", stage=stage, file=str(source))
    print(f"Đã chép vào {target}. Tiếp: ./run.sh run {job.slug}")
    return 0


def cmd_check(args) -> int:
    from harness.pipeline import review_check
    job = _job(args.job)
    meta = json.loads((job.stage_dir("probe") / "metadata.json").read_text(encoding="utf-8"))
    scenes = review_check.load_scenes(job.stage_dir("read") / "materials" / "scenes.json")
    result = review_check.check(job.review, job.config(), meta["duration"], scenes)
    print(review_check.format_report(result))
    for row in result.get("per_segment", []):
        print(f"  seg {row['id']:>3} {row['section']:10} {row['tokens']:4} tiếng ~{row['estimate_seconds']:6.1f}s "
              f"{row['shots']:2} shot / {row['footage_seconds']:.1f}s hình")
    return 0 if result["ok"] else 1


def cmd_frame(args) -> int:
    from harness.pipeline.materials import zoom_frames
    for path in zoom_frames(_job(args.job), [float(t) for t in args.seconds]):
        print(path)
    return 0


def cmd_brief(args) -> int:
    from harness.config import load_config
    from harness.editorial import EditorialPolicy
    from harness.video.probe import probe_video
    meta = probe_video(args.video)
    budget = EditorialPolicy.model_validate(load_config()["editorial"]).budget(meta["duration"])
    print(f"{args.video}: {format_seconds(meta['duration'])} ({meta['duration']:.3f}s), {meta['width']}x{meta['height']} {meta['fps']} fps")
    print(f"Review: {budget['total_min']:.1f}-{budget['total_max']:.1f}s, mục tiêu {budget['total_target']:.1f}s "
          f"(kể {budget['story_target']:.1f}s + đánh giá {budget['assessment_target']:.0f}s)")
    return 0


def cmd_voice(args) -> int:
    from harness.audio.narration_builder import NarrationBuilder
    from harness.audio.speech import SpeechUnit
    from harness.config import load_config
    config = load_config({"tts": {"voice": args.voice}} if args.voice else None)
    out = Path(args.out)
    result = NarrationBuilder(config["tts"], config["audio"]["narration"]).build(
        [SpeechUnit(text=args.text, emotion=args.emotion)], out)
    print(f"{out}: {result.duration:.2f}s, {result.metrics['syllables_per_second']:.2f} tiếng/s")
    return 0


def cmd_doctor(args) -> int:
    from harness.doctor import report
    ok = True
    for name, passed, detail in report():
        ok &= passed or name.startswith("(tuỳ chọn)")
        print(f"{'OK  ' if passed else 'THIẾU'} {name}: {detail}")
    return 0 if ok else 1


def cmd_serve(args) -> int:
    from harness.monitor.server import main as serve
    return serve(host=args.host, port=args.port, open_browser=not args.no_browser)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="./run.sh", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new")
    p.add_argument("job"), p.add_argument("video")
    p.add_argument("--title"), p.add_argument("--voice", choices=VOICES)
    p.add_argument("--read", choices=READ_ENGINES), p.add_argument("--write", choices=WRITE_ENGINES)
    p.set_defaults(func=cmd_new)
    p = sub.add_parser("run")
    p.add_argument("job"), p.add_argument("--from", dest="start", choices=STAGE_IDS)
    p.add_argument("--to", dest="end", choices=STAGE_IDS), p.add_argument("--only", choices=STAGE_IDS)
    p.add_argument("--force", action="store_true", help="re-run finished stages (agents run again)")
    p.add_argument("--run-id", type=_run_id, help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("status")
    p.add_argument("job", nargs="?")
    p.set_defaults(func=cmd_status)
    for name, approved in (("approve", True), ("reject", False)):
        p = sub.add_parser(name)
        p.add_argument("job"), p.add_argument("stage", choices=("read", "write"))
        p.add_argument("--note", required=not approved)
        p.set_defaults(func=lambda a, ok=approved: cmd_gate(a, ok))
    p = sub.add_parser("import")
    p.add_argument("job"), p.add_argument("kind", choices=("timeline", "review")), p.add_argument("file")
    p.set_defaults(func=cmd_import)
    p = sub.add_parser("check")
    p.add_argument("job")
    p.set_defaults(func=cmd_check)
    p = sub.add_parser("frame")
    p.add_argument("job"), p.add_argument("seconds", nargs="+")
    p.set_defaults(func=cmd_frame)
    p = sub.add_parser("brief")
    p.add_argument("video")
    p.set_defaults(func=cmd_brief)
    p = sub.add_parser("voice")
    p.add_argument("--text", required=True), p.add_argument("--voice", choices=VOICES)
    p.add_argument("--emotion", default="normal", choices=("normal", "suspense", "excited", "serious", "punchline", "calm"))
    p.add_argument("--out", default=str(ROOT / "jobs" / ".voice_preview.wav"))
    p.set_defaults(func=cmd_voice)
    p = sub.add_parser("doctor")
    p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("serve")
    p.add_argument("--host", default=None), p.add_argument("--port", type=int, default=None)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_serve)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        return 2
