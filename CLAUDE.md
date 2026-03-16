# AEGIS - Claude Code instructions

## What this project is

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Build, test, lint

This machine has Python 3.14 (system) and 3.12 (user). AEGIS is installed under 3.12. Always use the explicit path or `py -3.12` on Windows.

```bash
pip install -e ".[dev]"                              # install with dev deps (uses 3.12)
py -3.12 -m pytest tests/ -m "not slow" -x           # fast tests (~5s)
py -3.12 -m pytest tests/                             # all tests (~30s)
py -3.12 -m ruff check src/ tests/                    # lint
py -3.12 -m ruff format src/ tests/                   # format
py -3.12 -m mkdocs serve                              # local docs preview
```

## Architecture

- `src/aegis/tissue/` - tissue EM properties, Fresnel coefficients, Cole-Cole model
- `src/aegis/geometry/` - body mesh, ambient occlusion, directivity, spatial averaging
- `src/aegis/kernels/` - fidelity levels 0-8, each file is one level
- `src/aegis/coherent/` - field channel, exposure operator Q, ECBF solver
- `src/aegis/compliance/` - ICNIRP 2020 limits
- `src/aegis/engine.py` - main entry point, level dispatch
- `src/aegis/paths.py` - PropagationPaths dataclass
- `src/aegis/result.py` - DosimetryResult dataclass

## Theory (the monograph)

All theory lives in `../monograph/`. Read these carefully before implementing physics.

- `../monograph/monograph_v2.tex` - **the full monograph** (~6000 lines LaTeX). This is the single source of truth for all equations, tables, proofs, and fidelity level definitions. Read it thoroughly before any physics implementation.
- `../monograph/monograph_v2.pdf` - compiled PDF (latest build)
- `../monograph/summary_paper.tex` - condensed version (~1100 lines), good for quick reference
- `../monograph/summary_vs_monograph.md` - what's in the summary vs the full monograph
- `../monograph/factcheck_fixes.md` - corrections applied after fact-checking
- `../monograph/references.bib` - bibliography

There are also prior design documents in `../coding_project/`:

- `../coding_project/project_proposal.md` - original AEGIS project proposal (627 lines)
- `../coding_project/implementation_plan.md` - detailed implementation plan with data model (692 lines)
- `../coding_project/ray_tracer_comparison.md` - DiffeRT vs Sionna RT comparison

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
- Follow the writing style guide in `.claude/style_guide.md` for all docs and comments.
- No em dashes, no semicolons, no AI buzzwords. Sentence case for headings.

## Self-evolution

Claude should actively maintain this file and create skills when patterns emerge:

- If you correct the same mistake twice, add a rule here.
- If you repeat a multi-step workflow 3+ times, create a skill for it.
- If you discover a gotcha, document it here immediately.
- Keep this file under 80 lines. Move details to skills or docs.
