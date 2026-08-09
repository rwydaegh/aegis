# Physics and correctness findings

From the audit run on 2026-08-04, before the refactor moved any code. Every item
here was reproduced numerically, not inferred from reading.

The refactor does not fix these. The golden lock pins current behaviour, the
refactor has to reproduce it, and each fix lands afterwards as its own commit
with its own before and after number. That way the effect on the paper stays
legible instead of being buried in a rename.

Ranked by whether a published number moves.

## Status pass 2026-08-09

Every finding below was re-checked against the production tree, the branch that
carries the `first_material_interaction_v1` contract. Original text is kept as
written. Status lines are added under each heading and nothing else was edited.

Two things changed the ground under this file since 2026-08-04. Production
transport is now `first_material_interaction_v1`, described in
[the current production contract](CURRENT_PRODUCTION_CONTRACT.md), so findings
about deep multi-bounce gathers and the mixed suffix are sensitivity-only. And
production roughness is now `finish_only`, so finding 2 no longer describes the
active rule. See finding 2 for what replaced it, which is not what finding 2
asked for.

Line numbers in status lines are from the production tree and are relative to
the package, so `semantic_twin/transport/next_event.py:617` rather than the old
`propagation/sources.py:382`.

## Moves a published number

### 1. Next event throws away the specular lobe

Status 2026-08-09: fixed on the production contract, still open on the bare
gather. Under `first_material_interaction_v1` the order-one all-specular term is
exact and is credited `reflectance * share` at
`semantic_twin/transport/specular.py:908`, which is the exact complement of the
diffuse `throughput * (1 - share) / pi` the gather still credits at
`semantic_twin/transport/next_event.py:584`. The partition is enforced at run
time by `_validate_first_material_interaction`,
`semantic_twin/exposure/roofline_campaign.py:1822`, which refuses the field
unless the direct atoms are exact, the all-specular support is complete at order
one, and the mixed suffix mass is exactly zero. The bounce-two discard is moot
because the contract has no second bounce.

Still open where no specular transport is attached, which is the legacy hybrid
gather. That is what the two strict xfails at
`tests/test_invariant_reciprocity.py:236` and `:256` pin, and their `measure()`
helper builds a `NextEventGather` with no `specular_transport` and
`max_bounces=2`. Nothing in the invariant suite yet asserts the closed partition
on the production estimator, so the fix is enforced by the campaign validator and
not by an invariant.

`propagation/sources.py:382`. The connection is credited
`throughput * (1 - share) / pi`, so only the diffuse part of the reflection is
ever routed to a source. The docstring at line 324 defers the specular share to
"the ray continuation and to image sources". No image source connection exists
anywhere on that path.

Measured at 15 GHz on the shipped materials, the estimator discards 54 percent of
the power reflected at bounce 1 and 73 percent at bounce 2.

Crediting it as an upper bound, rerouted as Lambertian, moves the surplus from
+0.45 to +1.04 dB at Korenmarkt and from +0.55 to +1.18 dB at Brussels. Across six
squares it closes 39 to 62 percent of the gap between the two estimators.

**This changes the story, not just a number.** `NEXT_EVENT.md` attributes the
whole escape-versus-next-event gap to the escape band filling whatever sky is
visible. About half of it is this instead.

Why no test caught it: every test in `tests/test_next_event.py` sets
`rms_height_m = 1.0` m, which makes `share` identically zero. That is the one
regime where the defect cannot appear.

### 2. The facade roughness drops the term that matters

Status 2026-08-09: the quadrature defect is superseded, the substance is still
open, and the production answer moved the other way. Production now reduces a
two scale surface with `finish_only`, the default at
`semantic_twin/materials/catalogue.py:240` and passed explicitly at
`semantic_twin/exposure/execution.py:351` and `:473`. Quadrature is retained as
a named historical sensitivity and `masonry_two_level` as research only,
`semantic_twin/materials/roughness.py:241-248`.

`finish_only` drops the mortar relief, which is what this finding asked for, and
also drops `unit_scatter_mm`, which is what this finding said was the term that
matters. Measured on the shipped config at 15 GHz and normal incidence, the
brick facade class:

```
rule                 s (m)      specular share
finish_only          3e-05      0.9996   <- production today
quadrature           1.155e-03  0.5901   <- what every published number ran through
masonry_two_level    3.119e-03  0.0213   <- the route that reads unit_scatter_mm
```

The ground class moves the other way, 0.0035 quadrature to 0.0285 finish only.
Roof and soffit are Gaussian classes and do not move.

So the production facade is now very nearly a mirror, against 0.59 before and
0.02 under the reading this finding argued for. Facades are 44 percent of crop
area, and under `first_material_interaction_v1` the `share` is exactly the split
between the exact specular channel and the stochastic diffuse one, so this sets
which of the two carries the facade term.
[The publication physics decisions](PUBLICATION_PHYSICS_DECISIONS.md) records
the decision and quotes 0.59053 and 0.0214631, but does not state the 0.9996
that production actually uses, and no campaign-level before and after was found
for the rule change. `semantic_twin/materials/roughness.py:323-325` still says
switching the default to the route that reads `unit_scatter_mm` is the fix this
finding asks for.

`propagation/scene.py:113-134`. The finish RMS is folded in quadrature with the
deterministic mortar joint relief, and `unit_scatter_mm` is ignored. The config's
own note says `unit_scatter_mm` "is the random part of a brick wall that actually
matters at 10.7 mm".

The Rayleigh closure is a model for the random part. So the code keeps the term
the closure is wrong for and drops the term it is right for.

Facades are 44 percent of crop area in the headline run. Facade specular share at
normal incidence is 0.590 as shipped, 0.017 if `unit_scatter` is read as an RMS,
0.439 if read as a full width.

Coupled to finding 1: at the larger roughness the discarded specular fraction
falls from 0.544 to 0.400 and the gap closed rises to 56 percent, so finding 1
survives either reading. Settle this one first, then re-measure that one.

### 3. The absorbed density mean was unweighted over unequal triangles

Status 2026-08-09: confirmed fixed. In the production tree the weighted mean is
written at `semantic_twin/exposure/coupler.py:229`, `:290`, `:361` and `:642`,
and the uniform-yaw endpoint carries it as `yaw_mean_area_mean_sab_w_m2` at
`:517`. The line references in the 2026-08-06 note below have shifted since.

Status: fixed on 2026-08-06. Scalar and batched couplers now report the
area-weighted body mean as `p_abs / body.total_area`. Checkpoint identity binds
the exact float64 triangle areas. Legacy monolithic checkpoints retain full
`Sab`, so the weighted mean can be recomputed without retracing. Independent
verification passed 247 tests, skipped 4, marked 10 as expected failures, and
deselected 1. See [the publication physics decisions](PUBLICATION_PHYSICS_DECISIONS.md)
for the corrected result medians.

Historical evidence: `propagation/exposure.py:93` used `mean_sab_w_m2` as a plain
mean over Duke's 56,024 triangles, whose areas varied by a factor of 9,300 with
a coefficient of variation of 1.02. The current scalar and batched couplers are
in `semantic_twin/exposure/coupler.py:89-95` and
`semantic_twin/exposure/coupler.py:194-204`, where they compute
`p_abs / body.total_area`.

Pre-fix measurements: against the published spectra, area weighting raised it by
a median of 5.18 percent, or +0.219 dB, varying 2.3 to 6.1 percent across
standpoints. The p95 over p05 spread moved from 3.827 to 3.869 dB.

The pre-fix values were published at `run_exposure.py:675`,
`propagation/report.py:244` and
`FIGURES/make_walk_exposure_cdf.py:186`.

The audit identified a one-line correction, `result.p_abs / total_area`. The
current couplers apply it as `p_abs / body.total_area`.

Why no test caught the pre-fix behavior: `tests/test_propagation.py:650` asserts
the isotropic case equals `T0/4`, which is exactly unbiased by symmetry.

### 4. Foliage converts nepers to decibels with the wrong factor

Status 2026-08-09: confirmed fixed, and the stale constant is gone too.
`POWER_DB_PER_NEPER` is `10 / ln 10` at `semantic_twin/materials/foliage.py:92`
and is used at `:247`. The two routes agree to 1.3e-15 across 1.3, 11.2, 28.8
and 61.5 GHz at 1.0 and 4.5 m. The invariant at
`tests/test_invariant_foliage.py:124-141` is a plain parametrized assertion, not
an xfail. No `sensitivity.json` survives and neither 2.078 nor 4.157 appears
anywhere, because `semantic_twin/materials/foliage_study.py:156` and `:260` now
derive the reference optical depth from `sigma_tau_per_m` in nepers at run time.

Status: fixed in the current refactor. The direct conversion and
`slab_transmission` now agree at `10/ln10`, and the former expected-failure
invariant is a passing test. Historical foliage outputs still record the old
factor and must be regenerated before reuse.

The former `foliage.py:239` used 8.686 where ITU-R P.833-10 makes it 4.343. Equation (12)
reads `Lscat = -10 log10 { e^-tau ... }`, so `e^-tau` is a power transmittance and
the conversion is `10/ln10` per unit sigma.

The module contradicted itself: the same sigma through `slab_transmission` gave
exactly half.

The old value fired at `run_foliage_study.py:267`. The shipped reference optical depth in
`sensitivity.json` is 2.078 and should be 4.157. `FOLIAGE.md` quotes its whole
crossing table "at the reference optical depth of 2", and at tau 4 the
medium-versus-cut 0.5 dB crossing moves from 6.0 to 4.6 percent.

### 5. The masonry grating solver uses the wrong Fourier factorisation

Status 2026-08-09: still open, and off every production path. The Laurent form
is now at `semantic_twin/materials/masonry/rcwa.py:298-316`, fed by `:338`,
which inverts the Toeplitz of eps rather than building the Toeplitz of 1/eps.
The module docstring names it at `rcwa.py:31-41` and the strict xfails at
`tests/test_invariant_rcwa_limit.py:138` and `:157` still pin it. Reproduced on
a lamellar grating at period lambda/400: TE is exact to six digits at every
truncation, TM converges slowly to the analytic effective-medium answer, 42
percent off at M=2 and 0.74 percent off at M=128. The sign of the TM bias came
out high on this referee rather than low, but the defect is unambiguous.

Cannot reach a campaign number. Nothing under `semantic_twin/exposure/`,
`semantic_twin/transport/` or `semantic_twin/cli/` references masonry, and the
only production-adjacent link is `semantic_twin/materials/roughness.py:340`,
which imports wall geometry and never `rcwa` or `kirchhoff`. That route is
`MASONRY_RULE`, status `research_only`.

`rcwa.py:188-206` uses Laurent's rule where Li's inverse rule is required for the
TM case. This is the classic RCWA error and it converges to the right answer
slowly rather than failing loudly.

On an analytic deep-subwavelength referee, TM is 79 percent low at M=2 and still
2 percent low at M=128. On the study's own bed joint wall at the production
truncation, specular is 4 percent high and diffuse 17 percent low, with the error
falling as 1/n.

Why no test caught it: the energy conservation test in `tests/test_rcwa.py`
cannot see it. R moves 2.4 percent while R+T stays at 1e-15.

### 6. Kirchhoff compares an angle against a direction cosine width

Status 2026-08-09: still open, and off every production path.
`semantic_twin/materials/masonry/kirchhoff.py:623` still sets
`beam_width = radians(receiver_resolution_deg)` and `:624` compares it against
quantities on the direction cosine grid. The same defect is at `:657`, where
`beam_width / step` is a sigma in grid units. No cosine appears in that block.
Three strict xfails at `tests/test_invariant_audit.py:1040-1042` pin it. Same
scope argument as finding 5.

`kirchhoff.py:622-624`. A receiver beam of R degrees at scattering angle theta
covers `radians(R) * cos(theta)`, not `radians(R)`. Off by exactly one over
cosine, which is 11.5 times at the sweep's 85 degree row.

`MASONRY.md`'s comb-above-trend numbers shift by 1.3 to 4.6 dB at 60 degrees. The
28 GHz five degree entry goes from 3.47 to 1.58 dB, which crosses below the
paper's own 2 dB instrumental floor.

### 7. The range diagnostic charges from the wrong centre

Status 2026-08-09: still open, and it cannot fire in a campaign. The shell
radius is still the largest vertex norm measured from the world origin at
`semantic_twin/transport/tracer.py:312`, and the sphere is still solved about
the origin at `semantic_twin/transport/trace_kernel.py:589-592`, duplicated at
`semantic_twin/transport/device_tracer.py:61`. No recentring on the mesh
centroid or bounds anywhere. The diagnostic only runs when
`range_weighted_escape` is true, and that is false at
`semantic_twin/runconfig.py:212` and `:331`,
`semantic_twin/exposure/execution.py:525` and
`semantic_twin/cli/exposure.py:131`, and is never set by the roofline setup or
campaign. So this taints the quoted `NEXT_EVENT.md` numbers and nothing else.

`tracer.py:449` puts the source shell on a sphere centred at the world origin,
which sits 35 to 45 m below the lowest mesh point.

Charged range at Korenmarkt varies 236 m straight up, 283 m horizontal and 332 m
downward, all of it artefact.

The published -0.13 and -0.35 dB in `NEXT_EVENT.md` reproduce exactly. Recentring
gives -0.11 and -0.24 dB. **The conclusion survives**, since a properly centred
charge moves things even less than the paper claims, but the quoted numbers are 20
to 25 percent too large.

### 8. The validation gate compares a band average to a band centre

Status 2026-08-09: still open, and it still carries the paper's agreement claim.
`semantic_twin/exposure/validation.py:11` imports only
`ground_plane_susceptibility` and `:60` evaluates it at band centres.
`ground_plane_band_average` is never called from the package, only from tests.
Reproduced on the production tree: lowest band above the horizon, centre
1.7320287 against band average 1.7478202, maximum absolute difference 0.01579,
still larger than the quoted 0.0122 `max_abs_error`. Off the roofline path,
since `validate()` is the exposure-study gate and the campaign does not call it,
but the one percent agreement statement in the methods rests on it.

`run_exposure.validate()`. `closed_form.ground_plane_band_average` exists for
exactly this and is not called. The mismatch is 0.0158 in the lowest band against
a reported `max_abs_error` of 0.0122.

So the headline "1 percent agreement" is mostly quadrature, and the gate cannot
resolve an estimator error below about 1 percent.

### 8b. Korenmarkt's material binding runs through a cross-mesh join

Status 2026-08-09: moot on the production path, still live on the legacy branch.
Three things moved. The comparable-city cohort is at 250 m with
`primary_material_mode` set to `atlas` in `config/city_cohort_manifest.json`, so
the 130 m fishnet is not what production reads. Korenmarkt carries only
`inhouse_leaf_250m_f64.ply` at 250 m, so the two-build ambiguity does not exist
there. And the atlas is now bound by exact support-mesh hash:
`semantic_twin/exposure/execution.py:373-385` computes the mesh SHA-256 and
passes `expected_mesh_sha256`, which `semantic_twin/materials/atlas.py:466`
enforces by raising rather than joining. `semantic_twin/scene/site_fishnets.py:246`
also resolves the cut mesh through `paths.site_mesh`, preferring the `_f64`
build. The centroid join survives only under `--materials walk` or
`--materials semantic`.

Not fully verifiable here: `outputs/site_semantics/` is absent from this
worktree, so the configs, the hash gate and the mesh inventory were read but the
built Korenmarkt 250 m atlas artefact was not.

Found during the golden capture, not by the audit.

Korenmarkt's fishnet was cut against `inhouse_leaf_130m.ply`. The run traces the
double precision rebuild, `inhouse_leaf_130m_f64.ply`. Those are different files,
so the binding has to join one triangle set onto another by centroid.

That join keeps 86.65 percent of source triangles, refuses 13.32 percent on the
normal test, and has a median centroid distance of 0.249 m. Prague cuts and traces
the same file and matches 100 percent at zero distance.

So the site the study calls its material showcase is the one where a quarter metre
sits between a segmented facade and the triangle that receives its material.

Be careful about what this does and does not imply. The Prague binding moves
`chi_rooftop` by +0.45 dB on the median and Korenmarkt's moves it by almost
nothing, but Prague also has ten times the coverage, 32.95 percent of area against
3.13 percent. The coverage difference alone roughly accounts for the difference in
effect. So this is a quality defect at the showcase site, not by itself evidence
that the null material result is an artefact. Fixing the join and re-measuring is
what would settle that.

### 8c. The coverage ladder test was checking nothing

Status 2026-08-09: fixed, and the guard survived the refactor. `Case.clear()` at
`tests/golden/cases.py:68-85` deletes only `clears` globs under `outputs/` and
raises on any path whose name lacks `golden`. Called from
`tests/golden/capture.py:236` and `tests/test_golden_regression.py:480`, with
`tests/golden/coverage_ladder_korenmarkt_130m.json` present.

`run_exposure.reusable()` lets `--coverage-ladder` accept a rung already on disk
whose settings match. That is right for a sweep that has to survive being stopped
and wrong for a test, which re-read three runs instead of making them. The golden
case ran in 1.7 s and traced no rays.

Now fixed in the golden harness: the case clears its own rungs first, and the
clear refuses any path whose name lacks `golden`, so a published stem cannot be
caught by a careless pattern. The retraced numbers matched the reused ones to the
last bit, so nothing was wrong with the values. The test was simply not testing.

## Silent wrong answer, not currently fired

### 9. Foliage never initialises the inside-canopy flag

Status 2026-08-09: still open, and pinned. `inside` is still initialised to all
false at `semantic_twin/materials/foliage.py:808`, with the defect written into
the code at `:799-807` so the fix carries its own before and after number.
Parity only toggles on a canopy face crossing at `:885`. The target invariant is
a strict xfail at `tests/test_invariant_foliage.py:149-171`. Cannot reach a
campaign number: nothing under `semantic_twin/exposure/`,
`semantic_twin/transport/` or `semantic_twin/cli/` imports `FoliageTracer`.

`foliage.py:775`. An observer starting inside the canopy hull inverts the parity
flag for the whole trace, and the ray then collides in vacuum forever.

It fails silently. `chi` returns exactly 0.000000 where the exact answer is
0.26244, nothing raises, and `absorbed_in_medium_fraction` reads 1.0000, which is
impossible at albedo 0.9.

Does not fire in `run_foliage_study.py`, where the observer is at 1.5 m and the
canopy base at 4.0 m. `FOLIAGE.md` part 5 proposes exactly the sweep that
triggers it.

### 10. A passive grating returns more power than it receives (fixed)

Status 2026-08-09: confirmed fixed, reproduced independently. Ran the passivity
ladder directly over period-to-wavelength ratios 3.75, 20, 100 and 400, both
polarisations, truncations 4, 8, 16, 24 and 32. All 40 reflectances land in
[0, 1] with no violation and none of the 54, 56.7 or 58 values. The fix is
`_normal_flux` at `semantic_twin/materials/masonry/rcwa.py:226-234` and
`_numerical_mode_branches` at `:236-295`, wired at `:345-356`. The xfail is gone
and `tests/test_invariant_audit.py:994` is a plain strict test.

Fixed on 2026-08-06. The numerical eigensystem now removes each candidate mode's
local eigenvalue residual with a biorthogonal Rayleigh quotient. A local
roundoff bound separates lossless propagating modes from lossy modes without
letting deeply evanescent orders set their tolerance. Propagating modes are
directed by their normal Poynting flux. Evanescent and lossy modes are directed
by decay. The strict passivity witness now covers both polarisations, five
truncations and periods from the masonry pitch down to one four hundredth of a
wavelength. It passes under Haswell, SkylakeX, Prescott and Zen OpenBLAS
dispatch.

`rcwa.py`, the same solver as finding 5 and a separate failure from it. A lossless
passive grating on a semi-infinite substrate returns total reflectance far above
1, and nothing raises. Measured:

```
p/lam = 1/100  TM   M=4  0.02015   M=8  54.09     M=16  0.01764   M=32  0.0172
p/lam = 1/400  TE   M=4  12.79     M=8  0.07818   M=16  0.07818   M=32  12.79
p/lam = 1/400  TM   M=4  0.02015   M=8  0.01849   M=16  56.7      M=32  58.14
```

Reflectance of 58 from a passive structure is not a slow convergence, it is a
broken solve. The dangerous part is that it is not monotone in the truncation, so
the usual defence does not work: a convergence sweep can step straight over it,
and picking a larger M is as likely to land on a bad value as a good one.

Why no test caught it: `tests/test_rcwa.py:129` already asserts
`0 < total_reflectance < 1` on exactly this patterned half space, but evaluates it
at a single point (masonry cell, 10 GHz, 20 degrees, harmonics (6,4)). The failure
is non-monotone in period, polarisation and truncation, so one point steps over
it. The right assertion was already in the suite, sampled once.

The energy identity is not the blind spot here and cannot be. On a patterned half
space the substrate modes are not plane waves, so the solver reports the budget as
undefined rather than guessing: transmitted efficiency is `nan` by design on every
run of this geometry, correct answers included. An `R + T` assertion would fail on
the NaN rather than sail through it, and no energy test is applied to this
geometry at all.

Not reached by any published number. The masonry stack is research code and is not
on the tracer's live path. It is recorded here because anyone who wires it in will
hit this before they hit finding 5.

Found independently by two agents. Pinned by
`tests/test_invariant_audit.py::test_a_passive_grating_never_reflects_more_than_it_receives`.

### 11. An empty walk wins the walk contest

Status 2026-08-09: first half fixed, second half still open, and neither can
reach a campaign. The nan comparison is gone: an empty candidate is scored
`float("inf")` and skipped at `semantic_twin/walk/site.py:224-229`, and
`:235-236` raises when every candidate is empty, so no nan reaches
`path_candidates_m`. The silent empty walk is unchanged.
`semantic_twin/walk/site.py:262-269` still only writes a `note` when no camera
is within `max(stride_m, 5)`, `:538-541` still returns the zero-point walk at
zero stride, and the `site_walk` docstring at `:444-446` still claims it raises.
Every stride default is still 6.0, at `semantic_twin/runconfig.py:183` and
`:323`, `semantic_twin/cli/exposure.py:123` and
`semantic_twin/cli/next_event.py:46`. The roofline campaign is pinned to
`walk_path="street"` at `semantic_twin/exposure/roofline_setup.py:248` and
raises on an empty walk at `semantic_twin/exposure/roofline_campaign.py:272-273`
before any trace.

`walk/site.py:194`, in `_nearest_of`, reached by `--walk-path closest`. Each
candidate walk is scored by the mean distance from a standpoint to the nearest
admitted camera, and the smaller mean wins. A candidate with no standpoints
scores `nan`, `nan < best_gap` is False, so it loses without ever being compared.
The other candidate wins by default rather than by measurement, and `nan` is
written into `path_candidates_m` in the manifest.

A candidate really can come out empty. `_keep_near_the_street` drops every camera
further from the routed walking path than `max(stride_m, 5)`, and at
`--walk-stride-m 0` that is a flat 5 m. Mexico City's Zocalo is the square where
it happens. The Zocalo is 240 m across with no pedestrian way mapped inside it,
so Routes walks the streets around it. Measured against the cached route and the
admitted set on disk, all twelve cameras are off that 276.5 m path and the
nearest is 19.8 m off:

```
19.8  24.5  29.7  32.7  39.7  40.5  50.0  53.1  54.5  56.4  62.1  67.1
```

None within 5 m, so the street candidate is trimmed to zero standpoints.

The second half is worse than the scoring. At `--walk-stride-m 0`,
`--walk-path street` on its own returns a `Walk` holding zero standpoints and
nothing raises. The provenance carries a `note` saying no camera is within 5 m,
which is the only signal, and no caller reads it. The docstring of `site_walk`
says it raises rather than quietly falling back, and here it neither raises nor
falls back. It returns an empty sample.

Reproduced on the analytic caster with a routed path 60 m off every camera:

```
street,  stride 0  -> standpoints: 0, nothing raised
closest, stride 0  -> path_candidates_m {'links': 0.0,  'street': nan}
closest, stride 6  -> path_candidates_m {'links': 3.45, 'street': 60.07}
```

Not currently fired. Every driver defaults `--walk-stride-m` to 6.0, and above
zero the stride lays standpoints along the routed line itself, so the candidate
is never empty and the comparison is real. The last line above is the healthy
case: the street path is scored at 60.07 m and loses honestly.

Why no test caught it: the golden lock does not cover this path at all, and says
so. `tests/golden/capture.py` records `next_event_walk_paths` as a deliberate
hole, because `street` and `closest` both call the Google Routes API and a
network call does not belong in a golden test. Only `--walk-path links` is
locked.

### 12. Only one half of the surplus refuses a site that is too close

Status 2026-08-09: still open, deliberately, and it is on the production path.
The gather still refuses a site nearer than `min_connect_m` at
`semantic_twin/transport/next_event.py:617`, and `direct_from_sites` still keeps
every site with `distance > 0.0` at `semantic_twin/illumination/sources.py:212`.
The estimator docstring at `semantic_twin/transport/next_event.py:942-944` names
the mismatch and says it is preserved until it can be changed and measured in
its own commit. The production direct term runs through that function, called at
`semantic_twin/transport/next_event.py:1848`. The roofline connection has the
same shape, `distance > 0.0` at `semantic_twin/illumination/roofline.py:339`,
and `floor_m` still defaults to 0.0 at
`semantic_twin/illumination/sources.py:151` and `:368`.

The exposure changed with the source model. Roofline sources sit on the observed
route-aligned roofline rather than on lifted facade tips, so a source a few tens
of centimetres from a 1.5 m standpoint is much less likely than it was. No guard
was added, so it is not impossible.

Found on 2026-08-04 while moving the illumination code into
`semantic_twin/illumination/`, not by the audit.

The next event surplus is `(direct + bounced) / direct`. The two terms disagree
about which sites are physical.

`sources.NextEventGather._connect_once` drops any site closer than
`MIN_CONNECT_M`, 0.5 m, from the vertex it is connecting from. The constant's own
note says why: a site is a point standing for a real antenna of finite size, and
`1/r**2` at a few centimetres is meaningless.

`sources.direct_from_sites` has no such floor. It keeps every site with
`distance > 0.0` and sums `1/r**2` over all of them.

So a site that lands very close to an evaluation standpoint enters `direct` and
is refused by `bounced`. It does not shift the answer a little. At Korenmarkt the
direct term is 4.7e-4 over about 1,500 sites, so one site at 0.1 m contributes
`100 / 1500 = 0.067`, which is 140 times the whole term. The surplus would
collapse to 0.00 dB and the standpoint would read as having no multipath at all.

Not currently fired. Across the three next event golden fixtures the per
standpoint direct term has a maximum over median of 1.01, 1.51 and 1.09, so no
site is anywhere near a standpoint in any of them. The exposure is real though:
sites sit on facade tips lifted 0.5 m, standpoints are heads at 1.5 m, and the
silhouette fan runs from 0.05 to 85 degrees with no near range floor unless
`--floor-m` is passed. A standpoint under an arcade or in a narrow passage can
see a tip a few tens of centimetres away.

Why no test caught it: `tests/test_next_event.py` and `tests/test_source_thinning.py`
both place sites tens of metres from the origin, which is the regime where the
two halves cannot disagree.

The fix is one line, and which line is a real choice rather than an obvious one.
Giving `direct_from_sites` the same 0.5 m floor makes the two halves agree.
Removing the floor from the gather makes them agree the other way and reintroduces
the singularity. Either way it lands as its own commit with its own before and
after number, per the rule at the top of this file.

### 13. The two depth conflict tables disagree on every code

Status 2026-08-09: still open, and still not wired, which was the thing worth
re-checking. Both tables are unchanged, at
`semantic_twin/vision/depth_comparison.py:119-126` and
`semantic_twin/vision/conflict.py:36-42`, and the `conflict.py` docstring at
`:17-21` says so. `SparseAtlasLedger` at `semantic_twin/vision/ledger.py:82` is
still constructed only in `tests/test_ledger.py`. The surface atlas builder added
by the refactor did not join them: `semantic_twin/scene/surface_atlas_builder.py`
carries only `max_sky_conflict` and `min_conflict_range_m`, which feed the
registration gate rather than the ledger. Every other consumer uses the 0 to 6
`DECISIONS` convention consistently, at
`semantic_twin/vision/body_placement.py:40` and `:92` and
`semantic_twin/scene/fishnet/regions.py:81` and `:118`. The collision becomes
real the first time a `DECISIONS` raster is routed into the ledger.

Found on 2026-08-04 while moving the image evidence into `semantic_twin/vision/`,
not by the audit.

Depth conflict is written by one file and read by another, and each keeps its own
integer table. They do not agree on a single value.

`compare_mesh_depth.py:63` writes the raster:

```
no_mesh 0  agree 1  uncertain 2  front_blocker 3  mesh_or_pose_blocker 4
dynamic_object 5  no_depth_evidence 6
```

`vision/conflict.py`, in `DepthConflictState`, reads it:

```
AGREEMENT 0  UNCERTAIN 1  FRONT_BLOCKER 2  MESH_POSE_CONFLICT 3  NO_MESH_HIT 4
```

Every code is shifted by one and the two ends do not line up, so the shift is not
even a consistent offset. `no_mesh` and `AGREEMENT` are the same integer and are
opposite meanings, which is the worst pair of the seven to collide.

Measured on a 10,000 pixel raster drawn at the observed class shares, 0.15 no
mesh, 0.62 agree, 0.15 uncertain, 0.05 front blocker, 0.03 mesh or pose blocker,
seed 0xAE615. The script calls 6,234 pixels `agree`. Asking the ledger for
`AGREEMENT` returns 1,497 rows, and those are exactly the `no_mesh` pixels. The
answer is not short, it is the complement: every pixel where the depth check
confirmed the mesh is dropped, and every pixel where there was no mesh to check
against is painted onto the surface as confirmed evidence.

Codes 5 and 6 have no counterpart at all. Handing either one to
`SparseAtlasLedger.append` raises `ValueError: depth_conflict contains an unknown
state`, so a raster carrying any dynamic object pixel fails outright rather than
mislabelling.

Not currently fired. Nothing calls the ledger outside its own tests, which is
finding 13's only defence and is the same defence as finding 9's. The two files
have never been run against each other.

Why no test caught it: `tests/test_ledger.py` builds its rasters from
`DepthConflictState` members and `tests/test_compare_mesh_depth.py` builds its
own from `DECISIONS`. Each table is self-consistent and each suite passes. No
test imports both, so nothing in the repository ever compares them.

The fix is not a renumbering. The script's vocabulary is the richer of the two
and the enum cannot express `dynamic_object` or `no_depth_evidence` at all, so
whoever wires these together has to decide what the ledger should do with a
pixel that a person walked through. That is a modelling choice, and it lands as
its own commit.

### 14. The default tree species is decided by the order of a source tuple

Status 2026-08-09: still open at source, routed around by every current caller.
The tie-breaking `min` is at `semantic_twin/materials/foliage.py:297`. Verified
in a throwaway process: `ret_parameters(15e9).species` is `ginkgo` at sigma 0.74,
seven rows tie exactly at the 12.5 GHz column, and reversing `_RET_ROWS` in
memory returns `dawn_redwood` at sigma 0.44. No raise, no envelope, first wins.

No caller hits the tie today. `ret_parameter_candidates` at
`semantic_twin/materials/foliage.py:331` keeps every species and is what
`evaluate_p833_segments` uses at
`semantic_twin/materials/vegetation_transport.py:558`, and
`semantic_twin/materials/foliage_study.py:156` pins `species="london_plane"`.
`evaluate_p833_segments` itself has no caller outside its tests. So the defect is
mitigated in the shim, not fixed at source.

Found on 2026-08-04 while moving `foliage.py` into `semantic_twin/materials/`,
not by the audit.

`materials/foliage.py:303`, in `ret_parameters`. With no `species` given, the
nearest cell of Tables 5 to 8 is chosen by `min(rows, key=...)` on the log
frequency gap. At 15 GHz, seven species are tabulated at 12.5 GHz and every one
of them is 0.263 octaves away, so the key is an exact seven way tie and `min`
returns whichever row is written first in `_RET_ROWS`.

That decides the extinction, which is the one parameter the answer is most
sensitive to. Species at 15 GHz, and what a 10 m canopy crossing transmits:

```
himalayan_cedar  sigma 0.90  T = 1.23e-4      <- last of the tied rows
ginkgo           sigma 0.74  T = 6.11e-4      <- first, and what you get today
korean_pine      sigma 0.50  T = 6.74e-3
trident_maple    sigma 0.47  T = 9.10e-3
dawn_redwood     sigma 0.44  T = 1.23e-2
cherry_japanese  sigma 0.18  T = 1.65e-1
```

Reversing `_RET_ROWS`, which every convention treats as a safe edit, changes the
default from ginkgo to dawn_redwood, sigma from 0.74 to 0.44 per metre, and that
10 m crossing by a factor of 20. Across every species the module will accept at
15 GHz the extinction spans 0.124 to 0.9 per metre and the crossing spans a
factor of 2,300.

Nothing warns. `ret_parameters` raises on an unknown species and never mentions
the tie, and `FoliageMedium.from_p833` and `medium_for_spec` both default to
`species=None`. The written provenance does name the chosen species, so a
manifest records ginkgo, which makes this recoverable after the fact but not
before it.

The module already knows this is not a defensible choice. `ret_parameter_envelope`
exists, and its docstring says a single species "is a choice the evidence does
not support". The default path does not call it.

Why no test caught it: `tests/test_foliage.py` and `tests/test_invariant_foliage.py`
either pass an explicit species or build a `FoliageMedium` directly, so nothing
exercises the tie. A test that pinned `ret_parameters(15e9).species` would have
turned a silent reordering into a failure.

Not currently fired. Nothing on the tracer's live path calls this. Anyone who
sweeps a canopy crossing will fire it on the first run.

The fix is not a sort key. Either the tie has to raise and make the caller name a
species, or the default has to return the envelope rather than one row.

## Puts a camera in the wrong place, no published number moves

### 11. The ground under a camera is bounded from above and not from below, and neither bound is the one that fires

Status 2026-08-09: still open, unchanged. `search_up_m` is still 5.0 at
`semantic_twin/scene/camera_ground.py:139`, the ceiling is still
`ground_z + search_up_m` at `:158`, and `:84` still takes the topmost surface at
or below it. No floor, and no spread or peak-to-peak rejection anywhere in
`ground_elevation` or `camera_altitude`. `semantic_twin/vision/align.py:148-155`
has the same one-sided form. The quality fields are still emitted at
`camera_ground.py:51-53` and still read by exactly one consumer,
`semantic_twin/report/panorama_registration.py:54`, which copies
`ground_spread_m` into a table row and gates nothing. The production callers at
`semantic_twin/acquire/streetview.py:257` and
`semantic_twin/acquire/mapillary.py:429` ignore them. Effect on a campaign is
indirect: it perturbs panorama pose height, so it reaches the atlas material
labelling rather than the transport kernel.

Found during the geometry refactor, not by the audit.

`support_mesh.camera_altitude`, now `scene/camera_ground.py`. The downward cast
starts at `camera_ground_z_m + search_up_m` with `search_up_m` fixed at 5.0 m,
and takes the topmost surface at or below that. The docstring says the ceiling
"keeps an arcade roof out of the answer". There is no floor at all, so a hole in
the photogrammetry that exposes a surface thirty metres down would be taken
silently.

Neither half is what actually goes wrong. Measured over the 127 distinct cameras
that carry a support-mesh ground reading across all eleven sites, the median
departure from the scene datum is +0.058 m and the low tail stops at -1.26 m. The
high tail does not: 12 cameras land more than 1 m above the datum, 10 more than
2 m, and one at Mexico Zocalo lands 4.83 m above it. Every one of those sits
inside the 5 m ceiling, so the guard that exists cannot see them. The camera's
2.5 m height is then added on top.

The wide ones look like a camera standing on something rather than on the
pavement. The three worst carry patch peak-to-peak spreads of 4.81, 4.40 and
2.84 m, so the 3 m patch straddles both the object and the ground beside it and
the median lands on the object.

`GroundSample` reports `spread_m`, `peak_to_peak_m` and `n_hits` for exactly this
reason, and its own docstring says a bad patch should be "visible as a wide
spread rather than as a confidently wrong number". Nothing reads them. The only
consumer is `summarise_site_panoramas.py:63`, which copies `ground_spread_m` into
a table. 19 of the 127 cameras have a patch spanning more than 2 m and 3 have a
patch with a hole in it, and all 22 are accepted without comment.

Sites carrying at least one camera more than 2 m above the datum: Madrid 3,
Brussels 3, Korenmarkt Mapillary 1, Mexico 1, Prague 1, Tokyo 1.

Nothing on the eleven city headline path reads this. That run is
`--materials geometric`, which never opens a panorama. It reaches the material
arm, where a mis-placed camera casts its whole first-hit buffer from the wrong
height and the fishnet then cuts against it, and it reaches the skyline
measurement. Korenmarkt's own worst camera is +2.37 m, on the Mapillary walk that
carries the SAM 3 binding, which is the same reconstruction stage as finding 8b
and at the same site.

## Smaller, verified, low impact

Status 2026-08-09, bullet by bullet:

- `floquet.py:147` still open at
  `semantic_twin/materials/masonry/floquet.py:147-150`. The auto limit takes
  `min(|b1|, |b2|)` and then a square index box, which does not cover the k
  circle for a sheared basis. Reproduced at 15 GHz, 45 degrees, 225 by 75 mm
  cell: rectangular matches the reference at 129 orders, centred drops 14 of
  133. Different operating point from the 118 recorded below, same defect.
  Production still uses the rectangular cell only.
- `kirchhoff.py:274` still open at
  `semantic_twin/materials/masonry/kirchhoff.py:274`, and still numerically
  inert. Flipping the recess sign moves every efficiency by at most 2.8e-17
  against peak efficiencies of 0.046 to 0.807, because the efficiencies are
  conjugation invariant.
- `rcwa.py:172` still open, now at
  `semantic_twin/materials/masonry/rcwa.py:210` with the indexing at `:215`. The
  guard admits `|delta_m| <= n_x // 2` where an even grid tops out at
  `n_x / 2 - 1`, so an 8 by 8 profile with `delta_m = 4` passes the guard and
  dies with an `IndexError` instead of the intended message.
- `run_next_event.py:174` is moot. The call is now
  `semantic_twin/exposure/next_event_study.py:161-176` and still passes no
  `rng`, but `build_source_set` at
  `semantic_twin/illumination/sources.py:648-676` no longer calls `thin()`, so
  there is no sub-cell z bias left to have. The one remaining `thin()` caller,
  `semantic_twin/illumination/source_silhouette_study.py:162`, passes a
  generator.
- `run_next_event.py:117` is fixed. The variant is written into the payload at
  `semantic_twin/exposure/next_event_study.py:272`.

- `floquet.py:147` under-covers non-orthogonal lattices silently. 118 propagating
  orders are dropped on the running bond primitive cell. Production only uses the
  rectangular cell.
- `kirchhoff.py:274` gives the joint recess the wrong phase sign. Three
  independent lines agree on this, but every efficiency in the shipped sweep is
  identical to 1e-18.
- `rcwa.py:172` undersampling guard is off by one on even grids, which is what
  the codebase uses.
- `run_next_event.py:174` calls `build_source_set` without `rng`, so `thin()`
  keeps the highest point per cell. `sources.py:75-79` documents that rule as
  wrong. Sub-cell z bias, about 0.01 dB.
- `run_next_event.py:117` accepts `--variant` and never writes it into the
  payload, so which ray tracing backend produced a file is only knowable from the
  filename an operator chose. The backends do differ, see below.

## Checked and cleared

On the record so nobody reopens them.

Status 2026-08-09: these were not re-derived. Each was checked only for whether
the code it describes moved or changed, which is what would put a clearance back
in doubt.

- The CUDA versus LLVM divergence: moved, substance unchanged. `connections` is
  incremented at `semantic_twin/transport/next_event.py:618`, before the shadow
  ray at `:629`, and `cleared` is at `:634`. Clearance holds.
- The connection start offset: unchanged. `lift_m` is 1.0e-2 at
  `semantic_twin/transport/next_event.py:477` and `:956`.
- The bounce rays: moved to
  `semantic_twin/transport/trace_kernel.py:376`, same epsilon geometry.
  Clearance holds.
- The diffuse albedo asymmetry: moot under `first_material_interaction_v1`,
  which has one diffuse event and so no chained albedo.
- Russian roulette: now inert by construction rather than by coincidence.
  `roulette_start` is `DEFAULT_MAX_BOUNCES + 1` at
  `semantic_twin/transport/tracer.py:85`. Also moot under the current contract.
- The polarisation reduction: unchanged at
  `semantic_twin/transport/tracer.py:223-235`.
- The material binding fallback and the 0 percent coverage: the literal moved to
  `semantic_twin/exposure/execution.py:353`, but the premise is stale. The
  semantic-route cohort now forbids geometric materials at
  `semantic_twin/exposure/roofline_campaign.py:182`, so the headline no longer
  runs through that branch at all.

**The CUDA versus LLVM divergence is benign, and not for the reason it looked
like.** `connections` cannot report a blocked-or-clear verdict: `sources.py:395`
increments it before the shadow ray is cast at line 407. It counts vertices whose
drawn site is in front of the surface and further than 0.5 m. `cleared` is the
visibility count.

The two bench files used different source sets, 9,037 sites against 9,035. Sky
fraction is bit identical at all four standpoints, so the primary casts agree
exactly. The divergence is in the 110 million ray silhouette fan, where a few
float32 near-tangent roof edge rays flip hit or miss, and thinning to 1 m cubes
turns that into two sites.

A different site count reshuffles every random draw. Verified: dropping one site
from a 3,148 site set, same mesh, rays, seeds and backend, moves `connections` by
97 out of 925,019. Random sign, same order as the bench pair.

**The connection start offset is fine.** `chi_bounce` is 1.4541e-4 at a 0.1 mm
lift, 1.4543e-4 at 1 mm, 1.4590e-4 at the shipped 1 cm. That is a plateau across
two decades. A missing epsilon would show as a cliff.

**The bounce rays that write the published numbers are clean.** Of 612,044 post
first bounce segments, exactly 2 land on the same face as the previous bounce.
`tracer.py:649` lands the vertex on the true hit point, so the next ray starts a
clean 1 mm times cosine clear of the surface.

**The diffuse albedo is non-reciprocal and it is worth almost nothing.** Done
properly, on the same drawn site, a symmetric albedo moves the bounced term by
+0.07 to +0.10 dB, under 0.02 dB on the surplus.

**Russian roulette is fully inert at the defaults.** `roulette_start` is 4 and the
loop breaks at depth 3 first. When `--roulette-start 3` is passed, which older
manifests record, it is unbiased.

**The polarisation reduction does what its docstring says.** Applying
`0.5(|Gamma_TE|^2 + |Gamma_TM|^2)` independently along a chain is not the same as
carrying two polarisations, and for a two bounce chain sharing a plane of
incidence the code reads 0.2 to 3.0 dB low. Bounce 2 carries 12.7 percent of the
power and the diffuse lobes randomise the plane, so the real effect is at most
about +0.3 dB on the multipath term.

## Modules that came back correct

Status 2026-08-09: not re-derived. The 2026-08-04 clearances below stand as
written, with one correction of scope. `masonry.py` in that list means the wall
geometry module, not the RCWA or Kirchhoff solvers, which carry findings 5, 6
and the two bullets above.

`directions.py` is the strongest thing in the package. The band law's elevation
marginal matches an independent four million sample Monte Carlo over the real site
population to 5e-4 in every one of 20 bands. All seven models integrate to exactly
1.000000 over 4 pi. The fast nearest-cell search is bit identical to brute force
over 1.8 million queries.

`tracer.py`'s core loop is sound. The lobe split carries the right expectation,
the cosine hemisphere weight is right, and free space chi comes out 1.000
isotropic and 1.001 rooftop.

`closed_form.py`, `geometry.py`, `monostatic.py`, `masonry.py`, `mmwave.py`,
`materials.py` and `material_posterior.py` are correct. All 15 `itu_p2040_4.json`
rows match the P.2040-4 text exactly, including the three that do not exist in -3.
The material mixture averages power and never permittivity. Averaging permittivity
would have overstated facade reflectance by 8.3 dB.

**The material binding fallback is correct, and the 0 percent coverage is a run
configuration fact rather than a bug.** The eleven city headline uses
`--materials geometric`, which never calls `semantic_binding`, and
`run_exposure.py:532` writes the 0.0 as a literal in that branch. Runs that do
invoke the binding reach 3.1 to 33 percent by area.

**No inefficiency worth changing.** `np.add.at` is 0.71 ms against `bincount`'s
0.55 ms on this numpy, so the hot deposit is fine. The walk's per point loops cost
about 1 s per site. Mitsuba only has AD variants compiled in this build, so there
is no cheaper backend available.
