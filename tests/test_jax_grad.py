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
