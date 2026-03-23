"""Flask server for the AEGIS interactive viewer."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np
from flask import Flask, jsonify

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
_cache_lock = threading.RLock()

# Fidelity catalog for GET /api/levels (names and blurbs match kernel modules in src/aegis/kernels/).
FIDELITY_LEVELS_API = [
    {
        "level": 0,
        "name": "Bound",
        "description": (
            "Worst-case absorbed power bound: O(1) in mesh size. "
            "Uniform per-triangle S_ab from a scalar bound, not a resolved hotspot map."
        ),
    },
    {
        "level": 1,
        "name": "Aggregate",
        "description": (
            "Total absorbed power via spherical-harmonic absorption directivity per path, O(N) in paths. "
            "Per-triangle S_ab is uniform because the spatial map is not resolved."
        ),
    },
    {
        "level": 2,
        "name": "Geometric ReLU",
        "description": (
            "Incoherent spatial map S_ab = T_0 * ReLU(n_hat \u00b7 (-k_hat)) weighted by path powers. "
            "Standard level for compliance-style assessment."
        ),
    },
    {
        "level": 3,
        "name": "Fresnel",
        "description": (
            "Like level 2 but with angle-dependent unpolarised Fresnel transmission T_avg(theta) instead of fixed T_0."
        ),
    },
    {
        "level": 4,
        "name": "Polarisation",
        "description": (
            "Polarisation-aware Fresnel (TM/TE splitting). Collapses to level 3 for unpolarised or circular waves."
        ),
    },
    {
        "level": 5,
        "name": "Curvature",
        "description": (
            "Adds a first-order physical optics curvature correction on top of the Fresnel map "
            "(level 3 baseline with extra ReLU-squared term)."
        ),
    },
    {
        "level": 6,
        "name": "Diffraction",
        "description": (
            "Smooths the shadow boundary by replacing sharp ReLU with a physical GELU kernel tied to local curvature."
        ),
    },
    {
        "level": 7,
        "name": "Coherent MIMO",
        "description": (
            "Coherent absorption map from the body-surface channel and precoding vector x using path phasors psi."
        ),
    },
    {
        "level": 8,
        "name": "ECBF",
        "description": (
            "Exposure-constrained beamforming: solves for the precoder that maximises signal power "
            "subject to absorbed power and transmit power limits."
        ),
    },
]


def _load_and_cache_voxels_single(voxel_json: str, bbox_radius: float) -> None:
    """Load a single voxel JSON file into _cache."""
    positions, colors, materials, voxel_sizes = load_voxels(
        voxel_json,
        bbox_radius=bbox_radius,
    )
    with _cache_lock:
        _cache["voxel_positions"] = positions
        _cache["voxel_materials"] = materials
        _cache["voxel_sizes"] = voxel_sizes
        _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
            positions,
            colors,
            materials,
            voxel_sizes=voxel_sizes,
        )
        _cache["body_placement"] = find_body_placement(positions, materials)
    try:
        from aegis.viewer.raytracer import clear_voxel_scene_cache

        clear_voxel_scene_cache()
    except ImportError:
        pass
    vs = float(np.median(voxel_sizes)) if len(voxel_sizes) > 0 else 0
    print(f"  Voxels: {len(positions):,} loaded, median_size={vs:.4f}")
    print(f"  Body placement: {_cache['body_placement']}")


def _load_and_cache_voxels_dir(voxel_dir: str, bbox_radius: float) -> None:
    """Load all voxel JSONs from a directory into _cache."""
    positions, colors, materials, voxel_sizes = load_voxels_directory(
        voxel_dir,
        bbox_radius=bbox_radius,
    )
    with _cache_lock:
        _cache["voxel_positions"] = positions
        _cache["voxel_materials"] = materials
        _cache["voxel_sizes"] = voxel_sizes
        _cache["voxel_binary"], _cache["voxel_meta"] = voxels_to_binary(
            positions,
            colors,
            materials,
            voxel_sizes=voxel_sizes,
        )
        _cache["body_placement"] = find_body_placement(positions, materials)
    try:
        from aegis.viewer.raytracer import clear_voxel_scene_cache

        clear_voxel_scene_cache()
    except ImportError:
        pass
    vs = float(np.median(voxel_sizes)) if len(voxel_sizes) > 0 else 0
    print(f"  Body placement: {_cache['body_placement']}")
    print(f"  Voxels (directory): {len(positions):,} loaded, median_size={vs:.4f}")


def create_app(
    data_dir: str,
    voxel_json: str | None = None,
    voxel_dir: str | None = None,
    bbox_radius: float = 15.0,
    body_name: str = "thelonious",
    pipeline_dir: str | None = None,
    cache_dir: str | None = None,
    config: dict | None = None,
) -> Flask:
    """Create and configure the Flask app."""
    from aegis.viewer.config import load_config

    if config is None:
        config = load_config()
    _cache["config"] = config

    # Propagate config to scene_data module
    from aegis.viewer.scene_data import set_config as set_scene_config

    set_scene_config(config)

    template_dir = str(Path(__file__).parent / "templates")
    app = Flask(__name__, template_folder=template_dir)

    # Optional HTTP Basic Auth for remote access
    _viewer_auth = os.environ.get("AEGIS_VIEWER_AUTH")
    if _viewer_auth and ":" in _viewer_auth:
        _auth_user, _, _auth_pass = _viewer_auth.partition(":")

        @app.before_request
        def _check_basic_auth():
            from flask import Response, request

            auth = request.authorization
            if not auth or auth.username != _auth_user or auth.password != _auth_pass:
                return Response(
                    "Authentication required.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="AEGIS Viewer"'},
                )

    # Store pipeline config
    _cache["bbox_radius"] = bbox_radius
    _cache["pipeline_dir"] = pipeline_dir
    _cache["cache_dir"] = cache_dir
    _cache["data_dir"] = data_dir

    # Pre-load data
    print("Loading data...")

    with _cache_lock:
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
                _cache["voxel_sizes"] = None
                _cache["body_placement"] = None
                _cache["voxel_positions"] = None
        elif voxel_json:
            try:
                _load_and_cache_voxels_single(voxel_json, bbox_radius)
            except Exception as e:
                print(f"  Warning: voxel load failed: {e}")
                _cache["voxel_binary"] = None
                _cache["voxel_meta"] = None
                _cache["voxel_sizes"] = None
                _cache["body_placement"] = None
                _cache["voxel_positions"] = None
        else:
            _cache["voxel_binary"] = None
            _cache["voxel_meta"] = None
            _cache["voxel_sizes"] = None
            _cache["body_placement"] = None
            _cache["voxel_positions"] = None

        # Resolve tiles directory (sibling of voxels dir from pipeline)
        _cache["tiles_dir"] = None
        _vs = voxel_dir or (str(Path(voxel_json).parent) if voxel_json else None)
        if _vs:
            _tc = Path(_vs).parent / "tiles"
            if _tc.is_dir() and any(_tc.glob("*.glb")):
                _cache["tiles_dir"] = _tc
                print(f"  Tiles: {len(list(_tc.glob('*.glb')))} GLB files")

    # --- Lightweight routes kept inline ---

    @app.route("/api/health")
    def api_health():
        from aegis import __version__

        return jsonify({"status": "ok", "version": __version__})

    @app.route("/api/system")
    def api_system():
        """Host info, CPU/RAM/GPU utilization for the server info badge."""
        import platform
        import socket
        import subprocess as _sp

        info: dict = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "cpu_pct": None,
            "ram_pct": None,
            "gpu": None,
        }

        # CPU and RAM
        try:
            import os as _os

            import psutil

            info["cpu_pct"] = round(psutil.cpu_percent(interval=0.1))
            info["cpu_cores"] = _os.cpu_count() or 0
            mem = psutil.virtual_memory()
            info["ram_pct"] = round(mem.percent)
            info["ram_total_gb"] = round(mem.total / (1024**3))
        except ImportError:
            pass

        # GPU
        try:
            out = _sp.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=5,
            ).strip()
            parts = [p.strip() for p in out.split(",")]
            if len(parts) >= 5:
                info["gpu"] = {
                    "name": parts[0],
                    "vram_total_mb": int(parts[1]),
                    "vram_used_mb": int(parts[2]),
                    "utilization_pct": int(parts[3]),
                    "temp_c": int(parts[4]),
                }
        except Exception:
            pass
        return jsonify(info)

    @app.route("/api/levels")
    def api_levels():
        """Fidelity levels 0-8 with short descriptions."""
        return jsonify(FIDELITY_LEVELS_API)

    @app.route("/api/body/info")
    def api_body_info():
        """Body mesh metadata without binary geometry."""
        body = _cache.get("body")
        if body is None:
            return jsonify({"error": "No body mesh loaded"}), 404

        bmin, bmax = body.bounding_box
        return jsonify(
            {
                "name": body.name,
                "n_triangles": body.n_triangles,
                "total_area": body.total_area,
                "bounding_box": {"min": bmin.tolist(), "max": bmax.tolist()},
            }
        )

    # --- Register route modules ---
    from aegis.viewer.routes import compute, data, location

    data.register(app, _cache, _cache_lock)
    compute.register(app, _cache, _cache_lock)
    location.register(app, _cache, _cache_lock)

    return app
