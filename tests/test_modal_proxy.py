"""Tests for modal_proxy.py - fallback and dispatch logic."""

from unittest.mock import MagicMock

import numpy as np

from aegis.paths import PropagationPaths


class TestModalProxyFallback:
    """Test that the proxy returns None when Modal is unavailable."""

    def test_returns_none_when_no_token(self, monkeypatch):
        monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
        monkeypatch.delenv("USE_MODAL_RT", raising=False)

        from aegis.viewer import modal_proxy

        # Force re-init
        modal_proxy._MODAL_AVAILABLE = False
        modal_proxy._initialized = False

        result = modal_proxy.trace_differt(
            scene_xml="<scene/>",
            tx_pos=[0, 0, 10],
            rx_pos=[0, 0, 1],
            max_order=0,
            freq_hz=28e9,
            tx_power_dbm=23.0,
        )
        assert result is None

    def test_returns_none_when_modal_disabled(self, monkeypatch):
        monkeypatch.setenv("MODAL_TOKEN_ID", "fake")
        monkeypatch.setenv("MODAL_TOKEN_SECRET", "fake")
        monkeypatch.setenv("USE_MODAL_RT", "false")

        from aegis.viewer import modal_proxy

        modal_proxy._MODAL_AVAILABLE = False
        modal_proxy._initialized = False

        result = modal_proxy.trace_differt(
            scene_xml="<scene/>",
            tx_pos=[0, 0, 10],
            rx_pos=[0, 0, 1],
            max_order=0,
            freq_hz=28e9,
            tx_power_dbm=23.0,
        )
        assert result is None

    def test_returns_none_on_modal_exception(self, monkeypatch):
        monkeypatch.setenv("MODAL_TOKEN_ID", "fake")
        monkeypatch.setenv("MODAL_TOKEN_SECRET", "fake")
        monkeypatch.setenv("USE_MODAL_RT", "true")

        from aegis.viewer import modal_proxy

        # Mock the Modal class lookup to raise
        modal_proxy._initialized = True
        modal_proxy._MODAL_AVAILABLE = True
        modal_proxy._differt_cls = MagicMock()
        modal_proxy._differt_cls.return_value.trace.remote.side_effect = ConnectionError("Modal down")

        result = modal_proxy.trace_differt(
            scene_xml="<scene/>",
            tx_pos=[0, 0, 10],
            rx_pos=[0, 0, 1],
            max_order=0,
            freq_hz=28e9,
            tx_power_dbm=23.0,
        )
        assert result is None


class TestModalProxyDispatch:
    """Test that the proxy correctly dispatches and returns results."""

    def test_trace_differt_returns_dict(self, monkeypatch):
        monkeypatch.setenv("MODAL_TOKEN_ID", "fake")
        monkeypatch.setenv("MODAL_TOKEN_SECRET", "fake")
        monkeypatch.setenv("USE_MODAL_RT", "true")

        fake_paths = PropagationPaths(
            k_hat=np.array([[0, 0, -1]]),
            psi=np.array([[1 + 0j, 0, 0]]),
            element_index=np.array([0]),
            delay=np.array([1e-8]),
            is_los=np.array([True]),
        )
        fake_result = {
            "paths": fake_paths.to_dict(),
            "path_viz": [],
            "timings": {"trace_ms": 100},
            "gpu_backend": "T4",
        }

        from aegis.viewer import modal_proxy

        modal_proxy._initialized = True
        modal_proxy._MODAL_AVAILABLE = True
        modal_proxy._differt_cls = MagicMock()
        modal_proxy._differt_cls.return_value.trace.remote.return_value = fake_result

        result = modal_proxy.trace_differt(
            scene_xml="<scene/>",
            tx_pos=[0, 0, 10],
            rx_pos=[0, 0, 1],
            max_order=0,
            freq_hz=28e9,
            tx_power_dbm=23.0,
        )
        assert result is not None
        assert result["gpu_backend"] == "T4"
        assert "paths" in result

        # Verify round-trip
        recovered = PropagationPaths.from_dict(result["paths"])
        np.testing.assert_array_equal(recovered.k_hat, fake_paths.k_hat)


class TestGpuStatus:
    """Test GPU warmth status tracking."""

    def test_gpu_status_cold_by_default(self, monkeypatch):
        """GPU status reports cold when no RT calls have been made."""
        from aegis.viewer import modal_proxy

        monkeypatch.setattr(modal_proxy, "_last_rt_success", 0.0)
        monkeypatch.setattr(modal_proxy, "_initialized", False)
        monkeypatch.setattr(modal_proxy, "_MODAL_AVAILABLE", False)
        status = modal_proxy.gpu_status()
        assert status["warm"] is False
        assert status["seconds_remaining"] == 0

    def test_gpu_status_warm_after_mark(self, monkeypatch):
        """GPU status reports warm after _mark_success() when Modal is available."""
        from aegis.viewer import modal_proxy

        monkeypatch.setattr(modal_proxy, "_initialized", True)
        monkeypatch.setattr(modal_proxy, "_MODAL_AVAILABLE", True)
        monkeypatch.setattr(modal_proxy, "_last_rt_success", 0.0)
        modal_proxy._mark_success()
        status = modal_proxy.gpu_status()
        assert status["warm"] is True
        assert status["enabled"] is True
        assert status["seconds_remaining"] > 0

    def test_gpu_status_cold_when_enabled_but_not_initialized(self, monkeypatch):
        """GPU reports enabled=True, warm=False before first RT call."""
        from aegis.viewer import modal_proxy

        monkeypatch.setattr(modal_proxy, "_initialized", False)
        monkeypatch.setattr(modal_proxy, "_MODAL_AVAILABLE", False)
        monkeypatch.setenv("MODAL_TOKEN_ID", "fake")
        monkeypatch.setenv("USE_MODAL_RT", "true")
        status = modal_proxy.gpu_status()
        assert status["enabled"] is True
        assert status["warm"] is False
