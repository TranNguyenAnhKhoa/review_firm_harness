"""One review job = one folder jobs/<job>/ holding its inputs, stage outputs, state and logs.

    jobs/<job>/
      job.json          title, source video (absolute path + size/mtime), created
      config.yaml       optional overrides of config/default.yaml (voice, agents, watermark ...)
      state.json        status of every stage and gate, current run (written by the runner)
      events.jsonl      append-only history: stage start/finish, approvals, runs
      runs/             one log + record per pipeline run started from the CLI or dashboard
      01_probe/ ... 06_qc/   stage outputs; final_review.mp4 once QC passes
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import threading
from pathlib import Path

from harness import ROOT, __version__
from harness.config import load_config
from harness.utils import now_iso, read_json, sha256_file, write_json

JOBS_DIR = Path(os.environ.get("HARNESS_JOBS_DIR") or ROOT / "jobs").resolve()
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{1,63}")
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".m4v", ".webm", ".avi", ".ts"}

# (id, folder, title shown in the dashboard)
STAGES = (
    ("probe", "01_probe", "Probe & ngân sách"),
    ("read", "02_read", "READ - đọc phim"),
    ("write", "03_write", "WRITE - kịch bản"),
    ("measure", "04_measure", "MEASURE - TTS"),
    ("render", "05_render", "RENDER - dựng video"),
    ("qc", "06_qc", "QC - kiểm định"),
)
STAGE_IDS = tuple(s[0] for s in STAGES)
STAGE_DIRS = {s[0]: s[1] for s in STAGES}
STATUSES = ("pending", "running", "done", "waiting", "failed", "stopped", "skipped")
_state_lock = threading.Lock()


def check_slug(slug: str) -> str:
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("Job name: 2-64 chars, lowercase letters, digits, _ or -, starting with a letter/digit")
    return slug


def file_signature(path: Path) -> str:
    """Content hash for small files; size + mtime for big media (hashing a 1 GB film each poll is too slow)."""
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    if stat.st_size > 64 * 1024 * 1024:
        return f"size:{stat.st_size}:mtime:{stat.st_mtime_ns}"
    return "sha256:" + sha256_file(path)


class Job:
    def __init__(self, slug: str, jobs_dir: Path | None = None):
        self.slug = check_slug(slug)
        self.root = (jobs_dir or JOBS_DIR) / slug

    # ---- paths -------------------------------------------------------------------------------------
    def stage_dir(self, stage: str) -> Path:
        return self.root / STAGE_DIRS[stage]

    @property
    def manifest_path(self) -> Path:
        return self.root / "job.json"

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def config_path(self) -> Path:
        return self.root / "config.yaml"

    @property
    def final_video(self) -> Path:
        return self.root / "final_review.mp4"

    @property
    def timeline(self) -> Path:
        return self.stage_dir("read") / "timeline.md"

    @property
    def review(self) -> Path:
        return self.stage_dir("write") / "review.json"

    @property
    def timing_report(self) -> Path:
        return self.stage_dir("measure") / "review_timing.json"

    def exists(self) -> bool:
        return self.manifest_path.is_file()

    # ---- manifest / config ---------------------------------------------------------------------------
    def manifest(self) -> dict:
        data = read_json(self.manifest_path)
        if not isinstance(data, dict):
            raise FileNotFoundError(f"Job {self.slug!r} not found ({self.manifest_path})")
        return data

    @property
    def source(self) -> Path:
        """The source video. A relative path is relative to the harness root (e.g. media/film.mp4)."""
        path = Path(self.manifest()["source"]["path"]).expanduser()
        return path if path.is_absolute() else ROOT / path

    @property
    def title(self) -> str:
        return self.manifest().get("title") or self.slug

    def config(self) -> dict:
        return load_config(self.config_path)

    # ---- state ---------------------------------------------------------------------------------------
    def state(self) -> dict:
        state = read_json(self.state_path, {}) or {}
        state.setdefault("stages", {})
        state.setdefault("gates", {})
        state.setdefault("run", {})
        for stage in STAGE_IDS:
            state["stages"].setdefault(stage, {"status": "pending"})
        return state

    @contextlib.contextmanager
    def _locked_state(self):
        """Read-modify-write of state.json, safe across threads (dashboard) and processes (runner)."""
        self.root.mkdir(parents=True, exist_ok=True)
        with _state_lock, open(self.root / ".state.lock", "a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                state = self.state()
                yield state
                write_json(self.state_path, state)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def update_stage(self, stage: str, **fields) -> dict:
        if stage not in STAGE_IDS:
            raise ValueError(f"Unknown stage {stage!r}")
        with self._locked_state() as state:
            record = state["stages"][stage]
            for key, value in fields.items():
                if key == "metrics" and isinstance(value, dict):
                    record.setdefault("metrics", {}).update(value)
                elif value is None:
                    record.pop(key, None)
                else:
                    record[key] = value
            return dict(record)

    def reset_stage(self, stage: str) -> None:
        with self._locked_state() as state:
            state["stages"][stage] = {"status": "pending"}

    def update_run(self, **fields) -> None:
        with self._locked_state() as state:
            state["run"].update(fields)

    def set_gate(self, stage: str, approved: bool, note: str = "", by: str = "cli") -> dict:
        if stage not in ("read", "write"):
            raise ValueError("Only read and write have approval gates")
        if approved and stage == "write" and "read" in self.config().get("gates", []) and not self.gate_ok("read"):
            raise ValueError("Approve READ first (or its timeline.md changed after approval)")
        with self._locked_state() as state:
            record = state["stages"][stage]
            if record.get("status") not in ("waiting", "done"):
                raise ValueError(f"{stage} has no output to approve yet (status {record.get('status')})")
            artifact = self.timeline if stage == "read" else self.review
            gate = {"approved": approved, "note": note, "by": by, "at": now_iso(),
                    "artifact": file_signature(artifact)}
            state["gates"][stage] = gate
            record["status"] = "done" if approved else "failed"
            record["message"] = ("Đã duyệt" if approved else "Bị từ chối") + (f": {note}" if note else "")
        self.event("gate", stage=stage, approved=approved, note=note, by=by)
        return gate

    def gate_ok(self, stage: str) -> bool:
        """Approved, and the artifact has not been edited since the approval."""
        gate = self.state()["gates"].get(stage) or {}
        artifact = self.timeline if stage == "read" else self.review
        return bool(gate.get("approved")) and gate.get("artifact") == file_signature(artifact)

    def clear_gate(self, stage: str) -> None:
        with self._locked_state() as state:
            state["gates"].pop(stage, None)

    def event(self, kind: str, **data) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"at": now_iso(), "kind": kind, **data}, ensure_ascii=False, default=str)
        with open(self.root / "events.jsonl", "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def events(self, limit: int = 200) -> list[dict]:
        path = self.root / "events.jsonl"
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows

    # ---- creation ------------------------------------------------------------------------------------
    @classmethod
    def create(cls, slug: str, video: str | Path, *, title: str = "", overrides: dict | None = None,
               jobs_dir: Path | None = None) -> "Job":
        job = cls(slug, jobs_dir)
        if job.exists():
            raise FileExistsError(f"Job {slug!r} already exists")
        source = Path(video).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Video not found: {source}")
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Not a video file ({', '.join(sorted(VIDEO_EXTENSIONS))}): {source.name}")
        stat = source.stat()
        # Inside the harness (media/...) the path is stored relative, so the job folder can move machines.
        stored = source.relative_to(ROOT) if ROOT in source.parents else source
        job.root.mkdir(parents=True)
        for _, folder, _ in STAGES:
            (job.root / folder).mkdir()
        write_json(job.manifest_path, {
            "job": slug, "title": title.strip() or slug, "created": now_iso(), "harness_version": __version__,
            "source": {"path": str(stored), "name": source.name, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns},
        })
        if overrides:
            job.write_overrides(overrides)
        job.event("created", source=str(source), title=title)
        return job

    def write_overrides(self, overrides: dict) -> None:
        """Merge overrides into config.yaml after validating the merged result."""
        import yaml
        from harness.config import merge, read_yaml
        merged = merge(read_yaml(self.config_path), overrides)
        load_config(merged)  # raises on an invalid value; nothing is written
        self.config_path.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def archive(self) -> Path:
        """Move the job folder to jobs/.trash/<job>-<time>/ (recoverable), never rm -rf."""
        trash = self.root.parent / ".trash"
        trash.mkdir(exist_ok=True)
        target = trash / f"{self.slug}-{now_iso().replace(':', '')}"
        shutil.move(str(self.root), str(target))
        return target


def list_jobs(jobs_dir: Path | None = None) -> list[Job]:
    folder = jobs_dir or JOBS_DIR
    if not folder.is_dir():
        return []
    return [Job(p.name, folder) for p in sorted(folder.iterdir())
            if p.is_dir() and SLUG.fullmatch(p.name) and (p / "job.json").is_file()]
