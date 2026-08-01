from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.decal_atlas import barycentric_uv, conservative_simplify_contour, rasterize_triangle_evidence


def test_barycentric_uv_is_canonical_and_rejects_degenerate_triangle() -> None:
    vertices = np.array(((2.0, 0.0, 1.0), (4.0, 0.0, 1.0), (2.0, 3.0, 1.0)))

    assert np.array_equal(barycentric_uv(vertices), np.array(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))))
    with pytest.raises(ValueError, match="non-degenerate"):
        barycentric_uv(np.array(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (2.0, 2.0, 2.0))))


def test_rasterizer_accumulates_weighted_classes_and_masks_outside_triangle() -> None:
    atlas = rasterize_triangle_evidence(
        triangle_indices=np.array((0, 0, 0, 1)),
        barycentric=np.array(((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))),
        labels=np.array((2, 1, 1, 0)),
        confidence=np.array((3.0, 1.0, 2.0, 4.0)),
        resolution=5,
        triangle_count=2,
        class_count=3,
    )

    assert atlas.weights.shape == (2, 5, 5, 3)
    assert atlas.labels[0, 0, 0] == 2
    assert atlas.support[0, 0, 0] == pytest.approx(4.0)
    assert atlas.confidence[0, 0, 0] == pytest.approx(0.75)
    assert atlas.labels[0, 0, 4] == 1
    assert atlas.labels[1, 4, 0] == 0
    assert not atlas.valid_texels[4, 4]
    assert np.all(atlas.labels[:, 4, 4] == -1)
    assert np.all(atlas.support[:, 4, 4] == 0.0)


def test_rasterizer_ignores_unlabelled_observations_but_rejects_bad_geometry() -> None:
    atlas = rasterize_triangle_evidence(
        triangle_indices=np.array((0,)),
        barycentric=np.array(((0.2, 0.3, 0.5),)),
        labels=np.array((-1,)),
        confidence=np.array((1.0,)),
        resolution=(3, 4),
        triangle_count=1,
    )

    assert atlas.weights.shape == (1, 3, 4, 0)
    assert np.all(atlas.labels == -1)
    with pytest.raises(ValueError, match="sum to one"):
        rasterize_triangle_evidence(
            np.array((0,)), np.array(((0.4, 0.4, 0.4),)), np.array((0,)), np.array((1.0,)), resolution=3
        )


def test_conservative_simplifier_removes_collinear_points_but_preserves_concave_notch() -> None:
    rectangle = np.array(((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)))
    simplified = conservative_simplify_contour(rectangle, tolerance=0.01)

    assert len(simplified) == 4
    assert not np.any(np.all(simplified == (1.0, 0.0), axis=1))

    notch = np.array(((0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (2.0, 3.0), (2.0, 1.0), (1.0, 1.0), (1.0, 3.0), (0.0, 3.0)))
    guarded = conservative_simplify_contour(notch, tolerance=10.0)

    assert np.any(np.all(guarded == (2.0, 1.0), axis=1))
    assert np.any(np.all(guarded == (1.0, 1.0), axis=1))


def test_hypotenuse_observations_stay_inside_the_canonical_triangle() -> None:
    atlas = rasterize_triangle_evidence(
        triangle_indices=np.array((0,)),
        barycentric=np.array(((0.0, 0.5, 0.5),)),
        labels=np.array((1,)),
        confidence=np.array((2.0,)),
        resolution=8,
        triangle_count=1,
        class_count=2,
    )

    assert atlas.support.sum() == pytest.approx(2.0)
    assert atlas.weights.sum() == pytest.approx(2.0)
    assert int((atlas.labels == 1).sum()) == 1


def test_a_high_triangle_identifier_does_not_allocate_a_dense_atlas() -> None:
    atlas = rasterize_triangle_evidence(
        triangle_indices=np.array((157_743,)),
        barycentric=np.array(((0.2, 0.3, 0.5),)),
        labels=np.array((7,)),
        confidence=np.array((1.0,)),
        resolution=8,
        triangle_count=157_744,
        class_count=66,
    )

    assert atlas.weights.nbytes < 10 * 2**20
    np.testing.assert_array_equal(atlas.triangle_ids, np.array((157_743,)))
    np.testing.assert_array_equal(atlas.rows_for(np.array((157_743, 5))), np.array((0, -1)))
    assert int(atlas.labels[0].max()) == 7
