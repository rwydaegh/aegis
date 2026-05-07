# 01 — SMPL-X seeding (answer)

Status: **done**. `[body]` extra installed, model files seeded, all model-gated tests pass, full non-slow suite green (3119 passed, no regressions).

## End-to-end check

```python
>>> from aegis.geometry.parametric import ParametricBody
>>> import numpy as np
>>> pb = ParametricBody.load("smplx", gender="neutral")
>>> body = pb.generate(betas=np.zeros(10))
>>> body.n_triangles, body.vertices.shape, body.normals.shape
(20908, (20908, 3, 3), (20908, 3))
```

20908 triangles is the canonical SMPL-X topology. Brief 02 (AMASS pose ingest) is now unblocked.

## What was done

### 1. `pip install -e ".[body]"`

Ran in the project `.venv` (Python 3.12.3). Pulled `smplx 0.1.28`, `torch 2.11.0+cu130` (full CUDA 13 stack), `pygltflib 1.16.5`, plus a numpy bump 2.4.3 → 2.4.4. `import smplx, torch, pygltflib` all clean. Torch and JAX coexist in this venv without conflict.

### 2. Path bug in `_load_smplx`

The brief said to treat `geometry/parametric.py` as working code. It wasn't quite. Verified with a synthetic dir:

```python
smplx.create("/tmp/test/smplx", model_type="smplx", gender="neutral")
# AssertionError: Path /tmp/test/smplx/smplx does not exist!
```

`smplx.create` joins another `model_type` segment when `model_path` is a directory: `os.path.join(model_path, "smplx")`. The previous default of `~/.aegis/models/smplx` therefore resolved to `~/.aegis/models/smplx/smplx/SMPLX_NEUTRAL.npz`, contradicting the brief's stated location and the on-disk reality.

Fix: changed the default to `~/.aegis/models/` (the canonical SMPL-X "models root" layout). `smplx.create` now joins to `~/.aegis/models/smplx/SMPLX_NEUTRAL.npz`. Updated the `FileNotFoundError` text to point at the new fetch script. No callers pass an explicit `model_path`, so the change is internal.

### 3. `scripts/fetch_smplx.py`

Bootstrap helper. Takes either the official zip or an already-extracted directory, drops the three NPZs into `~/.aegis/models/smplx/`. Honours `AEGIS_MODELS_DIR` and `--dest`. Idempotent (re-running overwrites). Smoke-tested against a synthetic zip before Robin's real download.

License-gated download was the chosen mechanism over fetch-on-first-call or Docker-baked assets — MPI's EULA is per-user and can't be auto-accepted. CI / cloud runners mirror the unzipped files into the same path or set `AEGIS_MODELS_DIR`.

### 4. The download

Robin downloaded `smplx_lockedhead_20230207.zip` (392 MB on the page, 411 MB on disk) — the AMASS-compatible "removed head bun" variant. Picking that over `models_smplx_v1_1.zip` because brief 02 needs AMASS, and AMASS pose data is registered against the locked-head shape space. Inspected the zip's internal layout (`models_lockedhead/smplx/SMPLX_{NEUTRAL,MALE,FEMALE}.npz`) — `rglob` in `fetch_smplx.py` finds them by basename, no script changes needed.

```
$ python scripts/fetch_smplx.py /home/user/aegis/smplx_lockedhead_20230207.zip
Installed 3 SMPL-X model files into /home/user/.aegis/models/smplx:
  SMPLX_NEUTRAL.npz  (137.1 MB)
  SMPLX_FEMALE.npz   (137.2 MB)
  SMPLX_MALE.npz     (137.1 MB)
```

### 5. `generate_batch` bug

After files were in, `test_parametric_batch` failed at `lbs(...)` with a tensor-shape mismatch. Root cause: `smplx` fixes `batch_size` at model construction. Calling `model(betas=(N, 10))` against a default `batch_size=1` model crashes because `expression`, `body_pose`, `global_orient`, etc. all stay at batch=1 and `torch.cat([betas, expression], dim=-1)` fails on the dim-0 mismatch.

Fix: rewrote `generate_batch` as a per-row loop calling `self.generate(...)`. One-line change. Loses the (theoretical) batched-forward speedup, but the only caller is the test, and `plaza_run` will drive bodies one at a time anyway since each body has its own pose at each timestep.

### 6. Docs

Added a "SMPL-X bootstrap" section to `docs/developer_guide/phantom_pipeline.md`. Covers the `[body]` extra, registration, the fetch command, and the `AEGIS_MODELS_DIR` override for CI / cloud caches.

### 7. `.gitignore`

Added `!scripts/fetch_smplx.py` to the `scripts/*` allowlist (otherwise the helper would be ignored), and `smplx_*.zip` / `models_smplx_*.zip` to keep the 411 MB archive out. Robin separately added `data/poses/amass_smplx_g/` while working on brief 02.

## Final test state

| File | Result |
|---|---|
| `tests/test_parametric.py` | 5 passed, 1 skipped (the smplx-not-installed branch — by design only runs when the package is absent) |
| `tests/test_viewer_parametric.py` | 6 passed |
| `tests/test_pose_stream.py` | 8 passed |
| Full non-slow suite | 3119 passed, 32 unrelated skips (JAX, basestationLib, etc.) |

Ruff clean on `parametric.py` and `fetch_smplx.py`.

## Files touched

- `src/aegis/geometry/parametric.py` — `_load_smplx` path-default fix; `generate_batch` rewrite as per-row loop
- `scripts/fetch_smplx.py` — new, the bootstrap helper
- `docs/developer_guide/phantom_pipeline.md` — new "SMPL-X bootstrap" section
- `.gitignore` — `scripts/fetch_smplx.py` allowlist + `smplx_*.zip` / `models_smplx_*.zip` exclude
- `JSAC/code/prompts/01_smplx_seeding_answer.md` — this file
- `~/.aegis/models/smplx/SMPLX_{NEUTRAL,MALE,FEMALE}.npz` — model files in place (outside the repo)

## What this didn't touch

Per the brief's "what this is NOT" section:

- Body of `geometry/parametric.py` other than the two surgical bug fixes
- `viewer/routes/parametric.py` (already worked, no changes needed)
- The Anny stub (still `NotImplementedError`)
- The viewer dropdown / SMPL-X UI panel (out of scope)
- AMASS / pose ingest (brief 02)

## Not committed

I haven't run `git commit` yet. The work is staged on `master` (per Robin's "do not work with branches"). Awaiting word on whether to commit and push.
