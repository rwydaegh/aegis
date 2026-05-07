"""Tests for the monostatic radar link-budget and detection model.

The module is small and the values are textbook, so the tests are too:
- Range / azimuth resolution match the standard formulas.
- Albersheim Pd reproduces Skolnik's table values within 0.5 dB.
- The radar equation matches a hand computation at the paper's
  operating point (26 GHz, 8x8 panel, 30 dBm, 50 m, 1 m^2 target).
"""

from __future__ import annotations

import math

import pytest

from aegis.sensing import (
    angular_resolution_deg,
    crossrange_resolution_m,
    detection_probability,
    monostatic_snr_db,
    occupancy_envelope_density,
    range_resolution_m,
    tier_c_cell_area_m2,
)
from aegis.sensing.rcs import detection

# ---------------------------------------------------------------------------
# Resolutions
# ---------------------------------------------------------------------------


def test_range_resolution_textbook():
    # 400 MHz -> 0.375 m exactly (c / 2B)
    assert range_resolution_m(400e6) == pytest.approx(0.3747, rel=1e-3)
    # 30 MHz SSB -> 5 m
    assert range_resolution_m(30e6) == pytest.approx(4.997, rel=1e-3)


def test_angular_hpbw_8_elements():
    # 8x8 half-wavelength panel: HPBW = 0.886 * 2 / 8 rad = 0.2215 rad = 12.69 deg
    hpbw = angular_resolution_deg(num_elements_per_side=8, freq_hz=26e9)
    assert hpbw == pytest.approx(12.69, abs=0.05)


def test_hpbw_independent_of_frequency_at_lambda_over_two():
    # Half-wavelength spacing makes HPBW (in radians) only a function of N.
    a = angular_resolution_deg(8, 3.5e9)
    b = angular_resolution_deg(8, 26e9)
    assert a == pytest.approx(b, rel=1e-12)


def test_crossrange_grows_linearly_with_range():
    hpbw = angular_resolution_deg(8, 26e9)
    cr_25 = crossrange_resolution_m(25.0, hpbw)
    cr_50 = crossrange_resolution_m(50.0, hpbw)
    assert cr_50 == pytest.approx(2.0 * cr_25, rel=1e-12)
    # at 50 m, 8x8 at 26 GHz: 50 * 0.2215 rad = 11.07 m
    assert cr_50 == pytest.approx(11.07, abs=0.05)


def test_cell_area_at_50m():
    hpbw = angular_resolution_deg(8, 26e9)
    area = tier_c_cell_area_m2(range_m=50.0, hpbw_deg=hpbw, bandwidth_hz=400e6)
    # 11.07 m crossrange * 0.375 m range = ~4.15 m^2
    assert area == pytest.approx(11.07 * 0.3747, rel=1e-3)


def test_resolution_validators():
    with pytest.raises(ValueError, match="bandwidth"):
        range_resolution_m(0)
    with pytest.raises(ValueError, match="hpbw"):
        crossrange_resolution_m(50.0, 0)
    with pytest.raises(ValueError, match="range"):
        crossrange_resolution_m(-1.0, 5.0)
    with pytest.raises(ValueError, match="num_elements"):
        angular_resolution_deg(0, 26e9)
    with pytest.raises(ValueError, match="freq"):
        angular_resolution_deg(8, 0)


# ---------------------------------------------------------------------------
# Radar equation
# ---------------------------------------------------------------------------


def _hand_radar_pr_dbm(*, P_t_dbm, G_t, G_r, lam, sigma_dbsm, R):
    return P_t_dbm + G_t + G_r + 20 * math.log10(lam) + sigma_dbsm - 30 * math.log10(4 * math.pi) - 40 * math.log10(R)


def test_monostatic_snr_matches_hand_calc_50m():
    # Paper §VII operating point: 30 dBm, 8x8 (~21 dBi), 26 GHz, 1 m^2, 50 m,
    # 400 MHz, 6 dB NF, no CPI gain (compare single-snapshot only).
    snr1, snr_int = monostatic_snr_db(
        range_m=50.0,
        eirp_dbm=30.0 + 21.0,  # EIRP = Pt + Gt
        rx_gain_dbi=21.0,
        freq_hz=26e9,
        bandwidth_hz=400e6,
        rcs_dbsm=0.0,
        noise_figure_db=6.0,
        integration_gain_db=0.0,
    )
    lam = 3e8 / 26e9
    pr = _hand_radar_pr_dbm(P_t_dbm=30.0, G_t=21.0, G_r=21.0, lam=lam, sigma_dbsm=0.0, R=50.0)
    noise = -174.0 + 10 * math.log10(400e6) + 6.0
    expected = pr - noise
    assert snr1 == pytest.approx(expected, abs=0.1)
    # No CPI: integrated SNR equals single-snapshot.
    assert snr_int == pytest.approx(snr1, abs=1e-10)


def test_monostatic_snr_drops_40db_per_decade_in_range():
    # Two-way 1/R^4 -> 40 dB / decade, all else equal.
    snr_a, _ = monostatic_snr_db(
        range_m=10.0,
        eirp_dbm=51.0,
        rx_gain_dbi=21.0,
        freq_hz=26e9,
        bandwidth_hz=400e6,
    )
    snr_b, _ = monostatic_snr_db(
        range_m=100.0,
        eirp_dbm=51.0,
        rx_gain_dbi=21.0,
        freq_hz=26e9,
        bandwidth_hz=400e6,
    )
    assert snr_a - snr_b == pytest.approx(40.0, abs=0.2)


def test_integration_gain_adds_in_db():
    snr1, snr_int = monostatic_snr_db(
        range_m=50.0,
        eirp_dbm=51.0,
        rx_gain_dbi=21.0,
        freq_hz=26e9,
        bandwidth_hz=400e6,
        integration_gain_db=15.0,
    )
    assert snr_int - snr1 == pytest.approx(15.0, abs=1e-12)


def test_snr_validators():
    with pytest.raises(ValueError, match="range"):
        monostatic_snr_db(
            range_m=0,
            eirp_dbm=51,
            rx_gain_dbi=21,
            freq_hz=26e9,
            bandwidth_hz=400e6,
        )
    with pytest.raises(ValueError, match="freq"):
        monostatic_snr_db(
            range_m=50,
            eirp_dbm=51,
            rx_gain_dbi=21,
            freq_hz=0,
            bandwidth_hz=400e6,
        )
    with pytest.raises(ValueError, match="bandwidth"):
        monostatic_snr_db(
            range_m=50,
            eirp_dbm=51,
            rx_gain_dbi=21,
            freq_hz=26e9,
            bandwidth_hz=0,
        )


# ---------------------------------------------------------------------------
# Detection probability (Albersheim)
# ---------------------------------------------------------------------------


def test_pd_matches_skolnik_table_pfa_1e6():
    # Skolnik 3rd ed., Fig 2.7 / Table 2.1 (Swerling-0, single pulse, Pfa=1e-6):
    # Pd = 0.50 needs ~11.2 dB; Pd = 0.90 needs ~13.2 dB.
    pd_at_11_2 = detection_probability(11.2, pfa=1e-6)
    pd_at_13_2 = detection_probability(13.2, pfa=1e-6)
    assert pd_at_11_2 == pytest.approx(0.50, abs=0.05)
    assert pd_at_13_2 == pytest.approx(0.90, abs=0.03)


def test_pd_monotone_in_snr():
    pds = [detection_probability(s, pfa=1e-6) for s in range(0, 20)]
    assert all(b >= a for a, b in zip(pds[:-1], pds[1:], strict=True))


def test_pd_saturates_at_unity():
    # Plaza-range CPI integrated SNR is ~40 dB; Pd should round-trip to 1.0.
    assert detection_probability(40.0, pfa=1e-6) == 1.0
    # Albersheim is calibrated for Pd in [0.1, 0.9]; outside that the
    # asymptote isn't 0 but it has to be small at deeply negative SNR.
    assert detection_probability(-20.0, pfa=1e-6) < 0.05


def test_pd_validates_pfa():
    with pytest.raises(ValueError, match="pfa"):
        detection_probability(10.0, pfa=0.0)
    with pytest.raises(ValueError, match="pfa"):
        detection_probability(10.0, pfa=1.0)
    with pytest.raises(ValueError, match="pfa"):
        detection_probability(10.0, pfa=2.0)


# ---------------------------------------------------------------------------
# Bundled detection result
# ---------------------------------------------------------------------------


def test_bundled_detection_at_paper_operating_point():
    r = detection(
        range_m=50.0,
        eirp_dbm=51.0,  # 30 dBm Tx + 21 dBi Tx gain
        rx_gain_dbi=21.0,
        freq_hz=26e9,
        bandwidth_hz=400e6,
        rcs_dbsm=0.0,
        noise_figure_db=6.0,
        integration_gain_db=27.8,  # 10 ms CPI at 60 kHz SCS = 600 symbols
        pfa=1e-6,
        num_elements_per_side=8,
    )
    # Single-snapshot SNR at 50 m, 0 dBsm, 51 dBm EIRP, 21 dBi rx, 400 MHz, 6 dB NF
    # ~= 14 dB; integrated 14 + 27.8 = 41.8 dB; Pd = 1.0.
    assert r.snr_single_db == pytest.approx(14.3, abs=0.5)
    assert r.snr_integrated_db == pytest.approx(42.1, abs=0.5)
    assert r.pd == 1.0
    # Geometry: HPBW 12.69, crossrange 11.07 m at 50 m, range 0.375 m.
    assert r.geometry.azimuth_hpbw_deg == pytest.approx(12.69, abs=0.05)
    assert r.geometry.crossrange_resolution_m == pytest.approx(11.07, abs=0.05)
    assert r.geometry.range_resolution_m == pytest.approx(0.3747, rel=1e-3)


# ---------------------------------------------------------------------------
# Occupancy envelope
# ---------------------------------------------------------------------------


def test_density_presets_ordered():
    quiet = occupancy_envelope_density("quiet")
    bxl = occupancy_envelope_density("brussels_grand_place_peak")
    shibuya = occupancy_envelope_density("shibuya_peak")
    dense = occupancy_envelope_density("dense_crowd")
    assert quiet < bxl < shibuya < dense
    assert bxl == pytest.approx(0.25)


def test_density_accepts_float_override():
    assert occupancy_envelope_density(0.42) == 0.42
    assert occupancy_envelope_density(0.0) == 0.0


def test_density_rejects_negative():
    with pytest.raises(ValueError, match="non-negative"):
        occupancy_envelope_density(-0.1)


def test_density_rejects_unknown_preset():
    with pytest.raises(ValueError, match="unknown region preset"):
        occupancy_envelope_density("hong_kong_mtr")  # type: ignore[arg-type]
