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

Full-sphere first-hit cast, 1536 x 3072 rays per station, against the 157,744
triangle `inhouse_leaf_130m` support mesh.

A useful property fell out of the geometry: **the set of faces a panorama can see
depends on where the camera is, not on how it is turned**, because a full sphere
has no outside. So this curve needs the position only. It does not wait on the
skyline registration and does not inherit its orientation covariance.

| | faces | by count | by area |
|---|---|---|---|
| single capture (nearest station) | 7,323 | 4.64 % | 6.86 % |
| twelve fused | 27,014 | **17.13 %** | **24.78 %** |

**3.7x by face count, 3.6x by area.**

The curve, which matters more than the endpoint:

| n | faces | count % | area % | n | faces | count % | area % |
|---|---|---|---|---|---|---|---|
| 1 | 7,323 | 4.64 | 6.86 | 7 | 20,919 | 13.26 | 19.88 |
| 2 | 14,486 | 9.18 | 14.92 | 8 | 22,489 | 14.26 | 20.94 |
| 3 | 16,133 | 10.23 | 16.22 | 9 | 23,261 | 14.75 | 21.70 |
| 4 | 16,894 | 10.71 | 16.95 | 10 | 25,235 | 16.00 | 23.23 |
| 5 | 19,413 | 12.31 | 18.72 | 11 | 26,459 | 16.77 | 24.37 |
| 6 | 20,505 | 13.00 | 19.51 | 12 | **27,014** | **17.13** | **24.78** |

**It has not saturated.** The second panorama is worth 4.5 points of face
coverage, but the twelfth is still worth 0.36 and the eleventh 0.77, and the
increments are not decaying towards zero so much as settling onto a slow linear
climb. Eight panoramas reach 83 % of what twelve reach. Whatever the budget per
city turns out to be, twelve is not the point where more stops paying at this
site, and a walk of 25 to 40 is the experiment that would find that point.

Note the per-station coverage is nearly flat with range: the station at 2.7 m
sees 4.64 % and the one at 35.1 m sees 7.25 %. A panorama near the middle of an
open square is boxed in by the near facades; one further out sees more surface,
worse. That is why the gain is close to linear rather than front-loaded.

### Coverage is not accuracy, so here is the geometry of the gain

The obvious attack is that a union counts junk: a face caught at a grazing angle
from 80 m is "seen" but is weak evidence. Measured, that attack does not land.

| | median incidence | beyond 70 deg | median range | beyond 40 m |
|---|---|---|---|---|
| single-capture faces | 59.6 deg | 33.9 % | 43.7 m | 53.6 % |
| the 19,691 faces gained | 56.2 deg | 33.8 % | 39.8 m | 49.7 % |
| all fused faces | 53.2 deg | 30.3 % | 37.3 m | 46.0 % |

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
the incidence that surface gets, which is why its median sits at 59.6 degrees,
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

Over the 27,014 union faces, with a conservative 10 degree decorrelation angle:

- raw looks per face: **3.38**
- effective independent looks per face: **1.92**
- ratio: **0.567**

**Roughly 43 % of the apparent multi-view evidence at this site is redundant.**
A twelve-panorama walk delivers what fewer than seven ideally-placed panoramas
would. The coverage numbers above are a union and are unaffected by this, but any
posterior that counted 3.38 observations where there are 1.92 would be
overconfident by that factor, and the accumulator now has the weight to avoid it.

## What is not yet in hand

Two of the three promised numbers are still running and are **not** reported here.

- **Transient-object occlusion.** Needs per-station entity segmentation to
  identify transient classes and a registered pose to bind pixels to faces.
  Segmentation of the twelve panoramas is running on the A6000 at ~55 to 75 s
  each with Mask2Former at native 1536. Not finished, so the 19.6 % figure has no
  fused counterpart yet.
- **Cross-capture material agreement.** This is the one worth waiting for. It
  needs registration for all twelve, and the material axis needs the SAM 3
  concept pass, which was skipped in this segmentation run for time. Without it
  the material axis reduces to the deterministic Vistas class prior, and
  "agreement" would then only be testing entity agreement wearing a material
  label. Worth stating plainly rather than shipping the weaker thing as if it
  were the cross-validation.

The walk itself, the poses, and the selection are all on disk, so both are a
resume rather than a restart.

## Caveats worth carrying

- The panoramas are 5760 x 2880 provider originals. The existing single-capture
  Street View panorama is 16384 x 8192. The walk trades per-image resolution for
  viewpoint diversity, and any material comparison against the older result has
  to account for that rather than attribute the difference to fusion.
- Coverage uses `inhouse_leaf_130m.ply` (157,744 faces). The published
  single-capture texture-evidence numbers use `inhouse_leaf_130m_f64.ply`
  (157,862 faces). The 4.64 % baseline above is recomputed on **this** mesh at
  **this** ray density so that the before and after share a denominator. It is
  not the 3.3 % headline number and should not be quoted against it.
- The 2022 sequence sits entirely north of the square, so its cross-date
  comparison will only ever cover north-side facades.
