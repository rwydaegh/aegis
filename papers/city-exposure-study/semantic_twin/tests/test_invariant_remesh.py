"""A surface quantity may not depend on how the surface was cut into triangles.

Splitting a triangle into four does not move any absorbing surface, so every
quantity that describes the surface has to come out the same. Total area, total
absorbed power, the peak density and the average density over the body are all
of that kind. The number of triangles is not, and neither is any plain mean over
them.

The mesh here is deliberately built to look like the phantom the study runs on.
Duke's triangle areas vary by a factor of 9,300 with a coefficient of variation
just over one, so the areas below are drawn log uniformly over two decades. The
remesh splits every triangle facing the incoming power, which is what a real
remesh does: it refines where the geometry is interesting.
"""

from __future__ import annotations

import pathlib
import struct

import numpy as np
import pytest

from semantic_twin.illumination import fibonacci_sphere

pytest.importorskip("aegis", reason="the body side needs AEGIS installed")

FREQUENCY_HZ = 15.0e9
BODY_MASS_KG = 70.0


def write_binary_stl(path: pathlib.Path, vertices: np.ndarray, normals: np.ndarray) -> None:
    """The 80 byte header, the count, then 50 bytes a triangle."""
    with path.open("wb") as handle:
        handle.write(b"\0" * 80)
        handle.write(struct.pack("<I", vertices.shape[0]))
        for triangle, normal in zip(vertices, normals, strict=True):
            handle.write(np.asarray(normal, dtype="<f4").tobytes())
            handle.write(np.asarray(triangle, dtype="<f4").tobytes())
            handle.write(struct.pack("<H", 0))


def patchwork(count: int = 192, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Triangles facing every direction, with areas spread over two decades.

    Each one is equilateral, placed in its own tangent plane, so the normal is
    exactly the direction it was built from and the area is exactly what the
    scale says. Orientation and area are drawn independently, so nothing about
    the construction favours the outcome.
    """
    rng = np.random.default_rng(seed)
    normal = fibonacci_sphere(count)
    scale = np.exp(rng.uniform(np.log(0.004), np.log(0.4), size=count))
    helper = np.where(np.abs(normal[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    tangent = np.cross(helper, normal)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    bitangent = np.cross(normal, tangent)
    centre = 0.9 * normal
    corner = np.array([0.0, 2.0 * np.pi / 3.0, 4.0 * np.pi / 3.0])
    vertices = np.empty((count, 3, 3))
    for k in range(3):
        vertices[:, k] = centre + scale[:, None] * (np.cos(corner[k]) * tangent + np.sin(corner[k]) * bitangent)
    return vertices, normal


def subdivide(vertices: np.ndarray, normals: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Midpoint split of the masked triangles, four children each.

    The children are coplanar with the parent and tile it exactly, so the
    surface is unchanged down to the rounding of a midpoint. The normal is
    carried over verbatim rather than recomputed, which keeps the two meshes bit
    identical in orientation and leaves area as the only thing that moved.
    """
    a, b, c = vertices[mask, 0], vertices[mask, 1], vertices[mask, 2]
    ab, bc, ca = 0.5 * (a + b), 0.5 * (b + c), 0.5 * (c + a)
    children = np.concatenate(
        [
            np.stack([a, ab, ca], axis=1),
            np.stack([ab, b, bc], axis=1),
            np.stack([ca, bc, c], axis=1),
            np.stack([ab, bc, ca], axis=1),
        ]
    )
    return (
        np.concatenate([vertices[~mask], children]),
        np.concatenate([normals[~mask], np.tile(normals[mask], (4, 1))]),
    )


#: An anisotropic angular spectrum, so the answer depends on which way a
#: triangle faces. An isotropic one would be unbiased by symmetry, which is
#: exactly the blind spot this file exists to avoid.
GRID = fibonacci_sphere(96)
RHO = 0.2 + 2.0 * np.maximum(GRID[:, 2], 0.0) ** 2
SOLID_ANGLE = 4.0 * np.pi / GRID.shape[0]


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    """The same surface, cut two ways, each run through the body coupler."""
    from semantic_twin.exposure import BodyCoupler

    root = tmp_path_factory.mktemp("remesh")
    coarse_v, coarse_n = patchwork()
    fine_v, fine_n = subdivide(coarse_v, coarse_n, coarse_n[:, 2] > 0.0)

    out = []
    for name, vertices, normals in (("coarse", coarse_v, coarse_n), ("fine", fine_v, fine_n)):
        path = root / f"{name}.stl"
        write_binary_stl(path, vertices, normals)
        coupler = BodyCoupler(str(path), FREQUENCY_HZ, level=2, body_mass_kg=BODY_MASS_KG)
        exposure = coupler.couple(GRID, RHO, SOLID_ANGLE, 1.0)
        out.append((coupler, exposure))
    return out


def test_the_remesh_really_did_change_the_tessellation(pair):
    """Guard on the fixture.

    If the two meshes had the same triangle count, or the same area
    distribution, every assertion below would be trivially true.
    """
    (coarse, _), (fine, _) = pair
    assert fine.body.n_triangles > 2 * coarse.body.n_triangles
    assert coarse.body.areas.max() / coarse.body.areas.min() > 1000.0
    # The tolerance is the single precision the STL format stores vertices in,
    # which is the only thing a midpoint split can move.
    assert fine.body.total_area == pytest.approx(coarse.body.total_area, rel=1e-7)


def test_the_absorbed_power_survives_the_remesh(pair):
    """The area weighted total, which the engine already computes correctly.

    This is the positive control. It says the harness can tell a remesh from a
    change of physics, so the failure below is about the reduction and not about
    the mesh, the tissue or the kernel.
    """
    (_, coarse), (_, fine) = pair
    assert fine.absorbed_power_w == pytest.approx(coarse.absorbed_power_w, rel=1e-7)
    assert fine.sar_wb_w_kg == pytest.approx(coarse.sar_wb_w_kg, rel=1e-7)
    assert fine.peak_sab_w_m2 == pytest.approx(coarse.peak_sab_w_m2, rel=1e-9)
    assert fine.susceptibility == pytest.approx(coarse.susceptibility, rel=1e-12)


def test_the_correct_mean_is_already_in_the_result(pair):
    """``p_abs / total_area`` is the surface average and it is remesh invariant.

    Stated separately because it is the value finding 3 says the code should be
    reporting, and because a test that only says the current mean is wrong does
    not say what the right one is.
    """
    (coarse_body, coarse), (fine_body, fine) = pair
    coarse_mean = coarse.absorbed_power_w / coarse_body.body.total_area
    fine_mean = fine.absorbed_power_w / fine_body.body.total_area
    assert fine_mean == pytest.approx(coarse_mean, rel=1e-7)


def test_the_mean_absorbed_density_survives_the_remesh(pair):
    """The average over the body's surface cannot depend on how it was cut.

    The reported mean is the absorbed power divided by the total body area.
    Splitting the illuminated half therefore leaves it unchanged, just like the
    total absorbed power and the peak density.
    """
    (_, coarse), (_, fine) = pair
    assert fine.mean_sab_w_m2 == pytest.approx(coarse.mean_sab_w_m2, rel=1e-6)


def test_synthetic_frame_is_optional_without_route_yaw_but_required_with_it(tmp_path):
    """Native-frame remesh checks must not need an anatomical orientation."""
    vertices, normals = patchwork(count=32, seed=17)
    # Force the synthetic extent's dominant axis away from the standing z axis
    # so AEGIS cannot infer a valid anatomical frame for this mesh.
    vertices[:, :, 1] *= 2.0
    path = tmp_path / "non_anatomical.stl"
    write_binary_stl(path, vertices, normals)

    from semantic_twin.exposure import BodyCoupler

    coupler = BodyCoupler(str(path), FREQUENCY_HZ, level=2, body_mass_kg=BODY_MASS_KG)
    assert coupler.body_anterior_axis is None
    exposure = coupler.couple(GRID, RHO, SOLID_ANGLE, 1.0)
    assert exposure.absorbed_power_w > 0.0
    with pytest.raises(ValueError, match="valid anatomical frame"):
        coupler.couple(GRID, RHO, SOLID_ANGLE, 1.0, body_yaw_deg=0.0)
