"""Request parameter parsers for compute routes."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from flask import Response, jsonify
from numpy.typing import NDArray

from aegis.compliance import ExposureScenario
from aegis.defaults import DEFAULT_FREQ_HZ

_ErrResp = tuple[Response, int]

# String constants (avoid duplicate literals)
_ERR_VEC3_LEN = "must be a 3-element array [x, y, z]"
_ERR_VEC3_TYPE = "must be a 3-element numeric array"
_ERR_INVALID_JSON = "Invalid or missing JSON body"
_ERR_ROTATION_TYPE = "body_rotation_y must be a number"
_ERR_INVALID_SCENE = "Invalid scene path. Use /api/scenes to list available scenes."


def _parse_bool(value, default: bool) -> bool:
    """Parse a boolean from JSON params, handling string 'false'/'true'."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "no", "")
    return bool(value)


_VALID_DIFFRACTION_MODELS = ("none", "gelu", "fock")
_VALID_INTER_BODY = ("off", "specular1")


def _parse_diffraction_model(params: dict) -> tuple[str | None, _ErrResp | None]:
    """Resolve the shadow-edge gate selector from request params.

    An explicit ``diffraction_model`` wins. Otherwise the legacy ``diffraction``
    bool maps ``True -> "fock"`` and ``False -> "none"``. Returns
    ``(model, None)`` on success or ``(None, error_response)`` on failure.
    """
    raw = params.get("diffraction_model")
    if raw is not None:
        if not isinstance(raw, str) or raw not in _VALID_DIFFRACTION_MODELS:
            return None, (
                jsonify({"error": f"diffraction_model must be one of: {', '.join(_VALID_DIFFRACTION_MODELS)}"}),
                400,
            )
        return raw, None
    return ("fock" if _parse_bool(params.get("diffraction"), False) else "none"), None


def _parse_inter_body(params: dict) -> tuple[str | None, _ErrResp | None]:
    """Parse the inter-body backend selector. Returns ``(value, None)`` or ``(None, error)``."""
    raw = params.get("inter_body", "off")
    if not isinstance(raw, str) or raw not in _VALID_INTER_BODY:
        return None, (
            jsonify({"error": f"inter_body must be one of: {', '.join(_VALID_INTER_BODY)}"}),
            400,
        )
    return raw, None


def _validate_scene_path(scene_path: str) -> bool:
    """Check that scene_path matches a known scene from list_available_scenes.

    Prevents path traversal attacks where a user-supplied path could read
    arbitrary files from the server filesystem.
    """
    from pathlib import Path as _Path

    try:
        from aegis.viewer.raytracer import list_available_scenes

        allowed = {s["path"] for s in list_available_scenes()}
    except ImportError:
        return False
    # A path that cannot even be resolved (embedded null byte, malformed UTF-8,
    # OS-level error) is by definition not one of our known scenes. Treat it as
    # invalid rather than letting ``Path.resolve`` raise a raw 500. Schemathesis
    # found ``scene_path`` containing a null byte crashed this with ValueError.
    try:
        resolved = str(_Path(scene_path).resolve())
        allowed_resolved = {str(_Path(p).resolve()) for p in allowed}
    except (ValueError, OSError):
        return False
    return resolved in allowed_resolved


# Position-vector components live in meters in an engine-local frame. Even
# planet-scale coordinates are well under 1e8 m. ``np.linalg.norm`` overflows
# to ``inf`` when components approach ``~1e154``, at which point
# ``direction / norm`` produces NaNs that propagate into k_hat and later raise
# deep in PropagationPaths.from_powers as an unhandled 500. Cap at 1e12 m -
# astronomically permissive (~100 AU) while leaving 140 orders of magnitude
# of headroom before overflow.
_MAX_POSITION_ABS_M = 1e12


def _parse_vec3(
    params: dict, key: str, default: list | None = None
) -> tuple[NDArray[np.float64] | None, _ErrResp | None]:
    """Parse a 3-element numeric array from request params.

    Returns (np.ndarray, None) on success or (None, error_response) on failure.
    """
    default = default or [0, 0, 0]
    try:
        raw = list(params.get(key, default))
        if len(raw) != 3:
            return None, (jsonify({"error": f"{key} {_ERR_VEC3_LEN}"}), 400)
        values = [float(v) for v in raw]
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{key} {_ERR_VEC3_TYPE}"}), 400)
    if not all(math.isfinite(v) for v in values):
        return None, (jsonify({"error": f"{key} values must be finite"}), 400)
    if any(abs(v) > _MAX_POSITION_ABS_M for v in values):
        return None, (
            jsonify({"error": f"{key} components must have magnitude <= {_MAX_POSITION_ABS_M:g} m"}),
            400,
        )
    return np.array(values, dtype=np.float64), None


def _parse_rotation_y(params: dict) -> tuple[float | None, _ErrResp | None]:
    """Parse body_rotation_y from request params.

    Returns (float, None) on success or (None, error_response) on failure.
    """
    try:
        value = float(params.get("body_rotation_y", 0.0))
    except (TypeError, ValueError):
        return None, (jsonify({"error": _ERR_ROTATION_TYPE}), 400)
    if not math.isfinite(value):
        return None, (jsonify({"error": "body_rotation_y must be finite"}), 400)
    return value, None


def _parse_freq_and_tissue(
    params: dict, default_freq: float = DEFAULT_FREQ_HZ
) -> tuple[Any, float | None, _ErrResp | None]:
    """Parse freq_hz and resolve tissue model from request params.

    Returns (tissue, freq_hz, None) on success or (None, None, error_response) on failure.
    """
    from aegis.viewer.compute import resolve_skin_model

    try:
        freq_hz = float(params.get("freq_hz", default_freq))
    except (TypeError, ValueError):
        return None, None, (jsonify({"error": "freq_hz must be a number"}), 400)
    if not math.isfinite(freq_hz) or freq_hz <= 0:
        return None, None, (jsonify({"error": "freq_hz must be positive and finite"}), 400)
    # Reject subnormal/near-zero positives that underflow ``omega * EPS_0`` to
    # 0 downstream in ``fresnel.n_complex`` (Python scalar division by zero
    # raises on the complex path). Schemathesis found ``freq_hz=5e-324``
    # crashed /api/compute with ``ZeroDivisionError`` -> 500.
    from aegis.constants import EPS_0

    if 2 * math.pi * freq_hz * EPS_0 <= 0.0:
        return None, None, (jsonify({"error": "freq_hz is too small to compute tissue properties"}), 400)
    # Reject frequencies above the ICNIRP 2020 upper limit (300 GHz). Extreme
    # values overflow Cole-Cole model arithmetic -> 500. Schemathesis found
    # freq_hz=1.16e307 caused this.
    _MAX_FREQ_HZ = 300e9
    if freq_hz > _MAX_FREQ_HZ:
        return None, None, (jsonify({"error": f"freq_hz must be at most {_MAX_FREQ_HZ:.0e} Hz (300 GHz)"}), 400)

    skin_model_name = params.get("skin_model", "itis")
    try:
        tissue = resolve_skin_model(skin_model_name, freq_hz)
    except ValueError as exc:
        return None, None, (jsonify({"error": str(exc)}), 400)

    return tissue, freq_hz, None


def _parse_quantities_and_scenario(
    params: dict,
) -> tuple[Any, ExposureScenario | None, _ErrResp | None]:
    """Parse display quantities and exposure scenario from request params.

    Returns (quantities, scenario, None) on success or (None, None, error_response) on failure.
    """
    quantities = params.get("quantities", ["sab", "sab_4cm2"])
    scenario_str = params.get("exposure_scenario", "general_public")
    try:
        scenario = ExposureScenario(scenario_str)
    except ValueError:
        return None, None, (jsonify({"error": f"Invalid exposure_scenario: {scenario_str}"}), 400)
    return quantities, scenario, None


_VALID_INCOHERENT_MODES = {"bound", "aggregate", "spatial"}


def _parse_mode_or_level(params: dict, default_level: int = 2) -> tuple[dict[str, Any] | None, _ErrResp | None]:
    """Extract mode+corrections or level from request params.

    Returns (engine_kw, None) on success or (None, error_response) on failure.
    """
    mode = params.get("mode")
    if mode is not None:
        if mode not in _VALID_INCOHERENT_MODES:
            return None, (
                jsonify({"error": f"mode must be one of: {', '.join(sorted(_VALID_INCOHERENT_MODES))}"}),
                400,
            )
        out: dict = {"mode": mode}
        if mode == "spatial":
            out["fresnel"] = _parse_bool(params.get("fresnel"), True)
            out["polarisation"] = _parse_bool(params.get("polarisation"), False)
            out["curvature"] = _parse_bool(params.get("curvature"), False)
            diffraction_model, err = _parse_diffraction_model(params)
            if err is not None:
                return None, err
            out["diffraction_model"] = diffraction_model
            inter_body, err = _parse_inter_body(params)
            if err is not None:
                return None, err
            out["inter_body"] = inter_body
        return out, None
    try:
        level = int(params.get("level", default_level))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "level must be an integer"}), 400)
    if level < 0 or level > 8:
        return None, (jsonify({"error": "level must be between 0 and 8"}), 400)
    return {"level": level}, None
