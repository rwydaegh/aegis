# The material axis, tested

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street small cell columns
> in every table below, and the percentile spreads the null is measured against, are
> integrals against the old height and range bands. The null survives, because it is a
> statement about material contrast, but the ratio it forms has to be recomputed.

Run 2026-08-02. This closes the gap PAPER_METHODS.md section 9.3 flagged under
"what this ladder does not test": the published evidence ladder varied **entity**
coverage while the material of every facade was fixed by construction, so it
licensed nothing about material discrimination. SAM 3 has now been run on all
eight Korenmarkt walk stations and the ladder re-measured with the material axis
live.

**The result is a null, and it is a much stronger null than the one it
replaces.** Resolving brick against glass against render on the facades the
entity axis could only call brick moves the exposure distribution median by 0.023
to 0.029 dB, and not one of the 120 standpoints moves by more than 0.2 dB under
isotropic or rooftop illumination. That holds on both published walk sets, the
eight station one and the nine station one. The eleven city geometric only table
is therefore justified rather than merely forced.

One secondary result cuts the other way and is reported here because it would be
easy to mistake for the first: replacing the *whole* material field with the
SAM 3 axis, rather than only the facades, moves the median by -0.22 dB. That is
not material discrimination. It is the material axis losing the entity's metal,
vegetation and asphalt assignments on poles, trees and road, and it says the same
thing the original ladder said, measured on the other axis: entity matters more
than material.

---

## 1. What was run

### 1.1 Segmentation

`semantic_twin.semantics --backend hybrid` on ten Korenmarkt walk panoramas: the
eight that pass the 4 degree skyline residual gate and feed every published walk
number, plus `walk_04` and `walk_11` so the conflict gated nine station set could
be built too. Before this run, 94 of 96 panoramas in the study were
`mask2former` only and none of the walk stations had ever seen SAM 3.

```
python -m semantic_twin.semantics \
    --panorama <station>/panorama_original.jpg --out <station>/semantics \
    --backend hybrid --concepts config/semantic_concepts.json --device cuda \
    --inference-size 1536 --view-size 1536 --output-width 4096
```

The dense Mapillary Vistas pass was reused from cache, verified by
`dense_cache_reused: true` in every `semantics.json`, so **the entity axis is
byte identical to the published one and only the material axis is new**. Cost on
an RTX A6000: 30.8 to 36.9 s of SAM 3 per panorama, 78 to 92 s wall clock per
panorama including spherical fusion of the four concept layers. Concept backed
pixel fraction 0.330 to 0.469 over the sphere.

### 1.2 Walk binding

`build_walk_twin.py semantic` was extended to carry a second raster through the
same ray cast. `modal_material` is the modal `rf_material` over exactly the rays
that produce `modal_class`, with the same transient mask and the same clean
majority rule, so the entity and material bindings differ in which raster they
read and in nothing else.

The published `walk_semantic.npz` turned out to have been built at
`--grid-height 1024`, not at the parser default of 1536. Rebuilding at 1024
reproduces `rays`, `transient_rays`, `clean_rays` and `modal_class` **bit for
bit**, so that is the grid used here. The 1536 rebuild is kept beside it as
`walk_semantic_grid1536.npz`; it casts 2.25 times as many rays and moves
`modal_class` on 4.9 % of the commonly seen faces, which is a sensitivity worth
knowing about and is not otherwise used.

### 1.3 Exposure

All rungs re-run at HEAD, 120 standpoints, seed 7, 200k rays, 6 bounces,
130 m crop, `llvm_ad_rgb`. New `--materials` modes in `run_exposure.py`:

| mode | what it binds |
|---|---|
| `walk_material` | SAM 3 material everywhere it routes, geometric rule elsewhere |
| `walk_material_mixture` | same, voting with the per face material histogram instead of each station's modal material |
| `walk_material_over_entity` | SAM 3 material laid over the entity binding, so coverage matches `walk` exactly |
| `walk_material_facade_only` | SAM 3 material **only** on the faces the entity binding resolved to brick, entity binding everywhere else |

`walk_material_facade_only` is the one that answers the question. `Building` and
`Wall` are the only two Vistas classes whose material prior peaks on brick, so
the entity brick set is exactly the set where the entity axis is degenerate.
Everywhere else the entity already names the material, and changing those faces
measures the modal reduction rather than material discrimination.

---

## 2. SAM 3 does discriminate

Pooled over the eight stations, within `Building` and `Wall` pixels:

| material | share of building pixels |
|---|---|
| brick | 59.8 % |
| glass | 23.0 % |
| plasterboard | 14.4 % |
| marble | 1.8 % |
| wood, concrete, metal, chipboard, ceramic | 0.9 % combined |

Per station the brick share runs 51.8 to 70.4 %, and 53.6 to 73.9 % of building
pixels are concept backed rather than falling through to the class prior. So the
null below is not "the detector saw nothing".

On the tracer mesh, over the 15,537 m² of surface both bindings cover:

| | entity axis | SAM 3 material axis |
|---|---|---|
| `semantic_brick` | 7997 faces, 7.215 % of scene area | 6884 faces, 6.936 % |
| `semantic_glass` | **1 face, 0.000 %** | **958 faces, 0.880 %** |
| `semantic_plasterboard` | **0 faces, 0.000 %** | **653 faces, 0.684 %** |
| `semantic_marble` | 686 faces, 0.925 % | 795 faces, 0.675 % |
| `semantic_metal` | 695 faces, 1.214 % | 450 faces, 0.583 % |

**33.2 % of commonly bound faces and 38.5 % of commonly bound area change
material.** Of the 10,596 m² the entity axis called brick, SAM 3 changes 28.5 %:
11.9 % to glass, 9.5 % to plasterboard, 4.8 % to marble, 1.7 % to wood.

Those are not cosmetic swaps. Normal incidence power reflectance at 15 GHz from
the bound ITU-R P.2040-4 rows:

| class | eps_r | RMS height | R at normal incidence |
|---|---|---|---|
| brick | 3.910 | 1.16 mm | -9.67 dB |
| glass | 6.310 | 0.00 mm | -7.32 dB |
| plasterboard | 2.730 | 0.15 mm | -12.16 dB |
| marble | 7.074 | 0.64 mm | -6.87 dB |

Brick to glass is +2.35 dB more reflective and specular rather than rough. Brick
to plasterboard is -2.49 dB. They partly cancel over the scene, and that
cancellation is part of why the exposure result is what it is.

---

## 3. The ladder

Same 120 standpoints, same seed, same walk, same geometry. Rooftop is the
corrected law of section 4.2. Shifts are ratios of distribution medians, and the
standpoint counts are paired per standpoint.

> **Old illumination law, see `LAW_CHANGE.md`.** The corrected law of section 4.2 is the
> old law with its elevation support fixed, so every rooftop and street column below still
> carries the height and range bands. The isotropic columns do not and survive as printed.

### 3.1 Every rung, against the zero evidence baseline

The four published rungs first, entity axis only, re-run at HEAD:

| rung | evidence by area | isotropic median | shift | rooftop median | shift | standpoints > 1 dB (iso / roof) |
|---|---|---|---|---|---|---|
| geometric | 0 % | 0.3099 | | 0.2164 | | |
| one registered panorama | 3.133 % | 0.3141 | +0.059 dB | 0.2240 | +0.149 dB | 2 / 0 |
| eight stations, 4 degree gate | 10.574 % | 0.3360 | **+0.351 dB** | 0.2354 | **+0.365 dB** | 16 / 8 |
| nine stations, conflict gated | 10.982 % | 0.3360 | **+0.352 dB** | 0.2355 | **+0.368 dB** | 16 / 8 |

This reproduces the published ladder. The one panorama and eight station
bindings are bit identical to `clean_semantic`'s and `clean_walk8`'s, including
every one of the 11 chosen material triangle counts and the covered area
fractions to full double precision, and the shifts reproduce the published
0.351 and 0.364 dB. The nine station rung is 0.037 % of area short of the
published 11.019 % for a reason given in section 3.5, and lands on the same
numbers regardless.

Now the material variants, all on the eight station set:

| variant | evidence by area | isotropic median | shift vs geometric | rooftop median | shift | standpoints > 1 dB (iso / roof) |
|---|---|---|---|---|---|---|
| entity axis | 10.574 % | 0.3360 | +0.351 dB | 0.2354 | +0.365 dB | 16 / 8 |
| entity axis with SAM 3 material on the facades | 10.574 % | 0.3379 | **+0.376 dB** | 0.2369 | **+0.394 dB** | 17 / 11 |
| SAM 3 material everywhere it routes | 10.563 % | 0.3195 | +0.133 dB | 0.2270 | +0.208 dB | 2 / 1 |
| SAM 3 material over the entity binding | 10.574 % | 0.3195 | +0.133 dB | 0.2272 | +0.212 dB | 2 / 1 |
| SAM 3 material, histogram vote | 10.635 % | 0.3203 | +0.144 dB | 0.2311 | +0.286 dB | 2 / 1 |

And the same facade only comparison repeated on the top rung of the ladder, the
nine conflict gated stations:

| variant | evidence by area | isotropic median | shift vs geometric | rooftop median | shift | standpoints > 1 dB (iso / roof) |
|---|---|---|---|---|---|---|
| nine stations, entity axis | 10.982 % | 0.3360 | +0.352 dB | 0.2355 | +0.368 dB | 16 / 8 |
| nine stations, entity axis with SAM 3 material on the facades | 10.982 % | 0.3378 | +0.375 dB | 0.2369 | +0.392 dB | 17 / 10 |

### 3.2 The isolating comparison

Material axis against entity axis on the same standpoints, changing only the
material of the facades the entity axis resolved to brick.

| illumination | entity median | facade material median | shift | > 0.5 dB | > 1 dB | worst standpoint |
|---|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3379 | **+0.024 dB** | **0 of 120** | 0 of 120 | 0.110 dB |
| rooftop, corrected | 0.2354 | 0.2369 | **+0.029 dB** | **0 of 120** | 0 of 120 | 0.193 dB |
| street small cell | 0.0984 | 0.0989 | **+0.022 dB** | 1 of 120 | 0 of 120 | 0.929 dB |

**This is the number the ladder could not produce before.** 2950 m² of facade,
28.5 % of the entity brick area, gets a materially different surface, including
1258 m² that goes from rough brick to specular glass, and the exposure
distribution moves by a fortieth of a decibel against 5th to 95th percentile
spreads of 3.9 dB isotropic, 8.4 dB rooftop and 16.7 dB street small cell.
Under isotropic and rooftop illumination not one standpoint of 120 moves by even
half a decibel. Under isotropic, the model the section 4.2 correction cannot
touch and the narrowest of the three distributions, the worst single standpoint
moves 0.110 dB against the 1.98 dB that entity coverage moves it.

The 0.929 dB street outlier is one standpoint and does not repeat in the other
two models, so it is a single grazing geometry rather than a systematic effect.

> **Old illumination law, see `LAW_CHANGE.md`.** The 8.4 dB and 16.7 dB spreads this null
> is judged against are themselves quoted per illumination model, so the denominator of
> the comparison moves along with the numerator. The isotropic line is untouched by the
> law change and carries the null on its own.

Repeating the same comparison on the top rung of the ladder, the nine conflict
gated stations at 10.982 % of area, gives the same answer with nothing added:

| illumination | entity median | facade material median | shift | > 0.5 dB | worst standpoint |
|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3378 | **+0.023 dB** | **0 of 120** | 0.094 dB |
| rooftop, corrected | 0.2355 | 0.2369 | **+0.024 dB** | **0 of 120** | 0.175 dB |
| street small cell | 0.0986 | 0.0989 | **+0.014 dB** | 1 of 120 | 0.839 dB |

So the null does not depend on which of the two published walk sets is used, and
adding the ninth station does not make the material axis matter more.

### 3.3 The result that is not material discrimination

Replacing the whole material field, not only the facades:

| illumination | entity median | full material median | shift | > 1 dB | worst standpoint |
|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3195 | -0.218 dB | 15 of 120 | 2.020 dB |
| rooftop, corrected | 0.2354 | 0.2270 | -0.156 dB | 3 of 120 | 1.117 dB |
| street small cell | 0.0984 | 0.0979 | -0.024 dB | 1 of 120 | 1.102 dB |

Two controls say this is not an artefact of how the run was set up. Laying the
material axis over the entity binding instead of over the geometric rule, which
makes the covered set identical to the entity rung's rather than 0.011 % of area
smaller, gives -0.218 dB isotropic against -0.218: the coverage difference
contributes nothing. Voting with the per face material histogram instead of each
station's modal material gives -0.207 dB: the modal reduction contributes almost
nothing either.

So the decomposition is clean. Facades contribute +0.024 dB, everything else
contributes the remaining -0.242 dB, and "everything else" is where the entity
axis was already right.

What drives it is the 19.1 % of the bound area where the entity axis had already
named the material and the material axis overwrites it, almost all of it flowing
*into* brick: 982 m² the entity called marble, 932 m² it called metal, 306 m² it
called vegetation, 177 m² asphalt and 172 m² concrete. Metal to brick is a
9.67 dB drop in reflectance on street furniture and poles, and vegetation to
brick replaces a vacuum row that barely reflects with a real interface. Those are
the material axis being **worse** than the entity axis on surfaces whose entity
already determines their material, not SAM 3 resolving anything.

So the honest reading of -0.218 dB is that it measures a degradation, and it is
reported here only so nobody quotes it as the material effect. The material
effect is +0.024 dB.

### 3.4 Cross capture agreement is much weaker on the material axis

Same station pairs, same overlap sets, same modal reduction:

| | entity axis | SAM 3 material axis |
|---|---|---|
| same sequence, overlap weighted | 0.842 | 0.587 |
| cross sequence, overlap weighted | 0.713 | 0.423 |
| cross sequence, worst pair | 0.646 | 0.245 |

Two independent captures of the same facade disagree on its material more often
than they agree. Some of that is expected, because the material vocabulary is
finer and an open vocabulary detector has no coverage guarantee, so a face can be
concept backed in one capture and fall through to the class prior in another. It
is still the weakest number in this document, and it means the material axis is
noisier evidence than the entity axis, not merely less consequential.

### 3.5 The nine station rung was built on two different ray grids

Rebuilding the conflict gated nine station set turned up a defect in the stored
one. Eight of its nine stations were cast at `--grid-height 1024` and the ninth,
`678330966745190`, at the parser default 1536, because it was appended to the
file by a separate script rather than rebuilt with the others. It carries
3,799,663 rays against 1,688,755 for the same station at 1024, a factor of
2.25 = (1536/1024)², and it therefore sees 191 faces the other eight stations'
grid would have missed.

The rebuild here casts all nine at 1024. Its first eight stations are bit
identical to the stored file's, and on the ninth the two grids agree on the
modal class of 99.45 % of the 2559 faces both see. Coverage drops from 11.019 %
to 10.982 % of area, brick from 8787 to 8689 triangles. The exposure numbers do
not move: the uniform grid rebuild gives +0.352 dB isotropic and +0.368 dB
rooftop, against +0.350 and +0.364 for the stored mixed grid file, with 16 and 8
standpoints past 1 dB against 17 and 8. So this is a provenance defect rather
than a numerical one, but the stored
`walk_semantic_conflict9.npz` should be replaced by the uniform grid rebuild now
in `outputs/walk_korenmarkt/`.

---

## 4. What this does and does not license

**Licensed.** At 15 GHz, in this square, over 120 pedestrian standpoints, with
10.6 % of scene area carrying street level image evidence, the choice between the
Vistas material prior and an open vocabulary material segmentation on the facades
does not move the exposure distribution. A cross city table that binds materials
geometrically is not hiding a material sensitivity of the size the ladder itself
spans.

**Not licensed.** This is one square at one carrier. It says nothing about a
scene dominated by metal cladding or glass curtain wall, where the entity prior's
brick default would be wrong on most of the facade rather than on 28.5 % of it,
and where the tested swap is brick to metal, a 9.67 dB reflectance change, rather
than brick to glass at 2.35 dB. Korenmarkt is a historic masonry square and the
prior is close to right there. The correct statement is that the material axis
does not move exposure **where the prior is already approximately correct**, and
the study has not found a square where it is not.

It also says nothing about roofs, courtyards and rear elevations, which are 55 %
of the surface and which no panorama count reaches.

---

## 5. Replacement text for PAPER_METHODS.md

Another agent owns that file. Below is the exact text to merge.

> **Old illumination law, see `LAW_CHANGE.md`.** The text below prints rooftop and street
> small cell decibels straight into the paper. The sentences survive, those numbers do
> not, so they have to be recomputed before this block is merged.

### 5.1 Replaces the block headed "#### What this ladder does not test" in section 9.3

```markdown
#### The material axis, tested

The ladder above varies entity coverage. Whether resolving brick against glass on
the same facade also moves exposure is a separate question, and it was untested
until 2026-08-02. It is now tested and the answer is a stronger null.

`semantics.py` runs a cascade. Mask2Former on Mapillary Vistas owns the entity
axis, and SAM 3 owns the material axis, because Vistas has a single `Building`
class covering brick, render, ashlar, glass curtain wall and metal cladding,
whose permittivity and roughness are not close to each other. The published
ladder ran `mask2former` alone on all eight walk stations, so `bind_from_walk`
mapped the Vistas entity through a fixed $p(\text{material}\mid\text{entity})$
table and took the argmax. `Building` resolves to `brick` deterministically, and
`Building` is **74.3 %** of the face observations the eight stations bind. In
that binding `semantic_glass` claims 1 triangle of 157,862 and
`semantic_plasterboard` claims none.

The hybrid backend has now been run on all eight stations, with the dense pass
reused from cache so the entity axis is byte identical and only the material axis
is new. Pooled over the eight, SAM 3 splits the `Building` and `Wall` pixels
59.8 % brick, 23.0 % glass, 14.4 % plasterboard and 1.8 % marble, and 28.5 % of
the facade area the entity axis called brick is reassigned: 11.9 % to glass,
9.5 % to plasterboard, 4.8 % to marble. `semantic_glass` goes from 1 triangle to
958 and `semantic_plasterboard` from 0 to 653. At 15 GHz brick to glass is
+2.35 dB in normal incidence reflectance and specular rather than rough, and
brick to plasterboard is -2.49 dB.

Rebinding those facades and rerunning the same 120 standpoints:

| illumination | entity axis | SAM 3 material on the facades | shift | standpoints $>0.5$ dB | worst standpoint |
|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3379 | **0.024 dB** | **0 of 120** | 0.110 dB |
| rooftop, corrected | 0.2354 | 0.2369 | **0.029 dB** | **0 of 120** | 0.193 dB |
| street small cell | 0.0984 | 0.0989 | **0.022 dB** | 1 of 120 | 0.929 dB |

Against 5th to 95th percentile spreads of 3.9 dB isotropic, 8.4 dB rooftop and
16.7 dB street small cell in those same distributions, and against the
1.98 dB the worst standpoint moves when entity coverage goes from 0 to 10.6 %,
material discrimination on the facades is not a term in this problem. Repeating
it on the nine conflict gated stations gives 0.023 dB isotropic and 0.024 dB
rooftop with the same 0 of 120, so the null does not depend on which walk set is
used.

**One measurement in this experiment moves and must not be misread.** Replacing
the *whole* material field with the SAM 3 axis, rather than only the facades,
shifts the isotropic median by -0.218 dB and moves 15 of 120 standpoints by more
than 1 dB. That is not material discrimination. It is the material axis
overwriting surfaces whose entity already determines their material: 932 m² the
entity called metal, 982 m² marble, 306 m² vegetation and 177 m² asphalt all flow
into brick, and metal to brick alone is a 9.67 dB reflectance drop on poles and
street furniture. Measured on the axis it is competent at, the open vocabulary
pass is worse than the class prior. So the conclusion is the same one section 9.3
already reached, now confirmed on the second axis: **entity segmentation carries
the material field, and material segmentation on top of it does not move
exposure.**

Cross capture agreement is the weakest number in the experiment. Independent
captures of the same facade agree on the entity 71.3 % of the time across
sequences and on the material only 42.3 %, with a worst pair at 24.5 %. The
material axis is therefore noisier evidence as well as less consequential
evidence, and a study that needed material at higher confidence would need more
than one detector.

This result is bounded by the square it was measured in. Korenmarkt is historic
masonry, so the `Building` prior's brick default is approximately right and the
tested swap is brick to glass at 2.35 dB. A square of metal cladding or glass
curtain wall would test brick to metal at 9.67 dB, and nothing here licenses that
case. The full run is in `SAM3_LADDER.md` and
`outputs/exposure_korenmarkt/sam3lad_*`.

One limit stands unchanged. The ladder spans 0 to 11.0 % of area, which is as far
as street level capture reaches, and it licenses nothing about a fully evidence
bound scene. Roofs, courtyards and rear elevations are 55 % of the surface and no
panorama count reaches them.
```

### 5.2 Replaces the "Section 9.3, material axis" row of the section 11 table

```markdown
| Section 9.3, material axis | **tested, and the null holds.** SAM 3 now runs on all eight walk stations. It reassigns 28.5 % of the facade area the entity prior called brick, putting 958 triangles on glass and 653 on plasterboard against 1 and 0 before, and the exposure distribution moves 0.024 dB isotropic and 0.029 dB rooftop with 0 of 120 standpoints moving as much as 0.5 dB, and 0.023 and 0.024 dB on the nine station set. Bounded to a masonry square: the tested swap is brick to glass at 2.35 dB, not brick to metal at 9.67 dB |
```

---

## 6. Artefacts

| path | what |
|---|---|
| `data/panoramas/korenmarkt_walk/walk_*/semantics/` | ten panoramas re-segmented with `--backend hybrid`, entity axis unchanged |
| `outputs/walk_korenmarkt/walk_semantic.npz` | entity axis bit identical to the published file, plus `modal_material`, `material_counts`, `concept_rays`, `material_names` |
| `outputs/walk_korenmarkt/walk_semantic.json` | adds a `material` block: per station backend, vocabulary, material share, concept backed ray fraction and material agreement |
| `outputs/walk_korenmarkt/walk_semantic_grid1536.npz` | the 1536 grid rebuild, kept as a ray density sensitivity |
| `outputs/walk_korenmarkt/walk_semantic_conflict9.npz` | the conflict gated nine station set, all nine at grid 1024, replacing the mixed grid file of section 3.5 |
| `outputs/walk_korenmarkt/walk_semantic_conflict9_tenstation.json` | the ten station manifest it was subset from, `--max-residual-deg 6.4`, all ten hybrid |
| `outputs/walk_korenmarkt/_pre_sam3/` | the pre run files, for the bit identity check |
| `outputs/exposure_korenmarkt/sam3lad_*` | every rung of this document, 120 standpoints each: `geometric`, `semantic`, `walk`, `walk9`, `walk_facade`, `walk9_facade`, `walk_sam3`, `walk_sam3mix`, `walk_matched` |

`outputs/korenmarkt_fishnet_sam3/` was not touched. It holds the mesh cutting
experiment on the single hero panorama and sits on a different path to the mesh
than the walk binding does, so extending it would have measured a second thing
rather than the material axis.

Code touched: `build_walk_twin.py` (material raster through the same ray cast,
material agreement), `semantic_twin/propagation/semantic_binding.py`
(`bind_from_walk_material`), `run_exposure.py` (four new `--materials` modes).
`bind_from_walk` is untouched, which is why the entity rung reproduces bit for
bit.

### A note on reproducibility that came out of this run

The published `clean_geometric`, `clean_semantic`, `clean_walk8` and
`clean_walk9` runs were produced by a working tree carrying a fourth illumination
model, `rooftop_fixed_height`, that is not at HEAD and is not in git history for
`run_exposure.py`. Re-running `--materials geometric` at HEAD does not reproduce
them: the isotropic median matches to three digits but individual standpoints
differ by up to 0.011 dB isotropic, 0.034 dB rooftop and 0.614 dB street small
cell. Every rung in this document was therefore re-run at HEAD rather than
compared against the stored files.

The tracer itself is exactly deterministic. The same command at HEAD on two
different machines with different core counts, one 4 core and one 8 core, gives
bit identical `chi_isotropic`, `chi_rooftop`, `chi_street_small_cell` and
`sky_fraction` at every standpoint, so the differences above are code state and
nothing else.
