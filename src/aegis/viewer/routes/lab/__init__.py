"""Exposure Lab blueprint: posable-phantom dosimetry sandbox.

All heavy imports (torch, smplx, the nearfield kernel) are lazy inside handlers
so non-lab requests never pay the RAM.
"""

import numpy as np
from flask import Flask, jsonify, request


def register(app: Flask, cache: dict, cache_lock) -> None:
    from . import _patterns

    @app.route("/api/lab/nf-patterns")
    def api_lab_nf_patterns():
        return jsonify({"patterns": _patterns.list_patterns()})

    @app.route("/api/lab/presets")
    def api_lab_presets():
        from ._presets import POSE_PRESETS

        return jsonify(POSE_PRESETS)

    @app.route("/api/lab/pattern_lobe")
    def api_lab_pattern_lobe():
        pid = request.args.get("id", "dipole")
        freq_mhz = request.args.get("freq_mhz", type=float)
        n_theta = max(2, min(request.args.get("n_theta", default=32, type=int), 90))
        n_phi = max(2, min(request.args.get("n_phi", default=64, type=int), 180))
        try:
            pat = _patterns.get_pattern(pid, freq_mhz)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        theta = np.linspace(0.0, np.pi, n_theta)
        phi = np.linspace(-np.pi, np.pi, n_phi)
        th, ph = np.meshgrid(theta, phi, indexing="xy")  # (n_phi, n_theta)
        dirs = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], axis=-1)
        r = np.asarray(pat.sample(dirs))
        return jsonify({"theta": theta.tolist(), "phi": phi.tolist(), "r": r.tolist()})

    @app.route("/api/lab/compute", methods=["POST"])
    def api_lab_compute():
        from aegis.viewer.routes._helpers import get_json_dict
        from aegis.viewer.routes.compute._responses import (
            _build_binary_response,
            _build_stats_response,
            _json_dumps_safe,
        )

        from . import _compute

        params, err = get_json_dict()
        if err is not None:
            return err
        try:
            body, tissue, result, extra = _compute.compute_lab(params)
        except (KeyError, ValueError, FileNotFoundError, ImportError) as e:
            return jsonify({"error": str(e)}), 400
        quantities = params.get("quantities", ["sab", "sab_4cm2"])
        buf, arrays_meta = _build_binary_response(result, quantities)
        stats = _build_stats_response(result, body, tissue, None, mode="spatial")
        stats["arrays"] = arrays_meta
        timings = extra.get("timings")
        if timings is not None:
            timings["payload_bytes"] = len(buf)
            stats["timings"] = timings
        resp = app.make_response(bytes(buf))
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp

    @app.route("/api/lab/rig")
    def api_lab_rig():
        from . import _rig

        gender = request.args.get("gender", "neutral")
        if gender not in {"neutral", "male", "female"}:
            return jsonify({"error": "gender must be neutral, male, or female"}), 400
        raw = request.args.get("betas", "")
        try:
            betas = np.array([float(x) for x in raw.split(",") if x], dtype=np.float64) if raw else np.zeros(10)
        except ValueError:
            return jsonify({"error": "betas must be comma-separated numbers"}), 400
        try:
            return jsonify(_rig.build_rig(gender, betas))
        except (FileNotFoundError, ImportError) as e:
            return jsonify({"error": str(e)}), 400
