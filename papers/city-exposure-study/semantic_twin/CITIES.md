# City screening, site selection and acquisition

Phase 6 of `ROADMAP.md`, done on 2026-08-01. Twenty-four candidate squares were screened on Street View
metadata alone before any tile was paid for, ten sites were chosen, and tiles and support meshes were
acquired for all of them at a 130 m radius. The two sites that already exist end to end, Korenmarkt and
Piazza del Duomo, were screened with the rest as the only way to know what the numbers mean.

**Provider.** The official Map Tiles Street View metadata endpoint,
`tile.googleapis.com/v1/streetview/metadata`, and the Map Tiles 3D Tiles endpoint for geometry. Nothing
here touches Mapillary, so the sampled bounding-box defect measured on the Mapillary bbox endpoint,
where a 200 m box returned 2 of 13 frames of a sequence, does not apply, and neither does the 13-point
overstatement of cross-capture agreement that follows from it. This screening never queries a box. It
starts from one panorama and walks the `links` list outwards, which is the same shape as the
sequence-enumeration pattern that fixed the Mapillary path.

**Cost.** Screening: 4091 metadata requests over 24 sites, 79 seconds. Acquisition: 1575 leaf tiles,
3216 tile requests, 156.2 MB over 10 sites, about 3 minutes of wall clock with the ten downloads run
concurrently. Per-site request counts are in the acquisition table and in each site's
`manifest.json`.

## What was measured

`ROADMAP.md` phase 6 asks for coverage with a connected panorama link graph and prefers pedestrianised
squares, where trekker capture puts panoramas where pedestrians actually stand. Everything below is
inside a 60 m disc about the site centre.

**Panorama count and median spacing.** Spacing is the median nearest-neighbour distance. It separates a
trekker walk from a car track, and the screening reproduces the difference measured independently
before this work started: Piazza del Duomo at 2.5 m against Korenmarkt at 10.0 m, against 2.8 m and
10.5 m reported earlier. That agreement is the reason to believe the other twenty-two rows.

**Distinct capture dates.** Every site carries between 5 and 21 of them inside 60 m, and that is not a
bonus. Panoramas link to their neighbours within one capture run and almost never across runs, so a
site with 17 dates is not a site with 17 times the coverage, it is a site whose coverage is cut into
pieces no walk can cross.

**The walk.** The largest set of panoramas that share one capture date and are linked to each other:
one temporally coherent traverse through a scene that agrees with itself about scaffolding, market
stalls and parked vehicles. This, not the panorama count, is the quantity the study samples.

**Azimuth spread, which is the gate.** The fraction of sixteen 22.5-degree sectors about the site centre
that the walk enters, ignoring panoramas within 5 m of the centre whose azimuth is set by position
noise. A dense line driven straight through a square fills two opposite sectors and scores an eighth,
however many panoramas are in it, whereas a walk that goes round the square fills nearly all of them.

This replaced an earlier measure, the fraction of probe points the walk passes within 20 m of, which
was wrong in a way worth recording. Normalising it by what any capture of the site reaches made it
return 1.0 for exactly the case it existed to catch, a 55-panorama line down the middle of a square
against a sparser capture covering the whole of it, because the line reaches every probe point that
lies along it and the normalisation forgave the rest. Azimuth spread cannot be maxed out by a collinear
set. The old measure is still reported as `Coverage` because it says something different and useful,
but it decides nothing.

Spread rather than density is the gate because extent binds harder than count: widening a site from
60 m to 80 m was separately measured to lift achievable surface coverage from 30.6 to 44.8 percent of
scene area, which is worth more than tripling the panorama count inside 60 m.

**Connectivity, checked twice.** A breadth-first walk of the link graph can only ever report the
component it started in, so it can never discover that it missed one. Seventeen probe points, at the
centre and on two rings, are looked up independently, and anything they find that the walk did not
reach is walked in turn. Unlinked user photospheres are counted separately and are not held against a
site: they are abundant in tourist squares, they carry no pose solution, and a walk was never going to
step to them anyway.

**The gate.** The largest single-date component must hold at least nine tenths of that date's
panoramas, and the walk must enter at least three fifths of the azimuth sectors. A fragmented link
graph does not give a worse walk, it gives no walk.

## Screening table

| Rank | Site | Country | Panoramas | Dates | Walk date | Walk panoramas | Median spacing | Span | Azimuth | Coverage | Passes | Newest usable walk | Requests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Plaza de la Constitucion | Mexico | 388 | 8 | 2016-10 | 253 | 1.9 m | 87 m | 100% | 82% | yes | 2021-03, 42 panoramas | 404 |
| 2 | Piazza del Duomo | Italy | 226 | 13 | 2014-09 | 214 | 2.5 m | 119 m | 100% | 94% | yes | none | 268 |
| 3 | Rynek Glowny | Poland | 344 | 11 | 2024-11 | 162 | 2.1 m | 88 m | 81% | 47% | yes | 2024-11, 162 panoramas | 364 |
| 4 | Staromestske namesti | Czechia | 228 | 14 | 2014-06 | 147 | 2.7 m | 117 m | 100% | 82% | yes | 2025-04, 23 panoramas | 248 |
| 5 | Sultanahmet Meydani | Turkey | 157 | 10 | 2015-10 | 146 | 2.7 m | 119 m | 75% | 76% | yes | none | 199 |
| 6 | Trafalgar Square | United Kingdom | 206 | 12 | 2012-08 | 144 | 5.5 m | 112 m | 100% | 100% | yes | 2021-05, 43 panoramas | 238 |
| 7 | Place du Capitole | France | 219 | 10 | 2018-12 | 118 | 2.4 m | 63 m | 81% | 59% | yes | 2020-11, 24 panoramas | 254 |
| 8 | Plaza Mayor | Spain | 97 | 16 | 2025-05 | 56 | 9.0 m | 112 m | 100% | 94% | yes | 2025-05, 56 panoramas | 113 |
| 9 | Grand-Place | Belgium | 110 | 17 | 2024-07 | 45 | 10.0 m | 111 m | 100% | 100% | yes | 2024-07, 45 panoramas | 121 |
| 10 | Placa Reial | Spain | 176 | 16 | 2021-10 | 31 | 9.4 m | 111 m | 75% | 76% | yes | 2021-10, 31 panoramas | 199 |
| 11 | Hachiko square, Shibuya | Japan | 277 | 16 | 2018-05 | 105 | 2.8 m | 118 m | 62% | 56% | no | 2023-09, 18 panoramas | 309 |
| 12 | Federation Square | Australia | 165 | 11 | 2018-07 | 69 | 2.7 m | 53 m | 31% | 40% | no | none | 190 |
| 13 | Trg bana Jelacica | Croatia | 220 | 10 | 2019-04 | 63 | 1.0 m | 32 m | 12% | 12% | no | 2022-12, 47 panoramas | 236 |
| 14 | Times Square | United States | 105 | 14 | 2023-11 | 45 | 3.3 m | 84 m | 44% | 43% | no | 2023-11, 45 panoramas | 128 |
| 15 | Raffles Place | Singapore | 156 | 10 | 2016-04 | 39 | 0.4 m | 7 m | 6% | 13% | no | 2021-10, 20 panoramas | 173 |
| 16 | Greenmarket Square | South Africa | 84 | 8 | 2024-02 | 31 | 2.9 m | 35 m | 12% | 29% | no | 2024-02, 31 panoramas | 100 |
| 17 | Piazza San Marco | Italy | 41 | 14 | 2019-12 | 18 | 1.4 m | 40 m | 19% | 19% | no | none | 44 |
| 18 | Dam | Netherlands | 95 | 21 | 2016-03 | 16 | 0.6 m | 6 m | 12% | 12% | no | 2022-08, 9 panoramas | 111 |
| 19 | Alexanderplatz | Germany | 71 | 12 | 2023-07 | 15 | 10.1 m | 85 m | 44% | 44% | no | 2023-07, 15 panoramas | 89 |
| 20 | Korenmarkt | Belgium | 66 | 9 | 2025-06 | 14 | 10.0 m | 103 m | 50% | 57% | no | 2025-06, 14 panoramas | 86 |
| 21 | Piazza Navona | Italy | 64 | 17 | 2019-09 | 13 | 8.4 m | 110 m | 25% | 38% | no | 2023-10, 11 panoramas | 78 |
| 22 | Kongens Nytorv | Denmark | 40 | 5 | 2024-09 | 11 | 10.1 m | 112 m | 38% | 62% | no | 2024-09, 11 panoramas | 62 |
| 23 | Stephansplatz | Austria | 42 | 14 | 2017-11 | 10 | 11.4 m | 98 m | 38% | 44% | no | 2024-07, 9 panoramas | 56 |
| 24 | Praca do Comercio | Portugal | 16 | 13 | 2019-01 | 3 | 26.3 m | 53 m | 12% | 21% | no | none | 20 |

Per-panorama records, per-epoch breakdowns and the probe results are in `screening.json`. Korenmarkt
sits at rank 20 on its own screening, which is the honest way to read every result so far derived from
it.

## The ten sites

Eight new, plus the two that already exist.

| Site | Walk | Spacing | Span | Azimuth | Capture | Built form | Why |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Korenmarkt, Ghent | 14 | 10.0 m | 103 m | 50% | 2025-06 | Medieval brick, car-track capture | Already acquired end to end. The low-density control |
| Piazza del Duomo, Milan | 214 | 2.5 m | 119 m | 100% | 2014-09 | Monumental stone, pinnacle field | Already acquired end to end. The densest European walk in the set |
| Plaza de la Constitucion, Mexico City | 253 | 1.9 m | 87 m | 100% | 2016-10 | Very large open plaza, volcanic stone, low blocks | Largest and densest walk measured anywhere here, and the only genuinely open plaza floor at this density, which is the geometry where the ground bounce dominates |
| Rynek Glowny, Krakow | 162 | 2.1 m | 88 m | 81% | 2024-11 | Very large medieval square with a free-standing hall | The densest recent capture in the set. The Cloth Hall standing in the middle puts a facade on both sides of the observer, which nothing else here does |
| Staromestske namesti, Prague | 147 | 2.7 m | 117 m | 100% | 2014-06 | Irregular medieval, gothic towers, plaster and stone | Dense, full azimuth spread, and a facade mix no other chosen site has. Carries a 2025-04 walk of 23 panoramas as a current-epoch cross-check |
| Trafalgar Square, London | 144 | 5.5 m | 112 m | 100% | 2012-08 | Open terraced square, Portland stone, traffic on one side | Full azimuth spread and full probe coverage, live traffic on one edge, and Portland stone against brick, render and marble elsewhere |
| Times Square, New York | 45 | 3.3 m | 84 m | 44% | 2023-11 | Deep glass and LED canyon, 428 m of vertical extent | Promoted from reserve after Place du Capitole failed the anchor check. The most extreme aspect ratio acquired, a recent capture, and a mesh that passes every consistency check |
| Hachiko square, Shibuya | 105 | 2.8 m | 118 m | 62% | 2018-05 | Dense glass canyon, scramble crossing, heavy signage | The only glass and signage canyon of the ten, the highest facade-to-width ratio, and the longest span. Metal-backed signage is a specular class the masonry sites do not exercise at all |
| Plaza Mayor, Madrid | 56 | 9.0 m | 112 m | 100% | 2025-05 | Closed arcaded rectangle, painted render, four gated entries | The most nearly closed geometry in the set, the extreme case for multiple-bounce enclosure, and the newest capture of the ten |
| Grand-Place, Brussels | 45 | 10.0 m | 111 m | 100% | 2024-07 | Fully enclosed guildhall square, gilded stone | Highest enclosure ratio, ornate and deeply modulated facades, full azimuth spread on a recent capture |

Built forms across the ten: medieval brick, monumental marble, open volcanic-stone plaza, medieval
square with a free-standing central block, gothic plaster and stone, Portland stone with traffic, fired
brick, glass and signage canyon, closed painted arcade, ornate gilded guildhall. Latitudes from 19.4 N
to 52.4 N. That is a spread of enclosure ratio, facade modulation depth and material class, which is
what an exposure distribution needs.

Three picks went against the raw ranking and all three are argued rather than assumed.

**Hachiko square is in although it fails the gate**, on epoch fragmentation: its 2018-05 capture is
split into linked runs and the largest holds 105 of them rather than nine tenths of the date. It clears
the azimuth threshold at 62 percent, it has the longest span of the ten at 118 m, and its 105-panorama
walk is larger than that of any of Madrid, Brussels or Placa Reial, which all pass. Against a per-site
budget of 12 to 16 panoramas the fragmentation costs nothing that matters, and it is the only glass
canyon available.

**Sultanahmet Meydani is out although it ranks fifth and passes**, and **Place du Capitole is out
although it ranks seventh and passes.** Both were chosen, acquired, and then dropped on the geometry
rather than on the panoramas, for two different reasons. Times Square came off the reserve bench to
replace Toulouse. Both rejects keep their tiles and both are recoverable.

## The two sites dropped after acquisition

Sultanahmet screens well: 146-panorama walk at 2.7 m spacing over a 119 m span, second only to Milan on
span. Its tiles are worthless. At 130 m the Sultanahmet pull returned 80 leaf tiles holding **11,864
triangles**, against 130k to 470k at every other site, with a median leaf of 14 kB against 52 to 278 kB
elsewhere. Every leaf still reports the same 2.006 m geometric error, so the tile scheme claims the
same LOD and does not deliver it: this is a textured coarse base mesh with no photogrammetric detail
over Istanbul, not a deep leaf set.

**Place du Capitole is anchored on a building, not on the square.** The screened latitude and longitude
put the crop centre somewhere enclosed and low. Casting a 256-ray sphere from 1.5 m above the ground
under five points, at the anchor and 20 m out in each cardinal direction, gives:

```
ground   191.1   211.1   210.7   190.9   207.1   m ellipsoidal
sky       0.14    0.96    0.59    0.19    0.00
```

Ground stepping 20 m over a 20 m baseline is a roofline, not a slope, and 14 percent sky is not what a
standing observer sees in a large open square. The same test at every other site returns a ground
consistent to about a metre across all five points and sky between 0.35 and 0.92 at the anchor, so the
test is discriminating rather than noisy. Toulouse is the only site that fails it.

It is recoverable and worth recovering, since it is the largest mesh acquired at 470,673 source
triangles and it is the only site that would have contributed fired brick as a bulk facade material.
The fix is to move the anchor into the open square and re-pull, which costs about 350 requests.

**Krakow is anchor-suspect for a related and more interesting reason.** Its anchor reads a ground of
269.6 m with 92 percent sky, against a Rynek pavement that should sit near 261 m ellipsoidal, and the
Cloth Hall stands in the middle of the Rynek. The anchor is very probably on the Cloth Hall roof. This
is not a screening error: the centroid of the square genuinely is the building, and that is precisely
the built form Krakow was chosen for. Krakow ships without a config for this reason and its anchor needs
moving off the hall before its panoramas are fetched.

The lesson for the remaining rollout is that panorama screening does not screen geometry, and the three
failures are independent of it and of each other. Two checks are cheap and both should run before any
further site is committed: triangle count per leaf set, which costs one pull and would have caught
Istanbul, and the five-point sky and ground consistency cast, which costs one mesh build and catches
Toulouse and Krakow.

## Why the rejects were rejected

**Dense but pinned to one spot.** Raffles Place has a 39-panorama walk at 0.4 m spacing over a 7 m span
and 6 percent azimuth spread. Dam has 16 at 0.6 m over 6 m. These are tripod sequences at an entrance,
not traverses. Spacing alone would have ranked them first, which is precisely why the gate is built on
spread. Trg bana Jelacica is the same shape at larger scale, 63 panoramas at 1.0 m over 32 m and
12 percent spread, and Federation Square is a 69-panorama walk over 53 m at 31 percent.

**No walk worth the name.** Praca do Comercio: 16 panoramas, largest same-date connected walk of 3,
spacing 26.3 m. The square opens onto the Tagus and its coverage is one road along the north edge.
Kongens Nytorv, Stephansplatz, Alexanderplatz, Piazza Navona and Dam are the same failure in milder
form, with walks of 10 to 16. Alexanderplatz and Kongens Nytorv are the ones worth revisiting, since
both are recent and simply thin.

**Small square, thin coverage.** Piazza San Marco is the painful one: the most pedestrianised square in
Europe, and it screens at 41 panoramas with an 18-panorama walk at 19 percent azimuth spread. Being
car-free means there is no car track, and the trekker coverage inside it is old and broken into pieces.
Greenmarket Square, Cape Town fails the same way at 31 panoramas and 12 percent spread, and would have
been the Africa entry.

**Good, but beaten on built form.** Placa Reial passes the gate at rank 10 and was displaced by Hachiko
square: its walk is 31 panoramas at 9.4 m, and an enclosed arcaded courtyard is a class Madrid and
Brussels already cover twice over. It is the first site to promote if another one fails.

Losing Toulouse costs the set its only fired-brick site other than Ghent, and taking Times Square in its
place puts two glass canyons in the ten. That is a real narrowing of the built-form spread and it is the
price of shipping only sites whose geometry has been checked. Recovering Toulouse should be the first
follow-up job, ahead of adding an eleventh site.

## Capture age, and what will go wrong

The chosen ten span 2012-08 to 2025-06 with a median of 2017. Five are nine years old or older:
Trafalgar Square 2012-08, Staromestske namesti 2014-06, Piazza del Duomo 2014-09, Plaza de la
Constitucion 2016-10, and Korenmarkt's own 2025-06 capture is the exception rather than the rule.
Hachiko square 2018-05 and Place du Capitole 2018-12 sit in the middle. Krakow 2024-11, Brussels
2024-07 and Madrid 2025-05 are current.

What goes wrong is specific. Semantic labels are read off the panorama and projected onto the mesh, so
where the city changed between the two, a label lands on geometry that is not what the label describes.
Milan already shows the failure mode: its 2014 panorama has a tower crane and full scaffolding over the
Galleria's north wing that the current tile mesh does not contain, so that region gives facade evidence
for a structure that no longer exists. Refurbished facades, replaced shopfronts and new street furniture
are the same defect in smaller pieces.

Registration will not report it. The skyline objective is fitted against rooflines, and rooflines are
the part of a city that changes least, which is why Milan's twelve-year-old panorama still registers at
1.05 degrees, better than Korenmarkt's current one. A good residual is not evidence that the foreground
matches.

The detector that does report it is already being computed. The fishnet produces a per-view sky versus
mesh conflict metric, and a demolished or added building is exactly its signature: segmentation saying
sky where geometry says surface, or the reverse. It costs nothing extra. Every site with a walk older
than about 2020 should have that metric read per view before its semantics are trusted, and the
affected azimuth ranges excluded from facade evidence rather than the whole site dropped.

Three of the old sites carry a recent walk that can serve as an independent cross-check with no further
screening: Prague 2025-04 with 23 panoramas, Trafalgar 2021-05 with 43, and the Zocalo 2021-03 with 42.
Milan has no recent walk at all inside 60 m, so there the conflict metric is the only check available.

## Panorama budget

Coverage of directly observed surface saturates between 12 and 16 panoramas per site: 12 reach 77
percent of achievable coverage and 15 reach 82 percent, while 26 are needed for 90 percent and 33 for
95 percent. The second panorama adds 3,938 faces and the last five add 182 each. Eight of the ten sites
have a single-epoch walk of 45 panoramas or more, so the walk is not the binding constraint anywhere
except Korenmarkt, whose 14 is the known weak case.

Two consequences for how the panoramas should be picked, neither of which is a screening decision but
both of which the screening records make possible.

First, take a spatially spread subset of 12 to 16 rather than the 12 to 16 nearest the centre. Extent
binds harder than count, and `screening.json` carries the east and north offset of every panorama, so
the spread subset can be chosen without another request.

Second, which single panorama comes first matters enormously: the first capture alone delivers between
1.59 and 6.29 percent of scene area depending on which one it is, a fourfold lottery. So a thin site is
riskier than its headline count suggests, and any per-site coverage figure quoted from one panorama
should be resampled before it is believed.

## Acquisition

All ten pulls used a 130 m radius, the deepest available leaves, and the region of interest as a
vertical cylinder about the site up axis, so the radius is horizontal at every height and the Milan
ellipsoid-ball defect does not recur. Acquisition radius equals crop radius, so every tile fetched is
inside the crop and nothing paid for is discarded.

| Site | Leaf tiles | Requests | Bytes | Source triangles | Cropped mesh triangles | Config |
| --- | --- | --- | --- | --- | --- | --- |
| Plaza de la Constitucion | 150 | 305 | 14.6 MB | 331,309 | 138,458 | `config/mexico_zocalo.json` |
| Rynek Glowny | 91 | 187 | 11.0 MB | 251,488 | 130,704 | pending, anchor suspect |
| Staromestske namesti | 121 | 250 | 15.8 MB | 353,706 | 171,747 | `config/prague_staromestske.json` |
| Trafalgar Square | 118 | 242 | 19.6 MB | 415,734 | 217,098 | pending ground height |
| Place du Capitole | 171 | 353 | 20.3 MB | 470,673 | 259,263 | dropped, anchor defect |
| Plaza Mayor | 150 | 306 | 15.2 MB | 323,793 | 187,462 | `config/madrid_plazamayor.json` |
| Grand-Place | 75 | 155 | 16.0 MB | 335,883 | 200,273 | `config/brussels_grandplace.json` |
| Hachiko square | 219 | 444 | 20.2 MB | 404,000 | 197,092 | `config/tokyo_hachiko.json` |
| Sultanahmet Meydani | 80 | 168 | 2.5 MB | 11,864 | not built | dropped, see above |
| Times Square | 400 | 806 | 21.0 MB | 384,100 | 220,259 | `config/newyork_timessquare.json` |

Totals: 1575 leaf tiles, 3216 requests, 156.2 MB. Tiles live in `data/tiles/<site>/` and are gitignored.
Support meshes are `data/geometry/<site>/inhouse_leaf_130m.ply` with the matching manifest.

Meshes were built with the shipped pipeline, one command per site, about 50 seconds each:

```
~/blender-4.5/blender --background --python build_inhouse_mesh.py -- \
  --tiles data/tiles/<site> --out data/geometry/<site>/inhouse_leaf_130m.ply --crop-radius-m 130
```

They carry the known single-precision ECEF-to-ENU defect of `build_inhouse_mesh.py`, measured at
Korenmarkt as about 0.22 m of mean rigid shift and up to 0.44 m of differential tile-to-tile
misregistration, and will need rebuilding when that is fixed. Rebuilding costs no requests.

### Why three sites have no config yet

`camera_ground_z_m` is circular on a fresh site: the mesh has to exist before the ground can be
measured, and `semantic_twin.panorama` needs the value in the config before it can write
`pose_initial.json`. It was measured here by casting downward against the shipped mesh over a 13 by 13
grid spanning 6 by 6 m centred on the walk panorama nearest the site centre, with the ray starting
above the whole scene.

That measurement is trustworthy only when the patch it lands on is flat. Applied to Korenmarkt as a
control it returns 55.43 m against the shipped 50.837 m, with a patch spread of 2.19 m and a
peak-to-peak of 7.13 m, because a ray starting above the scene hits the first thing it meets and near
buildings that is an awning or a cornice rather than the pavement. The spread is a working guard on
exactly that failure: it is 2.19 m where the answer is wrong and 0.014 to 0.065 m at the six sites
whose configs are shipped.

Krakow at 0.96 m spread, Trafalgar at 0.17 m and Place du Capitole at 6.89 m are not shipped with a
ground height, because the patch under their centre panorama straddles the Cloth Hall, the plinth of
Nelson's Column and the Capitole respectively. They need the two-pass treatment: cast once to find a
candidate, then re-cast with the ray ceiling set a few metres above that candidate so an arcade roof is
excluded, exactly as `camera_altitude` already does once a scene constant exists. For Krakow and
Toulouse the anchor has to move first, since no ceiling choice rescues a cast that starts over a roof.

The general rule, learned the expensive way in this session and independently by two other agents: on a
downward cast take neither the highest hit nor the lowest. The highest puts you on a roof wherever the
photogrammetry bridges a street and the lowest puts you in a basement or under an arcade. A median over
a small patch is robust to both, and the patch spread is the guard that says when even the median
cannot be trusted.

## What a follow-up run needs to do

1. **Re-anchor Toulouse and Krakow off their buildings, and measure the missing ground heights.**
   Toulouse needs a new centre in the open square, a re-pull of about 350 requests and a rebuild.
   Krakow needs its centre moved off the Cloth Hall, which may not need a re-pull at all if the new
   centre is still inside the 130 m cylinder that was fetched. Trafalgar needs only the two-pass cast.
   Then write those three configs. Nothing else is blocked on anything else.
2. **Fetch panoramas.** No panorama has been fetched for any new site. The spread subset of 12 to 16
   per site should be chosen from the east and north offsets already in `screening.json`, not by
   nearest-to-centre. At Milan's cost of 338 tiles for one zoom-5 panorama, sixteen panoramas at eight
   sites is roughly 43,000 tile requests, which is the largest single piece of spend still outstanding
   and the one worth sizing deliberately.
3. **Re-screen the chosen sites at 80 m rather than 60 m.** Extent is now the binding criterion and the
   whole table was measured inside 60 m, so the walks are being judged on a disc smaller than the one
   the study wants to use. This costs about 4000 metadata requests and would change which panoramas get
   picked, though it is unlikely to change which sites were chosen.
4. **Check triangle count per leaf set before committing any further site**, after Sultanahmet.
5. **Run the crop convergence sweep.** Every new site is cropped at 130 m because that is what
   Korenmarkt uses, and Milan needed 170 m. The right radius is a property of the square. Re-pulling at
   a larger radius reuses nothing, since the downloader has no cross-run cache, so the sweep should be
   run before any decision to widen.
6. **Read the sky versus mesh conflict metric** on every site whose walk predates 2020, before its
   semantics are trusted.
