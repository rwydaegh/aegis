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

The current face-level accumulator is in `semantic_twin/evidence.py`. It is the
first storage backend, not a commitment to preserving the source triangulation.
A later adaptive surfel or semantic-atlas backend can expose the same posterior
interface.

`project_semantics.py` assigns one panorama sample to each source-face centroid
and owns the RF export: it is the only writer of `scene.xml`, the Sionna RT
scene that binds each material group of triangles to an ITU radio material. Its
semantic boundaries inherit the photogrammetry triangulation, so it is not the
right source of surface detail, but nothing else currently produces a traceable
scene and it stays until the fishnet path grows an exporter.

`project_pixel_semantics.py` is the pixel-faithful projection path. It starts
from each 1024 x 1024 perspective label map and builds adaptive image tiles.
Uniform interiors may merge, but mixed tiles recursively split down to one input
pixel. Tile corners, edge midpoints, and centres are ray-cast onto the first-hit
Inhouse surface, with further subdivision at depth or normal discontinuities.
The resulting Blender geometry therefore preserves source-pixel semantic
boundaries while using the Inhouse mesh only as geometric support.

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
