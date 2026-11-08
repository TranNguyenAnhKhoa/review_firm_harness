"""Local dashboard: watch every job's stages, read their outputs, run/stop, approve gates.

    ./start.sh                  (or ./run.sh serve) then open http://127.0.0.1:8790

Safety: binds 127.0.0.1 unless --host/HARNESS_HOST says otherwise. Every request must carry an allowed
Host header (blocks DNS rebinding); every write must be a JSON POST with the X-Harness header and,
when the browser sends one, a same-host Origin (blocks other web pages). Files are served only from
inside a job folder (plus that job's own source video). Runs start only `python -m harness run`.
No CORS headers are ever sent.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from harness import ROOT
from harness.config import READ_ENGINES, VOICES, WRITE_ENGINES
from harness.monitor import collect, procs
from harness.pipeline.job import SLUG, VIDEO_EXTENSIONS, Job

STATIC = Path(__file__).with_name("static")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
MAX_BODY = 8 * 1024 * 1024
DEFAULT_PORT = 8790
MODEL_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\[\]-]{0,80}$")
mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("application/x-ndjson", ".jsonl")


class HttpError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def host_name(header: str) -> str:
    host = (header or "").strip().lower()
    if host.startswith("["):
        return host[1:host.index("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def media_roots() -> list[Path]:
    raw = os.environ.get("HARNESS_MEDIA_DIRS") or f"{ROOT / 'media'}:{Path.home() / 'Videos'}:{Path.home()}"
    roots = []
    for item in raw.split(":"):
        path = Path(item).expanduser()
        if path.is_dir():
            roots.append(path.resolve())
    return roots


def make_handler(allowed_hosts: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ReviewHarness"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quiet; errors still go to stderr
            if args and str(args[1]).startswith(("4", "5")):
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        # ---- plumbing ----
        def send_body(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if self.close_connection:
                self.send_header("Connection", "close")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, data, code: int = 200) -> None:
            self.send_body(code, json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"),
                           "application/json; charset=utf-8")

        def fail(self, code: int, message: str) -> None:
            if self.command == "POST":
                self.close_connection = True   # an unread request body must not be parsed as the next request
            self.send_json({"error": message}, code)

        def check_host(self) -> None:
            if host_name(self.headers.get("Host", "")) not in allowed_hosts:
                raise HttpError(421, "Host not allowed (use 127.0.0.1/localhost or add --allow-host)")

        def check_write(self) -> None:
            if self.headers.get("X-Harness") != "1":
                raise HttpError(403, "Missing X-Harness header")
            origin = self.headers.get("Origin")
            if origin and host_name(urlparse(origin).netloc) not in allowed_hosts:
                raise HttpError(403, "Cross-origin write refused")
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                raise HttpError(415, "JSON body required")

        def body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise HttpError(413, "Body too large")
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                raise HttpError(400, "Invalid JSON")
            if not isinstance(data, dict):
                raise HttpError(400, "JSON object required")
            return data

        def job(self, slug: str) -> Job:
            if not SLUG.fullmatch(slug or ""):
                raise HttpError(400, "Bad job name")
            job = Job(slug)
            if not job.exists():
                raise HttpError(404, f"No job {slug}")
            return job

        # ---- routing ----
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                self.check_host()
                url = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                parts = [unquote(p) for p in url.path.strip("/").split("/") if p]
                if not parts or parts == ["index.html"]:
                    return self.static("index.html")
                if parts[0] != "api":
                    return self.fail(404, "Not found")
                if parts[1:] == ["overview"]:
                    return self.send_json(collect.overview())
                if parts[1:] == ["doctor"]:
                    from harness.doctor import report
                    return self.send_json({"checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in report()]})
                if parts[1:] == ["browse"]:
                    return self.send_json(self.browse(query.get("dir")))
                if len(parts) >= 3 and parts[1] == "jobs":
                    job = self.job(parts[2])
                    if len(parts) == 3:
                        return self.send_json(collect.detail(job))
                    if parts[3] == "log":
                        return self.send_json(self.log_tail(job, query))
                    if parts[3] == "file":
                        return self.serve_file(job, query.get("path", ""))
                return self.fail(404, "Not found")
            except HttpError as error:
                self.fail(error.code, str(error))
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as error:
                self.fail(500, f"{type(error).__name__}: {error}")

        def do_POST(self):
            try:
                self.check_host()
                self.check_write()
                parts = [unquote(p) for p in urlparse(self.path).path.strip("/").split("/") if p]
                data = self.body()
                if parts == ["api", "jobs"]:
                    return self.send_json(self.create(data), 201)
                if len(parts) == 4 and parts[:2] == ["api", "jobs"]:
                    job, action = self.job(parts[2]), parts[3]
                    handler = {"run": self.run_job, "stop": self.stop_job, "gate": self.gate, "config": self.config,
                               "upload": self.upload, "archive": self.archive, "reset": self.reset}.get(action)
                    if handler:
                        return self.send_json(handler(job, data))
                return self.fail(404, "Not found")
            except HttpError as error:
                self.fail(error.code, str(error))
            except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as error:
                self.fail(400, str(error))
            except Exception as error:
                self.fail(500, f"{type(error).__name__}: {error}")

        # ---- GET handlers ----
        def static(self, name: str) -> None:
            path = STATIC / name
            self.send_body(200, path.read_bytes(), "text/html; charset=utf-8",
                           {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; media-src 'self'; "
                                                       "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                                                       "frame-ancestors 'none'"})

        def log_tail(self, job: Job, query: dict) -> dict:
            run_id = query.get("run") or job.state()["run"].get("id")
            if not run_id or not re.fullmatch(r"[0-9]{8}-[0-9]{6}(-[0-9]{1,3})?", run_id):
                return {"run": None, "text": "", "offset": 0, "size": 0}
            path = job.root / "runs" / f"{run_id}.log"
            if not path.is_file():
                path = job.root / "runs" / f"{run_id}.out"
            if not path.is_file():
                return {"run": run_id, "text": "", "offset": 0, "size": 0}
            size = path.stat().st_size
            offset = int(query.get("offset") or 0)
            if offset < 0 or offset > size:
                offset = 0
            start = max(offset, size - 256 * 1024) if offset == 0 else offset
            with open(path, "rb") as handle:
                handle.seek(start)
                chunk = handle.read(512 * 1024)
            return {"run": run_id, "text": chunk.decode("utf-8", errors="replace"), "offset": start + len(chunk),
                    "size": size, "truncated": start > 0 and offset == 0}

        def resolve(self, job: Job, rel: str) -> Path:
            if rel == "source":
                return job.source
            if not rel or rel.startswith("/") or "\0" in rel:
                raise HttpError(400, "Bad path")
            path = (job.root / rel).resolve()
            root = job.root.resolve()
            if root not in path.parents:
                raise HttpError(403, "Outside the job folder")
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                raise HttpError(403, "Hidden file")
            return path

        def serve_file(self, job: Job, rel: str) -> None:
            path = self.resolve(job, rel)
            if not path.is_file():
                raise HttpError(404, "File not found")
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/json", "application/x-ndjson"):
                ctype = ("text/plain" if ctype == "text/markdown" else ctype) + "; charset=utf-8"
            size = path.stat().st_size
            start, end, code = 0, size - 1, 200
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
            if match and size:
                first, last = match.groups()
                if first:
                    start, end = int(first), min(int(last), size - 1) if last else size - 1
                elif last:
                    start, end = max(0, size - int(last)), size - 1
                if start > end or start >= size:
                    self.send_body(416, b"", "text/plain", {"Content-Range": f"bytes */{size}"})
                    return
                code = 206
            length = end - start + 1 if size else 0
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "sandbox")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD" or not length:
                return
            with open(path, "rb") as handle:
                handle.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = handle.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def browse(self, folder: str | None) -> dict:
            roots = media_roots()
            if not folder:
                return {"dir": None, "roots": [str(r) for r in roots], "dirs": [str(r) for r in roots], "videos": []}
            path = Path(folder).expanduser().resolve()
            if not any(path == r or r in path.parents for r in roots):
                raise HttpError(403, "Thư mục nằm ngoài HARNESS_MEDIA_DIRS")
            if not path.is_dir():
                raise HttpError(404, "Không có thư mục")
            dirs, videos = [], []
            try:
                entries = sorted(path.iterdir(), key=lambda p: p.name.lower())
            except PermissionError:
                raise HttpError(403, "Không có quyền đọc thư mục")
            for entry in entries[:2000]:
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    dirs.append(str(entry))
                elif entry.suffix.lower() in VIDEO_EXTENSIONS:
                    videos.append({"path": str(entry), "name": entry.name, "size": entry.stat().st_size})
            parent = str(path.parent) if any(path.parent == r or r in path.parent.parents for r in roots) else None
            return {"dir": str(path), "parent": parent, "roots": [str(r) for r in roots], "dirs": dirs, "videos": videos}

        # ---- POST handlers ----
        def create(self, data: dict) -> dict:
            overrides: dict = {}
            if data.get("voice"):
                if data["voice"] not in VOICES:
                    raise ValueError("voice không hợp lệ")
                overrides.setdefault("tts", {})["voice"] = data["voice"]
            for stage, engines in (("read", READ_ENGINES), ("write", WRITE_ENGINES)):
                engine = data.get(f"{stage}_engine")
                if engine:
                    if engine not in engines:
                        raise ValueError(f"{stage} engine không hợp lệ")
                    overrides.setdefault("agents", {}).setdefault(stage, {})["engine"] = engine
            job = Job.create(str(data.get("job", "")), str(data.get("video", "")), title=str(data.get("title", ""))[:200],
                             overrides=overrides or None)
            if data.get("start"):
                procs.start(job, end="read" if "read" in job.config().get("gates", []) else None)
            return {"job": job.slug}

        def run_job(self, job: Job, data: dict) -> dict:
            run_id = procs.start(job, start=data.get("from") or None, end=data.get("to") or None,
                                 only=data.get("only") or None, force=bool(data.get("force")))
            return {"run": run_id}

        def stop_job(self, job: Job, data: dict) -> dict:
            return {"stopped": procs.stop(job)}

        def gate(self, job: Job, data: dict) -> dict:
            stage = data.get("stage")
            if stage not in ("read", "write"):
                raise ValueError("stage phải là read hoặc write")
            note = str(data.get("note") or "")[:4000]
            approved = bool(data.get("approved"))
            if not approved and not note.strip():
                raise ValueError("Từ chối cần ghi lý do (agent sẽ đọc lý do này khi làm lại)")
            gate = job.set_gate(stage, approved, note=note, by="dashboard")
            started = None
            if data.get("continue") and approved:
                started = procs.start(job)
            return {"gate": gate, "run": started}

        def config(self, job: Job, data: dict) -> dict:
            overrides: dict = {}
            if "voice" in data:
                if data["voice"] not in VOICES:
                    raise ValueError("voice không hợp lệ")
                overrides["tts"] = {"voice": data["voice"]}
            for stage, engines in (("read", READ_ENGINES), ("write", WRITE_ENGINES)):
                block = data.get(stage) or {}
                if not block:
                    continue
                out = {}
                if "engine" in block:
                    if block["engine"] not in engines:
                        raise ValueError(f"{stage}.engine không hợp lệ")
                    out["engine"] = block["engine"]
                if "model" in block:
                    if block["model"] and not MODEL_RX.match(block["model"]):
                        raise ValueError("Tên model không hợp lệ")
                    out["model"] = block["model"]
                if "effort" in block:
                    if block["effort"] not in ("", "low", "medium", "high", "xhigh", "max"):
                        raise ValueError("effort không hợp lệ")
                    out["effort"] = block["effort"]
                overrides.setdefault("agents", {})[stage] = out
            if "gates" in data:
                gates = data["gates"]
                if not isinstance(gates, list) or any(g not in ("read", "write") for g in gates):
                    raise ValueError("gates không hợp lệ")
                overrides["gates"] = sorted(set(gates), key=("read", "write").index)
            if "revise_rounds" in data:
                rounds = int(data["revise_rounds"])
                if not 0 <= rounds <= 5:
                    raise ValueError("revise_rounds 0-5")
                overrides.setdefault("agents", {})["revise_rounds"] = rounds
            if "watermark" in data:
                overrides.setdefault("render", {}).setdefault("picture_style", {})["watermark"] = str(data["watermark"])[:60]
            if "subtitles" in data:
                overrides["subtitle"] = {"enabled": bool(data["subtitles"])}
            if "background_volume" in data:
                volume = float(data["background_volume"])
                if not 0 <= volume <= 1:
                    raise ValueError("background_volume 0-1")
                overrides.setdefault("audio", {})["background_volume"] = volume
            if not overrides:
                raise ValueError("Không có thay đổi")
            job.write_overrides(overrides)
            job.event("config", by="dashboard", changes=overrides)
            return {"ok": True}

        def upload(self, job: Job, data: dict) -> dict:
            kind, content = data.get("kind"), data.get("content")
            if kind not in ("timeline", "review") or not isinstance(content, str) or not content.strip():
                raise ValueError("kind: timeline|review và content không rỗng")
            if kind == "review":
                json.loads(content)  # reject non-JSON before it lands on disk
            from harness.pipeline.stages import _backup
            target = job.timeline if kind == "timeline" else job.review
            target.parent.mkdir(parents=True, exist_ok=True)
            _backup(target)
            target.write_text(content, encoding="utf-8")
            stage = "read" if kind == "timeline" else "write"
            job.update_stage(stage, status="pending", message="Đã dán file tay, bấm Chạy để kiểm tra", needs_input=None)
            job.event("upload", stage=stage, by="dashboard", bytes=len(content))
            return {"ok": True}

        def reset(self, job: Job, data: dict) -> dict:
            stage = data.get("stage")
            from harness.pipeline.job import STAGE_IDS
            if stage not in STAGE_IDS:
                raise ValueError("stage không hợp lệ")
            from harness.pipeline.runner import is_running
            if is_running(job):
                raise RuntimeError("Đang chạy, dừng trước")
            job.reset_stage(stage)
            job.event("reset", stage=stage, by="dashboard")
            return {"ok": True}

        def archive(self, job: Job, data: dict) -> dict:
            if data.get("confirm") != job.slug:
                raise ValueError("Gõ đúng tên job để xác nhận")
            from harness.pipeline.runner import is_running
            if is_running(job):
                raise RuntimeError("Đang chạy, dừng trước")
            target = job.archive()
            return {"archived": str(target)}

    return Handler


def main(host: str | None = None, port: int | None = None, open_browser: bool = False,
         allow_hosts: list[str] | None = None) -> int:
    host = host or os.environ.get("HARNESS_HOST") or "127.0.0.1"
    port = port or int(os.environ.get("HARNESS_PORT") or DEFAULT_PORT)
    allowed = set(LOOPBACK)
    allowed |= {h.strip().lower() for h in (allow_hosts or os.environ.get("HARNESS_ALLOW_HOSTS", "").split(",")) if h.strip()}
    if host not in LOOPBACK and host not in ("0.0.0.0", "::"):
        allowed.add(host.lower())
    if host in ("0.0.0.0", "::"):
        print("Cảnh báo: dashboard không có đăng nhập; mở ra mạng thì ai vào được cổng này cũng chạy được job. "
              "Nên dùng SSH tunnel: ssh -L 8790:127.0.0.1:8790 <máy>", file=sys.stderr)
    try:
        httpd = ThreadingHTTPServer((host, port), make_handler(allowed))
    except OSError as error:
        print(f"Không mở được {host}:{port}: {error}. Cổng đang bận? Đổi bằng --port hoặc HARNESS_PORT.", file=sys.stderr)
        return 2
    httpd.daemon_threads = True
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}/"
    print(f"Review harness dashboard: {url}  (Ctrl+C để tắt)", flush=True)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
