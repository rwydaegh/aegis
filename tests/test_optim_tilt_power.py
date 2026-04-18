"""Tests for tilt/power optimizer."""

import numpy as np
import pytest


def _make_synthetic_paths(n_paths=50, seed=42):
    """Build synthetic PropagationPaths for testing."""
    from aegis.paths import PropagationPaths

    rng = np.random.default_rng(seed)
    theta = rng.uniform(0, np.pi / 2, n_paths)
    phi = rng.uniform(0, 2 * np.pi, n_paths)
    k_hat = np.column_stack(
        [
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta),
        ]
    )
    power = rng.uniform(0.1, 2.0, n_paths)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


class TestTiltPowerSetup:
    def test_setup_returns_state(self):
        from aegis.optim.tilt_power import setup

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)
        state = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            tilt_init_deg=10.0,
            power_init_dbm=60.0,
            icnirp_limit=20.0,
        )
        assert "tilt_deg" in state
        assert "power_dbm" in state
        assert state["tilt_deg"] == pytest.approx(10.0)


class TestTiltPowerStep:
    def test_converges_to_compliance(self):
        from aegis.optim.tilt_power import setup, step

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)
        state = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            tilt_init_deg=0.0,
            power_init_dbm=70.0,
            icnirp_limit=20.0,
        )

        for _ in range(200):
            state, result = step(state)
            if result.get("converged"):
                break

        # Should find a compliant configuration
        assert result["stats"]["peak_sab"] <= 20.0 + 0.5

    def test_sab_array_returned(self):
        from aegis.optim.tilt_power import setup, step

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)
        state = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            tilt_init_deg=5.0,
            power_init_dbm=60.0,
            icnirp_limit=20.0,
        )
        state, result = step(state)
        assert "sab" in result
        assert result["sab"].shape[0] > 0

    def test_power_increases_when_compliant(self):
        """When starting well below the limit, optimizer should increase power."""
        from aegis.optim.tilt_power import setup, step

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)
        initial_pwr = 30.0  # low power, definitely compliant
        state = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            tilt_init_deg=10.0,
            power_init_dbm=initial_pwr,
            icnirp_limit=20.0,
        )

        for _ in range(50):
            state, result = step(state)

        assert result["params"]["power_dbm"] > initial_pwr

    def test_stats_dict_has_peaks_sab_for_colorlegend(self):
        """Regression test for PR #565 (issue #563): ColorLegend reads
        stats.peaks?.[displayQuantity] ?? stats.peak_sab. If either key is
        missing, the legend renders NaN ticks."""
        from aegis.optim.tilt_power import setup, step

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)
        state = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            tilt_init_deg=5.0,
            power_init_dbm=60.0,
            icnirp_limit=20.0,
        )
        _, result = step(state)

        assert "stats" in result
        stats = result["stats"]
        assert "peak_sab" in stats
        assert "peaks" in stats
        assert "sab" in stats["peaks"]
        assert np.isfinite(stats["peak_sab"])
        assert stats["peak_sab"] == stats["peaks"]["sab"]

    def test_T0_scales_sab(self):
        """T0 factor must scale S_ab: lower T0 should yield lower peak S_ab."""
        from aegis.optim.tilt_power import _evaluate, setup

        paths = _make_synthetic_paths()
        normals = np.tile([0, 0, 1], (100, 1)).astype(np.float64)

        state_no_T0 = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            T0=1.0,
        )
        state_skin = setup(
            paths=paths,
            normals=normals,
            antenna_direction=np.array([0.0, 0.0, -1.0]),
            T0=0.44,
        )

        _, peak_1 = _evaluate(state_no_T0, 0.0, 60.0)
        _, peak_skin = _evaluate(state_skin, 0.0, 60.0)

        assert peak_skin == pytest.approx(0.44 * peak_1, rel=1e-10)
