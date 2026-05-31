"""Walking-body posers.

Two backends produce a ``BodyMesh`` at a trajectory sample:

- ``SmplxWalkPoser`` is the production path: an SMPL-X body driven by an AMASS
  walking clip, then placed in the world at the agent's position and heading.
- ``StaticPhantomPoser`` is the cheap fallback for the cost-discovery spike and
  for nodes without smplx/torch/AMASS: a static STL phantom translated and
  yaw-rotated along the path.

Both expose the same ``pose(position_xy, heading_rad, z_ground, frame_idx)``.
"""

from __future__ import annotations

import numpy as np

from aegis.geometry.mesh import BodyMesh


def _place(vertices: np.ndarray, heading_rad: float, position_xy, z_ground: float) -> np.ndarray:
    """Yaw-rotate triangle vertices about z, set the xy-centroid to position_xy
    and the lowest point to z_ground. ``vertices`` is (N, 3, 3)."""
    flat = vertices.reshape(-1, 3).copy()
    c, s = np.cos(heading_rad), np.sin(heading_rad)
    rot = np.array([[c, -s], [s, c]])
    flat[:, :2] = flat[:, :2] @ rot.T
    centroid_xy = flat[:, :2].mean(axis=0)
    flat[:, 0] += position_xy[0] - centroid_xy[0]
    flat[:, 1] += position_xy[1] - centroid_xy[1]
    flat[:, 2] += z_ground - flat[:, 2].min()
    return flat.reshape(vertices.shape)


class StaticPhantomPoser:
    """Rigid STL phantom translated and yaw-rotated along the path."""

    def __init__(self, base_mesh: BodyMesh):
        self.base_mesh = base_mesh

    def pose(self, position_xy, heading_rad, z_ground=0.0, frame_idx=0) -> BodyMesh:
        position_xy = np.asarray(position_xy, dtype=float)
        placed = _place(self.base_mesh.vertices, heading_rad, position_xy, z_ground)
        return BodyMesh.from_arrays(placed, name="static_phantom")


class SmplxWalkPoser:
    """SMPL-X body posed from an AMASS walking clip, placed in the world."""

    def __init__(self, clip_path, gender="neutral", betas=None):
        from aegis.geometry.parametric import ParametricBody
        from aegis.geometry.pose_stream import PoseStream

        self.stream = PoseStream.load(clip_path)
        self.body = ParametricBody.load(model_type="smplx", gender=gender)
        self.betas = self.stream.betas[:10] if betas is None else np.asarray(betas)

    def pose(self, position_xy, heading_rad, z_ground=0.0, frame_idx=0) -> BodyMesh:
        position_xy = np.asarray(position_xy, dtype=float)
        # Articulation only; place in the world ourselves so heading is exact.
        local = self.stream.posed_body(frame_idx, self.body, apply_translation=False, betas=self.betas)
        placed = _place(local.vertices, heading_rad, position_xy, z_ground)
        return BodyMesh.from_arrays(placed, name="smplx_walk")
