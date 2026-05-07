"""Monostatic radar link budget and detection model for tier-C bystanders.

The paper §VI tier table claims the BS can localise non-cooperating
bystanders via monostatic ISAC on its own aperture. This module is the
back-of-envelope that has to either close that claim or refuse it.

Physics
-------
Monostatic radar equation (Skolnik, *Introduction to Radar Systems*,
3rd ed., eq. 2.6):

    P_r = (P_t G_t G_r lambda^2 sigma) / ((4 pi)^3 R^4)

with thermal noise floor ``N = k T0 B F`` (kTBF, F = noise figure) and
coherent integration gain ``10 log10(N_int)`` over a coherent
processing interval (Swerling-0 / non-fluctuating target). Detection
probability uses Albersheim's approximation (Albersheim 1969;
Skolnik §2.5), which is accurate to ~0.2 dB for Swerling-0 targets in
the regime ``10^-7 <= Pfa <= 10^-3`` and ``0.1 <= Pd <= 0.9``. We
extrapolate to Pd close to 1 since the tier-C link budget at plaza
range sits well above the design point.

Resolutions
-----------
- Range: ``c / (2 B)``. With the full 400 MHz NR FR2 carrier, this is
  0.375 m. With SSB-only sync band (~30 MHz), 5 m.
- Azimuth (uniform aperture): HPBW ``approx 0.886 lambda / D`` rad,
  with ``D = N_per_side * (lambda/2)`` for a half-wavelength ULA. An
  8x8 panel at 26 GHz gives 12.7 deg per axis; the paper's 6 deg
  number is off by 2x. Crossrange resolution is ``R * HPBW``.

This module deliberately omits multi-target angle estimation
(MUSIC / ESPRIT), micro-Doppler, polarimetric processing, and
multi-snapshot superresolution. The tier-C claim is presence + sector,
not body-scale localisation.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# Boltzmann constant
_K_B = 1.380649e-23
# Reference temperature [K]
_T0_K = 290.0
# Speed of light [m/s]
_C = 2.99792458e8
# kT in dBm/Hz at T0=290 K: 10*log10(k*T0 * 1e3) = -174 dBm/Hz
_KT_DBM_HZ = -173.975

__all__ = [
    "DetectionResult",
    "SensingGeometry",
    "angular_resolution_deg",
    "crossrange_resolution_m",
    "detection_probability",
    "monostatic_snr_db",
    "occupancy_envelope_density",
    "range_resolution_m",
    "tier_c_cell_area_m2",
]


# ---------------------------------------------------------------------------
# Geometry / resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SensingGeometry:
    """Geometric resolution cell for a uniform half-wavelength square panel.

    Attributes
    ----------
    azimuth_hpbw_deg : 3 dB beamwidth per principal axis [deg]
    range_resolution_m : range resolution from waveform bandwidth [m]
    crossrange_resolution_m : crossrange resolution at the requested range [m]
    cell_area_m2 : crossrange x range cell footprint at the requested range [m^2]
    """

    azimuth_hpbw_deg: float
    range_resolution_m: float
    crossrange_resolution_m: float
    cell_area_m2: float


def angular_resolution_deg(num_elements_per_side: int, freq_hz: float) -> float:
    """3 dB beamwidth (HPBW) of a square uniform half-wavelength panel.

    Uses the classical uniform-aperture HPBW ``0.886 lambda / D`` with
    ``D = N (lambda / 2)``, simplifying to ``0.886 * 2 / N`` rad.

    Parameters
    ----------
    num_elements_per_side : >= 1, count of elements along one principal axis
    freq_hz : carrier frequency [Hz] (kept in the signature for clarity even
        though it cancels in the half-wavelength-spaced result)

    Returns
    -------
    HPBW per axis in degrees.
    """
    if num_elements_per_side < 1:
        raise ValueError("num_elements_per_side must be >= 1")
    if freq_hz <= 0:
        raise ValueError("freq_hz must be positive")
    hpbw_rad = 0.886 * 2.0 / num_elements_per_side
    return math.degrees(hpbw_rad)


def range_resolution_m(bandwidth_hz: float) -> float:
    """Range resolution ``c / (2 B)`` for a matched-filter processed waveform."""
    if bandwidth_hz <= 0:
        raise ValueError("bandwidth_hz must be positive")
    return _C / (2.0 * bandwidth_hz)


def crossrange_resolution_m(range_m: float, hpbw_deg: float) -> float:
    """Crossrange (linear) resolution at ``range_m`` for the given HPBW."""
    if range_m <= 0:
        raise ValueError("range_m must be positive")
    if hpbw_deg <= 0:
        raise ValueError("hpbw_deg must be positive")
    return range_m * math.radians(hpbw_deg)


def tier_c_cell_area_m2(range_m: float, hpbw_deg: float, bandwidth_hz: float) -> float:
    """Resolution-cell footprint at ``range_m``: crossrange x range."""
    return crossrange_resolution_m(range_m, hpbw_deg) * range_resolution_m(bandwidth_hz)


# ---------------------------------------------------------------------------
# Link budget
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectionResult:
    """Output of one monostatic detection link-budget evaluation.

    Attributes
    ----------
    range_m : target range [m]
    snr_single_db : SNR before coherent integration [dB]
    snr_integrated_db : SNR after CPI integration [dB]
    pd : detection probability at the requested Pfa
    pfa : false-alarm probability used for Pd
    geometry : SensingGeometry at this range
    """

    range_m: float
    snr_single_db: float
    snr_integrated_db: float
    pd: float
    pfa: float
    geometry: SensingGeometry


def monostatic_snr_db(
    *,
    range_m: float,
    eirp_dbm: float,
    rx_gain_dbi: float,
    freq_hz: float,
    bandwidth_hz: float,
    rcs_dbsm: float = 0.0,
    noise_figure_db: float = 6.0,
    integration_gain_db: float = 0.0,
) -> tuple[float, float]:
    """Monostatic radar SNR before and after coherent integration.

    Parameters
    ----------
    range_m : two-way range to target [m]
    eirp_dbm : transmit EIRP into the beam [dBm] (= ``P_tx + G_tx``)
    rx_gain_dbi : receive aperture gain [dBi]
    freq_hz : carrier [Hz]
    bandwidth_hz : matched-filter bandwidth [Hz]
    rcs_dbsm : target RCS [dBsm]; 0 dBsm = 1 m^2, the convention for a
        standing torso at mmWave (Marchetti 2017, Chen 2018)
    noise_figure_db : receiver noise figure [dB]
    integration_gain_db : CPI coherent gain in dB (Swerling-0).
        Pass ``10 log10(N_sym)`` for ``N_sym`` symbols at full coherence.

    Returns
    -------
    (snr_single_db, snr_integrated_db) : SNR before and after CPI gain.
    """
    if range_m <= 0:
        raise ValueError("range_m must be positive")
    if freq_hz <= 0:
        raise ValueError("freq_hz must be positive")
    if bandwidth_hz <= 0:
        raise ValueError("bandwidth_hz must be positive")

    lam = _C / freq_hz
    # Radar equation in dBm form. The "(4 pi)^3 R^4" denominator and the
    # lambda^2 numerator are split across the two-way path-loss term.
    pr_dbm = (
        eirp_dbm
        + rx_gain_dbi
        + 20.0 * math.log10(lam)
        + rcs_dbsm
        - 30.0 * math.log10(4.0 * math.pi)
        - 40.0 * math.log10(range_m)
    )
    noise_dbm = _KT_DBM_HZ + 10.0 * math.log10(bandwidth_hz) + noise_figure_db
    snr_single = pr_dbm - noise_dbm
    snr_integrated = snr_single + integration_gain_db
    return snr_single, snr_integrated


def detection_probability(snr_db: float, pfa: float = 1e-6) -> float:
    """Albersheim's Pd approximation (Swerling-0, single-pulse equivalent).

    Inverts the textbook required-SNR-for-Pd formula
    (Albersheim 1969; Skolnik §2.5):

        SNR_dB ~= -5 log10(N) + (6.2 + 4.54 / sqrt(N + 0.44))
                                * log10(A + 0.12 A B + 1.7 B)

    with ``A = ln(0.62 / Pfa)`` and ``B = ln(Pd / (1 - Pd))``. At ``N = 1``
    (one coherent CPI taken as a single matched-filter output) the
    relation is linear in ``B`` and inverts in closed form. Accurate to
    ~0.2 dB in ``10^-7 <= Pfa <= 10^-3`` and ``0.1 <= Pd <= 0.9``;
    saturates cleanly outside that band.

    Parameters
    ----------
    snr_db : post-integration SNR [dB]
    pfa : probability of false alarm; 1e-6 is the conventional default

    Returns
    -------
    Pd in [0, 1].
    """
    if not (0.0 < pfa < 1.0):
        raise ValueError("pfa must be in (0, 1)")
    a = math.log(0.62 / pfa)
    # N = 1 single CPI: -5 log10(N) = 0 and the prefactor is 6.2 + 4.54/sqrt(1.44).
    prefactor = 6.2 + 4.54 / math.sqrt(1.44)
    x = 10.0 ** (snr_db / prefactor)
    b = (x - a) / (0.12 * a + 1.7)
    # Pd = sigmoid(B). Saturate cleanly for very large |b|.
    if b >= 50.0:
        return 1.0
    if b <= -50.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-b))


def detection(
    *,
    range_m: float,
    eirp_dbm: float,
    rx_gain_dbi: float,
    freq_hz: float,
    bandwidth_hz: float,
    rcs_dbsm: float = 0.0,
    noise_figure_db: float = 6.0,
    integration_gain_db: float = 0.0,
    pfa: float = 1e-6,
    num_elements_per_side: int = 8,
) -> DetectionResult:
    """Bundled link-budget + Pd + geometry evaluation at a single range."""
    snr1, snr_int = monostatic_snr_db(
        range_m=range_m,
        eirp_dbm=eirp_dbm,
        rx_gain_dbi=rx_gain_dbi,
        freq_hz=freq_hz,
        bandwidth_hz=bandwidth_hz,
        rcs_dbsm=rcs_dbsm,
        noise_figure_db=noise_figure_db,
        integration_gain_db=integration_gain_db,
    )
    pd = detection_probability(snr_int, pfa=pfa)
    hpbw = angular_resolution_deg(num_elements_per_side, freq_hz)
    geom = SensingGeometry(
        azimuth_hpbw_deg=hpbw,
        range_resolution_m=range_resolution_m(bandwidth_hz),
        crossrange_resolution_m=crossrange_resolution_m(range_m, hpbw),
        cell_area_m2=tier_c_cell_area_m2(range_m, hpbw, bandwidth_hz),
    )
    return DetectionResult(
        range_m=range_m,
        snr_single_db=snr1,
        snr_integrated_db=snr_int,
        pd=pd,
        pfa=pfa,
        geometry=geom,
    )


# ---------------------------------------------------------------------------
# Tier-D occupancy envelope
# ---------------------------------------------------------------------------

# Per-region pedestrian density [bodies / m^2] for tier-D fallback.
# Sources:
#   - Brussels Grand Place peak: ~0.25 /m^2 (1 person per 4 m^2),
#     consistent with Fruin Level-of-Service "C-D" range. See
#     Fruin, J. *Pedestrian Planning and Design* (1971), Fig 3.4-3.5.
#   - Tokyo Shibuya Crossing peak: ~0.5 /m^2 (Fruin LoS E).
#   - Dense crowd / Hajj-class: clamped to 1.0 /m^2 (Fruin LoS F floor).
#   - Suburban plaza / quiet hours: ~0.05 /m^2.
_DENSITY_PRESETS_M2: dict[str, float] = {
    "quiet": 0.05,
    "brussels_grand_place_peak": 0.25,
    "shibuya_peak": 0.5,
    "dense_crowd": 1.0,
}


def occupancy_envelope_density(
    region: Literal["quiet", "brussels_grand_place_peak", "shibuya_peak", "dense_crowd"] | float,
) -> float:
    """Resolve a tier-D occupancy density [bodies / m^2].

    Pass a string preset (Fruin LoS-anchored) or a float density. When
    no detection telemetry is available for a region (sensing blind spot),
    the precoder budgets exposure assuming this density of worst-case
    Cauchy bodies uniformly across that region.

    ICNIRP and ITU-T K.122 do not specify a numerical density for
    sensorless audit; this preset table is a conservative proposal,
    not a regulatory citation.
    """
    if isinstance(region, (int, float)):
        d = float(region)
        if d < 0:
            raise ValueError("density must be non-negative")
        return d
    if region not in _DENSITY_PRESETS_M2:
        raise ValueError(f"unknown region preset {region!r}; choose from {sorted(_DENSITY_PRESETS_M2)}")
    return _DENSITY_PRESETS_M2[region]
