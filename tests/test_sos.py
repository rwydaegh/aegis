"""Tests for the sum-of-sinusoids spatial correlation engine."""

from __future__ import annotations

import numpy as np
import pytest


class TestSumOfSinusoidsBasic:
    def test_output_shape_single_point(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1.0)
        positions = np.array([[0.0, 0.0, 0.0]])
        result = sos.evaluate(positions)
        assert result.shape == (1,)

    def test_output_shape_grid(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1.0)
        positions = np.zeros((50, 3))
        result = sos.evaluate(positions)
        assert result.shape == (50,)

    def test_deterministic_with_seed(self):
        from aegis.channel.sos import SumOfSinusoids

        positions = np.random.default_rng(0).standard_normal((30, 3))
        sos1 = SumOfSinusoids(d_lambda=2.0, seed=42)
        sos2 = SumOfSinusoids(d_lambda=2.0, seed=42)
        np.testing.assert_array_equal(sos1.evaluate(positions), sos2.evaluate(positions))

    def test_different_seeds_differ(self):
        from aegis.channel.sos import SumOfSinusoids

        positions = np.random.default_rng(0).standard_normal((30, 3))
        sos1 = SumOfSinusoids(d_lambda=2.0, seed=1)
        sos2 = SumOfSinusoids(d_lambda=2.0, seed=2)
        assert not np.allclose(sos1.evaluate(positions), sos2.evaluate(positions))

    def test_values_finite(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1.0)
        positions = np.random.default_rng(99).standard_normal((100, 3))
        result = sos.evaluate(positions)
        assert np.all(np.isfinite(result))


class TestSumOfSinusoidsStatistics:
    def test_approximate_zero_mean(self):
        from aegis.channel.sos import SumOfSinusoids

        rng = np.random.default_rng(7)
        positions = rng.uniform(-10, 10, (2000, 3))
        sos = SumOfSinusoids(d_lambda=0.5, n_sinusoids=20, seed=42)
        values = sos.evaluate(positions)
        assert abs(values.mean()) < 0.15

    def test_approximate_unit_variance(self):
        from aegis.channel.sos import SumOfSinusoids

        rng = np.random.default_rng(7)
        positions = rng.uniform(-10, 10, (2000, 3))
        sos = SumOfSinusoids(d_lambda=0.5, n_sinusoids=20, seed=42)
        values = sos.evaluate(positions)
        assert abs(values.var() - 1.0) < 0.3

    def test_acf_at_zero_is_one(self):
        from aegis.channel.sos import SumOfSinusoids

        origin = np.array([[0.0, 0.0, 0.0]])
        # Variance from many realizations at origin (different seeds)
        vals_at_origin = np.array(
            [SumOfSinusoids(d_lambda=1.0, n_sinusoids=50, seed=s).evaluate(origin)[0] for s in range(200)]
        )
        acf_zero = np.corrcoef(vals_at_origin, vals_at_origin)[0, 1]
        assert acf_zero == pytest.approx(1.0)

    def test_acf_decays_with_distance(self):
        from aegis.channel.sos import SumOfSinusoids

        d_lambda = 5.0
        n_seeds = 300
        origin = np.array([[0.0, 0.0, 0.0]])
        near = np.array([[2.0, 0.0, 0.0]])
        far = np.array([[50.0, 0.0, 0.0]])

        vals_origin, vals_near, vals_far = [], [], []
        for s in range(n_seeds):
            sos = SumOfSinusoids(d_lambda=d_lambda, n_sinusoids=30, seed=s)
            vals_origin.append(sos.evaluate(origin)[0])
            vals_near.append(sos.evaluate(near)[0])
            vals_far.append(sos.evaluate(far)[0])

        vals_origin = np.array(vals_origin)
        vals_near = np.array(vals_near)
        vals_far = np.array(vals_far)

        corr_near = np.corrcoef(vals_origin, vals_near)[0, 1]
        corr_far = np.corrcoef(vals_origin, vals_far)[0, 1]

        assert corr_near > corr_far

    def test_decorrelation_distance_scaling(self):
        from aegis.channel.sos import SumOfSinusoids

        n_seeds = 300
        origin = np.array([[0.0, 0.0, 0.0]])
        probe = np.array([[3.0, 0.0, 0.0]])

        corrs = []
        for d_lambda in [1.0, 10.0]:
            vals_origin, vals_probe = [], []
            for s in range(n_seeds):
                sos = SumOfSinusoids(d_lambda=d_lambda, n_sinusoids=30, seed=s)
                vals_origin.append(sos.evaluate(origin)[0])
                vals_probe.append(sos.evaluate(probe)[0])
            corrs.append(np.corrcoef(vals_origin, vals_probe)[0, 1])

        # Larger d_lambda means more correlation at the same separation
        assert corrs[1] > corrs[0]


class TestSumOfSinusoidsEdgeCases:
    def test_2d_positions_raise_value_error(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1.0)
        with pytest.raises(ValueError):
            sos.evaluate(np.array([[0.0, 1.0]]))

    def test_single_sinusoid_works(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1.0, n_sinusoids=1)
        result = sos.evaluate(np.array([[0.0, 0.0, 0.0]]))
        assert result.shape == (1,)
        assert np.isfinite(result[0])

    def test_very_small_d_lambda_works(self):
        from aegis.channel.sos import SumOfSinusoids

        sos = SumOfSinusoids(d_lambda=1e-4)
        result = sos.evaluate(np.array([[0.0, 0.0, 0.0], [1e-5, 0.0, 0.0]]))
        assert result.shape == (2,)
        assert np.all(np.isfinite(result))
