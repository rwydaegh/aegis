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
directly observed surface to **24.8 percent by area**, against 6.9 percent for
the single capture recomputed on the same denominator and the same ray density.
That is a factor of 3.6.

I recounted this independently, with a different tracer, a different ray density
and station altitudes re-derived rather than taken from the pipeline's outputs.
By area the two agree to 2.8 percent, 24.09 against 24.78. By face count they
disagree by 7.6 percent, which is the expected direction and magnitude for a
count that depends on whether sliver triangles are ever sampled. **The area
fraction is the number to quote.** The count fraction moves with ray density and
a reader who re-runs at a different density will otherwise think they have found
a bug.

The coverage curve has not saturated at twelve. The eleventh and twelfth
panoramas are still each worth a few tenths of a point on a slow linear climb,
and eight panoramas reach 83 percent of what twelve reach. Where it saturates is
the number that sets the acquisition budget for every other city, so it is being
measured rather than assumed.

Two qualifications that limit the headline. Roughly **43 percent of the apparent
multi-view evidence is redundant**: a Kish effective sample size under a parallax
kernel gives 1.92 effective looks where the raw count is 3.38. Any posterior
counting raw looks is overconfident by that factor. And rising coverage is not
rising accuracy, although the usual form of that objection does not land here,
because the faces gained by fusion are seen at slightly better geometry than the
baseline rather than worse: 56.2 against 59.6 degrees median incidence, 39.8
against 43.7 m median range.

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
