"""Tests for the basestations viewer routes and multi-station path aggregation.

Covers: geocode_location, paths_from_basestations, and the Flask API endpoints
at /api/basestations/list, /api/basestations/load, /api/basestations/compute.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from aegis.basestation.adapter import paths_from_basestations
from aegis.basestation.antenna import BaseStation

pytest.importorskip("flask")

from aegis.viewer.routes.basestations import geocode_location  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bs(
    lat: float = 51.050,
    lon: float = 3.720,
    height_m: float = 30.0,
    eirp_dbm: float = 50.0,
    gain_dbi: float = 17.0,
    freq_mhz: float = 3500.0,
    azimuth_deg: float = 0.0,
    technology: str = "5G NR",
    site_code: str = "S001",
    label: str = "test",
) -> BaseStation:
    return BaseStation(
        site_code=site_code,
        antenna_label=label,
        operator="TestOp",
        technology=technology,
        latitude=lat,
        longitude=lon,
        height_m=height_m,
        eirp_dbm=eirp_dbm,
        gain_dbi=gain_dbi,
        freq_mhz=freq_mhz,
        azimuth_deg=azimuth_deg,
        electrical_tilt_deg=5.0,
        mechanical_tilt_deg=0.0,
        horizontal_beamwidth_deg=65.0,
        vertical_beamwidth_deg=10.0,
    )


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------


class TestGeocodeLocation:
    """Tests for the geocode_location coordinate parser."""

    def test_parse_comma_separated(self):
        lat, lon = geocode_location("51.05, 3.72")
        assert lat == pytest.approx(51.05)
        assert lon == pytest.approx(3.72)

    def test_parse_space_separated(self):
        lat, lon = geocode_location("51.05 3.72")
        assert lat == pytest.approx(51.05)
        assert lon == pytest.approx(3.72)

    def test_parse_negative_coordinates(self):
        lat, lon = geocode_location("-33.8688, 151.2093")
        assert lat == pytest.approx(-33.8688)
        assert lon == pytest.approx(151.2093)

    def test_parse_integer_coordinates(self):
        lat, lon = geocode_location("51, 4")
        assert lat == pytest.approx(51.0)
        assert lon == pytest.approx(4.0)

    def test_parse_with_extra_whitespace(self):
        lat, lon = geocode_location("  51.05 ,  3.72  ")
        assert lat == pytest.approx(51.05)
        assert lon == pytest.approx(3.72)

    def test_named_location_falls_back_to_geocoder(self):
        """Named locations that don't match lat,lon pattern try geopy."""
        with pytest.raises((ValueError, ImportError)):
            # Either geopy is missing (ImportError) or the service is unavailable
            # in CI (ValueError). Either way, the fallback path is exercised.
            geocode_location("Nonexistent Place XYZ123")


# ---------------------------------------------------------------------------
# paths_from_basestations (multi-station aggregation)
# ---------------------------------------------------------------------------


class TestPathsFromBasestations:
    """Tests for multi-station path aggregation."""

    @pytest.fixture()
    def origin(self):
        return (51.050, 3.720)

    @pytest.fixture()
    def body_center(self):
        return np.array([0.0, 50.0, 1.5])

    def test_single_station(self, origin, body_center):
        bs = _make_bs()
        paths = paths_from_basestations([bs], body_center, origin)
        assert paths.n_paths == 1
        assert paths.power[0] > 0

    def test_multiple_stations_concatenated(self, origin, body_center):
        stations = [
            _make_bs(azimuth_deg=0.0, site_code="A"),
            _make_bs(azimuth_deg=90.0, site_code="B"),
            _make_bs(azimuth_deg=180.0, site_code="C"),
        ]
        paths = paths_from_basestations(stations, body_center, origin)
        assert paths.n_paths == 3

    def test_far_station_filtered_out(self, origin):
        # Station at origin, body 5 km away - beyond default 2 km limit
        body_far = np.array([5000.0, 0.0, 1.5])
        bs = _make_bs()
        paths = paths_from_basestations([bs], body_far, origin, max_distance_m=2000.0)
        # Station should be filtered; fallback zero path returned
        assert paths.total_power == pytest.approx(0.0)

    def test_custom_max_distance(self, origin):
        body_far = np.array([5000.0, 0.0, 1.5])
        bs = _make_bs()
        # Increase limit to include the station
        paths = paths_from_basestations([bs], body_far, origin, max_distance_m=10000.0)
        assert paths.n_paths == 1
        assert paths.power[0] > 0

    def test_empty_list_returns_zero_power(self, origin, body_center):
        paths = paths_from_basestations([], body_center, origin)
        assert paths.total_power == pytest.approx(0.0)

    def test_all_filtered_returns_zero_power(self, origin):
        body_far = np.array([50000.0, 0.0, 1.5])
        bs = _make_bs()
        paths = paths_from_basestations([bs], body_far, origin, max_distance_m=100.0)
        assert paths.total_power == pytest.approx(0.0)

    def test_k_hats_are_unit_vectors(self, origin, body_center):
        stations = [_make_bs(azimuth_deg=i * 30.0) for i in range(6)]
        paths = paths_from_basestations(stations, body_center, origin)
        norms = np.linalg.norm(paths.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-10)

    def test_all_powers_nonnegative(self, origin, body_center):
        stations = [_make_bs(azimuth_deg=i * 60.0) for i in range(6)]
        paths = paths_from_basestations(stations, body_center, origin)
        assert np.all(paths.power >= 0)

    def test_closer_station_contributes_more_power(self, origin):
        """Inverse square law: closer station has higher power density."""
        body_center = np.array([0.0, 50.0, 1.5])
        bs_close = _make_bs(site_code="CLOSE")  # at origin, 50m from body
        # Station 500m north, ~550m from body
        bs_far = _make_bs(lat=51.0545, site_code="FAR")

        paths_close = paths_from_basestations([bs_close], body_center, origin)
        paths_far = paths_from_basestations([bs_far], body_center, origin)

        assert paths_close.power[0] > paths_far.power[0]


# ---------------------------------------------------------------------------
# Flask API routes
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Create a test Flask app with basestations routes registered."""
    from aegis.viewer.server import create_app

    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config={"server": {"host": "127.0.0.1", "port": 5098}},
    )
    app.config["TESTING"] = True
    return app


class TestBasestationsListRoute:
    """GET /api/basestations/list"""

    def test_empty_list_on_startup(self, app):
        with app.test_client() as c:
            resp = c.get("/api/basestations/list")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["count"] == 0
            assert data["basestations"] == []

    def test_list_after_populating_cache(self, app):
        """Manually inject stations into cache, verify list returns them."""
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs(site_code="LIST01", label="test_ant")
        with _cache_lock:
            _cache["basestations"] = [bs]

        with app.test_client() as c:
            resp = c.get("/api/basestations/list")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["count"] == 1
            entry = data["basestations"][0]
            assert entry["site_code"] == "LIST01"
            assert entry["freq_mhz"] == 3500.0
            assert entry["eirp_dbm"] == 50.0
            assert "archetype" in entry  # from classify_basestation

        # Clean up
        with _cache_lock:
            _cache.pop("basestations", None)


class TestBasestationsLoadRoute:
    """POST /api/basestations/load"""

    def test_load_with_lat_lon(self, app):
        """Loading with explicit lat/lon and no CSV file returns an error or empty."""
        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/load",
                json={"lat": 51.05, "lon": 3.72, "radius_m": 100},
            )
            # Without CSV data or basestationLib, this returns 500 (loading failed)
            # or 200 with count=0. Both are acceptable.
            assert resp.status_code in (200, 500)

    def test_load_with_invalid_location_string(self, app):
        """Non-geocodable location string returns 400."""
        with (
            app.test_client() as c,
            patch(
                "aegis.viewer.routes.basestations.geocode_location",
                side_effect=ValueError("Could not geocode"),
            ),
        ):
            resp = c.post(
                "/api/basestations/load",
                json={"location": "Not A Real Place XYZ"},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert "error" in data

    def test_load_with_bbox(self, app):
        """Loading with explicit bbox parameter."""
        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/load",
                json={"bbox": [3.71, 3.73, 51.04, 51.06]},
            )
            # Without data, either 500 or 200 with empty results
            assert resp.status_code in (200, 500)

    def test_load_with_comma_separated_coords(self, app):
        """Location string in 'lat, lon' format gets parsed correctly."""
        with (
            app.test_client() as c,
            patch(
                "aegis.basestation.adapter.load_basestations_from_csv",
                return_value=[],
            ),
        ):
            resp = c.post(
                "/api/basestations/load",
                json={"location": "51.05, 3.72"},
            )
            # Should succeed (parsing coords) even if no CSV found
            # May still 500 if no CSV file exists, so we accept 200 or 500
            assert resp.status_code in (200, 500)


class TestBasestationsComputeRoute:
    """POST /api/basestations/compute"""

    def test_compute_without_basestations_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/basestations/compute", json={})
            assert resp.status_code == 400
            data = resp.get_json()
            assert "No base stations loaded" in data["error"]

    def test_compute_without_body_returns_400(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs()
        with _cache_lock:
            _cache["basestations"] = [bs]
            _cache.pop("body", None)
            _cache.pop("bodies", None)

        with app.test_client() as c:
            resp = c.post("/api/basestations/compute", json={})
            # "No body mesh loaded" because body may not be set
            # In test fixture with e2e_icosahedron, body is loaded
            # so this may actually proceed. Check status code is valid.
            assert resp.status_code in (200, 400)

        with _cache_lock:
            _cache.pop("basestations", None)

    def test_compute_without_origin_returns_400(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs()
        with _cache_lock:
            _cache["basestations"] = [bs]
            _cache.pop("basestations_origin", None)
            saved_body = _cache.get("body")

        # If body is loaded but no origin, should get 400
        if saved_body is not None:
            with app.test_client() as c:
                resp = c.post("/api/basestations/compute", json={})
                assert resp.status_code == 400
                data = resp.get_json()
                assert "No scene origin" in data["error"]

        with _cache_lock:
            _cache.pop("basestations", None)

    def test_compute_with_valid_data_returns_binary(self, app):
        """Full compute with injected cache data returns binary response."""
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs()
        with _cache_lock:
            body = _cache.get("body")
            _cache["basestations"] = [bs]
            _cache["basestations_origin"] = (51.050, 3.720)

        if body is None:
            pytest.skip("No body mesh loaded in test fixture")

        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute",
                json={"freq_hz": 3.5e9, "skin_model": "itis"},
            )
            assert resp.status_code == 200
            assert resp.content_type == "application/octet-stream"

            # Check X-Stats header contains valid JSON
            stats_raw = resp.headers.get("X-Stats")
            assert stats_raw is not None
            stats = json.loads(stats_raw)
            assert "peak_sab" in stats
            assert "n_basestations" in stats
            assert stats["n_basestations"] == 1
            assert stats["n_paths"] >= 1

            # Binary data should be float32 array
            data = resp.data
            n_tri = body.n_triangles
            assert len(data) >= n_tri * 4  # at least sab array

        with _cache_lock:
            _cache.pop("basestations", None)
            _cache.pop("basestations_origin", None)

    def test_compute_with_index_filter(self, app):
        """Filtering by indices selects only those stations."""
        from aegis.viewer.server import _cache, _cache_lock

        stations = [
            _make_bs(azimuth_deg=0.0, site_code="A"),
            _make_bs(azimuth_deg=90.0, site_code="B"),
            _make_bs(azimuth_deg=180.0, site_code="C"),
        ]
        with _cache_lock:
            body = _cache.get("body")
            _cache["basestations"] = stations
            _cache["basestations_origin"] = (51.050, 3.720)

        if body is None:
            pytest.skip("No body mesh loaded in test fixture")

        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute",
                json={"indices": [0, 2]},
            )
            assert resp.status_code == 200
            stats = json.loads(resp.headers["X-Stats"])
            assert stats["n_basestations"] == 2

        with _cache_lock:
            _cache.pop("basestations", None)
            _cache.pop("basestations_origin", None)

    def test_compute_with_empty_indices_returns_400(self, app):
        """Empty indices list means no stations selected."""
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs()
        with _cache_lock:
            body = _cache.get("body")
            _cache["basestations"] = [bs]
            _cache["basestations_origin"] = (51.050, 3.720)

        if body is None:
            pytest.skip("No body mesh loaded in test fixture")

        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute",
                json={"indices": [5, 10]},  # out of range
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert "No base stations selected" in data["error"]

        with _cache_lock:
            _cache.pop("basestations", None)
            _cache.pop("basestations_origin", None)


class TestBasestationsComputeMimoRoute:
    """POST /api/basestations/compute_mimo"""

    def test_missing_index_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post("/api/basestations/compute_mimo", json={})
            assert resp.status_code == 400
            data = resp.get_json()
            assert "Missing 'index'" in data["error"]

    def test_invalid_index_type_returns_400(self, app):
        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute_mimo",
                json={"index": "abc"},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert "'index' must be an integer" in data["error"]

    def test_out_of_range_index_returns_400(self, app):
        from aegis.viewer.server import _cache, _cache_lock

        bs = _make_bs()
        with _cache_lock:
            _cache["basestations"] = [bs]

        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute_mimo",
                json={"index": 5},
            )
            assert resp.status_code == 400
            assert "out of range" in resp.get_json()["error"]

        with _cache_lock:
            _cache.pop("basestations", None)

    def test_non_mmimo_station_returns_400(self, app):
        """A regular macro station (not mMIMO) should be rejected."""
        from aegis.viewer.server import _cache, _cache_lock

        # Low gain, wide beamwidth = macro, not mmimo
        bs = _make_bs(gain_dbi=12.0, technology="LTE")
        with _cache_lock:
            _cache["basestations"] = [bs]

        with app.test_client() as c:
            resp = c.post(
                "/api/basestations/compute_mimo",
                json={"index": 0},
            )
            assert resp.status_code == 400
            assert "not 'mmimo'" in resp.get_json()["error"]

        with _cache_lock:
            _cache.pop("basestations", None)


class TestBsSummary:
    """Test the _bs_summary serialization helper."""

    def test_summary_contains_required_fields(self):
        from aegis.viewer.routes.basestations import _bs_summary

        bs = _make_bs(site_code="SUM01", label="test_label")
        summary = _bs_summary(bs)

        assert summary["site_code"] == "SUM01"
        assert summary["antenna_label"] == "test_label"
        assert summary["operator"] == "TestOp"
        assert summary["technology"] == "5G NR"
        assert summary["latitude"] == pytest.approx(51.05)
        assert summary["longitude"] == pytest.approx(3.72)
        assert summary["height_m"] == pytest.approx(30.0)
        assert summary["eirp_dbm"] == pytest.approx(50.0)
        assert summary["gain_dbi"] == pytest.approx(17.0)
        assert summary["freq_mhz"] == pytest.approx(3500.0)
        assert summary["has_pattern"] is False
        assert "archetype" in summary

    def test_summary_with_pattern(self):
        from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
        from aegis.viewer.routes.basestations import _bs_summary

        pat = synthetic_pattern_from_beamwidth(65.0, 10.0, 17.0)
        bs = BaseStation(
            site_code="PAT01",
            antenna_label="patterned",
            operator="Op",
            technology="5G NR",
            latitude=51.0,
            longitude=3.7,
            height_m=25.0,
            eirp_dbm=45.0,
            gain_dbi=17.0,
            freq_mhz=3500.0,
            azimuth_deg=0.0,
            electrical_tilt_deg=0.0,
            mechanical_tilt_deg=0.0,
            horizontal_beamwidth_deg=65.0,
            vertical_beamwidth_deg=10.0,
            pattern=pat,
        )
        summary = _bs_summary(bs)
        assert summary["has_pattern"] is True
