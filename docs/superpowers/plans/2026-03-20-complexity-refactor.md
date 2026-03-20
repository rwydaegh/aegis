# Complexity refactor implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce cognitive complexity across 6 files from ~460 to ~120 without changing behavior.

**Architecture:** Pure extract-method refactoring. Each task takes one file, extracts heavy logic into focused helper functions, and validates that all tests still pass. No new abstractions, no behavior changes.

**Tech Stack:** Python 3.12, Flask, NumPy, ruff, qlty

**Spec:** `docs/superpowers/specs/2026-03-20-complexity-refactor-design.md`

---

### Task 1: Refactor dashboard.py (28 -> < 15)

**Files:**
- Modify: `src/aegis/viz/dashboard.py`

- [ ] **Step 1: Extract `_draw_sab_histogram` helper**

Extract lines 55-64 of `plot_dashboard()` (panel 1: histogram drawing) into a standalone function:

```python
def _draw_sab_histogram(ax, result) -> None:
    """Panel 1: S_ab distribution histogram with ICNIRP limit line."""
    sab = result.sab
    ax.hist(sab[sab > 0], bins=50, color="#e74c3c", alpha=0.8, edgecolor="white")
    limit = ICNIRP_2020.sab_peak
    ax.axvline(limit, color="gold", linewidth=2, linestyle="--", label=f"ICNIRP limit ({limit} W/m²)")
    ax.set_xlabel("S_ab (W/m²)")
    ax.set_ylabel("Triangle count")
    ax.set_title("S_ab distribution")
    ax.legend(fontsize=8)
```

Replace lines 55-64 in `plot_dashboard()` with `_draw_sab_histogram(axes[0], result)`.

- [ ] **Step 2: Extract `_draw_compliance_summary` helper**

Extract lines 66-115 (panel 2: compliance text) into:

```python
def _draw_compliance_summary(ax, result, body_mass: float | None) -> None:
    """Panel 2: text summary of compliance status."""
    ax.axis("off")
    lines = [
        f"Fidelity level: {result.fidelity_level}",
        f"P_abs: {result.p_abs * 1e3:.2f} mW",
        f"Peak S_ab: {result.peak_sab:.3f} W/m²",
    ]
    if result.peak_sab_averaged is not None:
        lines.append(f"Peak S_ab (4 cm² avg): {result.peak_sab_averaged:.3f} W/m²")
    if result.sar_wb is not None:
        lines.append(f"SAR_wb: {result.sar_wb * 1e3:.2f} mW/kg")
    elif body_mass is not None:
        if body_mass <= 0:
            raise ValueError("body_mass must be positive when provided")
        sar = result.p_abs / body_mass
        lines.append(f"SAR_wb: {sar * 1e3:.2f} mW/kg")
    sab_status = "PASS" if result.peak_sab < ICNIRP_2020.sab_peak else "FAIL"
    lines.append("")
    lines.append(f"S_ab compliance: {sab_status}")
    if result.sar_wb is not None:
        sar_status = "PASS" if result.sar_wb < ICNIRP_2020.sar_wb else "FAIL"
        lines.append(f"SAR compliance: {sar_status}")
    for i, line in enumerate(lines):
        color = "black"
        weight = "normal"
        if "PASS" in line:
            color = "#2ecc71"
            weight = "bold"
        elif "FAIL" in line:
            color = "#e74c3c"
            weight = "bold"
        ax.text(0.1, 0.9 - i * 0.1, line, transform=ax.transAxes, fontsize=11,
                verticalalignment="top", color=color, fontweight=weight)
    ax.set_title("Compliance summary")
```

Replace lines 66-115 with `_draw_compliance_summary(axes[1], result, body_mass)`.

- [ ] **Step 3: Extract `_draw_eigenspectrum` helper**

Extract lines 118-127 (panel 3: Q eigenspectrum bar chart) into:

```python
def _draw_eigenspectrum(ax, result) -> None:
    """Panel 3: Q eigenvalue bar chart."""
    eigs = result.eigenvalues
    if eigs is not None:
        n_eigs = len(eigs)
        ax.bar(range(n_eigs), eigs, color="#3498db", alpha=0.8)
        ax.set_xlabel("Eigenvalue index")
        ax.set_ylabel("Eigenvalue magnitude")
        ax.set_title("Q eigenspectrum")
        ax.set_yscale("log" if np.max(eigs) / (np.min(eigs[eigs > 0]) + 1e-30) > 100 else "linear")
```

- [ ] **Step 4: Update `plot_dashboard()` to call helpers**

The main function becomes:

```python
def plot_dashboard(result, *, body_mass=None, title="AEGIS compliance dashboard",
                   out_path=None, show=True):
    import matplotlib.pyplot as plt
    is_coherent = result.Q is not None
    n_panels = 4 if is_coherent else 2
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 5))
    if n_panels == 1:
        axes = [axes]
    fig.suptitle(title, fontsize=14, fontweight="bold")

    _draw_sab_histogram(axes[0], result)
    _draw_compliance_summary(axes[1], result, body_mass)

    if is_coherent:
        _draw_eigenspectrum(axes[2], result)
        _draw_rho_gauge(axes[3], result.rho if result.rho is not None else 0.0)

    plt.tight_layout()
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    return fig
```

- [ ] **Step 5: Validate**

Run: `py -3.12 -m ruff check src/aegis/viz/dashboard.py`
Run: `py -3.12 -m ruff format src/aegis/viz/dashboard.py`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/aegis/viz/dashboard.py
git commit -m "refactor(viz): extract panel helpers from plot_dashboard

Reduces cognitive complexity from 28 to ~12 by extracting
_draw_sab_histogram, _draw_compliance_summary, _draw_eigenspectrum."
```

---

### Task 2: Refactor __main__.py (56 -> < 20)

**Files:**
- Modify: `src/aegis/viewer/__main__.py`

- [ ] **Step 1: Extract `_resolve_config` function**

Create a new function above `main()` that handles the entire config resolution cascade (config file -> scenario overrides -> CLI overrides). Extract lines ~145-206 of `main()`:

```python
def _resolve_config(args) -> tuple[dict, str | None]:
    """Load config, apply scenario, apply CLI overrides. Returns (config, scenario_name)."""
    from aegis.viewer.config import apply_scenario_to_config, load_config, scenario_launch

    cfg = load_config(args.config)
    scenario_name = args.scenario if args.scenario is not None else cfg.get("default_scenario")
    if isinstance(scenario_name, str) and not scenario_name.strip():
        scenario_name = None

    scen_launch = scenario_launch(cfg, scenario_name)
    if scenario_name and scenario_name not in (cfg.get("scenarios") or {}):
        print(f"  Warning: unknown scenario {scenario_name!r}, ignoring scenario launch block")
        scen_launch = {}
        scenario_name = None

    # Build resolved values: scenario overrides config, CLI overrides scenario
    host = args.host or cfg["server"]["host"]
    port = args.port or cfg["server"]["port"]

    bbox = float(cfg["location"]["default_radius"])
    if "bbox" in scen_launch and scen_launch["bbox"] is not None:
        bbox = float(scen_launch["bbox"])
    if args.bbox is not None:
        bbox = float(args.bbox)

    body_name = cfg["body"]["default_name"]
    if "body" in scen_launch and scen_launch["body"]:
        body_name = str(scen_launch["body"])
    if args.body:
        body_name = args.body

    no_open = args.no_open or not cfg["server"]["open_browser"]

    data_dir = args.data_dir
    if data_dir is None and scen_launch.get("data_dir"):
        data_dir = str(scen_launch["data_dir"])
    if data_dir is None:
        data_dir = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data")

    voxel_dir = None
    voxel_json = None
    if scen_launch:
        if "voxel_dir" in scen_launch:
            voxel_dir = scen_launch["voxel_dir"]
        if "voxel_json" in scen_launch:
            voxel_json = scen_launch["voxel_json"]
    if args.voxel_dir is not None:
        voxel_dir = args.voxel_dir
    if args.voxel_json is not None:
        voxel_json = args.voxel_json

    cfg = apply_scenario_to_config(cfg, scenario_name)

    return cfg, {
        "host": host,
        "port": port,
        "bbox": bbox,
        "body_name": body_name,
        "no_open": no_open,
        "data_dir": data_dir,
        "voxel_dir": voxel_dir,
        "voxel_json": voxel_json,
        "scenario_name": scenario_name,
    }
```

- [ ] **Step 2: Rewrite `main()` as a thin orchestrator**

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS interactive 3D viewer")
    # ... all add_argument calls unchanged ...
    args = parser.parse_args()

    cfg, opts = _resolve_config(args)

    # Fetch location if needed
    if not opts["voxel_dir"] and not opts["voxel_json"] and args.location:
        opts["voxel_dir"] = _fetch_location(
            args.location, int(opts["bbox"] / 2), args.cache_dir,
        )

    if opts["scenario_name"]:
        print(f"  Scenario: {opts['scenario_name']}")
        desc = (cfg.get("scenarios") or {}).get(opts["scenario_name"], {}).get("description")
        if desc:
            print(f"    {desc}")

    _kill_previous_on_port(opts["port"])

    from aegis.viewer.server import create_app

    app = create_app(
        data_dir=opts["data_dir"],
        voxel_json=opts["voxel_json"],
        voxel_dir=opts["voxel_dir"],
        bbox_radius=opts["bbox"] / 2.0,
        body_name=opts["body_name"],
        pipeline_dir=args.pipeline_dir,
        cache_dir=args.cache_dir,
        config=cfg,
    )

    url = f"http://{opts['host']}:{opts['port']}"
    print(f"\n  AEGIS Viewer: {url}\n")
    if not opts["no_open"]:
        webbrowser.open(url)
    app.run(host=opts["host"], port=opts["port"], debug=cfg["server"]["debug"], threaded=True)
```

- [ ] **Step 3: Validate**

Run: `py -3.12 -m ruff check src/aegis/viewer/__main__.py`
Run: `py -3.12 -m ruff format src/aegis/viewer/__main__.py`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/__main__.py
git commit -m "refactor(viewer): extract _resolve_config from main()

Separates config resolution (file + scenario + CLI overrides) from
server launch. Reduces cognitive complexity from 56 to ~18."
```

---

### Task 3: Refactor scene_data.py (61 -> < 20)

**Files:**
- Modify: `src/aegis/viewer/scene_data.py`

- [ ] **Step 1: Convert `classify_material` to table-driven lookup**

Replace the nested if-chain in `classify_material()` with an ordered rules table.

**CRITICAL: Read the actual `classify_material()` function before writing rules.** The code snippet below is illustrative only. The actual function has these subtleties that must be preserved:
- HSV hue is scaled to 0-360 degrees (`hue = h * 360`)
- There are TWO vegetation hue ranges (`vegetation_hue_range_1` and `vegetation_hue_range_2`)
- There is an early "low saturation" gate (`saturation_gray_threshold`) that branches to either asphalt or concrete based on value
- The blue-hue range gates water vs glass vs concrete as nested conditions
- There is a `brick_secondary_hue_range` config key
- The asphalt check uses `value_dark_threshold`, not `asphalt.max_value`

Build the rules table to match the exact branching order of the existing code. First match wins.

```python
def _build_material_rules(mc: dict) -> list[dict]:
    """Build ordered material classification rules from config thresholds.

    IMPORTANT: derive rules from actual classify_material() logic.
    The order and conditions must produce identical output.
    """
    # Read the actual classify_material function and translate each
    # branch into a rule entry. Use hue_360 = h * 360 for thresholds.
    ...


def classify_material(r, g, b) -> str:
    """Classify material from RGB using HSV thresholds (config-driven)."""
    import colorsys
    r, g, b = int(r), int(g), int(b)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue_360 = h * 360  # actual code scales to degrees
    mc = _config["material_classification"]
    rules = _build_material_rules(mc)
    for rule in rules:
        if "test" not in rule or rule["test"](hue_360, s, v):
            return rule["name"]
    return "concrete"
```

- [ ] **Step 2: Extract coordinate transform helpers**

Split `_transform_to_local()` into two focused helpers.

**CRITICAL: Read the actual `_transform_to_local()` before implementing.** The actual function signature is `_transform_to_local(positions, has_ecef)` and it returns `(positions, transform_4x4_matrix)`. Key details:
- The ECEF path computes lon/lat from the position data itself (mean of ECEF coords), not from config
- The Y-up path does column stacking `[x, -z, y]`, not a simple axis swap
- Both paths construct and return a 4x4 homogeneous transform matrix `M` that is used downstream for tile alignment
- The helpers must preserve this `(positions, M)` return signature

```python
def _ecef_to_local(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Transform ECEF positions to local ENU Z-up coordinates.
    Returns (transformed_positions, 4x4 transform matrix).
    Read the actual code for lon/lat derivation and matrix construction.
    """
    ...


def _yup_to_zup(positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Swap Y-up to Z-up convention: column stacking [x, -z, y].
    Returns (transformed_positions, 4x4 transform matrix).
    """
    ...
```

Update `_transform_to_local()` to dispatch to the appropriate helper while preserving its current signature `(positions, has_ecef) -> (positions, M)`.

- [ ] **Step 3: Validate**

Run: `py -3.12 -m ruff check src/aegis/viewer/scene_data.py`
Run: `py -3.12 -m ruff format src/aegis/viewer/scene_data.py`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/aegis/viewer/scene_data.py
git commit -m "refactor(viewer): table-driven classify_material, extract coord transforms

Replaces nested if-chain with ordered rules table. Splits
_transform_to_local into _ecef_to_local and _yup_to_zup helpers."
```

---

### Task 4: Refactor server.py (151 -> < 30)

**Files:**
- Create: `src/aegis/viewer/routes/__init__.py`
- Create: `src/aegis/viewer/routes/data.py`
- Create: `src/aegis/viewer/routes/compute.py`
- Create: `src/aegis/viewer/routes/location.py`
- Modify: `src/aegis/viewer/server.py`

This is the largest task. Work in sub-steps.

- [ ] **Step 1: Create `routes/__init__.py`**

```python
"""Viewer Flask route modules."""
```

- [ ] **Step 2: Create `routes/data.py` with static data routes**

Move these routes from `create_app()`:
- `index()` (lines 168-170)
- `api_viewer_config()` (lines 172-175)
- `api_body()` (lines 177-189)
- `api_voxels()` (lines 191-202)
- `api_tiles_list()` (lines 204-226)
- `api_tiles_file()` (lines 228-236)
- `api_config()` (lines 238-288)

Pattern:
```python
"""Data-serving routes: body mesh, voxels, tiles, config."""
from __future__ import annotations
import json
from flask import Response, jsonify, render_template, request


def register(app, cache, cache_lock):
    """Attach data-serving routes to the Flask app."""

    @app.route("/")
    def index():
        # IMPORTANT: template variable is "viewer_config", NOT "config_json"
        return render_template("index.html", viewer_config=json.dumps(cache.get("config", {})))

    @app.route("/api/viewer-config")
    def api_viewer_config():
        return jsonify(cache.get("config", {}))

    # ... remaining routes, each accessing `cache` directly ...
```

**Important notes for data.py:**
- `send_from_directory` is imported lazily inside `api_tiles_file` in the original. Keep it lazy.
- `api_config` uses `data_dir` to scan for STL files. Store `data_dir` in `cache["data_dir"]` during `create_app()` so data.py can access it.
- Preserve all existing lazy import patterns from the original code.

- [ ] **Step 3: Create `routes/compute.py` with dosimetry routes**

Move these routes:
- `api_compute()` (lines 290-330)
- `api_scenes()` (lines 331-339)
- `api_scene_load()` (lines 341-362)
- `api_voxels_hull_mesh()` (lines 364-407)
- `api_compute_rt()` (lines 409-508)
- `api_compute_voxel_rt()` (lines 510-702)

Extract shared helpers:
```python
def _build_stats_response(result, body, tissue, level, extra=None):
    """Build the X-Stats JSON dict shared by all compute routes."""
    import numpy as np
    stats = {
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "compliant": bool(result.peak_sab < 10.0),
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": int(body.n_triangles),
        "level": level,
        "T0": float(tissue.T0),
    }
    if extra:
        stats.update(extra)
    return stats


def _zero_paths_response(body, tissue, level, extra=None):
    """Build response when ray tracer finds zero paths."""
    import numpy as np
    sab = np.zeros(body.n_triangles, dtype=np.float32)
    stats = {
        "p_abs": 0.0, "p_abs_mw": 0.0, "peak_sab": 0.0,
        "compliant": True, "n_illuminated": 0,
        "n_triangles": int(body.n_triangles), "level": level,
        "T0": float(tissue.T0), "n_paths": 0,
    }
    if extra:
        stats.update(extra)
    return Response(
        sab.tobytes(),
        mimetype="application/octet-stream",
        headers={"X-Stats": json.dumps(stats)},
    )
```

For `api_compute_voxel_rt`, extract the inner compute logic into `_do_compute_voxel_rt(cache, params)` that takes explicit parameters and returns `(sab_bytes, stats)`. The route handler parses the request and calls this function.

**Body rotation note:** The actual `api_compute_voxel_rt` at lines 548-558 rotates only centroids and normals (not vertices), while `_transform_body_for_viewer` in compute.py rotates everything. Do NOT blindly swap in `_transform_body_for_viewer` -- read the actual code and preserve the existing rotation behavior. If the partial rotation is intentional, keep it as-is in the extracted helper.

For `api_compute_rt`, similarly extract to `_do_compute_rt(cache, params)`.

Preserve all lazy imports (DiffeRT, engine, etc.) inside the route handlers or the extracted functions, not at module level.

- [ ] **Step 4: Create `routes/location.py` with geographic pipeline routes**

Move:
- `api_location_load()` (lines 704-776) including the nested `generate()` SSE generator
- `api_location_cancel()` (lines 778-784)

```python
"""Geographic pipeline routes: location loading and cancellation."""
from __future__ import annotations
import json
from flask import Response, jsonify, request


def register(app, cache, cache_lock):
    """Attach location pipeline routes to the Flask app."""

    @app.route("/api/location/load")
    def api_location_load():
        # ... extract SSE streaming logic ...
        # NOTE: the generate() SSE generator calls _load_and_cache_voxels_dir
        # and clear_voxel_scene_cache. Import these lazily:
        #   from aegis.viewer.server import _load_and_cache_voxels_dir
        #   from aegis.viewer.raytracer import clear_voxel_scene_cache

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        # ... pipeline cancellation ...
```

**Important:** `api_location_load` calls `_load_and_cache_voxels_dir` (from server.py) and `clear_voxel_scene_cache` (from raytracer.py). Import these lazily inside the route handler to avoid circular imports. The `_load_and_cache_voxels_dir` function operates on the module-level `_cache` in server.py, so pass `cache` and `cache_lock` to it or refactor it to accept them as parameters.

- [ ] **Step 5: Slim down `server.py`**

Remove all route handler code from `create_app()`. Replace with three `register()` calls:

```python
from aegis.viewer.routes import compute, data, location

def create_app(...):
    app = Flask(...)
    # ... data loading into _cache (unchanged) ...

    data.register(app, _cache, _cache_lock)
    compute.register(app, _cache, _cache_lock)
    location.register(app, _cache, _cache_lock)

    return app
```

The three module-level helpers (`_load_grid_coords`, `_load_and_cache_voxels_single`, `_load_and_cache_voxels_dir`) stay in `server.py`.

- [ ] **Step 6: Validate thoroughly**

Run: `py -3.12 -m ruff check src/aegis/viewer/`
Run: `py -3.12 -m ruff format src/aegis/viewer/`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Run: `py -3.12 -m pytest tests/test_viewer_compute.py tests/test_viewer_server_lock.py tests/test_viewer_config.py -v`

Check that the viewer starts without errors:
```bash
py -3.12 -m aegis.viewer --no-open --port 5099 &
# Wait 3 seconds, then:
curl http://127.0.0.1:5099/api/config
# Should return JSON with bodies, tissues, levels
```

- [ ] **Step 7: Commit**

```bash
git add src/aegis/viewer/routes/ src/aegis/viewer/server.py
git commit -m "refactor(viewer): split server routes into routes/ package

Extracts 16 route handlers from the 700-line create_app() into
routes/data.py, routes/compute.py, routes/location.py. Shared
helpers _build_stats_response and _zero_paths_response deduplicate
response construction. server.py now handles only app creation
and data loading."
```

---

### Task 5: Refactor differt.py (101 -> < 25)

**Files:**
- Modify: `src/aegis/integration/differt.py`

- [ ] **Step 1: Extract `_initial_polarisation_vector`**

Extract the initial psi setup from `_track_polarisation()` (the block that handles "vertical" vs other polarization types):

```python
def _initial_polarisation_vector(k_hat: np.ndarray, pol_type: str) -> np.ndarray:
    """Compute initial polarization vector from propagation direction.

    For 'vertical' polarization: project z-hat onto the plane perpendicular to k_hat.
    For other types: project x-hat similarly.
    """
    if pol_type == "vertical":
        ref = np.array([0.0, 0.0, 1.0])
    else:
        ref = np.array([1.0, 0.0, 0.0])
    perp = ref - np.dot(ref, k_hat) * k_hat
    norm = np.linalg.norm(perp)
    if norm < 1e-12:
        # _arbitrary_perpendicular is vectorized: takes (N,3), returns (N,3)
        perp = _arbitrary_perpendicular(k_hat[np.newaxis, :])[0]
    else:
        perp = perp / norm
    return perp
```

- [ ] **Step 2: Extract `_decompose_te_tm`**

Extract the TE/TM basis computation (the block that computes e_s and e_p from k_hat and surface normal):

```python
def _decompose_te_tm(k_hat: np.ndarray, normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute TE (s) and TM (p) basis vectors for a reflection.

    Returns (e_s, e_p_in) where e_s is perpendicular to the plane of incidence
    and e_p_in is in the plane of incidence, perpendicular to k_hat.
    Handles degenerate case (normal incidence) by falling back to arbitrary perpendicular.
    """
    e_s = np.cross(k_hat, normal)
    e_s_norm = np.linalg.norm(e_s)
    if e_s_norm < 1e-12:
        e_s = _arbitrary_perpendicular(k_hat)
    else:
        e_s = e_s / e_s_norm
    e_p_in = np.cross(e_s, k_hat)
    e_p_norm = np.linalg.norm(e_p_in)
    if e_p_norm > 1e-12:
        e_p_in = e_p_in / e_p_norm
    return e_s, e_p_in
```

- [ ] **Step 3: Extract `_reflect_at_surface`**

Extract the inner-loop body of `_track_polarisation()` that does a single Fresnel reflection.

**CRITICAL physics details -- read the actual code before implementing:**
1. The normal must be flipped to face the incident ray: `if np.dot(normal, -k_in) < 0: normal = -normal`
2. The TE basis `e_s` is the SAME for incident and reflected beams. Do NOT recompute it for the reflected direction.
3. The reflected TM basis is `e_p_r = np.cross(e_s, k_out)` (using the shared `e_s`, not a fresh decomposition)
4. Fresnel imports (`fresnel_reflection`, `n_complex`) are at module level in differt.py (line 18). Keep them there.

```python
def _reflect_at_surface(
    psi: np.ndarray,
    k_in: np.ndarray,
    k_out: np.ndarray,
    normal: np.ndarray,
    n_tilde: complex,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply Fresnel reflection to polarization vector at a surface.

    Returns (psi_reflected, k_out) -- both the updated field and outgoing direction.
    """
    # Flip normal to face the incident ray
    if np.dot(normal, -k_in) < 0:
        normal = -normal

    e_s, e_p_in = _decompose_te_tm(k_in, normal)

    # Decompose incident psi into TE/TM
    psi_s = np.dot(psi, e_s)
    psi_p = np.dot(psi, e_p_in)

    cos_i = abs(np.dot(k_in, normal))
    cos_i = min(cos_i, 1.0)

    r_s, r_p = fresnel_reflection(cos_i, n_tilde)

    psi_s_r = psi_s * r_s
    psi_p_r = psi_p * r_p

    # Reflected TM basis uses the SAME e_s (not recomputed)
    e_p_r = np.cross(e_s, k_out)
    e_p_r_norm = np.linalg.norm(e_p_r)
    if e_p_r_norm > 1e-12:
        e_p_r = e_p_r / e_p_r_norm

    psi_out = psi_s_r * e_s + psi_p_r * e_p_r
    return psi_out, k_out
```

- [ ] **Step 4: Rewrite `_track_polarisation` to use helpers**

The main loop becomes:

```python
def _track_polarisation(path_vertices, scene_normals, object_indices,
                        material_indices, material_n_tilde, amplitude,
                        initial_polarisation="vertical"):
    N_paths = path_vertices.shape[0]
    path_len = path_vertices.shape[1]
    psi_out = np.zeros((N_paths, 3), dtype=complex)

    for i in range(N_paths):
        verts = path_vertices[i]
        seg = verts[1] - verts[0]
        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-12:
            continue
        k = seg / seg_len
        psi = amplitude[i] * _initial_polarisation_vector(k, initial_polarisation).astype(complex)

        for j in range(1, path_len - 1):
            next_seg = verts[j + 1] - verts[j]
            next_len = np.linalg.norm(next_seg)
            if next_len < 1e-12:
                continue
            k_out = next_seg / next_len

            obj_idx = int(object_indices[i, j])
            normal = scene_normals[obj_idx]
            mat_idx = material_indices[obj_idx] if material_indices is not None else 0
            n_tilde = material_n_tilde[mat_idx]

            psi, k = _reflect_at_surface(psi, k, k_out, normal, n_tilde)

        psi_out[i] = psi
    return psi_out
```

- [ ] **Step 5: Extract `_compute_element_paths` from `paths_from_differt_scene`**

```python
def _compute_element_paths(scene, tx_pos, rx_pos, freq, max_bounces):
    """Compute ray-traced paths for a single TX element across all bounce orders.

    Returns list of (vertices, object_indices, amplitudes) tuples, one per successful bounce order.
    """
    # ... extracted from the inner loop of paths_from_differt_scene ...
```

- [ ] **Step 6: Extract `_pad_and_concatenate`**

```python
def _pad_and_concatenate(path_arrays: list[np.ndarray]) -> np.ndarray:
    """Pad variable-length path arrays to the same length and concatenate."""
    if not path_arrays:
        return np.empty((0, 0, 3))
    max_len = max(a.shape[1] for a in path_arrays)
    padded = []
    for a in path_arrays:
        if a.shape[1] < max_len:
            pad_width = ((0, 0), (0, max_len - a.shape[1]), (0, 0))
            a = np.pad(a, pad_width, mode="edge")
        padded.append(a)
    return np.concatenate(padded, axis=0)
```

- [ ] **Step 7: Rewrite `paths_from_differt_scene` to use helpers**

The main function becomes ~40 lines: load scene, loop over TX elements, concatenate, call `paths_from_differt()`.

- [ ] **Step 8: Validate carefully**

Run: `py -3.12 -m ruff check src/aegis/integration/differt.py`
Run: `py -3.12 -m ruff format src/aegis/integration/differt.py`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Run: `py -3.12 -m pytest tests/test_integration.py -v` (if it exists and tests DiffeRT)

- [ ] **Step 9: Commit**

```bash
git add src/aegis/integration/differt.py
git commit -m "refactor(integration): extract helpers from polarisation tracking and scene loader

Splits _track_polarisation into _initial_polarisation_vector,
_decompose_te_tm, _reflect_at_surface. Splits paths_from_differt_scene
into _compute_element_paths and _pad_and_concatenate."
```

---

### Task 6: Refactor occlusion.py (57 -> < 25, light touch)

**Files:**
- Modify: `src/aegis/geometry/occlusion.py`

- [ ] **Step 1: Extract `_precompute_triangle_data`**

Extract the triangle setup code from `compute_ambient_occlusion()` (the block that computes v0, e1, e2, centroids, normals, bmin, bmax from the mesh vertices):

```python
def _precompute_triangle_data(vertices: np.ndarray) -> dict:
    """Precompute per-triangle geometry for ray intersection.

    Returns dict with keys: v0, edge1, edge2, centroids, normals, tri_bmin, tri_bmax.
    """
    v0 = vertices[:, 0, :]
    e1 = vertices[:, 1, :] - v0
    e2 = vertices[:, 2, :] - v0
    centroids = vertices.mean(axis=1)
    cross = np.cross(e1, e2)
    norms = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / np.where(norms > 0, norms, 1.0)
    tri_bmin = vertices.min(axis=1)
    tri_bmax = vertices.max(axis=1)
    return {
        "v0": v0, "edge1": e1, "edge2": e2,
        "centroids": centroids, "normals": normals,
        "tri_bmin": tri_bmin, "tri_bmax": tri_bmax,
    }
```

- [ ] **Step 2: Extract `_sample_and_test`**

Extract the inner sampling loop from `compute_ambient_occlusion()`:

```python
def _sample_and_test(origin, normal, samples_base, tri_data, bvh, n_rays, rng, tri_idx):
    """Fire n_rays hemisphere samples from a triangle and count unoccluded ones."""
    t, b = make_tangent_frame(normal)
    rotated = samples_base[:, 0:1] * t + samples_base[:, 1:2] * b + samples_base[:, 2:3] * normal
    hit_count = 0
    for s in range(n_rays):
        d = rotated[s]
        # ... call ray_mesh_any_hit with tri_data arrays and bvh ...
        if hit:
            hit_count += 1
    return hit_count
```

Note: match the exact parameter passing pattern of the existing inner loop. The ray intersection functions take individual scalar/array parameters, not the dict. Unpack `tri_data` at the call site.

- [ ] **Step 3: Update `compute_ambient_occlusion` to use helpers**

Replace the inline triangle setup with `_precompute_triangle_data()` and the inner loop with `_sample_and_test()`.

- [ ] **Step 4: Validate**

Run: `py -3.12 -m ruff check src/aegis/geometry/occlusion.py`
Run: `py -3.12 -m ruff format src/aegis/geometry/occlusion.py`
Run: `py -3.12 -m pytest tests/test_geometry.py -v`
Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

- [ ] **Step 5: Commit**

```bash
git add src/aegis/geometry/occlusion.py
git commit -m "refactor(geometry): extract triangle precomputation and sampling from AO

Extracts _precompute_triangle_data and _sample_and_test from
compute_ambient_occlusion. No changes to ray intersection functions."
```

---

### Task 7: Final validation and complexity check

**Files:** none (validation only)

- [ ] **Step 1: Run full test suite**

```bash
py -3.12 -m pytest tests/ -m "not slow" -x -v
```

Expected: all tests pass.

- [ ] **Step 2: Run ruff**

```bash
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format --check src/ tests/
```

Expected: clean.

- [ ] **Step 3: Run qlty complexity check**

```bash
powershell.exe -Command "cd 'C:\Users\rwydaegh\OneDrive - UGent\rwydaegh\Geometric Dosimetry\aegis'; qlty metrics --all --sort complexity --limit 20"
```

Verify the 6 target files are under their complexity targets.

- [ ] **Step 4: Push**

```bash
git push origin master
```
