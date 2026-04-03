"""Optimization SSE endpoint.

Streams optimization iterations as server-sent events.
POST /api/optimize - start optimization (returns text/event-stream)
POST /api/optimize/cancel - cancel running optimization
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import uuid
from typing import Any

import numpy as np
from flask import Flask, Response, jsonify, request, session

from aegis.optim.loop import run_optimization

logger = logging.getLogger(__name__)

_cancel_events: dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def _get_session_id() -> str:
    """Return a stable session ID for the current request.

    Uses Flask session if available, otherwise generates a UUID and stores it
    so subsequent requests from the same client can cancel a running optimization.
    """
    sid = session.get("session_id")
    if sid is None:
        sid = uuid.uuid4().hex
        session["session_id"] = sid
    return sid


def _json_safe(obj: Any) -> Any:
    """Make obj JSON-serializable (handle numpy types)."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def _encode_sab(sab: np.ndarray) -> str:
    """Encode float32 SAB array as base64."""
    return base64.b64encode(np.asarray(sab, dtype=np.float32).tobytes()).decode()


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach optimization routes to app."""

    @app.route("/api/optimize", methods=["POST"])
    def api_optimize():
        params = request.get_json(silent=True) or {}
        mode = params.get("mode")
        if not mode:
            return jsonify({"error": "mode is required"}), 400

        try:
            config = _build_config(params, app, cache, cache_lock)
        except (ValueError, KeyError) as e:
            return jsonify({"error": str(e)}), 400

        sid = _get_session_id()
        cancel = threading.Event()
        with _cancel_lock:
            if sid in _cancel_events:
                _cancel_events[sid].set()
            _cancel_events[sid] = cancel

        def generate():
            try:
                for result in run_optimization(config, cancel_event=cancel):
                    event = _json_safe(result)
                    if "sab" in event:
                        event["sab_b64"] = _encode_sab(result["sab"])
                        del event["sab"]
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                logger.exception("Optimization error")
                yield f"data: {json.dumps({'error': True, 'message': str(e)})}\n\n"
            finally:
                with _cancel_lock:
                    _cancel_events.pop(sid, None)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.route("/api/optimize/cancel", methods=["POST"])
    def api_optimize_cancel():
        sid = _get_session_id()
        with _cancel_lock:
            ev = _cancel_events.get(sid)
            if ev:
                ev.set()
                return jsonify({"cancelled": True})
        return jsonify({"cancelled": False})


def _build_config(params: dict, app: Flask, cache: dict, cache_lock) -> dict:
    """Parse request params into optimizer config dict."""
    mode = params["mode"]
    config: dict[str, Any] = {"mode": mode, "max_iters": params.get("max_iters", 50)}

    if mode == "mimo_peak":
        if "G_tilde_real" in params:
            G_real = np.array(params["G_tilde_real"])
            G_imag = np.array(params["G_tilde_imag"])
            config["G_tilde"] = G_real + 1j * G_imag
        else:
            with cache_lock:
                scene = cache.get("mimo_scene")
            if scene is None:
                raise ValueError("No MIMO scene cached. Run /api/mimo/compute first.")
            config["G_tilde"] = scene.G_tilde

        x_real = np.array(params.get("x_init_real", []))
        x_imag = np.array(params.get("x_init_imag", []))
        if x_real.size > 0:
            config["x_init"] = x_real + 1j * x_imag
        else:
            G = config["G_tilde"]
            config["x_init"] = G[0, 0, :]
            norm = np.linalg.norm(config["x_init"])
            if norm > 0:
                config["x_init"] = config["x_init"] / norm

        config["p_max"] = params.get("p_max", 1.0)
        config["signal_threshold"] = params.get("signal_threshold", 0.0)

    elif mode == "tilt_power":
        with cache_lock:
            last_result = app.config.get("_last_dosimetry_result")
            last_body = app.config.get("_last_dosimetry_body")
        if last_result is None or last_body is None:
            raise ValueError("No dosimetry result cached. Run /api/compute first.")

        paths = getattr(last_result, "_paths", None)
        if paths is None:
            raise ValueError("Cached result has no paths. Use RT compute first.")
        config["paths"] = paths
        config["normals"] = np.array(last_body.normals)
        config["antenna_direction"] = np.array(params.get("antenna_direction", [0, 0, -1]))
        config["tilt_init_deg"] = params.get("tilt_init_deg", 0.0)
        config["power_init_dbm"] = params.get("power_init_dbm", 60.0)
        config["icnirp_limit"] = params.get("icnirp_limit", 20.0)

    elif mode == "placement":
        config["center"] = np.array(params.get("center", [5, 0, 3]))
        config["grid_size"] = params.get("grid_size", 5)
        config["grid_spacing"] = params.get("grid_spacing", 2.0)
        config["constraint_axis"] = params.get("constraint_axis")
        config["constraint_value"] = params.get("constraint_value")
        if "evaluate_fn" not in params:
            raise ValueError("Placement mode requires RT integration (not yet available via API)")

    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    return config
