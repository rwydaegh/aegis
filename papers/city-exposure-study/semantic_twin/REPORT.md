# Overnight run, 1 to 2 August 2026

What was built, what was measured, and what turned out to be wrong. Numbers in
this file are measured unless explicitly labelled otherwise. Where a claim was
checked twice by different means, both are given, including the cases where the
check was the thing that was broken.

Figures referenced here are collected in `FIGURES/`. The two assembled scenes
are `outputs/showcase_korenmarkt/korenmarkt.blend` and
`outputs/showcase_milan_duomo/milan_duomo.blend`.

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
and station altitudes re-derived rather than taken from the pipeline's outputs.
By area the two agree to 2.8 percent. By face count they disagree by 7.6 percent,
which is the expected direction and magnitude for a count that depends on whether
sliver triangles are ever sampled. **The area fraction is the number to quote.**
The count fraction moves with ray density and a reader who re-runs at a different
density will otherwise think they have found a bug.

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

The experiment this sets up is the one that ties the project together: vary the
fraction of the scene carrying image evidence, from 3 percent at one panorama to
24 percent at twelve, and measure how far the exposure distribution moves. If it
barely moves, semantic material binding does not matter much at these frequencies
and this study should say so. If it moves a lot, single capture twins are unfit
and the walk is mandatory across all eleven cities. If it moves and then flattens,
the flattening point is how much evidence a site actually needs, which is a design
number nobody currently has.

## Brickwork, derived rather than measured

No measurement will be taken in this project, so the scattering behaviour of
masonry is derived from construction standards and solved rigorously. A coupled
wave solve over standard bond geometry, checked against a Kirchhoff phase screen,
with nothing fitted anywhere in the chain.

Convergence is established rather than assumed. Over 293 to 2,397 retained
Floquet orders the specular efficiency settles within 0.6 percent, while the
diffuse term oscillates between 0.0162 and 0.0178 with no monotone trend, so
**every diffuse number carries a 6 percent bar**. The propagating order count
saturates at 458 against the 462 the visible disc predicts. Elliptic rather than
rectangular harmonic truncation drops the box corner orders, which are the most
deeply evanescent in the set, for 30 percent fewer modes and half the memory with
the answer moving 0.08 percent.

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
and Toulouse, all at the same 130 m crop radius and all in double precision.

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

## Still open

- Binding the semantic posterior into the exposure run, and measuring how far the
  distribution moves when materials come from image evidence rather than surface
  orientation.
- Where the coverage curve saturates, which sets the per city acquisition budget.
- Foliage. Vegetation is 1.4 percent of classified area at Korenmarkt and 0.9
  percent at Milan, so it is a small correction at two stone paved squares, but it
  is the only class where the geometry itself is wrong rather than merely the
  material, and the ten city set will include sites where it is not small.
- The crop radius. 130 m has not converged and the convergence sweep should run
  before the remaining propagation modules, because the answer changes the scene
  every later stage consumes.
- Milan's two registration objectives still disagree on horizontal position by
  2.5 m against a 0.21 m seed spread, and a 0.33 m systematic between depth
  derived and skyline derived altitude, same sign at both sites, is unexplained.
