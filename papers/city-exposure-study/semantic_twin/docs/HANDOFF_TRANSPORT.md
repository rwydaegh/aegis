# Handoff: the transport package

Written 2026-08-04, on a stop order at 99 percent of the account budget. The work
was cut off early and deliberately, before anything that draws a random number was
touched.

## Read this first

**No traced number can have moved. I did not edit the tracer.** `tracer.py`,
`exposure.py`, `monostatic.py` and `sionna_check.py` under
`semantic_twin/propagation/`, and `semantic_twin/illumination/sources.py`, are all
byte identical to what they were when I started. I verified that by copying each
one before I began and running `diff` against the copy at the end. All five report
`UNTOUCHED`. `git diff` on those paths shows nothing from me.

So there is no bit-exactness question to answer, because there is nothing to
compare. No RNG draw order changed, no float literal changed, no operation order
changed. What follows is a design and a plan, not a move that needs checking.

The one thing worth knowing before you trust that sentence: the file I was going
to restructure is `propagation/tracer.py`, and the restructure I had designed
does move code inside `_run_batch` and `_deposit`. None of it happened. If you
pick this up, you are starting from a clean tracer.

## What exists now

One new package, `semantic_twin/transport/`, three files, all additive. Nothing
imports it except itself. Deleting the directory returns the tree to where it was.

| File | What is in it | State |
|---|---|---|
| `transport/model.py` | `Estimator` protocol, `Gather` protocol, `Surplus` record, `require_credit` | Finished, ruff clean, hand checked |
| `transport/observers.py` | `PathRecord`, `PathRecorder`, `BounceEvidenceTally`, `MultiGather` | Bodies copied verbatim, but see the warning below |
| `transport/__init__.py` | Re-exports the above, and says the package is incomplete | Finished |

I checked that `import semantic_twin.transport` works, that
`require_credit("next_event", ISOTROPIC)` raises with a readable message, and that
`Surplus(direct=1.0, total=2.0).surplus_db` is 3.0103. `ruff check` and
`ruff format --check` pass on all three files.

### The warning on observers.py

`transport/observers.py` holds **copies** of four classes that also still exist in
their original homes. `PathRecord`, `PathRecorder` and `BounceEvidenceTally` are
duplicated from `propagation/tracer.py`. `MultiGather` is duplicated from
`illumination/sources.py`. Nothing imports the copies, so they are inert, but two
copies of a class is exactly the failure mode `TANGLE.md` section 8 is about.

Whoever picks this up should either finish the move on the same pass or delete
`transport/observers.py`. Do not leave it sitting there.

`TERMINATIONS` is the one thing I did not duplicate. `observers.py` imports it
from `propagation.tracer`, which points backwards through the layering and is
temporary. It is the only import in the new package that does.

## Nothing moved out of illumination/sources.py

Asked plainly: **I did not move `NextEventGather`.** It is still at
`semantic_twin/illumination/sources.py:364`, untouched, and `MultiGather` is still
at line 510. `illumination/__init__.py` still exports both. `MIN_CONNECT_M` is
still at line 44.

The only trace of the intended move is the inert copy of `MultiGather` in
`transport/observers.py` described above.

## The Estimator protocol, and why it has that shape

This part I did finish, and it is in `transport/model.py` with the reasoning in
the module docstring. The short version.

```python
class Estimator(Protocol):
    name: str  # one of runconfig.ESTIMATORS

    def illumination(self) -> IlluminationModel: ...
    def estimate(self, origin, *, ground_z_m=0.0, seed=None) -> Surplus: ...
```

`Surplus` carries `estimator`, `law`, `direct`, `total`, and a free-form `detail`
dict, with `surplus` and `surplus_db` as properties.

The shape comes from reading both estimators rather than from the plan. Both are
handed the same `SbrTracer`, both are asked about one standpoint, and both produce
a line of sight term and a total. Their ratio is the multipath surplus, which is
the quantity the whole escape-versus-next-event result is stated in
(+0.30 to +0.57 dB against +1.10 to +2.63 dB). That ratio is the honest shared
return.

### What I refused to unify, and why

**The angular power spectrum is not on the protocol.** The escape estimator
reduces to `rho(u)` on a few hundred cell grid and that is what the body coupler
integrates against a phantom. Next event never forms one: it connects a vertex to
a point and accumulates a scalar, and there is no direction grid in it anywhere.
Putting `rho` on the protocol would make next event return an empty array to
satisfy a type. The consequence is worth stating in the paper: **the dosimetry arm
of this study is escape only**, and that is physics, not a gap in the code.

**`direct` and `total` are not comparable between estimators.** Escape normalises
its density to one over 4 pi so free space `chi` is exactly 1. Next event averages
over the site set and leaves the antenna count, the transmit power and a `4 pi` in
front of both terms. Those constants cancel in the ratio and nowhere else. The
protocol therefore promises the ratio and explicitly does not promise the two
terms. This is the same split `illumination/model.py` found when it said both laws
normalise but normalise different things.

**`sionna_check.py` is not an Estimator.** It computes the same `chi` with a
different ray tracer, so it looks like a third implementation, and it is not one.
It cannot run per standpoint, it needs `sionna-rt` and a GPU, and for the real
runs it needs a Modal account. Forcing it behind `estimate(origin, seed)` would be
a fiction. It is an oracle that scores a whole scene in batch.

**`monostatic.py` is not an Estimator either.** It returns `g = P_r / P_t`, a
link budget for a radar standing where the pedestrian stands. There is no
`direct`, no `total` and no surplus in it. What it genuinely shares with next
event is the `Gather` hook, not the estimator contract, which is why I wrote
`Gather` as its own protocol in `model.py`. `NextEventGather`, `MonostaticGather`
and `MultiGather` all satisfy it today without any change.

### How it meets `credited_by`

It asks rather than repeats. `require_credit(name, model)` calls
`semantic_twin.illumination.credited_by(model)` and raises `TypeError` unless the
estimator's name is in the returned tuple. There is no second copy of the
"escape reads a density, next event reads positions" reasoning anywhere in
`transport/`. I checked the two live cases by hand: `credited_by(ISOTROPIC)` is
`("escape",)` and `SourceSet` satisfies `PlacedIllumination` and not
`AngularIllumination`, so it comes back `("next_event",)`.

## Decisions I made but did not carry out

These are calls, not options. I am recording them so the next person does not
re-litigate them, but none of them is implemented.

### The body coupler goes to its own package, `semantic_twin/exposure/`

Not into `transport/`. Three reasons.

1. It imports AEGIS (`aegis.engine`, `aegis.geometry.mesh`, `aegis.tissue`) and
   nothing else from this package. It is an adapter to an external engine.
2. It knows nothing about rays, bounces, geometry or illumination. Its input is a
   spherical function plus a scale factor. Any transport that produces one can
   feed it.
3. Putting it in `transport/` would make the transport layer depend on a dosimetry
   engine, and every import of the tracer would sit above that dependency.

Target: `semantic_twin/exposure/coupler.py`, holding `BodyExposure`, `BodyCoupler`
and `describe` verbatim from `propagation/exposure.py`.

I did **not** create `exposure/observables.py`, which the plan lists as "the ratio,
the surplus". The surplus is the estimator's own return type, so it lives beside
the protocol that returns it, in `transport/model.py`. A protocol whose return type
sits in a third package is worse than either alternative. If someone later wants
`exposure/observables.py` for the dB conversions and the cross estimator table,
that is a reasonable place for it, but it should not hold `Surplus`.

### monostatic.py: keep, move to `transport/monostatic.py`

It is transport. It is a next event estimate of the co-located return, riding the
same trace through the `gather` hook, and `MultiGather` exists precisely so it and
the next event connection can share one trace. Keeping it as a diagnostic is the
plan's call and I agree with it.

The reason it is not wired in is not a physics reason. The wiring point is
`run_exposure.py`, which I was forbidden to touch. The work is small: build a
`MonostaticGather`, wrap it with the next event gather in a `MultiGather`, pass it
as `gather=`, and write `MonostaticResult.scalars()` into the row. `run_monostatic.py`
already does exactly this and can be read as the reference.

### sionna_check.py: keep, and keep it in the package

I am overruling `REFACTOR_PLAN.md` here, which says move it beside the tests.
Target: `transport/sionna_check.py`, with the docstring saying in its first line
that it is an oracle and never writes a published number.

Reasons.

1. `tests/` is not a package in this repository. There is no `tests/__init__.py`,
   so anything moved there is importable only through pytest's rootdir insertion.
   A module with its own `__main__`, five argparse subcommands and a Modal GPU app
   deployment does not belong behind that.
2. It drives our own tracer. `tracer_reference()` at line 939 builds an `SbrTracer`
   and runs it at the same standpoints. It is a consumer of transport, not of
   tests.
3. `python -m semantic_twin.propagation.sionna_check site --site korenmarkt` is a
   command the study actually ran, and `CROSS_VALIDATION.md` quotes its output.
   Moving it breaks that invocation for no gain.
4. The plan's reason for moving it was "it is a validation oracle, not production
   code". That argues for labelling it and keeping it off the live path. It does
   not argue for relocation. Nothing on the published path imports it today and
   nothing should.

### `direct_from_sites` and `visible` stay in `illumination/sources.py`

This one I am least sure about and I want to flag it as a judgement call rather
than a finding.

The argument for moving them is strong: `direct_from_sites` is the `direct` half
of `(direct + bounced) / direct`, it casts shadow rays, and finding 12 is
precisely about it disagreeing with `NextEventGather._connect_once` over which
sites are too close. The two halves of one estimator sitting in two packages is
how finding 12 stayed invisible.

The argument against is that moving them forces `SourceSet.direct()` at
`illumination/sources.py:314` to import from `transport`, which inverts the
layering, and `run_next_event.py:185` calls `sources.direct(...)` and I could not
rewire it.

My call: leave them, and have `NextEventEstimator` import `direct_from_sites`
directly rather than going through `SourceSet.direct`. Then both halves of the
surplus are visible in one class, the layering stays one way, and
`SourceSet.direct` survives as a convenience for the driver. The estimator's
docstring is where finding 12 should be named.

## What I would do next, in order

1. **Delete `transport/observers.py` or finish the move.** Do not leave the
   duplicate classes. If finishing, delete them from `propagation/tracer.py` and
   `illumination/sources.py` in the same edit.
2. **Move the body coupler.** `propagation/exposure.py` to
   `semantic_twin/exposure/coupler.py`, leave a staging shim behind, rewire the
   six callers listed below. This is the lowest risk piece in the whole job: no
   RNG, no tracer, one small file.
3. **Move `NextEventGather` and `MIN_CONNECT_M`** out of `illumination/sources.py`
   into `transport/next_event.py`, and write `NextEventEstimator` around it. Leave
   `thin`, `silhouette_cloud`, `build_source_set`, `SourceSet`, `direct_from_sites`
   and `visible` where they are.
4. **Move the tracer**, and only then attempt the restructure in the next section.
   A plain move with no restructure is bit-exact by inspection and is worth
   landing on its own.
5. **Move `monostatic.py` and `sionna_check.py`** into `transport/`. Both are
   import-only edits.
6. **Write the tests.** The list I had is in the section after next.

### The tracer restructure I designed and did not do

Recording it because the reasoning took a while and because it is the risky part.

`SbrTracer._run_batch` takes 13 parameters and `SbrTracer._deposit` takes 14.
Between them they carry `models`, `normalisations`, `rho`, `rho_direct`,
`cell_counts`, `exit_power` and `totals`, which are seven pieces of one thing: the
escape estimator's accumulator. The plan lists "functions with too many
parameters" as a quality target and these two are among the worst in the package.

The design was an `EscapeDeposit` class in `transport/escape.py` owning all seven,
with `launch(cell)`, `escape(...)`, `truncate(...)` and
`reduce(origin, ground_z_m, seconds) -> PointResult`. `_run_batch` drops to six
parameters. `trace()` becomes: build the deposit, loop the batches, return
`deposit.reduce(...)`. The statement it makes is true and is the point of the
whole exercise: **the tracer has two deposit points, one at escape and one at each
vertex. Escape estimation is a rule for the first, next event a rule for the
second.** They become symmetric hooks instead of one buried private method and one
public argument.

`PointResult` would move to `escape.py` with the deposit, because it is the escape
estimator's reduction and putting it there is what breaks the import cycle
(`tracer.py` imports `escape.py`, never the other way). `tracer.py` re-exports it.
`source_shell_radius_m` and `_range_to_the_source_shell` move too, since they are
only read by the range charge diagnostic inside `_deposit`. **Finding 7 lives at
`tracer.py:449` and must move with them, unfixed.** The shell is centred on the
world origin, which is 35 to 45 m below the lowest mesh point, and it stays that
way.

Two things make this harder than it looks.

- `make_sensitivity_study.py:163` and `:171` define `HarvestTracer`, which
  subclasses `SbrTracer` and overrides `_run_batch` and `_deposit` with exact
  positional signatures and `*args, **kwargs` pass-through. Any change to either
  signature breaks it silently. The fix is to give `SbrTracer` a
  `_new_deposit(models)` factory that `HarvestTracer` overrides to return a
  recording subclass of `EscapeDeposit`, which is better code than overriding two
  private methods. `HarvestTracer._cell_counts` then becomes `deposit.cell_counts`
  and the `_run_batch` override disappears entirely.
- Bit-exactness has to be proved, not argued. The method I set up and did not get
  to use: copy the current `tracer.py` to a scratch directory before editing,
  import both the copy and the new module in one process, run both on the same
  geometry, standpoint and seed, and assert every scalar is equal with
  `==` rather than `np.isclose`. I confirmed the baseline is sound first:
  the working tree `tracer.py` differs from `git show HEAD:` by exactly one line,
  the import at line 36, and `exposure.py` and `monostatic.py` are identical to
  HEAD. So HEAD is a valid reconstruction for all three.

### The tests I had planned

None of these are written. They are here so the list is not re-derived.

- **Closed form agreement.** On a geometry where the answer is known, escape and
  next event must agree. `tests/test_next_event.py` already has the plane case and
  `propagation/closed_form.py` has `ground_plane_susceptibility`. This is the test
  that says the three to five times disagreement on real cities is the geometry
  and not a bug.
- **Attaching a gather moves no bit.** Trace once with `gather=None` and once with
  a `NextEventGather`, assert every scalar of the `PointResult` is `==`. The
  docstrings claim this in three places and nothing checks it.
- **Empty models moves no bit either.** `NextEventEstimator` would pass `{}` where
  `run_next_event.py` passes `{isotropic, rooftop}`. I read `_deposit` and
  convinced myself no RNG draw depends on the model dict, so `chi_bounce` should
  be identical either way. It should be asserted, not read.
- **The bounce budget is respected exactly.** No recorded path has more than
  `max_bounces` surface vertices, at several budgets.
- **Throughput never exceeds what entered.** Every segment's throughput is at most
  the previous one, on a passive scene.
- **Russian roulette is unbiased.** Run with `roulette_start=1` and
  `roulette_start=9` over enough samples and check the means agree within the
  standard error. `docs/BUGS.md` records that roulette is inert at the defaults, so
  this needs the non-default setting to test anything.
- **`require_credit` against every registered law.** Parameterised over
  `LAW_REGISTRY`, so a new law inherits the check.

All of these except the closed form one run without a mesh and belong in the fast
tier.

## Exact lines the final rewiring pass must change

I rewired nothing, so this is the full list, not a remainder. Line numbers are as
of 2026-08-04 and the two drivers are being edited concurrently, so re-grep before
trusting them.

**`run_exposure.py`**

- Line 33, `from semantic_twin.propagation import (...)` through line 45. Of the
  names in it, `DEFAULT_MAX_BOUNCES`, `SbrTracer`, `TraceConfig` and
  `trace_standpoints` become `semantic_twin.transport`. `ISOTROPIC`, `ROOFTOP` and
  `STREET_SMALL_CELL` are already `semantic_twin.illumination`. `PEC_PERMITTIVITY`
  and `ground_plane_susceptibility` are `propagation.closed_form`, and
  `MitsubaGeometry` and `PlaneGeometry` are `propagation.geometry`. Neither of
  those two files was in my scope and neither has moved.
- Line 46, `from semantic_twin.propagation.exposure import BodyCoupler, describe`
  becomes `from semantic_twin.exposure import BodyCoupler, describe`.

**`run_next_event.py`**

- Line 47, `from semantic_twin.propagation.sources import SITE_LIFT_M, NextEventGather, build_source_set`
  splits: `NextEventGather` from `semantic_twin.transport.next_event`, the other
  two from `semantic_twin.illumination`.
- Line 50, `from semantic_twin.propagation.tracer import SbrTracer, TraceConfig`
  becomes `semantic_twin.transport`.
- Lines 174 to 234 are the loop that `NextEventEstimator` was meant to replace.
  Line 185 calls `sources.direct(geometry, evaluate)` for the whole standpoint
  batch at once. I checked that `direct_from_sites` loops standpoints
  independently, so calling it one origin at a time is bit-identical and the
  estimator can own it. Line 199 builds the gather with
  `np.random.default_rng(args.seed + 1000 + i)` while line 206 traces with
  `seed=args.seed + i`. That offset of 1000 is the convention the estimator has to
  keep if the swap is to move no number.

**Outside the two drivers**, and outside what I was allowed to touch:

- `semantic_twin/materials/foliage.py:778` does a deferred
  `from ..propagation.tracer import fresnel_power_reflectance, specular_share`.
  `materials/` was off limits to me. This one needs the shim until someone with
  that package rewires it.

**Callers I would have rewired myself but did not**, grouped by what they import.
None of them is broken today, because nothing moved.

- `propagation.tracer`: `bench_pinned.py:36,56,59`, `bench_workers.py:38`,
  `measure_escape_range_term.py:68`, `measure_surplus_spread.py:38`,
  `run_crop_convergence.py:93`, `tests/test_antenna.py:46`,
  `tests/test_bystanders.py:248,264`, `tests/test_determinism.py:38`,
  `tests/test_invariant_audit.py:97`, `tests/test_invariant_interface.py:23`,
  `tests/test_invariant_reciprocity.py:36`, `tests/test_materials_package.py:42`,
  `tests/test_next_event.py:17`, `tests/test_propagation.py:49`,
  `tests/test_sionna_check.py:48`.
- `propagation.exposure`: `export_propagation_payload.py:70`,
  `repair_torn_sites.py:42`, `run_material_ablation.py:39`,
  `tests/test_invariant_audit.py:736`, `tests/test_invariant_remesh.py:101`,
  `tests/test_propagation.py:620`.
- `propagation.monostatic`: `run_monostatic.py:30,414`, `tests/test_monostatic.py:23`.
- `propagation.sionna_check`: `tests/test_sionna_check.py:28,380`.
- `make_sensitivity_study.py:58` imports `SbrTracer` from the package and then
  subclasses it, see the restructure warning above.
- `tests/golden/capture.py:298` imports `SbrTracer` and `TraceConfig` from
  `semantic_twin.propagation`. **That file must not be edited.** Whatever else
  moves, `semantic_twin/propagation/__init__.py` has to keep re-exporting those two
  names, so it becomes a staging shim itself rather than being deleted.

## Shims I left

None. Nothing moved, so nothing needed one.

The existing staging shims in `propagation/` are not mine and are unchanged:
`directions.py`, `skyline.py`, `sources.py`, `walk.py`, `route.py` and `scene.py`.

## New defects found

None. I read `tracer.py`, `exposure.py`, `monostatic.py`, `illumination/model.py`
and `illumination/sources.py` closely and `sionna_check.py` in outline, and found
nothing that is not already in `docs/BUGS.md`. `docs/BUGS.md` is untouched by me,
and the numbering still ends at 14.

I did not read `sionna_check.py` line by line. If there is a fifteenth finding in
this scope, that is where I would look for it.

## Things I am unsure about

Stated as uncertainty on purpose.

- **Whether `direct_from_sites` should have moved.** Argued both ways above. I
  left it, and I can see the case for the other call. Finding 12 gets harder to
  see either way until someone decides which of the two halves gets the 0.5 m
  floor.
- **Whether `EscapeEstimator` scoring one law is right.** The escape estimator
  scores any number of laws in one trace at no extra cost, which is why
  `run_exposure.py` passes three. A protocol that reports one law per call throws
  that away unless the class also exposes the raw `trace()`. My plan was to expose
  both, `estimate()` for the protocol and `trace()` for the cheap multi-law path,
  but two entry points on one class is a smell and I did not get to live with it.
- **Whether `geometry.py` and `closed_form.py` belong in `transport/`.** Both are
  arguably transport. `geometry.py` is the intersector and `closed_form.py` is what
  the estimators are checked against. Neither was in my scope so I left both in
  `propagation/`, which means `propagation/` survives this refactor as a real
  package rather than an empty shell of shims. That may or may not be what anyone
  wants.
- **The `Gather` protocol signature is the one place I did finish checking.**
  `NextEventGather.vertex`, `MonostaticGather.vertex` at `monostatic.py:267` and
  the nine positional arguments the tracer passes at `tracer.py:677` all agree,
  name for name and in order. So this protocol is not a guess. I list it here only
  because I checked it last and it deserves to be re-checked by whoever moves the
  tracer.
