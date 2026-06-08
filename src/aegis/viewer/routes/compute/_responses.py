"""Response builders, sanitization and export caching for compute routes."""

from __future__ import annotations

import json
import logging
import warnings
from typing import Any

import numpy as np
from flask import Response, jsonify

from aegis.compliance import ExposureScenario, evaluate_compliance
from aegis.viewer.compute import _load_phantom_masses, collect_ecbf_warnings
from aegis.viewer.server import scoped_cache_set

logger = logging.getLogger(__name__)

_ErrResp = tuple[Response, int]

# String constants (avoid duplicate literals)
_OCTET_STREAM = "application/octet-stream"
_ERR_NO_BODY = "No body mesh loaded"
_ERR_NO_DIFFERT = "DiffeRT not installed"
_ERR_NO_EXPORT_DATA = "No dosimetry result available. Run a compute first."
_MAX_POWER_DBM = 100  # must match config.py dosimetry.power_input.max


def _sanitize_for_json(obj):
    """Recursively replace float inf/nan with None for valid JSON output."""
    import math

    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _json_dumps_safe(obj: object) -> str:
    """Serialize to valid JSON, replacing inf/nan with null.

    Python's json.dumps outputs non-standard ``Infinity``/``NaN`` tokens that
    JavaScript's ``JSON.parse`` rejects.
    """
    return json.dumps(_sanitize_for_json(obj))


def _cache_dosimetry_for_export(cache: dict, result, body, stats: dict, paths=None, tissue=None) -> None:
    """Cache the last dosimetry result, body, and stats for export (session-scoped).

    RT paths and tissue are always written (including ``None`` for non-RT
    computes) so the cache stays in sync with the current compute. Leaving
    stale RT paths alive after a non-RT compute would feed mismatched paths
    plus the new body into ``path_contributions`` / tilt-power optimization.
    """
    scoped_cache_set(cache, "_last_dosimetry_result", result)
    scoped_cache_set(cache, "_last_dosimetry_body", body)
    scoped_cache_set(cache, "_last_dosimetry_stats", stats)
    scoped_cache_set(cache, "_last_compliance_result", stats.get("compliance"))
    scoped_cache_set(cache, "_last_rt_paths", paths)
    scoped_cache_set(cache, "_last_rt_tissue", tissue)


def _diffraction_active(engine_kw: dict) -> bool:
    """True when a shadow-edge gate is active (legacy bool or non-"none" model)."""
    model = engine_kw.get("diffraction_model")
    return bool(engine_kw.get("diffraction")) or (model is not None and model != "none")


def _inject_curvature_H(engine_kw: dict, body) -> dict:
    """Add curvature_H to engine kwargs if curvature or diffraction is requested."""
    if engine_kw.get("curvature") or _diffraction_active(engine_kw):
        from aegis.viewer.compute import _compute_face_curvature

        engine_kw["curvature_H"] = _compute_face_curvature(body)
    return engine_kw


def _inject_bound_aggregate_params(engine_kw: dict, body) -> dict:
    """Add A_ab and D_max for bound/aggregate modes and legacy levels 0-1.

    The DosimetryEngine requires ``A_ab`` for aggregate/bound and ``D_max``
    for bound. Routes that don't go through the ``compute_dosimetry``
    wrapper (e.g. /api/compute/rt, placement optimizer) need these
    precomputed from the body geometry and viewer config.
    """
    import numpy as _np

    from aegis.viewer.config import DEFAULTS

    mode = engine_kw.get("mode")
    level = engine_kw.get("level")
    # Parameters are only needed for bound/aggregate modes or levels 0-1.
    needs_a_ab = mode in ("bound", "aggregate") or (level is not None and level <= 1)
    needs_d_max = mode == "bound" or level == 0
    if not needs_a_ab and not needs_d_max:
        return engine_kw

    dos_cfg = DEFAULTS.get("dosimetry", {})
    total_area = float(_np.sum(body.areas)) if hasattr(body, "areas") and body.areas is not None else 0.0

    if needs_a_ab and "A_ab" not in engine_kw:
        engine_kw["A_ab"] = total_area * dos_cfg.get("convex_body_area_factor", 0.5)
    if needs_d_max and "D_max" not in engine_kw:
        engine_kw["D_max"] = dos_cfg.get("level0_D_max", 1.64)
    return engine_kw


def _run_dosimetry(
    tissue, body, paths, engine_kw, *, ecbf_warnings_out: list[str] | None = None
) -> tuple[Any, _ErrResp | None]:
    """Instantiate engine, inject curvature, run compute, return result.

    Returns (result, None) on success, or (None, error_response) on failure.

    If ``ecbf_warnings_out`` is provided, captured ECBF/absorption-constraint
    warnings emitted by the dosimetry kernel (level 8) are appended to it.
    """
    from aegis.engine import DosimetryEngine

    engine = DosimetryEngine(tissue)
    _inject_curvature_H(engine_kw, body)
    _inject_bound_aggregate_params(engine_kw, body)
    body_mass = _load_phantom_masses().get(body.name) if body.name else None
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = engine.compute(body, paths, body_mass=body_mass, **engine_kw)
    except Exception as exc:
        logger.exception("Dosimetry compute failed")
        return None, (jsonify({"error": f"Dosimetry compute failed: {exc}"}), 500)
    if ecbf_warnings_out is not None:
        ecbf_warnings_out.extend(collect_ecbf_warnings(caught))
    return result, None


def _make_rt_response(
    result, body, tissue, engine_kw, quantities, scenario, extra, timing_pairs
) -> tuple[Response | None, dict[str, Any] | None, _ErrResp | None]:
    """Build binary Response with X-Stats header for RT route handlers.

    timing_pairs is a list of (key, value) timing entries to inject.
    Returns (response, stats, None) on success, or (None, None, error_response) on failure.
    """
    try:
        buf, arrays_meta = _build_binary_response(result, quantities)
        level_val, mode_val, corr_val = _stats_label(engine_kw)
        stats = _build_stats_response(
            result,
            body,
            tissue,
            level_val,
            mode=mode_val,
            corrections=corr_val,
            extra=extra,
            scenario=scenario,
        )
        timings: dict[str, Any] = stats.get("timings", {})
        for key, val in timing_pairs:
            timings[key] = val
        stats["timings"] = timings
        stats["arrays"] = arrays_meta
        resp = Response(bytes(buf), mimetype=_OCTET_STREAM)
        resp.headers["X-Stats"] = _json_dumps_safe(stats)
        resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
        return resp, stats, None
    except Exception as exc:
        logger.exception("Response build failed")
        return None, None, (jsonify({"error": f"Response build failed: {exc}"}), 500)


def _stats_label(engine_kwargs: dict) -> tuple:
    """Return (level_int, mode_str, corrections_list) for stats response."""
    if "mode" in engine_kwargs:
        mode = engine_kwargs["mode"]
        corrections = [k for k in ("fresnel", "polarisation", "curvature") if engine_kwargs.get(k)]
        if _diffraction_active(engine_kwargs):
            corrections.append("diffraction")
        return (None, mode, corrections)
    return (engine_kwargs.get("level", 2), None, [])


def _build_binary_response(result, quantities):
    """Assemble multi-array binary buffer from a DosimetryResult.

    Returns (buf, arrays_meta) where arrays_meta is a list of
    {"key": str, "offset": int, "length": int} dicts describing each array
    in the buffer.
    """
    buf = bytearray()
    arrays_meta = []

    # sab is always included
    sab_arr = result.sab.astype(np.float32)
    sab_bytes = sab_arr.tobytes()
    arrays_meta.append({"key": "sab", "offset": 0, "length": sab_arr.shape[0]})
    buf.extend(sab_bytes)

    quantity_map = {
        "sab_4cm2": lambda: result.sab_averaged,
        "sab_1cm2": lambda: result.sab_1cm2_averaged,
        "sinc_local": lambda: result.sinc,
        "sinc_wb": lambda: result.sinc_averaged,
    }

    for key in quantities:
        if key == "sab":
            continue  # already included
        getter = quantity_map.get(key)
        if getter is None:
            continue
        arr = getter()
        if arr is None:
            continue
        arr_f32 = arr.astype(np.float32)
        arr_bytes = arr_f32.tobytes()
        arrays_meta.append({"key": key, "offset": len(buf), "length": arr_f32.shape[0]})
        buf.extend(arr_bytes)

    return buf, arrays_meta


def _build_stats_response(
    result, body, tissue, level, extra=None, mode=None, corrections=None, scenario=None
) -> dict[str, Any]:
    """Build the X-Stats JSON dict from a DosimetryResult."""
    freq_hz = result.freq_hz or tissue.freq_hz
    scenario = scenario or ExposureScenario.GENERAL_PUBLIC

    # Centralized compliance kwargs extraction (prevents callers forgetting params)
    ckw = result.compliance_kwargs(body=body)

    try:
        compliance = evaluate_compliance(scenario=scenario, freq_hz=freq_hz, **ckw)
    except (ValueError, TypeError):
        compliance = None

    # Per-quantity peaks for the stats response (reuse from compliance_kwargs where possible)
    peak_sab_averaged = ckw["sab_4cm2"]
    peak_sab_1cm2 = ckw["sab_1cm2"]
    peak_sinc_local = float(np.max(result.sinc)) if result.sinc is not None and result.sinc.size > 0 else None
    peak_sinc_averaged = (
        float(np.max(result.sinc_averaged))
        if result.sinc_averaged is not None and result.sinc_averaged.size > 0
        else None
    )

    stats = {
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "peak_sab_averaged": peak_sab_averaged,
        "compliance": {
            "overall_pass": compliance.overall_pass,
            "margin_db": compliance.margin_db if compliance.margin_db != float("inf") else None,
            "scenario": scenario.value,
            "freq_hz": freq_hz,
            "checks": [
                {
                    "label": c.label,
                    "value": round(c.value, 4),
                    "limit": round(c.limit, 4),
                    "unit": c.unit,
                    "pass": c.compliant,
                    "ratio": round(c.ratio, 10),
                    "margin_db": round(c.margin_db, 2) if c.margin_db != float("inf") else None,
                }
                for c in compliance.all_checks
            ],
        }
        if compliance is not None
        else None,
        "compliant": compliance.overall_pass if compliance is not None else None,
        "warning": "Frequency outside ICNIRP 2020 range (100 kHz to 300 GHz); compliance not evaluated."
        if compliance is None
        else None,
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level if level is not None else 0,
        "T0": float(tissue.T0),
        "tissue_eps_r": tissue.eps_r,
        "tissue_sigma": tissue.sigma,
    }

    # Exposure distribution statistics
    if result.sab.size > 0:
        sab_arr = result.sab
        n_illum = int(np.sum(sab_arr > 0))
        sab_nonzero = sab_arr[sab_arr > 0]
        stats["distribution"] = {
            "mean": float(np.mean(sab_arr)),
            "median": float(np.median(sab_arr)),
            "p95": float(np.percentile(sab_arr, 95)),
            "p99": float(np.percentile(sab_arr, 99)),
            "illuminated_fraction": n_illum / sab_arr.size,
            "illuminated_area_cm2": float(np.sum(body.areas[sab_arr > 0]) * 1e4)
            if hasattr(body, "areas") and body.areas is not None
            else None,
            "illuminated_mean": float(np.mean(sab_nonzero)) if sab_nonzero.size > 0 else 0.0,
            "illuminated_p50": float(np.median(sab_nonzero)) if sab_nonzero.size > 0 else 0.0,
        }

    # Per-quantity peak values (reuse precomputed values)
    peaks = {"sab": float(result.peak_sab)}
    if peak_sab_averaged is not None:
        peaks["sab_4cm2"] = peak_sab_averaged
    if peak_sab_1cm2 is not None:
        peaks["sab_1cm2"] = peak_sab_1cm2
    if peak_sinc_local is not None:
        peaks["sinc_local"] = peak_sinc_local
    if peak_sinc_averaged is not None:
        peaks["sinc_wb"] = peak_sinc_averaged
    stats["peaks"] = peaks

    if mode is not None:
        stats["mode"] = mode
    if corrections:
        stats["corrections"] = corrections
    if extra:
        stats.update(extra)
    return stats


def _zero_paths_response(body, tissue, level, extra=None, cache=None):
    """Build stats dict when zero paths are found."""
    n_tri = body.n_triangles
    stats = {
        "p_abs": 0,
        "p_abs_mw": 0,
        "peak_sab": 0,
        "compliant": True,
        "n_illuminated": 0,
        "n_triangles": n_tri,
        "level": level,
        "S_inc": 0,
        "distance_m": 0,
        "T0": tissue.T0,
        "n_rt_paths": 0,
        "path_viz": [],
        "arrays": [{"key": "sab", "offset": 0, "length": n_tri}],
        "peaks": {"sab": 0.0},
        "distribution": {
            "mean": 0.0,
            "median": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "illuminated_fraction": 0.0,
            "illuminated_area_cm2": 0.0,
            "illuminated_mean": 0.0,
            "illuminated_p50": 0.0,
        },
    }
    if extra:
        stats.update(extra)
    # Clear stale export cache so subsequent CSV/JSON/NPZ exports
    # reflect the zero-result instead of serving old data
    if cache is not None:
        scoped_cache_set(cache, "_last_dosimetry_result", None)
        scoped_cache_set(cache, "_last_dosimetry_body", None)
        scoped_cache_set(cache, "_last_dosimetry_stats", None)
        scoped_cache_set(cache, "_last_compliance_result", None)
        scoped_cache_set(cache, "_last_rt_paths", None)
        scoped_cache_set(cache, "_last_rt_tissue", None)
    sab_bytes = np.zeros(body.n_triangles, dtype=np.float32).tobytes()
    resp = Response(sab_bytes, mimetype=_OCTET_STREAM)
    resp.headers["X-Stats"] = _json_dumps_safe(stats)
    resp.headers["Access-Control-Expose-Headers"] = "X-Stats"
    return resp
