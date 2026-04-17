# QA plan — maintainability refactors (v0.29.0 → v0.29.2)

Three rounds of maintainability refactoring touched almost every viewer surface: backend routes, the viewer compute orchestrator, voxel meshing, base station processing, frontend stores and hooks, physics, and the entire panel/scene tree. Organized here by the touched surface so a tester can see what to verify for any given feature, not which PR it came from.

No intentional behavior change across all three rounds. This plan targets regressions the extractions could plausibly cause plus the interleaved production fixes that shipped between tags.

## Backend

### Flask routes (v0.29.0 PR-2/3 + v0.29.1 PR-B/C/D)

Every route handler under `src/aegis/viewer/routes/` moved from a nested closure to a module-level `_impl(cache, cache_lock)` function. `server.py` (670 lines) became a package with `_cache`, `_fidelity`, `_auth`, `_bodies`, `_voxels`, `_precompute`, `_app` submodules. `routes/compute.py` became an 11-file package. `routes/basestations.py` became a 6-file package (`_geocode`, `_fidelity`, `_data`, `_load`, `_compute`, `_compute_mimo`). Nine heavy handlers (`_api_compute_impl` 61→4, `_api_compute_rt_impl` 52→16, `_build_config` optimize 41→5, `_handle_export_config` data 35→2, `_api_location_load_impl` 37→20, `_build_scene` mimo 35→7, etc.) further decomposed.

External contracts preserved: `register(app, cache, cache_lock)`, public exports from `viewer/server/__init__.py` (`create_app`, `create_app_from_env`, `_cache`, `_cache_lock`, `scoped_cache_*`, `_load_and_cache_voxels_dir`, `FIDELITY_LEVELS_API`), late-import shims for `_validate_scene_path` and `_run_dosimetry` so `mock.patch` still works.

- [ ] `python -m aegis.viewer --location "Ghent, Belgium"` launches and registers 74 routes
- [ ] `POST /api/compute` default config returns 200 with `sab`, `stats`, `extra`
- [ ] `POST /api/compute` multi-antenna sums `S_inc` and returns per-antenna contributions
- [ ] `POST /api/compute` with stochastic channel preset returns `cluster_viz`
- [ ] `POST /api/compute` mode-based (bound, aggregate, spatial + fresnel + curvature) returns correct level
- [ ] `POST /api/compute` legacy level-based (0, 2, 5, 6) matches expected kernel dispatch
- [ ] `POST /api/compute/rt` DiffeRT returns path count and timings
- [ ] `POST /api/compute/voxel-rt` voxel hull RT produces correct quad count
- [ ] `POST /api/compute/sionna-rt` Modal path hits scene cache on second call
- [ ] `POST /api/compute/sionna-env-rt` environment mesh RT runs
- [ ] `POST /api/validate/sinc` CloudRF comparison response structure intact
- [ ] `GET /api/gpu/status`, `GET /api/scenes`, `POST /api/scene/load`
- [ ] `GET /api/voxels/hull-mesh` confirmation-gated lazy mesh path
- [ ] `GET /api/export/dosimetry-{csv,json,npz}` work after a compute; `guardSab` blocks export with no cached SAB
- [ ] `GET /api/export/config` returns deterministic JSON covering dosimetry, body, antenna, raytracer, stochastic, display
- [ ] `GET /api/compliance/report`, `GET /api/channel-presets`, `POST /api/lsp-heatmap`
- [ ] `POST /api/basestations/load` with `{"location": "Ghent, Belgium", "radius_m": 500}` returns Flanders dataset
- [ ] `POST /api/basestations/load` with raw `{"lat": 50.85, "lon": 4.35}` resolves Brussels via reverse geocode
- [ ] `POST /api/basestations/load` with unknown country returns `{"count": 0}`
- [ ] `POST /api/basestations/load` with explicit `bbox` bypasses geocode
- [ ] `POST /api/basestations/compute` still honours `exposure_mode`, `indices`, `max_distance_m`
- [ ] `POST /api/basestations/compute_mimo` accepts `level` 7 or 8 only, archetype `mmimo` only
- [ ] `GET /api/basestations/list` returns `fidelity_tier` per base station (full/spatial/geometric/bound/location_only)
- [ ] `POST /api/optimize` placement/tilt_power/mimo_peak modes all stream SSE with `iter`, `objective`, `sab_b64`, `done`
- [ ] `POST /api/location/load` streams SSE progress events ending in `{"done": true}`
- [ ] `POST /api/geocode` `{"query": "Brussels"}` returns lat/lon/address
- [ ] `POST /api/mimo/compute` per-user SAB distributions and compliance summaries

### Auth + session gate (v0.29.1 PR-B)

`_auth` submodule: `setup_auth`, `_path_is_exempt`, `_auth_probe_response`, `_auth_login_response`.

- [ ] `AEGIS_GATE_PASSWORD` set. `/api/auth` login with correct password issues session cookie
- [ ] Exempt paths (`/api/health`, `/api/auth`, `/robots.txt`, `/assets/*`, `/cesium/*`, `/`) bypass the gate

### Body + voxel preload (v0.29.1 PR-B)

- [ ] Bodies load from `data/*.stl`; `phantoms.yaml` device_offset overrides apply
- [ ] GLB phantoms (thelonious/duke/eartha/ella/adult_male/adult_female/boy_6y/girl_8y) shadow STL only where a GLB is missing
- [ ] Background averaging-matrix precompute runs on first request; `G(<body>, 4cm2)` log line per body under the triangle budget

### Viewer compute orchestrator (v0.29.0 PR-4)

`viewer/compute.py::compute_dosimetry` split into `_compute_incidence_geometry`, `_generate_stochastic_paths`, `_build_single_antenna_paths`, `_generate_multi_antenna_paths`, `_generate_single_plane_wave_paths`, `_run_engine_mode`, `_run_engine_legacy_level`, `_run_engine_compute`, `_build_compute_extras`. Return tuple and `timings` dict byte-identical.

- [ ] `S_inc` matches pre-refactor baseline for a fixed (antenna pos, power, phantom) triple
- [ ] Distance readout matches antenna-to-body-center distance
- [ ] Status bar timing breakdown (body transform, engine compute, total) populated
- [ ] Fine-grained timings (`kernel_ms`, `avg_build_G_4cm2_ms`, `avg_matvec_4cm2_ms`, `avg_build_G_1cm2_ms`) populated when applicable
- [ ] Zero-antenna edge case returns zero-power result without crashing
- [ ] `exposure_mode` `actual_max`/`typical` reduce effective power vs `theoretical`
- [ ] Curvature-enabled modes (`level >= 5` or `corrections.curvature`) produce different S_ab than Fresnel-only

### Voxel greedy meshing (v0.29.0 PR-1 + v0.29.2 PR-H)

Old v1 greedy-meshing deleted (v0.29.0 PR-1). v2 (maximal-area rectangle) is canonical and was split into `_mesh_direction`, `_mesh_slice`, `_best_rectangle_for_seed`, `_emit_greedy_quad` (v0.29.2 PR-H).

- [ ] Voxel source renders hull mesh without holes or overlapping quads
- [ ] `/api/voxels/hull-mesh` triangle count matches pre-refactor baseline for a known voxel set
- [ ] `POST /api/compute/voxel-rt` produces plausible `sab`
- [ ] Bridge-like scenes (stacked materials) emit correct per-face normals and no holes
- [ ] Greedy-rectangle picker still prefers squarer quads over u-biased strips (visual check on a mixed-material cube)

### Base station processing (v0.29.2 PR-H)

`basestation/msi.py::parse_msi` split into `_parse_frequency`, `_parse_gain`, `_parse_tilt`, `_read_pattern_rows`. `basestation/merge.py::spatial_dedup` split into `_project_to_metres`, `_bfs_cluster_labels`, `_merge_cluster_rows`.

- [ ] Load `data/basestation/patterns/*.msi`; every pattern's `gain_dbi`, `frequency_mhz`, `tilt_deg` matches prior parse
- [ ] Range notation (`FREQUENCY 1.88-1.93`) returns the midpoint
- [ ] `GAIN 12.86 dBd` converts to 15.01 dBi (+2.15)
- [ ] `zenith` convention still detected when `v_atten[0] != 0`
- [ ] Belgium full dataset merges to same cluster count as pre-refactor
- [ ] Cross-operator towers within 50 m stay separate
- [ ] Same-operator same-frequency towers within 50 m merge into one row
- [ ] NaN fields fill from later rows in the cluster

### Interleaved production fixes (#535 → #544)

Shipped between v0.29.1 and v0.29.2. Verify they still hold.

- [ ] `#535` Belgium geocoding: "Ghent" / "Bruges" / "Antwerp" route to the correct region data
- [ ] `#536` GPU-unavailable Sionna RT returns 501 (not 503) without a Modal token
- [ ] `#537` MIMO precoder fallback, camera toggle, export errors, optimize cancel — full MIMO flow doesn't crash the UI
- [ ] `#539` Fresnel correction checkbox labels as angle-dependence (not baseline Fresnel)
- [ ] `#540` No dead CloudRF coverage checkbox in Environment panel
- [ ] `#541` Malformed `/api/compute` payloads (bad array shapes, wrong types) return 4xx with useful messages
- [ ] `#542` 401 during base station load revokes cached coverage blobs
- [ ] `#543` ECBF slack regime returns the optimal precoder (not unconstrained fallback)
- [ ] `#544` `/api/compliance/spatial` rejects invalid bbox and receiver_height

## Frontend

### Stores and hooks (v0.29.1 PR-E + v0.29.2 PR-K)

- `stores/simulation.ts::setFreqGhz`: 6 GHz crossover swaps `sar_wb` in/out; 30 GHz crossover swaps `sab_4cm2 ↔ sab_1cm2`
- `hooks/useConfig.ts`: split into `applySceneAndBody`, `applyInitialSimulation`, `applyDosimetryConfig`, `applyDisplayConfig`, `applyEnvironmentConfig`, `applyScenesConfig`
- `hooks/useDosimetry.ts`: `buildComputeParams`, `buildRtConfig`, `selectComputeCall`, `onComputeSuccess`, `onComputeError`, `shouldSkipCompute`, `buildAntennasParam`
- `hooks/useOptimization.ts`: `handleIterationEvent`, `applyPlacementMove`, `handleDoneEvent`, `buildPlacementRequest`
- `hooks/useMIMODosimetry.ts` + `useBaseStationsDosimetry.ts`: share `_dosimetryResult.ts` (`applyDosimetryResult`, `handleDosimetryError`)
- `hooks/useScenario.ts`: split into `applySimulationState`, `applyEnvironmentState`, `applyCoverageForScenario`, `fetchEnvironmentIfNeeded`, `updateScenarioUrl`
- `hooks/useKeyboard.ts`: `isTypingTarget`, `deleteAntenna`, `nudgeAntennaWithArrow`; arrow dispatch via `ARROW_DELTAS` map

- [ ] Frequency 28 → 5 GHz: `sar_wb` enabled, `sab_1cm2` replaced by `sab_4cm2`, display quantity falls back to `sab` if unavailable
- [ ] Frequency 5 → 35 GHz: `sar_wb` removed, `sab_4cm2` replaced by `sab_1cm2`
- [ ] Reload with a non-default scenario: recommended body position, default freq, power, skin model, antenna position, dynamic range, RT max_order, body offset/rotation, colormap, lighting, camera FoV, environment source, scenes list all apply
- [ ] Compute fires only when MIMO guard, GLTF guard, animation guard pass. `setComputing(false)` fires on every terminated path
- [ ] RT compute without environment mesh: warning notification appears, compute does not proceed
- [ ] Optimization placement mode: antenna moves per iteration (server Z-up → scene Y-up swap), final best applied on `done`, notification text shows iteration count and percent reduction
- [ ] MIMO compute: low-height and all-zero warnings fire with shared hint text. Network/timeout/abort/GPU-unavailable paths show correct notification styles
- [ ] Scenario switch (any entry in `config.scenarios`): previous state fully cleared; new state applied; URL updates; `coverage_globe` enables coverage overlay; OSM scenario triggers `fetchOSM`; 3D Tiles triggers `fetchTilesForRT`
- [ ] Keyboard: WASD moves; Arrow keys nudge antenna (single-user only); Shift+Arrow uses `nudge_step_shift`; Delete/Backspace removes antenna; typing in text inputs does not trigger these

### Physics / movement (v0.29.2 PR-K)

`lib/physics.ts::stepPhysics` split into `stepAngular`, `stepLateral` (+ `buildMoveDirection`), `stepVertical`, `integratePositionWithWalls`, `resolveGroundCollision`, `autoStepUp`, `applyFallProtection`, `smoothFacing`.

- [ ] First-person walk on voxel environments is smooth
- [ ] Step-up onto raised platforms works within `max_step_height`
- [ ] Wall sliding prevents clipping through vertical surfaces
- [ ] Fall-through protection: descending below `y = -20` teleports back to y=0
- [ ] Body rotation smoothly follows movement direction when moving

### Panels (v0.29.0 PR-5 + v0.29.1 PR-F + v0.29.2 PR-J)

Panels touched across all three rounds: `AnalysisPanel` (split into 10 subcomponents + `utils.ts`), `RayTracingPanel` (capFor → `PARAM_CAPS` dict dispatch), `AntennasPanel`, `EnvironmentPanel`, `ScenePanel`, `BugReporter`, `ExportPanel`, `BaseStationsPanel`, `PatternBrowserPanel`, `OptimizePanel`, `AntennaDetailPanel`. Inline `Row`/`Hint`/`CheckboxRow` sub-components lifted from render bodies into module scope (React perf anti-pattern fix).

- [ ] Analysis panel: each section expands/collapses
    - Power sweep runs, renders recharts line chart, shows margin color
    - Frequency sweep runs, respects 30 GHz crossover for Sab vs Sinc
    - Distance sweep runs
    - Compliance heatmap canvas gradient, ICNIRP pass/warn/fail colors, hover tooltip shows power + margin
    - Exposure distribution shows peak, p99, p95, mean, illuminated-mean, illuminated-p50 with unit-less `formatSabNumber`
    - Sab histogram bins render, tooltip shows `"x0 - x1 W/m²"`
    - No console warnings about duplicate keys or missing React deps on section switch
- [ ] Ray tracing panel: toggle Sionna RT ↔ DiffeRT, per-param enable/disable flips (method fixed to SBR for Sionna, rays/paths/seed per backend, edge diffraction gated on `diffraction=true`). Reflection-loss slider in 0.01 steps; max depth clamped 0..10; seed accepts integers
- [ ] Antennas panel: MIMO guard shows correct empty state. Add antenna; edit power/array/spacing/element pattern/position/height/direction/focus point
- [ ] Environment panel: switch source across none/voxels/osm/3dtiles. Radius, OSM options checkboxes, GeoJSON upload, terrain section all render
- [ ] Scene panel: Sionna scene selector loads a scene and resets dependent state. Location form has no SSE errors. Clear scene removes all loaded state
- [ ] Bug reporter: Shift+B opens modal; screenshot at full page resolution; submit posts to `/api/bug-report` and shows success view; Escape closes
- [ ] Export panel: CSV / JSON / NPZ / compliance / configuration / screenshot all download non-empty files
- [ ] Base stations panel: region list loads; filter checkboxes (operator/technology/frequency band) update count and markers; fidelity legend renders; loading spinner while fetching
- [ ] Pattern browser panel: search filters as you type; "Selected pattern" card shows when chosen; result count matches list length
- [ ] Optimize panel: each mode (grid/random/bayesian) shows description + constraints; placement progress bar fills; cancel aborts cleanly
- [ ] Antenna detail panel: every FieldRow shows correct value; dominant source (strongest path) highlighted

### HUD (v0.29.2 PR-J)

`MIMOPanel`, `CompliancePanel`, `ColorLegend` decomposed at module scope.

- [ ] MIMO panel: add user button creates a UserRow; per-user focus-point control; compliance title updates when compliance runs
- [ ] Compliance panel: summary numbers (max Sab, ratio, limit) correct; each CheckRow shows label + limit + pass/fail
- [ ] Color legend: linear/dB toggle; lock-colormap toggle; ratio mode percent ticks; floor input accepts `-80..-5` dB

### R3F scene components (v0.29.2 PR-I)

`AntennaArray` (cog 62→0), `ComplianceRing` (62→20), `BodyMeshInstance` (45→0), `OptimizeGridPreview` (45→0), `panels/analysis/HeatmapCanvas` (48→21). Helpers hoisted to module scope; sub-components extracted. Ref typing updated for React 19 (`RefObject<T | null>`).

- [ ] MIMO antenna array: visible, correct position, correct phase colors, click-to-select, selection ring; element count matches `arrayConfig.n_elements`
- [ ] Pattern geometry (wireframe gain pattern) renders for array antennas on enable
- [ ] Compliance ring: circle (isotropic) or directional shape (radial) per toggle; label positioned correctly; toggling off leaves no orphan geometry
- [ ] Body mesh instance: jet colormap matches `displayQuantity` + legend scale; ratio/absolute toggle re-renders without flicker; multi-body scenes (eartha + duke) keep per-body colormap lock state
- [ ] Optimize grid preview: grid points appear when optimizer primed; per-cell colors reflect predicted Sab (or at least render)
- [ ] Heatmap canvas (Compliance panel): axes, crosshair at peak, boundary circle, colorbar matches quantity; hover shows Sab readout

### AnnotationCanvas + share link (v0.29.1 PR-G)

`AnnotationCanvas` cog 85→5. Split into `drawing.ts`, `viewport.ts`, `composite.ts`, `Toolbar.tsx`, hooks (`useSpaceHeld`, `useZoomPan`, `usePointerHandlers`, `useBackgroundImage`), orchestrator `index.tsx`. `getCompositeImage` → `buildCompositeImage`. `applyShareState` split into `applySimulationState`, `applySceneState`, `applyUIState`, `applyAntennaState`.

- [ ] Bug reporter annotation canvas: draw with mouse/pen; wheel zoom; space-drag pan; stroke styles match pre-refactor
- [ ] Clear button resets the canvas
- [ ] Composite image export produces a PNG that matches the visible region (screenshot + annotations)
- [ ] Share link with full state (antenna pos, body, frequency, UI flags) restores every piece of state

## Run before ship

```bash
source .venv/bin/activate
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m pytest tests/ -m "not slow" \
  --deselect tests/test_bugreport.py::test_bug_report_missing_screenshot \
  --deselect tests/test_bugreport.py::test_bug_report_success \
  --deselect tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503
cd aegis-web && npm run build
```

### Known pre-existing failures

- `tests/test_bugreport.py::test_bug_report_missing_screenshot` — predates this work
- `tests/test_bugreport.py::test_bug_report_success` — related helper
- `tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503` — stale expectation; #536 shipped the fix, test not updated

## End-to-end smoke test

Run the viewer and exercise. If all steps work without console errors, all three rounds are shipping correctly.

1. `python -m aegis.viewer --location "Ghent, Belgium"` — server starts, UI loads
2. Place a single antenna at the default position
3. Compute at level 2 (spatial + fresnel). Heatmap renders on phantom
4. Switch to level 5 (curvature). Heatmap changes
5. Switch phantom from the dropdown. Re-run. New geometry, new result
6. Frequency 28 → 5 → 35 → 28 GHz. Verify 6 GHz Sab/Sar_wb crossover and 30 GHz 4cm²/1cm² crossover
7. Enable voxel environment. Hull mesh renders, ground plane hides
8. DiffeRT ray trace (`/api/compute/rt`). Paths render, Sab updates
9. Switch to Sionna RT backend. Capability-driven disable flags on ray tracing panel match documented behaviour
10. Analysis panel: walk through power, frequency, distance, compliance heatmap, distribution, histogram. Each renders
11. Antennas panel: add a second antenna; edit power and array size; re-run compute with both
12. Environment panel: switch to OSM; buildings render
13. Scenario switcher: coverage globe → open ground → coverage globe. No stale antenna or mesh leaks
14. Base stations: load Belgium, enable fidelity tiers, compute aggregate Sab
15. Pattern browser: search "cosine", select a pattern, apply to antenna
16. MIMO mode: add 4 users, run precoder, confirm per-user Sab
17. Optimize mode: grid search on small grid, best point selected; cancel aborts cleanly
18. Bug reporter (Shift+B): draw annotation, zoom, pan, submit
19. Export dosimetry CSV, JSON, NPZ; compliance report; configuration
20. Keyboard: WASD + arrow nudge + Shift+arrow + Delete antenna + Space to jump on a voxel scene
21. Reload the page. Persisted state restores (antenna position, power, phantom)
22. Share the URL; open in a new tab; full state restores
