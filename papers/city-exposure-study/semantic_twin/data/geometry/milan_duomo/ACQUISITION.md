# Piazza del Duomo, Milan acquisition

Second site for the panorama-driven semantic twin, after Korenmarkt in Ghent. This records what was
acquired on 2026-08-01, the numbers that were measured rather than assumed, and the three defects that
the result is currently carrying.

Site centre and ENU origin: 45.4642 N, 9.1900 E, ellipsoid height 0.

## What was acquired

| Artifact | Path |
| --- | --- |
| Scene config | `config/milan_duomo.json` |
| Support mesh | `data/geometry/milan_duomo/inhouse_leaf_170m.ply` |
| Mesh provenance | `data/geometry/milan_duomo/inhouse_leaf_170m.json` |
| 200 m reference mesh | `data/geometry/milan_duomo/inhouse_leaf_200m.ply` and `.json` |
| Panorama | `data/panoramas/milan_duomo/panorama_z5.jpg` |
| Panorama metadata | `data/panoramas/milan_duomo/metadata.json`, `session.json`, `pose_initial.json` |
| Aligned pose | `data/panoramas/milan_duomo/alignment/pose_aligned.json` |
| Seed study | `data/panoramas/milan_duomo/alignment/skyline_seed_study.json` |
| Skyline diagnostic | `data/panoramas/milan_duomo/alignment/skyline_alignment.jpg` |
| Alignment figures | `data/panoramas/milan_duomo/alignment/figures/` |

`data/panoramas/` is gitignored, so only the geometry and the config are tracked.

## Panorama

Official Google Street View capture `sqF_X7Lx3QDikLALUtGhMA`, dated 2014-09, at 45.464206509962104 N,
9.190013102997568 E. Copyright string "From the Owner, Photo by: Google". Four neighbour links.
Metadata heading 359.6104, tilt 85.794815, roll 354.46985.

Zoom 5 gives 13312 x 6656, which is 36.98 pixels per degree. The grid is 26 x 13 = 338 tiles of
512 x 512. All 338 were fetched, all decoded, no tile is missing, and no two tiles have identical
bytes, so nothing was silently duplicated to fill a hole. The stitched image is exactly 13312 x 6656.
Tile cache 5.95 MB, stitched JPEG 14.37 MB.

## Ground height, and what `camera_ground_z_m` actually is

`camera_ground_z_m` is one scene-wide constant in the current code. It is not a terrain model. The
value shipped here is the median topmost tile surface over a 13 x 13 grid spanning 6 x 6 m centred on
the panorama's own ENU position (1.025, 0.724):

```
samples 169   min 162.873   median 162.939   mean 162.938   max 162.995   std 0.032
```

So `camera_ground_z_m = 162.93862133337055` m, an ellipsoidal height, and the initial camera altitude
is that plus `camera_height_m = 2.5`. The pavement is flat enough here that the measurement is
unambiguous to about 3 cm, but the number describes one square of pavement, not the square. Any later
panorama on the cathedral steps or under the Galleria arch will inherit a biased altitude from it.

The same procedure applied to the shipped Korenmarkt mesh at the Korenmarkt panorama position returns
50.870 m against the 50.837 m in `config/korenmarkt.json`, a 3.3 cm agreement, so the method
reproduces how the existing site was derived.

Cross-check that does *not* agree: the Street View metadata reports
`originalElevationAboveEgm96 = 132.221` m. Combined with the tile-derived 162.939 m ellipsoidal that
implies an EGM96 geoid undulation of 30.7 m at Milan. The identical computation at Korenmarkt gives
42.9 m, which is right for Belgium, whereas published EGM96 undulation for the Po plain is nearer
46 to 48 m. One of the two Milan numbers is off by roughly 15 m and I could not settle which offline,
since `pyproj` and a geoid grid are not installed here. The tile geometry is the more plausible of the
two: the mesh puts the cathedral's spire tip at 272.15 m, which is 109.2 m above the sampled pavement
against a true height of 108.5 m. It does not affect internal consistency, because both the mesh and
the camera altitude come from the same tile geometry and the metadata elevation is never used.

## Tiles

Two pulls were made. The first is superseded and is recorded only because it was paid for.

| Pull | Radius | Leaf tiles | Requests | Bytes | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | 200 m | 77 | 160 | 11,464,542 | superseded, ROI defect below |
| 2 | 320 m | 342 | 691 | 51,736,536 | used |

Total tile API usage 419 leaf GLBs, 851 requests, 63.20 MB. Panorama API usage on top of that:
338 tile requests plus 2 `createSession` and 2 `metadata` calls, 5.95 MB. Caps were passed explicitly
on both pulls, `--max-requests 400 --max-bytes 80000000` and `--max-requests 1500 --max-bytes
250000000`, and neither was reached.

Every leaf reports geometric error 2.006368774808128 m. That is the global constant of the tile LOD
scheme, identical at every site probed, and it is not a Milan-specific quality result.

### Why 320 m and not 200 m

`download_inhouse_tiles.py` centres its region of interest on the ellipsoid, at
`llh_to_ecef(lat, lon)` with height zero, and then tests bounding volumes as a 3D distance against
`radius_m`. The horizontal reach at street level is therefore `sqrt(radius^2 - h^2)`, with `h` the
site's ellipsoidal height, and nothing above `z = radius` is inside the ball at all. At Ghent, with
`h` near 50 m, a nominal 200 m ball still reaches 194 m horizontally and the defect is invisible.
Piazza del Duomo sits at `h = 162.94 m`, measured from the tiles as above, so:

| Radius | Horizontal reach at pavement | Height above ground at centre | at 130 m out | at 160 m out |
| --- | --- | --- | --- | --- |
| 200 m | 116.0 m | 37.1 m | ball does not reach the ground | ball does not reach the ground |
| 258 m | 200.0 m | 95.1 m | 59.9 m | 39.5 m |
| 320 m | 275.4 m | 157.1 m | 129.5 m | 114.2 m |

A nominal 200 m pull at this site does not reach ground level anywhere beyond 116 m, and it truncates
the cathedral: the first pull's mesh topped out at 226.16 m, whereas the 320 m pull reaches 272.15 m
and captures the whole spire. Cropped at the same 200 m the first pull kept 233,997 triangles and the
second kept 476,334, so the broken region of interest was discarding half the geometry inside the
crop and everything it did keep beyond 116 m was accidental tile-bounding-box overshoot.

320 m was chosen over the minimal `sqrt(200^2 + 162.94^2) = 258` m so that the ball still clears
114 m above ground at the 160 m ring, which is what the crop study below needed. Cost of the choice
was 265 extra leaf tiles and 40 MB.

## Support mesh and crop radius

Build command, worth keeping because the mesh will need rebuilding once the precision defect below is
fixed:

```
~/blender-4.5/blender --background --python build_inhouse_mesh.py -- \
  --tiles <tiles dir> \
  --out data/geometry/milan_duomo/inhouse_leaf_170m.ply \
  --crop-radius-m 170
```

Shipped mesh: 338,787 triangles, 442,042 vertices, 9.71 MB PLY, bbox
(-169.79, -169.85, 101.72) to (169.91, 169.91, 272.15) m in local ENU.

Crop radius was chosen by the criterion `DESIGN.md` records for Korenmarkt: keep at least 99% of the
200 m projection in every validation view. Coverage is the fraction of covered pixels in the 1024 x
1024 Blender render from the recovered camera at panorama yaw 0, 90, 180 and 270, and the crops below
200 m are exact subsets, so retained fraction and recall of the 200 m mask are the same number.

| Crop | Triangles | yaw 0 | yaw 90 | yaw 180 | yaw 270 |
| --- | --- | --- | --- | --- | --- |
| 200 m | 476,334 | 100.00% | 100.00% | 100.00% | 100.00% |
| 180 m | 380,250 | 100.00% | 100.00% | 99.95% | 99.57% |
| **170 m** | **338,787** | **100.00%** | **100.00%** | **99.88%** | **99.12%** |
| 160 m | 295,700 | 100.00% | 100.00% | 99.87% | 98.43% |
| 130 m | 174,485 | 100.00% | 98.84% | 95.06% | 97.17% |
| 100 m | 83,723 | 99.66% | 95.71% | 94.83% | 86.90% |
| 60 m | 10,156 | 67.73% | 93.49% | 73.83% | 80.74% |

170 m is the smallest radius that clears 99% in all four views, so that is the shipped mesh.

Korenmarkt's 130 m does not transfer. Piazza del Duomo is roughly 215 by 90 m and the camera sits near
its centre, so the ring of facades is already 60 to 110 m away and the streets radiating off the
square, Corso Vittorio Emanuele II to the east and the via Torino and via Mazzini mouths to the
south-west, put load-bearing silhouette at 130 to 170 m. At 130 m the yaw 180 view loses 4.9% of its
geometry and yaw 270 loses 2.8%, both of which are visible building fronts rather than clutter. The
site is simply bigger than the Ghent one, and the crop has to follow the square.

## Registration

Segmentation for the sky mask was run on CPU with the repository's own Mask2Former Mapillary Vistas
baseline, 26 perspective views at 1024 x 1024 fused to an 8192 x 4096 equirectangular label map. No
GPU work and no substitute segmenter.

Shipped pose, `alignment/pose_aligned.json`, fitted against the 170 m mesh with the shipped seed:

```
mean robust skyline residual   1.054 deg
translation correction         (+0.708, +0.114, -1.470) m
yaw correction                 -0.974 deg
total pitch / roll             -4.404 / 355.722 deg
```

References: 2.83 deg for the Korenmarkt Street View panorama and 5.81 deg for a Mapillary panorama at
the same site. Milan is materially *better*, not worse, so the 2014 imagery date did not degrade the
skyline fit. That is expected on reflection, since the skyline is the one part of the scene that is
stable across a twelve-year gap. The foreground is not: the panorama shows a tower crane and full
scaffolding over the Galleria's north wing that are absent from the current tile mesh, which is
exactly the failure mode to watch when this panorama is later used for facade semantics rather than
for pose.

The site also flatters the method. The square is ringed by tall continuous cornice lines and the
cathedral's pinnacle field, all well separated from the camera, which gives a high-contrast sky
boundary over most of the azimuth range: 1003 of 1024 azimuth bins had structural support, against
930 at Korenmarkt.

### The residual is not an accuracy estimate

`check_skyline_seeds.py` repeats the identical objective on the identical observation from 8 seeds.

Shipped `dz` bounds `(-1.5, 3.0)`:

```
residual   mean 1.028 deg, std 0.015, range 1.007 to 1.054
dx         mean +0.850 m, std 0.273
dy         mean +0.219 m, std 0.311
dz         mean -1.481 m, std 0.018
yaw        mean -0.673 deg, std 0.210
```

**All 8 of 8 seeds land within 0.1 m of the `-1.5` floor.** The recovered altitude is therefore set by
the bound and not by the data, and it should not be trusted. This matches every previously shipped
pose in this repository.

Relaxing the bound to `(-12.0, 12.0)`, as a diagnostic only:

```
residual   mean 0.858 deg, std 0.010
dz         mean -2.691 m, std 0.140    (no seed near either bound)
yaw        mean -0.348 deg, std 0.252
```

The residual improves, but the answer is not more physical. `dz = -2.69` puts the camera at 162.75 m,
which is 0.19 m *below* the pavement the same tiles report, for a vehicle-roof camera that should sit
about 2.5 m above it. The optimiser is buying residual by sinking the camera, because lowering it
raises every modelled elevation angle at once. The skyline diagnostic shows why that helps: the
modelled silhouette sits systematically a little below the segmented one, since the photogrammetry
rounds off balustrades, statues and pinnacle tips. `dz` is absorbing a geometry bias that is not a
pose error. So the tight bound is not merely conservative here, it is masking a systematic error, and
relaxing it alone would be the wrong fix. The same caution probably applies to the reported Korenmarkt
improvement from 2.97 to 2.03 deg under a relaxed bound.

Horizontal and yaw spread across seeds, roughly 0.3 m and 0.2 deg, is the more honest uncertainty
figure for this pose.

For reference, the same fit against the 200 m mesh gives 0.948 deg with the shipped seed and
0.952 +/- 0.008 deg across seeds. The shipped pose uses the 170 m mesh so that the pose and the
scene's `source_mesh` are consistent.

### Visual verdict

Looked at `alignment/figures/alignment_overlays_grid.jpg`, the per-view overlays at full resolution,
and `alignment/skyline_alignment.jpg`.

The registration is good, and better than the residual alone suggests. On the cathedral facade the
modelled silhouette resolves individual pinnacles and each modelled pinnacle lands on the real one,
which is a far stronger statement than a matching envelope. On the Palazzo dei Portici Settentrionali
the modelled edge follows the balustrade for its whole run within about 2 to 4 pixels at 1024 px over
90 deg, so 0.2 to 0.35 deg. Yaw 180 and yaw 270 track the Arengario and the north-west block cleanly.

Two honest qualifications. First, there is a consistent vertical bias: the modelled silhouette sits a
few pixels high across the cathedral's pinnacle group and along the palazzo balustrade, the same bias
that is pinning `dz` to its bound, so the camera is probably still a little too low. Second, on the
right of the yaw 0 view the modelled edge cuts across the Galleria's scaffolding rather than following
anything in the photograph, because the mesh is current and the scaffolding is from 2014. Registration
against the skyline is unaffected, but that region should not be trusted for facade evidence.

The one clear absence, the dark tower behind the yaw 180 rooftops with no modelled silhouette, is
Torre Velasca at roughly 500 m. It is correctly outside the 170 m crop.

## Known defects carried by this acquisition

1. **Ellipsoid-centred region of interest.** `download_inhouse_tiles.py` centres its ball at ellipsoid
   height zero, so `--radius-m` is not a horizontal radius. Compensated here by requesting 320 m for
   275 m of horizontal reach. Not fixed in the module, and the two-pull request count above is the
   price of discovering it late.
2. **Single-precision ECEF to ENU.** `build_inhouse_mesh.py` applies the ECEF-to-ENU transform through
   `mathutils.Matrix` and `Object.matrix_world`, both float32, while ECEF translations are around
   6.4e6 m. On the Korenmarkt pull this was measured at about 0.22 m of mean rigid shift and up to
   0.44 m of differential tile-to-tile misregistration, so neighbouring photogrammetry tiles seam
   against each other. The Milan mesh carries the same defect and I have not attempted to work around
   it. Practical consequence for the numbers above: up to roughly half a metre of the skyline misfit
   may be mesh seaming rather than pose error, which is a real fraction of the 1.05 deg residual at
   the 60 to 110 m facade distances here. Rebuild with the command in the crop section once the module
   is fixed.
3. **Scene-wide `camera_ground_z_m`.** One constant for the whole site, as described above.
4. **Geoid inconsistency.** Tile geometry and Street View's `elevationAboveEgm96` disagree by about
   15 m at this site and agree at Korenmarkt. Unresolved. Harmless today because the metadata
   elevation is never used, but it should be settled before any absolute-altitude claim is made.

## Reproduce

```
export GOOGLE_API_KEY=...   # or GOOGLE_MAPS_API_KEY

python download_inhouse_tiles.py --lat 45.4642 --lon 9.1900 --radius-m 320 \
  --geometric-error-cutoff-m 0 --max-requests 1500 --max-bytes 250000000 --out <tiles>

~/blender-4.5/blender --background --python build_inhouse_mesh.py -- --tiles <tiles> \
  --out data/geometry/milan_duomo/inhouse_leaf_170m.ply --crop-radius-m 170

python -m semantic_twin.panorama --scene config/milan_duomo.json --zoom 5

python -m semantic_twin.semantics --panorama data/panoramas/milan_duomo/panorama_z5.jpg \
  --out data/panoramas/milan_duomo/semantics --device cpu

python -m semantic_twin.align_skyline \
  --mesh data/geometry/milan_duomo/inhouse_leaf_170m.ply \
  --semantics data/panoramas/milan_duomo/semantics/panorama_semantics.npz \
  --semantics-json data/panoramas/milan_duomo/semantics/semantics.json \
  --pose data/panoramas/milan_duomo/pose_initial.json \
  --panorama data/panoramas/milan_duomo/panorama_z5.jpg \
  --out data/panoramas/milan_duomo/alignment

python check_skyline_seeds.py \
  --mesh data/geometry/milan_duomo/inhouse_leaf_170m.ply \
  --semantics data/panoramas/milan_duomo/semantics/panorama_semantics.npz \
  --semantics-json data/panoramas/milan_duomo/semantics/semantics.json \
  --pose data/panoramas/milan_duomo/pose_initial.json \
  --out data/panoramas/milan_duomo/alignment/skyline_seed_study.json

~/blender-4.5/blender --background --python render_blender_alignment.py -- \
  --mesh data/geometry/milan_duomo/inhouse_leaf_170m.ply \
  --pose data/panoramas/milan_duomo/alignment/pose_aligned.json \
  --out data/panoramas/milan_duomo/alignment/blender
```

The last step writes one mesh render per yaw next to the matching inference crop,
which is how the registration is inspected. There is no figure script any more:
`make_alignment_figures.py` composited those two directories into overlay JPEGs
and was deleted with the rest of the one-off figure code.

Note that `camera_ground_z_m` is circular on a fresh site: the mesh has to exist before it can be
measured, and `semantic_twin.panorama` needs it in the config before it can write `pose_initial.json`.
Build the mesh first, sample the ground under the panorama's reported position, write the config, then
run the panorama step.
