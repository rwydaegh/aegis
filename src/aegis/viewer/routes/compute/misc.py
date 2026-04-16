"""Miscellaneous compute routes: compliance report, channel presets, LSP heatmap."""

from __future__ import annotations

import logging
import os

from flask import Response, jsonify, request

logger = logging.getLogger(__name__)


def _compliance_report_impl(cache: dict, cache_lock) -> Response:
    """Compliance data is returned inline in X-Stats from compute endpoints.

    This endpoint is deprecated. Clients should read compliance from the
    X-Stats header of /api/compute responses.
    """
    return jsonify({"error": "Compliance data is available in X-Stats from /api/compute"}), 410


def _channel_presets_impl(cache: dict, cache_lock) -> Response:
    """List available 3GPP stochastic channel presets."""
    from pathlib import Path

    from aegis.channel import list_presets, load_preset

    with cache_lock:
        cfg = cache["config"]
    stoch_cfg = cfg["dosimetry"].get("stochastic", {})
    preset_dir = Path(stoch_cfg.get("preset_dir", "data/channel_presets"))
    if not preset_dir.is_absolute():
        data_root = Path(os.environ.get("AEGIS_DATA_DIR", str(Path(__file__).resolve().parents[5] / "data")))
        preset_dir = data_root / "channel_presets"
    all_names = list_presets(preset_dir)
    presets = []
    for name in all_names:
        try:
            p = load_preset(name, preset_dir)
            presets.append(
                {
                    "name": name,
                    "params": p["params"],
                }
            )
        except Exception as exc:
            logger.warning("Failed to load channel preset %r: %s", name, exc)
            continue
    return jsonify(presets)


def _lsp_heatmap_impl(cache: dict, cache_lock) -> Response:
    """Generate an LSP spatial map for the frontend heatmap overlay."""
    from aegis.viewer.compute import generate_lsp_heatmap

    data = request.get_json(silent=True) or {}
    preset_name = data.get("preset", "3GPP_38.901_UMi_LOS")
    freq_ghz = data.get("freq_ghz", 28.0)
    antenna_pos = data.get("antenna_pos", [0, 0, 10])
    lsp_name = data.get("lsp_name", "SF_dB")
    raw_bounds = data.get("bounds", [-100, 100, -100, 100])
    try:
        if not isinstance(raw_bounds, (list, tuple)) or len(raw_bounds) != 4:
            return jsonify({"error": "bounds must be a 4-element list"}), 400
        bounds = tuple(float(b) for b in raw_bounds)
        resolution = max(1, min(int(data.get("resolution", 128)), 256))
        seed = int(data.get("seed", 42))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid parameter: {exc}"}), 400

    try:
        result = generate_lsp_heatmap(
            preset_name=preset_name,
            freq_ghz=freq_ghz,
            antenna_pos=tuple(antenna_pos),
            lsp_name=lsp_name,
            bounds=bounds,
            resolution=resolution,
            seed=seed,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
