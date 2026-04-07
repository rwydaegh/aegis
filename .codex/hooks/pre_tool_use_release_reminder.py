#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def main() -> None:
    try:
        payload = json.load(__import__("sys").stdin)
    except json.JSONDecodeError:
        print("{}")
        return

    command = str(payload.get("tool_input", {}).get("command", ""))
    if "git commit" not in command and "git push" not in command:
        print("{}")
        return

    try:
        last_tag = git("describe", "--tags", "--abbrev=0")
        count = int(git("rev-list", "--count", f"{last_tag}..HEAD"))
    except Exception:
        print("{}")
        return

    if count <= 10:
        print("{}")
        return

    try:
        commits = git("log", "--oneline", f"{last_tag}..HEAD").splitlines()[:8]
    except Exception:
        commits = []

    summary = " | ".join(commits) if commits else "recent commits unavailable"
    message = (
        f"RELEASE REMINDER: {count} commits since {last_tag}. "
        "Consider whether a patch or minor release is warranted. "
        "If tagging, also run 'bash .claude/hooks/update-release-metadata.sh'. "
        f"Recent commits: {summary}"
    )
    print(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    main()
