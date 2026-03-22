# Claude Code and Cursor workflow

AEGIS is developed with Claude Code as the primary coding agent. Cursor uses the same repo conventions via `.cursor/rules/`. The `.claude/` directory contains Claude-specific automation (rules with path globs, slash-command skills, hooks).

## Cursor rules (`.cursor/rules/`)

Cursor loads **project rules** from `.cursor/rules/*.mdc`. These mirror the intent of `.claude/rules/` and `CLAUDE.md`:

| File | Role |
|------|------|
| `aegis.mdc` | Always apply: Python version, pre-commit checks, GitHub ship steps, docs pointer. |
| `viewer.mdc` | Scoped to `src/aegis/viewer/**` and viewer config paths. |
| `documentation.mdc` | Scoped to `docs/**`. |

Skills under `.claude/skills/` (for example `/ship`, `/qa`, `/docs`) do not run inside Cursor automatically. Agents should still follow the same procedures when the user asks to ship or document.

## Directory layout

```
.claude/
    ai_writing_tells.md          AI writing checklist (always loaded, 39 lines)
    settings.json                Hooks for auto-formatting
    rules/
        docs-style.md            Writing guide (loaded for docs/**)
        git-workflow.md          Commit and push rules (always loaded)
        viewer.md                Coordinate systems, known bugs (loaded for viewer/**)
    skills/
        docs/SKILL.md            /docs - documentation writer
        qa/SKILL.md              /qa - Playwright + pytest QA
        ship/SKILL.md            /ship - issue, branch, PR, merge
```

## How rules work

Files in `.claude/rules/` use YAML frontmatter to declare which paths they apply to. When Claude reads or edits a file matching the pattern, the corresponding rule loads into context automatically.

```yaml
---
paths: ["src/aegis/kernels/**", "src/aegis/tissue/**"]
---
```

This rule only loads when Claude touches files in `kernels/` or `tissue/`. Rules without a `paths` field load on every interaction (like `git-workflow.md`).

The purpose is context efficiency. A session editing the viewer does not need physics rules, and a session writing kernels does not need the 200-line documentation style guide.

## Context budget

Every session starts by loading `CLAUDE.md` (~86 lines) plus any applicable rules. The baseline was reduced from 2,040 lines to roughly 125 lines by:

- Moving three historical plan documents (1,600 lines total) out of `.claude/` into `docs/internal/`
- Path-scoping the documentation style guide (200 lines) so it only loads for `docs/**` edits
- Extracting the git workflow and style sections from `CLAUDE.md` into dedicated rule files

Smaller baseline means more room for actual code in the context window.

## Skills

Three slash commands are available:

- `/docs` writes or updates documentation pages following the AEGIS style guide.

- `/qa` runs visual QA on the 3D viewer using Playwright CLI screenshots, backend tests using pytest, or both. Covers 12 test groups from initial load to stress testing.

- `/ship` handles the full GitHub workflow: analyze changes, run pre-flight checks (ruff, pytest), create an issue and feature branch, commit, push, create a PR, and squash merge.

## Hooks

A PostToolUse hook in `.claude/settings.json` auto-formats Python files with `ruff` after every Edit or Write operation. Pre-commit hooks (configured in `.pre-commit-config.yaml`) run ruff and codespell on every `git commit`.

These remove manual quality steps from the workflow. Claude does not need to remember to format before committing.

## Memory system

Claude Code maintains a persistent memory at `~/.claude/projects/<project>/memory/`. Current entries track operational lessons (use Playwright CLI not MCP, kill old servers before relaunching) and reference information (viewer scene graph layout).

Memory differs from rules: rules are prescriptive instructions that load automatically. Memory stores facts and lessons learned that Claude recalls when relevant.
