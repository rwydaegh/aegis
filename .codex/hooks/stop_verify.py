#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def git_status_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def main() -> None:
    try:
        payload = json.load(__import__("sys").stdin)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return

    if payload.get("stop_hook_active"):
        print(json.dumps({"continue": True}))
        return

    if not git_status_dirty():
        print(json.dumps({"continue": True}))
        return

    message = str(payload.get("last_assistant_message") or "")
    message_lc = message.lower()
    completion_pattern = re.compile(
        r"\b(done|complete|completed|fixed|implemented|ready|passing|all tests pass|ported)\b"
    )
    verification_pattern = re.compile(
        r"\b(pytest|ruff|npm test|npm run build|npm run lint|verified|verification|tested|lint|build)\b"
    )

    if not completion_pattern.search(message_lc):
        print(json.dumps({"continue": True}))
        return

    if verification_pattern.search(message_lc):
        print(json.dumps({"continue": True}))
        return

    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "Before closing out, run fresh project-appropriate verification and report the result. "
                    "At minimum inspect the current diff and run the relevant tests, lint, or build commands "
                    "for the files you changed."
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
