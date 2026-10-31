"""Prepare and deliver a scoped READ request through the running Antigravity Desktop UI.

Uses its existing loopback CDP endpoint and visible DOM only. No credential reads,
private inference API, permission changes, or automatic confirmation of app dialogs.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.video.probe import probe_video
from src.pipeline.editorial import EditorialPolicy
from src.pipeline.build_review import load_config


def job_paths(job: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", job):
        raise ValueError("job must be a simple lowercase name, e.g. moana")
    folder = (ROOT / "data/handoff" / job).resolve()
    output = (ROOT / "data/timeline" / job / "timeline.md").resolve()
    if not folder.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError("Handoff paths must remain inside the project")
    return folder, output


def save_manifest(folder: Path, manifest: dict) -> None:
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare(video: str, job: str) -> tuple[Path, dict]:
    folder, output = job_paths(job)
    source = Path(video).resolve()
    if not source.is_file() or not source.is_relative_to(ROOT / "input/videos"):
        raise ValueError("Source must be an existing file inside this project's input/videos")
    if (folder / "manifest.json").exists():
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["source_video"] != str(source):
            raise ValueError("Job belongs to another source; choose a different --job")
        return folder, manifest
    if output.exists():
        raise FileExistsError(f"Preserve existing timeline; use a new job: {output}")
    metadata = probe_video(source)
    policy = EditorialPolicy.model_validate(load_config(ROOT / "config/config.yaml")["editorial"])
    budget = policy.budget(metadata["duration"])
    request_id = f"{job}-{uuid4().hex[:12]}"
    values = dict(metadata, **{k:v for k,v in budget.items() if k not in metadata},
                  request_id=request_id, project=str(ROOT), source_video=str(source),
                  source_video_yaml=json.dumps(str(source), ensure_ascii=False),
                  source_size_bytes=source.stat().st_size,
                  output_directory=str(output.parent), output_file=str(output))
    content = (ROOT / "prompts/antigravity_read.md").read_text(encoding="utf-8").format(**values)
    folder.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    request = folder / "request.md"
    request.write_text(content, encoding="utf-8")
    manifest = {"request_id": request_id, "job": job, "source_video": str(source),
                "source_size_bytes": source.stat().st_size, "source_mtime_ns": source.stat().st_mtime_ns,
                "metadata": metadata, "budget": budget, "request_file": str(request),
                "output_file": str(output), "delivery_status": "prepared",
                "created_at": datetime.now(timezone.utc).isoformat()}
    save_manifest(folder, manifest)
    return folder, manifest


class DesktopUI:
    def __init__(self):
        self.sequence = 0

    async def __aenter__(self):
        port_file = Path(os.environ.get("APPDATA", "")) / "Antigravity/DevToolsActivePort"
        if not port_file.is_file():
            raise RuntimeError("Open Antigravity Desktop and sign in first; no local UI endpoint found")
        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        if not 1 <= port <= 65535:
            raise RuntimeError("Invalid Antigravity local UI port")
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        try:
            async with self.session.get(f"http://127.0.0.1:{port}/json/list") as response:
                response.raise_for_status()
                targets = await response.json()
            pages = [t for t in targets if t.get("type") == "page"
                     and urlparse(t.get("url", "")).hostname in ("127.0.0.1", "localhost")]
            # The title becomes the conversation name after the first message.
            if len(pages) != 1:
                raise RuntimeError("Expected one Antigravity window; close extra windows before handoff")
            target = pages[0]
            if urlparse(target["webSocketDebuggerUrl"]).hostname not in ("127.0.0.1", "localhost"):
                raise RuntimeError("Refusing a non-loopback UI endpoint")
            self.ws = await self.session.ws_connect(target["webSocketDebuggerUrl"])
        except Exception as error:
            await self.session.close()
            raise RuntimeError("Antigravity UI unavailable. Open the Desktop app; do not use language_server.exe as a chat CLI.") from error
        return self

    async def __aexit__(self, *args):
        await self.ws.close()
        await self.session.close()

    async def call(self, method: str, params: dict) -> dict:
        self.sequence += 1
        await self.ws.send_json({"id": self.sequence, "method": method, "params": params})
        while True:
            message = await self.ws.receive(timeout=15)
            if message.type != aiohttp.WSMsgType.TEXT:
                raise RuntimeError("Antigravity UI connection closed")
            data = json.loads(message.data)
            if data.get("id") == self.sequence:
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                return data.get("result", {})

    async def evaluate(self, expression: str):
        result = await self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        if result.get("exceptionDetails"):
            raise RuntimeError("UI structure changed or a required control is missing")
        return result.get("result", {}).get("value")


async def send(folder: Path, manifest: dict) -> None:
    if manifest["delivery_status"] != "prepared":
        raise RuntimeError("This request was already submitted or delivery is uncertain. Check the app; do not send duplicates.")
    source = Path(manifest["source_video"])
    if source.stat().st_size != manifest["source_size_bytes"] or source.stat().st_mtime_ns != manifest["source_mtime_ns"]:
        raise RuntimeError("Source changed after prepare; create a new job")
    marker = f"READ request {manifest['request_id']}"
    prompt = (f"{marker}\n"
              f"Người dùng giao bạn phân tích video local. Đọc toàn bộ file yêu cầu: {manifest['request_file']}\n"
              f"Video nguồn: {manifest['source_video']}\n"
              f"Trả file Markdown UTF-8 thật tại: {manifest['output_file']}\n"
              "Thực hiện READ theo contract trong request.md. Chỉ ghi trong thư mục đích của job; "
              "không sửa code, không ghi đè phim/timeline khác, không cài package hay dùng API key. "
              "Nếu không đọc đủ video/âm thanh, ghi status partial/blocked trung thực; không suy đoán từ tên phim. "
              "Không cần xác nhận lại yêu cầu READ; nếu ứng dụng cần đăng nhập/quyền truy cập thì báo rõ.")
    async with DesktopUI() as ui:
        state = await ui.evaluate("""JSON.stringify({
            draft:document.querySelector('[aria-label="Message input"][contenteditable="true"]')?.innerText,
            canStart:!!document.querySelector('[data-testid="new-conversation-button"]')})""")
        state = json.loads(state)
        if state.get("draft", "").strip():
            raise RuntimeError("An existing draft is open; preserve it before sending a new job")
        if not state["canStart"]:
            raise RuntimeError("Antigravity is not ready; sign in or complete required app setup")
        await ui.evaluate("""document.querySelector('[data-testid="new-conversation-button"]').click()""")
        for _ in range(30):
            ready = await ui.evaluate("""!!document.querySelector('[aria-label="Message input"][contenteditable="true"]')""")
            if ready:
                break
            await asyncio.sleep(.2)
        else:
            raise RuntimeError("No message editor found")
        await ui.evaluate("""document.querySelector('[aria-label="Message input"][contenteditable="true"]').focus()""")
        await ui.call("Input.insertText", {"text": prompt})
        for _ in range(30):
            enabled = await ui.evaluate("""(()=>{const b=document.querySelector('button[aria-label="Send message"]');return !!b && !b.disabled})()""")
            if enabled:
                break
            await asyncio.sleep(.2)
        else:
            raise RuntimeError("Send is disabled; no request was submitted")
        # Persist uncertain before clicking: a crash must not cause duplicate submissions.
        manifest["delivery_status"] = "submission_in_progress"
        save_manifest(folder, manifest)
        await ui.evaluate("""document.querySelector('button[aria-label="Send message"]').click()""")
        for _ in range(60):
            confirmation = json.loads(await ui.evaluate("""JSON.stringify({
                draft:document.querySelector('[aria-label="Message input"][contenteditable="true"]')?.innerText || '',
                text:document.body.innerText, path:location.pathname})"""))
            if not confirmation["draft"].strip() and marker in confirmation["text"] and confirmation["path"] != "/":
                manifest.update(delivery_status="ui_submitted", submitted_at=datetime.now(timezone.utc).isoformat(),
                                conversation_path=confirmation["path"])
                save_manifest(folder, manifest)
                print("UI_SUBMITTED:", manifest["request_id"])
                print("Expected output:", manifest["output_file"])
                return
            await asyncio.sleep(.25)
        raise RuntimeError("Submission not confirmed; inspect the app before retrying. No completion is claimed.")


def check(job: str) -> int:
    folder, output = job_paths(job)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if not output.exists():
        print(f"WAITING: {output}; delivery={manifest['delivery_status']}")
        return 2
    content = output.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", content, re.S)
    if not match:
        raise ValueError("Returned file is missing required YAML front matter")
    header = yaml.safe_load(match.group(1))
    if header.get("request_id") != manifest["request_id"]:
        raise ValueError("Timeline request_id mismatch; do not use another film/job")
    if Path(header.get("source_video", "")).resolve() != Path(manifest["source_video"]):
        raise ValueError("Timeline source mismatch")
    if abs(float(header.get("source_duration_seconds", 0)) - manifest["metadata"]["duration"]) > .1:
        raise ValueError("Timeline duration mismatch")
    status = header.get("analysis_status")
    if status not in ("complete", "partial", "blocked"):
        raise ValueError("Invalid analysis_status")
    print(f"RETURNED_{status.upper()}: {output}")
    print("Manual content/timestamp review is required before WRITE/render.")
    return 0 if status == "complete" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare/send a scoped Antigravity READ job; verify its Markdown return.")
    parser.add_argument("--video")
    parser.add_argument("--job", required=True)
    parser.add_argument("--send", action="store_true", help="Submit through the running Desktop UI")
    parser.add_argument("--check", action="store_true", help="Read returned timeline; no external action")
    args = parser.parse_args()
    try:
        if args.check:
            if args.send:
                raise ValueError("--check and --send are mutually exclusive")
            return check(args.job)
        if not args.video:
            raise ValueError("--video is required to prepare/send")
        folder, manifest = prepare(args.video, args.job)
        print("Request:", manifest["request_file"])
        print("Output:", manifest["output_file"])
        if args.send:
            asyncio.run(send(folder, manifest))
        return 0
    except Exception as error:
        print(f"Handoff failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
