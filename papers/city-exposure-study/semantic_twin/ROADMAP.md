# Roadmap

The phase plan for the semantic twin, from the first cleanup to the ten-city
rollout. Until this file existed the plan lived only in a session scratch file
outside the repository, which is why it is written down here.

Status is one of **done**, **in progress**, **not started** or **rejected**.
Rejections stay in the list with their reason, because the reason is worth more
than the item.

The propagation phases are specified in detail elsewhere and this file does not
repeat them. `MONOSTATIC_SBR.md` section 10.3 has the module layout, section 11
the validation suite, section 12 the cost and storage model.

## Phase 0: cleanup and commit. Done

Deleted the superseded multiview pose and refine modules, the one-off figure
scripts and the scratch seed study, folding the seed logic into `align_skyline.py`
as a first-class output. Consolidated three copies of `llh_to_ecef` and three of
`panorama_rotation`. Corrected the `DESIGN.md` reading of the leaf
`geometricError` as a Korenmarkt result when it is a global constant of the tile
scheme.

## Phase 1: registration. Done

`mapillary.pose_from_metadata` was discarding `computed_rotation` and hardcoding
a level camera, throwing away measured gravity tilts of 4.5, 7.8 and 26.8 degrees
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
the mesh completely, and it is still the wrong move. It raises the fishnet face
floor twentyfold, costs specular fidelity that no feasible voxel size buys back,
and at 2 m voxels it deletes the pavement outright. The full argument and the
measurements are in `DECISIONS.md`. The targeted fix instead is per-face
orientation from the camera's own first-hit votes plus a two-sided BSDF.

## Phase 3: pipeline integration. Done

Fishnet replaced the quadtree on the production path. Semantics regenerated at
native 1536 rather than the checkpoint's 384 default, which recovered seventeen
clutter classes including poles, street lights and traffic signals that the
photogrammetry does not contain at all. Texture evidence added for the faces no
panorama sees. Ten-city compute cut from 171 to 58 hours, with
`groups_by_triangle` down from 45 minutes to 2.2 seconds.

## Phase 4: propagation core. Not started

The twelve modules of `MONOSTATIC_SBR.md` section 10.3, in dependency order:
`atlas`, `planes`, `bsdf`, the `materials` extension, `transport`, `prune`,
`adjoint`, `tensor`, then `monostatic`, `specular`, `analytic` and
`sionna_check`.

Two known correctness risks, both flagged in that document: polarisation
bookkeeping, which must be gated behind the reciprocity test, and Dr.Jit
returning `si.n` shaped `(3, N)` rather than `(N, 3)`.

**Sequencing note added after the prior-art audit.** The crop radius, not
diffraction, is now the largest hole. Section 7.5 already measured that 130 m has
not converged, and the rooftop illumination weight needs sources outside the crop
for 79 to 95 percent of its measure. The crop convergence sweep is cheap, one
Mitsuba run per radius, and it should run before the module build rather than
after, because the answer changes the scene every later stage consumes.

## Phase 5: validation. Not started

The seven tests of `MONOSTATIC_SBR.md` section 11, ordered from closed form to
tool agreement: the ground plane under the observation point, the Lambertian
spherical cavity, the invariants as property tests, image sources and plate RCS,
a bistatic cross-check against Sionna, the empirical question of whether
monostatic backscatter predicts isotropic susceptibility, and leave-one-panorama-out
predictive validation.

Plus the two convergence curves that turn parameters into measurements: bounce
count and the dynamic-range threshold. Publish the curve, not the number.

The leave-one-panorama-out test is the one that matters most for how any accuracy
figure gets read. Calibrated ray tracers report residuals after fitting material
parameters against the same measurements, which is a different and easier
quantity than a blind prediction on geometry the tracer has never seen.

## Phase 6: ten cities. Not started

Screen candidate cities on official Street View coverage with a connected
panorama link graph before spending anything, since zero neighbour links means no
walk at all and only official captures are linked. Prefer pedestrianised squares,
where trekker capture puts panoramas where pedestrians actually stand: Milan is
2.8 m median spacing against Ghent's 10.5 m car track. The walk is the link graph
traversed, so no synthetic routing is needed. Population weighting via GHSL is
still required for any population claim, because panorama density samples the
street network rather than the population.

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
