# Installation

From this repository, run:

```sh
cp .claude/hooks/block_destructive_bash.py ~/.claude/hooks/block_destructive_bash.py && chmod +x ~/.claude/hooks/block_destructive_bash.py
```

Then add the hook entry from `.claude/settings.json` to your `~/.claude/settings.json`, or copy that file into a project as `.claude/settings.json` and run Claude Code from that project. The hook creates `~/.claude/hooks/blocked.log` on the first blocked attempt.
