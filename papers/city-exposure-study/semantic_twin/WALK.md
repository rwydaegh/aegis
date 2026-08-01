# Many panoramas per site

A record of the first fusion of a *walk* of panoramas at Korenmarkt, what it
measurably bought, and which of the three promised numbers is actually in hand.

Code: `semantic_twin/walk.py`, `build_walk_twin.py`, `tests/test_walk.py`.
Outputs: `outputs/walk_korenmarkt/`. Images: `data/panoramas/korenmarkt_walk/`.

## The bounding-box endpoint silently returns a sample

This is a methods result, not a footnote, and it is the one most likely to
quietly corrupt somebody else's panorama study. Anyone selecting street-level
imagery for a site does the obvious thing and queries a bounding box. The
bounding box does not return what is in the box.

**Measured at Korenmarkt.** A single `GET https://graph.mapillary.com/images`
with `bbox` covering roughly 200 m around 51.055 N, 3.722 E, `limit=100`,
returned **43 images in total**, of which **2** belonged to sequence
`u5WIQvkTXO7SbeL1l8UN6a`. Enumerating that same sequence through
`GET /image_ids?sequence_id=u5WIQvkTXO7SbeL1l8UN6a` returns 135 frames, of which
**13 lie within 60 m of the site centre** and 15 within 70 m.

So the box returned **2 of 13**, about 15 %, and reported no truncation.

The failure mode is what makes this dangerous:

- The response carries **no truncation flag, no paging cursor and no total
  count**. There is nothing in the payload that distinguishes "these are all of
  them" from "here is a sample".
- It is **not** the documented `limit`. The query was capped at 100 and returned
  43, so the cap never bound. Tiling the box into 36 smaller cells raised the
  count to 112 panorama seeds but still did not recover full sequence membership.
- It is **not** a geometry error. The 11 missing frames are inside the box by
  their own published `computed_geometry`.
- The bias is **spatially structured**, not random. Sampling that thins a dense
  drive preferentially removes exactly the tightly spaced frames that a
  multi-view study needs, so a naive study loses its short baselines first and
  never learns that it did.

A study that selects from the box therefore under-counts available imagery by
roughly an order of magnitude at this site, concludes that a site is
single-capture when it is not, and reports a leave-one-panorama-out validation as
impossible when the data for it exists.

**The fix, and it is cheap.** Use the box only to *name* sequences, then expand
each named sequence through `/image_ids?sequence_id=` and fetch metadata by
explicit identifier. The identifier-based endpoints are complete in every case
checked here. Around Korenmarkt this turns 112 panorama seeds into 11 named
sequences, which expand to **1798 linked images**, of which **41 are spherical
captures inside the 60 m site radius** and 87 within 80 m.

Implemented in `semantic_twin/walk.py` as `seed_sequences` (names only) followed
by `traverse` (expands), with the docstring stating why the two counts are not
comparable. Any site screening for the other nine cities should use the same two
steps.

## The walk, and what a sequence is

Mapillary publishes imagery as *sequences*, the ordered frames of one continuous
drive or ride, and the sequence is the only officially linked structure the
provider exposes. Only linked captures form a walk, so the sequence is both the
unit of traversal and the unit of capture independence: two frames of one
sequence share a camera, a day, a weather condition and an exposure setting,
while two frames of different sequences share none of those.

## The walk that was selected

Twelve stations, thinned to an 8 m separation floor, capped at six per sequence so
one dense drive could not fill the walk.

| | |
|---|---|
| stations | 12 |
| sequences | 3 |
| capture days | 2022-04-03, 2025-03-03, 2025-04-28 |
| range from site centre | 2.7 to 37.2 m, median 21.5 m |
| camera-to-camera baseline | 8.2 to 56.0 m, median 27.8 m |
| nearest-neighbour baseline | 8.2 m min, 8.6 m median |
| convex hull of camera centres | 1417 m² |
| extent | 45.4 m east by 55.2 m north |

Three capture days three years apart is the part that matters. It is what makes a
cross-capture comparison possible at all, and it is the first time this project
has had one.

Every station carries a measured gravity tilt from `computed_rotation`; the
selector refuses a panorama without one rather than assuming a level camera.
Measured tilts in this walk run to **20.7 degrees** off gravity.

## What fusion bought: directly observed surface

Full-sphere first-hit cast, 1536 x 3072 rays per station, against the 157,862
triangle `inhouse_leaf_130m_f64` support mesh.

A useful property fell out of the geometry: **the set of faces a panorama can see
depends on where the camera is, not on how it is turned**, because a full sphere
has no outside. So this curve needs the position only. It does not wait on the
skyline registration and does not inherit its orientation covariance.

### Quote the area fraction, not the face count

The two denominators do not behave the same way under resampling and only one of
them is a stable number.

**Area is nearly ray-density independent. Face count is not.** Whether a sliver
triangle is ever hit at all depends on how finely the sphere is sampled, so
raising the ray count finds more small faces and inflates the count fraction
while barely moving the area fraction. An independent recount at a different ray
density and with a different caster agreed to **1.2 % relative on single-capture
area and 2.8 % on fused area**, but differed by **8.8 % and 7.6 % on the
corresponding face counts**. That is the right way round and is a property of the
metric, not a disagreement about the geometry.

So the area fraction is the headline here, and the face count is reported beside
it as the density-dependent one. A reader re-running at a different ray count
should expect the counts to move and the areas not to.

**Mesh matters too.** All numbers below trace against
`inhouse_leaf_130m_f64.ply`, the double-precision tile placement the rest of the
study uses. The single-precision `inhouse_leaf_130m.ply` displaces whole tiles by
up to 0.61 m and reports a fused area fraction about **4.6 % relative higher**,
so the mesh choice is a real bias in the optimistic direction. `build_walk_twin.py`
defaults to the f64 mesh rather than to the scene's declared `source_mesh`.

### On camera altitude, which can fail silently in both directions

Station altitude is taken from a **downward ray cast under the camera with a
patch median** over 25 samples in a 3 m patch, not from the highest hit in the
column. The distinction is load bearing. Where photogrammetry bridges a street
with a spurious membrane, or where the 3 m patch straddles a facade, a maximum
puts the camera on the roof, and a camera on a roof sees a completely different
and much larger set of faces. Two of the twelve stations here have a ground
sample peak-to-peak of **4.8 m** inside their patch, so they would have been
placed metres too high by a maximum. The median rejects it.

Audited against the scene's own ground constant, all twelve stations land between
**-0.06 m and +1.19 m** of pedestrian level, with no outliers. The failure mode is
worth naming because it is silent in both directions: too high inflates coverage,
too low buries the camera inside geometry and destroys it, and neither raises an
error.

| | by area (headline) | by count (density-dependent) |
|---|---|---|
| single capture (nearest station) | 6.87 % | 4.32 % (6,816 faces) |
| twelve fused | **24.14 %** | 15.87 % (25,054 faces) |

**3.5x by area, 3.7x by face count.**

The curve, which matters more than the endpoint:

| n | area % | count % | n | area % | count % |
|---|---|---|---|---|---|
| 1 | 6.87 | 4.32 | 7 | 19.37 | 12.25 |
| 2 | 14.78 | 8.63 | 8 | 20.33 | 13.21 |
| 3 | 15.91 | 9.53 | 9 | 21.04 | 13.65 |
| 4 | 16.43 | 9.91 | 10 | 22.58 | 14.81 |
| 5 | 18.39 | 11.46 | 11 | 23.72 | 15.54 |
| 6 | 19.04 | 12.04 | 12 | **24.14** | **15.87** |

**At twelve it had not visibly saturated.** The second panorama is worth 7.9
points of area and the twelfth is still worth 0.42, which looked at the time like
a slow linear climb rather than a turnover. That reading was wrong, and the
41-station run below shows why: twelve captures is too few to reach the knee, so
the tail of a twelve-point curve cannot distinguish a plateau from a line.

Note the per-station coverage is nearly flat with range: the station at 2.7 m
sees 4.64 % and the one at 35.1 m sees 7.25 %. A panorama near the middle of an
open square is boxed in by the near facades; one further out sees more surface,
worse. That is why the gain is close to linear rather than front-loaded.

### Coverage is not accuracy, so here is the geometry of the gain

The obvious attack is that a union counts junk: a face caught at a grazing angle
from 80 m is "seen" but is weak evidence. Measured, that attack does not land.

| | median incidence | beyond 70 deg | median range | beyond 40 m |
|---|---|---|---|---|
| single-capture faces | 60.2 deg | 34.1 % | 44.7 m | 54.4 % |
| the 18,238 faces gained | 56.5 deg | 34.0 % | 39.1 m | 48.6 % |
| all fused faces | 53.5 deg | 30.3 % | 37.0 m | 45.5 % |

The newly covered surface is seen at **slightly better** incidence and slightly
closer range than the surface the single capture already had. Fusion is not
padding the count with grazing scraps, and the fused set is better conditioned on
both axes than the baseline it replaces.

**Why later panoramas see better rather than worse**, which is the natural
objection. The mechanism is a min over stations, not an average. A face enters
the union as soon as *one* station first-hits it, and the incidence and range
reported for it are that station's best, not the mean over stations. So the
question is not whether panorama twelve is a good viewpoint in general, it is
whether it is a good viewpoint *for the faces it is the first to reach*. It
usually is, because a face is typically first reached by the station it faces.

The geometric argument is about the hull, not about Korenmarkt. Twelve stations
spread over 1417 m² approach the same facade block from directions separated by
tens of degrees. A wall that is nearly edge-on from one camera is frontal from
another 30 m along the street, and the union keeps the frontal look. A single
capture has no such choice: whatever incidence it happens to have on a surface is
the incidence that surface gets, which is why its median sits at 60.2 degrees,
close to the 60 degrees expected if incidence were near-uniform on a
randomly-oriented sample. Adding viewpoints lets the min over stations pull that
median down toward frontal.

That generalises. The prediction it makes for the other nine sites is that the
incidence improvement should scale with the *angular* spread of the camera hull
as seen from the facades, not with the panorama count, so a dense drive down one
straight street should improve coverage but barely improve incidence, while a few
captures spread around a square should improve both. It also predicts the
improvement saturates once the hull subtends enough angle to supply a frontal
look at every reachable surface, which is a much lower count than coverage
saturation needs. Both are testable with the machinery already written and
neither has been tested yet.

## Where the curve saturates, and what actually bounds it

The twelve-station result left the curve still climbing, so this ran **every**
panorama the link graph offers: 41 within the 60 m site radius and 87 within
80 m, each a full-sphere cast on the f64 mesh. Curves are averaged over 60 random
acquisition orders, because nearest-first is the order most likely to manufacture
an apparent saturation by spending its first captures where surface is densest.

**Within a fixed site radius, coverage saturates hard.**

| n | 60 m radius, area % | 80 m radius, area % |
|---|---|---|
| 1 | 6.11 | 5.47 |
| 5 | 16.75 | 17.95 |
| 10 | 22.35 | 25.85 |
| 12 | 23.52 | 28.16 |
| 15 | 25.23 | 31.15 |
| 20 | 26.80 | 33.56 |
| 25 | 27.95 | 35.43 |
| 30 | 28.76 | 37.12 |
| 41 | **30.58** (all) | 39.79 (at n=40) |
| 87 | | **44.76** (all) |

The marginal panorama collapses. In the 60 m arm the second capture adds 3,938
faces and the last five add **182 each, 4.6 % of the second**. In the 80 m arm the
decay is sharper still, **2.3 %**. This is a genuine turnover, not a slow linear
climb, and it contradicts what the twelve-station curve suggested. Twelve
panoramas was simply too few to see the knee.

**But the ceiling is set by how much street you walk, not by how many captures
you take.** Widening the walk from a 60 m radius to 80 m lifts the achievable
area fraction from **30.6 % to 44.8 %**, a bigger gain than going from 12 to 41
panoramas inside 60 m. Extent buys coverage. Count buys the approach to a ceiling
that extent has already fixed.

So both halves of the coordinator's hypothesis are true, at different scales.
Capture count binds up to roughly 15 to 25 panoramas; past that street geometry
binds, and **no number of panoramas recovers the remaining 55 %**. That residue
is roofs, courtyards, rear elevations and anything with no line of sight to a
public way. It is a structural property of street-level acquisition and it is why
the tile texture layer is not optional.

### The budget number for a per-site acquisition

Reading the 60 m arm, which is the geometry a city site actually has:

| target | panoramas |
|---|---|
| 77 % of achievable coverage | 12 |
| 82 % | 15 |
| **90 %** | **26** |
| 95 % | 33 |

The marginal area gain per panorama falls below 0.5 points at about **n = 15** and
below 0.25 points at about **n = 20**. Against a cost of roughly 55 s of GPU
segmentation plus a skyline registration per panorama, **12 to 16 panoramas per
site is the efficient budget**, and anything above 25 is buying the last tenth at
three times the price. If the choice is between 25 panoramas in a tight radius
and 15 spread over twice the extent, take the extent.

**A single capture is a lottery.** Across random orders the first panorama alone
delivers anywhere from 1.59 % to 6.29 % of faces, a four-fold spread depending on
which capture you happen to get. That spread is the strongest argument in this
document against single-capture twins, and it is invisible unless you resample the
order.

## Registration: twelve poses, twelve covariances, and they are not equal

All twelve panoramas were registered against the mesh skyline with the existing
eight-seed ensemble, and every pose ships the seed-study covariance the
single-capture flow ships. The headline is that **registration quality across a
walk is strongly heterogeneous, and treating the twelve poses as interchangeable
would be wrong.**

| | best | median | worst |
|---|---|---|---|
| skyline residual | 1.08 deg | 3.07 deg | 8.10 deg |
| yaw standard deviation | 0.088 deg | 0.36 deg | 3.89 deg |
| horizontal position sd | 0.018 m | 0.15 m | 0.92 m |

For comparison the single Street View capture registers at 1.31 deg. Only two of
the twelve walk panoramas beat it. Two plausible reasons, not yet separated: the
walk images are 5760 x 2880 against the Street View capture's 16384 x 8192, so
the observed skyline is coarser; and the outer stations sit near the edge of the
130 m mesh crop, where the predicted skyline is truncated by the crop rather than
by the buildings. The residual does correlate with range from the site centre,
which is consistent with the second, but three stations is not a test.

**Five of twelve pushed the altitude search to its bound**, meaning the fit wanted
to move the camera more than 1.5 m vertically. That is flagged in each pose as
`skyline_dz_at_bound` rather than silently accepted.

A useful cross-check fell out of this. Mapillary's structure-from-motion gravity
and the independent skyline fit are separate estimates of the same pitch, and on
the best-registered stations they agree to **0.15 deg**. On the worst they differ
by 5.9 deg. So the residual is not just an aesthetic score, it tracks a quantity
that has an independent witness.

The consequence for fusion is concrete. Coverage is untouched, because it needs
position only. Anything that binds a *pixel* to a face needs orientation, so the
semantic stage below excludes stations with a residual above 4 deg rather than
letting a 3.9 deg yaw uncertainty smear labels across facade boundaries. That
exclusion is a stopgap: the right answer is to feed the covariance into
`ObservationQuality.registration`, which is the second unused field in that
dataclass and is the obvious follow-on to the independence work below.

## The suspicion check: how much of that is double counting

Nothing had ever supplied `ObservationQuality.independence`. It is now computed,
and it says the naive reading of the union is too generous.

Independence is a Kish effective sample size under a kernel in **parallax angle
at the surface**, not in camera baseline. Parallax is the right axis because it
is what actually decorrelates two looks: a 3 m baseline is a 40 degree parallax
on a shopfront 4 m away and under 2 degrees on a gable 90 m away, and one
baseline number cannot describe both. Each station's weight is
`w_a = 1 / sum_b K(theta_ab)` over stations that also see the surface, so two
co-located cameras get 1/2 each and contribute one observation between them.

Over the 25,054 union faces, with a conservative 10 degree decorrelation angle:

- raw looks per face: **3.43**
- effective independent looks per face: **1.92**
- ratio: **0.560**

**Roughly 44 % of the apparent multi-view evidence at this site is redundant.**
A twelve-panorama walk delivers what fewer than seven ideally-placed panoramas
would. The coverage numbers above are a union and are unaffected by this, but any
posterior that counted 3.43 observations where there are 1.92 would be
overconfident by that factor, and the accumulator now has the weight to avoid it.

## What fusion bought: transient occlusion

Eight of the twelve stations, those registering below 4 deg, with pixels bound to
faces through the skyline-registered pose. A face counts as *lost* when it is
reached but fewer than half its rays land on the facade rather than on something
passing in front of it.

| | faces seen | lost to transients | by area |
|---|---|---|---|
| single capture | 6,836 | 881 (**12.9 %**) | 11.5 % |
| eight fused | 11,398 | 472 (**4.1 %**) | 3.6 % |

**Transient occlusion falls by a factor of 3.1, from 12.9 % of observed faces to
4.1 %.** This is the cleanest justification for the whole multi-capture decision:
a person or a van standing in front of a facade in March 2025 is not standing
there in April 2025, and the second capture simply sees through the problem.

Note what does *not* happen: it does not go to zero. 472 faces are occluded in
every station that reaches them, and those are mostly low wall segments behind
parked vehicles and street furniture that is not transient at all on the
timescale between captures. More panoramas from the same three days will not
recover them.

**On the 19.6 % figure this is often compared against.** These are not the same
measurement and should not be quoted against each other. The 19.6 % is transient
pixels against projected support area in one rectilinear crop at yaw 0. The
numbers above are over the full sphere, which includes sky and paving and so
dilutes the denominator, and they are per face rather than per pixel. The
per-view transient *pixel* fraction over the full sphere for these eight stations
has a median of **5.5 %** and a maximum of **28.9 %**, and that spread is the real
point: occupancy at this site varies by a factor of five between captures, so any
single capture is a lottery ticket on how busy the square happened to be.

## Cross-capture agreement, which is the first real validation here

Where two stations both have a clean look at the same face, do they assign it the
same class? Split by whether the two stations come from the same Mapillary
sequence, because same-sequence pairs share a camera, a day, a weather condition
and an exposure setting, and cross-sequence pairs share none of those.

| | pairs | overlap faces | agreement |
|---|---|---|---|
| same sequence | 11 | 34,644 | **84.2 %** |
| cross sequence | 17 | 51,242 | **71.3 %** |

**Independent captures agree 13 points less than frames of one drive.** Range
across pairs is 79 to 89 % within a sequence and 65 to 78 % across sequences, so
the two distributions barely overlap and the gap is not driven by one bad pair.

This is a finding, not a bug, and it is the number that should be believed. Had
the walk been drawn from a single dense drive, as the naive bounding-box
selection would have produced, the measured self-consistency would have been
84 %, and it would have been an overestimate of the twin's reliability by 13
points. **Same-capture agreement is not validation.** It mostly measures whether
the segmentation is deterministic, which it is.

Roughly three faces in ten get a different entity class from an independent
capture. Where that comes from is not yet separated, and the three candidates are
not equally benign: genuine segmentation error, pose error smearing labels across
facade boundaries (the retained stations still span 1.08 to 3.07 deg of skyline
residual), and real change over three years on a commercial square where shopfronts
turn over. The 2022 sequence sits entirely north of the square, so cross-date and
cross-viewpoint are partly confounded in this walk and a clean separation needs
two sequences that overlap spatially.

**This is entity agreement, not material agreement.** The material axis needs the
SAM 3 concept pass, which was skipped for time. Without it, material is a
deterministic function of entity and reporting it would restate the number above
while sounding like an independent result.

## What is not yet in hand

- **Material agreement**, as distinct from the entity agreement above. Needs the
  SAM 3 concept pass over the walk, which is a GPU run of roughly the same size
  as the segmentation already done. This is the version of the cross-validation
  that would bear on RF material assignment rather than on object class.
- **Registration-weighted fusion.** Four stations are currently excluded by a
  hard 4 deg residual threshold. The covariance is already computed for all
  twelve, so the right answer is to feed it into
  `ObservationQuality.registration` and let a poorly registered station
  contribute weakly rather than not at all. That is the same one-line pattern the
  independence weight now uses.
- **Separating the three causes of cross-capture disagreement**: segmentation
  error, pose error, and real change. Needs two spatially overlapping sequences
  from different dates, which this walk does not have.

## Caveats worth carrying

- The walk panoramas are 5760 x 2880 provider originals. The existing
  single-capture Street View panorama is 16384 x 8192. The walk trades per-image
  resolution for viewpoint diversity, and any comparison against the older result
  has to account for that rather than attribute the difference to fusion. It is
  also the leading suspect for why walk stations register worse.
- Every coverage number here is recomputed on `inhouse_leaf_130m_f64.ply` at this
  ray density, so the before and after share a denominator. The single-capture
  baseline is **not** the published 3.3 % headline and must not be quoted against
  it.
- The 2022 sequence sits entirely north of the square, so its cross-date
  comparison only covers north-side facades, and cross-date is partly confounded
  with cross-viewpoint.
- Agreement is measured on the modal non-transient class per face, which is a
  hard assignment. A distributional comparison would be better and the tally is
  already stored in `walk_semantic.npz` to support one.
