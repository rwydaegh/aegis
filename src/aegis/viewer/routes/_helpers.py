"""Shared helpers for Flask route handlers."""

from __future__ import annotations

from typing import Any

from flask import current_app, jsonify, request

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
    Schemathesis fuzzing on /api/environment/combine and /api/optimize). An
    empty body is still treated as an empty dict with no error. Parse failures
    (malformed JSON, or non-finite literals rejected by ``StrictJSONProvider``)
    surface as 400 instead of silently falling through to defaults.
    """
    raw_bytes = request.get_data(cache=True)
    if not raw_bytes or not raw_bytes.strip():
        return {}, None
    try:
        parsed = current_app.json.loads(raw_bytes)
    except ValueError as exc:
        return {}, (jsonify({"error": f"Invalid JSON body: {exc}"}), 400)
    if parsed is None:
        return {}, None
    if not isinstance(parsed, dict):
        return {}, (jsonify({"error": "Request body must be a JSON object"}), 400)
    return parsed, None
