# QA plan for v0.29.2

Maintainability release on top of v0.29.1. Four refactor PRs (H, I, J, K) plus the production bug fixes shipped between tags (#535 through #544). No intentional behavior change from the refactors, so this plan focuses on regressions the extractions could plausibly cause and on verifying the interleaved bug fixes still hold.

Run the smoke-test script at the end before shipping. Bulk non-UI checks should pass `python -m pytest tests/` in CI; this plan exists for the UI paths and subtle contract changes that the suite does not cover.

## Backend regression risks

### PR-H — Python complexity hotspot decomposition

Three module-local refactors. External signatures unchanged, but voxel hull meshing and base station dedup are both hot paths that touch compute flows.

`src/aegis/viewer/raytracer.py::_greedy_mesh_faces` split into `_mesh_direction`, `_mesh_slice`, `_best_rectangle_for_seed`, `_emit_greedy_quad`.

- [ ] Enable voxel source, compute voxel-hull mesh. Triangle count, quad count, and orientation match the pre-PR-H baseline.
- [ ] Bridge-like voxel scenes (vertically-stacked materials) still emit correct per-face normals and no holes.
- [ ] `POST /api/compute/voxel-rt` completes and the response has plausible `sab` values.
- [ ] Greedy-rectangle picker still prefers squarer quads over u-biased strips (visual check on a mixed-material cube).

`src/aegis/basestation/msi.py::parse_msi` split into `_parse_frequency`, `_parse_gain`, `_parse_tilt`, `_read_pattern_rows`.

- [ ] Load `data/basestation/patterns/*.msi` and confirm every pattern's `gain_dbi`, `frequency_mhz`, `tilt_deg` match the prior parse.
- [ ] Test files with range notation (e.g. `FREQUENCY 1.88-1.93`): resulting frequency is the midpoint.
- [ ] Pattern with `GAIN 12.86 dBd` still converts to 15.01 dBi (+2.15).
- [ ] MSI files using `zenith` convention still detect correctly (`v_atten[0] != 0`).

`src/aegis/basestation/merge.py::spatial_dedup` split into `_project_to_metres`, `_bfs_cluster_labels`, `_merge_cluster_rows`.

- [ ] Belgium full dataset merges to the same cluster count as pre-PR-H.
- [ ] Cross-operator towers within 50 m stay separate.
- [ ] Same-operator, same-frequency-band towers within 50 m merge into one row.
- [ ] NaN fields still fill from later rows in the cluster.

### Interleaved fixes since v0.29.1 (#535-#544)

These shipped between tags. Verify they still hold after the refactors.

- [ ] `#535` Belgium geocoding: type "Ghent" / "Bruges" / "Antwerp" into the location search, correct region data loads.
- [ ] `#536` GPU-unavailable RT now returns 501 (not 503). `POST /api/compute/sionna-rt` in an env without the Modal token returns 501.
- [ ] `#537` MIMO precoder fallback, camera toggle, export errors, optimize cancel — run through the MIMO flow end to end and confirm nothing crashes the UI.
- [ ] `#539` Fresnel correction checkbox is labeled as angle-dependence (not baseline Fresnel).
- [ ] `#540` No dead CloudRF coverage checkbox in the Environment panel.
- [ ] `#541` Malformed `/api/compute` payloads (bad array shapes, wrong types) return 4xx with useful messages.
- [ ] `#542` On a 401 during base station load, cached coverage blobs are revoked.
- [ ] `#543` ECBF slack-regime now returns the optimal precoder (not the unconstrained fallback).
- [ ] `#544` `/api/compliance/spatial` rejects invalid bbox and receiver_height.

## Frontend regression risks

### PR-I — Scene component decomposition

Five files refactored. Helpers hoisted to module scope; inner components extracted. Ref typing updated for React 19 (`RefObject<T | null>`).

`components/scene/AntennaArray.tsx` (cog 62 → clean), `ComplianceRing.tsx` (62 → 20), `BodyMeshInstance.tsx` (45 → clean), `OptimizeGridPreview.tsx` (45 → clean), `panels/analysis/HeatmapCanvas.tsx` (48 → 21).

- [ ] MIMO antenna array: visible, correct position, correct phase colors, click-to-select works, selection ring visible. Element count matches `arrayConfig.n_elements`.
- [ ] Pattern geometry (wireframe gain pattern) renders correctly for an array antenna on enable.
- [ ] Compliance ring: renders as a circle (isotropic) or directional shape (radial) depending on toggle. Compliance label positioned correctly. Toggling the ring on and off leaves no orphan geometry.
- [ ] Body mesh instance: jet colormap matches `displayQuantity` and legend scale. Ratio/absolute toggle re-renders without flicker. Multi-body scenes (eartha + duke) keep per-body colormap lock state.
- [ ] Optimize grid preview: grid points appear when the optimizer is primed. Grid colors reflect per-cell predicted Sab (or at least render).
- [ ] Heatmap canvas (Compliance panel): axes drawn, crosshair at peak position, compliance boundary circle drawn, colorbar matches selected quantity. Mouse hover shows the Sab readout at that cell.

### PR-J — Panels + HUD decomposition

Seven files. Extracted sub-components at module scope so they are not re-created each render.

`components/panels/BaseStationsPanel.tsx` (cog 31), `PatternBrowserPanel.tsx` (39), `OptimizePanel.tsx` (25), `hud/MIMOPanel.tsx` (28), `CompliancePanel.tsx` (28), `ColorLegend.tsx` (42), `panels/AntennaDetailPanel.tsx` (22).

- [ ] BaseStationsPanel: region list loads, filter checkboxes (operator, technology, frequency band) update results count and map markers. Fidelity legend renders. Loading spinner appears while fetch is pending.
- [ ] PatternBrowserPanel: search box filters results as you type. "Selected pattern" card shows when a pattern is chosen. Result count text matches the list length.
- [ ] OptimizePanel: each mode (grid, random, bayesian) shows its description and constraints. Placement progress bar fills during optimization. Cancel button aborts cleanly.
- [ ] MIMOPanel: add user button creates a UserRow. Per-user focus-point control works. Compliance title updates when compliance runs.
- [ ] CompliancePanel: summary numbers (max Sab, ratio, limit) correct. Each CheckRow shows label + limit + pass/fail.
- [ ] ColorLegend: linear/dB toggle works. Lock colormap toggle works. Ratio mode percent ticks. Floor input accepts -80..-5 dB.
- [ ] AntennaDetailPanel: every FieldRow shows correct value. Dominant source (strongest path) highlighted.

### PR-K — Hooks + physics decomposition

Three files. Pure helpers extracted; behavior preserved.

`hooks/useScenario.ts` (cog 42 → ~5), `hooks/useKeyboard.ts` (cog 40 → clean), `lib/physics.ts::stepPhysics` (cog 58 → clean).

- [ ] Load each scenario (`coverage_globe`, `open_ground`, `mimo_demo`, any others in `config.scenarios`). Previous scenario state is fully cleared. New state (freq, power, mode, antenna, env source, location) is applied. URL updates.
- [ ] Coverage globe scenario fetches coverage data and renders the overlay. Switching away disables the overlay.
- [ ] OSM scenario triggers fetchOSM and shows loading spinner. 3D Tiles scenario triggers fetchTilesForRT.
- [ ] Keyboard: WASD movement works. Arrow keys nudge antenna in single-antenna mode. Delete/Backspace removes the antenna. Shift+Arrow uses the larger nudge step. Typing in a text input does not trigger keyboard controls.
- [ ] Physics: first-person walk works on voxel environments. Step-up onto raised platforms. Wall sliding prevents clipping. Fall-through protection teleports back when descending below y=-20. Smooth body facing when moving.

## Run before ship

```bash
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m pytest tests/ -m "not slow" --deselect tests/test_bugreport.py::test_bug_report_missing_screenshot --deselect tests/test_bugreport.py::test_bug_report_success --deselect tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503
cd aegis-web && npm run build
```

### Known pre-existing failures

Same list as v0.29.1 QA:

- `tests/test_bugreport.py::test_bug_report_missing_screenshot` — screenshot-missing path predates this work.
- `tests/test_bugreport.py::test_bug_report_success` — related helper.
- `tests/viewer/test_compute_routes.py::TestComputeSionnaRtRoute::test_gpu_unavailable_returns_503` — stale expectation; #536 shipped the fix but the test was not updated.

## End-to-end smoke test

Run the viewer locally and exercise:

1. `python -m aegis.viewer --location "Ghent, Belgium"` -> server starts, UI loads.
2. Default scenario computes dosimetry on the first antenna click. Sab heatmap renders.
3. Frequency sweep in Analysis panel completes for 6, 28, 60 GHz.
4. Power sweep completes; margin chart renders.
5. Distance sweep completes.
6. Compliance panel shows pass/fail for 4 cm^2, 1 cm^2, and whole-body checks.
7. Compliance heatmap (Analysis -> compliance heatmap): scan across the body, max highlighted.
8. MIMO mode: add 4 users, run precoder, confirm Sab per user.
9. Optimize mode: run grid search on a small grid, confirm the best point is selected.
10. Scenario switch: coverage globe -> open ground -> coverage globe again. No stale antenna or mesh leaks.
11. Base stations: load Belgium, enable fidelity tiers, compute aggregate Sab.
12. Pattern browser: search "cosine", select a pattern, save it, apply it to the antenna.
13. Ray tracing: enable DiffeRT, compute paths, toggle path visualization.
14. Sionna voxel RT on a voxel scene (if Modal is configured).
15. Share link: copy link, open in incognito, state restores.
16. Keyboard: WASD + arrow nudge + shift-nudge + delete antenna + space to jump on a voxel scene.
17. Annotation canvas (bug reporter): open modal, draw on the screenshot, submit.
18. Export dosimetry CSV, JSON, NPZ; compliance report.
