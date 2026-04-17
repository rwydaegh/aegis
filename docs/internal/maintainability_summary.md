# Maintainability refactor summary (v0.29.0 → v0.29.2)

Three rounds of qlty-driven tech-debt reduction shipped between 2026-04-16 and 2026-04-17. Dashboard tech-debt ratio went from >10% (grade C) → ~5.5% (grade B) and is projected to hit <5% (grade A) after Qlty Cloud re-scans v0.29.2.

The pattern for every round: (1) audit with `qlty smells` / `qlty metrics`, (2) triage by reading the code, not the score, (3) extract named helpers or split files into packages, (4) verify with tests + build + per-file qlty re-run, (5) ship one PR per logical grouping, squash-merged.

See `docs/internal/qa_maintainability.md` for the consolidated regression checklist covering all three rounds.

## Round 1 — v0.29.0 (5 PRs)

**Tag:** `v0.29.0` — 2026-04-16. **Baseline:** dashboard ratio >10% (grade C). Planning doc: `.claude/plans/plan-this-playful-swan.md`.

The first round executed the original "zoom-out" plan. Two big structural moves (route closure flattening; `compute.py` package split) accounted for most of the complexity reduction.

| PR | Title | Commit | Files |
|----|-------|--------|-------|
| 1/5 | Exclude blender-mcp, remove dead greedy-mesh v1 | [#517](https://github.com/rwydaegh/aegis/pull/517) `c1bc88e` | `.qlty/qlty.toml`, `src/aegis/viewer/raytracer.py` |
| 2/5 | Flatten route handler closures | [#521](https://github.com/rwydaegh/aegis/pull/521) `733a1ef` | all 14 `src/aegis/viewer/routes/*.py` |
| 3/5 | Split `compute.py` into package | [#523](https://github.com/rwydaegh/aegis/pull/523) `9a6cb3c` | `src/aegis/viewer/routes/compute/{__init__,_parsing,_responses,_rt_config,dosimetry,rt,voxel_rt,sionna_rt,scenes}.py` |
| 4/5 | Decompose `compute_dosimetry` | [#524](https://github.com/rwydaegh/aegis/pull/524) `37e9ece` | `src/aegis/viewer/compute.py` |
| 5/5 | Split `AnalysisPanel.tsx` into folder | [#525](https://github.com/rwydaegh/aegis/pull/525) `460147e` | `aegis-web/src/components/panels/analysis/*` (10 files) |

**Top wins:**
- `routes/compute.py::register` cog 361 → ~60 (route flattening)
- `_api_compute_impl` 1862-line file split into 11 small files
- `compute_dosimetry` cog 81 → orchestrator
- `AnalysisPanel.tsx` 1085 lines → folder of 10 subcomponents + `utils.ts`

## Round 2 — v0.29.1 (7 PRs)

**Tag:** `v0.29.1` — 2026-04-16, ~3 hours after v0.29.0. **After round 1:** 7.80% (grade B). User asked to keep going.

Planning was dynamic — audit showed the remaining hotspots were all file-level total complexity (not single-function hotspots). Plan: split more files into packages + decompose any route handlers whose cog was still >15 + refactor the big React panels and hooks.

| PR | Title | Commit | Scope |
|----|-------|--------|-------|
| A | Exclude `spinoff/` and `build_phantoms.py` from qlty | [#526](https://github.com/rwydaegh/aegis/pull/526) `9c9ff14` | `.qlty/qlty.toml` |
| B | Split `viewer/server.py` into package | [#528](https://github.com/rwydaegh/aegis/pull/528) `e376adc` | `src/aegis/viewer/server/{__init__,_cache,_fidelity,_auth,_voxels,_bodies,_precompute,_app}.py` (670-line file → 8-file package) |
| C | Split `routes/basestations.py` into package | [#529](https://github.com/rwydaegh/aegis/pull/529) `3c95f36` | `src/aegis/viewer/routes/basestations/{_geocode,_fidelity,_data,_load,_compute,_compute_mimo}.py` (839-line file → 6-file package) |
| D | Decompose backend route handlers | [#530](https://github.com/rwydaegh/aegis/pull/530) `9a77601` | 9 route handlers: `_api_compute_impl` 61→4, `_api_compute_rt_impl` 52→16, `_api_compute_voxel_rt_impl` 24→11, `_api_compute_sionna_rt_impl` 19→6, `_api_compute_sionna_env_rt_impl` 23→5, optimize `_build_config` 41→5, data `_handle_export_config` 35→2, location `_api_location_load_impl` 37→20, mimo `_build_scene` 35→7 and `_user_stats` 26→6 |
| E | Decompose frontend stores and hooks | [#531](https://github.com/rwydaegh/aegis/pull/531) `334af81` | `stores/simulation.ts::setFreqGhz` 45→10; `hooks/useConfig.ts` useEffect 76→3; `useDosimetry.ts::triggerCompute` 73 distributed; `useOptimization.ts::start` 53→24; `useMIMODosimetry.ts` 50→26; `useBaseStationsDosimetry.ts` 18→8; new shared `hooks/_dosimetryResult.ts` |
| F | Split frontend panels into folders | [#532](https://github.com/rwydaegh/aegis/pull/532) `bf0ffc5` | `RayTracingPanel` (folder split, `capFor` 41→1 via `PARAM_CAPS` dict); `AntennasPanel` 36→1; `EnvironmentPanel` 41→2; `ScenePanel` in-place extraction; `BugReporter` 29→13 + `BugReporterModal` 20→13; `ExportPanel` 48→13 (handlers hoisted to module scope) |
| G | Decompose AnnotationCanvas and shareLink | [#533](https://github.com/rwydaegh/aegis/pull/533) `18077b2` | `hud/annotationCanvas/` folder (types, drawing, viewport, composite, Toolbar, 4 custom hooks); `lib/shareLink.ts::applyShareState` 49→0 |

**Top wins:** `server.py` total cog 246 → <80 per file (package split); `basestations.py` similar; `applyShareState` 49 → 0 with clean state-application helpers; `AnnotationCanvas` 85 → 5 via hooks extraction.

## Round 3 — v0.29.2 (4 PRs + interleaved production fixes)

**Tag:** `v0.29.2` — 2026-04-17. **After round 2:** 5.52% (grade B, close to A).

Dynamic plan again. Remaining hotspots split into four independent groups small enough to parallel-dispatch: Python helpers, R3F scene components, panels + HUD, hooks + physics. Three subagents ran in parallel; final merge order was PR-J (#547), PR-I (direct commit), PR-K (#548) after PR-H (#546).

| PR | Title | Commit | Scope |
|----|-------|--------|-------|
| H | Decompose Python complexity hotspots | [#546](https://github.com/rwydaegh/aegis/pull/546) `1929c4a` | `viewer/raytracer.py::_greedy_mesh_faces` cog 85 → ~10 (split into `_mesh_direction`, `_mesh_slice`, `_best_rectangle_for_seed`, `_emit_greedy_quad`); `basestation/msi.py::parse_msi` cog 71 → ~10 (per-directive helpers `_parse_frequency`, `_parse_gain`, `_parse_tilt`, `_read_pattern_rows`); `basestation/merge.py::spatial_dedup` cog 54 → ~5 (split into `_project_to_metres`, `_bfs_cluster_labels`, `_merge_cluster_rows`) |
| I | Decompose frontend scene components | direct `2bb5d9f` (not a PR — merged directly because parallel subagent's branch was co-located) | `scene/AntennaArray.tsx` 62→0; `ComplianceRing.tsx` 62→20; `BodyMeshInstance.tsx` 45→0; `OptimizeGridPreview.tsx` 45→0; `panels/analysis/HeatmapCanvas.tsx` 48→21. React 19 `RefObject<T \| null>` typing update |
| J | Decompose frontend panels and HUD | [#547](https://github.com/rwydaegh/aegis/pull/547) `67d7c85` | `BaseStationsPanel` 31; `PatternBrowserPanel` 39; `OptimizePanel` 25; `MIMOPanel` 28; `CompliancePanel` 28; `ColorLegend` 42; `AntennaDetailPanel` 22. Extracted `FilterCheckboxGroup`, `ModeSelector`/`ModeDescription`/`ModeConstraints`/`PlacementProgress`, `UserRow`/`AddUserSection`, `CheckRow`/`ComplianceSummary`, `buildTicks`/`findRatioLimit`, `FieldRow`/`findDominantSource` |
| K | Decompose frontend hooks and physics | [#548](https://github.com/rwydaegh/aegis/pull/548) `946c7e7` | `lib/physics.ts::stepPhysics` 58 → split into `stepAngular`, `stepLateral` (+ `buildMoveDirection`), `stepVertical`, `integratePositionWithWalls`, `resolveGroundCollision`, `autoStepUp`, `applyFallProtection`, `smoothFacing`; `hooks/useScenario.ts` 42 → ~5 (`applySimulationState`, `applyEnvironmentState`, `applyCoverageForScenario`, `fetchEnvironmentIfNeeded`, `updateScenarioUrl`); `hooks/useKeyboard.ts` 40 → clean (`isTypingTarget`, `deleteAntenna`, `nudgeAntennaWithArrow`, `ARROW_DELTAS` map) |

**Interleaved production fixes** shipped between v0.29.1 and v0.29.2, folded into the v0.29.2 tag notes:

| PR | Title |
|----|-------|
| [#535](https://github.com/rwydaegh/aegis/pull/535) | Fix Belgium geocoding so locale names route correctly |
| [#536](https://github.com/rwydaegh/aegis/pull/536) | Fix stale test expecting 503 for GPU-unavailable RT (now 501) |
| [#537](https://github.com/rwydaegh/aegis/pull/537) | Fix MIMO precoder fallback, camera toggle, export errors, optimize cancel |
| [#539](https://github.com/rwydaegh/aegis/pull/539) | Clarify Fresnel correction toggle is angle-dependence, not baseline |
| [#540](https://github.com/rwydaegh/aegis/pull/540) | Remove dead CloudRF coverage map checkbox |
| [#541](https://github.com/rwydaegh/aegis/pull/541) | Harden input validation in `/api/compute` and `/api/basestations/load` |
| [#542](https://github.com/rwydaegh/aegis/pull/542) | Handle 401 and revoke coverage blobs in base station flows |
| [#543](https://github.com/rwydaegh/aegis/pull/543) | Fix dead-code ECBF slack-regime branch returning suboptimal precoder |
| [#544](https://github.com/rwydaegh/aegis/pull/544) | Validate bbox and receiver_height in `/api/compliance/spatial` |

**Top wins:** `_greedy_mesh_faces` was finally decomposed (had been flagged every round); `parse_msi` dict-dispatch and `spatial_dedup` BFS extraction cleaned two basestation hot paths; every top-10 remaining hotspot on master after v0.29.2 is genuine Tier 3 (SLAV straight-skeleton, OSM parser, roofs triangulation, engine dispatcher).

## Patterns that worked

- **Package split beats in-place refactor for large files.** `server.py` / `basestations.py` / `compute.py` each had 600-1800 lines and a single "high total complexity" smell worth 70-145 points. Splitting into `module/__init__.py` + submodules eliminated the smell entirely and dropped per-file cog below any threshold.
- **Flatten closures before splitting.** Handlers nested inside `register()` accumulated into the `register` cog number. Lifting each `_impl(cache, cache_lock)` to module scope was a mechanical rewrite that unlocked the later per-handler decompositions.
- **Hoist React sub-components to module scope.** Inline `<Row>` / `<Hint>` / `<CheckboxRow>` defined inside the render body are re-created every render (perf anti-pattern) and also get absorbed into the parent component's cog count. Lifting them into sibling files or module-scope consts fixed both issues.
- **Dict dispatch for long if/elif chains.** `capFor` in `RayTracingPanel` (PR-F), `parse_msi` directives (PR-H), arrow-key nudges in `useKeyboard` (PR-K) — each went from 40+ cog to <10 via a `Record<string, ...>` or `dict`.
- **Phase-extract for simulation loops.** `stepPhysics` (PR-K) and the RT path loops were easiest to read as `stepAngular → stepLateral → stepVertical → integrate → collide → facing` pipelines. Tuple returns worked fine; no need for dataclass parameter objects at this size.

## Patterns that didn't help

- **Chasing qlty "many returns" warnings.** These often flag valid guard-clause patterns. Rewriting to a single-return form consistently made code worse. Left alone.
- **Chasing "many parameters" warnings on numba kernels.** Numba jit forbids dataclass/kwargs wrapping; physics-kernel signatures must match the math. Left alone, already triaged in `.qlty/qlty.toml`.
- **Splitting files just because they're long.** Long files that consist of many small functions (`src/aegis/compliance/__init__.py`, `src/aegis/engine.py` for the fidelity dispatcher) stayed as single files. qlty's raw "high total complexity" score is a lagging indicator; the real question is whether a reader can find what they need.

## Tier 3 (deliberately untouched)

These stay as-is. Inherent algorithm complexity; refactoring would obscure the logic.

- `src/aegis/environment/skeleton/**` (SLAV straight-skeleton, postprocess spike/parallel-edge cleanup)
- `src/aegis/environment/osm.py`, `roofs.py`, `geojson.py`, `relations.py` — OSM/GeoJSON parsing and polygon algorithms
- `src/aegis/engine.py::compute` — 9-fidelity-level dispatcher (each branch is clear)
- `src/aegis/kernels/**` — physics kernels, numba-jit signature constraints
- `src/aegis/compliance/__init__.py` — structured dataclass catalog, LCOM=2 is correct here
- `tools/cloud.py`, `tools/blender-mcp/**` — one-off scripts, not production

## Artifacts

- Full regression checklist: [`docs/internal/qa_maintainability.md`](qa_maintainability.md)
- Round-1 plan (historical): `.claude/plans/plan-this-playful-swan.md`
- Release tag notes: `git show v0.29.0`, `git show v0.29.1`, `git show v0.29.2`
- Qlty config: `.qlty/qlty.toml`
- `/maintainability` skill: `.claude/skills/maintainability/SKILL.md`
