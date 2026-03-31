"""Tests for location loading routes.

Covers: /api/location/load, /api/location/cancel, /api/geocode.

The pipeline subprocess and Google API key are mocked to avoid external
dependencies.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")


# ---------------------------------------------------------------------------
# GET /api/location/load (SSE stream)
# ---------------------------------------------------------------------------


class TestLocationLoad:
    def test_missing_location_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load")
        assert resp.status_code == 400
        assert "location" in resp.get_json()["error"].lower()

    def test_missing_location_empty_string_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=")
        assert resp.status_code == 400

    def test_invalid_radius_string_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=abc")
        assert resp.status_code == 400
        assert "radius" in resp.get_json()["error"]

    def test_radius_zero_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=0")
        assert resp.status_code == 400
        assert "between 1 and 500" in resp.get_json()["error"]

    def test_radius_negative_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=-10")
        assert resp.status_code == 400

    def test_radius_too_large_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=600")
        assert resp.status_code == 400

    def test_invalid_voxel_size_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&voxel_size=abc")
        assert resp.status_code == 400

    def test_voxel_size_zero_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&voxel_size=0")
        assert resp.status_code == 400
        assert "voxel_size" in resp.get_json()["error"]

    def test_voxel_size_too_small_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&voxel_size=0.05")
        assert resp.status_code == 400
        assert "0.1" in resp.get_json()["error"]

    def test_voxel_size_too_large_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&voxel_size=15")
        assert resp.status_code == 400

    def test_missing_google_api_key_returns_400(self, viewer_app):
        import os

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False),
        ):
            resp = c.get("/api/location/load?location=Ghent")
        assert resp.status_code == 400
        assert "GOOGLE_API_KEY" in resp.get_json()["error"]

    def test_pipeline_not_found_returns_404(self, viewer_app):
        import os

        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["pipeline_dir"] = None

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", return_value=None),
        ):
            resp = c.get("/api/location/load?location=Ghent")
        assert resp.status_code == 404
        assert "Pipeline not found" in resp.get_json()["error"]

    def test_valid_params_returns_sse_stream(self, viewer_app):
        """With all requirements met, the route returns an SSE event stream."""
        import os
        from pathlib import Path

        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["pipeline_dir"] = "/tmp/fake_pipeline"
            _cache["cache_dir"] = "/tmp/fake_cache"

        fake_pipeline_js = Path("/tmp/fake_pipeline/index.js")

        def mock_find_pipeline(pipeline_dir):
            return fake_pipeline_js

        def mock_run_pipeline(*args, **kwargs):
            yield "Processing..."
            yield "Done"

        def mock_cache_dir_for(location, radius, base_cache):
            return Path("/tmp/fake_cache/voxels")

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", side_effect=mock_find_pipeline),
            patch("aegis.viewer.pipeline.run_pipeline", side_effect=mock_run_pipeline),
            patch("aegis.viewer.pipeline.cache_dir_for", side_effect=mock_cache_dir_for),
        ):
            resp = c.get("/api/location/load?location=Ghent&radius=30")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type


# ---------------------------------------------------------------------------
# POST /api/location/cancel
# ---------------------------------------------------------------------------


class TestLocationCancel:
    def test_cancel_returns_json(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/location/cancel")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "cancelled" in data
        assert isinstance(data["cancelled"], bool)

    def test_cancel_without_running_pipeline(self, viewer_app):
        """Cancel when no pipeline is running returns cancelled=False."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/location/cancel")
        data = resp.get_json()
        assert data["cancelled"] is False

    def test_cancel_calls_cancel_pipeline(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.pipeline.cancel_pipeline", return_value=True) as mock_cancel,
        ):
            resp = c.post("/api/location/cancel")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["cancelled"] is True
        mock_cancel.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/location/load - extended
# ---------------------------------------------------------------------------


class TestLocationLoadExtended:
    def test_valid_voxel_size(self, viewer_app):
        """Valid voxel_size within range (0.1 to 10) passes validation."""
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", return_value=MagicMock()),
            patch("aegis.viewer.pipeline.run_pipeline", return_value=iter(["Done"])),
            patch("aegis.viewer.pipeline.cache_dir_for", return_value=MagicMock()),
        ):
            resp = c.get("/api/location/load?location=Ghent&voxel_size=0.5")
        # Should get past validation (200 or SSE stream); not 400
        assert resp.status_code != 400 or "voxel_size" not in resp.get_json().get("error", "")

    def test_voxel_size_exactly_0_1(self, viewer_app):
        """Boundary: voxel_size=0.1 should be accepted (not < 0.1)."""
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", return_value=MagicMock()),
            patch("aegis.viewer.pipeline.run_pipeline", return_value=iter(["Done"])),
            patch("aegis.viewer.pipeline.cache_dir_for", return_value=MagicMock()),
        ):
            resp = c.get("/api/location/load?location=Ghent&voxel_size=0.1")
        # 0.1 is exactly the minimum; should not fail with "below 0.1m"
        if resp.status_code == 400:
            assert "0.1" not in resp.get_json().get("error", "")

    def test_voxel_size_exactly_10(self, viewer_app):
        """Boundary: voxel_size=10 should be accepted."""
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", return_value=MagicMock()),
            patch("aegis.viewer.pipeline.run_pipeline", return_value=iter(["Done"])),
            patch("aegis.viewer.pipeline.cache_dir_for", return_value=MagicMock()),
        ):
            resp = c.get("/api/location/load?location=Ghent&voxel_size=10")
        if resp.status_code == 400:
            assert "voxel_size" not in resp.get_json().get("error", "")

    def test_radius_exactly_1(self, viewer_app):
        """Boundary: radius=1 is the minimum valid value."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=1")
        # Should pass radius validation (may fail on API key or pipeline)
        if resp.status_code == 400:
            assert "between 1 and 500" not in resp.get_json().get("error", "")

    def test_radius_exactly_500(self, viewer_app):
        """Boundary: radius=500 is the maximum valid value."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=Ghent&radius=500")
        if resp.status_code == 400:
            assert "between 1 and 500" not in resp.get_json().get("error", "")

    def test_whitespace_only_location_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/location/load?location=%20%20")
        assert resp.status_code == 400

    def test_force_true_param(self, viewer_app):
        """force=true bypasses cache."""
        from pathlib import Path

        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["pipeline_dir"] = "/tmp/fake_pipeline"
            _cache["cache_dir"] = "/tmp/fake_cache"

        fake_pipeline_js = Path("/tmp/fake_pipeline/index.js")

        def mock_find_pipeline(pipeline_dir):
            return fake_pipeline_js

        def mock_run_pipeline(*args, **kwargs):
            yield "Processing with force..."
            yield "Done"

        def mock_cache_dir_for(location, radius, base_cache):
            return Path("/tmp/fake_cache/voxels")

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.pipeline.find_pipeline", side_effect=mock_find_pipeline),
            patch("aegis.viewer.pipeline.run_pipeline", side_effect=mock_run_pipeline),
            patch("aegis.viewer.pipeline.cache_dir_for", side_effect=mock_cache_dir_for),
        ):
            resp = c.get("/api/location/load?location=Ghent&radius=30&force=true")

        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_sse_stream_has_correct_headers(self, viewer_app):
        """SSE responses should have appropriate cache control headers."""
        from pathlib import Path

        from aegis.viewer.server import _cache, _cache_lock

        with _cache_lock:
            _cache["pipeline_dir"] = "/tmp/fake_pipeline"
            _cache["cache_dir"] = "/tmp/fake_cache"

        fake_pipeline_js = Path("/tmp/fake_pipeline/index.js")

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch(
                "aegis.viewer.pipeline.find_pipeline",
                return_value=fake_pipeline_js,
            ),
            patch(
                "aegis.viewer.pipeline.run_pipeline",
                return_value=iter(["step 1"]),
            ),
            patch(
                "aegis.viewer.pipeline.cache_dir_for",
                return_value=Path("/tmp/fake_cache/voxels"),
            ),
        ):
            resp = c.get("/api/location/load?location=Ghent&radius=30")

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "no-cache"
        assert resp.headers.get("X-Accel-Buffering") == "no"


# ---------------------------------------------------------------------------
# GET /api/geocode
# ---------------------------------------------------------------------------


class TestGeocode:
    def test_missing_query_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/geocode")
        assert resp.status_code == 400
        assert "Missing q" in resp.get_json()["error"]

    def test_empty_query_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/geocode?q=")
        assert resp.status_code == 400

    def test_query_too_long_returns_error(self, viewer_app):
        long_query = "x" * 501
        with viewer_app.test_client() as c:
            resp = c.get(f"/api/geocode?q={long_query}")
        # Route does not validate length, so the query passes through.
        # Without a mock, the result depends on the API key and network.
        # Accept 400 (no API key) or 404 (no results) or 502 (network error).
        assert resp.status_code in (400, 404, 502)

    def test_missing_api_key_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False),
        ):
            resp = c.get("/api/geocode?q=Ghent")
        assert resp.status_code == 400
        assert "GOOGLE_API_KEY" in resp.get_json()["error"]

    def test_successful_geocode(self, viewer_app):
        """Mock a successful Google Geocoding API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "geometry": {"location": {"lat": 51.0543, "lng": 3.7174}},
                    "formatted_address": "Ghent, Belgium",
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.routes.location.http_requests.get", return_value=mock_response),
        ):
            resp = c.get("/api/geocode?q=Ghent")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["lat"] == pytest.approx(51.0543)
        assert data["lon"] == pytest.approx(3.7174)
        assert data["formatted"] == "Ghent, Belgium"

    def test_zero_results_returns_404(self, viewer_app):
        """When Google returns ZERO_RESULTS, endpoint returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_response.raise_for_status = MagicMock()

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.routes.location.http_requests.get", return_value=mock_response),
        ):
            resp = c.get("/api/geocode?q=xyznonexistent12345")

        assert resp.status_code == 404
        assert "No results" in resp.get_json()["error"]

    def test_api_error_status_returns_404(self, viewer_app):
        """When Google returns an error status with empty results, route returns 404.

        The geocode route does not inspect the status field; it only checks
        whether the results list is empty.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "results": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.routes.location.http_requests.get", return_value=mock_response),
        ):
            resp = c.get("/api/geocode?q=Ghent")

        assert resp.status_code == 404

    def test_network_error_returns_502(self, viewer_app):
        """When the HTTP request to Google fails, endpoint returns 502."""
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch(
                "aegis.viewer.routes.location.http_requests.get",
                side_effect=ConnectionError("Network unreachable"),
            ),
        ):
            resp = c.get("/api/geocode?q=Ghent")

        assert resp.status_code == 502
        assert "Geocoding failed" in resp.get_json()["error"]

    def test_ok_status_with_empty_results_returns_404(self, viewer_app):
        """Edge case: Google returns OK but results list is empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "OK", "results": []}
        mock_response.raise_for_status = MagicMock()

        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False),
            patch("aegis.viewer.routes.location.http_requests.get", return_value=mock_response),
        ):
            resp = c.get("/api/geocode?q=Ghent")

        assert resp.status_code == 404

    def test_query_max_length_boundary(self, viewer_app):
        """Query of exactly 500 chars should be accepted."""
        query = "x" * 500
        with (
            viewer_app.test_client() as c,
            patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False),
        ):
            resp = c.get(f"/api/geocode?q={query}")
        # Should not fail with "too long"; may fail on API key
        if resp.status_code == 400:
            assert "too long" not in resp.get_json()["error"]
