# Bystanders

Every exposure number this study has published so far describes a pedestrian
standing alone in an empty square. Nobody stands alone in Korenmarkt. This note
puts the other people into the scene, measures what they take away, and checks
the cheap way of estimating it against the expensive one.

Code is `semantic_twin/propagation/bystanders.py`. Tests are
`tests/test_bystanders.py`. The run is
`python -m semantic_twin.propagation.bystanders --locations 12 --realisations 2
--rays 120000`, the noise floor adds `--noise-floor` and the control adds
`--body-absorber --locations 8 --realisations 1 --stature-modes adult --tag
korenmarkt_absorber` at the top two densities. Output is
`outputs/bystander_study/`. Nothing in `run_exposure.py` was touched: the
bystander runner reads the illumination models from
`semantic_twin/propagation/directions.py`, which is where they are defined, and
resolves the site mesh and the ground datum itself.

## The prediction, before the measurement

A bystander is not a small perturbation at 15 GHz. The wavelength is 20 mm, the
azimuth averaged silhouette width of the reconstructed bodies is 0.586 m, so a
person is 29 wavelengths across. One skin depth in skin at 15 GHz is 2.1 mm, so
a body is optically thick as well as geometrically large. There is no
diffraction path around a bystander worth writing down. They are geometry.

What makes them a different kind of blocker from a building is that they stand
at the observation point's own height. The walk in `walk.py` puts the
observation point 1.5 m above the ground, and a standing adult tops out around
1.73 m, so the height a bystander adds above the observation point is about
0.23 m. A ray leaving at elevation `e` clears a crowd of height `h_b` after a
horizontal distance `(h_b - h_o)/tan(e)`. That is 13 m at 1 degree, 2.6 m at 5
degrees and 0.4 m at 30 degrees. **A crowd is opaque near the horizon and
transparent above about 10 degrees, and there is no density that changes this.**

That interacts with the corrected illumination laws of `MONOSTATIC_SBR.md`
section 2.7 in a way that should be visible in the results table:

| model | support (deg) | share of the illumination measure below 5 deg |
| --- | --- | --- |
| isotropic | -90 to 90 | 0.544 |
| rooftop | 3.09 to 60.11 | 0.094 |
| street small cell | 0.96 to 33.02 | 0.879 |

So the prediction was: crowd blockage should cost the street small cell column
many decibels and the rooftop column very little, with isotropic in between.

## What was measured

12 standpoints on the Korenmarkt walk, 2 crowd realisations each, 6 densities, 2
stature modes, 120 000 rays per trace and the study's own trace budget of three
surface interactions with Russian roulette off, 300 traced rows in
`outputs/bystander_study/korenmarkt_15ghz_rows.jsonl`. Each crowd trace is paired
with a baseline trace of the same standpoint under the same ray seed, so the
numbers below are medians of a paired per-standpoint dB shift and not a
difference of two independently sampled populations.

Baseline median `chi_S` on the empty square: isotropic 0.2846, rooftop 0.1558,
street small cell 0.01333.

### Traced crowd against Beer-Lambert, adult statures

Median paired shift in `chi_S` (dB). BL-w is the Beer-Lambert arm with the
density read on walkable area, BL-n with the density read on nominal disc area.

| density (m-2) | bodies | iso traced | iso BL-w | iso BL-n | roof traced | roof BL-w | roof BL-n | street traced | street BL-w | street BL-n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.050 | 66 | +0.01 | -0.04 | -0.08 | -0.06 | -0.08 | -0.17 | -0.11 | -0.12 | -0.24 |
| 0.150 | 200 | +0.00 | -0.10 | -0.18 | -0.17 | -0.22 | -0.40 | -0.32 | -0.33 | -0.58 |
| 0.308 (A/B) | 410 | -0.02 | -0.18 | -0.29 | -0.33 | -0.37 | -0.65 | -0.50 | -0.59 | -0.96 |
| 0.718 (C/D) | 956 | -0.03 | -0.31 | -0.46 | -0.48 | -0.66 | -1.10 | -0.79 | -1.01 | -1.60 |
| 1.076 (D/E) | 1434 | -0.07 | -0.39 | -0.55 | -0.79 | -0.85 | -1.38 | -0.99 | -1.29 | -2.00 |
| 2.153 (E/F) | 2867 | -0.07 | -0.53 | -0.70 | -1.07 | -1.32 | -2.08 | -1.40 | -1.93 | -2.84 |

### Traced crowd against Beer-Lambert, statures as reconstructed

| density (m-2) | bodies | iso traced | iso BL-w | iso BL-n | roof traced | roof BL-w | roof BL-n | street traced | street BL-w | street BL-n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.050 | 66 | +0.00 | -0.03 | -0.07 | -0.04 | -0.06 | -0.12 | -0.08 | -0.08 | -0.16 |
| 0.150 | 200 | +0.01 | -0.09 | -0.16 | -0.12 | -0.15 | -0.29 | -0.21 | -0.21 | -0.37 |
| 0.308 (A/B) | 410 | -0.01 | -0.15 | -0.25 | -0.23 | -0.26 | -0.45 | -0.30 | -0.34 | -0.58 |
| 0.718 (C/D) | 956 | -0.00 | -0.26 | -0.39 | -0.32 | -0.44 | -0.68 | -0.45 | -0.58 | -0.87 |
| 1.076 (D/E) | 1434 | -0.04 | -0.33 | -0.47 | -0.58 | -0.54 | -0.79 | -0.70 | -0.72 | -1.06 |
| 2.153 (E/F) | 2867 | -0.03 | -0.45 | -0.58 | -0.62 | -0.73 | -1.01 | -0.74 | -1.01 | -1.40 |

The median walkable fraction inside the 30 m disc is 0.47, so a nominal density
of `lambda` puts about `0.47 lambda` people per square metre of disc, and BL-n
sits below BL-w by construction.

### Is the shift real

Re-tracing the same 12 standpoints on the **empty** square with three different
ray seeds gives the estimator's own spread,
`outputs/bystander_study/korenmarkt_15ghz_noise_floor.json`:

| model | per-row median abs shift (dB) | per-row p95 (dB) | floor on an entry median of 24 rows (dB) |
| --- | --- | --- | --- |
| isotropic | 0.009 | 0.024 | 0.003 |
| rooftop | 0.035 | 0.119 | 0.013 |
| street small cell | 0.112 | 0.645 | 0.043 |

This is a conservative bound, because the study uses common random numbers and
the noise floor does not. Every entry in the two tables clears it, the tightest
being the as reconstructed isotropic entry at 0.05 m-2, +0.004 dB against a
0.003 dB floor, and the top of the isotropic column clearing by 23 times. The
street small cell column carries by far the most sampling noise per row, which is
expected: it draws `chi_S` from a 1 degree wide band of arrival directions, so it
sees the fewest rays.

### The trace budget, and the rerun that closed it

The first crowd arm was traced at `max_bounces: 6` with roulette from bounce 3,
which is the budget this study used before `BOUNCE_BUDGET.md` settled on three
surface interactions with roulette off. The tables above are the retrace on the
settled budget. It is the same mesh, the same measured datum of 50.837 m and the
same 12 standpoints, which were rebuilt and checked index by index against the
first run before anything was compared, because two of the eleven city reruns in
this project turned out to be confounded by a datum change underneath them.

Nothing of substance moved. At 2.153 m-2 with adult statures the paired median
went from -0.049 to -0.070 dB isotropic, -1.044 to -1.069 rooftop and -1.391 to
-1.396 street small cell, and the arriving shares below 5 degrees went from
0.1850 to 0.1847 rooftop and 0.2123 to 0.2116 street, so the 1.15 ratio that
refutes the geometric prediction is unchanged. The largest single move anywhere
in the two ladder tables is 0.055 dB, in the as reconstructed street small cell
column, which is the noisiest column in the study and the one whose per-row floor
is 0.112 dB.

The noise floor and the absorber control needed no retrace, because both had
already been run at three interactions: the noise floor JSON reproduces byte for
byte, and rerunning `--body-absorber` reproduces its summary byte for byte. So
the absorber contrast is now measured on one budget throughout, which it was not
before.

### The prediction was wrong, and interestingly so

The prediction was that blockage would track the share of the illumination
measure the model sends below 5 degrees: street small cell hit hard (0.879 sent
below 5 deg), rooftop barely (0.094), isotropic in between (0.544). What was
measured, at the top of the ladder with adult statures, is street -1.40 dB,
rooftop -1.07 dB, isotropic -0.07 dB. The street to rooftop ratio is 1.3 to 1.9
across the whole ladder, not the 9.3 the sent measure predicts, and isotropic,
which sends more than half its measure into the band a crowd is opaque to, is
the one column a crowd barely touches.

Two separate things are going on.

**The buildings get there first.** The measure a model *sends* below 5 degrees is
not the share of `chi_S` that *arrives* from below 5 degrees. Korenmarkt's
facades have already redistributed the power by the time it reaches the
pedestrian. The traced arriving shares, medians over the 12 standpoints, are
0.162 isotropic, 0.185 rooftop, 0.212 street small cell, against sent shares of
0.544, 0.094 and 0.879. The square flattens a 9-to-1 difference into a 1.15-to-1
one. That is the whole explanation for street and rooftop responding within a
factor of 1.5 of each other, and it is a result about the square rather than
about the crowd: **a dense European square is already its own near-horizon
blocker, and adding people to it is a second-order edit to an angular
distribution the buildings have set.** The right panel of
`korenmarkt_15ghz_mechanism.png` plots the sent measure against elevation and
puts both the sent and the arriving near-horizon share in its legend.

That explanation carries the two directional models and then fails on the third.
Deleting the entire arriving below-5-degree band, which is the most a perfectly
absorbing crowd could ever do, would cost -0.77 dB isotropic, -0.89 dB rooftop
and -1.03 dB street small cell. The traced crowd at 2.153 m-2 delivers -1.07 dB
rooftop and -1.40 dB street, at or past that bound because it also eats into the
5 to 15 degree band, and -0.07 dB isotropic, which is nowhere near it. So a
second mechanism is needed, and only for isotropic.

**Isotropic does not care where the power goes, only whether it is gone.**
`chi_S` under isotropic illumination weights every arrival direction equally, so
any redistribution of arrival direction is free and only absorption costs
anything. A bystander at 15 GHz reflects about half of what it intercepts and
scatters it diffusely, and under isotropic weighting that scattered half is
recovered somewhere else on the sphere. Under a directional model it lands
outside the model's support and is lost. That is why the isotropic column sits at
-0.07 dB at 2.15 people per square metre while the Beer-Lambert arm, which by
construction cannot recover a reflected photon, predicts -0.53 to -0.70 dB there.
The sign at the bottom of the ladder is the same story read forwards: isotropic
`chi_S` comes out **positive** at 0.05 and 0.15 m-2, +0.006 and +0.005 dB with
adult statures, a gain rather than a loss at about twice the 0.003 dB floor,
which is what a sparse crowd standing close to the pedestrian does if it scatters
slightly more power inwards than it removes.

### The control run says the same thing directly

That mechanism was first an inference, from the traced against Beer-Lambert gap
and from the sign at low density. It was then measured. `--body-absorber`
re-traces the top two rungs of the ladder with the bodies made index matched
absorbers, so the geometry, the multi-bounce blockage and the crowd truncation
are all unchanged and only the reflected half is gone. 8 standpoints, adult
statures, `outputs/bystander_study/korenmarkt_absorber_15ghz_*`.

The comparison that matters is within a run, traced against that run's own
Beer-Lambert arm on the same standpoints, because the control run draws a
different standpoint subset and a different crowd:

| model | skin traced / BL-w | absorbing traced / BL-w |
| --- | --- | --- |
| isotropic | 0.13 | 1.27 |
| rooftop | 0.81 | 0.94 |
| street small cell | 0.73 | 0.81 |

(at 2.153 m-2, adult statures.)

An absorbing crowd puts isotropic on top of Beer-Lambert and slightly past it,
which is the prediction, and the overshoot past 1.0 is the arm's other error
showing through: Beer-Lambert extinguishes the final leg only, so once
re-illumination is removed it under-predicts rather than over-predicts. The two
directional columns move by about a tenth of a ratio point, isotropic by ten
times. In absolute terms, at 2.153 m-2 the isotropic shift goes from -0.07 dB
with skin bodies to -0.71 dB with absorbing ones, while rooftop moves only from
-1.07 to -1.33 dB and street small cell from -1.40 to -1.61 dB.

So the isotropic column is insensitive to a crowd **because the crowd reflects**,
and this is now measured rather than argued.

### So the cheap arm is usable for directional models and useless for isotropic

The two errors named in the method section do not cancel. The perfect-absorber
error wins everywhere, at every density and in every model, so the Beer-Lambert
arm always over-predicts blockage:

| model | BL-n over traced | BL-w over traced |
| --- | --- | --- |
| isotropic | 10x | 7.6x |
| rooftop | 1.9x | 1.2x |
| street small cell | 2.0x | 1.4x |

(ratio of dB shifts at 2.153 m-2, adult statures.)

For the two directional models the walkable reading of the cheap arm is within
40 % of the traced answer in dB and has the right shape against density,
which is enough to use it as a screening estimate as long as it is understood as
an upper bound on the loss. The nominal reading is a factor of two out and should
not be used. For isotropic illumination the cheap arm is wrong by an order of
magnitude and the sign of its error is not recoverable by tuning a density,
because the physics it is missing is re-illumination and not extinction. The
absorber control above is the proof of that last clause: give the cheap arm the
crowd it actually assumes and it is accurate to 27 % on isotropic.

### Statures matter about as much as the crowd does

Rerunning the same crowd with the reconstructions at their own statures (median
1.55 m, only 0.05 m above the observation point) roughly halves the traced
blockage at the top of the ladder: street -0.74 dB against -1.40, rooftop -0.62
against -1.07. That is a bigger lever than a full level-of-service step on the
density ladder. Any bystander number quoted from this study has to quote the
assumed stature with it.

### The size of the effect, stated plainly

Over the whole defensible density range for a European city square, from an
empty square at 0.05 people per square metre to the Fruin E/F boundary at 2.15,
with adult statures, a crowd removes:

- **0.0 to 0.1 dB** under isotropic illumination,
- **0.1 to 1.1 dB** under the rooftop model,
- **0.1 to 1.4 dB** under the street small cell model.

At the densities a square actually spends its time in, level of service A and B,
0.05 to 0.43 people per square metre, the whole effect is 0.5 dB or less in every
column, the largest sampled value being -0.50 dB street small cell at the A/B
boundary. Bystanders are a real, measurable, correctly signed effect on
exposure at 15 GHz, and they are smaller than the spread between standpoints on
the same square. The 5th to 95th percentile of the paired street small cell shift
at the top density spans -3.90 to -0.84 dB, so the median understates what
happens to individual pedestrians who end up boxed in.

## Method

### Where the bodies come from

`outputs/korenmarkt_dynamic_bodies/` holds 18 SMPL-X reconstructions written by
`infer_sam3_body.py` and placed into scene ENU by `build_dynamic_bodies.py`. Each
npz carries `vertices_enu_m`, already floored onto the support mesh, so the pose
and the body shape are the reconstruction's own. Only the reconstructed
positions are discarded here, because 18 people in fixed places is not a density
sweep.

They are used as a shape library: recentred so the footprint centroid sits at
the origin and the lowest vertex at `z = 0`, then placed with a translation and
a yaw.

### Decimation

18 439 vertices and 36 874 triangles per body times a few thousand bodies is not
a scene anyone traces. Blockage is a silhouette quantity, though, and the
silhouette is what survives decimation. Going to 600 triangles per body moves
the azimuth averaged projected area of the worst of the 18 by 0.95 %, which is
inside the spread of the reconstructions themselves. The projected area is
computed as half the sum of `|n.d| dA` over the closed surface, which needs no
visibility test, and is checked in the tests against Cauchy's formula for a box.

### Where the bodies stand

Bystander centres are drawn uniformly on walkable ground inside a 30 m disc
around the observation point. Walkable is decided the way `walk.py` decides it,
by dropping a ray from above and keeping the sample only where it lands on a
near horizontal face within 2.5 m of the square's ground datum, so nobody is
placed inside a building or on a roof. A 0.45 m hard core stops two people
interpenetrating and a 0.60 m exclusion radius keeps anyone from standing inside
the observation point.

The density is people per square metre of **walkable** ground. Korenmarkt's
walkable fraction inside a 30 m disc varies a lot between standpoints, from
about 0.12 at the mouth of a side street to about 0.9 in the middle of the
square, so this distinction is not cosmetic and both readings are carried
through to the cheap arm.

### Arm 1: bodies as traced geometry

`CompositeGeometry` holds the site mesh and a crowd mesh as two ray casting
backends, returns the nearer hit, and offsets the crowd's face indices by the
site's face count so that a single `face_class` array indexes both. The tracer
itself is unmodified.

The body material is one more surface class. Its permittivity is IT'IS skin at
the carrier, read through `aegis.tissue.TissueModel.from_database`, so the body
in the scene and the body in the dosimetry come from one source: 26.4 - 16.6j at
15 GHz, which is a 0.50 power reflectance at normal incidence and 0.54 at 85
degrees. Its RMS height is a 2 mm prior standing for clothing weave and drape,
which puts the Rayleigh coherent fraction at 0.21 face on and 0.83 at 70
degrees. So a bystander in this scene absorbs about half of what hits it and
scatters the rest, mostly diffusely.

That reflectance is why a crowd is not a pure attenuator, and it is the single
most important thing to keep in mind when reading the results below.

### The control: a crowd that only absorbs

`--body-absorber` swaps the skin permittivity for `1 - 1e-6j` and the RMS height
for zero, which makes the Fresnel reflectance of the body class smaller than
`1e-6` at every incidence from face on to 85 degrees, so the tracer's throughput
multiply kills a ray the moment it lands on a person. That is the traced version
of exactly the assumption the Beer-Lambert arm makes, with the geometry, the
multi-bounce blockage and the crowd truncation all still in place. Running it
against the same standpoints isolates re-illumination from extinction: whatever
gap remains between the absorbing crowd and Beer-Lambert is the arm's other
error, the final-leg-only one.

### Arm 2: Beer-Lambert post-multiply

Take bystander centres to be a Poisson field of intensity `lambda` on the
ground. A ray leaving the observation point at elevation `e` is at height
`h_o + r tan(e)` after horizontal distance `r`, and a body of height `h_b`
standing there intercepts it whenever `0 <= h_o + r tan(e) <= h_b`. That is an
interval in `r`:

- climbing, `tan(e) > 0`: `[0, (h_b - h_o)/tan(e)]`, and empty when the body is
  shorter than the observation point,
- level: everything, capped by the crowd radius,
- falling, `tan(e) < 0`: `[(h_o - h_b)/|tan(e)|, h_o/|tan(e)|]`, the far end
  being where the ray reaches the ground.

Clip that to `[r_exclusion, R]` to get `L(e)`. The expected number of
interceptions is `lambda` times the mean of `w_i L(e; h_i)` over the body
population, `w_i` being the Cauchy mean width of body `i`, and the survival
probability of the final leg is its exponential. Thinning a Poisson field by
body type is why the population mean goes inside the exponent rather than
outside it, and the tests assert the difference.

`chi` after blockage is then `sum_cells rho[cell] T(u_cell) dOmega` on the
already traced `rho`. No re-trace, no geometry, one exponential.

Two things this gets wrong, in opposite directions:

- it extinguishes the **final leg only**, so blockage of the earlier legs of a
  multi-bounce path is missing and `chi` comes out too high,
- it treats a body as a **perfect absorber**, so the half of the intercepted
  power that skin reflects is thrown away and `chi` comes out too low.

Which of those wins is the thing the comparison measures.

One quadrature detail that is not optional. `T` falls from 1 to nearly 0 across
the first degree above the horizon, which is narrower than one cell of a 512
cell Fibonacci grid, so reading `T` at the cell centre is a quadrature error of
the same order as the effect. `crowd_transmittance(..., cells=512)` integrates
`T` over the `2/512` wide band in `sin(elevation)` that a cell occupies.

### Density range

From J. J. Fruin, "Designing for pedestrians: a level-of-service concept",
*Highway Research Record* 355 (1971), pp. 1-15. Fruin states walkway level of
service as a pedestrian area module `M` in square feet per pedestrian, and the
density is `1/M`:

| level of service | area module (sq ft/ped) | area module (m2/ped) | density (ped/m2) |
| --- | --- | --- | --- |
| A | above 35 | above 3.25 | below 0.307 |
| B | 25 to 35 | 2.32 to 3.25 | 0.307 to 0.431 |
| C | 15 to 25 | 1.39 to 2.32 | 0.431 to 0.717 |
| D | 10 to 15 | 0.929 to 1.39 | 0.717 to 1.076 |
| E | 5 to 10 | 0.465 to 0.929 | 1.076 to 2.153 |
| F | below 5 | below 0.465 | above 2.153 |

The sweep is `0.05, 0.15, 0.307, 0.717, 1.076, 2.153` people per square metre.
The top four rungs are the class boundaries themselves, so the sweep is read
against a published scale and not against round numbers. The bottom two sit
inside level of service A, where Fruin's description is that a pedestrian can
choose their own speed and avoid conflicts: 0.05 for an empty square, 0.15 for
an ordinary weekday one. The top rung, the E/F boundary, is where Fruin reports
a loss of control and a situation "more representative of a queuing than a
traffic flow situation", so it stands for a market stall queue or an event
crowd, not for a square someone is walking across. Fruin's own inter-person
spacing measurement, a 2 ft (0.61 m) lane "adopted intermittently and only under
the densest flow conditions", is also the sanity check on the 0.586 m mean
silhouette width measured off the reconstructions.

## Caveats

### The reconstructions are short

The 18 bodies have statures from 1.39 to 1.71 m with a median of 1.55 m, which
is short for adults. The observation point sits at 1.5 m, so as reconstructed
the crowd is only 0.05 m taller than the pedestrian it is blocking for, against
0.23 m for a real adult population. Blocking depth is linear in that gap, so it
is a factor of four, and it is the single largest lever in the study.

Both are therefore run: `as_reconstructed`, the bodies exactly as the pipeline
produced them, and `adult`, the same bodies scaled uniformly to statures drawn
from `N(1.73, 0.09)` truncated to `[1.45, 2.05]`. Scaling is uniform, so width
tracks height and the two stay paired.

The adult stature is a declared modelling parameter and not a measurement of
anyone on Korenmarkt. Nothing needs it to be exact: the blocking depth is linear
in `h_body - h_observer`, so a reader who prefers a different population can
rescale the cheap arm by hand.

### The crowd stops at 30 m

Bodies are placed out to 30 m and no further. Truncation is safe for a single
leg near the horizon at high density, where the survival to 30 m is already
negligible, and it is not safe for a multi-bounce path that leaves the disc,
bounces off the ground outside it and comes back through crowd that is not
there. The bias is towards too little blockage in the traced arm.

### One site, one carrier, static people

Korenmarkt at 15 GHz, on the 250 m crop. Bystanders stand still and stand
upright, which is the pose the reconstructions were caught in. Nobody is sitting
at a cafe table, nobody is holding a phone against their head, and no bystander
is between the observation point and a specific site because there is no
specific site: the illumination models are angular measures over a population of
sites, not a network layout.

### The absorber control is a smaller run

The control uses 8 standpoints and 1 realisation at the top two densities, not
12 and 2 across the whole ladder, because it exists to answer one question. Its
standpoint subset is drawn by the same stratifier at a different count, so it is
not the same 8 of the 12 and its median walkable fraction is 0.53 against 0.47.
Cross-run absolute dB are therefore indicative, on the standpoint set if no
longer on the trace budget, which is now three interactions in both runs. The
ratio table above is within-run and is not affected by either.

### `aegis.geometry.inter_body` does not apply

`src/aegis/geometry/inter_body.py` was checked and is a different problem. It
casts one specular ray per lit triangle of a **single** `BodyMesh` and deposits
the recaptured power back on that same mesh, using that mesh's own BVH. It
models a body re-illuminating itself across the gap between the legs or under
the chin. It has no concept of a second body, it works on the dosimetry side
rather than on the environment side, and it would not scale to a few thousand
people. It is not reused here, and nothing here duplicates it.
