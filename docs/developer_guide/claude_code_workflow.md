# Claude Code workflow

AEGIS is developed with Claude Code as the primary coding agent. The `.claude/` directory contains all configuration that keeps sessions productive as the codebase grows.

## Directory layout

```
.claude/
    ai_writing_tells.md          AI writing checklist (always loaded, 39 lines)
    settings.json                Hooks for auto-formatting
    handoffs/                    Session handoff documents
    rules/
        docs-style.md            Writing guide (loaded for docs/**)
        geometry.md              Mesh conventions (loaded for geometry/**)
        git-workflow.md          Commit and push rules (always loaded)
        physics.md               Dimensional analysis, conservation (loaded for kernels/**, tissue/**, coherent/**)
        viewer.md                Coordinate systems, known bugs (loaded for viewer/**)
    skills/
        docs/SKILL.md            /docs - documentation writer
        handoff/SKILL.md         /handoff - session context handoff
        physics-review/SKILL.md  /physics-review - five-lens physics review
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

Five slash commands are available:

- `/docs` writes or updates documentation pages following the AEGIS style guide.

- `/qa` runs visual QA on the 3D viewer using Playwright CLI screenshots, backend tests using pytest, or both. Covers 12 test groups from initial load to stress testing.

- `/ship` handles the full GitHub workflow: analyze changes, run pre-flight checks (ruff, pytest), create an issue and feature branch, commit, push, create a PR, and squash merge.

- `/handoff` writes a structured session handoff document when context is filling up or a session ends. The next session reads the latest handoff and resumes where the last one stopped. Handoff docs go in `.claude/handoffs/`.

- `/physics-review` reviews changes to physics code through five lenses: dimensional analysis, conservation laws, monograph fidelity, sign and factor checks, and regression testing. The `/ship` skill auto-triggers this when the diff touches `kernels/`, `tissue/`, or `coherent/`.

## Hooks

A PostToolUse hook in `.claude/settings.json` auto-formats Python files with `ruff` after every Edit or Write operation. Pre-commit hooks (configured in `.pre-commit-config.yaml`) run ruff and codespell on every `git commit`.

These remove manual quality steps from the workflow. Claude does not need to remember to format before committing.

## Session handoff protocol

When a session reaches its context limit or the user pauses work, run `/handoff`. The skill writes a markdown file to `.claude/handoffs/` with these sections:

1. **Intent** - what was the goal
2. **Completed** - what got done, with commit hashes
3. **In progress** - partially-done work with file paths
4. **Failed approaches** - what did not work (prevents repeating mistakes)
5. **Next steps** - specific enough to resume immediately

To resume: "Read the latest file in `.claude/handoffs/` and pick up where the last session left off."

## Physics review protocol

The `/physics-review` skill checks five things:

1. **Dimensional analysis** - units balance in every arithmetic expression ($S_{ab}$ in W/m$^2$, areas in m$^2$, Fresnel coefficients dimensionless)
2. **Conservation laws** - absorbed power $\leq$ incident power, $S_{ab} \geq 0$, energy balance
3. **Monograph fidelity** - code matches the equation in `summary_paper.tex` or `monograph_v2.tex`
4. **Sign and factor check** - conjugates, factor-of-2, TE/TM convention
5. **Regression tests** - Mie canary, golden tables, property tests all pass

The output is PASS/FAIL per lens with file:line citations for any issues.

## Memory system

Claude Code maintains a persistent memory at `~/.claude/projects/<project>/memory/`. Current entries track operational lessons (use Playwright CLI not MCP, kill old servers before relaunching) and reference information (viewer scene graph layout).

Memory differs from rules: rules are prescriptive instructions that load automatically. Memory stores facts and lessons learned that Claude recalls when relevant.
