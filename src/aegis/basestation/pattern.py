"""Pattern utilities: Gaussian fallback, SH fitting."""

from __future__ import annotations

import numpy as np

from aegis.basestation.antenna import AntennaPattern


def synthetic_pattern_from_beamwidth(
    hpbw_h_deg: float,
    hpbw_v_deg: float,
    gain_dbi: float,
    sidelobe_suppression_db: float | None = 15.0,
) -> AntennaPattern:
    """Create a Gaussian-approximation pattern from beamwidth specs.

    Uses ITU-R F.1336-5 model:
        G(el, az) = G_max * exp(-2.76 * (el/hpbw_v)^2) * exp(-2.76 * (az/hpbw_h)^2)

    The factor 2.76 = 4*ln(2) gives -3 dB at the half-power angle.
    """
    if np.isnan(hpbw_h_deg) or hpbw_h_deg <= 0:
        hpbw_h_deg = 65.0  # typical sector antenna
    if np.isnan(hpbw_v_deg) or hpbw_v_deg <= 0:
        hpbw_v_deg = 10.0  # typical sector antenna
    if np.isnan(gain_dbi):
        gain_dbi = 17.0  # typical sector gain

    elev = np.linspace(-90, 90, 181)
    azim = np.linspace(-180, 179, 360)
    el_grid, az_grid = np.meshgrid(elev, azim, indexing="ij")

    k = 4.0 * np.log(2.0)  # 2.7726
    g_linear = np.exp(-k * (el_grid / hpbw_v_deg) ** 2) * np.exp(-k * (az_grid / hpbw_h_deg) ** 2)
    g_dbi = 10.0 * np.log10(np.maximum(g_linear, 1e-20)) + gain_dbi

    if sidelobe_suppression_db is not None:
        floor_dbi = gain_dbi - sidelobe_suppression_db
        g_dbi = np.maximum(g_dbi, floor_dbi)

    return AntennaPattern(gain_dbi=g_dbi.astype(np.float32), max_gain_dbi=gain_dbi)
