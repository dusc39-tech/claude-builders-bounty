import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "block_destructive.py"


def run_hook(command: str, hooks_dir: str, cwd: str = "/tmp/demo-project") -> subprocess.CompletedProcess[str]:
    payload = {
        "cwd": cwd,
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    env = os.environ.copy()
    env["CLAUDE_HOOKS_DIR"] = hooks_dir
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class DestructiveHookTests(unittest.TestCase):
    def test_blocks_required_patterns_and_logs_context(self):
        commands = [
            "rm -rf build",
            "DROP TABLE accounts",
            "git push --force origin main",
            "TRUNCATE TABLE events",
            "DELETE FROM users",
        ]
        with tempfile.TemporaryDirectory() as hooks_dir:
            for command in commands:
                result = run_hook(command, hooks_dir)
                self.assertEqual(result.returncode, 0)
                decision = json.loads(result.stdout)
                self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("blocked", decision["hookSpecificOutput"]["permissionDecisionReason"])

            log_lines = (Path(hooks_dir) / "blocked.log").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(log_lines), len(commands))
            entries = [json.loads(line) for line in log_lines]
            self.assertEqual([entry["command"] for entry in entries], commands)
            self.assertTrue(all(entry["project_path"] == "/tmp/demo-project" for entry in entries))
            self.assertTrue(all(entry["timestamp"] for entry in entries))

    def test_allows_normal_commands(self):
        safe_commands = [
            "rm file.txt",
            "rm -r build",
            "git push origin main",
            "DELETE FROM users WHERE id = 1",
            "python -m unittest",
        ]
        with tempfile.TemporaryDirectory() as hooks_dir:
            for command in safe_commands:
                result = run_hook(command, hooks_dir)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
            self.assertFalse((Path(hooks_dir) / "blocked.log").exists())

    def test_delete_where_is_checked_per_statement(self):
        with tempfile.TemporaryDirectory() as hooks_dir:
            allowed = run_hook("DELETE FROM users WHERE id = 1; SELECT 1", hooks_dir)
            blocked = run_hook("DELETE FROM users; SELECT 1 WHERE id = 1", hooks_dir)
            self.assertEqual(allowed.stdout, "")
            self.assertIn("permissionDecision", blocked.stdout)

    def test_malformed_or_missing_input_is_a_noop(self):
        with tempfile.TemporaryDirectory() as hooks_dir:
            env = os.environ.copy()
            env["CLAUDE_HOOKS_DIR"] = hooks_dir
            result = subprocess.run(
                [sys.executable, str(HOOK)],
                input="not json",
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
