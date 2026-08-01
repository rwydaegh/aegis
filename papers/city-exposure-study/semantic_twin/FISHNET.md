# Fishnet surface cutter

`semantic_twin/fishnet.py` replaces the image-space quadtree in
`semantic_twin/pixel_projection.py`. Instead of tiling the label image and
splatting two triangles per tile onto the support mesh, it projects each support
triangle into the image, cuts it there against the semantic island boundaries,
and maps the pieces back onto the triangle's own plane.

The output is the visible surface set at one panorama centre. Each face carries
its class, class posterior, material posterior, confidence, outward normal,
metric area, solid angle from the capture point, and the source pixels it was
built from. Faces that were considered and rejected are kept in a parallel table
with the reason, so the propagation stage can see what was removed and why.

Run it with `build_fishnet_surface.py`. No Blender, no rendering.

## The reframing, and the verdict

The proposal was to reverse the direction of travel: project mesh triangles into
image space rather than ray-splatting image tiles outward. The claim that makes
it work is that the projection is a bijection on the visible surface.

**Confirmed, with two mandatory guards.** Within one rectilinear crop the camera
is an ordinary pinhole, so a triangle maps to a triangle by a projective map that
is invertible on the triangle's interior. The inverse used here is not
barycentric interpolation of the projected corners, which would be wrong under
perspective, but the exact intersection of the pixel ray with the triangle's
supporting plane. Checked against the Blender BVH depth buffer at Korenmarkt yaw
0: unprojecting all 707,620 first-hit pixels and testing the result against the
plane of the face the BVH reported gives a median residual of 4.7e-7 m, a 95th
percentile of 3.7e-6 m, and a worst case of 1.9e-5 m. The projection and the
Blender ray cast are the same map to well below any relevant tolerance.

The two guards:

1. **Near-plane clipping is not optional.** At Korenmarkt yaw 0, 4 of the 1,431
   visible support triangles have a vertex behind the camera plane, and those 4
   own 33.5% of the hit pixels in the view. They are the large ground triangles
   under the camera. Projecting them without clipping produces garbage, so each
   triangle is clipped in camera space against `z >= near_plane_m` before it is
   projected.
2. **The projection is a bijection on the *visible* surface only.** Two
   triangles routinely project to the same pixel. The mesh first-hit id buffer
   from `raycast_mesh_depth.py` decides ownership, and any piece of a projected
   triangle that a different triangle owns is rejected rather than painted.

## Algorithm

1. **Paintability** (`paintability`). Each pixel gets one reason code: paintable,
   no mesh hit, low confidence, transient object, clutter in front,
   mesh or pose conflict, or not a support surface. Metric distance and class are
   kept as separate causes on purpose. `clutter_in_front` comes from the
   mesh-versus-monocular depth decision written by `compare_mesh_depth.py`, which
   is where distance says something stands in front of the tile surface.
   `transient_object` comes from the class, because a person's depth often agrees
   with the wall they stand against and only the class can reject them.

2. **Islands** (`build_region_map`). Paintable pixels are grouped into connected
   components that share a class *and* are continuous in first-hit range, with a
   relative step test so grazing surfaces stay whole. Folding depth continuity
   into the island definition is what puts occlusion silhouettes into the
   fishnet: a wall seen past a nearer building is a different island from that
   building even when both are labelled `Building`. Islands below
   `min_region_pixels` are merged into the depth-continuous neighbour with the
   longest shared boundary, which suppresses segmentation speckle.

3. **Boundary chains** (`boundary_chains`). Boundaries are traced on the
   pixel-corner crack grid, not per class mask, so a boundary between two islands
   is one shared geometric object. Chains run between junctions where three or
   more islands meet, and each chain is simplified once with Douglas-Peucker
   holding its junctions fixed. Because the chain is shared, simplifying it can
   open neither a gap nor an overlap between the two islands it separates.

4. **Cut** (`build_fishnet`). Each visible support triangle is clipped to the
   near plane and the crop rectangle, rasterized to find its footprint, and then:
   - if the footprint lies in one island and the triangle owns at least
     `full_visibility_fraction` of it, the triangle is emitted untouched. The
     support triangulation is metre-scale photogrammetry and subdividing it where
     the semantics do not change buys nothing.
   - otherwise the local chains are noded against the triangle outline and
     `polygonize` returns the arrangement faces. Each face is depth-tested and
     support-tested, then triangulated with ear clipping.

5. **Evidence.** A face's class is the confidence-weighted majority over the
   pixels it owns, its confidence is that majority's purity times the mean source
   confidence of the winning pixels, and its material posterior is the mean of
   the per-pixel material probabilities over the same pixels.

## Measured results on Korenmarkt

Support mesh `data/geometry/korenmarkt/inhouse_leaf_130m.ply` (157,744
triangles), pose `data/panoramas/korenmarkt/alignment/pose_aligned.json`,
Mapillary Vistas label maps under `data/panoramas/korenmarkt/semantics/views`,
mesh first-hit buffers from `outputs/korenmarkt_mesh_depth`, depth decisions from
`outputs/korenmarkt_depth_consistency_two_models`. Defaults: boundary tolerance
1.5 px, minimum island 64 px, minimum piece 1 px squared.

Before is the recorded output of the quadtree path on exactly the same mesh,
pose and label maps, from
`outputs/korenmarkt_pixel_projection_leaf130/pixel_projection_manifest.json`.

| view | before | after | ratio | visible support triangles |
| --- | --- | --- | --- | --- |
| yaw 0 | 76,718 | 3,306 | 23.2 | 1,431 |
| yaw 90 | 47,538 | 1,717 | 27.7 | 1,077 |
| yaw 180 | 63,786 | 1,778 | 35.9 | 510 |
| yaw 270 | 69,268 | 3,733 | 18.6 | 2,333 |
| total | 257,310 | 10,534 | 24.4 | |

Per class at yaw 0, which is where the old path spent 52,582 triangles on flat
facade:

| class | before | after |
| --- | --- | --- |
| Building | 52,582 | 2,296 |
| Pedestrian Area | 11,050 | 325 |
| Billboard | 5,154 | 223 |
| Fence | 4,740 | 293 |
| On Rails | 1,818 | 92 |
| Sidewalk | 678 | 49 |
| Banner | 386 | 20 |
| Rail Track | 180 | 4 |
| Curb | 130 | 4 |

The reduction is a factor of 24, not the two orders of magnitude the brief asked
for, and the reason is a hard floor. A triangle inside one island is preserved,
so the output can never fall below the number of visible support triangles:
1,431 at yaw 0, or 54 times below the old count. At 3,306 the cutter sits 2.3
times above that floor. Going lower means decimating the support mesh itself,
which is a different change.

Coverage is not identical between the two runs. The old path treated 587,358
source pixels at yaw 0 as valid, this one 541,763, because street furniture and
railings are now excluded as separate-layer objects rather than painted onto the
wall. Normalising for that, the like-for-like ratio at yaw 0 is about 21.

### Fidelity

Round trip: the output faces are rasterized back into the image with a
nearest-surface test and compared against the source label map.

| view | class change | coverage | leaked into unpaintable | phantom | deleted |
| --- | --- | --- | --- | --- | --- |
| yaw 0 | 0.190% | 98.91% | 0.294% | 0.380% | 1.086% |
| yaw 90 | 0.126% | 98.74% | 0.117% | 0.094% | 1.262% |
| yaw 180 | 0.123% | 98.92% | 0.121% | 0.129% | 1.080% |
| yaw 270 | 0.250% | 99.27% | 1.111% | 0.063% | 0.731% |

- *class change* is the fraction of covered paintable pixels whose class differs
  after the round trip.
- *leaked* is unpaintable pixels that an output face nonetheless paints,
  normalised by the paintable count. This is the "person painted onto the wall"
  error.
- *phantom* is painted pixels where the painting face is not the mesh first hit,
  which would put a scatterer where the camera cannot see one.
- *deleted* is paintable first-hit pixels with no output face over them, which
  silently removes a propagation path.

Both directions of the visibility error are reported because they fail
differently for propagation. Phantom faces invent scatterers, deleted faces
remove paths.

Area is conserved exactly. At every view, `emitted_area_px + rejected_area_px`
equals `clipped_source_area_px` to the last pixel, so nothing is lost or double
counted between the accepted and rejected tables.

### The tolerance trade

Yaw 0, sweeping the boundary simplification tolerance and the minimum island
size. The angular column is the worst-case boundary displacement at the image
centre, where a 90 degree crop has its coarsest angular pixel pitch.

| tolerance px | min island px | triangles | angular | class change | coverage | leaked | deleted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 64 | 12,191 | 0.000 deg | 0.077% | 99.23% | 0.000% | 0.773% |
| 1.0 | 64 | 3,987 | 0.112 deg | 0.150% | 99.02% | 0.219% | 0.979% |
| 1.5 | 64 | 3,306 | 0.168 deg | 0.190% | 98.91% | 0.294% | 1.086% |
| 2.5 | 64 | 2,932 | 0.280 deg | 0.277% | 98.72% | 0.495% | 1.277% |
| 4.0 | 64 | 2,768 | 0.448 deg | 0.353% | 98.55% | 0.834% | 1.455% |
| 1.5 | 256 | 3,252 | 0.168 deg | 0.348% | 98.91% | 0.292% | 1.086% |

The count falls steeply up to about 1.5 px and then flattens, because past that
point the geometry is dominated by the support triangulation rather than by the
boundary description. Raising the minimum island from 64 to 256 px nearly doubles
the class change while saving 2% of the triangles, so 64 is the default.

The default tolerance of 1.5 px is 0.168 degrees, which is 29 mm at 10 m range.
At 28 GHz that is about 2.7 wavelengths, so the boundary description is fine
enough for material assignment but not for coherent phase on a boundary-hugging
path.

### Second taxonomy

The same run against the SAM3 concept label maps in
`outputs/korenmarkt_sam3_projection_inputs`, which is a 17-class material-facing
taxonomy rather than Mapillary Vistas:

| view | triangles | class change | phantom | deleted |
| --- | --- | --- | --- | --- |
| yaw 0 | 4,367 | 0.322% | 0.261% | 1.016% |
| yaw 90 | 4,534 | 0.400% | 0.101% | 0.976% |
| yaw 180 | 2,770 | 0.266% | 0.057% | 1.049% |
| yaw 270 | 4,780 | 0.162% | 0.032% | 0.958% |

Counts are higher because SAM3 separates windows, roof tile and paving inside
regions that Vistas calls one Building or one Pedestrian Area, so genuinely more
boundaries land inside each support triangle.

### Cost

2.3 s for the cut and 2.7 s end to end per 1024 x 1024 view on one core, with
1.2 MB of NPZ per view of which most is the pixel provenance. Turn provenance off
with `record_provenance=False` if that matters at city scale.

## Dependencies added

- `shapely` (BSD): GEOS noding, `polygonize` and polygon predicates. The
  alternative was hand-rolling Weiler-Atherton with hole handling, which is a
  correctness liability for no gain.
- `mapbox_earcut` (ISC): ear clipping of a polygon with holes without inserting
  Steiner points. Shewchuk's `triangle` was rejected because its licence forbids
  commercial use.

`scikit-image` supplies Douglas-Peucker through `approximate_polygon`, so no
extra dependency was needed for simplification.

`decal_atlas.conservative_simplify_contour` was evaluated and not used. It only
removes convex vertices so that a region can shrink but never spill, which is
right for an independent decal and wrong here: a chain is shared by two islands,
and shrinking both sides of the same boundary is a contradiction. Douglas-Peucker
has a symmetric error bound, which is what a partition needs.

## Known failure modes

- **Missed cuts leave a single arrangement face.** At yaw 0, 301 of the 993 cut
  triangles produced one face rather than several and were emitted whole. Most
  are benign, since the cut was triggered by partial occlusion rather than by a
  class boundary, but where a chain genuinely dangles inside a triangle the cut
  is lost. The residual shows up as the leaked column: 1,592 pixels at yaw 0.
- **GEOS noding is sensitive to where the chains are trimmed.** Trimming chains
  exactly on the triangle outline puts fragment endpoints on that outline to
  within rounding, and `polygonize` then treats them as dangles and refuses to
  split. Chains are therefore trimmed to a window two pixels larger and the
  outside faces are discarded. This was a real bug, not a hypothetical: before
  the fix, 94% of transient pixels were painted onto the walls behind them.
- **Majority rules delete real surface.** A piece that is 55% transient and 45%
  wall is rejected whole, and the wall part of it counts as deleted. That is the
  1% deleted column. Lowering `piece_support_fraction` trades it back against the
  leak.
- **Crop seams are the caller's problem.** The four pitch-0 yaw crops at 90
  degrees tile a cube band exactly, so clipping each triangle to its crop
  partitions the band. The overlapping `h+45` and `h-45` crops would double-cover
  and need an explicit assignment rule that this module does not provide.
- **Small islands with no depth-continuous neighbour survive.** 30 islands at yaw
  0 stayed below `min_region_pixels` because every neighbour sat across a depth
  break. They are kept rather than force-merged across a silhouette.
- **Sky pixels with a mesh first hit are a registration conflict, not handled.**
  They are excluded as non-surface, which hides the conflict rather than
  resolving it. The right fix is upstream in pose alignment.
- **The depth decision map is taxonomy-bound.** Its `front_blocker` entries are
  label-independent and transfer between taxonomies, but its `dynamic_object`
  entries were derived from the Vistas classes. Reusing those decisions with the
  SAM3 labels is sound for the first and redundant for the second.
- **Mesh cracks reduce support rather than crash.** Where the tile mesh has a
  hole, pixels inside a projected triangle have no first hit, the piece's support
  fraction falls, and the piece is either kept with reduced pixel support or
  rejected as `no_semantic_support`. Degenerate and behind-camera triangles are
  counted in the rejection table instead of raising.
