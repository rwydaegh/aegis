# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Build, test, lint

AEGIS requires Python 3.12. Use a virtualenv or ensure `python` resolves to 3.12. On Windows with multiple versions, `python` also works.

```bash
pip install -e ".[dev]"                              # install with dev deps (uses 3.12)
python -m pytest tests/ -m "not slow" -x           # excludes @slow; still minutes locally (coherent, Hypothesis, JAX)
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
cd aegis-web && npm run build:copy                    # copy dist -> src/aegis/viewer/static (Flask serves /)
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
- `aegis-web/` - React + Three.js frontend (Vite, R3F, Zustand). State in Zustand store, 3D scene in `components/scene/`, HUD overlay in `components/hud/`. Dev: `npm run dev` (localhost:5173), proxies `/api` to Flask on port 5000
- `src/aegis/viz/` - matplotlib/plotly dashboards and comparison plots

## Theory (the monograph)

All theory lives in `../monograph/`. Read before implementing physics.

- `../monograph/monograph_v2.tex` - the full monograph (~6000 lines LaTeX). Single source of truth for all equations, tables, proofs, and fidelity level definitions.
- `../monograph/summary_paper.tex` - condensed version (~1100 lines), good for quick reference

## Data

Phantom meshes (STL) and the IT'IS tissue database live in `data/` inside the repo. Available phantoms: thelonious, duke, eartha, ella. Override with `AEGIS_DATA_DIR` env var. Tests needing mesh data are marked `@pytest.mark.slow` and skipped if data is absent.

## Testing rules

- Pre-commit runs ruff, codespell, trailing-whitespace, end-of-file-fixer, YAML/TOML/JSON validators, and large-file checks. Not pytest. CI runs a slim check (lint + ubuntu/3.12) on push and PR. Full matrix (Linux/Windows x 3.11-3.13) runs only on tag push via `release.yml`. Locally, `pytest -m "not slow"` skips slow-marked tests. Default pytest uses two workers (`-n 2` in `pyproject.toml`). Use `pytest -n 0` for a single process. Avoid `pytest -n auto` on typical laptops (memory scales with CPU count).
- The Mie regression test is the CI canary. If it passes, physics are correct.
- Every monograph table has a golden test in `tests/golden/`.
- Property tests (Hypothesis) check physics invariants: Sab >= 0, energy conservation, ReLU bound.
- E2E tests run the full pipeline: mesh + tissue + paths -> result.
- Never weaken assertions to make tests pass. Fix the code, not the test.

## Style

- NumPy + SciPy core, optional JAX backend (`_array_backend.py`). Frontend is TypeScript/React.
- Type annotations on public API. No docstrings on private helpers unless non-obvious.
- No em dashes, no semicolons. Sentence case for headings.
- Writing tells to avoid: `.claude/ai_writing_tells.md`. Full doc style: `.claude/rules/docs-style.md`.
- Git workflow: `.claude/rules/git-workflow.md`. Release cadence enforced by PreToolUse hook on git commit/push.

## Web search

Reddit has honest, unfiltered opinions. Use the Reddit MCP (`reddit-mcp-server`) proactively for library comparisons, debugging, community opinions, and tool evaluations. Read threads one by one (the API is per-post). `WebFetch` cannot access Reddit or Twitter (bot-blocking).

## When you're stuck, ask Robin

If you or a subagent hits a tooling blocker (missing API keys, can't access a website, need browser interaction, need an MCP server installed, need a manual download), STOP and ask. Do not silently fall back to an inferior approach. Robin can provide API keys, run browser steps, install tools, download files, or grant permissions. He wants the most ambitious result, not the fastest fallback. This applies to subagent prompts too: always include instructions to report NEEDS_CONTEXT instead of downgrading quality.

## Self-evolution

- If you correct the same mistake twice, add a rule here.
- If you repeat a multi-step workflow 3+ times, create a skill for it.
- If you discover a gotcha, document it here immediately.
- Keep this file under 80 lines. Move details to `.claude/rules/`, skills, or docs.
