# 01 — SMPL-X seeding

**Goal.** Make `aegis[body]` install + the existing SMPL-X parametric body code actually work on this machine. End state: someone can call `ParametricBody.load("smplx")` and get a real mesh back.

## Blockers

None.

## Why this matters

The JSAC paper's hero scenario (paper §VII, see `JSAC/planning/paper_v2.tex`) wants 50 SMPL-X bodies on AMASS walks at 30 Hz. The plumbing for SMPL-X is *already in the codebase* — the issue is that the model files are gated behind a registration wall and nobody downloaded them yet, so every `ParametricBody.load("smplx")` call falls through to "model files not found" and the tests skip silently.

This brief exists to make that go away once and for all, before brief 02 (AMASS) and brief 08 (plaza_run) try to use it.

## What's already in place

- `src/aegis/geometry/parametric.py` — has `_load_smplx()` that imports `smplx` lazily, looks for model files at `~/.aegis/models/smplx/`, and constructs a `ParametricBody` with shape betas + pose. The code is real, not a stub.
- `src/aegis/viewer/routes/parametric.py` — exposes `POST /api/parametric-body` that takes betas + pose vector and returns a binary mesh.
- `pyproject.toml` — has the `[body]` extra: `smplx>=0.1.28`, `torch>=2.11.0`, `pygltflib>=1.16.5`. Currently `python -c "import smplx; import torch"` fails in the project venv because the extra hasn't been installed.
- `tests/test_parametric.py` and `tests/test_viewer_parametric.py` — gated on `SMPLX_DIR.exists()`, so they always skip today. Once the model files are in place, they should run without modification.

## Where the model files come from

SMPL-X is hosted at `https://smpl-x.is.tue.mpg.de/`. License: free for research and non-commercial; you have to register and accept the EULA. Files: `SMPLX_NEUTRAL.npz`, `SMPLX_FEMALE.npz`, `SMPLX_MALE.npz` plus optional UV templates. Total around 200 MB. They go in `~/.aegis/models/smplx/`.

## Open questions for the dev

- Where do the model files live in CI? Options: download script in `scripts/`, fetch on first call (cache once), bake into a Docker layer, mount from a Hetzner-side volume. Pick whatever is least painful given how the rest of `aegis` deals with external assets.
- Does the project have any existing convention for license-gated downloads? Worth checking; if not, this is the first instance.
- Is `torch` going to fight with whatever JAX setup the rest of the codebase has? They normally coexist fine but worth a smoke test on whatever Python / CUDA combo the project venv runs.

## What "done" looks like

- `pip install -e ".[body]"` succeeds in the project venv.
- A model file presence check (manual or scripted) lands the three NPZ files in `~/.aegis/models/smplx/`.
- `pytest tests/test_parametric.py tests/test_viewer_parametric.py` runs without skipping.
- A short note (one paragraph in `docs/` or in the test file's docstring) explaining how to bootstrap the model files for a new dev / CI runner.
- The Anny stub stays as it is — `NotImplementedError`, no change.

## What this is NOT

- A re-implementation of `geometry/parametric.py`. Treat that file as working code.
- A SMPL-X panel for the viewer frontend. The HTTP route exists; whether the viewer dropdown should expose it is a separate question, and not blocking the paper.
- A pose-control system. Pose comes from brief 02 (AMASS). This brief just unblocks the *static* mesh path.
