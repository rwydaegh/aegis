"""Complex Fock local gate in the coherent body channel (Task 6).

The gate enters ``compute_body_channel`` / ``compute_body_channel_factored`` at
the F_psi construction, polarization-resolved: the soft (TE) creeping constant
gates the TE field component, the hard (TM) constant the TM component. Deep lit
both ``-> 1`` so the lit region is unchanged and coherent stays exact there;
near the terminator the complex transition rolls the penumbra off.

Note on shadow leakage: ``compute_fresnel_operator`` hard-zeros ``t_s, t_p`` for
``mu <= 0`` (back-facing), so the coherent channel carries field only in the
lit/penumbra (``mu > 0``); the gate modulates that penumbra rolloff. The
"shadowed convex" tests therefore probe the grazing penumbra of a convex body,
where the gate is active and the field is nonzero.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.coherent import body_channel
from aegis.coherent.body_channel import (
    _fock_gate_factors,
    compute_body_channel,
    compute_body_channel_factored,
)
from aegis.coherent.exposure_operator import compute_exposure_operator, eigendecompose_Q
from aegis.coherent.fresnel_operator import apply_fresnel_operator, compute_fresnel_operator
from aegis.constants import C_0
from aegis.kernels.fock import fock_eigenvalues, fock_g
from aegis.tissue.dielectric import SKIN_28GHZ
from aegis.tissue.fresnel import xi_from_mu

FREQ = 28e9
N_TILDE = SKIN_28GHZ.n_complex
SIGMA = SKIN_28GHZ.sigma


# ---------------------------------------------------------------------------
# Mesh / scenario helpers
# ---------------------------------------------------------------------------


def _icosphere(subdiv: int = 2, radius: float = 0.1):
    """Subdivided icosahedron projected to a sphere. Returns (normals, centroids, areas)."""
    phi = (1 + np.sqrt(5)) / 2
    v = np.array(
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
    v /= np.linalg.norm(v[0])
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
    tris = [tuple(v[i] for i in f) for f in faces]
    for _ in range(subdiv):
        new = []
        for a, b, c in tris:
            ab = (a + b) / 2
            bc = (b + c) / 2
            ca = (c + a) / 2
            ab /= np.linalg.norm(ab)
            bc /= np.linalg.norm(bc)
            ca /= np.linalg.norm(ca)
            new += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        tris = new

    verts = np.array([[t[0], t[1], t[2]] for t in tris]) * radius  # (M, 3, 3)
    v0, v1, v2 = verts[:, 0], verts[:, 1], verts[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / norms
    centroids = verts.mean(axis=1)
    flip = np.sum(normals * centroids, axis=1) < 0
    normals[flip] *= -1
    areas = 0.5 * norms[:, 0]
    return normals, centroids, areas, verts


def _tilted_lit_mesh(n=12, seed=1):
    """Flat-ish patch with normals near +z (all deep lit for a downward ray)."""
    rng = np.random.default_rng(seed)
    centroids = rng.uniform(-0.05, 0.05, (n, 3))
    centroids[:, 2] = 0.0
    nrm = rng.normal(0, 0.05, (n, 3))
    nrm[:, 2] = 1.0
    normals = nrm / np.linalg.norm(nrm, axis=1, keepdims=True)
    areas = np.full(n, 1e-4)
    return normals, centroids, areas


def _paths(n_paths, seed=0, downward=True):
    rng = np.random.default_rng(seed)
    k = rng.standard_normal((n_paths, 3))
    if downward:
        k[:, 2] = -np.abs(k[:, 2]) - 0.5  # mostly downward into +z normals
    k_hat = k / np.linalg.norm(k, axis=1, keepdims=True)
    psi = (rng.standard_normal((n_paths, 3)) + 1j * rng.standard_normal((n_paths, 3))) * 0.1
    element_index = np.arange(n_paths, dtype=np.intp)
    return k_hat, psi, element_index


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_gate_off_is_bit_identical():
    """fock_R=None reproduces the ungated channel bit-for-bit (back-compat)."""
    normals, centroids, _ = _tilted_lit_mesh()
    k_hat, psi, eidx = _paths(5, seed=3)
    n_elem = 5

    G_none = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, n_elem, fock_R=None)

    # Independent reference reproducing the pre-gate code path exactly.
    k0 = 2 * np.pi * FREQ / C_0
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, N_TILDE)
    F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)
    xi = xi_from_mu(mu, N_TILDE)
    alpha = np.maximum(-np.imag(k0 * xi), 1e-30)
    depth = np.sqrt(SIGMA / (4 * alpha))
    phase = np.exp(-1j * k0 * (centroids @ k_hat.T))
    weighted = depth[:, :, None] * F_psi * phase[:, :, None]
    G_ref = np.zeros((normals.shape[0], 3, n_elem), dtype=complex)
    for n in range(k_hat.shape[0]):
        G_ref[:, :, eidx[n]] += weighted[:, n, :]

    np.testing.assert_array_equal(np.asarray(G_none), G_ref)


def test_lit_region_unchanged_by_gate():
    """Deep-lit triangles: g -> 1, gated channel matches the ungated one."""
    normals, centroids, _ = _tilted_lit_mesh()
    # Straight-down ray: mu = normals_z, all > 0.99 here -> deep lit.
    k_hat = np.array([[0.0, 0.0, -1.0]])
    psi = np.array([[1.0 + 0.2j, 0.3 - 0.1j, 0.0]]) * 0.1
    eidx = np.zeros(1, dtype=np.intp)
    fock_R = np.full(normals.shape[0], 0.1)

    # Confirm the triangles really are deep lit.
    mu = normals @ (-k_hat).T
    assert np.all(mu > 0.99)

    G_no = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, 1, fock_R=None)
    G_gate = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, 1, fock_R=fock_R)

    np.testing.assert_allclose(np.asarray(G_gate), np.asarray(G_no), rtol=1e-5, atol=1e-12)


def test_penumbra_gate_is_active():
    """Sanity: at grazing incidence the gate visibly rolls the channel down."""
    # Single triangle, normal +z, ray at ~30 deg above the surface (mu ~ 0.5).
    normals = np.array([[0.0, 0.0, 1.0]])
    centroids = np.array([[0.0, 0.0, 0.0]])
    theta_inc = np.deg2rad(60.0)  # from normal
    k_hat = np.array([[np.sin(theta_inc), 0.0, -np.cos(theta_inc)]])
    psi = np.array([[1.0, 0.0, 0.0]]) * 0.1
    eidx = np.zeros(1, dtype=np.intp)
    fock_R = np.array([0.1])

    G_no = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, 1, fock_R=None)
    G_gate = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, 1, fock_R=fock_R)

    rel = np.linalg.norm(np.asarray(G_gate) - np.asarray(G_no)) / np.linalg.norm(np.asarray(G_no))
    assert rel > 1e-2  # gate is materially active in the penumbra


def test_coherent_ge_incoherent_on_shadowed_convex():
    """Coherent matched dose >= incoherent (isotropic) dose, gate preserves total dose.

    On the grazing penumbra of a convex sphere with the gate active:

    1. trace(Q) is identical for the complex gate and the magnitude-only |g| gate,
       because |g_complex|^2 = |g_magnitude|^2. trace(Q) is the incoherent
       absorbed-power dose (sum of per-path, |g|^2-gated powers). So the complex
       gate does not lose dose versus the magnitude-only gate.
    2. With equal total transmit power, the coherent matched-filter dose
       (n_elem * lambda_max = max_x x^H Q x at ||x||^2 = n_elem) is >= the
       incoherent isotropic dose (trace(Q), power spread over all elements),
       since lambda_max >= trace(Q)/n_elem (max eigenvalue >= mean).
    """
    from aegis.geometry.curvature import fock_radius
    from aegis.geometry.mesh import BodyMesh

    normals, centroids, areas, verts = _icosphere(subdiv=2, radius=0.1)
    body = BodyMesh(vertices=verts, normals=normals, centroids=centroids, areas=areas, name="sphere")

    # Illuminate from +z. Grazing penumbra: small positive mu (field nonzero,
    # gate actively rolling off). Pick a few near-terminator directions.
    n_elem = 4
    rng = np.random.default_rng(5)
    base = np.array([0.05, 0.0, -1.0])
    k = base + rng.normal(0, 0.05, (n_elem, 3))
    k_hat = k / np.linalg.norm(k, axis=1, keepdims=True)
    psi = (rng.standard_normal((n_elem, 3)) + 1j * rng.standard_normal((n_elem, 3))) * 0.1
    eidx = np.arange(n_elem, dtype=np.intp)

    # Keep the grazing-penumbra faces (small positive mu) for the dominant dir.
    mu0 = normals @ (-k_hat[0])
    sel = (mu0 > 1e-3) & (mu0 < 0.4)
    assert sel.sum() >= 8
    nrm, cen, ar = normals[sel], centroids[sel], areas[sel]

    fock_R = fock_radius(body, k_hat[0])[sel]
    assert np.all(np.isfinite(fock_R))
    assert np.median(fock_R) < 0.5  # ~0.1 m sphere

    # Complex gate channel and Q.
    G_cplx = compute_body_channel(nrm, cen, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, n_elem, fock_R=fock_R)
    Q_cplx = compute_exposure_operator(G_cplx, ar)

    # Magnitude-only gate channel (built explicitly with |g_soft|, |g_hard|).
    k0 = 2 * np.pi * FREQ / C_0
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(nrm, k_hat, N_TILDE)
    g_soft, g_hard = _fock_gate_factors(mu, fock_R, FREQ, None, None)
    psi_s = np.einsum("mnj,nj->mn", e_s, psi)
    psi_p = np.einsum("mnj,nj->mn", e_p, psi)
    F_mag = (np.abs(g_soft) * t_s * psi_s)[:, :, None] * e_s + (np.abs(g_hard) * t_p * psi_p)[:, :, None] * e_p
    xi = xi_from_mu(mu, N_TILDE)
    alpha = np.maximum(-np.imag(k0 * xi), 1e-30)
    depth = np.sqrt(SIGMA / (4 * alpha))
    phase = np.exp(-1j * k0 * (cen @ k_hat.T))
    wmag = depth[:, :, None] * F_mag * phase[:, :, None]
    G_mag = np.zeros_like(G_cplx)
    for n in range(n_elem):
        G_mag[:, :, eidx[n]] += wmag[:, n, :]
    Q_mag = compute_exposure_operator(G_mag, ar)

    # 1. Complex gate preserves total dose vs magnitude-only gate.
    np.testing.assert_allclose(np.trace(Q_cplx).real, np.trace(Q_mag).real, rtol=1e-10)

    # 2. Coherent matched >= incoherent isotropic (equal total power n_elem).
    eig, _ = eigendecompose_Q(Q_cplx)
    lam_max = float(eig[0])
    trace = float(np.trace(Q_cplx).real)
    coherent_dose = n_elem * lam_max
    incoherent_dose = trace
    assert coherent_dose >= incoherent_dose * (1 - 1e-9)
    # And the coherent advantage is real (not a degenerate rank-1 tie).
    assert lam_max > trace / n_elem


def test_complex_local_phase_matches_cylinder_oracle():
    """Gate magnitude pins to the PEC cylinder oracle; phase tracks the creeping slope.

    The committed cylinder oracle exports |field|^2 (magnitude), so the magnitude
    is validated against the oracle-pinned hard terminator value (|g(0)|^2 ~ 0.488,
    the kR-independent exact PEC value), and the complex phase is validated against
    the analytic creeping-wave phase ramp arg ~ Re(nu) * xi with
    nu = q exp(-i pi/3), i.e. slope d(arg)/d(xi) = 0.5 * Re(q) deep in the shadow.
    """
    # Magnitude vs oracle (the exact PEC cylinder terminator value).
    assert abs(fock_g(np.array(0.0), "hard")) ** 2 == pytest.approx(0.488, abs=0.03)

    # Deep lit: GO, real, phase ~ 0.
    xi_lit = np.linspace(3.0, 5.0, 50)
    assert np.max(np.abs(np.angle(fock_g(xi_lit, "soft")))) < 1e-3

    # Deep shadow: phase ramps with the analytic creeping slope 0.5 * Re(q1).
    q1 = fock_eigenvalues("soft")[0].real
    xi_sh = np.linspace(-12.0, -8.0, 200)
    ph = np.unwrap(np.angle(np.asarray(fock_g(xi_sh, "soft"))))
    slope = np.polyfit(xi_sh, ph, 1)[0]
    assert slope == pytest.approx(0.5 * q1, rel=0.1)


def test_factored_matches_nonfactored_with_gate():
    """Factored channel == non-factored channel with the gate, on array-expanded paths."""
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.paths import PropagationPaths

    normals, centroids, _ = _tilted_lit_mesh(n=20, seed=2)
    M = normals.shape[0]
    fock_R = np.full(M, 0.1)  # per-triangle radius (same for all paths/elements)

    positions = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0], [0.0, 0.05, 1.0]])
    array = AntennaArray(element_positions=positions, element_pattern="isotropic")

    N_center = 4
    k_hat, psi, _ = _paths(N_center, seed=9)
    center_paths = PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.zeros(N_center, dtype=np.intp),
        delay=np.zeros(N_center),
        is_los=np.zeros(N_center, dtype=bool),
    )
    expanded = expand_paths_to_array(center_paths, array, FREQ)
    gain = array.element_gain(center_paths.k_hat)
    center_psi_gained = center_paths.psi * gain[:, None]

    for fr, qfs, qfh in [(None, None, None), (fock_R, None, None)]:
        G_full = compute_body_channel(
            normals,
            centroids,
            expanded.k_hat,
            expanded.psi,
            expanded.element_index,
            N_TILDE,
            SIGMA,
            FREQ,
            array.n_elements,
            fock_R=fr,
            q_F_s=qfs,
            q_F_h=qfh,
        )
        G_fac = compute_body_channel_factored(
            normals,
            centroids,
            center_paths.k_hat,
            center_psi_gained,
            expanded.psi,
            expanded.element_index,
            N_TILDE,
            SIGMA,
            FREQ,
            array.n_elements,
            fock_R=fr,
            q_F_s=qfs,
            q_F_h=qfh,
        )
        np.testing.assert_allclose(np.asarray(G_fac), np.asarray(G_full), atol=1e-12, rtol=1e-7)


def test_module_exposes_gate_helper():
    """The private gate helper is importable and returns (M, N) complex factors."""
    mu = np.array([[0.9, 0.2], [0.05, 0.7]])
    gs, gh = body_channel._fock_gate_factors(mu, np.array([0.1, 0.1]), FREQ, None, None)
    assert gs.shape == (2, 2)
    assert gh.shape == (2, 2)
    assert np.iscomplexobj(np.asarray(gs))


# ---------------------------------------------------------------------------
# Task 13: distal self-shadowing amplitude gate (A3 approximation)
# ---------------------------------------------------------------------------


def test_distal_off_is_bit_identical():
    # clearance=None must reproduce the no-distal channel bit-for-bit.
    normals, centroids, _ = _tilted_lit_mesh()
    k_hat, psi, eidx = _paths(5, seed=7)
    n_elem = 5
    a = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, n_elem, fock_R=None)
    b = compute_body_channel(
        normals,
        centroids,
        k_hat,
        psi,
        eidx,
        N_TILDE,
        SIGMA,
        FREQ,
        n_elem,
        fock_R=None,
        clearance=None,
        R_occ=None,
        distal_d1=None,
        distal_d2=None,
    )
    assert np.array_equal(a, b)


def test_distal_amplitude_attenuates_shadow():
    # Shadowed rows (clearance < 0) lose channel amplitude; lit rows (clearance
    # large positive) are essentially unchanged. A3: amplitude only, phase kept.
    normals, centroids, _ = _tilted_lit_mesh(n=12, seed=2)
    M = normals.shape[0]
    k_hat, psi, eidx = _paths(1, seed=2)
    n_elem = 1
    clearance = np.full((M, 1), 5.0)  # deep clear: gate saturates to 1
    clearance[: M // 2, 0] = -0.5  # first half shadowed
    R_occ = np.full((M, 1), 0.1)
    d1 = np.full((M, 1), np.inf)
    d2 = np.full((M, 1), 0.05)

    G_off = compute_body_channel(normals, centroids, k_hat, psi, eidx, N_TILDE, SIGMA, FREQ, n_elem)
    G_on = compute_body_channel(
        normals,
        centroids,
        k_hat,
        psi,
        eidx,
        N_TILDE,
        SIGMA,
        FREQ,
        n_elem,
        clearance=clearance,
        R_occ=R_occ,
        distal_d1=d1,
        distal_d2=d2,
    )
    norm_off = np.linalg.norm(G_off.reshape(M, -1), axis=1)
    norm_on = np.linalg.norm(G_on.reshape(M, -1), axis=1)
    lit = slice(M // 2, M)
    # shadowed rows attenuated (only where the row actually sees the source, mu>0)
    mu = normals @ (-k_hat[0])
    sh_lit = (np.arange(M) < M // 2) & (mu > 1e-3)
    assert np.all(norm_on[sh_lit] < norm_off[sh_lit] * 0.999)
    # lit rows unchanged
    assert np.allclose(norm_on[lit], norm_off[lit], rtol=1e-9)
    # amplitude gate never amplifies
    assert np.all(norm_on <= norm_off + 1e-12)


def test_distal_factored_matches_direct():
    # The factored channel applies the same distal amplitude as the direct one.
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.paths import PropagationPaths

    normals, centroids, _ = _tilted_lit_mesh(n=12, seed=4)
    M = normals.shape[0]
    positions = np.array([[0.0, 0.0, 1.0], [0.05, 0.0, 1.0], [0.0, 0.05, 1.0]])
    array = AntennaArray(element_positions=positions, element_pattern="isotropic")

    # Single center direction so the clearance tiling across elements is exact.
    k_hat, psi, _ = _paths(1, seed=9)
    center_paths = PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.zeros(1, dtype=np.intp),
        delay=np.zeros(1),
        is_los=np.zeros(1, dtype=bool),
    )
    expanded = expand_paths_to_array(center_paths, array, FREQ)
    gain = array.element_gain(center_paths.k_hat)
    center_psi_gained = center_paths.psi * gain[:, None]
    n_elem = array.n_elements
    n_total = expanded.k_hat.shape[0]

    clearance = np.full((M, 1), -0.3)
    R_occ = np.full((M, 1), 0.1)
    d1 = np.full((M, 1), np.inf)
    d2 = np.full((M, 1), 0.05)

    G_direct = compute_body_channel(
        normals,
        centroids,
        expanded.k_hat,
        expanded.psi,
        expanded.element_index,
        N_TILDE,
        SIGMA,
        FREQ,
        n_elem,
        clearance=np.repeat(clearance, n_total, axis=1),
        R_occ=np.repeat(R_occ, n_total, axis=1),
        distal_d1=np.repeat(d1, n_total, axis=1),
        distal_d2=np.repeat(d2, n_total, axis=1),
    )
    G_fac = compute_body_channel_factored(
        normals,
        centroids,
        center_paths.k_hat,
        center_psi_gained,
        expanded.psi,
        expanded.element_index,
        N_TILDE,
        SIGMA,
        FREQ,
        n_elem,
        clearance=clearance,
        R_occ=R_occ,
        distal_d1=d1,
        distal_d2=d2,
    )
    assert np.allclose(G_direct, G_fac, atol=1e-10)
