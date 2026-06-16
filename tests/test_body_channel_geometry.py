"""The geometry / frequency split must equal the monolithic body channel.

compute_body_channel routes the ungated case (no Fock gate, no distal shadow)
through precompute_body_channel_geometry + body_channel_from_geometry so a
frequency sweep can hoist the geometry. The split is the same operations
factored, so it must reproduce the monolithic build bit-for-bit; the studio
multi-frequency precompute relies on that.
"""

import numpy as np
import pytest

from aegis.coherent.body_channel import (
    body_channel_from_geometry,
    compute_body_channel,
    precompute_body_channel_geometry,
)
from aegis.tissue.dielectric import skin_props


def _rays(n_paths=400, n_tri=120, n_elements=16, seed=0):
    rng = np.random.default_rng(seed)
    # Triangles roughly facing +z, centroids in a small slab.
    normals = rng.normal(size=(n_tri, 3))
    normals[:, 2] = np.abs(normals[:, 2]) + 0.3
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    centroids = rng.normal(size=(n_tri, 3)) * 0.2
    # Arrivals from above, but a few back-facing so the mu <= 0 gate is exercised.
    k = rng.normal(size=(n_paths, 3))
    k[:, 2] = -np.abs(k[:, 2]) - 0.1
    k[: n_paths // 10, 2] *= -1.0  # flip a tenth to back-facing
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    psi = (rng.normal(size=(n_paths, 3)) + 1j * rng.normal(size=(n_paths, 3))) * 0.05
    element_index = rng.integers(0, n_elements, size=n_paths).astype(np.int64)
    return normals, centroids, k, psi, element_index, n_elements


def test_split_matches_monolithic_bit_for_bit():
    normals, centroids, k, psi, elem, m = _rays()
    n_tilde, sigma = skin_props(28)
    freq = 28e9

    g_full = np.asarray(compute_body_channel(normals, centroids, k, psi, elem, n_tilde, sigma, freq, m))

    geom = precompute_body_channel_geometry(normals, centroids, k, psi, elem, m)
    g_split = np.asarray(body_channel_from_geometry(geom, n_tilde, sigma, freq))

    # Same operations, just factored: require exact equality, not approximate.
    assert np.array_equal(g_full, g_split)


def test_geometry_reused_across_frequencies():
    normals, centroids, k, psi, elem, m = _rays(seed=3)
    geom = precompute_body_channel_geometry(normals, centroids, k, psi, elem, m)

    for freq_ghz in (10, 28):
        n_tilde, sigma = skin_props(freq_ghz)
        freq = freq_ghz * 1e9
        g_direct = np.asarray(compute_body_channel(normals, centroids, k, psi, elem, n_tilde, sigma, freq, m))
        g_cached = np.asarray(body_channel_from_geometry(geom, n_tilde, sigma, freq))
        assert np.array_equal(g_direct, g_cached)


def test_precompute_validates_element_index():
    normals, centroids, k, psi, elem, m = _rays()
    elem[0] = m  # out of [0, m)
    with pytest.raises(ValueError, match="element_index"):
        precompute_body_channel_geometry(normals, centroids, k, psi, elem, m)
