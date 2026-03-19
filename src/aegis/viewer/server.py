"""Flask server for the AEGIS interactive viewer."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, render_template, request

from aegis.viewer.scene_data import (
    body_to_binary,
    find_body_placement,
    load_body,
    load_voxels,
    load_voxels_directory,
    voxels_to_binary,
)

# Module-level cache
_cache: dict = {}


def _load_grid_coords(voxel_json: str) -> np.ndarray | None:
    """Load integer grid coordinates from voxel JSON (for RT mesh building)."""
    import json as _json

    try:
        with open(voxel_json) as f:
            data = _json.load(f)
        voxels = data if isinstance(data, list) else data.get("voxels", [])
        return np.array([[v.get("x", 0), v.get("y", 0), v.get("z", 0)] for v in voxels], dtype=np.int64)
    except Exception:
        return None


def _load_and_cache_voxels_single(voxel_json: str, bbox_radius: float) -> None:
    """Load a single voxel JSON file into _cache."""
    positions, colors, materials, grid_coords, voxel_size = load_voxels(
        voxel_json,
        bbox_radius=bbox_radius,
    )
    _cache["voxel_positions"] = positions
    _cache["voxel_materials"] = materials
    _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
        positions,
        colors,
        materials,
        voxel_size=voxel_size,
    )
    _cache["voxel_grid_coords"] = grid_coords if len(grid_coords) > 0 else _load_grid_coords(voxel_json)
    _cache["body_placement"] = find_body_placement(positions, materials)
    print(f"  Voxels: {len(positions):,} loaded, voxel_size={voxel_size:.4f}")
    print(f"  Body placement: {_cache['body_placement']}")


def _load_and_cache_voxels_dir(voxel_dir: str, bbox_radius: float) -> None:
    """Load all voxel JSONs from a directory into _cache."""
    positions, colors, materials, grid_coords, voxel_size = load_voxels_directory(
        voxel_dir,
        bbox_radius=bbox_radius,
    )
    _cache["voxel_positions"] = positions
    _cache["voxel_materials"] = materials
    _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
        positions,
        colors,
        materials,
        voxel_size=voxel_size,
    )
    _cache["voxel_grid_coords"] = grid_coords if len(grid_coords) > 0 else None
    _cache["body_placement"] = find_body_placement(positions, materials)
    print(f"  Body placement: {_cache['body_placement']}")
    print(f"  Voxels (directory): {len(positions):,} loaded, voxel_size={voxel_size:.4f}")


def create_app(
    data_dir: str,
    voxel_json: str | None = None,
    voxel_dir: str | None = None,
    bbox_radius: float = 15.0,
    body_name: str = "thelonious",
    pipeline_dir: str | None = None,
    cache_dir: str | None = None,
) -> Flask:
    """Create and configure the Flask app."""
    template_dir = str(Path(__file__).parent / "templates")
    app = Flask(__name__, template_folder=template_dir)

    # Store pipeline config
    _cache["bbox_radius"] = bbox_radius
    _cache["pipeline_dir"] = pipeline_dir
    _cache["cache_dir"] = cache_dir

    # Pre-load data
    print("Loading data...")

    try:
        body = load_body(body_name, data_dir)
        _cache["body"] = body
        _cache["body_binary"], _cache["body_meta"] = body_to_binary(body)
        print(f"  Body: {body.name}, {body.n_triangles:,} triangles")
    except FileNotFoundError as e:
        print(f"  Warning: {e}")
        _cache["body"] = None

    _cache["voxel_json_path"] = voxel_json
    if voxel_dir:
        try:
            _load_and_cache_voxels_dir(voxel_dir, bbox_radius)
        except Exception as e:
            print(f"  Warning: voxel directory load failed: {e}")
            _cache["voxel_binary"] = None
            _cache["voxel_meta"] = None
    elif voxel_json:
        try:
            _load_and_cache_voxels_single(voxel_json, bbox_radius)
        except Exception as e:
            print(f"  Warning: voxel load failed: {e}")
            _cache["voxel_binary"] = None
            _cache["voxel_meta"] = None
    else:
        _cache["voxel_binary"] = None
        _cache["voxel_meta"] = None

    # --- Routes ---

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/body")
    def api_body():
        """Return body mesh as binary (positions + normals, float32)."""
        if _cache.get("body") is None:
            return jsonify({"error": "No body mesh loaded"}), 404

        data = _cache["body_binary"]
        meta = _cache["body_meta"]

        # Return binary with metadata in headers
        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/voxels")
    def api_voxels():
        """Return voxel data as binary (positions float32 + colors uint8 + materials uint8)."""
        if _cache.get("voxel_binary") is None:
            return jsonify({"error": "No voxel data loaded"}), 404

        data = _cache["voxel_binary"]
        meta = _cache["voxel_meta"]

        resp = Response(data, mimetype="application/octet-stream")
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp

    @app.route("/api/config")
    def api_config():
        """Return available configuration options."""
        bodies = []
        data_path = Path(data_dir)
        if data_path.exists():
            bodies = [p.stem for p in data_path.glob("*.stl")]

        # Check for DiffeRT and available scenes
        has_differt = False
        scenes = []
        try:
            from aegis.viewer.raytracer import list_available_scenes

            has_differt = True
            scenes = list_available_scenes()
        except ImportError:
            pass

        # Check location loader availability
        from aegis.viewer.pipeline import find_pipeline

        has_pipeline = find_pipeline() is not None
        has_api_key = bool(os.environ.get("GOOGLE_API_KEY"))

        return jsonify(
            {
                "bodies": bodies,
                "tissues": ["skin_28ghz", "skin_60ghz"],
                "levels": list(range(7)),
                "has_voxels": _cache.get("voxel_binary") is not None,
                "has_differt": has_differt,
                "scenes": scenes,
                "body_meta": _cache.get("body_meta"),
                "voxel_meta": _cache.get("voxel_meta"),
                "has_location_loader": has_pipeline and has_api_key,
                "has_api_key": has_api_key,
                "body_placement": _cache.get("body_placement"),
            }
        )

    @app.route("/api/compute", methods=["POST"])
    def api_compute():
        """Compute dosimetry for given antenna position."""
        from aegis.viewer.compute import TISSUE_PRESETS, compute_dosimetry

        body = _cache.get("body")
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

        params = request.get_json()
        antenna_pos = params.get("antenna_pos", [5, 0, 1])
        body_offset = params.get("body_offset", [0, 0, 0])
        level = params.get("level", 2)
        tissue_name = params.get("tissue", "skin_28ghz")
        power_dbm = params.get("power_dbm", 30.0)
        n_paths = params.get("n_paths", 1)

        tissue = TISSUE_PRESETS.get(tissue_name)

        result = compute_dosimetry(
            body,
            antenna_pos=np.array(antenna_pos),
            body_offset=np.array(body_offset),
            level=level,
            tissue=tissue,
            power_dbm=power_dbm,
            n_paths=n_paths,
        )

        # Return binary S_ab with JSON stats in header
        sab_bytes = result.pop("sab_bytes")
        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(result)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/scenes")
    def api_scenes():
        """List available Sionna XML scenes for DiffeRT ray tracing."""
        try:
            from aegis.viewer.raytracer import list_available_scenes

            return jsonify(list_available_scenes())
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

    @app.route("/api/scene/load", methods=["POST"])
    def api_scene_load():
        """Load a Sionna scene and return its geometry for Three.js."""
        try:
            from aegis.viewer.raytracer import load_scene, scene_geometry_to_binary
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        params = request.get_json()
        scene_path = params.get("path")
        if not scene_path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        try:
            scene_data = load_scene(scene_path)
            data, meta = scene_geometry_to_binary(scene_data)
            resp = Response(data, mimetype="application/octet-stream")
            resp.headers["X-Meta"] = json.dumps(meta)
            return resp
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/compute/rt", methods=["POST"])
    def api_compute_rt():
        """Compute dosimetry using DiffeRT ray-traced paths."""
        try:
            from aegis.viewer.raytracer import compute_paths_differt
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        from aegis.viewer.compute import TISSUE_PRESETS

        body = _cache.get("body")
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

        params = request.get_json()
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        scene_path = params.get("scene_path")
        level = params.get("level", 2)
        tissue_name = params.get("tissue", "skin_28ghz")
        power_dbm = params.get("power_dbm", 30.0)
        max_order = params.get("max_order", 1)
        body_pos = params.get("body_pos")

        if not scene_path:
            return jsonify({"error": "Missing 'scene_path'"}), 400

        tissue = TISSUE_PRESETS.get(tissue_name)
        if tissue is None:
            from aegis.tissue.dielectric import SKIN_28GHZ

            tissue = SKIN_28GHZ

        # Body position in scene coordinates (defaults to origin at height 1.0)
        body_center = np.array(body_pos) if body_pos is not None else np.array([0.0, 0.0, 1.0])

        # Run DiffeRT
        try:
            paths, path_viz = compute_paths_differt(
                scene_path,
                tx_pos=antenna_pos,
                rx_pos=body_center,
                max_order=max_order,
                freq_hz=tissue.freq_hz,
                tx_power_dbm=power_dbm,
            )
        except Exception as e:
            return jsonify({"error": f"Ray tracing failed: {e}"}), 500

        if paths.n_paths == 0:
            # No paths found, return zeros
            sab_bytes = np.zeros(body.n_triangles, dtype=np.float32).tobytes()
            stats = {
                "p_abs": 0,
                "p_abs_mw": 0,
                "peak_sab": 0,
                "compliant": True,
                "n_illuminated": 0,
                "n_triangles": body.n_triangles,
                "level": level,
                "S_inc": 0,
                "distance_m": 0,
                "T0": tissue.T0,
                "n_rt_paths": 0,
                "path_viz": [],
            }
            resp = Response(sab_bytes, mimetype="application/octet-stream")
            resp.headers["X-Stats"] = json.dumps(stats)
            resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
            return resp

        # Run dosimetry engine
        from aegis.engine import DosimetryEngine

        engine = DosimetryEngine(tissue)
        result = engine.compute(body, paths, level=level)

        sab_bytes = result.sab.astype(np.float32).tobytes()
        dist = float(np.linalg.norm(antenna_pos - body_center))
        total_power = float(np.sum(paths.power))

        stats = {
            "p_abs": float(result.p_abs),
            "p_abs_mw": float(result.p_abs * 1e3),
            "peak_sab": float(result.peak_sab),
            "compliant": bool(result.peak_sab < 10.0),
            "n_illuminated": int(np.sum(result.sab > 0)),
            "n_triangles": body.n_triangles,
            "level": level,
            "S_inc": total_power,
            "distance_m": dist,
            "T0": float(tissue.T0),
            "n_rt_paths": paths.n_paths,
            "path_viz": path_viz,
        }

        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/compute/voxel-rt", methods=["POST"])
    def api_compute_voxel_rt():
        """Compute dosimetry using DiffeRT on the voxel environment geometry."""
        try:
            from aegis.viewer.raytracer import get_or_build_voxel_scene
        except ImportError:
            return jsonify({"error": "DiffeRT not installed"}), 501

        from aegis.viewer.compute import TISSUE_PRESETS
        from aegis.viewer.scene_data import extract_exterior

        body = _cache.get("body")
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 400

        grid_coords = _cache.get("voxel_grid_coords")
        if grid_coords is None:
            return jsonify({"error": "No voxel grid data available"}), 400

        params = request.get_json()
        antenna_pos = np.array(params.get("antenna_pos", [5, 0, 1]))
        body_offset = np.array(params.get("body_offset", [0, 0, 0]), dtype=np.float64)
        level = params.get("level", 2)
        tissue_name = params.get("tissue", "skin_28ghz")
        power_dbm = params.get("power_dbm", 30.0)
        max_order = params.get("max_order", 0)

        tissue = TISSUE_PRESETS.get(tissue_name)
        if tissue is None:
            from aegis.tissue.dielectric import SKIN_28GHZ

            tissue = SKIN_28GHZ

        body_center = body.centroids.mean(axis=0) + body_offset

        # Build or get cached voxel DiffeRT scene
        MAX_RT_TRIANGLES = 50_000
        try:
            ext_mask = extract_exterior(grid_coords)
            ext_grid = grid_coords[ext_mask]
            ext_pos = ext_grid.astype(float)

            # Each exterior voxel face is 2 triangles, up to 6 faces per voxel
            est_triangles = len(ext_pos) * 12
            if est_triangles > MAX_RT_TRIANGLES and max_order > 0:
                return jsonify(
                    {
                        "error": f"Scene too large for reflections ({est_triangles:,} triangles, "
                        f"limit {MAX_RT_TRIANGLES:,}). Use LOS only (order 0) or reduce scene size."
                    }
                ), 400

            scene = get_or_build_voxel_scene(ext_pos, ext_grid, voxel_size=1.0)
        except Exception as e:
            return jsonify({"error": f"Voxel mesh build failed: {e}"}), 500

        # Run DiffeRT on the voxel scene
        try:
            import equinox as eqx
            import jax.numpy as jnp

            scene_with_tx_rx = eqx.tree_at(lambda s: s.transmitters, scene, jnp.array([antenna_pos.tolist()]))
            scene_with_tx_rx = eqx.tree_at(lambda s: s.receivers, scene_with_tx_rx, jnp.array([body_center.tolist()]))

            all_k_hat = []
            all_power = []
            path_viz = []

            tx_power_w = 10 ** ((power_dbm - 30) / 10)
            wavelength = 3e8 / tissue.freq_hz

            for order in range(max_order + 1):
                try:
                    paths_result = scene_with_tx_rx.compute_paths(order=order)
                except Exception:
                    continue

                verts = np.array(paths_result.vertices)
                mask = np.array(paths_result.mask)
                flat_v = verts.reshape(-1, verts.shape[-2], verts.shape[-1])
                flat_m = mask.flatten()

                for i in range(len(flat_v)):
                    if i >= len(flat_m) or not flat_m[i]:
                        continue
                    pv = flat_v[i]
                    segments = np.diff(pv, axis=0)
                    seg_lens = np.linalg.norm(segments, axis=1)
                    total_len = float(np.sum(seg_lens))
                    if total_len < 1e-6:
                        continue

                    k_hat = segments[-1] / np.linalg.norm(segments[-1])
                    all_k_hat.append(k_hat)

                    fspl_amp = wavelength / (4 * np.pi * max(total_len, 0.01))
                    S_inc = tx_power_w * (fspl_amp**2) * (0.5**order)
                    all_power.append(S_inc)

                    path_viz.append(
                        {
                            "vertices": pv.tolist(),
                            "order": order,
                            "length": total_len,
                        }
                    )

        except Exception as e:
            return jsonify({"error": f"Voxel RT failed: {e}"}), 500

        if not all_k_hat:
            sab_bytes = np.zeros(body.n_triangles, dtype=np.float32).tobytes()
            stats = {
                "p_abs": 0,
                "p_abs_mw": 0,
                "peak_sab": 0,
                "compliant": True,
                "n_illuminated": 0,
                "n_triangles": body.n_triangles,
                "level": level,
                "S_inc": 0,
                "distance_m": 0,
                "T0": tissue.T0,
                "n_rt_paths": 0,
                "path_viz": [],
            }
        else:
            from aegis.engine import DosimetryEngine
            from aegis.paths import PropagationPaths

            paths = PropagationPaths.from_powers(k_hat=np.array(all_k_hat), power=np.array(all_power))
            engine = DosimetryEngine(tissue)
            result = engine.compute(body, paths, level=level)

            sab_bytes = result.sab.astype(np.float32).tobytes()
            dist = float(np.linalg.norm(antenna_pos - body_center))
            stats = {
                "p_abs": float(result.p_abs),
                "p_abs_mw": float(result.p_abs * 1e3),
                "peak_sab": float(result.peak_sab),
                "compliant": bool(result.peak_sab < 10.0),
                "n_illuminated": int(np.sum(result.sab > 0)),
                "n_triangles": body.n_triangles,
                "level": level,
                "S_inc": float(np.sum(all_power)),
                "distance_m": dist,
                "T0": float(tissue.T0),
                "n_rt_paths": len(all_k_hat),
                "path_viz": path_viz,
            }

        resp = Response(sab_bytes, mimetype="application/octet-stream")
        resp.headers["X-Stats"] = json.dumps(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/location/load")
    def api_location_load():
        """Stream pipeline progress via SSE, then load voxels."""
        from aegis.viewer.pipeline import (
            cache_dir_for,
            find_pipeline,
            run_pipeline,
        )

        location = request.args.get("location", "").strip()
        radius = int(request.args.get("radius", 30))
        force = request.args.get("force", "false").lower() == "true"

        if not location:
            return jsonify({"error": "Missing location parameter"}), 400

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return jsonify({"error": "GOOGLE_API_KEY not set"}), 400

        if find_pipeline() is None:
            return jsonify({"error": "Pipeline not found"}), 404

        # Determine cache/output directory
        base_cache = Path(
            _cache.get("cache_dir")
            or os.environ.get("VOXELEARTH_CACHE_DIR")
            or str(find_pipeline().parent / "pipeline_cache")
        )
        voxel_output = cache_dir_for(location, radius, base_cache)
        pipeline_output = voxel_output.parent

        def generate():
            # Check cache
            cached = voxel_output.exists() and any(voxel_output.glob("*.json"))
            if cached and not force:
                yield "event: progress\ndata: Using cached data\n\n"
            else:
                # Run pipeline
                for line in run_pipeline(location, radius, api_key, pipeline_output):
                    yield f"event: progress\ndata: {line}\n\n"
                    if line.startswith("ERROR:"):
                        yield f"event: error\ndata: {line}\n\n"
                        return

            # Load voxels from output directory
            try:
                yield "event: progress\ndata: Loading voxels into viewer...\n\n"
                br = _cache.get("bbox_radius", 15.0)
                _load_and_cache_voxels_dir(str(voxel_output), br)
                meta = _cache.get("voxel_meta", {})
                yield f"event: done\ndata: {json.dumps(meta)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: Voxel load failed: {e}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/location/cancel", methods=["POST"])
    def api_location_cancel():
        """Kill running pipeline subprocess."""
        from aegis.viewer.pipeline import cancel_pipeline

        killed = cancel_pipeline()
        return jsonify({"cancelled": killed})

    return app
