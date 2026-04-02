"""Tests for the inter-parameter correlation matrix builder."""

from __future__ import annotations

import numpy as np
import pytest


def _umi_los_params() -> dict:
    return {
        "ds_kf": -0.7,
        "ds_sf": -0.4,
        "asD_ds": 0.5,
        "asA_ds": 0.8,
        "esA_ds": 0.2,
        "sf_kf": 0.5,
        "asD_kf": -0.2,
        "asA_kf": -0.3,
        "asD_sf": -0.5,
        "asA_sf": -0.4,
        "asD_asA": 0.4,
        "esD_asD": 0.5,
        "esA_asD": 0.3,
    }


@pytest.fixture
def umi_result():
    from aegis.channel.correlation import build_correlation_matrix

    return build_correlation_matrix(_umi_los_params())


def test_shape_8x8(umi_result):
    R, L = umi_result
    assert R.shape == (8, 8)
    assert L.shape == (8, 8)


def test_diagonal_is_ones(umi_result):
    R, _ = umi_result
    np.testing.assert_array_almost_equal(np.diag(R), np.ones(8))


def test_symmetric(umi_result):
    R, _ = umi_result
    np.testing.assert_array_almost_equal(R, R.T)


def test_cholesky_reconstructs_R(umi_result):
    R, L = umi_result
    np.testing.assert_allclose(L @ L.T, R, atol=1e-10)


def test_positive_definite(umi_result):
    R, _ = umi_result
    eigvals = np.linalg.eigvalsh(R)
    assert np.all(eigvals > 0)


def test_known_value_ds_kf():
    from aegis.channel.correlation import build_correlation_matrix

    params = {"ds_kf": -0.7}
    R, _ = build_correlation_matrix(params)
    # With only one off-diagonal entry set, the matrix is already PD for |r| < 1
    assert R[0, 1] == pytest.approx(-0.7, abs=1e-10)
    assert R[1, 0] == pytest.approx(-0.7, abs=1e-10)


def test_empty_params_gives_identity():
    from aegis.channel.correlation import build_correlation_matrix

    R, L = build_correlation_matrix({})
    np.testing.assert_array_almost_equal(R, np.eye(8))
    np.testing.assert_array_almost_equal(L, np.eye(8))


def test_forces_positive_definite():
    from aegis.channel.correlation import build_correlation_matrix

    # These three correlations together are inconsistent (not PD)
    params = {"ds_kf": -0.99, "ds_sf": -0.99, "sf_kf": -0.99}
    R, L = build_correlation_matrix(params)
    # Matrix must still be PD
    eigvals = np.linalg.eigvalsh(R)
    assert np.all(eigvals > 0)
    # Cholesky factor must reconstruct R
    np.testing.assert_allclose(L @ L.T, R, atol=1e-10)
    # Diagonal must remain 1
    np.testing.assert_array_almost_equal(np.diag(R), np.ones(8))
