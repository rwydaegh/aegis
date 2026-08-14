"""Focused closure checks for ray-reached evidence and exact specular audit."""

from types import SimpleNamespace

import numpy as np

from semantic_twin.materials.atlas import (
    FALLBACK_BOUND,
    FALLBACK_UNOBSERVED,
    FALLBACK_UNROUTABLE,
)
from semantic_twin.materials.atlas_binding import AtlasMaterialBinding
from semantic_twin.materials.evidence_audit import (
    AUDIT_CATEGORY_NAMES,
    ATLAS_INTERFACE,
    GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE,
    GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY,
    GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS,
    GEOMETRIC_FALLBACK_OTHER,
    GEOMETRIC_NO_PANORAMA_EVIDENCE,
    NONBLOCKING_WOODY_ATLAS,
    classify_joint_atlas,
)
from semantic_twin.transport.specular_evidence_audit import partition_specular_paths


def _binding() -> AtlasMaterialBinding:
    valid = np.array([[True, True, False], [True, True, False], [True, False, False]])
    supported = np.zeros((2, 3, 3), dtype=bool)
    supported[0, 0, 0] = True
    nonblocking = np.zeros_like(supported)
    nonblocking[0, 0, 1] = True
    nonblocking[1, 1, 0] = True
    probability = np.zeros((2, 3, 3, 1), dtype=np.float32)
    probability[supported, 0] = 1.0
    return AtlasMaterialBinding(
        face_to_atlas_row=np.array([0, 1, -1], dtype=np.int32),
        material_probability=probability,
        supported=supported,
        valid_texels=valid,
        material_names=("concrete",),
        material_class=np.array([0], dtype=np.int32),
        provenance={"rule": "focused test"},
        nonblocking=nonblocking,
    )


class _AuditAtlas(SimpleNamespace):
    def host_compatible_material_probability(self, _geometric_class: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self.raw_material_probability, self.compatible_support


def _atlas_state() -> _AuditAtlas:
    state = np.full((2, 3, 3), FALLBACK_UNOBSERVED, dtype=np.uint8)
    state[0, 0, 0] = FALLBACK_BOUND
    state[0, 0, 1] = FALLBACK_BOUND
    # This is deliberately ``bound`` despite host incompatibility. The
    # classifier must use the final geometric host gate, not this state code.
    state[0, 1, 0] = FALLBACK_BOUND
    state[1, 0, 0] = FALLBACK_UNROUTABLE
    state[1, 0, 1] = FALLBACK_BOUND
    state[1, 1, 0] = FALLBACK_BOUND
    raw = np.zeros((2, 3, 3, 1), dtype=np.float64)
    raw[0, 0, 0, 0] = 1.0
    raw[0, 0, 1, 0] = 1.0
    raw[0, 1, 0, 0] = 1.0
    raw[1, 0, 0, 0] = 1.0
    raw[1, 0, 1, 0] = 0.25
    raw[1, 1, 0, 0] = 1.0
    compatible = np.zeros((2, 3, 3), dtype=bool)
    compatible[0, 0, 0] = True
    compatible[0, 0, 1] = True
    compatible[1, 0, 0] = True
    compatible[1, 0, 1] = True
    compatible[1, 1, 0] = True
    support = (raw[..., 0] > 0.0).astype(np.float64)
    return _AuditAtlas(
        fallback_state_dense=state,
        raw_material_probability=raw,
        compatible_support=compatible,
        material_probability=raw,
        material_support=support,
        material_names=np.asarray(("concrete",)),
    )


def test_classifier_exports_device_shape_and_preserves_joint_gates() -> None:
    categories = classify_joint_atlas(_binding(), atlas=_atlas_state(), geometric_class=np.zeros(3, dtype=np.int64))
    assert categories.names == AUDIT_CATEGORY_NAMES
    assert categories.face_to_category_row.shape == (3,)
    assert categories.category_by_texel.shape == (2, 3, 3)
    assert categories.fallback_category_by_face.shape == (3,)
    assert categories.category_by_texel[0, 0, 0] == ATLAS_INTERFACE
    assert categories.category_by_texel[0, 0, 1] == NONBLOCKING_WOODY_ATLAS
    assert categories.category_by_texel[0, 1, 1] == GEOMETRIC_NO_PANORAMA_EVIDENCE
    assert categories.category_by_texel[0, 1, 0] == GEOMETRIC_EVIDENCE_REFUSED_HOST_COMPATIBILITY
    assert categories.category_by_texel[1, 0, 0] == GEOMETRIC_EVIDENCE_REFUSED_ATLAS_STATE
    assert categories.category_by_texel[1, 0, 1] == GEOMETRIC_EVIDENCE_REFUSED_INSUFFICIENT_STRUCTURAL_MASS
    assert categories.category_by_texel[0, 0, 2] == GEOMETRIC_FALLBACK_OTHER
    assert categories.fallback_category_by_face[2] == GEOMETRIC_NO_PANORAMA_EVIDENCE


def test_specular_partition_uses_surface_sequence_and_barycentric_uv_with_mass_closure() -> None:
    triangles = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            [[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 1.0, 0.0]],
            [[4.0, 0.0, 0.0], [5.0, 0.0, 0.0], [4.0, 1.0, 0.0]],
        ]
    )
    categories = classify_joint_atlas(_binding(), atlas=_atlas_state(), geometric_class=np.zeros(3, dtype=np.int64))
    paths = SimpleNamespace(
        transfer=np.array([2.0, 3.5, 0.0, 1.25]),
        surface_sequence=np.array([[0], [0], [1], [2]], dtype=np.int64),
        reflection_point=np.array(
            [
                [0.05, 0.05, 0.0],
                [0.25, 0.25, 0.0],
                [2.05, 0.05, 0.0],
                [4.2, 0.2, 0.0],
            ]
        ),
    )
    partition = partition_specular_paths(paths, triangles, categories)
    assert partition.total_count == 4
    assert partition.count_closure_residual == 0
    assert partition.transfer == 6.75
    assert partition.transfer_closure_residual == 0.0
    assert int(partition.count_by_category.sum()) == 4
    assert float(partition.transfer_by_category.sum()) == 6.75
    # The fourth row has no atlas row and has zero/nonzero mass just like any
    # other accepted atom.  Zero nonblocking events are never silently dropped.
    assert partition.path_category[-1] == GEOMETRIC_NO_PANORAMA_EVIDENCE
