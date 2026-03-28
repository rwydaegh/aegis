import numpy as np
import pytest

from aegis.environment import MaterialType
from aegis.environment.roofs import extrude_walls, generate_building, triangulate_polygon

SQUARE = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
RECTANGLE = np.array([[0, 0], [20, 0], [20, 10], [0, 10]], dtype=np.float64)
ROOF_TYPES = [
    "flat",
    "gabled",
    "hipped",
    "pyramidal",
    "skillion",
    "half_hipped",
    "gambrel",
    "saltbox",
    "mansard",
    "dome",
    "onion",
    "round",
]


class TestTriangulatePolygon:
    def test_triangle_returns_itself(self):
        poly = np.array([[0, 0], [1, 0], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        assert tris.shape == (1, 3)
        np.testing.assert_array_equal(tris[0], [0, 1, 2])

    def test_square(self):
        poly = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        assert tris.shape == (2, 3)
        assert tris.min() >= 0
        assert tris.max() <= 3

    def test_pentagon(self):
        angles = np.linspace(0, 2 * np.pi, 6)[:-1]
        poly = np.column_stack([np.cos(angles), np.sin(angles)])
        tris = triangulate_polygon(poly)
        assert tris.shape == (3, 3)  # n-2 triangles

    def test_ccw_winding(self):
        """All output triangles should have CCW winding (positive signed area)."""
        poly = np.array([[0, 0], [2, 0], [2, 1], [1, 2], [0, 1]], dtype=np.float64)
        tris = triangulate_polygon(poly)
        for tri in tris:
            a, b, c = poly[tri[0]], poly[tri[1]], poly[tri[2]]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            assert cross > 0, f"Triangle {tri} has CW winding"


class TestExtrudeWalls:
    def test_square_building_walls(self):
        footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        verts, tris = extrude_walls(footprint, base_height=0.0, top_height=5.0)
        assert verts.shape[0] == 16  # 4 walls * 4 verts
        assert verts.shape[1] == 3
        assert tris.shape[0] == 8  # 4 walls * 2 tris
        z_vals = np.unique(verts[:, 2])
        np.testing.assert_allclose(sorted(z_vals), [0.0, 5.0])

    def test_triangle_building_walls(self):
        footprint = np.array([[0, 0], [5, 0], [2.5, 4]], dtype=np.float64)
        verts, tris = extrude_walls(footprint, base_height=0.0, top_height=3.0)
        assert verts.shape[0] == 12  # 3 walls * 4 verts
        assert tris.shape[0] == 6  # 3 walls * 2 tris


class TestGenerateBuilding:
    @pytest.mark.parametrize("roof_shape", ROOF_TYPES)
    def test_produces_valid_mesh(self, roof_shape):
        footprint = RECTANGLE if roof_shape in ("gabled", "saltbox", "round") else SQUARE
        verts, tris, mats = generate_building(
            footprint=footprint,
            height=10.0,
            roof_shape=roof_shape,
            roof_height=3.0,
        )
        assert verts.ndim == 2 and verts.shape[1] == 3
        assert tris.ndim == 2 and tris.shape[1] == 3
        assert mats.ndim == 1
        assert len(mats) == len(tris)
        assert tris.max() < len(verts)
        assert tris.min() >= 0

    @pytest.mark.parametrize("roof_shape", ROOF_TYPES)
    def test_normals_nonzero(self, roof_shape):
        footprint = RECTANGLE if roof_shape in ("gabled", "saltbox", "round") else SQUARE
        verts, tris, mats = generate_building(
            footprint=footprint,
            height=10.0,
            roof_shape=roof_shape,
        )
        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        normals = np.cross(v1 - v0, v2 - v0)
        areas = np.linalg.norm(normals, axis=1)
        assert np.all(areas > 1e-10), f"Degenerate triangles in {roof_shape}"

    def test_flat_roof_height(self):
        verts, tris, mats = generate_building(
            footprint=SQUARE,
            height=10.0,
            roof_shape="flat",
        )
        assert verts[:, 2].max() == pytest.approx(10.0)

    def test_gabled_roof_ridge_above_eave(self):
        verts, tris, mats = generate_building(
            footprint=RECTANGLE,
            height=10.0,
            roof_shape="gabled",
            roof_height=3.0,
        )
        assert verts[:, 2].max() == pytest.approx(13.0, abs=0.5)

    def test_material_assignment(self):
        verts, tris, mats = generate_building(
            footprint=SQUARE,
            height=10.0,
            roof_shape="flat",
            material=MaterialType.BRICK,
            roof_material=MaterialType.CONCRETE,
        )
        assert MaterialType.BRICK in mats
        assert MaterialType.CONCRETE in mats
