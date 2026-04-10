"""Tests for array_factor_gain() in aegis.viewer.compute."""

from __future__ import annotations

import pytest

pytest.importorskip("flask")

import numpy as np  # noqa: E402

from aegis.viewer.compute import array_factor_gain  # noqa: E402

_FREQ = 28e9
_BROADSIDE = np.array([1.0, 0.0, 0.0])  # pointing along +x


def test_isotropic_1x1_returns_one():
    k = np.array([1.0, 0.0, 0.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "isotropic", _FREQ)
    assert result == pytest.approx(1.0)


def test_isotropic_1x1_off_axis_still_one():
    # Isotropic has no angular dependence, any direction should give 1.0
    k = np.array([0.0, 1.0, 0.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "isotropic", _FREQ)
    assert result == pytest.approx(1.0)


def test_short_dipole_1x1_broadside():
    # k along broadside (+x), dipole axis is perpendicular to broadside.
    # Broadside = [1,0,0], ref = [0,1,0] (least-aligned canonical axis... wait:
    # abs_b = [1,0,0], argmin -> index 1, ref = [0,1,0]
    # dipole_axis = cross([1,0,0], [0,1,0]) = [0,0,1]
    # k=[1,0,0], cos_alpha = 0, sin^2_alpha = 1, G = 1.5
    k = np.array([1.0, 0.0, 0.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "short_dipole", _FREQ)
    assert result == pytest.approx(1.5)


def test_short_dipole_1x1_along_axis():
    # k along dipole axis -> sin^2(alpha) = 0 -> G = 0
    # Broadside = [1,0,0], dipole_axis = [0,0,1] (from above derivation)
    k = np.array([0.0, 0.0, 1.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "short_dipole", _FREQ)
    assert result == pytest.approx(0.0, abs=1e-12)


def test_patch_1x1_broadside():
    # k along broadside: cos(theta) = 1, G = 1.0^1.5 = 1.0
    k = np.array([1.0, 0.0, 0.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "patch", _FREQ)
    assert result == pytest.approx(1.0)


def test_patch_1x1_backside_zero():
    # k opposite to broadside: cos(theta) < 0, G = max(cos,0)^1.5 = 0
    k = np.array([-1.0, 0.0, 0.0])
    result = array_factor_gain(k, 1, 1, 0.5, 0.5, _BROADSIDE, "patch", _FREQ)
    assert result == pytest.approx(0.0, abs=1e-12)


def test_4x4_broadside_gain_equals_N_squared_times_element():
    # 4x4 patch at broadside: all phases identical -> |AF|^2 = (4*4)^2 = 256
    # G_element(broadside) = 1.0, total = 256
    k = np.array([1.0, 0.0, 0.0])
    result = array_factor_gain(k, 4, 4, 0.5, 0.5, _BROADSIDE, "patch", _FREQ)
    assert result == pytest.approx(256.0, rel=1e-10)


def test_2x2_isotropic_broadside():
    # 2x2 isotropic at broadside: all phases zero -> |AF|^2 = (2*2)^2 = 16
    # G_element = 1.0, total = 16
    k = np.array([1.0, 0.0, 0.0])
    result = array_factor_gain(k, 2, 2, 0.5, 0.5, _BROADSIDE, "isotropic", _FREQ)
    assert result == pytest.approx(16.0, rel=1e-10)


def test_gain_is_always_nonnegative():
    rng = np.random.default_rng(42)
    directions = rng.standard_normal((50, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)

    for k in directions:
        for pattern in ("isotropic", "patch", "short_dipole"):
            result = array_factor_gain(k, 3, 3, 0.5, 0.5, _BROADSIDE, pattern, _FREQ)
            assert result >= 0.0, f"Negative gain {result} for {pattern}, k={k}"
