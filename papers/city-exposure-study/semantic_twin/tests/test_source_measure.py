"""Frozen facade-tip source-measure contracts."""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.illumination import build_facade_tip_curve, build_mesh_edge_curve
from semantic_twin.illumination.curve import (
    HORIZONTAL_PROJECTED_EDGE_LENGTH,
    PHYSICAL_3D_EDGE_LENGTH,
    curve_from_polylines,
)
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.illumination.sources import SourceSet, build_source_set, direct_from_sites, normalized_source_weights


def line(start: float, stop: float, *, count: int = 2) -> np.ndarray:
    return np.column_stack((np.linspace(start, stop, count), np.zeros(count), np.zeros(count)))


def test_arc_length_weights_sum_to_one_for_unequal_segments() -> None:
    curve = curve_from_polylines([line(0.0, 1.0), line(10.0, 13.0)])
    np.testing.assert_allclose(curve.segment_lengths_m, [1.0, 3.0])
    np.testing.assert_allclose(curve.normalized_weights(), [0.25, 0.75])
    assert curve.support_length_m == pytest.approx(4.0)


def test_sloped_segment_retains_exact_endpoints_and_both_length_measures() -> None:
    sloped = np.array([[1.0, 2.0, 3.0], [4.0, 6.0, 15.0]], dtype=np.float64)
    curve = curve_from_polylines([sloped])

    assert curve.has_exact_endpoints
    np.testing.assert_allclose(curve.segment_starts, sloped[:1])
    np.testing.assert_allclose(curve.segment_ends, sloped[1:])
    np.testing.assert_allclose(curve.points, [[2.5, 4.0, 9.0]])
    np.testing.assert_allclose(curve.measure_lengths(PHYSICAL_3D_EDGE_LENGTH), [13.0])
    np.testing.assert_allclose(curve.measure_lengths(HORIZONTAL_PROJECTED_EDGE_LENGTH), [5.0])


def test_projected_measure_changes_weights_but_not_physical_areal_count() -> None:
    curve = curve_from_polylines(
        [
            np.array([[1.0, 0.0, 2.0], [4.0, 0.0, 6.0]], dtype=np.float64),
            np.array([[10.0, 0.0, 2.0], [15.0, 0.0, 2.0]], dtype=np.float64),
        ]
    )
    physical = SourceSet.from_curve(
        curve,
        crop_area_m2=200.0,
        density_per_m2=0.1,
        source_measure_rule=PHYSICAL_3D_EDGE_LENGTH,
    )
    legacy_default = SourceSet.from_curve(curve, crop_area_m2=200.0, density_per_m2=0.1)
    projected = SourceSet.from_curve(
        curve,
        crop_area_m2=200.0,
        density_per_m2=0.1,
        source_measure_rule=HORIZONTAL_PROJECTED_EDGE_LENGTH,
    )

    np.testing.assert_allclose(physical.normalized_source_weights(), [0.5, 0.5])
    np.testing.assert_array_equal(legacy_default.normalized_source_weights(), physical.normalized_source_weights())
    np.testing.assert_allclose(projected.normalized_source_weights(), [0.375, 0.625])
    assert physical.physical_expected_count == projected.physical_expected_count == pytest.approx(20.0)
    assert physical.source_hash == projected.source_hash == curve.source_hash
    assert "source_measure_rule" not in legacy_default.source_provenance()
    assert physical.source_provenance()["source_measure_rule"] == PHYSICAL_3D_EDGE_LENGTH
    assert projected.source_provenance()["source_measure_rule"] == HORIZONTAL_PROJECTED_EDGE_LENGTH


def test_projected_measure_allows_zero_segments_but_refuses_zero_total() -> None:
    mixed = curve_from_polylines(
        [
            np.array([[1.0, 0.0, 1.0], [1.0, 0.0, 3.0]], dtype=np.float64),
            np.array([[2.0, 0.0, 1.0], [4.0, 0.0, 1.0]], dtype=np.float64),
        ]
    )
    np.testing.assert_allclose(mixed.normalized_weights(HORIZONTAL_PROJECTED_EDGE_LENGTH), [0.0, 1.0])

    vertical = curve_from_polylines([np.array([[1.0, 0.0, 1.0], [1.0, 0.0, 3.0]], dtype=np.float64)])
    with pytest.raises(ValueError, match="no positive support"):
        vertical.normalized_weights(HORIZONTAL_PROJECTED_EDGE_LENGTH)


def test_duplicate_views_are_unioned_without_double_counting() -> None:
    curve = curve_from_polylines([line(0.0, 2.0), line(2.0, 0.0)])
    reordered = curve_from_polylines([line(2.0, 0.0), line(0.0, 2.0)])
    assert 0.0 < curve.support_length_m <= 2.0
    assert curve.points.shape == (1, 3)
    assert curve.normalized_weights().sum() == pytest.approx(1.0)
    assert reordered.source_hash == curve.source_hash


def test_refining_a_segment_preserves_support_and_measure() -> None:
    coarse = curve_from_polylines([line(0.0, 4.0)])
    refined = curve_from_polylines([line(0.0, 4.0, count=9)])
    assert refined.support_length_m == pytest.approx(coarse.support_length_m)
    np.testing.assert_allclose(refined.normalized_weights().sum(), coarse.normalized_weights().sum())


def test_source_set_keeps_physical_count_separate_from_relative_weights() -> None:
    curve = curve_from_polylines([line(0.0, 2.0), line(4.0, 6.0)])
    sources = SourceSet(
        positions=curve.points,
        cell_m=1.0,
        dims=3,
        azimuths=16,
        builders=2,
        curve=curve,
        crop_area_m2=100.0,
        density_per_m2=0.2,
        eirp_w=10.0,
    )
    np.testing.assert_allclose(sources.normalized_probabilities, [0.5, 0.5])
    assert sources.physical_expected_count == pytest.approx(20.0)
    per_density = sources.per_density_eirp_transfer(2.0)
    assert per_density == pytest.approx(200.0 / (4.0 * np.pi))
    physical = sources.physical_transfer(2.0)
    assert physical == pytest.approx(20.0 * 10.0 * 2.0 / (4.0 * np.pi))
    assert physical == pytest.approx(per_density * 0.2 * 10.0)
    assert sources.source_provenance()["support_length_m"] == pytest.approx(4.0)


def test_direct_transfer_uses_arc_length_probabilities_not_point_count() -> None:
    class OpenSky:
        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            del directions
            count = np.asarray(origins).shape[0]
            return np.zeros(count, dtype=bool), np.full(count, 1.0e30), np.zeros((count, 3)), np.zeros(count)

    curve = curve_from_polylines([line(1.0, 2.0), line(10.0, 13.0)])
    sources = SourceSet.from_curve(curve)
    direct, seen = direct_from_sites(
        OpenSky(), np.array([[0.0, 0.0, 0.0]]), sources.positions, weights=sources.source_weights
    )
    expected = 0.25 / 1.5**2 + 0.75 / 11.5**2
    assert direct[0] == pytest.approx(expected)
    assert seen[0] == pytest.approx(1.0)


def test_physical_scale_refuses_missing_crop_area() -> None:
    curve = curve_from_polylines([line(0.0, 2.0)])
    sources = SourceSet(curve.points, 1.0, 3, 16, 2, curve=curve)
    with pytest.raises(ValueError, match="crop_area_m2"):
        sources.per_density_eirp_transfer(1.0)
    legacy = SourceSet(np.array([[0.0, 0.0, 1.0]]), 1.0, 3, 0, 0, crop_area_m2=1.0)
    with pytest.raises(ValueError, match="curve data"):
        legacy.per_density_eirp_transfer(1.0)


def test_builder_silhouette_is_deterministic_and_duplicate_views_are_merged() -> None:
    class Geometry:
        pass

    def synthetic_silhouette(_geometry: Geometry, origin: np.ndarray, *, azimuths: int, elevations: int):
        del origin, elevations
        alpha = np.full(azimuths, np.pi / 6.0)
        horizontal = np.full(azimuths, 10.0)
        return alpha, horizontal, np.ones(azimuths, dtype=bool)

    first = build_facade_tip_curve(
        Geometry(),
        np.array([[0.0, 0.0, 0.0]]),
        synthetic_silhouette,
        azimuths=32,
        elevations=4,
    )
    repeated = build_facade_tip_curve(
        Geometry(),
        np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        synthetic_silhouette,
        azimuths=32,
        elevations=4,
    )
    assert repeated.support_length_m == pytest.approx(first.support_length_m)
    assert repeated.source_hash == first.source_hash


def test_silhouette_no_hit_gap_does_not_create_a_chord() -> None:
    class Geometry:
        pass

    def discontinuous(_geometry: Geometry, origin: np.ndarray, *, azimuths: int, elevations: int):
        del origin, elevations
        alpha = np.full(azimuths, np.pi / 6.0)
        horizontal = np.full(azimuths, 10.0)
        found = np.ones(azimuths, dtype=bool)
        found[azimuths // 2 :] = False
        return alpha, horizontal, found

    curve = build_facade_tip_curve(Geometry(), np.zeros((1, 3)), discontinuous, azimuths=4, elevations=4)
    assert curve.points.shape[0] == 1

    def wrapped(_geometry: Geometry, origin: np.ndarray, *, azimuths: int, elevations: int):
        alpha, horizontal, found = discontinuous(_geometry, origin, azimuths=azimuths, elevations=elevations)
        del origin
        found[:] = True
        found[1] = False
        return alpha, horizontal, found

    wrapped_curve = build_facade_tip_curve(Geometry(), np.zeros((1, 3)), wrapped, azimuths=4, elevations=4)
    assert wrapped_curve.points.shape[0] == 2


def test_mesh_edges_union_exact_vertex_ids_and_use_geometric_lengths() -> None:
    class Mesh:
        vertices = np.array(
            [[0.0, -1.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 3.0], [0.0, 1.0, 3.0]],
            dtype=np.float64,
        )
        faces = np.array([[0, 2, 3], [0, 3, 1]], dtype=np.int64)

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            count = origins.shape[0]
            direction = np.asarray(directions, dtype=np.float64)
            denominator = direction[:, 0]
            distance = np.divide(-origins[:, 0], denominator, out=np.full(count, np.inf), where=denominator < 0.0)
            points = origins + distance[:, None] * direction
            hit = (
                (denominator < 0.0)
                & np.isfinite(distance)
                & (points[:, 1] >= -1.0)
                & (points[:, 1] <= 1.0)
                & (points[:, 2] >= 0.0)
                & (points[:, 2] <= 3.1)
            )
            return (
                hit,
                distance,
                points,
                np.zeros(count, dtype=np.int64),
            )

    def top_face(_geometry: Mesh, origin: np.ndarray, *, azimuths: int, elevations: int):
        del origin, elevations
        found = np.zeros(azimuths, dtype=bool)
        found[[azimuths // 2 - 1, azimuths // 2]] = True
        return (
            np.full(azimuths, np.arctan2(1.5, 10.0)),
            np.full(azimuths, 10.0),
            found,
        )

    curve = build_mesh_edge_curve(
        Mesh(), np.array([[10.0, 0.0, 1.5], [10.1, 0.0, 1.5]]), top_face, azimuths=32, elevations=4
    )
    assert 0.0 < curve.support_length_m <= 2.0
    assert curve.provenance["edge_ids_sha256"]
    assert curve.provenance["merge_rule"] == "undirected_mesh_vertex_edge_id_union"
    routed = build_facade_tip_curve(
        Mesh(),
        np.array([[10.0, 0.0, 1.5]]),
        top_face,
        azimuths=32,
        elevations=4,
        top_edge_tolerance_m=1.5,
    )
    assert routed.provenance["deprecated_top_edge_tolerance_m"] == pytest.approx(1.5)


class _TriangularFacade:
    """Small deterministic mesh double for route-edge selection tests."""

    vertices = np.array(
        [
            [-2.0, 5.0, 0.0],
            [2.0, 5.0, 0.0],
            [2.0, 5.0, 4.0],
            [-2.0, 5.0, 4.0],
        ],
        dtype=np.float64,
    )
    # The diagonal (0, 2) is a coplanar tessellation seam.  The upper boundary
    # is (2, 3), while (0, 1), (1, 2), and (3, 0) are the floor and side edges.
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        direction = np.asarray(directions, dtype=np.float64)
        count = origins.shape[0]
        denominator = direction[:, 1]
        plane_y = float(np.mean(self.vertices[:, 1]))
        distance = np.divide(plane_y - origins[:, 1], denominator, out=np.full(count, np.inf), where=denominator > 0.0)
        points = origins + distance[:, None] * direction
        hit = (
            (denominator > 0.0)
            & np.isfinite(distance)
            & (points[:, 0] >= float(np.min(self.vertices[:, 0])))
            & (points[:, 0] <= float(np.max(self.vertices[:, 0])))
            & (points[:, 2] >= float(np.min(self.vertices[:, 2])))
            & (points[:, 2] <= float(np.max(self.vertices[:, 2]) + 0.1))
        )
        # The test silhouette supplies rays whose point at range 5 is the centre
        # of the second triangle.  Returning that exact face makes the selector
        # choose from real mesh edges rather than an invented fan chord.
        return (
            hit,
            distance,
            points,
            np.full(count, 1, dtype=np.int64),
        )


def _one_north_ray(_geometry: _TriangularFacade, _origin: np.ndarray, *, azimuths: int, elevations: int):
    del elevations
    alpha = np.zeros(azimuths, dtype=np.float64)
    horizontal = np.full(azimuths, 5.0, dtype=np.float64)
    found = np.zeros(azimuths, dtype=bool)
    # For azimuths=2, the first bin points along +y, onto the facade.
    found[0] = True
    return alpha, horizontal, found


def _interval_north_ray(_geometry: _TriangularFacade, _origin: np.ndarray, *, azimuths: int, elevations: int):
    """Two adjacent skyline contacts that delimit a nonzero edge interval."""
    del elevations
    alpha = np.full(azimuths, np.arctan2(2.0, 5.0))
    horizontal = np.full(azimuths, 5.0)
    found = np.zeros(azimuths, dtype=bool)
    left = max(0, azimuths // 4 - 1)
    right = min(azimuths - 1, azimuths // 4)
    found[left] = True
    found[right] = True
    return alpha, horizontal, found


def _interval_low_edge_ray(_geometry: object, _origin: np.ndarray, *, azimuths: int, elevations: int):
    """Two contacts for the top-edge tolerance invariance fixture."""
    del elevations
    alpha = np.full(azimuths, np.arctan2(1.0, 5.0))
    horizontal = np.full(azimuths, 5.0)
    found = np.zeros(azimuths, dtype=bool)
    left = max(0, azimuths // 4 - 1)
    right = min(azimuths - 1, azimuths // 4)
    found[left] = True
    found[right] = True
    return alpha, horizontal, found


def _interval_split_ray(_geometry: object, _origin: np.ndarray, *, azimuths: int, elevations: int):
    """Two contacts reaching the upper contour of the split-facade fixture."""
    del elevations
    alpha = np.full(azimuths, np.arctan2(3.0, 5.0))
    horizontal = np.full(azimuths, 5.0)
    found = np.zeros(azimuths, dtype=bool)
    left = max(0, azimuths // 4 - 1)
    right = min(azimuths - 1, azimuths // 4)
    found[left] = True
    found[right] = True
    return alpha, horizontal, found


def test_mesh_selector_keeps_top_envelope_and_excludes_coplanar_seam_and_sides() -> None:
    curve = build_mesh_edge_curve(
        _TriangularFacade(),
        np.array([[0.0, 0.0, 2.0], [0.0, 0.0, 2.0]]),
        _interval_north_ray,
        azimuths=16,
        elevations=4,
    )
    # The two route standpoints observe the same edge IDs.  It is counted once,
    # with its geometric length, and the diagonal/vertical edges never enter the
    # line measure.
    assert curve.support_length_m > 0.0
    assert curve.provenance["edge_count"] == 1
    # Visible-face provenance is a unique mesh-face count, just like the exact
    # edge support is deduplicated by vertex IDs across repeated standpoints.
    assert curve.provenance["builder_visible_faces"] == 1


def test_mesh_edge_curve_is_stable_under_fan_refinement_and_translation() -> None:
    coarse = build_mesh_edge_curve(
        _TriangularFacade(),
        np.array([[0.0, 0.0, 2.0]]),
        _interval_north_ray,
        azimuths=16,
        elevations=2,
    )

    refined = build_mesh_edge_curve(
        _TriangularFacade(),
        np.array([[0.0, 0.0, 2.0]]),
        _interval_north_ray,
        azimuths=32,
        elevations=16,
    )
    assert refined.support_length_m > 0.0
    assert refined.provenance["edge_ids_sha256"] == coarse.provenance["edge_ids_sha256"]

    translated = _TriangularFacade()
    translated.vertices = _TriangularFacade.vertices + np.array([11.0, -7.0, 3.0])
    shifted = build_mesh_edge_curve(
        translated,
        np.array([[11.0, -7.0, 5.0]]),
        _interval_north_ray,
        azimuths=16,
        elevations=2,
    )
    assert shifted.support_length_m == pytest.approx(coarse.support_length_m)
    assert shifted.provenance["edge_ids_sha256"] == coarse.provenance["edge_ids_sha256"]


def test_build_facade_tip_curve_forwards_top_edge_tolerance_to_mesh_selector() -> None:
    class SlopedTriangle:
        vertices = np.array(
            [[-2.0, 5.0, 0.0], [0.0, 5.0, 4.0], [2.0, 5.0, 3.0]],
            dtype=np.float64,
        )
        faces = np.array([[0, 1, 2]], dtype=np.int64)

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            direction = np.asarray(directions, dtype=np.float64)
            count = origins.shape[0]
            denominator = direction[:, 1]
            distance = np.divide(5.0 - origins[:, 1], denominator, out=np.full(count, np.inf), where=denominator > 0.0)
            points = origins + distance[:, None] * direction
            hit = (
                (denominator > 0.0)
                & np.isfinite(distance)
                & (points[:, 0] >= -2.0)
                & (points[:, 0] <= 2.0)
                & (points[:, 2] >= 0.0)
                & (points[:, 2] <= 4.1)
            )
            return (
                hit,
                distance,
                points,
                np.zeros(count, dtype=np.int64),
            )

    # Two contacts delimit a nonzero contour interval.  The old tolerance is
    # deprecated metadata and must not select a different edge.
    strict = build_facade_tip_curve(
        SlopedTriangle(),
        np.array([[-1.0, 0.0, 1.0]]),
        _interval_low_edge_ray,
        azimuths=16,
        elevations=4,
        top_edge_tolerance_m=0.0,
    )
    loose = build_facade_tip_curve(
        SlopedTriangle(),
        np.array([[-1.0, 0.0, 1.0]]),
        _interval_low_edge_ray,
        azimuths=16,
        elevations=4,
        top_edge_tolerance_m=10.0,
    )
    np.testing.assert_allclose(strict.points, loose.points)
    assert strict.provenance["deprecated_top_edge_tolerance_m"] == pytest.approx(0.0)
    assert loose.provenance["deprecated_top_edge_tolerance_m"] == pytest.approx(10.0)


def test_build_source_set_lifts_exact_edges_without_changing_arc_measure() -> None:
    unlifted = build_source_set(
        _TriangularFacade(),
        np.array([[0.0, 0.0, 2.0]]),
        _interval_north_ray,
        azimuths=16,
        elevations=4,
        site_lift_m=0.0,
        crop_area_m2=40.0,
    )
    sources = build_source_set(
        _TriangularFacade(),
        np.array([[0.0, 0.0, 2.0]]),
        _interval_north_ray,
        azimuths=16,
        elevations=4,
        site_lift_m=0.5,
        crop_area_m2=40.0,
        density_per_m2=0.25,
        eirp_w=2.0,
    )
    assert sources.support_length_m > 0.0
    assert sources.physical_expected_count == pytest.approx(10.0)
    assert sources.positions[0, 2] == pytest.approx(4.5)
    assert sources.curve is not None and unlifted.curve is not None
    np.testing.assert_allclose(sources.curve.segment_starts[:, 2], unlifted.curve.segment_starts[:, 2] + 0.5)
    np.testing.assert_allclose(sources.curve.segment_ends[:, 2], unlifted.curve.segment_ends[:, 2] + 0.5)
    np.testing.assert_array_equal(sources.curve.segment_lengths_m, unlifted.curve.segment_lengths_m)
    np.testing.assert_allclose(
        sources.curve.measure_lengths(HORIZONTAL_PROJECTED_EDGE_LENGTH),
        unlifted.curve.measure_lengths(HORIZONTAL_PROJECTED_EDGE_LENGTH),
    )
    np.testing.assert_allclose(sources.normalized_source_weights(), [1.0])
    assert sources.source_provenance()["merge_rule"] == "undirected_mesh_vertex_edge_id_union"


def test_source_set_rejects_inconsistent_physical_metadata_and_curve_weights() -> None:
    curve = curve_from_polylines([line(0.0, 2.0), line(4.0, 8.0)])
    with pytest.raises(ValueError, match="expected_count"):
        SourceSet.from_curve(
            curve,
            crop_area_m2=10.0,
            density_per_m2=0.2,
            expected_count=3.0,
        )
    with pytest.raises(ValueError, match="crop_area_m2"):
        SourceSet.from_curve(curve, crop_area_m2=-1.0)
    with pytest.raises(ValueError, match="curve points"):
        SourceSet(
            positions=curve.points + np.array([0.0, 0.0, 1.0]),
            cell_m=1.0,
            dims=1,
            azimuths=0,
            builders=0,
            curve=curve,
        )
    with pytest.raises(ValueError, match="segment lengths"):
        SourceSet(
            positions=curve.points,
            cell_m=1.0,
            dims=1,
            azimuths=0,
            builders=0,
            curve=curve,
            source_weights=np.array([0.5, 0.5]),
        )


def test_legacy_source_objects_keep_equal_weight_compatibility() -> None:
    class LegacySources:
        def sites(self) -> np.ndarray:
            return np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 2.0]])

    np.testing.assert_allclose(normalized_source_weights(LegacySources()), [0.5, 0.5])


def test_mesh_selector_refuses_cluttered_or_empty_support() -> None:
    with pytest.raises(ValueError, match="no mesh facade-tip edges"):
        build_mesh_edge_curve(
            _TriangularFacade(),
            np.array([[0.0, 0.0, 2.0]]),
            _one_north_ray,
            azimuths=2,
            elevations=4,
            clutter_triangles=np.array([False, True]),
        )

    class NoHit:
        vertices = _TriangularFacade.vertices
        faces = _TriangularFacade.faces

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            count = origins.shape[0]
            return (
                np.zeros(count, dtype=bool),
                np.full(count, np.inf),
                np.zeros((count, 3)),
                np.full(count, -1, dtype=np.int64),
            )

    with pytest.raises(ValueError, match="no mesh facade-tip edges"):
        build_mesh_edge_curve(
            NoHit(),
            np.array([[0.0, 0.0, 2.0]]),
            _one_north_ray,
            azimuths=2,
            elevations=4,
        )


def test_mesh_selector_refuses_singleton_contact_without_interval_evidence() -> None:
    with pytest.raises(ValueError, match="unmatched mesh-edge intervals"):
        build_mesh_edge_curve(
            _TriangularFacade(),
            np.array([[0.0, 0.0, 2.0]]),
            _one_north_ray,
            azimuths=2,
            elevations=4,
        )


def test_mesh_selector_does_not_bridge_contacts_from_different_views() -> None:
    def one_contact_per_view(
        _geometry: _TriangularFacade,
        origin: np.ndarray,
        *,
        azimuths: int,
        elevations: int,
    ):
        del elevations
        alpha = np.full(azimuths, np.arctan2(2.0, 5.0))
        horizontal = np.full(azimuths, 5.0)
        found = np.zeros(azimuths, dtype=bool)
        center = azimuths // 4
        found[center - 1 if origin[0] < 0.5 else center] = True
        return alpha, horizontal, found

    with pytest.raises(ValueError, match="unmatched mesh-edge intervals"):
        build_mesh_edge_curve(
            _TriangularFacade(),
            np.array([[0.0, 0.0, 2.0], [1.0, 0.0, 2.0]]),
            one_contact_per_view,
            azimuths=32,
            elevations=4,
        )


def test_mesh_selector_does_not_bridge_nonadjacent_same_view_contacts() -> None:
    def nonadjacent_contacts(
        _geometry: _TriangularFacade,
        _origin: np.ndarray,
        *,
        azimuths: int,
        elevations: int,
    ):
        del elevations
        alpha = np.full(azimuths, np.arctan2(2.0, 5.0))
        horizontal = np.full(azimuths, 5.0)
        found = np.zeros(azimuths, dtype=bool)
        center = azimuths // 4
        found[[center - 1, center + 1]] = True
        return alpha, horizontal, found

    with pytest.raises(ValueError, match="unmatched mesh-edge intervals"):
        build_mesh_edge_curve(
            _TriangularFacade(),
            np.array([[0.0, 0.0, 2.0]]),
            nonadjacent_contacts,
            azimuths=32,
            elevations=4,
        )


def test_mesh_selector_batches_refinement_and_midpoint_intersections() -> None:
    class CountingFacade(_TriangularFacade):
        def __init__(self) -> None:
            self.intersect_calls = 0
            self.batch_sizes: list[int] = []

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            self.intersect_calls += 1
            self.batch_sizes.append(int(np.asarray(origins).shape[0]))
            return super().intersect(origins, directions)

    def dense_contacts(
        _geometry: _TriangularFacade,
        _origin: np.ndarray,
        *,
        azimuths: int,
        elevations: int,
    ):
        del elevations
        alpha = np.full(azimuths, np.arctan2(2.0, 5.0))
        horizontal = np.full(azimuths, 5.0)
        found = np.zeros(azimuths, dtype=bool)
        center = azimuths // 4
        found[center - 3 : center + 3] = True
        return alpha, horizontal, found

    geometry = CountingFacade()
    curve = build_mesh_edge_curve(
        geometry,
        np.array([[0.0, 0.0, 2.0]]),
        dense_contacts,
        azimuths=64,
        elevations=4,
    )
    accepted = curve.provenance["accepted_contact_count"]
    assert accepted >= 6
    assert geometry.intersect_calls <= 32
    assert geometry.intersect_calls < accepted * 6
    assert max(geometry.batch_sizes) >= accepted


def test_mesh_selector_does_not_invent_lower_edge_when_recast_hits_adjacent_face() -> None:
    class SplitFacade:
        vertices = np.array(
            [
                [-2.0, 5.0, 0.0],
                [2.0, 5.0, 0.0],
                [2.0, 5.0, 2.0],
                [-2.0, 5.0, 2.0],
                [2.0, 5.0, 4.0],
                [-2.0, 5.0, 4.0],
            ],
            dtype=np.float64,
        )
        # Four coplanar triangles form one rectangle.  Face zero is the lower
        # triangle.  The real skyline is the edge (4, 5), two faces away.
        faces = np.array([[0, 1, 2], [0, 2, 3], [3, 2, 4], [3, 4, 5]], dtype=np.int64)

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            direction = np.asarray(directions, dtype=np.float64)
            count = origins.shape[0]
            denominator = direction[:, 1]
            distance = np.divide(5.0 - origins[:, 1], denominator, out=np.full(count, np.inf), where=denominator > 0.0)
            points = origins + distance[:, None] * direction
            hit = (
                (denominator > 0.0)
                & np.isfinite(distance)
                & (points[:, 0] >= -2.0)
                & (points[:, 0] <= 2.0)
                & (points[:, 2] >= 0.0)
                & (points[:, 2] <= 4.1)
            )
            return (
                hit,
                distance,
                points,
                np.zeros(count, dtype=np.int64),
            )

    curve = build_mesh_edge_curve(
        SplitFacade(),
        np.array([[0.0, 0.0, 1.0]]),
        _interval_split_ray,
        azimuths=16,
        elevations=4,
    )
    # A lower-face fallback is scientifically wrong.  The selector should
    # either walk the coplanar surface to (4, 5), or refuse this inconsistent
    # recast rather than silently returning the floor/side support.
    assert curve.points[0, 2] == pytest.approx(4.0)


def test_mesh_selector_refuses_a_hit_far_from_any_candidate_edge() -> None:
    class LargeTriangle:
        vertices = np.array(
            [[-20.0, 5.0, 0.0], [20.0, 5.0, 0.0], [0.0, 5.0, 40.0]],
            dtype=np.float64,
        )
        faces = np.array([[0, 1, 2]], dtype=np.int64)

        def intersect(self, origins: np.ndarray, directions: np.ndarray):
            del directions
            count = origins.shape[0]
            return (
                np.ones(count, dtype=bool),
                np.full(count, 5.0),
                np.zeros((count, 3), dtype=np.float64),
                np.zeros(count, dtype=np.int64),
            )

    with pytest.raises(ValueError, match="no mesh facade-tip edges"):
        build_mesh_edge_curve(
            LargeTriangle(),
            np.array([[0.0, 0.0, 20.0]]),
            _one_north_ray,
            azimuths=2,
            elevations=4,
        )


class _IntervalOccluder(_TriangularFacade):
    """Stateful intersector for midpoint first-hit and sky-above gates."""

    def __init__(self, mode: str):
        self.mode = mode
        self.calls = 0

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        self.calls += 1
        count = origins.shape[0]
        # The batched refinement uses one call for all contact elevations.
        # The interval midpoint is the next scalar call, followed by the
        # sky-above probe.
        if count == 1 and (
            (self.mode == "midpoint_block" and self.calls >= 3) or (self.mode == "sky_block" and self.calls >= 4)
        ):
            return (
                np.ones(count, dtype=bool),
                np.full(count, 4.0 if self.mode == "midpoint_block" else 5.0),
                np.zeros((count, 3), dtype=np.float64),
                np.full(count, 1, dtype=np.int64),
            )
        return super().intersect(origins, directions)


def test_mesh_selector_rejects_interval_midpoint_with_a_closer_first_hit() -> None:
    with pytest.raises(ValueError, match="unmatched mesh-edge intervals"):
        build_mesh_edge_curve(
            _IntervalOccluder("midpoint_block"),
            np.array([[0.0, 0.0, 2.0]]),
            _interval_north_ray,
            azimuths=16,
            elevations=1,
        )


def test_mesh_selector_rejects_interval_without_clear_sky_above() -> None:
    with pytest.raises(ValueError, match="unmatched mesh-edge intervals"):
        build_mesh_edge_curve(
            _IntervalOccluder("sky_block"),
            np.array([[0.0, 0.0, 2.0]]),
            _interval_north_ray,
            azimuths=16,
            elevations=1,
        )


class _FiniteRectangularFacade:
    """Finite two-triangle wall whose skyline is its analytic top edge."""

    def __init__(self, *, width_m: float = 10.0, depth_m: float = 30.0, height_m: float = 12.0) -> None:
        half_width = width_m / 2.0
        self.vertices = np.array(
            [
                [-half_width, depth_m, 0.0],
                [half_width, depth_m, 0.0],
                [half_width, depth_m, height_m],
                [-half_width, depth_m, height_m],
            ],
            dtype=np.float64,
        )
        self.faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        origins = np.asarray(origins, dtype=np.float64)
        directions = np.asarray(directions, dtype=np.float64)
        depth_m = float(self.vertices[0, 1])
        denominator = directions[:, 1]
        distance = np.divide(
            depth_m - origins[:, 1],
            denominator,
            out=np.full(origins.shape[0], np.inf, dtype=np.float64),
            where=denominator > 0.0,
        )
        points = origins + distance[:, None] * directions
        half_width = float(np.max(np.abs(self.vertices[:, 0])))
        height_m = float(np.max(self.vertices[:, 2]))
        hit = (
            (denominator > 0.0)
            & np.isfinite(distance)
            & (points[:, 0] >= -half_width)
            & (points[:, 0] <= half_width)
            & (points[:, 2] >= -1.0e-9)
            & (points[:, 2] <= height_m + 1.0e-9)
        )
        # The diagonal is only a tessellation seam.  Return the actual face
        # containing each point so the selector must traverse that seam to
        # recover the shared upper contour edge (2, 3).
        diagonal_height = (points[:, 0] + half_width) * height_m / (2.0 * half_width)
        face = np.where(points[:, 2] <= diagonal_height + 1.0e-10, 0, 1).astype(np.int64)
        return hit, distance, points, face


def test_finite_facade_fan_converges_to_analytic_top_edge() -> None:
    """A real silhouette fan converges to the full finite top edge.

    The fan contacts only the top edge of this finite wall.  Increasing the
    azimuth count should therefore recover more of the known ten-metre edge,
    without changing the selected geometric edge union or manufacturing a
    second contour segment.
    """
    geometry = _FiniteRectangularFacade(width_m=10.0)
    origin = np.array([[0.0, 0.0, 2.0]], dtype=np.float64)
    curves = [
        build_mesh_edge_curve(geometry, origin, silhouette, azimuths=azimuths, elevations=160)
        for azimuths in (360, 720, 1440)
    ]
    lengths = np.asarray([curve.support_length_m for curve in curves])
    analytic_length = 10.0
    assert np.all(lengths > 0.8 * analytic_length)
    assert lengths[0] < lengths[1] < lengths[2] < analytic_length
    assert analytic_length - lengths[0] < 1.1
    assert analytic_length - lengths[1] < 0.3
    assert analytic_length - lengths[2] < 0.15
    assert all(curve.provenance["interval_count"] == 1 for curve in curves)
    edge_hashes = {curve.provenance["edge_ids_sha256"] for curve in curves}
    assert len(edge_hashes) == 1
