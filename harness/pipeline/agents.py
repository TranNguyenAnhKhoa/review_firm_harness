"""Run READ/WRITE through an agent CLI in print mode and keep its stream as a log.

    claude  Claude Code  (claude -p, stream-json). Sees images (frame sheets), not video.
    agy     Antigravity  (agy -p, stream-json).  Its read_file tool views video files (Gemini).
    codex   Codex CLI    (codex exec --json).    Sees images passed with -i.

The prompt goes in on stdin (claude, codex) or as the argument (agy). Every CLI runs from the harness
root, so AGENTS.md / CLAUDE.md apply, with the job folder as its only writable target. No tool
permits a shell command except claude's `./run.sh frame` and `./run.sh check` helpers.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from harness import ROOT
from harness.utils import executable

# Variables that tie a process to the Claude Code session that may have launched the harness.
SESSION_VARS = re.compile(r"^(CLAUDECODE|CLAUDE_CODE_[A-Z_]+|CLAUDE_AGENT_SDK[A-Z_]*|CLAUDE_PID|CLAUDE_EFFORT)$")
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\[\]-]{0,80}$")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


@dataclass
class AgentResult:
    engine: str
    exit_code: int
    seconds: float
    text: str = ""
    usage: dict = field(default_factory=dict)
    cost_usd: float | None = None
    denied: list = field(default_factory=list)
    error: str = ""

    def summary(self) -> dict:
        return {"engine": self.engine, "exit_code": self.exit_code, "seconds": round(self.seconds, 1),
                "usage": self.usage, "cost_usd": self.cost_usd, "denied": self.denied, "error": self.error}


class AgentError(RuntimeError):
    pass


def clean_env() -> dict:
    return {k: v for k, v in os.environ.items() if not SESSION_VARS.match(k)}


def build_command(engine: str, settings: dict, *, model: str = "", effort: str = "", job_root: Path,
                  images: list[Path] = ()) -> tuple[list[str], bool]:
    """Return (argv, prompt_via_stdin). Raise ValueError on an unknown engine or unsafe value."""
    if model and not MODEL.match(model):
        raise ValueError(f"Invalid model name {model!r}")
    if effort and effort not in EFFORTS:
        raise ValueError(f"effort must be one of {', '.join(EFFORTS)}")
    conf = settings.get(engine, {})
    if engine == "claude":
        tools = list(conf.get("tools") or ["Read", "Write", "Edit", "Glob", "Grep"])
        tools += ["Bash(./run.sh frame:*)", "Bash(./run.sh check:*)"]
        argv = [executable(conf.get("bin", "claude")), "-p", "--output-format", "stream-json", "--verbose",
                "--allowedTools", ",".join(tools), "--strict-mcp-config", "--setting-sources", "project,local",
                "--add-dir", str(job_root)]
        argv += ["--model", model] if model else []
        argv += ["--effort", effort] if effort else []
        return argv, True
    if engine == "agy":
        argv = [executable(conf.get("bin", "agy")), "--output-format", "stream-json", "--mode", "accept-edits",
                "--add-dir", str(job_root)]
        argv += ["--model", model] if model else []
        argv += ["--effort", effort] if effort else []
        return argv + ["-p"], False
    if engine == "codex":
        argv = [executable(conf.get("bin", "codex")), "exec", "--json", "--skip-git-repo-check",
                "-s", conf.get("sandbox", "workspace-write"), "-C", str(ROOT)]
        argv += ["-m", model] if model else []
        for image in images:
            argv += ["-i", str(image)]
        return argv + ["-"], True
    raise ValueError(f"Unknown agent engine {engine!r}")


def _describe(engine: str, event: dict) -> str | None:
    """One readable line for the live log, or None to stay quiet."""
    if engine == "claude":
        kind = event.get("type")
        if kind == "assistant":
            parts = []
            for item in event.get("message", {}).get("content", []):
                if item.get("type") == "text" and item.get("text", "").strip():
                    parts.append(item["text"].strip().replace("\n", " ")[:220])
                elif item.get("type") == "tool_use":
                    data = item.get("input", {})
                    target = data.get("file_path") or data.get("path") or data.get("pattern") or data.get("command") or ""
                    parts.append(f"[{item.get('name')}] {str(target)[:160]}")
            return " | ".join(parts) or None
        if kind == "result":
            return f"[result] {event.get('subtype')} turns={event.get('num_turns')} cost=${event.get('total_cost_usd') or 0:.3f}"
        return None
    if engine == "agy":
        if "step_update" in event:
            step = event["step_update"]
            if step.get("step_type") == "tool" and step.get("state") == "ACTIVE":
                params = (step.get("tool_info") or {}).get("parameters") or {}
                target = params.get("Path") or params.get("CommandLine") or params.get("TargetFile") or ""
                return f"[{step.get('tool_name')}] {str(target)[:160]}"
            return None
        if "result" in event:
            res = event["result"]
            return f"[result] {res.get('status')} turns={res.get('num_turns')} tokens={(res.get('usage') or {}).get('total_tokens')}"
        return None
    if engine == "codex":
        item = event.get("item") or {}
        if event.get("type") == "item.completed":
            if item.get("type") == "agent_message":
                return (item.get("text") or "").replace("\n", " ")[:220] or None
            if item.get("type") in ("command_execution", "file_change"):
                return f"[{item.get('type')}] {str(item.get('command') or item.get('changes') or '')[:160]}"
        if event.get("type") == "turn.completed":
            return f"[result] tokens={event.get('usage')}"
    return None


def _absorb(engine: str, event: dict, result: AgentResult) -> None:
    if engine == "claude" and event.get("type") == "result":
        result.text = event.get("result") or ""
        result.cost_usd = event.get("total_cost_usd")
        usage = event.get("usage") or {}
        result.usage = {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                        "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                        "cache_write_tokens": usage.get("cache_creation_input_tokens", 0)}
        result.usage["total_tokens"] = (result.usage["input_tokens"] + result.usage["output_tokens"]
                                        + result.usage["cache_write_tokens"])
        if event.get("is_error"):
            result.error = result.text[:500] or str(event.get("subtype"))
        result.denied = [d.get("tool_name") for d in event.get("permission_denials") or []]
    elif engine == "agy" and "result" in event:
        res = event["result"]
        result.text = res.get("response") or ""
        usage = res.get("usage") or {}
        result.usage = {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                        "thinking_tokens": usage.get("thinking_tokens", 0),
                        "cache_read_tokens": usage.get("cache_read_tokens", 0),
                        "total_tokens": usage.get("total_tokens") or usage.get("input_tokens", 0) + usage.get("output_tokens", 0)}
        result.denied = [d.get("display_name") or d.get("action") for d in res.get("denied_actions") or []]
        if res.get("status") != "SUCCESS":
            result.error = str(res.get("status"))
    elif engine == "codex":
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or {}
            for key, value in usage.items():
                result.usage[key] = result.usage.get(key, 0) + (value or 0)
            result.usage["total_tokens"] = result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0)
        elif event.get("type") == "item.completed" and (event.get("item") or {}).get("type") == "agent_message":
            result.text = event["item"].get("text") or ""
        elif event.get("type") in ("error", "turn.failed"):
            result.error = str(event.get("message") or event.get("error"))[:500]


def run_agent(engine: str, prompt: str, *, settings: dict, model: str = "", effort: str = "",
              job_root: Path, log_path: Path, timeout_minutes: float = 60, images: list[Path] = (),
              echo=print) -> AgentResult:
    argv, via_stdin = build_command(engine, settings, model=model, effort=effort, job_root=job_root, images=images)
    if not via_stdin:
        argv = argv + [prompt]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    echo(f"Agent {engine}{' / ' + model if model else ''}: started (log {log_path.relative_to(job_root)})")
    started = time.monotonic()
    result = AgentResult(engine=engine, exit_code=-1, seconds=0)
    deadline = started + timeout_minutes * 60
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(argv, cwd=ROOT, env=clean_env(), stdin=subprocess.PIPE if via_stdin else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                errors="replace", bufsize=1)
        try:
            if via_stdin:
                proc.stdin.write(prompt)
                proc.stdin.close()
            for line in proc.stdout:
                log.write(line)
                log.flush()
                if time.monotonic() > deadline:
                    raise AgentError(f"{engine} exceeded {timeout_minutes:g} min timeout")
                text = line.strip()
                if not text:
                    continue
                try:
                    event = json.loads(text)
                except ValueError:
                    echo(f"  {engine}: {text[:240]}")
                    continue
                if isinstance(event, dict):
                    _absorb(engine, event, result)
                    line_text = _describe(engine, event)
                    if line_text:
                        echo(f"  {line_text}")
            result.exit_code = proc.wait(timeout=max(1, deadline - time.monotonic()))
            proc.stdout.close()
        except subprocess.TimeoutExpired:
            result.error = f"{engine} exceeded {timeout_minutes:g} min timeout"
        except AgentError as error:
            result.error = str(error)
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                result.exit_code = proc.returncode if proc.returncode is not None else -9
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
    result.seconds = time.monotonic() - started
    if result.exit_code and not result.error:
        result.error = f"{engine} exited with code {result.exit_code}"
    echo(f"Agent {engine}: finished in {result.seconds:.0f}s, exit {result.exit_code}"
         + (f", cost ${result.cost_usd:.3f}" if result.cost_usd else "")
         + (f", denied {result.denied}" if result.denied else ""))
    return result
