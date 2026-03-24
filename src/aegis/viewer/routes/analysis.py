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
        scenario = (
            ExposureScenario.OCCUPATIONAL
            if scenario_str == "occupational"
            else ExposureScenario.GENERAL_PUBLIC
        )

        try:
            limits = icnirp_limits(scenario=scenario, freq_hz=freq_hz)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({
            "scenario": scenario_str,
            "freq_hz": freq_hz,
            "sab_4cm2": limits.sab_4cm2,
            "sab_1cm2": limits.sab_1cm2,
            "sar_wb": limits.sar_wb,
            "sinc_local": limits.sinc_local,
            "sinc_whole_body": limits.sinc_whole_body,
        })

    # ------------------------------------------------------------------
    # GET /api/compliance/summary
    # ------------------------------------------------------------------
    @app.route("/api/compliance/summary")
    def compliance_summary():
        """Human-readable compliance summary text."""
        from aegis.compliance import summary_text

        last_compliance = app.config.get("_last_compliance_result")
        if last_compliance is None:
            return jsonify({"error": "No compliance result available. Run a compute first."}), 400

        tx_dbm = request.args.get("tx_power_dbm", type=float)
        text = summary_text(last_compliance, tx_power_dbm=tx_dbm)
        return jsonify({"text": text})

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
        n = min(max(n, 10), 1000)

        try:
            freqs = np.linspace(f_min, f_max, n)
            result = get_tissue_spectrum(tissue, freqs)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({
            "tissue": tissue,
            "freqs_hz": result["freqs_hz"].tolist(),
            "eps_r": result["eps_r"].tolist(),
            "sigma": result["sigma"].tolist(),
            "T0": result["T0"].tolist(),
        })
