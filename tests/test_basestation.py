"""Edge case tests for the basestation module.

Covers: coords, orientation, power, pattern, antenna, adapter.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aegis.basestation.adapter import _safe_float, _sanitize_label, paths_from_basestation
from aegis.basestation.antenna import AntennaPattern, BaseStation
from aegis.basestation.coords import enu_to_wgs84, wgs84_to_enu
from aegis.basestation.orientation import (
    antenna_rotation_matrix,
    departure_to_antenna_local,
)
from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
from aegis.basestation.power import dbm_to_w, eirp_to_tx_power_dbm, eirp_to_tx_power_w, w_to_dbm

# ---------------------------------------------------------------------------
# coords
# ---------------------------------------------------------------------------


class TestWgs84ToEnu:
    """WGS84 <-> ENU coordinate transforms."""

    def test_same_point_as_origin_gives_zero(self):
        lat, lon, alt = 51.05, 3.72, 0.0
        enu = wgs84_to_enu(lat, lon, alt, lat, lon, alt)
        np.testing.assert_allclose(enu, [0.0, 0.0, 0.0], atol=1e-10)

    def test_roundtrip_identity(self):
        lat0, lon0, alt0 = 51.05, 3.72, 0.0
        lat, lon, alt = 51.06, 3.73, 25.0
        enu = wgs84_to_enu(lat, lon, alt, lat0, lon0, alt0)
        lat_r, lon_r, alt_r = enu_to_wgs84(float(enu[0]), float(enu[1]), float(enu[2]), lat0, lon0, alt0)
        assert lat_r == pytest.approx(lat, abs=1e-9)
        assert lon_r == pytest.approx(lon, abs=1e-9)
        assert alt_r == pytest.approx(alt, abs=1e-9)

    def test_altitude_passthrough(self):
        lat0, lon0 = 0.0, 0.0
        alt_antenna = 30.0
        alt_ground = 5.0
        enu = wgs84_to_enu(lat0, lon0, alt_antenna, lat0, lon0, alt_ground)
        assert enu[2] == pytest.approx(alt_antenna - alt_ground)

    def test_one_degree_latitude_approx_111km(self):
        lat0, lon0 = 0.0, 0.0
        enu = wgs84_to_enu(1.0, 0.0, 0.0, lat0, lon0)
        north_m = enu[1]
        # 1 degree latitude ~ 111 km (using R_earth = 6371 km: 2*pi*6371000/360 = 111195)
        assert north_m == pytest.approx(111_195, rel=0.01)
        # East component should be zero for pure latitude change
        assert enu[0] == pytest.approx(0.0, abs=1e-6)

    def test_east_component_at_equator(self):
        enu = wgs84_to_enu(0.0, 1.0, 0.0, 0.0, 0.0)
        # At equator, cos(0)=1, so 1 degree of longitude = 1 degree of latitude
        assert enu[0] == pytest.approx(enu[1] if enu[1] != 0 else 111_195, rel=0.01)
        # Specifically, east for 1 deg lon at equator should equal north for 1 deg lat
        enu_lat = wgs84_to_enu(1.0, 0.0, 0.0, 0.0, 0.0)
        assert enu[0] == pytest.approx(enu_lat[1], rel=1e-10)

    def test_roundtrip_at_high_latitude(self):
        lat0, lon0, alt0 = 70.0, 25.0, 0.0
        lat, lon, alt = 70.001, 25.002, 50.0
        enu = wgs84_to_enu(lat, lon, alt, lat0, lon0, alt0)
        lat_r, lon_r, alt_r = enu_to_wgs84(float(enu[0]), float(enu[1]), float(enu[2]), lat0, lon0, alt0)
        assert lat_r == pytest.approx(lat, abs=1e-9)
        assert lon_r == pytest.approx(lon, abs=1e-9)
        assert alt_r == pytest.approx(alt, abs=1e-9)


# ---------------------------------------------------------------------------
# orientation
# ---------------------------------------------------------------------------


class TestAntennaRotationMatrix:
    """Rotation matrix properties and known orientations."""

    def test_orthogonality(self):
        for az in [0, 45, 90, 180, 270]:
            for tilt in [0, 5, 10, 45, 90]:
                R = antenna_rotation_matrix(az, tilt)
                np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
                np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-12)

    def test_det_is_one(self):
        for az in [0, 90, 180, 270]:
            for tilt in [0, 10, 45]:
                R = antenna_rotation_matrix(az, tilt)
                assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-12)


class TestDepartureToAntennaLocal:
    """departure_to_antenna_local edge cases."""

    def test_boresight_at_zero_az_zero_tilt(self):
        # Azimuth=0 means North, tilt=0 means horizontal.
        # Boresight direction in ENU is +Y (North).
        boresight = np.array([[0.0, 1.0, 0.0]])
        elev, azim = departure_to_antenna_local(boresight, 0.0, 0.0)
        assert elev[0] == pytest.approx(0.0, abs=1e-10)
        assert azim[0] == pytest.approx(0.0, abs=1e-10)

    def test_boresight_at_90_az_zero_tilt(self):
        # Azimuth=90 means East (+X in ENU).
        boresight = np.array([[1.0, 0.0, 0.0]])
        elev, azim = departure_to_antenna_local(boresight, 90.0, 0.0)
        assert elev[0] == pytest.approx(0.0, abs=1e-10)
        assert azim[0] == pytest.approx(0.0, abs=1e-10)

    def test_known_tilt(self):
        # Azimuth=0 (North), tilt=10 deg. Boresight in world frame:
        # points North and 10 degrees below horizontal.
        tilt = 10.0
        boresight_world = np.array([[0.0, math.cos(math.radians(tilt)), -math.sin(math.radians(tilt))]])
        elev, azim = departure_to_antenna_local(boresight_world, 0.0, tilt)
        # Should map to boresight in local frame -> elev=0, azim=0
        assert elev[0] == pytest.approx(0.0, abs=1e-8)
        assert azim[0] == pytest.approx(0.0, abs=1e-8)

    def test_opposite_direction_gives_180_azimuth(self):
        # Opposite to boresight at az=0, tilt=0 -> direction is -Y (South)
        opposite = np.array([[0.0, -1.0, 0.0]])
        elev, azim = departure_to_antenna_local(opposite, 0.0, 0.0)
        assert elev[0] == pytest.approx(0.0, abs=1e-10)
        assert abs(azim[0]) == pytest.approx(180.0, abs=1e-10)

    def test_batch_directions(self):
        dirs = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        elev, azim = departure_to_antenna_local(dirs, 0.0, 0.0)
        assert elev.shape == (3,)
        assert azim.shape == (3,)


# ---------------------------------------------------------------------------
# power
# ---------------------------------------------------------------------------


class TestPowerConversions:
    """Power unit conversions and EIRP edge cases."""

    def test_30_dbm_is_1w(self):
        assert dbm_to_w(30.0) == pytest.approx(1.0, rel=1e-12)

    def test_0_dbm_is_1mw(self):
        assert dbm_to_w(0.0) == pytest.approx(1e-3, rel=1e-12)

    def test_dbm_w_roundtrip(self):
        for val in [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]:
            assert w_to_dbm(dbm_to_w(w_to_dbm(val))) == pytest.approx(w_to_dbm(val), rel=1e-10)

    def test_w_to_dbm_roundtrip(self):
        for dbm_val in [-30.0, 0.0, 10.0, 30.0, 50.0]:
            assert dbm_to_w(w_to_dbm(dbm_to_w(dbm_val))) == pytest.approx(dbm_to_w(dbm_val), rel=1e-10)

    def test_w_to_dbm_zero_returns_neg_inf(self):
        # np.log10(0) = -inf, so w_to_dbm(0) = -inf + 30 = -inf.
        # This is mathematically correct: 0 W is -inf dBm.
        result = w_to_dbm(0.0)
        assert result == float("-inf")

    def test_w_to_dbm_negative_returns_nan(self):
        # Negative watts is physically meaningless. np.log10(-1) = nan.
        result = w_to_dbm(-1.0)
        assert np.isnan(result)

    def test_eirp_with_zero_gain_returns_eirp(self):
        # Zero gain_dbi is treated as isotropic, returns EIRP unchanged.
        assert eirp_to_tx_power_dbm(50.0, 0.0) == 50.0

    def test_eirp_with_nan_gain_returns_eirp(self):
        assert eirp_to_tx_power_dbm(50.0, float("nan")) == 50.0

    def test_eirp_with_real_gain(self):
        # EIRP=50 dBm, gain=17 dBi -> tx_power = 50-17 = 33 dBm
        assert eirp_to_tx_power_dbm(50.0, 17.0) == pytest.approx(33.0)

    def test_eirp_to_tx_power_w(self):
        # 33 dBm = 10^((33-30)/10) = 10^0.3 ~ 1.9953 W
        assert eirp_to_tx_power_w(50.0, 17.0) == pytest.approx(10.0**0.3, rel=1e-10)


# ---------------------------------------------------------------------------
# pattern
# ---------------------------------------------------------------------------


class TestSyntheticPattern:
    """Synthetic antenna pattern generation."""

    def test_output_shape(self):
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        assert pat.gain_dbi.shape == (181, 360)

    def test_peak_gain_at_boresight(self):
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        assert pat.max_gain_dbi == pytest.approx(17.0)
        # Boresight is elev=0 (index 90), azim=0 (index 180)
        boresight_gain = pat.gain_dbi[90, 180]
        assert boresight_gain == pytest.approx(17.0, abs=0.01)

    def test_nan_beamwidth_defaults(self):
        pat = synthetic_pattern_from_beamwidth(float("nan"), float("nan"), float("nan"))
        assert pat.gain_dbi.shape == (181, 360)
        assert pat.max_gain_dbi == pytest.approx(17.0)

    def test_negative_beamwidth_uses_default(self):
        pat = synthetic_pattern_from_beamwidth(-5.0, -10.0, 17.0)
        assert pat.gain_dbi.shape == (181, 360)
        # Should use the defaults (65, 10), so peak at boresight should be 17
        assert pat.gain_dbi[90, 180] == pytest.approx(17.0, abs=0.01)

    def test_minus_3db_at_half_power_angle_horizontal(self):
        hpbw_h = 65.0
        hpbw_v = 10.0
        gain = 17.0
        pat = synthetic_pattern_from_beamwidth(hpbw_h, hpbw_v, gain)

        # At half-power angle (hpbw/2), gain should be ~3 dB below peak.
        # Azimuth index: half_angle = 32.5 deg -> index = 180 + 32.5 = 212.5
        # Test at the nearest whole-degree index: azim = 32 deg -> idx 212
        # (the ITU-R formula gives -3dB at exactly hpbw/2)
        boresight = pat.gain_dbi[90, 180]
        at_half = pat.gain_dbi[90, 212]  # elev=0, azim=+32 deg
        at_half_plus = pat.gain_dbi[90, 213]  # elev=0, azim=+33 deg
        # The -3dB point at hpbw/2 = 32.5 should be between index 212 and 213
        drop_lo = boresight - at_half
        drop_hi = boresight - at_half_plus
        assert drop_lo < 3.0 < drop_hi, (
            f"Expected -3dB crossing between 32 and 33 degrees, got drops {drop_lo:.2f} and {drop_hi:.2f}"
        )

    def test_minus_3db_at_half_power_angle_vertical(self):
        hpbw_h = 65.0
        hpbw_v = 10.0
        gain = 17.0
        pat = synthetic_pattern_from_beamwidth(hpbw_h, hpbw_v, gain)

        # Vertical half-power angle = 5 deg. elev index: 90 + 5 = 95
        boresight = pat.gain_dbi[90, 180]
        at_half = pat.gain_dbi[95, 180]
        # k * (5/10)^2 = 4*ln(2)*0.25 = ln(2) -> 10*log10(exp(-ln2)) = 10*(-ln2/ln10) = -3.01 dB
        drop = boresight - at_half
        assert drop == pytest.approx(3.01, abs=0.05)


# ---------------------------------------------------------------------------
# antenna
# ---------------------------------------------------------------------------


class TestAntennaPattern:
    """AntennaPattern validation and evaluation."""

    def test_rejects_wrong_shape(self):
        with pytest.raises(ValueError, match="must be \\(181, 360\\)"):
            AntennaPattern(gain_dbi=np.zeros((100, 360), dtype=np.float32), max_gain_dbi=0.0)

    def test_rejects_wrong_shape_cols(self):
        with pytest.raises(ValueError, match="must be \\(181, 360\\)"):
            AntennaPattern(gain_dbi=np.zeros((181, 100), dtype=np.float32), max_gain_dbi=0.0)

    def test_rejects_1d(self):
        with pytest.raises(ValueError):
            AntennaPattern(gain_dbi=np.zeros(181 * 360, dtype=np.float32), max_gain_dbi=0.0)

    def test_evaluate_at_boresight_gives_max_gain(self):
        gain = 17.0
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, gain)
        result = pat.evaluate(np.array([0.0]), np.array([0.0]))
        expected_linear = 10.0 ** (gain / 10.0)
        assert result[0] == pytest.approx(expected_linear, rel=0.01)

    def test_evaluate_returns_nonnegative(self):
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        elev = np.linspace(-90, 90, 100)
        azim = np.linspace(-180, 179, 100)
        result = pat.evaluate(elev, azim)
        assert np.all(result >= 0.0)

    def test_gain_linear_replaces_nan(self):
        g = np.full((181, 360), float("nan"), dtype=np.float32)
        g[90, 180] = 10.0  # one valid point
        pat = AntennaPattern(gain_dbi=g, max_gain_dbi=10.0)
        g_lin = pat.gain_linear
        # NaN entries should map to effectively zero (10^(-200/10) ~ 0)
        assert g_lin[90, 180] == pytest.approx(10.0, rel=0.01)
        assert g_lin[0, 0] == pytest.approx(0.0, abs=1e-15)


class TestBaseStation:
    """BaseStation property computation."""

    @pytest.fixture()
    def bs(self):
        return BaseStation(
            site_code="TEST001",
            antenna_label="test",
            operator="TestOp",
            technology="5G NR",
            latitude=51.05,
            longitude=3.72,
            height_m=30.0,
            eirp_dbm=50.0,
            gain_dbi=17.0,
            freq_mhz=3500.0,
            azimuth_deg=120.0,
            electrical_tilt_deg=6.0,
            mechanical_tilt_deg=2.0,
            horizontal_beamwidth_deg=65.0,
            vertical_beamwidth_deg=10.0,
        )

    def test_total_tilt(self, bs):
        assert bs.total_tilt_deg == pytest.approx(8.0)

    def test_freq_hz(self, bs):
        assert bs.freq_hz == pytest.approx(3.5e9)

    def test_pattern_default_none(self, bs):
        assert bs.pattern is None

    def test_frozen(self, bs):
        with pytest.raises(AttributeError):
            bs.height_m = 50.0  # type: ignore[misc]

    def test_frequency_band_field(self):
        bs = BaseStation(
            site_code="TEST001", antenna_label="test", operator="TestOp",
            technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
            eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
            electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
            horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
            frequency_band="Band3600MHz",
        )
        assert bs.frequency_band == "Band3600MHz"

    def test_provenance_field(self):
        from aegis.basestation.provenance import FieldSource

        prov = (("eirp_dbm", FieldSource("gov:brussels", 1.0)),)
        bs = BaseStation(
            site_code="TEST001", antenna_label="test", operator="TestOp",
            technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
            eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
            electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
            horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
            provenance=prov,
        )
        assert bs.provenance_dict["eirp_dbm"].confidence == 1.0

    def test_pattern_source_field(self):
        bs = BaseStation(
            site_code="TEST001", antenna_label="test", operator="TestOp",
            technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
            eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
            electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
            horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
            pattern_source="synthetic:gaussian",
        )
        assert bs.pattern_source == "synthetic:gaussian"

    def test_defaults_for_new_fields(self, bs):
        assert bs.frequency_band == ""
        assert bs.provenance == ()
        assert bs.pattern_source == ""


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


class TestSanitizeLabel:
    """_sanitize_label replaces special characters with underscores."""

    def test_spaces_and_parens(self):
        assert _sanitize_label("Kathrein (840)") == "Kathrein__840_"

    def test_dots_and_slashes(self):
        assert _sanitize_label("ant.v2/rev-3") == "ant_v2_rev_3"

    def test_ampersand(self):
        assert _sanitize_label("A&B") == "A_B"

    def test_backslash(self):
        assert _sanitize_label("path\\to") == "path_to"

    def test_no_special_chars(self):
        assert _sanitize_label("clean_label") == "clean_label"

    def test_empty_string(self):
        assert _sanitize_label("") == ""


class TestSafeFloat:
    """_safe_float handles NaN, None, and invalid input."""

    def test_valid_float(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_valid_int(self):
        assert _safe_float(42) == pytest.approx(42.0)

    def test_valid_string(self):
        assert _safe_float("2.5") == pytest.approx(2.5)

    def test_nan_returns_default(self):
        assert _safe_float(float("nan")) == 0.0

    def test_nan_with_custom_default(self):
        assert _safe_float(float("nan"), default=10.0) == 10.0

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_invalid_string_returns_default(self):
        assert _safe_float("not_a_number", default=5.0) == 5.0

    def test_empty_string_returns_default(self):
        assert _safe_float("", default=1.0) == 1.0


class TestPathsFromBasestation:
    """paths_from_basestation returns valid PropagationPaths."""

    @pytest.fixture()
    def bs(self):
        return BaseStation(
            site_code="TEST001",
            antenna_label="test",
            operator="TestOp",
            technology="5G NR",
            latitude=51.050,
            longitude=3.720,
            height_m=30.0,
            eirp_dbm=50.0,
            gain_dbi=17.0,
            freq_mhz=3500.0,
            azimuth_deg=0.0,
            electrical_tilt_deg=5.0,
            mechanical_tilt_deg=0.0,
            horizontal_beamwidth_deg=65.0,
            vertical_beamwidth_deg=10.0,
        )

    def test_returns_single_path(self, bs):
        body = np.array([0.0, 50.0, 1.5])
        origin = (51.050, 3.720)
        paths = paths_from_basestation(bs, body, origin)
        assert paths.n_paths == 1

    def test_power_is_positive(self, bs):
        body = np.array([0.0, 50.0, 1.5])
        origin = (51.050, 3.720)
        paths = paths_from_basestation(bs, body, origin)
        assert paths.power[0] > 0.0

    def test_k_hat_is_unit_vector(self, bs):
        body = np.array([100.0, 200.0, 1.5])
        origin = (51.050, 3.720)
        paths = paths_from_basestation(bs, body, origin)
        norm = np.linalg.norm(paths.k_hat[0])
        assert norm == pytest.approx(1.0, abs=1e-10)

    def test_with_pattern(self):
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        bs = BaseStation(
            site_code="PAT001",
            antenna_label="patterned",
            operator="TestOp",
            technology="5G NR",
            latitude=51.050,
            longitude=3.720,
            height_m=30.0,
            eirp_dbm=50.0,
            gain_dbi=17.0,
            freq_mhz=3500.0,
            azimuth_deg=0.0,
            electrical_tilt_deg=5.0,
            mechanical_tilt_deg=0.0,
            horizontal_beamwidth_deg=65.0,
            vertical_beamwidth_deg=10.0,
            pattern=pat,
        )
        body = np.array([0.0, 50.0, 1.5])
        origin = (51.050, 3.720)
        paths = paths_from_basestation(bs, body, origin)
        assert paths.n_paths == 1
        assert paths.power[0] > 0.0

    def test_on_boresight_power_exceeds_back_lobe(self):
        """Body on boresight should get main-lobe gain, not back-lobe gain.

        Regression test: departure_dir sign was inverted, causing the
        antenna pattern to be evaluated 180 degrees off, yielding back-lobe
        gain instead of the main-lobe peak.
        """
        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        # Antenna at origin, boresight north (azimuth=0), no tilt
        bs_north = BaseStation(
            site_code="DIR001",
            antenna_label="directed",
            operator="TestOp",
            technology="5G NR",
            latitude=51.050,
            longitude=3.720,
            height_m=10.0,
            eirp_dbm=50.0,
            gain_dbi=17.0,
            freq_mhz=3500.0,
            azimuth_deg=0.0,
            electrical_tilt_deg=0.0,
            mechanical_tilt_deg=0.0,
            horizontal_beamwidth_deg=65.0,
            vertical_beamwidth_deg=10.0,
            pattern=pat,
        )
        origin = (51.050, 3.720)
        # Body directly north (on boresight), same height as antenna
        body_north = np.array([0.0, 50.0, 10.0])
        # Body directly south (behind antenna)
        body_south = np.array([0.0, -50.0, 10.0])

        paths_north = paths_from_basestation(bs_north, body_north, origin)
        paths_south = paths_from_basestation(bs_north, body_south, origin)

        # On boresight power must exceed back-lobe power by at least 10 dB
        ratio_db = 10 * np.log10(paths_north.power[0] / paths_south.power[0])
        assert ratio_db > 10.0, f"On-boresight power should be >10 dB above back-lobe, got {ratio_db:.1f} dB"

    def test_body_at_antenna_position_clamps_distance(self, bs):
        # When body is at antenna position, distance gets clamped to 0.1 m.
        ant_enu = wgs84_to_enu(bs.latitude, bs.longitude, 0.0, 51.050, 3.720)
        body = np.array([ant_enu[0], ant_enu[1], bs.height_m])
        origin = (51.050, 3.720)
        paths = paths_from_basestation(bs, body, origin)
        # Should not crash, power should be finite
        assert paths.n_paths == 1
        assert np.isfinite(paths.power[0])
