# Clutter and the harness question

Notes toward the next stage: take the Inhouse 3D Tiles environment and mass
produce ray-tracing scenes whose small clutter is accurate. Written 2026-07-30.
Everything here is either measured in this repo or measured below; where it is
an opinion it says so.

## 1. Clutter cannot be extracted from the tiles

`README.md` (session 3) already establishes the ceiling: `ge=2.0 m` is the
deepest LOD Inhouse serves for this block, about 25 cm/texel, facades resolve
only at 60-100 m standoff and never in alleys, and tile materials are baked
emission so shadowed captures stay dark.

At 25 cm/texel a 15 cm lamp post is sub-texel. It is not that the geometry is
melted, it is that the object was never sampled. No amount of mesh processing,
model cleverness or prompt engineering recovers an object the capture did not
contain. **Clutter has to be instantiated from other evidence, not extracted.**

That reframes the whole problem. The question is not "which agent cleans up the
tiles", it is "what is the evidence source for objects the tiles never saw, and
how is it turned into geometry with materials".

## 2. OSM is not that evidence source

Measured 2026-07-30, Overpass, 200 m radius around the Korenmarkt anchor
(51.0550, 3.7220), the same footprint the rest of this study uses:

| count | feature            |
|------:|--------------------|
|    32 | `natural=tree`     |
|    23 | `barrier=bollard`  |
|    19 | `amenity=waste_basket` |
|    13 | `amenity=bench`    |
|    10 | `barrier=wall` (ways) |
|     8 | `amenity=bicycle_parking` |
|     5 | `barrier=gate`     |
|     3 | `highway=street_lamp` |
|     3 | `barrier=fence`    |
|     2 | `highway=bus_stop` |

308 elements total, but the large counts are points of interest, not objects:
59 `amenity=restaurant`, 17 `amenity=pub`, 15 `fast_food`, 12 `cafe` are labels
hung on buildings with no geometry, and 43 `man_made=surveillance` are cameras
that are irrelevant scatterers at 3.5 GHz.

Three street lamps in a 200 m radius of a major city square is the number to
remember. Belgium is well mapped and the building layer here is good enough that
`fetch_osm.py` returned 448 footprints. Street furniture is simply not mapped to
the same standard anywhere. A pipeline that sources clutter from OSM produces
empty streets and does it silently, which is the worst failure mode available:
the scene looks finished.

Trees are the exception worth keeping. 32 mapped trees is plausible coverage,
and vegetation is the one clutter class the ablation already shows to matter
(the canopy proxies carry an ITU-R P.833-10 effective medium).

## 3. Decide how much clutter is worth modelling before building for it

This repo already contains the instrument to answer that, and the answer is not
yet known. `run_ablation.py` traces 4 real masts against 3 scene variants along
a routed walk and reports per-sample path gain and LOS flags. The smoke run says
the dominant errors are:

- photogrammetry uniformly **12-20 dB dark**, from melted facade normals
- OSM **over-predicting 4-5 dB median, up to +26 dB p90** from the tall masts,
  and manufacturing 21 LOS samples the audited skyline does not allow

Both are macro-geometry errors: facade normals and skyline. Neither is a
small-clutter error. Before investing in a clutter pipeline it is worth adding a
fourth arm to the existing ablation - the hybrid scene with clutter classes
switched on and off - and reading the dB delta on the same walk. If poles and
benches move the median by 0.2 dB while facade treatment moves it by 15 dB, the
effort belongs on facades.

A physics-ordered prior for what should matter at 3.5 GHz (lambda 8.6 cm),
strongest first, to be confirmed or killed by that ablation:

1. **Vegetation.** Volumetric attenuator, metres thick, already in the pipeline.
2. **Vehicles.** A parked van is a 2 x 5 m conducting blocker at pedestrian
   height, sitting exactly in the street canyon the walk runs through.
3. **Facade micro-structure.** Balcony slabs, window recesses, shopfront glass.
   Not "clutter" in the street-furniture sense, but it is the actual cause of
   the 12-20 dB photogrammetry deficit, and it is geometry the tiles smoothed.
4. **Poles and masts.** Thin vertical scatterers, small RCS individually.
5. **Small furniture.** Bollards, bins, benches. Sub-metre, near the ground.

The ordering matters because 4 and 5 are what "small clutter" usually means, and
they are at the bottom.

## 4. Imagery: Mapillary before Street View

Street View has the resolution the tiles lack and carries pose metadata, so
detections can be back-projected onto the mesh. The problem is licensing: the
same Inhouse terms that keep tile GLBs untracked in this repo constrain derived
and cached content, and a published paper with a reproducible scene corpus is
exactly the case that gets awkward.

Mapillary is the better first call:

- imagery and API are free under **CC BY-SA 4.0**, and the data is explicitly
  downloadable as GeoJSON
- the computer-vision pipeline already publishes **map features**: 42 point
  classes including poles, street lights and benches, plus ~1500 traffic sign
  classes, as geolocated vector geometry at `tiles.mapillary.com`
- because detections are pre-extracted, the expensive per-image VLM detection
  step disappears for those classes

Constraint noted from the API docs: since 2026-01-16, bbox queries against
`/images`, `/map_features` and detection search must be smaller than
0.01 degrees square, so a city has to be tiled into requests. That is a harness
detail, not a blocker.

**Open question, needs a token to answer:** what is actual Mapillary coverage
along the Ghent walk corridor? Coverage is contributor-driven and varies wildly
between cities. If Ghent is well covered, Mapillary is the clutter source. If it
is not, the fallback is procedural priors conditioned on street class (lamp
spacing, tree spacing, bollard runs) with Street View used only as a visual
check rather than as stored derived data.

## 5. The harness: not Blender MCP

Blender MCP is the wrong tool for the mass-production stage, for reasons that
are structural rather than aesthetic.

- **It needs an interactive Blender.** The addon dispatches every command
  through `bpy.app.timers`, which only fire inside the interactive event loop.
  `blender --background` with a blocking wait never executes a single command.
  Verified directly (see `tools/blender-mcp/studio.sh`, which exists because the
  fix is a virtual X display, not a flag).
- **It is a chat-latency loop.** Every operation is a socket round trip driven
  by a model turn. That is the right shape for exploring one scene and the wrong
  shape for building a thousand.
- **This pipeline is already headless Python and that is strictly better.**
  `build_scene.py`, `analyze_hybridize.py` and `export_scenes.py` run under
  `blender -b -P` or plain Python, are deterministic, and leave an audit trail
  in `decisions.json`.

Where an agent genuinely earns its place, per the README's own observation that
authoring needed judgment but running does not:

- **Authoring and extending the pipeline.** Axis self-calibration, threshold
  choice, debugging a blank render. Interactive, one-off, high judgment.
- **Per-item structured judgment inside the batch.** Already measured here:
  material assignment needs a frontier model, agreement 69%, ground truth 4/5
  frontier against 2/5 Haiku, and Haiku collapsed to "plasterboard" for 29/32
  buildings *with higher mean confidence* (0.76 against 0.60). That last detail
  is the important one - the cheap model fails confidently, so confidence cannot
  be used as the routing signal.
- **Audit at scale.** A model that reads rendered views plus the decisions log
  and flags scenes that came out wrong. This is the piece that makes mass
  production safe, and it does not exist yet.

## 6. Against a single master prompt

One master prompt that produces an environment is unverifiable and unbatchable.
It cannot be regression tested, a failure cannot be localised, and cheap and
frontier models cannot be routed per decision.

The alternative that fits what is already built: **a typed contract per decision
point.** Each one gets a schema, a golden set, and its own cheap-vs-frontier
A/B, exactly like the material A/B already run. Candidate decision points:

| decision | input | output schema |
|---|---|---|
| facade material | facade render + OSM context | P.2040 class + confidence |
| clutter class | Mapillary detection + crop | proxy type, dimensions, material |
| height conflict | OSM tag + measured distribution | keep-tag / adopt-photo / carve |
| blob classification | height roughness + crop | vegetation / structure |
| scene audit | rendered views + decisions log | pass / flag + reason |

Each is a small closed question. Each is testable against held-out ground truth.
The composition of them is the "environment", and the harness that runs them is
plain Python.

## 7. Multi-angle checking is cheap and catches real errors

One camera angle hides a class of error that survives numeric checks. Building
a contact sheet - the same scene rendered from six orbit positions - caught a
lighting artefact in an unrelated scene today that seven single-view iterations
had missed, and confirmed a shading term was correct in a way no single view
could. For scene QA at scale this is close to free: `bpy.ops.render.opengl`
renders a viewport-quality frame offscreen in about 0.3 s at 800x450, against
39.5 s for EEVEE on this box.

Worth wiring into the audit step in section 5: every produced scene gets a
six-view sheet, and the audit model sees the sheet rather than one hero render.

## 8. Suggested order of work

1. Add the clutter on/off arm to `run_ablation.py`. Decide from the dB delta
   whether clutter is a first-order term at all. This is a day and it might
   redirect everything after it.
2. Get a Mapillary token, measure coverage along the Ghent walk corridor.
3. If facades dominate (likely, given the 12-20 dB deficit), the next build is
   facade micro-structure - parametric balcony and recess reconstruction on the
   audited prisms, driven by the facade renders that `render_facades.py`
   already produces.
4. Only then the clutter instancer, sourced from Mapillary where coverage
   allows and procedural priors where it does not.
5. The scene auditor, with six-view sheets, before any run that produces more
   scenes than a human will look at.

## 9. Every facade is currently specular-only (check this first)

Verified against the installed sionna-rt on 2026-07-30:

```
itu_material('brick', 3.5e9)  -> (3.91, 0.0291)     # permittivity, conductivity only
RadioMaterial defaults        -> S = 0.0, Kx = 0.0  # no diffuse component
```

`export_scenes.py` emits `<bsdf type="itu-radio-material" id="mat-itu_{name}">`
with no scattering parameters, so all three scene variants trace facades as
pure specular reflectors. The only material in the pipeline with custom
scattering behaviour is the vegetation effective medium built in
`run_ablation.py`.

This is worth testing before any geometry work, because ray tracing represents
small-scale facade structure as a **material parameter rather than as geometry**.
The effective roughness model (Degli-Esposti, IEEE TAP, July 2001; implemented
in Sionna) splits incident power as `R^2 + S^2 = 1` with a scattering
coefficient `S`, a cross-polarisation coefficient `Kx` and a lobe shape.
Measured `S` for brick and concrete at these frequencies is typically of order
0.2 to 0.4, not 0.

Hypothesis, not a result: a specular-only melted mesh sends reflected power in
the wrong directions and the receiver never sees it, which is what a uniform
12-20 dB deficit looks like. A diffuse lobe is much less sensitive to exact
normal orientation, so switching `S` on should preferentially rescue the
photogrammetry scene - the one that is failing. It will move all three scenes,
which is exactly why it needs the ablation rather than an argument.

Cost: one parameter per material. Compare against reconstructing balcony
geometry.

## 10. On generative 3D as a cleanup step

The idea of cutting the tiles into pieces and handing each blob to a 3D-native
generative model is feasible in the narrow sense. `MeshReGen` (arXiv 2604.28134)
does VecSet-conditioned geometry regeneration - update or improve an input mesh
with fine-grained detail - which is the shape of the request.

Three reasons it is the wrong tool for this target:

1. **Off-the-shelf models are out of distribution.** The MeshReGen evaluation
   notes that TRELLIS "fails to recover fine geometry, as it is trained on clean
   geometry which does not generalize to broken, incomplete inputs", with
   Hunyuan3D-Omni degrading similarly. Photogrammetry blobs are that case.
2. **Ray tracing needs correct, not plausible.** A generated balcony cannot be
   falsified against the real building, so it cannot enter `decisions.json` with
   a justification, which is the property that makes this pipeline defensible.
3. **It generates geometry the physics wants as a parameter** (section 9), on a
   heavier mesh, which the solver then reduces to statistics anyway.

The vegetation case makes the cost concrete: a generative tree brings tens of
thousands of leaf facets, when the correct RF model is a volumetric attenuator
with the P.833-10 effective medium already derived in
`data/vegetation_material.json`. Denser and less correct at once.

**Where multimodal 3D models do belong: recognition and parameterisation.**
Blob plus street imagery in, a typed description out - "plane tree, 12 m,
trunk at (x, y), canopy radius 4 m", or "brick, four storeys, balconies,
ground-floor glazing" - and the harness instantiates a parametric proxy or sets
`S`, `Kx` and permittivity. That output is small, checkable against held-out
ground truth, and fits the typed-contract table in section 6.
