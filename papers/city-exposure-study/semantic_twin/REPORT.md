# Overnight run, 1 to 2 August 2026

What was built, what was measured, and what turned out to be wrong. Numbers in
this file are measured unless explicitly labelled otherwise. Where a claim was
checked twice by different means, both are given, including the cases where the
check was the thing that was broken.

Figures referenced here are collected in `FIGURES/`. The two assembled scenes
are `outputs/showcase_korenmarkt/korenmarkt.blend` and
`outputs/showcase_milan_duomo/milan_duomo.blend`.

## The short version

- **Eleven squares are now built**, nine acquired tonight, all in double
  precision at a common radius, for 3,216 tile requests and about three minutes
  of wall clock. Ten of them carry an exposure distribution, Milan being held out
  of the comparison because its crop predates the set at 170 m. Sky fraction across them runs from 18 percent at Times Square to
  46 percent at Krakow, which is the geometric spread this study exists to turn
  into an exposure distribution.
- **The first exposure distributions exist.** Where a pedestrian stands in one
  square is worth 3.5 dB under isotropic illumination and 12.5 dB under rooftop
  macro sites. The assumed source geometry moves the answer further than position
  does.
- **Tripling the image evidence bound into the scene moved the median by 0.30 dB
  and left the spread unchanged.** If that survives the outstanding zero evidence
  baseline it reframes the project's claim: geometry sets the distribution, and
  the semantic layer earns its place through occlusion handling and validation
  rather than by moving the number.
- **One panorama sees 4.4 percent of a scene by area. Twelve see 24.1 percent,
  and it saturates there**, so the per site budget is 12 to 16. Extent matters
  more than count: widening the radius from 60 to 80 m beat tripling the panorama
  count. Beyond that nothing helps, because 55 percent of the surface is roofs,
  courtyards and rear elevations that no street level capture reaches.
- **The remesh rejection was wrong in three of its four reasons**, and the
  argument in its favour was wrong too: a clean mesh does not trace faster. One
  reason survives and it is enough.
- **A published endpoint silently returns a sixth of its data**, and the cost of
  believing it is a 13 point overstatement of cross capture agreement.
- **The crop bias showed up again in registration**, from code sharing nothing
  with the propagation path: six poses at the Zocalo all stand in the northern
  half looking south across 200 m of open ground, and re-fitting them against the
  wider shell improves their residuals by about 30 percent.
- **The acquired crop radius is too small, and worst for the case that matters
  most.** Isotropic susceptibility converges by 100 m, rooftop needs 250 m and
  street level small cells need 250 to 300. At the 130 m everything was acquired
  at, street cells are **9.93 dB** in error and rooftop 3.24. Widening the annulus
  is about fifteen minutes of network time.
- Two workstreams reached honest negative or unvalidatable results and say so:
  brickwork is validated at 4 GHz and unvalidated at FR2 because the only
  measurement available cannot adjudicate, and the vegetation standard has no
  tabulated data anywhere in our band.

## One thing needs you

**The Street View tiles API has a daily cap of 15,000 requests and we hit it.**
Acquisition stopped on HTTP 429 partway through the third site and did not
recover after cooldown at reduced concurrency, so it is a daily quota rather than
a burst limit.

One zoom-5 panorama is exactly 338 tiles, a 26 by 13 grid, so the cap is **44
panoramas per day**, which bought three sites at fourteen each. The remaining five
sites need two more days at zoom 5, or one day if the quota is raised in the
console, which is an action only you can take. Zoom 4 would give 176 panoramas a
day at 18.5 pixels per degree instead of 37, which is a real option if resolution
can be traded for coverage.

Total panorama spend was 14,367 tile requests plus about 40 metadata calls.

## The twin, at two sites

Korenmarkt in Ghent and Piazza del Duomo in Milan are both complete end to end:
Photorealistic 3D Tiles leaves placed in double precision, a registered panorama
camera with a pose covariance, semantics cut onto the surface at the island
boundaries, and the pedestrians the segmenter refused to paint onto the walls
carried as separate bodies. Milan is 476,410 triangles from 342 leaf tiles at a
0.745 degree pose residual.

Both blends now open on their establishing shot and carry one named camera per
shipped figure, so switching camera reproduces a figure rather than approximating
it.

## What one panorama sees, and what twelve see

The single strongest result of the night is also the least flattering, which is
why it is first.

One registered panorama at Korenmarkt is a first hit on **3.3 percent of support
triangles, 4.4 percent by area**, inside the 45 degree crop band. Everything else
takes its material from tile texture, or from nothing at all: 72.8 percent of
faces are texture only and **23.9 percent carry no image evidence whatsoever**.
That is `FIGURES/03_what_one_panorama_sees.png`, and it is the honest picture of
what a single capture twin actually knows.

Fusing twelve panoramas from three sequences and three capture days raises
directly observed surface to **24.1 percent by area**, against 6.9 percent for
the single capture recomputed on the same denominator and the same ray density.
That is a factor of 3.5.

I recounted this independently, with a different tracer, a different ray density
and station altitudes re-derived rather than taken from the pipeline's outputs. On
the same mesh the two agree by area to 2.8 percent, 24.09 against 24.78 on the
single precision mesh both were first run on, and to 4.8 percent on the double
precision mesh the figure now quotes, 22.97 against 24.14. By face count they
disagree by 7.6 percent, which is the expected direction and magnitude for a count
that depends on whether sliver triangles are ever sampled.

**The area fraction is the number to quote.** The count fraction moves with ray
density, and a reader who re-runs at a different density will otherwise think they
have found a bug.

### Where it saturates, and what actually binds

Running every panorama the link graph offers, 41 within 60 m and 87 within 80 m,
with the curve averaged over 60 random acquisition orders so its shape is not the
selection rule's shape:

| target, within a 60 m arm | panoramas |
|---|---|
| 77 percent of achievable coverage | 12 |
| 82 percent | 15 |
| 90 percent | 26 |
| 95 percent | 33 |

The second capture adds 3,938 faces. The last five add 182 each, 4.6 percent of
what the second added. **The per site budget is 12 to 16.** Past about 25 you buy
the final tenth at three times the price.

An earlier reading of a twelve point curve said it had not saturated. That was
wrong, and worth recording as a methodological trap rather than quietly fixing:
twelve captures do not reach the knee, so the tail of a twelve point curve cannot
distinguish a plateau from a straight line, and it will look like the latter.

**Count is not what binds, though.** Widening the site radius from 60 m to 80 m
lifts achievable coverage from 30.6 to 44.8 percent of scene area, which is worth
more than going from 12 to 41 panoramas inside 60 m. Beyond that no panorama count
helps at all: the remaining 55 percent is roofs, courtyards and rear elevations
that no street level capture ever sees. Count binds up to roughly 15 to 25, then
street geometry binds, and then nothing does. Given a choice between 25 panoramas
in a tight radius and 15 over twice the extent, take the extent.

**Which panorama you get first is a fourfold lottery.** The first capture alone
delivers between 1.59 and 6.29 percent of scene area depending on which one it is.
That is invisible without resampling, and it is the strongest single argument
against single capture twins, because it means a one panorama result is not just
low but unreproducible.

### What fusion buys beyond coverage

Transient occlusion falls **3.1x**, from 12.9 percent of observed faces lost in
one capture to 4.1 percent across eight. Not to zero: 472 faces are blocked from
every station that reaches them, mostly wall behind parked vehicles that do not
move between captures.

Panoramas from the same capture drive agree on 84.2 percent of shared faces.
Panoramas from **different** drives agree on only 71.3 percent, and the two ranges
barely overlap. Same-drive agreement mostly measures whether the segmentation is
deterministic. This also puts a number on the cost of the sampled bounding box
described below: a naive box query tends to return one dense drive, which would
have reported 84 percent and **overstated cross-capture reliability by 13 points**.

Two qualifications that limit the headline. Roughly **43 percent of the apparent
multi-view evidence is redundant**: a Kish effective sample size under a parallax
kernel gives 1.92 effective looks where the raw count is 3.38. Any posterior
counting raw looks is overconfident by that factor. And rising coverage is not
rising accuracy, although the usual form of that objection does not land here,
because the faces gained by fusion are seen at slightly better geometry than the
baseline rather than worse: 56.2 against 59.6 degrees median incidence, 39.8
against 43.7 m median range.

Registration quality across the twelve is heterogeneous, residuals 1.08 to 8.10
degrees, and only two beat the Street View capture's 1.31 degrees, most likely
because the walk panoramas are 5760 by 2880 against 16384 by 8192. The four above
4 degrees are excluded from the semantic stage rather than smeared across facade
boundaries.

## A published endpoint that silently returns a sixth of the data

While building the walk, the Mapillary bounding box endpoint was found to be
sampled rather than complete, with no truncation flag. A 200 m box returned **2**
frames of sequence `u5WIQvkTXO7SbeL1l8UN6a`. Enumerating that same sequence by
its id returned **13** within 60 m.

Anything that selects panoramas from a bounding box is therefore working from an
unknown fraction of what exists, and the fraction presumably varies by site,
which is worse than a constant undercount because it silently reorders any
ranking built on panorama density. The working pattern is to use the box only to
name sequences and then enumerate each sequence by id.

The cost is quantified above: because the box tends to return one dense capture
drive rather than a spread across dates, a study built on it would report
same-drive agreement, 84.2 percent, in place of cross-drive agreement, 71.3
percent, and overstate its own reliability by 13 points while looking internally
consistent.

## Exposure, first pilot

A streaming shoot and bounce estimator now runs over walk locations and reduces
each to per location scalars. No ray or path table is ever written, per the
storage rule: results are produced and consumed, and the rays stay internal.

The first pilot is 20 locations at 15 GHz against three illumination models,
isotropic, rooftop macro sites, and street furniture small cells, composed with
the duke phantom through the existing AEGIS dosimetry engine rather than a
reimplementation of it.

It passes a parameter free identity that is worth more than it looks. Zero bounce
isotropic susceptibility must equal the fraction of the sphere that is sky, and
across the traced locations the two agree to every digit printed, median 0.2599
against 0.2599. That single check exercises the direction binning, the solid angle
weights, the occlusion test and the normalisation at once.

Bounce depth and ray count are now measured rather than assumed. Susceptibility
reaches 0.29894 at four bounces against 0.29902 at six and above, while the
truncated throughput share falls from 0.567 at one bounce to 6.9e-4 at four and to
zero by eight. Four bounces is the operating point. Sky fraction is 0.24596 at
200,000 rays and 0.2459935 at 2,000,000, so the ray count is converged well below
where it was set.

### The first distribution

Over 120 locations at Korenmarkt, the susceptibility spread from the fifth to the
ninety fifth percentile is:

| illumination | p05 | median | p95 | spread |
|---|---|---|---|---|
| isotropic | 0.195 | 0.314 | 0.441 | **3.5 dB** |
| rooftop macro sites | 0.022 | 0.138 | 0.393 | **12.5 dB** |
| street small cells | 0.004 | 0.066 | 0.274 | **18.0 dB** |

The illumination model matters more than the position does. Under isotropic
illumination, standing anywhere in one square changes exposure by 3.5 dB. Under
rooftop macro sites it changes by 12.5 dB and under street small cells by 18 dB,
because those sources arrive in narrow elevation bands that the surrounding built
form either admits or blocks completely, and a location either sees the sky in
that band or it does not.

Any population exposure claim therefore depends on the assumed source geometry far
more than on where in a square people actually stand, which is a result about how
such claims should be framed rather than about Ghent.

**The two directional rows are upper bounds, not values.** The crop sweep below
shows their absolute level is set by how far the scene extends, and at the 130 m
radius used here the rooftop susceptibility is **3.24 dB** high. The isotropic row
carries no such caveat, and the spread within a row, which is what the paragraph
above is about, is far less affected than the level.

## Ten cities compared

80 walk locations per city at 15 GHz, one common 130 m radius, one common material
treatment, so what varies between rows is urban form and nothing else.

| site | sky | isotropic median | within-city spread | rooftop median | rooftop spread |
|---|---|---|---|---|---|
| Rynek Glowny, Krakow | 0.462 | 0.534 | 0.80 dB | 0.714 | 3.06 dB |
| Zocalo, Mexico City | 0.374 | 0.420 | 2.25 dB | 0.247 | 10.01 dB |
| Place du Capitole, Toulouse | 0.069 | 0.401 | 2.41 dB | 0.102 | 8.63 dB |
| Trafalgar Square, London | 0.372 | 0.395 | 3.56 dB | 0.140 | 5.22 dB |
| Staromestske, Prague | 0.343 | 0.366 | 4.35 dB | 0.090 | 7.23 dB |
| Plaza Mayor, Madrid | 0.321 | 0.350 | 6.48 dB | 0.035 | 7.86 dB |
| Korenmarkt, Ghent | 0.248 | 0.301 | 3.10 dB | 0.139 | 11.68 dB |
| Hachiko, Tokyo | 0.270 | 0.257 | 3.28 dB | 0.102 | 10.98 dB |
| Grand-Place, Brussels | 0.267 | 0.226 | 5.96 dB | 0.033 | 14.84 dB |
| Times Square, New York | 0.179 | 0.203 | 5.35 dB | 0.204 | 8.52 dB |

**The median susceptibility spans 4.20 dB across the ten cities.** The
within-city spread reaches 6.48 dB under isotropic illumination and 14.84 dB under
rooftop sites. So **where a person stands within one square matters as much as
which city the square is in, and often more.**

That is the most useful thing this table says, and it cuts against how population
exposure is usually framed. A per city or per country figure averages over a
variation larger than the differences it is trying to report.

The ordering is also not simply built density. Krakow's wide open Rynek runs
highest and most uniform, 0.534 with only 0.80 dB of spread, while Brussels'
Grand-Place is both lower and highly variable at 0.226 and 5.96 dB, because a
walk there passes from an enclosed square into the narrow streets feeding it.
Toulouse illustrates the reverse: its 0.069 sky fraction is the roofline anchor
artefact described above, and the walk locations, which are on the actual square,
give a perfectly ordinary 0.401.

Two caveats carried from elsewhere in this document. The rooftop columns are
crop-limited upper bounds at this radius. And the material treatment is a class
prior held constant across all ten rather than per site semantics, which is what
makes the comparison fair rather than what makes it complete.

## The crop radius, and a rule for choosing it

`ROADMAP.md` calls this the largest known hole and says the sweep should run
before the propagation modules, because the answer changes the scene every later
stage consumes. Nine crops at Korenmarkt from 60 to 340 m, observers held fixed
inside the smallest so only the surroundings change, error against the 340 m crop:

| crop | triangles | isotropic | rooftop, 3.1 to 60 deg | street cells, 0.95 to 33 deg |
|---|---|---|---|---|
| 100 m | 97,114 | +0.048 dB | +3.954 dB | +12.040 dB |
| **130 m** | 157,862 | +0.054 dB | **+3.236 dB** | **+9.930 dB** |
| 160 m | 245,112 | +0.013 dB | +0.886 dB | +4.608 dB |
| 200 m | 390,518 | +0.002 dB | +0.108 dB | +1.241 dB |
| **250 m** | 632,406 | +0.000 dB | +0.018 dB | **+0.186 dB** |
| 300 m | 909,832 | +0.000 dB | +0.008 dB | +0.043 dB |
| 340 m | 1,153,486 | 0 | 0 | 0 |

**Isotropic converges by 100 m, rooftop needs 250 m, street small cells need 250
to 300 m.** At the acquired 130 m radius the three errors are +0.05, +3.24 and
**+9.93 dB**.

I proposed a rule here and the third column refuted it, which is worth recording
because the rule was appealing. Rooftop places its farthest macro site at 250 m
and converges at 250 m, so the rule looked like *the crop must reach the farthest
source*. Street small cells reach only 150 m and should therefore have converged
sooner. They converge later, and are three times worse at 130 m. The coincidence
was a coincidence.

What actually orders the three is **how close to the horizon each model puts its
weight**: full sphere, then 3.1 to 60 degrees, then 0.95 to 33, which is also the
order of how much crop each needs. That ordering is measured, and the geometry
newly blocked by widening the crop is indeed grazing, at 0.13 to 6.4 degrees of
elevation with a median of 3.4. The sign is the opposite of the intuitive worry
throughout: a small crop is not missing scatterers that would add power, it is
missing blockers that would remove it.

**I claimed here that the mechanism was short by a factor of thirty. That was my
arithmetic error, not a gap in the physics.** The newly blocked sliver carries
2.3 percent of the rooftop model's illumination measure, and I read that as a
2.3 percent fractional loss, giving 0.1 dB against a measured 3.24. But the share
is an **absolute addition to a small number, not a fractional loss of a large
one**: the converged rooftop susceptibility is only 0.043, so removing 0.023 from
the 0.091 that a 130 m crop reports is 1.2 dB, not 0.1. The sliver is small on the
sphere and large in the answer precisely because the rooftop weight is
concentrated at those elevations.

With the arithmetic right, the mechanism was then decomposed exactly rather than
argued from a proxy. Susceptibility splits with no residual into a zero bounce
part, which is blocking, and a multi bounce part, which is redistribution, and
both are already computed:

| model | blocking | redistribution |
|---|---|---|
| isotropic | 69.2 % | 30.8 % |
| macro rooftop | 69.2 % | 30.8 % |
| street small cells | 76.9 % | 23.1 % |

**Blocking dominates at 69 to 77 percent and redistribution is the rest.** Both
are real, neither alone accounts for the effect, and the split is measured rather
than inferred. Directly observed, the rays a 130 m crop wrongly lets escape are
0.18 percent of the sphere at elevations of 0.1 to 6.4 degrees, and the geometry
that should have blocked them sits at 138 to 184 m horizontal, just outside the
crop. A sliver of sky that should have been brick.

The consequence lands on the case that matters most. **Street level small cells
are the geometry most relevant to dense urban deployment and they are the worst
affected.** Acquire at 250 m minimum, where all three models are within 0.19 dB,
and 300 m for comfort.

### The same bias, found from a different direction

The crop finding turned up independently in registration, which is a separate part
of the pipeline that shares none of the propagation code.

Six poses at the Zocalo registered badly, and they are not scattered: every one
stands in the **northern half of the plaza looking south**, across 200 m of open
ground whose far facades lie outside the 130 m crop. The skyline objective was
therefore being fitted against a silhouette that the scene does not contain.
Re-registering the same panoramas against the 250 m shell, with everything else
held fixed, improves them by about 30 percent:

| pose | at 130 m | at 250 m |
|---|---|---|
| pano_00 | 2.07 deg | 1.31 deg |
| pano_01 | 2.03 deg | 1.56 deg |

The narrow conclusion is worth adopting on its own: **the skyline objective should
be fitted against the widest available geometry, not against the crop the
scattering mesh uses.** The skyline is by definition the far silhouette. Milan's
170 m crop was chosen for the same underlying reason without the reason being
stated.

Two controls, because the sweep spans a precision change and a second tile fetch.
The 60 to 120 m meshes are single precision and the rest double, which is why that
one step reads the wrong way; every step from 130 m upward is like for like. And
the 250 m and wider crops come from a second, larger fetch, so a 200 m crop
rebuilt from it was compared against the original: 390,518 triangles from both, so
the step at 200 to 250 m is physics rather than acquisition.

### The finding hiding in the manifest

A second run bound the semantic posterior in as the material source, over 120
locations. Its manifest reports the area fraction carrying each class, and that
is the number to read:

**The semantic classes together cover about 3 percent of scene area.** Brick 2.53
percent, marble 0.22, metal 0.15, asphalt 0.10, concrete and glass essentially
zero. The geometric fallback covers the other 97 percent.

That is not a defect, it is the coverage result arriving from the other direction.
One panorama is a first hit on 4.4 percent of scene area, so a single capture twin
can only bind materials from evidence on a few percent of the surface and must
guess the rest from surface orientation. Which means the two runs do not compare
geometric materials against semantic ones. They compare a 97 percent geometric
scene against a 97 percent geometric scene, and any difference between them is the
effect of 3 percent of the surface.

### The experiment, and its first answer

Vary the fraction of the scene carrying image evidence, hold everything else
fixed, and measure how far the exposure distribution moves. Both runs below are
120 locations on the same walk with the same seed.

| evidence coverage | isotropic median | rooftop median | isotropic spread | rooftop spread |
|---|---|---|---|---|
| one panorama, 3.0 % | 0.3144 | 0.1380 | 3.55 dB | 12.48 dB |
| fused walk, 10.6 % | 0.3370 | 0.1485 | 3.86 dB | 12.46 dB |

**Tripling the evidence coverage moves the median by 0.30 dB and leaves the spread
unchanged**, 12.48 against 12.46 dB. On this evidence the exposure distribution is
set by geometry, meaning sky fraction and blockage, and is close to insensitive to
where the materials came from.

Two honest limits on that. The comparison spans 3 to 10.6 percent and not zero,
because the geometric pilot ran on a different and smaller location set, so the
zero evidence baseline on these same 120 locations is still owed. And the result
licenses nothing about a fully evidence bound scene, because no such scene was
observed and the saturation work says street level capture cannot produce one:
roofs, courtyards and rear elevations are 55 percent of the surface and no
panorama count reaches them.

If it survives the baseline, this reframes the project's claim in a direction that
is both more defensible and more interesting. Not that semantic materials make
exposure right, but that **the geometry sets the distribution, and the semantic
layer earns its place through occlusion handling, evidence confidence and cross
capture validation rather than by moving the exposure number**. That is falsifiable
in a way the other claim was not.

## Brickwork, derived rather than measured

No measurement will be taken in this project, so the scattering behaviour of
masonry is derived from construction standards and solved rigorously. A coupled
wave solve over standard bond geometry, checked against a Kirchhoff phase screen,
with nothing fitted anywhere in the chain.

Convergence is established rather than assumed, and it changed an answer. Across
four cases the last truncation step moves specular by 0.1 to 0.8 percent and
diffuse by 0.4 to 6.8, so **every specular number carries a 1 percent bar and
every diffuse number a 7 percent bar**, measured rather than asserted. The
propagating order count saturates at 458 against the 462 the visible disc
predicts. Elliptic rather than rectangular harmonic truncation drops the box
corner orders, which are the most deeply evanescent in the set, for 30 percent
fewer modes and half the memory with the answer moving 0.08 percent.

The answer it changed is worth recording because it went against the interesting
direction. An earlier claim that the phase screen ran two to five times high on
diffuse scattering at a groove aspect ratio of one turned out to be an artefact of
the rigorous side being 43 percent low at the truncation it was computed at.
Converged, the factor is 1.8. Specular was converged throughout and is unaffected.

**The result that constrains another part of this project.** The rigorous solve
and the phase screen agree in the forward and specular directions to 2 dB. In
backscatter they diverge by 13 to 27 dB across a 14 degree span, with the rigorous
orders on a flat floor near -41.5 dB where the screen falls to -68.2 dB. It is not
a correctable bias: a phase screen can redirect power but cannot send it back the
way it came, and the backscatter here comes from the groove walls and the arris of
every unit. So the phase screen is barred from the monostatic branch at FR2.

**And one claim about real facades rather than about a method.** The rigorous
order envelope is flat to 1.2 dB at 10 GHz across the whole hemisphere, with
backscatter between half and 1.2 times the forward power. That is Lambertian.
Published measurement work fits Lambertian to facades and attributes it to
pillars, balconies and street furniture. Here the brickwork alone produces it,
from construction geometry.

### A validation that could not be run

Against Landron 1996 at 4 GHz the model predicts reflection magnitude to 2.0 dB
rms with no fitted parameter. Against Dillard 2003 at 28 GHz it is 8.2 dB rms and
systematically low, which is the band this study actually works in, so it was
chased rather than reported.

Inverting the two geometric parameters fits all six points to 1.40 dB, at a joint
recess of 8.2 mm and a unit scatter of 0.90 mm, both construction plausible, and
without breaking the 4 GHz agreement. So the disagreement is in the parameters
rather than in the form of the model. The leading hypothesis, flush pointing, is
not the answer on its own, because at 28 GHz the unit scatter dominates the recess.

But the residual turned out not to be testable. In the source's own tables, four
repeats at one angle span a factor of 3.3 to 8.4 in amplitude with standard
deviations at or above the means, the brick and limestone clouds overlap
completely below 60 degrees, and the 60 degree points exceed the smooth surface
Fresnel bound implied by the permittivities the same document reports, which is
impossible. The absolute calibration is a sidelobe gain estimate read 85 degrees
off boresight, and four of six angles were never calibrated at all.

So the honest verdict is symmetric: **1.40 dB is not a validation and 8.2 dB is
not a refutation**, because the disagreement is smaller than the measurement's own
repeat scatter. The model is validated at 4 GHz and unvalidated at FR2, and that
is the top open item for this workstream.

## Foliage

Foliage fails a ray tracer twice over. The geometry is wrong, because
photogrammetric trees are lumpy opaque blobs rather than a canopy of leaves, and
the material is wrong, because a tree is not a surface at all.

Measured first, so the effort stays proportionate: vegetation is **1.4 percent of
classified area at Korenmarkt and 0.9 percent at Milan**, or 2.0 percent of solid
angle at Korenmarkt. Small at two stone paved squares, which are the best case,
and the ten city set will not all be like that.

### The standard does not cover the band

ITU-R P.833-10 (09/2021) is the version in force, which I verified independently
against the ITU register. Its recommends clause claims 30 MHz to 100 GHz, but that
is a union over disjoint sub-models. The radiative transfer model is the only
volume-renderable part, and its tables have rows at 1.3, 2, 2.2, 11, 37 and
61.5 GHz. **There is no row anywhere in FR2, none in upper FR3, and nothing at all
between 12.5 and 37 GHz.** The saturation ceiling exists only below 3.6 GHz, so
the headline equation cannot even be closed here.

The provenance is circular in the same shape `ROUGHNESS.md` found for facade
roughness. The theory traces to a single 1985 US Army report, the tabulated
species data to a single 2002 project, and the millimetre wave anchor to one Texas
pecan orchard measured at three spot frequencies in 1985. The tables have been
byte-identical since 2005. The recommendation also contradicts itself: one table
gives 6.5 dB/m at 11 GHz where its own figure gives 2.2.

That is why the deliverable is a swept curve rather than a number.

### The medium wins, and not for the expected reason

Three treatments were compared: cutting vegetation out as the honest null, an
opaque surface, and a participating medium.

The surface loses on a derived construction fact rather than on taste. Leaf area
index times leaf thickness over canopy depth gives a volume fraction of 6.4e-5,
and Maxwell-Garnett then gives a boundary reflectance of 1.9e-9 against the 0.029
of the wood row the pipeline currently uses. That is **71.8 dB of invented
reflection**. A canopy has no interface.

Procedural trees lose on the tracer's own material model rather than on ray
budget. Its Fresnel term is a half space and a leaf is 0.2 mm, so half space over
thin slab over-reflects by 15.2 dB at 7 GHz and 9.1 at 15. No ray budget fixes
that.

The medium does not win by beating the surface at some optical depth. It wins
because the surface is pinned at the opaque limit and the null is pinned at
transparent, and the medium is the only treatment that carries the optical depth
uncertainty, which is precisely what the standard cannot pin down in this band.

### Two corrections to what I assumed

I scoped this work as a small correction. At the measured optical depth, the
surface and null treatments cross 0.5 dB at **2.1 percent** canopy solid angle.
**Korenmarkt is 2.0 percent, so it sits exactly on that line**, not comfortably
below it. Milan at 0.9 percent is genuinely safe.

And between roughly 2 and 6 percent the surface treatment is the outlier, which
means **doing nothing would beat what the pipeline currently does**, since
`semantic_binding.py` maps vegetation to the wood row. That mapping is now known
to be the worst of the three available choices in exactly the regime one of our
two sites occupies.

Validation used no measurement anywhere: the estimator reproduces free space to
1e-6 and the PEC ground plane to 2.0, and its transport is checked against the
exact absorbing slab result, chi = 1/2 + 1/2 E2(tau).

## Ten cities

Twenty four candidate squares were screened before any acquisition spend, in
**4,091 metadata requests and 79 seconds with zero tiles fetched**. Screening
walks outwards along the Street View link graph rather than querying a bounding
box, which matters given what the Mapillary box turned out to do.

The unit of merit is the **walk**, meaning the largest set of panoramas sharing
one capture date and linked to each other. Sites carry between 5 and 21 capture
dates inside 60 m and panoramas almost never link across dates, so a raw panorama
count overstates what any single traverse can reach. The screening is
independently consistent with what was already known at the two built sites:
Milan at 2.5 m median spacing and Korenmarkt at 10.0 m, against 2.8 and 10.5 m
measured separately and earlier.

The coverage gate needed one correction, and its own test caught it. The first
form scored a dense straight line down the middle of a square as full coverage,
which would have promoted line drives over walks. It is now azimuth spread over
sixteen sectors about the centre, which a collinear set cannot max out because a
line fills two opposite sectors and scores 2 of 16.

Acquisition ran at **1,575 leaf tiles in 3,216 requests and about three minutes**
with ten concurrent pulls, with the acquisition radius set equal to the crop
radius so nothing paid for is discarded.

Two sites failed after acquisition, both on geometry rather than panoramas.
**Istanbul** returned 80 leaf tiles holding 11,864 triangles against 130k to 470k
everywhere else, so it is a coarse base mesh with no photogrammetry at all despite
reporting the same 2.006 m geometric error as every other site. Its 10 m skyline
in the gallery render confirms this independently. **Toulouse** is the anchor
problem described above and went to reserve, with Times Square promoted in its
place.

The full table is `outputs/city_screening/screening_table.md` and the selection
argument is in `CITIES.md`.

Nine sites were then acquired and built, giving eleven with the two that already
existed: Brussels, Krakow, London, Madrid, Mexico City, New York, Prague, Tokyo
and Toulouse, all at the same 130 m crop radius and all in double precision. They
were later re-acquired at 250 m as well, 4,032 tiles for 8,128 requests, giving
occlusion shells of 708k to 720k triangles against 130k to 260k at 130 m.

### Panoramas, and how far they got

| site | fetched | segmented at 1536 | registered | status |
|---|---|---|---|---|
| Staromestske namesti, Prague | 14 | 14 | 14 | complete |
| Plaza de la Constitucion, Mexico City | 14 | 14 | 14 | complete |
| Plaza Mayor, Madrid | 9 | 9 | 9 | partial, quota |

Madrid's nine are the most spread nine of its fourteen rather than an arbitrary
prefix, because farthest-point sampling is prefix optimal. Its extent is identical
to the full set and only the minimum separation differs, 30.5 m against 21.7, so
Madrid lost density rather than reach.

Registration quality varies more than I first reported. I read the first few poses
and quoted 0.28 to 1.49 degrees, which was optimistic. The actual medians are
0.33 at Madrid, 0.82 at Prague and **2.76 at the Zocalo**, with a worst case of
9.33. Madrid and Prague beat both existing references, Milan at 1.05 and
Korenmarkt at 2.83. The Zocalo does not.

One genuine improvement: **ten of thirty-seven poses landed on the altitude search
bound and twenty-seven did not.** Every pose previously shipped in this repository
had that defect, so a majority free of it is new.

I ran a quality pass over every one of them, because a cross city distribution is
only as good as its worst site and a bad site fails quietly rather than loudly.
All ten have zero degenerate faces, zero duplicate index triples and a consistent
260 by 260 m extent, and the ground altitudes independently check out against real
city elevations, including New York at -18 m, which is right once the roughly
-32 m geoid separation there is accounted for, and Times Square's 428 m of
vertical extent, which is also right.

**One site failed.** At the Toulouse anchor a standing observer sees 6.9 percent
sky. Twenty metres east it is 47.6 percent, and the ground steps from 191.1 to
211.1 m over that distance, which is a roofline rather than a slope. The anchor
is on the Capitole building instead of the square in front of it. Since tiles are
cached per tile, re-cropping at a corrected centre costs almost nothing.

The general form of that check is worth keeping for the remaining cities: cast a
full sphere from 1.5 m above the ground under the nominal anchor and reject any
site below about 0.10 sky, then sample a few points 20 to 30 m out to confirm the
anchor is not on a local high. The healthy range across the other sites is 0.18 at
Times Square, a genuine canyon, up to 0.46 at Krakow.

## Things that were wrong

**The voxel remeshing rejection was measuring a misparameterisation.** The
original argument used a 0.30 m solidify thickness against voxel grids of 0.5 to
2.0 m, so the walls were between 1.7 and 6.7 times thinner than the grid that had
to represent them, and adaptivity was off. With thickness set equal to voxel size,
which is how Robin had done it before, the conclusion reverses. Details in the
mesh section of `DECISIONS.md`.

**My own coverage verification was broken before it was right.** The first
recount returned 12.29 percent against the pipeline's 17.13 and I nearly reported
a 39 percent discrepancy. The cause was mine: finding ground by casting downward
from above the bounding box and taking the highest hit puts the camera on the roof
wherever the photogrammetry bridges a street, and four of twelve stations landed 7
to 18 m above the pavement. Casting from just above pedestrian level fixed it and
the pipeline's number then held.

**The texture evidence module still claimed to be correcting a defect that had
been fixed.** Its per tile offset compensation was justified by single precision
tile placement, which phase 2 removed. Measured now it estimates 97 nanometres
and is a no-op. That is worth recording rather than deleting, because it is an
independent confirmation of the placement fix from a measurement never used to
argue for it: face to tile matching goes from 87.2 percent on the old mesh to
**99.97 percent** on the double precision one.

**The shipped blend could not be opened usefully.** It contained no camera object
at all, because cameras were built and destroyed inside the render loop and the
file was saved before that loop ran, and it saved with the tiles hidden so it
rendered an empty sky. Both are fixed and verified by rendering from the saved
file rather than by inspecting its metadata.

## Reproducing any of this

Everything below regenerates from the repository plus the tile cache under
`data/tiles/`, which is gitignored because it is 200 MB of GLB but is stable and
per tile cacheable, so a rerun at a different radius refetches only what is new.

```
python screen_cities.py                                   # the screening table
python download_inhouse_tiles.py --lat .. --lon .. --radius-m 130
python render_showcase.py --site korenmarkt --blend       # figures 01 to 06
blender --background --python render_city_gallery.py      # every city, figure 11
python make_city_sheet.py                                 # figure 11 composed
python make_remesh_panel.py                               # figure 10 composed
python run_exposure.py                                    # figures 14
python run_masonry_grating.py && python run_masonry_spectrum.py
python run_foliage_study.py                               # figure 12
python remesh_support_mesh.py                             # the mesh study meshes
```

The two showcase blends carry one named camera per shipped figure, so switching
camera in Blender reproduces a figure rather than approximating it.
`korenmarkt_mesh_study.blend` carries the three candidate support meshes as
separate collections plus both the pedestrian crop camera and the orbit camera
that figure 10 uses.

The suite is 698 passing and 1 skipped, up from 570 at the start of the night.

## Still open

- **The zero evidence baseline** on the same 120 locations, which is what turns
  the evidence coverage experiment from suggestive into conclusive.
- **The brickwork model is unvalidated at FR2.** It is validated at 4 GHz to
  2.0 dB with nothing fitted, and the only FR2 measurement available cannot
  adjudicate because its own repeat scatter exceeds the disagreement.
- **Vegetation currently routes to the wood row**, which the foliage sweep now
  shows is the worst of the three available treatments in the 2 to 6 percent
  canopy regime that Korenmarkt sits in. The one line fix is to route it to the
  null. The right fix is a twenty line medium boundary hook in the tracer, already
  specified.
- **Re-running the ten city sweep at 250 m.** The acquisition is done, 4,032
  tiles for 8,128 requests, and the shells are built. Keep the narrow crop as the
  scattering and semantics mesh and use the wide one as an occlusion shell, which
  is the two level scheme the roadmap anticipated and which the sweep has now
  sized.
- **Whether the grazing-weight explanation survives a second site.** It ordered
  the three illumination models correctly at Korenmarkt after the source-range
  rule failed, but one site is one site, and Times Square at 18 percent sky should
  stress it hardest.
- Panoramas for the acquired cities. Nine sites have geometry and none have
  panoramas, so eight of eleven are geometry only. Sizing measured rather than
  estimated: roughly 43,000 requests for 16 panoramas across 8 sites.
- Toulouse needs re-cropping onto the square rather than the Capitole roof, at
  about 350 requests since tiles are cached per tile.
- Milan's two registration objectives still disagree on horizontal position by
  2.5 m against a 0.21 m seed spread, and a 0.33 m systematic between depth
  derived and skyline derived altitude, same sign at both sites, is unexplained.
