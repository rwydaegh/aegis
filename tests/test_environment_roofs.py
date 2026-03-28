import numpy as np

from aegis.environment.roofs import extrude_walls, triangulate_polygon


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
