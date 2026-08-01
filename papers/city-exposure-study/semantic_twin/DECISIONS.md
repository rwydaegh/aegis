# Decision record

Running log of the calls made on the semantic twin, why, and what would reverse
them. Newest section last. Questions asked and answered in chat are not recorded
here unless they changed a decision.

## 2026-08-01

### Observable: adjoint transfer tensor, not the monostatic loop

**Decision.** The headline per-location quantity is `T_S(Omega, tau, f)`, the
field at S produced by a unit plane wave arriving from direction Omega, built by
recording every ray that escapes the neighbourhood after up to three
interactions. The co-located monostatic response is retained as a derived
diagnostic.

**Why.** The monostatic response is one entry of the environment's transfer
operator, the diagonal. Knowing `G(S,S)` does not determine `G(S,x)` for an
external transmitter, because the loop coefficient factorises into two one-way
legs and reciprocity gives their product, not the factors. Concretely it ranks
locations backwards: an open street with clear line of sight to a mast has high
exposure and a weak loop, an enclosed courtyard with no mast has low exposure and
a strong loop. So it is not an upper bound and cannot be defended as a
representative worst case.

**Why it costs nothing.** Same rays, same free first hit, same cull, same
materials. The only change is which rays are written down at the end. The current
formulation discards every ray that fails to close, which is nearly all of them.

**What it buys.** Exposure factorises as an integral of
`Tr[T_S Q_S T_S^H]` over the sphere, separating an expensive
deployment-independent per-location quantity from a cheap assumption-laden one.
Transmitter hardware never appears, only an angular incident-power distribution,
which sidesteps the unparameterisable 5G and 6G antenna zoo. A genuine worst case
does exist in this framework: `chi_max(S)`, the largest singular value of `T_S`
over arrival directions.

**Reverses if.** The exit-surface definition proves untenable, specifically if
masts at 50 to 200 m turn out to be too near for a plane-wave treatment and the
exit point rather than only the exit direction is needed for coherent work. Then
fall back to a near-field formulation, not to the monostatic loop.

Full argument in `METHOD.tex`.

### Line of sight is the zero-bounce term, measured not modelled

**Decision.** Line of sight enters as `T_0` in the same tensor rather than as a
separately bolted-on Friis integral. Its angular support is the set of directions
where the mesh first-hit range exceeds the source range, which the depth buffer
already provides. The sky mask is the special case of infinite first-hit range.

**Consequence worth banking separately.** Line-of-sight probability becomes
measured per location from street-level imagery rather than taken from the fitted
3GPP UMa or UMi curve. Ten cities of measured p_LOS against the standard model is
a self-contained result needing segmentation only, no ray tracing.

**On the maximum-distance cutoff.** Not optional. For uniform base-station
density the line-of-sight integral goes as the integral of `1/d^2` against
`2 pi d dd`, which diverges logarithmically. What regularises it is p_LOS
decaying with distance, and since p_LOS is now measured, the cutoff is set by data
rather than assumed.

### Ray termination: admissible bound, per-class range law

**Decision.** Cull a direction using an upper bound on what it could contribute,
computed with the most reflective material still admissible under that pixel's
posterior and the shortest geometric path. Discarded swaths are then provably
negligible rather than probably negligible.

**The range law splits by semantic class.** For a ray subtending fixed solid
angle, an extended facade has an illuminated footprint growing as `Omega R^2`, so
substituting into the radar equation leaves the per-ray return falling as `R^-2`
and the dynamic range mapping through `20 log10`. A discrete scatterer whose
cross-section does not grow with range (bollard, pole, sign, person) keeps `R^-4`
and maps through `40 log10`. One budget, two cull distances, and the segmentation
already knows which regime each direction is in. At 30 dB referenced to 10 m that
is 316 m for facades against 56 m for clutter.

This is the first place in the design where the semantic layer buys propagation
accuracy rather than only material labels.

**Effective distance.** Reflection loss may be folded into range as
`r_eff = r / sqrt(eta)` so one budget prunes uniformly across bounce orders. Valid
for pruning bounds only. It must never enter the field sum, because a complex
reflection coefficient carries phase no real distance can represent.

### Architecture: hybrid search plus Monte Carlo, not one or the other

**Decision.** Specular contributions are found by an image-method search over
pairs and triples of visible surface elements. Diffuse contributions are found by
ordinary gather-based Monte Carlo. Both are required.

**Why the search is necessary.** For a co-located two-bounce specular path the
launch direction supplies two free parameters and the closure condition imposes
two constraints, so solutions are isolated points on the launch sphere. A set of
isolated points has zero measure, so random ray shooting finds them with
probability zero regardless of ray count. This is a structural incapability, not
an efficiency problem, and it is what makes the pair-search framing correct rather
than merely convenient.

**Why the search is not sufficient.** At 28 GHz a brick wall with 1 mm RMS
roughness retains only 25 percent of its reflected power in the specular lobe at
normal incidence, rising to 96 percent at 80 degrees. Most of the reflected power
in a real scene is diffuse, lives on a continuum, and is handled correctly by
Monte Carlo with a gather at each bounce.

**Consequence for geometry.** The search is quadratic in surface-element count.
The current image-space quadtree emits 76,718 elements for one view, giving
5.9e9 ordered pairs. A fishnet target of order 1e3 elements gives order 1e6.
Aggressive planar simplification is therefore a hard requirement for tractability,
not an aesthetic preference.

### Polarisation: carry the 3x3 from the start, report the scalar

**Decision.** Data structures carry a polarisation-complete field amplitude even
though the first paper reports the scalar `K_S`.

**Why.** Retrofitting polarisation means touching every path-accumulation site in
the tracer, which is the one thing genuinely painful to change later, whereas
carrying a 3-vector now is nearly free and `materials.py` already evaluates
polarisation-dependent Fresnel coefficients that are currently discarded. The
effect is first order, not a refinement: brick at 28 GHz and 60 degrees incidence
gives -5.02 dB for TE against -26.46 dB for TM, a 21 dB split near the
pseudo-Brewster angle.

### The hidden middle bounce is a ray cast, not an inference problem

**Decision.** For the three-bounce path S -> A -> B -> C -> S where B is out of
view, B is obtained by ray casting against the support mesh. No learned
scene-completion model.

**Why.** External advice framed B as unknown and proposed a machine-learning
programme to infer it, because it assumed no 3D prior was available. We have the
tile mesh. What we genuinely lack at B is its material, since B carries no image
evidence, and that is handled by marginalising over the class prior conditioned on
the visible surroundings, with the resulting spread reported as uncertainty.

### Site selection is gated on official Street View coverage

**Decision.** Piazza del Duomo, Milan is the second site. Times Square, Grand-Place
and Placa de Catalunya are rejected for now.

**Why.** Measured directly from the Map Tiles API:

| Site | px/deg | tilt / roll | neighbour links |
|---|---|---|---|
| Korenmarkt Ghent | 45.5 | 102.33 / 4.24 | 2 |
| Duomo Milan | 37.0 | 85.79 / 354.47 | 4 |
| Grand-Place Brussels | 24.2 | 90 / 0 | 0 |
| Times Square New York | 15.2 | 90 / 0 | 0 |
| Placa de Catalunya | 14.9 | 99 / 359.7 | 0 |

`tilt = 90, roll = 0` exactly means no orientation metadata, not a level camera.
That is the same degenerate prior that leaves Mapillary registering at 5.81
degrees against Street View's 2.83. Three of the five candidates are user
photospheres with no pose metadata and no neighbour links.

**The walk requirement makes this binding.** A walk is the panorama link graph
traversed. Zero links means no graph and no walk at all. Only official captures
are linked. So official Street View coverage with a connected pano graph is a
precondition, testable against a candidate city in seconds, and it should screen
all ten cities before any budget is spent.

**Trekker versus car capture matters.** Three link-hops out, Milan gives 22
panoramas at 2.8 m median spacing, Ghent gives 11 at 10.5 m. Milan's spacing is
walking-pace trekker capture on a pedestrianised square, so those panoramas sit
where pedestrians actually stand. Ghent's is car-track, roughly 3 m further from
the facades than a pedestrian would be. This matters because the free-first-hit
trick pins the evaluation point to the exact panorama position: you cannot offset
laterally toward the pavement without losing the panorama lookup. Prefer
pedestrianised squares.

**Caveat to carry into the paper.** Panorama density samples the street network,
not the population. A population-exposure claim needs the walk locations weighted
by pedestrian density, for which GHSL is already in the study code.

**Rejected reasoning worth recording.** Times Square has 631 leaf tiles against
Milan's 77, three to eight times the support-mesh density, and much richer
material and clutter diversity. That was the initial recommendation. It was
overturned because mesh density is the weak input by design and imagery quality
plus pose metadata are the strong ones, so buying the former with the latter is
the wrong trade.

**Not a per-site quality signal.** The deepest reachable leaf `geometricError`
came back bit-identical at 2.006368774808128 m across all five sites. It is a
global constant of the tile LOD scheme. `DESIGN.md` currently over-reads it as a
Korenmarkt-specific audit result.

### Segmentation runs at native resolution

**Decision.** Inference resolution becomes an explicit recorded parameter with a
default around 1536, not an accident of the checkpoint config.

**Why.** The processor config shipped with
`facebook/mask2former-swin-large-mapillary-vistas-semantic` is
`{'height': 384, 'width': 384}` with `do_resize: True`, so every crop was
downsampled to 384x384 before inference regardless of its size. The 1536x1536
hires runs produced identical semantic resolution to the 1024x1024 runs at 2.25
times the cost. Measured on a real Korenmarkt crop on the A6000:

| native input | mask logits | classes found | time |
|---|---|---|---|
| 384 (old default) | 96 | 15 | 85 ms |
| 1024 | 256 | 26 | 249 ms |
| 1536 | 384 | 32 | 511 ms |
| 2048 | 512 | 31 | 937 ms |

Nothing is lost going up and 2048 adds nothing over 1536. The 17 classes recovered
only at native resolution are Bike Rack, Pole, Street Light, Utility Pole, Traffic
Sign front and back, Traffic Light, Mailbox, On Rails, Curb, Bicyclist and Other
Rider, which is precisely the small clutter `DESIGN.md` requires as geometry at
millimetre wave and which the photogrammetry does not contain at all. Cost is 12 s
per panorama instead of 2.

All existing Korenmarkt semantic outputs predate this and are missing the clutter
classes.

### Registration is not yet trustworthy, and the reported residual is not an error bar

**Finding, not yet a decision.** Verified directly: the skyline optimiser's `dz`
bound is `(-1.5, 3.0)` and all six poses shipped in this repository landed between
-1.37 and -1.49, pressed against the floor every time. Relaxing that single bound
dropped the Korenmarkt residual from 2.97 to 2.03 degrees. An eight-seed repeat
showed the objective is flat over roughly a 3 m by 2.5 degree valley, so poses
differing by metres score equally and the single reported residual is not an
accuracy estimate. `view_02` is saturated in pitch and roll simultaneously,
consistent with its true gravity tilt being 26.8 degrees against a 6 degree search
range.

Separately, `mapillary.pose_from_metadata` hardcodes `tilt_deg = 90, roll_deg = 0`
while discarding `computed_rotation`, which Mapillary's own structure-from-motion
supplies in metadata already on disk and which encodes gravity tilts of 4.5, 7.8
and 26.8 degrees for the three selected panoramas.

**Implication for the method.** The free-first-hit trick assumes the panorama is
registered to the mesh. Until pose uncertainty is quantified and propagated rather
than reported as a single best-fit number, every downstream claim inherits an
unmeasured error. Pose covariance must become an output, not a footnote.

### Geometry defect: ECEF to ENU is being done in single precision

**Finding.** `build_inhouse_mesh.py` assigns the ECEF-to-ENU transform through
`mathutils.Matrix` and `Object.matrix_world`, both float32. Verified under Blender
4.5 that 6378137.123456789 stores as 6378137.0. With ECEF translations near 6.4e6
and ENU results near 100 m this is catastrophic cancellation: a mean rigid shift
of about 0.22 m and up to 0.44 m of differential tile-to-tile misregistration, so
neighbouring photogrammetry tiles seam against each other. That is 41 wavelengths
at 28 GHz and it is unrecoverable downstream.

### Geometry defect: the acquisition ROI is centred on the ellipsoid, not the terrain

**Finding.** `download_inhouse_tiles.py` centres the region of interest at height
zero and tests bounding volumes with a 3D distance, so horizontal coverage at
street level is `sqrt(radius^2 - h^2)` for a site at ellipsoidal height h, and
nothing above `z = radius` is inside the region at all. Ghent at roughly +50 m got
away with it. This is a per-city landmine for the ten-city run, since European
city-centre ellipsoidal heights range from tens of metres to several hundred.
Acquisition radius must be sized as `sqrt(desired_horizontal^2 + h^2)`.
