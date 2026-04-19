"""Metamorphic relation: incoherent sab is invariant under a simultaneous
rotation of mesh normals and path directions.

Monograph: Eq. 2.5 (sec:local-law):

    Sab(r) = S_inc * T_eff(mu) * ReLU(mu),    mu = n_hat . (-k_hat).

`mu` is a scalar dot product of two unit vectors. Under any R in SO(3),

    mu' = (R n_hat) . (-R k_hat) = n_hat^T R^T R (-k_hat) = mu,

so per-triangle sab at Levels 2, 3, and 4 (with q=0) is invariant under
simultaneous rotation of normals and k_hat.

Applies to: Levels 2, 3, 4 (q=0 only).
Does not apply to Level 4 (q != 0) because q is expressed relative to
a global polarisation basis whose orientation is not part of the
rotation argument here. Levels 5 and 6 (curvature, diffraction) depend
on additional per-triangle quantities that need extra care; we skip
them to avoid claiming an invariance we have not separately validated.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import make_icosahedron
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests._metamorphic import rotation_matrix_from_axis_angle


def _rotate_mesh(mesh: BodyMesh, R: np.ndarray) -> BodyMesh:
    """Rotate all vertex positions, centroids, and normals by R.

    Areas and triangle topology are unchanged.
    """
    vertices = mesh.vertices @ R.T  # (N, 3, 3), rotate each vertex row-wise
    normals = mesh.normals @ R.T
    centroids = mesh.centroids @ R.T
    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=mesh.areas,
        name=f"{mesh.name}_rot",
    )


def _rotate_paths(paths: PropagationPaths, R: np.ndarray) -> PropagationPaths:
    """Rotate k_hat and psi by R. Other fields unchanged.

    psi is a complex 3-vector; rotation is applied to real and imaginary
    parts separately (R is real).
    """
    k_hat_r = paths.k_hat @ R.T
    psi_r = paths.psi @ R.T
    return PropagationPaths(
        k_hat=k_hat_r,
        psi=psi_r,
        element_index=paths.element_index,
        delay=paths.delay,
        is_los=paths.is_los,
    )


@pytest.mark.parametrize(
    "level",
    [2, 3, 4],
)
@pytest.mark.parametrize(
    ("axis", "angle"),
    [
        (np.array([0.0, 0.0, 1.0]), 0.7),
        (np.array([1.0, 0.0, 0.0]), np.pi / 3),
        (np.array([1.0, 1.0, 0.0]), np.pi / 4),
        (np.array([1.0, -1.0, 2.0]), 1.23),
    ],
    ids=["z_0.7", "x_60deg", "xy_45deg", "oblique_1.23"],
)
def test_simultaneous_rotation_invariance(level: int, axis: np.ndarray, angle: float) -> None:
    """Levels 2, 3, 4(q=0) produce invariant per-triangle sab under R.

    The test rotates both the mesh (normals, centroids, vertices) and the
    paths (k_hat) by the same R, and asserts sab_j is unchanged.
    """
    body = make_icosahedron()
    rng = np.random.default_rng(12345)
    k_hat = rng.standard_normal((10, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.3, 3.0, size=10)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    R = rotation_matrix_from_axis_angle(axis, angle)

    engine = DosimetryEngine(SKIN_28GHZ)
    kwargs = {"q": 0.0} if level == 4 else {}
    sab_ref = np.asarray(engine.compute_sab(body, paths, level=level, **kwargs))
    sab_rot = np.asarray(engine.compute_sab(_rotate_mesh(body, R), _rotate_paths(paths, R), level=level, **kwargs))

    np.testing.assert_allclose(sab_rot, sab_ref, rtol=1e-12, atol=1e-14)


@given(
    angle=st.floats(min_value=-np.pi, max_value=np.pi, allow_nan=False, allow_infinity=False),
    ax=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    ay=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    az=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=30, deadline=5000)
def test_rotation_invariance_hypothesis_level3(angle: float, ax: float, ay: float, az: float, seed: int) -> None:
    """Hypothesis sweep: Level 3 sab invariant under simultaneous rotation.

    Skips degenerate axes (norm < 1e-3). Uses Level 3 specifically since
    it exercises the angle-dependent Fresnel weights (not just ReLU*T0).
    """
    axis = np.array([ax, ay, az])
    norm = np.linalg.norm(axis)
    if norm < 1e-3:
        return  # degenerate axis, skip
    axis = axis / norm

    body = make_icosahedron()
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((8, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 2.0, size=8)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    R = rotation_matrix_from_axis_angle(axis, angle)

    engine = DosimetryEngine(SKIN_28GHZ)
    sab_ref = np.asarray(engine.compute_sab(body, paths, level=3))
    sab_rot = np.asarray(engine.compute_sab(_rotate_mesh(body, R), _rotate_paths(paths, R), level=3))

    np.testing.assert_allclose(sab_rot, sab_ref, rtol=1e-11, atol=1e-13)


def test_rotation_of_only_body_not_invariant() -> None:
    """Sanity: rotating ONLY the body (not the paths) generally CHANGES sab.

    This confirms the relation is "simultaneous rotation", not "body
    rotation alone". If this ever passed, it would mean sab is not
    actually dependent on mu, which would be a bug.
    """
    body = make_icosahedron()
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([1.0]),
    )
    R = rotation_matrix_from_axis_angle(np.array([1.0, 0.0, 0.0]), np.pi / 2)

    engine = DosimetryEngine(SKIN_28GHZ)
    sab_ref = np.asarray(engine.compute_sab(body, paths, level=3))
    sab_body_only = np.asarray(engine.compute_sab(_rotate_mesh(body, R), paths, level=3))

    # The two sab maps should differ: rotating the body changes which
    # triangles are illuminated by the fixed path. If they were equal,
    # the kernel would be ignoring the mesh orientation.
    assert not np.allclose(sab_body_only, sab_ref, rtol=1e-6), (
        "Rotating only the body should change sab; either the kernel is "
        "ignoring normals or the test setup is degenerate"
    )
