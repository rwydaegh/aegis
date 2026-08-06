# Refactor plan

Companion to `TANGLE.md`. That file says what is knotted. This one says what to
build instead, in what order, and how we know we did not break the physics.

The governing constraint is not tidiness. It is that the method has changed five
times in four days and will change again. Good structure here means the next
change costs one file, not a weekend.

## Rules of the refactor

Four policies, applied to every file we touch.

**Objectively worse code leaves.** Where two pieces of code do the same job and
one is plainly better, the worse one goes and git keeps the history. No
compatibility shim, no deprecation window. There is one consumer of this code and
he is in the room.

**Superseded code is archived, not deleted.** A module that has a clear
replacement moves to `archive/` with a one-line note saying what replaced it and
why. This is the rule for anything that is the record of a method that was
actually run and published under, because that record has to stay reproducible.

**Orphans go on a list and the default is to wire them in.** About 7,700 lines
are written, tested and connected to nothing. The assumption is that each one is
re-added unless there is a reason not to. Each gets a fate and a reason.

**Outputs are shaved on the same rule.** Where one output supersedes another, the
worse one goes. A figure rebuilt after a correction should not leave its
predecessor on disk and still referenced.

Above all: the numbers must not move by accident. A refactor that improves a
result is a bug until proven otherwise.

## The golden lock comes first

Nothing moves until the current answers are frozen.

The tracer is deterministic for a fixed seed. That is what makes this feasible
and it is worth a lot. We capture reference outputs for both estimators, both
laws, on at least one site, plus a fast tier of closed-form checks that needs no
mesh. Every later wave has to reproduce them or explain, per number, why it
moved.

This is not optional and it is not a formality. Half the pain recorded in
`docs/` is a number whose provenance nobody could recover.

## Target structure

Two halves, because the study genuinely has two halves. `LAW_CHANGE.md` proved
it: when the illumination law was replaced, the reconstruction side needed no
changes at all. That is a real seam and the package should show it.

```
semantic_twin/
  sites.py              Site registry, read from config/*.json
  paths.py              every filesystem path in the study
  runconfig.py          one frozen config object per run
  geo.py                ENU and WGS84

  acquire/              anything that talks to an external service
    tiles.py            Google 3D Tiles, with the placement cache
    streetview.py       Google Street View panoramas
    mapillary.py        Mapillary sequences
    routes.py           Google Routes walking paths
    cache.py            one cache policy, keyed by position not by URL

  scene/                geometry
    mesh.py             load, crop, precision
    ground.py           the ground datum
    fishnet.py          contour cutting
    surfaces.py         surface classes from orientation
    support.py          the support mesh

  vision/               images to labels to mesh
    provenance.py       what saw a surface, how well, and the gate
    vocabulary.py       what the evidence is allowed to say
    views.py            panorama to rectilinear crops, and back
    dense.py            Mask2Former, the entity axis
    prompted.py         SAM 3, the material axis
    fuse.py             many views into one sphere
    layers.py           instances into non-exclusive layers
    material.py         the cascade concepts run through
    panorama.py         the command that segments one panorama
    register.py         fitting a pose to the skyline
    conflict.py         where the image and the geometry disagree
    align.py            the command that writes a pose
    project.py          pixel to triangle, as adaptive tiles
    atlas.py            triangle-local decals
    ledger.py           the replayable observation store
    evidence.py         Dirichlet and Beta posteriors
    captures.py         which panoramas a site has
    tiles.py            the photogrammetry texture as a surface
    appearance.py       what a patch of it looks like
    texture.py          the texture as a material channel
    vlm.py              a vision language model as a backend
    bodies.py           SMPL-X

  materials/            labels to electromagnetic response
    itu.py              P.2040-4 rows
    roughness.py        the roughness prior
    binding.py          triangle to material, with provenance
    masonry.py          brickwork as a grating (rcwa, floquet, kirchhoff)
    foliage.py          canopy as a participating medium

  illumination/         where the sources are
    model.py            the protocol, plus isotropic
    roofline.py         skyline extraction, the facade tip law
    sources.py          explicit source sets
    bands.py            the legacy band law, kept as a control

  transport/            the ray tracer
    tracer.py           the core shoot and bounce
    escape.py           the escape estimator
    next_event.py       the next event estimator
    paths.py            path records

  exposure/             body coupling and observables
    coupler.py          the phantom
    observables.py      the ratio, the surplus

  report/               aggregation, tables, CDFs
  viz/                  Blender payloads and figures
  cli/                  one thin module per command
```

Nine subpackages for 25,000 lines is about 2,800 lines each. That is the right
size to hold in your head.

Two rules go with it. The package holds functions and classes. `cli/` holds
`argparse` and `main`. No module has both.

## The seven objects the design rests on

Structure is mostly these. Get them right and the folder layout follows.

### 1. `Site`

Loaded from `config/<name>.json`. Carries the anchor, the ENU origin, the ground
datum, which crops exist, which imagery provider it uses, and where its mesh and
panoramas live.

Kills the copied site list, the hardcoded `korenmarkt`, the `130m` in a module
constant, and Milan's special case. `Site.all()` becomes the one place that knows
there are eleven.

### 2. `RunConfig`

One frozen dataclass: site, crop, frequency, bounce budget, seed, walk kind,
illumination law, estimator, materials mode. Serialised into every output
manifest alongside the git sha.

Today this is forty argparse flags in `run_exposure.py` and a manifest assembled
by hand. One object means a new method parameter is one field, and every
downstream reader sees it without being taught.

This is the single change that makes the next method change cheap.

### 3. `IlluminationModel`

A protocol with three implementations: `Isotropic`, `BandLaw`, `RooflineLaw`.

Today `directions.py` is one dataclass with a string field switching five laws
through a chain of `if self.law == ...`. That is the largest avoidable complexity
in the package and it is why the new law had to be built somewhere else entirely.

Contract every implementation must satisfy: the density integrates to 1 over
4 pi. That is one test that covers all of them and any future one.

### 4. `Estimator`

A protocol with `EscapeEstimator` and `NextEventEstimator`, both taking the same
scene, walk and illumination model.

Next event is currently a script, so it cannot be called, composed or tested the
way the tracer can. Given the two disagree by three to five times, they need to
be swappable in one line so the comparison is a config change rather than a
different program.

### 5. `Walk`

A protocol with `GridWalk`, `PanoramaChainWalk` and `StreetRouteWalk`, all
returning the same record.

The grid sampler stays, because it is what every published number used. It stops
being the default.

### 6. `SurfaceBinding`

Triangle to class, permittivity, roughness, and provenance. Provenance is a
required field, not an optional one.

The fact that image evidence reaches 0 percent of surface area on the headline
run should be visible in the object, not buried in a JSON key nobody reads.

### 7. `PanoramaSource`

A protocol with `GoogleStreetView` and `Mapillary`. The study uses both and no
document says so. Making it a config field on `Site` turns an undocumented
accident into a recorded choice.

While we are here: every `inhouse` becomes `google`. 104 files, including 79
mesh filenames. The naming was left alone on purpose once and is now being
changed on purpose.

## Tests

The instruction is tests that earn their place. Five kinds do.

**Golden regression.** Pin the published numbers. Refactor must reproduce or
explain. This is the one that actually protects us.

**Physics invariants.** Energy is conserved. Reflectance stays in [0, 1]. Every
illumination density integrates to 1 over 4 pi. The foliage slab reproduces the
`E_2` identity. These catch a sign error that a golden test would only catch if
it happened to be on the golden path.

**Cross-estimator agreement.** On a geometry with a closed form, escape and next
event must agree. They currently disagree on real cities for a reason we think we
understand, so the closed-form case is the check that the reason is the geometry
and not a bug.

**Protocol contracts.** One parameterised test per protocol, run against every
implementation. Add a new law or a new walk, inherit the test suite for free.

**Property tests on geometry.** The fishnet cut preserves area. The ground datum
is idempotent. A crop contains its own anchor.

What we do not write: tests that assert a function returns what it returns.

## Quality targets

Baseline from `qlty`, on the non-test code, measured today:

| Metric | Now |
|---|---|
| Lines of code | 50,420 |
| Cyclomatic complexity | 4,396 |
| Cognitive complexity | 5,836 |
| Smells | 182 across 64 files |
| Functions with too many parameters | 85 |
| Functions above the complexity threshold | 45 |
| Files above the total complexity threshold | 41 |
| Deeply nested control flow | 10 |

Targets: no function above the complexity threshold in the package (scripts get
more latitude), the many-parameters count down by most of its value (`RunConfig`
alone should take a large bite), and total lines down. Some of the drop comes
free from deleting duplicates and archiving superseded code.

`qlty` is installed at `~/.qlty/bin/qlty` and the repo already has a
`.qlty/qlty.toml`. `papers/**` is not excluded from it, so this directory is
already being scored.

## The orphan list

Default is wire it in. Reasons given where the default does not hold.

| Module | Lines | Fate |
|---|---|---|
| `foliage.py` | 926 | **Wire.** `FOLIAGE.md` estimates twenty lines in the tracer: a per-class predicate marking a class as a medium boundary rather than a surface. It was built separate only because `propagation/` was shared and not to be edited. That reason is gone. |
| `propagation/bystanders.py` | 1,534 | **Wire.** A completed run already sits in `outputs/bystander_study/`. Asked for twice. |
| `body_layer.py` | 437 | **Wire**, with bystanders. It is their geometry. Moved to `vision/bodies.py` on 2026-08-04. Not stranded at script level, three scripts call it, but stranded from the published path. Wiring it needs `propagation/bystanders.py`, which the vision pass did not own. |
| `masonry.py`, `rcwa.py`, `floquet.py`, `kirchhoff.py` | 1,790 | **Wire** as a material response option under `materials/`. It is a scattering model that currently talks to nobody. |
| `propagation/antenna.py` | 1,292 | **Wire, after a conversation.** Its own test shows a matched beam gives a result bit-identical to no pattern at all, which is correct physics and means the headline configuration provably changes nothing. Wiring it without settling that would ship a knob that does not turn. |
| `propagation/monostatic.py` | 580 | **Keep and wire as a diagnostic.** This is the original idea. `DECISIONS.md` promised it as a derived quantity and never delivered it. |
| `propagation/sionna_check.py` | 1,685 | **Keep, move.** It is a validation oracle, not production code. It belongs beside the tests, not in the package. |
| `atlas_ledger.py`, `decal_atlas.py` | 767 | **Keep, not archive.** Investigated on 2026-08-04. The fishnet is not their replacement: the fishnet cuts geometry so a triangle can carry one class, the atlas paints inside a triangle and leaves the mesh alone. They are alternatives to the fishnet, not a superseded version of it. Wiring the atlas would change the mesh contract the tracer binds against, which is a physics change and out of scope under the golden lock. Moved to `vision/atlas.py` and `vision/ledger.py`. Blocked on finding 13, which has to be settled before either can read a real depth raster. |

## Everything else on the list

Things I would add, beyond what you named.

**Provenance is a type, not a convention.** Every output manifest carries its
`RunConfig`, the git sha, the illumination law and the estimator. The reason
`LAW_CHANGE.md` needed 270 lines of survives-or-not tables is that this was not
true. Make it structural and that document becomes a query.

**Kill the crop radius in filenames.** `inhouse_leaf_130m_f64.ply` encodes the
crop, the provider and the precision in a string that eighteen files parse. Crop
is a `RunConfig` field, the path comes from `paths.py`.

**Figures named by content.** `FIGURES/` currently has two figure 24s and two
figure 25s, because two work streams numbered independently. Number at assembly
time, not at creation time.

**One cache policy.** Tiles are cached by position in one place and by address in
another, which is already recorded as a bug that was fixed once. One module.

**CI on this directory.** Nothing runs against it today. A slim job on push: ruff,
the fast test tier, and the closed-form checks.

**Ruff config that does something.** `pyproject.toml` sets a line length and
nothing else. A real ruleset, with the physics naming conventions triaged the way
the AEGIS `qlty.toml` already triages them.

**Performance, measured before touched.** `PERFORMANCE.md` exists and the GPU box
is gone, so the profile has changed. Profile first, then take the low-hanging
items: the brute force nearest-cell path, per-ray Python loops, and anything
recomputed inside the trace loop.

**Decide the doc filename question.** 106 files cite doc filenames in prose. The
timestamp rename is staged and not committed. Either rewrite the references or
revert and put the dates inside the files.

## Rulings made during the refactor

Recorded here so they are not re-litigated later.

**Milan's crop radius is 170 m, and the gallery's 200 m is not a contradiction.**
`config/milan_duomo.json` and the acquisition record both give 170 m for the
support mesh, which is what the study traces on. `measure_city_metrics.py` and
`make_city_sheet.py` render the gallery tile at 200 m and the caption says so.
Those are two different jobs. `Site.built_crop_m` is the support mesh, 170 m. The
gallery radius stays a gallery concern.

Checked and cleared along the way: the 200 m mesh on disk is not the defective
first tile pull. It carries 476,410 faces, which is the second pull cropped to
200 m. The broken pull kept 233,997 and is not on disk.

**The ray tracing backend belongs in the run identity.** `bench_cuda_250m.json`
and `bench_llvm_250m.json` are the same run under two Mitsuba backends and 58 of
103 leaves differ. The median surplus moves 0.001 dB, which is small against the
0.047 dB between-square gap the study treats as meaningful. But `connections` is
an integer count and it differs too, 805,334 against 805,326 at one standpoint
and 597,945 against 598,383 at another. The backends disagree about whether some
connection rays are blocked. That is now a lead with the physics audit, because a
missing self-intersection guard on a shadow ray would bias the bounced term
downward, and next event already reports the smaller surplus of the two
estimators.

**The walk is a top level package, `semantic_twin/walk/`, not a corner of
`propagation/`.** The plan named no home for it. Where the pedestrian stands is
not a propagation concern. It is chosen before any ray is cast, it decides what
the study is averaging over, and the three rules that choose it disagree enough
to move the headline: Korenmarkt reads 0.032 by the capture chain and 0.106 by
the fused walk, and Prague reads 0.330 under the rule that gives Korenmarkt
0.032. Burying that inside `propagation/` is what let three answers to one
question sit in three files without a reader seeing they were three answers.

This forced a rename. `semantic_twin/walk.py` already held the name and meant
something else: the *capture* walk, the set of panoramas a site was photographed
from, and its parallax spread. Two different things called walk in one package
was the naming collision `TANGLE.md` flagged. The module is now
`semantic_twin/capture_set.py` and the name `walk` belongs to the pedestrian.

`semantic_twin/propagation/walk.py` and `semantic_twin/propagation/route.py`
survive as re-export shims, each marked with a comment saying so, because
`run_next_event.py` still imports from them and is being edited concurrently.
The driver rewiring pass deletes both.

## Waves

Each wave is a set of agents that can work without stepping on each other. A wave
lands and is checked before the next starts. That matches what you asked for
earlier: pilot, look, green light.

**Wave 0, running now.** Golden lock. Physics and correctness audit. Output and
data inventory. No code moves.

**Wave 1, the spine.** `sites.py`, `paths.py`, `runconfig.py`, `geo.py`. Every
copied site list, hardcoded path and loose flag is routed through them. Nothing
else changes shape. This wave alone removes most of the wrong-number risk and it
is mechanical enough to verify by reading a diff.

**Wave 2, the protocols.** `IlluminationModel`, `Estimator`, `Walk`,
`SurfaceBinding`, `PanoramaSource`. The string switches become subclasses. This is
the wave that makes the next method change cheap, and it is the one that most
needs the golden lock to be already in place.

**Wave 3, the move.** Files go to their subpackages. `inhouse` becomes `google`.
Duplicated helpers collapse. Superseded code goes to `archive/`. Mostly rename
and re-import, verified by the tests from waves 0 to 2.

**Wave 4, the orphans.** Wire foliage, bystanders, masonry, the monostatic
diagnostic. Each one lands with the test that shows it changes a number, or the
measurement that shows it does not.

**Wave 5, the polish.** Complexity hotspots, `run_exposure.py` split into driver,
validator and reporter, output shaving per the inventory, CI, docs.

## Settled decisions

1. **The package keeps the name `semantic_twin`.** Every doc, commit message and
   cross-reference uses it, and the name is wrong only in emphasis.

2. **All waves run, review at the end.** One branch, one review. This raises the
   stakes on the golden lock, because it becomes the only thing standing between
   the refactor and a silently changed number. If wave 0 comes back thin, the
   waves get gated after all and that is my call to make.

3. **The `docs/` timestamp rename stays.** References are left broken. The notes
   are as tangled as the code was, and rewiring pointers into a set of files that
   is about to be replaced is wasted work.

4. **A new, lean docs set gets written.** Short, current, to the point. The 49
   existing notes stay untouched as the historical record. The new set is not a
   rewrite of them, it is what a reader needs today: the method as it stands, how
   to run it, what each number means, and what is known to be open. This lands in
   wave 5, once the structure is settled, because writing it earlier means
   writing it twice.
