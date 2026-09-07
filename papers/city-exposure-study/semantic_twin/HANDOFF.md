# Handoff: where the refactor stopped

Written 2026-08-04 by the Claude session that ran the refactor, when the account
hit its usage limit. Work continues in Codex, with no shared memory. This file
assumes you know nothing.

Read `TANGLE.md` for how the code got tangled, `REFACTOR_PLAN.md` for the target,
and `docs/BUGS.md` for the fourteen numbered defects. Then read this.

## The one thing you must not break

There is a golden lock. `tests/golden/` pins 10,249 scalar values from real traced
runs at a relative tolerance of 1e-12, captured before any code moved. Eleven
cases. It exists so that a large refactor can be proven to have changed nothing.

The discipline is strict and it has held so far:

- The refactor changes structure only. It fixes no bug, not even a bug sitting in
  a file being moved.
- Every fix lands afterwards, as its own commit, with its own before and after
  numbers, so its effect on the paper stays legible.
- Nothing under `tests/golden/` is ever edited.

Do not change a float literal, an operation order, or a random draw order. The
tracer draws twice per ray for the launch direction plus once per bounce, all
from one stream, so reordering anything changes every number in the study.

Verify the fixtures are untouched at any time:

```
find tests/golden -type f | sort | xargs sha256sum
```

All 17 files were unchanged at the moment this was written, across nine agents.

## State of the tree

Nothing is committed. Everything below is uncommitted work in the working tree.

The shell has no virtualenv on its path. Call the interpreter absolutely:
`/home/user/aegis/.venv/bin/python`.

### Done and verified

| Area | Where | Evidence |
|---|---|---|
| Spine | `sites.py`, `paths.py`, `runconfig.py` | 155 tests, run identity pinned to literal digests |
| Imagery | `semantic_twin/acquire/` | 84 tests |
| Aggregation | `semantic_twin/report/` | golden aggregation cases pass |
| Drawing | `semantic_twin/viz/` | golden fast case passes |
| Illumination | `semantic_twin/illumination/` | bit-exact against `git show HEAD:` copies |
| Walks | `semantic_twin/walk/` | bit-exact, 80 cases across four functions |
| Vision | `semantic_twin/vision/` | 288 tests, absent from both drivers by design |
| Invariant tests | `tests/test_invariant_*.py` | verified by 20 mutation trees |

### Interrupted

Three agents were stopped mid-flight. Each was asked to leave the tree importable
and write its own handoff. Look for these files and trust them over this one:

- `docs/HANDOFF_MATERIALS.md`
- `docs/HANDOFF_SCENE.md`
- `docs/HANDOFF_TRANSPORT.md`

All three files exist and all three agents stopped cleanly.

**On the tracer, which is the thing to worry about.** That agent owned
`tracer.py`, which draws the random numbers for the whole study. It was told to
revert rather than leave an unverified move in place, and it did the careful
thing: it touched nothing that draws, and left only additive new files under
`semantic_twin/transport/` that nothing imports yet.

`tracer.py` does differ from the last commit, but by exactly one line: an import
rewired from `.directions` to `..illumination`. The orchestrator checked that
independently rather than trusting the report, by reconstructing the old module
from git and comparing behaviour:

```
sample_sphere     4 seeds x 2 sizes    bit-identical
fibonacci_sphere  3 sizes              bit-identical
nearest_cell      2000 probes          bit-identical
```

So the draw order is intact. The scene and materials agents proved their own
moves the same way: 144 fishnet cases over 52,756 faces, 720 camera
configurations, 3,000 planar draws for scene; the full binding path on real
Korenmarkt data plus both golden fixtures for materials.

## Verified state at handoff

Measured, not assumed, at the moment this file was finished:

```
144 package modules import cleanly     (the four bpy ones need Blender, expected)
1750 tests collect, no import errors
53 passed  numeric golden tier, no mesh, 5.3 s
17 of 17   golden fixtures byte-identical to the pre-refactor baseline
```

So the tree is in a state you can pick up and run. What has NOT been verified is
the full golden suite, which traces real rays. See step 2 below.

## First thing to do

Find out where you actually are. Do not assume this file is current.

```
/home/user/aegis/.venv/bin/python -m pytest tests/ -m "not slow" -q -p no:randomly
```

Roughly 1,600 tests, a few minutes. Then the golden tiers:

```
# numeric only, no mesh, ~6 s
/home/user/aegis/.venv/bin/python -m pytest tests/test_golden_regression.py -q -k "not slow"

# everything, traces real rays, ~7 min
/home/user/aegis/.venv/bin/python -m pytest tests/test_golden_regression.py -q
```

Expect roughly 27 xfail markers. Those are deliberate. Each pins one numbered
finding in `docs/BUGS.md` and is `strict=True`, so a fix turns it into a reported
failure that forces the marker out. **An unexpected pass is a signal, not a
success.** It means either someone fixed that defect, or something moved that
should not have.

## The next task, in order

### 1. Rewire the two drivers and delete the shims

This is the critical path and everything else waits on it.

Because agents could not edit the same driver at once, each left its old module
path importable as a temporary re-export shim. There are 31 of them:

```
grep -rln "staging shim" --include="*.py" semantic_twin/
```

Delete every one and point the callers at the real homes. The drivers still
import from old paths at:

```
run_exposure.py:33 (block), 46, 47, 48, 49, and a comment at 52
run_next_event.py:43, 44, 45, 46, 47, 48, 49, 50, 51, and prose at 11
```

`run_exposure.py:651, 858, 1406` are already done.

Three references could not be touched and need a decision:
`tests/golden/capture.py:300` (never edit that tree, so this may have to wait for
a fixture recapture), `semantic_twin/viz/blender/payload.py:44-45` (a staleness
list), `semantic_twin/report/rows.py:91` (a docstring).

Two things this pass must also settle:

- Three of `run_exposure.py`'s argparse defaults genuinely disagree with
  `RunConfig`. `RunConfig` currently matches `run_next_event.py`. The three
  divergences are computed by a test rather than listed, so a fourth cannot slip
  in unnamed. Decide which side is right for each.
- Four callers still read the config `source_mesh` key raw instead of going
  through `paths.site_mesh`: `acquire/source.py:164`, `build_walk_twin.py:47`,
  `fetch_site_panoramas.py:310`, `render_showcase.py:847`. The ruling already
  made is that `source_mesh` is acquisition provenance and not a resolver,
  because every config names the unsuffixed build, which at Korenmarkt and Milan
  is the old-format mesh that the version gate correctly refuses.

### 2. Run the full golden suite

The single verification that the whole refactor reproduced the pinned numbers.
It has not run since agents started changing things, because they were fenced off
it to stop them clobbering each other's output files. This is the moment of
truth. Until it passes, treat the refactor as unverified.

### 3. Commit

Nothing has been committed. Stage specific paths, never `git add -A`. See the
warning about the shared checkout below.

### 4. Then the rest

- Finish whatever the three interrupted agents left, per their handoff files.
- The remaining orphans: `propagation/bystanders.py` (1,534 lines),
  `propagation/antenna.py` (1,292, needs an invariance conversation first).
  Default is to wire an orphan back in unless there is a real reason not to.
- `screen_cities.py:236` `MapTilesMetadata` is a third Street View client
  duplicating `acquire/streetview.py`, with its own retry policy and its own
  constants at lines 43-44.
- Split `run_exposure.py` (1,610 lines) into driver, validator and reporter.
- Shave outputs per `docs/OUTPUT_INVENTORY.md`, about 217 MB to archive.
- Write a new lean docs set. The 49 existing timestamped notes stay untouched as
  historical record, by the user's decision, so this is new writing.
- Rename the 80 `inhouse_leaf` mesh files to `google_leaf`. Every identifier in
  code is already renamed. What is left is the on-disk rename, and it cannot be
  done under the golden lock because the fixtures pin runs that read those names.
  `paths.GOOGLE_MESH_STEM` is the single point of control in code, but the name
  also lives in twelve `config/*.json` files, two fishnet manifests,
  `build_site_config.py`, and the two script filenames.

### 5. Last, and only last: the bug fixes

Fourteen numbered findings in `docs/BUGS.md`, none fixed, deliberately. Each is
its own commit with its own before and after numbers, and each flips a pinned
xfail to a pass, which is how you know the fix worked.

Ordering matters. Finding 2, the roughness quadrature, must be settled before
finding 1 is re-measured, because the two are coupled.

**Finding 1 changes the paper, not just a number.** Next-event estimation
discards 54 percent of the power reflected at the first bounce and 73 percent at
the second, by treating it as specular and never routing it anywhere. Crediting
it closes 39 to 62 percent of the gap between the two estimators. `NEXT_EVENT.md`
attributes that whole gap to something else. About half of that explanation is
wrong. Do not rewrite the paper's story without talking to Robin first.

## Traps that cost this session real time

**The checkout is shared.** Other Claude sessions have run in this same working
tree. One swept 49 file renames into its own commit. One deleted a file from the
worktree while the git index still held an older copy of it. Before committing,
run `git status` and `git diff --cached`, and re-stage from the working tree
rather than trusting the index. Two stale index entries were already cleared once
during this session: they held a pre-deduplication module and a test that could
no longer import.

**A number that lives only in a docstring has nothing to protect it.** A measured
result was lost when an agent rebuilt a file from git and retyped its prose from
memory. It was recovered from the shipped output file and now names that file, so
it can be checked instead of retyped. Do the same for any measurement you write
into a comment.

**An inert mutation does not prove code is dead.** One agent showed by mutation
that removing a clamp changed no number, and concluded it was dead code. Another
read the code and proved it load-bearing: the window is stored in degrees and
read back in radians, so two limits that should meet exactly do not, and without
the clamp the density goes negative at its own support edge by about six parts in
ten billion. Too small to move a test, large enough to be wrong.

**Energy conservation is a weak test for the grating solver.** It missed two
separate defects. On a patterned half space the transmitted efficiency is
undefined by design, so no energy identity applies to that geometry at all.

**`pip install -e .` was broken and nobody noticed**, because the working
directory happens to sit on the path. `pyproject.toml` declared only the top
package, so no subpackage was ever installed. Fixed to a find directive. If you
add a package, check it is picked up.

## Facts worth carrying forward

- The eleven-city headline uses zero image evidence. It runs with
  `--materials geometric`, which classifies surfaces by triangle orientation and
  never calls the image binding. The 0.0 coverage it reports is a literal written
  at `run_exposure.py:532`, not a measurement.
- Of 112 cameras, 83 have a solved pose, 51 are admitted, 14 sit inside the
  building geometry, and 18 are refused on registration residual alone. One site
  has 14 panoramas and no usable pose. Re-run it with
  `vision.provenance.survey()`.
- At Korenmarkt, twelve panoramas lift observed facade area from 6.9 to 24.1
  percent of the crop, but only 1.92 of 3.43 looks per face are independent. So
  44 percent of the apparent multi-view evidence is redundant. Source:
  `outputs/walk_korenmarkt/walk_coverage.json`.
- The validation gate reports about one percent agreement and quotes a worst
  error of 0.0122. The correction it is missing is 0.0158, which is larger. That
  agreement is mostly quadrature, and the gate cannot resolve an estimator error
  below roughly one percent.
- The published `city250_corrected_*` set has torn lines, two in New York and one
  in Prague, so under the current guard those sites cannot be published. The
  `city250_L3_*` set is clean at eleven sites by eighty standpoints. Check which
  set any paper figure came from.
