"""Analysis routes: compliance utilities, tissue spectrum."""

from __future__ import annotations

import logging
import math

import numpy as np
from flask import Flask, jsonify, request

from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.routes._types import RouteResponse
from aegis.viewer.server import scoped_cache_get

logger = logging.getLogger(__name__)

_VALID_SCENARIOS = {"general_public", "occupational"}


def _finite_or_none(v):
    """Replace inf/NaN with None for JSON-safe output."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def _sanitize_list(lst):
    """Replace inf/NaN with None in a list (possibly nested)."""
    out = []
    for v in lst:
        if isinstance(v, list):
            out.append(_sanitize_list(v))
        elif isinstance(v, float) and not math.isfinite(v):
            out.append(None)
        else:
            out.append(v)
    return out


def _reject_non_finite(pairs):
    """Reject NaN/Inf floats at the boundary.

    Flask's `type=float` accepts "NaN"/"Infinity" strings, which silently
    propagate into compliance math and produce all-True/all-False payloads.
    Returns a 400 response tuple on failure or None on success.
    """
    for name, val in pairs:
        if val is not None and not math.isfinite(val):
            return jsonify({"error": f"{name} must be finite"}), 400
    return None


def _compliance_limits_impl(cache: dict, cache_lock) -> RouteResponse:
    """Query ICNIRP 2020 limits at an arbitrary frequency/scenario."""
    from aegis.compliance import ExposureScenario, icnirp_limits

    freq_hz = request.args.get("freq_hz", type=float)
    if freq_hz is None:
        return jsonify({"error": "freq_hz is required"}), 400
    if freq_hz <= 0:
        return jsonify({"error": "freq_hz must be positive"}), 400

    scenario_str = request.args.get("scenario", "general_public")
    if scenario_str not in _VALID_SCENARIOS:
        return jsonify({"error": f"scenario must be one of {sorted(_VALID_SCENARIOS)}"}), 400
    scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

    try:
        limits = icnirp_limits(scenario=scenario, freq_hz=freq_hz)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "scenario": scenario_str,
            "freq_hz": freq_hz,
            "sab_4cm2": limits.sab_4cm2,
            "sab_1cm2": limits.sab_1cm2,
            "sar_wb": limits.sar_wb,
            "sinc_local": limits.sinc_local,
            "sinc_whole_body": limits.sinc_whole_body,
        }
    )


def _compliance_summary_impl(cache: dict, cache_lock) -> RouteResponse:
    """Human-readable compliance summary text from last compute."""
    last = scoped_cache_get(cache, "_last_compliance_result")
    if last is None:
        return jsonify(
            {
                "text": (
                    "ICNIRP 2020 Compliance Summary\n"
                    + "=" * 40
                    + "\n\n"
                    + "Compliance not evaluated.\n"
                    + "Frequency outside ICNIRP 2020 absorbed power density range "
                    "(applicable from 6 GHz to 300 GHz).\n\n"
                    + "Run a simulation at a frequency >= 6 GHz to generate a compliance report."
                )
            }
        )

    tx_dbm = request.args.get("tx_power_dbm", type=float)

    # Build a text summary from the stored compliance dict
    lines = ["ICNIRP 2020 Compliance Summary", "=" * 40]
    scenario = last.get("scenario", "general_public")
    freq_hz = last.get("freq_hz", 0)
    lines.append(f"Scenario: {scenario.replace('_', ' ').title()}")
    lines.append(f"Frequency: {freq_hz / 1e9:.1f} GHz")
    if tx_dbm is not None:
        lines.append(f"TX power: {tx_dbm:.1f} dBm")
    lines.append("")

    checks = last.get("checks", [])
    for c in checks:
        status = "PASS" if c.get("pass") else "FAIL"
        lines.append(f"  {c['label']}: {c['value']:.2f} / {c['limit']:.2f} {c['unit']}  [{status}]")

    overall = last.get("overall_pass")
    margin = last.get("margin_db")
    lines.append("")
    overall_str = "N/A" if overall is None else ("PASS" if overall else "FAIL")
    lines.append(f"Overall: {overall_str}")
    if margin is not None:
        lines.append(f"Margin: {margin:+.1f} dB")

    return jsonify({"text": "\n".join(lines)})


def _tissue_spectrum_impl(cache: dict, cache_lock) -> RouteResponse:
    """Vectorized tissue properties vs frequency."""
    from aegis.tissue.database import get_tissue_spectrum

    tissue = request.args.get("tissue", "Skin")
    f_min = request.args.get("f_min", 1e9, type=float)
    f_max = request.args.get("f_max", 100e9, type=float)
    n = request.args.get("n", 100, type=int)
    skin_model = request.args.get("skin_model", "itis")
    n = min(max(n, 10), 1000)

    if not (math.isfinite(f_min) and math.isfinite(f_max)):
        return jsonify({"error": "f_min and f_max must be finite"}), 400
    if f_min <= 0 or f_max <= 0:
        return jsonify({"error": "f_min and f_max must be positive"}), 400
    if f_min >= f_max:
        return jsonify({"error": "f_min must be less than f_max"}), 400

    try:
        freqs = np.linspace(f_min, f_max, n)
        result = get_tissue_spectrum(tissue, freqs)

        # Apply skin model adjustments when tissue is Skin
        if tissue == "Skin" and skin_model != "itis":
            from aegis.constants import EPS_0 as eps_0

            omega = 2 * np.pi * freqs
            if skin_model == "christ2021":
                eps_r = result["eps_r"] * 1.2
                sigma = result["sigma"] * 1.2
            elif skin_model == "christ2025":
                from aegis.tissue.cole_cole import debye_permittivity

                eps_complex = np.array(
                    [debye_permittivity(f, eps_inf=7.88, eps_static=47.0, sigma=5.19, tau_s=8.35e-12) for f in freqs]
                )
                eps_r = np.real(eps_complex)
                sigma = -np.imag(eps_complex) * omega * eps_0
            elif skin_model == "nict":
                from aegis.viewer.compute import _load_nict_data

                data = _load_nict_data()
                log_freqs = np.log10(freqs)
                log_f_clamped = np.clip(log_freqs, data["log_freq"][0], data["log_freq"][-1])
                eps_r = 10 ** np.interp(log_f_clamped, data["log_freq"], data["log_eps_r"])
                sigma = 10 ** np.interp(log_f_clamped, data["log_freq"], data["log_sigma"])
            else:
                eps_r = result["eps_r"]
                sigma = result["sigma"]
            eps_complex = eps_r - 1j * sigma / (omega * eps_0)
            m = np.sqrt(eps_complex)
            m = np.where(np.real(m) < 0, -m, m)
            n_ri = np.real(m)
            kappa = -np.imag(m)
            result = {
                "freqs_hz": freqs,
                "eps_r": eps_r,
                "sigma": sigma,
                "T0": 4 * n_ri / ((1 + n_ri) ** 2 + kappa**2),
            }
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "tissue": tissue,
            "skin_model": skin_model,
            "freqs_hz": result["freqs_hz"].tolist(),
            "eps_r": result["eps_r"].tolist(),
            "sigma": result["sigma"].tolist(),
            "T0": result["T0"].tolist(),
        }
    )


def _compliance_power_sweep_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compliance margin vs transmit power at a fixed frequency."""
    from aegis.compliance import ExposureScenario, evaluate_compliance, power_sweep

    sab_4cm2 = request.args.get("sab_4cm2", type=float)
    freq_hz = request.args.get("freq_hz", type=float)
    ref_power_dbm = request.args.get("ref_power_dbm", type=float)
    sab_1cm2 = request.args.get("sab_1cm2", type=float)
    sinc_local = request.args.get("sinc_local", type=float)
    sinc_wb = request.args.get("sinc_wb", type=float)
    sar_wb = request.args.get("sar_wb", type=float)

    if freq_hz is None or ref_power_dbm is None:
        return jsonify({"error": "freq_hz and ref_power_dbm are required"}), 400
    if sab_4cm2 is None and sab_1cm2 is None and sar_wb is None:
        return jsonify({"error": "At least one of sab_4cm2, sab_1cm2, or sar_wb is required"}), 400
    err = _reject_non_finite(
        [
            ("freq_hz", freq_hz),
            ("ref_power_dbm", ref_power_dbm),
            ("sab_4cm2", sab_4cm2),
            ("sab_1cm2", sab_1cm2),
            ("sinc_local", sinc_local),
            ("sinc_wb", sinc_wb),
            ("sar_wb", sar_wb),
        ]
    )
    if err is not None:
        return err
    if freq_hz <= 0:
        return jsonify({"error": "freq_hz must be positive"}), 400

    scenario_str = request.args.get("scenario", "general_public")
    if scenario_str not in _VALID_SCENARIOS:
        return jsonify({"error": f"scenario must be one of {sorted(_VALID_SCENARIOS)}"}), 400
    scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

    n_points = request.args.get("n_points", 50, type=int)
    n_points = min(max(n_points, 10), 500)

    ref_power_w = 10.0 ** ((ref_power_dbm - 30) / 10.0)

    try:
        cr = evaluate_compliance(
            freq_hz=freq_hz,
            scenario=scenario,
            sab_4cm2=sab_4cm2,
            sab_1cm2=sab_1cm2,
            sar_wb=sar_wb,
            sinc_local=sinc_local,
            sinc_whole_body=sinc_wb,
        )
        sweep = power_sweep(cr, ref_power_w, n_points=n_points)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    p_max_w = sweep["p_max_compliant_w"]
    p_max_dbm = 10.0 * np.log10(p_max_w * 1e3) if 0 < p_max_w < float("inf") else None

    return jsonify(
        {
            "power_dbm": sweep["power_dbm"].tolist(),
            "margin_db": _sanitize_list(sweep["margin_db"].tolist()),
            "compliant": sweep["compliant"].tolist(),
            "p_max_compliant_w": _finite_or_none(float(p_max_w)),
            "p_max_compliant_dbm": p_max_dbm,
        }
    )


def _compliance_heatmap_impl(cache: dict, cache_lock) -> RouteResponse:
    """2D compliance margin over (frequency, power) plane."""
    from aegis.compliance import ExposureScenario, compliance_heatmap

    sab_4cm2 = request.args.get("sab_4cm2", type=float)
    sab_1cm2 = request.args.get("sab_1cm2", type=float)
    freq_hz = request.args.get("freq_hz", type=float)
    ref_power_dbm = request.args.get("ref_power_dbm", type=float)

    if freq_hz is None or ref_power_dbm is None:
        return jsonify({"error": "freq_hz and ref_power_dbm are required"}), 400
    if sab_4cm2 is None and sab_1cm2 is None:
        return jsonify({"error": "At least one of sab_4cm2 or sab_1cm2 is required"}), 400
    if freq_hz <= 0:
        return jsonify({"error": "freq_hz must be positive"}), 400

    scenario_str = request.args.get("scenario", "general_public")
    if scenario_str not in _VALID_SCENARIOS:
        return jsonify({"error": f"scenario must be one of {sorted(_VALID_SCENARIOS)}"}), 400
    scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

    sinc_local = request.args.get("sinc_local", type=float)
    err = _reject_non_finite(
        [
            ("freq_hz", freq_hz),
            ("ref_power_dbm", ref_power_dbm),
            ("sab_4cm2", sab_4cm2),
            ("sab_1cm2", sab_1cm2),
            ("sinc_local", sinc_local),
        ]
    )
    if err is not None:
        return err
    n_freq = request.args.get("n_freq", 40, type=int)
    n_power = request.args.get("n_power", 40, type=int)
    n_freq = min(max(n_freq, 10), 100)
    n_power = min(max(n_power, 10), 100)

    ref_power_w = 10.0 ** ((ref_power_dbm - 30) / 10.0)

    # Use sab_4cm2 if available, fall back to sab_1cm2 as reference
    ref_sab = sab_4cm2 if sab_4cm2 is not None else sab_1cm2
    assert ref_sab is not None  # noqa: S101 - enforced by the sab_4cm2/sab_1cm2 check above

    try:
        result = compliance_heatmap(
            sab_4cm2=ref_sab,
            ref_power_w=ref_power_w,
            scenario=scenario,
            n_freq=n_freq,
            n_power=n_power,
            sinc_local=sinc_local,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Flatten 2D arrays for JSON transport (row-major: power varies fastest)
    margin_flat = _sanitize_list(result["margin_db"].tolist())
    compliant_flat = result["compliant"].tolist()

    p_max_per_freq = result["p_max_per_freq"]
    p_max_dbm_per_freq = _sanitize_list((10.0 * np.log10(np.clip(p_max_per_freq, 1e-30, None) * 1e3)).tolist())

    return jsonify(
        {
            "freq_ghz": (result["freq_hz"] / 1e9).tolist(),
            "power_dbm": result["power_dbm"].tolist(),
            "margin_db": margin_flat,
            "compliant": compliant_flat,
            "p_max_dbm_per_freq": p_max_dbm_per_freq,
            "n_freq": n_freq,
            "n_power": n_power,
        }
    )


def _compliance_frequency_sweep_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compliance margin vs frequency at fixed exposure values."""
    from aegis.compliance import ExposureScenario, frequency_sweep

    sab_4cm2 = request.args.get("sab_4cm2", type=float)
    sab_1cm2 = request.args.get("sab_1cm2", type=float)
    sar_wb = request.args.get("sar_wb", type=float)
    if sab_4cm2 is None and sab_1cm2 is None and sar_wb is None:
        return jsonify({"error": "At least one of sab_4cm2, sab_1cm2, or sar_wb is required"}), 400

    scenario_str = request.args.get("scenario", "general_public")
    if scenario_str not in _VALID_SCENARIOS:
        return jsonify({"error": f"scenario must be one of {sorted(_VALID_SCENARIOS)}"}), 400
    scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

    sinc_local = request.args.get("sinc_local", type=float)
    sinc_wb = request.args.get("sinc_wb", type=float)
    err = _reject_non_finite(
        [
            ("sab_4cm2", sab_4cm2),
            ("sab_1cm2", sab_1cm2),
            ("sar_wb", sar_wb),
            ("sinc_local", sinc_local),
            ("sinc_wb", sinc_wb),
        ]
    )
    if err is not None:
        return err
    n_points = request.args.get("n_points", 50, type=int)
    n_points = min(max(n_points, 10), 500)

    try:
        sweep = frequency_sweep(
            sab_4cm2=sab_4cm2,
            sab_1cm2=sab_1cm2,
            sar_wb=sar_wb,
            sinc_local=sinc_local,
            sinc_whole_body=sinc_wb,
            scenario=scenario,
            n_points=n_points,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        {
            "freq_ghz": sweep["freq_ghz"].tolist(),
            "margin_db": _sanitize_list(sweep["margin_db"].tolist()),
            "compliant": sweep["compliant"].tolist(),
        }
    )


def _compliance_spatial_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compute spatial compliance margins over a grid around base stations.

    Takes loaded base stations and a bounding box, creates a grid,
    and returns ICNIRP compliance margins at each grid point using
    free-space path loss estimation.
    """
    from aegis.compliance import ExposureScenario, spatial_compliance_grid
    from aegis.viewer.server import scoped_cache_get

    with cache_lock:
        basestations = scoped_cache_get(cache, "basestations", [])

    if not basestations:
        return jsonify({"error": "No base stations loaded. Call /api/basestations/load first."}), 400

    body, err = get_json_dict()
    if err is not None:
        return err

    # Grid bounds
    bbox = body.get("bbox")
    if bbox is None:
        # Derive bbox from base station extent with padding
        lats = [bs.latitude for bs in basestations]
        lons = [bs.longitude for bs in basestations]
        pad_lat = max(0.002, (max(lats) - min(lats)) * 0.15)
        pad_lon = max(0.002, (max(lons) - min(lons)) * 0.15)
        bbox = [
            min(lons) - pad_lon,
            max(lons) + pad_lon,
            min(lats) - pad_lat,
            max(lats) + pad_lat,
        ]

    if not isinstance(bbox, list) or len(bbox) != 4:
        return jsonify({"error": "bbox must be [lon_min, lon_max, lat_min, lat_max]"}), 400

    try:
        lon_min, lon_max, lat_min, lat_max = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return jsonify({"error": "bbox values must be numbers"}), 400

    if not all(math.isfinite(v) for v in (lon_min, lon_max, lat_min, lat_max)):
        return jsonify({"error": "bbox values must be finite numbers"}), 400

    if lon_min >= lon_max or lat_min >= lat_max:
        return (
            jsonify({"error": "bbox must have lon_min < lon_max and lat_min < lat_max"}),
            400,
        )

    resolution = body.get("resolution", 80)
    try:
        resolution = int(resolution)
    except (TypeError, ValueError):
        return jsonify({"error": "resolution must be an integer"}), 400
    resolution = min(max(resolution, 10), 200)

    try:
        receiver_height = float(body.get("receiver_height_m", 1.5))
    except (TypeError, ValueError):
        return jsonify({"error": "receiver_height_m must be a number"}), 400
    if not (0.0 < receiver_height <= 500.0):
        return (
            jsonify({"error": "receiver_height_m must be positive and <= 500 m"}),
            400,
        )

    scenario_str = body.get("scenario", "general_public")
    if scenario_str not in _VALID_SCENARIOS:
        return jsonify({"error": f"scenario must be one of {sorted(_VALID_SCENARIOS)}"}), 400
    scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

    # Build grid
    grid_lat_1d = np.linspace(lat_min, lat_max, resolution)
    grid_lon_1d = np.linspace(lon_min, lon_max, resolution)
    grid_lon_2d, grid_lat_2d = np.meshgrid(grid_lon_1d, grid_lat_1d)
    flat_lats = grid_lat_2d.ravel()
    flat_lons = grid_lon_2d.ravel()

    # Extract station arrays
    station_lats = np.array([bs.latitude for bs in basestations])
    station_lons = np.array([bs.longitude for bs in basestations])
    station_eirp = np.array([bs.eirp_dbm for bs in basestations])
    station_freq = np.array([bs.freq_hz for bs in basestations])
    station_heights = np.array([bs.height_m for bs in basestations])

    try:
        result = spatial_compliance_grid(
            station_lats=station_lats,
            station_lons=station_lons,
            station_eirp_dbm=station_eirp,
            station_freq_hz=station_freq,
            station_heights_m=station_heights,
            grid_lats=flat_lats,
            grid_lons=flat_lons,
            scenario=scenario,
            receiver_height_m=receiver_height,
        )
    except Exception as e:
        logger.exception("Spatial compliance grid failed")
        return jsonify({"error": f"Computation failed: {e}"}), 500

    # Reshape to 2D grid (n_lat, n_lon) for easy frontend consumption
    n_lat = resolution
    n_lon = resolution
    margin_2d = result["margin_db"].reshape(n_lat, n_lon)
    compliant_2d = result["compliant"].reshape(n_lat, n_lon)
    sinc_2d = result["sinc"].reshape(n_lat, n_lon)

    # Clamp infinite/NaN margins to display-friendly values for valid JSON
    margin_clamped = np.where(np.isnan(margin_2d), 0.0, margin_2d)
    margin_clamped = np.where(np.isinf(margin_clamped), 60.0, margin_clamped)
    sinc_clean = np.where(np.isnan(sinc_2d), 0.0, sinc_2d)
    sinc_clean = np.where(np.isinf(sinc_clean), 0.0, sinc_clean)

    return jsonify(
        {
            "lats": grid_lat_1d.tolist(),
            "lons": grid_lon_1d.tolist(),
            "margin_db": margin_clamped.tolist(),
            "compliant": compliant_2d.tolist(),
            "sinc_w_m2": sinc_clean.tolist(),
            "n_lat": n_lat,
            "n_lon": n_lon,
            "scenario": scenario_str,
            "freq_hz_dominant": result["freq_hz_dominant"],
            "T0": result["T0"],
            "n_stations": len(basestations),
        }
    )


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Register analysis-related API routes."""

    @app.route("/api/compliance/limits")
    def compliance_limits():
        return _compliance_limits_impl(cache, cache_lock)

    @app.route("/api/compliance/summary")
    def compliance_summary():
        return _compliance_summary_impl(cache, cache_lock)

    @app.route("/api/tissue/spectrum")
    def tissue_spectrum():
        return _tissue_spectrum_impl(cache, cache_lock)

    @app.route("/api/compliance/power-sweep")
    def compliance_power_sweep():
        return _compliance_power_sweep_impl(cache, cache_lock)

    @app.route("/api/compliance/heatmap")
    def compliance_heatmap_route():
        return _compliance_heatmap_impl(cache, cache_lock)

    @app.route("/api/compliance/frequency-sweep")
    def compliance_frequency_sweep():
        return _compliance_frequency_sweep_impl(cache, cache_lock)

    @app.route("/api/compliance/spatial", methods=["POST"])
    def compliance_spatial():
        return _compliance_spatial_impl(cache, cache_lock)
