"""Metamorphic relation: global phase invariance of the coherent precoder.

Monograph: Theorem 4.1 (thm:coherent-law), Eq. 4.9:

    Sab(r) = || G_tilde(r) @ x ||^2.

Multiplying x by a unit-modulus complex scalar e^{i*phi} leaves the
norm-squared unchanged:

    Sab(r; e^{i*phi} * x) = Sab(r; x)   for any real phi.

This is an algebraic identity (a scalar factors out of a norm-squared).
Any deviation is a bug -- most likely a place where the kernel uses a
real part or magnitude inconsistently, or where an antenna-element
phase is referenced against something outside the precoder.
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


def _build_paths(seed: int, n_paths: int = 5, n_elements: int = 3) -> PropagationPaths:
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((n_paths, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    amplitude = rng.uniform(0.2, 1.0, size=n_paths)

    psi = np.zeros((n_paths, 3), dtype=complex)
    for i in range(n_paths):
        ref = np.array([1.0, 0.0, 0.0]) if abs(k_hat[i, 0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        e = np.cross(k_hat[i], ref)
        e /= np.linalg.norm(e)
        psi[i] = amplitude[i] * np.sqrt(2 * Z_0) * e * np.exp(1j * rng.uniform(0, 2 * np.pi))

    element_index = rng.integers(0, n_elements, size=n_paths).astype(np.intp)
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_index,
        delay=np.zeros(n_paths),
        is_los=np.ones(n_paths, dtype=bool),
    )


@pytest.mark.parametrize(
    "phi",
    [0.0, 0.17, np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2, 2 * np.pi, -1.3],
    ids=lambda v: f"phi={v:.3f}",
)
@pytest.mark.parametrize("seed", [0, 11, 42])
def test_global_phase_invariance(phi: float, seed: int) -> None:
    """Multiplying x by e^{i*phi} leaves per-triangle sab unchanged."""
    body = make_icosahedron()
    paths = _build_paths(seed)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(seed + 1000)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)

    sab_ref = np.asarray(engine.compute_sab(body, paths, level=7, precoder=Precoder(x=x)))
    sab_rotated = np.asarray(engine.compute_sab(body, paths, level=7, precoder=Precoder(x=np.exp(1j * phi) * x)))

    np.testing.assert_allclose(sab_rotated, sab_ref, rtol=1e-12, atol=1e-14)


@given(
    phi=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=30, deadline=5000)
def test_global_phase_invariance_hypothesis(phi: float, seed: int) -> None:
    """Hypothesis sweep over phi across several periods of the unit circle."""
    body = make_icosahedron()
    paths = _build_paths(seed, n_paths=4, n_elements=2)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(seed)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)

    sab_ref = np.asarray(engine.compute_sab(body, paths, level=7, precoder=Precoder(x=x)))
    sab_rotated = np.asarray(engine.compute_sab(body, paths, level=7, precoder=Precoder(x=np.exp(1j * phi) * x)))

    np.testing.assert_allclose(sab_rotated, sab_ref, rtol=1e-11, atol=1e-14)


def test_exposure_operator_invariant_under_global_phase() -> None:
    """x^H Q x must equal (e^{i*phi} x)^H Q (e^{i*phi} x) exactly.

    Q is Hermitian and phi cancels in the conjugate: this is a sanity
    check on the exposure-operator side of the same relation.
    """
    body = make_icosahedron()
    paths = _build_paths(seed=5)
    engine = DosimetryEngine(SKIN_28GHZ)

    rng = np.random.default_rng(5)
    x = rng.standard_normal(paths.n_elements) + 1j * rng.standard_normal(paths.n_elements)
    phi = 1.234

    res = engine.compute(body, paths, level=7, precoder=Precoder(x=x))
    Q = res.Q

    p_abs_ref = float(np.real(x.conj() @ Q @ x))
    x_rot = np.exp(1j * phi) * x
    p_abs_rot = float(np.real(x_rot.conj() @ Q @ x_rot))

    assert abs(p_abs_rot - p_abs_ref) <= 1e-12 * max(abs(p_abs_ref), 1.0)
