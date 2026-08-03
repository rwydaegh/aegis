# Overnight run, 1 to 2 August 2026

What was built, what was measured, and what turned out to be wrong. Numbers in
this file are measured unless explicitly labelled otherwise. Where a claim was
checked twice by different means, both are given, including the cases where the
check was the thing that was broken.

Figures referenced here are collected in `FIGURES/`. The two assembled scenes
are `outputs/showcase_korenmarkt/korenmarkt.blend` and
`outputs/showcase_milan_duomo/milan_duomo.blend`.

## Read this first: the directional numbers below are under a superseded law

Late on 2026-08-02 the rooftop and small cell illumination models were
re derived. The old pair put a fixed site height into a `1/sin^3(el)` weight and
then widened the support with a height band the weight knows nothing about. The
corrected pair takes the height band and the range band as the model and derives
both the shape and the support from them. `DECISIONS.md` carries the call and
`MONOSTATIC_SBR.md` section 2.7 the derivation.

**Everything in this report with "rooftop" or "street" on it was computed under
the old law.** The isotropic column, the sky fractions, the coverage and
saturation work, the evidence ladder and the mesh, brickwork and foliage results
are untouched, because none of them evaluates a directional model.

The correction is large and it points one way. The old rooftop model put 61.7
percent of its measure below 5 degrees of elevation, the corrected one puts 9.4.
Measured at Korenmarkt from the same rays at the same seed, so the difference
between the two laws carries no Monte Carlo noise:

| | 130 m | 250 m | crop correction |
|---|---|---|---|
| rooftop, old | 0.09335 | 0.04034 | -3.64 dB |
| rooftop, corrected | 0.16766 | 0.14897 | **-0.51 dB** |
| small cells, old | 0.04804 | 0.00471 | -10.08 dB |
| small cells, corrected | 0.05827 | 0.01179 | **-6.94 dB** |
| isotropic | 0.29123 | 0.28681 | -0.07 dB |

So the headline crop result below, which is the thing this report leads on, is
**halved for the small cells and all but erased for the rooftop model at this
site**. That is the mechanism agreeing with itself rather than collapsing: near
horizon measure was the entire reason a crop radius mattered, and the correction
removes most of it. Re-acquiring at 250 m stays the right call, because 7 dB is
still 7 dB.

**The eleven city sweep has since been re-run under the corrected law**, as the
`city250_corrected_*` tags, and the cross city table below now carries both
columns. Everything else in this report with a rooftop or street number on it is
still the old law and is flagged where it appears. Read those as ordinal rather
than absolute, and the isotropic column as it stands.

One caveat inside the corrected pair. The superseded runs traced six surface
interactions and the corrected ones four, so the two are not bit for bit paired.
The convergence measurement below sizes that at 0.0004 dB, and the isotropic
column, which both runs share and which the law does not touch, reproduces to the
fourth decimal at every site.

## The short version

- **Eleven squares are built and all eleven are compared**, nine acquired
  tonight, then all re-acquired at 250 m once the crop sweep said 130 was too
  small. Median sky fraction over the walk runs from 11 percent at Times Square
  to 45 percent at Krakow, which is the geometric spread this study exists to
  turn into an exposure distribution. The 18 to 46 percent pair quoted later in
  this report is a different measurement, a single full sphere cast at each
  site's anchor on the 130 m mesh, and it is
  `outputs/city_gallery/metrics.json`, 0.1790 at Times Square and 0.4617 at
  Krakow. The two are not interchangeable.

  **Superseded on 2026-08-03.** Both readings put Krakow at the top because its
  walk was on the Cloth Hall roof. On `city250_L3_*` the walk median sky fraction
  runs 12.1 percent at Times Square to 33.0 percent at London Trafalgar, with
  Krakow third at 31.4 percent.
- **Eleven cities now carry an exposure distribution at the converged crop
  radius.** The median spans 5.13 dB isotropic and **9.65 dB rooftop** between
  cities, against 14.49 dB rooftop under the superseded law, while the largest
  spread *within* one square is 6.15 dB isotropic and 13.29 dB rooftop.
  **Superseded on 2026-08-03.** The ground datum fix and the retrace at three
  bounces put those spreads at 3.71 dB isotropic, 4.93 dB rooftop and 9.58 dB
  street small cell, with the largest within city spread 6.46 dB isotropic at
  Madrid. See `AGGREGATE_REBUILD.md`. The conclusion below survives and its
  margin grows from 1.02 to 2.75 dB.
  **Under isotropic illumination the variation inside one
  square exceeds the variation between eleven cities on three continents.** A per
  city figure therefore averages over a variation larger than the differences it
  reports. A split half test says these characterise the walk rather than the
  square, so an area representative number needs a sampling design.
- **Image evidence barely moves exposure, and this is now conclusive.** Going
  from no image evidence at all to a tenth of the scene bound by it shifts the
  median 0.29 dB and moves exactly one location in 120 by more than a decibel. A
  single panorama is worth 0.008 dB. That reframes the claim: geometry sets the
  distribution, and the semantic layer earns its place through occlusion
  handling, evidence confidence and cross capture validation rather than by
  moving the number.
- **One panorama sees 6.9 percent of a scene by area. Twelve see 24.1 percent,
  and it saturates there**, so the per site budget is 12 to 16. Both figures are
  the full sphere on a common denominator. The 4.4 percent quoted further down is
  the same capture scored inside the four rectilinear crops the fishnet cuts
  against, which is a different denominator and does not reproduce from anything
  shipped. Extent matters
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
- **The acquired crop radius was too small, worst for the case that matters most,
  and the error is not a constant.** Re-run at 250 m across the ten sites that
  have a mesh at both radii, Milan being the one with no 130 m build, the
  correction ranges **0.05 to 4.80 dB rooftop and 0.16 to 11.39 street**, which
  is comparable to the whole between-city spread, so the original columns were
  distorted relative to each other rather than shifted together. Crop corrected,
  the between-city spread is 5.13 dB isotropic and 14.49 dB rooftop: urban form
  matters far more under directional illumination, which was invisible before.

  **Superseded in part, 2026-08-02.** Both legs of that crop correction, and the
  14.49 dB, were computed under the elevation law corrected in
  `MONOSTATIC_SBR.md` section 2.7.1. The isotropic column is unaffected and
  stands. The rooftop column does not: the law correction shifts each site by
  1.06 to 6.33 dB, which is site dependent and so cannot be applied as an offset,
  and it reorders the cities, with New York Times Square falling six places of
  eleven. The between-city rooftop spread becomes **9.65 dB**, and the per site
  rooftop over isotropic range narrows from 11.32 to 6.12 dB, so urban form still
  matters more under directional illumination but by 6 dB rather than 11. The
  crop requirement itself survives: 250 m is still needed, now set by the street
  model alone, rooftop having converged in to 200 m. The cross site crop
  correction has not been remeasured under the corrected law, and at Korenmarkt,
  where it has, the 130 to 250 m rooftop shift falls from 4.58 to 1.09 dB.

  **Superseded again, 2026-08-03.** The 9.65 dB was measured on the run whose
  ground datum put two walks on a roof. On `city250_L3_*` the between city
  rooftop spread is **4.93 dB** and the isotropic one **3.71 dB**.
  `AGGREGATE_REBUILD.md` carries the per site shifts.
- Two workstreams reached honest negative or unvalidatable results and say so:
  brickwork is validated at 4 GHz and unvalidated at FR2 because the only
  measurement available cannot adjudicate, and the vegetation standard has no
  tabulated data anywhere in our band.

## One thing needs you

**The Street View tiles API has a daily cap of 15,000 requests and we hit it.**
Acquisition stopped on HTTP 429 partway through the third site and did not
recover after cooldown at reduced concurrency, so it is a daily quota rather than
a burst limit.

**A day buys between 29 and 117 panoramas, and the difference is the capture, not
the setting.** I first wrote that a zoom-5 panorama is 338 tiles and the cap is
therefore 44 a day. That holds only for a 13,312 pixel wide car capture.
Brussels' 2024 capture is 16,384 wide and costs 512 tiles. Times Square is 8,192
wide and costs 128. Had the second cohort all been 512, forty-one panoramas would
have been 21,000 requests and blown the cap. As it fell out they cost 13,540.

That width also carries a trap that cost a run. **Times Square has no Street View
car coverage at all**, because the square is pedestrianised, so all 105 of its
panoramas across every capture date are user contributed photospheres. Those stop
at zoom 4, and a hardcoded `MAX_ZOOM = 5` made every single tile request 404 and
the first attempt acquired nothing. The top of the pyramid is now derived from
the tile grid the metadata implies, which resolves to 5 for both car widths and
to 4 here, and two tests pin it.

Total panorama spend across both cohorts was about 27,900 tile requests.

Segmentation cost is now measured on both machines, because the difference
decides where this runs. **On the A6000, 47.8 to 58.4 seconds per panorama,
median 53.4, with 41 panoramas segmented in 37.4 minutes.** On this four core
VM with no GPU it is 45 to 105 seconds *per view* and 26 views per panorama, so
20 to 50 minutes each. A factor of 20 to 50, which is the whole argument for
keeping a GPU box alive while panoramas are still arriving.

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

One registered panorama at Korenmarkt is a first hit on **4.3 percent of support
triangles, 6.9 percent by area**, over the full sphere. Inside the four 90 degree
rectilinear crops the fishnet cuts against, the shipped
`outputs/korenmarkt_fishnet_vistas/*_fishnet.npz` files touch 2.3 percent of
triangles and 3.2 percent by area. **The 3.3 and 4.4 percent pair this section
carried until now reproduces from neither**, and is withdrawn rather than
reassigned to a denominator it may not belong to. Everything else takes its
material from tile texture, or from nothing at all: 72.8 percent of
faces are texture only and **23.9 percent carry no image evidence whatsoever**.
That is `FIGURES/03_what_one_panorama_sees.png`, and it is the honest picture of
what a single capture twin actually knows.

Fusing twelve panoramas from three sequences and three capture days raises
directly observed surface to **15.9 percent of triangles and 24.1 percent by
area**, on the same full sphere denominator and the same ray density. That is a
factor of 3.5 on area. Source `outputs/walk_korenmarkt/walk_coverage.json`.

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

| target, within a 60 m arm | panoramas, by area | panoramas, by face count |
|---|---|---|
| 77 percent of achievable coverage | 13 | 15 |
| 82 percent | 15 | 18 |
| 90 percent | 24 | 26 |
| 95 percent | 32 | 33 |

Earlier drafts gave 12, 15, 26, 33 in one column, which is the area answer for
the first two rows and the face answer for the last two. Twelve panoramas reach
76.9 percent of the achievable area and 72.0 percent of the achievable faces.

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

**Which panorama you get first is a fourteenfold lottery.** The first capture
alone delivers between 0.84 and 11.56 percent of scene area depending on which
one it is. The 1.59 to 6.29 percent quoted in earlier drafts is the tenth to
ninetieth percentile of the *face* count, which is both a different quantity and
a trimmed one. That is invisible without resampling, and it is the strongest
single argument
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
across the traced locations the two agree closely, median 0.2582 against 0.2579
with a worst case of 0.64 percent. That single check exercises the direction
binning, the solid angle weights, the occlusion test and the normalisation at
once. The residual is not noise: susceptibility is a ratio of sums over direction
cells and sky fraction is a sum of per cell means, so the two differ by a
covariance between cell weight and cell occlusion, which
`tests/test_propagation.py::test_zero_bounce_susceptibility_equals_the_sky_fraction`
states and bounds. An earlier draft of this paragraph reported the pair as 0.2599
against 0.2599, agreeing to every digit printed. That run has been overwritten and
the surviving `pilot_15ghz_locations.jsonl` does not reproduce it.

**And it is validated against a case that could have failed.** The perfect
conductor ground plane, which the design specifies, cannot discriminate: both
polarisations reflect fully, so it returns 2 whether the Fresnel average is
right, TE only or TM only. Measured, its upper hemisphere mean is 1.9999823 with
a worst cell 1.15 percent out, which is the Monte Carlo floor of the run and not
a bias. A concrete ground plane at nine elevation bands matches the band averaged
closed form to 1.02 percent and **rejects the TE only answer at every band where
the two separate.** All three of those are in
`outputs/exposure_korenmarkt/exposure_validation.json`. Two further closed forms
fell out of building that check and are derivations rather than runs, with no
output file behind them: a Lambertian plane gives `K = 1 + 2 sin(el)` exactly,
and the Rayleigh criterion's angle dependence appears only in the lowest band.

One weak internal consistency check is worth quoting because it uses nothing but
the outputs. Dividing absorbed power by mean absorbed power density recovers 1.96
square metres at the median, which is an adult male body surface area, from two
independently computed quantities. It is weak rather than free because the two
are not the same average: absorbed power is an area weighted integral over
triangles and the mean density is an unweighted triangle mean, so the ratio is a
body area only up to the correlation between triangle area and illumination. It
spans 1.88 to 2.01 across the 20 locations, which is the size of that effect.

Bounce depth and ray count are now measured rather than assumed, in
`outputs/exposure_korenmarkt/exposure_convergence.json`. Isotropic susceptibility
reaches 0.35134 at four surface interactions against 0.35137 at six and above,
a difference of 0.0004 dB, while the truncated throughput share falls from 0.2515
at one interaction to 6.3e-4 at four, 1.4e-5 at six and zero by eight. Four is
the operating point. Sky fraction is 0.23711 with a seed to seed standard
deviation of 0.00085 at 200,000 rays and 0.23695 with 0.00027 at 1,600,000, so
the ray count is converged well below where it was set.

An earlier form of this paragraph reported 0.29894 at four bounces against
0.29902 at six, a truncated share of 0.567 at one bounce, and sky fractions of
0.24596 and 0.2459935. Those predate a fix that made `max_bounces` count surface
interactions rather than one more than it, and the file that produced them has
been overwritten. The conclusion, that four is enough, is unchanged.

### The first distribution

Over 120 locations at Korenmarkt, the susceptibility spread from the fifth to the
ninety fifth percentile is:

| illumination | p05 | median | p95 | spread | spread, superseded |
|---|---|---|---|---|---|
| isotropic | 0.195 | 0.314 | 0.441 | **3.5 dB** | 3.5 dB |
| rooftop macro sites | 0.077 | 0.224 | 0.503 | **8.2 dB** | 12.5 dB |
| street small cells | 0.007 | 0.098 | 0.314 | **16.6 dB** | 18.0 dB |

The first four columns are `clean_semantic`, the corrected law re-run of the
`korenmarkt_semantic` pass this section was first written from. The last column
is that original pass, kept so a published number can be located. The isotropic
row is identical in both, as it must be.

The illumination model matters more than the position does. Under isotropic
illumination, standing anywhere in one square changes exposure by 3.5 dB. Under
rooftop macro sites it changes by 8.2 dB and under street small cells by 16.6 dB,
because those sources arrive in narrow elevation bands that the surrounding built
form either admits or blocks completely, and a location either sees the sky in
that band or it does not. The correction narrowed both directional rows and did
not touch the ordering.

Any population exposure claim therefore depends on the assumed source geometry far
more than on where in a square people actually stand, which is a result about how
such claims should be framed rather than about Ghent.

Carried through to the body, which is the point of the whole pipeline, the same
120 locations give a peak absorbed power density spanning **7.8 dB** and a whole
body SAR spanning **8.6 dB**, both at a reference incident density of 1 W/m2 and
both under rooftop illumination. Under the superseded law those were 12.7 and
13.0 dB. So the dosimetric endpoint inherits the illumination geometry's spread
rather than the scene's average openness, which is 3.5 dB.

**The two directional rows are upper bounds, not values.** The crop sweep below
shows their absolute level is set by how far the scene extends, and at the 130 m
radius used here the rooftop susceptibility is 3.24 dB high under the superseded
law and **1.09 dB** high under the corrected one. The isotropic row carries no
such caveat, and the spread within a row, which is what the paragraph above is
about, is far less affected than the level.

### The finding hiding in the manifest

A second run bound the semantic posterior in as the material source, over 120
locations. Its manifest reports the area fraction carrying each class, and that
is the number to read:

**The semantic classes together cover about 3 percent of scene area.** Brick 2.53
percent, marble 0.22, metal 0.15, asphalt 0.10, concrete and glass essentially
zero. The geometric fallback covers the other 97 percent.

That is not a defect, it is the coverage result arriving from the other direction.
One panorama binds material on 3.13 percent of scene area, the ladder's second
rung below, so a single capture twin can only bind materials from evidence on a
few percent of the surface and must guess the rest from surface orientation. That
is lower than the 6.9 percent it is a first hit on, because the semantic stage
also drops any pose whose skyline residual exceeds 4 degrees and any face whose
island assignment is ambiguous. Which means the two runs do not compare
geometric materials against semantic ones. They compare a 97 percent geometric
scene against a 97 percent geometric scene, and any difference between them is the
effect of 3 percent of the surface.

### The experiment, and its first answer

Vary the fraction of the scene carrying image evidence, hold everything else
fixed, and measure how far the exposure distribution moves. All three runs are
120 locations on the same walk with the same seed, and the zero evidence rung is
the honest baseline where every material comes from surface orientation.

| evidence by area | source | rooftop median | shift from zero | locations moving over 1 dB |
|---|---|---|---|---|
| 0 % | orientation rule only | 0.1377 | | |
| 3.13 % | one registered panorama | 0.1380 | **0.008 dB** | **0 of 120** |
| 10.57 % | eight stations, fused | 0.1472 | **0.289 dB** | **1 of 120** |
| 11.02 % | nine stations, the sky conflict gate | 0.1475 | **0.298 dB** | **1 of 120** |

The fourth rung was added by the audit of section 3.2.1's sky conflict test,
which readmits one station the 4 degree residual gate had rejected. The gate
therefore raises the top of the ladder rather than eroding it.

**Going from no image evidence at all to a tenth of the scene bound by it moves
the median by 0.29 dB and moves exactly one location out of 120 by more than a
decibel.** A single panorama is worth 0.008 dB, which is nothing.

Those rooftop medians are the superseded law. Under the corrected law the same
ladder reads 0.2165, 0.2239 and 0.2354, a 0.36 dB shift, and the count of
standpoints moving over a decibel goes from 1 to **8 of 120**. The distribution
level conclusion survives the correction and the per standpoint one is weaker
than it looked, and weaker still under isotropic illumination, where 17 of 120
move over a decibel against a distribution only 3.4 dB wide. The median claim
should be quoted, the per standpoint claim should not be quoted as a null.

So the answer is a clean negative, and it reframes what this project should claim.
Not that semantic materials make exposure right, but that **the geometry sets the
distribution, and the semantic layer earns its place through occlusion handling,
evidence confidence and cross capture validation rather than by moving the
exposure number**. That is both more defensible and more falsifiable than the
claim it replaces.

**The reason it is a strong result rather than a null one** is that the semantics
and the orientation prior do not agree. They **disagree on 51 percent of the area
they both cover**, and the exposure distribution still does not move. So this is
not a case of two methods producing the same materials. It is a case of materials
mattering less than geometry over the range that street level capture can reach.

One limit stands. The ladder spans 0 to 10.6 percent, which is as far as street
level capture reaches, and it licenses nothing about a fully evidence bound scene
because no such scene exists here. The saturation work says one cannot be built
from the street: roofs, courtyards and rear elevations are 55 percent of the
surface and no panorama count reaches them.

## Eleven cities compared

**Superseded on 2026-08-03. Do not quote this section.** Everything below is the
`city250_corrected_*` run, whose ground datum estimator put the Krakow and
Toulouse standpoints on the roof of the Cloth Hall and of the Capitole, and which
ran at a bounce budget of four. The replacement is `city250_L3_*`, audited in
`AGGREGATE_REBUILD.md` and tabulated in `PAPER_METHODS.md` section 9.2. Every
headline number in this section moved: the between city spread is 3.71 dB
isotropic, 4.93 dB rooftop and 9.58 dB street small cell, the largest within city
spread is 6.46 dB isotropic at Madrid and 12.89 dB rooftop at Brussels, and
Mexico City Zocalo rather than Krakow is the most exposed square. The section is
kept as written because it is the record of what was believed on 2 August.

80 walk locations per city at 15 GHz, one common 250 m crop radius where the
directional illumination models converge, one common material treatment, so what
varies between rows is urban form and nothing else.

| site | isotropic median | within-city spread | rooftop median | rooftop spread | rooftop median, superseded |
|---|---|---|---|---|---|
| Rynek Glowny, Krakow | 0.5304 | 0.77 dB | 0.9001 | 2.26 dB | 0.7052 |
| Place du Capitole, Toulouse | 0.3992 | 2.31 dB | 0.3383 | 5.30 dB | 0.0981 |
| Zocalo, Mexico City | 0.3974 | 2.14 dB | 0.2990 | 4.39 dB | 0.0816 |
| Trafalgar Square, London | 0.3894 | 3.54 dB | 0.2868 | 3.07 dB | 0.0767 |
| Staromestske, Prague | 0.3626 | 4.33 dB | 0.2357 | 5.86 dB | 0.0631 |
| Piazza del Duomo, Milan | 0.3538 | 2.73 dB | 0.2477 | 2.51 dB | 0.0799 |
| Plaza Mayor, Madrid | 0.3473 | **6.15 dB** | 0.1462 | 8.38 dB | 0.0341 |
| Korenmarkt, Ghent | 0.2917 | 2.85 dB | 0.1627 | 6.39 dB | 0.0483 |
| Grand-Place, Brussels | 0.2351 | 5.96 dB | 0.0976 | **13.29 dB** | 0.0251 |
| Hachiko, Tokyo | 0.2238 | 3.42 dB | 0.1009 | 6.98 dB | 0.0363 |
| Times Square, New York | 0.1629 | 3.67 dB | 0.1294 | 6.34 dB | 0.0924 |

The rooftop columns are the corrected law, the `city250_corrected_*` tags. The
last column is the superseded law on the same standpoints, kept so a number
published before 2026-08-02 can be located. The isotropic column is common to
both.

**Across eleven cities the median susceptibility spans 5.13 dB isotropic and
9.65 dB rooftop, against 14.49 dB rooftop under the superseded law. The largest
spread within a single square is 6.15 dB isotropic and 13.29 dB rooftop.**

So under isotropic illumination the variation inside one square **exceeds** the
variation between eleven cities on three continents, and under rooftop
illumination the two are comparable. A per city or per country exposure figure
therefore averages over a variation at least as large as the differences it is
trying to report, which is a result about how such figures should be framed rather
than about any of these cities.

The ordering is not simply built density. Krakow's wide open Rynek runs highest
and most uniform, 0.53 with only 0.77 dB of spread. Brussels' Grand-Place is both
low and highly variable because a walk there passes from an enclosed square into
the narrow streets feeding it. Times Square is lowest on isotropic, at 0.16 with
a median sky fraction of 11 percent, and it is the one site the law correction
moves in the ranking: third of eleven on rooftop under the superseded law and
ninth under the corrected one. Its towers block the horizon while leaving the
high elevations comparatively open, so it gained least from a correction that
moves weight up off the horizon.

**Krakow and Toulouse are the two rows not to quote.** Their ground datum sits
18.19 and 13.94 m above the surrounding pavement, which puts their standpoints on
the roof of the Sukiennice and of the Capitole rather than in the square. The
estimator took the median first hit over a 15 m disc at the crop centre, and at
both sites the centre of the square is a building. `GROUND_DATUM.md` carries the
fix and the eleven measured datums, nine of which move by less than a quarter of
a metre. Both rows are invalid pending the requalified run, and the remaining
nine are unaffected. Krakow leading the table is that defect and not its
openness.

## The crop radius, and the rule I got wrong about it

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
**+9.93 dB**. Source
`outputs/crop_convergence/korenmarkt_crop_convergence.json`, 32 observers.

**The two directional columns are the superseded law and this sweep has not been
re-run.** What has been remeasured is the 130 m to 250 m step at Korenmarkt, on
the 80 city standpoints rather than these 32 observers and against the 250 m mesh
rather than the 340 m one. That step falls from 4.58 to 1.09 dB rooftop and from
11.37 to 8.21 dB street under the corrected law. The isotropic column is
unaffected. The conclusion is unchanged in direction and in which model binds:
250 m is still the requirement, now set by the street model alone.

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
one step reads the wrong way. Every step from 130 m upward is like for like. And
the 250 m and wider crops come from a second, larger fetch, so a 200 m crop
rebuilt from it was compared against the original: 390,518 triangles from both, so
the step at 200 to 250 m is physics rather than acquisition.

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
orders on a floor near -42.0 dB, flat within 1.3 dB from -30 to -68 degrees,
where the screen falls to -68.2 dB. It is not
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
repeats at one angle span a factor of 4.3 to 8.4 in amplitude on brick at 5 to 30
degrees, with sample standard deviations 61 to 101 percent of the means, the
brick and limestone clouds overlap
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

## Acquiring the cities

Twenty four candidate squares were screened before any acquisition spend, in
**4,091 metadata requests and 109 seconds with zero tiles fetched**. Screening
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

| site | fetched | segmented at 1536 | registered | median residual | status |
|---|---|---|---|---|---|
| Staromestske namesti, Prague | 14 | 14 | 14 | 0.82 deg | complete |
| Plaza de la Constitucion, Mexico City | 14 | 14 | 14 | 2.76 deg | complete |
| Plaza Mayor, Madrid | 10 | 10 | 10 | 0.40 deg | partial, quota |
| Grand Place, Brussels | 14 | 14 | 14 | 2.87 deg | complete |
| Times Square, New York | 14 | 14 | 14 | **10.13 deg** | rejected, mesh |
| Hachiko, Tokyo | 13 | 13 | 0 | none | rejected, wrong walk |

The second cohort of three went out on the next day's quota, 13,540 requests, no
throttle. One of the three is usable and the two failures are the interesting
part, because neither is a panorama problem.

**Times Square registers an order of magnitude worse than anything else**, and
the cause is the mesh described above rather than the capture. Three
explanations were tested and two cleared: widening the crop from 130 to 250 m
moves it 0.06 degrees, so it is not the crop truncation that explains the
Zocalo, and its median observed skyline elevation is 14.8 degrees against 15.3
at Brussels and 15.7 at Madrid, so it is not a high elevation canyon regime.
What remains is the degeneracy `align_skyline` documents against itself: a
roofline too low by `d` and a camera too high by `d` are indistinguishable, so a
wrong silhouette is paid for by sinking the camera. Widening the altitude bound
to plus or minus 25 m buys residual monotonically, all the way to a camera
20 m below the street, and no interior optimum exists. Signed residual medians
of -0.05 and 0.20 degrees against a 10 to 12 degree mean absolute say the
silhouette is wrong bin by bin, which is what a broken mesh looks like and not
what a mispointed camera looks like.

**Hachiko square was never above ground.** All thirteen panoramas see between
0.00 and 0.03 percent sky, so the skyline objective had nothing to fit and every
one returned zero structurally supported samples. The entity histogram is 68
percent building, 5.6 percent rail track, 1.4 percent tunnel, and a thumbnail
settles it: this is the Shibuya subway platform, with the station signage and the
DT01 and Z01 line markers in frame. The screening chose it because a walk is the
largest set of panoramas sharing a capture date and linked to each other, and
Google's indoor mapping of Shibuya Station has 183 linked panoramas on one date
against 18 on the next best. **At a transit hub that definition selects the
station over the street.** Nothing downstream caught it because pose altitude
comes from a downward cast against the street level mesh, so all thirteen
cameras were placed at street level plus 2.5 m while the real camera was a floor
below ground. Cost 4,408 requests, and looking at one panorama would have shown
it. Recoverable from the 2023-09 walk, 18 panoramas, about 6,100 requests.

Madrid's ten are the most spread ten of its fourteen rather than an arbitrary
prefix, because farthest-point sampling is prefix optimal. Its extent is identical
to the full set and only the minimum separation differs, 30.2 m against 21.7, so
Madrid lost density rather than reach. Its tenth pose landed after
`outputs/city_screening/panorama_registration.json` was written, which is why that
file and several earlier drafts say nine.

Registration quality varies more than I first reported. I read the first few poses
and quoted 0.28 to 1.49 degrees, which was optimistic. The actual medians are
0.40 at Madrid, 0.82 at Prague and **2.76 at the Zocalo**, with a worst case of
9.33. The two existing references are Milan at 0.74 and Korenmarkt at 1.31,
taken from `skyline_score_mean_deg` in each site's shipped `pose_aligned.json`,
so Madrid and Prague are comparable to them rather than clearly better. The
Zocalo is not. The 1.05 and 2.83 quoted in earlier drafts are a superseded pair.

One genuine improvement: **eleven of thirty-eight poses landed on the altitude
search bound and twenty-seven did not.** Every pose previously shipped in this repository
had that defect, so a majority free of it is new.

I ran a quality pass over every one of them, because a cross city distribution is
only as good as its worst site and a bad site fails quietly rather than loudly.
All ten have zero degenerate faces, zero duplicate index triples and a consistent
260 by 260 m extent, and the ground altitudes independently check out against real
city elevations, including New York at -18 m, which is right once the roughly
-32 m geoid separation there is accounted for.

**I passed Times Square on that quality check and should not have.** I read its
428 m of vertical extent as right for a site with 226 m of tower above the
street, and the
arithmetic works only because two errors of opposite sign were added together.
The mesh runs from -220.3 m to +207.2 m against a camera at -19.0 m, so **2.87
percent of its vertices sit more than 30 m below street level**. Grand Place and
Prague have exactly zero. Times Square is mirror glass and animated LED
billboards, which is the worst case there is for multi view stereo, and the
reconstruction answered with two hundred metres of geometry underneath the
street. The check I ran compared a total against an expectation, and a total
cannot see a cancellation. Comparing the floor against the camera would have
caught it and now does.

Its exposure numbers in the table above are computed against that mesh, so the
next question is whether they survive it. **Measured rather than argued, they
do.** `run_substreet_ablation.py` traces the same forty standpoints twice, once
against the mesh as built and once with every face lying wholly below eight
metres under the ground datum removed, which is 38,354 faces or 3.60 percent of
the site.

| quantity | as built | culled | median shift | worst location |
|---|---|---|---|---|
| isotropic | 0.16433 | 0.16438 | +0.0013 dB | 0.012 dB |
| rooftop | 0.09341 | 0.09398 | +0.0263 dB | 0.235 dB |
| street small cells | 0.03663 | 0.03703 | +0.0473 dB | 0.168 dB |
| sky fraction | 0.11455 | 0.11455 | 0.0000 dB | 0.0007 dB |

Those are the superseded illumination law, and the conclusion does not depend on
it: the largest shift anywhere in the table is 0.24 dB, which is two orders of
magnitude below the 5 dB the law correction itself moves the rooftop median. The
same ablation was run at Grand-Place, where 0.43 percent of faces lie below the
floor, and the shifts there are smaller still, at most 0.30 dB at one standpoint
under the street model.
`outputs/substreet_ablation/newyork_timessquare_substreet.json` and
`brussels_grandplace_substreet.json`.

Not one of the forty standpoints moves by half a decibel under any model. The
sign is worth reading too: every shift is positive, meaning the spurious
geometry was absorbing a little power that should have escaped, which is exactly
what a surface below the observer does and it is two orders of magnitude below
anything this study reports. **Times Square stays in the cross city table and is
rejected only for registration**, where the same geometry is fatal because the
skyline objective pays for a wrong silhouette by sinking the camera. A mesh can
be too broken to align a photograph against and good enough to trace, and this
one is both.

The cull removes faces wholly below the floor rather than any face crossing it,
because a facade that reaches down through the street is real geometry with a
bad tail, and dropping it would open a hole in the road and change the answer
for a reason unrelated to the defect being measured.

**One site failed on the anchor.** At the Toulouse anchor a standing observer sees 6.9 percent
sky. Twenty metres east it is 47.6 percent, and the ground steps from 191.1 to
211.1 m over that distance, which is a roofline rather than a slope. The anchor
is on the Capitole building instead of the square in front of it. Since tiles are
cached per tile, re-cropping at a corrected centre costs almost nothing.

The general form of that check is worth keeping for the remaining cities: cast a
full sphere from 1.5 m above the ground under the nominal anchor and reject any
site below about 0.10 sky, then sample a few points 20 to 30 m out to confirm the
anchor is not on a local high. The healthy range across the other sites is 0.179
at Times Square, a genuine canyon, up to 0.462 at Krakow, in
`outputs/city_gallery/metrics.json`. Toulouse at 0.069 is the only site below the
gate. Note that this is a single cast at one point and not the walk median sky
fraction the exposure runs report, which is lower everywhere.

## Things that were wrong

**I passed Times Square's mesh on a quality check that could not have caught the
defect.** I compared its total vertical extent against an expectation, and a
total cannot see a cancellation of two errors with opposite signs. That is
written up in full above. The general lesson is worth keeping separate from the
site: a check on an aggregate is not a check on the thing the aggregate is made
of, and the fix is to compare the floor against the camera rather than the span
against a guess.

**I reported a cache defect that does not exist and had to withdraw it.** A
subagent found that the segmentation view cache keys on model, checkpoint and
sizes but not on `--output-width`, and concluded the shipped 57 to 66 second
per panorama figures were warm re-runs over a stale cache. I passed that on
before checking it. The log settles it: 37 distinct panoramas, 37 result lines,
one pass from 23:48 to 00:31, no cache or skip line anywhere, times spanning
56.5 to 118.9 seconds. Those are cold numbers. The cache key omission is real as
code and harmless in effect. The subagent retracted it unprompted, which is the
behaviour to want, and I should have verified before repeating it rather than
after.

**A tile cost I stated as a constant is not one.** I wrote that a zoom 5
panorama is 338 tiles and the daily cap is therefore 44 panoramas. That is true
of one capture width. Across the six sites acquired it runs 128 to 512 tiles, so
a day buys between 29 and 117. Had the second cohort all been at the top of that
range it would have been 21,000 requests against a 15,000 cap.

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

**I proposed a crop radius rule and it was wrong.** That the crop must reach the
farthest source read beautifully on the rooftop model, which reaches 250 m and
converges at 250. The street small cell model reaches 150 m and converges later,
which kills it. The coincidence was a coincidence.

**I then declared the surviving mechanism unexplained, on my own bad
arithmetic.** I read a 2.3 percent share of the illumination measure as a
fractional loss and concluded blocking was short by a factor of thirty. It is an
absolute addition to a small number: against a converged rooftop susceptibility of
0.043, that share is 1.2 dB, not 0.1. Decomposed properly the effect is 69 to 77
percent blocking and the rest redistribution, with no residual.

**Numbers from before and after the illumination law correction coexisted in this
file without labels.** An audit on 2026-08-02 traced every quantity of
consequence back to the file in `outputs/` that produced it. Six were wrong
rather than merely unlabelled: the between-city rooftop spread was 14.49 dB where
the corrected law gives 9.65, the per site law shift was 0.98 to 6.30 dB where it
is 1.06 to 6.33, the rooftop over isotropic range was 11.37 dB where it is 11.32,
the cross site crop correction was said to cover nine cities where it covers ten,
the ground datum was 18.19 and 13.94 m too high at Krakow and Toulouse, and the
single panorama coverage pair was quoted on one denominator against a fused
number on another. Four more were quoted from runs that have since been
overwritten and no longer reproduce: the 0.2599 sky fraction identity, the 1.956
square metre body area, the 0.29894 bounce convergence trio and the 0.24596 ray
count pair. Those are now stated as withdrawn rather than left standing, which is
the only honest thing to do with a number whose file is gone.

**That audit's own replacement for the first item has since been superseded.**
The 9.65 dB is the corrected law on the superseded ground datum. With the datum
fixed and the sweep retraced at three bounces the between city rooftop spread is
4.93 dB, per `AGGREGATE_REBUILD.md`. The lesson the paragraph above draws is
unchanged and is now demonstrated twice.

**A published figure was built from a partial aggregate.** `16_eleven_cities`
was copied out of an aggregate a concurrent run was still writing, so its
Brussels curve carries 3 locations against the 80 every per site record holds.
The legend says so, `brussels grandplace (3)`, and it went unread. Three of the
shipped figures were marked stale in `FIGURES/README.md` for that or for the
superseded law, and `16_eleven_cities` was rebuilt from `city250_L3_*` on
2026-08-03 behind a guard that refuses a ragged aggregate.

**I duplicated an acquisition that was already running**, costing about 9,000
redundant tile requests, because I told an agent not to start something it had
already started and did not check before launching my own.

**I ran a regression test into the live output directory** and overwrote two
shipped figures at draft resolution. Recoverable only because `FIGURES/` held
full resolution copies.

**I misread registration quality from the first few poses**, quoting 0.28 to 1.49
degrees where the site medians are 0.40, 0.82 and 2.76 with a worst case of 9.33.

## Seeing the propagation, rather than reading it

Four Blender files, one per site, at `outputs/propagation_viz/`. Korenmarkt as
the reference, Krakow as the most open square in the set, Times Square as the
canyon and Grand Place as the widest spread inside a single square. They span
the measured range rather than represent it, because four sites cannot
represent eleven.

**Superseded on 2026-08-03 as to the choice of Krakow.** These blends were built
on the old ground datum, which had the Krakow walk on the Cloth Hall roof at a
0.4456 sky fraction. At street level Krakow reads 0.3138 and is third of the
eleven behind London Trafalgar at 0.3304 and Mexico City Zocalo at 0.3240. The
blends have not been rebuilt.

Each carries six collections: the support mesh tinted by the surface class that
chose its material, the recorded ray paths, the angular power spectrum at one
standpoint, the illumination model's sources at true range and height, every
traced standpoint coloured by susceptibility, and the duke phantom coloured by
absorbed power density. No textures, no packed images, vertex colours only,
compressed. Between 5.6 and 7.6 MB each and 27 MB for all four zipped, against
roughly 150 MB for one textured showcase blend of the same square.

**The rays in the file are the rays the estimator integrated.** A new
`PathRecorder` keeps the polyline of a capped number of them, and it is a
passive observer: it consumes no random draw and touches no accumulator, so a
traced result is bit identical with it attached and without it, which
`tests/test_propagation.py` asserts rather than assumes. Nothing about the
storage rule changes, because the capacity is set at the call site, the
production runs do not enable it, and no path table reaches disk.

The paths are sorted into five exclusive bundles, and the split is what makes
the picture worth looking at. A ray either left the scene or died in it, and if
it left, it either left into the elevation band a directional model illuminates
from or it did not. **An escape outside the band contributes nothing under that
model no matter how far the ray travelled**, so the orange and pale yellow
bundles are the ones carrying rooftop power and the blue cone going straight up
is carrying none of it.

Three things in those files are drawn rather than measured, and all three are
recorded as custom properties on the object that carries them. The arrival lobe
is normalised by its own peak, because the three models differ by two orders of
magnitude in level and drawing that faithfully leaves two of them invisible. It
has a radius floor, because a directional model's true lobe is a pancake a few
centimetres thick at this scale. And it is drawn thirteen metres above the
standpoint, or it would enclose the phantom standing there.

One thing had to be measured to make the figures work at all. Camera offsets
that frame a square with fifteen metre eaves put the camera inside a tower at
Times Square, so each camera now casts towards its subject and stops short of
whatever it hits. A camera that ends up very close is a result about the site
rather than a failure.

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
python run_exposure.py --site korenmarkt --crop-m 250 --max-bounces 4 \
       --tag-suffix _corrected                            # figure 14
python run_masonry_grating.py && python run_masonry_spectrum.py
python run_foliage_study.py                               # figure 12
python remesh_support_mesh.py                             # the mesh study meshes
python build_propagation_blends.py                        # the four walkthrough blends
python run_substreet_ablation.py --site newyork_timessquare
python run_exposure.py --all-sites --locations 80 --crop-m 250 \
       --max-bounces 4 --tag-suffix _corrected            # the eleven city table
python run_exposure.py --validate                         # the closed form checks
python run_crop_convergence.py                            # the nine radius sweep
```

Two defaults do not match the runs above. `run_exposure.py` defaults to a 130 m
crop and to six surface interactions, so the corrected eleven city table needs
`--crop-m 250 --max-bounces 4` stated explicitly, and the tag suffix is what
keeps the two laws' outputs apart in `outputs/exposure_korenmarkt/`.

The two showcase blends carry one named camera per shipped figure, so switching
camera in Blender reproduces a figure rather than approximating it.
`korenmarkt_mesh_study.blend` carries the three candidate support meshes as
separate collections plus both the pedestrian crop camera and the orbit camera
that figure 10 uses.

The suite was 700 passing and 1 skipped at the end of the night, up from 570 at
its start. As of the 2026-08-02 audit it collects 798, of which 790 pass, 1 is
skipped and 7 fail on this machine for want of Blender's `mathutils`, which is
an environment gap rather than a result. It is still growing, so treat any count
in this file as a timestamp rather than a property.

## Still open

- **Section 2.7 stated two illumination models and called them one, and this is
  now fixed in the code.** The `1/sin^3` elevation law was derived for sources at
  a **fixed** height above head, and the support was then stated using the
  extremes of a height band and a range band. Sampling those bands literally gave
  an elevation distribution off the stated law by a factor of 22, which is how it
  surfaced: it had to be sampled to place source markers in the blends. The
  corrected law integrates an admissible height window under both the height and
  the range cap. `MONOSTATIC_SBR.md` section 2.7.1 carries the derivation and
  `semantic_twin/propagation/directions.py` the implementation. What remains open
  is the re-running: the eleven city sweep and the Korenmarkt walk are done, the
  nine radius crop sweep and the cross site crop correction are not.
- **Tokyo needs re-screening from the street.** The walk definition selects the
  largest set of same-date linked panoramas, and at a transit hub that is the
  station. Screening should require a minimum sky fraction on the panorama
  itself, which is one cheap check on data already fetched, and the same rule
  would have caught it before the 4,408 requests were spent.
- **Times Square needs a mesh, not more panoramas.** Its 14 panoramas are
  fetched and segmented and its poses are unusable, and neither is fixable by
  fetching more. Options are an independent source of geometry for that block,
  or accepting the site as trace-only, which the sub street ablation says costs
  nothing at all on the exposure side.
- **The brickwork model is unvalidated at FR2.** It is validated at 4 GHz to
  2.0 dB with nothing fitted, and the only FR2 measurement available cannot
  adjudicate because its own repeat scatter exceeds the disagreement.
- **Vegetation now routes to the vacuum row rather than wood**, which removes the
  72 dB of invented reflection but is still not right: a vacuum row face absorbs
  where a canopy should partly transmit. The correct treatment is the participating
  medium, which needs a twenty line medium boundary hook in the tracer, already
  specified by the foliage work.
- **The two level scheme.** The 250 m re-run is done, under both laws, but it
  traces the wide crop throughout. Keeping the narrow crop as the scattering and
  semantics mesh and using the wide one only as an occlusion shell is the scheme
  the roadmap anticipated and which the sweep has now sized, and it is unbuilt.
- **The ground datum was wrong at Krakow and Toulouse**, by 18.19 and 13.94 m,
  which put both walks on a roof. Fixed in `walk.py` and documented in
  `GROUND_DATUM.md`, with the requalified exposure run still to land. Every
  eleven city rooftop and isotropic number for those two sites is invalid until
  it does.
- **An unresolved sky fraction disagreement.** `MONOSTATIC_SBR.md` section 7.5
  records 0.2271 at the panorama camera. Two independent code paths now give
  0.2464, and no crop radius or camera height reproduces the recorded value. One
  of the two is wrong and it is not yet known which.
- **A sampling design rather than a walk**, if any within-square figure is to be
  area representative. A contiguous split half of one site's locations gives a KS
  statistic of 0.53 with medians a factor of 2.7 apart.
- **Whether the grazing-weight explanation survives a second site.** It ordered
  the three illumination models correctly at Korenmarkt after the source-range
  rule failed, but one site is one site, and Times Square at 18 percent sky should
  stress it hardest.
- Panoramas for the acquired cities. Nine sites have geometry and none have
  panoramas, so eight of eleven are geometry only. Sizing measured rather than
  estimated: roughly 43,000 requests for 16 panoramas across 8 sites.
- Toulouse needs re-cropping onto the square rather than the Capitole roof.
- Housekeeping: the 250 m shells exist twice, as `inhouse_leaf_250m.ply` and
  `inhouse_leaf_250m_f64.ply`, because the acquisition agent and I built them
  independently before my message to stop reached it. They are byte identical and
  one set should be deleted. That duplication also cost about 9,000 redundant tile
  requests, which is my error: I should have checked what was already running
  before starting.
- Milan's two registration objectives still disagree on horizontal position by
  2.5 m against a 0.21 m seed spread, and a 0.33 m systematic between depth
  derived and skyline derived altitude, same sign at both sites, is unexplained.
