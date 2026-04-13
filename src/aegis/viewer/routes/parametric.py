"""Routes for parametric body generation (SMPL-X, Anny)."""

import json

import numpy as np
from flask import jsonify, request

from aegis.viewer.scene_data import body_to_binary


def register(app, cache, cache_lock):
    @app.route("/api/parametric-body", methods=["POST"])
    def api_parametric_body():
        """Generate a parametric body mesh from shape/pose parameters."""
        from aegis.geometry.parametric import ParametricBody

        params = request.get_json(silent=True) or {}
        model_type = params.get("model", "smplx")
        gender = params.get("gender", "neutral")

        _VALID_MODELS = {"smplx", "anny"}
        _VALID_GENDERS = {"neutral", "male", "female"}
        if model_type not in _VALID_MODELS:
            return jsonify({"error": f"model must be one of {sorted(_VALID_MODELS)}"}), 400
        if gender not in _VALID_GENDERS:
            return jsonify({"error": f"gender must be one of {sorted(_VALID_GENDERS)}"}), 400

        raw_betas = params.get("betas", [0.0] * 10)
        if not isinstance(raw_betas, list) or len(raw_betas) > 300:
            return jsonify({"error": "betas must be a list of at most 300 values"}), 400
        betas = np.array(raw_betas, dtype=np.float64)
        if not np.all(np.isfinite(betas)):
            return jsonify({"error": "betas must contain finite values"}), 400

        pose = params.get("pose")
        if pose is not None:
            if not isinstance(pose, list) or len(pose) > 600:
                return jsonify({"error": "pose must be a list with at most 600 elements"}), 400
            pose = np.array(pose, dtype=np.float64)
            if pose.size > 500 or not np.all(np.isfinite(pose)):
                return jsonify({"error": "pose must contain at most 500 finite values"}), 400

        try:
            pb = ParametricBody.load(model_type, gender)
        except (FileNotFoundError, NotImplementedError, ImportError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

        body = pb.generate(betas, pose=pose, name=f"{model_type}_{gender}")
        binary, meta = body_to_binary(body)

        resp = app.make_response(binary)
        resp.headers["Content-Type"] = "application/octet-stream"
        resp.headers["X-Meta"] = json.dumps(meta)
        return resp
