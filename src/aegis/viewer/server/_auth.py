"""Session-based password gate for the viewer Flask app."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, session

_EXEMPT_PATHS = {"/api/auth", "/api/health", "/api/sentry-webhook", "/robots.txt"}
_STATIC_EXTENSIONS = {".woff2", ".woff", ".ttf", ".svg", ".png", ".ico", ".js", ".css", ".json", ".wasm"}


def _path_is_exempt(path: str) -> bool:
    """Return True for paths that bypass the password gate."""
    if path in _EXEMPT_PATHS:
        return True
    if path.startswith(("/assets/", "/cesium/")) or path == "/":
        return True
    return not path.startswith("/api/") and Path(path).suffix in _STATIC_EXTENSIONS


def _auth_probe_response(app: Flask) -> tuple:
    """Respond to GET /api/auth with the current session's status."""
    if session.get("authenticated"):
        lifetime = app.config["PERMANENT_SESSION_LIFETIME"]
        expires_at = datetime.now(UTC) + lifetime
        return (
            jsonify(
                {
                    "authenticated": True,
                    "expires_at": expires_at.isoformat(),
                    "session_id": session.get("session_id", ""),
                }
            ),
            200,
        )
    return jsonify({"authenticated": False}), 401


def _auth_login_response(gate_password: str) -> tuple:
    """Respond to POST /api/auth by validating the submitted password."""
    data = request.get_json(silent=True) or {}
    if data.get("password") != gate_password:
        return jsonify({"error": "Wrong password"}), 401
    session.permanent = True
    session["authenticated"] = True
    session["session_id"] = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(hours=2)
    return (
        jsonify(
            {
                "ok": True,
                "expires_at": expires_at.isoformat(),
                "session_id": session["session_id"],
            }
        ),
        200,
    )


def setup_auth(app: Flask, gate_password: str | None) -> None:
    """Register the before_request auth check and /api/auth route."""
    if os.environ.get("AEGIS_PUBLIC_ACCESS") == "true":
        gate_password = None

    @app.before_request
    def check_auth():
        if gate_password is None:
            return
        if _path_is_exempt(request.path):
            return
        if not session.get("authenticated"):
            return jsonify({"error": "Authentication required"}), 401

    @app.route("/api/auth", methods=["GET", "POST"])
    def authenticate():
        if request.method == "GET":
            if gate_password is None:
                return jsonify({"authenticated": True, "gate_enabled": False})
            return _auth_probe_response(app)

        if gate_password is None:
            return jsonify({"error": "No password configured"}), 500
        return _auth_login_response(gate_password)
