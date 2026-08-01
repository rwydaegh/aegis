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

**Caveat that matters more than any number in the pilot.** Materials in this run
are assigned geometrically, by which way a triangle points, with the semantic
posterior not yet bound in. So the pilot currently demonstrates a working tracer
over Google photogrammetry, which is not novel, rather than a semantically bound
one, which is the entire thesis. Binding the fishnet posterior in, and reporting
how far the exposure distribution moves when it is, is the outstanding item.

## Ten cities

Twenty four candidate squares were screened before any acquisition spend, on
panorama count, median spacing, capture dates, angular coverage of the square and
whether a single walk encircles it. The screening is independently consistent with
what was already known at the two built sites: Milan comes out near the top at
2.5 m median spacing and Korenmarkt near the bottom at 10.0 m, against 2.8 and
10.5 m measured separately and earlier.

The full table is `outputs/city_screening/screening_table.md`.

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
