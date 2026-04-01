"""Exposure mode definitions, TDD lookup, and power reduction factors.

Three exposure modes:
- THEORETICAL_MAX: no power reduction (regulatory worst case)
- ACTUAL_MAX: TDD duty cycle + beam scanning reduction
- TYPICAL: ACTUAL_MAX * 0.50 traffic load factor
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# mMIMO gain threshold (dBi)
_MMIMO_THRESHOLD = 20.0

# Traffic load factor for TYPICAL mode
_TRAFFIC_LOAD = 0.50

# TDD 4G LTE frequency bands (MHz): band -> (low, high)
_LTE_TDD_BANDS: list[tuple[float, float]] = [
    (2300.0, 2400.0),  # B38
    (2570.0, 2620.0),  # B40
    (3400.0, 3600.0),  # B42/B43
]

# 5G NR TDD bands (MHz): (low, high, tdd_ratio)
_NR_TDD_BANDS: list[tuple[float, float, float]] = [
    (2496.0, 2690.0, 0.75),  # n41
    (3300.0, 4200.0, 0.75),  # n77/n78
    (24000.0, 40000.0, 0.72),  # mmWave n257/n258/n261
]


class ExposureMode(StrEnum):
    """Exposure scenario determining the power reduction factor."""

    THEORETICAL_MAX = "theoretical_max"
    ACTUAL_MAX = "actual_max"
    TYPICAL = "typical"


def _normalize_technology(technology: str) -> str:
    """Normalize technology string to short canonical form."""
    tech = technology.upper()
    if "5G" in tech:
        return "5G"
    if "LTE" in tech:
        return "4G"
    if "UMTS" in tech:
        return "3G"
    if "GSM" in tech:
        return "2G"
    # Pass through short forms unchanged
    return tech


def lookup_tdd_dl_ratio(technology: str, freq_mhz: float) -> float:
    """Return TDD downlink duty cycle for a given technology and frequency.

    Returns 1.0 for FDD, 2G, and 3G technologies (no TDD reduction).
    """
    tech = _normalize_technology(technology)

    if tech == "5G":
        for low, high, ratio in _NR_TDD_BANDS:
            if low <= freq_mhz <= high:
                return ratio
        return 1.0

    if tech == "4G":
        for low, high in _LTE_TDD_BANDS:
            if low <= freq_mhz <= high:
                return 0.60
        return 1.0

    return 1.0


def lookup_prf(technology: str, freq_mhz: float, gain_dbi: float) -> float:
    """Return power reduction factor for beam scanning (mMIMO only).

    Only applies to 5G antennas with gain >= 20 dBi (mMIMO).
    Sub-6 GHz: 0.32. mmWave (>=24000 MHz): 0.30. All others: 1.0.
    """
    tech = _normalize_technology(technology)
    if tech != "5G" or gain_dbi < _MMIMO_THRESHOLD:
        return 1.0
    if freq_mhz >= 24000.0:
        return 0.30
    return 0.32


def power_reduction_factor(
    mode: ExposureMode,
    technology: str,
    freq_mhz: float,
    *,
    gain_dbi: float = 0.0,
) -> float:
    """Compute combined power reduction factor for an exposure mode.

    - THEORETICAL_MAX: 1.0
    - ACTUAL_MAX: tdd * prf
    - TYPICAL: tdd * prf * 0.50
    """
    if mode is ExposureMode.THEORETICAL_MAX:
        return 1.0

    tdd = lookup_tdd_dl_ratio(technology, freq_mhz)
    prf = lookup_prf(technology, freq_mhz, gain_dbi)
    factor = tdd * prf

    if mode is ExposureMode.TYPICAL:
        factor *= _TRAFFIC_LOAD

    return factor


@dataclass(frozen=True)
class MimoBeamParams:
    """Beam parameters for massive MIMO base stations.

    Broadcast beam: wide coverage pattern used for control channels.
    Traffic beam: narrow steered beam used for data transmission.
    """

    broadcast_gain_dbi: float
    broadcast_hpbw_h_deg: float
    broadcast_hpbw_v_deg: float
    traffic_gain_dbi: float
    traffic_hpbw_h_deg: float
    traffic_hpbw_v_deg: float
    h_sweep_range_deg: float
    v_sweep_range_deg: float
    sidelobe_suppression_db: float


# Default sub-6 GHz mMIMO beam parameters (3300-4200 MHz, e.g. n77/n78)
_SUB6_BEAM = MimoBeamParams(
    broadcast_gain_dbi=18.0,
    broadcast_hpbw_h_deg=65.0,
    broadcast_hpbw_v_deg=5.5,
    traffic_gain_dbi=25.0,
    traffic_hpbw_h_deg=12.0,
    traffic_hpbw_v_deg=10.0,
    h_sweep_range_deg=60.0,
    v_sweep_range_deg=15.0,
    sidelobe_suppression_db=15.0,
)

# mmWave mMIMO beam parameters (24000-40000 MHz)
_MMWAVE_BEAM = MimoBeamParams(
    broadcast_gain_dbi=20.0,
    broadcast_hpbw_h_deg=90.0,
    broadcast_hpbw_v_deg=30.0,
    traffic_gain_dbi=27.0,
    traffic_hpbw_h_deg=5.0,
    traffic_hpbw_v_deg=8.0,
    h_sweep_range_deg=60.0,
    v_sweep_range_deg=15.0,
    sidelobe_suppression_db=20.0,
)


def lookup_mimo_beam_params(
    technology: str,
    freq_mhz: float,
    gain_dbi: float,
) -> MimoBeamParams | None:
    """Return MIMO beam parameters for an mMIMO base station, or None.

    Returns None for non-mMIMO antennas (non-5G or gain < 20 dBi).
    """
    tech = _normalize_technology(technology)
    if tech != "5G" or gain_dbi < _MMIMO_THRESHOLD:
        return None
    if freq_mhz >= 24000.0:
        return _MMWAVE_BEAM
    if 3300.0 <= freq_mhz <= 4200.0:
        return _SUB6_BEAM
    # Fallback for unknown 5G mMIMO bands: use sub-6 defaults
    return _SUB6_BEAM
