"""Analysis routes: compliance utilities, tissue spectrum."""

from __future__ import annotations

import logging

import numpy as np
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Register analysis-related API routes."""

    # ------------------------------------------------------------------
    # GET /api/compliance/limits
    # ------------------------------------------------------------------
    @app.route("/api/compliance/limits")
    def compliance_limits():
        """Query ICNIRP 2020 limits at an arbitrary frequency/scenario."""
        from aegis.compliance import ExposureScenario, icnirp_limits

        freq_hz = request.args.get("freq_hz", type=float)
        if freq_hz is None:
            return jsonify({"error": "freq_hz is required"}), 400

        scenario_str = request.args.get("scenario", "general_public")
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

    # ------------------------------------------------------------------
    # GET /api/compliance/summary
    # ------------------------------------------------------------------
    @app.route("/api/compliance/summary")
    def compliance_summary():
        """Human-readable compliance summary text from last compute."""
        last = app.config.get("_last_compliance_result")
        if last is None:
            return jsonify({"error": "No compliance result available. Run a compute first."}), 400

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

        overall = last.get("overall_pass", True)
        margin = last.get("margin_db")
        lines.append("")
        lines.append(f"Overall: {'PASS' if overall else 'FAIL'}")
        if margin is not None:
            lines.append(f"Margin: {margin:+.1f} dB")

        return jsonify({"text": "\n".join(lines)})

    # ------------------------------------------------------------------
    # GET /api/tissue/spectrum
    # ------------------------------------------------------------------
    @app.route("/api/tissue/spectrum")
    def tissue_spectrum():
        """Vectorized tissue properties vs frequency."""
        from aegis.tissue.database import get_tissue_spectrum

        tissue = request.args.get("tissue", "Skin")
        f_min = request.args.get("f_min", 1e9, type=float)
        f_max = request.args.get("f_max", 100e9, type=float)
        n = request.args.get("n", 100, type=int)
        skin_model = request.args.get("skin_model", "itis")
        n = min(max(n, 10), 1000)

        try:
            freqs = np.linspace(f_min, f_max, n)
            result = get_tissue_spectrum(tissue, freqs)

            # Apply skin model adjustments when tissue is Skin
            if tissue == "Skin" and skin_model != "itis":
                eps_0 = 8.8541878128e-12
                omega = 2 * np.pi * freqs
                if skin_model == "christ2021":
                    eps_r = result["eps_r"] * 1.2
                    sigma = result["sigma"] * 1.2
                elif skin_model == "christ2025":
                    from aegis.viewer.compute import debye_permittivity
                    eps_complex = np.array([
                        debye_permittivity(f, eps_inf=7.88, eps_static=47.0, sigma=5.19, tau_s=8.35e-12)
                        for f in freqs
                    ])
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

    # ------------------------------------------------------------------
    # GET /api/compliance/power-sweep
    # ------------------------------------------------------------------
    @app.route("/api/compliance/power-sweep")
    def compliance_power_sweep():
        """Compliance margin vs transmit power at a fixed frequency."""
        from aegis.compliance import ExposureScenario, evaluate_compliance, power_sweep

        sab_4cm2 = request.args.get("sab_4cm2", type=float)
        freq_hz = request.args.get("freq_hz", type=float)
        ref_power_dbm = request.args.get("ref_power_dbm", type=float)

        if sab_4cm2 is None or freq_hz is None or ref_power_dbm is None:
            return jsonify({"error": "sab_4cm2, freq_hz, and ref_power_dbm are required"}), 400

        scenario_str = request.args.get("scenario", "general_public")
        scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

        sab_1cm2 = request.args.get("sab_1cm2", type=float)
        sinc_local = request.args.get("sinc_local", type=float)
        sinc_wb = request.args.get("sinc_wb", type=float)
        sar_wb = request.args.get("sar_wb", type=float)
        n_points = request.args.get("n_points", 50, type=int)

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
        p_max_dbm = 10.0 * np.log10(p_max_w * 1e3) if p_max_w < float("inf") else None

        return jsonify(
            {
                "power_dbm": sweep["power_dbm"].tolist(),
                "margin_db": sweep["margin_db"].tolist(),
                "compliant": sweep["compliant"].tolist(),
                "p_max_compliant_w": p_max_w,
                "p_max_compliant_dbm": p_max_dbm,
            }
        )

    # ------------------------------------------------------------------
    # GET /api/compliance/frequency-sweep
    # ------------------------------------------------------------------
    @app.route("/api/compliance/frequency-sweep")
    def compliance_frequency_sweep():
        """Compliance margin vs frequency at fixed exposure values."""
        from aegis.compliance import ExposureScenario, frequency_sweep

        sab_4cm2 = request.args.get("sab_4cm2", type=float)
        if sab_4cm2 is None:
            return jsonify({"error": "sab_4cm2 is required"}), 400

        scenario_str = request.args.get("scenario", "general_public")
        scenario = ExposureScenario.OCCUPATIONAL if scenario_str == "occupational" else ExposureScenario.GENERAL_PUBLIC

        sinc_local = request.args.get("sinc_local", type=float)
        sinc_wb = request.args.get("sinc_wb", type=float)
        sab_1cm2 = request.args.get("sab_1cm2", type=float)
        sar_wb = request.args.get("sar_wb", type=float)
        n_points = request.args.get("n_points", 50, type=int)

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
                "margin_db": sweep["margin_db"].tolist(),
                "compliant": sweep["compliant"].tolist(),
            }
        )
