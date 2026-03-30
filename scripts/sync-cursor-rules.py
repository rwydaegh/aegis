#!/usr/bin/env python3
"""Sync .claude/ rules to .cursor/rules/ MDC files.

.claude is the ground truth. This script generates Cursor-compatible
.mdc rule files from CLAUDE.md and .claude/rules/*.md files.

Run manually or via CI on release tags.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO / "CLAUDE.md"
CLAUDE_RULES = REPO / ".claude" / "rules"
CURSOR_RULES = REPO / ".cursor" / "rules"

# Map .claude/rules/ files to Cursor MDC config.
# key: stem of the .claude/rules/*.md file
# value: dict with globs (optional) and description
RULE_MAP: dict[str, dict] = {
    "viewer": {
        "description": "Flask + React viewer (coordinates, config, port)",
        "globs": "src/aegis/viewer/**,aegis-web/**,configs/*.json,configs/README.md",
    },
    "docs-style": {
        "description": "MkDocs and prose style for docs/",
        "globs": "docs/**",
        "cursor_name": "documentation",
    },
    "git-workflow": {
        "description": "Git commit, push, branch, and release workflow",
        "globs": None,
    },
    "sentry-issues": {
        "description": "Handling Sentry bug reports from GitHub issues",
        "globs": None,
    },
}


def make_frontmatter(description: str, globs: str | None, always_apply: bool = False) -> str:
    lines = ["---"]
    lines.append(f"description: {description}")
    if globs:
        lines.append(f"globs: {globs}")
    if always_apply:
        lines.append("alwaysApply: true")
    lines.append("---")
    return "\n".join(lines)


def strip_claude_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (---...---) from .claude/rules/ files."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].lstrip("\n")
    return text


def strip_top_heading(text: str) -> str:
    """Remove the first top-level heading (# ...) since we add our own."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^# .+$", line):
            lines.pop(i)
            # Remove blank line after heading if present
            if i < len(lines) and lines[i].strip() == "":
                lines.pop(i)
            break
    return "\n".join(lines)


def adapt_commands(text: str) -> str:
    """Replace python -m with py -3.12 -m for Windows-friendly Cursor usage."""
    # Don't replace inside code blocks that already use py -3.12
    text = text.replace("python -m ", "py -3.12 -m ")
    return text


def generate_aegis_mdc() -> str:
    """Generate the main aegis.mdc from CLAUDE.md."""
    claude_md = CLAUDE_MD.read_text()

    # Extract sections we want (skip gstack, self-evolution, web search)
    sections_to_include = [
        "What this project is",
        "Build, test, lint",
        "Architecture",
        "Data",
        "Testing rules",
        "Style",
    ]

    parts = []
    current_section = None
    current_lines: list[str] = []

    for line in claude_md.splitlines():
        heading_match = re.match(r"^## (.+)$", line)
        if heading_match:
            if current_section in sections_to_include:
                parts.append("\n".join(current_lines))
            current_section = heading_match.group(1)
            current_lines = [line]
        elif current_section:
            current_lines.append(line)

    # Capture last section
    if current_section in sections_to_include:
        parts.append("\n".join(current_lines))

    body = "\n\n".join(parts)
    body = adapt_commands(body)

    # Add parity note
    body += textwrap.dedent("""

    ## Parity with Claude Code

    Rules under `.claude/rules/` and skills under `.claude/skills/` are the canonical
    automation for Claude Code. This file summarizes what Cursor agents should do the
    same. Path-scoped detail is in sibling `.mdc` rules where useful.
    """).rstrip()

    fm = make_frontmatter(
        "AEGIS repository defaults for Cursor (aligned with CLAUDE.md and .claude/rules)",
        globs=None,
        always_apply=True,
    )
    return fm + "\n\n# AEGIS (Cursor)\n\n" + body.strip() + "\n"


def generate_rule_mdc(stem: str, config: dict) -> str:
    """Generate a .mdc file from a .claude/rules/ source."""
    source = CLAUDE_RULES / f"{stem}.md"
    if not source.exists():
        return ""

    content = source.read_text()
    content = strip_claude_frontmatter(content)
    content = strip_top_heading(content)
    content = adapt_commands(content)

    cursor_name = config.get("cursor_name", stem)
    fm = make_frontmatter(config["description"], config.get("globs"))
    title = cursor_name.replace("-", " ").title()

    return fm + f"\n\n# {title} (Cursor)\n\n" + content.strip() + "\n"


def main() -> None:
    CURSOR_RULES.mkdir(parents=True, exist_ok=True)

    # Generate main aegis.mdc
    aegis_mdc = generate_aegis_mdc()
    (CURSOR_RULES / "aegis.mdc").write_text(aegis_mdc)
    print("  wrote .cursor/rules/aegis.mdc")

    # Generate per-rule .mdc files
    for stem, config in RULE_MAP.items():
        cursor_name = config.get("cursor_name", stem)
        mdc = generate_rule_mdc(stem, config)
        if mdc:
            (CURSOR_RULES / f"{cursor_name}.mdc").write_text(mdc)
            print(f"  wrote .cursor/rules/{cursor_name}.mdc")

    # Also generate ai-writing-tells.mdc from the standalone file
    tells_src = REPO / ".claude" / "ai_writing_tells.md"
    if tells_src.exists():
        content = tells_src.read_text().strip()
        fm = make_frontmatter("AI writing tells to avoid", "docs/**")
        mdc = fm + "\n\n" + content + "\n"
        (CURSOR_RULES / "ai-writing-tells.mdc").write_text(mdc)
        print("  wrote .cursor/rules/ai-writing-tells.mdc")

    print("done.")


if __name__ == "__main__":
    main()
