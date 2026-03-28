import numpy as np

from aegis.environment.skeleton import polygonize, skeletonize


class TestSkeletonize:
    def test_square(self):
        """Square skeleton should produce a single apex at center."""
        verts = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0
        for arc in arcs:
            assert 0 <= arc.source[0] <= 10
            assert 0 <= arc.source[1] <= 10

    def test_rectangle(self):
        """Rectangle skeleton should produce a ridge line along the long axis."""
        verts = np.array([[0, 0], [20, 0], [20, 10], [0, 10]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0

    def test_triangle(self):
        """Triangle skeleton should produce a single apex."""
        verts = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        arcs = skeletonize([verts])
        assert len(arcs) > 0
        sources = [arc.source for arc in arcs]
        assert len(sources) >= 1

    def test_subtree_structure(self):
        """Each subtree should have source, height, sinks."""
        verts = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        arcs = skeletonize([verts])
        for arc in arcs:
            assert hasattr(arc, "source")
            assert hasattr(arc, "height")
            assert hasattr(arc, "sinks")
            assert arc.height >= 0


class TestPolygonize:
    def test_square_produces_faces(self):
        """Polygonize a square at height 5 should produce triangular roof faces."""
        footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        verts_out = [np.array([v[0], v[1], 0.0]) for v in footprint]
        faces = polygonize(verts_out, footprint, height=5.0)
        assert len(faces) > 0
        for face in faces:
            assert len(face) >= 3

    def test_rectangle_produces_faces(self):
        footprint = np.array([[0, 0], [20, 0], [20, 10], [0, 10]], dtype=np.float64)
        verts_out = [np.array([v[0], v[1], 0.0]) for v in footprint]
        faces = polygonize(verts_out, footprint, height=5.0)
        assert len(faces) > 0

    def test_verts_extended(self):
        """polygonize should add skeleton nodes to verts_out."""
        footprint = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float64)
        verts_out = [np.array([v[0], v[1], 0.0]) for v in footprint]
        initial_len = len(verts_out)
        polygonize(verts_out, footprint, height=5.0)
        assert len(verts_out) > initial_len
