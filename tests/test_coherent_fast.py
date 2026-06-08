"""Equivalence tests for the factored / vmap fast path and translation phasor.

Anchors the optimisation work in `coherent/_fast.py` and
`coherent/translation.py` against the reference `compute_body_channel`
on element-expanded paths and against re-evaluation under translation.

These tests are CPU-friendly: the JAX kernels are imported eagerly here,
the meshes are small, and tolerances are loose enough to be backend-agnostic.
"""

from __future__ import annotations

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jnp = jax.numpy
jax.config.update("jax_enable_x64", True)

# The fast / translation kernels reuse `compute_fresnel_operator`, which routes
# through the project array-backend shim `aegis._array_backend.xp`. When that
# shim resolves to numpy, calls like `xp.asarray(mu, dtype=complex)` cannot
# accept a JAX tracer, so vmap traces blow up with `TracerArrayConversionError`.
# This module-level skip keeps the suite green when `AEGIS_ARRAY_BACKEND` isn't
# set; the canonical run is `AEGIS_ARRAY_BACKEND=jax pytest tests/test_coherent_fast.py`.
from aegis._array_backend import xp as _xp  # noqa: E402

if _xp is not jnp:
    pytest.skip("Fast / translation tests require AEGIS_ARRAY_BACKEND=jax", allow_module_level=True)

from aegis.coherent._fast import (  # noqa: E402
    compute_body_channel_factored_jax,
    compute_q_batch_vmap,
    compute_q_for_body,
)
from aegis.coherent.body_channel import (  # noqa: E402
    compute_body_channel,
    compute_body_channel_factored,
)
from aegis.coherent.exposure_operator import compute_exposure_operator  # noqa: E402
from aegis.coherent.translation import (  # noqa: E402
    compute_static_path_gram,
    q_translate,
    q_translate_batch,
    translation_phasor,
)
from aegis.mimo.array import AntennaArray  # noqa: E402
from aegis.mimo.array_paths import expand_paths_to_array  # noqa: E402
from aegis.paths import PropagationPaths  # noqa: E402
from aegis.tissue.dielectric import SKIN_28GHZ  # noqa: E402

ATOL = 1e-9
RTOL = 1e-6


def _flat_mesh(n=80, seed=42):
    rng = np.random.default_rng(seed)
    side = np.sqrt(n * 1e-4)
    s = np.sqrt(1e-4 * 2)
    cx = rng.uniform(0, side, n)
    cy = rng.uniform(0, side, n)
    z = np.zeros(n)
    centroids = np.column_stack([cx, cy, z])
    normals = np.tile([0.0, 0.0, 1.0], (n, 1))
    areas = 0.5 * s * s * np.ones(n)
    return normals, centroids, areas


def _scenario(seed=0):
    """Build a small two-element-array, three-center-direction scenario."""
    rng = np.random.default_rng(seed)
    freq_hz = 28e9
    n_tilde = SKIN_28GHZ.n_complex
    sigma = SKIN_28GHZ.sigma

    positions = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0], [0.0, 0.05, 1.0]])
    array = AntennaArray(element_positions=positions, element_pattern="isotropic")

    N_center = 4
    k_raw = rng.standard_normal((N_center, 3))
    k_raw[:, 2] = -np.abs(k_raw[:, 2]) - 0.2  # downward into +z normals
    k_hat = k_raw / np.linalg.norm(k_raw, axis=1, keepdims=True)
    psi = (rng.standard_normal((N_center, 3)) + 1j * rng.standard_normal((N_center, 3))) * 0.05

    center_paths = PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.zeros(N_center, dtype=np.intp),
        delay=np.zeros(N_center),
        is_los=np.zeros(N_center, dtype=bool),
    )
    expanded = expand_paths_to_array(center_paths, array, freq_hz)
    offsets = array.element_positions - array.reference_position

    # The factored path expects the element-pattern gain folded into center_psi.
    # expand_paths_to_array does this internally; replicate for the factored side.
    gain = array.element_gain(center_paths.k_hat)
    center_psi_gained = center_paths.psi * gain[:, None]

    return {
        "array": array,
        "freq_hz": freq_hz,
        "n_tilde": n_tilde,
        "sigma": sigma,
        "center_paths": center_paths,
        "expanded": expanded,
        "offsets": offsets,
        "center_psi_gained": center_psi_gained,
        "n_elements": array.n_elements,
    }


def test_factored_jax_matches_compute_body_channel():
    """`compute_body_channel_factored_jax` must agree with the reference path."""
    normals, centroids, _ = _flat_mesh()
    sc = _scenario()

    G_ref = compute_body_channel(
        normals=normals,
        centroids=centroids,
        k_hat=sc["expanded"].k_hat,
        psi=sc["expanded"].psi,
        element_index=sc["expanded"].element_index,
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
        n_elements=sc["n_elements"],
    )

    G_fast = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )

    np.testing.assert_allclose(np.asarray(G_fast), np.asarray(G_ref), atol=ATOL, rtol=RTOL)


def test_vmap_q_matches_per_body():
    """Vmapped Q over a 3-body batch must match per-body Q evaluations."""
    normals, centroids, areas = _flat_mesh()
    sc = _scenario()

    rng = np.random.default_rng(7)
    n_bodies = 3
    offsets_per_body = rng.normal(scale=2.0, size=(n_bodies, 3))

    normals_b = np.broadcast_to(normals, (n_bodies, *normals.shape)).copy()
    areas_b = np.broadcast_to(areas, (n_bodies, *areas.shape)).copy()
    centroids_b = np.stack([centroids + offsets_per_body[b] for b in range(n_bodies)])

    # Same paths across bodies.
    k_b = np.broadcast_to(sc["center_paths"].k_hat, (n_bodies, *sc["center_paths"].k_hat.shape)).copy()
    psi_b = np.broadcast_to(sc["center_psi_gained"], (n_bodies, *sc["center_psi_gained"].shape)).copy()

    Q_b = compute_q_batch_vmap(
        jnp.asarray(normals_b),
        jnp.asarray(centroids_b),
        jnp.asarray(areas_b),
        jnp.asarray(k_b),
        jnp.asarray(psi_b),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
    )

    for b in range(n_bodies):
        Q_one = compute_q_for_body(
            jnp.asarray(normals_b[b]),
            jnp.asarray(centroids_b[b]),
            jnp.asarray(areas_b[b]),
            jnp.asarray(k_b[b]),
            jnp.asarray(psi_b[b]),
            jnp.asarray(sc["offsets"]),
            sc["n_tilde"],
            sc["sigma"],
            sc["freq_hz"],
        )
        np.testing.assert_allclose(np.asarray(Q_b[b]), np.asarray(Q_one), atol=ATOL, rtol=RTOL)


def test_translation_phasor_matches_recompute():
    """`q_translate` must reproduce a from-scratch Q evaluation at the translated centroids."""
    normals, centroids, areas = _flat_mesh()
    sc = _scenario()

    delta_t = np.array([0.42, -0.17, 0.05])

    # Reference: rebuild Q at centroids + delta_t.
    G_ref = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids + delta_t),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    Q_ref = compute_exposure_operator(G_ref, jnp.asarray(areas))

    # Cache-and-translate path.
    M_static = compute_static_path_gram(
        normals=jnp.asarray(normals),
        centroids_0=jnp.asarray(centroids),
        areas=jnp.asarray(areas),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    phi = translation_phasor(jnp.asarray(sc["center_paths"].k_hat), jnp.asarray(delta_t), sc["freq_hz"])
    Q_translated = q_translate(M_static, phi)

    np.testing.assert_allclose(np.asarray(Q_translated), np.asarray(Q_ref), atol=ATOL, rtol=RTOL)


def test_translation_zero_recovers_static():
    """At Δt = 0 the translation refresh must reproduce Q at the cache pose."""
    normals, centroids, areas = _flat_mesh()
    sc = _scenario()

    Q0 = compute_q_for_body(
        jnp.asarray(normals),
        jnp.asarray(centroids),
        jnp.asarray(areas),
        jnp.asarray(sc["center_paths"].k_hat),
        jnp.asarray(sc["center_psi_gained"]),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
    )

    M_static = compute_static_path_gram(
        normals=jnp.asarray(normals),
        centroids_0=jnp.asarray(centroids),
        areas=jnp.asarray(areas),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    phi = translation_phasor(jnp.asarray(sc["center_paths"].k_hat), jnp.zeros(3), sc["freq_hz"])
    Q_zero = q_translate(M_static, phi)

    np.testing.assert_allclose(np.asarray(Q_zero), np.asarray(Q0), atol=ATOL, rtol=RTOL)


def test_translation_batch_matches_per_body():
    """`q_translate_batch` agrees with single-body `q_translate` per element."""
    normals, centroids, areas = _flat_mesh()
    sc = _scenario()

    rng = np.random.default_rng(11)
    n_bodies = 3
    deltas = rng.normal(scale=0.5, size=(n_bodies, 3))

    # Same M_static for all bodies in this synthetic check.
    M_static = compute_static_path_gram(
        normals=jnp.asarray(normals),
        centroids_0=jnp.asarray(centroids),
        areas=jnp.asarray(areas),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    M_static_b = jnp.broadcast_to(M_static, (n_bodies, *M_static.shape))

    phi_b = jnp.stack(
        [translation_phasor(jnp.asarray(sc["center_paths"].k_hat), jnp.asarray(d), sc["freq_hz"]) for d in deltas]
    )

    Q_b = q_translate_batch(M_static_b, phi_b)

    for b in range(n_bodies):
        Q_one = q_translate(M_static, phi_b[b])
        np.testing.assert_allclose(np.asarray(Q_b[b]), np.asarray(Q_one), atol=ATOL, rtol=RTOL)


# ---------------------------------------------------------------------------
# Fock shadow gate parity (the _fast.py JAX twins vs the NumPy reference).
# ---------------------------------------------------------------------------


def _grazing_mesh(n=80, seed=4):
    """Flat patch with normals spread away from +z, so incidence vs the scenario's
    downward directions spans the grazing penumbra (gate materially active)."""
    rng = np.random.default_rng(seed)
    centroids = rng.uniform(-0.05, 0.05, (n, 3))
    centroids[:, 2] = 0.0
    nrm = rng.normal(0.0, 0.6, (n, 3))
    nrm[:, 2] = 1.0
    normals = nrm / np.linalg.norm(nrm, axis=1, keepdims=True)
    areas = np.full(n, 1e-4)
    return normals, centroids, areas


def test_fast_gate_off_bit_identical():
    """fock_R=None must reproduce the current ungated twin output bit-for-bit."""
    normals, centroids, areas = _grazing_mesh()
    sc = _scenario()

    common = dict(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    G_default = compute_body_channel_factored_jax(**common)
    G_none = compute_body_channel_factored_jax(**common, fock_R=None)
    # Bit-identical: the None branch must skip the gate entirely.
    np.testing.assert_array_equal(np.asarray(G_none), np.asarray(G_default))

    # Same through the Q twins (single body and vmap batch).
    Q_default = compute_q_for_body(
        jnp.asarray(normals),
        jnp.asarray(centroids),
        jnp.asarray(areas),
        jnp.asarray(sc["center_paths"].k_hat),
        jnp.asarray(sc["center_psi_gained"]),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
    )
    Q_none = compute_q_for_body(
        jnp.asarray(normals),
        jnp.asarray(centroids),
        jnp.asarray(areas),
        jnp.asarray(sc["center_paths"].k_hat),
        jnp.asarray(sc["center_psi_gained"]),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
        fock_R=None,
    )
    np.testing.assert_array_equal(np.asarray(Q_none), np.asarray(Q_default))


def _q_F_h_impedance(sc, R):
    """Representative impedance-Fock hard eigenvalue (matches engine fock_params)."""
    from aegis.kernels import fock

    eta = complex(1.0 / sc["n_tilde"])
    k0 = 2.0 * np.pi * sc["freq_hz"] / 3e8
    kR = float(np.clip(k0 * R, 4.0, 2048.0))
    return fock.fock_impedance_param(eta, kR, "hard")


@pytest.mark.parametrize("impedance", [False, True])
def test_fast_gate_matches_numpy_reference(impedance):
    """Gated JAX twin G_tilde and Q match the NumPy compute_body_channel_factored.

    Both run under the JAX x64 backend (the test module forces
    AEGIS_ARRAY_BACKEND=jax and jax_enable_x64), so the only divergence is
    summation order (einsum vs the numpy np.add.at scatter in the reference).
    rtol 1e-6 / atol 1e-9 absorbs that float64 round-off, matching the tolerance
    of the pre-existing factored-equivalence test.
    """
    normals, centroids, areas = _grazing_mesh()
    sc = _scenario()
    M = normals.shape[0]
    R = 0.03
    fock_R = np.full(M, R)
    q_F_h = _q_F_h_impedance(sc, R) if impedance else None

    # NumPy reference: factored channel with the gate (center-keyed fock_R).
    G_ref = compute_body_channel_factored(
        normals,
        centroids,
        sc["center_paths"].k_hat,
        sc["center_psi_gained"],
        sc["expanded"].psi,
        sc["expanded"].element_index,
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
        sc["n_elements"],
        fock_R=fock_R,
        q_F_s=None,
        q_F_h=q_F_h,
    )
    Q_ref = compute_exposure_operator(G_ref, jnp.asarray(areas))

    # JAX twin with the same gate.
    G_fast = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
        fock_R=jnp.asarray(fock_R),
        q_F_s=None,
        q_F_h=q_F_h,
    )
    Q_fast = compute_q_for_body(
        jnp.asarray(normals),
        jnp.asarray(centroids),
        jnp.asarray(areas),
        jnp.asarray(sc["center_paths"].k_hat),
        jnp.asarray(sc["center_psi_gained"]),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
        fock_R=jnp.asarray(fock_R),
        q_F_s=None,
        q_F_h=q_F_h,
    )

    np.testing.assert_allclose(np.asarray(G_fast), np.asarray(G_ref), atol=ATOL, rtol=RTOL)
    np.testing.assert_allclose(np.asarray(Q_fast), np.asarray(Q_ref), atol=ATOL, rtol=RTOL)

    # The gate must be materially active (otherwise this would pass trivially).
    G_ungated = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(sc["center_paths"].k_hat),
        center_psi=jnp.asarray(sc["center_psi_gained"]),
        array_offsets=jnp.asarray(sc["offsets"]),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    rel = np.linalg.norm(np.asarray(G_fast) - np.asarray(G_ungated)) / np.linalg.norm(np.asarray(G_ungated))
    assert rel > 1e-2

    # vmap batch traces the gate (q_F_h is a static Python scalar, not a tracer)
    # and matches the per-body Q.
    n_bodies = 3
    normals_b = np.broadcast_to(normals, (n_bodies, *normals.shape)).copy()
    centroids_b = np.broadcast_to(centroids, (n_bodies, *centroids.shape)).copy()
    areas_b = np.broadcast_to(areas, (n_bodies, *areas.shape)).copy()
    k_b = np.broadcast_to(sc["center_paths"].k_hat, (n_bodies, *sc["center_paths"].k_hat.shape)).copy()
    psi_b = np.broadcast_to(sc["center_psi_gained"], (n_bodies, *sc["center_psi_gained"].shape)).copy()
    fock_R_b = np.broadcast_to(fock_R, (n_bodies, *fock_R.shape)).copy()

    Q_batch = compute_q_batch_vmap(
        jnp.asarray(normals_b),
        jnp.asarray(centroids_b),
        jnp.asarray(areas_b),
        jnp.asarray(k_b),
        jnp.asarray(psi_b),
        jnp.asarray(sc["offsets"]),
        sc["n_tilde"],
        sc["sigma"],
        sc["freq_hz"],
        fock_R_b=jnp.asarray(fock_R_b),
        q_F_s=None,
        q_F_h=q_F_h,
    )
    for b in range(n_bodies):
        np.testing.assert_allclose(np.asarray(Q_batch[b]), np.asarray(Q_fast), atol=ATOL, rtol=RTOL)


def test_fast_lit_unchanged():
    """Deep-lit triangles: g -> 1, so the gated twin matches the ungated twin."""
    sc = _scenario()
    # Normals near +z, single straight-down direction -> mu ~ 1 (deep lit).
    rng = np.random.default_rng(2)
    n = 40
    centroids = rng.uniform(-0.05, 0.05, (n, 3))
    centroids[:, 2] = 0.0
    nrm = rng.normal(0.0, 0.03, (n, 3))
    nrm[:, 2] = 1.0
    normals = nrm / np.linalg.norm(nrm, axis=1, keepdims=True)

    k_hat = np.array([[0.0, 0.0, -1.0]])
    assert np.all((normals @ (-k_hat).T) > 0.99)
    psi = np.array([[1.0 + 0.2j, 0.3 - 0.1j, 0.0]]) * 0.1
    offsets = sc["offsets"][:1]  # single element
    fock_R = np.full(n, 0.1)

    G_no = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(k_hat),
        center_psi=jnp.asarray(psi),
        array_offsets=jnp.asarray(offsets),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
    )
    G_gate = compute_body_channel_factored_jax(
        normals=jnp.asarray(normals),
        centroids=jnp.asarray(centroids),
        center_k_hat=jnp.asarray(k_hat),
        center_psi=jnp.asarray(psi),
        array_offsets=jnp.asarray(offsets),
        n_tilde=sc["n_tilde"],
        sigma=sc["sigma"],
        freq_hz=sc["freq_hz"],
        fock_R=jnp.asarray(fock_R),
    )
    np.testing.assert_allclose(np.asarray(G_gate), np.asarray(G_no), rtol=1e-5, atol=1e-12)
