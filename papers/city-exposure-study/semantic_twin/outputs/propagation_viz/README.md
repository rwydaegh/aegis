# Korenmarkt propagation visualization

The current presentation artifact is `korenmarkt_atlas_4096_final.blend`. It was
built from the exact 15 GHz production run with digest `af8b9fc7cf3e`. The run
contains 13 exposure standpoints, a 4,096-cell angular grid, and a 1.6 million-ray
production trace at each standpoint. The blend uses a separate bounded 1,200-ray
trace only for visible path lines. That small trace supplies no exposure values.

The final blend is 93,811,902 bytes. Its SHA-256 is
`c364620f62f8befa91caca7e6bd478741c6b86306b568c9292e935ba1388871a`.

## Start here

Open scene `01 VIEW - exposure overview`. Scenes `01` through `12` are prepared
views. Scene `99 DATA - raw layers and audit` contains the complete archive.

The most important audit scenes are:

| Scene | What it shows |
| --- | --- |
| `03 VIEW - arrival angular shape` | A smooth display of the hero arrival spectrum. |
| `06 VIEW - material binding` | Whole-face geometric material fallback beside fused and legacy image evidence. |
| `08 VIEW - evidence audit` | Accepted, refused, depth, and fused evidence as separate layers. |
| `09 VIEW - full traced support` | The full 250 m transport support and the closer 110 m display boundary. |
| `10 VIEW - all-camera fused surface` | The joint atlas made from all nine admitted 360 captures. |
| `11 VIEW - final transport decision` | Final state, host-gated material mixture, and geometric fallback for every atlas cell. |
| `12 VIEW - Vistas and SAM 3 contributions` | Vistas weight, SAM 3 weight, and which source contributed to each atlas cell. |

The raw scene also has numbered collections for the city mesh, semantic fishnets,
image coverage, refused faces, depth, panorama captures, bystanders, exposure
standpoints, ray paths, source sites, next-event connections, arrival spectrum,
body exposure, cameras, and the two animation explanations.

## Final transport decision

The joint atlas has 289,901 observed cells on 13,921 support faces. Scene `11`
shows the exact production decision for those cells:

| State | Cells |
| --- | ---: |
| Atlas interface | 205,848 |
| Nonblocking woody vegetation | 21,770 |
| Geometric fallback | 62,283 |

The material-mixture layer stores all 15 host-compatible material probabilities
as face attributes named `transport_probability_00` through
`transport_probability_14`. Its colour shows the largest channel only. Transport
uses the complete posterior, not the display winner.

The fallback layer stores the geometric support class for every atlas cell. Read it
together with the final-state layer. The fallback class is active only where the
final state selects geometric fallback.

## Vistas and SAM 3 evidence

Scene `12` separates the two sources used by the joint atlas. Exact linear weights
are stored in `value_vistas_prior_weight` and `value_sam3_concept_weight`. The
display uses one shared logarithmic colour range. A third layer labels cells as
Vistas only, SAM 3 only, or both.

All six audit objects are linked views of one fused atlas mesh. They do not copy the
522,136 display triangles six times.

## Panorama cameras

The blend has one saved panorama-registration scene for each of the nine admitted
captures. `07 VIEW - panorama registration` remains the hero capture. The eight
scenes named `07 PANO 02` through `07 PANO 09` open the other captures directly.
Each scene has all of the data needed to render that capture after reopening the
blend:

- A dedicated equirectangular PANO render camera at the registered pose.
- The matching 2:1 source panorama in the compositor.
- The source image's own pixel resolution.
- A translucent support copy scaled about that capture's camera centre.
- An orange marker and metadata for the nearest other admitted capture.
- A normal perspective camera with its linked 90 degree forward crop.

The hero scene still contains all nine PANO cameras and all nine normal perspective
cameras for quick comparison. The eight sibling scenes keep only their active
audit PANO and perspective camera. The nine dedicated render cameras live in the
camera-only `Panorama active render cameras` collection. That collection is linked
only to the opening scene and the nine panorama scenes. Blender then restores every
raw camera transform on a cold open. The camera outlines are 0.15 m and cannot be
selected, so they do not crowd the opening view. Their support objects share the
same display mesh data, so the per-capture scenes do not copy the full support mesh
eight more times.

Only the `Registered photograph` view layer is enabled for a normal F12 render.
`Panorama capture poses` and `Exposure standpoints` remain saved audit layers and
start disabled. Turn either one on when you want that comparison.

The image path and SHA-256 are stored on each scene and camera. No handler, driver,
or saved Python script changes the active photograph. The scene camera, compositor
image, output resolution, and support-overlay centre are saved as ordinary Blender
data.

The images stay linked so the blend does not copy nine large panoramas into its
file. Keep the repository's `data/panoramas/korenmarkt` and
`data/panoramas/korenmarkt_walk` directories in place when moving the blend.

## Depth evidence boundary

There is no admitted monocular-depth layer in this artifact. The selected 250 m
family uses `inhouse_leaf_250m_f64.ply`, its aligned pose, and four 1536 by 1536
views. The available monocular-depth products have different view IDs or image
shapes and belong to an excluded family. The blend records this as an explicit
absence on collection `05 depth clouds`.

The mesh first-hit depth layer is present with 470,358 points. It is the matched
depth evidence for the selected family.

## Arrival spectrum

Collection `13 arrival spectrum` keeps two objects for the rooftop model:

- `arrival_rooftop_raw_scientific` stores the exact 4,096 `rho` values on the
  original 8,188 source triangles. It is flat shaded and hidden by default.
- `arrival_rooftop_display_only_smooth` clips the display at its stated decibel
  floor, subdivides each source triangle into 16 display triangles, and uses smooth
  normals. It adds no scientific angular samples.

The raw object's `value_rho_per_sr` attribute is the scientific record. The smooth
object is a presentation layer only.

## Production inputs

The payload and manifest beside the blend are:

- `korenmarkt_15ghz_af8b9fc7cf3e_payload.npz`
- `korenmarkt_15ghz_af8b9fc7cf3e_manifest.json`

Their source triple is under `outputs/exposure_korenmarkt` with stem
`final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz`.

## Regenerating

From `papers/city-exposure-study/semantic_twin`:

```bash
python export_propagation_payload.py \
  --production-stem final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz \
  --paths 1200 \
  --out outputs/propagation_viz

/home/user/blender-4.5/blender --background \
  --python propagation_blender.py -- \
  --payload outputs/propagation_viz/korenmarkt_15ghz_af8b9fc7cf3e_payload.npz \
  --manifest outputs/propagation_viz/korenmarkt_15ghz_af8b9fc7cf3e_manifest.json \
  --blend outputs/propagation_viz/korenmarkt_atlas_4096_final.blend
```

The exporter verifies the production input hashes and the atlas binding before it
writes the payload. The Blender builder verifies the payload and manifest pair and
stamps its source-code fingerprint into every scene.
