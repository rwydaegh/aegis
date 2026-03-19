"""Dosimetry result: the output of every fidelity level.

DosimetryResult is the same type regardless of fidelity level. Coherent-specific
fields (Q, rho, eigenvalues) are None for incoherent computations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.compliance import ICNIRP_2020


@dataclass(frozen=True)
class DosimetryResult:
    """Output of a dosimetry computation.

    Attributes
    ----------
    sab : (M,) per-triangle absorbed power density [W/m^2]
    sab_averaged : (M,) or None, spatially averaged (ICNIRP 4 cm^2) [W/m^2]
    p_abs : total absorbed power [W]
    sar_wb : whole-body SAR [W/kg], or None if body mass not provided
    fidelity_level : which kernel level produced this result (0-8)
    """

    sab: np.ndarray = field(repr=False)
    p_abs: float
    fidelity_level: int
    sab_averaged: np.ndarray | None = field(default=None, repr=False)
    sar_wb: float | None = None

    # Coherent-specific (None for incoherent levels 0-6)
    Q: np.ndarray | None = field(default=None, repr=False)
    rho: float | None = None
    eigenvalues: np.ndarray | None = field(default=None, repr=False)
    x_star: np.ndarray | None = field(default=None, repr=False)

    @property
    def peak_sab(self) -> float:
        """Peak per-triangle S_ab [W/m^2]."""
        return float(np.max(self.sab))

    @property
    def peak_sab_averaged(self) -> float | None:
        """Peak spatially averaged S_ab [W/m^2], or None if not computed."""
        if self.sab_averaged is None:
            return None
        return float(np.max(self.sab_averaged))

    @property
    def compliant_sab(self) -> bool | None:
        """ICNIRP compliance for S_ab: peak averaged < limit.

        Returns None if spatial averaging was not performed.
        """
        peak = self.peak_sab_averaged
        if peak is None:
            return None
        return peak < ICNIRP_2020.sab_peak

    @property
    def compliant_sar(self) -> bool | None:
        """ICNIRP compliance for whole-body SAR: < limit.

        Returns None if SAR was not computed.
        """
        if self.sar_wb is None:
            return None
        return self.sar_wb < ICNIRP_2020.sar_wb

    def __repr__(self) -> str:
        parts = [
            f"DosimetryResult(level={self.fidelity_level}",
            f"p_abs={self.p_abs:.4g} W",
            f"peak_sab={self.peak_sab:.4g} W/m^2",
        ]
        if self.sar_wb is not None:
            parts.append(f"sar_wb={self.sar_wb:.4g} W/kg")
        return ", ".join(parts) + ")"
