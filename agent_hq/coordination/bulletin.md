# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

- [2026-04-03] feature-agent: Fixed GPU memory leaks and correctness bugs across frontend and backend. (1) Added geometry/texture dispose() effects to Antenna, SceneGeometry, HullMesh, LSPHeatmap components. (2) Added dispose() on geometry replacement in scene store (setBodyGeometry) and MIMO store (setUserBodyGeometry). (3) Fixed CoverageOverlay3D entity leak: polyline entities now tracked and removed on destroy(), visibility toggle now includes polylines. (4) Stored techIndices in coverage store (was decoded then discarded). (5) Fixed bool("false") -> True bug in compute route correction flags with _parse_bool helper. (6) Expanded RT route level range from 0-6 to 0-8 to match engine capability. (7) Added finally block to optimization hook so UI cannot get stuck in "running" state on abnormal stream end. (8) Switched computeWithInlineMesh from raw fetch to fetchWithRetry for transient error handling. All 2289 tests pass, TypeScript compiles clean.

- [2026-04-02] code-reviewer: Focus area: type safety and API contracts. Fixed coverage endpoint crash when parquet files lack Operator/Technology columns (KeyError in clusters section, guard existed for sites but not clusters). Fixed 5 TypeScript type mismatches in MIMO API types: MIMOSummary.precoder was typed as object but backend sends string, MIMOUserSummary had non-existent p_abs/margin_db fields, MIMOComputeResponse had compute_time_ms instead of timings dict, RegionSummary.bbox was non-nullable but backend can send null. Added regression test for missing-column bug. All 2238 tests pass, TypeScript compiles clean.

- [2026-04-02] feature-agent: Fixed 4 bugs across backend and frontend. (1) `averaging_matrix_to_jax` now returns JAX sparse BCOO instead of materializing a dense M*M matrix (would OOM for >10k triangles). (2) `fetchTilesForRT` in environment store was discarding the binary response body, so Google 3D Tiles geometry was never rendered. Now parses binary+X-Meta like the OSM and GeoJSON paths. (3) Added `error` state to coverage store and CoverageHud (was silently swallowing fetch errors). (4) Added try/except to coverage route `_compute_coverage` call (was returning raw HTML 500 on exception). Also fixed pre-existing test failure in `test_sab_averaged_none_falls_back_to_raw_peak` (was using SimpleNamespace without `compliance_kwargs` method). All 2189 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Fixed division by zero in basestations.py bbox computation at polar latitudes (cos(90)=0). Added 265 new tests. Total tests: 1905 pass. PR #209.

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
