# QA plan for v0.29.0 + v0.29.1

Two maintainability-only releases. v0.29.0 shipped the first five-PR cleanup (April 16 2026). v0.29.1 shipped the second seven-PR cleanup on top of that. Together these refactors touch almost every viewer route, several zustand stores, most hooks, and the majority of frontend panels. No intentional behavior change, so this checklist focuses on regressions the refactors could plausibly cause.

The sections are ordered by the PR that introduced the change. Run the smoke-test script at the end as a fast sanity check.

## Backend regression risks

### v0.29.0 PR-2 / PR-3 — route flattening and `compute.py` package

Every Flask route handler under `src/aegis/viewer/routes/` was moved from a nested closure to a module-level `_impl(cache, cache_lock)` function. `compute.py` became a package of 11 files. External `register(app, cache, cache_lock)` contract preserved.

High-risk endpoints:

- [ ] `POST /api/compute` with default config returns 200 and has `sab`, `stats`, `extra`
- [ ] `POST /api/compute` with multi-antenna payload sums `S_inc` and returns per-antenna contributions
- [ ] `POST /api/compute` with stochastic channel preset returns `cluster_viz`
- [ ] `POST /api/compute` mode-based (bound, aggregate, spatial + fresnel + curvature) returns correct level number
- [ ] `POST /api/compute` legacy level-based (levels 0, 2, 5, 6) matches expected kernel dispatch
- [ ] `POST /api/compute/rt` DiffeRT ray trace returns path count and timing
- [ ] `POST /api/compute/voxel-rt` voxel hull RT still produces the greedy-mesh quad count
- [ ] `POST /api/compute/sionna-rt` Modal GPU path hits the scene cache on the second call
- [ ] `POST /api/compute/sionna-env-rt` environment mesh RT
- [ ] `POST /api/validate/sinc` CloudRF comparison
- [ ] `GET /api/gpu/status`, `GET /api/scenes`, `POST /api/scene/load`
- [ ] `GET /api/voxels/hull-mesh` confirmation-gated lazy mesh
- [ ] `GET /api/export/dosimetry-{csv,json,npz}` work after a compute
- [ ] `GET /api/compliance/report`, `/api/channel-presets`, `POST /api/lsp-heatmap`
- [ ] One smoke call each on basestations, optimize, mimo, location, data, environment routes

### v0.29.0 PR-4 — `compute_dosimetry` decomposition

`viewer/compute.py::compute_dosimetry` split into nine small helpers (`_compute_incidence_geometry`, `_generate_stochastic_paths`, `_build_single_antenna_paths`, `_generate_multi_antenna_paths`, `_generate_single_plane_wave_paths`, `_run_engine_mode`, `_run_engine_legacy_level`, `_run_engine_compute`, `_build_compute_extras`). Return tuple and `timings` dict should be byte-identical.

- [ ] `S_inc` value matches pre-release baseline for a fixed (antenna pos, power, phantom) triple
- [ ] Distance readout matches antenna-to-body-center distance
- [ ] Timing breakdown in the status bar (body transform, engine compute, total) populated
- [ ] Fine-grained kernel timings (`kernel_ms`, `avg_build_G_4cm2_ms`, `avg_matvec_4cm2_ms`, `avg_build_G_1cm2_ms`) populated when applicable
- [ ] Zero-antenna edge case returns zero-power result without crashing
- [ ] `exposure_mode` set to `actual_max` or `typical` reduces effective power vs `theoretical`
- [ ] Curvature-enabled modes (`level >= 5`, or `corrections.curvature`) produce a different S_ab than the Fresnel-only run

### v0.29.0 PR-1 — `_greedy_mesh_faces` dedup

Old v1 greedy meshing deleted. v2 is canonical.

- [ ] Enable voxel source. Hull mesh renders without holes or overlapping quads
- [ ] `/api/voxels/hull-mesh` response has the expected triangle count for a known voxel set
- [ ] Voxel RT scene generation (`POST /api/compute/voxel-rt`) produces a reasonable Sab distribution

### v0.29.1 PR-B — `viewer/server.py` package split

The 670-line server.py became a package with `_cache`, `_fidelity`, `_auth`, `_bodies`, `_voxels`, `_precompute`, `_app` submodules. Public surface (`create_app`, `create_app_from_env`, `_cache`, `_cache_lock`, `scoped_cache_*`, `_load_and_cache_voxels_dir`, `FIDELITY_LEVELS_API`) preserved via `__init__.py`.

- [ ] `python -m aegis.viewer --location "Ghent, Belgium"` launches and registers 74 routes
- [ ] `AEGIS_GATE_PASSWORD` is set. `/api/auth` login with the right password issues a session cookie. Exempt paths (`/api/health`, `/api/auth`, `/robots.txt`, `/assets/*`, `/cesium/*`, `/`) bypass the gate
- [ ] Bodies load from `data/*.stl`. `phantoms.yaml` device_offset overrides still apply
- [ ] GLB phantoms (thelonious/duke/eartha/ella/adult_male/adult_female/boy_6y/girl_8y) shadow their STL counterparts only where a GLB is missing
- [ ] Background averaging-matrix precompute starts on the first request. `G(<body>, 4cm2)` log line appears in Flask output for each body under the triangle budget

### v0.29.1 PR-C — `routes/basestations.py` package split

Six-file package (`_geocode`, `_fidelity`, `_data`, `_load`, `_compute`, `_compute_mimo`). `_handle_basestations_load` cyclo 53 decomposed into `_geocode_if_needed` + `_build_bbox` + `_resolve_country_and_region` + an orchestrator.

- [ ] `POST /api/basestations/load` with `{"location": "Ghent, Belgium", "radius_m": 500}` returns the Flanders dataset
- [ ] `POST /api/basestations/load` with raw `{"lat": 50.85, "lon": 4.35}` resolves Brussels via reverse geocode
- [ ] `POST /api/basestations/load` with unknown country returns `{"count": 0}` gracefully
- [ ] `POST /api/basestations/load` with explicit `bbox` bypasses geocoding and loads from Parquet if present
- [ ] `POST /api/basestations/compute` still honours `exposure_mode`, `indices`, and `max_distance_m`
- [ ] `POST /api/basestations/compute_mimo` only accepts `level` 7 or 8 and only for archetype `mmimo`
- [ ] `GET /api/basestations/list` shows `fidelity_tier` field per base station (full/spatial/geometric/bound/location_only)

### v0.29.1 PR-D — backend handler decompositions

Nine route handlers broken down. Cognitive complexity drops:

- `_api_compute_impl` 61 → 4
- `_api_compute_rt_impl` 52 → 16
- `_api_compute_voxel_rt_impl` 24 → 11
- `_api_compute_sionna_rt_impl` 19 → 6
- `_api_compute_sionna_env_rt_impl` 23 → 5
- `_build_config` (optimize) 41 → 5
- `_build_placement_evaluate_fn` 24 → 10
- `_handle_export_config` (data) 35 → 2
- `_api_location_load_impl` 37 → 20
- `_build_scene` (mimo) 35 → 7
- `_user_stats` (mimo) 26 → 6

Late-import shims for `_validate_scene_path` and `_run_dosimetry` still get resolved at call time so `mock.patch` keeps working. Error messages on the mimo vec3 parse now read e.g. `"user position for 'alice' must have 3 elements, got (2,)"` instead of `"User position must have 3 elements, got (2,)"` — no tests assert on the exact string and status codes are unchanged.

- [ ] Every `/api/compute/*` endpoint returns the same response shape as pre-refactor (X-Stats header, `sab` array, `stats.peak_sab`)
- [ ] `POST /api/optimize` placement mode still streams SSE iterations with `iter`, `objective`, `sab_b64`, `done` fields
- [ ] `POST /api/optimize` tilt_power and mimo_peak modes both stream the same field set
- [ ] `GET /api/export/config` returns a deterministic JSON with all sections (dosimetry, body, antenna, raytracer, stochastic, display)
- [ ] `POST /api/location/load` streams SSE progress events and ends with `{"done": true}`
- [ ] `POST /api/geocode` with `{"query": "Brussels"}` returns lat/lon/address
- [ ] `POST /api/mimo/compute` still produces per-user SAB distributions and compliance summaries

## Frontend regression risks

### v0.29.0 PR-5 — `AnalysisPanel.tsx` folder split

The 1085-line panel was broken into 10 subcomponent files plus `utils.ts`. Each subcomponent reads from zustand directly.

- [ ] Section component expands/collapses on click
- [ ] Power sweep runs, renders recharts line chart, shows margin colour
- [ ] Frequency sweep runs, renders line chart, respects the 30 GHz crossover for Sab vs Sinc
- [ ] Distance sweep runs, renders line chart
- [ ] Compliance heatmap canvas renders gradient, ICNIRP pass/warn/fail colours correct, hover tooltip shows power and margin
- [ ] Exposure distribution section shows peak, p99, p95, mean, illuminated-mean, illuminated-p50 with the renamed `formatSabNumber` helper (unit-less)
- [ ] Sab histogram bins render, hover tooltip shows `"x0 - x1 W/m²"` with the library `W/m²` suffix applied at the tooltip level
- [ ] No console warnings about duplicate keys or missing React deps when switching sections

### v0.29.1 PR-E — frontend store and hook decompositions

`setFreqGhz` cog 45 → 10. Split into `applyFreq6GhzCrossover` and `applyFreq30GhzCrossover`. The 6 GHz boundary swaps `sar_wb` in/out of the enabled quantities. The 30 GHz boundary swaps `sab_4cm2` ↔ `sab_1cm2`. Covered by both directions of the crossover.

`useConfig` useEffect cog 76 → 3. Split into `applySceneAndBody`, `applyInitialSimulation`, `applyDosimetryConfig`, `applyDisplayConfig`, `applyEnvironmentConfig`, `applyScenesConfig`.

`useDosimetry` `triggerCompute` cog 73. Extracted `buildComputeParams`, `buildRtConfig`, `selectComputeCall`, `onComputeSuccess`, `onComputeError`, `shouldSkipCompute`, `buildAntennasParam` at module scope.

`useOptimization` `start` cog 53 → 24. Extracted `handleIterationEvent`, `applyPlacementMove`, `handleDoneEvent`, `buildPlacementRequest`.

`useMIMODosimetry` cog 50 → 26. `useBaseStationsDosimetry` cog 18 → 8. Shared helper `hooks/_dosimetryResult.ts` with `applyDosimetryResult` and `handleDosimetryError`. Duplication smell (mass 98) eliminated.

- [ ] Change frequency from 28 GHz to 5 GHz in the Parameters panel. Verify: `sar_wb` becomes enabled, `sab_1cm2` is replaced by `sab_4cm2`, display quantity falls back to `sab` if the previous display quantity is no longer available
- [ ] Change from 5 GHz to 35 GHz. Verify: `sar_wb` removed, `sab_4cm2` replaced by `sab_1cm2`
- [ ] Reload the page with a non-default scenario and verify the recommended body position, default frequency, power, skin model, antenna position, dynamic range, RT max_order, body offset/rotation, colormap, lighting, camera FoV, environment source, scenes list all apply correctly
- [ ] Trigger a compute. Verify the MIMO guard (if MIMO enabled), GLTF guard, and animation guard still prevent compute. Verify `setComputing(false)` fires in all terminated paths
- [ ] Start an RT compute without an environment mesh. The warning notification appears and compute does not proceed
- [ ] Start an optimization run in placement mode. Verify antenna moves per iteration (server Z-up → scene Y-up swap), final "best" position applied on `done`, notification text shows iteration count and percent reduction
- [ ] MIMO compute: the "low antenna height" and "all zero" warnings still fire with the shared hint text. Network, timeout, abort, and GPU-unavailable paths all produce the correct notification style

### v0.29.1 PR-F — panel folder splits

Seven panels refactored. `capFor` (RayTracingPanel) cog 41 → 1 via `PARAM_CAPS` dict dispatch. Inline `Row`, `Hint`, `CheckboxRow` sub-components lifted from the render body into `Rows.tsx` (React perf anti-pattern fix).

- [ ] Ray tracing panel: toggle backend between Sionna RT and DiffeRT. Per-param enable/disable flags flip correctly (method fixed to SBR for Sionna, rays/paths/seed behaviour per backend, edge diffraction gated on `diffraction=true`)
- [ ] Ray tracing panel: reflection loss slider moves in 0.01 steps. Max depth clamped to 0..10. Seed accepts integers
- [ ] Antennas panel: MIMO guard shows the correct empty state. Add antenna, edit power/array/spacing/element pattern/position/height/direction/focus point. Each section updates the store
- [ ] Environment panel: switch source across none/voxels/osm/3dtiles. Radius control, OSM options checkboxes, GeoJSON upload, terrain section all still render
- [ ] Scene panel: Sionna scene selector loads a scene and resets dependent state. Location form runs without SSE errors. Clear scene removes all loaded state
- [ ] Bug reporter: Shift+B shortcut opens the modal. Screenshot captured at full page resolution. Submit posts to `/api/bug-report` and shows the success view. Escape closes the modal
- [ ] Export panel: CSV / JSON / NPZ / compliance / configuration / screenshot all download a non-empty file. The `guardSab` helper blocks export when no SAB array is cached

### v0.29.1 PR-G — AnnotationCanvas + shareLink decomposition

`AnnotationCanvas` cog 85 → 5. Folder split into `drawing.ts`, `viewport.ts`, `composite.ts`, `Toolbar.tsx`, hooks (`useSpaceHeld`, `useZoomPan`, `usePointerHandlers`, `useBackgroundImage`), and the orchestrator `index.tsx`. `getCompositeImage` replaced by `buildCompositeImage` (cog 0).

`applyShareState` cog 49 → 0. Split into `applySimulationState`, `applySceneState`, `applyUIState`, `applyAntennaState`.

- [ ] Bug reporter annotation canvas opens. Draw strokes with mouse/pen. Zoom in (wheel), zoom out, pan while holding space. Stroke styles match pre-refactor (color, width, endcap)
- [ ] Click the "Clear" button and confirm the canvas resets
- [ ] Composite image export produces a PNG that matches the visible region (screenshot + annotations on top)
- [ ] Open a share link URL with full state (antenna pos, body, frequency, UI flags). Every piece of state applies correctly to the restored session

## Run-before-ship checks

Run these in order. Each should be green before declaring the release clean.

```bash
source .venv/bin/activate
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m pytest tests/ -m "not slow" --deselect tests/test_bugreport.py::test_bug_report_missing_screenshot --deselect tests/test_bugreport.py::test_bug_report_success --deselect tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503
cd aegis-web && npm run build
```

Known pre-existing failures (carry-over from v0.29.0, not caused by this release):

- `tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503` (expects 503, gets 501 after PR #512)
- `tests/test_bugreport.py::test_bug_report_success` (AttributeError on removed helper)
- `tests/test_bugreport.py::test_bug_report_missing_screenshot` (expects 400, gets 200)

## Smoke test script

Minimum viable path to confirm the viewer works end-to-end:

1. Launch: `python -m aegis.viewer --location "Ghent, Belgium"`
2. Open the printed URL in a browser
3. Place a single antenna at the default position
4. Run a compute at level 2 (spatial + fresnel). Verify heatmap renders on the phantom
5. Switch to level 5 (curvature). Verify heatmap changes
6. Switch to a different phantom from the dropdown. Re-run. Verify new geometry and new result
7. Change frequency from 28 GHz to 5 GHz and back. Verify the Sab/Sar_wb crossover at 6 GHz and the 4cm²/1cm² crossover at 30 GHz
8. Enable voxel environment. Confirm hull mesh renders and ground plane hides
9. Run a DiffeRT ray trace (`/api/compute/rt`). Verify paths render and Sab updates
10. Switch to Sionna RT backend. Verify the capability-driven disable flags on the ray tracing panel match the documented behaviour
11. Open the Analysis panel. Walk through every section (power, frequency, distance, compliance heatmap, distribution, histogram). Confirm each renders
12. Open the Antennas panel. Add a second antenna. Edit its power and array size. Re-run compute with both enabled
13. Open the Environment panel. Switch source to OSM. Verify buildings render
14. Run an optimization in placement mode. Verify antenna moves per iteration and final best position applies
15. Open the bug reporter (Shift+B). Draw an annotation, zoom, pan. Submit
16. Export dosimetry as CSV. Confirm download and non-empty file
17. Reload the page. Confirm persisted state restores (antenna position, power, phantom)
18. Share the URL, open in a new tab, confirm the full state restores

If all 18 steps work without console errors, both maintainability rounds are shipping correctly.
