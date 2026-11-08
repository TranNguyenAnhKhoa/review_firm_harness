"""Run a job's stages in order, one run per job at a time, with gates, resume and stop.

A run owns jobs/<job>/.run.lock (flock) for its lifetime and logs to jobs/<job>/runs/<run-id>.log,
which the dashboard tails. SIGTERM/SIGINT stop it between steps; the current stage is marked stopped.
A finished stage is skipped on the next run unless its inputs changed (see stale()) or --force.
"""
from __future__ import annotations

import fcntl
import logging
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from harness.pipeline.job import STAGE_IDS, Job, file_signature
from harness.pipeline.stages import STAGE_FUNCS, NeedsInput, StageContext, StageError, TimingFailed
from harness.utils import now_iso, read_json, write_json

GATED = ("read", "write")


class RunLocked(RuntimeError):
    pass


def stage_inputs(job: Job, stage: str) -> dict:
    """What a stage's result depends on: if any of these change, the result is stale."""
    def sig(path: Path) -> str:
        return file_signature(path)
    config = job.config_path
    base = {"config": sig(config)}
    if stage == "probe":
        return {"source": sig(job.source)}
    if stage == "read":
        return {"source": sig(job.source)}
    if stage == "write":
        return {"timeline": sig(job.timeline)}
    if stage == "measure":
        return {"review": sig(job.review), **base}
    if stage == "render":
        return {"timing": sig(job.timing_report), "review": sig(job.review), **base}
    if stage == "qc":
        return {"render": sig(job.stage_dir("render") / "render.json")}
    return {}


def stale(job: Job, stage: str, record: dict | None = None) -> bool:
    record = record if record is not None else job.state()["stages"][stage]
    if record.get("status") != "done":
        return False
    saved = record.get("inputs") or {}
    current = stage_inputs(job, stage)
    # A stage's own output (timeline/review) may be edited by hand after it finished: that is not stale.
    return any(saved.get(k) != v for k, v in current.items() if k in saved)


class _Tee:
    def __init__(self, path: Path):
        self.handle = open(path, "a", encoding="utf-8", buffering=1)
        self.lock = threading.Lock()

    def __call__(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self.lock:
            print(line, flush=True)
            self.handle.write(line + "\n")


class _LogHandler(logging.Handler):
    def __init__(self, tee: _Tee):
        super().__init__(logging.INFO)
        self.tee = tee

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.tee(record.getMessage())
        except Exception:
            pass


def run(job: Job, *, start: str | None = None, end: str | None = None, only: str | None = None,
        force: bool = False, run_id: str | None = None) -> str:
    """Run stages; return the final run status: finished | waiting | failed | stopped."""
    if not job.exists():
        raise FileNotFoundError(f"Job {job.slug!r} not found")
    stages = list(STAGE_IDS)
    if only:
        stages = [only]
    else:
        if start:
            stages = stages[stages.index(start):]
        if end:
            stages = stages[:stages.index(end) + 1]
    job.root.mkdir(parents=True, exist_ok=True)
    lock_handle = open(job.root / ".run.lock", "a+")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_handle.close()
        raise RunLocked(f"Job {job.slug} is already running")
    (job.root / "runs").mkdir(exist_ok=True)
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    base, n = run_id, 1
    while (job.root / "runs" / f"{run_id}.json").exists():   # two runs in the same second
        n += 1
        run_id = f"{base}-{n}"
    log_path = job.root / "runs" / f"{run_id}.log"
    tee = _Tee(log_path)
    handler = _LogHandler(tee)
    logging.getLogger("harness").addHandler(handler)
    logging.getLogger("harness").setLevel(logging.INFO)
    stop = threading.Event()
    previous = {}

    def on_signal(signum, frame):
        stop.set()
        raise KeyboardInterrupt

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, on_signal)
    record = {"id": run_id, "pid": os.getpid(), "pgid": os.getpgid(0), "status": "running", "started": now_iso(),
              "stages": stages, "force": force, "log": f"runs/{run_id}.log", "stage": None, "finished": None}
    job.update_run(**record)
    write_json(job.root / "runs" / f"{run_id}.json", record)
    job.event("run_start", run=run_id, stages=stages, force=force)
    tee(f"Run {run_id}: job {job.slug}, stages {', '.join(stages)}" + (" (force)" if force else ""))
    status = "finished"
    try:
        config = job.config()
        ctx = StageContext(job=job, config=config, log=tee, force=force, stop=stop)
        revisions_left = int(config["agents"].get("revise_rounds", 0))
        index = 0
        while index < len(stages):
            stage = stages[index]
            state = job.state()
            current = state["stages"][stage]
            if not force and current.get("status") == "done" and not stale(job, stage, current):
                if stage in GATED and stage in config["gates"] and not job.gate_ok(stage):
                    job.update_stage(stage, status="waiting", message="Chờ duyệt (file đã sửa sau lần duyệt trước)")
                    tee(f"{stage}: chờ duyệt lại")
                    status = "waiting"
                    break
                tee(f"{stage}: đã xong, bỏ qua")
                index += 1
                continue
            if stage in GATED and current.get("status") == "waiting" and current.get("output_ready") and not force:
                if job.gate_ok(stage):
                    job.update_stage(stage, status="done", message="Đã duyệt")
                    index += 1
                    continue
                tee(f"{stage}: đang chờ duyệt, dừng run")
                status = "waiting"
                break
            job.update_run(stage=stage)
            began = time.monotonic()
            job.update_stage(stage, status="running", started=now_iso(), finished=None, message=None, error=None,
                             metrics=None, output_ready=None)
            job.event("stage_start", stage=stage, run=run_id)
            tee(f"=== {stage} ===")
            try:
                metrics = STAGE_FUNCS[stage](ctx)
            except NeedsInput as wait:
                job.update_stage(stage, status="waiting", message=str(wait), needs_input=True, finished=now_iso(),
                                 seconds=round(time.monotonic() - began, 1))
                tee(f"{stage}: {wait}")
                status = "waiting"
                break
            except TimingFailed as failure:
                job.update_stage(stage, status="failed", message=str(failure), finished=now_iso(),
                                 seconds=round(time.monotonic() - began, 1))
                job.event("stage_failed", stage=stage, run=run_id, message=str(failure))
                tee(f"{stage}: {failure}")
                if revisions_left > 0 and config["agents"]["write"]["engine"] != "manual":
                    revisions_left -= 1
                    round_no = int(config["agents"].get("revise_rounds", 0)) - revisions_left
                    tee(f"Gửi số đo cho WRITE sửa kịch bản (vòng {round_no})")
                    ctx.revision = failure.report
                    job.update_stage("write", status="running", started=now_iso(), message=f"Tự sửa vòng {round_no}")
                    try:
                        write_metrics = STAGE_FUNCS["write"](ctx)
                    finally:
                        ctx.revision = None
                    job.update_stage("write", status="done", finished=now_iso(), metrics={**write_metrics, "revised": round_no},
                                     inputs=stage_inputs(job, "write"), message=f"Tự sửa theo số đo, vòng {round_no}")
                    if "write" in config["gates"]:
                        job.set_gate("write", True, note=f"Tự duyệt sau khi sửa theo số đo TTS (vòng {round_no})", by="auto-revise")
                    continue   # measure again
                status = "failed"
                break
            except (StageError, Exception) as error:
                if stop.is_set():
                    raise KeyboardInterrupt from error
                detail = "" if isinstance(error, StageError) else traceback.format_exc(limit=6)
                job.update_stage(stage, status="failed", message=str(error)[:2000], error=detail[-4000:] or None,
                                 finished=now_iso(), seconds=round(time.monotonic() - began, 1))
                job.event("stage_failed", stage=stage, run=run_id, message=str(error)[:500])
                tee(f"{stage}: LỖI {error}")
                if detail:
                    tee(detail)
                status = "failed"
                break
            seconds = round(time.monotonic() - began, 1)
            gated = stage in GATED and stage in config["gates"]
            # A new READ/WRITE output always needs a fresh approval.
            if gated:
                job.clear_gate(stage)
            job.update_stage(stage, status="waiting" if gated else "done", finished=now_iso(), seconds=seconds,
                             metrics=metrics, inputs=stage_inputs(job, stage), output_ready=True if gated else None,
                             needs_input=None, message="Chờ duyệt" if gated else "Xong")
            job.event("stage_done", stage=stage, run=run_id, seconds=seconds)
            tee(f"{stage}: xong trong {seconds:.0f}s" + (" - chờ duyệt" if gated else ""))
            # downstream results built on the old output are now stale; drop their done status
            for later in STAGE_IDS[STAGE_IDS.index(stage) + 1:]:
                record_later = job.state()["stages"][later]
                if record_later.get("status") == "done" and stale(job, later, record_later):
                    job.update_stage(later, status="pending", message="Đầu vào đã đổi, cần chạy lại")
            if gated:
                status = "waiting"
                break
            index += 1
    except KeyboardInterrupt:
        status = "stopped"
        stage = job.state()["run"].get("stage")
        if stage and job.state()["stages"][stage].get("status") == "running":
            job.update_stage(stage, status="stopped", message="Đã dừng", finished=now_iso())
        tee("Run stopped")
    except Exception as error:   # config error or a bug outside a stage: record it, never leave "running"
        status = "failed"
        tee(f"Run lỗi: {error}\n{traceback.format_exc(limit=6)}")
        stage = job.state()["run"].get("stage")
        if stage and job.state()["stages"][stage].get("status") == "running":
            job.update_stage(stage, status="failed", message=str(error)[:2000], finished=now_iso())
    finally:
        job.update_run(status=status, finished=now_iso(), stage=None)
        record.update(status=status, finished=now_iso())
        write_json(job.root / "runs" / f"{run_id}.json", record)
        job.event("run_end", run=run_id, status=status)
        tee(f"Run {run_id}: {status}")
        logging.getLogger("harness").removeHandler(handler)
        tee.handle.close()
        for sig, handler_before in previous.items():
            signal.signal(sig, handler_before)
        fcntl.flock(lock_handle, fcntl.LOCK_UN)
        lock_handle.close()
    return status


def is_running(job: Job) -> bool:
    """True while some process holds the job's run lock."""
    path = job.root / ".run.lock"
    if not path.exists():
        return False
    with open(path, "a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False
