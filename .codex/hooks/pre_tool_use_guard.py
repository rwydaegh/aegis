#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RM_LOCK_FILE = REPO_ROOT / ".rm_confirmed"
GIT_LOCK_FILE = REPO_ROOT / ".git_destructive_confirmed"


def load_command() -> str:
    try:
        payload = json.load(__import__("sys").stdin)
    except json.JSONDecodeError:
        return ""
    return str(payload.get("tool_input", {}).get("command", ""))


def block(message: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    }
    print(json.dumps(payload))


def allow() -> None:
    print("{}")


def main() -> None:
    command = load_command()

    rm_rf = re.search(r"\brm\s+.*-(?:[A-Za-z]*r[A-Za-z]*f|[A-Za-z]*f[A-Za-z]*r)\b", command)
    if rm_rf:
        if RM_LOCK_FILE.exists():
            RM_LOCK_FILE.unlink()
            allow()
            return
        block(
            "BLOCKED: rm -rf detected. If deletion is truly intended, run "
            f"'touch {RM_LOCK_FILE}' and retry the exact same command. "
            "Ask Robin first if uncommitted work, user content, dotfiles, or out-of-repo paths are involved."
        )
        return

    destructive_patterns = [
        (r"\bgit\s+clean\s+.*-[A-Za-z]*f\b", "git clean -f deletes untracked files permanently"),
        (r"\bgit\s+checkout\s+--\s+\.", "git checkout -- . discards uncommitted changes"),
        (r"\bgit\s+reset\s+--hard\b", "git reset --hard discards uncommitted changes"),
        (r"\bgit\s+restore\s+\.", "git restore . discards uncommitted changes"),
        (r"\bgit\s+stash\s+(?:drop|clear)\b", "git stash drop/clear permanently deletes stashed work"),
        (r"\bgit\s+push\s+.*--force\b", "git push --force can overwrite remote history"),
    ]
    for pattern, reason in destructive_patterns:
        if re.search(pattern, command):
            if GIT_LOCK_FILE.exists():
                GIT_LOCK_FILE.unlink()
                allow()
                return
            block(
                f"BLOCKED: Destructive git command detected. {reason}. "
                "Run 'git status' first, verify what would be lost, then run "
                f"'touch {GIT_LOCK_FILE}' and retry if you truly intend it."
            )
            return

    allow()


if __name__ == "__main__":
    main()
