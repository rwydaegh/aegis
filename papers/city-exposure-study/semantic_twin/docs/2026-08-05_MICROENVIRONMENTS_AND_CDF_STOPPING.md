# Microenvironment audit and walk-CDF stopping rule

Date: 2026-08-05

The checkout supports a useful four-site semantic comparison: Korenmarkt, Prague
Staromestske, Tokyo Hachiko, and Mexico Zocalo. These sites have 250 m meshes,
panorama-derived walk bindings, and matched four-seed exposure runs. Only Hachiko
is a true street canyon in this set. A strict request for several non-plaza street
types needs more registration work.

This audit uses labels already stored in
`outputs/city_screening/screening.json`. It does not infer a building type from a
city name or an image.

## Recommended comparison set

| Site | Stored built-form evidence | Runnable evidence | Scientific role | Main limit |
| --- | --- | --- | --- | --- |
| Korenmarkt | Medieval brick square and car-track capture | 250 m f64 mesh with 617,091 triangles. The v1 atlas uses 9 cameras. Four matched runs use 80 locations, 200,000 rays, 512 cells, and seeds 7 to 10. The final route uses 5 cameras, 8 interpolated points, 1.6 million rays, and 4,096 cells. | Current high-fidelity anchor | This is the sealed v1 baseline. It is not binding-matched to the legacy city runs. |
| Prague Staromestske | Irregular medieval square with gothic towers and a plaster and stone mix | 250 m f64 mesh with 664,619 triangles. The strict v2 gate admits 12 of 14 stations. Four matched walk runs use the same 80-location, 200,000-ray, 512-cell design. | Irregular historic enclosure | The current pose diagnostics name the 130 m support mesh. A 250 m registration pass is still required. |
| Tokyo Hachiko | Dense glass canyon with a scramble crossing and heavy signage | 250 m f64 mesh with 797,615 triangles. The old binding used three stations. Strict v2 admission retains two. | Dense canyon diagnostic | Two cameras cover 2.72 percent of faces and 7.19 percent of area. This is too thin for a production material claim. |
| Mexico Zocalo | Very large open plaza with volcanic stone and low surrounding blocks | 250 m f64 mesh with 707,812 triangles. The sealed v1 semantic binding uses 12 of 14 stations. Strict v2 admits 9. Four matched walk runs use the common design. | Open reference endpoint | This is an open plaza, not a non-plaza street type. |

The screening inventory also records useful acquisition context. The total
panorama counts are 66 for Korenmarkt, 228 for Prague, 277 for Hachiko, and 388
for Zocalo. Their selected walk candidate counts are 14, 147, 105, and 253,
respectively. The semantic source binding uses only the registered and admitted
subset, so the larger screening counts do not imply matching semantic coverage.

## Strict non-plaza reading

Hachiko is the only true canyon in the matched set, but it is not production
ready under strict admission. Times Square
is the strongest second canyon candidate. Its stored label is "deep glass and LED
canyon, tallest aspect ratio in the set." It also has a 250 m mesh with 1,064,389
triangles. The geometry inventory gives a median sky fraction of 0.121 and a
214.8 m skyline height, which makes it a strong enclosure extreme.

Times Square is currently suitable only as a geometry-controlled diagnostic. Its
site registration residual is about 10 degrees, above the 4 degree semantic gate,
and no site-semantic binding was produced. Existing exposure runs use the generic
`geometric` binding and force the facade class to brick. They cannot test a glass
and LED material claim. Repairing the registration would add a second true canyon
without changing the study question.

London is less ready because it lacks a site registration summary and site
semantic output. Krakow and Toulouse have acquisition or anchor defects in the
current artifacts. They should not enter a production comparison yet.

## Binding choice

There are two valid comparisons, and they answer different questions.

1. Use the common `geometric` binding for a controlled morphology study. Materials
   remain generic, so conclusions should be about geometry and enclosure.

2. Use the matched `walk` runs for the four semantic sites, or rebuild the same
   atlas design for every site, for a material-aware study.

The final Korenmarkt result uses an `atlas` binding. Its absolute difference from
a legacy `walk` or `geometric` city run cannot be assigned to built form alone.

## Strict production status

Both candidate sites have valid format-version-3 meshes at 250 m. Old notes
about single-precision defects are stale. The unsuffixed and `_f64` 250 m files
are byte-identical at both sites.

| Site | Exact 250 m exposure mesh | SHA-256 | Current route preview |
| --- | --- | --- | --- |
| Tokyo Hachiko | `data/geometry/tokyo_hachiko/inhouse_leaf_250m_f64.ply` | `1bccad9bedd7c1764e15d06042b0340530e795396f15f6d3fc40a759f3249e71` | Strict v2 retains 2 cameras, 44.126 m apart in plan. The old 23-point route and its hash belong to the three-camera v1 input and are not a v2 route. |
| Prague Staromestske | `data/geometry/prague_staromestske/inhouse_leaf_250m_f64.ply` | `a2533b5d589f3604b63e905a5673873df2db7a41d396c8cef03389e72d08b6f4` | Strict v2 admits 12 cameras. The current 68-point preview remains preproduction until the poses are fitted and diagnosed against the 250 m mesh. |

### Completed evidence

Hachiko's residuals are 1.420, 3.700, and 3.082 degrees. The middle pose reached
the vertical search bound. Admission v2 rejects it even though its residual is
below 4 degrees. The two retained cameras cover 21,673 faces, or 2.72 percent of
the mesh, and 7.19 percent of its area. The median support remains one camera per
seen face. This two-camera route is a no-go for production. The existing binding
hashes, `0c5541dbcee2d94eb0e24b82946ca429cdece2e059dc8b255e726905a2637d81`
for NPZ and `bb9672208d05728f75934febb61c8c48b899ff0e8076f97a65049e9fa58cbdb6`
for JSON, describe the three-camera v1 artifact.

Prague passes strict v2 with 12 cameras. `pano_03` fails the residual gate and
`pano_05` has the paired inside-geometry signature: a sky-hit fraction of 1.0 at
a median range of 0.559 m. None of the 12 admitted cameras is at the altitude
bound. The current 250 m binding covers 6.71 percent of faces and 9.93 percent of
area. Its NPZ SHA-256 is
`fc01fdb06f51a900c3edb92f138d96abf36747b67915979ccade1166b4dd5147` and
its JSON SHA-256 is
`906a79e8246bd98239957c1289d36edd9ad263bea979744df6b75930e07d6bcf`.
The pose diagnostics still name the 130 m support mesh, so these are audited
preproduction hashes rather than a sealed 250 m contract.

Times Square is a no-go. All 14 residuals exceed 4 degrees, five fits end at the
altitude bound, and three cameras have the paired inside-geometry signature.
Widening the vertical search does not produce a useful interior optimum.

Korenmarkt remains the sealed admission-v1 baseline. Its atlas contains nine
admitted cameras and its final route uses five cameras over 13 standpoints.
Applying v2 to the stored fits would retain four atlas cameras and two route
cameras. Every removal is caused by the altitude-bound rule.

The final widened-bound audit is a no-go for promotion. It repeated the five
lower-bound fits over `[-2.0, 3.0]` m. An interior optimum had to remain at least
0.1 m from either bound. The exact results are:

| Camera | dz (m) | Residual (deg) | Height above pavement (m) | Sky-hit fraction | Median conflict range (m) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `korenmarkt` | -1.602588 | 1.192397 | 0.618412 | 0.060077 | 19.385696 | Interior, held for low height |
| `walk_03_706535575184668` | -1.735411 | 2.230664 | 0.764589 | 0.032775 | 20.567124 | Interior, held for low height |
| `walk_06_1419513849204492` | -1.993075 | 2.809796 | 0.506925 | 0.049745 | 16.892166 | At lower boundary |
| `walk_08_1019442960256615` | -1.918687 | 2.041920 | 0.581313 | 0.045199 | 18.171973 | At lower boundary |
| `walk_10_3367014310197013` | -1.904032 | 2.254061 | 0.595968 | 0.079447 | 18.535477 | At lower boundary |

The provider records a 2.5 m scene height for the walk cameras. The accepted
production route's non-bound anchors are 1.590 and 1.701 m above pavement. The
two widened interior fits are only 0.62 and 0.76 m high, so they remain on hold.

The boundary-only counterfactual reduces the route from five to three cameras
and from 13 to 8 standpoints, with five interpolated points. Holding the two low
cameras leaves two tied two-camera fragments and no unique continuation. The
current fragment ordering selects `walk_00` and `walk_01`, spans 8.05 m, and has
three standpoints. That is a material route change.

Full-sphere first-hit coverage also falls. The sealed nine-camera atlas covers
13,921 faces, 2.2559 percent of faces and 3.2497 percent of area. The six-camera
boundary counterfactual covers 11,686 faces, 1.8937 percent of faces and 2.7097
percent of area. The four-camera promotion hold covers 10,828 faces, 1.7547
percent of faces and 2.5577 percent of area. The sealed five-camera route union
covers 11,598 faces and 2.5791 percent of area. The three-camera counterfactual
covers 9,838 faces and 2.1801 percent of area. The current two-camera fragment
covers 9,105 faces and 2.2596 percent of area.

The accepted atlas and route remain unchanged under v1. Their atlas manifest,
atlas NPZ, and sealed route manifest SHA-256 values remain
`80d8f0bb448d6677fc29c9c51e81036e9b54913d52f1480030095ac16f08d783`,
`c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76`, and
`e87bd8e5db0308cfa9ad445c179a8464b19a7aaa8eaf2242fb1492c0eee75a9d`.

### Pending GPU work

Prague still needs a 250 m registration and diagnostic pass. Hachiko needs a
wider outdoor acquisition before another production attempt. Neither site has
the complete hybrid SAM3 RF-material product or a joint atlas. The SAM3 model
download also needs an authorized credential on the GPU host. Until that access
and the missing artifacts are present, both sites remain preproduction. No CUDA
reference or named production contract should be generated from the current
inputs.


## Exact next-site runnable input audit (walk-arm view, kept from the studio line at merge)

Tokyo Hachiko is the first non-plaza production site. Prague Staromestske is the
second contrast after Hachiko passes the stopping rule. Both have usable geometry
and camera registrations. Neither has a production material atlas yet.

The site configuration files still describe older 130 m mesh work and old
single-precision defects. Those notes are stale. The exposure resolver selects
the 250 m `_f64` mesh and requires mesh format version 3. The unsuffixed 250 m
files are byte-identical copies of the `_f64` files at both sites.

| Site | Exact exposure mesh | SHA-256 | Format and size |
| --- | --- | --- | --- |
| Tokyo Hachiko | `data/geometry/tokyo_hachiko/inhouse_leaf_250m_f64.ply` | `1bccad9bedd7c1764e15d06042b0340530e795396f15f6d3fc40a759f3249e71` | Version 3, 797,615 triangles, 1,034,677 vertices. Its sidecar SHA-256 is `1ecd79110351f4e8808c29272bc3375268715d18e45a5c2063a98805f8f17e03`. All 714 source objects used double precision and none used fallback placement. |
| Prague Staromestske | `data/geometry/prague_staromestske/inhouse_leaf_250m_f64.ply` | `a2533b5d589f3604b63e905a5673873df2db7a41d396c8cef03389e72d08b6f4` | Version 3, 664,619 triangles, 823,889 vertices. Its sidecar SHA-256 is `c69c5e3a6f23a412ea38946770f479eca32f354922aa23f6319b99da551e1174`. All 322 source objects used double precision and none used fallback placement. |

The admission gate is the same in `build_site_semantics.py` and
`build_surface_atlas.py`: skyline residual at most 4 degrees, sky conflict at
most 0.5 when the median conflict range is at least 2 m, grid height 1,536, and
128-row cast blocks.

Hachiko currently admits three of four actual `pano_` stations. They are
`pano_00_GR5jUP1WQSbKFJwS`, `pano_01_VBNtG0Y_-d3vtklg`, and
`pano_02_yBgJrdk6yBBnvYyF`. Their residuals are 1.420, 3.700, and 3.082 degrees.
Their sky-conflict fractions are 0.0158, 0.0749, and 0.0105. Station `pano_01`
passes the gate but its vertical search ended at the search bound, so the atlas
manifest should keep that warning visible. `pano_03_NCILawcpTxk3OjbQ` has no
complete registration or semantic product. The 13 `indoor_2018-05_*` folders are
rejected sky-fraction probes and are outside station discovery. They must stay
out of the atlas.

The current Hachiko poses record the 250 m support mesh. Its walk binding is
therefore crop-matched to the exposure mesh. The binding covers 3.19 percent of
faces and 8.05 percent of area, with a median of one supporting camera per seen
face. Its exact files are:

- `outputs/site_semantics/tokyo_hachiko/walk_semantic_250m.npz`, SHA-256
  `0c5541dbcee2d94eb0e24b82946ca429cdece2e059dc8b255e726905a2637d81`

- `outputs/site_semantics/tokyo_hachiko/walk_semantic_250m.json`, SHA-256
  `bb9672208d05728f75934febb61c8c48b899ff0e8076f97a65049e9fa58cbdb6`

Prague currently admits 12 of 14 actual panoramas. The admitted indices are 00,
01, 02, 04, and 06 through 13. `pano_03` fails with a 9.330 degree residual.
`pano_05` is inside geometry, with every tested sky direction hitting within a
median range of 0.559 m. The extra `walk_manifest.json` refusal in the binding
report is a discovery artifact, not a camera. The admitted residual range is
0.481 to 1.583 degrees. The admitted sky-conflict range is 0.00437 to 0.02460,
and no admitted vertical solution is at its search bound.

Prague's pose files name the valid 130 m format-v3 mesh in their sky-conflict
records and do not record a 250 m support mesh. Production needs one fresh 250 m
registration pass and a rebuilt binding before the admitted material-inference
input list is frozen. Its current binding covers 6.71 percent of faces and 9.93
percent of area, with a median of three supporting cameras per seen face. The
current files are:

- `outputs/site_semantics/prague_staromestske/walk_semantic_250m.npz`, SHA-256
  `fc01fdb06f51a900c3edb92f138d96abf36747b67915979ccade1166b4dd5147`

- `outputs/site_semantics/prague_staromestske/walk_semantic_250m.json`, SHA-256
  `906a79e8246bd98239957c1289d36edd9ad263bea979744df6b75930e07d6bcf`

These walk bindings contain rays and entity classes. They contain no RF material
axis. Every current admitted `semantics/semantics.json` at both sites records the
Mask2Former backend, immutable revision
`4772b6bf101d91f2534c106dc524d906aeb3c68a`, and provisional material hints.
There are no `semantics_sam3_*` directories and no
`joint_atlas_250m_r8.{npz,json}` files. `build_surface_atlas.py` will refuse both
sites until every selected camera has a hybrid product with the required
`rf_material` rasters.

### Route preview

A CPU-only LLVM preparation pass used the exact meshes above, the current
admission files, `walk=route`, `walk_path=links`, a 90 m radius, 6 m stride, and
seed 7. It did not trace paths or write output.

| Site | Camera order | Full route | Ground datum | Point-array SHA-256 |
| --- | --- | --- | --- | --- |
| Tokyo Hachiko | 01, 00, 02 | 23 points, made from 3 registered cameras and 20 stride points. Link-road length is 120.199 m and camera-hop length is 112.740 m. | 51.5966796875 m | `1034b4f23f688a69e293a1df689477307c414a22eb83f698104e7ff52463ea92` |
| Prague Staromestske | 04, 08, 12, 00, 10, 07, 01, 13, 06, 02, 09, 11 | 68 points, made from 12 registered cameras and 56 stride points. Link-road length is 339.557 m and camera-hop length is 320.882 m. | 236.650390625 m | `16c615490e53814d55d99ae859b28afb61f5782eb5338f303282046b6b8a1ed4` |

These are route previews. CUDA may change the cast ground coordinates by small
floating-point amounts. The sealed seed-7 CUDA generation is the production
authority. Keep `--locations 0` so every 6 m route point is traced. Forcing 13
points would discard much of each route and would no longer match the Korenmarkt
spacing rule. Weight sites equally in a pooled comparison so Prague's longer
route does not dominate.

### Shortest matched production path

Run these steps from `semantic_twin/` after the Korenmarkt campaign converges.
First repair Prague's crop match and rebuild its admission source:

```bash
.venv/bin/python reregister_site.py \
  --site prague_staromestske --crop-m 250
.venv/bin/python build_site_semantics.py \
  --site prague_staromestske --crop-m 250 --grid-height 1536 \
  --block-rows 128 --max-residual-deg 4 \
  --max-sky-conflict 0.5 --min-conflict-range-m 2
```

Read the admitted station list from each final binding. Run the same pinned
hybrid model used for the Korenmarkt walk. Its production panorama resolution was
4,096 by 2,048. The 8,192 default belongs to a different Korenmarkt plaza
product, so pass 4,096 explicitly here.

```bash
SITE=tokyo_hachiko
SEMANTICS_DIR=semantics_sam3_3c879f39826c281e_61id
jq -r '.stations_admitted[].station' \
  "outputs/site_semantics/${SITE}/walk_semantic_250m.json" |
while read -r STATION
do
  .venv/bin/python -m semantic_twin.cli.panorama \
    --panorama "data/panoramas/${SITE}/${STATION}/panorama_z5.jpg" \
    --out "data/panoramas/${SITE}/${STATION}/${SEMANTICS_DIR}" \
    --model facebook/mask2former-swin-large-mapillary-vistas-semantic \
    --dense-revision 4772b6bf101d91f2534c106dc524d906aeb3c68a \
    --backend hybrid --concepts config/semantic_concepts.json \
    --sam-revision 3c879f39826c281e95690f02c7821c4de09afae7 \
    --sam-repository-commit 96914d2425f90a64f45ca977c2b5165418099543 \
    --device cuda --inference-size 1536 --view-size 1536 \
    --concept-resolution 1008 --concept-threshold 0.35 \
    --prompt-batch 32 --output-width 4096 --production
done
```

Repeat that block with `SITE=prague_staromestske` after its rebuilt admission
file is final. The reviewed concept catalogue has file SHA-256
`75849c493f7c8f11839168875fd8f60fa569acb203750707f5703ae9b8cc3dac`
and parsed semantic SHA-256
`66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b`.
The pinned SAM checkpoint SHA-256 is
`9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e`.

Build each atlas with the same gate and resolution:

```bash
SITE=tokyo_hachiko
.venv/bin/python build_surface_atlas.py \
  --site "$SITE" --crop-m 250 --grid-height 1536 --block-rows 128 \
  --atlas-resolution 8 --max-residual-deg 4 --max-sky-conflict 0.5 \
  --min-conflict-range-m 2 --concepts config/semantic_concepts.json \
  --semantics-dirname semantics_sam3_3c879f39826c281e_61id
```

Repeat with `SITE=prague_staromestske`. Before tracing, check that the atlas JSON
records the mesh SHA-256 from the table above, the expected camera IDs, the
reviewed catalogue digest, and an empty
`admitted_without_complete_hybrid_product` list.

Generate Hachiko's sealed seed-7 reference first:

```bash
.venv/bin/python run_exposure.py \
  --site tokyo_hachiko --crop-m 250 --materials atlas \
  --atlas-npz outputs/site_semantics/tokyo_hachiko/joint_atlas_250m_r8.npz \
  --walk route --walk-path links --walk-radius-m 90 --walk-stride-m 6 \
  --locations 0 --frequency-ghz 15 --rays 1600000 --local-cells 4096 \
  --max-bounces 3 --seed 7 --variant cuda_ad_rgb \
  --transport-kernel drjit \
  --tag final_tokyo_hachiko_walk_drjit_atlas_4096_v1
```

At the current source revision, the unexposed CLI fields match Korenmarkt:
isotropic, rooftop, and street-small-cell laws, 1.5 m head height, roulette start
4, roulette floor 0.05, 1 mm ray lift, no range weighting, 400,000-ray batches,
and 18 exit bands. The output manifest records all of them. It also hashes the
mesh, atlas, surface binding, locations, and spectra, and records the Duke body
identity. The CDF loader adds exact body-mesh and IT'IS database hashes. Use a
distinct tag for Prague and replace only the site and atlas path.

The generic CDF runner can replay either sealed reference. Its named production
contract currently hard-codes Korenmarkt's hashes, run settings, and five-camera
plus eight-stride route. A custom contract skips those source-level Korenmarkt
pins. Production-grade city campaigns should add one named hash contract per site
after the seed-7 generation exists, then run `run_cdf_convergence.py --dry-run`
before CUDA preparation. Keep the same seeds 7 through 38, looks 16, 24, and 32,
bootstrap settings, and stopping thresholds. Run Hachiko to its stopping decision
before starting Prague.

The 4,096-cell choice transfers Korenmarkt's estimator-resolution protocol to the
new sites. It is not a new site-specific angular convergence proof. The full
replica stopping rule measures Monte Carlo uncertainty at that fixed resolution.

## Sequential stopping rule for a fixed walk

The independent Monte Carlo unit should be one complete walk replica with a new
base seed. Within a replica, standpoint `i` keeps the current deterministic seed
mapping `base_seed + 1000 * i`. The four 400,000-ray transfer chunks in the final
Korenmarkt run are implementation chunks, not independent replicas. They should
not be counted as four batches unless disjoint random streams and chunk-level
results are recorded and verified.

Use at least 16 complete replicas at the production setting of 1.6 million rays
and 4,096 cells. Treat 8 replicas as diagnostic. Check at 16, 24, and 32 replicas.
Stop after two consecutive checks pass. This makes 24 the earliest stopping point.
Cap the first campaign at 32 and report residual uncertainty if the rule still
fails.

At every check, average exposure in linear power across seeds for each standpoint.
Convert the resulting mean to dB. Do not average dB values. Resample complete base
seed replicas as clusters, while preserving all 13 standpoint values in each
resampled replica.

The confidence target is 95 percent over selection among the three formal
looks. Spend alpha equally over the fixed looks at 16, 24, and 32 replicas.
Each formal look therefore uses alpha 1/60 and a 59/60, or 98.333 percent,
joint max-t bootstrap band. A Bonferroni bound limits the chance that any formal
look family misses to 1/20 if each bootstrap band attains its nominal coverage.
The max-t bootstrap is approximate at finite replica count. This is nominal
familywise coverage rather than an exact finite-sample confidence sequence.
The 8-replica diagnostic has no role in this coverage claim or the stop.

Use one cluster resample and one studentized maximum for the whole bounded
family at a formal look. The family contains total susceptibility for all three
source laws, rooftop mean absorbed density, and every rooftop surface
absorbed-density mean. It also includes each fixed-route CDF rank and the
minimum, q10, q50, q90, and maximum summaries for the scalar curves. Direct
susceptibility stays outside this family because a true direct-path zero has no
finite dB value.

Require all three source laws to pass these alpha-spent bootstrap criteria:

- Across the 13 standpoints, the 90th percentile of per-standpoint confidence
  half-widths is at most 0.10 dB. The largest half-width is at most 0.15 dB.

- For the fixed-route CDF, the median half-width is at most 0.05 dB. The q10 and
  q90 half-widths are at most 0.10 dB. The minimum and maximum half-widths are at
  most 0.15 dB.

- Between consecutive checks, the one-dimensional Wasserstein distance is at most
  0.03 dB. The median moves by at most 0.03 dB. q10 and q90 move by at most 0.05
  dB. The minimum and maximum move by at most 0.10 dB.

Keep the minimum, second-lowest, second-highest, and maximum in the output. Do not
trim or winsorize endpoints. If body peak absorbed power is reported, apply a
0.15 dB maximum confidence half-width rule to it in the same joint family.
Define the published body-peak estimator as the maximum absorbed density of the
ensemble-mean angular spectrum. At level 2, average the retained per-replica
surface fields before taking that maximum. Do not average the per-replica
maxima. That order has a positive Jensen and peak-selection bias.

Build one simultaneous band over every surface mean, then project it through
the maximum. The body-peak lower bound is the maximum of the face lower bounds.
The upper bound is the maximum of the face upper bounds. This construction
still covers the peak when two or more faces tie, conditional on coverage of
the joint face band. Bootstrap winner fractions and leave-one-replica-out
winners are useful regularity diagnostics. They do not carry the formal
coverage claim.

Keep exact direct-path zeros in linear units. Report the fraction of fixed-route
standpoints whose direct estimate is zero as a probability atom at zero. Do not
add a logarithmic floor or pseudo-count. Report dB values only for positive
direct estimates and make no confidence claim for that diagnostic curve.

## What the 13-point CDF means

The final Korenmarkt walk covers 49.2 m with 13 frozen positions. Its empirical
CDF has steps of 1/13, or 0.0769. A p95 or p99 value is therefore an interpolation
near one endpoint. Report q10, q50, q90, and both endpoints as results conditional
on this fixed route.

The positions are spatially correlated. Extra ray seeds reduce Monte Carlo error,
but they do not add independent street samples. A population claim about a
microenvironment needs new route fragments. A reasonable exploratory minimum is
four separate fragments and at least 40 total positions, with equal fragment
weight. About 100 positions is a safer target for a p90 claim because it gives
roughly ten observations in the upper tenth. In a pooled city result, weight sites
or route fragments equally so that the longest walk does not dominate.

## Evidence behind the thresholds

The existing angular study supports the production resolution. At 4,096 cells,
the largest change in scalar chi from 800,000 to 1.6 million rays is 0.0041 dB,
while the peak direction can still move by 4.78 degrees. At 1.6 million rays, a
512-cell result differs from 4,096 cells by only 0.0048 dB in chi, but by as much
as 0.697 dB in top-one-percent share and 1.817 dB in peak angular density. The
4,096-cell setting matters for angular peaks and tails.

Existing 200,000-ray Monte Carlo runs also show why a four-seed CDF is too small.
Korenmarkt's 32-seed walk-median standard deviations are 0.003, 0.026, and 0.039
dB for isotropic, rooftop, and street laws. New York's eight-seed values are
0.008, 0.031, and 0.094 dB. Across the four matched Hachiko seeds, the street-law
walk median spans 0.853 dB, compared with 0.069 dB in Prague. These values are
diagnostics, not proof of convergence. They justify independent full-walk
replicas and an explicit tail-preserving stop.

Key artifacts are:

- `outputs/exposure_korenmarkt/final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz_manifest.json`

- `outputs/angular_convergence_4096_atlas_v2/`

- `outputs/site_semantics/<site>/walk_semantic_250m.json`

- `outputs/exposure_korenmarkt/ladder250_<site>_s<seed>_walk_15ghz_manifest.json`

- `outputs/city_screening/screening.json`
