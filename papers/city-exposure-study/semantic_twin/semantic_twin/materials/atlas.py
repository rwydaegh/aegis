"""Sparse joint semantic and material evidence on support-mesh triangles.

The stored truth is a joint posterior over entity and material for every
observed triangle-local texel.  Marginal winners are carried only as quicklook
arrays.  This matters on large support triangles: two materials may occupy
different texels, and one texel may retain a genuine material mixture.
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass, fields

import numpy as np


ATLAS_FORMAT_VERSION = 1
SOURCE_VISTAS_PRIOR = np.uint8(1)
SOURCE_SAM_CONCEPT = np.uint8(2)
FALLBACK_BOUND = np.uint8(0)
FALLBACK_UNOBSERVED = np.uint8(1)
FALLBACK_HOST_CONFLICT = np.uint8(2)
FALLBACK_UNROUTABLE = np.uint8(3)


@dataclass(frozen=True)
class JointSemanticMaterialAtlas:
    """Deterministic CSR storage for a joint all-camera evidence atlas.

    ``triangle_ids`` and ``texel_offsets`` map support triangles to sparse
    atlas cells.  ``joint_offsets`` then maps each cell to its nonzero
    entity-material posterior entries.  The entries in every cell sum to one.
    Arrays are sorted by triangle, texel row, texel column, entity, material.
    """

    atlas_resolution: int
    triangle_count: int
    mesh_sha256: str
    entity_names: np.ndarray
    material_names: np.ndarray
    station_ids: np.ndarray
    station_weight: np.ndarray
    triangle_ids: np.ndarray
    texel_offsets: np.ndarray
    texel_row: np.ndarray
    texel_column: np.ndarray
    entity_offsets: np.ndarray
    entity_index: np.ndarray
    entity_weight: np.ndarray
    joint_offsets: np.ndarray
    joint_entity: np.ndarray
    joint_material: np.ndarray
    joint_weight: np.ndarray
    support_weight: np.ndarray
    observation_count: np.ndarray
    camera_count: np.ndarray
    station_mask: np.ndarray
    source_mask: np.ndarray
    concept_weight: np.ndarray
    prior_weight: np.ndarray
    compatible_weight: np.ndarray
    incompatible_weight: np.ndarray
    fallback_state: np.ndarray
    entity_label: np.ndarray
    material_label: np.ndarray
    entity_confidence: np.ndarray
    material_confidence: np.ndarray
    mean_entity_score: np.ndarray
    mean_concept_confidence: np.ndarray
    vegetation_form_names: np.ndarray
    vegetation_subtype_names: np.ndarray
    vegetation_form_posterior: np.ndarray
    vegetation_subtype_posterior: np.ndarray
    format_version: int = ATLAS_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ATLAS_FORMAT_VERSION:
            raise ValueError(f"unsupported joint atlas format {self.format_version}")
        if self.atlas_resolution < 2:
            raise ValueError("atlas_resolution must be at least two")
        if self.triangle_count < 0:
            raise ValueError("triangle_count cannot be negative")
        if len(self.mesh_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.mesh_sha256.lower()
        ):
            raise ValueError("mesh_sha256 must be a 64-character hexadecimal digest")
        for name in ("entity_names", "material_names", "station_ids"):
            values = tuple(str(value) for value in np.asarray(getattr(self, name)).tolist())
            if not values or any(not value for value in values) or len(set(values)) != len(values):
                raise ValueError(f"{name} must contain unique nonempty values")
        if len(self.station_ids) > 64:
            raise ValueError("station_mask supports at most 64 cameras")
        triangle_ids = np.asarray(self.triangle_ids)
        if triangle_ids.ndim != 1 or np.any(np.diff(triangle_ids) <= 0):
            raise ValueError("triangle_ids must be a strictly increasing vector")
        if triangle_ids.size and (triangle_ids[0] < 0 or triangle_ids[-1] >= self.triangle_count):
            raise ValueError("triangle_ids leave the source support mesh")
        if np.asarray(self.texel_offsets).shape != (triangle_ids.size + 1,):
            raise ValueError("texel_offsets must have one boundary per observed triangle")
        _validate_offsets(self.texel_offsets, len(self.texel_row), "texel")
        cells = len(self.texel_row)
        if np.asarray(self.texel_column).shape != (cells,):
            raise ValueError("texel row and column arrays have different shapes")
        if cells and (
            np.min(self.texel_row) < 0
            or np.max(self.texel_row) >= self.atlas_resolution
            or np.min(self.texel_column) < 0
            or np.max(self.texel_column) >= self.atlas_resolution
            or np.any(
                np.asarray(self.texel_row, dtype=np.int64) + np.asarray(self.texel_column, dtype=np.int64)
                >= self.atlas_resolution
            )
        ):
            raise ValueError("a sparse texel leaves the canonical triangle")
        for start, stop in zip(self.texel_offsets[:-1], self.texel_offsets[1:], strict=True):
            key = np.asarray(self.texel_row[start:stop], dtype=np.int64) * self.atlas_resolution + np.asarray(
                self.texel_column[start:stop], dtype=np.int64
            )
            if np.any(np.diff(key) <= 0):
                raise ValueError("texels must be strictly sorted inside each triangle")
        _validate_offsets(self.entity_offsets, len(self.entity_weight), "entity")
        if np.asarray(self.entity_offsets).shape != (cells + 1,):
            raise ValueError("entity_offsets must have one boundary per sparse texel")
        if np.asarray(self.entity_index).shape != np.asarray(self.entity_weight).shape:
            raise ValueError("entity index and weight arrays have different shapes")
        entity_index = np.asarray(self.entity_index, dtype=np.int64)
        if len(self.entity_weight) and (np.any(entity_index < 0) or np.any(entity_index >= len(self.entity_names))):
            raise ValueError("an entity posterior index leaves its vocabulary")
        if np.any(~np.isfinite(self.entity_weight)) or np.any(self.entity_weight < 0.0):
            raise ValueError("entity weights must be finite and nonnegative")
        _validate_segment_probability(self.entity_offsets, self.entity_weight, cells, "entity")
        _validate_offsets(self.joint_offsets, len(self.joint_weight), "joint")
        if np.asarray(self.joint_offsets).shape != (cells + 1,):
            raise ValueError("joint_offsets must have one boundary per sparse texel")
        joints = len(self.joint_weight)
        if np.asarray(self.joint_entity).shape != (joints,) or np.asarray(self.joint_material).shape != (joints,):
            raise ValueError("joint entity, material, and weight arrays have different shapes")
        joint_entity = np.asarray(self.joint_entity, dtype=np.int64)
        joint_material = np.asarray(self.joint_material, dtype=np.int64)
        if joints and (
            np.any(joint_entity < 0)
            or np.any(joint_entity >= len(self.entity_names))
            or np.any(joint_material < 0)
            or np.any(joint_material >= len(self.material_names))
        ):
            raise ValueError("a joint posterior index leaves its vocabulary")
        if np.any(~np.isfinite(self.joint_weight)) or np.any(self.joint_weight < 0.0):
            raise ValueError("joint weights must be finite and nonnegative")
        _validate_segment_probability(self.joint_offsets, self.joint_weight, cells, "joint")
        vector_fields = (
            "support_weight",
            "observation_count",
            "camera_count",
            "station_mask",
            "source_mask",
            "concept_weight",
            "prior_weight",
            "compatible_weight",
            "incompatible_weight",
            "fallback_state",
            "entity_label",
            "material_label",
            "entity_confidence",
            "material_confidence",
            "mean_entity_score",
            "mean_concept_confidence",
        )
        for name in vector_fields:
            if np.asarray(getattr(self, name)).shape != (cells,):
                raise ValueError(f"{name} must have one value per sparse texel")
        if np.any(np.asarray(self.support_weight) <= 0.0):
            raise ValueError("every stored sparse texel must have positive support")
        if np.any(np.asarray(self.camera_count, dtype=np.int64) > len(self.station_ids)):
            raise ValueError("camera_count exceeds the station vocabulary")
        if np.asarray(self.station_weight).shape != (len(self.station_ids),):
            raise ValueError("station_weight must have one value per station")
        if np.any(~np.isfinite(self.station_weight)) or np.any(self.station_weight < 0.0):
            raise ValueError("station weights must be finite and nonnegative")
        if np.any(
            (np.asarray(self.fallback_state, dtype=np.int64) < 0)
            | (np.asarray(self.fallback_state, dtype=np.int64) > FALLBACK_UNROUTABLE)
        ):
            raise ValueError("fallback_state contains an unknown code")
        for name, vocabulary in (
            ("entity_label", self.entity_names),
            ("material_label", self.material_names),
        ):
            index = np.asarray(getattr(self, name), dtype=np.int64)
            if np.any((index < 0) | (index >= len(vocabulary))):
                raise ValueError(f"{name} leaves its vocabulary")
        for name, vocabulary in (
            ("vegetation_form_posterior", self.vegetation_form_names),
            ("vegetation_subtype_posterior", self.vegetation_subtype_names),
        ):
            values = np.asarray(getattr(self, name))
            if values.shape != (cells, len(vocabulary)):
                raise ValueError(f"{name} must have shape (cells, vocabulary)")
            if np.any(~np.isfinite(values)) or np.any(values < 0.0):
                raise ValueError(f"{name} must be finite and nonnegative")

    @property
    def observed_triangle_count(self) -> int:
        return len(self.triangle_ids)

    @property
    def cell_count(self) -> int:
        return len(self.texel_row)

    @property
    def resolution(self) -> tuple[int, int]:
        """Square barycentric resolution used by transport and Blender."""
        return self.atlas_resolution, self.atlas_resolution

    @property
    def face_to_atlas_row(self) -> np.ndarray:
        """Direct face-to-observed-row join, with ``-1`` for no evidence."""
        result = np.full(self.triangle_count, -1, dtype=np.int32)
        result[np.asarray(self.triangle_ids, dtype=np.int64)] = np.arange(
            self.observed_triangle_count,
            dtype=np.int32,
        )
        return result

    @property
    def valid_texels(self) -> np.ndarray:
        """Mask of square-grid texels inside the canonical triangle."""
        axis = np.linspace(0.0, 1.0, self.atlas_resolution)
        return axis[:, None] + axis[None, :] <= 1.0 + 1e-12

    @property
    def material_probability(self) -> np.ndarray:
        """Dense material posterior over observed triangle rows."""
        return self.material_posterior_dense()

    @property
    def entity_probability(self) -> np.ndarray:
        """Dense Vistas posterior, kept separate from material confidence."""
        return self.entity_posterior_dense()

    @property
    def entity_weights(self) -> np.ndarray:
        """Compatibility alias for the dense entity posterior."""
        return self.entity_probability

    @property
    def material_weights(self) -> np.ndarray:
        """Compatibility alias for the dense material posterior."""
        return self.material_probability

    @property
    def material_support(self) -> np.ndarray:
        """Dense pre-normalisation joint support for every local texel."""
        return self.cell_support_dense("support_weight")

    @property
    def entity_support(self) -> np.ndarray:
        """Dense entity support for QA and geometric fallback decisions."""
        return self.material_support

    @property
    def view_count(self) -> np.ndarray:
        return self.cell_support_dense("camera_count")

    @property
    def observation_count_dense(self) -> np.ndarray:
        return self.cell_support_dense("observation_count")

    @property
    def fallback_state_dense(self) -> np.ndarray:
        """Stored evidence state with unobserved texels marked explicitly."""
        dense = np.full(
            (self.observed_triangle_count, self.atlas_resolution, self.atlas_resolution),
            FALLBACK_UNOBSERVED,
            dtype=np.uint8,
        )
        owner = np.repeat(np.arange(self.observed_triangle_count, dtype=np.int64), np.diff(self.texel_offsets))
        dense[owner, self.texel_row, self.texel_column] = self.fallback_state
        return dense

    def host_compatible_material_probability(
        self,
        geometric_class: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Material posterior after the geometric host gate.

        The gate is applied to each joint entity-material entry. A cell binds
        only when compatible entity mass strictly exceeds incompatible mass.
        Its returned material mixture then contains compatible entries only and
        is renormalised. This prevents a transient object over a wall from
        leaking object material into reflection while allowing a window-like
        subregion to keep its own material within a large wall triangle.
        """
        from .support import entity_supports_atlas_cell

        geometric = np.asarray(geometric_class, dtype=np.int64)
        if geometric.shape != (self.triangle_count,):
            raise ValueError("geometric_class must have one value per support-mesh face")
        cell_triangle = np.repeat(np.asarray(self.triangle_ids, dtype=np.int64), np.diff(self.texel_offsets))
        cell_geometric = geometric[cell_triangle]
        joint_owner = np.repeat(np.arange(self.cell_count, dtype=np.int64), np.diff(self.joint_offsets))
        entity_names = tuple(str(value) for value in self.entity_names)
        compatible_entity = np.asarray(
            [
                entity_supports_atlas_cell(name, int(surface_class))
                for name in entity_names
                for surface_class in range(4)
            ],
            dtype=bool,
        ).reshape(len(entity_names), 4)
        compatible = compatible_entity[
            np.asarray(self.joint_entity, dtype=np.int64),
            cell_geometric[joint_owner],
        ]
        weight = np.asarray(self.joint_weight, dtype=np.float64)
        compatible_mass = np.bincount(
            joint_owner[compatible],
            weights=weight[compatible],
            minlength=self.cell_count,
        )
        incompatible_mass = np.bincount(
            joint_owner[~compatible],
            weights=weight[~compatible],
            minlength=self.cell_count,
        )
        bound = (compatible_mass > incompatible_mass) & (compatible_mass > 0.0)
        per_cell = np.zeros((self.cell_count, len(self.material_names)), dtype=np.float32)
        np.add.at(
            per_cell,
            (joint_owner[compatible], np.asarray(self.joint_material, dtype=np.int64)[compatible]),
            weight[compatible],
        )
        per_cell = np.divide(
            per_cell,
            compatible_mass[:, None],
            out=np.zeros_like(per_cell),
            where=bound[:, None],
        )
        dense = self._scatter_dense(per_cell)
        supported = np.zeros(dense.shape[:-1], dtype=bool)
        owner = np.repeat(np.arange(self.observed_triangle_count, dtype=np.int64), np.diff(self.texel_offsets))
        supported[owner, self.texel_row, self.texel_column] = bound
        return dense, supported

    def rows_for_triangles(self, triangle_ids: np.ndarray) -> np.ndarray:
        """Map source triangle identifiers to sparse atlas rows, or ``-1``."""
        query = np.asarray(triangle_ids, dtype=np.int64)
        if not len(self.triangle_ids):
            return np.full(query.shape, -1, dtype=np.int64)
        location = np.clip(np.searchsorted(self.triangle_ids, query), 0, len(self.triangle_ids) - 1)
        return np.where(self.triangle_ids[location] == query, location, -1).astype(np.int64)

    def cell_slice(self, triangle_id: int) -> slice:
        """Return the sparse-cell slice for one source triangle."""
        row = int(self.rows_for_triangles(np.asarray([triangle_id]))[0])
        if row < 0:
            return slice(0, 0)
        return slice(int(self.texel_offsets[row]), int(self.texel_offsets[row + 1]))

    def material_posterior_dense(self) -> np.ndarray:
        """Material marginals as ``(triangles, R, R, materials)``.

        The first axis follows ``triangle_ids``.  Unobserved and geometrically
        invalid texels are all zero.
        """
        return self._marginal_dense(self.joint_material, len(self.material_names))

    def entity_posterior_dense(self) -> np.ndarray:
        """Entity marginals as ``(triangles, R, R, entities)``."""
        per_cell = np.zeros((self.cell_count, len(self.entity_names)), dtype=np.float32)
        if len(self.entity_weight):
            owner = np.repeat(np.arange(self.cell_count, dtype=np.int64), np.diff(self.entity_offsets))
            np.add.at(per_cell, (owner, np.asarray(self.entity_index, dtype=np.int64)), self.entity_weight)
        return self._scatter_dense(per_cell)

    def _marginal_dense(self, index: np.ndarray, classes: int) -> np.ndarray:
        per_cell = np.zeros((self.cell_count, classes), dtype=np.float32)
        if len(self.joint_weight):
            owner = np.repeat(np.arange(self.cell_count, dtype=np.int64), np.diff(self.joint_offsets))
            np.add.at(per_cell, (owner, np.asarray(index, dtype=np.int64)), self.joint_weight)
        return self._scatter_dense(per_cell)

    def _scatter_dense(self, per_cell: np.ndarray) -> np.ndarray:
        dense = np.zeros(
            (
                self.observed_triangle_count,
                self.atlas_resolution,
                self.atlas_resolution,
                per_cell.shape[-1],
            ),
            dtype=np.float32,
        )
        owner = np.repeat(np.arange(self.observed_triangle_count, dtype=np.int64), np.diff(self.texel_offsets))
        dense[owner, self.texel_row, self.texel_column] = per_cell
        return dense

    def cell_support_dense(self, field: str = "support_weight") -> np.ndarray:
        """Scatter one public per-cell field to ``(triangles, R, R)``."""
        value = np.asarray(getattr(self, field))
        if value.shape != (self.cell_count,):
            raise ValueError(f"{field} is not a scalar per-cell field")
        dense = np.zeros(
            (self.observed_triangle_count, self.atlas_resolution, self.atlas_resolution),
            dtype=value.dtype,
        )
        owner = np.repeat(np.arange(self.observed_triangle_count, dtype=np.int64), np.diff(self.texel_offsets))
        dense[owner, self.texel_row, self.texel_column] = value
        return dense

    def content_digest(self) -> str:
        """SHA-256 of the canonical schema values, independent of ZIP headers."""
        digest = hashlib.sha256()
        for name, value in self._arrays().items():
            array = np.ascontiguousarray(value)
            digest.update(name.encode())
            digest.update(b"\0")
            digest.update(array.dtype.str.encode())
            digest.update(str(array.shape).encode())
            digest.update(array.tobytes())
        return digest.hexdigest()

    def sha256(self) -> str:
        """Compatibility spelling used by the refined-surface manifest."""
        return self.content_digest()

    def save(self, path: pathlib.Path) -> None:
        """Write a compressed NPZ containing only non-object arrays."""
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **self._arrays())

    def _arrays(self) -> dict[str, np.ndarray]:
        arrays = {
            field.name: np.asarray(getattr(self, field.name))
            for field in fields(self)
            if field.name != "format_version"
        }
        arrays.update(
            format_version=np.asarray(self.format_version, dtype=np.int16),
            atlas_resolution=np.asarray(self.atlas_resolution, dtype=np.int16),
            triangle_count=np.asarray(self.triangle_count, dtype=np.int64),
        )
        return dict(sorted(arrays.items()))

    @classmethod
    def load(
        cls,
        path: pathlib.Path,
        *,
        expected_mesh_sha256: str | None = None,
    ) -> JointSemanticMaterialAtlas:
        """Load and validate a saved atlas without enabling pickle."""
        with np.load(pathlib.Path(path), allow_pickle=False) as document:
            atlas = cls(
                **{
                    field.name: (
                        int(document[field.name])
                        if field.name in {"format_version", "atlas_resolution", "triangle_count"}
                        else str(document[field.name])
                        if field.name == "mesh_sha256"
                        else document[field.name].copy()
                    )
                    for field in fields(cls)
                }
            )
        if expected_mesh_sha256 is not None and atlas.mesh_sha256 != expected_mesh_sha256.lower():
            raise ValueError("joint atlas belongs to a different support mesh")
        return atlas


@dataclass(frozen=True)
class StationAtlasShard:
    """One station's cell-normalised contribution before camera fusion."""

    station_id: str
    station_weight: float
    cell_key: np.ndarray
    joint_offsets: np.ndarray
    joint_entity: np.ndarray
    joint_material: np.ndarray
    joint_weight: np.ndarray
    observation_count: np.ndarray
    source_mask: np.ndarray
    concept_fraction: np.ndarray
    prior_fraction: np.ndarray
    compatible_fraction: np.ndarray
    incompatible_fraction: np.ndarray
    mean_entity_score: np.ndarray
    mean_concept_confidence: np.ndarray
    vegetation_form_posterior: np.ndarray
    vegetation_subtype_posterior: np.ndarray

    def __post_init__(self) -> None:
        cells = len(self.cell_key)
        if not self.station_id:
            raise ValueError("station_id cannot be empty")
        if not np.isfinite(self.station_weight) or self.station_weight < 0.0:
            raise ValueError("station_weight must be finite and nonnegative")
        if np.asarray(self.cell_key).ndim != 1 or np.any(np.diff(self.cell_key) <= 0):
            raise ValueError("station cell keys must be strictly increasing")
        _validate_offsets(self.joint_offsets, len(self.joint_weight), "station joint")
        if np.asarray(self.joint_offsets).shape != (cells + 1,):
            raise ValueError("station joint offsets must have one segment per cell")
        if not (
            np.asarray(self.joint_entity).shape
            == np.asarray(self.joint_material).shape
            == np.asarray(self.joint_weight).shape
        ):
            raise ValueError("station joint arrays have different shapes")
        if len(self.joint_weight) and (
            np.any(np.asarray(self.joint_entity, dtype=np.int64) < 0)
            or np.any(np.asarray(self.joint_material, dtype=np.int64) < 0)
        ):
            raise ValueError("station joint indices must be nonnegative")
        cumulative = np.r_[0.0, np.cumsum(np.asarray(self.joint_weight, dtype=np.float64))]
        total = cumulative[self.joint_offsets[1:]] - cumulative[self.joint_offsets[:-1]]
        if np.any(~np.isclose(total, 1.0, atol=2e-6)):
            raise ValueError("each station cell posterior must sum to one")
        vectors = (
            self.observation_count,
            self.source_mask,
            self.concept_fraction,
            self.prior_fraction,
            self.compatible_fraction,
            self.incompatible_fraction,
            self.mean_entity_score,
            self.mean_concept_confidence,
        )
        if any(np.asarray(value).shape != (cells,) for value in vectors):
            raise ValueError("station cell diagnostic arrays have different shapes")
        if np.asarray(self.vegetation_form_posterior).shape[0] != cells:
            raise ValueError("station vegetation form rows do not match cells")
        if np.asarray(self.vegetation_subtype_posterior).shape[0] != cells:
            raise ValueError("station vegetation subtype rows do not match cells")


def fuse_station_atlases(
    shards: list[StationAtlasShard],
    *,
    atlas_resolution: int,
    triangle_count: int,
    entity_names: list[str] | tuple[str, ...],
    material_names: list[str] | tuple[str, ...],
    mesh_sha256: str,
    vegetation_form_names: list[str] | tuple[str, ...] = ("unresolved",),
    vegetation_subtype_names: list[str] | tuple[str, ...] = ("unresolved",),
    routable_material: np.ndarray | None = None,
) -> JointSemanticMaterialAtlas:
    """Fuse station-normalised shards in canonical station-name order.

    A camera contributes at most its explicit station weight to one cell.  Its
    pixel count changes the precision diagnostics, not its vote.  This prevents
    a nearby camera or a denser panorama raster from silently dominating the
    same physical patch.
    """
    if atlas_resolution < 2:
        raise ValueError("atlas_resolution must be at least two")
    if len(mesh_sha256) != 64 or any(character not in "0123456789abcdef" for character in mesh_sha256.lower()):
        raise ValueError("mesh_sha256 must be a 64-character hexadecimal digest")
    ordered = sorted(shards, key=lambda shard: shard.station_id)
    ids = [shard.station_id for shard in ordered]
    if len(set(ids)) != len(ids):
        raise ValueError("station identifiers must be unique")
    if len(ordered) > 64:
        raise ValueError("format version 1 supports at most 64 station bits")
    entity_names = tuple(entity_names)
    material_names = tuple(material_names)
    form_names = tuple(vegetation_form_names)
    subtype_names = tuple(vegetation_subtype_names)
    if not entity_names or not material_names:
        raise ValueError("entity and material vocabularies cannot be empty")
    for shard in ordered:
        if len(shard.joint_entity) and (
            np.any(np.asarray(shard.joint_entity, dtype=np.int64) < 0)
            or np.any(np.asarray(shard.joint_entity, dtype=np.int64) >= len(entity_names))
            or np.any(np.asarray(shard.joint_material, dtype=np.int64) < 0)
            or np.any(np.asarray(shard.joint_material, dtype=np.int64) >= len(material_names))
        ):
            raise ValueError(f"{shard.station_id} leaves the declared vocabulary")
        keys = np.asarray(shard.cell_key, dtype=np.int64)
        if np.any((keys < 0) | (keys >= triangle_count * atlas_resolution**2)):
            raise ValueError(f"{shard.station_id} has a cell outside the declared atlas")
        if shard.vegetation_form_posterior.shape[1] != len(form_names):
            raise ValueError(f"{shard.station_id} has a different vegetation form vocabulary")
        if shard.vegetation_subtype_posterior.shape[1] != len(subtype_names):
            raise ValueError(f"{shard.station_id} has a different vegetation subtype vocabulary")

    all_keys = np.unique(np.concatenate([shard.cell_key for shard in ordered])) if ordered else np.zeros(0, np.int64)
    cells = len(all_keys)
    support = np.zeros(cells, dtype=np.float64)
    observation = np.zeros(cells, dtype=np.uint64)
    camera_count = np.zeros(cells, dtype=np.uint16)
    station_mask = np.zeros(cells, dtype=np.uint64)
    source_mask = np.zeros(cells, dtype=np.uint8)
    concept_weight = np.zeros(cells, dtype=np.float64)
    prior_weight = np.zeros(cells, dtype=np.float64)
    compatible_weight = np.zeros(cells, dtype=np.float64)
    incompatible_weight = np.zeros(cells, dtype=np.float64)
    entity_score = np.zeros(cells, dtype=np.float64)
    concept_confidence = np.zeros(cells, dtype=np.float64)
    vegetation_form = np.zeros((cells, len(form_names)), dtype=np.float64)
    vegetation_subtype = np.zeros((cells, len(subtype_names)), dtype=np.float64)
    joint_keys: list[np.ndarray] = []
    joint_values: list[np.ndarray] = []

    for station_index, shard in enumerate(ordered):
        if not len(shard.cell_key) or shard.station_weight == 0.0:
            continue
        target = np.searchsorted(all_keys, shard.cell_key)
        weight = float(shard.station_weight)
        support[target] += weight
        observation[target] += np.asarray(shard.observation_count, dtype=np.uint64)
        camera_count[target] += 1
        station_mask[target] |= np.uint64(1) << np.uint64(station_index)
        np.bitwise_or.at(source_mask, target, np.asarray(shard.source_mask, dtype=np.uint8))
        concept_weight[target] += weight * shard.concept_fraction
        prior_weight[target] += weight * shard.prior_fraction
        compatible_weight[target] += weight * shard.compatible_fraction
        incompatible_weight[target] += weight * shard.incompatible_fraction
        entity_score[target] += weight * shard.mean_entity_score
        concept_confidence[target] += weight * shard.mean_concept_confidence
        vegetation_form[target] += weight * shard.vegetation_form_posterior
        vegetation_subtype[target] += weight * shard.vegetation_subtype_posterior
        joint_owner = np.repeat(target, np.diff(shard.joint_offsets))
        key = (
            joint_owner.astype(np.int64) * (len(entity_names) * len(material_names))
            + np.asarray(shard.joint_entity, dtype=np.int64) * len(material_names)
            + np.asarray(shard.joint_material, dtype=np.int64)
        )
        joint_keys.append(key)
        joint_values.append(weight * np.asarray(shard.joint_weight, dtype=np.float64))

    if cells:
        normalizer = np.where(support > 0.0, support, 1.0)
        entity_score /= normalizer
        concept_confidence /= normalizer
        vegetation_form /= normalizer[:, None]
        vegetation_subtype /= normalizer[:, None]
    if joint_keys:
        key = np.concatenate(joint_keys)
        value = np.concatenate(joint_values)
        order = np.argsort(key, kind="stable")
        key, value = key[order], value[order]
        unique, first = np.unique(key, return_index=True)
        value = np.add.reduceat(value, first)
        owner, pair = np.divmod(unique, len(entity_names) * len(material_names))
        joint_entity, joint_material = np.divmod(pair, len(material_names))
        value /= support[owner]
        count_by_cell = np.bincount(owner, minlength=cells)
        joint_offsets = np.r_[0, np.cumsum(count_by_cell)].astype(np.int64)
    else:
        joint_entity = joint_material = np.zeros(0, dtype=np.uint16)
        value = np.zeros(0, dtype=np.float32)
        joint_offsets = np.zeros(cells + 1, dtype=np.int64)

    material_marginal = np.zeros((cells, len(material_names)), dtype=np.float64)
    entity_marginal = np.zeros((cells, len(entity_names)), dtype=np.float64)
    if len(value):
        owner = np.repeat(np.arange(cells, dtype=np.int64), np.diff(joint_offsets))
        np.add.at(material_marginal, (owner, joint_material), value)
        np.add.at(entity_marginal, (owner, joint_entity), value)
    material_label = material_marginal.argmax(axis=1).astype(np.int16) if cells else np.zeros(0, np.int16)
    entity_label = entity_marginal.argmax(axis=1).astype(np.int16) if cells else np.zeros(0, np.int16)
    material_conf = material_marginal.max(axis=1).astype(np.float32) if cells else np.zeros(0, np.float32)
    entity_conf = entity_marginal.max(axis=1).astype(np.float32) if cells else np.zeros(0, np.float32)
    entity_owner, entity_index = np.nonzero(entity_marginal > 0.0)
    entity_counts = np.bincount(entity_owner, minlength=cells)
    entity_offsets = np.r_[0, np.cumsum(entity_counts)].astype(np.int64)
    entity_values = entity_marginal[entity_owner, entity_index].astype(np.float32)
    if routable_material is None:
        routable_material = np.asarray([name not in {"unknown", "air"} for name in material_names], dtype=bool)
    routable_material = np.asarray(routable_material, dtype=bool)
    if routable_material.shape != (len(material_names),):
        raise ValueError("routable_material must have one flag per material")
    routable = material_marginal[:, routable_material].sum(axis=1) > 0.0 if cells else np.zeros(0, bool)
    fallback = np.full(cells, FALLBACK_BOUND, dtype=np.uint8)
    fallback[compatible_weight <= incompatible_weight] = FALLBACK_HOST_CONFLICT
    fallback[(compatible_weight > incompatible_weight) & ~routable] = FALLBACK_UNROUTABLE

    triangle = all_keys // (atlas_resolution * atlas_resolution)
    texel = all_keys % (atlas_resolution * atlas_resolution)
    row, column = np.divmod(texel, atlas_resolution)
    triangle_ids, first, counts = np.unique(triangle, return_index=True, return_counts=True)
    texel_offsets = np.r_[0, np.cumsum(counts)].astype(np.int64)
    if np.any(first != texel_offsets[:-1]):
        raise AssertionError("canonical cell keys did not group by triangle")
    return JointSemanticMaterialAtlas(
        atlas_resolution=atlas_resolution,
        triangle_count=triangle_count,
        mesh_sha256=mesh_sha256.lower(),
        entity_names=np.asarray(entity_names),
        material_names=np.asarray(material_names),
        station_ids=np.asarray(ids),
        station_weight=np.asarray([shard.station_weight for shard in ordered], dtype=np.float32),
        triangle_ids=triangle_ids.astype(np.int64),
        texel_offsets=texel_offsets,
        texel_row=row.astype(np.uint16),
        texel_column=column.astype(np.uint16),
        entity_offsets=entity_offsets,
        entity_index=entity_index.astype(np.uint16),
        entity_weight=entity_values,
        joint_offsets=joint_offsets,
        joint_entity=np.asarray(joint_entity, dtype=np.uint16),
        joint_material=np.asarray(joint_material, dtype=np.uint16),
        joint_weight=np.asarray(value, dtype=np.float32),
        support_weight=support.astype(np.float32),
        observation_count=np.minimum(observation, np.iinfo(np.uint32).max).astype(np.uint32),
        camera_count=camera_count,
        station_mask=station_mask,
        source_mask=source_mask,
        concept_weight=concept_weight.astype(np.float32),
        prior_weight=prior_weight.astype(np.float32),
        compatible_weight=compatible_weight.astype(np.float32),
        incompatible_weight=incompatible_weight.astype(np.float32),
        fallback_state=fallback,
        entity_label=entity_label,
        material_label=material_label,
        entity_confidence=entity_conf,
        material_confidence=material_conf,
        mean_entity_score=entity_score.astype(np.float32),
        mean_concept_confidence=concept_confidence.astype(np.float32),
        vegetation_form_names=np.asarray(form_names),
        vegetation_subtype_names=np.asarray(subtype_names),
        vegetation_form_posterior=vegetation_form.astype(np.float32),
        vegetation_subtype_posterior=vegetation_subtype.astype(np.float32),
    )


def _validate_offsets(offsets: np.ndarray, values: int, name: str) -> None:
    offsets = np.asarray(offsets, dtype=np.int64)
    if offsets.ndim != 1 or not offsets.size or offsets[0] != 0 or offsets[-1] != values:
        raise ValueError(f"{name}_offsets must start at zero and end at the value count")
    if np.any(np.diff(offsets) < 0):
        raise ValueError(f"{name}_offsets cannot decrease")


def _validate_segment_probability(
    offsets: np.ndarray,
    weights: np.ndarray,
    segments: int,
    name: str,
) -> None:
    if not segments:
        return
    cumulative = np.r_[0.0, np.cumsum(np.asarray(weights, dtype=np.float64))]
    totals = cumulative[np.asarray(offsets[1:], dtype=np.int64)] - cumulative[np.asarray(offsets[:-1], dtype=np.int64)]
    if np.any(~np.isclose(totals, 1.0, atol=2e-6)):
        raise ValueError(f"every observed texel {name} posterior must sum to one")
