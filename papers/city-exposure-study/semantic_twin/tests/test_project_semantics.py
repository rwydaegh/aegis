from __future__ import annotations

import numpy as np

from semantic_twin.scene.semantic_projection import UNOBSERVED_MATERIAL, assign_materials, material_groups


def test_never_observed_faces_carry_a_sentinel_instead_of_material_zero() -> None:
    face_material = np.array((0, 0, 3, 0), dtype=np.uint16)
    visible = np.array((False, True, True, False))

    assigned = assign_materials(face_material, visible)

    assert assigned.tolist() == [UNOBSERVED_MATERIAL, 0, 3, UNOBSERVED_MATERIAL]
    assert UNOBSERVED_MATERIAL != 0


def test_unobserved_faces_never_reach_an_itu_material_group() -> None:
    face_material = np.array((0, 0, 3, 0), dtype=np.uint16)
    visible = np.array((False, True, True, False))

    groups = material_groups(assign_materials(face_material, visible), {0: "unknown", 3: "vegetation"})

    assert sorted(groups) == ["unknown", "vegetation"]
    assert int(groups["unknown"].sum()) == 1
    assert int(sum(int(selection.sum()) for selection in groups.values())) == int(visible.sum())
