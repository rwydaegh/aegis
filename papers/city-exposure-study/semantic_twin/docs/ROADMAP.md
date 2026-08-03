# Roadmap

The phase plan for the semantic twin, from the first cleanup to the cross city
rollout. Until this file existed the plan lived only in a session scratch file
outside the repository, which is why it is written down here.

Status is one of **done**, **in progress**, **not started** or **rejected**.
Rejections stay in the list with their reason, because the reason is worth more
than the item.

The rollout is eleven squares, not the ten the early phases say. The phase names
below keep the count they were written with, and the headline run is the eleven
site table of `PAPER_METHODS.md` section 9.2.

The propagation phases are specified in detail elsewhere and this file does not
repeat them. `MONOSTATIC_SBR.md` section 10.3 has the module layout, section 11
the validation suite, section 12 the cost and storage model.

## Phase 0: cleanup and commit. Done

Deleted the superseded multiview pose and refine modules, the one-off figure
scripts and the scratch seed study, folding the seed logic into
`semantic_twin/align_skyline.py` as a first-class output. Consolidated three
copies of `llh_to_ecef` and three of
`panorama_rotation`. Corrected the `DESIGN.md` reading of the leaf
`geometricError` as a Korenmarkt result when it is a global constant of the tile
scheme.

## Phase 1: registration. Done

`semantic_twin/mapillary.pose_from_metadata` was discarding `computed_rotation`
and hardcoding a level camera, throwing away measured gravity tilts of 4.5, 7.8
and 26.8 degrees
that were already on disk. Camera altitude is now measured per camera by a
downward ray cast against the support mesh rather than taken from one scene-wide
constant. Every pose ships a covariance from an independent seed study instead of
a single residual, after the earlier claim of a flat three metre valley turned out
to be an artefact of the optimiser stopping at `maxiter=35` in eight runs out of
eight. The sky-versus-mesh conflict is surfaced as a per-view metric, which is a
registration check independent of the skyline objective and costs nothing because
the fishnet already computes it.

Open: Milan's two objectives disagree on horizontal position by 2.5 m against a
0.21 m seed spread, and a 0.33 m systematic between depth-derived and
skyline-derived altitude, same sign at both sites, is unexplained.

## Phase 2: geometry correctness. Done, with one rejection

Tile placement is read in double precision from the glTF node matrices. The
defect was at import rather than at the ENU assignment: a leaf carries its full
ECEF placement in the node matrix and `Object.matrix_world` is float32, which
quantises at half a metre out at Earth radius. Worst differential tile-to-tile
seaming was 0.66 m at Ghent and 0.996 m at Milan, the latter 93 wavelengths at
28 GHz. Now under 20 micrometres against an independent assembler.

The region of interest was a ball centred on the ellipsoid, so horizontal reach
shrank with site altitude and Milan got 116 m from a nominal 200 m. It is now a
vertical cylinder about the site up axis.

**Rejected: the planar merge of the support mesh by voxel remeshing.** It closes
the mesh completely, and it is still the wrong move, but for one reason rather
than the four first recorded. Three of those four were measuring a
misparameterisation, a 0.30 m solidified shell inside voxel grids up to seven
times coarser, and do not survive a correct rerun: it does not delete the
pavement, it does not raise the fishnet face floor, and it does not trace faster
either, which retires the argument in its favour as well. The surviving reason is
that a level set cannot hold the surface still, so flatness and range fidelity
trade monotonically and no voxel size beats as built on both. The corrected
19-candidate sweep and the recipe to use if closure ever becomes mandatory are in
`DECISIONS.md`. The targeted fix instead is per-face orientation from the
camera's own first-hit votes plus a two-sided BSDF.

**Kept from that work: plane segmentation, for a different purpose.**
Reconstructing the support mesh from plane primitives loses on closure and
orientation because the source is a doubly sided shell, but the segmentation
itself yields 5,095 planar clusters at a 1.5 cm median in-plane residual and is
the primitive section 6.3 wants for image source enumeration.

## Phase 3: pipeline integration. Done

Fishnet replaced the quadtree on the production path. Semantics regenerated at
native 1536 rather than the checkpoint's 384 default, which recovered seventeen
clutter classes including poles, street lights and traffic signals that the
photogrammetry does not contain at all. Texture evidence added for the faces no
panorama sees. Projected ten-city compute cut from 171 to 58 hours, with
`groups_by_triangle` down from 45 minutes to 2.2 seconds. Both figures are
projections made before the rollout, and the rollout that happened does not test
them, because it ran with the semantic binding switched off.

## Phase 4: propagation core. Done, on a different module layout

The twelve modules of `MONOSTATIC_SBR.md` section 10.3 were `atlas`, `planes`,
`bsdf`, the `materials` extension, `transport`, `prune`, `adjoint`, `tensor`,
then `monostatic`, `specular`, `analytic` and `sionna_check`. What was built
instead is `semantic_twin/propagation/`: `tracer.py` (the shoot and gather SBR
loop with the free first hit, the Rayleigh specular split and an opt-in
`PathRecorder`), `directions.py` (the illumination laws), `geometry.py` (the
Mitsuba 3 ray-cast backend plus the plane and sphere backends the closed form
tests need), `scene.py`, `semantic_binding.py`, `walk.py`, `bystanders.py`,
`exposure.py`, `closed_form.py` and `report.py`. The monostatic loop, the
image-source specular search and the Sionna bistatic cross-check were not built.
Section 10.3 is the design, not the inventory.

Of the two flagged correctness risks, one was dissolved and one is handled.
Polarisation is not carried at all: the tracer averages the two Fresnel
coefficients into an unpolarised power, so there is no Jones bookkeeping to gate
behind a reciprocity test, and the cross polarisation ratio is lost. The Dr.Jit
`si.n` shape hazard is real and `MitsubaGeometry.intersect` asserts the
`(3, N)` layout rather than assuming it.

**Sequencing note added after the prior-art audit, and then half retired.** The
crop radius, not diffraction, was the largest hole. Section 7.5 measured that
130 m has not converged, and the rooftop illumination weight was said to need
sources outside the crop for 79 to 95 percent of its measure. That percentage is
superseded: it was computed under the fixed-height elevation law replaced on
2026-08-02, and `MONOSTATIC_SBR.md` section 2.7.1 carries the corrected weight.
The sequencing call was right anyway. The sweep ran, the study re-acquired at
250 m, and the eleven site table is a 250 m run.

## Phase 5: validation. Partly done

Of the seven tests of `MONOSTATIC_SBR.md` section 11, four are in
`tests/test_propagation.py`: the dielectric and PEC ground plane under the
observation point against `closed_form.py`, the closed lossless cavity, the
Lambertian ground plane against `1 + 2 sin(alpha)`, and the invariants as
property tests including the ReLU bound, the sky-fraction identity for the zero
bounce term and the image-theory excess delay. Not done: image sources and plate
RCS, the bistatic cross-check against Sionna, the empirical question of whether
monostatic backscatter predicts isotropic susceptibility, and
leave-one-panorama-out predictive validation. No external tool has ever seen this
scene.

The bounce count curve is now done, in `BOUNCE_BUDGET.md`, and the production
runs are fixed at three surface interactions with Russian roulette off. Still not
done: the dynamic-range threshold curve. Publish the curve, not the number.

The leave-one-panorama-out test is the one that matters most for how any accuracy
figure gets read. Calibrated ray tracers report residuals after fitting material
parameters against the same measurements, which is a different and easier
quantity than a blind prediction on geometry the tracer has never seen. It is
also the test the eleven site run cannot support as it stands. Ten of the eleven
sites carry no material binding of any kind, and three of them have no panoramas
at all, so there is no panorama to leave out.

## Phase 6: ten cities. Done as eleven, geometry only

Eleven squares are traced at a 250 m crop, 80 standpoints each, at three surface
interactions, under the corrected illumination law and on the measured ground
datum, as `city250_L3_*` in `outputs/exposure_korenmarkt/`. The earlier
`city250_corrected_*` sweep of the same eleven squares is kept beside it and is
not the headline, because its ground datum put the Krakow and Toulouse walks on a
roof. `AGGREGATE_REBUILD.md` audits the replacement. Krakow Rynek, Toulouse Capitole, Mexico Zocalo,
London Trafalgar, Prague Staromestske, Milan Duomo, Madrid Plaza Mayor,
Korenmarkt, Brussels Grand-Place, Tokyo Hachiko and New York Times Square.

**What this run does not use is any image evidence.** Every one of the eleven
manifests carries `semantic_binding.materials = "geometric"` with
`covered_fraction_by_face` and `covered_fraction_by_area` both exactly 0.0, so
the surface class comes from the face normal alone and the panorama pipeline
contributes nothing to the headline numbers. The screening rationale below still
holds, and so does the caveat that panorama density samples the street network
rather than the population, but GHSL population weighting is still not applied.

Screen candidate cities on official Street View coverage with a connected
panorama link graph before spending anything, since zero neighbour links means no
walk at all and only official captures are linked. Prefer pedestrianised squares,
where trekker capture puts panoramas where pedestrians actually stand: Milan is
2.8 m median spacing against Ghent's 10.5 m car track. The walk is the link graph
traversed, so no synthetic routing is needed.

## Work outside the original phases

Started because the evidence demanded it rather than because the plan called for
it.

- The roughness prior graded by provenance, `ROUGHNESS.md` and
  `config/surface_roughness.json`, after the literature turned out to be
  circular: widely cited facade roughness heights trace back to a fit of height
  jointly with permittivity against reflection data.
- `PRIOR_ART.md`, a hostile review of what the published work already owns.
- The masonry scattering work, deriving the bistatic response of brickwork from
  construction standards rather than fitting it to measurements, since no
  measurement will be taken.
- The procedural showcase render.

## Out of scope

Diffraction in version one, stated up front rather than hidden. Coherent
multipath superposition at the body until pose covariance exists. Transmission
and outdoor-to-indoor. And any monostatic result presented as an exposure claim.

## Seeing it, added after the first exposure results

The walkthrough blends, `build_propagation_blends.py`. One Blender file per site
carrying the support mesh, the recorded ray paths, the angular power spectrum,
the illumination sources at true range and height, the walk coloured by
susceptibility and the phantom coloured by absorbed power density. Built for
Korenmarkt, Krakow, Times Square and Grand Place, which span the measured range
rather than represent it.

The enabling change is `PathRecorder` in the tracer: a bounded, opt-in observer
that keeps a capped number of ray polylines and is asserted to leave every
traced number bit identical. The storage rule is unchanged, since no path table
reaches disk and production runs do not enable it.

Two defects were found by building it rather than by reading anything. The
elevation law and the height bands of section 2.7 disagree, which only shows up
when the model is sampled rather than evaluated. That one became the 2026-08-02
illumination-law correction, and it moved every directional number in the study.
And camera placement by fixed offset fails at any site that is not a low rise
square, which is now a search for an open bearing rather than an assumption that
one exists.

## What is actually blocking the paper

Three things, in the order they threaten a submission.

**The eleven site table carries no image evidence.** Every site is
`materials: geometric` with covered area 0.0, so the headline result is a
geometry-and-prior study wearing the name of a semantic twin. The one binding
that exists is Korenmarkt at the 130 m crop, and the crop study says 130 m is not
converged for either directional model, so the semantic ablation and the
converged cross city table cannot currently be the same run.

**The evidence pipeline ran on almost nothing.** SAM 3, which is the entire
material axis, ran on 2 of the 96 panoramas that carry semantics, Korenmarkt and
Milan Duomo. Of the 83 skyline registrations in
`outputs/registration_sky_conflict.csv`, 14 feed something downstream, the twelve
Korenmarkt walk poses plus the two single-panorama sites. The other 69, all of
Brussels, Mexico, New York, Prague, Madrid and Tokyo, feed no result at all.

**Nothing has been validated against an external tool.** Section 11's Sionna
cross-check is not built, and neither is leave-one-panorama-out.
