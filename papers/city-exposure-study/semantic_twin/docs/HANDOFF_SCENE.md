# Handoff: the geometry layer, `semantic_twin/scene/`

Written 2026-08-04 by the agent that owned `fishnet.py`, `support_mesh.py`,
`scene.py`, `geo.py`, `pano_geometry.py` and `mmwave.py`. Assume the reader has
no context from that session.

State on handing over: the tree imports, ruff passes on everything touched, and
82 tests across `test_fishnet.py`, `test_scene_geometry.py`,
`test_support_mesh.py`, `test_pano_geometry.py` and `test_ground_datum.py` pass.
Nothing is half-moved. Nothing was committed and nothing was staged.

## What was built

A new package, `semantic_twin/scene/`. It holds the frames, the mesh, the ground
and the cut.

| File | Came from | Holds |
|---|---|---|
| `scene/__init__.py` | new | package docstring, plus the staging re-export of `load_scene` and `google_api_key` |
| `scene/site_config.py` | `scene.py` | `load_scene`, `google_api_key` |
| `scene/enu.py` | `geo.py` | `EnuFrame`, `llh_to_ecef`, `ecef_to_llh`, `enu_rotation` |
| `scene/frames.py` | new | the single `view_basis`, see the dedup section |
| `scene/pinhole.py` | `fishnet.py` | `PinholeView`, `CameraPose`, `world_to_view`, `view_to_world`, `view_to_image`, `image_to_view_directions` |
| `scene/planar.py` | `fishnet.py` | `signed_area`, `triangle_solid_angle`, `clip_near_plane`, `clip_to_rect`, `clip_half_plane`, `rasterize_convex`, `fan_triangles` |
| `scene/mesh.py` | `support_mesh.py` | `read_binary_ply`, `read_binary_ply_vertices`, `first_hit_range` |
| `scene/camera_ground.py` | `support_mesh.py` | `GroundSample`, `ground_elevation`, `camera_altitude` |
| `scene/fishnet/regions.py` | `fishnet.py` | `PAINT_REASONS`, `UNPAINTABLE`, `paintability`, `RegionMap`, `build_region_map`, `boundary_chains` |
| `scene/fishnet/surface.py` | `fishnet.py` | `REJECTION_REASONS`, `FishnetSurface`, `FishnetRaster`, `save_fishnet`, `load_fishnet` |
| `scene/fishnet/cut.py` | `fishnet.py` | `build_fishnet` and the cutter |
| `scene/fishnet/audit.py` | `fishnet.py` | `rasterize_fishnet`, `class_fidelity`, `occlusion_fidelity`, `occlusion_budget`, `aggregate_occlusion_budget`, `angular_tolerance_deg` |

The seams turned out to be five, not the five the plan guessed. The plan expected
mesh, ground, fishnet, surfaces and frames. What is actually there is: the frames
(three of them, geodetic, panorama and pinhole), the mesh as bytes on disk, the
ground under one camera, plane arithmetic in the image, and the cut. `surfaces.py`
in the plan is `propagation/scene.py`, owned by the materials agent, and never
came near this work.

`fishnet.py` was 1,422 lines doing four jobs. Splitting it dropped its file
complexity from 197 to 78 (`cut.py`) and 55 (`regions.py`), removed the only
function above the complexity threshold (`_process_triangle`, 28), and took the
many-parameter count from four to zero among the private functions. The three
remaining many-parameter warnings are all public API that outside callers pass by
keyword: `build_fishnet` (17), `paintability` (11), `ground_elevation` (8).

## The golden lock

Nothing in this scope is imported by `run_exposure.py` or `run_next_event.py`.
Verified by grep: neither driver names `semantic_twin.geo`, `.scene`,
`.support_mesh`, `.fishnet`, `.pano_geometry` or `.mmwave`. The fishnet reaches
the drivers only through NPZ files already on disk, and none were regenerated.

Beyond that, the move was checked bit for bit against the pre-refactor code taken
from git HEAD. The harness is at
`/tmp/claude-1001/-home-user-aegis-papers-city-exposure-study/03aeda6f-3c58-494f-b81b-a6fa68c6350a/scratchpad/equiv.py`
and it is worth rerunning after any further edit in this package. It reported:

```
144 fishnet cases identical, 52756 emitted faces compared
camera model identical over 720 view configurations
planar primitives identical over 3000 draws
ground datum and ENU frame identical over 200 draws
```

Every array is compared with `np.array_equal`, including dtype, not with a
tolerance. The 144 cases sweep three crop sizes, three yaws, two camera
rotations, with and without an occluder, and four class/transient/decision/material
combinations. They cover `paintability`, `build_region_map`, `boundary_chains`,
`build_fishnet` (every field of `FishnetSurface` and every key of its report),
`rasterize_fishnet`, `class_fidelity`, `occlusion_fidelity`, `occlusion_budget`,
`aggregate_occlusion_budget` and `angular_tolerance_deg`.

No float literal, operation order or RNG draw was changed. No finding in
`docs/BUGS.md` was fixed, including 8b, which is in this territory. `scene/mesh.py`
now names 8b in its module docstring so the next reader trips over it.

## The duplicated helpers, in full

This is the part nobody else can reconstruct, so it is spelled out completely.

### Unified

**`view_basis`.** Two copies, `fishnet.py:221` and `pano_geometry.py:66`. Both
were in this scope. **They were genuinely identical, and this was verified
numerically, not by reading.** The bodies differed in exactly one expression:
`math.radians(x)` twice against `np.radians([yaw, pitch])` once. The three
returned vectors were compared with `np.array_equal` over 20,000 random angles
crossed with seven pitches, plus every multiple of 45 degrees, both poles and
1e-12/1e12; zero mismatches, worst absolute difference 0.0. It was checked again
inside the equivalence harness over 720 further configurations. The surviving
body is `pano_geometry`'s, byte for byte, now at `scene/frames.py:23`. That was
deliberate: the module with thirty importers is unchanged and the module with
four moved.

There is one residual risk worth stating rather than hiding. `np.radians` on a
two-element list infers its dtype from the inputs, so if a caller ever passed
`np.float32` yaw and pitch the shared body would compute in single precision
where `math.radians` would have promoted to double. Every construction site in
the tree was checked and all pass Python floats or `float(...)` casts:
`build_fishnet_surface.py:151`, `raycast_mesh_depth.py:121`,
`crop_fused_semantics.py:121`, `project_pixel_semantics.py:86`,
`pano_geometry.inference_views`, and the tests. It is safe today. It is not
structurally guarded.

`view_basis` now has exactly one definition in the whole tree. The signature
changed for one of the two callers: it took a `PinholeView` in `fishnet.py` and
takes `(yaw_deg, pitch_deg)` now. Nothing outside `fishnet.py` ever called the
object-taking form, so no caller was affected. The shim re-exports the scalar
form.

**`_signed_area`.** `fishnet.py:1309` is now `scene/planar.signed_area`. The
private copy that was in this scope is gone.

### Left in place, with locations

None of these live in files this agent owned, so none were touched.

| Helper | Copies still live | Identical? |
|---|---|---|
| `_signed_area` | `semantic_twin/vision/atlas.py:257` (vision agent) and `semantic_twin/scene/planar.py:21` | **Yes, verified.** Compared over 5,000 random polygons of 3 to 8 vertices, every result equal to the last bit. Safe to collapse onto `scene.planar.signed_area` in one edit. |
| `_cosine_hemisphere` | `semantic_twin/propagation/tracer.py:403` and `semantic_twin/materials/foliage.py:925` | **Yes, verified.** They differ in that the tracer calls its own `_cross` and `_row_norms` instead of `np.cross` and `np.linalg.norm`. Both draw `u1` then `u2` from `rng.random(count)`, in that order. Compared over 300 batches of 500 normals with two generators seeded identically: bit identical, worst difference 0.0. **The RNG draw order is the same, so merging them will not move a traced number.** Keep the tracer's body, which is the faster one. |
| `sample_sphere` | `semantic_twin/illumination/sphere.py:47` and `semantic_twin/showcase.py:306` | **Not duplicates. Do not merge them.** `illumination.sphere.sample_sphere(count, rng)` draws uniform directions. `showcase.sample_sphere(centroids, pose, sphere, keys)` reads named panorama channels along rays from a camera. Same name, unrelated jobs. The one that matters, `illumination.sphere`, has only one copy. Rename the showcase one; do not unify. |
| `write_ply` | `semantic_twin/export.py:18` and `semantic_twin/propagation/sionna_check.py:317` | Not compared. Different signatures: `export.write_ply(path, vertices, faces) -> (n_v, n_f)` writes a file, `sionna_check.write_ply(vertices, faces) -> bytes` returns the buffer. They are probably one function plus a wrapper, but that was not verified. |
| `ground_datum` | `semantic_twin/walk/ground.py:225`, `semantic_twin/propagation/bystanders.py:846`, `build_site_config.py:92` | Not compared, and not in this scope. `walk/ground.py` is the walk agent's canonical one. Note `scene/camera_ground.py` is **not** a fourth copy: it measures the surface under one camera, `walk/ground.py` measures the walkable level of a whole square, and they disagree at seven of the 51 admitted stations. Both docstrings now say so. |
| `site_mesh` | `run_next_event.py:57`, `run_exposure.py:239`, `measure_escape_range_term.py:75`, `measure_surplus_spread.py:45`, `build_site_fishnets.py:223`, `build_site_semantics.py:145`, `FIGURES/make_walk_route.py:57`, `FIGURES/make_walk_cities.py:65`, `semantic_twin/propagation/bystanders.py:827`, `semantic_twin/propagation/sionna_check.py:871`, and the canonical `semantic_twin/paths.py:118` | **No copy of this ever existed in this scope**, so nothing was done to it. All ten should route through `paths.site_mesh`, which gates on the mesh format version. `source_mesh` in `config/*.json` is acquisition provenance, not a resolver. |

One aside that reads like a bug and is not: the `_f64` mesh files store
`property float x/y/z`, the same as the plain builds. `_f64` names the precision
of the *tile placement arithmetic* during the rebuild, not the storage. `paths.py`
and `docs/BUGS.md` both call them "double precision", which invites the wrong
reading.

## The two modules named scene.py

There were three, not two: `semantic_twin/scene.py` (site config plus the Google
key), `semantic_twin/propagation/scene.py` (surface classes from triangle
orientation, materials agent), and `semantic_twin/viz/blender/scene.py` (Blender
collections, viz agent).

What was done: `semantic_twin/scene.py` is deleted and the name `scene` now
belongs to the geometry package, which is the name `REFACTOR_PLAN.md` assigns to
this layer. The site-config loader moved to its real name,
`semantic_twin/scene/site_config.py`.

Why the package could not be called anything else. `semantic_twin/scene.py` had
two importers this agent was forbidden to edit, `acquire/streetview.py:41` and
`:302` and `acquire/mapillary.py:495`, all spelled `from ..scene import ...`. A
package `__init__` satisfies that spelling exactly, so `scene/__init__.py`
carries the two names as a marked staging shim and no separate shim file exists.
Naming the package anything else would have needed a `scene.py` shim, which
cannot coexist with a `scene/` directory.

The collision is therefore not fixed, it is aimed. The plan's destination for
`propagation/scene.py` is `scene/surfaces.py`, and that directory now exists. The
viz one is unrelated and should be renamed by whoever owns `viz/`.

## Shims left, and what the final pass must change

Four old import paths still resolve. Each carries a one-line comment saying it is
a temporary staging shim removed in the driver rewiring pass.

`run_exposure.py` and `run_next_event.py` need **no** changes for this scope.
Neither imports anything here. The shims exist for in-package modules owned by
other agents, listed below with exact lines.

**`semantic_twin/scene/__init__.py`** re-exports `load_scene`, `google_api_key`.
Rewire to `semantic_twin.scene.site_config`:
- `semantic_twin/acquire/streetview.py:41` `from ..scene import google_api_key`
- `semantic_twin/acquire/streetview.py:302` `from ..scene import load_scene`
- `semantic_twin/acquire/mapillary.py:495` `from ..scene import load_scene`

**`semantic_twin/geo.py`** re-exports `scene/enu.py`. Rewire to
`semantic_twin.scene.enu`:
- `semantic_twin/sites.py:35`
- `semantic_twin/walk/site.py:38`
- `semantic_twin/vision/captures.py:43`
- `semantic_twin/acquire/mapillary.py:64`
- `semantic_twin/acquire/streetview.py:40`
- `semantic_twin/acquire/routes.py:56`
- `semantic_twin/acquire/tiles.py:54`
- `tests/test_captures.py:16`, `tests/test_acquire_routes.py:16`,
  `tests/test_acquire_tiles.py:21`, `tests/test_acquire_mapillary.py:9`

**`semantic_twin/support_mesh.py`** re-exports `scene/mesh.py` and
`scene/camera_ground.py`. Rewire:
- `semantic_twin/vision/conflict.py:33` `first_hit_range` to `scene.mesh`
- `semantic_twin/vision/align.py:38` `ground_elevation` to `scene.camera_ground`,
  `read_binary_ply` to `scene.mesh`
- `semantic_twin/acquire/source.py:167` `read_binary_ply` to `scene.mesh`
- `semantic_twin/acquire/streetview.py:42` `camera_altitude` to
  `scene.camera_ground`
- `semantic_twin/acquire/mapillary.py:66` `camera_altitude` to
  `scene.camera_ground`

**`semantic_twin/fishnet.py`** re-exports `scene/fishnet/`, `scene/pinhole.py`
and `scene/planar.py`. One importer left:
- `semantic_twin/showcase.py:769` `from semantic_twin.fishnet import REJECTION_REASONS`,
  to `semantic_twin.scene.fishnet`

Once those are done, all four shim files can be deleted outright, except
`scene/__init__.py` which should keep only its docstring.

Rewired properly already, no action needed: `build_fishnet_surface.py`,
`export_propagation_payload.py:856` and `:910`, `backfill_sky_conflict.py:55`,
`showcase_blender.py:43`, `build_inhouse_mesh.py:41`, `build_walk_twin.py:32-33`,
`screen_cities.py:34`, `fetch_site_panoramas.py:78`, `tests/test_fishnet.py`,
`tests/test_support_mesh.py`.

## Deliberately not done

**`pano_geometry.py` was not moved.** It stayed at
`semantic_twin/pano_geometry.py`. It is part of this layer and the brief said so.
It has 34 importing files, of which 11 are modules other waves are actively
rewriting: `acquire/mapillary.py`, `align_skyline.py`, `semantics.py`,
`showcase.py`, and `vision/{align,bodies,conflict,fuse,layers,panorama,register,views}.py`.
Moving it would have left two live spellings of the most imported module in the
package while five agents were editing, which is a worse outcome than an untidy
import path. The brief's own rule was "properly or not at all", so: not at all.
The only thing it genuinely shared, `view_basis`, does live under `scene/` and is
imported back into `pano_geometry.py` at line 26. The package docstring in
`scene/__init__.py` says where it is and why.

If a later pass wants to move it, the mechanical change is
`semantic_twin.pano_geometry` to `semantic_twin.scene.pano_geometry` in those 34
files, and the module name should be kept as-is rather than renamed to
`panorama.py`, which would collide with `semantic_twin/vision/panorama.py`.

**`mmwave.py` was not touched.** It is in this scope by assignment and it is not
geometry. It is wavelength and Rayleigh roughness scaling, and every consumer is
in the materials stack: `materials/roughness.py:31`, `materials.py:12`,
`floquet.py:24`, `rcwa.py:45`, `kirchhoff.py:47`, plus two masonry scripts and
five tests. It belongs at `semantic_twin/materials/mmwave.py`. It was left alone
because `semantic_twin/materials/` was mid-write by another agent during this
session and a move would have collided. This is a one-file move for whoever owns
`materials/`.

## Tests added

`tests/test_scene_geometry.py`, 19 tests, no mesh on disk needed, all CI-safe.
The one worth knowing about is
`test_the_cutter_and_the_panorama_sampler_build_one_set_of_crop_axes`: it asserts
that the pinhole camera basis and `pano_geometry.view_basis` agree with
`assert_array_equal` over 97 yaws crossed with 6 pitches. That is the regression
guard on the `view_basis` merge. If someone reintroduces a second convention, the
cut pieces and the pixels they were cut from desynchronise silently, and this is
what refuses it.

The others pin: the ENU round trip and axis directions, signed-area winding, that
two adjacent polygons claim every pixel exactly once (the partition property the
whole fishnet rests on), near-plane clipping, eight octants summing to 4 pi, the
camera ground lying on the surface it claims to measure on a ramp, and the one
that matters most for the cut, `test_every_cut_piece_lands_back_on_its_source_triangle_plane`:
every emitted vertex sits within 1e-9 m of its source triangle's supporting
plane. That property is why the projective inverse is legitimate rather than a
resampling, and it was not pinned before.

## New defect found

`docs/BUGS.md` finding 11, code untouched. The ground under a camera is bounded
5 m from above and not at all from below, and neither bound is the one that
fires: 10 of 127 cameras land more than 2 m above the scene datum, one at Mexico
Zocalo at +4.83 m, all inside the ceiling. `GroundSample.spread_m`,
`peak_to_peak_m` and `n_hits` exist to catch exactly this and nothing reads them.
Reproduced from the recorded pose provenance on disk, not inferred.

## What to do next, in order

1. Rewire the four shims per the line list above, then delete them. Mechanical,
   about 20 import lines.
2. Move `mmwave.py` to `materials/mmwave.py`. Coordinate with whoever owns
   `materials/`.
3. Collapse `vision/atlas.py:257` `_signed_area` onto `scene.planar.signed_area`.
   Verified identical, safe.
4. Collapse `materials/foliage.py:925` `_cosine_hemisphere` onto the tracer's.
   Verified identical including RNG draw order, safe. Keep the tracer's body.
5. Rename `showcase.sample_sphere`. It is not a duplicate of
   `illumination.sphere.sample_sphere` and the shared name is a trap.
6. Move `propagation/scene.py` to `scene/surfaces.py`. The directory is waiting
   for it and this is what finally kills the `scene.py` collision.
7. Decide `pano_geometry.py`. Either move it into `scene/` and rewire all 34
   files in one pass, or write down that it stays at the top level on purpose.
8. Route the ten `site_mesh` copies through `paths.site_mesh`.

## Stated uncertainties

- The `np.float32` sensitivity of the shared `view_basis`, above. Safe today,
  unguarded.
- `_merge_small_regions` in `scene/fishnet/regions.py` iterates a precomputed
  `np.argsort(sizes)` while mutating `sizes` inside the loop, and breaks on the
  live value. That looked fragile while reading it. It was **not** investigated
  and is **not** claimed as a defect, because nothing was measured. Behaviour is
  bit-identical to before either way. Someone should decide whether the break is
  intended.
- `write_ply`'s two copies were never compared.
- Whether the 22 cameras with a wide or holed ground patch (finding 11) actually
  move a material-arm number was not measured. The claim in BUGS.md is limited to
  where the cameras are, not to what that costs.
