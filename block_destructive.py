#!/usr/bin/env python3
"""Claude Code PreToolUse hook that blocks destructive Bash commands.

The hook deliberately makes no decision for commands it does not recognize.
Claude Code can then apply its normal permission flow.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_RM_RF = re.compile(r"(?<![\w-])rm(?:\s+|\s+-[A-Za-z]*)(?:-[A-Za-z]*\s+)*-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*(?:\s|$)", re.IGNORECASE)
_RM_FLAGS = re.compile(r"(?<![\w-])rm\s+(?P<flags>(?:-[A-Za-z]+\s+)+)", re.IGNORECASE)
_DROP_TABLE = re.compile(r"\bdrop\s+table\b", re.IGNORECASE)
_FORCE_PUSH = re.compile(r"\bgit\s+push\b[^;&|\n]*(?:--force(?:-with-lease)?|(?<![\w-])-f(?![\w-]))", re.IGNORECASE)
_TRUNCATE = re.compile(r"\btruncate(?:\s+table)?\b", re.IGNORECASE)
_DELETE_FROM = re.compile(r"\bdelete\s+from\b", re.IGNORECASE)
_WHERE = re.compile(r"\bwhere\b", re.IGNORECASE)


def _rm_rf(command: str) -> bool:
    """Return whether a command invokes rm with both recursive and force flags."""
    if _RM_RF.search(command):
        return True
    for match in _RM_FLAGS.finditer(command):
        flags = "".join(match.group("flags").split())
        if "r" in flags.lower() and "f" in flags.lower():
            return True
    return False


def _delete_without_where(command: str) -> bool:
    """Find a DELETE statement that has no WHERE clause in that statement."""
    for match in _DELETE_FROM.finditer(command):
        statement = command[match.start() :]
        statement = re.split(r"[;\n]", statement, maxsplit=1)[0]
        if not _WHERE.search(statement):
            return True
    return False


def reason_for(command: str) -> str | None:
    """Return a human-readable block reason, or None for a safe command."""
    checks = (
        (_rm_rf(command), "blocked rm -rf: recursive forced deletion is not allowed"),
        (_DROP_TABLE.search(command), "blocked DROP TABLE: destructive schema operation is not allowed"),
        (_FORCE_PUSH.search(command), "blocked forced git push: it can overwrite remote history"),
        (_TRUNCATE.search(command), "blocked TRUNCATE: destructive table operation is not allowed"),
        (
            _delete_without_where(command),
            "blocked DELETE FROM without WHERE: it can remove every row in a table",
        ),
    )
    for matched, reason in checks:
        if matched:
            return reason
    return None


def _hooks_dir() -> Path:
    """Return the hook directory, with a test-only override."""
    override = os.environ.get("CLAUDE_HOOKS_DIR")
    return Path(override).expanduser() if override else Path.home() / ".claude" / "hooks"


def _project_path(payload: dict[str, Any]) -> str:
    value = payload.get("cwd") or payload.get("project_dir") or os.environ.get("CLAUDE_PROJECT_DIR")
    return str(value or Path.cwd())


def _log_block(payload: dict[str, Any], command: str) -> None:
    hooks_dir = _hooks_dir()
    hooks_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = json.dumps(
        {
            "timestamp": timestamp,
            "command": command,
            "project_path": _project_path(payload),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    with (hooks_dir / "blocked.log").open("a", encoding="utf-8") as log:
        log.write(line + "\n")


def _decision(reason: str) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        return 0

    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0

    reason = reason_for(command)
    if reason is None:
        return 0

    _log_block(payload, command)
    print(_decision(reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
