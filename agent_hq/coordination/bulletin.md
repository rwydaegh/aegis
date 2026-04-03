# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

- [2026-04-03] code-reviewer: Focus area: kernels and physics correctness. Fixed missing T0 Fresnel transmission factor in tilt_power optimizer `_evaluate` (was overestimating S_ab by ~2.3x for skin at 28 GHz, causing overly conservative power limits). Added regression test. Also noted: tilt_power mode unreachable via /api/optimize (DosimetryResult has no `_paths` attribute, so `getattr(last_result, "_paths", None)` always returns None) -- not fixed, appears to be unfinished feature integration. All kernels (levels 0-8), coherent body channel, exposure operator, ECBF solver, spatial kernel, tissue/Fresnel, channel generator, and other optim modules reviewed with no further physics bugs found. 2319 tests pass.

- [2026-04-02] code-reviewer: Focus area: type safety and API contracts. Fixed coverage endpoint crash when parquet files lack Operator/Technology columns (KeyError in clusters section, guard existed for sites but not clusters). Fixed 5 TypeScript type mismatches in MIMO API types: MIMOSummary.precoder was typed as object but backend sends string, MIMOUserSummary had non-existent p_abs/margin_db fields, MIMOComputeResponse had compute_time_ms instead of timings dict, RegionSummary.bbox was non-nullable but backend can send null. Added regression test for missing-column bug. All 2238 tests pass, TypeScript compiles clean.

- [2026-04-02] feature-agent: Fixed 4 bugs across backend and frontend. (1) `averaging_matrix_to_jax` now returns JAX sparse BCOO instead of materializing a dense M*M matrix (would OOM for >10k triangles). (2) `fetchTilesForRT` in environment store was discarding the binary response body, so Google 3D Tiles geometry was never rendered. Now parses binary+X-Meta like the OSM and GeoJSON paths. (3) Added `error` state to coverage store and CoverageHud (was silently swallowing fetch errors). (4) Added try/except to coverage route `_compute_coverage` call (was returning raw HTML 500 on exception). Also fixed pre-existing test failure in `test_sab_averaged_none_falls_back_to_raw_peak` (was using SimpleNamespace without `compliance_kwargs` method). All 2189 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Fixed division by zero in basestations.py bbox computation at polar latitudes (cos(90)=0). Added 265 new tests: compliance sweep functions (power_sweep, frequency_sweep, max_compliant_power), compute route parsing helpers (_parse_vec3, _parse_rotation_y, _parse_mode_or_level, _build_binary_response), basestations edge cases (polar lat, radius validation, _resolve_belgian_region). Total tests: 1905 pass. PR #209.

- [2026-03-30] code-reviewer: Reviewed integration bridges (DiffeRT, Sionna). No physics bugs. Fixed dead psi computation in MIMO path expansion array_paths.py. Filed #204 for unimplemented `_build_scene_from_mesh` in Sionna voxel RT.

- [2026-03-30] feature-agent: Vectorized MIMO path expansion, voxel-to-mesh, coherent_sinc. Hardened input validation across 5 route files. PRs #200-203.

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
