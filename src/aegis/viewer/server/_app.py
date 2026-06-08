"""Flask app factory and lightweight inline routes for the AEGIS viewer."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

from aegis.viewer.config import DEFAULTS as _VIEWER_DEFAULTS

from ._auth import setup_auth
from ._bodies import preload_bodies
from ._cache import _cache, _cache_lock
from ._fidelity import FIDELITY_LEVELS_API
from ._precompute import setup_precompute_G
from ._voxels import preload_voxels


class StrictJSONProvider(DefaultJSONProvider):
    """JSON provider that rejects ``NaN``/``Infinity``/``-Infinity`` literals in
    request bodies. Python's :mod:`json` accepts these by default as a
    non-standard RFC 8259 extension, which lets non-finite floats slip past
    every downstream route's ``math.isfinite`` guard. Rejecting them at the
    parser is a single choke point that replaces per-field per-route checks.

    Only ``loads`` is overridden; ``dumps`` still permits NaN so routes that
    intentionally emit masked NaNs (e.g. out-of-ROI spatial averaging) are
    unchanged.
    """

    @staticmethod
    def _reject_non_finite(constant: str) -> float:
        raise ValueError(f"non-finite JSON literal {constant!r} is not allowed in request bodies")

    def loads(self, s: str | bytes, **kwargs: Any) -> Any:
        kwargs.setdefault("parse_constant", self._reject_non_finite)
        return super().loads(s, **kwargs)


_PROCESS_WAIT_TIMEOUT_S = _VIEWER_DEFAULTS["server"]["process_wait_timeout_s"]

_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval' blob: "
    "https://analytics.waves-ugent.be https://maps.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com "
    "https://*.google.com https://*.cesium.com https://*.cesium.org "
    "https://*.virtualearth.net; "
    "font-src 'self' data: https://fonts.gstatic.com; "
    "connect-src 'self' blob: https://analytics.waves-ugent.be "
    "https://*.sentry.io https://tile.googleapis.com "
    "https://*.googleapis.com "
    "https://*.cesium.com https://*.cesium.org https://*.virtualearth.net; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'"
)


def _resolve_secret_key() -> str:
    secret_key = os.environ.get("FLASK_SECRET_KEY", "")
    if secret_key:
        return secret_key
    if os.environ.get("FLASK_ENV") == "development" or not os.environ.get("AEGIS_GATE_PASSWORD"):
        return "dev-secret-key-change-me"

    import secrets
    import warnings

    warnings.warn(
        "FLASK_SECRET_KEY is not set in production. Generating a random key. "
        "Sessions will not survive restarts. Set FLASK_SECRET_KEY for stable sessions.",
        stacklevel=2,
    )
    return secrets.token_hex(32)


def _configure_app(app: Flask) -> None:
    app.secret_key = _resolve_secret_key()
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") != "development"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", _CSP_POLICY)
        return response


def _register_inline_routes(app: Flask) -> None:
    @app.route("/robots.txt")
    def robots_txt():
        return app.send_static_file("robots.txt")

    @app.route("/api/health")
    def api_health():
        from aegis import __version__

        return jsonify({"status": "ok", "version": __version__})

    @app.route("/api/system")
    def api_system():
        return jsonify(_system_info())

    @app.route("/api/levels")
    def api_levels():
        return jsonify(FIDELITY_LEVELS_API)

    @app.route("/api/openapi.json")
    def api_openapi_json():
        from aegis.viewer.openapi import build_openapi_spec

        return jsonify(build_openapi_spec())

    @app.route("/api/body/info")
    def api_body_info():
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


def _system_info() -> dict:
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
        "git_commit": os.environ.get("AEGIS_GIT_COMMIT"),
    }

    try:
        import os as _os

        import psutil

        info["cpu_pct"] = round(psutil.cpu_percent(interval=None))
        info["cpu_cores"] = _os.cpu_count() or 0
        mem = psutil.virtual_memory()
        info["ram_pct"] = round(mem.percent)
        info["ram_total_gb"] = round(mem.total / (1024**3))
    except ImportError:
        pass

    try:
        out = _sp.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=_PROCESS_WAIT_TIMEOUT_S,
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
    return info


def _register_route_modules(app: Flask) -> None:
    from aegis.viewer.routes import (
        analysis,
        basestations,
        bugreport,
        compute,
        coverage,
        data,
        environment,
        lab,
        location,
        mimo,
        optimize,
        parametric,
        patterns,
        sentry_webhook,
        terrain,
    )

    for module in (
        data,
        compute,
        location,
        analysis,
        mimo,
        environment,
        basestations,
        coverage,
        parametric,
        patterns,
        sentry_webhook,
        terrain,
        optimize,
        bugreport,
        lab,
    ):
        module.register(app, _cache, _cache_lock)


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
    from aegis.viewer.config import _deep_merge, load_config
    from aegis.viewer.scene_data import set_config as set_scene_config

    config = load_config() if config is None else _deep_merge(load_config(), config)
    _cache["config"] = config
    set_scene_config(config)

    template_dir = str(Path(__file__).parent.parent / "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.json = StrictJSONProvider(app)
    _configure_app(app)
    setup_auth(app, os.environ.get("AEGIS_GATE_PASSWORD"))
    _register_security_headers(app)

    _cache["bbox_radius"] = bbox_radius
    _cache["pipeline_dir"] = pipeline_dir
    _cache["cache_dir"] = cache_dir
    _cache["data_dir"] = data_dir

    print("Loading data...")
    preload_bodies(data_dir, body_name, _cache, _cache_lock)
    preload_voxels(voxel_json, voxel_dir, bbox_radius, _cache, _cache_lock)
    setup_precompute_G(app, _cache)

    _register_inline_routes(app)
    _register_route_modules(app)
    return app


def create_app_from_env() -> Flask:
    """Factory for Gunicorn: reads config from environment variables."""
    from aegis.viewer.config import load_config

    data_dir = os.environ.get("AEGIS_DATA_DIR", "data")
    body_name = os.environ.get("AEGIS_BODY", "thelonious")
    config_path = os.environ.get("AEGIS_CONFIG")
    config = load_config(config_path) if config_path else None
    return create_app(data_dir=data_dir, body_name=body_name, config=config)
