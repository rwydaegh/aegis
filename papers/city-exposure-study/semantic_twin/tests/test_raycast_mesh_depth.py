from __future__ import annotations

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from raycast_mesh_depth import first_hit_range, ground_offset_m  # noqa: E402


def _ground(z: float = 0.0) -> trimesh.Trimesh:
    vertices = np.array([(-10.0, -10.0, z), (10.0, -10.0, z), (10.0, 10.0, z), (-10.0, 10.0, z)])
    return trimesh.Trimesh(vertices=vertices, faces=np.array([(0, 1, 2), (0, 2, 3)]), process=False)


def test_first_hit_reports_euclidean_range_not_axial_depth() -> None:
    mesh = _ground()
    origin = np.array((0.0, 0.0, 3.0))
    slanted = np.array((0.6, 0.0, -0.8))

    range_m, face_ids = first_hit_range(mesh, origin, np.array([(0.0, 0.0, -1.0), slanted]))

    assert range_m[0] == pytest.approx(3.0)
    # The ray drops 3 m over a 0.8 vertical component, so the range is 3.75 m
    # rather than the 3 m an axial depth buffer would report.
    assert range_m[1] == pytest.approx(3.75)
    assert np.all(face_ids >= 0)


def test_an_escaping_ray_is_nan_and_minus_one_rather_than_a_far_plane() -> None:
    range_m, face_ids = first_hit_range(_ground(), np.array((0.0, 0.0, 3.0)), np.array([(0.0, 0.0, 1.0)]))

    assert not np.isfinite(range_m[0])
    assert face_ids[0] == -1


def test_ground_offset_measures_the_camera_height_the_mesh_actually_implies() -> None:
    # The mesh ground sits 1.0 m under a camera that claims a 2.5 m capture
    # height, so the diagnostic asks for a 1.5 m lift.
    mesh = _ground(z=49.0)

    assert ground_offset_m(mesh, np.array((0.0, 0.0, 50.0)), 2.5) == pytest.approx(1.5)

    with pytest.raises(ValueError, match="no support-mesh ground"):
        ground_offset_m(mesh, np.array((0.0, 0.0, 40.0)), 2.5)
