"""3GPP TR 38.901 path loss models."""

from __future__ import annotations

import logging
import math

log = logging.getLogger(__name__)


def compute_path_loss(
    params: dict,
    distance_m: float,
    freq_ghz: float,
    h_bs: float = 10.0,
    h_ms: float = 1.5,
) -> float:
    """Compute path loss in dB for the given model parameters.

    Supports: logdist, dual_slope, nlos, constant. Unknown models fall back to FSPL.
    """
    model = params.get("PL_model", "logdist")
    d3d = max(distance_m, 1.0)

    if model == "logdist":
        return _logdist(params, d3d, freq_ghz)
    elif model == "dual_slope":
        return _dual_slope(params, d3d, freq_ghz, h_bs, h_ms)
    elif model == "nlos":
        return _nlos(params, d3d, freq_ghz, h_bs, h_ms)
    elif model == "constant":
        return _constant(params)
    else:
        log.warning("Unsupported PL model %r, using free-space", model)
        return _fspl(d3d, freq_ghz)


def p_los(d_2d_m: float, scenario: str = "umi") -> float:
    """3GPP TR 38.901 line-of-sight probability (Table 7.4.2-1).

    The stochastic study arm blends LOS and NLOS channel statistics by this
    distance-based probability instead of shadow-raying the real mesh, so the
    comparison against the deterministic (ray-traced) arm stays honest.

    Parameters
    ----------
    d_2d_m : 2D (ground-plane) BS-UE distance in metres.
    scenario : "umi" (street canyon, default) or "uma".

    Returns
    -------
    Probability in [0, 1]. Both forms assume a ground-level user (the
    height-dependent UMa correction C(h_UT) is 0 for h_UT <= 13 m, which holds
    for pedestrians, so it is omitted).
    """
    d = max(float(d_2d_m), 0.0)
    if d <= 18.0:
        return 1.0
    s = scenario.lower()
    if s == "umi":
        return 18.0 / d + math.exp(-d / 36.0) * (1.0 - 18.0 / d)
    if s == "uma":
        return 18.0 / d + math.exp(-d / 63.0) * (1.0 - 18.0 / d)
    raise ValueError(f"unknown LOS scenario {scenario!r} (use 'umi' or 'uma')")


def _fspl(d3d: float, freq_ghz: float) -> float:
    return 20 * math.log10(d3d) + 20 * math.log10(freq_ghz) + 32.45


def _constant(params: dict) -> float:
    return float(params.get("PL_A", 0.0))


def _logdist(params: dict, d3d: float, freq_ghz: float) -> float:
    A = params.get("PL_A", 20)
    B = params.get("PL_B", 32.45)
    C = params.get("PL_C", 20)
    return A * math.log10(d3d) + B + C * math.log10(freq_ghz)


def _dual_slope(
    params: dict,
    d3d: float,
    freq_ghz: float,
    h_bs: float,
    h_ms: float,
) -> float:
    A1 = params.get("PL_A1", 21)
    A2 = params.get("PL_A2", 40)
    B = params.get("PL_B", 32.4)
    C = params.get("PL_C", 20)
    E = params.get("PL_E", 13.34)
    hE = params.get("PL_hE", 1)
    D = params.get("PL_D", 0)

    d_bp = E * (h_bs - hE) * (h_ms - hE) * freq_ghz
    d_bp = max(d_bp, 1.0)

    pl1 = A1 * math.log10(d3d) + B + C * math.log10(freq_ghz) + D * d3d
    if d3d <= d_bp:
        return pl1
    pl1_bp = A1 * math.log10(d_bp) + B + C * math.log10(freq_ghz) + D * d_bp
    return pl1_bp + A2 * math.log10(d3d / d_bp)


def _nlos(
    params: dict,
    d3d: float,
    freq_ghz: float,
    h_bs: float,
    h_ms: float,
) -> float:
    pl_los = _dual_slope(params, d3d, freq_ghz, h_bs, h_ms)
    An = params.get("PL_An", 39.08)
    Bn = params.get("PL_Bn", 14.44)
    Cn = params.get("PL_Cn", 20)
    E3n = params.get("PL_E3n", 0)
    pl_nlos = An * math.log10(d3d) + Bn + Cn * math.log10(freq_ghz) + E3n * h_ms
    return max(pl_los, pl_nlos)
