# Pose streams

Per-body walk-cycle pose trajectories at 30 Hz, consumed by the JSAC plaza
scenario (one stream per body). Built from AMASS by `scripts/ingest_amass.py`.

## Format

Each `.npz` is one body's recording:

| key      | shape       | dtype  | meaning                                          |
|----------|-------------|--------|--------------------------------------------------|
| `poses`  | (N, P)      | f32    | axis-angle pose, P = 156 (SMPL-H) or 165 (SMPL-X) |
| `trans`  | (N, 3)      | f32    | root translation per frame, metres               |
| `betas`  | (B,)        | f32    | body-shape coefficients, B in {10, 16}            |
| `gender` | scalar str  | utf-8  | `neutral` / `male` / `female`                     |
| `fps`    | scalar int  | i32    | always 30                                         |
| `source` | scalar str  | utf-8  | provenance, e.g. `CMU_01_01_walk`                |

The runtime loader is `aegis.geometry.PoseStream.load(path)`. Only the first
66 pose params drive the SMPL-X mesh (root + 21 body joints); hands / face /
eyes are kept on disk but ignored at posing time.

## Why this directory is otherwise empty

AMASS is research-only and license-gated. The contents of this directory
are gitignored on purpose — `*.npz` here is excluded by `.gitignore` so the
corpus does not end up in a public repo.

## How to populate

1. Register at <https://amass.is.tue.mpg.de/> and accept the EULA.
2. Download one or more subsets — CMU, BMLrub, BMLmovi are walking-heavy
   choices. The files arrive as `<Subset>.tar.bz2`.
3. Extract somewhere outside the repo, e.g. `~/data/amass/`. The layout
   per subset is `<Subset>/<subject>/<sequence>.npz`.
4. Run the ingest:

   ```bash
   python scripts/ingest_amass.py \
       --input ~/data/amass \
       --output data/poses \
       --max-sequences 50 \
       --filter walk
   ```

   `--filter walk` keeps only sequences whose path or filename contains the
   substring `walk`. Pass `--filter ''` to keep everything (and pre-filter
   yourself), or `--dry-run` to preview the picks.

5. Sanity check: `aegis.geometry.PoseStream.load("data/poses/<...>.npz")`
   should return without error and `len(stream)` should match
   roughly (sequence_duration × 30) frames.

## Visual sanity

A five-frame render of one trace lives at `figures/sanity_<source>.png`
once SMPL-X model files are present (see
`JSAC/code/prompts/01_smplx_seeding.md`). Until then this is a TODO — the
ingest pipeline itself is independent of the SMPL-X model and runs fine.

## Body-shape variation

The ingest preserves each AMASS sequence's own `betas` vector. The loader
defaults to using those at posing time, giving the plaza scenario real
demographic spread for free. Pass `betas=` to `PoseStream.posed_body()` to
override.
