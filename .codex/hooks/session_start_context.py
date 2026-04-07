#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    memory_index = Path.home() / ".claude/projects/-home-user-aegis/memory/MEMORY.md"

    lines = [
        "AEGIS Codex port active.",
        "",
        "Project-scoped Codex assets:",
        f"- Skills: {repo_root / '.agents/skills'}",
        "- Most ported workflow skills disable implicit invocation. Use /skills or $skill-name explicitly.",
        "- Start with $using-superpowers when you want the old Claude workflow discipline.",
        "- Use $aegis-memory when you need long-lived AEGIS history or Robin-specific preferences.",
        f"- Custom agents: {repo_root / '.codex/agents'}",
        f"- Hooks: {repo_root / '.codex/hooks.json'}",
    ]

    if memory_index.exists():
        lines.extend(
            [
                "",
                "Supplemental historical memory is available outside the repo:",
                f"- {memory_index}",
                "- Read only the relevant memory files for the task. Do not bulk-load the full memory bank by default.",
            ]
        )

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
