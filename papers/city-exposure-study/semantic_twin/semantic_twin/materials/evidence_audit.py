"""Ray-reached material-evidence categories.

The production atlas already has a small number of gates.  This module gives
those gates a stable, audit-only integer vocabulary.  It deliberately does
not infer a finer provenance from a posterior that did not retain one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .atlas import (
    FALLBACK_BOUND,
)
from .atlas_binding import MIN_INTERFACE_POSTERIOR, AtlasMaterialBinding


# Keep this order append-only.  Device and CSV consumers use the integer codes
# as a compact interchange format.
AUDIT_CATEGORY_NAMES = (
    "atlas_interface",
    "nonblocking_woody_atlas",
    "geometric_no_panorama_evidence",
    "geometric_evidence_refused_host_compatibility",
    "geometric_evidence_refused_atlas_state",
    "geometric_evidence_refused_insufficient_structural_mass",
    "geometric_fallback_other",
)

ATLAS_INTERFACE = 0
NONBLOCKING_WOODY_ATLAS = 1
GEOMETRIC_NO_PANORAMA_EVIDENCE = 2
GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY = 3
GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE = 4
GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS = 5
GEOMETRIC_FALLBACK_OTHER = 6

# Short aliases for callers that prefer the category role over the persisted
# report vocabulary.  The integer values and names above remain canonical.
EVIDENCE_REFUSAL_HOST_COMPATIBILITY = GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY
EVIDENCE_REFUSAL_ATLAS_STATE = GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE
EVIDENCE_REFUSAL_INSUFFICIENT_STRUCTURAL_MASS = GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS
FALLBACK_OTHER = GEOMETRIC_FALLBACK_OTHER


def _category_code(name: str) -> int:
    try:
        return AUDIT_CATEGORY_NAMES.index(name)
    except ValueError as error:
        raise ValueError(f"unknown evidence-audit category {name!r}") from error


@dataclass(frozen=True)
class EvidenceAuditCategoryMap:
    """Category lookup arrays shared by host and device audit paths.

    ``face_to_category_row`` maps a support-mesh face to the first axis of
    ``category_by_texel`` and uses ``-1`` for a face with no panorama atlas
    row.  ``fallback_category_by_face`` is used for an invalid or unavailable
    texel lookup.  Both arrays use the stable integer vocabulary in
    :data:`AUDIT_CATEGORY_NAMES`.
    """

    names: tuple[str, ...]
    face_to_category_row: np.ndarray
    category_by_texel: np.ndarray
    fallback_category_by_face: np.ndarray

    def __post_init__(self) -> None:
        names = tuple(str(name) for name in self.names)
        if names != AUDIT_CATEGORY_NAMES:
            raise ValueError("evidence-audit category names must use the canonical append-only vocabulary")
        face_to_row = np.asarray(self.face_to_category_row, dtype=np.int64)
        raw_categories = np.asarray(self.category_by_texel)
        raw_fallback = np.asarray(self.fallback_category_by_face)
        for value, label in ((raw_categories, "category_by_texel"), (raw_fallback, "fallback_category_by_face")):
            if not np.issubdtype(value.dtype, np.integer):
                raise ValueError(f"{label} must contain integer category codes")
            if np.any(value < 0) or np.any(value >= len(names)):
                raise ValueError(f"{label} contains an unknown category code")
        categories = raw_categories.astype(np.uint8, copy=False)
        fallback = raw_fallback.astype(np.uint8, copy=False)
        if face_to_row.ndim != 1 or fallback.shape != face_to_row.shape:
            raise ValueError("face category arrays must be aligned one-dimensional vectors")
        if categories.ndim != 3:
            raise ValueError("category_by_texel must have shape (atlas_rows, height, width)")
        if np.any(face_to_row < -1) or np.any(face_to_row >= categories.shape[0]):
            raise ValueError("face_to_category_row leaves the category atlas")
        object.__setattr__(self, "names", names)
        object.__setattr__(self, "face_to_category_row", face_to_row)
        object.__setattr__(self, "category_by_texel", categories)
        object.__setattr__(self, "fallback_category_by_face", fallback)

    @property
    def category_count(self) -> int:
        return len(self.names)

    @property
    def category_names(self) -> tuple[str, ...]:
        """Alias used by the device and replay detail contracts."""
        return self.names

    def categories_for_hits(self, face: np.ndarray, barycentric_uv: np.ndarray) -> np.ndarray:
        """Classify hits using the exact atlas nearest-texel convention.

        ``barycentric_uv`` contains weights of triangle vertices one and two,
        matching :meth:`AtlasMaterialBinding.lookup` and Mitsuba ``prim_uv``.
        """
        face = np.asarray(face, dtype=np.int64)
        uv = np.asarray(barycentric_uv, dtype=np.float64)
        if face.ndim != 1 or uv.shape != (face.size, 2):
            raise ValueError("face and barycentric_uv must have shapes (hits,) and (hits, 2)")
        if np.any(face < 0) or np.any(face >= self.face_to_category_row.size):
            raise ValueError("face contains an index outside the support mesh")
        if not np.all(np.isfinite(uv)):
            raise ValueError("barycentric coordinates must be finite")
        if np.any(uv < -1.0e-5) or np.any(uv.sum(axis=1) > 1.0 + 1.0e-5):
            raise ValueError("barycentric coordinates must lie in the canonical triangle")
        result = self.fallback_category_by_face[face].copy()
        row = self.face_to_category_row[face]
        present = row >= 0
        if not np.any(present):
            return result
        atlas_row, texel_row, texel_column = _texel_lookup(row[present], uv[present], self.category_by_texel.shape[1:])
        result[np.flatnonzero(present)] = self.category_by_texel[atlas_row, texel_row, texel_column]
        return result


@dataclass(frozen=True)
class RayReachedEvidenceClassifier:
    """Serializable-facing wrapper around :class:`EvidenceAuditCategoryMap`.

    The wrapper keeps the three dense arrays as direct attributes so device
    adapters can consume it without importing the host atlas implementation.
    ``from_files`` is an audit-only loader.  It never changes transport
    material binding or any sealed campaign output.
    """

    names: tuple[str, ...]
    face_to_category_row: np.ndarray
    category_by_texel: np.ndarray
    fallback_category_by_face: np.ndarray
    atlas_npz: Path | None = None

    def __post_init__(self) -> None:
        category_map = EvidenceAuditCategoryMap(
            names=self.names,
            face_to_category_row=self.face_to_category_row,
            category_by_texel=self.category_by_texel,
            fallback_category_by_face=self.fallback_category_by_face,
        )
        object.__setattr__(self, "names", category_map.names)
        object.__setattr__(self, "face_to_category_row", category_map.face_to_category_row)
        object.__setattr__(self, "category_by_texel", category_map.category_by_texel)
        object.__setattr__(self, "fallback_category_by_face", category_map.fallback_category_by_face)
        if self.atlas_npz is not None:
            object.__setattr__(self, "atlas_npz", Path(self.atlas_npz).resolve())

    @property
    def category_names(self) -> tuple[str, ...]:
        return self.names

    @property
    def category_count(self) -> int:
        return len(self.names)

    @property
    def resolution(self) -> tuple[int, int]:
        return tuple(int(value) for value in self.category_by_texel.shape[1:])

    @classmethod
    def from_category_map(
        cls,
        category_map: EvidenceAuditCategoryMap,
        *,
        atlas_npz: Path | None = None,
    ) -> "RayReachedEvidenceClassifier":
        return cls(
            names=category_map.names,
            face_to_category_row=category_map.face_to_category_row,
            category_by_texel=category_map.category_by_texel,
            fallback_category_by_face=category_map.fallback_category_by_face,
            atlas_npz=atlas_npz,
        )

    @classmethod
    def from_files(
        cls,
        atlas_npz: Path,
        binding: AtlasMaterialBinding,
        *,
        geometric_class: np.ndarray,
        expected_mesh_sha256: str | None = None,
    ) -> "RayReachedEvidenceClassifier":
        """Load one authenticated joint atlas and classify its bound cells."""
        from .atlas import JointSemanticMaterialAtlas

        path = Path(atlas_npz).resolve()
        atlas = JointSemanticMaterialAtlas.load(path, expected_mesh_sha256=expected_mesh_sha256)
        category_map = classify_joint_atlas(binding, atlas=atlas, geometric_class=geometric_class)
        return cls.from_category_map(category_map, atlas_npz=path)

    def categories_for_hits(self, face: np.ndarray, barycentric_uv: np.ndarray) -> np.ndarray:
        return EvidenceAuditCategoryMap(
            names=self.names,
            face_to_category_row=self.face_to_category_row,
            category_by_texel=self.category_by_texel,
            fallback_category_by_face=self.fallback_category_by_face,
        ).categories_for_hits(face, barycentric_uv)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category_names": list(self.names),
            "category_count": self.category_count,
            "resolution": list(self.resolution),
            "face_count": int(self.face_to_category_row.size),
            "atlas_npz": None if self.atlas_npz is None else str(self.atlas_npz),
        }


def classify_joint_atlas(
    binding: AtlasMaterialBinding,
    *,
    atlas: Any,
    geometric_class: np.ndarray,
) -> EvidenceAuditCategoryMap:
    """Build the audit map from the original atlas gates.

    ``geometric_class`` must be the exact support-mesh face class passed to
    :func:`bind_surface_atlas`. Recomputing the host gate is essential because
    the atlas fallback state alone cannot identify a host-compatibility
    refusal for the final geometric class.
    """
    supported = np.asarray(binding.supported, dtype=bool)
    nonblocking = np.asarray(binding.nonblocking, dtype=bool)
    valid = np.asarray(binding.valid_texels, dtype=bool)
    if supported.shape != nonblocking.shape or supported.shape[1:] != valid.shape:
        raise ValueError("atlas binding category arrays have incompatible shapes")
    rows, height, width = supported.shape
    geometric = np.asarray(geometric_class)
    if geometric.ndim != 1 or geometric.shape != (binding.face_to_atlas_row.size,):
        raise ValueError("geometric_class must have one entry per support-mesh face")
    if not (np.issubdtype(geometric.dtype, np.integer) or np.issubdtype(geometric.dtype, np.floating)):
        raise ValueError("geometric_class must contain finite integer indices")
    geometric_float = geometric.astype(np.float64)
    if np.any(~np.isfinite(geometric_float)) or np.any(geometric_float != np.floor(geometric_float)):
        raise ValueError("geometric_class must contain finite integer indices")
    geometric = geometric_float.astype(np.int64)
    if np.any(geometric < 0) or np.any(geometric >= 4):
        raise ValueError("geometric_class leaves the four structural host classes")

    compatible_marginal = getattr(atlas, "host_compatible_material_probability", None)
    if compatible_marginal is None:
        raw = np.asarray(getattr(atlas, "material_probability"), dtype=np.float64)
        compatible_support = np.asarray(getattr(atlas, "material_support"), dtype=np.float64) > 0.0
    else:
        raw, compatible_support = compatible_marginal(geometric)
        raw = np.asarray(raw, dtype=np.float64)
        compatible_support = np.asarray(compatible_support, dtype=bool)
    atlas_names = tuple(str(value) for value in np.asarray(atlas.material_names).tolist())
    if raw.shape != (rows, height, width, len(atlas_names)):
        raise ValueError("atlas material posterior does not match the binding atlas dimensions")
    if compatible_support.shape != (rows, height, width):
        raise ValueError("atlas host-compatibility support does not match the binding atlas dimensions")
    if not np.all(np.isfinite(raw)) or np.any(raw < 0.0):
        raise ValueError("atlas material posterior must be finite and nonnegative")
    transport_names = tuple(str(value) for value in binding.provenance.get("transport_material_names", ()))
    if not transport_names:
        transport_names = tuple(str(value) for value in binding.material_names)
    source_channels = np.asarray(
        [index for index, name in enumerate(atlas_names) if name in transport_names],
        dtype=np.intp,
    )
    if source_channels.size != len(transport_names):
        raise ValueError("binding transport material names do not match the source atlas vocabulary")
    structural_mass = raw[..., source_channels].sum(axis=-1)
    support_weight = np.asarray(getattr(atlas, "material_support"), dtype=np.float64)
    if support_weight.shape != (rows, height, width):
        raise ValueError("atlas material support does not match the binding atlas dimensions")
    fallback_state = getattr(atlas, "fallback_state_dense", None)
    if fallback_state is None:
        fallback_bound = np.ones((rows, height, width), dtype=bool)
    else:
        fallback_state = np.asarray(fallback_state)
        if fallback_state.shape != (rows, height, width):
            raise ValueError("atlas fallback_state_dense does not match the material binding")
        fallback_bound = fallback_state == int(FALLBACK_BOUND)

    observed = (support_weight > 0.0) & valid[None, ...]
    decisive_structural = structural_mass > MIN_INTERFACE_POSTERIOR
    recomputed_supported = compatible_support & observed & fallback_bound & decisive_structural & ~nonblocking
    if not np.array_equal(recomputed_supported, supported):
        raise ValueError("audit classifier gates disagree with AtlasMaterialBinding.supported")

    category = np.full((rows, height, width), FALLBACK_OTHER, dtype=np.uint8)
    reachable = valid[None, ...]
    category[reachable & ~observed] = GEOMETRIC_NO_PANORAMA_EVIDENCE
    category[reachable & observed & nonblocking] = NONBLOCKING_WOODY_ATLAS
    category[reachable & observed & ~nonblocking & ~compatible_support] = GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY
    category[reachable & observed & ~nonblocking & compatible_support & ~fallback_bound] = (
        GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE
    )
    category[reachable & observed & ~nonblocking & compatible_support & fallback_bound & ~decisive_structural] = (
        GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS
    )
    category[recomputed_supported] = ATLAS_INTERFACE

    face_to_row = np.asarray(binding.face_to_atlas_row, dtype=np.int64)
    fallback_by_face = np.full(face_to_row.shape, GEOMETRIC_NO_PANORAMA_EVIDENCE, dtype=np.uint8)
    present_face = face_to_row >= 0
    if np.any(present_face):
        for face, row in zip(np.flatnonzero(present_face), face_to_row[present_face], strict=True):
            face_cells = category[row][valid]
            if face_cells.size and np.all(face_cells == GEOMETRIC_NO_PANORAMA_EVIDENCE):
                fallback_by_face[face] = GEOMETRIC_NO_PANORAMA_EVIDENCE
            else:
                fallback_by_face[face] = FALLBACK_OTHER
    return EvidenceAuditCategoryMap(
        names=AUDIT_CATEGORY_NAMES,
        face_to_category_row=face_to_row,
        category_by_texel=category,
        fallback_category_by_face=fallback_by_face,
    )


def _texel_lookup(
    atlas_row: np.ndarray,
    barycentric_uv: np.ndarray,
    resolution: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return sparse-row and nearest valid canonical triangle texel indices."""
    height, width = (int(value) for value in resolution)
    if height < 2 or width < 2:
        raise ValueError("atlas resolution must be at least two")
    u = np.clip(barycentric_uv[:, 0], 0.0, 1.0)
    v = np.clip(barycentric_uv[:, 1], 0.0, 1.0)
    rows = np.floor(v * (height - 1) + 0.5)
    columns = np.floor(u * (width - 1) + 0.5)
    row_excess = rows - v * (height - 1)
    column_excess = columns - u * (width - 1)
    outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1.0e-12
    while np.any(outside):
        step_row = outside & (row_excess >= column_excess)
        step_column = outside & ~step_row
        rows[step_row] -= 1.0
        columns[step_column] -= 1.0
        row_excess[step_row] -= 1.0
        column_excess[step_column] -= 1.0
        outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1.0e-12
    return atlas_row, rows.astype(np.intp), columns.astype(np.intp)


__all__ = [
    "ATLAS_INTERFACE",
    "AUDIT_CATEGORY_NAMES",
    "EVIDENCE_REFUSAL_ATLAS_STATE",
    "EVIDENCE_REFUSAL_HOST_COMPATIBILITY",
    "EVIDENCE_REFUSAL_INSUFFICIENT_STRUCTURAL_MASS",
    "EvidenceAuditCategoryMap",
    "FALLBACK_OTHER",
    "GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE",
    "GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY",
    "GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS",
    "GEOMETRIC_FALLBACK_OTHER",
    "GEOMETRIC_NO_PANORAMA_EVIDENCE",
    "NONBLOCKING_WOODY_ATLAS",
    "RayReachedEvidenceClassifier",
    "classify_joint_atlas",
]
