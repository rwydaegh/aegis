"""Audit partition of accepted exact order-one specular paths."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum

import numpy as np

from ..materials.evidence_audit import AUDIT_CATEGORY_NAMES, EvidenceAuditCategoryMap
from .specular import SpecularPaths


@dataclass(frozen=True)
class SpecularEvidencePartition:
    """Per-path category labels and exact count/mass closure summaries."""

    category_names: tuple[str, ...]
    path_category: np.ndarray
    barycentric_uv: np.ndarray
    count_by_category: np.ndarray
    transfer_by_category: np.ndarray
    total_count: int
    total_transfer: float
    count_closure_residual: int
    transfer_closure_residual: float

    def __post_init__(self) -> None:
        names = tuple(str(name) for name in self.category_names)
        if names != AUDIT_CATEGORY_NAMES:
            raise ValueError("specular evidence partition must use the canonical category vocabulary")
        raw_path_category = np.asarray(self.path_category)
        if not np.issubdtype(raw_path_category.dtype, np.integer):
            raise ValueError("path categories must contain integer category codes")
        if np.any(raw_path_category < 0) or np.any(raw_path_category >= len(names)):
            raise ValueError("specular evidence partition contains an unknown category code")
        path_category = raw_path_category.astype(np.uint8, copy=False)
        uv = np.asarray(self.barycentric_uv, dtype=np.float64)
        count = np.asarray(self.count_by_category, dtype=np.int64)
        transfer = np.asarray(self.transfer_by_category, dtype=np.float64)
        if path_category.ndim != 1 or uv.shape != (path_category.size, 2):
            raise ValueError("path categories and barycentric UV must be aligned")
        if count.shape != (len(names),) or transfer.shape != count.shape:
            raise ValueError("category totals must have one entry per category")
        if np.any(~np.isfinite(uv)):
            raise ValueError("specular evidence partition contains invalid path data")
        if np.any(count < 0) or np.any(~np.isfinite(transfer)) or np.any(transfer < 0.0):
            raise ValueError("specular category totals must be finite and nonnegative")
        if self.total_count != path_category.size or int(count.sum()) != self.total_count:
            raise ValueError("specular category counts do not close")
        if self.count_closure_residual != 0:
            raise ValueError("specular count closure residual must be zero")
        if not np.isclose(float(transfer.sum(dtype=np.float64)), self.total_transfer, rtol=2e-14, atol=1e-300):
            raise ValueError("specular category transfer does not close")
        object.__setattr__(self, "category_names", names)
        object.__setattr__(self, "path_category", path_category)
        object.__setattr__(self, "barycentric_uv", uv)
        object.__setattr__(self, "count_by_category", count)
        object.__setattr__(self, "transfer_by_category", transfer)

    @property
    def count(self) -> int:
        return self.total_count

    @property
    def transfer(self) -> float:
        return self.total_transfer

    @property
    def accepted_event_count(self) -> np.ndarray:
        """Device/replay spelling for the per-category atom count."""
        return self.count_by_category

    @property
    def contribution_transfer(self) -> np.ndarray:
        """Device/replay spelling for the per-category atom transfer."""
        return self.transfer_by_category

    @property
    def atom_category(self) -> np.ndarray:
        """Device/replay spelling for one category code per accepted atom."""
        return self.path_category

    def as_dict(self) -> dict[str, object]:
        """Return the compact detail record consumed by the replay reporter."""
        return {
            "category_names": list(self.category_names),
            "accepted_event_count": self.accepted_event_count.tolist(),
            "contribution_transfer": self.contribution_transfer.tolist(),
            "atom_category": self.atom_category.tolist(),
            "barycentric_uv": self.barycentric_uv.tolist(),
            "closure": {
                "count": self.count_closure_residual == 0,
                "transfer": abs(self.transfer_closure_residual)
                <= 32.0 * np.finfo(np.float64).eps * max(abs(self.total_transfer), 1.0),
            },
        }


def partition_specular_paths(
    paths: SpecularPaths,
    triangles: np.ndarray,
    categories: EvidenceAuditCategoryMap,
    *,
    strict: bool = True,
) -> SpecularEvidencePartition:
    """Partition accepted paths by exact reflection-point atlas evidence.

    ``paths.surface_sequence[:, 0]`` contains support-mesh face identifiers,
    not a compact local surface index.  ``triangles`` must therefore be the
    original support-mesh triangle array indexed by those identifiers.
    """
    triangle_array = np.asarray(triangles, dtype=np.float64)
    if triangle_array.ndim != 3 or triangle_array.shape[1:] != (3, 3):
        raise ValueError("triangles must have shape (faces, 3, 3)")
    transfer = np.asarray(paths.transfer, dtype=np.float64)
    sequence = np.asarray(paths.surface_sequence, dtype=np.int64)
    reflection = np.asarray(paths.reflection_point, dtype=np.float64)
    count = transfer.size
    if sequence.shape != (count, 1) or reflection.shape != (count, 3):
        raise ValueError("specular path geometry does not match transfer rows")
    if np.any(sequence < 0) or np.any(sequence[:, 0] >= triangle_array.shape[0]):
        raise ValueError("surface_sequence contains a face outside the support triangles")
    if categories.face_to_category_row.size != triangle_array.shape[0]:
        raise ValueError("category face map must match the support triangle count")
    face = sequence[:, 0]
    uv = _barycentric_uv(triangle_array[face], reflection)
    path_category = categories.categories_for_hits(face, uv)
    count_by_category = np.bincount(path_category, minlength=len(categories.names)).astype(np.int64)
    transfer_by_category = np.zeros(len(categories.names), dtype=np.float64)
    np.add.at(transfer_by_category, path_category, transfer)
    total_transfer = fsum(float(value) for value in transfer)
    closure = total_transfer - fsum(float(value) for value in transfer_by_category)
    count_residual = count - int(count_by_category.sum())
    tolerance = 32.0 * np.finfo(np.float64).eps * max(abs(total_transfer), 1.0)
    if strict and (count_residual != 0 or abs(closure) > tolerance):
        raise ValueError(f"specular evidence partition does not close: count={count_residual}, transfer={closure}")
    return SpecularEvidencePartition(
        category_names=categories.names,
        path_category=path_category,
        barycentric_uv=uv,
        count_by_category=count_by_category,
        transfer_by_category=transfer_by_category,
        total_count=count,
        total_transfer=total_transfer,
        count_closure_residual=count_residual,
        transfer_closure_residual=closure,
    )


def _barycentric_uv(triangles: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Compute canonical ``(weight_vertex_1, weight_vertex_2)`` coordinates."""
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    offset = points - triangles[:, 0]
    d11 = np.einsum("ij,ij->i", edge1, edge1)
    d12 = np.einsum("ij,ij->i", edge1, edge2)
    d22 = np.einsum("ij,ij->i", edge2, edge2)
    q1 = np.einsum("ij,ij->i", offset, edge1)
    q2 = np.einsum("ij,ij->i", offset, edge2)
    determinant = d11 * d22 - d12 * d12
    if np.any(determinant <= 1.0e-24):
        raise ValueError("specular reflection support contains a degenerate triangle")
    u = (d22 * q1 - d12 * q2) / determinant
    v = (d11 * q2 - d12 * q1) / determinant
    if np.any(~np.isfinite(u)) or np.any(~np.isfinite(v)):
        raise ValueError("specular reflection barycentric coordinates are not finite")
    tolerance = 2.0e-7
    if np.any(u < -tolerance) or np.any(v < -tolerance) or np.any(u + v > 1.0 + tolerance):
        raise ValueError("specular reflection point lies outside its surface triangle")
    return np.column_stack((np.clip(u, 0.0, 1.0), np.clip(v, 0.0, 1.0)))


__all__ = ["SpecularEvidencePartition", "partition_specular_paths"]
