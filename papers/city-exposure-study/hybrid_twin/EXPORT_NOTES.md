# Sionna RT scene export

`export_scenes.py` turns the hybrid twin into three Mitsuba scenes for an
ablation: intelligent hybrid vs naive OSM vs naive photogrammetry.

```bash
~/blender-4.5/blender -b scene_hybrid.blend -P export_scenes.py            # export
/home/user/aegis/.venv/bin/python export_scenes.py --validate              # load + trace
```

Export takes ~40 s (or ~10 s off the terrain cache), validation ~6 s. Useful
flags after a `--` separator in Blender: `--materials PATH` (per-building
material map, default `data/materials.json`), `--refresh-terrain`,
`--blend scene_export_debug.blend`.

## Format

Mitsuba XML 2.1 plus one binary little-endian PLY per shape under `meshes/`.
PLYs are written directly with numpy (`write_ply`), not through
`bpy.ops.wm.ply_export`: the operator only writes the selection or the whole
scene, and every mesh here is generated numerically anyway, so going through
Blender objects would only add a round trip.

All three scenes share the local ENU frame of `data/osm_buildings.json`
(metres, z up, origin at 51.0550 N 3.7220 E, ellipsoidal). No `to_world`
transforms, so a position printed by `analyze_hybridize.py` or
`poc_relevance.py` can be handed to Sionna unchanged.

## Materials

Sionna's `process_xml` (sionna/rt/scene_utils.py:75-121, sionna-rt 2.0.1) takes
any BSDF whose `id` starts with `mat-itu_` or `itu_`, strips the prefix and
rewrites the node into the `itu-radio-material` plugin with that `type`. The
exporter emits `<bsdf type="itu-radio-material" id="mat-itu_<name>">` with an
explicit `<string name="type">` and `thickness=0.1` (Sionna's
`DEFAULT_THICKNESS`), which satisfies both the id convention and the plugin
directly. `--validate` asserts the material-name list in the exporter still
matches `ITU_MATERIALS_PROPERTIES` in the installed Sionna, so a version bump
that renames a material fails loudly instead of silently.

Defaults, used where `data/materials.json` says nothing: prisms `itu_brick`,
carved landmarks `itu_marble`, terrain `itu_medium_dry_ground`, vegetation
`itu_wood`, photogrammetry baseline `itu_concrete`.

`data/materials.json` does not exist yet. When it appears, re-running the
exporter picks it up with no other change. Format `{"<osm_id>": "brick", ...}`;
values may carry an `itu_`/`mat-itu_` prefix, unknown names are reported and
fall back to the default rather than producing a scene Sionna refuses to load.
The map is applied to the hybrid **and** the OSM baseline, so hybrid-vs-OSM
isolates geometry and photo-vs-either isolates semantics.

The vegetation material is a placeholder and the XML says so in a comment: a
canopy is a lossy volume, not a slab, and `itu_wood` as a 10 cm sheet is not a
tree. The runner is expected to swap that BSDF for a specific-attenuation
material derived from ITU-R P.833.

## What is in each scene

| | shapes | triangles | contents |
|---|---|---|---|
| `scenes/hybrid` | 344 | 67 320 | 8 carved photogrammetry buildings, 320 prisms, terrain, 15 canopy proxies |
| `scenes/osm` | 449 | 19 024 | 448 prisms on one flat level, same terrain |
| `scenes/photo` | 1 | 497 021 | the raw Google mesh, one material |

**Hybrid.** Carve set is the 6 `detailed`-tier buildings of `relevance.json`
*union* the 4 `landmark-keep-photo` buildings of `decisions.json`, which is 8
after the overlap. This is a deviation from a literal reading of the spec:
Sint-Michielskerk and Stadhuis are only `prism` tier in the relevance pass, but
the height audit already concluded that a box lies about them, and throwing that
away to satisfy tiering would make the hybrid worse at exactly the thing it is
supposed to be good at. Carving follows `analyze_hybridize.py`: triangles whose
centroid falls in the footprint, plus a 2 m ring pad, each triangle claimed by
at most one building (interiors first, then pads). Triangles whose centroid sits
below `ground + 1 m` are dropped so the carved building does not duplicate the
terrain underneath it. The pad costs about 22% more triangles than the bare
footprint count in `relevance.json` (50 524 vs 41 396) and buys facade continuity
at the building edge.

The 320 prisms are the `prism` tier minus whatever moved into the carve set.
The 120 `dropped`-tier buildings are absent, as specified.

**OSM.** Every footprint, height from the OSM `height`/`levels` tag where there
is one (39), else the photogrammetry measurement, else 12 m. All bases sit on
one flat level (51.14 m), which is the naive error being modelled: OSM alone has
no terrain. Bases are sunk 10 m below that so nothing floats over the shared
terrain mesh; only the roof error survives, which is the part that matters.

**Photo.** One PLY, one material, no segmentation. 14 MB.

## Terrain

Raycast the photogrammetry BVH downward on a 4 m grid (11 236 rays), keep hits
that fall outside every OSM footprint, fit a 10 m triangulation.

Naive local percentiles were wrong here. "Outside every OSM footprint" is not
"on the ground": whole neighbourhoods of samples land on the roofs of buildings
missing from OSM, and the first version produced terrain nodes at 70 m in the
south-west corner where the true street is near 50 m. The fix is a two-pass
morphological filter. Pass one seeds a smooth surface from the 5th percentile
over a 60 m window; pass two rejects every sample more than 3 m above that seed
(1502 of 4880 samples, all of them roofs) and refits the 25th percentile over
25 m. Terrain now spans 48.24-55.17 m over the 420 m block, which matches the
real drop from the Sint-Michiels ridge to the Leie banks.

The same trap is baked into `data/decisions.json`: 13 buildings have a
`ground_z` more than 3 m off the filtered terrain, because their local ground
was measured on a neighbour's roof. The exporter clamps those bases back onto
the terrain and reports the count. `decisions.json` itself is untouched.

Residual against the accepted street samples: median +0.29 m, 5th-95th -0.10 to
+2.31 m, i.e. the terrain sits slightly under the photogrammetry skin, as a
25th-percentile fit should. Along the walk the median offset between the
hybrid terrain and the photogrammetry surface is -0.75 m. Anything placing
receivers at a fixed height above ground should therefore probe the scene it is
tracing in rather than assume the three scenes agree on z; `--validate` does
exactly that.

## Vegetation proxies

The 15 blobs `decisions.json` classified as vegetation become ellipsoids of
radius `sqrt(area/pi)` (minimum 2 m) spanning `[0.35 h, h]` above the terrain,
so there is a trunk gap at pedestrian height instead of a solid dome sitting on
the pavement. The blob record only carries a centroid and an area, so a tree row
along a street becomes one 17.5 m ellipsoid; that is the resolution the upstream
clustering left, not a modelling choice made here. The 48 blobs classified as
unmapped structure are not exported in any scene - they are in the photo mesh by
construction and absent from OSM by definition, which is itself a difference the
ablation will show.

## Validation

Transmitter at the first site of `data/sites.json`, receiver at the walk point
nearest it, 3.5 GHz, isotropic single-element arrays, `max_depth=3`,
`samples_per_src=1e6`, LOS plus specular reflection.

```
tx (site SITE(91JAR_01), h=42.51 m) = [-40.82, -52.25, 93.29]
rx (nearest walk point, 1.5 m agl) = [-126.91, -17.8, 52.18]
tx-rx distance = 101.4 m
surface under rx per scene: hybrid=49.07, osm=49.07, photo=50.68
surface under tx per scene: hybrid=90.23, osm=58.14, photo=90.23

[hybrid] load ok  xml_shapes= 344  sionna_objects=   4  materials= 4  triangles=  67320  paths=  4  best=  -83.5 dB  sum=  -82.3 dB
[osm   ] load ok  xml_shapes= 449  sionna_objects=   2  materials= 2  triangles=  19024  paths=  7  best=  -83.5 dB  sum=  -82.3 dB
[photo ] load ok  xml_shapes=   1  sionna_objects=   1  materials= 1  triangles= 497021  paths= 11  best=  -83.5 dB  sum=  -82.6 dB
```

`sionna_objects` is small because `load_scene(merge_shapes=True)` merges shapes
sharing a material; the per-shape count is the `xml_shapes` column and the
triangle totals are summed from the merged meshes, so nothing is lost.

Two things worth reading off this. The strongest correctness signal is that the
LOS path is -83.5 dB in all three scenes, which is free-space at 101.4 m and
3.5 GHz to the decimal, so the ENU frame, the metre scale and the terminal
placement are right in all three. And the naive OSM baseline already misbehaves
before any statistics: the surface under the transmitter is at 58.14 m where the
hybrid and the photogrammetry both say 90.23 m, because the building the mast
stands on carries a short height tag. The mast is 32 m above its own roof in the
OSM scene and 3 m above it in the other two.

Photogrammetry gives the most paths, the hybrid the fewest, at one link.
Nothing follows from a single receiver; it is only evidence that all three
scenes trace.

The receiver was buried in the photo scene on the first attempt (0 paths): the
terrain estimate is 1.6 m below the photogrammetry skin at that point and 1.5 m
of antenna height did not clear it. `--validate` now probes all three loaded
scenes with a downward Mitsuba ray and places both terminals above the highest
of the three surfaces.

## Geometry checks

- All 335 generated closed meshes in the hybrid (320 prisms + 15 canopies) and
  all 448 OSM prisms have positive signed volume, so face windings are
  consistently outward. Caps are ear-clipped with `mathutils.geometry.
  tessellate_polygon`, since a triangle fan is wrong for the concave footprints
  in this block.
- Terrain: 3528 triangles, all up-facing.
- Every `filename` in every XML resolves, no duplicate shape ids.
- Degenerate (zero-area) triangles are dropped before writing; the Google mesh
  loses none, so the photo scene keeps all 497 021.

## Known gaps

- Carved buildings have no floor. They sit on the terrain, which closes them
  from below for any ray that matters, but they are not watertight on their own.
- The 2 m carve pad can pull in a neighbour's facade where buildings touch.
  Each triangle is claimed once, so nothing is duplicated, but a carved
  building's mesh can extend slightly past its own footprint.
- `decisions.json` heights for the 13 clamped buildings are still measured
  against a roof, so their absolute roof heights stay wrong even though the
  bases are now correct. Fixing that means re-running the audit with the
  filtered terrain.
