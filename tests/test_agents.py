"""Agent CLI adapters: command lines, stream parsing, and a fake CLI run end to end."""
import json
import os
import stat
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.pipeline import agents


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.job = Path(tempfile.mkdtemp())
        self.settings = {"claude": {"bin": "/bin/true", "tools": ["Read", "Write"]}, "agy": {"bin": "/bin/true"},
                         "codex": {"bin": "/bin/true", "sandbox": "workspace-write"}}

    def test_claude_is_restricted_and_reads_stdin(self):
        argv, stdin = agents.build_command("claude", self.settings, model="sonnet", effort="high", job_root=self.job)
        self.assertTrue(stdin)
        tools = argv[argv.index("--allowedTools") + 1]
        self.assertEqual(tools, "Read,Write,Bash(./run.sh frame:*),Bash(./run.sh check:*)")
        self.assertIn("--strict-mcp-config", argv)
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project,local")
        self.assertEqual(argv[argv.index("--model") + 1], "sonnet")

    def test_agy_takes_prompt_argument_and_accept_edits(self):
        argv, stdin = agents.build_command("agy", self.settings, job_root=self.job)
        self.assertFalse(stdin)
        self.assertEqual(argv[-1], "-p")
        self.assertEqual(argv[argv.index("--mode") + 1], "accept-edits")
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_codex_images_and_validation(self):
        argv, stdin = agents.build_command("codex", self.settings, job_root=self.job, images=[Path("/x/a.jpg")])
        self.assertEqual(argv[argv.index("-i") + 1], "/x/a.jpg")
        self.assertEqual(argv[-1], "-")
        with self.assertRaises(ValueError):
            agents.build_command("claude", self.settings, model="bad model;rm", job_root=self.job)
        with self.assertRaises(ValueError):
            agents.build_command("gpt", self.settings, job_root=self.job)

    def test_session_variables_are_removed(self):
        with patch.dict(os.environ, {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "x", "CLAUDE_CONFIG_DIR": "/c"}):
            env = agents.clean_env()
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_CODE_ENTRYPOINT", env)
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "/c")


class StreamTests(unittest.TestCase):
    def test_parse_real_event_shapes(self):
        result = agents.AgentResult("agy", 0, 0)
        agents._absorb("agy", {"result": {"status": "SUCCESS", "response": "OK", "num_turns": 1, "usage": {
            "input_tokens": 7030, "output_tokens": 62, "thinking_tokens": 61, "cache_read_tokens": 0}}}, result)
        self.assertEqual((result.text, result.usage["input_tokens"], result.error), ("OK", 7030, ""))
        line = agents._describe("agy", {"step_update": {"step_type": "tool", "state": "ACTIVE", "tool_name": "read_file",
                                                        "tool_info": {"parameters": {"Path": "/j/proxy/part_01.mp4"}}}})
        self.assertEqual(line, "[read_file] /j/proxy/part_01.mp4")
        claude = agents.AgentResult("claude", 0, 0)
        agents._absorb("claude", {"type": "result", "subtype": "success", "result": "done", "total_cost_usd": 0.42,
                                  "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100},
                                  "permission_denials": [{"tool_name": "Bash"}]}, claude)
        self.assertEqual((claude.cost_usd, claude.usage["cache_read_tokens"], claude.denied), (0.42, 100, ["Bash"]))
        codex = agents.AgentResult("codex", 0, 0)
        agents._absorb("codex", {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 4}}, codex)
        self.assertEqual(codex.usage, {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7})

    def test_fake_cli_streams_writes_file_and_reports_usage(self):
        folder = Path(tempfile.mkdtemp())
        fake = folder / "fake_claude"
        fake.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import json, os, sys
            prompt = sys.stdin.read()
            open(os.environ["FAKE_OUT"], "w").write("got:" + prompt[:20])
            print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write", "input": {"file_path": os.environ["FAKE_OUT"]}}]}}))
            print("not json noise")
            print(json.dumps({"type": "result", "subtype": "success", "result": "ok", "total_cost_usd": 0.01, "usage": {"input_tokens": 1, "output_tokens": 2}}))
            """), encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        out = folder / "timeline.md"
        lines = []
        with patch.dict(os.environ, {"FAKE_OUT": str(out)}):
            result = agents.run_agent("claude", "hello prompt", settings={"claude": {"bin": str(fake)}},
                                      job_root=folder, log_path=folder / "agent.jsonl", echo=lines.append)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.read_text(), "got:hello prompt")
        self.assertEqual(result.cost_usd, 0.01)
        self.assertTrue(any("[Write]" in l for l in lines))
        self.assertIn("not json noise", (folder / "agent.jsonl").read_text())

    def test_nonzero_exit_is_an_error(self):
        folder = Path(tempfile.mkdtemp())
        result = agents.run_agent("claude", "x", settings={"claude": {"bin": "/bin/false"}}, job_root=folder,
                                  log_path=folder / "a.jsonl", echo=lambda _: None)
        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(result.error)


if __name__ == "__main__":
    unittest.main()
