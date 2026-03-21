"""Smoke tests for JAX differentiability through dosimetry kernels."""

import numpy as np
import pytest

from aegis._array_backend import JAX_AVAILABLE

pytestmark = pytest.mark.skipif(not JAX_AVAILABLE, reason="JAX not installed")


def test_level2_grad_wrt_power():
    """Gradient of total S_ab w.r.t. per-path power flows through level 2."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level2_geometric import level2_geometric

    normals = jnp.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0]])
    T0 = 0.5

    def loss(power):
        sab = level2_geometric(normals, k_hat, power, T0)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)

    # Gradient must be finite and nonzero for the front-facing triangle
    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_level3_grad_wrt_power():
    """Gradient flows through level 3 (Fresnel)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level3_fresnel import level3_fresnel
    from aegis.tissue.fresnel import n_complex

    n_tilde = n_complex(10.0, 1.0, 28e9)
    normals = jnp.array([[0.0, 0.0, 1.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0]])

    def loss(power):
        sab = level3_fresnel(normals, k_hat, power, n_tilde)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)

    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_level2_grad_matches_finite_diff():
    """JAX grad matches finite-difference approximation for level 2."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level2_geometric import level2_geometric

    normals = jnp.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0], [0.0, -1.0, 0.0]])
    T0 = 0.6

    def loss(power):
        sab = level2_geometric(normals, k_hat, power, T0)
        return jnp.sum(sab)

    power = jnp.array([5.0, 3.0])
    jax_grad = jax.grad(loss)(power)

    # Finite difference
    eps = 1e-5
    fd_grad = np.zeros(2)
    for i in range(2):
        p_plus = power.at[i].set(power[i] + eps)
        p_minus = power.at[i].set(power[i] - eps)
        fd_grad[i] = (float(loss(p_plus)) - float(loss(p_minus))) / (2 * eps)

    np.testing.assert_allclose(np.asarray(jax_grad), fd_grad, rtol=1e-4)


def test_level0_grad_wrt_power():
    """Gradient flows through level 0 (worst-case bound)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level0_bound import level0_bound

    def loss(power):
        sab, _ = level0_bound(1.0, 0.5, 2.0, power, 0.5, 10)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)
    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_level4_grad_wrt_power():
    """Gradient flows through level 4 (polarisation)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level4_polarisation import level4_polarisation
    from aegis.tissue.fresnel import n_complex

    n_tilde = n_complex(10.0, 1.0, 28e9)
    normals = jnp.array([[0.0, 0.0, 1.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0]])

    def loss(power):
        sab = level4_polarisation(normals, k_hat, power, n_tilde, q=0.3)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)
    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_level5_grad_wrt_power():
    """Gradient flows through level 5 (curvature)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level5_curvature import level5_curvature
    from aegis.tissue.fresnel import n_complex

    n_tilde = n_complex(10.0, 1.0, 28e9)
    normals = jnp.array([[0.0, 0.0, 1.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0]])
    curvature_H = jnp.array([5.0])

    def loss(power):
        sab = level5_curvature(normals, k_hat, power, n_tilde, 0.5, curvature_H, 28e9)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)
    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_level6_grad_wrt_power():
    """Gradient flows through level 6 (diffraction/GELU)."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level6_diffraction import level6_diffraction
    from aegis.tissue.fresnel import n_complex

    n_tilde = n_complex(10.0, 1.0, 28e9)
    normals = jnp.array([[0.0, 0.0, 1.0]])
    k_hat = jnp.array([[0.0, 0.0, -1.0]])
    curvature_H = jnp.array([5.0])

    def loss(power):
        sab = level6_diffraction(normals, k_hat, power, n_tilde, 0.5, curvature_H, 28e9)
        return jnp.sum(sab)

    power = jnp.array([10.0])
    grad = jax.grad(loss)(power)
    assert jnp.all(jnp.isfinite(grad))
    assert float(grad[0]) > 0.0


def test_coherent_sab_grad_wrt_x():
    """Gradient of ||G_tilde @ x||^2 w.r.t. complex precoder x."""
    import jax
    import jax.numpy as jnp

    from aegis.optim import coherent_sab

    M, M_ant = 4, 3
    rng = np.random.default_rng(42)
    G_tilde = jnp.array(rng.standard_normal((M, 3, M_ant)) + 1j * rng.standard_normal((M, 3, M_ant)))

    def loss(x):
        return jnp.sum(coherent_sab(G_tilde, x))

    x = jnp.array(rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant))
    grad = jax.grad(loss)(x)
    assert grad.shape == (M_ant,)
    assert jnp.all(jnp.isfinite(grad))
    assert float(jnp.max(jnp.abs(grad))) > 0.0


def test_coherent_sab_grad_matches_finite_diff():
    """Coherent sab JAX grad matches finite-difference for real perturbations."""
    import jax
    import jax.numpy as jnp

    from aegis.optim import coherent_sab

    M, M_ant = 3, 2
    rng = np.random.default_rng(123)
    G_tilde = jnp.array(rng.standard_normal((M, 3, M_ant)) + 1j * rng.standard_normal((M, 3, M_ant)))
    x0 = jnp.array([1.0 + 0.5j, 0.3 - 0.2j])

    # Parameterise as real vector [re, im] for clean finite-diff
    def loss_real(x_flat):
        x = x_flat[:M_ant] + 1j * x_flat[M_ant:]
        return jnp.sum(coherent_sab(G_tilde, x))

    x_flat = jnp.concatenate([jnp.real(x0), jnp.imag(x0)])
    jax_grad = jax.grad(loss_real)(x_flat)

    eps = 1e-6
    fd_grad = np.zeros(2 * M_ant)
    for i in range(2 * M_ant):
        p = x_flat.at[i].set(x_flat[i] + eps)
        m = x_flat.at[i].set(x_flat[i] - eps)
        fd_grad[i] = (float(loss_real(p)) - float(loss_real(m))) / (2 * eps)

    np.testing.assert_allclose(np.asarray(jax_grad), fd_grad, rtol=1e-4)


def test_end_to_end_antenna_placement():
    """Gradient of exposure w.r.t. antenna position through synthetic trace."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level2_geometric import level2_geometric

    normals = jnp.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    body_center = jnp.array([0.0, 0.0, 0.0])
    T0 = 0.5

    def loss(antenna_pos):
        direction = body_center - antenna_pos
        d = jnp.linalg.norm(direction)
        k_hat = (direction / d)[None, :]
        power = jnp.array([1.0 / (4 * jnp.pi * d**2)])
        sab = level2_geometric(normals, k_hat, power, T0)
        return jnp.sum(sab)

    antenna_pos = jnp.array([0.0, 0.0, 2.0])
    grad = jax.grad(loss)(antenna_pos)
    assert jnp.all(jnp.isfinite(grad))
    # Antenna is above body at z=2; moving it away (increasing z) decreases
    # exposure, so gradient in z is negative.
    assert float(grad[2]) < 0.0


def test_end_to_end_grad_matches_finite_diff():
    """End-to-end JAX grad matches finite difference for antenna placement."""
    import jax
    import jax.numpy as jnp

    from aegis.kernels.level2_geometric import level2_geometric

    normals = jnp.array([[0.0, 0.0, 1.0]])
    T0 = 0.5

    def loss(antenna_pos):
        direction = jnp.array([0.0, 0.0, 0.0]) - antenna_pos
        d = jnp.linalg.norm(direction)
        k_hat = (direction / d)[None, :]
        power = jnp.array([1.0 / (4 * jnp.pi * d**2)])
        return jnp.sum(level2_geometric(normals, k_hat, power, T0))

    pos = jnp.array([0.0, 0.0, 2.0])
    jax_grad = jax.grad(loss)(pos)

    eps = 1e-5
    fd_grad = np.zeros(3)
    for i in range(3):
        p = pos.at[i].set(pos[i] + eps)
        m = pos.at[i].set(pos[i] - eps)
        fd_grad[i] = (float(loss(p)) - float(loss(m))) / (2 * eps)

    np.testing.assert_allclose(np.asarray(jax_grad), fd_grad, rtol=1e-3)
