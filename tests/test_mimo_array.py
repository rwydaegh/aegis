"""Tests for AntennaArray geometry and steering vectors."""

import numpy as np
import pytest

from aegis.constants import C_0


def test_upa_n_elements():
    """UPA with n_h x n_v elements has M = n_h * n_v total."""
    from aegis.mimo.array import AntennaArray

    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    assert arr.n_elements == 16


def test_upa_single_element():
    """1x1 UPA degenerates to a single element at center."""
    from aegis.mimo.array import AntennaArray

    center = np.array([5.0, 0.0, 3.0])
    arr = AntennaArray.upa(
        n_h=1,
        n_v=1,
        d_h=0.005,
        d_v=0.005,
        center=center,
        broadside=np.array([1.0, 0, 0]),
    )
    assert arr.n_elements == 1
    np.testing.assert_allclose(arr.element_positions[0], center)


def test_upa_elements_in_broadside_plane():
    """All elements lie in the plane perpendicular to broadside."""
    from aegis.mimo.array import AntennaArray

    broadside = np.array([0.6, 0.8, 0.0])
    broadside /= np.linalg.norm(broadside)
    center = np.array([1.0, 2.0, 3.0])
    arr = AntennaArray.upa(
        n_h=4,
        n_v=2,
        d_h=0.01,
        d_v=0.01,
        center=center,
        broadside=broadside,
    )
    offsets = arr.element_positions - center
    dots = offsets @ broadside
    np.testing.assert_allclose(dots, 0.0, atol=1e-14)


def test_upa_element_spacing():
    """Inter-element distances match d_h and d_v."""
    from aegis.mimo.array import AntennaArray

    d_h, d_v = 0.01, 0.008
    arr = AntennaArray.upa(
        n_h=3,
        n_v=2,
        d_h=d_h,
        d_v=d_v,
        center=np.zeros(3),
        broadside=np.array([0, 0, 1.0]),
    )
    # For 3x2 array, horizontal neighbors differ by d_h, vertical by d_v.
    # Element ordering: row-major (v outer, h inner).
    # Row 0: elements 0,1,2 (h varies). Row 1: elements 3,4,5.
    p = arr.element_positions
    # Horizontal spacing within row 0
    d01 = np.linalg.norm(p[1] - p[0])
    d12 = np.linalg.norm(p[2] - p[1])
    np.testing.assert_allclose(d01, d_h, atol=1e-14)
    np.testing.assert_allclose(d12, d_h, atol=1e-14)
    # Vertical spacing between row 0 and row 1 (same h index)
    d03 = np.linalg.norm(p[3] - p[0])
    np.testing.assert_allclose(d03, d_v, atol=1e-14)


def test_upa_centroid_at_reference():
    """Center of mass of element positions equals reference_position."""
    from aegis.mimo.array import AntennaArray

    center = np.array([5.0, 0.0, 3.0])
    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=center,
        broadside=np.array([-1.0, 0, 0]),
    )
    np.testing.assert_allclose(
        arr.element_positions.mean(axis=0),
        center,
        atol=1e-14,
    )


def test_antenna_array_frozen():
    """AntennaArray is immutable."""
    from aegis.mimo.array import AntennaArray

    arr = AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    with pytest.raises(AttributeError):
        arr.element_pattern = "patch"


def test_steering_vector_broadside():
    """Steering vector for broadside direction has uniform phase (all ones)."""
    from aegis.mimo.array import AntennaArray

    broadside = np.array([1.0, 0, 0])
    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=broadside,
    )
    freq_hz = 28e9
    a = arr.steering_vector(broadside, freq_hz)
    assert a.shape == (16,)
    assert a.dtype == complex
    # All elements in broadside plane -> k_hat . offset = 0 -> phase = 1
    np.testing.assert_allclose(a, np.ones(16, dtype=complex), atol=1e-14)


def test_steering_vector_endfire():
    """Steering vector for endfire has progressive phase shifts."""
    from aegis.mimo.array import AntennaArray

    freq_hz = 28e9
    lam = C_0 / freq_hz
    d = 0.5 * lam
    arr = AntennaArray.upa(
        n_h=2,
        n_v=1,
        d_h=d,
        d_v=d,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    # Elements are at offsets along some axis perpendicular to broadside.
    # For a direction along that axis, phase difference = k0 * d = pi.
    offsets = arr.element_positions - arr.reference_position
    # Pick a direction along the first offset
    direction = offsets[1] - offsets[0]
    direction /= np.linalg.norm(direction)
    a = arr.steering_vector(direction, freq_hz)
    # Phase difference between elements should be k0 * d = pi
    phase_diff = np.angle(a[1]) - np.angle(a[0])
    np.testing.assert_allclose(abs(phase_diff), np.pi, atol=1e-10)


def test_steering_matrix_shape():
    """Steering matrix has shape (N, M)."""
    from aegis.mimo.array import AntennaArray

    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    k_hat = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1.0]])
    A = arr.steering_matrix(k_hat, freq_hz=28e9)
    assert A.shape == (3, 16)
    assert A.dtype == complex


def test_steering_matrix_rows_match_vector():
    """Each row of steering_matrix matches a steering_vector call."""
    from aegis.mimo.array import AntennaArray

    arr = AntennaArray.upa(
        n_h=4,
        n_v=2,
        d_h=0.005,
        d_v=0.005,
        center=np.array([1.0, 2.0, 3.0]),
        broadside=np.array([0, 0, 1.0]),
    )
    rng = np.random.default_rng(42)
    k_hat = rng.standard_normal((5, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    freq_hz = 28e9

    A = arr.steering_matrix(k_hat, freq_hz)
    for i in range(5):
        a_i = arr.steering_vector(k_hat[i], freq_hz)
        np.testing.assert_allclose(A[i], a_i, atol=1e-14)
