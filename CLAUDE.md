# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Build, test, lint

This machine has Python 3.14 (system) and 3.12 (user). AEGIS is installed under 3.12. Always use the explicit path or `py -3.12` on Windows.

```bash
pip install -e ".[dev]"                              # install with dev deps (uses 3.12)
py -3.12 -m pytest tests/ -m "not slow" -x           # fast tests (~5s)
py -3.12 -m pytest tests/                             # all tests (~30s)
py -3.12 -m pytest tests/test_fresnel.py::test_name   # single test
py -3.12 -m ruff check src/ tests/                    # lint
py -3.12 -m ruff format src/ tests/                   # format
py -3.12 -m mkdocs serve                              # local docs preview
py -3.12 -m aegis.viewer --location "Ghent, Belgium"  # launch 3D viewer
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
- `src/aegis/viewer/` - Flask + Three.js 3D viewer (voxel scenes, body mesh, APD heatmap)
- `src/aegis/viz/` - matplotlib/plotly dashboards and comparison plots

## Theory (the monograph)

All theory lives in `../monograph/`. Read before implementing physics.

- `../monograph/monograph_v2.tex` - the full monograph (~6000 lines LaTeX). Single source of truth for all equations, tables, proofs, and fidelity level definitions.
- `../monograph/summary_paper.tex` - condensed version (~1100 lines), good for quick reference
- `../monograph/factcheck_fixes.md` - corrections applied after fact-checking

Design documents in `../coding_project/`: `project_proposal.md`, `implementation_plan.md`, `ray_tracer_comparison.md`.

## Ground truth (scripts)

The `../scripts/` directory contains 40+ standalone research scripts that produce correct results. Every extraction into `src/aegis/` must be validated against the original script output. Key oracle scripts:

- `../scripts/_fresnel.py` - Fresnel transmission (T0, Ts, Tp)
- `../scripts/_geom.py` - STL loading, triangle areas
- `../scripts/apd_pipeline.py` - full APD computation
- `../scripts/mie_theory_corrected.py` - Mie validation + IT'IS database
- `../scripts/verify_tables.py` - monograph table values

## Data

Mesh files (STL, ~5MB) live in `../data/`. Set `AEGIS_DATA_DIR` env var or the default `../../data` is used. Tests needing mesh data are marked `@pytest.mark.slow` and skipped if data is absent.

## Testing rules

- The Mie regression test is the CI canary. If it passes, physics are correct.
- Every monograph table has a golden test in `tests/golden/`.
- Property tests (Hypothesis) check physics invariants: Sab >= 0, energy conservation, ReLU bound.
- E2E tests run the full pipeline: mesh + tissue + paths -> result.
- Never weaken assertions to make tests pass. Fix the code, not the test.

## Style

- NumPy-only core (no JAX yet). Clean path to JAX later.
- Type annotations on public API. No docstrings on private helpers unless non-obvious.
- No em dashes (--), no semicolons. Sentence case for headings.
- Banned words: "delve", "leverage", "seamlessly", "robust", "comprehensive", "landscape", "ecosystem", "journey", "harness", "unlock", "empower".
- No "it's important to note", "in order to" (just "to"), no rhetorical question headers.
- Full writing guides: `.claude/style_guide.md` and `.claude/ai_writing_tells.md`.

## Git workflow

This is a vibe-coded project. Claude is often the only one making changes in a session, so committing and pushing is Claude's responsibility. Treat it as a reflex, not an afterthought.

### When to commit

- After completing a logical unit of work (new feature, bug fix, test suite, refactor).
- Before switching to a different area of the codebase.
- Before any risky or experimental change, so there is a clean rollback point.
- At the end of every session, commit any uncommitted work. Do not leave the repo dirty.
- Do NOT commit after every tiny edit. One commit per logical change, not per file touched.

### How to commit

- Run `py -3.12 -m ruff check src/ tests/` and `py -3.12 -m ruff format --check src/ tests/` before committing. Fix issues first.
- Run `py -3.12 -m pytest tests/ -m "not slow" -x` before committing. All fast tests must pass.
- Stage specific files, not `git add -A`. Review what you are committing.
- Write commit messages in imperative mood ("Add level 3 kernel", not "Added level 3 kernel").
- First line under 72 chars. Add a blank line and body for non-trivial changes.
- No fixup/wip commits on master. Every commit on master should be a clean, passing state.

### When to push

- After every commit, push to origin/master. This project has no CI gates or branch protection, so pushing is safe and ensures work is backed up.
- If the push fails (someone else pushed, or network issues), pull with rebase first: `git pull --rebase origin master`.

### Branching

- For now, work directly on master. The project is young and single-developer.
- If a change is large or experimental (touching 5+ files across multiple modules), create a feature branch, commit there, then ask the user before merging to master.
- Branch naming: `feature/short-description`, `fix/short-description`, `refactor/short-description`.

### What not to commit

No `.env`/credentials, no large binaries (STL), no generated files (`site/`, `__pycache__/`, coverage). All covered by `.gitignore`.

## Self-evolution

- If you correct the same mistake twice, add a rule here.
- If you repeat a multi-step workflow 3+ times, create a skill for it.
- If you discover a gotcha, document it here immediately.
- Keep this file under 120 lines. Move details to skills or docs.
