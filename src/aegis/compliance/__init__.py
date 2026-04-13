"""ICNIRP 2020 compliance limits for EMF exposure (100 kHz to 300 GHz).

Reference: ICNIRP, "Guidelines for Limiting Exposure to Electromagnetic
Fields (100 kHz to 300 GHz)," Health Physics, vol. 118, no. 5, 2020.

Covers both general public and occupational scenarios. Above 6 GHz, absorbed
power density (S_ab), incident power density (S_inc), and whole-body SAR limits
are evaluated. Below 6 GHz, only whole-body SAR is checked (local SAR over
10 g cubic mass is not yet implemented).
"""

from __future__ import annotations

import enum
import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aegis.defaults import DEFAULT_FREQ_HZ

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "ExposureScenario",
    "ICNIRPLimits",
    "ComplianceCheck",
    "ComplianceResult",
    "icnirp_limits",
    "evaluate_compliance",
    "max_compliant_power",
    "margin_db",
    "summary_text",
    "power_sweep",
    "frequency_sweep",
    "compliance_heatmap",
    "link_budget_compliance",
    "spatial_compliance_grid",
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
    sab_4cm2 : absorbed power density limit over 4 cm^2 [W/m^2], None if <= 6 GHz
    sab_1cm2 : absorbed power density limit over 1 cm^2 [W/m^2], None if <= 30 GHz
    sar_wb : whole-body SAR [W/kg]
    sinc_local : local incident power density limit [W/m^2] (Table 6), None if <= 6 GHz
    sinc_whole_body : whole-body incident power density limit [W/m^2] (Table 5), None if <= 6 GHz
    """

    scenario: ExposureScenario
    freq_hz: float
    sab_4cm2: float | None
    sab_1cm2: float | None
    sar_wb: float
    sinc_local: float | None
    sinc_whole_body: float | None


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
    def overall_pass(self) -> bool | None:
        """True if all checks pass, False if any fail, None if no checks present."""
        checks = self.all_checks
        if not checks:
            return None
        return all(c.compliant for c in checks)

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
_FREQ_MIN_HZ = 100.0e3  # 100 kHz (ICNIRP 2020 lower bound)
_FREQ_MAX_HZ = 300.0e9  # inclusive upper bound: 300 GHz
_FREQ_SAB_THRESHOLD_HZ = 6.0e9  # S_ab limits apply above 6 GHz
_FREQ_1CM2_THRESHOLD_HZ = 30.0e9  # 1 cm^2 limit only above 30 GHz


def _validate_freq(freq_hz: float) -> None:
    """Raise ValueError if freq outside the ICNIRP 2020 range (100 kHz to 300 GHz)."""
    if not math.isfinite(freq_hz):
        raise ValueError(f"Frequency must be finite, got {freq_hz}")
    if freq_hz < _FREQ_MIN_HZ or freq_hz > _FREQ_MAX_HZ:
        raise ValueError(f"Frequency {freq_hz / 1e9:.6g} GHz is outside the ICNIRP 2020 range (100 kHz to 300 GHz)")


def icnirp_limits(
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    freq_hz: float = DEFAULT_FREQ_HZ,
) -> ICNIRPLimits:
    """Compute ICNIRP 2020 limits for a given scenario and frequency.

    Parameters
    ----------
    scenario : ExposureScenario
        General public or occupational.
    freq_hz : float
        Frequency in Hz. Must be >= 100 kHz and <= 300 GHz.
        Above 6 GHz all limits are returned. Below 6 GHz only SAR_wb
        is returned (S_ab and S_inc are set to None).

    Returns
    -------
    ICNIRPLimits
        All applicable limits at this frequency.
    """
    _validate_freq(freq_hz)

    freq_ghz = freq_hz / 1e9

    sar_wb = 0.08 if scenario == ExposureScenario.GENERAL_PUBLIC else 0.4

    # Below 6 GHz: only SAR_wb applies. S_ab and S_inc limits are for >6 GHz.
    if freq_hz <= _FREQ_SAB_THRESHOLD_HZ:
        return ICNIRPLimits(
            scenario=scenario,
            freq_hz=freq_hz,
            sab_4cm2=None,
            sab_1cm2=None,
            sar_wb=sar_wb,
            sinc_local=None,
            sinc_whole_body=None,
        )

    if scenario == ExposureScenario.GENERAL_PUBLIC:
        sab_4cm2 = 20.0
        sab_1cm2 = 40.0 if freq_hz > _FREQ_1CM2_THRESHOLD_HZ else None
        sinc_local = 55.0 / freq_ghz**0.177
        sinc_whole_body = 10.0
    else:
        # Occupational
        sab_4cm2 = 100.0
        sab_1cm2 = 200.0 if freq_hz > _FREQ_1CM2_THRESHOLD_HZ else None
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

    Only checks for which both a value and a limit are available will be
    included. Below 6 GHz, only SAR_wb is checked.

    Parameters
    ----------
    freq_hz : float
        Frequency in Hz. Must be >= 100 kHz and <= 300 GHz.
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
    if sab_4cm2 is not None and limits.sab_4cm2 is not None:
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
    if sinc_local is not None and limits.sinc_local is not None:
        check_sinc_local = ComplianceCheck(
            value=sinc_local,
            limit=limits.sinc_local,
            unit=_UNIT_WM2,
            label="S_inc (local)",
        )

    check_sinc_wb = None
    if sinc_whole_body is not None and limits.sinc_whole_body is not None:
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
    overall = "N/A" if result.overall_pass is None else "PASS" if result.overall_pass else "FAIL"
    lines.append(f"Overall: {overall} (tightest margin: {result.margin_db:+.1f} dB)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Power sweep
# ---------------------------------------------------------------------------


def power_sweep(
    result: ComplianceResult,
    ref_power_w: float,
    p_min_w: float | None = None,
    p_max_w: float | None = None,
    n_points: int = 200,
) -> dict:
    """Compute compliance margin vs transmit power.

    S_ab scales linearly with P, so all checks scale by P/P_ref. This
    function evaluates compliance across a power range without re-running
    the dosimetry engine.

    Parameters
    ----------
    result : ComplianceResult
        A compliance evaluation at reference power ref_power_w.
    ref_power_w : float
        Transmit power [W] at which result was computed.
    p_min_w : float or None
        Minimum power [W]. Defaults to ref_power_w / 100.
    p_max_w : float or None
        Maximum power [W]. Defaults to ref_power_w * 100.
    n_points : int
        Number of power samples.

    Returns
    -------
    dict with keys:
        power_w : (n_points,) power in watts
        power_dbm : (n_points,) power in dBm
        margin_db : (n_points,) tightest compliance margin in dB
        compliant : (n_points,) boolean mask
        p_max_compliant_w : float, maximum compliant power [W]
    """
    import numpy as np

    if ref_power_w <= 0:
        raise ValueError("ref_power_w must be positive")

    if p_min_w is None:
        p_min_w = ref_power_w / 100.0
    if p_max_w is None:
        p_max_w = ref_power_w * 100.0

    power_w = np.geomspace(p_min_w, p_max_w, n_points)
    power_dbm = 10.0 * np.log10(power_w * 1e3)  # W -> mW -> dBm

    checks = result.all_checks
    p_max_compliant = max_compliant_power(result, ref_power_w)

    if not checks:
        return {
            "power_w": power_w,
            "power_dbm": power_dbm,
            "margin_db": np.full(n_points, float("inf")),
            "compliant": np.ones(n_points, dtype=bool),
            "p_max_compliant_w": float("inf"),
        }

    # Vectorized: compute margin for all power levels and checks at once.
    values = np.array([c.value for c in checks])
    limits = np.array([c.limit for c in checks])

    # Filter out checks with non-positive values (cannot compute log)
    valid = values > 0
    if not np.any(valid):
        return {
            "power_w": power_w,
            "power_dbm": power_dbm,
            "margin_db": np.full(n_points, float("inf")),
            "compliant": np.ones(n_points, dtype=bool),
            "p_max_compliant_w": p_max_compliant,
        }

    values = values[valid]
    limits = limits[valid]
    scales = power_w / ref_power_w  # (n_points,)
    # margins shape: (n_checks_valid, n_points)
    scaled_values = values[:, None] * scales[None, :]
    margins = 10.0 * np.log10(limits[:, None] / scaled_values)
    margin_db_arr = np.min(margins, axis=0)  # tightest check at each power

    return {
        "power_w": power_w,
        "power_dbm": power_dbm,
        "margin_db": margin_db_arr,
        "compliant": margin_db_arr >= 0,
        "p_max_compliant_w": p_max_compliant,
    }


# ---------------------------------------------------------------------------
# Frequency sweep
# ---------------------------------------------------------------------------


def frequency_sweep(
    *,
    sab_4cm2: float | None = None,
    sab_1cm2: float | None = None,
    sar_wb: float | None = None,
    sinc_local: float | None = None,
    sinc_whole_body: float | None = None,
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    freq_min_hz: float = 7e9,
    freq_max_hz: float = 100e9,
    n_points: int = 200,
) -> dict:
    """Evaluate compliance across a frequency range.

    The measured values are assumed constant (worst-case: same exposure
    level across frequency). The ICNIRP limits change with frequency
    (especially sinc_local ~ 1/f^0.177), so compliance margin varies.

    This answers: "At which frequencies is this exposure level compliant?"

    Parameters
    ----------
    sab_4cm2, sab_1cm2, sar_wb, sinc_local, sinc_whole_body : float or None
        Measured quantities (constant across frequency).
    scenario : ExposureScenario
    freq_min_hz, freq_max_hz : float
        Frequency range (must be within 100 kHz to 300 GHz).
    n_points : int
        Number of frequency samples.

    Returns
    -------
    dict with keys:
        freq_hz : (n_points,) frequency array
        freq_ghz : (n_points,) frequency in GHz
        margin_db : (n_points,) tightest margin at each frequency
        compliant : (n_points,) boolean mask
        results : list of ComplianceResult at each frequency
    """
    import numpy as np

    freq_hz_arr = np.geomspace(freq_min_hz, freq_max_hz, n_points)
    margin_db_arr = np.zeros(n_points)
    compliant_arr = np.ones(n_points, dtype=bool)
    results_list = []

    for i, f in enumerate(freq_hz_arr):
        cr = evaluate_compliance(
            freq_hz=float(f),
            scenario=scenario,
            sab_4cm2=sab_4cm2,
            sab_1cm2=sab_1cm2,
            sar_wb=sar_wb,
            sinc_local=sinc_local,
            sinc_whole_body=sinc_whole_body,
        )
        results_list.append(cr)
        margin_db_arr[i] = cr.margin_db
        overall = cr.overall_pass
        compliant_arr[i] = overall if overall is not None else True

    return {
        "freq_hz": freq_hz_arr,
        "freq_ghz": freq_hz_arr / 1e9,
        "margin_db": margin_db_arr,
        "compliant": compliant_arr,
        "results": results_list,
    }


# ---------------------------------------------------------------------------
# Compliance heatmap (2D: power x frequency)
# ---------------------------------------------------------------------------


def compliance_heatmap(
    *,
    sab_4cm2: float,
    ref_power_w: float = 1.0,
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    freq_min_hz: float = 7e9,
    freq_max_hz: float = 100e9,
    p_min_w: float | None = None,
    p_max_w: float | None = None,
    n_freq: int = 50,
    n_power: int = 50,
    sinc_local: float | None = None,
) -> dict:
    """2D compliance map over frequency and transmit power.

    Given an S_ab measurement at reference power, compute the compliance
    margin across the (frequency, power) plane. S_ab scales linearly with
    power. The ICNIRP S_ab limit is constant (20 or 100 W/m^2) but other
    limits (sinc_local) vary with frequency.

    This answers: "For what (frequency, power) combinations is this
    exposure scenario compliant?"

    Parameters
    ----------
    sab_4cm2 : float
        Peak spatially averaged S_ab [W/m^2] at ref_power_w.
    ref_power_w : float
        Transmit power [W] at which sab_4cm2 was measured.
    scenario : ExposureScenario
    freq_min_hz, freq_max_hz : float
        Frequency range.
    p_min_w, p_max_w : float or None
        Power range. Defaults to ref_power_w / 100 .. ref_power_w * 100.
    n_freq, n_power : int
        Grid resolution.
    sinc_local : float or None
        Peak incident power density S_inc [W/m^2] at ref_power_w.
        When provided, also checks the ICNIRP sinc_local limit
        (55/f_GHz^0.177 for GP, 275/f_GHz^0.177 for occupational)
        which varies with frequency, making the heatmap non-degenerate.

    Returns
    -------
    dict with keys:
        freq_hz : (n_freq,) frequency array
        power_w : (n_power,) power array
        power_dbm : (n_power,) power in dBm
        margin_db : (n_power, n_freq) margin heatmap (positive = compliant)
        compliant : (n_power, n_freq) boolean mask
        p_max_per_freq : (n_freq,) max compliant power at each frequency
    """
    import numpy as np

    if ref_power_w <= 0:
        raise ValueError("ref_power_w must be positive")
    if p_min_w is None:
        p_min_w = ref_power_w / 100.0
    if p_max_w is None:
        p_max_w = ref_power_w * 100.0

    freq_hz_arr = np.geomspace(freq_min_hz, freq_max_hz, n_freq)
    power_w_arr = np.geomspace(p_min_w, p_max_w, n_power)
    power_dbm_arr = 10.0 * np.log10(power_w_arr * 1e3)

    # Vectorized: S_ab scales linearly with power
    # scaled_sab shape: (n_power,)
    scaled_sab = sab_4cm2 * (power_w_arr / ref_power_w)

    # S_ab limit per frequency (None below 6 GHz, constant above)
    sab_limit_vals = [icnirp_limits(scenario, float(f)).sab_4cm2 for f in freq_hz_arr]
    sab_limits = np.array([v if v is not None else np.inf for v in sab_limit_vals])
    has_any_sab_limit = any(v is not None for v in sab_limit_vals) and sab_4cm2 > 0

    if has_any_sab_limit:
        # sab margin: (n_power, 1) vs (1, n_freq) -> (n_power, n_freq)
        with np.errstate(divide="ignore"):
            sab_margin = np.where(
                scaled_sab[:, None] <= 0,
                np.inf,
                10.0 * np.log10(sab_limits[None, :] / scaled_sab[:, None]),
            )
        margin_grid = sab_margin
        p_max_per_freq = ref_power_w * sab_limits / sab_4cm2
    else:
        margin_grid = np.full((len(power_w_arr), len(freq_hz_arr)), np.inf)
        p_max_per_freq = np.full(len(freq_hz_arr), float("inf"))

    # If sinc_local provided, also check frequency-dependent sinc limit
    if sinc_local is not None and sinc_local > 0:
        # Get sinc limits at each frequency: shape (n_freq,)
        sinc_limit_vals = [icnirp_limits(scenario, float(f)).sinc_local for f in freq_hz_arr]
        sinc_limits = np.array([v if v is not None else np.inf for v in sinc_limit_vals])

        # Scaled sinc: (n_power,)
        scaled_sinc = sinc_local * (power_w_arr / ref_power_w)

        # sinc margin: (n_power, 1) vs (1, n_freq) -> (n_power, n_freq)
        with np.errstate(divide="ignore"):
            sinc_margin = np.where(
                scaled_sinc[:, None] <= 0,
                np.inf,
                10.0 * np.log10(sinc_limits[None, :] / scaled_sinc[:, None]),
            )

        # Take the tighter (minimum) margin
        margin_grid = np.minimum(margin_grid, sinc_margin)

        # p_max from sinc at each frequency
        p_max_sinc = ref_power_w * sinc_limits / sinc_local
        p_max_per_freq = np.minimum(p_max_per_freq, p_max_sinc)

    return {
        "freq_hz": freq_hz_arr,
        "power_w": power_w_arr,
        "power_dbm": power_dbm_arr,
        "margin_db": margin_grid,
        "compliant": margin_grid >= 0,
        "p_max_per_freq": p_max_per_freq,
    }


# ---------------------------------------------------------------------------
# Link budget compliance
# ---------------------------------------------------------------------------


def link_budget_compliance(
    *,
    tx_power_w: float,
    antenna_gain_dbi: float = 0.0,
    distance_m: float,
    freq_hz: float,
    T0: float | None = None,
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
) -> dict:
    """Quick compliance check from RF link budget parameters.

    Estimates incident power density from free-space path loss and
    computes approximate S_ab using normal-incidence transmission.

    This is a conservative (worst-case) estimate: it assumes the body
    intercepts the full antenna beam at the given distance, with all
    power arriving at normal incidence. Real dosimetry with mesh geometry
    will give lower (more accurate) values.

    Parameters
    ----------
    tx_power_w : float
        Transmit power [W]. Must be positive.
    antenna_gain_dbi : float
        Antenna gain [dBi]. Default 0 (isotropic).
    distance_m : float
        Distance from antenna to body [m]. Must be positive.
    freq_hz : float
        Frequency [Hz]. Must be in ICNIRP range (100 kHz to 300 GHz).
    T0 : float or None
        Normal-incidence transmission coefficient. If None, estimated
        from skin tissue at the given frequency.
    scenario : ExposureScenario
        General public or occupational.

    Returns
    -------
    dict with keys:
        sinc : float, incident power density [W/m^2]
        sab_estimate : float, estimated S_ab [W/m^2]
        T0 : float, transmission coefficient used
        compliance : ComplianceResult
        compliant : bool
        margin_db : float
        max_tx_power_w : float, max compliant TX power [W]
        max_tx_power_dbm : float, max compliant TX power [dBm]
    """
    if tx_power_w <= 0:
        raise ValueError("tx_power_w must be positive")
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    _validate_freq(freq_hz)

    # Incident power density from free-space spreading + antenna gain
    gain_linear = 10.0 ** (antenna_gain_dbi / 10.0)
    sinc = tx_power_w * gain_linear / (4.0 * math.pi * distance_m**2)

    # Estimate T0 from skin tissue if not provided
    if T0 is None:
        try:
            from aegis.tissue.dielectric import TissueModel

            tissue = TissueModel.from_database("Skin", freq_hz)
            T0 = tissue.T0
        except ImportError:
            T0 = 0.4
        except Exception:
            logger.warning(
                "Failed to load tissue T0 for %.1f MHz, using fallback T0=0.4",
                freq_hz / 1e6,
                exc_info=True,
            )
            T0 = 0.4

    sab_estimate = sinc * T0

    # Evaluate compliance
    cr = evaluate_compliance(
        freq_hz=freq_hz,
        scenario=scenario,
        sab_4cm2=sab_estimate,
        sinc_local=sinc,
    )

    # Max compliant TX power: scale linearly
    p_max_w = max_compliant_power(cr, tx_power_w) if cr.all_checks else float("inf")
    p_max_dbm = 10.0 * math.log10(p_max_w * 1e3) if p_max_w < float("inf") else float("inf")

    return {
        "sinc": sinc,
        "sab_estimate": sab_estimate,
        "T0": T0,
        "compliance": cr,
        "compliant": cr.overall_pass,
        "margin_db": cr.margin_db,
        "max_tx_power_w": p_max_w,
        "max_tx_power_dbm": p_max_dbm,
    }


# ---------------------------------------------------------------------------
# Spatial compliance grid
# ---------------------------------------------------------------------------


def spatial_compliance_grid(
    *,
    station_lats: np.ndarray,
    station_lons: np.ndarray,
    station_eirp_dbm: np.ndarray,
    station_freq_hz: np.ndarray,
    station_heights_m: np.ndarray,
    grid_lats: np.ndarray,
    grid_lons: np.ndarray,
    scenario: ExposureScenario = ExposureScenario.GENERAL_PUBLIC,
    receiver_height_m: float = 1.5,
    T0: float | None = None,
) -> dict:
    """Compute ICNIRP compliance margin at a grid of receiver locations.

    For each grid point, sums incident power density from all stations
    using free-space path loss, estimates absorbed power density via T0,
    and evaluates the tightest ICNIRP compliance margin.

    Uses per-station frequency for correct limit evaluation. Multi-frequency
    cumulative exposure is assessed using the ICNIRP summation rule:
    sum(value_i / limit_i) <= 1 across frequency groups.

    Parameters
    ----------
    station_lats, station_lons : (N,) arrays
        Station positions in WGS84 degrees.
    station_eirp_dbm : (N,) array
        EIRP per station in dBm.
    station_freq_hz : (N,) array
        Operating frequency per station in Hz.
    station_heights_m : (N,) array
        Antenna height above ground per station in meters.
    grid_lats, grid_lons : (M,) arrays
        Receiver grid positions in WGS84 degrees.
    scenario : ExposureScenario
    receiver_height_m : float
        Receiver (body) height above ground in meters.
    T0 : float or None
        Normal-incidence transmission coefficient. If None, estimated
        from skin tissue at the EIRP-weighted mean frequency.

    Returns
    -------
    dict with keys:
        sinc : (M,) total incident power density at each grid point [W/m^2]
        sab_estimate : (M,) estimated S_ab at each grid point [W/m^2]
        margin_db : (M,) tightest ICNIRP compliance margin [dB]
        compliant : (M,) boolean, True if all limits satisfied
        freq_hz_dominant : float, EIRP-weighted mean frequency
        T0 : float, transmission coefficient used
    """
    import numpy as np

    station_lats = np.asarray(station_lats, dtype=np.float64)
    station_lons = np.asarray(station_lons, dtype=np.float64)
    station_eirp_dbm = np.asarray(station_eirp_dbm, dtype=np.float64)
    station_freq_hz = np.asarray(station_freq_hz, dtype=np.float64)
    station_heights_m = np.asarray(station_heights_m, dtype=np.float64)
    grid_lats = np.asarray(grid_lats, dtype=np.float64)
    grid_lons = np.asarray(grid_lons, dtype=np.float64)

    n_stations = len(station_lats)
    n_grid = len(grid_lats)

    if n_stations == 0:
        return {
            "sinc": np.zeros(n_grid),
            "sab_estimate": np.zeros(n_grid),
            "margin_db": np.full(n_grid, float("inf")),
            "compliant": np.ones(n_grid, dtype=bool),
            "freq_hz_dominant": 0.0,
            "T0": T0 or 0.4,
        }

    # EIRP in watts: shape (N,)
    eirp_w = 10.0 ** ((station_eirp_dbm - 30.0) / 10.0)

    # EIRP-weighted mean frequency for T0 estimation
    total_eirp = np.sum(eirp_w)
    if total_eirp > 0:
        freq_mean_hz = float(np.sum(station_freq_hz * eirp_w) / total_eirp)
    else:
        freq_mean_hz = float(np.median(station_freq_hz))

    # Estimate T0 from skin tissue if not provided
    if T0 is None:
        try:
            from aegis.tissue.dielectric import TissueModel

            tissue = TissueModel.from_database("Skin", freq_mean_hz)
            T0 = tissue.T0
        except Exception:
            T0 = 0.4

    # Haversine distance: grid (M,) x stations (N,) -> (M, N)
    lat1 = np.radians(grid_lats[:, None])  # (M, 1)
    lat2 = np.radians(station_lats[None, :])  # (1, N)
    dlat = lat2 - lat1
    dlon = np.radians(station_lons[None, :] - grid_lons[:, None])

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    horiz_dist_m = 6_371_000.0 * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))

    # 3D distance including height difference
    dh = station_heights_m[None, :] - receiver_height_m  # (1, N) broadcast to (M, N)
    dist_3d = np.sqrt(horiz_dist_m**2 + dh**2)
    dist_3d = np.maximum(dist_3d, 1.0)  # clamp to 1m minimum

    # Free-space incident power density: S_inc = EIRP / (4 pi d^2)
    # Shape: (M, N)
    sinc_per_station = eirp_w[None, :] / (4.0 * np.pi * dist_3d**2)

    # Total incident power density at each grid point: (M,)
    sinc_total = np.sum(sinc_per_station, axis=1)

    # Estimated absorbed power density (normal-incidence worst case)
    sab_estimate = sinc_total * T0

    # Evaluate compliance at the mean frequency
    margin_db_arr = np.full(n_grid, float("inf"))
    compliant_arr = np.ones(n_grid, dtype=bool)

    try:
        limits = icnirp_limits(scenario=scenario, freq_hz=freq_mean_hz)
    except ValueError:
        # Frequency outside ICNIRP range
        return {
            "sinc": sinc_total,
            "sab_estimate": sab_estimate,
            "margin_db": margin_db_arr,
            "compliant": compliant_arr,
            "freq_hz_dominant": freq_mean_hz,
            "T0": T0,
        }

    # Check S_ab (4 cm^2) - most relevant above 6 GHz
    if limits.sab_4cm2 is not None:
        with np.errstate(divide="ignore"):
            m = np.where(sab_estimate > 0, 10.0 * np.log10(limits.sab_4cm2 / sab_estimate), np.inf)
        margin_db_arr = np.minimum(margin_db_arr, m)
        compliant_arr &= sab_estimate <= limits.sab_4cm2

    # Check S_ab (1 cm^2) for >30 GHz
    if limits.sab_1cm2 is not None:
        with np.errstate(divide="ignore"):
            m = np.where(sab_estimate > 0, 10.0 * np.log10(limits.sab_1cm2 / sab_estimate), np.inf)
        margin_db_arr = np.minimum(margin_db_arr, m)
        compliant_arr &= sab_estimate <= limits.sab_1cm2

    # Check S_inc (whole-body)
    if limits.sinc_whole_body is not None:
        with np.errstate(divide="ignore"):
            m = np.where(sinc_total > 0, 10.0 * np.log10(limits.sinc_whole_body / sinc_total), np.inf)
        margin_db_arr = np.minimum(margin_db_arr, m)
        compliant_arr &= sinc_total <= limits.sinc_whole_body

    # Check S_inc (local)
    if limits.sinc_local is not None:
        with np.errstate(divide="ignore"):
            m = np.where(sinc_total > 0, 10.0 * np.log10(limits.sinc_local / sinc_total), np.inf)
        margin_db_arr = np.minimum(margin_db_arr, m)
        compliant_arr &= sinc_total <= limits.sinc_local

    return {
        "sinc": sinc_total,
        "sab_estimate": sab_estimate,
        "margin_db": margin_db_arr,
        "compliant": compliant_arr,
        "freq_hz_dominant": freq_mean_hz,
        "T0": T0,
    }


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
