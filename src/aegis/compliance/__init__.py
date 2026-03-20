"""ICNIRP 2020 compliance limits for EMF exposure above 6 GHz.

Reference: ICNIRP, "Guidelines for Limiting Exposure to Electromagnetic
Fields (100 kHz to 300 GHz)," Health Physics, vol. 118, no. 5, 2020.

All limits are for the general public (not occupational).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "ICNIRPLimits",
    "ICNIRP_2020",
    "is_compliant_sab",
    "is_compliant_sar",
    "margin_db",
    "summary_text",
]


@dataclass(frozen=True)
class ICNIRPLimits:
    """ICNIRP 2020 basic restriction limits (general public, > 6 GHz).

    Attributes
    ----------
    sab_peak : peak spatially averaged S_ab over 4 cm^2 [W/m^2]
    sar_wb : whole-body SAR [W/kg]
    averaging_area_cm2 : spatial averaging area [cm^2]
    """

    sab_peak: float
    sar_wb: float
    averaging_area_cm2: float


# ICNIRP 2020 Table 5 (general public, > 6 GHz)
ICNIRP_2020 = ICNIRPLimits(
    sab_peak=10.0,
    sar_wb=0.08,
    averaging_area_cm2=4.0,
)


def is_compliant_sab(peak_sab_averaged: float, limits: ICNIRPLimits = ICNIRP_2020) -> bool:
    """Check if peak spatially averaged S_ab is below the ICNIRP limit."""
    return peak_sab_averaged <= limits.sab_peak


def is_compliant_sar(sar_wb: float, limits: ICNIRPLimits = ICNIRP_2020) -> bool:
    """Check if whole-body SAR is below the ICNIRP limit."""
    return sar_wb <= limits.sar_wb


def margin_db(peak_sab: float, limits: ICNIRPLimits = ICNIRP_2020) -> float:
    """Compliance margin for peak S_ab in dB: 10 * log10(limit / peak_sab).

    Positive values correspond to peak_sab below the ICNIRP peak limit.
    """
    if peak_sab <= 0:
        raise ValueError("peak_sab must be positive")
    return float(10.0 * math.log10(limits.sab_peak / peak_sab))


def summary_text(
    peak_sab: float,
    sar_wb: float | None = None,
    *,
    limits: ICNIRPLimits = ICNIRP_2020,
) -> str:
    """Human-readable compliance summary (plain text, no DosimetryResult dependency)."""
    margin_line = (
        f"S_ab margin: {margin_db(peak_sab, limits):+.3f} dB"
        if peak_sab > 0
        else "S_ab margin: n/a (peak_sab must be positive for dB margin)"
    )
    lines = [
        f"Peak spatially averaged S_ab: {peak_sab:.6g} W/m^2",
        f"ICNIRP peak S_ab limit: {limits.sab_peak:g} W/m^2",
        margin_line,
        f"S_ab: {'PASS' if is_compliant_sab(peak_sab, limits) else 'FAIL'}",
    ]
    if sar_wb is not None:
        lines.extend(
            [
                f"Whole-body SAR: {sar_wb:.6g} W/kg",
                f"ICNIRP SAR limit: {limits.sar_wb:g} W/kg",
                f"SAR: {'PASS' if is_compliant_sar(sar_wb, limits) else 'FAIL'}",
            ]
        )
    return "\n".join(lines)
