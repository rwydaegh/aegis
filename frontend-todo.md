# Frontend TODO - post overnight agents

Backend gained 22 features overnight. The frontend hasn't caught up. This is a comprehensive list of frontend work to surface those new capabilities, plus existing gaps.

## High priority (new backend features need a frontend)

### 1. Max compliant power display
- Backend: `max_compliant_power()` returns the exact P_max in watts
- Frontend: show P_max (dBm) in the CompliancePanel, e.g. "Max compliant power: 23.4 dBm"
- Already have the compliance result in the store, just need one more API field or client-side computation

### 2. Per-path contribution breakdown (opt-in toggle)
- Backend: `path_contributions()` in `analysis.py` ranks paths by contribution to peak exposure
- Frontend: add a toggle "Show path breakdown" in RayTracingPanel or a new AnalysisPanel
- When ON: call a new `/api/analysis/contributions` endpoint, highlight top-K paths in the 3D scene (thicker lines, color by contribution fraction), show ranked list in HUD
- When OFF: skip entirely (no speed penalty)
- Also: clicking a triangle on the body could show "which paths hit here" using `triangle_index` param

### 3. Fidelity level convergence view
- Backend: `sweep_levels()` + `DosimetryResult.compare()` run multiple levels and compute RMSE/error
- Frontend: add a "Convergence" mode or panel that shows a small table/chart comparing peak Sab across levels 2-6
- Useful for researchers to see how much the corrections matter for their scenario

### 4. Result scaling slider (power sweep)
- Backend: `DosimetryResult.scale(factor)` scales all power quantities linearly
- Frontend: add a real-time power slider that scales the displayed colormap without recomputing
- Currently changing power triggers a full recompute. With `scale()`, the frontend can just multiply the cached sab array by (new_power / ref_power) client-side
- This makes the power slider feel instant

### 5. Compliance report export
- Backend: `summary_text()` and `/api/compliance/report` exist
- Frontend: add a "Download report" button in CompliancePanel that fetches the text/JSON report

### 6. Tissue spectrum plot
- Backend: `get_tissue_spectrum()` returns vectorized tissue properties vs frequency
- Frontend: small inline chart (Recharts?) showing T0, epsilon, sigma vs frequency for the selected tissue
- Helps users understand why results change with frequency

## Medium priority (UX improvements)

### 7. Click-to-inspect triangle
- Click a triangle on the body mesh to see its local Sab, normal, area, and (if path breakdown is on) which paths contribute
- Needs raycasting in R3F (already have click-to-place for antenna)

### 8. Exposure scenario toggle in toolbar
- Currently `exposureScenario` is in the UI store but may not be prominently exposed
- Should be a clear toggle: General Public / Occupational, since it changes all ICNIRP limits

### 9. Body mesh info display
- Backend: `BodyMesh` now has `from_arrays()`, better metadata
- Frontend: show triangle count, total area, bounding box in PhantomPanel
- Useful for understanding mesh resolution

### 10. Paths serialization (save/load scenarios)
- Backend: `PropagationPaths.to_dict()`/`from_dict()` and `DosimetryResult.to_dict()`/`from_dict()` enable full round-trip serialization
- Frontend: "Save scenario" / "Load scenario" buttons that persist antenna position, body config, paths, and results to a JSON file
- Enables reproducible comparisons

### 11. LOS/NLOS path filtering
- Backend: `paths.los_paths` / `paths.nlos_paths` properties
- Frontend: toggle in RayTracingPanel to show only LOS, only NLOS, or both
- Color differently in the scene

### 12. Path concatenation UI
- Backend: `PropagationPaths.concatenate()` merges paths from multiple sources
- Frontend: allow multiple antenna sources, each with their own paths, merged for a single dosimetry computation
- This is a bigger feature (multi-antenna scenarios)

## Lower priority (nice-to-have)

### 13. Spherical path generator UI
- Backend: `from_spherical()` and `uniform_sphere()` create paths from angles or uniform sampling
- Frontend: a "synthetic paths" mode where you specify theta/phi ranges or uniform N, for testing/worst-case analysis
- Partially exists via stochastic presets

### 14. Colormap improvements
- Dynamic range is already configurable (dB scale)
- Add: colormap selector (viridis, inferno, coolwarm), colormap lock per-quantity
- Show S_inc alongside S_ab with split colormap

### 15. Ambient occlusion toggle
- Backend: Numba-accelerated AO is now fast enough for real-time use
- Frontend: toggle to enable/disable AO shading on the body mesh for better depth perception
- May already exist but worth verifying

### 16. Performance timing display
- Backend: `_last_timings` dict tracks kernel, averaging, RT times
- Frontend: the StatusBar shows compute elapsed but could show a breakdown (kernel: 12ms, averaging: 45ms, RT: 200ms)
- Helps users understand what's slow
