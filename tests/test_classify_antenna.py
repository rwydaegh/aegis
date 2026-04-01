"""Tests for base station archetype classification."""

from unittest.mock import MagicMock, patch

import pytest

from aegis.basestation.classify import classify_antenna, infer_element_grid


class TestClassifyAntenna:
    """Archetype assignment from antenna metadata."""

    def test_mmimo_high_gain_5g(self):
        result = classify_antenna(
            gain_dbi=24.8,
            technology="5G",
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result == "mmimo"

    def test_mmimo_mixed_4g5g(self):
        result = classify_antenna(
            gain_dbi=22.0,
            technology="4G/5G",
            freq_mhz=3750.0,
            h_bw=100,
            v_bw=20,
        )
        assert result == "mmimo"

    def test_sector_typical_4g(self):
        result = classify_antenna(
            gain_dbi=16.8,
            technology="4G",
            freq_mhz=1800.0,
            h_bw=65,
            v_bw=10,
        )
        assert result == "sector"

    def test_sector_high_gain_non_5g(self):
        """High gain but not 5G should NOT be mmimo."""
        result = classify_antenna(
            gain_dbi=22.0,
            technology="4G",
            freq_mhz=2600.0,
            h_bw=65,
            v_bw=7,
        )
        assert result == "sector"

    def test_small_cell_low_gain(self):
        result = classify_antenna(
            gain_dbi=2.1,
            technology="2G",
            freq_mhz=800.0,
            h_bw=168,
            v_bw=100,
        )
        assert result == "small_cell"

    def test_null_technology_not_mmimo(self):
        """Unknown tech should never classify as mmimo."""
        result = classify_antenna(
            gain_dbi=24.0,
            technology=None,
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result != "mmimo"

    def test_empty_technology_not_mmimo(self):
        result = classify_antenna(
            gain_dbi=24.0,
            technology="",
            freq_mhz=3750.0,
            h_bw=126,
            v_bw=34,
        )
        assert result != "mmimo"


class TestInferElementGrid:
    """Element count inference and grid snapping."""

    def test_mmimo_snaps_to_standard_grid(self):
        n_h, n_v = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (64, 128)
        assert n_v >= n_h  # tall panels

    def test_sector_dual_column(self):
        n_h, n_v = infer_element_grid(
            archetype="sector",
            gain_dbi=16.0,
            element_gain_dbi=5.0,
        )
        assert n_h in (1, 2)
        assert n_v >= 2

    def test_small_cell_minimal(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell",
            gain_dbi=2.1,
            element_gain_dbi=5.0,
        )
        assert n_h == 1
        assert n_v == 1

    def test_small_cell_moderate_gain(self):
        n_h, n_v = infer_element_grid(
            archetype="small_cell",
            gain_dbi=8.0,
            element_gain_dbi=5.0,
        )
        assert n_h * n_v in (1, 4)

    def test_custom_element_gain(self):
        n_h_5, n_v_5 = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=5.0,
        )
        n_h_7, n_v_7 = infer_element_grid(
            archetype="mmimo",
            gain_dbi=24.8,
            element_gain_dbi=7.0,
        )
        # Higher element gain means fewer inferred elements
        assert n_h_7 * n_v_7 <= n_h_5 * n_v_5


def test_classify_returns_exposure_config():
    from aegis.basestation.classify import classify_basestation

    result = classify_basestation(gain_dbi=24.8, technology="5G", freq_mhz=3500)
    assert "exposure_config" in result
    exp = result["exposure_config"]
    assert exp.duplex_mode == "tdd"
    assert exp.tdd_dl_ratio == 0.75
    assert exp.power_reduction_factor == 0.32


def test_classify_sector_fdd():
    from aegis.basestation.classify import classify_basestation

    result = classify_basestation(gain_dbi=15.0, technology="4G", freq_mhz=1800)
    exp = result["exposure_config"]
    assert exp.duplex_mode == "fdd"
    assert exp.tdd_dl_ratio == 1.0
    assert exp.power_reduction_factor == 1.0  # sector default


def test_classify_5g_sector_tdd():
    """5G sector at 3.5 GHz gets TDD ratio but no PRF reduction."""
    from aegis.basestation.classify import classify_basestation

    result = classify_basestation(gain_dbi=15.0, technology="5G", freq_mhz=3500)
    assert result["archetype"] == "sector"
    exp = result["exposure_config"]
    assert exp.duplex_mode == "tdd"
    assert exp.tdd_dl_ratio == 0.75
    assert exp.power_reduction_factor == 1.0  # sector, not mMIMO


def test_classify_returns_beam_config_for_mmimo():
    from aegis.basestation.classify import classify_basestation

    result = classify_basestation(gain_dbi=24.8, technology="5G", freq_mhz=3500)
    assert "beam_config" in result
    bc = result["beam_config"]
    assert bc.broadcast_gain_dbi == 18.0
    assert bc.traffic_hbw_deg == 12.0


def test_classify_no_beam_config_for_sector():
    from aegis.basestation.classify import classify_basestation

    result = classify_basestation(gain_dbi=15.0, technology="4G", freq_mhz=1800)
    assert result["beam_config"] is None


_viewer_deps_missing = False
try:
    import flask as _flask  # noqa: F401
    import geopy as _geopy  # noqa: F401
except ImportError:
    _viewer_deps_missing = True


@pytest.mark.skipif(_viewer_deps_missing, reason="Flask/geopy not installed (viewer extra)")
class TestGeocodeLocation:
    @staticmethod
    def _geocode(location: str):
        from aegis.viewer.routes.basestations import geocode_location

        return geocode_location(location)

    def test_raw_coordinates_comma(self):
        lat, lon, addr = self._geocode("50.85, 4.35")
        assert abs(lat - 50.85) < 0.001
        assert abs(lon - 4.35) < 0.001
        assert addr == {}

    def test_raw_coordinates_space(self):
        lat, lon, addr = self._geocode("50.85 4.35")
        assert abs(lat - 50.85) < 0.001
        assert abs(lon - 4.35) < 0.001
        assert addr == {}

    def test_negative_coordinates(self):
        lat, lon, _addr = self._geocode("-33.87, 151.21")
        assert abs(lat - (-33.87)) < 0.001

    def test_nominatim_fallback(self):
        from aegis.viewer.routes.basestations import geocode_location

        mock_location = MagicMock()
        mock_location.latitude = 50.85
        mock_location.longitude = 4.35
        mock_location.raw = {"address": {"ISO3166-2-lvl4": "BE-BRU"}}
        with patch("geopy.geocoders.Nominatim") as mock_nom:
            mock_nom.return_value.geocode.return_value = mock_location
            lat, lon, addr = geocode_location("Brussels, Belgium")
            assert abs(lat - 50.85) < 0.01
            assert addr.get("ISO3166-2-lvl4") == "BE-BRU"

    def test_unknown_location_raises(self):
        from aegis.viewer.routes.basestations import geocode_location

        with patch("geopy.geocoders.Nominatim") as mock_nom:
            mock_nom.return_value.geocode.return_value = None
            with pytest.raises(ValueError, match="Could not geocode"):
                geocode_location("xyznonexistent12345")
