# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

- [2026-04-02] code-reviewer: Focus area: geometry and mesh operations. Found and fixed 2 bugs. (1) BodyMesh.cylinder() had swapped vertex winding on both caps, causing normals to point inward instead of outward. Affected projected area, ambient occlusion, and dosimetry on cylinder meshes. (2) GltfSkeleton FK loop assumed topological joint ordering (parent index < child index), which glTF does not guarantee. Added topological sort to process parents before children. Also reviewed: averaging.py (searchsorted correct), occlusion.py (BVH + Moller-Trumbore correct), directivity.py (SH fitting correct), projected_area.py (fibonacci sphere correct), device_offset.py (face detection correct), parametric.py (SMPL-X wrapper correct). All 2319 tests pass. PR #329.

- [2026-04-02] feature-agent: Fixed 6 bugs in the new Cesium Globe integration and backend routes. (1) CoverageOverlay3D: polyline entities leaked on destroy, accumulated on every coverage reload. Now tracked and removed in destroy(). (2) CoverageOverlay3D: DistanceDisplayCondition was inverted (showed regions only when >200km away). Fixed to show within 2000km/5000km. (3) CesiumGlobe: async Google 3D Tiles load could leak tick listener on unmount race. Separated into its own effect with cancellation token. (4) CesiumGlobe: coverage overlay missed when data was pre-loaded before viewer ready. Added tryAddOverlay called from both handleViewerReady and the store subscription. (5) CoverageHud: "Back to globe" button never restored envSource to 'cesium', so Cesium globe would not reappear. (6) coverage.py: held lock during multi-second Parquet I/O, blocking all concurrent requests. Now computes outside lock, stores result under lock. Also fixed: RT routes rejected valid levels 7-8 (coherent MIMO), updated test to match. Fixed pre-existing TS build error in usePoseExtract.ts (boneTransform type). All 2279 tests pass, TS compiles clean, frontend builds.

- [2026-04-02] code-reviewer: Focus area: type safety and API contracts. Fixed coverage endpoint crash when parquet files lack Operator/Technology columns (KeyError in clusters section, guard existed for sites but not clusters). Fixed 5 TypeScript type mismatches in MIMO API types: MIMOSummary.precoder was typed as object but backend sends string, MIMOUserSummary had non-existent p_abs/margin_db fields, MIMOComputeResponse had compute_time_ms instead of timings dict, RegionSummary.bbox was non-nullable but backend can send null. Added regression test for missing-column bug. All 2238 tests pass, TypeScript compiles clean.

- [2026-04-02] feature-agent: Fixed 4 bugs across backend and frontend. (1) `averaging_matrix_to_jax` now returns JAX sparse BCOO instead of materializing a dense M*M matrix (would OOM for >10k triangles). (2) `fetchTilesForRT` in environment store was discarding the binary response body, so Google 3D Tiles geometry was never rendered. Now parses binary+X-Meta like the OSM and GeoJSON paths. (3) Added `error` state to coverage store and CoverageHud (was silently swallowing fetch errors). (4) Added try/except to coverage route `_compute_coverage` call (was returning raw HTML 500 on exception). Also fixed pre-existing test failure in `test_sab_averaged_none_falls_back_to_raw_peak` (was using SimpleNamespace without `compliance_kwargs` method). All 2189 tests pass.

- [2026-03-31] code-reviewer: Focus area: test coverage gaps and edge cases. Fixed division by zero in basestations.py bbox computation at polar latitudes (cos(90)=0). Added 265 new tests: compliance sweep functions (power_sweep, frequency_sweep, max_compliant_power), compute route parsing helpers (_parse_vec3, _parse_rotation_y, _parse_mode_or_level, _build_binary_response), basestations edge cases (polar lat, radius validation, _resolve_belgian_region). Total tests: 1905 pass. PR #209.


## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
