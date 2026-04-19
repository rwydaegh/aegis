"""Metamorphic relation: coherent Sab is a pure quadratic form in x.

Monograph: Theorem 4.1 (thm:coherent-law), Eq. 4.9:

    Sab(r) = || G_tilde(r) @ x ||^2

Two consequences follow immediately from the norm-squared structure:

    1.  Sab(r; alpha * x) = |alpha|^2 * Sab(r; x) for any complex alpha.
    2.  Sab(r; exp(i*phi) * x) = Sab(r; x) for any real phi.

Both hold exactly -- they are algebraic identities, not approximations.
Any deviation beyond FP round-off is a bug in the coherent kernel
(likely a missing abs() or a phase leak that breaks the quadratic form).
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import make_icosahedron
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.constants import Z_0
from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ


def _make_coherent_paths(seed: int, n_paths: int = 4, n_elements: int = 3) -> PropagationPaths:
    """Build a PropagationPaths with complex psi and multiple elements.

    The precise geometry does not matter for these tests: any valid
    coherent setup exercises the quadratic form.
    """
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((n_paths, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    amplitude = rng.uniform(0.1, 1.0, size=n_paths)

    psi = np.zeros((n_paths, 3), dtype=complex)
    for i in range(n_paths):
        ref = np.array([1.0, 0.0, 0.0]) if abs(k_hat[i, 0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e = np.cross(k_hat[i], ref)
        e /= np.linalg.norm(e)
        # Add a random complex phase so psi is genuinely complex, not purely real.
        psi[i] = amplitude[i] * np.sqrt(2 * Z_0) * e * np.exp(1j * rng.uniform(0, 2 * np.pi))

    element_index = rng.integers(0, n_elements, size=n_paths).astype(np.intp)
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_index,
        delay=np.zeros(n_paths),
        is_los=np.ones(n_paths, dtype=bool),
    )


@pytest.mark.parametrize("alpha", [0.5, 1.0, 2.0, 3.7])
@pytest.mark.parametrize("seed", [0, 17, 42])
def test_coherent_scaling_real_positive(alpha: float, seed: int) -> None:
    """Sab(alpha * x) = alpha^2 * Sab(x) for real positive alpha.

    The simplest shape of the metamorphic relation: scale the precoder,
    check that sab scales quadratically.
    """
    body = make_icosahedron()
    paths = _make_coherent_paths(seed, n_paths=5, n_elements=3)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(seed + 100)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)

    sab_ref = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=x))
    sab_scaled = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=alpha * x))

    np.testing.assert_allclose(np.asarray(sab_scaled), alpha**2 * np.asarray(sab_ref), rtol=1e-12, atol=1e-14)


@pytest.mark.parametrize("alpha_mag", [0.3, 1.0, 2.5])
@pytest.mark.parametrize("alpha_phase", [0.0, 0.7, np.pi / 3, np.pi])
@pytest.mark.parametrize("seed", [0, 7])
def test_coherent_scaling_complex(alpha_mag: float, alpha_phase: float, seed: int) -> None:
    """Sab(alpha * x) = |alpha|^2 * Sab(x) for complex alpha.

    Phase of alpha must not affect sab (that is part B, global-phase
    invariance). Magnitude squared is the only relevant quantity.
    """
    body = make_icosahedron()
    paths = _make_coherent_paths(seed, n_paths=4, n_elements=2)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(seed + 200)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)
    alpha = alpha_mag * np.exp(1j * alpha_phase)

    sab_ref = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=x))
    sab_scaled = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=alpha * x))

    np.testing.assert_allclose(np.asarray(sab_scaled), abs(alpha) ** 2 * np.asarray(sab_ref), rtol=1e-12, atol=1e-14)


@given(
    alpha_real=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=25, deadline=5000)
def test_coherent_scaling_hypothesis(alpha_real: float, seed: int) -> None:
    """Hypothesis sweep: Sab(alpha * x) = alpha^2 * Sab(x) for real alpha > 0."""
    body = make_icosahedron()
    paths = _make_coherent_paths(seed, n_paths=4, n_elements=2)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(seed)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)

    sab_ref = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=x))
    sab_scaled = engine.compute_sab(body, paths, level=7, precoder=Precoder(x=alpha_real * x))

    np.testing.assert_allclose(np.asarray(sab_scaled), alpha_real**2 * np.asarray(sab_ref), rtol=1e-10, atol=1e-14)
