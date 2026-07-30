# Hybrid twin experiment

One-shot experiment (2026-07-27): can an AI agent with headless Blender build an
"intelligent semi-manual hybrid" of Google Earth photogrammetry and OSM vectors,
instead of choosing one mesh source for ray tracing?

## Why

Photogrammetry (Google 3D Tiles): real heights, real terrain, real landmark
geometry, but melted facades, fused trees, no semantics, terrible for RT normals.
OSM extrusions: clean planar facades and semantics, but 91% of buildings here had
no height data, no terrain, and boxes lie about monuments. The hybrid takes each
source where it is strong and logs every decision.

## Pipeline (all headless, no GUI)

1. `download_google_tiles.py` - traverses the Google Photorealistic 3D Tiles tree
   (OBB-vs-sphere intersection, session token handling), downloads GLBs for a
   200 m radius around the Korenmarkt, Ghent. 177 tiles, 21 MB. Needs
   `GOOGLE_API_KEY` (the one in `aegis/.env` works).
2. `fetch_osm.py` - Overpass query for building footprints + height tags.
   448 buildings, only 39 with height/levels tags.
3. `build_scene.py` - runs in `blender -b`. Imports GLBs, self-calibrates the
   importer axis convention (tries candidate rotations, keeps the one landing at
   the geodetic anchor), transforms ECEF to a local ENU frame, extrudes OSM
   footprints in the same frame, renders matched views for visual verification.
4. `analyze_hybridize.py` - the intelligence. Builds a 497k-triangle BVH from the
   photogrammetry, raycasts a 3 m grid (~20k rays) for a terrain model, then per
   footprint measures ground level and roof height distribution and decides:
   - `confirmed` (14): OSM tag within 3 m of measurement, keep tag
   - `adopted-photo` (332): no OSM height, adopt measured p75 height
   - `conflict-photo` (8): tag disagrees, measurement dense and consistent,
     trust the mesh (found a cluster of stale blanket `height=18` tags,
     measured 12-14 m)
   - `conflict-tag`: tag disagrees and measurement noisy, keep tag
   - `no-data` (90): photogrammetry hole or footprint under 4 samples, keep
     tag or default (correctly caught the Belfort at the tile-coverage edge and
     kept its 95 m tag)
   - `landmark-keep-photo` (4): large and strongly non-prismatic, a box would
     lie, so the photogrammetry mesh is carved out per footprint and kept.
     Auto-detected: Sint-Niklaaskerk, Sint-Michielskerk, De Post, Stadhuis.
   Plus off-footprint detection: elevated cells not covered by any OSM polygon,
   clustered into 63 blobs, classified vegetation vs unmapped structure by
   height roughness.

Outputs: `data/decisions.json` (full audit), `scene.blend`, `scene_hybrid.blend`,
`renders/*.png`.

## Run

```bash
set -a; source ../../../.env; set +a
python download_google_tiles.py --lat 51.0550 --lon 3.7220 --radius 200
python fetch_osm.py --lat 51.0550 --lon 3.7220 --radius 200
~/blender-4.5/blender -b -P build_scene.py -- --renders renders
~/blender-4.5/blender -b scene.blend -P analyze_hybridize.py
```

Whole pipeline is a few minutes on CPU; renders are Cycles CPU at 24 samples.

## Session 2: relevance-driven LOD PoC + legacy pipeline resurrection

- `route_foot.py` - pedestrian routing on the OSM street graph (Dijkstra over
  foot-tagged ways). Needed because the key's Google project has neither the
  legacy Directions API nor the new Routes API enabled (this also silently
  breaks `aegis.study.mobility.route_walk` for uncached routes).
- `poc_relevance.py` - the walk + the real sites from `data/sites.json`
  (flanders.parquet: positions/azimuths/heights present, frequency/gain/tilt
  100% missing) drive a per-face importance field over the photogrammetry:
  direct blocker pass + 40k-ray specular Monte Carlo per site, scored by
  closest approach of reflected rays to the walk. Rolled up per footprint,
  adaptive tiering (97th percentile). Ghent block result: 497k triangles ->
  6.7k budget, 4 detailed buildings of which two sit 240 m off-walk and matter
  only through specular bounces, 271 prisms, 173 dropped, walk LOS fraction
  0.64. Walk z uses min-over-disk projection so the tube hugs streets.
- `data/itu_p2040_materials.json` - Table 3 of ITU-R P.2040-4 (09/2025),
  extracted from the official PDF. Use this, not model memory.
- Legacy `outdoor_environment.py` (hybrid-QuaDRiGa-FDTD): resurrected headless
  on Blender 4.5 up to 13 of 15 steps (blosm from repo + assets.zip + shim
  addons + STL operator rename + collection-link guards + tty shim + Overpass
  map pre-fetch). Remaining blocker: this blosm version lands Google tiles
  ~250 m off the OSM anchor, the 5 m `MAX_XY_MISMATCH` guard skips the XY fix,
  Z-alignment then diverges (+9.7 km) and the bbox cutoff crops a shard, so
  all 47 OpenCellID towers fail their shrinkwrap projection and the LOS loop
  runs empty (also: `base_stations` is only populated in the cache-skip branch
  on a fresh `NEVER_SKIP` run - latent since 2024). Verdict: port the unique
  steps (towers, GPX rig, LOS, QuaDRiGa export) onto the API-first acquisition
  above instead of pinning blosm; geodetic ECEF->ENU anchoring makes the whole
  landmark-matching alignment unnecessary.

## Session 3: materials, vegetation, and the three-way ablation

- `route_google.py` - the walk now comes from the Routes API (computeRoutes,
  WALK): 495 m Korenlei -> Korenmarkt -> Groentenmarkt. `aegis.study.mobility`
  was ported to the same endpoint (committed separately), un-breaking uncached
  routing for the ten-cities batch. Relevance rerun on the real walk: LOS 0.78,
  budget 30.6k tris (6 detailed / 322 prism / 120 dropped).
- `export_scenes.py` - exports three Sionna-loadable scene variants (Mitsuba
  XML + binary PLY, ENU frame): `scenes/hybrid` (carved landmarks + audited
  prisms + raycast terrain + 15 canopy proxies, 67k tris), `scenes/osm` (all
  448 footprints on flat ground, 19k tris), `scenes/photo` (raw 497k-tri
  photogrammetry, one material). Validated: LOS path = free space to the
  decimal in all three. Found: the terrain fit must reject roof samples
  (morphological filter), and 13 buildings in decisions.json have ground_z
  measured on a neighbour's roof (clamped at export). See EXPORT_NOTES.md.
- `render_facades.py` - street-level Cycles shots of 32 walk-corridor
  buildings from the textured tiles (4 honestly occluded). Finding: ge=2.0 m
  is the deepest LOD Google serves here (~25 cm/texel), so facades resolve at
  60-100 m standoff and never in alleys; tile materials are baked emission,
  shadowed captures stay dark.
- Material A/B (32 buildings x frontier vs Haiku, facade render + OSM context,
  P.2040 vocabulary, `building:material` tags withheld as ground truth):
  agreement 69%, ground truth frontier 4/5 vs Haiku 2/5, and Haiku collapses
  to "plasterboard" for 29/32 with *higher* mean confidence (0.76 vs 0.60).
  Verdict: per-item material judgment needs a frontier model; Haiku only for
  mechanical steps. Results in `data/materials.json` + `data/materials_ab.json`.
- `run_ablation.py` - Sionna path solver, 4 real masts x 3 scenes along the
  walk, 3.5 GHz, depth 3, diffraction on, TR 38.901 sector patterns applied
  analytically per path (verified against traced sectors). Vegetation proxies
  use an effective medium from ITU-R P.833-10 Table 8 (2.23 dB/m in-leaf ->
  sigma 1.49e-3 S/m at eps' 1.2), derivation in `data/vegetation_material.json`.
- Smoke-run verdict (see ABLATION_NOTES.md): the two naive baselines fail in
  opposite directions. Photo is uniformly 12-20 dB dark and loses paths
  entirely on stretches; OSM matches the hybrid to <0.5 dB on ordinary streets
  but over-predicts by 4-5 dB median (up to +26 dB p90) from the tall masts
  and manufactures 21 LOS samples where the audited skyline gives none.
  Deep-shadow tail needs >=4e6 solver samples; LOS flags are seed-exact.

## Notes and next steps

- Tile GLBs and renders stay untracked (Google ToS on caching tile content).
- The z-anchor lesson: OSM at ellipsoid h=0 buries the city 50 m below the
  photogrammetry terrain. Any hybrid must sample per-building ground from the
  mesh. Ghent ground is at ~+52 m ellipsoidal height.
- Facade texture baking (project photogrammetry color onto the clean prisms) is
  the missing prettiness step. Cycles bake per building, doable but slow on CPU.
- LOD2: the roof-height distribution per footprint already contains ridge/hip
  information (p75 vs max vs std). Fitting gabled roofs instead of flat tops is
  a cheap upgrade.
- Model-intelligence question: authoring this pipeline needed judgment
  (axis self-calibration, decision thresholds, debugging camera aim from a blank
  render). Running it does not: the structured decisions (arbitrate a conflict,
  classify a blob crop) are small closed questions a cheap model could answer
  per-item once the harness exists. The natural A/B: hand `decisions.json`
  conflicts + render crops to Haiku vs a frontier model and count agreement.
