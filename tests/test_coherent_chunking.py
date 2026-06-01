"""The triangle-chunked level-7 kernel must equal the single-block result.

level7_coherent processes triangles in blocks to bound the (B, N, 3) body-channel
intermediate (the GPU memory peak at full phantom resolution). Q is a triangle-sum
and sab is per-triangle, so blocking is exact up to floating-point summation order.
This test forces one triangle per block and checks it matches the single-block path.
"""

import sys

import numpy as np

import aegis.kernels.level7_coherent  # noqa: F401  (ensure submodule is imported)
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# The kernels package re-exports the function under the submodule's name, so
# getattr-based imports return the function. Grab the real module via sys.modules.
L7 = sys.modules["aegis.kernels.level7_coherent"]


def _setup(n_tri=300, seed=0):
    rng = np.random.default_rng(seed)
    side = np.sqrt(n_tri * 1e-4)
    s = np.sqrt(1e-4 * 2)
    centroids = np.column_stack([rng.uniform(0, side, n_tri), rng.uniform(0, side, n_tri), np.zeros(n_tri)])
    normals = np.tile([0.0, 0.0, 1.0], (n_tri, 1))
    areas = 0.5 * s * s * np.ones(n_tri)

    freq = 28e9
    positions = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0], [0.0, 0.05, 1.0]])
    array = AntennaArray(element_positions=positions, element_pattern="isotropic")
    n_center = 4
    k = rng.standard_normal((n_center, 3))
    k[:, 2] = -np.abs(k[:, 2]) - 0.2
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    psi = (rng.standard_normal((n_center, 3)) + 1j * rng.standard_normal((n_center, 3))) * 0.05
    center = PropagationPaths(
        k_hat=k,
        psi=psi,
        element_index=np.zeros(n_center, np.intp),
        delay=np.zeros(n_center),
        is_los=np.zeros(n_center, bool),
    )
    exp = expand_paths_to_array(center, array, freq)
    x = (rng.standard_normal(array.n_elements) + 1j * rng.standard_normal(array.n_elements)).astype(complex)
    h = (rng.standard_normal(array.n_elements) + 1j * rng.standard_normal(array.n_elements)).astype(complex)
    return {
        "normals": normals,
        "centroids": centroids,
        "areas": areas,
        "k_hat": exp.k_hat,
        "psi": exp.psi,
        "element_index": exp.element_index,
        "x": x,
        "n_tilde": SKIN_28GHZ.n_complex,
        "sigma": SKIN_28GHZ.sigma,
        "freq_hz": freq,
        "n_elements": array.n_elements,
        "h": h,
    }


def test_chunked_matches_single_block(monkeypatch):
    kw = _setup()
    # default budget is >> M*N, so this is a single block (the original path)
    sab1, q1, ev1, rho1 = L7.level7_coherent(**kw)
    # force one triangle per block: exercises the accumulation across many blocks
    monkeypatch.setattr(L7, "_TRI_CHUNK_MN", 1)
    sab_n, q_n, ev_n, rho_n = L7.level7_coherent(**kw)

    np.testing.assert_allclose(np.asarray(sab_n), np.asarray(sab1), rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(np.asarray(q_n), np.asarray(q1), rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(np.asarray(ev_n), np.asarray(ev1), rtol=1e-8, atol=1e-12)
    assert abs(float(rho_n) - float(rho1)) < 1e-9


def test_triangle_chunk_bounds():
    assert L7._triangle_chunk(100, 0) == 100  # no paths -> all triangles in one block
    assert L7._triangle_chunk(100, 10) >= 1
    assert L7._triangle_chunk(10, 10**9) == 1  # huge path count -> one triangle per block
