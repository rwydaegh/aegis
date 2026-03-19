"""ICNIRP 2020 compliance limits for EMF exposure above 6 GHz.

Reference: ICNIRP, "Guidelines for Limiting Exposure to Electromagnetic
Fields (100 kHz to 300 GHz)," Health Physics, vol. 118, no. 5, 2020.

All limits are for the general public (not occupational).
"""

from __future__ import annotations

from dataclasses import dataclass


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
    return peak_sab_averaged < limits.sab_peak


def is_compliant_sar(sar_wb: float, limits: ICNIRPLimits = ICNIRP_2020) -> bool:
    """Check if whole-body SAR is below the ICNIRP limit."""
    return sar_wb < limits.sar_wb
