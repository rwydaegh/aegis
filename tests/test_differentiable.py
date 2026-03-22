"""Verify the spatial kernel is differentiable via JAX (when available)."""

import numpy as np
import pytest

from aegis._array_backend import JAX_AVAILABLE
from aegis.tissue.dielectric import SKIN_28GHZ

pytestmark = pytest.mark.skipif(not JAX_AVAILABLE, reason="JAX not installed")


def _make_ico():
    """Inline icosahedron (can't import conftest helpers outside pytest easily)."""
    phi = (1 + np.sqrt(5)) / 2
    verts_raw = np.array(
        [
            [-1, phi, 0],
            [1, phi, 0],
            [-1, -phi, 0],
            [1, -phi, 0],
            [0, -1, phi],
            [0, 1, phi],
            [0, -1, -phi],
            [0, 1, -phi],
            [phi, 0, -1],
            [phi, 0, 1],
            [-phi, 0, -1],
            [-phi, 0, 1],
        ],
        dtype=float,
    )
    verts_raw /= np.linalg.norm(verts_raw[0])
    verts_raw *= 0.1
    faces = [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),
        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),
        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),
        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ]
    from aegis.geometry.mesh import BodyMesh

    n = len(faces)
    vertices = np.zeros((n, 3, 3))
    for i, (a, b, c) in enumerate(faces):
        vertices[i] = [verts_raw[a], verts_raw[b], verts_raw[c]]
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    norms_v = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / norms_v
    centroids = np.mean(vertices, axis=1)
    flip = np.sum(normals * centroids, axis=1) < 0
    normals[flip] *= -1
    areas = 0.5 * norms_v[:, 0]
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="ico")


@pytest.fixture
def setup():
    body = _make_ico()
    k_hat = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    power = np.array([5.0, 3.0])
    return body, k_hat, power


def test_spatial_kernel_jit(setup):
    """spatial_kernel runs under jax.jit without error."""
    import jax.numpy as jnp

    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup

    sab = spatial_kernel(
        jnp.array(body.normals),
        jnp.array(k_hat),
        jnp.array(power),
        SKIN_28GHZ.n_complex,
        SKIN_28GHZ.T0,
        SKIN_28GHZ.freq_hz,
    )
    assert sab.shape == (body.n_triangles,)
    assert jnp.all(jnp.isfinite(sab))


def test_spatial_kernel_grad_wrt_power(setup):
    """Gradient of total P_abs w.r.t. path powers exists and is finite."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup
    normals_j = jnp.array(body.normals)
    k_hat_j = jnp.array(k_hat)
    areas_j = jnp.array(body.areas)

    def p_abs(power_jax):
        sab = spatial_kernel(
            normals_j,
            k_hat_j,
            power_jax,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.T0,
            SKIN_28GHZ.freq_hz,
        )
        return jnp.sum(sab * areas_j)

    grad_fn = jax.grad(p_abs)
    g = grad_fn(jnp.array(power))
    assert g.shape == (2,)
    assert jnp.all(jnp.isfinite(g))
    assert jnp.all(g >= 0)


def test_spatial_kernel_grad_with_all_corrections(setup):
    """Gradient works with all corrections enabled (GELU is smooth)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.spatial import spatial_kernel

    body, k_hat, power = setup
    normals_j = jnp.array(body.normals)
    k_hat_j = jnp.array(k_hat)
    areas_j = jnp.array(body.areas)
    H = jnp.full(body.n_triangles, 10.0)

    def p_abs(power_jax):
        sab = spatial_kernel(
            normals_j,
            k_hat_j,
            power_jax,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.T0,
            SKIN_28GHZ.freq_hz,
            polarisation=True,
            q=0.3,
            curvature=True,
            diffraction=True,
            curvature_H=H,
        )
        return jnp.sum(sab * areas_j)

    grad_fn = jax.grad(p_abs)
    g = grad_fn(jnp.array(power))
    assert jnp.all(jnp.isfinite(g))
