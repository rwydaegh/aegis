"""Tests for the CloudRF API client."""

from unittest.mock import MagicMock, patch

import pytest


def test_search_antennas():
    from aegis.integration.cloudrf import CloudRFClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"rows": [{"id": 1, "manufacturer": "Ericsson", "model": "AIR6468"}]}
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    with patch("requests.Session.post", return_value=mock_resp):
        client = CloudRFClient(api_key="test-key")
        results = client.search_antennas(manufacturer="Ericsson")
        assert len(results) == 1
        assert results[0]["model"] == "AIR6468"


def test_antenna_to_pattern():
    from aegis.integration.cloudrf import CloudRFClient

    client = CloudRFClient.__new__(CloudRFClient)  # skip __init__
    antenna_data = {
        "gain_dbd": 10.0,
        "pattern_data": {
            "horizontal": [list(range(360)), [0.0] * 360],
            "vertical": [list(range(360)), [0.0] * 360],
        },
    }
    pattern = client.antenna_to_pattern(antenna_data)
    assert pattern.gain_dbi.shape == (181, 360)
    assert pattern.max_gain_dbi == pytest.approx(12.15, abs=0.5)


def test_path_returns_signal():
    from aegis.integration.cloudrf import CloudRFClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "Signal power at receiver dBm": -65.3,
        "Computed path loss dB": 98.2,
    }
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    with patch("requests.Session.post", return_value=mock_resp):
        client = CloudRFClient(api_key="test-key")
        result = client.path(50.85, 4.35, 30, 50.86, 4.36, 1.5, 3500, 2.0, 25.0)
        assert "Signal power at receiver dBm" in result
