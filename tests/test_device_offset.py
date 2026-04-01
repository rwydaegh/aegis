"""Tests for automatic device offset estimation from body meshes."""

import numpy as np

from aegis.geometry.device_offset import _face_direction_y, estimate_device_offset


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

    def _body_vertices_with_nose(self, x_range, y_range, z_range, face_y_sign=1, n_slices=20):
        """Create a body-like mesh with a nose protrusion to break symmetry.

        The nose adds extra triangles on one Y side at eye level, producing
        a clear normal-voting signal for face direction detection.
        """
        base = self._body_vertices(x_range, y_range, z_range, n_slices)

        # Add nose triangles at eye level
        x0, x1 = x_range
        y0, y1 = y_range
        z0, z1 = z_range
        height = z1 - z0
        eye_z = z0 + height * 0.96 - 0.02
        cx = (x0 + x1) / 2  # center X
        nose_w = 0.02  # narrow nose
        nose_depth = 0.03  # protrudes 3cm

        if face_y_sign > 0:
            nose_tip_y = y1 + nose_depth
            base_y = y1
        else:
            nose_tip_y = y0 - nose_depth
            base_y = y0

        # 4 triangles forming a small pyramid nose
        nose_tris = np.array(
            [
                [[cx - nose_w, base_y, eye_z - 0.01], [cx + nose_w, base_y, eye_z - 0.01], [cx, nose_tip_y, eye_z]],
                [[cx + nose_w, base_y, eye_z - 0.01], [cx + nose_w, base_y, eye_z + 0.01], [cx, nose_tip_y, eye_z]],
                [[cx + nose_w, base_y, eye_z + 0.01], [cx - nose_w, base_y, eye_z + 0.01], [cx, nose_tip_y, eye_z]],
                [[cx - nose_w, base_y, eye_z + 0.01], [cx - nose_w, base_y, eye_z - 0.01], [cx, nose_tip_y, eye_z]],
            ]
        )
        return np.concatenate([base, nose_tris], axis=0)

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
        """Works when mesh origin is not at the feet (z_min < 0).

        The offset Z is always ground-relative (feet at z=0), regardless
        of where the mesh origin sits.
        """
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (-0.9, 0.9))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        # Height is 1.8m, eye_z from ground ~ 1.8 * 0.96 - 0.02 = 1.708
        expected_eye_z = 1.8 * 0.96 - 0.02
        assert abs(offset[2] - expected_eye_z) < 0.05

    def test_returns_list_of_three_floats(self):
        """Return type is a list of three Python floats (JSON-serializable)."""
        verts = self._body_vertices((-0.2, 0.2), (-0.1, 0.1), (0.0, 1.8))
        offset = estimate_device_offset(verts, forward_distance=0.30)
        assert isinstance(offset, list)
        assert len(offset) == 3
        assert all(isinstance(v, float) for v in offset)


class TestFaceDirectionDetection:
    """Test face direction auto-detection for +Y and -Y facing phantoms."""

    def _body_with_nose(self, face_y_sign):
        """Body mesh with nose protrusion indicating face direction."""
        x_range = (-0.15, 0.15)
        y_range = (-0.10, 0.10)
        z_range = (0.0, 1.8)
        height = z_range[1] - z_range[0]
        eye_z = z_range[0] + height * 0.96 - 0.02

        # Base box
        n_slices = 20
        zs = np.linspace(*z_range, n_slices + 1)
        triangles = []
        x0, x1 = x_range
        y0, y1 = y_range
        for i in range(len(zs) - 1):
            za, zb = zs[i], zs[i + 1]
            triangles.append([[x0, y1, za], [x1, y1, za], [x1, y1, zb]])
            triangles.append([[x0, y1, za], [x1, y1, zb], [x0, y1, zb]])
            triangles.append([[x0, y0, za], [x1, y0, zb], [x1, y0, za]])
            triangles.append([[x0, y0, za], [x0, y0, zb], [x1, y0, zb]])
            triangles.append([[x0, y0, za], [x0, y1, za], [x0, y1, zb]])
            triangles.append([[x0, y0, za], [x0, y1, zb], [x0, y0, zb]])
            triangles.append([[x1, y0, za], [x1, y1, zb], [x1, y1, za]])
            triangles.append([[x1, y0, za], [x1, y0, zb], [x1, y1, zb]])

        # Add nose protrusion at eye level on the face side
        cx = 0.0
        nose_w = 0.02
        nose_depth = 0.04
        if face_y_sign > 0:
            base_y, tip_y = y1, y1 + nose_depth
        else:
            base_y, tip_y = y0, y0 - nose_depth

        nose_tris = [
            [[cx - nose_w, base_y, eye_z - 0.01], [cx + nose_w, base_y, eye_z - 0.01], [cx, tip_y, eye_z]],
            [[cx + nose_w, base_y, eye_z - 0.01], [cx + nose_w, base_y, eye_z + 0.01], [cx, tip_y, eye_z]],
            [[cx + nose_w, base_y, eye_z + 0.01], [cx - nose_w, base_y, eye_z + 0.01], [cx, tip_y, eye_z]],
            [[cx - nose_w, base_y, eye_z + 0.01], [cx - nose_w, base_y, eye_z - 0.01], [cx, tip_y, eye_z]],
        ]
        all_tris = np.array(triangles + nose_tris)
        return all_tris, eye_z

    def test_detects_positive_y_face(self):
        """Face pointing +Y should produce face_sign = +1."""
        tris, eye_z = self._body_with_nose(face_y_sign=+1)
        assert _face_direction_y(tris, eye_z) == 1.0

    def test_detects_negative_y_face(self):
        """Face pointing -Y should produce face_sign = -1."""
        tris, eye_z = self._body_with_nose(face_y_sign=-1)
        assert _face_direction_y(tris, eye_z) == -1.0

    def test_negative_y_phone_placed_in_front(self):
        """For a -Y-facing body, device Y should be LESS than the face surface."""
        tris, _ = self._body_with_nose(face_y_sign=-1)
        offset = estimate_device_offset(tris, forward_distance=0.30)
        # Face is at -Y, so device should be at even more negative Y
        # The 3rd percentile of Y at eye level is near -0.10 (body boundary)
        # Device should be at approximately -0.10 - 0.30 = -0.40
        assert offset[1] < -0.30, f"device_y={offset[1]:.3f}, expected < -0.30 for -Y face"

    def test_positive_y_phone_placed_in_front(self):
        """For a +Y-facing body, device Y should be greater than the face surface."""
        tris, _ = self._body_with_nose(face_y_sign=+1)
        offset = estimate_device_offset(tris, forward_distance=0.30)
        assert offset[1] > 0.30, f"device_y={offset[1]:.3f}, expected > 0.30 for +Y face"

    def test_symmetry_of_forward_distance(self):
        """Phone distance from face surface should be the same regardless of face direction."""
        tris_pos, _ = self._body_with_nose(face_y_sign=+1)
        tris_neg, _ = self._body_with_nose(face_y_sign=-1)
        fwd = 0.30
        offset_pos = estimate_device_offset(tris_pos, forward_distance=fwd)
        offset_neg = estimate_device_offset(tris_neg, forward_distance=fwd)
        # The absolute distance from body center (y=0) should be similar
        assert abs(abs(offset_pos[1]) - abs(offset_neg[1])) < 0.05
