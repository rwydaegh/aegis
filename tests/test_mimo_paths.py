"""Tests for per-element path expansion."""

import numpy as np

from aegis.constants import C_0
from aegis.paths import PropagationPaths


def _make_array_and_paths():
    """Helper: 2-element array and 3 center paths at 28 GHz."""
    from aegis.mimo.array import AntennaArray

    freq_hz = 28e9
    lam = C_0 / freq_hz
    arr = AntennaArray.upa(
        n_h=2,
        n_v=1,
        d_h=0.5 * lam,
        d_v=0.5 * lam,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    center_paths = PropagationPaths.from_powers(
        k_hat=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1.0]]),
        power=np.array([1.0, 0.5, 0.3]),
    )
    return arr, center_paths, freq_hz


def test_expand_total_paths():
    """Output has N * M total paths."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    expanded = expand_paths_to_array(paths, arr, freq)
    assert expanded.n_paths == paths.n_paths * arr.n_elements


def test_expand_n_elements():
    """Output n_elements matches the array."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    expanded = expand_paths_to_array(paths, arr, freq)
    assert expanded.n_elements == arr.n_elements


def test_expand_element_indices():
    """Each element j has exactly N paths with element_index == j."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    expanded = expand_paths_to_array(paths, arr, freq)
    for j in range(arr.n_elements):
        count = np.sum(expanded.element_index == j)
        assert count == paths.n_paths


def test_expand_k_hat_replicated():
    """k_hat directions are replicated M times."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    expanded = expand_paths_to_array(paths, arr, freq)
    M = arr.n_elements
    for j in range(M):
        mask = expanded.element_index == j
        np.testing.assert_allclose(expanded.k_hat[mask], paths.k_hat)


def test_expand_phase_steering():
    """Per-element psi includes the phase advance exp(+i*k0 * k_hat . offset_j)."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    k0 = 2 * np.pi * freq / C_0
    offsets = arr.element_positions - arr.reference_position
    expanded = expand_paths_to_array(paths, arr, freq)

    for j in range(arr.n_elements):
        mask = expanded.element_index == j
        psi_j = expanded.psi[mask]
        phase = np.exp(1j * k0 * (paths.k_hat @ offsets[j]))
        expected = paths.psi * phase[:, None]
        np.testing.assert_allclose(psi_j, expected, atol=1e-14)


def test_expand_single_element_identity():
    """Single-element array at center returns paths with same psi."""
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.array_paths import expand_paths_to_array

    arr = AntennaArray.upa(
        n_h=1,
        n_v=1,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([1.0]),
    )
    expanded = expand_paths_to_array(paths, arr, freq_hz=28e9)
    assert expanded.n_paths == 1
    np.testing.assert_allclose(expanded.psi, paths.psi, atol=1e-14)


def test_expand_power_magnitude_preserved():
    """Per-path |psi|^2 is preserved (phase steering doesn't change magnitude)."""
    from aegis.mimo.array_paths import expand_paths_to_array

    arr, paths, freq = _make_array_and_paths()
    expanded = expand_paths_to_array(paths, arr, freq)

    original_power = np.sum(np.abs(paths.psi) ** 2, axis=1)
    for j in range(arr.n_elements):
        mask = expanded.element_index == j
        expanded_power = np.sum(np.abs(expanded.psi[mask]) ** 2, axis=1)
        np.testing.assert_allclose(expanded_power, original_power, atol=1e-14)
