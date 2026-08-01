from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.atlas_ledger import DepthConflictState, SparseAtlasLedger
from semantic_twin.decal_atlas import rasterize_triangle_evidence


def append_rows(ledger: SparseAtlasLedger, triangle_id: np.ndarray, *, views: str | np.ndarray = "view-a") -> None:
    count = len(triangle_id)
    ledger.append(
        triangle_id,
        np.column_stack((np.linspace(0.0, 0.2, count), np.full(count, 0.2))),
        np.arange(count, dtype=np.int32),
        np.tile(np.array((0.2, 0.8), dtype=np.float32), (count, 1)),
        np.linspace(0.6, 0.9, count),
        views,
        np.linspace(2.0, 5.0, count),
        [DepthConflictState.AGREEMENT] * count,
    )


def test_ledger_groups_sparse_observations_and_emits_rasterizer_inputs() -> None:
    ledger = SparseAtlasLedger(10, ["glass", "metal"])
    ledger.append(
        np.array((100_000_000, 4, 100_000_000)),
        np.array(((0.2, 0.3), (0.1, 0.1), (0.0, 0.4))),
        np.array((3, 1, 2)),
        np.array(((0.2, 0.8), (0.9, 0.1), (0.1, 0.7))),
        np.array((0.9, 0.7, 0.8)),
        np.array(("north", "east", "south")),
        np.array((12.0, 5.0, 15.0)),
        np.array(("agreement", "front_blocker", "agreement")),
    )

    groups = ledger.groups_by_triangle(depth_conflicts=[DepthConflictState.AGREEMENT])

    assert [group.triangle_id for group in groups] == [100_000_000]
    assert groups[0].view_ids.tolist() == ["north", "south"]
    np.testing.assert_allclose(groups[0].barycentric.sum(axis=1), 1.0)
    triangle, barycentric, labels, confidence = ledger.rasterize_inputs(depth_conflicts=[DepthConflictState.AGREEMENT])
    np.testing.assert_array_equal(triangle, np.array((100_000_000, 100_000_000)))
    np.testing.assert_array_equal(labels, np.array((3, 2)))
    assert ledger._triangle_id.shape == (10,)

    # The same sparse input is directly compatible with the decal rasterizer.
    raster_ledger = SparseAtlasLedger(2, ["glass", "metal"])
    append_rows(raster_ledger, np.array((0, 0)))
    triangle, barycentric, labels, confidence = raster_ledger.rasterize_inputs()
    atlas = rasterize_triangle_evidence(
        triangle,
        barycentric,
        labels,
        confidence,
        resolution=4,
        triangle_count=1,
        class_count=2,
    )
    assert np.any(atlas.labels[0] >= 0)


def test_ledger_capacity_is_bounded_and_retains_most_recent_rows() -> None:
    ledger = SparseAtlasLedger(3, ["glass", "metal"])
    append_rows(ledger, np.array((10, 11)))
    append_rows(ledger, np.array((12, 13)), views=np.array(("view-b", "view-c")))

    observations = ledger.observations()

    assert len(ledger) == 3
    np.testing.assert_array_equal(observations.triangle_id, np.array((11, 12, 13)))
    assert ledger._triangle_id.shape == (3,)
    assert ledger._material_channels.shape == (3, 2)


def test_ledger_npz_round_trip_retains_sparse_fields_and_capacity(tmp_path) -> None:
    ledger = SparseAtlasLedger(5, ["glass", "metal"])
    ledger.append(
        np.array((7, 9)),
        np.array(((0.25, 0.25), (0.1, 0.8))),
        np.array((4, -1)),
        np.array(((1.0, 0.0), (0.3, 0.6))),
        np.array((0.8, 0.4)),
        "camera-42",
        np.array((8.5, 20.0)),
        np.array((DepthConflictState.AGREEMENT, DepthConflictState.NO_MESH_HIT)),
    )
    path = tmp_path / "ledger.npz"
    ledger.save(path)

    restored = SparseAtlasLedger.load(path)

    assert restored.max_observations == 5
    assert restored.material_channel_names == ("glass", "metal")
    before, after = ledger.observations(), restored.observations()
    for name in (
        "triangle_id",
        "barycentric_uv",
        "label",
        "material_channels",
        "confidence",
        "view_id",
        "range_m",
        "depth_conflict",
    ):
        np.testing.assert_array_equal(getattr(after, name), getattr(before, name))


def test_ledger_rejects_invalid_barycentrics_and_unknown_depth_state() -> None:
    ledger = SparseAtlasLedger(2, ["brick"])
    with pytest.raises(ValueError, match="inside the triangle"):
        ledger.append(
            np.array((0,)),
            np.array(((0.8, 0.3),)),
            np.array((0,)),
            np.array(((0.5,),)),
            np.array((0.9,)),
            "view",
            np.array((1.0,)),
            "agreement",
        )
    with pytest.raises(ValueError, match="unknown state"):
        ledger.append(
            np.array((0,)),
            np.array(((0.2, 0.3),)),
            np.array((0,)),
            np.array(((0.5,),)),
            np.array((0.9,)),
            "view",
            np.array((1.0,)),
            "not-a-state",
        )


def test_ledger_load_refuses_a_capacity_that_would_silently_drop_rows(tmp_path) -> None:
    ledger = SparseAtlasLedger(1000, ["glass", "metal"])
    append_rows(ledger, np.arange(300))
    path = tmp_path / "ledger.npz"
    ledger.save(path)

    with pytest.raises(ValueError, match="does not fit"):
        SparseAtlasLedger.load(path, max_observations=100)

    restored = SparseAtlasLedger.load(path, max_observations=5000)
    assert restored.max_observations == 5000
    assert len(restored) == 300
