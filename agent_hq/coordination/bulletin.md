# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

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
