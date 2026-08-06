# What image evidence each site actually has

The eleven city table was run with `--materials geometric` at every site, so its covered area fraction
is 0.000 in all eleven rows and no number in it depends on a photograph. That was not a decision, it
was a consequence: `run_exposure.py` refused `--materials semantic` and `--materials walk` at any site
except Korenmarkt, because Korenmarkt held the only per-triangle binding on disk. Meanwhile all 83
panoramas in `data/panoramas` were registered, segmented and feeding nothing, apart from the twelve at
Korenmarkt.

This is the coverage ledger. It says, per site, what was acquired, what registered, how much of that
registration is trustworthy, and whether a materially bound run is now possible. The last column is the
one the study needs. It was true at one site at one crop radius and it is now true at seven, by two
independent routes at five of those.

Four things changed to make that so, and one thing did not change and is blocking.

## The guard is now a question about the data

`run_exposure.py` carried

```python
if materials != "geometric" and site != "korenmarkt":
    raise ValueError(f"no panorama semantics for {site}, use --materials geometric")
```

That was accurate when it was written and became self-confirming afterwards. It is now

```python
walk_binding = walk_npz or site_walk_semantics(site, crop_m)
fishnet = site_fishnet(site)
if materials.startswith("walk") and walk_binding is None:
    raise ValueError(...)
if materials == "semantic" and fishnet is None:
    raise ValueError(...)
```

so a site is refused when it has no binding rather than when it is not Ghent, and the error names the
command that would build one. It is checked end to end rather than by reading: at Grand-Place over the
250 m crop `--materials walk` resolves the new binding, binds 4.47 percent of the triangle area and
returns real ITU rows, 15,779 triangles of brick, 1,156 of metal, 830 of wood, 403 of marble, 92 of
effective vegetation, 76 of asphalt and 37 of concrete, where the same command previously raised.

The crop radius is part of the question because it is part of the answer.
`modal_class` is indexed by triangle with no join key, so a 130 m binding is not valid for a 250 m run
and `bind_from_walk` refuses the mismatch on the column count. Korenmarkt keeps its Mapillary built
130 m binding, which is what every published walk number here was measured against, and falls through
to its own Street View binding at any other radius.

## The bindings themselves

`build_site_semantics.py` builds, per site and per crop radius, the same product `build_walk_twin.py`
built once at Korenmarkt from twelve Mapillary stations. Nothing in that product was Mapillary
specific. It casts an equirectangular ray grid from each admitted station against the mesh the tracer
will use, tallies the Mapillary Vistas entity class each triangle collects, and writes `modal_class`
and `clean_rays` with one row per station.

A site's stations are every registered panorama in its own directory and in any companion campaign, not
every panorama acquired the same way. Korenmarkt is the only site with two campaigns, one Street View
station and twelve Mapillary ones, and the twelve are what every published walk number here rests on.
Reading only the first would have made the reference site the thinnest row in the table. Nothing about
the cast cares which provider an image came from, only that the pose is registered against the same
mesh in the same frame, and both campaigns are.

Three further details are not inherited and are worth stating.

The material prior is a table, not a site measurement. `vistas_material_prior` maps a Vistas entity
class to a distribution over the RF material vocabulary. It is a property of the vocabulary, and it
lives only in the twelve `semantics.json` files the hybrid backend wrote, eleven of them at Korenmarkt.
All 83 station level `semantics.json` files carry one and the same 65 class vocabulary from the same
mask2former checkpoint, checked label by label rather than assumed, so the same table is passed through
to the other sites rather than recomputed at them. If that check ever fails the prior stops being
transferable, which is why it is a check and not a comment.

The SAM 3 material axis is still one square wide. Twelve panoramas carry `rf_material`, and eleven of
the twelve are Korenmarkt: its single Street View station plus ten of the twelve Mapillary walk
stations, with `walk_07` and `walk_09` left on mask2former. The twelfth is Milan. Every panorama at the
other nine sites carries only `entity`, so `bind_from_walk_material` cannot run at them and the entity
axis binding is the only one built. The audit found SAM 3 on 2 panoramas, a concurrent pass raised that
to 12, and the shape of the finding did not change: there is still no site outside Ghent where the
material axis could carry a cross city comparison.

The bindings built here carry the entity axis only, Korenmarkt's included. `build_site_semantics.py`
writes `modal_class` and `clean_rays` and not `modal_material`, so `--materials walk_material` and its
three variants remain a Korenmarkt 130 m capability served by the older `walk_semantic.npz`, and asking
for them anywhere else fails inside `bind_from_walk_material` with the message that names the rebuild.
Extending the cast to the SAM 3 axis is not hard and is not useful yet, because it would raise the
count of sites that can answer the question from one to one.

The covered fraction depends on the ray grid, and a cheap grid understates it. A triangle no ray landed
on is a triangle no station saw. At Plaza Mayor over the 130 m crop the same six admitted stations bind
18.04 percent of the area at a 384 row grid and 19.43 percent at 768, so a 4x cheaper grid costs about 7
percent of the answer, relative. Every binding here is built at 1536 rows, which is what the Korenmarkt
walk binding was built at, and the grid is held fixed across sites because the covered fraction is a
between site comparison.

## Why Krakow, London and Toulouse had no panoramas

None of the three had a quota problem or a coverage problem when they were skipped. All three screened
well, all three have a connected link graph, and all three already have tiles and a support mesh. What
they did not have is a scene config, and `fetch_site_panoramas.py` cannot run without one. The config
was never written because `camera_ground_z_m` could not be measured under the anchor by the method in
use, which took the median of a 6 by 6 m patch of the topmost tile surface under the seed panorama and
refused any site whose patch spread exceeded 0.1 m.

That method answers the question "what is under this one point". The question the config needs is "what
is the ground of this square", and the two come apart exactly when the anchor lands on a building.

`build_site_config.py` measures the site datum instead. It casts 20,000 downward rays over an 80 m
disc, histograms the topmost surface at 0.5 m, and takes the dominant mode in the lower half of the
relief, which for a city square is the square. It reproduces both independently measured constants in
this repository to under 0.1 m, Korenmarkt at 50.911 against 50.837 and Grand-Place at 65.361 against
65.270, which is the same order as the patch spread the old gate demanded.

| Site | Site datum | Topmost surface under the anchor | Anchor sits on | Verdict |
| --- | --- | --- | --- | --- |
| Trafalgar Square | 54.820 m | 54.65 m | the square, inside the largest open region | config written, ready to acquire |
| Rynek Glowny | 250.932 m | 269.59 m | the roof of the Cloth Hall, 18.7 m up | config written, ready to acquire |
| Place du Capitole | 191.187 m | 191.10 m | an enclosed patch 25 m from the square | not recoverable without a re-pull |

Krakow's anchor is on the Cloth Hall because the centroid of the Rynek genuinely is the Cloth Hall, and
that free standing central block is the built form Krakow was chosen for. It costs nothing: the datum
is measured from the square rather than from under the anchor, `camera_altitude` casts under each
camera's own easting and northing, and the constant only sets the ceiling that cast starts from. The
130 m and 250 m crops both contain the whole Rynek.

Toulouse is different and is not fixed here. Its anchor sits on a low surface at 191.10 m that is
within 0.1 m of the site datum and is nevertheless not the square: the surface is its own connected
component, and the nearest cell of the largest open region, 17,957 m2 of Place du Capitole, is 25 m
away. A sphere of rays from 1.5 m above the anchor sees 0.075 sky. The reading in `CITIES.md`, that the
anchor is on a roofline because ground steps 20 m over a 20 m baseline, has the sign the wrong way
round. The 191 m surface is the ground and the 211 m surfaces around it are roofs, which is why the
2018-12 stations sit at 211 m and see 0.47 sky, half a sphere, the signature of standing on top of a
roof. What is true is the conclusion: the crop is not centred on the square. The fix is to move the
anchor about 25 m and re-pull, roughly 350 tile requests and a mesh rebuild, and it is left alone here
because another agent is working the ground datum for this site and a re-pull would collide with it.

## The screener picks an indoor capture at three sites in eleven

Hachiko was already known: the 2018-05 component the screener chose is 105 panoramas of the Shibuchika
underground arcade, and thirteen of them measured a sky fraction of 0.000. It is not one site in ten.
It is three in eleven, and the other two are exactly the two sites that had no panoramas.

A cheap geometric test finds all three before a tile is paid for. Cast down at each candidate's easting
and northing and ask whether the topmost tile surface is near the site datum or well above it. A
station under an arcade, a concourse or a nave has a roof above it.

| Site | Screened walk | Provider | Stations with open sky above | Best outdoor capture |
| --- | --- | --- | --- | --- |
| Rynek Glowny | 2024-11, 162 panoramas | K2 Wirtualne Spacery | 0 of 162 | 2020-04, 118 panoramas, 55 open, full azimuth spread |
| Place du Capitole | 2018-12, 118 panoramas | Visitez Sans Bouger | 0 of 118 | 2010-10 Google, 41 panoramas, 34 open |
| Trafalgar Square | 2012-08, 142 panoramas | Google | 111 of 142 | the screened walk is the best one |

Both indoor captures are third party virtual tours, both beat every outdoor capture on count, which is
how they won the largest-component rule, and neither has a single station outdoors. Krakow's is the
inside of the Cloth Hall, and its 88 m span is the length of the building. Toulouse's is the inside of
the Capitole.

`fetch_site_panoramas.py --open-sky-m` now applies that test at selection time and is on by default at
2.5 m. It refuses outright when every candidate of a capture is roofed, and it names `--walk-date` in
the error. Where a walk mixes indoor and outdoor stations, as the 2020-04 Rynek walk does at 55 of 118,
it turns an unusable set into a usable one instead of forcing a manual override. It screens geometry,
not imagery, so it costs no request, and it is not a substitute for the sky fraction measured on the
segmented panorama. It is a way of not spending 400 requests to learn the same thing.

## Registration quality, measured with two tests rather than one

The shipping gate is the skyline residual. It is not sufficient, and the failure it misses is the one
that decides whether a pose can be used at all.

A pose whose camera has been driven inside the geometry scores a low residual, because the silhouette
it is matching is the inside of a wall and it matches it well. The discriminator is the sky conflict
already recorded in every `pose_aligned.json`, the fraction of directions the segmentation calls sky
for which the support mesh returns a first hit, read together with the range of the conflict. A healthy
pose sits near zero with its few conflicts tens of metres away. A pose at 1.0 with a median conflict
range under a metre is inside a building.

As the poses were shipped, 26 of the 83 were inside the geometry and 6 of those 26 passed the residual
gate. So the two tests are not redundant and the residual admits poses that are unusable.
`build_site_semantics.py` admits on both, and records every refusal with the test that made it. The
re-registrations described below take the inside count from 26 to 14 and the admitted count to 51, and
6 of the 14 still pass the residual gate, so the disagreement between the two tests survives the fix
rather than being an artefact of it.

A third test arrived from the propagation side while this was being written and points the same way.
Tracing the reference square and asking what fraction of first interaction incident power lands on a
triangle some panorama photographed gives 0.978 to 0.999 at seven of its eight stations and 0.362 at
the eighth, which stands eight metres from one scoring 0.999. Re-registering that camera takes it to
1.000. It costs one trace, it needs nothing but a registered panorama, and it is sharper than the
residual the registration itself minimises. See `paper/methods.tex` for the measurement. Three
independent tests now agree that the skyline residual alone is not a sufficient gate.

The rule reproduces the one published station set. Korenmarkt's `walk_semantic.json` names the eight
Mapillary stations the shipped binding was built from, chosen by hand at the time. The two tests applied
blind admit walk_00, 01, 02, 03, 05, 06, 08 and 10 and refuse the other four on residual, which is the
same eight images. All twelve read clear on sky conflict, so at Korenmarkt the second test changes
nothing and the agreement is carried entirely by the first. That is the useful shape of the result: the
gate is not stricter than the study has been, it is stricter than the study has been at the sites where
the study never looked.

Two sites lost everything under those two tests, Times Square with 12 of 14 poses inside the geometry
and Hachiko with 3 of 3. The next two sections are about why, because the two turned out to have
different diseases. Hachiko's was the crop and it is fixed. Times Square's is the objective, and
re-registering it takes its cameras out of the buildings without making a single one of them usable.

## Why a camera ends up under its own pavement

The 25 poses the conflict test calls inside the geometry are not scattered. Every one of them drove its
altitude down by more than 1.5 m and the median dive is 2.97 m against a search bound of 3.0 m, while
the 41 admitted poses have a median dive of 0.58 m and only one in eight goes past 1.5 m. Diving is the
failure, not a symptom of it, and the mechanism is visible in the objective.

The optimiser matches an observed sky boundary to the angular upper envelope of the support mesh. If
that envelope is too low it has one cheap correction available, which is to lower the camera, because
lowering the camera raises every rooftop in the model at once. It will keep doing so until it hits the
bound. The default bound of 3.0 m sits below a rig height of 2.5 m, so the search is permitted to put
the optical centre half a metre under the pavement, and in a canyon it takes that permission.

What makes an envelope too low is the crop. **Every registration in this repository was fitted against
`inhouse_leaf_130m.ply`**, which is not an assumption: the candidate vertex count recorded in each
`pose_aligned.json` reproduces the 130 m prune exactly at all six registered sites and reproduces no
other radius, 23640 at Grand-Place, 38138 at Plaza Mayor, 36782 at the Zocalo, 47184 at Old Town Square,
38304 at Times Square and 27371 at Hachiko. A 130 m crop is the whole skyline of a low rise square and
a fraction of the skyline of a high rise canyon.

Scoring the untouched initial pose on both crops separates the two cases cleanly. Each row is the median
over that site's first three stations, and the pose is held fixed so the only thing changing is how much
of the city the model is allowed to see.

| Site | Robust residual at 130 m | At 250 m | What the extra crop is worth |
| --- | --- | --- | --- |
| Old Town Square | 1.29 deg | 1.30 deg | -0.00 deg, nothing |
| Plaza Mayor | 3.34 deg | 3.33 deg | +0.00 deg, nothing |
| Grand-Place | 9.86 deg | 9.87 deg | -0.02 deg, nothing |
| Zocalo | 6.23 deg | 6.04 deg | +0.48 deg, marginal |
| Times Square | 14.32 deg | 12.95 deg | +1.37 deg, not the problem |
| Hachiko | 9.42 deg | 4.42 deg | +5.60 deg, the whole problem |

So the shipped crop was adequate at four sites out of six, immaterial at a fifth, and wrong at exactly
one. At Hachiko the fit had been paying three metres of altitude to buy back geometry the crop had
removed: on the 130 m mesh the untouched pose scores 9.42 degrees and the fit reaches 6.53 with the
camera 2.96 m down, and on the 250 m mesh that same untouched pose already scores 2.59.

The chain reproduces bit for bit, which is how it was confirmed rather than inferred. Re-evaluating the
shipped fit against the 130 m mesh returns 6.533 degrees at Hachiko and 10.220 at Times Square, matching
the shipped `skyline_score_mean_deg` to three decimals and matching the shipped candidate counts
exactly. The optimiser was never misbehaving. It was solving the problem it was given.

`reregister_site.py` re-runs the fit against a named crop, keeps the previous pose beside it, and
records the crop and the mesh in the pose it writes. Its `--dz-bounds` passes a clamp through to the
optimiser. Setting it to `-1.5 3.0` keeps the optical centre at least a metre above the ground measured
under that camera, which excludes no pose that was ever any good, since the admitted median dive is
0.58 m.

Hachiko re-registered at 250 m with that clamp goes from zero usable stations to all three.

| Station | Residual before | After | Sky conflict before | After | Camera height above ground |
| --- | --- | --- | --- | --- | --- |
| `pano_00` | 6.53 deg | 1.42 deg | 1.00 at 0.5 m | 0.02 at 108.1 m | -0.6 m to +2.2 m |
| `pano_01` | 4.80 deg | 3.70 deg | 1.00 at 0.3 m | 0.07 at 20.6 m | -0.4 m to +1.0 m |
| `pano_02` | 6.19 deg | 3.08 deg | 1.00 at 0.1 m | 0.01 at 33.9 m | -0.0 m to +2.0 m |

The two changes do different work and it is worth keeping them apart. The wider crop is what moves the
residual, from a median of 6.19 degrees to 3.08. The clamp is what moves the sky conflict, and it is
close to free: run at 250 m without it, `pano_01` scored 3.36 degrees and `pano_02` scored 3.09, so
clamping cost 0.34 degrees at one station and nothing at the other while taking both cameras out of the
pavement. Three metres of altitude had been buying 0.34 degrees of residual and a pose that could not
be used.

Hachiko then binds 8.05 percent of the 250 m crop from three stations, second only to Old Town Square
and from a quarter as many cameras, because the stations sit tight around the crossing and the
frontages there are close and tall. A site that read as a total loss is now one of the better rows in
the table, and nothing about its imagery changed.

The other four registered sites are left on their 130 m fits on purpose. The table above measures what
re-registering them would buy, which is between -0.02 and +0.48 degrees, so it would churn every pose
in the study and several fishnets built on top of them to change nothing. Where the crop is immaterial
it is better to say so than to redo the work.

## Times Square is a different problem and the crop does not fix it

Times Square keeps a residual near 11 degrees on the wider crop, and the reason is not height, it is
that the objective carries almost no information there. Scanning yaw over the entire circle at the
initial pose moves the robust residual by under two degrees at every one of the 14 stations, and four of
them score their minimum more than 120 degrees away from the metadata heading, one at 178 degrees. The
camera cannot tell front from back.

The control says this is a property of the site and not of the method. The same scan at Old Town Square
puts 13 of 14 stations within 2 degrees of the metadata heading, with residuals there from 0.83 to 6.36
degrees, and at Hachiko all three minimise within 2 degrees. A sharp, correctly placed minimum is what
a working registration looks like, and Times Square does not have one. Old Town Square's one exception,
`pano_03`, prefers a heading 102 degrees away and scores 17 degrees even there, which is what a single
bad station looks like beside thirteen good ones.

The geometry explains it. The modelled skyline at Times Square sits at a median elevation of 55 to 62
degrees in every direction, with a sky fraction of 0.15 to 0.33. A skyline that is uniformly high is a
skyline with no features, and rotating a camera inside it changes almost nothing. Skyline registration
needs a ragged horizon, and the deepest canyon in the set is the one place that does not have one.

That is a real limit on the method rather than a defect to be fixed, and it is worth stating in the
paper in those terms. The panoramas at Times Square are fine. The mesh is fine. The two cannot be
brought into correspondence by matching where the sky ends.

Times Square was re-registered at 250 m with the same clamp anyway, because the prediction was worth
testing and because a buried camera is worth removing whether or not its pose is usable. The clamp does
exactly what the mechanism says it should and nothing more. Poses inside the geometry fall from 12 of
14 to 3, eleven of the twelve having sat at a sky conflict of 1.00 with a median conflict range under a
metre, and 9 of the 14 now read their nearest conflicting surface more than 5 m away. The
residual barely moves: the median goes from 10.17 to 9.13 degrees and the best station in the site
reaches 7.20, against an admission gate of 4.0. Not one station is admitted before or after.

That is the cleanest available statement of the two failures being independent. The altitude collapse
was a consequence of the crop and it is gone at both sites. The residual at Times Square was never
about altitude, and putting the cameras back on the street leaves it where it was.

## Four sites had their image evidence built and unreachable

The fishnet path and the fused station path are different bindings, not two names for one. The fused
station path casts a ray grid from each admitted camera and tallies an entity class per tracer
triangle. The fishnet path cuts a surface per view, carrying a class and a confidence per cell, and
joins it back through `face_source_triangle`. They can disagree, which is the point of having both.

At four sites the fishnet path was unavailable for a reason with no physics in it at all. `bind`
collects its views with `glob("*_fishnet.npz")` over the directory it is handed, which does not recurse,
and Brussels, Madrid, Mexico City and Prague had every view written into a folder per panorama one
level down. The surfaces existed, 171,532 faces at Grand-Place through to 383,044 at Old Town Square,
and nothing could read them. Times Square had been flattened by hand and Korenmarkt and Milan were flat
already, each being a single panorama, so the layout split the corpus without anyone choosing it.

The fix needs no new code and no rebuild. `build_site_fishnets.py --all-sites --flatten-only` moves
each nested view to the top of its site directory under a name carrying the panorama it came from,
`pano_00_4Cxfyuve.../h+00_090_fishnet.npz` becoming `pano_00_4Cxfyuve..._h+00_090_fishnet.npz`, and
rewrites the site manifest. The builder writes that layout natively now, so the four sites are the ones
built before it did. Running it moved 164 surface sets and recomputed nothing.

What that returns is substantial, and it is measured rather than asserted. Binding each site's views
onto the mesh they were cut against covers 33.0 percent of the area at Old Town Square from 52 views,
23.4 at the Zocalo from 56, 18.7 at Plaza Mayor from 24 and 11.2 at Grand-Place from 32.

It is checked end to end rather than by reading, on the same terms the walk guard was. At Old Town
Square over the 130 m crop the fishnet binding puts 38,222 of the mesh's 171,747 triangles onto an
image derived material, 27,530 of brick, 3,738 of effective vegetation, 1,904 of wood, 1,899 of metal,
1,171 of marble, 1,039 of asphalt and 941 of concrete, and `load_bindings` resolves every one of those
classes to an ITU row at 15 GHz. The remaining 133,525 fall back to facade, roof and soffit.

The two routes land close to each other without being the same number, which is the useful part. At
130 m the fused station path reads 31.1, 26.2, 20.2 and 13.3 percent at those four sites against the
fishnet's 33.0, 23.4, 18.7 and 11.2, so the fishnet is the larger of the two at Old Town Square and the
smaller at the other three, by between one and three points of area. Two bindings built from the same
photographs by different machinery, agreeing to a few points and disagreeing in a direction that varies
by site, is a cross check the study did not previously have anywhere except Ghent. Which of them is
nearer the truth is not settled here and should not be asserted from the fractions alone.

The one site where this changes nothing is the one that most looks like it should. Times Square's 8
views cover 6.5 percent of the area and were cut from two cameras, neither of which is admitted, and
both of which were sitting inside the buildings they were pointed at when the surfaces were cut. Those
two poses have since been replaced by the re-registration above, so the surfaces are stale as well as
inadmissible. The matrix reports the coverage and refuses the route, and the fishnet column carries the
count of admitted poses behind every site's surfaces so that this stays visible rather than being an
argument made once in prose.

The count in that column uses the stricter of the two gates in the study. `build_site_fishnets.py`
admits a panorama on sky conflict alone, which is the right gate for cutting a surface, so it built
from 14 panoramas at the Zocalo and 13 at Old Town Square where the combined residual and conflict gate
admits 12 at each. The two extra surfaces per site are included in the coverage fractions above and
their provenance is on the page.

## The coverage matrix

Regenerate with `summarise_evidence_coverage.py`, which reads it all off disk and also writes
`outputs/evidence_coverage.json`. The fishnet bound area column is cached beside each fishnet and
refreshed with `--measure-semantic`, which loads a support mesh per site and takes minutes rather than
seconds.

<!-- COVERAGE_TABLE -->

| Site | Panoramas | Registered | Median residual | Worst residual | Median pose sigma | At altitude bound | Inside the geometry | Admitted | SAM 3 material axis | Fishnet faces | Fishnet bound area | Walk bound area at 130 m | Walk bound area at 250 m | Materially bound run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brussels_grandplace | 14 | 14 | 2.87 deg | 11.16 deg | 0.47 m | 6 | 6 | 8 | 0 of 14 | 171532 | 11.2% (32 views) from 8 of 8 admitted poses | 13.3% (8 stations) | 4.6% (8 stations) | walk at 130 m, walk at 250 m, semantic at 130m |
| korenmarkt | 13 | 13 | 3.06 deg | 8.10 deg | 0.17 m | 7 | 0 | 9 | 11 of 13 | 10534 | 3.2% (4 views), poses unattributed | 11.2% (9 stations) | 3.2% (9 stations) | walk at 130 m, walk at 250 m, semantic at 130m |
| krakow_rynek | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | none | none | not measured | none | none | no |
| london_trafalgar | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | none | none | not measured | none | none | no |
| madrid_plazamayor | 10 | 10 | 0.40 deg | 2.92 deg | 0.26 m | 5 | 4 | 6 | 0 of 10 | 157946 | 18.7% (24 views) from 6 of 6 admitted poses | 20.2% (6 stations) | 5.1% (6 stations) | walk at 130 m, walk at 250 m, semantic at 130m |
| mexico_zocalo | 14 | 14 | 2.76 deg | 4.59 deg | 1.86 m | 4 | 0 | 12 | 0 of 14 | 269675 | 23.4% (56 views) from 12 of 14 admitted poses | 26.2% (12 stations) | 7.0% (12 stations) | walk at 130 m, walk at 250 m, semantic at 130m |
| newyork_timessquare | 14 | 14 | 9.13 deg | 11.25 deg | 1.44 m | 5 | 3 | 0 | 0 of 14 | 40057 | 6.5% (8 views) from 0 of 2 admitted poses | none | none | no |
| prague_staromestske | 14 | 14 | 0.82 deg | 9.33 deg | 0.25 m | 2 | 1 | 12 | 0 of 14 | 383044 | 33.0% (52 views) from 12 of 13 admitted poses | 31.1% (12 stations) | 9.9% (12 stations) | walk at 130 m, walk at 250 m, semantic at 130m |
| milan_duomo | 1 | 1 | 0.74 deg | 0.74 deg | 0.26 m | 1 | 0 | 1 | 1 of 1 | 33753 | 6.7% (4 views), poses unattributed | none | 4.0% (1 stations) | walk at 250 m, semantic at 170m |
| tokyo_hachiko | 3 | 3 | 3.08 deg | 3.70 deg | 0.48 m | 1 | 0 | 3 | 0 of 3 | none | not measured | 15.9% (3 stations) | 8.1% (3 stations) | walk at 130 m, walk at 250 m |
| toulouse_capitole | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0 | none | none | not measured | none | none | no |

<!-- END_COVERAGE_TABLE -->

Reading the columns. Panoramas and registered are counts of directories and of `pose_aligned.json`
files. Median pose sigma is the horizontal one sigma of the seed ensemble covariance, the square root
of the sum of the two horizontal variances, which is the registration's own statement of how well it
knows where the camera is. At altitude bound counts poses whose recovered altitude landed on its search
bound, which is not a measurement, it is the bound. Inside the geometry and admitted are the two tests
above. Bound area is the fraction of the crop's triangle area that at least one admitted station saw,
which is the number that was 0.000 in every published row. It is very slightly the larger of two
fractions: a run reports the area that was seen and whose class carries prior mass over the RF material
vocabulary, and a triangle whose only observation is sky or an unmapped class falls out between the
two. At Grand-Place over 250 m that is 4.58 percent seen against 4.47 percent bound.

Fishnet faces counts the cut surfaces. Fishnet bound area is what those surfaces actually bind when
they are aggregated onto the mesh they were cut against, followed by how many of the panoramas behind
them hold a pose that passed admission. That second figure is there because a fishnet inherits the
error of the camera that cut it, and a site can have surfaces without having evidence. `site_fishnet`
also reads the mesh a fishnet was cut against out of that fishnet's own manifest instead of deriving it
from the crop radius of the run. `bind` joins each fishnet face back to a source triangle index, so
handing it the mesh of the run rather than the
mesh of the cut would join two different triangle numberings and would do it without complaining. That
is not hypothetical. Korenmarkt and Times Square were cut against `inhouse_leaf_130m.ply` and Milan
against `inhouse_leaf_170m.ply`, so no crop radius derives all three and a run at 250 m derives none of
them. A 130 m cut inside a 250 m run is supported. It just has to be declared.

## What is now possible, and what is not

A materially bound cross city run is possible at seven of the eleven sites, all seven at the 250 m crop
the headline table runs at: Old Town Square at 9.9 percent of area from twelve stations, Hachiko at 8.1
from three, the Zocalo at 7.0 from twelve, Plaza Mayor at 5.1 from six, Grand-Place at 4.6 from eight,
the Duomo at 4.0 from one and Korenmarkt at 3.2 from nine. Six of the seven can also run at 130 m,
where the fractions are two to three times larger because the crop is smaller and the cameras are in
the same place. Five of them have a second, independent route through the fishnet path. Before this it
was one site at one crop radius by one route. That is the deliverable, and it is the first time the
phrase means anything at more than one site.

The spread across those seven is threefold and it is not a quality signal. Bound area rises with the
number of admitted stations and falls with the size of the crop relative to the square, so Prague leads
on twelve stations in a tight square and the Duomo reaches 4.0 percent from a single camera because
the facade it faces is enormous and close. Hachiko reaches 8.1 percent from three stations for the same
reason in reverse, a small crossing tightly enclosed. Reading the column as "how well did the
segmentation do" would be reading it backwards.

The experiment this unlocks already exists in outline. `run_exposure.py --coverage-report` walks a site
through geometric, one panorama and fused station materials and reports how far the exposure
distribution moves as the bound fraction grows. Its `COVERAGE_LADDER` names Korenmarkt run stems
because Korenmarkt was the only site that could supply them. The inputs for six more sites now exist,
so generalising that tuple to the requested site is the piece of work that turns a single site ladder
into a question about whether the answer travels. It is left alone here because `run_exposure.py` is
under concurrent edit and this report's one change to it is the materials guard.

> **Old illumination law, see `LAW_CHANGE.md`.** The ladder reports how far an exposure
> distribution moves, and that distribution is integrated against the law being replaced.
> The bound area fractions in this document are geometry and survive untouched, but any
> ladder shift measured before the new law lands is stale and has to be rerun.

It is still not a bound run in the sense a reader will assume, and the geometry says why. At the sites
with a station set, the admitted cameras sit within 29 to 62 m of their own centroid, against a
crop that reaches 130 or 250 m. A camera at street level in a square sees the frontages around that
square and nothing behind them, so most of a 250 m crop is roofs and rear elevations that no photograph
in this study has ever seen, and it falls back to the geometric orientation rule exactly as before. The
bound fraction is therefore a property of where a car can drive, not of how good the segmentation is,
and the right way to report a bound run is beside its covered area fraction rather than instead of it.

Milan answers at one radius only. Its crop is 170 m and it has no 130 m mesh, so the column it is
missing is not a gap in its evidence. Everything else that could be filled has been. The 250 m batch
had to be run one site at a time rather than as a batch, because this machine was carrying eight other
jobs at a load average above thirty with swap full and the first attempt was killed after seven of
eleven sites.

Two things are outstanding and neither is a judgement call.

**The Street View tile quota is spent.** `streetviewtilesPerDayPerProject` is 15,000 per day per
project and the project is at its limit, so every tile request returns 429 with that quota named in the
body while the metadata and session endpoints, which are metered separately, continue to serve
normally. The rate limiter is not the issue: serial requests one every two seconds fail 30 out of 30.
Trafalgar's panoramas are 13312 by 6656 at zoom 5, which is 338 tiles each, so 14 panoramas is 4,732
tiles and the three missing sites together are 14,196, near enough the whole daily allowance. Zoom 4
would cost 91 tiles each and a quarter of that, and it is not a fallback worth taking: every panorama
already in this study is zoom 5 and the acquisition would stop being comparable with itself.

London and Krakow have configs written, walk dates chosen and the open sky filter in place, so each is
one command once quota exists:

```
python fetch_site_panoramas.py --scene config/london_trafalgar.json --count 14 --zoom 5
python fetch_site_panoramas.py --scene config/krakow_rynek.json --count 14 --zoom 5 --walk-date 2020-04
```

**Toulouse needs its anchor moved before it needs panoramas.** Acquiring 14 panoramas around a crop
centre that is 25 m outside the square would produce registrations against the wrong geometry. The
re-pull is cheap and the tiles are cached, but it changes a mesh the eleven city table already uses,
so it belongs with whoever owns that mesh.
