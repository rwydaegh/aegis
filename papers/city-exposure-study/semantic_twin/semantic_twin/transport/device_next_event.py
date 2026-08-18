"""Resident diffuse and sampled-specular next-event connections.

The device tracer keeps every path state on the selected Dr.Jit backend.  This
module connects every blocking vertex directly to a sampled source.  It can
also sample one finite reflector from the complete nondegenerate face support
and solve the source-nearest one-reflection image path without leaving Dr.Jit.
Direct source atoms and adaptive all-specular paths remain host calculations.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..illumination.sources import normalized_source_weights
from ..illumination.sphere import nearest_cell

SPECULAR_FACE_PROPOSAL = "0.9_triangle_area_plus_0.1_uniform_full_support_v1"
SPECULAR_SOURCE_PROPOSAL = "existing_normalized_discrete_source_weights_v1"
SPECULAR_COUNTER_GENERATOR = "splitmix64_seed_counter_dimension_v1"
SPECULAR_SOURCE_COUNTER_DIMENSION = 0
SPECULAR_FACE_COUNTER_DIMENSION = 1
_MASK_64 = (1 << 64) - 1

FIRST_DIFFUSE_AUDIT_CATEGORY_NAMES = (
    "atlas_interface",
    "nonblocking_woody_atlas",
    "geometric_no_panorama_evidence",
    "geometric_evidence_refused_host_compatibility",
    "geometric_evidence_refused_atlas_state",
    "geometric_evidence_refused_insufficient_structural_mass",
    "geometric_fallback_other",
)


@dataclass(frozen=True)
class DeviceFirstDiffuseAuditCategories:
    """Exact face/texel classification used only by first-diffuse audit replay."""

    face_to_category_row: np.ndarray
    category_by_texel: np.ndarray
    fallback_category_by_face: np.ndarray
    category_names: tuple[str, ...] = FIRST_DIFFUSE_AUDIT_CATEGORY_NAMES

    def __post_init__(self) -> None:
        names = tuple(str(value) for value in self.category_names)
        if names != FIRST_DIFFUSE_AUDIT_CATEGORY_NAMES:
            raise ValueError("first-diffuse audit categories must use the fixed ordered vocabulary")
        face_to_row = _readonly_array(self.face_to_category_row, np.int32)
        category = _readonly_array(self.category_by_texel, np.uint8)
        fallback = _readonly_array(self.fallback_category_by_face, np.uint8)
        if face_to_row.ndim != 1 or fallback.shape != face_to_row.shape:
            raise ValueError("first-diffuse audit face maps must be aligned vectors")
        if category.ndim != 3 or category.shape[0] < 1 or any(size < 2 for size in category.shape[1:]):
            raise ValueError("category_by_texel must have positive rows and resolution at least 2 by 2")
        if np.any(face_to_row < -1) or np.any(face_to_row >= category.shape[0]):
            raise ValueError("face_to_category_row contains an index outside the audit texel rows")
        count = len(names)
        if np.any(category >= count) or np.any(fallback >= count):
            raise ValueError("first-diffuse audit maps contain an unknown category")
        object.__setattr__(self, "category_names", names)
        object.__setattr__(self, "face_to_category_row", face_to_row)
        object.__setattr__(self, "category_by_texel", category)
        object.__setattr__(self, "fallback_category_by_face", fallback)

    @property
    def category_count(self) -> int:
        return len(self.category_names)

    @property
    def resolution(self) -> tuple[int, int]:
        return tuple(int(value) for value in self.category_by_texel.shape[1:])


@dataclass(frozen=True)
class DeviceFirstDiffuseAuditResult:
    """Closed category tally for accepted terminal first-diffuse connections."""

    category_names: tuple[str, ...]
    accepted_event_count: np.ndarray
    contribution_transfer: np.ndarray
    local_cell_mass: np.ndarray
    expected_accepted_events: int
    expected_contribution_transfer: float
    expected_local_cell_mass: np.ndarray | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        names = tuple(str(value) for value in self.category_names)
        counts = _readonly_array(self.accepted_event_count, np.uint64)
        transfer = _readonly_array(self.contribution_transfer, np.float64)
        field_mass = _readonly_array(self.local_cell_mass, np.float64)
        if names != FIRST_DIFFUSE_AUDIT_CATEGORY_NAMES:
            raise ValueError("first-diffuse audit result uses an unknown category vocabulary")
        if counts.shape != (len(names),) or transfer.shape != counts.shape:
            raise ValueError("first-diffuse audit category totals must be aligned vectors")
        if field_mass.ndim != 2 or field_mass.shape[0] != len(names):
            raise ValueError("first-diffuse audit local-cell mass must have one row per category")
        if np.any(~np.isfinite(transfer)) or np.any(transfer < 0.0):
            raise ValueError("first-diffuse audit contribution transfer must be finite and nonnegative")
        if np.any(~np.isfinite(field_mass)) or np.any(field_mass < 0.0):
            raise ValueError("first-diffuse audit local-cell mass must be finite and nonnegative")
        if int(np.sum(counts, dtype=np.uint64)) != int(self.expected_accepted_events):
            raise ValueError("first-diffuse audit accepted-event categories do not close")
        if not np.isclose(
            np.sum(transfer, dtype=np.float64),
            float(self.expected_contribution_transfer),
            rtol=2.0e-12,
            atol=1.0e-15,
        ):
            raise ValueError("first-diffuse audit contribution categories do not close")
        expected_field = self.expected_local_cell_mass
        if expected_field is not None:
            expected = np.asarray(expected_field, dtype=np.float64)
            if expected.shape != (field_mass.shape[1],) or not np.allclose(
                np.sum(field_mass, axis=0, dtype=np.float64),
                expected,
                rtol=2.0e-12,
                atol=1.0e-15,
            ):
                raise ValueError("first-diffuse audit category-resolved local-cell mass does not close")
        woody = names.index("nonblocking_woody_atlas")
        if counts[woody] or transfer[woody] != 0.0 or np.any(field_mass[woody] != 0.0):
            raise ValueError("nonblocking woody atlas cells cannot be terminal first-diffuse interactions")
        object.__setattr__(self, "category_names", names)
        object.__setattr__(self, "accepted_event_count", counts)
        object.__setattr__(self, "contribution_transfer", transfer)
        object.__setattr__(self, "local_cell_mass", field_mass)

    @property
    def total_accepted_events(self) -> int:
        return int(np.sum(self.accepted_event_count, dtype=np.uint64))

    @property
    def total_contribution_transfer(self) -> float:
        return float(np.sum(self.contribution_transfer, dtype=np.float64))

    def as_dict(self) -> dict[str, Any]:
        return {
            "category_names": list(self.category_names),
            "accepted_event_count": self.accepted_event_count.tolist(),
            "contribution_transfer": self.contribution_transfer.tolist(),
            "local_cell_mass": self.local_cell_mass.tolist(),
            "total_accepted_events": self.total_accepted_events,
            "total_contribution_transfer": self.total_contribution_transfer,
            "closure": {
                "accepted_events": True,
                "contribution_transfer": True,
                "local_cell_mass": self.expected_local_cell_mass is not None,
            },
            "nonblocking_woody_note": (
                "Pass-through woody atlas texels are not terminal material interactions and therefore "
                "have zero accepted first-diffuse events."
            ),
        }


@dataclass(frozen=True)
class DeviceNextEventBatch:
    """Fixed-width diffuse and sampled-specular deposits for one ray range."""

    weight_by_order: np.ndarray
    connections_by_order: np.ndarray
    cleared_by_order: np.ndarray
    ray_start: int
    rays: int
    samples: int
    specular_weight_by_order: np.ndarray | None = None
    specular_candidates_by_order: np.ndarray | None = None
    specular_geometric_by_order: np.ndarray | None = None
    specular_visible_by_order: np.ndarray | None = None
    specular_accepted_by_order: np.ndarray | None = None
    sampled_specular_samples: int = 1
    first_diffuse_audit_event_count: np.ndarray | None = None
    first_diffuse_audit_weight_by_category: np.ndarray | None = None

    def __post_init__(self) -> None:
        arrays = _validated_batch_arrays(self)
        weight, connections, cleared, specular_weight, candidates, geometric, visible, accepted = arrays
        object.__setattr__(self, "weight_by_order", weight)
        object.__setattr__(self, "connections_by_order", connections)
        object.__setattr__(self, "cleared_by_order", cleared)
        object.__setattr__(self, "specular_weight_by_order", specular_weight)
        object.__setattr__(self, "specular_candidates_by_order", candidates)
        object.__setattr__(self, "specular_geometric_by_order", geometric)
        object.__setattr__(self, "specular_visible_by_order", visible)
        object.__setattr__(self, "specular_accepted_by_order", accepted)


@dataclass(frozen=True)
class DeviceNextEventReduction:
    """Compact device reductions for one minimal roofline ray range.

    Unlike :class:`DeviceNextEventBatch`, this contract never contains one
    value per launched ray.  Order totals and, when requested, launch-cell
    fields are reduced before crossing the device boundary.
    """

    raw_by_order: np.ndarray
    specular_raw_by_order: np.ndarray
    connections_by_order: np.ndarray
    cleared_by_order: np.ndarray
    specular_candidates_by_order: np.ndarray
    specular_geometric_by_order: np.ndarray
    specular_visible_by_order: np.ndarray
    specular_accepted_by_order: np.ndarray
    raw_field_mass: np.ndarray
    specular_raw_field_mass: np.ndarray
    ray_start: int
    rays: int
    samples: int
    sampled_specular_samples: int = 1
    first_diffuse_audit_event_count: np.ndarray | None = None
    first_diffuse_audit_raw_by_category: np.ndarray | None = None
    first_diffuse_audit_raw_field_mass: np.ndarray | None = None

    def __post_init__(self) -> None:
        raw = np.asarray(self.raw_by_order, dtype=np.float64)
        specular = np.asarray(self.specular_raw_by_order, dtype=np.float64)
        connections = np.asarray(self.connections_by_order, dtype=np.uint64)
        cleared = np.asarray(self.cleared_by_order, dtype=np.uint64)
        if raw.ndim != 1 or specular.shape != raw.shape:
            raise ValueError("compact next-event order reductions must be aligned vectors")
        if connections.shape != raw.shape or cleared.shape != raw.shape:
            raise ValueError("compact next-event counts must have one value per order")
        count_arrays = (
            self.specular_candidates_by_order,
            self.specular_geometric_by_order,
            self.specular_visible_by_order,
            self.specular_accepted_by_order,
        )
        normalized_counts = tuple(np.asarray(value, dtype=np.uint64) for value in count_arrays)
        if any(value.shape != raw.shape for value in normalized_counts):
            raise ValueError("compact sampled-specular counts must have one value per order")
        candidates, geometric, visible, accepted = normalized_counts
        if (
            np.any(cleared > connections)
            or np.any(accepted > visible)
            or np.any(visible > geometric)
            or np.any(geometric > candidates)
        ):
            raise ValueError("compact next-event diagnostic stages are inconsistent")
        field = np.asarray(self.raw_field_mass, dtype=np.float64)
        specular_field = np.asarray(self.specular_raw_field_mass, dtype=np.float64)
        if field.ndim != 1 or specular_field.shape != field.shape:
            raise ValueError("compact next-event fields must be aligned vectors")
        if self.ray_start < 0 or self.rays < 1 or self.samples < 1 or self.sampled_specular_samples < 1:
            raise ValueError("compact next-event metadata is invalid")
        for name, value in (
            ("raw_by_order", raw),
            ("specular_raw_by_order", specular),
            ("connections_by_order", connections),
            ("cleared_by_order", cleared),
            ("specular_candidates_by_order", candidates),
            ("specular_geometric_by_order", geometric),
            ("specular_visible_by_order", visible),
            ("specular_accepted_by_order", accepted),
            ("raw_field_mass", field),
            ("specular_raw_field_mass", specular_field),
        ):
            object.__setattr__(self, name, value)
        audit_count = self.first_diffuse_audit_event_count
        audit_raw = self.first_diffuse_audit_raw_by_category
        audit_field = self.first_diffuse_audit_raw_field_mass
        if (audit_count is None) != (audit_raw is None) or (audit_count is None) != (audit_field is None):
            raise ValueError("compact first-diffuse audit reductions must be present together")
        if audit_count is not None:
            count = np.asarray(audit_count, dtype=np.uint64)
            category_raw = np.asarray(audit_raw, dtype=np.float64)
            category_field = np.asarray(audit_field, dtype=np.float64)
            if count.ndim != 1 or category_raw.shape != count.shape:
                raise ValueError("compact first-diffuse audit totals must be aligned vectors")
            if category_field.ndim != 2 or category_field.shape[0] != count.size:
                raise ValueError("compact first-diffuse audit fields need one row per category")
            object.__setattr__(self, "first_diffuse_audit_event_count", count)
            object.__setattr__(self, "first_diffuse_audit_raw_by_category", category_raw)
            object.__setattr__(self, "first_diffuse_audit_raw_field_mass", category_field)


def _specular_count_array(raw: np.ndarray | None, orders: int, name: str) -> np.ndarray:
    value = np.zeros(orders, dtype=np.uint64) if raw is None else np.asarray(raw, dtype=np.uint64)
    if value.shape != (orders,):
        raise ValueError(f"{name} must have one value per order")
    return value


def _validated_batch_arrays(batch: DeviceNextEventBatch) -> tuple[np.ndarray, ...]:
    """Normalize and validate one transferred batch without changing its layout."""
    weight = np.asarray(batch.weight_by_order, dtype=np.float32)
    connections = np.asarray(batch.connections_by_order, dtype=np.uint64)
    cleared = np.asarray(batch.cleared_by_order, dtype=np.uint64)
    if weight.ndim != 2 or weight.shape[1] != batch.rays:
        raise ValueError("weight_by_order must have shape (orders, rays)")
    if connections.shape != (weight.shape[0],) or cleared.shape != connections.shape:
        raise ValueError("connection counts must have one value per order")
    if np.any(cleared > connections):
        raise ValueError("cleared connections cannot exceed attempted connections")
    if batch.ray_start < 0 or batch.rays < 1 or batch.samples < 1:
        raise ValueError("device next-event batch metadata is invalid")
    specular_weight = (
        np.zeros_like(weight)
        if batch.specular_weight_by_order is None
        else np.asarray(batch.specular_weight_by_order, dtype=np.float32)
    )
    if specular_weight.shape != weight.shape:
        raise ValueError("specular_weight_by_order must align with diffuse order rows")
    count_arguments = (
        (batch.specular_candidates_by_order, "specular_candidates_by_order"),
        (batch.specular_geometric_by_order, "specular_geometric_by_order"),
        (batch.specular_visible_by_order, "specular_visible_by_order"),
        (batch.specular_accepted_by_order, "specular_accepted_by_order"),
    )
    candidates, geometric, visible, accepted = (
        _specular_count_array(raw, weight.shape[0], name) for raw, name in count_arguments
    )
    if np.any(accepted > visible) or np.any(visible > geometric) or np.any(geometric > candidates):
        raise ValueError("sampled specular diagnostic stages must be monotonically decreasing")
    if batch.sampled_specular_samples < 1:
        raise ValueError("sampled_specular_samples must be positive")
    audit_count = batch.first_diffuse_audit_event_count
    audit_weight = batch.first_diffuse_audit_weight_by_category
    if (audit_count is None) != (audit_weight is None):
        raise ValueError("first-diffuse audit batch arrays must be present together")
    if audit_count is not None:
        count = np.asarray(audit_count, dtype=np.uint64)
        category_weight = np.asarray(audit_weight, dtype=np.float32)
        if count.ndim != 1 or category_weight.shape != (count.size, batch.rays):
            raise ValueError("first-diffuse audit weights must have shape (categories, rays)")
        object.__setattr__(batch, "first_diffuse_audit_event_count", count)
        object.__setattr__(batch, "first_diffuse_audit_weight_by_category", category_weight)
    return weight, connections, cleared, specular_weight, candidates, geometric, visible, accepted


def _alias_table(probabilities: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build a deterministic Vose table and verify its represented measure."""
    probability = np.asarray(probabilities, dtype=np.float64)
    if probability.ndim != 1 or probability.size == 0:
        raise ValueError("device next-event estimation needs at least one source")
    if np.any(~np.isfinite(probability)) or np.any(probability < 0.0):
        raise ValueError("source probabilities must be finite and nonnegative")
    total = float(np.sum(probability, dtype=np.float64))
    if total <= 0.0:
        raise ValueError("source probabilities must contain positive mass")
    probability = probability / total
    count = probability.size
    scaled = probability * count
    threshold = np.ones(count, dtype=np.float64)
    alias = np.arange(count, dtype=np.uint32)
    small = [int(index) for index in np.flatnonzero(scaled < 1.0)]
    large = [int(index) for index in np.flatnonzero(scaled >= 1.0)]
    while small and large:
        low = small.pop()
        high = large.pop()
        threshold[low] = scaled[low]
        alias[low] = high
        scaled[high] -= 1.0 - scaled[low]
        if scaled[high] < 1.0 - 2.0e-15:
            small.append(high)
        else:
            large.append(high)
    threshold[np.asarray(small + large, dtype=np.int64)] = 1.0

    # The device stores float32 thresholds.  Validate the distribution that the
    # device will actually draw, rather than only the float64 construction.
    threshold32 = threshold.astype(np.float32)
    represented = threshold32.astype(np.float64) / count
    spill = (1.0 - threshold32.astype(np.float64)) / count
    np.add.at(represented, alias.astype(np.int64), spill)
    if not np.allclose(represented, probability, rtol=2.0e-7, atol=2.0e-10):
        raise ValueError("float32 alias table does not preserve the source probabilities")
    return threshold32, alias


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _readonly_array(value: np.ndarray, dtype: Any) -> np.ndarray:
    """Return one contiguous immutable array for a shared device proposal."""
    array = np.array(value, dtype=dtype, order="C", copy=True)
    array.setflags(write=False)
    return array


@dataclass(frozen=True)
class DeviceSpecularFaceProposal:
    """Immutable full-support face proposal shared by resident gathers."""

    triangles: np.ndarray
    normals: np.ndarray
    face_index: np.ndarray
    probability: np.ndarray
    alias_threshold: np.ndarray
    alias_index: np.ndarray
    support_complete: bool
    scene_face_count: int
    construction: str

    def __post_init__(self) -> None:
        triangles = _readonly_array(self.triangles, np.float32)
        normals = _readonly_array(self.normals, np.float32)
        face_index = _readonly_array(self.face_index, np.uint32)
        probability = _readonly_array(self.probability, np.float64)
        alias_threshold = _readonly_array(self.alias_threshold, np.float32)
        alias_index = _readonly_array(self.alias_index, np.uint32)
        count = probability.size
        if triangles.shape != (count, 3, 3) or normals.shape != (count, 3):
            raise ValueError("sampled specular proposal geometry has inconsistent shapes")
        if face_index.shape != (count,) or alias_threshold.shape != (count,) or alias_index.shape != (count,):
            raise ValueError("sampled specular proposal vectors must match its face count")
        if self.scene_face_count < count:
            raise ValueError("sampled specular scene_face_count cannot be smaller than its proposal")
        if self.support_complete and self.scene_face_count != count:
            raise ValueError("a complete sampled specular proposal must contain every scene face")
        if not self.construction:
            raise ValueError("sampled specular proposal construction must be named")
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "normals", normals)
        object.__setattr__(self, "face_index", face_index)
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "alias_threshold", alias_threshold)
        object.__setattr__(self, "alias_index", alias_index)

    @classmethod
    def from_geometry(cls, geometry: Any) -> DeviceSpecularFaceProposal:
        """Build the production area mixture once from finite geometry faces."""
        if not hasattr(geometry, "vertices") or not hasattr(geometry, "faces"):
            return cls(
                np.empty((0, 3, 3)),
                np.empty((0, 3)),
                np.empty(0),
                np.empty(0),
                np.empty(0),
                np.empty(0),
                True,
                0,
                "geometry_without_finite_faces",
            )
        vertices = np.asarray(geometry.vertices, dtype=np.float64)
        faces = np.asarray(geometry.faces, dtype=np.int64)
        triangles = vertices[faces]
        cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        double_area = np.linalg.norm(cross, axis=1)
        valid = double_area > 1.0e-12
        return cls._from_finite_faces(
            triangles[valid],
            cross[valid] / double_area[valid, None],
            np.arange(faces.shape[0], dtype=np.uint32)[valid],
            scene_face_count=int(np.sum(valid)),
            support_complete=True,
            construction="all_nondegenerate_mesh_faces",
        )

    @classmethod
    def _from_finite_faces(
        cls,
        triangles: np.ndarray,
        normals: np.ndarray,
        face_index: np.ndarray,
        *,
        scene_face_count: int,
        support_complete: bool,
        construction: str,
    ) -> DeviceSpecularFaceProposal:
        count = triangles.shape[0]
        if count == 0:
            probability = np.empty(0, dtype=np.float64)
            threshold = np.empty(0, dtype=np.float32)
            alias = np.empty(0, dtype=np.uint32)
        else:
            cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
            area = 0.5 * np.linalg.norm(cross, axis=1)
            probability = 0.9 * area / np.sum(area, dtype=np.float64) + 0.1 / count
            threshold, alias = _alias_table(probability)
        return cls(
            triangles,
            normals,
            face_index,
            probability,
            threshold,
            alias,
            support_complete,
            scene_face_count,
            construction,
        )


@dataclass(frozen=True)
class BoundDeviceSpecularFaceProposal:
    """One immutable proposal uploaded once for one resident geometry."""

    proposal: DeviceSpecularFaceProposal
    device_key: tuple[str, int]
    device_arrays: tuple[Any, ...]

    @classmethod
    def bind(cls, proposal: DeviceSpecularFaceProposal, kernel: Any) -> BoundDeviceSpecularFaceProposal:
        mi, dr = kernel.mi, kernel.dr
        key = (str(mi.variant()), id(kernel.geometry))
        if proposal.probability.size == 0:
            return cls(proposal, key, ())
        triangle = proposal.triangles
        normal = proposal.normals
        arrays = (
            mi.Float(triangle[:, 0, 0]),
            mi.Float(triangle[:, 0, 1]),
            mi.Float(triangle[:, 0, 2]),
            mi.Float(triangle[:, 1, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 1, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 1, 2] - triangle[:, 0, 2]),
            mi.Float(triangle[:, 2, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 2, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 2, 2] - triangle[:, 0, 2]),
            mi.Float(normal[:, 0]),
            mi.Float(normal[:, 1]),
            mi.Float(normal[:, 2]),
            mi.UInt32(proposal.face_index),
            mi.Float(proposal.probability.astype(np.float32)),
            mi.Float(proposal.alias_threshold),
            mi.UInt32(proposal.alias_index),
        )
        dr.eval(*arrays)
        return cls(proposal, key, arrays)


def _splitmix_seed_word(seed: int) -> int:
    value = (int(seed) + 0x9E3779B97F4A7C15) & _MASK_64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK_64
    return value ^ (value >> 31)


def _splitmix_uniform(mi: Any, counter: Any, seed_word: Any, dimension: int) -> Any:
    """Float32 uniform from the CPU reference's SplitMix64 counter word."""
    value = counter ^ seed_word
    value ^= mi.UInt64(((int(dimension) + 1) * 0xD1B54A32D192ED03) & _MASK_64)
    value += mi.UInt64(0x9E3779B97F4A7C15)
    value = (value ^ (value >> 30)) * mi.UInt64(0xBF58476D1CE4E5B9)
    value = (value ^ (value >> 27)) * mi.UInt64(0x94D049BB133111EB)
    value ^= value >> 31
    return mi.Float(value >> 40) * (1.0 / float(1 << 24))


@dataclass
class DeviceNextEventGather:
    """Host owner of one resident diffuse next-event trace.

    ``chi_bounce`` and ``bounced_mass`` use the same fixed-width deposits.  Their
    sums therefore differ only by host float64 reduction order.  The source draw
    uses a separate counter stream at ``trace_seed + seed_offset`` and is keyed by
    global ray index, bounce depth, and sample number.  Changing a transfer batch
    does not change any path or source draw.
    """

    sources: Any
    samples: int = 1
    max_order: int | None = None
    seed_offset: int = 1000
    epsilon_m: float = 1.0e-3
    lift_m: float = 1.0e-2
    min_connect_m: float = 0.5
    specular_suffix_order: int = 0
    sampled_specular_samples: int = 1
    sampled_specular_seed_offset: int = 2000
    collect_field: bool = True
    specular_face_proposal: BoundDeviceSpecularFaceProposal | None = None
    #: A closed first-surface transport contract.  The tracer may still perform
    #: its terminal collision query, but no next-event contribution is allowed
    #: after depth zero.
    first_material_interaction_only: bool = False
    first_diffuse_audit: DeviceFirstDiffuseAuditCategories | None = None

    _sites: np.ndarray = field(init=False, repr=False)
    _probabilities: np.ndarray = field(init=False, repr=False)
    _alias_threshold: np.ndarray = field(init=False, repr=False)
    _alias_index: np.ndarray = field(init=False, repr=False)
    _device_key: tuple[str, int] | None = field(init=False, default=None, repr=False)
    _device_arrays: tuple[Any, ...] | None = field(init=False, default=None, repr=False)
    _specular_device_key: tuple[str, int] | None = field(init=False, default=None, repr=False)
    _specular_device_arrays: tuple[Any, ...] | None = field(init=False, default=None, repr=False)
    _first_diffuse_audit_device_key: tuple[str, int] | None = field(init=False, default=None, repr=False)
    _first_diffuse_audit_device_arrays: tuple[Any, ...] | None = field(init=False, default=None, repr=False)
    _face_triangles: np.ndarray = field(init=False, default_factory=lambda: np.empty((0, 3, 3)), repr=False)
    _face_normals: np.ndarray = field(init=False, default_factory=lambda: np.empty((0, 3)), repr=False)
    _face_index: np.ndarray = field(init=False, default_factory=lambda: np.empty(0, dtype=np.uint32), repr=False)
    _face_probability: np.ndarray = field(init=False, default_factory=lambda: np.empty(0), repr=False)
    _face_alias_threshold: np.ndarray = field(init=False, default_factory=lambda: np.empty(0), repr=False)
    _face_alias_index: np.ndarray = field(init=False, default_factory=lambda: np.empty(0, dtype=np.uint32), repr=False)
    _surface_support_complete: bool = field(init=False, default=False, repr=False)
    _surface_scene_face_count: int = field(init=False, default=0, repr=False)
    _expected_rays: int = field(init=False, default=0, repr=False)
    _received_rays: int = field(init=False, default=0, repr=False)
    _sampled_specular_counter: int = field(init=False, default=0, repr=False)
    _local_grid: np.ndarray | None = field(init=False, default=None, repr=False)
    _raw_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1), repr=False)
    _raw_field_mass: np.ndarray = field(init=False, default_factory=lambda: np.zeros(0), repr=False)
    _connections_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _cleared_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False)
    _specular_raw_by_order: np.ndarray = field(init=False, default_factory=lambda: np.zeros(1), repr=False)
    _specular_raw_field_mass: np.ndarray = field(init=False, default_factory=lambda: np.zeros(0), repr=False)
    _specular_candidates_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_geometric_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_visible_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _specular_accepted_by_order: np.ndarray = field(
        init=False, default_factory=lambda: np.zeros(1, dtype=np.uint64), repr=False
    )
    _first_diffuse_audit_event_count: np.ndarray = field(
        init=False, default_factory=lambda: np.empty(0, dtype=np.uint64), repr=False
    )
    _first_diffuse_audit_raw_by_category: np.ndarray = field(
        init=False, default_factory=lambda: np.empty(0), repr=False
    )
    _first_diffuse_audit_raw_field_mass: np.ndarray = field(
        init=False, default_factory=lambda: np.empty((0, 0)), repr=False
    )

    def __post_init__(self) -> None:
        if self.samples < 1:
            raise ValueError("samples must be positive")
        if self.max_order is not None and self.max_order < 0:
            raise ValueError("max_order must be nonnegative")
        if self.epsilon_m <= 0.0 or self.lift_m < 0.0 or self.min_connect_m < 0.0:
            raise ValueError("next-event distances must be nonnegative and epsilon must be positive")
        if self.specular_suffix_order not in (0, 1):
            raise NotImplementedError("resident device next-event estimation completes at most one specular suffix")
        if self.sampled_specular_samples < 1:
            raise ValueError("sampled_specular_samples must be positive")
        if self.sampled_specular_seed_offset < 0:
            raise ValueError("sampled_specular_seed_offset must be nonnegative")
        if not isinstance(self.first_material_interaction_only, bool):
            raise TypeError("first_material_interaction_only must be boolean")
        if self.first_diffuse_audit is not None and not self.first_material_interaction_only:
            raise ValueError("first-diffuse audit is defined only for first-material-interaction transport")
        sites = np.asarray(self.sources.sites(), dtype=np.float64)
        if sites.ndim != 2 or sites.shape[1] != 3 or not np.all(np.isfinite(sites)):
            raise ValueError("source sites must have shape (sources, 3) and be finite")
        probabilities = normalized_source_weights(self.sources)
        if sites.shape[0] == 0:
            raise ValueError("resident device next-event estimation needs at least one source")
        threshold, alias = _alias_table(probabilities)
        self._sites = np.ascontiguousarray(sites, dtype=np.float32)
        self._probabilities = np.asarray(probabilities, dtype=np.float64)
        self._alias_threshold = threshold
        self._alias_index = alias

    @property
    def probabilities(self) -> np.ndarray:
        return self._probabilities.copy()

    @property
    def face_probabilities(self) -> np.ndarray:
        return self._face_probability.copy()

    @property
    def sampled_specular_ready(self) -> bool:
        return bool(self.specular_suffix_order == 1 and self._face_probability.size)

    def _prepare_specular_support(self, kernel: Any) -> None:
        if self.specular_suffix_order == 0:
            return
        geometry = kernel.geometry
        key = (str(getattr(geometry, "variant", "")), id(geometry))
        if self._specular_device_key == key and self._specular_device_arrays is not None:
            return
        if self.specular_face_proposal is None:
            proposal = DeviceSpecularFaceProposal.from_geometry(geometry)
            bound = None
        else:
            bound = self.specular_face_proposal
            if bound.device_key != (str(kernel.mi.variant()), id(geometry)):
                raise ValueError("sampled specular face proposal is bound to a different device geometry")
            proposal = bound.proposal
        self._face_triangles = proposal.triangles
        self._face_normals = proposal.normals
        self._face_index = proposal.face_index
        self._face_probability = proposal.probability
        self._face_alias_threshold = proposal.alias_threshold
        self._face_alias_index = proposal.alias_index
        self._surface_support_complete = proposal.support_complete
        self._surface_scene_face_count = proposal.scene_face_count
        self._specular_device_key = None if bound is None else bound.device_key
        self._specular_device_arrays = None if bound is None else bound.device_arrays

    def begin_trace(self, rays: int, local_grid: np.ndarray) -> None:
        """Reset host reductions before a complete, possibly batched trace."""
        if rays < 1:
            raise ValueError("rays must be positive")
        grid = np.asarray(local_grid, dtype=np.float64)
        if grid.ndim != 2 or grid.shape[1] != 3 or grid.shape[0] == 0:
            raise ValueError("local_grid must have shape (positive cells, 3)")
        self._expected_rays = int(rays)
        self._received_rays = 0
        self._sampled_specular_counter = 0
        self._local_grid = grid
        initial_orders = 1 if self.max_order is None else self.max_order + 1
        self._raw_by_order = np.zeros(initial_orders, dtype=np.float64)
        self._raw_field_mass = np.zeros(grid.shape[0], dtype=np.float64) if self.collect_field else np.empty(0)
        self._connections_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._cleared_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_raw_by_order = np.zeros(initial_orders, dtype=np.float64)
        self._specular_raw_field_mass = np.zeros(grid.shape[0], dtype=np.float64) if self.collect_field else np.empty(0)
        self._specular_candidates_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_geometric_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_visible_by_order = np.zeros(initial_orders, dtype=np.uint64)
        self._specular_accepted_by_order = np.zeros(initial_orders, dtype=np.uint64)
        categories = 0 if self.first_diffuse_audit is None else self.first_diffuse_audit.category_count
        self._first_diffuse_audit_event_count = np.zeros(categories, dtype=np.uint64)
        self._first_diffuse_audit_raw_by_category = np.zeros(categories, dtype=np.float64)
        self._first_diffuse_audit_raw_field_mass = (
            np.zeros((categories, grid.shape[0]), dtype=np.float64)
            if categories and self.collect_field
            else np.empty((categories, 0), dtype=np.float64)
        )

    def consume(
        self,
        batch: DeviceNextEventBatch,
        launch_direction: np.ndarray,
        *,
        launch_cells: np.ndarray | None = None,
    ) -> None:
        """Reduce one returned ray range without retaining per-ray deposits."""
        launch = self._validated_launch(batch, launch_direction)
        source_order_count = batch.weight_by_order.shape[0]
        order_count = source_order_count if self.max_order is None else self.max_order + 1
        self._grow_order_accumulators(order_count)
        self._accumulate_order_reductions(batch, source_order_count, order_count)
        self._sampled_specular_counter += int(np.sum(batch.specular_candidates_by_order, dtype=np.uint64))
        if self.collect_field:
            self._accumulate_field(batch, launch, launch_cells, source_order_count)
        self._accumulate_first_diffuse_audit_batch(batch, launch, launch_cells)
        self._received_rays += batch.rays

    def consume_reduced(self, reduction: DeviceNextEventReduction) -> None:
        """Accumulate one already reduced minimal-production range."""
        if self._local_grid is None:
            raise RuntimeError("begin_trace must be called before consuming device reductions")
        if reduction.samples != self.samples:
            raise RuntimeError("device next-event reduction used the wrong sample count")
        if reduction.sampled_specular_samples != self.sampled_specular_samples:
            raise RuntimeError("device next-event reduction used the wrong sampled-specular count")
        if reduction.ray_start != self._received_rays:
            raise RuntimeError("device next-event reductions are not in contiguous global ray order")
        source_order_count = reduction.raw_by_order.size
        order_count = source_order_count if self.max_order is None else self.max_order + 1
        self._grow_order_accumulators(order_count)
        reductions = (
            reduction.raw_by_order,
            reduction.connections_by_order,
            reduction.cleared_by_order,
            reduction.specular_raw_by_order,
            reduction.specular_candidates_by_order,
            reduction.specular_geometric_by_order,
            reduction.specular_visible_by_order,
            reduction.specular_accepted_by_order,
        )
        accumulators = (
            self._raw_by_order,
            self._connections_by_order,
            self._cleared_by_order,
            self._specular_raw_by_order,
            self._specular_candidates_by_order,
            self._specular_geometric_by_order,
            self._specular_visible_by_order,
            self._specular_accepted_by_order,
        )
        used_orders = min(source_order_count, order_count)
        for accumulator, values in zip(accumulators, reductions, strict=True):
            collapsed = self._reduced_order_tail(values, order_count, values.dtype)
            accumulator[:used_orders] += collapsed[:used_orders]
        self._sampled_specular_counter += int(np.sum(reduction.specular_candidates_by_order, dtype=np.uint64))
        if self.collect_field:
            if reduction.raw_field_mass.shape != self._raw_field_mass.shape:
                raise RuntimeError("compact next-event field has the wrong launch-cell count")
            self._raw_field_mass += reduction.raw_field_mass
            self._specular_raw_field_mass += reduction.specular_raw_field_mass
        elif reduction.raw_field_mass.size or reduction.specular_raw_field_mass.size:
            raise RuntimeError("scalar next-event gather received an unexpected angular field")
        self._accumulate_first_diffuse_audit_reduction(reduction)
        self._received_rays += reduction.rays

    def _accumulate_first_diffuse_audit_batch(
        self,
        batch: DeviceNextEventBatch,
        launch: np.ndarray,
        launch_cells: np.ndarray | None,
    ) -> None:
        if self.first_diffuse_audit is None:
            if batch.first_diffuse_audit_event_count is not None:
                raise RuntimeError("audit-disabled gather received first-diffuse audit data")
            return
        counts = batch.first_diffuse_audit_event_count
        weights = batch.first_diffuse_audit_weight_by_category
        if counts is None or weights is None:
            raise RuntimeError("audit-enabled gather did not receive first-diffuse audit data")
        if counts.shape != self._first_diffuse_audit_event_count.shape:
            raise RuntimeError("first-diffuse audit batch has the wrong category count")
        self._first_diffuse_audit_event_count += counts
        self._first_diffuse_audit_raw_by_category += np.sum(weights, axis=1, dtype=np.float64)
        if self.collect_field:
            cells = self._field_cells(batch, launch, launch_cells)
            for category, row in enumerate(weights):
                np.add.at(
                    self._first_diffuse_audit_raw_field_mass[category],
                    cells,
                    row.astype(np.float64, copy=False),
                )

    def _accumulate_first_diffuse_audit_reduction(self, reduction: DeviceNextEventReduction) -> None:
        if self.first_diffuse_audit is None:
            if reduction.first_diffuse_audit_event_count is not None:
                raise RuntimeError("audit-disabled gather received compact first-diffuse audit data")
            return
        counts = reduction.first_diffuse_audit_event_count
        raw = reduction.first_diffuse_audit_raw_by_category
        field_mass = reduction.first_diffuse_audit_raw_field_mass
        if counts is None or raw is None or field_mass is None:
            raise RuntimeError("audit-enabled gather did not receive compact first-diffuse audit data")
        if counts.shape != self._first_diffuse_audit_event_count.shape:
            raise RuntimeError("compact first-diffuse audit reduction has the wrong category count")
        self._first_diffuse_audit_event_count += counts
        self._first_diffuse_audit_raw_by_category += raw
        if self.collect_field:
            if field_mass.shape != self._first_diffuse_audit_raw_field_mass.shape:
                raise RuntimeError("compact first-diffuse audit field has the wrong local-cell shape")
            self._first_diffuse_audit_raw_field_mass += field_mass
        elif field_mass.shape != (counts.size, 0):
            raise RuntimeError("scalar compact first-diffuse audit returned a local-cell field")

    def _validated_launch(self, batch: DeviceNextEventBatch, launch_direction: np.ndarray) -> np.ndarray:
        if self._local_grid is None:
            raise RuntimeError("begin_trace must be called before consuming device deposits")
        if batch.samples != self.samples:
            raise RuntimeError("device next-event batch used the wrong sample count")
        if batch.sampled_specular_samples != self.sampled_specular_samples:
            raise RuntimeError("device next-event batch used the wrong sampled-specular count")
        if batch.ray_start != self._received_rays:
            raise RuntimeError("device next-event batches are not in contiguous global ray order")
        launch = np.asarray(launch_direction, dtype=np.float64)
        if launch.shape != (batch.rays, 3):
            raise RuntimeError("launch directions do not align with device next-event deposits")
        return launch

    def _grow_order_accumulators(self, order_count: int) -> None:
        grow = order_count - self._raw_by_order.size
        if grow <= 0:
            return
        names = (
            "_raw_by_order",
            "_connections_by_order",
            "_cleared_by_order",
            "_specular_raw_by_order",
            "_specular_candidates_by_order",
            "_specular_geometric_by_order",
            "_specular_visible_by_order",
            "_specular_accepted_by_order",
        )
        for name in names:
            setattr(self, name, np.pad(getattr(self, name), (0, grow)))

    @staticmethod
    def _reduced_order_tail(values: np.ndarray, order_count: int, dtype: Any) -> np.ndarray:
        reduced = values.copy()
        if reduced.shape[0] > order_count:
            reduced[order_count - 1] = np.sum(reduced[order_count - 1 :], dtype=dtype)
        return reduced

    def _accumulate_order_reductions(
        self,
        batch: DeviceNextEventBatch,
        source_order_count: int,
        order_count: int,
    ) -> None:
        raw_by_order = np.sum(batch.weight_by_order, axis=1, dtype=np.float64)
        specular_raw = np.sum(batch.specular_weight_by_order, axis=1, dtype=np.float64)
        reductions = (
            self._reduced_order_tail(raw_by_order, order_count, np.float64),
            self._reduced_order_tail(batch.connections_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.cleared_by_order, order_count, np.uint64),
            self._reduced_order_tail(specular_raw, order_count, np.float64),
            self._reduced_order_tail(batch.specular_candidates_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_geometric_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_visible_by_order, order_count, np.uint64),
            self._reduced_order_tail(batch.specular_accepted_by_order, order_count, np.uint64),
        )
        accumulators = (
            self._raw_by_order,
            self._connections_by_order,
            self._cleared_by_order,
            self._specular_raw_by_order,
            self._specular_candidates_by_order,
            self._specular_geometric_by_order,
            self._specular_visible_by_order,
            self._specular_accepted_by_order,
        )
        used_orders = min(source_order_count, order_count)
        for accumulator, reduction in zip(accumulators, reductions, strict=True):
            accumulator[:used_orders] += reduction[:used_orders]

    def _accumulate_field(
        self,
        batch: DeviceNextEventBatch,
        launch: np.ndarray,
        launch_cells: np.ndarray | None,
        source_order_count: int,
    ) -> None:
        cells = self._field_cells(batch, launch, launch_cells)
        tiled_cells = np.tile(cells, source_order_count)
        np.add.at(
            self._raw_field_mass,
            tiled_cells,
            batch.weight_by_order.reshape(-1).astype(np.float64, copy=False),
        )
        np.add.at(
            self._specular_raw_field_mass,
            tiled_cells,
            batch.specular_weight_by_order.reshape(-1).astype(np.float64, copy=False),
        )

    def _field_cells(
        self,
        batch: DeviceNextEventBatch,
        launch: np.ndarray,
        launch_cells: np.ndarray | None,
    ) -> np.ndarray:
        if launch_cells is None:
            return nearest_cell(launch, self._local_grid)
        cells = np.asarray(launch_cells, dtype=np.int64)
        if cells.shape != (batch.rays,) or np.any(cells < 0) or np.any(cells >= self._local_grid.shape[0]):
            raise RuntimeError("launch cells do not align with device next-event deposits")
        return cells

    def end_trace(self) -> None:
        if self._received_rays != self._expected_rays:
            raise RuntimeError(
                f"device next-event trace returned {self._received_rays} rays, expected {self._expected_rays}"
            )

    @property
    def rays(self) -> int:
        return self._received_rays

    @property
    def connections(self) -> int:
        return int(np.sum(self._connections_by_order, dtype=np.uint64))

    @property
    def cleared(self) -> int:
        return int(np.sum(self._cleared_by_order, dtype=np.uint64))

    def chi_by_order(self) -> np.ndarray:
        if self.rays == 0:
            return np.zeros_like(self._raw_by_order)
        return (4.0 * np.pi / (self.rays * self.samples)) * self._raw_by_order

    def bounced_mass(self) -> np.ndarray:
        if not self.collect_field:
            raise RuntimeError("this device next-event gather did not collect an angular field")
        if self.rays == 0:
            return np.zeros_like(self._raw_field_mass)
        return (4.0 * np.pi / (self.rays * self.samples)) * self._raw_field_mass

    def chi_bounce(self) -> float:
        if self.collect_field:
            return float(np.sum(self.bounced_mass(), dtype=np.float64))
        return float(np.sum(self.chi_by_order(), dtype=np.float64))

    def first_diffuse_audit_result(self) -> DeviceFirstDiffuseAuditResult:
        """Return the normalized, closure-checked opt-in first-diffuse tally."""
        if self.first_diffuse_audit is None:
            raise RuntimeError("this device next-event gather did not enable first-diffuse audit")
        if self.rays == 0:
            scale = 0.0
        else:
            scale = 4.0 * np.pi / (self.rays * self.samples)
        field_mass = scale * self._first_diffuse_audit_raw_field_mass
        expected_field = self.bounced_mass() if self.collect_field else None
        return DeviceFirstDiffuseAuditResult(
            category_names=self.first_diffuse_audit.category_names,
            accepted_event_count=self._first_diffuse_audit_event_count.copy(),
            contribution_transfer=scale * self._first_diffuse_audit_raw_by_category,
            local_cell_mass=field_mass,
            expected_accepted_events=self.cleared,
            expected_contribution_transfer=self.chi_bounce(),
            expected_local_cell_mass=expected_field,
        )

    @property
    def specular_candidates(self) -> int:
        return int(np.sum(self._specular_candidates_by_order, dtype=np.uint64))

    @property
    def specular_accepted(self) -> int:
        return int(np.sum(self._specular_accepted_by_order, dtype=np.uint64))

    def chi_specular_suffix_by_order(self) -> np.ndarray:
        if self.rays == 0:
            return np.zeros_like(self._specular_raw_by_order)
        return (4.0 * np.pi / (self.rays * self.sampled_specular_samples)) * self._specular_raw_by_order

    def chi_specular_suffix(self) -> float:
        if self.collect_field:
            return float(np.sum(self.specular_bounced_mass(), dtype=np.float64))
        return float(np.sum(self.chi_specular_suffix_by_order(), dtype=np.float64))

    def specular_bounced_mass(self) -> np.ndarray:
        if not self.collect_field:
            raise RuntimeError("this device next-event gather did not collect an angular field")
        if self.rays == 0:
            return np.zeros_like(self._specular_raw_field_mass)
        return (4.0 * np.pi / (self.rays * self.sampled_specular_samples)) * self._specular_raw_field_mass

    def sampled_specular_diagnostics(self) -> dict[str, Any]:
        if self.specular_suffix_order == 0:
            return {"enabled": False}
        trials = self.specular_candidates
        accepted = self.specular_accepted
        return {
            "enabled": self.sampled_specular_ready,
            "samples_per_vertex": self.sampled_specular_samples,
            "seed_offset": self.sampled_specular_seed_offset,
            "counter_start": 0,
            "counter_stop": self._sampled_specular_counter,
            "trials": trials,
            "candidates": trials,
            "geometric": int(np.sum(self._specular_geometric_by_order, dtype=np.uint64)),
            "visible": int(np.sum(self._specular_visible_by_order, dtype=np.uint64)),
            "accepted": accepted,
            "acceptance": accepted / max(trials, 1),
            "chi_specular_suffix": self.chi_specular_suffix(),
            "chi_specular_suffix_by_order": self.chi_specular_suffix_by_order().tolist(),
            "uncertainty_scope": (
                "sampled suffix diagnostics are conditional_on_traced_diffuse_vertices and do not claim a "
                "within-run or total-estimator standard error. Campaign seed replicas control primary-ray, "
                "sampled-face, body, and CDF uncertainty"
            ),
            "sampling_identity": {
                "status": "experimental_opt_in",
                "face_proposal": SPECULAR_FACE_PROPOSAL,
                "source_proposal": SPECULAR_SOURCE_PROPOSAL,
                "counter_generator": SPECULAR_COUNTER_GENERATOR,
                "source_counter_dimension": SPECULAR_SOURCE_COUNTER_DIMENSION,
                "face_counter_dimension": SPECULAR_FACE_COUNTER_DIMENSION,
                "source_count": int(self._probabilities.size),
                "source_support": int(np.count_nonzero(self._probabilities)),
                "source_probability_sha256": _array_sha256(self._probabilities),
                "face_count": int(self._face_probability.size),
                "face_probability_sha256": _array_sha256(self._face_probability),
                "surface_support_complete": self._surface_support_complete,
                "surface_scene_face_count": self._surface_scene_face_count,
                "surface_construction": "all_nondegenerate_mesh_faces",
            },
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "chi_bounce": self.chi_bounce(),
            "chi_by_order": self.chi_by_order().tolist(),
            "connections": self.connections,
            "cleared": self.cleared,
            "clear_fraction": self.cleared / max(self.connections, 1),
            "rays": self.rays,
            "samples": self.samples,
            "max_order": self.max_order,
            "field_collected": self.collect_field,
            "source_sampling": "validated_float32_vose_alias",
            "source_probability_count": int(self._probabilities.size),
            "counter_key": "trace_seed_plus_offset,global_ray_index,bounce_depth,sample_index",
            "direct_atoms": "exact_host_calculation_required_separately",
            "specular_suffix_supported": True,
            "sampled_specular_suffix": self.sampled_specular_diagnostics(),
        }

    def _bind_device(self, mi: Any, dr: Any) -> tuple[Any, ...]:
        key = (str(mi.variant()), id(mi.Float))
        if self._device_arrays is not None and self._device_key == key:
            return self._device_arrays
        sites = self._sites
        arrays = (
            mi.Float(sites[:, 0]),
            mi.Float(sites[:, 1]),
            mi.Float(sites[:, 2]),
            mi.Float(self._alias_threshold),
            mi.UInt32(self._alias_index),
        )
        dr.eval(*arrays)
        self._device_key = key
        self._device_arrays = arrays
        return arrays

    def _bind_specular_device(self, kernel: Any) -> tuple[Any, ...]:
        self._prepare_specular_support(kernel)
        if self._face_probability.size == 0:
            return ()
        mi, dr = kernel.mi, kernel.dr
        key = (str(mi.variant()), id(kernel.geometry))
        if self._specular_device_arrays is not None and self._specular_device_key == key:
            return self._specular_device_arrays
        triangle = self._face_triangles
        normal = self._face_normals
        arrays = (
            mi.Float(triangle[:, 0, 0]),
            mi.Float(triangle[:, 0, 1]),
            mi.Float(triangle[:, 0, 2]),
            mi.Float(triangle[:, 1, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 1, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 1, 2] - triangle[:, 0, 2]),
            mi.Float(triangle[:, 2, 0] - triangle[:, 0, 0]),
            mi.Float(triangle[:, 2, 1] - triangle[:, 0, 1]),
            mi.Float(triangle[:, 2, 2] - triangle[:, 0, 2]),
            mi.Float(normal[:, 0]),
            mi.Float(normal[:, 1]),
            mi.Float(normal[:, 2]),
            mi.UInt32(self._face_index),
            mi.Float(self._face_probability.astype(np.float32)),
            mi.Float(self._face_alias_threshold),
            mi.UInt32(self._face_alias_index),
        )
        dr.eval(*arrays)
        self._specular_device_key = key
        self._specular_device_arrays = arrays
        return arrays

    def _bind_first_diffuse_audit_device(self, kernel: Any) -> tuple[Any, ...]:
        if self.first_diffuse_audit is None:
            return ()
        key = (str(kernel.mi.variant()), id(kernel.geometry))
        if self._first_diffuse_audit_device_key == key and self._first_diffuse_audit_device_arrays is not None:
            return self._first_diffuse_audit_device_arrays
        audit = self.first_diffuse_audit
        if audit.face_to_category_row.shape != kernel.face_class.shape:
            raise ValueError("first-diffuse audit face maps must match the device support mesh")
        arrays = (
            kernel.mi.Int32(audit.face_to_category_row),
            kernel.mi.UInt32(audit.category_by_texel.reshape(-1).astype(np.uint32)),
            kernel.mi.UInt32(audit.fallback_category_by_face.astype(np.uint32)),
        )
        kernel.dr.eval(*arrays)
        self._first_diffuse_audit_device_key = key
        self._first_diffuse_audit_device_arrays = arrays
        return arrays

    def _device_state(
        self,
        kernel: Any,
        ray_index: Any,
        ray_count: int,
        trace_seed: int,
    ) -> _DeviceNextEventState:
        return _DeviceNextEventState(self, kernel, ray_index, ray_count, trace_seed)


class _DeviceNextEventState:
    """Per-range device arrays.  Created and consumed by DeviceSbrKernel."""

    def __init__(
        self,
        gather: DeviceNextEventGather,
        kernel: Any,
        ray_index: Any,
        ray_count: int,
        trace_seed: int,
    ) -> None:
        self.gather = gather
        self.kernel = kernel
        self.mi = kernel.mi
        self.dr = kernel.dr
        self.ray_index = ray_index
        self.ray_count = int(ray_count)
        self.seed_value = (int(trace_seed) + int(gather.seed_offset)) & 0xFFFFFFFFFFFFFFFF
        self.site_x, self.site_y, self.site_z, self.alias_threshold, self.alias_index = gather._bind_device(
            self.mi, self.dr
        )
        self.weight_by_order: list[Any] = [self.dr.zeros(self.mi.Float, self.ray_count)]
        self.connections_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.cleared_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_weight_by_order: list[Any] = [self.dr.zeros(self.mi.Float, self.ray_count)]
        self.specular_candidates_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_geometric_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_visible_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_accepted_by_order: list[Any] = [self.dr.zeros(self.mi.UInt32, 1)]
        self.specular_seed = (int(trace_seed) + int(gather.sampled_specular_seed_offset)) & _MASK_64
        self.specular_seed_word = self.dr.opaque(
            self.mi.UInt64,
            _splitmix_seed_word(self.specular_seed),
        )
        self.specular_arrays = gather._bind_specular_device(kernel)
        self.first_diffuse_audit_arrays = gather._bind_first_diffuse_audit_device(kernel)
        if gather.first_diffuse_audit is None:
            self.first_diffuse_audit_event_count: list[Any] = []
            self.first_diffuse_audit_weight_by_category: list[Any] = []
        else:
            categories = gather.first_diffuse_audit.category_count
            self.first_diffuse_audit_event_count = [self.dr.zeros(self.mi.UInt32, 1) for _ in range(categories)]
            self.first_diffuse_audit_weight_by_category = [
                self.dr.zeros(self.mi.Float, self.ray_count) for _ in range(categories)
            ]
        self.loop_errors: list[Any] = []

    def _first_diffuse_category(self, face: Any, barycentric_uv: Any, active: Any) -> Any:
        mi, dr = self.mi, self.dr
        if self.gather.first_diffuse_audit is None or not self.first_diffuse_audit_arrays:
            raise RuntimeError("first-diffuse category lookup requires an audit classifier")
        face_to_row, category_by_texel, fallback_by_face = self.first_diffuse_audit_arrays
        row = dr.gather(mi.Int32, face_to_row, face, active)
        present = active & (row >= 0)
        safe_row = dr.maximum(row, 0)
        height, width = self.gather.first_diffuse_audit.resolution
        u = dr.clip(barycentric_uv.x, 0.0, 1.0)
        v = dr.clip(barycentric_uv.y, 0.0, 1.0)
        scaled_row = v * float(height - 1)
        scaled_column = u * float(width - 1)
        texel_row = mi.Int32(dr.floor(scaled_row + 0.5))
        texel_column = mi.Int32(dr.floor(scaled_column + 0.5))
        row_excess = mi.Float(texel_row) - scaled_row
        column_excess = mi.Float(texel_column) - scaled_column
        outside = mi.Float(texel_row) / float(height - 1) + mi.Float(texel_column) / float(width - 1) > 1.0 + 1.0e-7
        step_row = outside & (row_excess >= column_excess)
        texel_row = dr.select(step_row, texel_row - 1, texel_row)
        texel_column = dr.select(outside & ~step_row, texel_column - 1, texel_column)
        texel = (safe_row * height + texel_row) * width + texel_column
        texel_category = dr.gather(mi.UInt32, category_by_texel, texel, present)
        fallback = dr.gather(mi.UInt32, fallback_by_face, face, active)
        return dr.select(present, texel_category, fallback)

    def _sample_source(self, uniform: Any, active: Any) -> tuple[Any, Any]:
        mi, dr = self.mi, self.dr
        count = int(self.gather._sites.shape[0])
        scaled = uniform * float(count)
        column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
        fraction = scaled - mi.Float(column)
        threshold = dr.gather(mi.Float, self.alias_threshold, column, active)
        alternate = dr.gather(mi.UInt32, self.alias_index, column, active)
        index = dr.select(fraction < threshold, column, alternate)
        target = mi.Point3f(
            dr.gather(mi.Float, self.site_x, index, active),
            dr.gather(mi.Float, self.site_y, index, active),
            dr.gather(mi.Float, self.site_z, index, active),
        )
        return index, target

    def _sample_specular_face(self, uniform: Any, active: Any) -> tuple[Any, ...]:
        mi, dr = self.mi, self.dr
        if not self.specular_arrays:
            raise RuntimeError("sampled specular face support is empty")
        (
            p0x,
            p0y,
            p0z,
            e1x,
            e1y,
            e1z,
            e2x,
            e2y,
            e2z,
            nx,
            ny,
            nz,
            face_index,
            probability,
            threshold,
            alias,
        ) = self.specular_arrays
        count = int(self.gather._face_probability.size)
        scaled = uniform * float(count)
        column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
        fraction = scaled - mi.Float(column)
        cut = dr.gather(mi.Float, threshold, column, active)
        alternate = dr.gather(mi.UInt32, alias, column, active)
        surface = dr.select(fraction < cut, column, alternate)

        def scalar(array: Any) -> Any:
            return dr.gather(mi.Float, array, surface, active)

        plane = mi.Point3f(scalar(p0x), scalar(p0y), scalar(p0z))
        edge1 = mi.Vector3f(scalar(e1x), scalar(e1y), scalar(e1z))
        edge2 = mi.Vector3f(scalar(e2x), scalar(e2y), scalar(e2z))
        normal = mi.Vector3f(scalar(nx), scalar(ny), scalar(nz))
        actual_face = dr.gather(mi.UInt32, face_index, surface, active)
        q = dr.gather(mi.Float, probability, surface, active)
        return surface, plane, edge1, edge2, normal, actual_face, q

    def _ensure_specular_order(self, order: int) -> None:
        while len(self.specular_weight_by_order) <= order:
            self.specular_weight_by_order.append(self.dr.zeros(self.mi.Float, self.ray_count))
            self.specular_candidates_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_geometric_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_visible_by_order.append(self.dr.zeros(self.mi.UInt32, 1))
            self.specular_accepted_by_order.append(self.dr.zeros(self.mi.UInt32, 1))

    def vertex(
        self,
        depth: int,
        position: Any,
        normal: Any,
        throughput: Any,
        share: Any,
        active: Any,
        random_draw: Any,
        face: Any | None = None,
        barycentric_uv: Any | None = None,
    ) -> None:
        """Add one fixed-width order row after material response."""
        if self.gather.first_material_interaction_only and depth != 0:
            return
        mi, dr = self.mi, self.dr
        total_weight = dr.zeros(mi.Float, self.ray_count)
        total_connections = dr.zeros(mi.UInt32, 1)
        total_cleared = dr.zeros(mi.UInt32, 1)
        if self.gather.first_diffuse_audit is None:
            audit_category = None
        else:
            if face is None or barycentric_uv is None:
                raise RuntimeError("first-diffuse audit requires exact first-hit face and barycentric coordinates")
            audit_category = self._first_diffuse_category(face, barycentric_uv, active)
        lobe = throughput * (1.0 - share) / np.pi
        for sample in range(self.gather.samples):
            _source_index, target = self._sample_source(random_draw(sample), active)
            delta = target - position
            distance = dr.norm(delta)
            direction = delta / dr.maximum(distance, 1.0e-12)
            cosine = dr.dot(direction, normal)
            worth = active & (cosine > 0.0) & (distance > float(self.gather.min_connect_m)) & (lobe > 0.0)
            total_connections += dr.sum(mi.UInt32(worth))
            lifted = position + float(self.gather.lift_m) * normal
            shadow_delta = target - lifted
            shadow_distance = dr.norm(shadow_delta)
            shadow_direction = shadow_delta / dr.maximum(shadow_distance, 1.0e-12)
            start = lifted + float(self.gather.epsilon_m) * shadow_direction
            clear, loop_error = self._visible(
                start,
                shadow_direction,
                shadow_distance,
                worth,
                depth,
            )
            self.loop_errors.append(dr.sum(mi.UInt32(loop_error)))
            total_cleared += dr.sum(mi.UInt32(clear))
            weight = lobe * cosine / dr.maximum(distance * distance, 1.0e-24)
            total_weight += dr.select(clear, weight, 0.0)
            if audit_category is not None:
                for category in range(self.gather.first_diffuse_audit.category_count):
                    accepted = clear & (audit_category == category)
                    self.first_diffuse_audit_event_count[category] += dr.sum(mi.UInt32(accepted))
                    self.first_diffuse_audit_weight_by_category[category] += dr.select(accepted, weight, 0.0)
        self._sampled_specular_vertex(depth, position, normal, lobe, active)
        self.weight_by_order.append(total_weight)
        self.connections_by_order.append(total_connections)
        self.cleared_by_order.append(total_cleared)
        dr.eval(total_weight, total_connections, total_cleared)

    def _sampled_specular_vertex(
        self,
        depth: int,
        position: Any,
        vertex_normal: Any,
        diffuse_lobe: Any,
        active: Any,
    ) -> None:
        """Sample one complete-support source/finite-face suffix per trial."""
        if self.gather.specular_suffix_order == 0 or not self.specular_arrays:
            return
        total_order = depth + 2
        maximum_order = (
            int(self.kernel.config.max_bounces) if self.gather.max_order is None else int(self.gather.max_order)
        )
        if total_order > maximum_order:
            return
        mi, dr = self.mi, self.dr
        eligible = active & (diffuse_lobe > 0.0)
        endpoint_count = dr.sum(mi.UInt64(eligible))
        sample_count = int(self.gather.sampled_specular_samples)
        total_weight = dr.zeros(mi.Float, self.ray_count)
        geometric_total = dr.zeros(mi.UInt32, 1)
        visible_total = dr.zeros(mi.UInt32, 1)
        accepted_total = dr.zeros(mi.UInt32, 1)
        for sample in range(sample_count):
            counter = (
                mi.UInt64(depth) * mi.UInt64(int(self.kernel.config.rays)) + mi.UInt64(self.ray_index)
            ) * mi.UInt64(sample_count) + mi.UInt64(sample)
            source_uniform = _splitmix_uniform(
                mi,
                counter,
                self.specular_seed_word,
                SPECULAR_SOURCE_COUNTER_DIMENSION,
            )
            face_uniform = _splitmix_uniform(
                mi,
                counter,
                self.specular_seed_word,
                SPECULAR_FACE_COUNTER_DIMENSION,
            )
            _source_index, source = self._sample_source(source_uniform, eligible)
            (
                _surface,
                plane,
                edge1,
                edge2,
                surface_normal,
                expected_face,
                face_probability,
            ) = self._sample_specular_face(face_uniform, eligible)
            source_side = dr.dot(source - plane, surface_normal)
            receiver_side = dr.dot(position - plane, surface_normal)
            image = source - 2.0 * source_side * surface_normal
            image_line = image - position
            denominator = dr.dot(image_line, surface_normal)
            fraction = -receiver_side / dr.select(dr.abs(denominator) > 1.0e-30, denominator, 1.0)
            reflection = position + fraction * image_line
            offset = reflection - plane
            d11 = dr.dot(edge1, edge1)
            d12 = dr.dot(edge1, edge2)
            d22 = dr.dot(edge2, edge2)
            q1 = dr.dot(offset, edge1)
            q2 = dr.dot(offset, edge2)
            determinant = d11 * d22 - d12 * d12
            safe_determinant = dr.select(determinant > 1.0e-24, determinant, 1.0)
            bary_u = (d22 * q1 - d12 * q2) / safe_determinant
            bary_v = (d11 * q2 - d12 * q1) / safe_determinant
            tolerance = 2.0e-8
            inside = (
                (determinant > 1.0e-24)
                & (bary_u >= -tolerance)
                & (bary_v >= -tolerance)
                & (bary_u + bary_v <= 1.0 + tolerance)
            )
            distinct = dr.squared_norm(source - position) > 1.0e-24
            geometric = (
                eligible
                & distinct
                & (source_side * receiver_side > float(self.gather.epsilon_m) ** 2)
                & dr.isfinite(fraction)
                & (fraction > 0.0)
                & (fraction < 1.0)
                & inside
            )
            geometric_total += dr.sum(mi.UInt32(geometric))

            source_leg = reflection - source
            source_range = dr.norm(source_leg)
            source_direction = source_leg / dr.maximum(source_range, 1.0e-12)
            source_clear, source_loop_error = self._visible(
                source + float(self.gather.epsilon_m) * source_direction,
                source_direction,
                source_range,
                geometric,
                depth,
                expected_face=expected_face,
            )
            receiver_leg = position - reflection
            receiver_range = dr.norm(receiver_leg)
            arrival = receiver_leg / dr.maximum(receiver_range, 1.0e-12)
            receiver_clear, receiver_loop_error = self._visible(
                reflection + float(self.gather.epsilon_m) * arrival,
                arrival,
                receiver_range,
                source_clear,
                depth,
            )
            self.loop_errors.extend(
                (
                    dr.sum(mi.UInt32(source_loop_error)),
                    dr.sum(mi.UInt32(receiver_loop_error)),
                )
            )
            visible = source_clear & receiver_clear
            visible_total += dr.sum(mi.UInt32(visible))

            source_cosine = dr.clip(dr.abs(dr.dot(source_direction, surface_normal)), 0.0, 1.0)
            fallback_material = dr.gather(mi.UInt32, self.kernel._face_class_device, expected_face, visible)
            reflectance, coherent_share, nonblocking = self.kernel._surface_response_at(
                source_cosine,
                fallback_material,
                expected_face,
                mi.Point2f(bary_u, bary_v),
                visible,
            )
            toward_reflection = -arrival
            diffuse_cosine = dr.dot(toward_reflection, vertex_normal)
            path_length = source_range + receiver_range
            contribution = (
                diffuse_lobe
                * dr.maximum(diffuse_cosine, 0.0)
                * reflectance
                * coherent_share
                / dr.maximum(path_length * path_length * face_probability, 1.0e-24)
            )
            accepted = (
                visible & ~nonblocking & (diffuse_cosine > 0.0) & (contribution > 0.0) & dr.isfinite(contribution)
            )
            accepted_total += dr.sum(mi.UInt32(accepted))
            total_weight += dr.select(accepted, contribution, 0.0)

        self._ensure_specular_order(total_order)
        self.specular_weight_by_order[total_order] += total_weight
        self.specular_candidates_by_order[total_order] += mi.UInt32(endpoint_count * mi.UInt64(sample_count))
        self.specular_geometric_by_order[total_order] += geometric_total
        self.specular_visible_by_order[total_order] += visible_total
        self.specular_accepted_by_order[total_order] += accepted_total
        dr.eval(
            total_weight,
            self.specular_candidates_by_order[total_order],
            geometric_total,
            visible_total,
            accepted_total,
        )

    def _visible(
        self,
        start: Any,
        direction: Any,
        target_distance: Any,
        active: Any,
        depth: int,
        *,
        expected_face: Any | None = None,
    ) -> tuple[Any, Any]:
        """Cast one leg, passing through atlas cells marked non-blocking.

        A source-to-reflector leg supplies ``expected_face`` and succeeds only
        when that exact finite face is reached.  A reflector-to-endpoint or
        direct diffuse leg omits it and succeeds on a miss or after reaching
        the endpoint range.
        """
        mi, dr = self.mi, self.dr
        searching = active
        query = start
        travelled = dr.zeros(mi.Float, self.ray_count)
        crossings = dr.zeros(mi.UInt32, self.ray_count)
        clear = dr.zeros(mi.Bool, self.ray_count)
        limit = int(self.kernel.face_class.size)

        def cond(searching: Any, query: Any, travelled: Any, crossings: Any, clear: Any) -> Any:
            del query, travelled, clear
            return searching & (crossings <= limit)

        def step(
            searching: Any,
            query: Any,
            travelled: Any,
            crossings: Any,
            clear: Any,
        ) -> tuple[Any, ...]:
            intersection = self.kernel.geometry.intersect_device(query, direction, searching)
            at_target = travelled + intersection.distance >= target_distance - 2.0 * float(self.gather.epsilon_m)
            if expected_face is None:
                reached = searching & (~intersection.hit | at_target)
            else:
                reached = searching & intersection.hit & at_target & (intersection.face == expected_face)
            clear |= reached
            before = searching & intersection.hit & ~at_target
            nonblocking = self.kernel._surface_nonblocking(intersection, before)
            pass_through = before & nonblocking
            crossings = dr.select(pass_through, crossings + 1, crossings)
            travelled = dr.select(
                pass_through,
                travelled + intersection.distance + float(self.gather.epsilon_m),
                travelled,
            )
            query = dr.select(
                pass_through,
                query + (intersection.distance + float(self.gather.epsilon_m)) * direction,
                query,
            )
            searching = pass_through
            return searching, query, travelled, crossings, clear

        searching, _query, _travelled, _crossings, clear = dr.while_loop(
            state=(searching, query, travelled, crossings, clear),
            cond=cond,
            body=step,
            mode="symbolic" if str(getattr(self.kernel.geometry, "variant", "")).startswith("cuda") else "evaluated",
            label=f"next-event non-blocking shadow at bounce {depth}",
        )
        return clear, searching

    def transfer(self, ray_start: int) -> DeviceNextEventBatch:
        """Copy all order rows in one packed device-to-host transfer."""
        mi, dr = self.mi, self.dr
        orders = max(len(self.weight_by_order), len(self.specular_weight_by_order))
        while len(self.weight_by_order) < orders:
            self.weight_by_order.append(dr.zeros(mi.Float, self.ray_count))
            self.connections_by_order.append(dr.zeros(mi.UInt32, 1))
            self.cleared_by_order.append(dr.zeros(mi.UInt32, 1))
        self._ensure_specular_order(orders - 1)
        packed_parts: list[Any] = []
        loop_errors = dr.zeros(mi.UInt32, 1)
        for value in self.loop_errors:
            loop_errors += value
        packed_parts.append(dr.reinterpret_array(mi.Float, loop_errors))
        for value in self.connections_by_order:
            packed_parts.append(dr.reinterpret_array(mi.Float, value))
        for value in self.cleared_by_order:
            packed_parts.append(dr.reinterpret_array(mi.Float, value))
        for values in (
            self.specular_candidates_by_order,
            self.specular_geometric_by_order,
            self.specular_visible_by_order,
            self.specular_accepted_by_order,
        ):
            for value in values:
                packed_parts.append(dr.reinterpret_array(mi.Float, value))
        audit_categories = len(self.first_diffuse_audit_event_count)
        for value in self.first_diffuse_audit_event_count:
            packed_parts.append(dr.reinterpret_array(mi.Float, value))
        packed_parts.extend(self.weight_by_order)
        packed_parts.extend(self.specular_weight_by_order)
        packed_parts.extend(self.first_diffuse_audit_weight_by_category)
        transferred = np.asarray(dr.concat(packed_parts)).copy()
        header = 1 + 6 * orders + audit_categories
        if transferred.size != header + (2 * orders + audit_categories) * self.ray_count:
            raise RuntimeError("device next-event record packing is inconsistent")
        counts = transferred[1 : 1 + 6 * orders].view(np.uint32).astype(np.uint64)
        audit_counts = (
            transferred[1 + 6 * orders : header].view(np.uint32).astype(np.uint64) if audit_categories else None
        )
        if transferred[:1].view(np.uint32)[0]:
            raise RuntimeError(
                "device next-event shadow ray exceeded the support-mesh face count while crossing "
                "non-blocking atlas cells"
            )
        weight_size = 2 * orders * self.ray_count
        weight = transferred[header : header + weight_size].reshape(2, orders, self.ray_count)
        audit_weight = (
            transferred[header + weight_size :].reshape(audit_categories, self.ray_count) if audit_categories else None
        )
        return DeviceNextEventBatch(
            weight_by_order=weight[0],
            connections_by_order=counts[:orders],
            cleared_by_order=counts[orders : 2 * orders],
            ray_start=ray_start,
            rays=self.ray_count,
            samples=self.gather.samples,
            specular_weight_by_order=weight[1],
            specular_candidates_by_order=counts[2 * orders : 3 * orders],
            specular_geometric_by_order=counts[3 * orders : 4 * orders],
            specular_visible_by_order=counts[4 * orders : 5 * orders],
            specular_accepted_by_order=counts[5 * orders : 6 * orders],
            sampled_specular_samples=self.gather.sampled_specular_samples,
            first_diffuse_audit_event_count=audit_counts,
            first_diffuse_audit_weight_by_category=audit_weight,
        )

    def transfer_reduced(
        self,
        ray_start: int,
        launch_cell: Any | None,
        field_cells: int,
    ) -> DeviceNextEventReduction:
        """Reduce order totals and launch-cell fields before host transfer."""
        mi, dr = self.mi, self.dr
        orders = max(len(self.weight_by_order), len(self.specular_weight_by_order))
        while len(self.weight_by_order) < orders:
            self.weight_by_order.append(dr.zeros(mi.Float, self.ray_count))
            self.connections_by_order.append(dr.zeros(mi.UInt32, 1))
            self.cleared_by_order.append(dr.zeros(mi.UInt32, 1))
        self._ensure_specular_order(orders - 1)

        loop_errors = dr.zeros(mi.UInt32, 1)
        for value in self.loop_errors:
            loop_errors += value
        count_parts: list[Any] = [loop_errors]
        count_parts.extend(self.connections_by_order)
        count_parts.extend(self.cleared_by_order)
        for values in (
            self.specular_candidates_by_order,
            self.specular_geometric_by_order,
            self.specular_visible_by_order,
            self.specular_accepted_by_order,
        ):
            count_parts.extend(values)
        count_parts.extend(self.first_diffuse_audit_event_count)

        raw_totals = [dr.sum(mi.Float64(value)) for value in self.weight_by_order]
        specular_totals = [dr.sum(mi.Float64(value)) for value in self.specular_weight_by_order]
        field_parts: list[Any] = []
        if self.gather.collect_field:
            if launch_cell is None or field_cells < 1:
                raise RuntimeError("compact field collection needs resident launch-cell indices")
            diffuse_field = dr.zeros(mi.Float64, field_cells)
            specular_field = dr.zeros(mi.Float64, field_cells)
            diffuse_per_ray = dr.zeros(mi.Float64, self.ray_count)
            specular_per_ray = dr.zeros(mi.Float64, self.ray_count)
            for value in self.weight_by_order:
                diffuse_per_ray += mi.Float64(value)
            for value in self.specular_weight_by_order:
                specular_per_ray += mi.Float64(value)
            dr.scatter_reduce(
                dr.ReduceOp.Add,
                diffuse_field,
                diffuse_per_ray,
                launch_cell,
                mode=dr.ReduceMode.Auto,
            )
            dr.scatter_reduce(
                dr.ReduceOp.Add,
                specular_field,
                specular_per_ray,
                launch_cell,
                mode=dr.ReduceMode.Auto,
            )
            field_parts.extend((diffuse_field, specular_field))

        audit_categories = len(self.first_diffuse_audit_event_count)
        audit_totals = [dr.sum(mi.Float64(value)) for value in self.first_diffuse_audit_weight_by_category]
        audit_field_parts: list[Any] = []
        if audit_categories and self.gather.collect_field:
            if launch_cell is None or field_cells < 1:
                raise RuntimeError("compact first-diffuse audit field needs resident launch-cell indices")
            for value in self.first_diffuse_audit_weight_by_category:
                category_field = dr.zeros(mi.Float64, field_cells)
                dr.scatter_reduce(
                    dr.ReduceOp.Add,
                    category_field,
                    mi.Float64(value),
                    launch_cell,
                    mode=dr.ReduceMode.Auto,
                )
                audit_field_parts.append(category_field)

        counts = np.asarray(dr.concat(count_parts), dtype=np.uint32).astype(np.uint64)
        if counts[0]:
            raise RuntimeError(
                "device next-event shadow ray exceeded the support-mesh face count while crossing "
                "non-blocking atlas cells"
            )
        floating_parts = raw_totals + specular_totals + field_parts + audit_totals + audit_field_parts
        floating = np.asarray(dr.concat(floating_parts), dtype=np.float64)
        total_count = 2 * orders
        standard_field_count = 2 * field_cells if self.gather.collect_field else 0
        audit_field_count = audit_categories * field_cells if self.gather.collect_field else 0
        expected = total_count + standard_field_count + audit_categories + audit_field_count
        if floating.size != expected or counts.size != 1 + 6 * orders + audit_categories:
            raise RuntimeError("compact device next-event reduction packing is inconsistent")
        field_offset = total_count
        raw_field = (
            floating[field_offset : field_offset + field_cells].copy()
            if self.gather.collect_field
            else np.empty(0, dtype=np.float64)
        )
        specular_field = (
            floating[field_offset + field_cells : field_offset + 2 * field_cells].copy()
            if self.gather.collect_field
            else np.empty(0, dtype=np.float64)
        )
        audit_offset = total_count + standard_field_count
        audit_raw = floating[audit_offset : audit_offset + audit_categories].copy() if audit_categories else None
        audit_field = (
            floating[audit_offset + audit_categories :].reshape(audit_categories, field_cells).copy()
            if audit_categories and self.gather.collect_field
            else (np.empty((audit_categories, 0), dtype=np.float64) if audit_categories else None)
        )
        return DeviceNextEventReduction(
            raw_by_order=floating[:orders].copy(),
            specular_raw_by_order=floating[orders:total_count].copy(),
            connections_by_order=counts[1 : 1 + orders],
            cleared_by_order=counts[1 + orders : 1 + 2 * orders],
            specular_candidates_by_order=counts[1 + 2 * orders : 1 + 3 * orders],
            specular_geometric_by_order=counts[1 + 3 * orders : 1 + 4 * orders],
            specular_visible_by_order=counts[1 + 4 * orders : 1 + 5 * orders],
            specular_accepted_by_order=counts[1 + 5 * orders : 1 + 6 * orders],
            raw_field_mass=raw_field,
            specular_raw_field_mass=specular_field,
            ray_start=ray_start,
            rays=self.ray_count,
            samples=self.gather.samples,
            sampled_specular_samples=self.gather.sampled_specular_samples,
            first_diffuse_audit_event_count=(counts[1 + 6 * orders :].copy() if audit_categories else None),
            first_diffuse_audit_raw_by_category=audit_raw,
            first_diffuse_audit_raw_field_mass=audit_field,
        )


def device_source_sample(
    gather: DeviceNextEventGather,
    uniform: np.ndarray,
    *,
    variant: str = "llvm_ad_rgb",
) -> np.ndarray:
    """Exercise the exact resident alias sampler for a validation experiment."""
    import drjit as dr
    import mitsuba as mi

    if mi.variant() != variant:
        mi.set_variant(variant)
    values = np.asarray(uniform, dtype=np.float32)
    if values.ndim != 1 or np.any(values < 0.0) or np.any(values >= 1.0):
        raise ValueError("uniform values must be a one-dimensional array in [0, 1)")
    site_x, site_y, site_z, threshold, alias = gather._bind_device(mi, dr)
    del site_x, site_y, site_z
    draw = mi.Float(values)
    count = gather._sites.shape[0]
    scaled = draw * float(count)
    column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
    fraction = scaled - mi.Float(column)
    cut = dr.gather(mi.Float, threshold, column)
    alternate = dr.gather(mi.UInt32, alias, column)
    return np.asarray(dr.select(fraction < cut, column, alternate), dtype=np.uint32)


def device_specular_face_sample(
    gather: DeviceNextEventGather,
    kernel: Any,
    uniform: np.ndarray,
) -> np.ndarray:
    """Exercise the exact resident face alias table for validation."""
    mi, dr = kernel.mi, kernel.dr
    arrays = gather._bind_specular_device(kernel)
    if not arrays:
        return np.empty(0, dtype=np.uint32)
    values = np.asarray(uniform, dtype=np.float32)
    if values.ndim != 1 or np.any(values < 0.0) or np.any(values >= 1.0):
        raise ValueError("uniform values must be a one-dimensional array in [0, 1)")
    probability = arrays[13]
    threshold = arrays[14]
    alias = arrays[15]
    del probability
    draw = mi.Float(values)
    count = gather._face_probability.size
    scaled = draw * float(count)
    column = mi.UInt32(dr.minimum(dr.floor(scaled), float(count - 1)))
    fraction = scaled - mi.Float(column)
    cut = dr.gather(mi.Float, threshold, column)
    alternate = dr.gather(mi.UInt32, alias, column)
    return np.asarray(dr.select(fraction < cut, column, alternate), dtype=np.uint32)
