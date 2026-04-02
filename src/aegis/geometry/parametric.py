"""Parametric body model wrapper for SMPL-X and Anny."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from aegis.geometry.mesh import BodyMesh


class ParametricBody:
    """Unified interface for parametric body models (SMPL-X, Anny)."""

    def __init__(self, model, faces: np.ndarray, model_type: str):
        self._model = model
        self._faces = faces  # (F, 3) triangle indices
        self._model_type = model_type

    @staticmethod
    def load(
        model_type: str = "smplx",
        gender: str = "neutral",
        model_path: str | Path | None = None,
    ) -> ParametricBody:
        if model_type == "smplx":
            return _load_smplx(gender, model_path)
        elif model_type == "anny":
            return _load_anny(gender, model_path)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def generate(
        self,
        betas: np.ndarray,
        pose: np.ndarray | None = None,
        name: str = "parametric",
    ) -> BodyMesh:
        import torch

        betas_t = torch.tensor(betas, dtype=torch.float32).unsqueeze(0)
        kwargs: dict = {"betas": betas_t}
        if pose is not None:
            kwargs["body_pose"] = torch.tensor(pose[3:66], dtype=torch.float32).unsqueeze(0)
            kwargs["global_orient"] = torch.tensor(pose[:3], dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            output = self._model(**kwargs)

        verts = output.vertices[0].numpy()  # (V, 3)
        return self._verts_to_body(verts, name)

    def generate_batch(
        self,
        betas_batch: np.ndarray,
        name_prefix: str = "parametric",
    ) -> list[BodyMesh]:
        import torch

        betas_t = torch.tensor(betas_batch, dtype=torch.float32)
        with torch.no_grad():
            output = self._model(betas=betas_t)

        return [self._verts_to_body(output.vertices[i].numpy(), f"{name_prefix}_{i}") for i in range(len(betas_batch))]

    def _verts_to_body(self, verts: np.ndarray, name: str) -> BodyMesh:
        """Convert indexed vertices to triangle soup BodyMesh."""
        tri_verts = verts[self._faces]  # (F, 3, 3)
        e1 = tri_verts[:, 1] - tri_verts[:, 0]
        e2 = tri_verts[:, 2] - tri_verts[:, 0]
        normals = np.cross(e1, e2)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        normals = normals / norms
        return BodyMesh.from_arrays(tri_verts.astype(np.float64), normals, name=name)


def _load_smplx(gender: str, model_path: str | Path | None) -> ParametricBody:
    try:
        import smplx as smplx_pkg
    except ImportError as err:
        raise ImportError("smplx is required for ParametricBody. Install with: pip install aegis[body]") from err
    if model_path is None:
        model_path = Path.home() / ".aegis" / "models" / "smplx"
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"SMPL-X model files not found at {model_path}. "
            "Download from https://smpl-x.is.tue.mpg.de/ and place in ~/.aegis/models/smplx/"
        )
    model = smplx_pkg.create(str(model_path), model_type="smplx", gender=gender)
    faces = model.faces.astype(np.int64)
    return ParametricBody(model, faces, "smplx")


def _load_anny(gender: str, model_path: str | Path | None) -> ParametricBody:
    raise NotImplementedError(
        "Anny model integration pending. Package name and API TBD. See https://europe.naverlabs.com/blog/anny/"
    )
