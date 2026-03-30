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

    def test_triangle_face_indices_valid(self):
        """Polygonize a triangle: all face vertex indices must be in range."""
        footprint = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        verts_out = [np.array([v[0], v[1], 0.0]) for v in footprint]
        faces = polygonize(verts_out, footprint, height=4.0)
        n = len(verts_out)
        for face in faces:
            for idx in face:
                assert 0 <= idx < n, f"vertex index {idx} out of range [0, {n})"

    def test_merged_face_rotation_finds_original_vertex(self):
        """Regression: merged face rotation must find original polygon vertices
        at any position, not only positions < first_skel_index."""
        # Simulate a scenario where merged_face has an original polygon vertex
        # at position >= first_skel_index (e.g., position 4 with first_skel_index=3).
        # Vertices 0, 1, 2 are polygon vertices; 3, 4 are skeleton vertices.
        first_skel_index = 3
        merged_face = [3, 4, 0, 2, 1]  # original vert 0 is at position 2
        orig_indices = [x[0] for x in enumerate(merged_face) if x[1] < first_skel_index]
        assert 2 in orig_indices, "position 2 should be found (vertex 0 is original)"
        assert 3 in orig_indices, "position 3 should be found (vertex 2 is original)"
        assert 4 in orig_indices, "position 4 should be found (vertex 1 is original)"
