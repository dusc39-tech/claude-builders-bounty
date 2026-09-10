# Installation

From this repository, run:

```sh
mkdir -p ~/.claude/hooks && cp block_destructive_bash.py ~/.claude/hooks/block_destructive_bash.py && chmod +x ~/.claude/hooks/block_destructive_bash.py
```

Then add the hook entry from `settings.json` to your `~/.claude/settings.json`, or copy that file into a project as `.claude/settings.json` while keeping the script path aligned with your project. The hook creates `~/.claude/hooks/blocked.log` on the first blocked attempt.
