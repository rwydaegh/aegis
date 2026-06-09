"""Parametric body model wrapper for SMPL-X and Anny."""

from __future__ import annotations

import functools
import threading
from collections import OrderedDict
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
        # Loading a parametric model reads a ~120 MB .npz and constructs a torch
        # nn.Module, which costs hundreds of ms. The model is read-only across
        # forward passes, so the built object is cached per (type, gender, path).
        # Without this the viewer rebuilt the model on every slider tick (twice,
        # since /api/parametric-body and /api/lab/compute each loaded it).
        key = str(Path(model_path)) if model_path is not None else None
        return _load_cached(model_type, gender, key)

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
        # smplx fixes batch_size at model construction, so a single forward
        # over (N, 10) betas with a batch_size=1 model fails inside lbs. Loop
        # over per-body generate() calls; the test surface is small and
        # plaza_run drives bodies one at a time anyway (each has its own pose).
        return [self.generate(betas_batch[i], name=f"{name_prefix}_{i}") for i in range(len(betas_batch))]

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


@functools.lru_cache(maxsize=6)
def _load_cached(model_type: str, gender: str, model_path: str | None) -> ParametricBody:
    """Cached model construction. Key is hashable (str/None), one entry per gender."""
    if model_type == "smplx":
        return _load_smplx(gender, model_path)
    elif model_type == "anny":
        return _load_anny(gender, model_path)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


# Posed-body cache. The lab re-poses the body on /api/parametric-body (for the
# visible mesh) and again on /api/lab/compute (for dose); a pure source/physics
# edit re-poses with the identical (gender, betas, pose), so caching the result
# means the second call and every same-pose recompute skip the torch forward
# pass entirely. Keyed by exact float bytes (the frontend resends the same
# vectors), bounded with FIFO eviction.
_POSED_CACHE: OrderedDict[tuple, BodyMesh] = OrderedDict()
_POSED_CACHE_MAX = 8
_POSED_CACHE_LOCK = threading.Lock()


def _pose_key(arr: np.ndarray | None) -> bytes | None:
    if arr is None:
        return None
    return np.asarray(arr, dtype=np.float64).tobytes()


def generate_posed(
    model_type: str,
    gender: str,
    betas: np.ndarray,
    pose: np.ndarray | None = None,
    name: str = "parametric",
    model_path: str | Path | None = None,
) -> BodyMesh:
    """Generate a posed body, reusing a cached result for identical inputs.

    Shared by /api/parametric-body and the Exposure Lab dose route so a single
    SMPL-X forward pass serves both, and same-pose recomputes are torch-free.
    """
    key = (model_type, gender, _pose_key(betas), _pose_key(pose))
    with _POSED_CACHE_LOCK:
        cached = _POSED_CACHE.get(key)
        if cached is not None:
            _POSED_CACHE.move_to_end(key)
            return cached
    # Build outside the lock: the torch forward pass is slow and two threads
    # racing on a fresh pose just duplicate work once, which is cheaper than
    # serialising every generate behind one mutex.
    body = ParametricBody.load(model_type, gender, model_path).generate(betas, pose=pose, name=name)
    with _POSED_CACHE_LOCK:
        _POSED_CACHE[key] = body
        while len(_POSED_CACHE) > _POSED_CACHE_MAX:
            _POSED_CACHE.popitem(last=False)
    return body


def _load_smplx(gender: str, model_path: str | Path | None) -> ParametricBody:
    try:
        import smplx as smplx_pkg
    except ImportError as err:
        raise ImportError("smplx is required for ParametricBody. Install with: pip install aegis[body]") from err
    if model_path is None:
        model_path = Path.home() / ".aegis" / "models"
    model_path = Path(model_path)
    npz = model_path / "smplx" / f"SMPLX_{gender.upper()}.npz"
    if not npz.exists():
        raise FileNotFoundError(
            f"SMPL-X model file not found at {npz}. "
            "Register at https://smpl-x.is.tue.mpg.de/, download models_smplx_v1_1.zip, "
            "and run: python scripts/fetch_smplx.py <path/to/zip>"
        )
    model = smplx_pkg.create(str(model_path), model_type="smplx", gender=gender)
    faces = model.faces.astype(np.int64)
    return ParametricBody(model, faces, "smplx")


def _load_anny(gender: str, model_path: str | Path | None) -> ParametricBody:
    raise NotImplementedError(
        "Anny model integration pending. Package name and API TBD. See https://europe.naverlabs.com/blog/anny/"
    )
