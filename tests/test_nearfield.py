"""Tests for the near-field hand-held exposure module (``aegis.nearfield``)."""

from __future__ import annotations

import numpy as np
import pytest

from aegis._array_backend import JAX_AVAILABLE
from aegis.geometry.mesh import BodyMesh
from aegis.nearfield.metrics import MetricsEvaluator, cube_side_length, h_depth_efficiency
from aegis.nearfield.patterns import AntennaPattern3D
from aegis.nearfield.phone import PhoneSource, compute_sab, euler_to_matrix
from aegis.nearfield.scenarios import (
    detect_body_frame,
    make_source,
    standard_placements,
)
from aegis.tissue.dielectric import TissueModel

RHO_SKIN = 1109.0
DATA = "data/duke.stl"

pytestmark = pytest.mark.slow  # needs phantom STL data


@pytest.fixture(scope="module")
def mesh():
    return BodyMesh.load(DATA)


@pytest.fixture(scope="module")
def tissue():
    t = TissueModel.from_database("Skin", 2.45e9)
    return t.n_complex, t.T0


def _source(mesh, scenario="front_of_eyes", **kw):
    pat = AntennaPattern3D.isotropic(2.45e9)
    pl = standard_placements(mesh)[scenario]
    return make_source(pl, pat, **kw)


# -- pattern sampling -------------------------------------------------------


def test_isotropic_pattern_is_unity():
    pat = AntennaPattern3D.isotropic(1e9)
    dirs = np.array([[0, 0, 1.0], [1, 0, 0], [0, 1, 0], [0, 0, -1.0]])
    d = np.asarray(pat.sample(dirs))
    assert np.allclose(d, 1.0, atol=1e-6)


def test_real_pattern_sphere_average_is_one():
    """A physical directivity pattern integrates to 4 pi over the sphere."""
    pat = next(iter(_load_real_patterns().values()))
    # Sample on a Fibonacci sphere and average.
    n = 4000
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5**0.5) * i
    dirs = np.stack([np.sin(phi) * np.cos(theta), np.sin(phi) * np.sin(theta), np.cos(phi)], axis=-1)
    mean_d = float(np.mean(np.asarray(pat.sample(dirs))))
    assert 0.85 < mean_d < 1.2  # sphere-average directivity ~ 1


def _load_real_patterns():
    import os

    from aegis.nearfield.patterns import load_band_patterns

    pattern_dir = os.environ.get("AEGIS_NEARFIELD_PATTERNS", "/home/user/goliat_farfield_results")
    patterns = load_band_patterns(pattern_dir)
    if not patterns:
        pytest.skip("real GOLIAT patterns not available")
    return patterns


# -- kernel physics ---------------------------------------------------------


def test_sab_nonnegative(mesh, tissue):
    nt, t0 = tissue
    src = _source(mesh)
    sab = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt))
    assert np.all(sab >= 0.0)
    assert np.any(sab > 0.0)


def test_power_is_linear(mesh, tissue):
    nt, t0 = tissue
    s1 = np.asarray(compute_sab(mesh.centroids, mesh.normals, _source(mesh, radiated_power_w=1.0), t0, nt))
    s2 = np.asarray(compute_sab(mesh.centroids, mesh.normals, _source(mesh, radiated_power_w=2.0), t0, nt))
    assert np.allclose(s2, 2.0 * s1, rtol=1e-6)


def test_far_field_inverse_square(mesh, tissue):
    """At large stand-off the peak APD follows the 1/d^2 free-space law."""
    nt, t0 = tissue
    pat = AntennaPattern3D.isotropic(2.45e9)
    pl = standard_placements(mesh)["front_of_eyes"]

    def peak(d):
        src = make_source(pl, pat, distance_m=d)
        return float(np.max(compute_sab(mesh.centroids, mesh.normals, src, t0, nt)))

    p2, p4 = peak(2.0), peak(4.0)
    assert p2 / p4 == pytest.approx(4.0, rel=0.05)


def test_back_face_is_shadowed(mesh, tissue):
    """Triangles facing away from the source receive zero (ReLU projection)."""
    nt, t0 = tissue
    src = _source(mesh)
    sab = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt))
    k = np.asarray(mesh.centroids) - src.position[None, :]
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    mu = np.sum(np.asarray(mesh.normals) * (-k), axis=1)
    assert np.all(sab[mu <= 0] == 0.0)


# -- Fock local diffraction gate --------------------------------------------


def _gate_geometry(mesh, src):
    """Per-face mu, distance, and curvature radius for the phone geometry."""
    from aegis.geometry import curvature

    c = np.asarray(mesh.centroids)
    n = np.asarray(mesh.normals)
    rel = c - src.position[None, :]
    dist = np.linalg.norm(rel, axis=1)
    k_hat = rel / dist[:, None]
    mu = np.sum(n * (-k_hat), axis=1)
    fock_R = np.asarray(curvature.fock_radius(mesh, k_hat))
    return mu, dist, k_hat, fock_R


def test_nearfield_gate_off_unchanged(mesh, tissue):
    """diffraction_model='none' (and the legacy no-body call) reproduce ReLU."""
    nt, t0 = tissue
    src = _source(mesh)
    legacy = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt))  # no body -> no gate
    none = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt, body=mesh, diffraction_model="none"))
    assert np.allclose(legacy, none, rtol=1e-12, atol=0.0)


def test_nearfield_gate_finite(mesh, tissue):
    """The Fock gate is finite, non-negative, and rolls the grazing dose off
    below the bare ReLU near the terminator (the dose-relevant penumbra effect).

    The creeping wave does leak past the geometric terminator (validated at the
    field level in tests/test_fock.py), but in the absorbed-power law it is gated
    by the Fresnel transmission, which vanishes at grazing (``relu_mu=0``), so the
    measurable dose change lives in the lit penumbra, not the deep shadow."""
    nt, t0 = tissue
    src = _source(mesh)
    none = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt, body=mesh, diffraction_model="none"))
    fock = np.asarray(compute_sab(mesh.centroids, mesh.normals, src, t0, nt, body=mesh, diffraction_model="fock"))
    assert np.all(np.isfinite(fock))
    assert np.all(fock >= 0.0)
    assert np.any(fock > 0.0)
    assert not np.allclose(fock, none)  # the gate actually changes the dose

    mu, _, _, _ = _gate_geometry(mesh, src)
    # Lit grazing band: the smooth penumbra rolls the dose off below GO/ReLU.
    lit_band = (mu > 0.0) & (mu < 0.15)
    assert fock[lit_band].sum() < none[lit_band].sum()


def test_nearfield_wnf_narrows(mesh, tissue):
    """In the phone geometry the near-field penumbra is NARROWER than the far
    field (L13: w_nf divides the detour). A multiply-bug would widen it."""
    from aegis.geometry import fock_gate as fg
    from aegis.kernels.fock import fock_local

    nt, _ = tissue
    src = _source(mesh)
    mu, dist, _, fock_R = _gate_geometry(mesh, src)
    freq = src.pattern.freq_hz
    q_F_h = fg.fock_q_hard(fock_R, freq, nt)
    relu = np.maximum(mu, 0.0)

    g_near = np.asarray(fock_local(mu, fock_R, freq, 0.5, 0.5, None, q_F_h, d1=dist, d2=None))
    g_far = np.asarray(fock_local(mu, fock_R, freq, 0.5, 0.5, None, q_F_h, d1=None))
    dev_near = float(np.sum(np.abs(g_near - relu)))
    dev_far = float(np.sum(np.abs(g_far - relu)))
    assert dev_near < dev_far


# -- metrics ----------------------------------------------------------------


def test_h_depth_efficiency():
    assert h_depth_efficiency(1e-12) == pytest.approx(1.0, abs=1e-6)
    # Monograph table (psSAR10g.tex, tab:skin-freq): h(1.9) ~ 0.45 at 2.45 GHz.
    assert h_depth_efficiency(1.9) == pytest.approx(0.447, abs=0.01)
    assert h_depth_efficiency(46.7) == pytest.approx(0.021, abs=0.005)
    # Strictly decreasing.
    u = np.linspace(0.1, 50, 200)
    assert np.all(np.diff(h_depth_efficiency(u)) < 0)


def test_cube_side_length():
    # 10 g of tissue at skin density -> ~21.5 mm cube.
    assert cube_side_length(RHO_SKIN) == pytest.approx(0.0215, abs=0.001)


def test_metric_ordering(mesh, tissue):
    nt, t0 = tissue
    src = _source(mesh, scenario="by_cheek")
    sab = compute_sab(mesh.centroids, mesh.normals, src, t0, nt)
    ev = MetricsEvaluator(mesh.centroids, mesh.areas, RHO_SKIN)
    m = ev.evaluate(np.asarray(sab), nt, 2.45e9, body_mass_kg=72.4)
    # Smaller averaging area -> larger peak average; raw peak is the largest.
    assert m.peak_apd >= m.apd_1cm2 >= m.apd_4cm2 > 0
    assert m.sar_wb > 0
    assert m.pssar_10g > 0
    assert m.p_abs_w > 0


# -- geometry / placements --------------------------------------------------


def test_body_frame_face_is_anterior(mesh):
    frame = detect_body_frame(mesh)
    assert np.allclose(frame.up, [0, 0, 1])
    assert frame.anterior[1] == -1.0  # all shipped phantoms face -y


def test_placements_are_outside_body(mesh):
    pl = standard_placements(mesh)
    c = np.asarray(mesh.centroids)
    for name, p in pl.items():
        pos = p.position()
        nearest = float(np.min(np.linalg.norm(c - pos[None, :], axis=1)))
        # Nearest surface point should be ~ the nominal stand-off (phone is off
        # the body, looking at its landmark).
        assert nearest > 0.5 * p.nominal_distance_m, name


def test_euler_matrix_is_orthonormal():
    R = np.asarray(euler_to_matrix(0.3, -0.4, 1.1))
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)
    assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-6)


# -- differentiability ------------------------------------------------------


@pytest.mark.skipif(not JAX_AVAILABLE, reason="requires AEGIS_ARRAY_BACKEND=jax")
def test_gradient_wrt_position_matches_fd(mesh, tissue):
    import jax
    import jax.numpy as jnp

    nt, t0 = tissue
    pat = next(iter(_load_real_patterns().values()))
    pl = standard_placements(mesh)["front_of_eyes"]
    from aegis.nearfield.scenarios import _rotation_aligning_z_to

    cen = jnp.asarray(mesh.centroids)
    nor = jnp.asarray(mesh.normals)
    rot = jnp.asarray(_rotation_aligning_z_to(pl.look_dir))

    def total_sab(pos):
        src = PhoneSource(position=pos, rotation=rot, pattern=pat, radiated_power_w=1.0)
        return jnp.sum(compute_sab(cen, nor, src, t0, nt, fresnel=True))

    pos0 = jnp.asarray(pl.position())
    g = np.asarray(jax.grad(total_sab)(pos0))
    assert np.all(np.isfinite(g))
    eps = 1e-5
    fd = np.array(
        [float((total_sab(pos0.at[i].add(eps)) - total_sab(pos0.at[i].add(-eps))) / (2 * eps)) for i in range(3)]
    )
    assert np.max(np.abs((g - fd) / (np.abs(fd) + 1e-6))) < 0.05


@pytest.mark.skipif(not JAX_AVAILABLE, reason="requires AEGIS_ARRAY_BACKEND=jax")
def test_nearfield_fock_gate_differentiable(mesh, tissue):
    """The Fock-gated dose stays differentiable in the source position.

    The curvature solve cannot trace a symbolic position, so ``fock_R`` and the
    representative hard eigenvalue are precomputed (NumPy) at the nominal pose and
    passed in; the gate's position dependence then flows through ``mu`` and the
    wavefront distance ``d1`` only, which stay traceable.
    """
    import jax
    import jax.numpy as jnp

    from aegis.geometry import curvature
    from aegis.geometry import fock_gate as fg
    from aegis.nearfield.scenarios import _rotation_aligning_z_to

    nt, t0 = tissue
    pat = next(iter(_load_real_patterns().values()))
    pl = standard_placements(mesh)["front_of_eyes"]

    cen = jnp.asarray(mesh.centroids)
    nor = jnp.asarray(mesh.normals)
    rot = jnp.asarray(_rotation_aligning_z_to(pl.look_dir))
    pos0 = jnp.asarray(pl.position())

    # Precompute curvature radius + hard eigenvalue at the nominal pose (NumPy).
    rel = np.asarray(mesh.centroids) - np.asarray(pos0)[None, :]
    k0 = rel / np.linalg.norm(rel, axis=1, keepdims=True)
    fock_R = np.asarray(curvature.fock_radius(mesh, k0))
    q_F_h = fg.fock_q_hard(fock_R, pat.freq_hz, nt)

    def total_sab(pos):
        src = PhoneSource(position=pos, rotation=rot, pattern=pat, radiated_power_w=1.0)
        return jnp.sum(
            compute_sab(cen, nor, src, t0, nt, body=mesh, diffraction_model="fock", fock_R=fock_R, q_F_h=q_F_h)
        )

    g = np.asarray(jax.grad(total_sab)(pos0))
    assert np.all(np.isfinite(g))  # no NaN from the gate / w_nf floor
    eps = 1e-5
    fd = np.array(
        [float((total_sab(pos0.at[i].add(eps)) - total_sab(pos0.at[i].add(-eps))) / (2 * eps)) for i in range(3)]
    )
    assert np.max(np.abs((g - fd) / (np.abs(fd) + 1e-6))) < 0.02
