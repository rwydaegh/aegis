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
