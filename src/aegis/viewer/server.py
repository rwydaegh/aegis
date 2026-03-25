"""Flask server for the AEGIS interactive viewer."""

from __future__ import annotations

import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, session

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


def create_app_from_env() -> Flask:
    """Factory for Gunicorn: reads config from environment variables."""
    from aegis.viewer.config import load_config

    data_dir = os.environ.get("AEGIS_DATA_DIR", "data")
    body_name = os.environ.get("AEGIS_BODY", "thelonious")
    config_path = os.environ.get("AEGIS_CONFIG")
    config = load_config(config_path) if config_path else None
    return create_app(data_dir=data_dir, body_name=body_name, config=config)


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

    # Session-based password gate
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

    _gate_password = os.environ.get("AEGIS_GATE_PASSWORD")
    _exempt_paths = {"/api/auth", "/api/health"}

    @app.before_request
    def check_auth():
        if _gate_password is None:
            return  # No password set, skip auth (local dev)
        if request.path in _exempt_paths:
            return
        if request.path.startswith("/assets/") or request.path == "/":
            return  # Serve React app and static assets without auth
        if not session.get("authenticated"):
            return jsonify({"error": "Authentication required"}), 401

    @app.route("/api/auth", methods=["GET", "POST"])
    def authenticate():
        if request.method == "GET":
            # Probe: is the current session valid?
            if _gate_password is None:
                return jsonify({"authenticated": True, "gate_enabled": False})
            if session.get("authenticated"):
                # Estimate remaining time from cookie max-age
                lifetime = app.config["PERMANENT_SESSION_LIFETIME"]
                expires_at = datetime.now(UTC) + lifetime
                return jsonify(
                    {
                        "authenticated": True,
                        "expires_at": expires_at.isoformat(),
                        "session_id": session.get("session_id", ""),
                    }
                )
            return jsonify({"authenticated": False}), 401

        # POST: login with password
        if _gate_password is None:
            return jsonify({"error": "No password configured"}), 500
        data = request.get_json(silent=True) or {}
        if data.get("password") != _gate_password:
            return jsonify({"error": "Wrong password"}), 401
        session.permanent = True
        session["authenticated"] = True
        session["session_id"] = str(uuid.uuid4())
        expires_at = datetime.now(UTC) + timedelta(hours=2)
        return jsonify(
            {
                "ok": True,
                "expires_at": expires_at.isoformat(),
                "session_id": session["session_id"],
            }
        )

    # Store pipeline config
    _cache["bbox_radius"] = bbox_radius
    _cache["pipeline_dir"] = pipeline_dir
    _cache["cache_dir"] = cache_dir
    _cache["data_dir"] = data_dir

    # Pre-load data
    print("Loading data...")

    with _cache_lock:
        # Preload all available bodies from data_dir
        available_bodies = [p.stem for p in Path(data_dir).glob("*.stl")]
        _cache["bodies"] = {}
        _cache["default_body"] = body_name
        for name in available_bodies:
            try:
                body = load_body(name, data_dir)
                binary, meta = body_to_binary(body)
                _cache["bodies"][name] = {"body": body, "binary": binary, "meta": meta}
                print(f"  Body: {body.name}, {body.n_triangles:,} triangles")
            except FileNotFoundError as e:
                print(f"  Warning: {e}")

        # Backward-compat aliases pointing at the default body
        default_entry = _cache["bodies"].get(body_name)
        if default_entry is not None:
            _cache["body"] = default_entry["body"]
            _cache["body_binary"] = default_entry["binary"]
            _cache["body_meta"] = default_entry["meta"]
        else:
            # Fallback: try loading the requested body_name even if not in glob results
            try:
                body = load_body(body_name, data_dir)
                binary, meta = body_to_binary(body)
                _cache["bodies"][body_name] = {"body": body, "binary": binary, "meta": meta}
                _cache["body"] = body
                _cache["body_binary"] = binary
                _cache["body_meta"] = meta
                print(f"  Body (fallback): {body.name}, {body.n_triangles:,} triangles")
            except FileNotFoundError as e:
                print(f"  Warning: {e}")
                _cache["body"] = None
                _cache["body_binary"] = None
                _cache["body_meta"] = None

    # Background-precompute averaging matrices so the first compute is fast.
    # Uses before_request hook to run once in the actual worker process
    # (gunicorn's preload_app forks after create_app, so a thread started
    # here would run in the master and its cache wouldn't be shared).
    _G_MAX_TRIANGLES = int(os.environ.get("AEGIS_G_MAX_TRIANGLES", 100_000))
    _g_precompute_started = {"done": False}

    @app.before_request
    def _maybe_precompute_G():
        if _g_precompute_started["done"]:
            return
        _g_precompute_started["done"] = True

        def _do():
            from aegis.engine import DosimetryEngine
            from aegis.geometry.averaging import precompute_averaging_matrix

            for name, entry in list(_cache.get("bodies", {}).items()):
                body = entry["body"]
                if body.n_triangles > _G_MAX_TRIANGLES:
                    app.logger.info("G(%s) skipped (%d > %d tri)", name, body.n_triangles, _G_MAX_TRIANGLES)
                    continue
                for area in [4e-4]:
                    key = (DosimetryEngine._body_cache_key(body), area)
                    if key not in DosimetryEngine._G_cache:
                        try:
                            G = precompute_averaging_matrix(body.centroids, body.areas, area)
                            DosimetryEngine._G_cache[key] = G
                            app.logger.info("G(%s, %dcm2) ready (%d nnz)", name, area * 1e4, G.nnz)
                        except Exception as e:
                            app.logger.warning("G(%s) failed: %s", name, e)

        import threading
        threading.Thread(target=_do, daemon=True, name="precompute-G").start()

    with _cache_lock:
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
    from aegis.viewer.routes import analysis, compute, data, location, mimo

    data.register(app, _cache, _cache_lock)
    compute.register(app, _cache, _cache_lock)
    location.register(app, _cache, _cache_lock)
    analysis.register(app, _cache, _cache_lock)
    mimo.register(app, _cache, _cache_lock)

    return app
