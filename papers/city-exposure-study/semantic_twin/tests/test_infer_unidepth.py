from __future__ import annotations

import numpy as np

from infer_unidepth import pinhole_intrinsics
from infer_depth_anything import axial_depth_to_ray_range


def test_pinhole_intrinsics_for_square_90_degree_crop() -> None:
    intrinsics = pinhole_intrinsics(1024, 1024)
    np.testing.assert_allclose(intrinsics, [[512.0, 0.0, 512.0], [0.0, 512.0, 512.0], [0.0, 0.0, 1.0]])


def test_pinhole_intrinsics_preserves_horizontal_field_of_view() -> None:
    intrinsics = pinhole_intrinsics(1920, 1080)
    np.testing.assert_allclose(intrinsics[0, 0], 960.0)
    np.testing.assert_allclose(intrinsics[1, 1], 960.0)


def test_axial_depth_is_converted_to_longer_corner_ray_range() -> None:
    ranges = axial_depth_to_ray_range(np.full((2, 2), 10.0, dtype=np.float32))
    assert np.all(ranges > 10.0)
