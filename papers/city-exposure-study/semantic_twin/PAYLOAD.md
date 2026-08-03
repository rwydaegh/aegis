# The propagation payload, and what the blend shows

`export_propagation_payload.py` writes one NPZ and one JSON manifest per site.
`propagation_blender.py` turns that pair into a blend. This document says what is
in the NPZ, which collection each array becomes, and what a reader is entitled to
conclude from looking at it.

Two halves. The traced half runs the estimator and was always here. The evidence
half reads what the reconstruction pipeline already wrote to `outputs` and had
never reached a blend before: no semantics, no depth, no SAM 3, no registered
pose, no bystander. The pipeline builds far more than the visualisation showed,
and this is the part that closes that gap.

Nothing in the evidence half is recomputed. Every array is a concatenation, a
reduction or an unprojection of a file on disk, and the manifest records which
directory each one came from.

## Running it

```bash
python export_propagation_payload.py --site korenmarkt
python export_propagation_payload.py --site krakow_rynek --no-evidence
python export_propagation_payload.py --site korenmarkt --depth-stride 8
python export_propagation_payload.py --site newyork_timessquare --evidence-only

~/blender-4.5/blender --background --python propagation_blender.py -- \
    --payload outputs/propagation_viz/korenmarkt_payload.npz \
    --blend outputs/propagation_viz/korenmarkt_propagation.blend \
    --render-dir outputs/propagation_viz/figures --gpu
```

`--gpu` picks OPTIX, CUDA, HIP, METAL or ONEAPI, whichever Cycles finds, and
raises if it finds none rather than quietly falling back. The nineteen figures
are about twenty minutes of A6000 and several hours of contended CPU, so the
flag is the difference between iterating on a figure and not.

`build_propagation_blends.py` already drives both stages with those paths, so the
usual way to regenerate everything is to run that and the figures land beside the
seven that were there before.

`--evidence-only` reuses the traced half of a payload that already exists and
rebuilds the image side alone. Tracing Times Square is two hours on this machine
and gathering its evidence is seconds, so when only the second half changed the
first half is not worth doing again.

Evidence is discovered by directory name under `outputs`, so a site that has no
panorama exports the traced layers alone and the blend opens with those
collections empty. Korenmarkt is the only site with the full set. New York has a
Vistas fishnet over two admitted panoramas and nothing else. Milan has a fishnet
and a mesh depth buffer and no body layer.

## One file, fourteen collections

There is one blend per site and it holds everything, in numbered collections
named for a reader rather than for this script:

| Collection | On at open | Source |
| --- | --- | --- |
| `01 city mesh` | yes | the traced half |
| `02 semantic surface` | no | `<site>_fishnet_vistas_fused`, `<site>_fishnet_sam3` |
| `03 image coverage` | no | the same fishnet run, accepted against rejected |
| `04 refused faces` | no | the fishnet's rejected table |
| `05 depth clouds` | no | `<site>_mesh_depth`, `<site>_depth_consistency_two_models` |
| `06 panorama captures` | no | `registration_sky_conflict.json` and the pose files |
| `07 bystander bodies` | no | `<site>_dynamic_bodies` |
| `08 walk standpoints` | yes | the traced half |
| `09 ray paths by fate` | yes | the traced half |
| `10 ray paths by bounce` | no | the same paths, cut at their reflections |
| `11 arrival spectrum` | yes | the traced half |
| `12 transmitter positions` | yes | the illumination model |
| `13 body exposure` | yes | the traced half |
| `14 cameras` | yes | the figure cameras and one per registered pose |

Every collection is created at every site whether or not the data for it
exists, so an empty `05 depth clouds` says this site has no depth buffers rather
than leaving you to notice a missing row. The seven that start off are off
because they are heavy or because they duplicate a layer that is already on, not
because they are secondary.

Everything is in one frame. The payload is written in scene ENU metres with the
hero standpoint at the origin, and every evidence layer is placed by the same
transform the tracer used, which is why the semantic surface lands a median 6 cm
from the drawn mesh rather than somewhere else entirely. That number is measured
per site and is in the manifest.

The blend also saves a viewport. A file built headlessly otherwise opens at the
factory view, two metres from the origin with a hundred metre clip, which inside
a 220 m square is a grey wall. The saved view sits over the standpoint at a
three quarter angle with the clip opened past the far edge, in every workspace.

## The traced half

| array | shape | what it is |
| --- | --- | --- |
| `mesh_vertices`, `mesh_faces` | | the support mesh, cropped to `drawn_radius_m` |
| `mesh_face_class` | per face | ground, facade, roof or soffit, geometric |
| `walk_points`, `walk_ground_z_m` | per standpoint | every traced walk location |
| `walk_chi_*`, `walk_peak_sab_*` | per standpoint | susceptibility and peak `Sab` per model |
| `path_*` | per recorded ray | polylines, throughput, exit direction, termination |
| `local_grid`, `rho_*` | per direction | the angular power spectrum at the hero standpoint |
| `body_vertices`, `body_faces`, `body_sab_w_m2` | per phantom triangle | absorbed power density |
| `network_*` | per source | where the illumination model's sources sit |

The recorded paths are drawn twice, from the same arrays. `09 ray paths by fate`
splits them by what happened at the end, five exclusive bundles. `10 ray paths
by bounce` cuts the same polylines at their reflections and groups the segments
by leg index, so leg zero is what left the standpoint, leg one is what carried
on after the first surface, and so on. The second reading is the one the bounce
budget is about: the panoramas measure the material for the first two
reflections and nothing measures it after that. At Korenmarkt the four legs hold
1200, 886, 437 and 245 segments, so switching the last object off shows how much
of the fan lives past the evidence. The bounce split starts hidden because
drawing it next to the fate split draws every path twice.

The rays are `Curves` rather than legacy Blender curves, which is the only curve
type that takes named attributes. Power is therefore on them three times: as the
point radius, which is the cube root of throughput so a fourth bounce stays
visible; as `value_throughput`, the exact number, in the spreadsheet; and as
`power_db`, a colour over the decades the fan spans. The default shading layer
is `fate`, the constant colour of the bundle, so the two readings are a click
apart and neither has to be chosen at build time.

## The evidence half

### Semantic surface, the `semantics` collection

Two surface sets, one per taxonomy, from `outputs/<site>_fishnet_vistas_fused`
and `outputs/<site>_fishnet_sam3`. Arrays are named `fishnet_<taxonomy>_<column>`.

| column | domain | meaning |
| --- | --- | --- |
| `vertices`, `faces` | | the cut surface, in scene ENU metres |
| `class` | face | the winning class id in that taxonomy |
| `class_rgb` | class | one tint per id, a lookup and not a ramp |
| `confidence` | face | majority purity times mean source confidence |
| `top_probability` | face | the winning class posterior |
| `entropy_bits` | face | Shannon entropy of the whole posterior row |
| `range_m` | face | distance from the capture point |
| `visible_fraction` | face | the occlusion decision, exposed rather than folded in |
| `area_m2`, `solid_angle_sr` | face | metric area, and solid angle from the capture point |
| `pixel_support` | face | how many source pixels decided this face |
| `view` | face | which of the four crops it came from |

The 59 column posterior itself is not shipped. No shader can read it and it is
most of the file, so it is reduced to the winning probability and the entropy.
Entropy is the number an argmax throws away: it is zero on a face that lies
inside one island and rises on a face the cutter assembled out of a mixed pixel
set. At Korenmarkt 17 percent of Vistas faces have a mixed posterior and the
median face has none, which is the honest shape of that evidence.

The SAM 3 concept masks exist for two panoramas, Korenmarkt and Milan. The
`sam3` surface set *is* those masks, projected onto geometry: a 17 class material
facing taxonomy with brick, stone, glass, roof tile and cobblestone as separate
classes where Vistas says Building and Pedestrian Area. That is the useful form
of a mask in a blend, and it is why no image is packed.

### Support triangles, the `evidence` collection

`support_evidence_*`, one row per support triangle any view considered. Built by
aggregating the fishnet's accepted and rejected tables back onto the triangle
they came from.

| column | meaning |
| --- | --- |
| `class`, `confidence` | modal class and mean confidence, weighted by pixel support |
| `clean_px` | source pixels that were painted |
| `transient_px` | refused because a person or a vehicle stood there |
| `clutter_px` | refused because something the tiles never captured stood in front |
| `occluded_px` | refused because another support triangle owned the pixel |
| `other_px` | every remaining reason, mostly sky and street furniture |
| `withheld_fraction` | everything refused, over everything considered |

The four refusal channels are kept apart because they do not mean the same
thing. A transient pixel is deferred and comes back as an SMPL-X body. A clutter
pixel is absent and never comes back. Reading them as one number is exactly the
error this layer exists to prevent, and it is the same split the occlusion budget
in `FISHNET.md` reports as *deferred* against *absent*.

At Korenmarkt `clutter_px` is zero across all four crops. That is not an absence
of clutter, it is the depth gate: the monocular scales were refused, so no pixel
ever received a `front_blocker` verdict and the only surviving refusals are the
class driven ones. See the depth collection below.

### Refusals, the `refused` collection

`rejected_vertices`, `rejected_faces`, `rejected_reason`, `rejected_image_area_px`.
The candidate surface the cutter did not emit, drawn as the support triangle it
was cut from, one Blender object per reason. Rows are deduplicated on the pair of
triangle and reason, because a triangle is refused once per view and often in
several pieces per view, and the image areas of the merged rows are summed.

Switching one object off answers what one reason removed. The two worth looking
at are `refused_transient_object` and `refused_clutter_in_front`.

### Depth, the `depth` collection

Two point clouds, both unprojected from stored range images at `--depth-stride`
pixels, both rendered through one geometry node rather than as triangles.

`depth_mesh_*` is the mesh first hit from `outputs/<site>_mesh_depth`, which is
what the twin actually uses, coloured by the fused decision map. Its holes are
where the transient mask removed pixels.

`depth_monocular_*` is the monocular surface from
`outputs/<site>_depth_consistency_two_models` at its per view fitted scale. **It
is the surface the plausibility gate refused, and the twin does not use it.** It
is drawn so the refusal can be seen instead of taken on trust: the fitted range
scales at Korenmarkt are 0.41, 0.62, 0.57 and 0.046, against a plausible band of
0.5 to 2 for a metric depth model, and the crops of one panorama disagree by a
factor of 13.6. One camera centre cannot have several metric scales. On screen
the whole square sits at a fraction of its range, inside the mesh. Every object
carries the gate's own list of problems as a property.

Point layers are `decision` (the seven verdict codes of `compare_mesh_depth`),
`range_m`, and for the monocular cloud `z_score` and `mesh_minus_this_m`.

### Registration, the `panoramas` collection

`pano_position`, `pano_rotation`, `pano_sigma_vectors`, `pano_verdict`,
`pano_residual_deg`, `pano_sky_conflict`. Every pose in
`outputs/registration_sky_conflict.json` whose support mesh belongs to this site,
which at Korenmarkt is the one capture the semantics ran on plus the twelve walk
captures.

Three objects. A real Blender camera per pose at the solved rotation, so the view
that pose saw can be reproduced from inside the blend. A marker per pose,
coloured by verdict. An ellipsoid per pose from the position block of the seed
study covariance.

The verdict follows the audit's own reading note rather than a threshold invented
here: below 5 percent of sky directions returning a mesh hit is healthy, above 50
percent means the camera is inside the geometry and its skyline residual is not
an error bar. Korenmarkt has thirteen poses, of which three sit at 100 percent
and four more are suspect. Six are clean. That is visible at a glance and no
residual would have said it.

The covariance ellipsoids are drawn at `--pose-sigma-scale`, 10 by default, and
the multiple is a property on the object. One sigma of pose position here is 3.5
to 54 cm, which at the scale of a square is invisible at life size. Read the
ellipsoid as a relative comparison between poses, not as a distance.

### Bystanders, the `bodies` collection

`body_layer_vertices` at `(bodies, 18439, 3)` and `body_layer_faces` once. All
the reconstructions share the SMPL-X topology, so the faces are stored a single
time, which is the difference between four megabytes and twelve for the eighteen
people at Korenmarkt. Statures, placed ranges, provenance and the placement
uncertainty are properties on each object.

These are the people the transient mask cut out of the static surface. The
fishnet leaves a hole where they stood and this layer is what fills it.

## Two things a reader has to know

**The semantic surface is not on the same mesh as the rays.** The fishnet was cut
against `inhouse_leaf_130m.ply`, whose tile placement was read back through
Blender in single precision, and the tracer runs on the 250 m double precision
rebuild. The manifest measures the disagreement at
`evidence.semantic_surface_offset_from_drawn_mesh`: at Korenmarkt the median is
6 cm and the 95th percentile 27 cm, over faces inside the drawn radius. Faces
outside it are counted separately and are not misregistered, they are simply past
the shell the blend draws. Six centimetres is fine for looking at and is not a
binding you would trace against without rebuilding the fishnet on the f64 mesh.

**The pose file on disk has moved since the evidence was built.** The skyline
alignment is re-run and rewrites `pose_aligned.json` in place, and at Korenmarkt
the current file sits 1.79 m from the camera centre recorded inside the fishnet
surface sets. Unprojecting the stored depth buffers with the current pose lands
0.94 m off the mesh, and with the recorded centre 0.04 m. So the recorded centre
is what the depth clouds use, the drift is in the manifest at `evidence.camera`,
and the `panoramas` collection deliberately shows the *current* poses because
inspecting the registration is its job. If those two disagree on screen, that is
the drift and not a bug in the drawing.

## Layers, and how to switch one

A layer is an attribute, not an object. Every evidence object carries its
measured quantities twice:

- `value_<name>`, a float or integer attribute holding the exact number, which
  the spreadsheet editor shows and a geometry node can read,
- `<name>`, a colour attribute holding the shaded version over a stated range,
  which is on the object as `<name>_range`.

The available layers are listed on each object as `colour_layers`. To switch,
pick a different colour attribute in Object Data Properties, or rename the
attribute the material's `layer` node reads. `show_layer` in the build script
sets both at once, which is what the figure renders use.

Class layers are palette lookups, not ramps. Adjacent Mapillary Vistas ids are
unrelated classes and a ramp invites reading a gradient into a lookup, so the
hues walk the colour circle by the golden angle. The id to name mapping is in the
manifest and on the object as `class_names`.

## The figures

Nineteen PNGs land in `outputs/propagation_viz/figures`, named after what they
are about rather than after the camera that took them. One through seven are the
traced walkthrough and were there before. Eight through seventeen are one per
evidence layer: the Vistas classes, the confidence, the split posterior, the SAM
3 materials, the refusals, clean against withheld, the mesh first hit, the
refused monocular depth, the registered poses and the bystanders. Eighteen is
the bounce depth. Nineteen is everything at once.

Three things sit out of the everything shot and none of the reasons is
aesthetic. `evidence` and `refused` are drawn on the same support triangles the
semantics are cut from, so putting them in the same frame is z fighting rather
than information. The monocular cloud is the surface the gate refused, and a
picture captioned everything would be claiming the twin uses it. `bounces` is
the ray fan a second time.

The evidence cameras are placed where the panorama stood rather than outside the
square looking in. The cut surface is by construction what was visible from the
capture point, most of it facade, so every outside vantage is behind a wall that
owns part of the layer, and raising the camera until the wall clears turns the
facades edge on and photographs roofs. Standing at the capture point, nothing it
can see is occluded, because seeing it is what put it there.

## File size

Korenmarkt, the site with the full evidence set, is a 13.0 MB payload and a
32.2 MB blend. The evidence roughly quintuples the payload and roughly quadruples the blend. The
choices that keep it there, rather than at ten times: no packed images, the
posterior reduced to two numbers, the SMPL-X topology stored once, the depth
clouds stored as one vertex per point with byte colour rather than as triangles,
and `--depth-stride` at 4 rather than 1. Raising the stride to 8 removes about
three quarters of the two clouds.

Every evidence collection starts hidden in both the viewport and the render, so
opening the blend costs what it did before and the layers are one click away.
