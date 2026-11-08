"""Read-only views of jobs for the dashboard API (no writes here)."""
from __future__ import annotations

import os
import time
from pathlib import Path

from harness import __version__
from harness.config import VOICE_NAMES
from harness.pipeline.job import STAGE_IDS, STAGES, Job, list_jobs
from harness.pipeline.runner import is_running, stale
from harness.utils import read_json

TEXT = {".md", ".json", ".jsonl", ".txt", ".log", ".yaml", ".ass"}
IMAGE = {".jpg", ".jpeg", ".png"}
MEDIA = {".mp4", ".mkv", ".wav", ".mp3", ".m4a"}
TITLES = {s[0]: s[2] for s in STAGES}
ENGINE_OF = {"probe": "local", "measure": "zerotts", "render": "ffmpeg", "qc": "ffmpeg"}


def _overall(job: Job, state: dict, running: bool) -> str:
    stages = state["stages"]
    if running:
        return "running"
    if job.final_video.is_file() and stages["qc"].get("status") == "done":
        return "done"
    if any(stages[s].get("status") == "failed" for s in STAGE_IDS):
        return "failed"
    if any(stages[s].get("status") == "waiting" for s in STAGE_IDS):
        return "waiting"
    if any(stages[s].get("status") == "stopped" for s in STAGE_IDS):
        return "stopped"
    return "pending" if all(stages[s].get("status", "pending") == "pending" for s in STAGE_IDS) else "idle"


def _engine(config: dict, stage: str) -> dict:
    if stage in ("read", "write"):
        conf = config["agents"][stage]
        return {"engine": conf["engine"], "model": conf.get("model") or "", "effort": conf.get("effort") or ""}
    if stage == "measure":
        return {"engine": "zerotts", "model": config["tts"]["voice"], "effort": ""}
    return {"engine": ENGINE_OF[stage], "model": "", "effort": ""}


def summary(job: Job) -> dict:
    state = job.state()
    manifest = job.manifest()
    running = is_running(job)
    stages = []
    done = 0
    for stage in STAGE_IDS:
        record = state["stages"][stage]
        is_stale = stale(job, stage, record)
        done += record.get("status") == "done" and not is_stale
        stages.append({"id": stage, "title": TITLES[stage], "status": record.get("status", "pending"), "stale": is_stale})
    meta = read_json(job.stage_dir("probe") / "metadata.json") or {}
    return {"job": job.slug, "title": manifest.get("title") or job.slug, "created": manifest.get("created"),
            "source_name": manifest["source"].get("name"), "source_exists": Path(manifest["source"]["path"]).is_file(),
            "duration": meta.get("duration"), "status": _overall(job, state, running), "running": running,
            "stages": stages, "progress": round(done / len(STAGE_IDS), 3), "final": job.final_video.is_file(),
            "updated": _mtime(job.state_path) or _mtime(job.manifest_path), "run": state.get("run", {})}


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def overview() -> dict:
    jobs = []
    for job in list_jobs():
        try:
            jobs.append(summary(job))
        except Exception as error:   # one broken job must not hide the others
            jobs.append({"job": job.slug, "title": job.slug, "status": "failed", "error": str(error), "stages": []})
    jobs.sort(key=lambda j: j.get("updated") or 0, reverse=True)
    return {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "version": __version__, "jobs": jobs, "voices": VOICE_NAMES,
            "counts": {k: sum(j["status"] == k for j in jobs) for k in ("running", "waiting", "failed", "done")}}


def _files(job: Job, stage: str) -> list[dict]:
    folder = job.stage_dir(stage)
    out = []
    if not folder.is_dir():
        return out
    wanted = {
        "probe": ["metadata.json", "budget.json"],
        "read": ["timeline.md", "request.md", "materials/materials.json", "materials/scenes.json",
                 "materials/transcript.txt"],
        "write": ["review.json", "check.json", "request.md", "revise_report.json"],
        "measure": ["review_timing.json"],
        "render": ["edl.json", "render.json"],
        "qc": ["qc.json", "thumbs.jpg"],
    }[stage]
    for rel in wanted:
        path = folder / rel
        if path.is_file():
            out.append(_file_row(job, path))
    if stage in ("read", "write"):
        out += [_file_row(job, p) for p in sorted(folder.glob("agent_*.jsonl"))]
    if stage == "read":
        mats = read_json(folder / "materials" / "materials.json") or {}
        for group in ("proxy", "sheets", "strip_sheets"):
            for item in mats.get(group, [])[:400]:
                path = job.root / item["file"]
                if path.is_file():
                    out.append({**_file_row(job, path), "group": group, "start": item.get("start"), "end": item.get("end")})
        keyframes = folder / "keyframes"
        if keyframes.is_dir():
            out += [{**_file_row(job, p), "group": "keyframes"} for p in sorted(keyframes.glob("*.jpg"))[:200]]
    if stage == "measure":
        out += [{**_file_row(job, p), "group": "audio"} for p in sorted((folder / "audio").glob("segment_*.wav"))]
    if stage == "qc" and job.final_video.is_file():
        out.insert(0, _file_row(job, job.final_video))
    return out


def _file_row(job: Job, path: Path) -> dict:
    suffix = path.suffix.lower()
    kind = "text" if suffix in TEXT else "image" if suffix in IMAGE else "media" if suffix in MEDIA else "other"
    return {"path": str(path.relative_to(job.root)), "name": path.name, "kind": kind, "size": path.stat().st_size,
            "mtime": path.stat().st_mtime}


def detail(job: Job) -> dict:
    state = job.state()
    config = job.config()
    base = summary(job)
    stages = []
    for stage in STAGE_IDS:
        record = dict(state["stages"][stage])
        stages.append({**record, "id": stage, "title": TITLES[stage], "stale": stale(job, stage, state["stages"][stage]),
                       "agent": _engine(config, stage), "gated": stage in config.get("gates", []),
                       "gate": state["gates"].get(stage), "files": _files(job, stage)})
    runs = []
    for path in sorted((job.root / "runs").glob("*.json"), reverse=True)[:30]:
        record = read_json(path)
        if record:
            runs.append(record)
    return {**base, "manifest": job.manifest(), "stages": stages, "runs": runs, "events": job.events(80)[::-1],
            "metadata": read_json(job.stage_dir("probe") / "metadata.json"),
            "budget": read_json(job.stage_dir("probe") / "budget.json"),
            "timing": _timing(job), "qc": read_json(job.stage_dir("qc") / "qc.json"),
            "settings": {"voice": config["tts"]["voice"], "gates": config.get("gates", []),
                         "read": config["agents"]["read"], "write": {k: v for k, v in config["agents"]["write"].items()},
                         "revise_rounds": config["agents"].get("revise_rounds", 0),
                         "watermark": config["render"]["picture_style"].get("watermark", ""),
                         "subtitles": bool(config["subtitle"].get("enabled")),
                         "background_volume": config["audio"]["background_volume"]},
            "pid_alive": _alive(state.get("run", {}).get("pid"))}


def _timing(job: Job) -> dict | None:
    report = read_json(job.timing_report)
    if not report:
        return None
    return {k: report.get(k) for k in ("passed", "errors", "review_duration", "source_ratio",
                                       "assessment_narration_duration", "budget", "segments", "measured_at", "voice")}


def _alive(pid) -> bool:
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
