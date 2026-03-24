"""Dosimetry result: the output of every fidelity level.

DosimetryResult is the same type regardless of fidelity level. Coherent-specific
fields (Q, rho, eigenvalues) are None for incoherent computations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from aegis.compliance import ComplianceResult, ExposureScenario


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

    def scale(self, factor: float) -> DosimetryResult:
        """Return a new result with all power quantities scaled by ``factor``.

        S_ab is linear in transmit power for all fidelity levels (0-8).
        This enables parameter sweeps: compute once at a reference power,
        then scale to explore the compliance boundary.

        Coherent-specific fields (Q, eigenvalues) scale with ``factor`` too,
        since Q ~ P and eigenvalues are eigenvalues of Q. The precoder
        x_star is not scaled (it encodes direction, not magnitude).

        Parameters
        ----------
        factor : float
            Multiplicative scaling factor. Must be non-negative.
        """
        if factor < 0:
            raise ValueError("scale factor must be non-negative")
        return DosimetryResult(
            sab=self.sab * factor,
            p_abs=self.p_abs * factor,
            fidelity_level=self.fidelity_level,
            sab_averaged=self.sab_averaged * factor if self.sab_averaged is not None else None,
            sar_wb=self.sar_wb * factor if self.sar_wb is not None else None,
            mode=self.mode,
            corrections=self.corrections,
            Q=self.Q * factor if self.Q is not None else None,
            rho=self.rho,
            eigenvalues=self.eigenvalues * factor if self.eigenvalues is not None else None,
            x_star=self.x_star,
            sinc=self.sinc * factor if self.sinc is not None else None,
            sinc_averaged=self.sinc_averaged * factor if self.sinc_averaged is not None else None,
            sab_1cm2_averaged=self.sab_1cm2_averaged * factor if self.sab_1cm2_averaged is not None else None,
            freq_hz=self.freq_hz,
        )

    def evaluate_compliance(
        self,
        scenario: ExposureScenario | None = None,
    ) -> ComplianceResult:
        """Run a full ICNIRP 2020 compliance evaluation on this result.

        Populates all available checks from the result fields. Requires
        ``freq_hz`` to be set. Uses general public scenario by default.

        Parameters
        ----------
        scenario : ExposureScenario or None
            Defaults to general public.
        """
        from aegis.compliance import ExposureScenario as _ES
        from aegis.compliance import evaluate_compliance as _eval

        if self.freq_hz is None:
            raise ValueError("freq_hz must be set on DosimetryResult for compliance evaluation")

        if scenario is None:
            scenario = _ES.GENERAL_PUBLIC

        peak_4 = self.peak_sab_averaged
        peak_1 = float(np.max(self.sab_1cm2_averaged)) if self.sab_1cm2_averaged is not None else None
        sinc_peak = float(np.max(self.sinc_averaged)) if self.sinc_averaged is not None else None

        return _eval(
            freq_hz=self.freq_hz,
            scenario=scenario,
            sab_4cm2=peak_4,
            sab_1cm2=peak_1,
            sar_wb=self.sar_wb,
            sinc_local=sinc_peak,
        )

    def __repr__(self) -> str:
        parts = [
            f"DosimetryResult(level={self.fidelity_level}",
            f"p_abs={self.p_abs:.4g} W",
            f"peak_sab={self.peak_sab:.4g} W/m^2",
        ]
        if self.sar_wb is not None:
            parts.append(f"sar_wb={self.sar_wb:.4g} W/kg")
        return ", ".join(parts) + ")"
