# Graslei at 28 GHz: an anchored generative twin

A digital twin of the Graslei quay in Ghent with an 8x8 MIMO panel at 28 GHz and
10 walking people, delivered as a module in the AEGIS viewer. Written 2026-07-30,
revised the same day after re-reading the July 28 brief and this session's research.

## Context

The previous version of this plan was wrong, and it is worth recording why, because
the failure is instructive.

It proposed making the existing scene *physically correct* at 28 GHz: fix the ground
material, add a scattering coefficient, measure whether window reveals matter, tile a
texture onto the grey prisms. Every step was defensible. The whole was pointed at the
wrong target, because the complaint on record was never that the scene was incorrect:

> "our current setup has only about six different materials and feels very
> homogeneous, an entire facade is brick, and the next building is all stone... We
> may be fundamentally wrong in our approach."

That plan would have produced exactly that scene, with better numbers attached.

## The governing principle

**Macro geometry is faithful to reality. Small detail is plausible for reality.**

The skeleton is measured and never invented: terrain, water, footprints, heights, the
road graph. Below that scale, where no dataset exists and none will, the twin
generates detail that is statistically right for this place rather than literally
right about it. That is the job an LLM is actually good at, and it is the only layer
where the model has any business making decisions.

Three consequences follow, and they resolve problems that previously looked like
blockers.

**Street-level imagery stops being a dependency for clutter.** Work was blocked on a
Mapillary token to measure clutter coverage along the walk. Under this principle the
measurement is beside the point. Google tiles cannot resolve a 15 cm lamp post at
25 cm/texel and OSM has three street lamps mapped within 200 m of Korenmarkt, so
clutter was never going to be recovered. It is going to be instantiated, and the
question is whether it is plausible, not whether it is the real one.

It does *not* stop being a dependency for facade grammar, and the distinction is
worth keeping straight. Clutter is genuinely unrecoverable and therefore generated.
A facade is right there in a photograph, and the difference shows: reading one
building from tiles alone marked four of seven schema groups `inferred`, and the
director's own note on the tile plate was that it "shreds the gable into spikes and
the facade into a purple smear". Given the same building's street photograph it read
stone cross-mullioned windows with a transom in the upper third and leaded upper
lights, and justified 7 mm RMS roughness from visibly washed-out mortar. Generating
plausible detail is the right move where no evidence exists. It is the wrong move
where evidence exists and was not fetched.

**The phase problem stops being a confession.** Window reveal depth cannot be pinned
tighter than about 0.10 m from the available evidence, while the interference phase
at 28 GHz moves 1174 rad per metre of depth. Fine geometry can never be a measurement
here. Under this principle it was never claiming to be.

**And the honest object becomes a distribution.** What gets built is one sample from
the family of scenes consistent with the measured skeleton. Re-rolling the clutter
seed while holding the skeleton fixed gives an exposure spread for the cost of a
re-run. "How much does invented detail move the answer" is a number nobody has, it
falls out of the same machinery, and it is the thing that makes generated detail
publishable rather than embarrassing.

## Approach

Anchored generative twinning, per the project brief in
`docs/superpowers/specs/2026-07-28-radio-digital-twin-project.md`. Measured skeleton,
procedural generators, model as scene director. What is new here is the evidence for
*why* the generator layer must be procedural rather than authored.

The strongest and most consistent finding in this session's research: **agents win at
parametric and procedural work and lose at anything eyeballed.** The most experienced
practitioner found ranked geometry-nodes scaffolding as "by far the most useful case
so far", two prompts for a parametric water surface with exposed controls without
touching a node, while two days spent on placement from screenshots ended in "Claude
vision is terrible" and abandonment.

So the previous plan's proposal to generalise `artloop/step04_row.py` by hand was the
losing approach dressed as reuse. A geometry-nodes grammar with the model setting
parameters is the mode that works. And placement is never the model's job: footprints
come from data, clutter positions are constrained by the road graph and quay edges.
The model classifies and turns knobs.

### The MineBench rubric, applied here

MineBench scores builds by four named failure modes. They read as a direct audit of
the current twin:

1. **Flat decoration**, colour painted on a box face. The previous plan's "tile a
   facade texture onto 320 prisms" was this exactly.
2. **Visible primitives**, a viewer can name the box. 320 OSM extrusions.
3. **Static isolation**, no environment. Empty streets, no vehicles, no people.
4. **Uniform detail**, equal resolution everywhere rather than concentrated on
   silhouettes, joints and openings. Every building gets one box and one material
   whether it is 3 m from the walk or 200 m away.

Failure mode four has a fix already half-built. `poc_relevance.py` computes
per-building importance and currently uses it only to *prune* buildings against a
triangle budget. The same number should *concentrate* grammar richness. Inverted use
of an existing quantity.

These four become an explicit pass/flag checklist on the six-view contact sheet.

## Layers

Each carries provenance: `measured`, `observed` or `plausible`. Nothing is
load-bearing and provenance-free.

| layer | content | provenance |
|---|---|---|
| L0 anchor | terrain, water, footprints, heights, road graph | measured (GRB, OSM, tiles) |
| L1 envelopes | roof forms | observed from the aerial plate, which is the only view of a roof |
| L2 facade grammar | storey count, window pitch and size, storefronts, balconies, sills | observed from street photographs where one exists, else plausible |
| L3 materials | ITU class, roughness sigma, scattering coefficient, PBR appearance | observed from street photographs, regional prior else |
| L4 clutter | vehicles in real parking lanes, trees, bollards, lamps, terraces | plausible, positions constrained by L0 |
| L5 people | 10 SMPL-X walkers on the real footway | measured route, sampled gait |
| L6 radiator | the 8x8 panel | placed by rule |

Provenance is per field, not per layer, and the director marks each one `seen` or
`inferred` itself. The audit in `twin/read.py` then checks the marks against what
the evidence could possibly support: a roof form marked `seen` from a street-level
view is flagged, because nothing at eye level looks down on a roof. That check
caught a real over-claim on its first run.

### Evidence sources, and what each can carry

| | Google 3D tiles | Mapillary photograph |
|---|---|---|
| roof form, massing | the only source | foreshortened or hidden |
| storey count, bay rhythm | usable | good |
| window size, glazing bars, reveal | no | good |
| ground floor kind | no | good |
| wall material, roughness | colour only | good |

Both go to the director, labelled, with a note on what each is weak at. Matching a
photograph to a building is geometric and never a search: the camera must stand
outside the building's street-facing edge, in range, and be pointing at it. The
target facade is then projected into the frame and outlined, so the director is
never asked to guess which of five houses it is being shown. Where the projection
runs off the top of the frame the outline gets a dashed lid, and the director marks
the roof `inferred` rather than reading a roof line that is not in the picture.

## Where the pipeline actually stands

Modules under `twin/`, each one job, no bpy below the realiser so every layer runs
under the venv and inside `blender -b` alike.

| module | job | state |
|---|---|---|
| `geo`, `anchor` | one ENU frame, the measured layer | done |
| `fetch_surface` | roads, water, trees, barriers from Overpass | done |
| `shoot` | one solved reference plate per building from the tiles | done, 32/32 |
| `mapillary` | street photographs matched and outlined by projection | done, 25/32 |
| `director` | the standing brief and the typed tasks | done |
| `read` | runs the director, audits against measured data | done |
| `facade` | the parametric grammar the readings drive | done |
| `clutter`, `people`, `radiator` | seeded plan, SMPL-X walkers, the 8x8 panel | done |
| `realise` | Blender realiser and materials | done |
| `rtproxy` | Sionna export at the coarse LOD | not built |

Run order for a new area: `fetch_surface` -> `shoot` -> `mapillary` -> `read` ->
`realise`. Only `areas.py` is city-specific, and only the camera and cell presets in
it are authored rather than derived.

## Toolbox

- **Buildify** for facade grammar. Footprint-driven by design, so it anchors to L0
  cleanly.
- **The City Generator 2.6** for clutter and vehicles. Integration risk to settle
  first: it is built to invent whole cities, which is the opposite posture to
  anchoring. The question is whether its clutter and vehicle layers detach from its
  street generator and instance onto our road graph. If not, take the assets and
  drive them ourselves.
- **PolyHaven via blender-mcp** for PBR materials and HDRIs. Already wired into the
  vendored addon. CC0, so nothing blocks publishing the twin later. This is the real
  answer to failure mode one: normal and roughness maps, not colour on a box.
- **Blender authors, Three.js displays.** Geometry nodes is Blender-only and is the
  modality that works. The viewer is already R3F. No converter in between.
- Sketchfab is available for specific props. Hyper3D Rodin generation is available and
  not recommended, since generated meshes in the reviewed experience arrived rotated
  and unusable.

## Pre-flight

Three measured blockers, roughly two hours, independent of everything above.

- **The pipeline does not run at 28 GHz at all.** `medium_dry_ground` is valid only
  1-10 GHz and `sionna.rt` raises rather than clamping. `export_scenes.py:73` sets it
  as the ground for the hybrid and OSM scenes, and `paths_from_sionna_scene` assigns
  `scene.frequency` as its first action. Swapping to concrete moves the ground bounce
  from -4.9 to -8.1 dB, so existing 3.5 GHz numbers are not comparable across it.
- **`max_center_paths: 12` silently cancels any scattering work.**
  `study/channel_det.py::_cap_paths` keeps the 12 strongest paths by power. Diffuse at
  S = 0.3 produces around 17,000 weak paths carrying 9% of reflected energy between
  them. Enabling S under the shipped config makes the specular paths 0.41 dB weaker
  and recovers none of the diffuse. No error, no warning. Fix by clustering into ~30
  angular bins and summing incoherently within each, which is honest because diffuse
  scattering is incoherent by construction.
- **Skin needs its own radio material.** Computed from AEGIS's own `SKIN_28GHZ`
  (eps_r 17.0, sigma 25.0), skin reflects at 0.679 against brick at 0.328, so a person
  is a 6.3 dB stronger reflector than a brick wall and fully opaque at ~9100 dB/m.
  The nearest ITU material is `wood` at 0.170, which would let rays pass through
  people. Use `RadioMaterial(17.0, 25.0, thickness=0.05)`.

Frequency itself is free in the solver: 4.2 s at 28 GHz against 4.3 s at 3.5 GHz,
measured, 10 receivers, depth 3. The cost lives downstream in the AEGIS kernel, which
builds an (M_tri, N_paths) phase matrix.

## Phases

**A. Grammar loop on one row.** Install Buildify and The City Generator, settle the
detachment question, and drive Buildify from the six Graslei footprints already in
`decisions.json`. Read the tile facade renders, set knobs, render, compare, correct.
This is the loop that either works or does not, and everything downstream assumes it.

**B. The block.** Extend to the quay and its opposite bank. Grammar richness scaled by
the relevance number rather than pruned by it. Materials with provenance. PolyHaven
PBR on everything.

**C. Clutter and vehicles.** Parking lanes from the road graph, trees at the 32 mapped
positions plus plausible rows, terraces at the mapped restaurant POIs, bollards along
the quay edge. Seeded, so it can be re-rolled.

**D. People and the panel.** 10 SMPL-X walkers from the AMASS clips in `data/poses/`,
placed by `SmplxWalkPoser` on the real footway. `AntennaArray.upa(8, 8, ...)` at
28 GHz, facade-mounted. Leave-one-out tracing, since a body sitting on its own
receiver returns no valid paths while the other nine must stay in as blockers. Beam
scheduling decided rather than accidental: HPBW is 12.7 degrees and the spot at 20 m
is 4.5 m across, so single-stream MRT illuminates one person and leaves nine in
sidelobes. Round-robin across frames.

**E. Trace, and the seed spread.** Sionna at 28 GHz, `center_paths` for the power
normalisation, `expand_paths_to_array`, level 7, 4 cm2 averaged S_ab against the
20 W/m2 ICNIRP local limit. Then re-roll the clutter seed N times on the fixed
skeleton and report the spread.

**F. Viewer module.** Studio pattern: `scripts/twin_precompute.py` into
`data/twin/graslei/`, `src/aegis/viewer/routes/twin/`,
`aegis-web/src/modules/cityTwin/`. Only two shared files need a line each
(`registry.ts`, `routes/__init__.py`), and a second agent shares this checkout, so
touch those last.

## Verification

- **The four failure modes** as an explicit pass/flag on a six-view contact sheet.
  Offscreen viewport renders cost 0.3 s each, so this is close to free.
- **Numeric `verify()`** re-deriving facts from the built scene rather than trusting
  the build. The precedent is worth keeping: `lobe_peak_error_deg = 0.314` catches a
  transposed axis instantly, and a phantom height check catches a units error that no
  render reveals.
- **Both, because neither is sufficient.** Earlier this session the physics was
  verified to 0.31 degrees through seven consecutive iterations in which the picture
  was unusable. Verification says the model is correct. It says nothing about whether
  the render communicates.
- **Bodies are opaque**: a receiver directly behind a body loses 15-25 dB against the
  same receiver with the body removed. If not, the skin material did not take.
- **Power is not double-counted**: total radiated power integrates to the configured
  transmit power. The bridge traces at a fixed 1 W reference and the configured power
  enters once through MRT normalisation, so bespoke glue lands 18-30 dB hot.
- **Provenance coverage** reported per layer: what fraction of the scene is measured,
  observed, plausible.
- `ruff check`, `ruff format --check`, `pytest tests/ -m "not slow"` before each
  commit.

## What generalises

Config is lat/lon/radius. The anchor layer, the exports, the array, the bodies and the
kernel are already coordinate-free or parameterised.

The grammar layer generalises **only if the style vocabulary does**. A Flemish gable
library does not dress Haussmann. This is precisely why the knobs are model-set rather
than hard-coded: the model already knows what limestone, wrought iron and zinc
mansards look like, and writing that library by hand per city is the thing that does
not scale.

One dependency does not generalise and is sidestepped rather than solved:
`data/sites.json` is the Belgian BIPT register with no French equivalent here. This
demo places its panel by rule, so it does not touch it. A future macro-cell study
elsewhere has to deal with it properly.
