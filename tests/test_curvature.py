"""Curvature estimation tests on analytic sphere and cylinder meshes.

The critical test is the in-incidence-plane Fock radius: a cylinder of radius R
must yield R for a ray normal to its axis, NOT 2R (the 2/H mistake).
"""

import numpy as np

from aegis.geometry import curvature
from aegis.geometry.mesh import BodyMesh


def _sphere_mesh(R: float = 0.1, subdivisions: int = 3) -> BodyMesh:
    return BodyMesh.sphere(radius=R, n_subdivisions=subdivisions)


def _open_cylinder_mesh(R: float = 0.05, h: float = 0.4, n_seg: int = 48, n_height: int = 20) -> BodyMesh:
    """Open cylinder (no end caps), axis = z, as a side-wall triangle grid."""
    angles = np.linspace(0.0, 2.0 * np.pi, n_seg, endpoint=False)
    cos_a = np.cos(angles)
    sin_a = np.sin(angles)
    zs = np.linspace(-h / 2.0, h / 2.0, n_height + 1)

    tris = []
    for iz in range(n_height):
        z0 = zs[iz]
        z1 = zs[iz + 1]
        for ia in range(n_seg):
            ja = (ia + 1) % n_seg
            p00 = [R * cos_a[ia], R * sin_a[ia], z0]
            p10 = [R * cos_a[ja], R * sin_a[ja], z0]
            p01 = [R * cos_a[ia], R * sin_a[ia], z1]
            p11 = [R * cos_a[ja], R * sin_a[ja], z1]
            # CCW outward winding
            tris.append([p00, p10, p11])
            tris.append([p00, p11, p01])
    vertices = np.asarray(tris, dtype=np.float64)
    return BodyMesh.from_arrays(vertices, name="open_cylinder")


def test_principal_curvatures_sphere():
    body = _sphere_mesh(R=0.1)
    k1, k2, _ = curvature.principal_curvatures(body)
    np.testing.assert_allclose(np.median(k1), 1 / 0.1, rtol=0.1)
    np.testing.assert_allclose(np.median(k2), 1 / 0.1, rtol=0.1)


def test_principal_curvatures_cylinder():
    body = _open_cylinder_mesh(R=0.05)
    k1, k2, _ = curvature.principal_curvatures(body)
    np.testing.assert_allclose(np.median(np.maximum(k1, k2)), 1 / 0.05, rtol=0.15)
    np.testing.assert_allclose(np.median(np.minimum(np.abs(k1), np.abs(k2))), 0.0, atol=2.0)


def test_fock_radius_cylinder_normal_incidence_is_R_not_2R():
    body = _open_cylinder_mesh(R=0.05)
    k_hat = np.array([1.0, 0.0, 0.0])  # normal to axis (axis = z)
    R = curvature.fock_radius(body, k_hat)
    med = np.median(R)
    np.testing.assert_allclose(med, 0.05, rtol=0.15)  # R, NOT 0.10
    assert abs(med - 0.10) > 0.02, f"fock_radius collapsed to 2R: {med}"


def test_fock_radius_sphere_isotropic():
    body = _sphere_mesh(R=0.1)
    for k_hat in ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]):
        R = curvature.fock_radius(body, np.asarray(k_hat))
        np.testing.assert_allclose(np.median(R), 0.1, rtol=0.1)


def test_face_curvature_sphere():
    body = _sphere_mesh(R=0.1)
    H = curvature.face_curvature(body)
    np.testing.assert_allclose(np.median(H), 2 / 0.1, rtol=0.1)


def test_viewer_wrapper_still_works():
    from aegis.viewer.compute import _compute_face_curvature

    body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
    H = _compute_face_curvature(body)
    assert H.shape == (body.n_triangles,)
    assert np.all(np.isfinite(H))
