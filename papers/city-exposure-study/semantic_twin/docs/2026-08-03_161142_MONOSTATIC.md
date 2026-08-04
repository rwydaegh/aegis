# The co-located branch, and the evidence it is the only formulation that guarantees

`semantic_twin/propagation/monostatic.py`, its tests in `tests/test_monostatic.py`,
its driver `run_monostatic.py`, its outputs under `outputs/monostatic/`.

MONOSTATIC_SBR.md is named after a quantity it then declines to build. Section 3
derives the monostatic loop, section 3.2 shows it cannot be inverted for the
transfer tensor the exposure integral needs, and section 10.3 lists
`monostatic.py` as one of twelve modules that were designed and never written.
Section 11.6 leaves one question attached to it: does the monostatic return
predict the exposure ratio. This document answers that, and answers a second
question that turns out to matter more.

## 1. Why this is not heritage

The reason to build the co-located branch is not that the project started there.
It is that the closed loop is the only formulation in which this twin's central
claim is exactly true rather than probably true.

The claim the semantic pipeline exists to support is that street level imagery
gives correct materials for the interactions that matter. Take a path that leaves
the observation point `S`, interacts at `A`, interacts at `C`, and returns to `S`.
The first leg is unoccluded, so `A` is visible from `S`. The last leg is
unoccluded, so `C` is visible from `S`. Both surfaces are therefore visible from
the point the pedestrian is standing at, and if a camera stood at that point both
carry measured material. The guarantee is geometric, it is exact, and it needs no
assumption about how much of the square the walk covered.

Under the adjoint formulation the path never comes back. Only the first hit is
visible from `S` by construction. The second and third hits are wherever the ray
went, and whether they carry measured material is an empirical question about
walk coverage. So the adjoint move, which was right for the estimator and is
still right, silently cost half of the material guarantee. DECISIONS.md records
that move as costing nothing. On this point it is wrong.

Section 4 measures the size of that cost. It is not small.

## 2. The quantity

`g = P_r / P_t` for an isotropic transmitter and an isotropic receiver at the
same point, dimensionless, receive aperture `A_e = G_r lam^2 / (4 pi)`. Nothing
is normalised away, so it is directly a link budget number: what a co-located
sounder standing at head height would read against what it transmits.

It has no zero bounce term. A ray that escapes never comes back, so unlike the
susceptibility `chi`, which splits into a direct part and a reflected part, the
monostatic return is entirely reflected. That is the shape of the correlation
question in section 5: if it predicts anything it should predict the reflected
part of the exposure, not the total.

## 3. The estimator, and the trap in it

### 3.1 A returning ray is measure zero

Sample a direction at `S`, follow it, and the probability that it comes back
through the point `S` is exactly zero. MONOSTATIC_SBR.md section 5.1 states this
correctly: the paths exist and are finite in number, they are simply unfindable
by forward sampling. An implementation that waits for a ray to return collects
nothing and reports a clean, plausible, entirely wrong zero. The first test in
`tests/test_monostatic.py` builds precisely that scene, a mirror under the
observation point, and asserts that the sampled branch returns zero while the
enumerated branch returns the image source.

The return is therefore split along the same Rayleigh boundary the tracer already
uses for its own scattering, and each part gets the estimator it admits.

### 3.2 The incoherent part: next event estimation, sharing the adjoint trace

At every surface interaction the path already carries the correct incident power
and the diffuse lobe radiates a finite radiance back toward `S`, so one occlusion
ray per vertex collects it with bounded variance. A ray leaving an isotropic
transmitter, one of `N` drawn uniformly on the sphere, carries `P_t / N` and
arrives at interaction `m` carrying `P_t W_m / N`, where `W_m` is the tracer's
throughput after that interaction's reflectance. The surface radiates toward `S`
with `W_m (1 - kappa) cos(th_s) / pi` per unit incident power, `kappa` being the
Rayleigh coherent share the other branch owns, and the receiver collects
`A_e / r^2`:

```
g = (1/N) sum over rays sum over vertices
    W_m * (1 - kappa_m) * cos(th_s) / pi * A_e / r^2 * V(x_m, S)
```

**This shares the adjoint trace, and it should.** The departure distribution the
adjoint estimator needs is uniform on the sphere, which is exactly what an
isotropic transmitter illuminates with, and the path prefix carries the same
throughput for both. Nothing is resampled, no random number is drawn in the
gather, and the traced `PointResult` is bit identical with a gather attached,
which the test suite asserts rather than assumes. The cost is one occlusion ray
per interaction on top of one intersection ray per interaction the trace already
pays. The measured relative standard error of the monostatic estimate off the
shared trace is given in section 5, and it is small enough that a separate trace
would buy nothing.

### 3.3 The coherent part: enumeration, because sampling cannot

A first order specular return needs the outgoing mirror direction to reverse the
incoming one, which happens only where the surface normal points at `S`. On a
triangulated scene that set is the feet of the perpendiculars from `S` onto the
facet planes: at most one point per facet, finite, and found by enumeration.

The weight is the image source result. A facet that contains the first Fresnel
zone of the round trip behaves as the infinite plane it lies in, giving
`g = |Gamma|^2 (lam / (4 pi L))^2` over `L = 2 d`, which is free space spreading
over the unfolded path and nothing else. A facet smaller than that zone is the
physical optics flat plate, `sigma = 4 pi A^2 / lam^2`, giving
`g = |Gamma|^2 A^2 / (16 pi^2 d^4)`. The two are equal at `A = lam d / 2`, which
is what fixes the crossover, and the implementation is the plane form times
`min(1, A / (lam d / 2))^2`. Both limits are tested against their own oracle, and
the two range laws, `1/d^2` for the plane and `1/d^4` for the plate, are tested
separately because that exponent is what tells the regimes apart.

Only the Rayleigh coherent share of the reflected power is taken here and only
its complement is taken by the gather, so the two branches partition the
reflected power and neither double counts the other.

### 3.4 What is not computed

Purely specular chains of order two and above. The wall to ground dihedral is the
member of that family that matters, and MONOSTATIC_SBR.md section 5.1 is explicit
that corner reflectors are where the monostatic response is largest and the
estimator least stable. The gather does carry every chain whose last interaction
is diffuse, so the omission is narrower than it sounds, but it is real and it
biases the total downward. The correct fix is next event estimation toward the
image of `S` in the ground plane, which is one more occlusion ray per vertex and
is the obvious next piece of work.

## 4. Validation

`python run_monostatic.py --validate`, written to
`outputs/monostatic/monostatic_validation.json`. Section 11.1 of the design
complains that an earlier validation left no artefact, so this one does.

| Check | Target | Measured | Relative error |
|---|---|---|---|
| Lambertian cavity, `R` = 10 m, one order | 1.011810e-07 | 1.011810e-07 | 2.8e-12 |
| Lambertian cavity, `R` = 8 m, three orders | 4.742861e-07 | 4.742861e-07 | 6.6e-12 |
| Image source, `h` = 1.5 m | 2.810585e-07 | 2.810585e-07 | 2.8e-12 |
| Image source, `h` = 3 m | 7.026461e-08 | 7.026461e-08 | 2.8e-12 |
| Image source, `h` = 12 m | 4.391538e-09 | 4.391538e-09 | 2.8e-12 |
| Physical optics plate at 100 m | 4.052847e-13 | 4.052847e-13 | 2.8e-12 |
| Rough half space under the observer, 1.5 m | 7.964292e-08 | 7.997068e-08 | 4.1e-03 |

The residual is not estimator error. It is the absorption of the mirror used as
the target: the package's `PEC_PERMITTIVITY` has a finite `1e12` imaginary part
which absorbs 2.8e-6 of the power per bounce, invisible against the
susceptibility targets it was chosen for and worth 2.5e-5 once several orders are
summed, so these checks use `1e24` instead and the residual is that material's
own 2.8e-12.

The half space is the only row with Monte Carlo error in it, and it is there
because it is the only one of these that exercises the return lobe and the range
law at once. The cavity sees `cos(th_s) = 1` at every vertex and `r = R` for every
ray, so it pins the aperture and the throughput chain and cannot catch an error
in either. A rough half space under the observer makes the estimator get
`mu^3` right and the angular dependence of Fresnel and of the Rayleigh split
right, against

```
g_1 = (A_e / (2 pi h^2)) * int_0^1 R(mu) (1 - kappa(mu)) mu^3 dmu
```

derived in the docstring of `half_space_first_order_return` and reimplemented
independently in the test. The 0.41 % residual is 1.4 standard errors of the
0.30 % the estimator reports for itself, which is the second thing that check
is for.

The cavity is a genuinely strong test because it has no Monte Carlo variance at
all: every wall point of a sphere is seen from the centre along its own normal,
so `cos(th_s) = 1` and `r = R` for every ray at every order, and the closed form
`g_K = rho lam^2 / (4 pi^2 R^2)` per order is hit exactly rather than to within
noise. Getting it required one discovery worth recording: the Rayleigh split
sends grazing incidence into the specular lobe however rough the surface is, so
an exactly Lambertian wall needs a roughness large enough to push that transition
below any angle a cosine sample can reach. At `s = 1 m` the cavity target is
missed by 7e-5 through that mechanism alone, which reads exactly like an
estimator bug and is not one.

The remaining tests are in `tests/test_monostatic.py`: the measure zero
demonstration, the `lam^2` aperture scaling, the two range laws, occlusion of
both branches, batching invariance, bit identity of the traced result with a
gather attached, and the containment rule for the specular point.

## 5. Result: the evidence guarantee, measured

### 5.1 The geometric claim, on traced paths

`test_a_closed_loop_lands_only_on_surfaces_the_observer_can_see` builds a scene
in which a near wall hides a far wall and the ground behind it from the
observation point, marks as observed exactly the triangles with a point visible
from that point, and traces. The assertions are exact, not approximate:

- the last surface of a returning path is observed at **1.0000** at every order
- the whole chain of a returning path is observed at **1.0000** at first and
  second order
- the whole chain at third order is strictly below one, because the guarantee is
  over the two ends of the loop and not over its middle
- the adjoint path that keeps going instead of returning is at 0.9947 at second
  order and 0.9066 at third in the same scene

The size of that gap is a property of the scene. Its sign is a theorem.

The same statement on real photogrammetric geometry: four meshes, 42 walk
standpoints, the mask built by first hit sampling of 2e6 directions from each
standpoint itself, so that "observed" means geometrically visible from the point
the radar stands at and nothing else.
`python run_monostatic.py --sites korenmarkt,brussels_grandplace,milan_duomo,tokyo_hachiko --visibility`.

| share of power on a fully visible chain | min | median | max |
|---|---|---|---|
| closed loop, order 1 | 0.999984 | **1.000000** | 1.000000 |
| closed loop, order 2 | 0.996854 | **0.999972** | 1.000000 |
| closed loop, order 3 | 0.717602 | 0.979514 | 0.998835 |
| open path, order 1 | 0.997769 | 0.999103 | 0.999952 |
| open path, order 2 | 0.843158 | **0.912004** | 0.955258 |
| open path, order 3 | 0.582827 | 0.714182 | 0.859821 |

Per site, medians:

| site | standpoints | closed loop 2 | closed loop 3 | open path 2 | open path 3 |
|---|---|---|---|---|---|
| brussels_grandplace | 10 | 0.999956 | 0.9797 | 0.9183 | 0.7343 |
| korenmarkt | 12 | 0.999991 | 0.9842 | 0.9157 | 0.7362 |
| milan_duomo | 10 | 0.999759 | 0.9807 | 0.9181 | 0.6885 |
| tokyo_hachiko | 10 | 0.999985 | 0.9760 | 0.8779 | 0.6709 |

The theorem holds on photogrammetric geometry to within 1e-4 in the median, and
the residual is the probe sampling of the mask rather than the estimator: the
mask is built from 2e6 rays and scored against a trace of 5e4, so a triangle the
trace reaches through a sliver the probe missed reads as a false negative. The
open path row is where the interesting number is. At the second interaction the
adjoint estimator is already running 9 % of its power over surfaces the
standpoint cannot see, and at the third it is running 29 % there, and the spread
across four cities on three continents is a few percent. Those are the surfaces
about which the twin has no image evidence and can have none, whatever the walk
covers.

### 5.2 The transfer to real image evidence

The theorem is about visibility from the observation point. It becomes a
statement about *measured material* only where a camera stood at that point, so
the experiment stands the radar where the camera stood:
`python run_monostatic.py --sites <site> --stations`. Twenty eight registered
Street View stations across four squares, 100k rays, three reflections, 250 m
crop, with the ledger scored twice on the same geometry. `own_station` is the
strict reading, the triangles that one camera collected transient free rays on.
`fused_walk` is the union over the walk, which is the mask the material binding
in `semantic_binding.bind_from_walk` actually uses.

Share of power whose entire interaction chain lands on observed triangles, over
the 28 stations:

| | closed loop, all orders | open path, order 2 | open path, order 3 |
|---|---|---|---|
| own station mask, median | **1.0000** | 0.9015 | 0.7161 |
| own station mask, mean | 0.9953 | 0.8945 | 0.7216 |
| own station mask, min | 0.9380 | 0.7772 | 0.5769 |
| fused walk mask, median | **1.0000** | 0.9638 | 0.8748 |
| fused walk mask, mean | 0.9999 | 0.9625 | 0.8736 |

Per site, own station mask, medians:

| site | stations | closed loop | open path order 2 | open path order 3 |
|---|---|---|---|---|
| brussels_grandplace | 8 | 1.0000 | 0.8800 | 0.6352 |
| korenmarkt | 9 | 0.9998 | 0.8718 | 0.6852 |
| madrid_plazamayor | 6 | 1.0000 | 0.9321 | 0.7616 |
| mexico_zocalo | 5 | 0.9992 | 0.9386 | 0.8685 |

The strict column is the one that answers the question. A single camera's own
rays cover essentially all of the power a radar at that camera would receive, and
they cover 90 % of the power the adjoint estimator carries into its second
interaction and 72 % of what it carries into its third. So the adjoint
formulation runs roughly a tenth of its second order energy and nearly three
tenths of its third order energy over material no camera at that point ever
measured, and the closed loop runs none of it there.

Two honest details. The closed loop number is not exactly one, and the gap is
informative: the mask is "a camera collected transient free rays on that
triangle", which is narrower than "geometrically visible", because a pedestrian
standing in front of a facade masks it, a triangle seen edge on collects too few
rays to clear the threshold, and the panorama's usable band is not the full
sphere. The mean shortfall of 0.5 % against a theorem that says zero is a
measurement of that difference and not of the estimator. Second, the closed loop
share falls to 0.9696 at third order under the strict mask, exactly as predicted:
a three interaction loop has one interaction in the middle that neither leg
constrains.

Coverage of the mesh itself is not what makes this work. The masks cover 1.1 % of
triangles per station and 2.8 % fused. Almost all of the return comes from the
small part of the square that the camera at that point could see, which is the
whole point.

### 5.3 Against the open path measurement in BOUNCE_BUDGET.md

That report measures the same thing from the other side, on the adjoint estimator
only, with an independent mask: a 1536 row equirectangular cast from each
registered panorama rather than a first hit probe from the standpoint, and per
depth last surface coverage rather than whole chain coverage. The two agree where
they overlap. Its closest row to my experiment is the eight standpoints within
five metres of an admitted station, where it reads 0.996, 0.959 and 0.899 for the
first three interactions against my fused walk chain shares of 1.0000, 0.9638 and
0.8748. Two implementations, two masks, two definitions of the quantity, same
answer to within a couple of percent.

The interesting difference is what happens away from the camera. That report
finds the adjoint coverage decaying with distance from the nearest station and
collapsing past forty metres, to 0.106 at the first interaction pooled over the
published 90 m walk. The closed loop does not decay: its chain share stays at
1.0000 with respect to visibility at every standpoint in section 5.1, because the
guarantee is anchored at the observation point wherever that point is. What it
does instead is refuse to transfer. Stand the radar where no camera stood and the
closed loop is still exactly on visible surfaces and those surfaces still have no
image evidence, which is the 2.5e-8 in section 8. So the two formulations fail
differently and that is the useful statement: the adjoint estimator is below one
even at the camera and degrades smoothly with distance, and the closed loop is
exactly one at the camera and carries no evidence at all away from it. Neither
gives the published 90 m walk a material guarantee. Only the closed loop gives
one to an instrument that stands where it measures.

## 6. Result: does the monostatic return predict the exposure ratio

Section 11.6 of the design asks this and says it is a result either way. It is
the second answer.

### 6.1 What the co-located radar is actually looking at

Before the correlation, the thing that explains it. Over 440 standpoints, forty
in each of the eleven cities, 100k rays, three reflections, 250 m crop, the
co-located return is **98.6 %** first order at the median, its power weighted two
way range is **4.05 m**, and its median sits at **-70.81 dB** against the closed
form of section 4 for a rough half space under the observer alone at -70.99 dB.
Second order carries 0.37 % and third 0.03 %.

An isotropic radar standing in a city square is looking at the pavement under its
own feet. The aperture weight `A_e / r^2` puts the nearest surface first and the
nearest surface is the ground at head height, at a four metre round trip, and the
buildings that set the exposure ratio are twenty times further away and enter
through `1/r^2` again. Everything in section 6.2 follows from that.

### 6.2 The correlation

`python run_monostatic.py --analyse --tag mono250`, on the same 440 rows, against
the susceptibility of the same standpoint from the same trace. Everything is in
dB, Pearson on the dB values and Spearman on the ranks, and the partial column
holds the sky fraction of the standpoint fixed.

| pooled, n = 440 | Pearson dB | Spearman | partial given sky fraction |
|---|---|---|---|
| total return vs `chi_isotropic` | -0.445 | -0.526 | -0.010 |
| total return vs `chi_isotropic` reflected part | -0.413 | -0.557 | -0.050 |
| total return vs `chi_street_small_cell` | -0.339 | -0.319 | -0.176 |
| second order return vs `chi_isotropic` | -0.598 | -0.629 | -0.304 |
| second order return vs `chi_isotropic` reflected part | -0.645 | -0.724 | -0.345 |

Within a site, over the forty standpoints, the total return against
`chi_isotropic` has a median Pearson of -0.56 and a range from -0.07 at Times
Square to -0.84 at Plaza Mayor. The second order return is both stronger and far
more stable: median -0.69, range -0.49 to -0.79, negative at all eleven sites.
Between the eleven site medians the total return gives Pearson -0.49 and Spearman
-0.68 against `chi_isotropic`, and -0.38 and -0.35 against
`chi_street_small_cell`.

> **Old illumination law, see `LAW_CHANGE.md`.** The two rows against
> `chi_street_small_cell` were computed under the height and range bands. Stale, and they
> have to be recomputed, while every `chi_isotropic` correlation here survives because the
> change does not touch isotropic illumination.

Three things have to be said about that.

**The sign is negative and it is not a bug.** A standpoint with more sky over it
has a higher susceptibility, because the isotropic illumination reaches it, and it
has a *lower* co-located return, because there is less geometry near it to send
power back. Sky fraction alone correlates with `chi_isotropic` in dB at +0.961
and with the return at -0.42. So the monostatic return is behaving as an inverse
proxy for openness, which is a real physical relation and not the relation the
question asked about.

**The pooled correlation is mostly that one variable.** Holding the sky fraction
fixed collapses the total return's partial correlation to -0.010. Whatever the
co-located return knows about the exposure ratio across the whole set, a fisheye
photograph of the sky already knew, and knew better. That answers section 11.6 of
the design in the negative for the total return.

**The second order return survives the control, weakly.** Its partial correlation
against the reflected part of the susceptibility is -0.345, so about a tenth of
the variance left after sky fraction is removed. That is the physically sensible
subset: the term that has bounced twice is the one that has sampled the facades,
and the facades are what the reflected susceptibility is made of. But it is
0.37 % of the received power at the median, its relative standard error at 100k
rays is 0.6 % on the total and much worse on that component alone, and reading it
off a real instrument means range gating a return 24 dB below the pavement clutter
at a two way range of a few tens of metres. The idea is not retired on physics. It
is retired on dynamic range for an isotropic pair, and it moves to the directive
experiment in section 8.

The blunt version of the whole section is a spread argument. Across the eleven
site medians the susceptibility moves 3.91 dB and the co-located return moves
0.71 dB. The return is nearly the same everywhere because the pavement is nearly
the same everywhere. An instrument whose reading barely changes between Times
Square and Korenmarkt cannot rank them.

![monostatic against susceptibility](outputs/monostatic/mono250_monostatic.png)

## 7. Reported alongside

`run_monostatic.py` writes the co-located columns next to the exposure columns in
one row per standpoint, at the same standpoints, from the same walk, with the
same per location seed, so the two are never joined across files. The columns are

```
mono_gain, mono_gain_db, mono_gain_diffuse, mono_gain_glint, mono_glint_share,
mono_first_order_share, mono_gain_order_1..K, mono_mean_two_way_range_m,
mono_relative_standard_error, mono_glint_facets, mono_blocked_fraction
```

plus, where an evidence mask is carried, `mono_evidence_chain_share` and the per
order closed loop and open path shares. The two way range profile goes to a
`_profiles.npz` beside the rows, which keeps the storage rule: nothing that
scales with the ray count reaches disk.

At the standpoint the published eleven city run calls index 0 of Korenmarkt, this
driver returns `chi_isotropic` = 0.1170180 against the published 0.1170230, a
difference of 0.004 %, the residual being the bounce budget moving from four to
three and half the ray count. The trace is the same trace.

Wiring the gather into `run_exposure.py` itself is a `gather=` argument and four
lines of scalars, and it is deliberately not done here: that file is under
concurrent edit tonight and the co-located columns are not free. The cost is one
occlusion ray per surface interaction, which is real if every published run pays
it and negligible if it is opt in.

## 8. Honest limits

**Purely specular chains above first order are missing.** Section 3.4. The wall
to ground dihedral is the term that matters and it is not computed, so the total
is biased low by an amount this work does not bound. The fix is next event
estimation toward the image of the observation point in the ground plane, which
is one more occlusion ray per vertex and is well defined.

**The glint branch inherits the mesh's facet normals.** A photogrammetric mesh
has noisy ones, and a specular point exists or does not according to a normal
that may be a degree off. The measured glint share over the 440 standpoints is a median of 0.55 % and a
ninetieth percentile of 19 %, and every correlation in section 6 is reported for
the total and for the incoherent part alone so that a reader can see whether the
conclusion depends on the noisy branch. It does not: the diffuse only estimator
gives -0.422 pooled against `chi_isotropic` where the total gives -0.445, and
-0.157 against -0.167 after the sky fraction control. There is also a geometric
hazard the unit tests had to be built around: on a rectangle triangulated across
its diagonal, the foot of the perpendicular can land exactly on the shared edge
and be counted twice.

**The guarantee is about visibility, not about cameras.** Section 5.2 measures
what the guarantee is worth when the camera is where the radar is. Nothing here
says the walk standpoints of the published runs inherit it: they do not, because
no camera stood at them. At an arbitrary walk standpoint 250 m from the nearest
station, the share of monostatic return power on observed triangles falls to
2.5e-8. The formulation guarantees the geometry; only a station standing there
guarantees the evidence.

**The guarantee is over the ends of the loop, not its middle.** A three
interaction closed loop constrains two of its three surfaces. Measured, the
closed loop chain share falls from 1.0000 at second order to 0.97 at third under
the strict mask, which is the size of that hole at this bounce budget.

**An isotropic co-located pair mostly sees its own pavement.** Section 6.1. That
is a property of the antennas, not of the formulation: `A_e / r^2` weights the
nearest surface and the nearest surface is the ground at 1.5 m. A directive
co-located pair aimed at a facade would return that facade instead, with the same
guarantee, and the estimator already supports it through
`MonostaticConfig.receive_gain` for the scalar and would need a transmit pattern
on the departure sampling to be complete. That is the obvious next experiment and
it is not done here.

**Polarisation.** The gather inherits the tracer's unpolarised power average, so
the co-located return is a band averaged second moment like everything else in
this study. A real monostatic sounder measures a polarimetric scattering matrix
and the depolarisation ratio is exactly the sort of thing a co-located instrument
is good at. Nothing here can produce it.
