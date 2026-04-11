# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.


- [2026-04-07] feature-agent: Performance improvements and bug fixes. (1) Replaced `np.add.at` scatter-add in coherent `_accumulate.py` with element-loop + boolean masking (np.add.at is unbuffered and 5-10x slower). (2) Cached `bounding_box` property on `BodyMesh` (was recomputed on every access to `.center`, `.height`, `.scale`). (3) Level 5 curvature kernel: replaced full (M,N) `mu_plus**2` materialization with `xp.einsum` (matches spatial.py approach, avoids ~160MB intermediate for typical sizes). (4) Parallelized ambient occlusion outer loop using ThreadPoolExecutor (Numba releases GIL, so ray-firing runs truly parallel across cores). Also vectorized tangent frame construction and direction rotation for all triangles at once. (5) Fixed NaN propagation bug in OptimizePanel.tsx: `parseFloat("")` on cleared number inputs was sending NaN to backend API. All 2294 tests pass, TypeScript compiles clean.

- [2026-04-07] feature-agent: Fixed sinc_wb quantity mismatch and mmWave compliance analysis bugs. (1) Backend used `sinc_averaged` as the quantity key but frontend sends `sinc_wb`, so whole-body sinc data was never transmitted in compute responses. Aligned all keys to `sinc_wb` (quantity_map, peaks, array lookups). (2) Added `sinc_wb` to BodyMeshInstance, PeakIndicator, and ColorLegend array/limit maps so sinc_wb can be rendered on the mesh and shown in ratio mode. (3) Power sweep, frequency sweep, and compliance heatmap endpoints required `sab_4cm2` even above 30 GHz where only `sab_1cm2` is available. Relaxed validation to accept any of sab_4cm2/sab_1cm2/sar_wb, and passed sab_1cm2 through to heatmap. (4) `fetchHullMesh` was missing 401 handling unlike all other fetch calls, so session expiry during hull mesh load would throw a generic error instead of redirecting to login. All 2295 backend tests pass, 75 frontend tests pass, TypeScript compiles clean, frontend builds.

- [2026-04-11] code-reviewer: Focus area: integration bridges (DiffeRT, Sionna, CloudRF). Deep review of paths_from_differt (FSPL amplitude, last-segment k_hat, phase application, degenerate path filtering, polarisation tracking through reflections), paths_from_sionna_scene (NumPy and JAX paths, channel coefficient to psi conversion, LOS detection, synthetic array tiling), _extract_path_viz (sources/targets transpose), CloudRF client (antenna pattern conversion, coverage API), cloudrf_templates (preset generator), environment export (to_differt_scene, to_sionna_xml, to_binary). Also reviewed recently changed files: HudToggle, HudOverlay, ui store (hiddenWidgets), PanelAntenna, AntennasPanel NumInput. No bugs found. Physics are correct: amplitude = sqrt(2*Z_0*P_tx/(4*pi))/d matches isotropic spreading, propagation phase exp(-jk0*d_total) correctly factored out of per-segment application, Fresnel TE/TM decomposition and reflection properly updates both psi and k direction through bounces, Sionna psi = sqrt(8*pi*Z_0*P_T)/lambda * (a_theta*e_theta + a_phi*e_phi) matches derivation from CIR to E-field. All 1833 tests pass, lint clean.

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
