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

**What that means concretely.** A path carries a 2x2 Jones matrix in its own
transverse basis, the observation point carries the 3x3 far-field matrix `A(u)`
whose transpose is the transfer tensor, and the accumulator bins the 2x2
coherency `<T T^H>`. The first paper reports only the scalar `K_S`, which is half
the trace of the delay-integrated coherency, so the polarised state is stored and
then deliberately not published. Reporting the scalar is a presentation choice,
not a storage one, and it can be revisited without re-tracing anything.

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

### Antennas are post-processing on a stored path set, never a re-trace

**Decision.** Array geometry, per-element pattern, beamformer weights and sector
pattern are all applied after the trace, as a re-weighting of an already stored
path set. None of them is an input to the tracer.

**Why it works.** The trace depends on the scene and on `S` and on nothing else.
What it writes down for each escaping path is `(x_K, u_e, tau, J)`: last
interaction point, exit direction, delay and Jones matrix. Every transmitter
property enters through `Q_S(u_ext, f)`, the angular incident-power density at
`S` in the absence of the local scene, and the exposure integral is
`integral trace[T_S Q_S T_S^H] dOmega`. An array's geometry, element pattern,
weights and sectorisation shape `Q_S` and only `Q_S`. Changing any of them
changes the weights in a quadrature over a stored angular grid, which costs
milliseconds against hours for a trace.

**Why the exit point matters here.** Storing `u_e` alone would restrict this to
sources at infinity, and a 64-element panel at 50 m is not at infinity for a
scene 100 m across. Storing `x_K` as well makes the same path set exact at finite
range, so a near array is still a re-weighting rather than a new trace. Three
extra floats per path.

**What it buys.** One trace per location amortises over the entire 5G and 6G
antenna zoo, including configurations that do not exist yet. It also means the
deployment assumptions, which are the arguable part, stay separable from the
per-location physics, which is the expensive part. A reviewer who disputes the
sectorisation model re-runs a quadrature rather than the study.

**Reverses if.** The array turns out to be close enough to `S` that its near
field, not merely its finite range, reaches the scene, at which point the
plane-wave-per-direction decomposition fails and the source has to enter the
trace itself.

### Coherent across the array, incoherent across the multipath

**Decision.** Coherent superposition of multipath contributions at the body is
out of scope until pose covariance exists and is propagated. Coherent
beamforming across array elements stays in scope.

**Why these are not the same question.** Both are called coherent and both need
phase, but the phase comes from different places. Multipath phase comes from
path-length differences through the reconstructed scene, and a path length is
only as good as the registration of the panorama to the mesh. That registration
is now measured rather than guessed, and it is decimetre scale: the seed ensemble
gives a horizontal one sigma of 0.085 to 0.087 m at Korenmarkt and 0.215 to 0.232 m
at Milan, with `dz` no longer pinned at a bound. An earlier version of this entry
cited a 3 m by 2.5 degree valley, which was largely an artefact of the optimiser
truncating at 35 iterations in every run rather than a property of the objective.
The conclusion is unchanged and in fact strengthened, because the decisive
comparison is against a wavelength and not against a metre. At 28 GHz a wavelength
is 10.7 mm, so even 0.085 m is about 8 wavelengths and the resulting phase is
uniform on the circle. Milan is worse than its own covariance suggests: the
skyline objective and the independent sky-conflict metric disagree by 2.5 m
horizontally, ten times the seed spread. A coherent
sum over uniformly distributed phases is not a refinement of the incoherent sum,
it is noise with the same mean. Array phase is different in kind: element spacing
is a manufactured quantity known to microns, so the element-to-element phase is
exact regardless of what the scene reconstruction does.

**Consequence.** The environment enters as the band-averaged and
ensemble-averaged coherency matrix, which is the second moment and needs no
phase, while the array side may be treated coherently in `Q_S`. This is also why
the observable is defined as the second moment in the first place rather than as
an amplitude.

**Reverses if.** Pose covariance becomes an output and propagates, and the
residual path-length standard deviation falls below roughly an eighth of a
wavelength, which is 1.3 mm at 28 GHz. That is a demanding target for
photogrammetry-based reconstruction and it should be treated as unlikely rather
than pending.

### Occlusion inside a fishnet cell is small, but occlusion inside the field of view is not

**Decision.** In the propagation stage a fishnet face is treated as a fully
visible planar patch whose area is scaled by its `visible_fraction`. No sub-cell
visibility mask, no occlusion-aware form factor, no per-face shadow geometry.
`visible_fraction` itself is kept, because it falls out of the same rasterisation
that already computes pixel support and so costs nothing.

**The distinction this rests on.** Within-cell partial occlusion and whole-cell
rejection are different quantities and only the first bears on this decision. An
earlier version of this entry conflated them and quoted a single total of about
1.7 percent, which was wrong: the denominator used was the summed face pixel
support, which double counts and inflates the result by a constant factor per set.
The corrected figures below are area weighted and were cross-checked against the
`paint_reason` histogram in the shipped manifest.

**Measured, four Korenmarkt crops, Vistas and SAM 3 nets.** Within-cell occlusion
removes 0.73 and 0.47 percent of surface. That is the term this decision is about
and it is small, which is what makes the decision safe. Beyond it, surfaces absent
from the visible set account for 9.17 and 9.66 percent with nothing that puts them
back, and deferred surfaces (people, vehicles, street furniture) account for 20.49
and 27.25 percent, handed to the body layer and the object pipeline rather than
lost. Totals are 30.4 and 37.4 percent.

**Korenmarkt is not a quiet capture.** At yaw 0 the `paint_reason` histogram gives
157,498 transient pixels against 802,479 pixels of projected support area, which
is 19.6 percent. Any reading of this site as lightly occupied is wrong, and the
deferred term is the largest of the three by a wide margin. That is the load
bearing reason the dynamic body pipeline exists.

**Reverses if.** The within-cell term, not the total, exceeds roughly five percent
at any site. The fishnet reports all three terms per view and per site, with a
warning above five percent, so this is monitored rather than assumed.
`piece_visibility_fraction` stays at 0.5.

### The semantic layer resolves RF material, not only object class

**Decision.** Two segmentation backends run over the same rectilinear crops and
own different axes. Mask2Former on Mapillary Vistas owns the **entity** axis: it
is a complete dense partition into 65 street classes and, at native resolution,
it is the strong one on small infrastructure. SAM 3 prompted from
`config/semantic_concepts.json` owns the **material** axis. Neither overwrites
the other.

**Why the split is forced.** Mapillary Vistas has a single `Building` class. It
covers brick, lime render, ashlar stone, glass curtain wall and metal cladding in
the same image, and their permittivity, conductivity and roughness are not close.
Vistas cannot express material at all, so the material axis has to come from
somewhere else. Conversely SAM 3 returns overlapping instances with no coverage
guarantee and no calibration, so it cannot be the partition.

**How they combine: a cascade, not a vote.**

1. The dense pass runs first and partitions the view.
2. Its class histogram gates the prompt set. A facade-material prompt is not put
   to the open-vocabulary model on a view with no building pixels. The threshold
   is 256 pixels in a 1536 crop, small enough to keep a single distant drainpipe.
3. SAM 3 runs on the surviving prompts.
4. The material axis is dense everywhere. Where no concept fires it is the Vistas
   class prior `p(material | entity)`, which for `Building` is deliberately flat
   at a 0.30 maximum. Where a concept fires **and is admissible over the dense
   class beneath it**, the concept's sharper distribution replaces the prior.

**Admissibility is the load-bearing rule.** A concept that names an entity is
admissible over that entity's Vistas classes, which is what stops a `brick
facade` mask repainting the pedestrian standing in front of the wall. A
material-only prompt names no entity, so it is admissible where the dense class
prior carries some mass on its material. That second rule was added after
measurement, not by design: on the first Korenmarkt run `metal surface` claimed
20.1 percent of the sphere with 78 percent of it over Sidewalk and Pedestrian
Area, on a cobbled square. Neither class carries any metal in its prior, so
requiring agreement with the prior removed the claim without a threshold or a
hand-written exclusion list, and left the same prompt correctly sharpening poles
and railings. It fell to 2.9 percent.

The same run exposed a second defect. The material-detail ordering bonus in
`fuse_concepts.layer_rules` keyed on the *absence* of a structural entity, so the
vaguest prompts in the catalogue received the largest bonus and outranked every
specific one. Material-only prompts are now demoted below anything that commits
to an entity.

**Reverses if.** A dense segmenter appears whose vocabulary separates facade
materials. Then the cascade collapses to one backend and the concept catalogue
becomes a refinement layer rather than the only source of material.

### The ITU material library is indoor-biased, and four of its rows are out of reach

**Audit.** `config/itu_p2040_4.json` carries 15 rows of Recommendation ITU-R
P.2040-4 Table 3. Before this pass, 8 were reachable from some prompt: concrete,
brick, plasterboard, wood, glass, marble, asphalt_concrete, metal. Now 11 are,
adding vacuum_air, plywood and chipboard. Surface prompts went from 17 to 40.

**The four that stay unreachable are all interior finishes**: `ceiling_board`,
`floorboard`, `vinyl_tile`, `carpet_tile`. Suspended mineral-fibre ceiling tile,
indoor timber floor, vinyl and carpet are not outdoor street surfaces, and a
prompt invented to reach them would be fabricating a discrimination the imagery
cannot make. `floorboard` deserves a separate note: it is tabulated only over 50
to 100 GHz, so at this study's 28 and 39 GHz it would raise in
`PowerLawMaterial.evaluate` anyway, and outdoor timber decking is better served
by the `wood` row which is valid from 1 MHz.

**Six materials a prompt can name have no P.2040 row at all**: ceramic, polymer,
fabric, soil, water and vegetation_effective. Ground and water need
Recommendation ITU-R P.527-6 and vegetation needs P.833-10, neither implemented
in `materials.py`. Ceramic is the awkward one, because fired roof tile is a large
fraction of a European roofscape and the table simply does not have it. All six
are recorded in `material_grounding` with their status, so the exporter cannot
mistake an unbound label for a tabulated dielectric.

**What the imagery genuinely cannot discriminate.** These are priors in the
catalogue and are labelled as such, not detections.

- **Metallised glass.** A low-emissivity or solar-control coating is a few tens
  of nanometres of silver, close to invisible in a street photograph, and it
  turns a partly transmitting panel into a near mirror. Carried as a
  `metallised` Bernoulli prior: 0.6 on a curtain wall, 0.2 on an ordinary
  window, 0.9 on a photovoltaic module.
- **Substrate under render.** A plastered facade conceals what it is plastered
  onto, including external wall insulation, which is now common, looks identical
  and behaves nothing like the masonry it wraps. The `plaster facade` concept
  keeps 0.2 of its mass spread over brick, concrete and unknown for this reason.
- **Stone type.** Limestone, granite, sandstone and slate all read as stone at 10
  m and span roughly 5 to 9 in permittivity. `marble` is the only dimension-stone
  row in the table and carries all of them.
- **Wall thickness and layer count.** Never observable, and the P.2040 slab
  response needs both. Single, double and triple glazing are not separable at
  street level either.
- **Moisture.** Brick and asphalt conductivity move by close to an order of
  magnitude wet against dry. One capture samples one weather state.
- **Hollow against solid brick.** Identical facing, different effective
  permittivity.

**Cache keying, which is the operational half of this.** Every cached artifact
now records what produced it, and a mismatch recomputes rather than warns.

The dense view directory is stamped with the model name, the Hub commit hash of
the checkpoint, the inference resolution, the crop size and a content digest of
the source panorama. It had no key at all before. That is not hypothetical
tidying: the label maps under `data/panoramas/korenmarkt/semantics/views/`
changed from 1024 to 1536 underneath a concurrent session this morning and were
silently reused, and it is how every semantic output in this repository came to
run at the checkpoint's 384 without anyone noticing. A model name alone does not
pin a checkpoint, because a name can be re-uploaded, and a view directory named
after a site does not pin a capture, which is why both digests are in the key.

The concept cache key is a digest of the checkpoint, the inference resolution,
the detection threshold, the crop size and the prompt vocabulary. It deliberately
excludes the entity, material and attribute distributions: those never reach the
model, they are read fresh from the catalogue at fusion time, and hashing them
would discard a city of segmentation every time a prior was retuned. What a key
cannot capture is which prompts a view was actually asked, because the gate
decides that from the dense labels rather than from the catalogue, so a stored
view is additionally accepted only when its recorded `asked_prompts` match the
gate this run computed. Changing `gate_min_pixels` or the entity-support table
therefore re-segments.

The catalogue answers this by splitting roughness from dielectric where the
imagery *can* see the difference. `ashlar stone facade` and `rubble stone masonry
wall` share a dielectric prior and differ by 0.35 against 0.97 on `rough`, which
at 28 GHz is what actually sets the specular fraction.

### Concept-catalogue size is a time budget, measured at 17.8 ms per prompt per view

**Finding.** SAM 3 as previously shipped ran `Sam3Processor.set_text_prompt` once
per prompt, which re-encodes the text and runs the fusion encoder, the DETR
decoder and the mask head every time. Measured on the A6000 with the 54-prompt
catalogue on a 1024 crop: 61.8 ms per prompt, 3.34 s per view, **89 s per
panorama** against the dense pass's 13 s of inference. That is the order of
magnitude the brief said not to accept.

**Two changes, both exact.** The text encoder is run once over the whole
catalogue at construction and gated subsets are taken by `index_select`, which
removes 11 ms per prompt per view. Grounding is then batched across prompts by
pointing every entry of `FindStage.img_ids` at the same image, which the model
supports but the shipped processor never uses. Batched cost is **17.8 ms per
prompt**, a 3.5x reduction, and it is asymptotically flat from 16 prompts up.
Verified against the serial path: identical instance counts and a worst
per-concept union-mask IoU of 0.9965 across batch sizes, the residual being bf16
nondeterminism. `prompt_batch` defaults to 32 because 32 and 57 run at the same
speed while 32 peaks at 14.0 GiB against 21.4.

**The decoder is 82 percent of what remains** and scales linearly in prompt
count, so there is no further structural win inside the model. Cost per panorama
is therefore `views x prompts x 17.8 ms` and adding a prompt to the catalogue
costs about 0.46 s per panorama. The gate is the only lever left, and at a dense
urban square it is a weak one: Korenmarkt asked 1363 of 1482 possible prompt
views, saving 8 percent, with a per-view range of 26 to 56. It will earn more on
open sites, and it is what makes rare prompts nearly free.

**A third change, outside SAM 3.** The four concept layers were each stitched to
the sphere by their own traversal, and only the dense path had the
equirectangular footprint cull. `fuse_layers` now culls once and paints all
layers inside the shared projection, because the projection depends on the view
and not on what is painted in it. Bit-identical to fusing them separately, and
worth 22 s per panorama at 8192 x 4096.

**Result**, 26 views, 1536 crops, 8192 x 4096 output, wall clock end to end
including panorama decode, crop extraction, spherical fusion and writing.

| site | dense | hybrid | ratio | concept inference | gate saved |
| --- | --- | --- | --- | --- | --- |
| Korenmarkt | 68.0 s | 156.4 s | 2.30 | 35.8 s, 1378 ms/view | 8.0% |
| Milan Duomo | 63.6 s | 132.5 s | 2.08 | 31.1 s, 1197 ms/view | 12.7% |

Both columns are full runs with `--force`, so the hybrid is not being credited
with a cached dense pass. Re-running the hybrid over cached crops and cached
dense labels takes 121 s at Korenmarkt, which is the number a re-fusion costs
rather than the number a new panorama costs.

On segmentation alone Korenmarkt is 13 s dense against 50 s hybrid, a factor of
3.8. The unbatched path would have been 8.4x, and it is the batching plus the
shared fusion traversal that bought the difference. Milan is cheaper on both
counts because a piazza gives the gate more empty sky to work with.

### SAM 3 has a fixed 1008 resize, and unlike Mask2Former's 384 it is not a bug

**Finding.** `Sam3Processor.__init__` takes `resolution=1008` and applies
`v2.Resize((1008, 1008))` to every input, so a 1536 crop is downsampled before
the backbone sees it, exactly as the Mapillary Vistas processor downsampled to
384. The two are not the same kind of defect. 384 was a config accident far below
what the checkpoint was trained on. 1008 is SAM 3's trained input size: the
ViTDet patch grid is 72 x 72 at 14 pixels, and the position embeddings and rope
tables are fitted there.

**Not raised.** Interpolation machinery exists (`get_abs_pos`, rope interpolation)
so it can be raised mechanically, but doing so takes the ViT off its trained
scale, and 54 prompts at 1260 already exhausted 46 GB of device memory against
24.6 GiB at 1008. The lever for angular detail is narrower crops, not larger
ones. The value is recorded in the manifest as
`concept_backend.resolution` with its status, so a future run can move it
deliberately.

**Worth stating plainly.** At 1536 crops over 90 degrees the pipeline already
samples 17 pixels per degree against the Street View panorama's native 45.5 at
Korenmarkt, and SAM 3's resize takes its own view of that to 11.2. Native
angular resolution would need roughly 4096-pixel crops. Neither backend is
running at the panorama's native angular sampling, and only the crop count and
field of view can change that.

### Out-of-view surfaces have coarse evidence, not zero evidence

**Decision.** Surfaces that no panorama sees are given a material posterior from
the Google 3D Tiles texture rather than from a prior alone. Roughness for those
surfaces still comes from a prior, because no imagery in this pipeline resolves
it.

**Measured on the 61 cached Korenmarkt tiles.** 130,665 square metres of surface
carry 6.75 million texels. The area-weighted median is 26 texels per square metre,
a ground sample distance of 19.6 cm. Splitting by face orientation gives 25 texels
per square metre on near-vertical faces and 26 on near-horizontal ones, so the
tiler equalises texel density across orientations and facades are not starved
relative to roofs. Textures are 256 by 256 or 256 by 512 JPEG, one image per tile.

**Against the panorama.** At 16384 pixels across 360 degrees the Street View
panorama resolves 7.7 mm at 20 m and 38 mm at 100 m, so it beats the tile texture
by 26 times linear at 20 m and everywhere inside the 130 m crop. The crossover is
near 520 m, well outside the scene. The panorama therefore remains the primary
evidence wherever it exists, and the texture is strictly the fallback.

**Why the distinction matters more than the numbers.** In the adjoint frame with
four bounces, every interaction after the first can land on a surface no panorama
sees, so out-of-view material is the majority of interactions rather than a corner
case. At 19.6 cm the texture separates brick from glass from metal from vegetation
from asphalt without difficulty, which settles the permittivity class. It cannot
resolve a mortar joint, a low-emissivity coating, or smooth against board-marked
concrete, which is exactly what sets roughness, and roughness moves the specular
fraction at 28 GHz by a factor of 237 against a 12 to 20 percent spread on
permittivity. So the texture closes the cheaper half of the out-of-view problem
and leaves the expensive half open.

**Consequence for priors.** Any knowledge-based prior, from building typology,
OpenStreetMap tags or a language model, should be aimed at roughness and
construction type rather than at material identity. Material identity is
observable at 19.6 cm and does not need inference.

**Reverses if.** A site returns tiles with materially lower texel density, or with
untextured geometry. This is measured per site alongside the leaf tile count.

### What the material layer actually resolved at the two sites

**Measured, both panoramas regenerated at 1536 native crops with the hybrid
backend.** The material axis is dense over the whole sphere. The fraction of it
carrying concept evidence rather than the bare Vistas prior is 32.8 percent at
Korenmarkt and 54.7 percent at Milan, against sky shares of 30.9 and 38.8
percent, so on visible surface the concept backend resolves roughly half at
Korenmarkt and nine tenths at Milan.

Twenty distinct concepts survive to the sphere at Korenmarkt, eleven at Milan.
The catalogue picks up what each site actually is: cobblestone and brick paving,
brick facade, plaster facade and slate roof at Korenmarkt, paving slab, ashlar
stone facade and an open archway at Milan. Ten ITU rows are realised at
Korenmarkt and nine at Milan, against eleven reachable in the catalogue. Plywood
is the reachable row neither site produced, because both hoardings found were
oriented strand board.

**The before and after, over building pixels only.** The dense pass alone put
every `Building` pixel on `unknown_building` and every `Wall` pixel on
`unknown_wall`, which is two names, neither of them an RF material. The hybrid
pass puts them on 9 materials at Korenmarkt and 6 at Milan, every one bound to a
dielectric model. The split is 48 percent brick, 22 glass, 17 render and 5 stone
at Korenmarkt against 44 percent stone, 20 render, 18 brick and 10 glass at
Milan, which is Ghent and the Duomo coming out the right way round.

**The admissibility guard holds on real data.** Across both sites, zero percent
of `Person` pixels and zero percent of `Sky` pixels carry a concept claim. Cars
are 98.5 percent vehicle composite with the 1.5 percent remainder metal, which is
a `metal surface` claim admitted over a class whose prior does carry metal. No
facade concept reached a pedestrian at either site.

**One result worth not glossing.** Milan's largest single material is `concrete`
at 38.9 percent, all of it from `paving slab` covering the piazza. Piazza del
Duomo is paved in stone, not concrete. The concept is right and the prior is
wrong for this site: a paving slab is concrete 0.60, marble 0.25, unknown 0.15
because most European paving slabs are concrete, and the argmax follows the
prior rather than the place. The winning probability is 0.60, so the layer is
reporting its own uncertainty correctly, but anything that reads the argmax as a
material name will get Milan's pavement wrong. This is the general failure mode
of a shared catalogue applied across ten cities, and the fix is site or region
conditioning on the priors, not a better prompt.

### Surface scattering is parameterised by a band-limited PSD, not by a sigma and a correlation length

**Decision.** The scattering model carries a band-limited power spectral density
per semantic class, with an explicit statement of the spatial band it covers.
It does not carry a single RMS height paired with a single correlation length.

**Why the usual parameterisation fails here.** Three independent literature
strands, searched separately, agree that lateral surface statistics for facade
materials are essentially unmeasured. No autocorrelation length, no PSD, no
fractal dimension, no Hurst exponent is published for a brick wall, a rendered
facade, a stone cladding panel or a curtain wall. Where a correlation length does
appear in a radio paper it was assumed or fitted, and the giveaway case is a
published fit of 4.1 mm RMS height to a surface the same authors call smooth,
which is not a surface statistic but a fit parameter absorbing model error.

**Two measured results make a single length the wrong model rather than merely an
unmeasured one.** Freshly cleaved basalt and granite show no roll-off anywhere
between 60 um and 20 mm, so natural stone is self-affine with a Hurst exponent
near 0.8 to 1.0 and has no correlation length in our band at all. Asphalt and
concrete pavement do have a roll-off, and it sits at 4 mm to 1 cm, landing
directly on the 10.7 mm wavelength. Concrete separately appears to carry a
micro-texture near 0.3 mm superposed on an aggregate scale near 5 mm, and which
one a given study reports is decided by its instrument bandwidth rather than by
the concrete.

**Bandwidth is the dominant confound and it is measurable.** ISO 4288 stylus
cut-offs of 0.25 to 0.8 mm discard everything above 0.8 mm in lateral wavelength,
which is precisely the 1 mm to few cm band that matters at 28 GHz. Within one
material family, sawn granite reads Ra 3 to 7 um under a 0.8 mm cut-off while
sawn sedimentary stone reads Sa 180 to 270 um measured areally with no filter, a
factor near 50. Directly measured: a 2025 concrete study shows the RMS gradient
Sdq and the developed area Sdr collapse by 80 to 90 percent when the sampling
interval is coarsened from 0.1 mm to 1.0 mm. So any table mixing filtered and
unfiltered values is incoherent, and every published amplitude parameter is a
band-limited quantity whether or not its paper says so.

**Consequence.** Every roughness entry ships with the spatial band it was measured
over. Values from different bands are never averaged. Where only a filtered
amplitude parameter exists it is recorded as a lower bound, not an estimate.

**Reverses if.** Someone publishes areal metrology of real facade surfaces over
the 1 mm to few cm band with a stated evaluation area, which would make a fitted
two-scale or self-affine form directly measurable rather than inferred.

### Facade roughness is masonry, not surface finish

**Decision.** A metre-scale facade patch gets its diffuse fraction from
macroscopic structure, unit-to-unit offsets, joints, relief and dressing, not
from the microscopic surface finish of the material it is made of.

**The evidence is three independent strands that only agree under this reading.**
Direct metrology of fired-clay block faces gives Rq of roughly 1 to 5 um, which
at 28 GHz is 20 to 80 times below the threshold that matters and is therefore
specular. Landron measured real exterior building walls and reports sigma_h of
0.5 cm for brick and 2.5 cm for limestone, three orders of magnitude larger. The
reconciliation is that the second measurement includes the masonry and the first
does not. BS EN 771-1 closes it quantitatively: dimensional tolerance class T1 is
plus or minus 6, 4 and 3 mm and range class R1 is 9, 6 and 5 mm within one
sample, so brick-to-brick face-plane offsets of a few millimetres exist in
nominally flush work. A 1996 radio field measurement and a European masonry
standard arrive at the same few-millimetre figure by unrelated routes.

**Provenance, checked directly rather than relayed.** Piesiewicz section II
measures surface roughness with commercial optical 3D micro and nanometrology, 5x
objective, 25 um lateral and 5 um vertical resolution, histograms of measured
height offset to zero mean, Gaussian approximated. Yoshino 2026 measures both
roughness and correlation length with a KEYENCE VHX-8000 digital microscope. Both
are metrology, independent of the radio data, which is what the NYU and Wang
chain lacked. Yoshino's samples are plates of 300 by 300 mm up to 400 by 1200 mm,
so those values are a lower bound for a weathered facade rather than a central
estimate.

**The periodic term is a grating, not roughness.** Standard UK brickwork gives a
75 mm vertical course pitch and a 225 mm horizontal stretcher pitch, which at
28 GHz are 7.0 and 21.0 wavelengths and support 14 and 43 propagating diffraction
orders across nearly the full hemisphere. Deterministic periodic structure is not
described by the Rayleigh criterion, and a smooth Lambertian or directive
pedestal may have the right total diffuse power with the wrong angular shape.
Untested, and worth testing, since measured bistatic data is conventionally fitted
with a smooth lobe that would hide it.

**Specular fraction of reflected power at 28 GHz**, computed through `mmwave.py`
from the values above: float glass and polished stone 1.000 even after six months
outdoors, honed stone 0.891, saw-cut stone 0.853, bush-hammered stone 0.679,
brick masonry 0.000 at normal incidence and 0.100 at 75 degrees, render 0.000 at
normal incidence on an inferred sand top size. That span, from 1.000 to 0.000
across surfaces found on one street, is the quantitative case for the semantic
layer. Weathering moves stone by 10 to 25 percent, so soiling is second order.

**Known gaps, stated as gaps.** Render, stucco and plaster returned zero direct
measurements, not weak ones. The brick metrology is extruded structural block,
not an architectural facing brick, and must not be transferred to one. Belgian
and Dutch brick formats and their course pitch are unverified.

**Reverses if.** Direct areal metrology of a weathered European facing brick or a
rendered facade lands materially away from the masonry-derived figure.

### The pipeline as a whole is not novel, and the paper must be framed on what survives

**Decision.** No claim of priority over image-driven RF material assignment.
Full detail and citations in `PRIOR_ART.md`; this entry records the calls that
follow from it.

**What is occupied.** "Image pixels to semantic class to electromagnetic material
on a ray-tracing surface" has been published independently at least six times,
twice with ITU-R P.2040 named as the target table. The sharpest version of our
claim, one facade resolved into several materials, is occupied by Cazzella et al.
at 28 GHz in Sionna with a Huawei co-author, done manually. mmSV took the framing
to MobiCom in 2023. Xia et al. segment photogrammetric point clouds into ground,
buildings, vegetation, fences, street furniture and cars for outdoor ray tracing.
An acoustics paper from 2021 has the same skeleton with absorption coefficients
in place of permittivity. Most of the closest work is dated January to June 2026,
so priority dates matter.

**What survives, in descending order of safety.** Recovering clutter from
street-level imagery into an RF simulation, which nobody joins. Running on
third-party photogrammetric tiles at ten-city scale with no per-scene
reconstruction and no channel measurements, where every comparable work needs
measurements or its own capture. Carrying a posterior over material class,
conditioned on a semantic observation, into the tracer, which must be worded at
that resolution because Remcom ships a Monte Carlo material type and OpenGERT
perturbs a fixed assignment, so uncertainty on parameters is taken. The attribute
vector, transient in particular. Population exposure as the application, which is
clean. Roughness priors per semantic class feeding a specular and diffuse split,
claimed at that resolution and no broader, since discrete roughness buckets are
taken.

**Two attacks to pre-empt in section 1.** OpenGERT reports that minor
perturbations in permittivity and conductivity do not significantly alter channel
statistics while metre-scale geometry perturbations do, which reads as fatal until
you check the setup: 3.5 GHz, and the perturbation is ten percent around an
already correct value. That says nothing about glass against metal against
vegetation, and nothing about the specular and diffuse partition at 28 GHz, where
material error is a category error rather than a ten percent wobble. Their own
sentence about largely unknown or mischaracterised parameters is quotable in our
favour. Second, Texture2LoD3 ortho-rectifies street-level panoramas against a
building prior and segments facades semantically with no RF, and combined with
Cazzella the method is largely assembled, so obviousness has to be answered
directly rather than ignored.

**The framing sentence, sourced to a vendor.** Ansys already ingests exactly our
geometry class, a 5 cm photogrammetric model of downtown Denver and Cesium 3D
Tiles streaming, and treats the imagery as decoration: a structural model with a
visual overlay introduced as a texture, while the solver consumes triangles with
separately assigned material properties. The incumbent has the photograph
registered to the geometry and uses it as wallpaper. Transcript is in this repo
at `spinoff/webinar_ansys/transcript.md`.

**Reverses if.** mmSV turns out on reading to be a near-identical statement of the
headline, which would force a further narrowing. Its full text is behind a
paywall that UGent access resolves, and the related-work section should not be
written before it is read.

### The atlas class axis is not what the expanded catalogue grows

**Question raised.** `decal_atlas.rasterize_triangle_evidence` allocates
`(observed_triangles, height, width, class_count)` float32, which is linear in
`class_count`, and the concept catalogue just grew. Does that move the memory
wall?

**No, and the reason is that the axes are painted one at a time.** The atlas
rasterises one semantic layer per call, and the largest layer is still the
Mapillary Vistas entity axis at 65 classes, which this work does not touch. The
concept axis is 58 values including unlabelled, and the RF material axis is 20.
At the 8 x 8 decal the quoted 17.2 KB per triangle implies, and a 52,386
triangle per-city batch:

| axis | classes | peak weights allocation |
| --- | --- | --- |
| Vistas entity, unchanged | 65 | 831 MB |
| concept, 54 prompts before | 55 | 703 MB |
| concept, 57 prompts now | 58 | 742 MB |
| RF material, new | 20 | 256 MB |

So the catalogue expansion added 39 MB to an axis that is not the binding one.
Painting three layers sequentially peaks at 831 MB, exactly where it was.
Painting them simultaneously would be 1.8 GB, which is the thing not to do.

**The headroom is explicit.** The concept axis costs 12.8 MB per prompt per
per-city batch and 38.5 MB per prompt over the whole 157,744 triangle support
mesh. It becomes the largest axis at 65 prompts, which is 8 more than the
catalogue has. Past that the ceiling rises linearly: 80 prompts is 1.04 GB and
120 prompts is 1.55 GB per city batch. Prompt count is therefore bounded twice
over, by segmentation time at 0.46 s per prompt per panorama and by this
allocation, and both bounds say the same thing about catalogue discipline.

**What would move the wall properly** is the representation, not the taxonomy: a
dense `(triangles, texels, classes)` block is the wrong shape for evidence that
is sparse in class at every texel. That is a separate change and is not made
here.

### The material axis is 3 percent less reproducible than the entity axis

**Measured, two independent full runs of the same panorama with the same code
and the same settings.** The dense entity partition agrees with itself on 99.95
percent of the sphere at Korenmarkt and 99.98 percent at Milan. The concept
layer agrees on 96.2 and 97.6 percent, and the RF material layer on 96.6 and
97.7 percent.

**Where the disagreement lives.** Almost all of it is paving. At Korenmarkt the
dominant swap is brick against marble, which is `brick paving` against
`cobblestone paving` over the same square: the two concepts trade about 2.5
percent of the sphere between runs, and the shipped run reads 11.9 percent
cobble and 5.2 percent brick paving where the previous one read 9.5 and 7.7. At
Milan it is `paving slab` against `cobblestone paving` and `asphalt road`. No
facade material and no clutter class is materially affected.

**Why.** SAM 3 runs in bfloat16, and the detection score of a broad textural
prompt on a large uniform region sits close to the 0.35 threshold, so which of
two visually similar paving prompts wins a given patch is not stable across
runs. The batched grounding is not the cause: it reproduces the serial path to a
worst per-concept union-mask IoU of 0.9965, an order of magnitude tighter than
this.

**Consequence, stated rather than fixed.** Any per-site material share quoted
from a single run carries about three percent of run-to-run noise, concentrated
on the ground plane. Ten cities of ground-material statistics should either
average several runs or raise the threshold on the paving prompts specifically.
Facade materials, which are what the concept backend exists for, are stable.

### The tile placement is read in double precision, not through Blender

A Photorealistic 3D Tiles leaf does not carry local coordinates. It carries its
full ECEF placement in the glTF node matrix, so a translation component reads
around 4423590.456613353 m. `Object.matrix_world` is float32, whose spacing at
that magnitude is 0.5 m, so Blender quantises every tile independently at
import. The earlier diagnosis blamed the ECEF-to-ENU assignment inside
`build_inhouse_mesh.py`, which is one step too late: `collect_world_triangles`
already promoted to float64, and folding the transform into the numpy world
matrix there would have recovered nothing, because the damage was already in
the object.

`semantic_twin/gltf.py` reads node matrices out of the GLB in float64 and the
builder matches them per object. `matrix_world` is now mutated only for the
optional `--blend` export, after the geometry has been written.

The quantity that matters is not the rigid shift, which a registration fit
absorbs, but the differential seaming between neighbouring tiles, which nothing
downstream can undo:

| site | rigid shift | mean per-vertex | worst tile-to-tile seam |
|---|---|---|---|
| Korenmarkt | 0.262 m | 0.299 m | 0.661 m |
| Milan | 0.175 m | 0.273 m | 0.996 m |

Milan's worst seam is 93 wavelengths at 28 GHz. Against an independent pure
numpy assembler that reads the GLB accessors without Blender, the rebuilt
meshes agree to 2.3 um median at Korenmarkt and 5.5 um at Milan, which is the
float32 PLY storage quantum, so the residual seaming is three orders below the
1 cm target. The old meshes sat at 0.256 m and 0.234 m median against the same
reference.

A side effect worth remembering when reading old numbers: camera-visible
inverted-normal area at Korenmarkt fell from 5.81% to 1.00%. The likely
mechanism is that seams no longer gap, so the camera stops seeing back faces
through tile cracks. It is not isolated from the region-of-interest change,
which pulled a different tile set.

The region of interest was a ball centred on the ellipsoid, so horizontal reach
fell off as `sqrt(r^2 - h^2)` with site altitude. It is now a vertical cylinder
about the site up axis, so `--radius-m` means horizontal reach at every height
and no site-height parameter is needed. Milan at r=320 costs 691 requests, so
the old 500 request cap would have silently truncated it.

Corrected meshes are committed as `*_f64.ply` alongside the originals. Every
registration, fishnet and texture-evidence number recorded before this entry
was computed against the superseded geometry. The skyline residual moves from
1.297 to 1.327 deg, which is inside the seed spread of +/- 0.26 deg, so
registration does not need redoing on accuracy grounds, but the provenance
should be stated.

### Voxel remeshing is rejected for the production path

The support mesh has a real topological defect: 16.6% boundary edges, 34.7 km
of boundary, 2.29% non-manifold edges, essentially no watertight area. Voxel
remeshing fixes all of it completely. Measured at Korenmarkt with a 0.30 m
solidify and a 1 degree planar dissolve:

| voxel | triangles | boundary edges | watertight area | median first-hit normal tilt | median range shift | fishnet face floor |
|---|---|---|---|---|---|---|
| none | 157,862 | 42,158 | 0.6% | - | - | 6,271 |
| 2.00 m | 79,832 | 0 | 100% | 57.7 deg | 2.94 m | 8,933 |
| 1.00 m | 384,048 | 0 | 100% | 17.5 deg | 0.387 m | 48,758 |
| 0.50 m | 1,976,934 | 0 | 100% | 12.9 deg | 0.264 m | 99,886 |
| 0.35 m | 4,481,690 | 0 | 100% | 6.9 deg | 0.208 m | 125,714 |

It is rejected for three reasons.

It defeats the cutter. The fishnet can never emit fewer faces than the visible
support triangles, and that floor goes from 6,271 to 125,714, a twentyfold
regression in exactly the quantity `FISHNET.md` exists to reduce. At 0.35 m the
emitted count collapses onto the floor, 125,835 against 125,714, so the cutter
stops doing anything at all.

It costs specular fidelity to buy closure. Median first-hit normal tilt is still
6.9 deg at the finest size that fits in memory, with p90 at 43 deg and 55.6% of
visible pixels beyond 5 deg. The curve falls slowly, so sub-degree needs voxels
well under 0.1 m, which is order 1e8 triangles. The median range shift of 0.21 m
is comparable to the 0.26 m float32 defect just removed.

The problem it solves is smaller than the edge table implies. Measured from the
camera rather than from topology, only 0.091% of first-hit rays land on a back
face and 1.00% of visible area is inverted. That is two orders below what 16.6%
boundary edges suggests, because tiles overlap rather than gap.

Two related findings. A 5 degree planar dissolve destroys closure, watertight
area 100% to 0.74%, from two non-manifold edges breaking the largest component,
so 1 degree or nothing. And the skyline residual does improve under remeshing,
1.327 to 0.614 deg at 1.00 m voxels, but the mechanism is the solidify dilating
the silhouette upward, which happens to cancel the known low-mesh-skyline bias.
That argues for the explicit bias term already planned, not for a dilation.

The cheap alternative of welding and orienting per component is worse than doing
nothing: camera-visible inverted area went from 1.00% to 4.33%, because
component-level sign voting is too coarse. The targeted fix is to orient per
face from the camera's own first-hit votes and make the BSDF two-sided, which
addresses the 1.00% at no geometric cost.

One flag remains untested. The solidify ran at `offset = 0`, which straddles the
surface and moves the visible face outward by 0.15 m, and that accounts for most
of the range error that plateaus near 0.2 m independent of voxel size.
`offset = -1` grows the shell inward and should leave the visible face where it
was. If this question is ever reopened, that is the first rerun.

### The support mesh does not have a small-triangle problem

The premise behind the original remesh suggestion was that decimation would clean
up slivers. Measured on both meshes: zero degenerate faces, smallest triangle
180 cm2, zero duplicate index triples, and the largest triangles carry the best
minimum angles, 31.8 and 36.5 deg median against 26.6 and 22.6 deg mesh-wide,
with zero slivers. Bad normals on large triangles hold for Milan only, 19.5%
inverted in the top 0.1% by area against a 6.5% baseline, and not for Korenmarkt.
The defect is topological and orientational, not metric.

### Diffraction is demoted, the crop radius is promoted

`MONOSTATIC_SBR.md` called diffraction the largest known physical omission in
three places and said it lands on exactly the elevation band the rooftop weight
needs. Both halves were wrong and the ranking is now reversed.

Diffraction at 28 GHz is measured at under 1% of received power against 20% for
diffuse, in the same NIST campaign this repository already cites for the diffuse
share. The theoretical edge coefficient is about -42 dB at 28 GHz, triangulated
three ways: Chizhik's Manhattan and Valparaiso measurements, the -46 dB 60 GHz
companion, and an ITU-R P.526-15 knife-edge computation for Ghent geometry
returning 43 to 48 dB. Scaling as 10 log10 f puts FR3 at 16.95 GHz only 4.5 dB
more diffractive than 28 GHz, so FR3 is not a different regime.

The power-integral error is unmeasurable. With blocked directions at -45 dB, the
omission costs 0.000 dB of `K_iso` at open-azimuth fraction 0.30, 0.135 dB at
0.001, and reaching 1 dB needs an open fraction below 0.012% of azimuth.
Korenmarkt's measured sky fraction is 0.2271. The UTD transition region adds
about 0.06 dB of bias.

The geometry claim reverses outright. Rooftop-diffracted power reaches a head at
1.7 m from the edge directly overhead, so it arrives at 35 to 86 degrees of
elevation, and `1/sin^3(el)` at 60 degrees is 0.001 times its value at 5 degrees.
Adding UTD would deposit power where the study's own weight suppresses it by
three orders of magnitude. The old text conflated the link with the local tensor:
over-rooftop multiscreen transport is upstream of `K_S` and factored out by
construction, and what `K_S` must capture is only the last edge.

Two exceptions survive and are recorded rather than dismissed. A transmitter
sited behind a parapet is a hard failure, since Chizhik measures over 15 dB of
extra loss for a 5 m setback under 100 m and a diffraction-free tracer predicts a
zero where measurement shows signal. And Koivumaki finds weak diffracted paths at
28 GHz outdoor that diffuse scattering cannot reproduce, so the Rayleigh split is
not a substitute for the diffracted field.

The decision: no diffraction term, and publish `f_open`, the low-elevation
open-azimuth fraction, per location as the validity flag. Nothing computes
`f_open` yet.

What takes first place is the crop radius, and writing it up showed that three
different crop questions had been running together.

1. **Scattered power.** Bounded small. ITU-R P.1411-13 Table 11 gives a measured
   28 GHz NLOS delay spread of 74.5 ns median, 22 m of excess path, and 3GPP
   38.901 UMi-SC gives 65.9 ns, so a scatterer at 130 m sits at -19 to -41 dB,
   under 0.05 dB of error. Atmospheric absorption cannot be used to justify the
   truncation either: P.676-13 gives 0.026 dB over 260 m at 28 GHz.
2. **Occlusion.** Not converged. Under the adjoint `R^0` law a distant blocker
   changes `K_S(u)` at full per-direction strength, directions beyond 90 m carry
   -28.4 dB of the isotropic weight, and that figure is still growing with radius
   against a 30 dB budget.
3. **Source support.** Broken. The rooftop weight is supported on `Delta_h` in
   [13.5, 43.5] m and `d` in [25, 250] m, the scene is cropped at 130 m, and the
   fraction of the `cos/sin^3` measure needing a source outside the crop is 27.5%
   at `Delta_h = 8` m, 79.4% at 15 m, 88.5% at 20 m and 94.9% at 30 m.

The delay-spread bound retires the first and not the other two. The repair for
the third is a reporting change: either narrow the stated support of `w_roof` to
what the crop contains, or keep the support and publish the fraction of its
measure that no geometry backs.

### Roughness: face against wall, and the Rayleigh split is scoped to half the classes

Three roughness contradictions across the documents resolved the same way, by
noticing that a single symbol was carrying three different physical quantities.

**Brick is 1 cm and 0.03 mm and both are right.** A profilometer measures a
prepared monolithic patch, and every direct measurement of a brick face returns
0.024 to 0.095 mm. A metre-scale facade patch, which is what a fishnet face
stands for, additionally carries mortar joints, course relief, block relief,
pointing, sills and reveals at centimetre pitch, and Landron measures 0.5 cm RMS
on a real brick wall. `config/surface_roughness.json` keeps `rms_height_mm` as
the face statistic in both `brick_face` and `brick_wall_with_mortar_joints` and
puts the wall structure in a separate `periodic_component` block, and its
`two_scales.do_not_average` note forbids reconciling them into one number. The
rule adopted: no brick, stone or paving roughness number appears anywhere without
the word face or the word wall next to it.

**Vitucci's 1 cm is neither measured nor fitted.** Checked against arXiv:2209.12685
verbatim: it is "typical literature values for a brick wall", assumed and plugged
into Kirchhoff purely to generate a comparison lobe, at 1.3 GHz, referring to a
building facade with the joints inside the illuminated patch. So it is a
wall-scale model parameter and it should never be quoted as metrology.

**The Rayleigh split is the right model for eight of sixteen classes, not
sixteen.** `PRIOR_ART.md` was selling it as the surviving physics differentiator
while `ROUGHNESS.md` and `materials.py` refuse to evaluate it for the periodic and
two-scale classes. Both stand once the scope is stated. Gaussian-random and
inside the split: glass, smooth metal cladding, painted render, as-cast concrete,
board-marked concrete, brick face, and both asphalt classes. Outside it: brick
wall with joints, dressed ashlar, rusticated stone, wood cladding, profiled metal
sheet, ceramic tile facade, concrete paving slab, sett paving. A 75 mm mortar
pitch supports 15 propagating orders at 28 GHz and 31 at 60 GHz. Claim the split
for the random classes and name the periodic ones as an open item with a stated
refusal in the code. Claim the roughness *prior* separately, because a per-class
lognormal with evidence grades is closure-agnostic and does not inherit the
limit.

Two stale numbers fell out of the same pass. `MONOSTATIC_SBR.md` section 5.4's
`sigma_h` table was an invented engineering prior, one to two orders of magnitude
too rough, and is now marked superseded rather than deleted, because its shape is
still the right illustration of the frequency-and-incidence interaction. And its
headline sensitivity, a factor-30 60 GHz swing between painted plaster and bare
concrete, dissolved: the config puts both at 0.15 mm. The surviving
random-roughness sensitivity is inside concrete, as-cast 0.15 mm against
board-marked 0.6 mm, worth a factor of 1.6 at 28 GHz and 8.4 at 60 GHz at normal
incidence and only 1.2 at 70 degrees.

### The two conflicting facade RMS height sets are the same three walls

Two measured-looking sets were in play with near-identical material names and
values differing 5 to 11 times. Guo, Zhang, Sun, Tao and Gao (arXiv:2502.00699,
IEEE WCNC Wkshps 2025, `10.1109/WCNC61545.2025.10978814`) give metal sheet
0.170 mm, marble wall 0.216, smooth wall 0.445, rough wall 0.715. Zhang, Sun,
Tao, Zhu and Gao (npj Wireless Technology 2(1) article 1, 2026,
`10.1038/s44459-025-00016-9`) give marble 1.0 to 1.1 mm, smooth wall 4.1, brick
wall 6.5 to 8.

They are the same three walls. Four of five authors overlap, Guo is thanked in
the acknowledgements of the second for the same campaign, the site is the same
Minhang campus, the second cites the first, and the dielectric constants identify
the surfaces one to one: marble 6.2 against 6.1 and 6.2, smooth wall 5.8 against
6.0 and 5.7, and the first paper's "rough wall" at 10.5 is the second's "brick
wall" at 10.1 and 11.5.

So there is no contradiction. There is one clean demonstration on identical
physical surfaces that a Gaussian height inverted from radio data is 5 to 11
times the geometric height the same group assumes going forward. Three facts make
the npj set unusable as a physical prior. Its own table is captioned "Fitting
parameters" and scored by SMAPE. The fits are at 8 GHz, where the wavelength is
37.5 mm, and its 28 GHz figure is a simulation driven by the 8 GHz fit rather
than an independent measurement. And taken as geometry it is self-refuting: brick
at 6.5 mm and 30 degrees gives `g^2 = 43.6` at 28 GHz, a coherent fraction of
1e-19, while the same group reports 28 GHz power concentrated in the specular
direction.

The correction that goes the other way: Guo's set is not metrology either. The
paper never states how `h_rms` was obtained, contains no profilometer, laser or
scan, uses the value as an *input* seeding the initial scattering coefficient
before `S`, `alpha_R`, `alpha_i` and `Lambda` are tuned to minimise FVU, and
assigns a relative permittivity of 6.0 to a metal sheet. It is a table of nominal
simulator inputs. `PRIOR_ART.md` had described it as "measured real facades" and
that has been corrected. Neither set belongs in a physical prior library, which
is what `SurfaceRoughnessPrior.__post_init__` already enforces for the second.

### Facade diffuse power is structural, and the conclusion was reached twice

Two literature passes that did not read each other reached the same conclusion
from sources that do not overlap, and that independent corroboration is the
strongest result the pair of documents contains.

From the scattering-model side: reproducing a brick wall's measured lobe width
from a Gaussian surface at 1 cm and 0.5 m correlation length needs a directivity
exponent of 65, while the measured wall fits 4, and the authors attribute the
excess to indentations, brick and mortar alternation and sub-surface
inhomogeneity rather than to surface roughness.

From the metrology side, four separate results. Kodra et al. say outright that
the diffuse power on their own flat slabs cannot be surface roughness because all
three materials are smooth, and their fitted `S` falls with frequency for one
material and rises for another, which no RMS height can do. Pascual-Garcia
measures metrology and fits `S` on the same five physical samples and finds
micro-roughness under-predicting the observed diffuse scattering by an order of
magnitude in amplitude and two in power, every time. Landron characterises real
exterior walls at 50 to 250 times the coupon values. Koivumaki finds the
Lambertian pattern beating the directive one on whole facades at 28 GHz, because
pillars and protruding windows backscatter as much as they forward-scatter.

The RMS-set finding above is a third independent route to the same place.

Architectural consequence: if the diffuse fraction is set by structure, it
arrives in a comb of grating orders at angles the semantic layer can already
estimate from course pitch, which a random roughness parameter can never predict.
The honest hedge stays attached. No published experiment separates a comb from a
smooth lobe on a real facade, because every campaign uses a jointless coupon or a
whole building with no angular resolution on one patch. The measurement that
closes it is a bistatic 28 GHz scan across one square metre of real brickwork at
fixed incidence, and it is an afternoon of anechoic time.

### Xia et al. retain clutter, they do not recover it

The IEEE TAP 2024 paper that threatened the photogrammetry and clutter claims
simultaneously was marked abstract-only and paywalled. The PDF was in `lit/` and
has been read. Xia, Zhou, Zhang, Cui, Liu, Ji, Zhang, Zhao and Xiao, IEEE TAP
72(10):7986-7997, `10.1109/TAP.2024.3451214`, code public.

Their geometry is their own DJI Matrice 30 oblique drone survey, about 7000
aerial frames over a 900 by 800 m district near Qingdao with 55 buildings and
33 m of relief, described as high greenery with minimal traffic. There is no
street-level imagery anywhere in the paper. Cars are deleted, on the stated
grounds of temporariness. Vegetation, fences and street furniture are kept and
meshed by ball pivoting, vegetation as a closed shell with wood permittivity and
no canopy volume model. So the pipeline is segment, drop cars, mesh the rest, and
nothing is inferred for anything the survey did not directly see. Their own
concession: "more minute obstacles are not considered in the scene model, leading
to rays being traced that should not exist."

The clutter-recovery claim therefore survives, and it survives on the distinction
between recovering and retaining. Aerial photogrammetry is systematically blind
to vertical facade detail, under-canopy furniture, ground-level poles and
bollards, awnings and parked-vehicle geometry, which is what a street-level
camera sees best.

Two things from that paper cut the other way and are recorded because they will
be quoted back. Their scene-model ablation puts non-vegetation clutter at 0.6 to
0.7 dB and vegetation at 4 to 5 dB, and never separates fences from poles, so
their "clutter matters" headline is really a vegetation result. And their full
Degli-Esposti sweep concludes that diffuse scattering matters for delay and
angular spread rather than for path loss, moving RMSE by under 0.3 dB across the
whole `S` range. That second one is a gift: it is a published measured statement
that scalar path loss is the wrong place to look for scattering physics, which
supports computing an angular second moment instead. It is also a warning against
any claim here that materials or roughness change path loss.

Materials in that paper are one flat ITU value per class over five classes, with
no glass class at all in an urban scene, and the two concrete rows come from
different revisions of P.2040. Sub-facade material assignment is untouched.
