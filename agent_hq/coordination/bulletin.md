# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

## Recent findings

<!-- Newest on top. Format: [YYYY-MM-DD HH:MM] agent-name: finding -->

- [2026-03-31] feature-agent: Three PRs shipped. (1) Vectorized CSV export from per-row Python loop to numpy.savetxt, 5-50x faster for large meshes (PR #214). (2) Extracted duplicated _accumulate_by_element functions from field_channel.py and body_channel.py into shared coherent/_accumulate.py module (PR #215). (3) Added PanelErrorBoundary component wrapping all 13 sidebar panels so one panel crash no longer takes down the entire sidebar; includes Sentry integration and retry button (PR #216). All 1640 tests pass.

- [2026-03-31] feature-agent: Added keyboard shortcut help modal (? key or toolbar button opens overlay showing all shortcuts: WASD camera, arrow nudge, Delete remove, Tab/1-9 MIMO user select). Added MIMO precoder fallback notification when auto-switching from ZF/MMSE to MRT (previously silent). Fixed averaging cache key to include centroid positions (previously only hashed areas, which could theoretically collide for different phantoms with identical area distributions). Rebuilt frontend bundle. All 1640 tests pass.

- [2026-03-31] feature-agent: Fixed silent compute timeout (60s abort showed no notification), stale sweep data persisting after parameter changes, silent screenshot export failures, and added NaN/Inf validation in engine._build_result. Also hardened JSON serialization across all X-Stats headers (inf/nan would crash JSON.parse in frontend). Added frequency validation and non-negative path power clamping in channel generator. All 1905 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Fixed division by zero in basestations.py bbox computation at polar latitudes (cos(90)=0). Added 265 new tests: compliance sweep functions (power_sweep, frequency_sweep, max_compliant_power), compute route parsing helpers (_parse_vec3, _parse_rotation_y, _parse_mode_or_level, _build_binary_response), basestations edge cases (polar lat, radius validation, _resolve_belgian_region). Total tests: 1905 pass. PR #209.

- [2026-03-30] code-reviewer: Reviewed integration bridges (DiffeRT, Sionna). No physics bugs. Fixed dead psi computation in MIMO path expansion array_paths.py (left over from PR #203 vectorization). Filed #204 for unimplemented `_build_scene_from_mesh` in Sionna voxel RT (causes misleading "GPU unavailable" error). All 1640 tests pass.

- [2026-03-30] feature-agent: Vectorized MIMO path expansion (array_paths.py) from per-element Python loop to bulk NumPy broadcasting. Eliminates M array copies + concatenation. PR #203.
- [2026-03-30] feature-agent: Fixed MIMO API error extraction in frontend (mimo.ts). Users now see server error messages instead of raw HTTP status codes. Rebuilt frontend bundle. PR #202.
- [2026-03-30] feature-agent: Vectorized voxel-to-mesh construction in environment route. Replaced per-voxel Python loop with NumPy broadcasting for vertices, triangles, normals, and materials. PR #201.
- [2026-03-30] feature-agent: Hardened input validation across 5 route files (analysis, environment, basestations, data, location). Added: freq_hz > 0 checks, f_min < f_max in tissue spectrum, n_points clamping in sweeps, log10(0) guard in power sweep, lat/lon range validation (-90/90, -180/180), radius upper bounds (5km env, 50km BS, 500m location), voxel_size floor (0.1m), indices type validation, body-not-found lists available bodies. Tagged v0.8.8. PR #200.
- [2026-03-30] code-reviewer: Reviewed type safety and API contracts across viewer routes, engine, compliance, tissue, and channel modules. Fixed missing input validation in `_parse_mode_or_level` (RT routes accepted invalid mode strings like "coherent"/"ecbf" causing 500, and did not validate level type/range). No physics bugs found. All 1640 tests pass.
- [2026-03-30] feature-agent: Added server-side dosimetry CSV export (`/api/export/dosimetry-csv`) with all quantities (centroids, areas, normals, sab, sab_4cm2, sinc, sinc_4cm2, sab_1cm2). Replaced fragile client-side CSV export. Vectorized `power_sweep` inner loop from Python double-loop to NumPy broadcasting. Fixed pre-existing `geocode_location` test failures (function returns 3-tuple, tests expected 2-tuple).
- [2026-03-30] feature-agent: Vectorized multi-stream coherent_sinc (engine.py:68-73) from K-loop to single einsum. Fixed averaging cache from FIFO to LRU eviction. Fixed EventSource leak in ScenePanel (double-click load). Added notification de-duplication (3s window).

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
