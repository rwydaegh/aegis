# Complexity refactor design

**Date:** 2026-03-20
**Goal:** Reduce cognitive complexity across 6 files from ~460 to ~120 without changing behavior.
**Strategy:** Extract heavy logic from large functions into focused helpers. No class hierarchies, no rewrites, no behavior changes.

## Scope

| File | Current complexity | Target | Priority |
|------|--------------------|--------|----------|
| `src/aegis/viewer/server.py` | 151 | < 30 | 1 (highest) |
| `src/aegis/integration/differt.py` | 101 | < 25 | 2 |
| `src/aegis/viewer/scene_data.py` | 61 | < 20 | 3 |
| `src/aegis/viewer/__main__.py` | 56 | < 20 | 4 |
| `src/aegis/geometry/occlusion.py` | 57 | < 25 | 5 (light touch) |
| `src/aegis/viz/dashboard.py` | 28 | < 15 | 6 (quick win) |

## Out of scope

- Performance optimization
- New features or API changes
- Class hierarchies or design pattern introductions
- Heavy refactoring of `occlusion.py` ray math (performance-critical NumPy)
- New unit tests for extracted helpers (deferred, not part of this refactor)

## Validation

Every refactored file must pass:
1. `py -3.12 -m pytest tests/ -m "not slow" -x` (all fast tests green)
2. `py -3.12 -m ruff check src/ tests/` (no lint regressions)
3. `qlty check --all --filter radarlint-python --level high` (complexity under target)
4. Manual smoke test of viewer if server.py changes are involved

---

## 1. server.py (151 -> < 30)

### Problem

`create_app()` is a ~700-line factory function containing 16 Flask route handlers as nested functions. Three route handlers contain the bulk of the complexity:

- `api_compute_voxel_rt()` -- 192 lines, reflection-order iteration, body rotation, path construction
- `api_compute_rt()` -- 99 lines, DiffeRT scene computation, dosimetry engine execution
- `api_location_load()` -- 71 lines, SSE streaming, cache checking, pipeline orchestration

The shared state is a module-level `_cache` dict protected by `_cache_lock` (a `threading.RLock`). Three helper functions (`_load_grid_coords`, `_load_and_cache_voxels_single`, `_load_and_cache_voxels_dir`) already live outside `create_app()` and mutate `_cache` directly.

### Design

**Step 1: Create `src/aegis/viewer/routes/` package with three modules:**

- `routes/compute.py` -- dosimetry computation handlers (simple, RT, voxel-RT)
- `routes/data.py` -- static data serving (body, voxels, tiles, config)
- `routes/location.py` -- geographic pipeline (location load, cancel)

Each module exports a function `register(app, cache, cache_lock)` that attaches routes to the Flask app. The module-level `_cache` dict and `_cache_lock` are passed directly (matching the existing pattern), not wrapped in a closure.

**Thread safety note:** Any route that mutates `cache` must acquire `cache_lock` first. Read-only access to immutable cache values (body mesh, config) does not require the lock. This matches the existing protocol in `create_app()`.

**Lazy import note:** The current route handlers use lazy imports (e.g., `from aegis.viewer.raytracer import compute_paths_differt` inside the handler body). Route modules must preserve this pattern to avoid circular imports at module load time.

**Step 2: Extract compute logic into standalone functions.**

The three heavy route handlers become thin wrappers that:
1. Parse request parameters
2. Call a standalone compute function with explicit arguments
3. Return the response

The standalone functions take explicit parameters (no Flask `request` object, no cache access).

**Step 3: Slim down `server.py`.**

`create_app()` becomes:
1. Load config and data into `_cache` (~80 lines, unchanged)
2. Call `routes.compute.register(app, _cache, _cache_lock)`
3. Call `routes.data.register(app, _cache, _cache_lock)`
4. Call `routes.location.register(app, _cache, _cache_lock)`
5. Return app

The three existing module-level helpers (`_load_grid_coords`, etc.) stay in `server.py` since they operate on the module-level cache.

**Estimated complexity after:** server.py ~15, compute.py ~20-25, data.py ~10, location.py ~10.

### Key function extractions in compute.py

`_do_compute_voxel_rt(cache, params)` -- extracted from `api_compute_voxel_rt()`:
- Takes a params dict (antenna position, frequency, power, bounces, body rotation)
- Returns (sab_bytes, stats_dict) tuple
- Internal helpers:
  - Body rotation must reuse `viewer/compute.py::_transform_body_for_viewer()` rather than duplicating rotation logic (the current code at server.py lines 548-558 does the same thing as `_transform_body_for_viewer`)
  - `_collect_rt_paths(scene, tx_pos, rx_pos, freq, bounces)` -- DiffeRT path collection with the broad try/except boundary preserved
  - `_build_stats_response(result, body, tissue, level, extra)` -- shared helper for building the X-Stats JSON, used by both RT routes

`_do_compute_rt(cache, params)` -- extracted from `api_compute_rt()`:
- Similar structure, simpler (no body rotation, no voxel scene)
- Shares `_build_stats_response` with voxel-RT

`api_compute()` -- already delegates to `viewer/compute.py::compute_dosimetry()`. Minimal change needed, just relocation.

`_zero_paths_response(body, tissue, level)` -- shared helper for the duplicated zero-paths-found response pattern in both `api_compute_rt` and `api_compute_voxel_rt`.

---

## 2. differt.py (101 -> < 25)

### Problem

Two functions concentrate the complexity:
- `_track_polarisation()` (135 LOC) -- triple-nested loop doing EM field evolution through reflections
- `paths_from_differt_scene()` (147 LOC) -- double-nested loop orchestrating DiffeRT calls

### Design

**Extract from `_track_polarisation()`:**

- `_initial_polarisation_vector(k_hat, pol_type)` -- compute initial psi from propagation direction and polarization model (vertical/horizontal). ~15 lines, eliminates a branching block.
- `_reflect_at_surface(psi_in, k_in, k_out, surface_normal, n_tilde)` -- single-reflection Fresnel transform. Takes incident field, geometry, material; returns `(psi_out, k_out)` tuple. Must return both reflected psi and outgoing propagation direction, since the caller needs to update `k` for the next iteration. ~40 lines.
- `_decompose_te_tm(k_hat, normal)` -- compute TE/TM basis vectors from propagation direction and surface normal, handling degenerate cases. ~20 lines.

The main `_track_polarisation()` loop becomes: for each path, set initial psi, then for each bounce call `_reflect_at_surface()`. ~30 lines instead of 135.

**Extract from `paths_from_differt_scene()`:**

- `_compute_element_paths(scene, tx_pos, rx_pos, freq, max_bounces)` -- compute paths for a single TX element across all bounce orders. Returns (vertices, object_indices, amplitudes). ~50 lines. Preserves the try/except/continue pattern for failed bounce orders.
- `_pad_and_concatenate(path_arrays)` -- normalize variable-length path arrays into a single padded array. ~15 lines.

The main function becomes: load scene, loop over TX elements calling `_compute_element_paths()`, concatenate, call `paths_from_differt()`. ~40 lines.

---

## 3. scene_data.py (61 -> < 20)

### Problem

Material classification has 10+ nested conditionals on HSV thresholds. Voxel loading threads a 4-tuple through 5 pipeline stages. Coordinate transforms have parallel ECEF/local paths.

### Design

**Extract `classify_material()` branching:**

Convert the HSV threshold rules to a data-driven lookup table: an ordered list of dicts with h/s/v ranges and material names. The first match wins (preserving the current early-return semantics). This eliminates most branches. The table is derived from the existing config dict.

**Keep the existing 4-tuple pattern for pipeline stages.** The VoxelData namedtuple adds migration cost across 4 function signatures with minimal complexity reduction. The private functions (`_parse_voxel_json`, `_deduplicate`, `_crop_to_bbox`, `_apply_filters`) already have clear signatures. No change here.

**Extract coordinate transform:**

- `_ecef_to_local(positions, lon, lat)` -- ECEF path
- `_yup_to_zup(positions)` -- local Y-up path
- Called from a single `_transform_to_local(data, config)` dispatcher

---

## 4. __main__.py (56 -> < 20)

### Problem

`main()` is ~100 lines mixing argument parsing, config resolution (3 override levels), subprocess management, and server launch.

### Design

**Extract config resolution:**

- `_resolve_config(args)` -- takes parsed argparse namespace, loads config JSON, applies scenario overrides, applies CLI overrides. Returns final config dict. ~40 lines.

Note: the `.env` loading at module level (dotenv) must stay at module level since it has side effects on `os.environ` before argument parsing.

**Existing helpers stay unchanged:**
- `_fetch_location(location, radius, cache_dir)` -- already extracted, minor cleanup only.
- `_kill_previous_on_port(port)` -- already extracted, no change.

`main()` becomes: parse args, resolve config, optionally fetch location, kill old server, create app, open browser, run. ~25 lines.

---

## 5. occlusion.py (57 -> < 25, light touch)

### Problem

Ray intersection functions have 12-19 parameters each. BVH uses 6 parallel arrays. The math itself is correct and performance-sensitive.

### Design

**Minimal changes only:**

- Extract `_precompute_triangle_data(vertices)` from `compute_ambient_occlusion()` inner setup. Returns a dict with keys (v0, edge1, edge2, centroids, normals, bmin, bmax). Using a dict (not a dataclass) to bundle the arrays without adding call overhead.
- Extract `_sample_and_test(origin, normal, tri_data, bvh_data, n_rays, rng)` -- the inner sampling loop. Receives the `tri_data` dict from above. ~30 lines.

**Do not touch** `_ray_aabb_hit`, `_ray_triangle_hit`, or `ray_mesh_any_hit`. These are hot-path NumPy with carefully tuned parameter passing.

---

## 6. dashboard.py (28 -> < 15, quick win)

### Problem

`plot_dashboard()` mixes panel layout decisions with panel rendering.

### Design

**Extract each panel into a function:**

- `_draw_sab_histogram(ax, result)` -- panel 1
- `_draw_compliance_summary(ax, result, body_mass)` -- panel 2
- `_draw_eigenspectrum(ax, result)` -- panel 3 (coherent only)
- `_draw_rho_gauge(ax, result)` -- already exists as a separate function

`plot_dashboard()` becomes: determine layout (2 vs 4 panels), create figure, call panel functions, save/show. ~20 lines.

---

## Implementation order

1. **dashboard.py** -- smallest, fastest, builds confidence
2. **__main__.py** -- small file, clear extractions
3. **scene_data.py** -- medium, table-driven classify_material
4. **server.py** -- largest, introduces routes/ package (done early because highest value)
5. **differt.py** -- physics-sensitive (must validate carefully against tests)
6. **occlusion.py** -- light touch, last

Each file is a separate commit. Tests run after each.
