import numpy as np
import pytest

from aegis.geometry.mesh import BodyMesh
from aegis.nearfield import phone
from aegis.nearfield.patterns import AntennaPattern3D

pytestmark = pytest.mark.slow  # numba bake


def _two_plate_body() -> BodyMesh:
    """A big z=0 plate (torso) plus a small z=-0.1 plate (arm) in front of it.

    Both face -z (toward a phone at negative z). The small plate sits between the
    phone and the torso, so it casts a distal shadow onto the big plate.
    """

    def grid_plate(cx, cy, z, half, n):
        xs = np.linspace(cx - half, cx + half, n)
        ys = np.linspace(cy - half, cy + half, n)
        verts, normals = [], []
        for i in range(n - 1):
            for j in range(n - 1):
                p00 = [xs[i], ys[j], z]
                p10 = [xs[i + 1], ys[j], z]
                p11 = [xs[i + 1], ys[j + 1], z]
                p01 = [xs[i], ys[j + 1], z]
                verts.append([p00, p10, p11])
                verts.append([p00, p11, p01])
                normals.append([0, 0, -1])
                normals.append([0, 0, -1])
        return verts, normals

    v1, n1 = grid_plate(0, 0, 0.0, 0.30, 12)
    v2, n2 = grid_plate(0, 0, -0.10, 0.06, 6)
    verts = np.array(v1 + v2, dtype=np.float64)
    normals = np.array(n1 + n2, dtype=np.float64)
    return BodyMesh.from_arrays(verts, normals, name="two_plate")


def test_self_shadow_reduces_dose_behind_occluder():
    body = _two_plate_body()
    pat = AntennaPattern3D.isotropic(3.5e9)
    src = phone.PhoneSource(
        position=np.array([0.0, 0.0, -0.20]),
        rotation=np.eye(3),
        pattern=pat,
        radiated_power_w=1.0,
    )
    n_tilde = 5.0 - 8.0j
    kw = dict(
        centroids=body.centroids,
        normals=body.normals,
        source=src,
        t0=0.5,
        n_tilde=n_tilde,
        body=body,
        diffraction_model="fock",
        source_pos=src.position,
    )
    sab_off = phone.compute_sab(self_shadow=False, **kw)
    sab_on = phone.compute_sab(self_shadow=True, **kw)
    c = body.centroids
    # Torso (z=0) centroids directly behind the z=-0.1 occluder. The z > -0.05
    # cut keeps the torso and drops the occluder plate itself.
    behind = (np.abs(c[:, 0]) < 0.05) & (np.abs(c[:, 1]) < 0.05) & (c[:, 2] > -0.05)
    assert behind.sum() > 0
    assert sab_on[behind].sum() < 0.9 * sab_off[behind].sum()
    edge = (np.abs(c[:, 0]) > 0.25) & (c[:, 2] > -0.05)
    assert np.allclose(sab_on[edge], sab_off[edge], rtol=0.05)


def test_self_shadow_noop_on_convex():
    from aegis.geometry import visibility

    body = BodyMesh.sphere(radius=0.3, n_subdivisions=2)
    assert visibility._is_convex(body) is True
    pat = AntennaPattern3D.isotropic(3.5e9)
    src = phone.PhoneSource(
        position=np.array([0.0, 0.0, -0.6]),
        rotation=np.eye(3),
        pattern=pat,
        radiated_power_w=1.0,
    )
    kw = dict(
        centroids=body.centroids,
        normals=body.normals,
        source=src,
        t0=0.5,
        n_tilde=5.0 - 8.0j,
        body=body,
        diffraction_model="fock",
        source_pos=src.position,
    )
    sab_off = phone.compute_sab(self_shadow=False, **kw)
    sab_on = phone.compute_sab(self_shadow=True, **kw)
    assert np.array_equal(sab_on, sab_off)
