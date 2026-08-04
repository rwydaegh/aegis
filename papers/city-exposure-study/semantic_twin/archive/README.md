# Archive

Nothing here was deleted. These are files that the study no longer reads,
moved out of the way so that what is left in `../docs/` is current. Each one is
on disk exactly as it was.

For why the illumination law changed, and for which results survive it, read
`../docs/LAW_CHANGE.md` first.

There is a second, larger archive at `../../archive/`, which holds big binary
things such as the GPU box backup and the Blender previews. This one holds
documents and completed study scripts.

## `scripts/`

These programs remain runnable reproduction records. They no longer belong to
the current command surface.

- `bench_intersect.py` measured the preliminary intersection path now used by
  `semantic_twin.propagation.geometry.MitsubaGeometry.intersect`.
- `bench_pinned.py` and `bench_workers.py` measured the worker policy now used
  by `semantic_twin.transport.tracer`.
- `backfill_sky_conflict.py` performed the completed one-time repair recorded in
  `outputs/registration_sky_conflict.json`.
- `repair_torn_sites.py` reproduced and repaired the two damaged
  `city250_corrected` result files. The repaired controls and replacements are
  retained under `outputs/city250_repair_*`.
- `build_progress_blender.py` was replaced by the packaged propagation Blender
  workflow in `semantic_twin.viz.blender`.
- `project_pixel_semantics.py` records the pixel-projection approach superseded
  by fishnet surface cutting. Its adaptive tiling primitives remain active in
  `semantic_twin.vision.project`.
- `measure_escape_range_term.py` records the completed test that ruled out a
  missing escape-range factor as the cause of the multipath surplus.
- `measure_source_construction.py`, `measure_source_near_share.py`, and
  `measure_source_thickness.py` record source-region constructions that the
  illumination study tested and rejected. Their reusable calculations remain
  under `semantic_twin.illumination`.

## `METHOD.tex`

An eight page explanatory writeup of the co-located transmitter argument,
written for Robin. It built with `latexmk -pdf METHOD.tex` and the built
`METHOD.pdf` sits beside it here, along with the latexmk working files.

**Why it moved.** It explains the old method, and its worked example places the
source on a rooftop mast 80 m away, which is the deployment picture the study is
dropping. Under the replacement, sites sit on facade tips, the top edge where a
wall meets the sky, so there is no mast and no assumed range. A document whose
one job is to explain the method has to explain the current one.

**What replaced it.** `../docs/METHOD.md`, which Robin is writing.

**What did not go stale in it, in case any of it is worth carrying over.** The
worst direction bound is the strongest part and it holds under any illumination
law, because the whole point of it is that the maximum over arrival directions
dominates whatever weight a reviewer proposes. The line of sight treatment, that
the angular support is where the mesh first hit range exceeds the source range
and that the sky mask is the infinite range case, is geometry and survives.
`chi_iso` is untouched. What goes is `chi_roof` and the mast example.
