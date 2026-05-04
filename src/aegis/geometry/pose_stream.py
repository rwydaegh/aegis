"""Pose stream loader.

A PoseStream is a per-body recording of axis-angle pose vectors and root
translations at a fixed frame rate (30 Hz by convention), produced by the
AMASS ingest in ``scripts/ingest_amass.py``. Brief 08 (plaza_run) consumes
one stream per body and walks frames at the scenario cadence.

The on-disk format is a NumPy ``.npz`` with keys:

    poses  (N, P)  axis-angle pose params, P >= 66 (root + 21 body joints)
    trans  (N, 3)  root translation per frame, metres
    betas  (B,)    body-shape coefficients, B in {10, 16}
    gender ()      utf-8 string: 'neutral' | 'male' | 'female'
    fps    ()      int, target frame rate (always 30 after ingest)
    source ()      utf-8 string: provenance hint, e.g. "CMU/01/01_01"

Only the first 66 pose params (root + body) feed SMPL-X's
``global_orient`` and ``body_pose``; hand / face / eye params are kept
on disk but ignored on load.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from aegis.geometry.mesh import BodyMesh
    from aegis.geometry.parametric import ParametricBody


@dataclass(frozen=True)
class PoseStream:
    """One body's pose trajectory at a fixed frame rate."""

    poses: np.ndarray
    trans: np.ndarray
    betas: np.ndarray
    gender: str
    fps: int
    source: str

    def __post_init__(self) -> None:
        if self.poses.ndim != 2 or self.poses.shape[1] < 66:
            raise ValueError(f"poses must be (N, P>=66); got {self.poses.shape}")
        if self.trans.shape != (self.poses.shape[0], 3):
            raise ValueError(f"trans must be (N, 3) matching poses; got {self.trans.shape} vs N={self.poses.shape[0]}")
        if self.betas.ndim != 1:
            raise ValueError(f"betas must be 1-D; got shape {self.betas.shape}")

    def __len__(self) -> int:
        return int(self.poses.shape[0])

    @classmethod
    def load(cls, path: str | Path) -> PoseStream:
        path = Path(path)
        with np.load(path, allow_pickle=False) as f:
            poses = np.asarray(f["poses"], dtype=np.float64)
            trans = np.asarray(f["trans"], dtype=np.float64)
            betas = np.asarray(f["betas"], dtype=np.float64)
            gender = str(f["gender"])
            fps = int(f["fps"])
            source = str(f["source"])
        return cls(poses=poses, trans=trans, betas=betas, gender=gender, fps=fps, source=source)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            poses=self.poses.astype(np.float32),
            trans=self.trans.astype(np.float32),
            betas=self.betas.astype(np.float32),
            gender=np.array(self.gender),
            fps=np.array(self.fps, dtype=np.int32),
            source=np.array(self.source),
        )

    def frame(self, i: int, *, loop: bool = True) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(pose, trans)`` for frame ``i``.

        With ``loop=True`` (default) the index wraps around so a short trace
        can drive an arbitrarily long scenario. With ``loop=False`` an index
        beyond the recorded length raises ``IndexError``.
        """
        n = len(self)
        if loop:
            j = i % n
        else:
            if i < 0 or i >= n:
                raise IndexError(f"frame {i} out of range for stream of length {n}")
            j = i
        return self.poses[j].copy(), self.trans[j].copy()

    def posed_body(
        self,
        i: int,
        body: ParametricBody,
        *,
        loop: bool = True,
        apply_translation: bool = True,
        name: str | None = None,
        betas: np.ndarray | None = None,
    ) -> BodyMesh:
        """Return a posed mesh for frame ``i``.

        ``body`` is a loaded ParametricBody (typically SMPL-X). By default
        the stream's own ``betas`` drive shape — pass ``betas`` to override.
        Translation is applied to the returned mesh's vertices unless
        ``apply_translation=False``.
        """
        pose, t = self.frame(i, loop=loop)
        used_betas = betas if betas is not None else self.betas
        if used_betas.shape[0] < 10:
            raise ValueError(f"betas must have >=10 entries; got {used_betas.shape}")
        used_betas = used_betas[:10]
        mesh_name = name or f"{self.source}_{i:05d}"
        mesh = body.generate(betas=used_betas, pose=pose[:66], name=mesh_name)
        if apply_translation:
            from aegis.geometry.mesh import BodyMesh

            verts = mesh.vertices + t
            return BodyMesh.from_arrays(verts, mesh.normals, name=mesh_name)
        return mesh


def resample_axis_angle(
    poses: np.ndarray,
    trans: np.ndarray,
    src_fps: float,
    target_fps: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Linear-interpolate pose and translation tracks onto a new frame rate.

    Linear interpolation in axis-angle space is not strictly geodesic on SO(3),
    but for downsampling from 60-120 Hz mocap to 30 Hz the per-frame angle
    delta is small enough (a few degrees) that the lerp/slerp gap is well
    below mocap noise. Translation is genuinely linear so it's fine.
    """
    if poses.shape[0] != trans.shape[0]:
        raise ValueError(f"poses and trans must have same N; got {poses.shape[0]} vs {trans.shape[0]}")
    if src_fps <= 0 or target_fps <= 0:
        raise ValueError(f"fps must be positive; got src={src_fps}, target={target_fps}")
    n_src = poses.shape[0]
    if n_src < 2:
        return poses.copy(), trans.copy()
    duration = (n_src - 1) / src_fps
    n_target = max(2, int(round(duration * target_fps)) + 1)
    src_t = np.arange(n_src) / src_fps
    target_t = np.linspace(0.0, duration, n_target)
    out_poses = np.empty((n_target, poses.shape[1]), dtype=np.float64)
    for d in range(poses.shape[1]):
        out_poses[:, d] = np.interp(target_t, src_t, poses[:, d])
    out_trans = np.empty((n_target, 3), dtype=np.float64)
    for d in range(3):
        out_trans[:, d] = np.interp(target_t, src_t, trans[:, d])
    return out_poses, out_trans
