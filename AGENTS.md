# AGENTS.md

This file provides guidance to Codex CLI when working with code in this repository. It mirrors CLAUDE.md for Claude Code compatibility.

## What this project is

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Build, test, lint

AEGIS requires Python 3.12. Use a virtualenv or ensure `python` resolves to 3.12.

```bash
pip install -e ".[dev]"                              # install with dev deps
python -m pytest tests/ -m "not slow" -x           # excludes @slow
python -m pytest tests/                             # full suite including @slow mesh/golden
python -m pytest tests/test_fresnel.py::test_name   # single test
python -m ruff check src/ tests/                    # lint
python -m ruff format src/ tests/                   # format
python -m mkdocs serve                              # local docs preview
python -m aegis.viewer --location "Ghent, Belgium"   # launch 3D viewer
python -m aegis.viewer --config configs/my.json      # custom config JSON
python -m aegis.viewer --scenario open_ground        # named scenario from config
cd aegis-web && npm run dev                            # React frontend dev server (localhost:5173)
cd aegis-web && npm run build                          # production build -> aegis-web/dist/
cd aegis-web && npm run build:copy                    # copy dist -> src/aegis/viewer/static
```

## Architecture

The data flow is: ray tracer -> `PropagationPaths` -> `DosimetryEngine.compute(body, paths, level)` -> `DosimetryResult`. Incoherent levels (0-6) use `paths.power`. Coherent levels (7-8) use `paths.psi` directly.

- `src/aegis/engine.py` - main entry point, dispatches to kernel by level
- `src/aegis/paths.py` - PropagationPaths (k_hat, psi, element_index). Use `.from_powers()` for incoherent-only paths.
- `src/aegis/result.py` - DosimetryResult (sab, p_abs, sar_wb, Q, rho)
- `src/aegis/precoder.py` - Precoder dataclass for MIMO beamforming vector x
- `src/aegis/tissue/` - tissue EM properties, Fresnel coefficients, Cole-Cole model
- `src/aegis/geometry/` - body mesh, ambient occlusion, directivity, spatial averaging
- `src/aegis/kernels/` - fidelity levels 0-8, each file is one level
- `src/aegis/coherent/` - field channel, exposure operator Q, ECBF solver
- `src/aegis/compliance/` - ICNIRP 2020 limits
- `src/aegis/integration/` - DiffeRT ray tracer bridge (requires `pip install aegis[rt]`)
- `src/aegis/viewer/` - Flask backend: REST API (`routes/`), serves `static/` React build, config via `config.py`
- `aegis-web/` - React + Three.js frontend (Vite, R3F, Zustand). State in Zustand store, 3D scene in `components/scene/`, HUD overlay in `components/hud/`
- `src/aegis/viz/` - matplotlib/plotly dashboards and comparison plots

## Theory (the monograph)

All theory lives in `../monograph/`. Read before implementing physics.

- `../monograph/monograph_v2.tex` - the full monograph (~6000 lines LaTeX). Single source of truth for all equations, tables, proofs, and fidelity level definitions.
- `../monograph/summary_paper.tex` - condensed version (~1100 lines), good for quick reference

## Data

Phantom meshes (STL) and the IT'IS tissue database live in `data/` inside the repo. Available phantoms: thelonious, duke, eartha, ella. Override with `AEGIS_DATA_DIR` env var. Tests needing mesh data are marked `@pytest.mark.slow` and skipped if data is absent.

## Testing rules

- Pre-commit runs ruff, codespell, trailing-whitespace, end-of-file-fixer, YAML/TOML/JSON validators, and large-file checks. Not pytest. CI runs a slim check (lint + ubuntu/3.12) on push and PR. Full matrix (Linux/Windows x 3.11-3.13) runs only on tag push via `release.yml`.
- The Mie regression test is the CI canary. If it passes, physics are correct.
- Every monograph table has a golden test in `tests/golden/`.
- Property tests (Hypothesis) check physics invariants: Sab >= 0, energy conservation, ReLU bound.
- E2E tests run the full pipeline: mesh + tissue + paths -> result.
- Never weaken assertions to make tests pass. Fix the code, not the test.

## Style

- NumPy + SciPy core, optional JAX backend (`_array_backend.py`). Frontend is TypeScript/React.
- Type annotations on public API. No docstrings on private helpers unless non-obvious.
- No em dashes, no semicolons. Sentence case for headings.
- Run `python -m ruff check src/ tests/` and `python -m ruff format src/ tests/` before committing.
- Stage specific files, not `git add -A`.
- Imperative mood for commit messages. First line under 72 chars.

## Git workflow

- For small changes, commit and push directly to master.
- For large changes (5+ files), use feature branches with squash-merge PRs via `gh pr create` + `gh pr merge --squash --delete-branch`.
- Branch naming: `feature/short-description`, `fix/short-description`, `refactor/short-description`.
- Version is automatic via `hatch-vcs` from git tags. Tag releases with `git tag v0.X.Y && git push origin master --tags`.

## Rules reference

Detailed rules live in `.claude/rules/` (shared between Claude Code and Codex):
- `docs-style.md` - documentation writing guide (sentence case, no em dashes, no semicolons, MathJax)
- `git-workflow.md` - full commit, branch, PR, and versioning conventions
- `sentry-issues.md` - handling Sentry bug reports
- `viewer.md` - Flask + Three.js viewer coordinate systems, architecture, testing

Read the relevant rule file before working in that area.

## Codex migration assets

- Repo-scoped Codex skills live in `.agents/skills/`. These are ported from `.claude/skills/`.
- Most ported skills have `allow_implicit_invocation: false` in `agents/openai.yaml` to avoid surprise activation. Invoke them explicitly with `/skills` or `$skill-name`.
- Project-scoped Codex custom agents live in `.codex/agents/` (`code-reviewer`, `deep-think`, `max-think`).
- Project-scoped Codex hooks live in `.codex/hooks.json`.
- Supplemental project memory still lives outside the repo at `~/.claude/projects/-home-user-aegis/memory/`. Use the `$aegis-memory` skill when a task depends on long-lived context such as commercialization, deployment history, local agents, DiffeRT collaboration, or Robin-specific preferences.

## When you're stuck, ask Robin

If you hit a tooling blocker (missing API keys, can't access a website, need browser interaction, need an MCP server installed, need a manual download), STOP and ask. Do not silently fall back to an inferior approach. Robin can provide API keys, run browser steps, install tools, download files, or grant permissions. He wants the most ambitious result, not the fastest fallback.

## Public and private workspace

The independent private repository lives at `private/`. It is ignored by the outer repository and is not a submodule. Search it explicitly when a task concerns private papers, business, research or operations, because ordinary searches may skip ignored paths.

Before finishing work, run `python3 tools/workspace-status.py`. Inspect both repositories. Commit and push only repositories that changed, using their respective remotes and explicit file staging. Never add private files or the private Git directory to the outer repository. Keep raw credentials and bulky generated assets out of both Git histories.

The public codebase is authoritative for `src`, tests and app data. Private research imports that code rather than keeping a second copy. Maintain references when files move. Existing mesh use, app experience and reporting automation are outside this cleanup's behavioral scope.
