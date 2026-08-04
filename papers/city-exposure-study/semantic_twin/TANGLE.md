# How this got tangled, and where the knots are

A map of the study directory as it stands on 4 August 2026. It is written for the
refactor. It answers three questions: what happened, what does the published
number actually run through, and what is stuck to what.

Nothing here is a criticism of a decision. Most of the decisions were right at the
time. The tangle is what you get when six method changes land in three days and
nothing old is ever deleted.

## The clock

Every commit that touches this directory falls between 1 and 3 August 2026, plus
one on 4 August. That is 270 commits: 45, then 68, then 157.

The code is 73,429 lines of Python in 202 files. The notes are 49 markdown files,
about 1.9 MB. `outputs/` is 3.7 GB and `data/` is 4.7 GB.

Read that back. The whole thing is four days old. Nothing in it has had a second
pass that was not itself a third change.

## Five turns that reshaped the method

Each turn left working code behind and did not remove it. That is the whole story
of the tangle, and each turn maps to a specific pile of files.

### Turn 1. Monostatic loop to adjoint escape (1 August, 17:23 to 18:01)

The opening pitch was a closed loop. Transmitter, receiver and street view camera
all at the same point. A ray leaves, bounces up to three times, comes back. Both
ends of the path are visible from the camera, so both carry a material read off
the photograph.

Within forty minutes that was replaced. Rays now leave the head, bounce, and are
credited when they escape the crop. The credit is an assumed angular density of
base stations, evaluated at the exit direction. Reciprocity makes this the same
integral and it is far cheaper.

What it cost was not written down at the time. Under the loop, two of three
interactions were guaranteed to sit on a photographed surface. Under escape, only
the first is. Robin spotted this 34 hours later and said the idea had "kind of
been lost in translation".

**Left behind:** `MONOSTATIC_SBR.md` (3,150 lines) is the design document for the
loop. `semantic_twin/propagation/monostatic.py` (580 lines) builds the loop as a
side diagnostic. Neither feeds a published number.

### Turn 2. 28 GHz to 15 GHz (1 August, 19:46)

Offered as a convenience, taken immediately. The study now leads at the FR3
midpoint.

**Left behind:** a large amount of prose still argues at 28 GHz on purpose,
because that is the band the argument was made in. `MASONRY.md` and `ROUGHNESS.md`
are the main ones. A reader cannot tell which numbers moved and which did not.

### Turn 3. Height bands to facade tips (3 August, 13:44 to 15:12)

The old illumination law put base stations in a box: 13.5 to 43.5 m above the
head, 25 to 250 m away. Robin said the four numbers were arbitrary and he was
right. `DEPLOYMENT_GEOMETRY.md` section 7.5 had already measured that sweeping
the outer cap over its defensible span moved the headline by 7.8 dB, against a
between city spread of 4.93 dB. The largest lever in the study was a number
nobody could cite.

The replacement puts sources on facade tips, the roofline you photograph. Each
azimuth carries one source distance, read off the geometry. No bands, no cap.

**This turn is not finished.** `LAW_CHANGE.md` says so plainly: nothing has been
recomputed under the new law. `run_exposure.py` still runs the band law today.

**Left behind:** both laws are live in the same file. `directions.py` holds five
laws and seven prebuilt models, including two marked "fixed height" that exist
only to reproduce numbers computed before an earlier correction. The new law
lives somewhere else entirely, in `skyline.py` and `sources.py`.

### Turn 4. Scattered standpoints to an actual walk (3 August, 13:29, repeated 22:20)

"NOT a scattered blob of things in a square, which I keep seeing." Then again
nine hours later: "what part of this is 'a straight walk'?"

The exposure numbers came from a 3 m grid over walkable ground, filtered by five
gates and chained by nearest neighbour. That is a sampling design. It is
defensible as physics and it is not a walk.

**Left behind:** three things called a walk now exist.

| Module | What it builds | Who uses it |
|---|---|---|
| `propagation/walk.py` | grid over walkable ground, 3 m spacing | `run_exposure.py`, every published number |
| `propagation/route.py` (1,057 lines) | path along the panorama link chain | `run_next_event.py` and eight others |
| `propagation/street.py` | Google Routes A to B walking path | newest, picked when it stands nearer a camera |

`route.py` and `street.py` were both added on 3 August. `walk.py` still writes
the headline.

### Turn 5. Escape estimator to next event estimation (3 August, 18:49 to 23:03)

The newest change, and the one with the sharpest result. The two estimators
answer the same question and disagree by a factor of three to five.

| | next event | escape |
|---|---|---|
| multipath surplus, eleven squares | +0.30 to +0.57 dB | +1.10 to +2.63 dB |

The gap was chased down. It is not a missing range term, which was tested and
moves at most a quarter of it. It is not empty azimuths, since 100 % of azimuths
carry a roofline at both pilot squares. The escape estimator's assumed source band
fills whatever sky is visible, so a ray that bounced up a wall gets rewarded for
seeing more sky. The measured roofline is a thin rim and does not reward it.

The escape answer was largely restating how open the square is. It moves -6.04 dB
per unit sky fraction. Next event moves -0.70.

**Left behind:** two estimators, two drivers, and a headline figure built by the
one that is now understood to be measuring something else.

## What the published number actually runs through

This is the shortest path through the repository, and it is the thing a refactor
must not break.

```
run_exposure.py                            1,610 lines, the driver
  -> propagation/walk.build_walk           grid standpoints, not a route
  -> propagation/scene.classify_faces      material by triangle orientation
  -> propagation/semantic_binding.bind     image materials, 0 % coverage on the headline run
  -> propagation/directions.ROOFTOP        the OLD band law
  -> propagation/tracer.SbrTracer          escape estimator, 3 bounces
  -> propagation/exposure.BodyCoupler      Duke phantom, 1 W/m^2 reference
  -> outputs/exposure_korenmarkt/          directory named for one city, holds eleven
```

Six package modules, 2,541 lines, plus the 1,610 line driver. That is one tenth
of the 25,299 lines in the package.

Everything else in the repository is either feeding that path indirectly, or is
built and tested and connected to nothing that is published.

## The knots

### 1. Two illumination laws, both live, the retired one still writing the headline

`directions.py:355-440` holds `ROOFTOP`, `STREET_SMALL_CELL`, their path loss
variants, and two fixed height variants kept for reproducing superseded numbers.
`run_exposure.py:188` picks from three of them.

The replacement law is not in this file. It is in `propagation/skyline.py` (roofline
extraction) and `propagation/sources.py` (explicit source points), and only
`run_next_event.py` uses them.

`LAW_CHANGE.md` is 270 lines of which-numbers-survive tables. It lists 20 result
families that need recomputing and 15 that stand. The isotropic column survives
everything, because it has no sources in it.

**Refactor must decide:** does the band law stay as a documented control, or does
it go? If it stays, it needs a name that says it is not the method.

### 2. Two estimators, and no shared interface

`tracer.SbrTracer` deposits on escape. `run_next_event.py` connects to explicit
sources at every path vertex. They share the ray casting and nothing else. The
next event path is a script, not a module, so it cannot be called or tested the
way the tracer can.

**Refactor must decide:** is next event a mode of the tracer, or a second tracer?
The physics says it is a mode. The code says it is a script.

### 3. Three walks

Covered above. The one that writes the numbers is the one Robin objected to
twice.

`propagation/walk.py` and `walk.py` at the package root are unrelated. The first
is pedestrian standpoints. The second is Mapillary capture sequences. Same word,
different job. `scene.py` and `propagation/scene.py` have the same problem.

### 4. Materials are built, measured, and reach nothing

The material stack is real. SAM 3 segments panoramas, a fishnet cutter projects
segment contours onto the support mesh and cuts triangles along them, a posterior
turns classes into ITU-R P.2040-4 rows.

At Korenmarkt, `covered_fraction_by_area` is 0.106. On the eleven city headline
run it is 0.0 at every site.

Corrected 2026-08-04: Korenmarkt is not the best covered site, and this file said
it was. The 0.106 is the fused walk route. By the fishnet route Korenmarkt is
0.032, and Prague is 0.330, with Mexico at 0.234 and Madrid at 0.187. Both numbers
are true of different routes. Quote the route with the number.

The 0.0 on the headline run is also not a binding failure. That run uses
`--materials geometric`, which never calls the binding at all, and
`run_exposure.py:532` writes the zero as a literal in that branch.

Robin has ruled on this and the ruling is not "fix it": *"remember even if the
materials segmentation panorama is just for show and the material parameters and
everything doesnt do much, i want it"*. So the arm stays. What it needs is an
honest place in the pipeline, not removal.

**Left behind:** `semantics.py`, `concepts.py`, `sam3_concepts.py`,
`fuse_concepts.py`, `semantic_binding.py`, `materials.py`, `material_posterior.py`,
`facade_vlm.py`, `texture_evidence.py`. About 5,300 lines across nine modules,
whose names do not say what order they run in.

### 5. Two imagery providers, undocumented

Every single-panorama site uses Google Street View. The twelve station Korenmarkt
walk, the only multi-station set and the one carrying the SAM 3 binding, is
Mapillary. No document in the repository says the two arms use two providers.

The naming makes this worse on purpose. `semantic_twin/panorama.py:1` says
"Inhouse Street View" and calls `tile.googleapis.com`. That inconsistency is a
standing instruction, 1 August 17:23: *"Long story short dw about that leave it
be."*

### 6. Physics modules that touch nothing

Each of these is written, tested and documented. None of them is imported by
anything on the published path.

| Module | Lines | Reached by |
|---|---|---|
| `propagation/sionna_check.py` | 1,685 | its own test and CLI |
| `propagation/bystanders.py` | 1,534 | its own test and CLI |
| `propagation/antenna.py` | 1,292 | its own test and CLI |
| `foliage.py` | 926 | `run_foliage_study.py` only |
| `masonry.py` + `rcwa.py` + `floquet.py` + `kirchhoff.py` | 1,790 | three masonry scripts only |
| `body_layer.py` | 437 | body building scripts only |

That is 7,664 lines, roughly 30 % of the package, doing no work in the answer.

The foliage case is the clearest. `FOLIAGE.md` says merging it needs about twenty
lines in `SbrTracer._run_batch`: a per-class predicate marking a class as a medium
boundary rather than a surface. It was built as a separate estimator only because
`propagation/` was shared and not to be edited.

The bystander case is the most finished. 18 SMPL-X bodies exist, a completed run
sits in `outputs/bystander_study/`, and `run_exposure.py` contains zero references
to any of it.

The antenna case carries a warning. `tests/test_antenna.py:209-241` asserts that a
matched beam, every site putting its peak on the pedestrian, gives a
susceptibility bit-identical to no pattern at all. That is correct: a per-direction
gain that is constant over the direction being integrated cancels out of a
normalised density. It also means the literal ask, an array that beamforms to
itself, is invisible to this observable.

### 7. Half the code lives in scripts

The package is 25,299 lines. The top level scripts are 29,044. Only about 9,500
lines of the package are called by other package code, so `semantic_twin/` is not
a library with scripts on top. It is a second script folder that happens to be
importable.

The line between the two is arbitrary. Eight package modules have their own
`__main__` block and run as `python -m semantic_twin.propagation.bystanders`.
Meanwhile `propagation_blender.py` (2,116 lines) and `run_exposure.py` (1,610) sit
at the top level.

Script size is lopsided. The median script is 265 lines. The top five hold 7,600
between them.

### 8. Facts copied instead of read

- The list of eleven sites appears in six files and disagrees with itself: 11
  entries in three places (two in different orders), 8 in `build_site_fishnets.py`,
  2 in `sionna_check.py` and in `run_next_event.py`'s default. `config/` already
  has one JSON per city and nothing reads the list from it.
- 30 files re-derive `ROOT = Path(__file__).resolve().parent` and hand-build their
  own output paths.
- 53 files patch `sys.path`. Two insert the absolute string
  `/home/user/aegis/theory/scripts`.
- The crop radius grew from 130 m to 250 m and left tracks: `data/tiles/` and
  `data/tiles250/`, `inhouse_leaf_130m_f64.ply` as a module constant, 18 files
  mentioning both numbers, and Milan needing a special case because it has no
  130 m build.
- `outputs/exposure_korenmarkt/` holds all eleven cities. Two figure scripts read
  from it.
- Small helpers written twice: `sample_sphere`, `_cosine_hemisphere`, `write_ply`,
  `view_basis`, `_signed_area`, `ground_datum`, `site_mesh`.
- `FIGURES/` has two figure 24s and two figure 25s.

### 9. The notes are their own subsystem

49 markdown files. `MONOSTATIC_SBR.md` alone is 3,150 lines, larger than any
Python module by a factor of two.

They are not stale in the ordinary sense. They are precise records of runs that
happened under laws that have since changed, and most of them carry a marker
saying so. One commit on 3 August at 17:09, "Mark every number with the
illumination law that produced it", touched 39 files at once. 32 of the 49 docs
carry a modification time inside that twenty minute window.

Which means recent modification time tells you nothing about whether a note was
recently rethought.

`docs/README.md` is the index and it is honest. It flags `PAPER_METHODS.md` and
`REPORT.md` as not current despite what the parent README says, and it lists five
orphan notes that nothing links to.

The notes also cite each other by filename, heavily. 106 files outside `docs/`
name a doc file in prose or comments. `LAW_CHANGE.md` is cited 45 times,
`MONOSTATIC_SBR.md` 35, `BOUNCE_BUDGET.md` 23. Any rename breaks all of it.

## What is actually good here

Worth stating, because the list above reads worse than the code is.

- 99 % of package functions carry return annotations. 66 % of definitions have a
  docstring, and the docstrings explain reasoning rather than restating the
  signature.
- 55 test files, 14,968 lines, against 55 package modules.
- Zero heavy imports at package top level. 107 imports are deferred into functions
  to keep torch, trimesh and Mitsuba optional.
- The tracer is deterministic for a fixed seed, which is what made the aggregate
  audit conclusive when a figure turned out to be built from a partial sweep.
- Every knot above is already written down somewhere. `CODE_AUDIT.md` has the
  bounce count inconsistency. `LAW_CHANGE.md` has the law split.
  `PROJECT_INTENT.md` has the asks that never landed. The problem is that the
  knowledge is spread over 1.9 MB of prose and not one page.

This is well-made code with no floor plan.

## Refactor order

Ranked by payoff against effort. The first three are cheap and remove most of the
risk of a wrong number.

**1. One sites registry.** Read the eleven from `config/*.json`. Put `crop_m` in
the config so Milan's missing 130 m build is data, not a branch. Right now two
scripts can silently run on different city sets.

**2. One paths module.** `paths.py` with `root()`, `site_mesh(site, crop_m)`,
`output(kind, site, crop_m)`. Delete the 30 copies. Rename
`outputs/exposure_korenmarkt` to `outputs/exposure`.

**3. Name the estimator and the law in one place.** A single `method.py` that
says which law and which estimator are current, with the retired ones behind an
explicit `legacy` import. The goal is that a reader of the code can answer
"which law wrote this number" without reading `LAW_CHANGE.md`.

**4. Settle the walk.** One walk builder with a mode argument, not three modules.
The grid sampler stays as a mode, because it is what the published numbers used,
but it should not be the default.

**5. Split the library from the runners.** Move the eight `__main__` blocks out of
the package. Rule: the package holds functions, the top level holds `argparse` and
`main`.

**6. Break up `run_exposure.py`.** It is four things: the trace driver, the
validator, the report writer, and the published coverage ladder constants. The
ladder is data and belongs in JSON.

**7. Rename the collisions.** `walk.py` becomes `mapillary_sequences.py`.
`propagation/walk.py` becomes `standpoints.py`. `scene.py` becomes
`site_config.py`. The nine semantics modules become a `semantics/` subpackage
named in pipeline order.

**8. Pull the shared helpers into one `geom.py`.** About 150 lines that currently
exist twice each.

**9. Wire or retire the orphans.** Foliage first, since `FOLIAGE.md` estimates
twenty lines. Bystanders second, since the run already exists. The antenna needs
the invariance conversation before it needs wiring.

What not to do: a rewrite. The physics modules are tested and the docstrings carry
real reasoning. The problem is navigation and duplicated facts, not correctness.

## Open questions for Robin

These need an answer before step 3 or step 4 can be done properly.

- **Is the band law dead or is it a control?** `LAW_CHANGE.md` says it is being
  replaced. `run_exposure.py` still runs it. Both can be true for a while but not
  forever.
- **Which estimator is the paper's?** Next event says +0.30 to +0.57 dB. Escape
  says +1.10 to +2.63 dB. The disagreement is now explained. The headline figure
  still uses escape.
- **What is the walk, finally?** There are now three. The panorama link path and
  the Google Routes path were both added on 3 August and the grid sampler still
  writes the numbers.
- **28 GHz or 15 GHz as the lead band?** The FR3 pivot was offered as a
  convenience on 1 August and taken. A lot of prose still argues at 28 GHz.
