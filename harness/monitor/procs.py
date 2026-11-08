"""Start and stop pipeline runs from the dashboard.

A run is `python -m harness run <job> ...` in its own session (process group): it keeps running
when the dashboard restarts, and Stop signals the whole group (runner, agent CLI, FFmpeg).
Only this fixed command can be started, with arguments validated against fixed lists.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

from harness import ROOT
from harness.pipeline.job import STAGE_IDS, Job
from harness.pipeline.runner import is_running


def start(job: Job, *, start: str | None = None, end: str | None = None, only: str | None = None,
          force: bool = False) -> str:
    for value in (start, end, only):
        if value is not None and value not in STAGE_IDS:
            raise ValueError(f"Unknown stage {value!r}")
    if is_running(job):
        raise RuntimeError("Job đang chạy")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    argv = [sys.executable, "-m", "harness", "run", job.slug, "--run-id", run_id]
    argv += ["--from", start] if start else []
    argv += ["--to", end] if end else []
    argv += ["--only", only] if only else []
    argv += ["--force"] if force else []
    (job.root / "runs").mkdir(exist_ok=True)
    out = open(job.root / "runs" / f"{run_id}.out", "w", encoding="utf-8")
    subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                     start_new_session=True, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    out.close()
    return run_id


def _ours(pid: int, slug: str) -> bool:
    try:
        cmdline = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
    except OSError:
        return False
    return b"harness" in cmdline and b"run" in cmdline and slug.encode() in cmdline


def stop(job: Job) -> bool:
    run = job.state().get("run", {})
    pid, pgid = run.get("pid"), run.get("pgid")
    if not isinstance(pid, int) or not is_running(job) or not _ours(pid, job.slug):
        return False
    target = pgid if isinstance(pgid, int) and pgid == pid else None
    if target:
        os.killpg(target, signal.SIGTERM)
    else:
        os.kill(pid, signal.SIGTERM)

    def escalate():
        time.sleep(20)
        if is_running(job) and _ours(pid, job.slug):
            try:
                os.killpg(target, signal.SIGKILL) if target else os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    threading.Thread(target=escalate, daemon=True).start()
    return True
