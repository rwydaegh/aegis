# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

## Recent findings

<!-- Newest on top. Format: [YYYY-MM-DD HH:MM] agent-name: finding -->

- [2026-03-31] code-reviewer: Focus area: compliance checks and limits. Reviewed compliance/__init__.py (ICNIRP 2020 limits, evaluate_compliance, power_sweep, frequency_sweep, compliance_heatmap, link_budget_compliance), compliance/__main__.py (CLI), result.py (compliant_sab, evaluate_compliance method), viewer/routes/compute.py (_build_stats_response), viewer/routes/analysis.py (compliance API routes), and CompliancePanel.tsx frontend. Verified all ICNIRP limit values (Tables 2, 5, 6). Found 1 bug: _build_stats_response passed sab_4cm2=None to evaluate_compliance when sab_averaged was None, silently omitting the most important compliance check. Now falls back to raw sab peak (conservative), matching DosimetryResult.evaluate_compliance(). Added regression test. All 1947 tests pass. PR #234.

- [2026-03-31] feature-agent: Four improvements shipped in one PR: (1) Cached body geometry hash on BodyMesh (computed once at construction, reused by engine averaging cache) to avoid O(M) SHA256 recomputation on every compute call. (2) Added 429 (rate limit) to frontend retry set alongside 502/503/504, using existing Retry-After header parsing. (3) Fixed CompliancePanel React anti-pattern where powerDbm was read via getState() inside an IIFE during render, causing stale "Max TX power" values. Now uses proper Zustand selector for reactive updates. (4) Added binary array bounds validation in API client to prevent silent Float32Array corruption from malformed server responses. Rebuilt frontend. All 1698 tests pass.

- [2026-03-31] code-reviewer: Focus area: tissue properties and Fresnel. Thorough review of all tissue/Fresnel code: fresnel.py, cole_cole.py, dielectric.py, database.py, _base.py (fresnel_weights), level3-6 kernels, coherent/fresnel_operator.py, coherent/body_channel.py, viewer/compute.py (resolve_skin_model), and analysis.py (tissue spectrum route). Verified all equations against monograph_v2.tex (Fresnel T_s/T_p, T0, amplitude t_s/t_p, depth coupling sqrt(sigma/4alpha), G_tilde definition, Cole-Cole model). All physics correct. Found one minor issue: analysis.py hardcoded eps_0 = 8.8541878128e-12 instead of importing EPS_0 from aegis.constants. Fixed in PR #230. All 1698 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Reviewed all recently changed files (engine.py, result.py, coherent/_accumulate.py, compliance/, viewer routes, channel/generator.py). No bugs found. Added 29 tests covering: evaluate_compliance() fallback paths (sab_averaged=None, sinc_averaged=None), serialization edge cases (unknown keys, None arrays, complex eigenvalues), coherent_sinc edge cases (single path, zero precoder, multi-element), body cache key translation invariance, _build_result NaN/Inf rejection, _sanitize_for_json with NaN/Inf/nested structures, scale() with sab_1cm2_averaged, accumulate_by_element edge cases, field_channel element_index validation. All 1699 tests pass. PR #229.

- [2026-03-31] feature-agent: Four improvements shipped in one PR: (1) Thread-safe G-matrix cache in engine.py, added threading.Lock to protect the class-level OrderedDict LRU cache from concurrent Flask/precompute thread races. (2) Heatmap rendering optimization in BodyMeshInstance.tsx, replaced per-vertex setXYZ() calls with direct typed array writes (eliminates ~45K function calls for a 15K face mesh). (3) Fixed /api/system endpoint blocking 100ms per call by changing psutil.cpu_percent(interval=0.1) to interval=None (non-blocking). (4) Fixed sigma floor inconsistency in spatial kernel diffraction path (0.0 -> 1e-20, matching level6 kernel) to avoid sqrt(0) gradient issues with JAX autodiff. Rebuilt frontend. All 1670 tests pass.

- [2026-03-31] code-reviewer: Focus area: compliance checks and limits. Verified all ICNIRP 2020 limit values against monograph (all correct). Found and fixed 2 bugs: (1) DosimetryResult.compliant_sab property crashed with ValueError when freq_hz was outside ICNIRP range (e.g. 3.5 GHz sub-6 GHz), now returns None. (2) _build_stats_response in compute route skipped sinc_local compliance check when sinc_averaged was None but raw sinc existed, now falls back to raw sinc peak matching DosimetryResult.evaluate_compliance() behavior. Added 2 regression tests. All 1671 tests pass. PR #224.

- [2026-03-31] feature-agent: Fixed Sentry #217 (HTTP 502 in fetchOSM). Added `fetchWithRetry` utility to frontend API client that retries up to 2 times with exponential backoff on transient HTTP errors (502/503/504). Respects Retry-After header. Applied to all fetch calls across client.ts, mimo.ts, basestations.ts, environment store, terrain store. Also fixed inconsistent error extraction in basestations API (now reads backend JSON errors). Separately: optimized spatial averaging NumPy fallback by skipping unnecessary sqrt (squared distances give same argsort order), fixed Sidebar re-render cascade (was subscribing to entire UIStore), memoized FocusPointMarker ring geometry. Tagged v0.8.10. PRs #221, #222. All 1640 tests pass.

- [2026-03-31] code-reviewer: Focus area: error handling and input validation. Fixed 3 categories of missing validation: (1) power_dbm not validated as numeric in all 3 RT routes (DiffeRT, Sionna, voxel), (2) MIMO level param accepted incoherent levels 0-6 in mimo.py and basestations.py routes, (3) lat/lon not validated as numeric in from-voxels and geojson environment routes. Also fixed compute_sab test that failed with JAX installed (test asserted np.ndarray but function documents returning raw backend array). Added 4 new tests. All 1943 tests pass. PR #218.

- [2026-03-31] feature-agent: Three PRs shipped. (1) Vectorized CSV export from per-row Python loop to numpy.savetxt, 5-50x faster for large meshes (PR #214). (2) Extracted duplicated _accumulate_by_element functions from field_channel.py and body_channel.py into shared coherent/_accumulate.py module (PR #215). (3) Added PanelErrorBoundary component wrapping all 13 sidebar panels so one panel crash no longer takes down the entire sidebar; includes Sentry integration and retry button (PR #216). All 1640 tests pass.

- [2026-03-31] feature-agent: Added keyboard shortcut help modal (? key or toolbar button opens overlay showing all shortcuts: WASD camera, arrow nudge, Delete remove, Tab/1-9 MIMO user select). Added MIMO precoder fallback notification when auto-switching from ZF/MMSE to MRT (previously silent). Fixed averaging cache key to include centroid positions (previously only hashed areas, which could theoretically collide for different phantoms with identical area distributions). Rebuilt frontend bundle. All 1640 tests pass.

- [2026-03-31] feature-agent: Fixed silent compute timeout (60s abort showed no notification), stale sweep data persisting after parameter changes, silent screenshot export failures, and added NaN/Inf validation in engine._build_result. Also hardened JSON serialization across all X-Stats headers (inf/nan would crash JSON.parse in frontend). Added frequency validation and non-negative path power clamping in channel generator. All 1905 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Fixed division by zero in basestations.py bbox computation at polar latitudes (cos(90)=0). Added 265 new tests: compliance sweep functions (power_sweep, frequency_sweep, max_compliant_power), compute route parsing helpers (_parse_vec3, _parse_rotation_y, _parse_mode_or_level, _build_binary_response), basestations edge cases (polar lat, radius validation, _resolve_belgian_region). Total tests: 1905 pass. PR #209.

- [2026-03-30] code-reviewer: Reviewed integration bridges (DiffeRT, Sionna). No physics bugs. Fixed dead psi computation in MIMO path expansion array_paths.py (left over from PR #203 vectorization). Filed #204 for unimplemented `_build_scene_from_mesh` in Sionna voxel RT (causes misleading "GPU unavailable" error). All 1640 tests pass.

- [2026-03-30] feature-agent: Vectorized MIMO path expansion (array_paths.py) from per-element Python loop to bulk NumPy broadcasting. Eliminates M array copies + concatenation. PR #203.
- [2026-03-30] feature-agent: Fixed MIMO API error extraction in frontend (mimo.ts). Users now see server error messages instead of raw HTTP status codes. Rebuilt frontend bundle. PR #202.
- [2026-03-30] feature-agent: Vectorized voxel-to-mesh construction in environment route. Replaced per-voxel Python loop with NumPy broadcasting for vertices, triangles, normals, and materials. PR #201.
- [2026-03-30] feature-agent: Hardened input validation across 5 route files (analysis, environment, basestations, data, location). Added: freq_hz > 0 checks, f_min < f_max in tissue spectrum, n_points clamping in sweeps, log10(0) guard in power sweep, lat/lon range validation (-90/90, -180/180), radius upper bounds (5km env, 50km BS, 500m location), voxel_size floor (0.1m), indices type validation, body-not-found lists available bodies. Tagged v0.8.8. PR #200.
- [2026-03-30] feature-agent: Vectorized multi-stream coherent_sinc, fixed averaging cache (FIFO->LRU), EventSource leak, notification dedup. Added server-side CSV export, vectorized power_sweep. Fixed input validation in RT routes (_parse_mode_or_level).

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
