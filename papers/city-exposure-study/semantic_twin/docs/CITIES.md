# City screening, site selection and acquisition

Phase 6 of `ROADMAP.md`, done on 2026-08-01. Twenty-four candidate squares were screened on Street View
metadata alone before any tile was paid for, and ten sites were chosen. Ten pulls followed, at a 130 m
radius each, which is a different ten: the eight new sites plus Sultanahmet and Place du Capitole, both
of which were dropped afterwards on their geometry. The two sites that already exist end to end,
Korenmarkt and Piazza del Duomo, were screened with the rest as the only way to know what the numbers
mean, and they keep the meshes they already had at 130 m and 170 m.

**Provider.** The official Map Tiles Street View metadata endpoint,
`tile.googleapis.com/v1/streetview/metadata`, and the Map Tiles 3D Tiles endpoint for geometry. Nothing
here touches Mapillary, so the sampled bounding-box defect measured on the Mapillary bbox endpoint,
where a 200 m box returned 2 of 13 frames of a sequence, does not apply, and neither does the 13-point
overstatement of cross-capture agreement that follows from it. This screening never queries a box. It
starts from one panorama and walks the `links` list outwards, which is the same shape as the
sequence-enumeration pattern that fixed the Mapillary path.

**Cost.** Screening: 4091 metadata requests over 24 sites, 109 seconds of wall clock, which is the sum
of the per-site `seconds` in `screening.json` because the sites are screened one after another and only
the metadata calls inside a site run concurrently. Acquisition: 1575 leaf tiles,
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
| Times Square, New York | 45 | 3.3 m | 84 m | 44% | 2023-11 | Deep glass and LED canyon, 226 m of tower above the street | Promoted from reserve after Place du Capitole failed the anchor check. The most extreme aspect ratio acquired and a recent capture. The mesh passed the checks run at acquisition time and failed a later one, see below |
| Hachiko square, Shibuya | 105 | 2.8 m | 118 m | 62% | 2018-05 | Dense glass canyon, scramble crossing, heavy signage | The only glass and signage canyon of the ten, the highest facade-to-width ratio, and the second longest span behind Milan's 119 m. Metal-backed signage is a specular class the masonry sites do not exercise at all |
| Plaza Mayor, Madrid | 56 | 9.0 m | 112 m | 100% | 2025-05 | Closed arcaded rectangle, painted render, four gated entries | The most nearly closed geometry in the set, the extreme case for multiple-bounce enclosure, and the newest capture of the ten |
| Grand-Place, Brussels | 45 | 10.0 m | 111 m | 100% | 2024-07 | Fully enclosed guildhall square, gilded stone | Highest enclosure ratio, ornate and deeply modulated facades, full azimuth spread on a recent capture |

Built forms across the ten: medieval brick, monumental marble, open volcanic-stone plaza, medieval
square with a free-standing central block, gothic plaster and stone, Portland stone with traffic, fired
brick, glass and signage canyon, closed painted arcade, ornate gilded guildhall. Latitudes from 19.4 N
at the Zocalo to 51.5 N at Trafalgar. That is a spread of enclosure ratio, facade modulation depth and
material class, which is what an exposure distribution needs.

Three picks went against the raw ranking and all three are argued rather than assumed.

**Hachiko square is in although it fails the gate**, on epoch fragmentation: its 2018-05 capture is
split into linked runs and the largest holds 105 of them rather than nine tenths of the date. It clears
the azimuth threshold at 62 percent, its 118 m span is the second longest of the ten, and its 105-panorama
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
triangles**, against 251k to 471k at every other site, with a median leaf of 14 kB against 28 to 278 kB
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

The cast was run by hand and no script for it ships, so only half of that block is reproducible from
this repository. Re-reading the topmost surface of `inhouse_leaf_130m.ply` at the same five points gives
191.1, 211.1, 210.7, 190.9 and 210.8 m, so four of the five ground values reproduce exactly and the
fifth does not, which makes the step larger rather than smaller. The sky row has no on-disk source at
all and is quoted here as it was measured.

It is recoverable and worth recovering, since it is the largest mesh acquired at 470,673 source
triangles and it is the only site that would have contributed fired brick as a bulk facade material.
The fix is to move the anchor into the open square and re-pull, which costs about 350 requests.

**Krakow is anchor-suspect for a related and more interesting reason.** Its anchor reads a ground of
269.6 m, which does reproduce from the shipped mesh, with 92 percent sky, which does not have a source
file, against a Rynek pavement that should sit near 261 m ellipsoidal, and the
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

The chosen ten span 2012-08 to 2025-06 with a median capture year of 2020. Four are nine years old or
older: Trafalgar Square 2012-08, Staromestske namesti 2014-06, Piazza del Duomo 2014-09 and Plaza de la
Constitucion 2016-10. Hachiko square 2018-05 sits in the middle. Times Square 2023-11, Brussels 2024-07,
Krakow 2024-11, Madrid 2025-05 and Korenmarkt 2025-06 are current.

What goes wrong is specific. Semantic labels are read off the panorama and projected onto the mesh, so
where the city changed between the two, a label lands on geometry that is not what the label describes.
Milan already shows the failure mode: its 2014 panorama has a tower crane and full scaffolding over the
Galleria's north wing that the current tile mesh does not contain, so that region gives facade evidence
for a structure that no longer exists. Refurbished facades, replaced shopfronts and new street furniture
are the same defect in smaller pieces.

Registration will not report it. The skyline objective is fitted against rooflines, and rooflines are
the part of a city that changes least, which is why Milan's twelve-year-old panorama still registers at
0.74 degrees, better than Korenmarkt's current one at 1.31. A good residual is not evidence that the
foreground matches. Both figures are the `skyline_score_mean_deg` of the shipped
`alignment/pose_aligned.json` at each site, and they supersede the 1.05 and 2.83 quoted in an earlier
draft, which no pose file on disk carries.

The detector that does report it is already being computed. The fishnet produces a per-view sky versus
mesh conflict metric, and a demolished or added building is exactly its signature: segmentation saying
sky where geometry says surface, or the reverse. It costs nothing extra. Every site with a walk older
than about 2020 should have that metric read per view before its semantics are trusted, and the
affected azimuth ranges excluded from facade evidence rather than the whole site dropped.

Three of the old sites carry a recent walk that can serve as an independent cross-check with no further
screening: Prague 2025-04 with 23 panoramas, Trafalgar 2021-05 with 43, and the Zocalo 2021-03 with 42.
Milan has no recent walk at all inside 60 m, so there the conflict metric is the only check available.

## Panorama budget

Coverage of directly observed surface saturates between 12 and 16 panoramas per site. Measured on area,
which is the stable axis, 12 panoramas reach 77 percent of achievable coverage and 15 reach 82 percent,
while 24 are needed for 90 percent and 32 for 95 percent. On face count, which moves with ray density,
the same targets need 15, 18, 26 and 33. The second panorama adds 3,938 faces and the last five add 182
each. Nine of the ten sites have a single-epoch walk of 45 panoramas or more, so the walk is not the
binding constraint anywhere except Korenmarkt, whose 14 is the known weak case.

Two consequences for how the panoramas should be picked, neither of which is a screening decision but
both of which the screening records make possible.

First, take a spatially spread subset of 12 to 16 rather than the 12 to 16 nearest the centre. Extent
binds harder than count, and `screening.json` carries the east and north offset of every panorama, so
the spread subset can be chosen without another request.

Second, which single panorama comes first matters enormously. Across the 60 random acquisition orders
the first capture alone delivers between 1.59 and 6.29 percent of faces, and those are the tenth and
ninetieth percentiles rather than the range. Over all 41 candidate panoramas the first capture is worth
anywhere from 0.59 to 6.77 percent of faces, or 0.84 to 11.56 percent of area, which is a fourteenfold
lottery by area rather than a fourfold one. So a thin site is riskier than its headline count suggests,
and any per-site coverage figure quoted from one panorama should be resampled before it is believed.

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
exactly that failure: it is 2.19 m where the answer is wrong and 0.015 to 0.065 m at the six sites
whose configs are shipped, each of which records its own spread in `camera_ground_z_note`.

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

## Panoramas: three sites taken to semantic completeness

Fetched, segmented and registered on 2026-08-02. Ghent and Milan already had one panorama each, so
this brings the study to five sites with semantics and forty registered poses in total, counting the
tenth Madrid pose that landed after the summary in `outputs/city_screening/panorama_registration.json`
was written.

Which twelve to sixteen cameras decides how much of the scene is ever observed, so they are chosen by
farthest-point sampling over the walk: start at the panorama nearest the site centre, then repeatedly
add whichever candidate is farthest from everything already chosen. Only the walk's own capture date is
eligible, so no set mixes a 2014 scaffold with a 2024 facade. The alternative, the sixteen nearest the
centre, would be a cluster that sees one ring of facades many times over.

| Site | Chosen | Walk | Capture | Minimum separation | Median separation | East extent | North extent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Staromestske namesti | 14 of 147 | 2014-06 | 21.5 m | 38.4 m | -59.4 to 55.6 m | -57.1 to 57.3 m |
| Plaza de la Constitucion | 14 of 260 | 2016-10 | 19.2 m | 29.0 m | -59.2 to 31.1 m | -29.3 to 54.7 m |
| Plaza Mayor | 10 of 56 | 2025-05 | 30.2 m | 45.4 m | -50.3 to 58.9 m | -41.5 to 36.8 m |

Selection worked: against screening medians of 2.7, 1.9 and 9.0 m between adjacent panoramas, the
chosen sets sit 19 to 30 m apart and span the full screening disc in both axes.

### Segmentation

Mask2Former on Mapillary Vistas at native 1536, on the A6000. Each `semantics.json` records
`inference_size: 1536` with `inference_size_status: set explicitly, not inherited from the checkpoint
processor`, which is the check worth making: the checkpoint's own default is 384 and it silently drops
seventeen clutter classes, including poles, street lights and traffic signals that the photogrammetry
does not contain at all. Throughput was 119 s per panorama under load and 57 s on a quiet box, so
37 panoramas took about 44 minutes.

### Registration

Every panorama is registered on its own against the site's 130 m mesh, so the useful quantity is the
distribution over a site rather than any single residual.

| Site | Panoramas | Registered | Median residual | Best | Worst | Poses at altitude bound |
| --- | --- | --- | --- | --- | --- | --- |
| Plaza Mayor | 10 | 10 | 0.40 deg | 0.18 deg | 2.92 deg | 5 |
| Staromestske namesti | 14 | 14 | 0.82 deg | 0.48 deg | 9.33 deg | 2 |
| Plaza de la Constitucion | 14 | 14 | 2.76 deg | 1.86 deg | 4.59 deg | 4 |

Read off the shipped `pose_aligned.json` files. `panorama_registration.json` still reports Madrid as 9
of 10 at a 0.33 deg median with 4 at the bound, because it was written before the tenth pose converged,
and the table above is the current state of the poses on disk.

References: 0.74 deg for Milan's single panorama and 1.31 deg for Korenmarkt's. Madrid and Prague are
better than either, which is what a 2025 capture and a high-contrast gothic silhouette should give.

Two things in that table are worth more than the medians.

**Eleven of thirty-eight poses landed on their altitude search bound, and twenty-seven did not.** A pose
at its bound is not a measurement, it is the bound, and every panorama previously shipped in this
repository had that defect. Having a majority free of it is new. The pinned poses should not be trusted
for altitude. Ten of them are listed in `outputs/city_screening/panorama_registration.json` and the
eleventh is the later Madrid pose, which `outputs/registration_sky_conflict.csv` does carry.

**The Zocalo is the outlier site, and its outliers are not scattered.** Six of its fourteen exceed
3 deg and every one of them stands in the northern half of the plaza looking south. The Zocalo is
roughly 200 m across, so from the north side the facades that set the southern skyline are 150 to 200 m
away and a 130 m crop does not contain them. The optimiser is fitting a silhouette against geometry
that was cut off.

That is the crop radius bias appearing in registration rather than in propagation, and it is
independently testable, so it was tested. Re-registering the Zocalo against the 250 m shell instead of
the 130 m mesh, with everything else held fixed:

```
pano_00   130 m: 2.07 deg    250 m: 1.31 deg
pano_01   130 m: 2.03 deg    250 m: 1.56 deg
```

A 30 percent reduction from geometry alone. Those four numbers were read off a console and no
`alignment250/` directory exists anywhere in the repository, so nothing on disk reproduces them: the
full re-registration of all three sites against the 250 m shells was still running when this was
written and never landed. The conclusion to draw now is narrow and firm: **the skyline objective should be
fitted against the widest available geometry, not against the crop the scattering mesh uses.** The
skyline is by definition the far silhouette, so truncating the mesh at the scattering radius removes
exactly the geometry the objective needs. Milan's 170 m crop was chosen for the same underlying reason
and the sweep has now put a number on it.

### What is complete and what is not

Prague and the Zocalo are complete end to end at 14 panoramas each: fetched, segmented at 1536, and
registered. Madrid is 10 of 14 and stopped on a quota wall, not on anything about the site.

Because farthest-point sampling is prefix-optimal, the ten Madrid panoramas that exist are the most
spread ten of the fourteen rather than an arbitrary ten. Their extent is identical to the full set's,
-50.3 to 58.9 m east and -41.5 to 36.8 m north, and only the minimum separation differs, 30.2 m against
21.7 m. Madrid lost density, not reach. Both separations are reproducible: rerunning the sampling on
the 56 walk panoramas in `screening.json` gives 30.22 m at ten and 21.74 m at fourteen.

### The quota, measured

Acquisition stopped at HTTP 429, `RATE_LIMIT_EXCEEDED` on quota metric
`tile.googleapis.com/streetviewtiles`, limit 15,000. It did not recover after several minutes of
cooldown at two concurrent workers, so it is a daily cap rather than a per-minute one.

Measured spend: **14,584 Street View tile files** on disk across the three sites, 14 by 338 at Prague
and the Zocalo and 10 by 512 at Madrid, plus about forty metadata and session calls. That is the count
after the tenth Madrid panorama, and it says why the wall fell where it did: the eleventh Madrid
panorama would have taken the total to 15,096. One zoom-5 panorama of a 13312-wide capture is exactly
**338 tiles**, a 26 by 13 grid.

That gives the number the remaining sites should be sized against:

- **44 panoramas per day** at zoom 5 against a 15,000 per day cap, which is three sites at 14.
- The remaining five sites therefore need **two more days** at zoom 5, or one day if the quota is
  raised in the console.
- Zoom 4 on the same capture costs 91 tiles rather than 338, a 13 by 7 grid over 6656 by 3328 pixels,
  which is 164 panoramas per day at 18.5 pixels per degree instead of 37. That is the lever if breadth
  matters more than angular resolution. An earlier draft said 85 tiles and 176 panoramas, which does not
  follow from the tile arithmetic in `semantic_twin.panorama.zoom_dimensions`.

A second, smaller lesson: `StreetViewTiles._read` retries on 5xx but raises immediately on any 4xx,
and 429 is a 4xx. A rate limit is the one 4xx that is worth backing off and retrying rather than
failing on, so a long acquisition dies on the first throttle instead of pausing through it.

## Panoramas: three more sites, and a tile budget that is not one number

Brussels, Shibuya and Times Square were fetched on the following day's quota, which brings the study
to six sites with semantics. Selection is the same farthest-point sampling over the walk.

| Site | Chosen | Walk | Minimum separation | Median separation | East extent | North extent |
| --- | --- | --- | --- | --- | --- | --- |
| Grand-Place | 14 of 45 | 2024-07 | 20.1 m | 36.6 m | -51.0 to 55.3 m | -47.0 to 51.8 m |
| Hachiko square | 13 of 183 | 2018-05 | 11.6 m | 18.6 m | -57.8 to 59.3 m | -14.3 to 14.3 m |
| Times Square | 14 of 45 | 2023-11 | 6.7 m | 10.2 m | -4.5 to 20.2 m | -59.3 to 20.7 m |

Shibuya and Times Square are both narrow in one axis because both are street canyons rather than
squares, which the screening already said: azimuth spread 0.625 and 0.4375 against 1.0 for the three
open squares. Their walks run along the street, so no selection rule can spread them across an extent
the panoramas do not occupy.

### A zoom-5 panorama is not 338 tiles

The line above, **"one zoom-5 panorama is exactly 338 tiles"**, is true only of the captures it was
measured on. Tile count follows the capture's own pixel dimensions, and those vary by rig and year:

| Capture width | Tile grid | Tiles per panorama | Seen at |
| --- | --- | --- | --- |
| 8192 | 16 x 8 | 128 | Times Square |
| 13312 | 26 x 13 | 338 | Prague, the Zocalo, Shibuya |
| 16384 | 32 x 16 | 512 | Madrid, Grand-Place |

So a day's quota buys between 29 and 117 panoramas depending on which sites are in it, not a flat 44.
Sizing a day's work against 338 would have overrun the cap by half on Grand-Place alone, since 512
against 338 is 51 percent more per panorama and 44 of them would have cost 22,528. Read `imageWidth`
from the metadata before committing a day, which costs one request per site.

Measured spend for these three: 7,183 requests for Grand-Place, 4,408 for Shibuya and 1,807 for Times
Square, plus twelve probe calls and about 130 lost to the failure below. **13,540 of 15,000**, and all
41 panoramas fit in one day only because the two cheap sites paid for the expensive one.

### Times Square has no Street View car coverage, and that broke the fetcher

Every one of the 105 panoramas within 60 m of the Times Square anchor, across all fourteen capture
dates, is a user-contributed photosphere rather than a Street View car capture. The square is
pedestrianised, so no car has ever driven it. The ids are the `CAoS...` form rather than the usual
22-character one, and the copyright reads `From the Owner, Photo by: airmess - Vermessung im Visier`.

Those spheres are 8192 pixels wide and their tile pyramid stops one level below a car capture, so
every `/5/x/y` request against one returns **HTTP 404** and the first attempt acquired zero tiles.
`MAX_ZOOM = 5` is a property of the car rig, not of the API. Probing the grid directly, `/4/15/7` is
the last tile of a full 16 by 8 grid and `/4/16/8` is a 404, so zoom 4 is that panorama's native
resolution and not a downscale of anything.

`semantic_twin.panorama.native_zoom` now derives the top of the pyramid from the tile grid the
metadata implies, `ceil(log2(imageWidth / tileWidth))`, and `zoom_dimensions` uses it instead of the
constant. The 13312 and 16384 wide captures still resolve to 5, so nothing already fetched changes.
`fetch_site_panoramas.py` clamps per panorama and records the settled zoom per directory in
`walk_manifest.json`, and its resume check reads the cached `metadata.json` rather than spending a
request to discover that a photosphere at zoom 4 is already on disk.

The wider point for the remaining sites: **a pedestrianised square is exactly the kind of site this
study wants and exactly the kind Street View covers worst.** Expect photospheres, expect them to be
half the resolution, and expect their poses to come from a phone or a tripod rather than a calibrated
rig.

### Segmentation cost, on a GPU and without one

The 37 panoramas of the first three sites are recorded at 56 to 119 s each in `semantics.json`, and
those are honest cold numbers: `seg_three.log` on the GPU box shows 37 starts and zero cache skips in
one pass, and the per-view arrays are still on the box. The spread inside that range is warm-up, not
caching, and the first panorama of a run is consistently the slowest.

Running the same command on a 4-core VM with no GPU gives **45 to 105 s per view**, so 20 to 45
minutes per panorama against 57 s on the A6000, a factor of 20 to 50. The three new sites were done on
the box in about 40 minutes. This stage is not optional GPU work, it is the one stage that decides
whether a site takes an hour or a day.

One thing to know before trusting a re-run: `dense_cache_settings` keys the per-view cache on model,
checkpoint, inference size, view size and the panorama digest, but **not** on `--output-width`. Fusion
resolution is therefore free to change on a re-run while the expensive per-view pass is reused, which
is the intended behaviour and is what makes a re-fusion cheap. It does mean a `wall_clock_seconds`
read out of a `semantics.json` is only a cold cost if you know the run was cold, so check for a
sibling `views/cache_settings.json` before quoting one as a benchmark.

### Registration: one site good, one bad, one impossible

| Site | Panoramas | Registered | Median residual | Best | Worst | At altitude bound |
| --- | --- | --- | --- | --- | --- | --- |
| Grand-Place | 14 | 14 | 2.87 deg | 1.19 deg | 11.16 deg | 6 |
| Hachiko square | 13 | **0** | n/a | n/a | n/a | n/a |
| Times Square | 14 | 14 | **10.13 deg** | 7.58 deg | 12.00 deg | 6 |

Against the existing references, Madrid 0.40, Milan 0.74, Prague 0.82, Korenmarkt 1.31 and the Zocalo
2.76, **Grand-Place sits just past the Zocalo at the far end of the usable range** and is usable. The
other two are not, and they fail for two different and separately interesting reasons.

**Hachiko square was never above ground.** All thirteen panoramas return zero structurally supported
skyline samples, because all thirteen see between 0.00 and 0.03 percent sky. They are inside Shibuya
Station: the entity histogram reads 68 percent Building, 17 percent Sidewalk, 5.6 percent Rail Track
and 1.4 percent Tunnel, and the images are plainly a subway platform with 渋谷 signage and DT01/Z01
line markers.

The screening picked this walk because a walk is defined as *the largest set of panoramas sharing one
capture date and linked to each other*, and Google's indoor mapping of Shibuya Station is far denser
than any street traverse near it: 183 linked panoramas on 2018-05 against 18 on the next best date.
**At a transit hub that definition selects the station over the street**, and nothing downstream
noticed, because pose altitude comes from a downward ray cast against the street-level mesh. Every one
of those thirteen poses was placed at street level plus 2.5 m while the camera was a floor or two
below ground.

The cheap detector is the one that caught it: **sky fraction of the segmented panorama**. Above ground
it runs from 7 to 44 percent per panorama across every other site here, with per-site medians of 21 to
44 percent, and the 7 percent is a camera under the Plaza Mayor arcade. Anything near zero is indoors. That check costs
nothing once semantics exist and should gate a walk before its panoramas are fetched, not after. The
screening already stores per-panorama elevation, so an even cheaper pre-fetch form is available.

Shibuya is recoverable: the 2023-09 walk has 18 panoramas and is a separate capture. Refetching costs
about 6,100 requests and it should be sky-checked on the first panorama rather than on all eighteen.

**Times Square registers, but the number is meaningless, and the mesh is why.** A 10.13 deg median is
an order of magnitude off every other site. Three measurements, each of which could have exonerated the
mesh, did not:

| Test | Result | Reading |
| --- | --- | --- |
| Register against the 250 m shell | 10.22 to 10.16 deg, and 8.56 to 7.79 on pano_01 | not crop truncation, unlike the Zocalo |
| Median observed skyline elevation | 14.8 deg, against 15.3 at Grand-Place and 15.7 at Madrid | not a high-elevation canyon regime |
| Widen the altitude bound to +-8 then +-25 m | 10.22, 9.52, 7.45 deg, camera sinking to 20 m below ground | no interior optimum exists |

Only the first entry of the third row is on disk. The shipped `pano_00` pose carries the 10.22 deg fit
pinned at -3.0 m and `alignment/align.log` shows it, while the reopened +-8 m and +-25 m fits and the
250 m shell run in the first row were console results that were never written out.

The third row is the diagnosis. `align_skyline` documents the degeneracy directly: a modelled roofline
too low by some height and a camera too high by that same height produce the same angular error, so when
the mesh silhouette is wrong the optimiser buys residual by sinking the camera. Here it sinks it 20 m and
still does not converge, and six of fourteen poses hit the shipped +-3 m bound.

The mesh itself says why. Its vertices span **-220.3 to 207.2 m** with the camera at -19.0, so
**2.9 percent of its vertices sit more than 30 m below the camera**. Grand-Place spans 45.5 to 158.8 m
and Prague 205.8 to 309.6 m, and both have exactly zero vertices below that line. Times Square is
wall-to-wall mirror glass and high-brightness LED billboards, which is the worst case for multi-view
stereo, and the reconstruction has answered with 200 m of geometry hanging under the street.

That also corrects a reading recorded elsewhere in this study, that Times Square's 428 m of vertical
extent is right for the site. It is 226 m of real tower plus 200 m of spurious sub-street geometry, and
the two should not have been added together.

The signed residual medians are near zero, -0.05 and 0.20 deg on the first two panoramas, while the
mean absolute residual is 10 to 12 deg. That combination is not a mispointed camera, which would bias
the sign. It is a silhouette whose shape is wrong bin by bin.

Times Square is therefore blocked on geometry, not on panoramas. Its 14 panoramas and their semantics
are good and stay on disk. The poses in `alignment/` should be treated as unregistered.

## What a follow-up run needs to do

1. **Re-anchor Toulouse and Krakow off their buildings, and measure the missing ground heights.**
   Toulouse needs a new centre in the open square, a re-pull of about 350 requests and a rebuild.
   Krakow needs its centre moved off the Cloth Hall, which may not need a re-pull at all if the new
   centre is still inside the 130 m cylinder that was fetched. Trafalgar needs only the two-pass cast.
   Then write those three configs. Nothing else is blocked on anything else.
2. **Fetch panoramas for the remaining two sites, and refetch Shibuya.** Prague, the Zocalo, Madrid
   and Brussels are registered. Krakow and Trafalgar are untouched and need their configs first.
   Shibuya needs its 2023-09 walk instead of the underground 2018-05 one. Size the day against each
   capture's own `imageWidth` rather than a flat 338 tiles, for the reason measured above. Madrid is
   still 10 of 14 and its four missing panoramas cost 2,048 requests.
3. **Gate a walk on sky fraction before spending a day's quota on it.** Shibuya cost 4,408 requests
   for thirteen panoramas of a subway platform, and one panorama would have shown it. Fetch one, segment
   it, and reject the walk if sky is below a few percent. Better still, screen on the per-panorama
   elevation the screening already stores, which costs nothing at all.
4. **Do not trust a photogrammetry mesh over mirror glass.** Times Square's reconstruction carries
   200 m of spurious geometry below the street and cannot support a skyline objective at any crop
   radius or altitude bound. Check the vertex z range against the camera before registering a new
   site: a healthy site has essentially nothing more than 30 m below the camera.
5. **Re-screen the chosen sites at 80 m rather than 60 m.** Extent is now the binding criterion and the
   whole table was measured inside 60 m, so the walks are being judged on a disc smaller than the one
   the study wants to use. This costs about 4000 metadata requests and would change which panoramas get
   picked, though it is unlikely to change which sites were chosen.
6. **Check triangle count per leaf set before committing any further site**, after Sultanahmet.
7. **Nothing further on the crop radius.** The sweep has run and 130 m is settled as too small. Under
   the superseded illumination law the error against a 340 m reference at Korenmarkt is +0.05 dB
   isotropic, +3.24 dB rooftop and +9.93 dB for street-level small cells, converging at 250 m, and that
   is what `outputs/crop_convergence/korenmarkt_crop_convergence.json` holds, since it was run before
   the law was corrected on 2026-08-02. Correcting the law does not rescue the 130 m crop: on the same
   rays at both radii, `outputs/law_comparison/korenmarkt_law_comparison.json` puts the 130 m against
   250 m difference at +0.51 dB rooftop and +6.94 dB street under the corrected law, so rooftop relaxes
   and street does not, and 250 m now stands on the street model alone. All eight new sites have
   therefore been re-pulled at 250 m into `data/tiles250/<site>/` and built into `inhouse_leaf_250m.ply`
   occlusion shells beside the 130 m meshes, which stay as the scattering and semantics geometry. That
   is 4032 tiles, 8128 requests and 397 MB, in about two minutes concurrently, plus seven minutes of
   Blender. Note that the downloader has no cross-run cache, so the 250 m pull re-fetched the inner
   130 m rather than reusing it: the cost above is a full pull, not an annulus.
8. **Read the sky versus mesh conflict metric** on every site whose walk predates 2020, before its
   semantics are trusted. That is now Prague at 2014-06 and the Zocalo at 2016-10 among the sites with
   semantics, and both have a recent walk available for cross-checking, Prague 2025-04 with 23
   panoramas and the Zocalo 2021-03 with 42.
9. **Register against the 250 m shells, not the 130 m meshes.** Measured on the Zocalo, where the
   residual falls about 30 percent, on a run that left nothing on disk. The scattering mesh and the
   registration mesh do not have to be the same mesh and should not be.
10. **Back off and retry on HTTP 429** in `StreetViewTiles._read`, which currently raises on any 4xx.
