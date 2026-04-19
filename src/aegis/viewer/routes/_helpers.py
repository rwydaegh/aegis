"""Shared helpers for Flask route handlers."""

from __future__ import annotations

from typing import Any

from flask import jsonify, request

from aegis.viewer.routes._types import RouteResponse


def get_json_dict() -> tuple[dict[str, Any], RouteResponse | None]:
    """Parse the request JSON body as a dict, or return a 400 error response.

    Usage:
        body, err = get_json_dict()
        if err is not None:
            return err

    Rationale: the legacy ``request.get_json(silent=True) or {}`` pattern
    crashes with 500 when the client posts a top-level JSON array or scalar,
    because subsequent ``body.get(...)`` calls raise AttributeError (found by
    Schemathesis fuzzing on /api/environment/combine and /api/optimize).
    """
    raw = request.get_json(silent=True)
    if raw is None:
        return {}, None
    if not isinstance(raw, dict):
        return {}, (jsonify({"error": "Request body must be a JSON object"}), 400)
    return raw, None
