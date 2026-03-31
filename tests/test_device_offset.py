"""Tests for automatic device offset estimation from body meshes."""

import numpy as np

from aegis.geometry.device_offset import estimate_device_offset


class TestEstimateDeviceOffset:
    """Test eye detection and device offset computation."""

    def _body_vertices(self, x_range, y_range, z_range, n_slices=20):
        """Create a body-like mesh with vertices spread across the height.

        Stacks horizontal quad strips so there are vertices at every
        height level, not just at the top and bottom corners.
        """
        x0, x1 = x_range
        y0, y1 = y_range
        z0, z1 = z_range
        zs = np.linspace(z0, z1, n_slices + 1)
        triangles = []
        for i in range(len(zs) - 1):
            za, zb = zs[i], zs[i + 1]
            # Two quads (front and back faces), each split into 2 triangles
            # Front face (y = y1)
            triangles.append([[x0, y1, za], [x1, y1, za], [x1, y1, zb]])
            triangles.append([[x0, y1, za], [x1, y1, zb], [x0, y1, zb]])
            # Back face (y = y0)
            triangles.append([[x0, y0, za], [x1, y0, zb], [x1, y0, za]])
            triangles.append([[x0, y0, za], [x0, y0, zb], [x1, y0, zb]])
            # Left face (x = x0)
            triangles.append([[x0, y0, za], [x0, y1, za], [x0, y1, zb]])
            triangles.append([[x0, y0, za], [x0, y1, zb], [x0, y0, zb]])
            # Right face (x = x1)
            triangles.append([[x1, y0, za], [x1, y1, zb], [x1, y1, za]])
            triangles.append([[x1, y0, za], [x1, y0, zb], [x1, y1, zb]])
        return np.array(triangles)  # (N, 3, 3)

    def test_device_z_near_eye_height(self):
        """Device Z should be near 96% of body height."""
        # Upright body: 1.8m tall, centered at x=0, face at y=0.1
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        expected_eye_z = 1.8 * 0.96 - 0.02
        assert abs(offset[2] - expected_eye_z) < 0.05

    def test_device_y_includes_forward_distance(self):
        """Device Y should be face surface + forward_distance."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.15), (0.0, 1.8))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        # Face front is at y ~ 0.15, so device y ~ 0.45
        assert offset[1] > 0.40
        assert offset[1] < 0.55

    def test_device_x_centered(self):
        """Device X should be near the face center, not offset to the side."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        assert abs(offset[0]) < 0.05

    def test_different_heights(self):
        """Shorter phantoms should produce lower device Z."""
        tall = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        short = self._body_vertices((-0.15, 0.15), (-0.08, 0.08), (0.0, 1.1))
        tall_offset = estimate_device_offset(tall, forward_distance=0.30)
        short_offset = estimate_device_offset(short, forward_distance=0.30)
        assert tall_offset[2] > short_offset[2]

    def test_custom_forward_distance(self):
        """Forward distance parameter should change device Y."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        close = estimate_device_offset(verts, forward_distance=0.20)
        far = estimate_device_offset(verts, forward_distance=0.40)
        assert far[1] > close[1]
        assert abs((far[1] - close[1]) - 0.20) < 0.02

    def test_offset_below_body_origin(self):
        """Works when mesh origin is not at the feet (z_min < 0)."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (-0.9, 0.9))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        # Height is 1.8m, eye_z from ground ~ 1.8 * 0.96 - 0.02 = 1.708
        # But feet are at z=-0.9, so absolute eye_z = -0.9 + 1.708 = 0.808
        expected_eye_z = -0.9 + 1.8 * 0.96 - 0.02
        assert abs(offset[2] - expected_eye_z) < 0.05

    def test_returns_list_of_three_floats(self):
        """Return type is a list of three Python floats (JSON-serializable)."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        assert isinstance(offset, list)
        assert len(offset) == 3
        assert all(isinstance(v, float) for v in offset)
