# Multi-view semantic mmWave twin

## Objective

The deliverable is not a coloured Inhouse mesh. It is a propagation-ready 3D
scene whose geometry and RF properties are supported by traceable image
observations. Every exported surface or object carries confidence, provenance,
and enough uncertainty information to run an ensemble of plausible ray-tracing
scenes.

Street View panoramas are observations. Inhouse 3D Tiles are a geometric prior.
Neither is treated as ground truth.

## Why multiple panoramas change the problem

A distant object may occupy only a few pixels in one panorama and hundreds in a
nearby panorama. The nearby observation should dominate its fine geometry and
classification, while the distant panorama still constrains visibility and
location. Repeated viewpoints also expose registration errors, transient people
and vehicles, and missing geometry in the aerial photogrammetry.

The system therefore maintains an immutable observation ledger and rebuildable
3D posteriors. Re-running pose optimisation, changing the taxonomy, or installing
a better segmenter does not require destructive repainting of the mesh.

## Representation

Three semantic axes are deliberately separate.

1. Entity is categorical: facade, window, road, person, bollard, vehicle, and so
   on. Its posterior is Dirichlet-distributed.
2. RF material is categorical over frequency-dependent material models: brick,
   concrete, glass, metal, wood, asphalt, vegetation, and so on. It has an
   independent Dirichlet posterior because visual class does not uniquely imply
   dielectric properties.
3. Attributes are multi-label Bernoulli variables: thin, rough, reflective,
   transparent, conductive, movable, wet, or transient. They use independent
   Beta posteriors. A railing can therefore be metal, thin, reflective, fixed,
   and a street-furniture entity simultaneously.

The face-level accumulator is in `semantic_twin/evidence.py`. It was the first
storage backend and it is not a commitment to preserving the source
triangulation. Two further backends now exist alongside it.
`semantic_twin/atlas_ledger.py` stores sparse, replayable per-observation rows in
a bounded ring buffer, so a city mesh with millions of triangles costs nothing
for the triangles no panorama has seen, and a batch can be checkpointed to a
compressed NPZ between acquisitions. `semantic_twin/decal_atlas.py` gives each
observed support triangle a small canonical right-triangle texture that
accumulates categorical weight per texel, which keeps the mesh topology intact
until a downstream renderer genuinely needs a material-boundary split. All three
expose the same posterior interface.

## The three projection paths, and which one is current

Three paths from a label map to surfaces exist in the tree. They are not
alternatives to choose between at run time. Two are superseded and one is
current, and the difference matters because measured numbers in this repository
were produced by different ones at different dates.

`project_semantics.py` assigns one panorama sample to each source-face centroid
and owns the RF export: it is still the only writer of `scene.xml`, the Sionna RT
scene that binds each material group of triangles to an ITU radio material. Its
semantic boundaries inherit the photogrammetry triangulation, so it is not the
right source of surface detail, but nothing else produces a traceable scene and
it stays until the fishnet path grows an exporter. **That exporter does not exist
yet**, which is the single largest gap between this document and a runnable
end-to-end pipeline.

`project_pixel_semantics.py` is the image-space quadtree path. It starts from
each 1024 x 1024 perspective label map, builds adaptive image tiles that merge
over uniform interiors and split down to one input pixel where mixed, and
ray-splats two triangles per leaf outward onto the first-hit support surface.
**Superseded.** Every class boundary became a staircase of axis-aligned squares
and flat facade paid for triangles it did not need.

`semantic_twin/fishnet.py`, driven by `build_fishnet_surface.py`, is the current
path and it reverses the direction of travel. Each support triangle is projected
*into* the rectilinear crop, cut there against the semantic island boundaries as
a plain 2D arrangement, and the pieces are mapped back to 3D by intersecting
their pixel rays with the triangle's own supporting plane. Within one crop the
camera is an ordinary pinhole, so that map is projective and exactly invertible.
A triangle whose footprint lies inside a single island is emitted untouched,
because the support triangulation is metre-scale photogrammetry and there is
nothing to gain from subdividing it where the semantics do not change. Full
account in `FISHNET.md`. Four things about it belong in this document:

- **It is a surface set, not a mesh.** Each face carries its class, class
  posterior, material posterior, confidence, outward normal, metric area, solid
  angle from the capture point, and the source pixels it was built from, so a
  propagation stage can use it directly as the first-hit acceleration structure.
- **Rejections are kept.** Faces that were considered and dropped go into a
  parallel table with the reason, so the propagation stage can see what was
  removed and why rather than inferring it from an absence.
- **Two guards are mandatory, not optional.** Triangles are clipped in camera
  space against the near plane before projection, because at Korenmarkt yaw 0
  four of the 1,431 visible triangles have a vertex behind the camera and those
  four own 33.5 % of the hit pixels. And the projection is a bijection on the
  *visible* surface only, so the mesh first-hit id buffer decides ownership and
  any piece a different triangle owns is rejected rather than painted.
- **The gain is a factor of 24, not the two orders of magnitude the brief
  wanted.** 257,310 faces to 10,534 across four yaws at Korenmarkt, against a
  hard floor of the visible support triangle count. Going below that floor means
  decimating the support mesh, which is a different change and one that
  `DECISIONS.md` has already rejected in its voxel-remesh form.

Fidelity is reported in both directions because they fail differently for
propagation. Round-tripping the output faces back into the image gives 0.12 to
0.25 % class change, 98.7 to 99.3 % coverage, 0.06 to 0.38 % phantom (a painted
pixel whose painting face is not the mesh first hit, which invents a scatterer)
and 0.7 to 1.3 % deleted (a paintable first-hit pixel with no output face, which
silently removes a path).

## Observation ledger

Each panorama record must preserve:

- provider panorama ID, capture date, copyright, and source location
- original image and exact spherical sampling transform
- initial and aligned camera pose, including a 6D covariance
- model identity, checkpoint digest, prompt catalogue, and thresholds
- per-pixel or per-region entity, material, and attribute probabilities
- view-local instance masks and embeddings
- image-resolution, blur, horizon, incidence, and occlusion quality terms
- links to every derived 3D association

Derived evidence is never written back over these records.

## Camera and geometry optimisation

Registration proceeds from robust global cues to local ones.

1. Metadata supplies the position and heading prior.
2. Segmented sky and rooflines align the panorama to the tile skyline without
   trusting noisy street-level tile geometry.
3. Stable facade corners, windows, signs, and DINO-style feature matches refine
   yaw, pitch, roll, and translation.
4. Shared features observed from several panorama locations enter a joint bundle
   adjustment. Camera poses, sparse landmarks, and a low-frequency deformation
   field on the tile mesh are optimised together.
5. The final Hessian or a sampled approximation supplies pose and geometry
   covariance rather than only a best-fit transform.

The tile mesh remains a prior. If several high-resolution street observations
agree that a surface is displaced, the fused model may locally depart from it.

## Inhouse support mesh resolution

The Inhouse acquisition path traverses the official Photorealistic 3D Tiles tree
and retains the deepest tiles that intersect the local region of interest. The
tile `geometricError` is an approximation-error metric in metres, not a triangle
edge length or texture resolution. Lowering a viewer's screen-space-error target
can request deeper descendants, but cannot create detail below the leaves served
by Inhouse.

The deepest reachable leaf at Korenmarkt reports a geometric error of
2.006368774808128 m, and a second traversal with a zero-metre cutoff found no
deeper descendants. This number is not a Korenmarkt measurement. The same value
came back bit-identical at all five sites probed, Korenmarkt, Piazza del Duomo,
Grand-Place, Times Square and Placa de Catalunya, so it is a global constant of
the tile level-of-detail scheme rather than a per-site quality signal. What does
vary between sites is how many leaf tiles the traversal returns, which is the
number to compare when judging support-mesh density. The blosm route can reach
the same source geometry here: its Inhouse
LOD6 band accepts tiles at or below 3 m, so these 2.006 m leaves satisfy its
highest-detail setting. LOD6 is not generally synonymous with leaf traversal
because blosm stops at the first in-band content tile. It cannot exceed the
server's leaf depth. blosm remains useful for interactive Blender acquisition
and inspection, while the standalone builder gives deterministic ECEF-to-ENU
placement and a compact PLY for automated projection. The earlier blosm proof
of concept used LOD5 and suffered a separate placement failure, so its cropped
mesh is not used as the current support geometry.

The final acquisition uses a 200 m ECEF culling sphere so elevated edge tiles
are not lost, followed by a 130 m horizontal mesh crop. The resulting support
mesh has 157,744 triangles and a 4.3 MB PLY. Compared with the previous 200 m
support mesh, it preserves 100% of the projected coverage at yaw 0, 90, and 180
degrees and 99.15% at yaw 270 degrees. A 60 m crop was rejected because it
retained only 88.39% at yaw 270. The support mesh can therefore stay modest:
semantic overlay triangles are generated from image-space tiles and split to one
source pixel at class boundaries, independently of Inhouse's coarse
triangulation.

The reproducible acquisition uses `download_inhouse_tiles.py --radius-m 200
--geometric-error-cutoff-m 0`, with explicit request and byte caps. The mesh is
then built with `build_inhouse_mesh.py --crop-radius-m 130`. API keys and session
tokens are used only in requests and are excluded from both manifests.

Two corrections to the paragraphs above, both later than the text they correct.

**Placement is read in float64 and never through Blender.** A 3D Tiles leaf
carries its full ECEF placement in the glTF node matrix, so a translation
component reads around 4.4e6 m, where float32 spacing is 0.5 m and Blender's
single-precision `Object.matrix_world` quantises every tile independently at
import. `semantic_twin/gltf.py` now reads node matrices out of the GLB in float64
and the builder matches them per object, with `matrix_world` mutated only for the
optional `--blend` export after the geometry has been written. The quantity that
mattered was never the rigid shift, which registration absorbs, but the
differential seaming between neighbouring tiles, which nothing downstream can
undo: worst tile-to-tile seam 0.661 m at Korenmarkt and 0.996 m at Milan, the
latter 93 wavelengths at 28 GHz. Corrected meshes are committed as `*_f64.ply`.
**Every registration, fishnet and texture-evidence number recorded before that
change, including the coverage-retention percentages above, was computed against
the superseded geometry.** The skyline residual moved only from 1.297 to
1.327 degrees, inside the seed spread, so nothing needs redoing on accuracy
grounds, but the provenance has to be stated wherever those numbers appear.

**The region of interest is a cylinder, not a ball.** It was a ball centred on
the ellipsoid, so horizontal reach fell off as `sqrt(r^2 - h^2)` with site
altitude. It is now a vertical cylinder about the site up axis, so `--radius-m`
means horizontal reach at every height and no site-height parameter is needed.
Milan at `r = 320` costs 691 requests, so the old 500-request cap would have
truncated it silently.

The support mesh's topology is genuinely defective, 16.6 % boundary edges and
essentially no watertight area, and `DECISIONS.md` records that voxel remeshing
fixes all of it and is rejected anyway: it raises the fishnet's face floor from
6,271 to 125,714, which is a twentyfold regression in exactly the quantity the
cutter exists to reduce, and it still leaves 6.9 degrees of median first-hit
normal tilt at the finest size that fits in memory. Measured from the camera
rather than from the edge table, only 0.091 % of first-hit rays land on a back
face and 1.00 % of visible area is inverted, because tiles overlap rather than
gap. The targeted fix is to orient per face from the camera's own first-hit votes
and make the BSDF two-sided.

## Soft projection

A semantic pixel is not assigned immediately to one triangle. Pose covariance,
mesh uncertainty, and depth ambiguity produce a probability distribution over
candidate surface elements. Evidence is spread over those candidates and
discounted by:

- segmentation information, not merely the winning score
- camera registration confidence
- geometry-match confidence
- projected pixel footprint at the hit distance
- incidence angle and visibility
- blur and panorama stitching quality
- dependence on near-duplicate source panoramas

The effective update is the product of these factors and the soft-association
probability. Uniform class predictions carry almost no directional evidence.
Contradictory confident observations remain visible as high posterior entropy.

## The second material channel: tile texture

The panorama only reaches surfaces a street-level capture sees, and at Korenmarkt
that is 3.7 percent of the support mesh from one capture position. In the adjoint
frame with four bounces, every interaction after the first can land outside it.
`semantic_twin/texture_evidence.py`, driven by `build_texture_evidence.py`,
supplies the fallback that nothing else in the pipeline reads: the 3D Tiles
leaves are already textured. Each support face is attached to the tile triangle
it was built from, the texel patch is classified, and a Dirichlet material
posterior is emitted for every face including the 96 percent no panorama sees.

**This channel is deliberately built to lose, and the ordering is encoded rather
than left to a downstream special case.** Texel density is measured per site
instead of assumed: at Korenmarkt the 205 cached tiles carry 27.6 texels per
square metre area-weighted median inside a 140 m crop, a 19.5 cm ground sample
distance. That resolves vegetation against opaque construction and it does not
resolve a mortar joint, a low-emissivity coating or a surface roughness, so the
channel claims **material identity only**. Roughness stays with the prior. The
panorama resolves 7.7 mm at 20 m, the crossover where the texture would win sits
near 510 m, outside every crop this study uses, and that ordering enters through
the `resolution` term of the emitted `ObservationQuality` plus a hard cap that
makes it impossible for the texture to move a class the panorama has already
won.

The measurement found something the resolution argument did not predict, and it
is worth carrying. On 3,204 faces the panorama does label, under spatially
blocked folds so the number is a transfer to unseen walls, the same descriptor
read off the panorama and then box-downsampled to 41 cm, *coarser* than the
texture, still scores 0.473 against the texture's 0.382. **The gap is viewpoint
and illumination, not sampling.** The tile texture sees a facade obliquely from
above and mostly in shadow, every opaque class collapses into one, and only
vegetation separates cleanly. So the honest scope of this channel is a
vegetation-against-construction discriminator with a material posterior attached,
not a material classifier that happens to be coarse.

## Object reconstruction

Objects missing from the aerial mesh are never painted onto their background ray
hit. They enter a separate instance pipeline.

1. SAM concept masks and image embeddings propose view-local instances.
2. Epipolar geometry, appearance, class compatibility, capture date, and overlap
   of uncertain 3D rays associate instances across panoramas.
3. Multi-view rays produce a probabilistic visual hull. Monocular depth and the
   tile mesh are weak priors, not final depth.
4. A class-aware shape family fits a compact watertight proxy:
   cylinders for poles and bollards, swept curves for cables, boxes and rounded
   hulls for vehicles, capsules for people, planes with thickness for signs and
   glass, and learned or reconstructed meshes where evidence supports them.
5. Residuals retain non-parametric corrections when a proxy is inadequate.

Each object hypothesis has existence, transient, pose, size, class, material,
and shape uncertainty. Static objects are fused across dates. People, bicycles,
and vehicles can be included in snapshot scenes or marginalised into occupancy
statistics for long-term scenes.

### The body layer, which is the first instance of that pipeline to exist

People are the first object class actually built, and they are built as a
separate transient layer rather than as a fifth item in the shape family above.
`semantic_twin/body_layer.py` holds the two ends that are pure arithmetic and can
be tested without a GPU: turning a label map into person instances to
reconstruct, and turning one reconstruction plus the recovered camera pose into
an ENU placement with its uncertainty. The model call is in `infer_sam3_body.py`
and the runner in `build_dynamic_bodies.py`, which emits one
`DynamicBodyArtifact` per person.

Three properties matter for the rest of the design.

- **Bodies never enter the static semantic atlas.** The fishnet already withholds
  their pixels as `transient_object`, on the class rather than on depth, because
  a person's monocular depth often agrees with the wall they stand against. The
  body layer puts back what was withheld, as posable geometry rather than as
  paint on a wall.
- **Range comes from evidence, not from apparent size**, whenever the depth
  fusion is usable, and the correction is applied radially so the bearing the
  segmenter measured survives it.
- **Nothing about the placement is averaged away.** What the placement is unsure
  about is carried in a `BodyUncertainty` record, which is the same discipline
  the material and roughness posteriors follow.

No exposure is computed in this layer. It produces geometry and uncertainty, and
the dosimetry stays downstream.

## mmWave requirements

At 28 GHz the free-space wavelength is about 10.7 mm, and at 60 GHz it is about
5.0 mm. This has four consequences.

First, poles, bollards, cables, signs, window reveals, street furniture, people,
and vehicles are electrically large and must exist as geometry if they can block,
reflect, diffract, or scatter important paths.

Second, coherent phase is much more sensitive than visual alignment. The
propagation export records path-length uncertainty and reports expected coherent
phasor retention. A visually convincing scene is not automatically suitable for
coherent validation.

Third, material names alone are insufficient. The RF layer needs
frequency-dependent complex permittivity or conductivity, thickness, surface RMS
roughness, roughness correlation length, and confidence. Roughness is evaluated
relative to wavelength and incidence angle to choose specular versus diffuse
scattering models.

The baseline material library implements Recommendation ITU-R P.2040-4 Table 3
and equations 57-59, with applicability ranges and provenance retained. The ITU
curves are representative priors rather than exact properties of the observed
wall. Site-specific measurements, literature values, moisture state, layered
construction, and inverse calibration update these priors. ITU-R P.833-10 is the
separate baseline for vegetation volumes, and ITU-R P.527-6 is required for
ground because P.2040's ground rows must not be extrapolated beyond 10 GHz.

**Roughness is a separate library, because P.2040 does not supply it.** This is
worth stating flatly, since the opposite is widely assumed and was written into
this repository's own prior-art notes. P.2040-4 Table 3 gives `eps' = a f^b` and
`sigma = c f^d` and nothing else: no roughness column, no RMS height, no
scattering coefficient. Its layered-slab model assumes smooth, planar, parallel
interfaces, so its reflection coefficients are smooth-surface coefficients by
construction. The one place it models scattering from a building surface,
section 2.3, defines the rough surface as a periodic array of circular cylinders
solved by lattice sums, which is a deterministic grating and not a Gaussian
random surface. P.2040-3 is the same and P.1411-13 has no facade roughness
either.

`config/surface_roughness.json` therefore supplies what `semantic_twin/materials.py`
refuses to default, over sixteen classes, and `ROUGHNESS.md` carries the
provenance for every entry. Four properties of that library shape the rest of
this design.

- **Every entry is a distribution with an evidence grade**, not a constant. A
  class carries a lognormal median and log standard deviation, a plausible range,
  a correlation length where the literature gives one, and a grade of
  `measured_mmwave`, `measured_metrology`, `inferred_radio` or `extrapolated`.
  `SurfaceRoughnessPrior.sample` draws it. Collapsing to the median before
  tracing is wrong, because `exp(-g^2)` is exponential in the square of the
  height and the mean of the function is far from the function of the mean.
- **Radio-fitted values cannot enter the library at all.**
  `SurfaceRoughnessPrior.__post_init__` raises if `radio_fitted` is true. Feeding
  a height that was fitted to reflection measurements into a twin that then
  predicts reflection loss validates the model against the data it was fitted to,
  one citation removed.
- **Face and wall are different objects and are never averaged.** The
  `rms_height_mm` field is the finish of a monolithic patch, which is what a
  profilometer measures and what essentially every published number is. A
  metre-scale facade patch, which is what a fishnet face stands for, additionally
  carries mortar joints, course relief, pointing, sills and reveals at centimetre
  pitch, and that structure lives in a separate `periodic_component` block. The
  gap is two orders of magnitude, and averaging the two produces a value that
  describes neither.
- **Eight of the sixteen classes are not Gaussian surfaces**, and
  `SurfaceRoughnessPrior.specular_power_fraction` raises for them unless the
  caller passes `allow_periodic=True`. A mortar grid, sett paving, corrugated
  cladding or a tile course reradiates into discrete grating orders at
  `sin(th_m) = sin(th_i) + m lam/d`, not into a broad lobe. The refusal exists so
  that gap stays visible instead of being absorbed into a plausible-looking
  scattering coefficient. A rigorous replacement is under construction in
  `semantic_twin/floquet.py`, `masonry.py`, `rcwa.py` and `kirchhoff.py`, and
  nothing in the projection or export path imports it yet.

The consequence for calibration effort is counter-intuitive and is a result in
its own right: at 28 GHz the specular loss is under one percent for any RMS
height below 85 micrometres, which covers glass, coil-coated metal, timber, brick
faces, glazed tile and polished stone by factors of ten to ten thousand. Their
roughness could be wrong by an order of magnitude without moving a decibel. The
classes where the number decides the answer are render, textured concrete,
dressed sedimentary stone, asphalt and paving.

Sionna's built-in ITU materials currently provide frequency-dependent
permittivity and conductivity, but their default diffuse-scattering coefficient
is zero. The final exporter must therefore emit explicit thickness, scattering,
cross-polarisation, and scattering-pattern parameters instead of assuming an ITU
material name completes the model.

Fourth, triangle size is not globally tied to wavelength. Large planar surfaces
can remain coarse, while curvature, silhouettes, material boundaries, thin
objects, and diffraction edges require refinement. Adaptive remeshing follows an
electromagnetic error criterion rather than uniform tessellation.

The formulas in `semantic_twin/mmwave.py` make wavelength-scaled phase,
roughness, and feature-size checks explicit.

## Building the final scene

The export is selected from the highest-confidence evidence, but uncertainty is
not discarded.

- The nominal scene uses maximum-posterior geometry and RF parameters.
- An ensemble samples plausible poses, object existence, material models, and
  roughness parameters.
- Stable path families across the ensemble receive high trust.
- Paths that appear only under a narrow geometric hypothesis are flagged.
- Incoherent and coherent outputs are reported separately because phase
  uncertainty can invalidate coherent sums while leaving power bounds useful.

The exporter should generate watertight object proxies, consistent outward
normals, semantic/material boundaries, explicit diffraction edges, and a mapping
from every emitted primitive back to its evidence ledger.

## Validation

The strongest validation is predictive, not visual.

1. Leave one panorama out, reconstruct from the others, and predict its masks,
   depth edges, and object silhouettes.
2. Compare aligned tile renders against every panorama at multiple scales.
3. Measure multi-view instance reprojection and epipolar residuals.
4. Track posterior entropy and coverage by physical surface area, not image pixels.
5. Compare simulated channels or power-delay profiles with measurements where
   available.
6. Run scene ensembles and report path, received-power, and exposure uncertainty.

## Active view selection

Street View locations should not be consumed uniformly. The next panorama is the
one with maximum expected information gain over uncovered surfaces, uncertain
materials, unresolved object depth, and important transmitter-to-human path
regions. This naturally selects close views of small clutter and avoids spending
equal inference on redundant road imagery.

The antenna and human locations can further weight the objective. Geometry that
cannot participate in relevant path families may remain coarse, while uncertain
first-bounce and blockage regions receive additional viewpoints and reconstruction
effort.

## What exists, and what is still a design

Most of this document is written in the present tense whether or not the thing
described has been built. This section separates the two, because the difference
has already caused numbers to be quoted for subsystems that do not exist.

**Built and measured at one site (Korenmarkt), one panorama, four yaw crops.**

| Subsystem | Module | State |
|---|---|---|
| Tile acquisition and float64 placement | `download_inhouse_tiles.py`, `semantic_twin/gltf.py`, `build_inhouse_mesh.py` | Built, two sites |
| Support-mesh queries | `semantic_twin/support_mesh.py` | Built |
| Skyline registration | `semantic_twin/align_skyline.py` | Built, single-pose |
| Panorama semantics | `semantic_twin/semantics.py`, `sam3_concepts.py`, `concepts.py` | Built, two taxonomies |
| Monocular depth and mesh-versus-depth decision | `infer_unidepth.py`, `infer_depth_anything.py`, `compare_mesh_depth.py` | Built, gated, degraded mode at this site |
| Fishnet cutter | `semantic_twin/fishnet.py` | Built |
| Evidence accumulation | `evidence.py`, `atlas_ledger.py`, `decal_atlas.py` | Built |
| Texture material channel | `semantic_twin/texture_evidence.py` | Built and measured to be the weaker channel |
| Body layer | `semantic_twin/body_layer.py`, `infer_sam3_body.py` | Built |
| Material and roughness libraries | `semantic_twin/materials.py`, `config/*.json` | Built |
| Sionna scene export | `project_semantics.py`, `semantic_twin/export.py` | Built, but only from the superseded centroid path |

**Designed and not built.** The multi-panorama joint bundle adjustment with a
mesh deformation field and a sampled Hessian. The full soft-projection product
over all eight discount terms. The object-reconstruction pipeline for anything
other than people. The scene ensemble and every uncertainty output that depends
on it. Active view selection. **An exporter that takes fishnet faces to a
propagation scene**, which is the gap that keeps `project_semantics.py` alive.
Every item under Validation above except the render comparison.

**Known stale references in code comments.** `semantic_twin/texture_evidence.py`
still says in its module docstring that `build_inhouse_mesh.py` rounds placement
through Blender's single-precision `Object.matrix_world` and that
`match_support_faces` therefore estimates and removes a per-tile offset. The
first half is no longer true, and the per-tile offset estimation is now
compensating for a defect that has been fixed upstream. That file is owned
elsewhere and the correction is flagged rather than made here.
