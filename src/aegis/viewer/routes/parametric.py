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
        betas = np.array(params.get("betas", [0.0] * 10), dtype=np.float64)
        pose = params.get("pose")
        if pose is not None:
            pose = np.array(pose, dtype=np.float64)

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
