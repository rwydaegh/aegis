"""Dosimetry result: the output of every fidelity level.

DosimetryResult is the same type regardless of fidelity level. Coherent-specific
fields (Q, rho, eigenvalues) are None for incoherent computations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields

import numpy as np


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

    # Mode-based API (None when using legacy level= API)
    mode: str | None = None
    corrections: tuple[str, ...] = ()

    # Coherent-specific (None for incoherent levels 0-6)
    Q: np.ndarray | None = field(default=None, repr=False)
    rho: float | None = None
    eigenvalues: np.ndarray | None = field(default=None, repr=False)
    x_star: np.ndarray | None = field(default=None, repr=False)

    # Incident and averaged fields
    sinc: np.ndarray | None = field(default=None, repr=False)
    sinc_averaged: np.ndarray | None = field(default=None, repr=False)
    sab_1cm2_averaged: np.ndarray | None = field(default=None, repr=False)
    freq_hz: float | None = None

    def to_dict(self) -> dict:
        """Serialize fields to a JSON-friendly dict. Omits None values."""
        out: dict = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if val is None:
                continue
            if isinstance(val, np.ndarray):
                out[f.name] = val.tolist()
            elif isinstance(val, np.generic):
                out[f.name] = val.item()
            else:
                out[f.name] = val
        return out

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @property
    def peak_sab(self) -> float:
        """Peak per-triangle S_ab [W/m^2]."""
        if self.sab.size == 0:
            raise ValueError("peak_sab is undefined for empty sab")
        return float(np.max(self.sab))

    @property
    def peak_triangle_index(self) -> int:
        """Triangle index with maximum S_ab."""
        return int(np.argmax(self.sab))

    @property
    def mean_sab(self) -> float:
        """Mean per-triangle S_ab [W/m^2]."""
        return float(np.mean(self.sab))

    @property
    def peak_sab_averaged(self) -> float | None:
        """Peak spatially averaged S_ab [W/m^2], or None if not computed."""
        if self.sab_averaged is None:
            return None
        if self.sab_averaged.size == 0:
            raise ValueError("peak_sab_averaged is undefined for empty sab_averaged")
        return float(np.max(self.sab_averaged))

    @property
    def compliant_sab(self) -> bool | None:
        """ICNIRP compliance: peak spatially averaged S_ab <= limit."""
        peak = self.peak_sab_averaged
        if peak is None or self.freq_hz is None:
            return None
        from aegis.compliance import ExposureScenario, icnirp_limits

        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, self.freq_hz)
        return peak <= lim.sab_4cm2

    @property
    def compliant_sar(self) -> bool | None:
        """ICNIRP compliance for whole-body SAR: <= limit.

        Returns None if SAR was not computed.
        """
        if self.sar_wb is None:
            return None
        from aegis.compliance import ICNIRP_2020

        return self.sar_wb <= ICNIRP_2020.sar_wb

    def __repr__(self) -> str:
        parts = [
            f"DosimetryResult(level={self.fidelity_level}",
            f"p_abs={self.p_abs:.4g} W",
            f"peak_sab={self.peak_sab:.4g} W/m^2",
        ]
        if self.sar_wb is not None:
            parts.append(f"sar_wb={self.sar_wb:.4g} W/kg")
        return ", ".join(parts) + ")"
