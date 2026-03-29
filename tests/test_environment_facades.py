"""Tests for facade decomposition with window and door openings."""

from __future__ import annotations

import numpy as np

from aegis.environment import MaterialType
from aegis.environment.facades import decompose_facade, generate_detailed_building
from aegis.environment.styles import BuildingStyle, WindowParams

QUAD = np.array([[0, 0], [10, 0], [10, 8], [0, 8]], dtype=np.float64)


def test_decompose_facade_produces_wall_and_windows():
    """A 10m wide, 3m tall facade should have windows."""
    style = BuildingStyle(window=WindowParams(width=1.2, margin_left=1.0, margin_right=1.0))
    geo = decompose_facade(
        start=np.array([0, 0]),
        end=np.array([10, 0]),
        z_bottom=0.0,
        z_top=3.0,
        style=style,
        is_ground=True,
        seed=0,
    )
    assert geo.wall_verts.shape[0] > 0
    assert geo.window_verts.shape[0] > 0


def test_narrow_facade_no_windows():
    """A 2m facade can't fit a 3.2m window slot."""
    style = BuildingStyle(window=WindowParams(width=1.2, margin_left=1.0, margin_right=1.0))
    geo = decompose_facade(
        start=np.array([0, 0]),
        end=np.array([2, 0]),
        z_bottom=0.0,
        z_top=3.0,
        style=style,
        is_ground=False,
        seed=0,
    )
    assert geo.window_verts.shape[0] == 0


def test_ground_floor_has_door():
    style = BuildingStyle(has_ground_floor_doors=True)
    geo = decompose_facade(
        start=np.array([0, 0]),
        end=np.array([10, 0]),
        z_bottom=0.0,
        z_top=3.5,
        style=style,
        is_ground=True,
        seed=0,
    )
    assert geo.door_verts.shape[0] > 0


def test_detailed_building_more_triangles_than_simple():
    from aegis.environment.roofs import generate_building

    simple_v, simple_t, simple_m = generate_building(QUAD, height=9.0, roof_shape="flat", material=MaterialType.BRICK)
    det_v, det_t, det_m = generate_detailed_building(QUAD, height=9.0, roof_shape="flat", material=MaterialType.BRICK)
    assert det_t.shape[0] > simple_t.shape[0]


def test_detailed_building_valid_mesh():
    verts, tris, mats = generate_detailed_building(QUAD, height=12.0, roof_shape="gabled")
    assert tris.max() < len(verts)
    assert np.all(np.isfinite(verts))


def test_detailed_building_has_glass_material():
    verts, tris, mats = generate_detailed_building(QUAD, height=9.0, roof_shape="flat")
    assert MaterialType.GLASS in mats
