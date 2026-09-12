#!/usr/bin/env python3
"""Install the destructive-command hook without discarding existing settings."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CLAUDE_DIR = Path.home() / ".claude"
HOOKS_DIR = CLAUDE_DIR / "hooks"
SETTINGS_PATH = CLAUDE_DIR / "settings.json"
HOOK_NAME = "block_destructive.py"
COMMAND = f"{HOOKS_DIR / HOOK_NAME}"


def _load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    with SETTINGS_PATH.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"{SETTINGS_PATH} must contain a JSON object")
    return value


def _install_hook(settings: dict) -> None:
    hooks = settings.setdefault("hooks", {})
    groups = hooks.setdefault("PreToolUse", [])
    if not isinstance(groups, list):
        raise ValueError("settings.hooks.PreToolUse must be a list")

    desired = {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": COMMAND}],
    }
    for group in groups:
        if isinstance(group, dict) and any(
            handler.get("command") == COMMAND
            for handler in group.get("hooks", [])
            if isinstance(handler, dict)
        ):
            return
    groups.append(desired)


def main() -> int:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    destination = HOOKS_DIR / HOOK_NAME
    shutil.copy2(ROOT / HOOK_NAME, destination)
    destination.chmod(destination.stat().st_mode | 0o111)

    settings = _load_settings()
    _install_hook(settings)
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2)
        file.write("\n")

    print(f"Installed {destination}")
    print(f"Updated {SETTINGS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
