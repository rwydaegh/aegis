"""Miscellaneous compute routes: compliance report, channel presets, LSP heatmap."""

from __future__ import annotations

import logging
import math
import os

from flask import jsonify

from aegis.viewer.routes._helpers import get_json_dict
from aegis.viewer.routes._types import RouteResponse

logger = logging.getLogger(__name__)


def _compliance_report_impl(cache: dict, cache_lock) -> RouteResponse:
    """Compliance data is returned inline in X-Stats from compute endpoints.

    This endpoint is deprecated. Clients should read compliance from the
    X-Stats header of /api/compute responses.
    """
    return jsonify({"error": "Compliance data is available in X-Stats from /api/compute"}), 410


def _channel_presets_impl(cache: dict, cache_lock) -> RouteResponse:
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


def _lsp_heatmap_impl(cache: dict, cache_lock) -> RouteResponse:
    """Generate an LSP spatial map for the frontend heatmap overlay."""
    from aegis.viewer.compute import generate_lsp_heatmap

    data, err = get_json_dict()
    if err is not None:
        return err
    preset_name = data.get("preset", "3GPP_38.901_UMi_LOS")
    lsp_name = data.get("lsp_name", "SF_dB")
    raw_freq = data.get("freq_ghz", 28.0)
    raw_antenna_pos = data.get("antenna_pos", [0, 0, 10])
    raw_bounds = data.get("bounds", [-100, 100, -100, 100])
    try:
        if not isinstance(raw_bounds, (list, tuple)) or len(raw_bounds) != 4:
            return jsonify({"error": "bounds must be a 4-element list"}), 400
        bounds_floats = (
            float(raw_bounds[0]),
            float(raw_bounds[1]),
            float(raw_bounds[2]),
            float(raw_bounds[3]),
        )
        freq_ghz = float(raw_freq)
        if not isinstance(raw_antenna_pos, (list, tuple)) or len(raw_antenna_pos) != 3:
            return jsonify({"error": "antenna_pos must be a 3-element list"}), 400
        antenna_pos = (
            float(raw_antenna_pos[0]),
            float(raw_antenna_pos[1]),
            float(raw_antenna_pos[2]),
        )
        resolution = max(1, min(int(data.get("resolution", 128)), 256))
        seed = int(data.get("seed", 42))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid parameter: {exc}"}), 400
    if not all(math.isfinite(v) for v in bounds_floats):
        return jsonify({"error": "bounds must be finite"}), 400
    if not math.isfinite(freq_ghz):
        return jsonify({"error": "freq_ghz must be finite"}), 400
    if not all(math.isfinite(v) for v in antenna_pos):
        return jsonify({"error": "antenna_pos must be finite"}), 400
    if seed < 0:
        return jsonify({"error": "seed must be a non-negative integer"}), 400

    bounds: tuple[float, float, float, float] = bounds_floats
    try:
        result = generate_lsp_heatmap(
            preset_name=preset_name,
            freq_ghz=freq_ghz,
            antenna_pos=antenna_pos,
            lsp_name=lsp_name,
            bounds=bounds,
            resolution=resolution,
            seed=seed,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
