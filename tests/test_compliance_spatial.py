"""Tests for spatial compliance grid computation."""

import numpy as np

from aegis.compliance import ExposureScenario, spatial_compliance_grid


class TestSpatialComplianceGrid:
    """Verify spatial_compliance_grid() correctness."""

    def _single_station(self, eirp_dbm=53.0, freq_hz=26e9, height_m=25.0):
        """Helper: one station at the origin."""
        return dict(
            station_lats=np.array([51.05]),
            station_lons=np.array([3.72]),
            station_eirp_dbm=np.array([eirp_dbm]),
            station_freq_hz=np.array([freq_hz]),
            station_heights_m=np.array([height_m]),
        )

    def test_output_shape(self):
        grid_lats = np.linspace(51.04, 51.06, 5)
        grid_lons = np.linspace(3.71, 3.73, 5)
        lat2d, lon2d = np.meshgrid(grid_lats, grid_lons, indexing="ij")

        result = spatial_compliance_grid(
            **self._single_station(),
            grid_lats=lat2d.ravel(),
            grid_lons=lon2d.ravel(),
        )
        assert result["sinc"].shape == (25,)
        assert result["margin_db"].shape == (25,)
        assert result["compliant"].shape == (25,)
        assert result["sab_estimate"].shape == (25,)
        assert isinstance(result["T0"], float)
        assert result["T0"] > 0

    def test_inverse_square_falloff(self):
        """S_inc should decay with distance squared."""
        # Two grid points: one close, one far
        grid_lats = np.array([51.05, 51.06])  # ~1.1 km apart
        grid_lons = np.array([3.72, 3.72])

        result = spatial_compliance_grid(
            **self._single_station(),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )
        # The close point should have higher S_inc
        assert result["sinc"][0] > result["sinc"][1]

    def test_zero_stations(self):
        """Empty station list returns zero exposure."""
        grid_lats = np.array([51.05])
        grid_lons = np.array([3.72])

        result = spatial_compliance_grid(
            station_lats=np.array([]),
            station_lons=np.array([]),
            station_eirp_dbm=np.array([]),
            station_freq_hz=np.array([]),
            station_heights_m=np.array([]),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )
        assert result["sinc"][0] == 0.0
        assert result["compliant"][0] is True or result["compliant"][0] == True  # noqa: E712

    def test_compliant_at_large_distance(self):
        """A typical base station should be compliant at 100m+ distance."""
        # 53 dBm EIRP = 200W, at 26 GHz
        grid_lats = np.array([51.051])  # ~111m away
        grid_lons = np.array([3.72])

        result = spatial_compliance_grid(
            **self._single_station(eirp_dbm=53.0),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )
        assert result["compliant"][0]
        assert result["margin_db"][0] > 0

    def test_exceeded_very_close(self):
        """Very high EIRP at close range should exceed limits."""
        # 80 dBm = 100 kW EIRP, extremely high
        grid_lats = np.array([51.05001])  # ~1m away horizontally
        grid_lons = np.array([3.72])

        result = spatial_compliance_grid(
            **self._single_station(eirp_dbm=80.0, height_m=1.5),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
            receiver_height_m=1.5,  # same height as antenna
        )
        assert not result["compliant"][0]
        assert result["margin_db"][0] < 0

    def test_multiple_stations_sum(self):
        """Multiple stations should produce higher S_inc than a single one."""
        grid_lats = np.array([51.051])
        grid_lons = np.array([3.72])

        result_single = spatial_compliance_grid(
            **self._single_station(),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )

        result_double = spatial_compliance_grid(
            station_lats=np.array([51.05, 51.049]),
            station_lons=np.array([3.72, 3.72]),
            station_eirp_dbm=np.array([53.0, 53.0]),
            station_freq_hz=np.array([26e9, 26e9]),
            station_heights_m=np.array([25.0, 25.0]),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )

        assert result_double["sinc"][0] > result_single["sinc"][0]

    def test_occupational_vs_general_public(self):
        """Occupational limits are more permissive (higher margins)."""
        grid_lats = np.array([51.051])
        grid_lons = np.array([3.72])
        kw = self._single_station()

        result_gp = spatial_compliance_grid(
            **kw,
            grid_lats=grid_lats,
            grid_lons=grid_lons,
            scenario=ExposureScenario.GENERAL_PUBLIC,
        )

        result_oc = spatial_compliance_grid(
            **kw,
            grid_lats=grid_lats,
            grid_lons=grid_lons,
            scenario=ExposureScenario.OCCUPATIONAL,
        )

        assert result_oc["margin_db"][0] > result_gp["margin_db"][0]

    def test_custom_T0(self):
        """Custom T0 should scale S_ab but not S_inc."""
        grid_lats = np.array([51.051])
        grid_lons = np.array([3.72])
        kw = self._single_station()

        result_low = spatial_compliance_grid(**kw, grid_lats=grid_lats, grid_lons=grid_lons, T0=0.2)
        result_high = spatial_compliance_grid(**kw, grid_lats=grid_lats, grid_lons=grid_lons, T0=0.8)

        # S_inc should be the same
        np.testing.assert_allclose(result_low["sinc"], result_high["sinc"])
        # S_ab should scale with T0
        np.testing.assert_allclose(result_high["sab_estimate"] / result_low["sab_estimate"], 4.0, rtol=1e-10)

    def test_freq_hz_dominant_eirp_weighted(self):
        """Dominant frequency should be EIRP-weighted average."""
        grid_lats = np.array([51.051])
        grid_lons = np.array([3.72])

        # Two stations: high-power at 26 GHz, low-power at 3.5 GHz
        result = spatial_compliance_grid(
            station_lats=np.array([51.05, 51.05]),
            station_lons=np.array([3.72, 3.72]),
            station_eirp_dbm=np.array([60.0, 30.0]),  # 60 dBm vs 30 dBm
            station_freq_hz=np.array([26e9, 3.5e9]),
            station_heights_m=np.array([25.0, 25.0]),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )

        # Dominant frequency should be much closer to 26 GHz (high EIRP dominates)
        assert result["freq_hz_dominant"] > 20e9

    def test_below_6ghz_uses_sinc_limits_only(self):
        """At sub-6 GHz, S_ab limits are None, so only SAR_wb matters.

        Since we do not compute SAR_wb in the spatial grid (it requires
        mesh dosimetry), margin should be inf (all checks pass trivially).
        """
        grid_lats = np.array([51.051])
        grid_lons = np.array([3.72])

        result = spatial_compliance_grid(
            station_lats=np.array([51.05]),
            station_lons=np.array([3.72]),
            station_eirp_dbm=np.array([40.0]),
            station_freq_hz=np.array([2.6e9]),  # 2.6 GHz
            station_heights_m=np.array([25.0]),
            grid_lats=grid_lats,
            grid_lons=grid_lons,
        )

        # Below 6 GHz, S_ab and S_inc limits are None, so margin is inf
        assert result["margin_db"][0] == float("inf")
        assert result["compliant"][0]
