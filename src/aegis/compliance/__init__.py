"""ICNIRP 2020 compliance limits for EMF exposure above 6 GHz.

Reference: ICNIRP, "Guidelines for Limiting Exposure to Electromagnetic
Fields (100 kHz to 300 GHz)," Health Physics, vol. 118, no. 5, 2020.

Covers both general public and occupational scenarios. Frequency range: >6 GHz
to 300 GHz. Tables 2, 5, and 6 are implemented.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass

__all__ = [
    "ExposureScenario",
    "ICNIRPLimits",
    "ComplianceCheck",
    "ComplianceResult",
    "icnirp_limits",
    "evaluate_compliance",
    "max_compliant_power",
    "power_sweep",
    "margin_db",
    "summary_text",
    # Backward-compat
    "ICNIRP_2020",
    "is_compliant_sab",
    "is_compliant_sar",
]


# ---------------------------------------------------------------------------
# String constants (avoid duplicate literals)
# ---------------------------------------------------------------------------

_UNIT_WM2 = "W/m^2"

# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------


class ExposureScenario(enum.Enum):
    """ICNIRP exposure scenario."""

    GENERAL_PUBLIC = "general_public"
    OCCUPATIONAL = "occupational"


@dataclass(frozen=True)
class ICNIRPLimits:
    """ICNIRP 2020 limits for a specific scenario and frequency.

    Attributes
    ----------
    scenario : ExposureScenario
    freq_hz : float
    sab_4cm2 : absorbed power density limit over 4 cm^2 [W/m^2]
    sab_1cm2 : absorbed power density limit over 1 cm^2 [W/m^2], None if <= 30 GHz
    sar_wb : whole-body SAR [W/kg]
    sinc_local : local incident power density limit [W/m^2] (Table 6)
    sinc_whole_body : whole-body incident power density limit [W/m^2] (Table 5)
    """

    scenario: ExposureScenario
    freq_hz: float
    sab_4cm2: float
    sab_1cm2: float | None
    sar_wb: float
    sinc_local: float
    sinc_whole_body: float


@dataclass(frozen=True)
class ComplianceCheck:
    """Result of checking a single quantity against its ICNIRP limit.

    Attributes
    ----------
    value : measured or computed value
    limit : ICNIRP limit
    unit : physical unit string
    label : human-readable name for this check
    """

    value: float
    limit: float
    unit: str
    label: str

    @property
    def compliant(self) -> bool:
        """True if value <= limit (ICNIRP uses <= for compliance)."""
        return self.value <= self.limit

    @property
    def margin_db(self) -> float:
        """Compliance margin in dB: 10 * log10(limit / value).

        Positive means compliant, negative means exceeded.
        """
        if self.value <= 0:
            return float("inf")
        return float(10.0 * math.log10(self.limit / self.value))

    @property
    def ratio(self) -> float:
        """value / limit. Values > 1.0 indicate exceedance."""
        if self.limit == 0:
            return float("inf")
        return self.value / self.limit


@dataclass(frozen=True)
class ComplianceResult:
    """Full ICNIRP 2020 compliance assessment.

    Attributes
    ----------
    scenario : ExposureScenario
    freq_hz : float
    sab_4cm2 : ComplianceCheck for S_ab over 4 cm^2
    sab_1cm2 : ComplianceCheck for S_ab over 1 cm^2, or None if <= 30 GHz
    sar_wb : ComplianceCheck for whole-body SAR
    sinc_local : ComplianceCheck for local incident power density
    sinc_whole_body : ComplianceCheck for whole-body incident power density
    """

    scenario: ExposureScenario
    freq_hz: float
    sab_4cm2: ComplianceCheck | None
    sab_1cm2: ComplianceCheck | None
    sar_wb: ComplianceCheck | None
    sinc_local: ComplianceCheck | None
    sinc_whole_body: ComplianceCheck | None

    @property
    def all_checks(self) -> list[ComplianceCheck]:
        """All non-None compliance checks."""
        checks: list[ComplianceCheck] = []
        for field in (
            self.sab_4cm2,
            self.sab_1cm2,
            self.sar_wb,
            self.sinc_local,
            self.sinc_whole_body,
        ):
            if field is not None:
                checks.append(field)
        return checks

    @property
    def overall_pass(self) -> bool:
        """True if all checks pass. True vacuously if no checks present."""
        return all(c.compliant for c in self.all_checks)

    @property
    def margin_db(self) -> float:
        """Tightest (smallest) margin across all checks, in dB.

        Returns inf if no checks are present.
        """
        checks = self.all_checks
        if not checks:
            return float("inf")
        return min(c.margin_db for c in checks)


# ---------------------------------------------------------------------------
# Limit computation (Tables 2, 5, 6)
# ---------------------------------------------------------------------------

# Frequency bounds (Hz)
_FREQ_MIN_HZ = 6.0e9  # exclusive lower bound: > 6 GHz
_FREQ_MAX_HZ = 300.0e9  # inclusive upper bound: 300 GHz
_FREQ_1CM2_THRESHOLD_HZ = 30.0e9  # 1 cm^2 limit only above 30 GHz


def _validate_freq(freq_hz: float) -> None:
    """Raise ValueError if freq outside the supported range (>6 to 300 GHz)."""
    if freq_hz <= _FREQ_MIN_HZ or freq_hz > _FREQ_MAX_HZ:
        raise ValueError(
            f"Frequency {freq_hz / 1e9:.3f} GHz is outside the supported ICNIRP 2020 range (>6 GHz to 300 GHz)"
        )


def icnirp_limits(
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    freq_hz: float = 28.0e9,
) -> ICNIRPLimits:
    """Compute ICNIRP 2020 limits for a given scenario and frequency.

    Parameters
    ----------
    scenario : ExposureScenario
        General public or occupational.
    freq_hz : float
        Frequency in Hz. Must be > 6 GHz and <= 300 GHz.

    Returns
    -------
    ICNIRPLimits
        All applicable limits at this frequency.
    """
    _validate_freq(freq_hz)

    freq_ghz = freq_hz / 1e9

    if scenario == ExposureScenario.GENERAL_PUBLIC:
        sab_4cm2 = 20.0
        sab_1cm2 = 40.0 if freq_hz > _FREQ_1CM2_THRESHOLD_HZ else None
        sar_wb = 0.08
        sinc_local = 55.0 / freq_ghz**0.177
        sinc_whole_body = 10.0
    else:
        # Occupational
        sab_4cm2 = 100.0
        sab_1cm2 = 200.0 if freq_hz > _FREQ_1CM2_THRESHOLD_HZ else None
        sar_wb = 0.4
        sinc_local = 275.0 / freq_ghz**0.177
        sinc_whole_body = 50.0

    return ICNIRPLimits(
        scenario=scenario,
        freq_hz=freq_hz,
        sab_4cm2=sab_4cm2,
        sab_1cm2=sab_1cm2,
        sar_wb=sar_wb,
        sinc_local=sinc_local,
        sinc_whole_body=sinc_whole_body,
    )


# ---------------------------------------------------------------------------
# Compliance evaluation
# ---------------------------------------------------------------------------


def evaluate_compliance(
    *,
    freq_hz: float,
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    sab_4cm2: float | None = None,
    sab_1cm2: float | None = None,
    sar_wb: float | None = None,
    sinc_local: float | None = None,
    sinc_whole_body: float | None = None,
) -> ComplianceResult:
    """Evaluate ICNIRP 2020 compliance for measured/computed quantities.

    Only checks for which values are provided will be included. Pass None
    for quantities that are not available.

    Parameters
    ----------
    freq_hz : float
        Frequency in Hz. Must be > 6 GHz and <= 300 GHz.
    scenario : ExposureScenario
        General public or occupational.
    sab_4cm2 : float or None
        Measured S_ab averaged over 4 cm^2 [W/m^2].
    sab_1cm2 : float or None
        Measured S_ab averaged over 1 cm^2 [W/m^2]. Ignored if freq <= 30 GHz.
    sar_wb : float or None
        Whole-body SAR [W/kg].
    sinc_local : float or None
        Local incident power density [W/m^2].
    sinc_whole_body : float or None
        Whole-body incident power density [W/m^2].

    Returns
    -------
    ComplianceResult
    """
    limits = icnirp_limits(scenario, freq_hz)

    check_sab_4 = None
    if sab_4cm2 is not None:
        check_sab_4 = ComplianceCheck(
            value=sab_4cm2,
            limit=limits.sab_4cm2,
            unit=_UNIT_WM2,
            label="S_ab (4 cm^2)",
        )

    check_sab_1 = None
    if sab_1cm2 is not None and limits.sab_1cm2 is not None:
        check_sab_1 = ComplianceCheck(
            value=sab_1cm2,
            limit=limits.sab_1cm2,
            unit=_UNIT_WM2,
            label="S_ab (1 cm^2)",
        )

    check_sar = None
    if sar_wb is not None:
        check_sar = ComplianceCheck(
            value=sar_wb,
            limit=limits.sar_wb,
            unit="W/kg",
            label="SAR_wb",
        )

    check_sinc_local = None
    if sinc_local is not None:
        check_sinc_local = ComplianceCheck(
            value=sinc_local,
            limit=limits.sinc_local,
            unit=_UNIT_WM2,
            label="S_inc (local)",
        )

    check_sinc_wb = None
    if sinc_whole_body is not None:
        check_sinc_wb = ComplianceCheck(
            value=sinc_whole_body,
            limit=limits.sinc_whole_body,
            unit=_UNIT_WM2,
            label="S_inc (whole-body)",
        )

    return ComplianceResult(
        scenario=scenario,
        freq_hz=freq_hz,
        sab_4cm2=check_sab_4,
        sab_1cm2=check_sab_1,
        sar_wb=check_sar,
        sinc_local=check_sinc_local,
        sinc_whole_body=check_sinc_wb,
    )


# ---------------------------------------------------------------------------
# Standalone margin_db helper
# ---------------------------------------------------------------------------


def margin_db(value: float, limit: float) -> float:
    """Compliance margin in dB: 10 * log10(limit / value).

    Positive means compliant (value below limit), negative means exceeded.
    Raises ValueError if value <= 0.
    """
    if value <= 0:
        raise ValueError("value must be positive")
    return float(10.0 * math.log10(limit / value))


# ---------------------------------------------------------------------------
# Maximum compliant power
# ---------------------------------------------------------------------------


def max_compliant_power(
    result: ComplianceResult,
    ref_power_w: float,
) -> float:
    """Compute the maximum transmit power that keeps all checks compliant.

    For incoherent dosimetry (levels 0-6) and coherent (levels 7-8), S_ab
    scales linearly with transmit power P. Given a ComplianceResult computed
    at reference power ``ref_power_w``, this function finds the largest P
    such that all measured quantities stay within their ICNIRP limits.

    Parameters
    ----------
    result : ComplianceResult
        A compliance evaluation from ``evaluate_compliance()``.
    ref_power_w : float
        The transmit power [W] at which the result was computed. Must be positive.

    Returns
    -------
    float
        Maximum compliant transmit power in watts. Returns ``inf`` if no
        checks are present or all measured values are zero. Returns 0.0
        if any check has a zero limit (should not happen for valid ICNIRP).
    """
    if ref_power_w <= 0:
        raise ValueError("ref_power_w must be positive")

    checks = result.all_checks
    if not checks:
        return float("inf")

    min_ratio = float("inf")
    for check in checks:
        if check.value <= 0:
            continue
        ratio = check.limit / check.value
        min_ratio = min(min_ratio, ratio)

    if min_ratio == float("inf"):
        return float("inf")

    return ref_power_w * min_ratio


# ---------------------------------------------------------------------------
# Power sweep
# ---------------------------------------------------------------------------


def power_sweep(
    result: ComplianceResult,
    ref_power_w: float,
    power_range_w: list[float] | None = None,
    n_points: int = 50,
) -> dict:
    """Compute compliance margin versus transmit power.

    Given a ComplianceResult at ``ref_power_w``, scales linearly to produce
    a compliance-vs-power curve. Useful for finding the compliance boundary
    and understanding headroom.

    Parameters
    ----------
    result : ComplianceResult
        Compliance evaluation at the reference power.
    ref_power_w : float
        Reference transmit power [W].
    power_range_w : list of two floats, or None
        [P_min, P_max] in watts. Defaults to [ref_power_w / 100, ref_power_w * 100].
    n_points : int
        Number of points in the sweep.

    Returns
    -------
    dict with keys:
        power_w : (n_points,) array of transmit powers [W]
        power_dbm : (n_points,) array of transmit powers [dBm]
        margin_db : (n_points,) tightest compliance margin [dB] at each power
        compliant : (n_points,) boolean array, True where all checks pass
        p_max_w : maximum compliant power [W]
        p_max_dbm : maximum compliant power [dBm]
    """
    import numpy as np

    if ref_power_w <= 0:
        raise ValueError("ref_power_w must be positive")

    if power_range_w is None:
        power_range_w = [ref_power_w / 100, ref_power_w * 100]

    p_min, p_max = power_range_w
    powers = np.geomspace(p_min, p_max, n_points)

    margins = np.empty(n_points)
    compliant = np.empty(n_points, dtype=bool)

    checks = result.all_checks
    if not checks:
        return {
            "power_w": powers,
            "power_dbm": 10 * np.log10(powers * 1e3),
            "margin_db": np.full(n_points, float("inf")),
            "compliant": np.ones(n_points, dtype=bool),
            "p_max_w": float("inf"),
            "p_max_dbm": float("inf"),
        }

    for i, p in enumerate(powers):
        scale = p / ref_power_w
        min_margin = float("inf")
        for check in checks:
            scaled_value = check.value * scale
            m = 10 * math.log10(check.limit / scaled_value) if scaled_value > 0 else float("inf")
            min_margin = min(min_margin, m)
        margins[i] = min_margin
        compliant[i] = min_margin >= 0

    p_max_val = max_compliant_power(result, ref_power_w)
    p_max_dbm = 10 * math.log10(p_max_val * 1e3) if p_max_val < float("inf") else float("inf")

    return {
        "power_w": powers,
        "power_dbm": 10 * np.log10(powers * 1e3),
        "margin_db": margins,
        "compliant": compliant,
        "p_max_w": p_max_val,
        "p_max_dbm": p_max_dbm,
    }


# ---------------------------------------------------------------------------
# Summary text
# ---------------------------------------------------------------------------


def summary_text(
    result: ComplianceResult,
    tx_power_dbm: float | None = None,
) -> str:
    """Human-readable compliance summary.

    Parameters
    ----------
    result : ComplianceResult
        The compliance evaluation result.
    tx_power_dbm : float or None
        Transmit power in dBm, shown if provided.

    Returns
    -------
    str
        Multi-line plain-text summary.
    """
    lines: list[str] = []
    lines.append(f"ICNIRP 2020 compliance ({result.scenario.value})")
    lines.append(f"Frequency: {result.freq_hz / 1e9:.3f} GHz")

    if tx_power_dbm is not None:
        lines.append(f"Tx power: {tx_power_dbm:.1f} dBm")

    lines.append("")

    for check in result.all_checks:
        status = "PASS" if check.compliant else "FAIL"
        lines.append(
            f"  {check.label}: {check.value:.6g} / {check.limit:.6g} {check.unit} "
            f"[{status}] (margin {check.margin_db:+.1f} dB)"
        )

    lines.append("")
    overall = "PASS" if result.overall_pass else "FAIL"
    lines.append(f"Overall: {overall} (tightest margin: {result.margin_db:+.1f} dB)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward-compat shim
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LegacyLimits:
    """Legacy limits dataclass for backward compatibility.

    Consumers access ICNIRP_2020.sab_peak and ICNIRP_2020.sar_wb.
    """

    sab_peak: float
    sar_wb: float
    averaging_area_cm2: float


# Correct ICNIRP 2020 general public limit: 20 W/m^2 over 4 cm^2 (Table 2)
ICNIRP_2020 = _LegacyLimits(sab_peak=20.0, sar_wb=0.08, averaging_area_cm2=4.0)


def is_compliant_sab(peak_sab_averaged: float, limits: _LegacyLimits = ICNIRP_2020) -> bool:
    """Check if peak spatially averaged S_ab is below the ICNIRP limit.

    Backward-compat function. Prefer evaluate_compliance() for new code.
    """
    return peak_sab_averaged <= limits.sab_peak


def is_compliant_sar(sar_wb: float, limits: _LegacyLimits = ICNIRP_2020) -> bool:
    """Check if whole-body SAR is below the ICNIRP limit.

    Backward-compat function. Prefer evaluate_compliance() for new code.
    """
    return sar_wb <= limits.sar_wb
