# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Build, test, lint

This machine has Python 3.14 (system) and 3.12 (user). AEGIS is installed under 3.12. Always use the explicit path or `py -3.12` on Windows.

```bash
pip install -e ".[dev]"                              # install with dev deps (uses 3.12)
py -3.12 -m pytest tests/ -m "not slow" -x           # excludes @slow; still minutes locally (coherent, Hypothesis, JAX)
py -3.12 -m pytest tests/                             # full suite including @slow mesh/golden
py -3.12 -m pytest tests/test_fresnel.py::test_name   # single test
py -3.12 -m ruff check src/ tests/                    # lint
py -3.12 -m ruff format src/ tests/                   # format
py -3.12 -m mkdocs serve                              # local docs preview
py -3.12 -m aegis.viewer --location "Ghent, Belgium"   # launch 3D viewer
py -3.12 -m aegis.viewer --config configs/my.json      # custom config JSON
py -3.12 -m aegis.viewer --scenario open_ground        # named scenario from config
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
- `src/aegis/viewer/` - Flask backend: REST API, serves `static/` React build; legacy `_legacy_index.html` only if no build
- `aegis-web/` - React + Three.js frontend (Vite, R3F, Zustand). Dev: `npm run dev` from `aegis-web/`
- `src/aegis/viz/` - matplotlib/plotly dashboards and comparison plots

## Theory (the monograph)

All theory lives in `../monograph/`. Read before implementing physics.

- `../monograph/monograph_v2.tex` - the full monograph (~6000 lines LaTeX). Single source of truth for all equations, tables, proofs, and fidelity level definitions.
- `../monograph/summary_paper.tex` - condensed version (~1100 lines), good for quick reference

## Data

Phantom meshes (STL) and the IT'IS tissue database live in `data/` inside the repo. Available phantoms: thelonious, duke, eartha, ella. Override with `AEGIS_DATA_DIR` env var. Tests needing mesh data are marked `@pytest.mark.slow` and skipped if data is absent.

## Testing rules

- Pre-commit runs ruff and codespell only, not pytest. CI runs the **full** `pytest tests/` on push and PR. Locally, `pytest -m "not slow"` is a shorter slice. Default is **`-n 2`** (pytest-xdist); avoid **`-n auto`** (OOM risk); use **`pytest -n 0`** for sequential (debuggers, low RAM).
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
- Git workflow: `.claude/rules/git-workflow.md`.

## Self-evolution

- If you correct the same mistake twice, add a rule here.
- If you repeat a multi-step workflow 3+ times, create a skill for it.
- If you discover a gotcha, document it here immediately.
- Keep this file under 80 lines. Move details to `.claude/rules/`, skills, or docs.
