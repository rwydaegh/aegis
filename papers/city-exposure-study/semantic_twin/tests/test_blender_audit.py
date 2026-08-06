"""Checks over the plain summary extracted from a Blender build artefact."""

from __future__ import annotations

from semantic_twin.viz.blender.audit import (
    check_finite,
    check_hair_curves,
    check_inside,
    select_inside_support,
)


def curves(**overrides: object) -> dict:
    record = {
        "kind": "curves",
        "control_positions_finite": True,
        "radii_finite": True,
        "evaluated_bounds_finite": True,
        "curve_types": [1],
        "min": [0.0, 0.0, 0.0],
        "max": [8.0, 0.0, 4.0],
        "max_radius": 0.1,
        "evaluated_min": [-0.1, -0.1, -0.1],
        "evaluated_max": [8.1, 0.1, 4.1],
    }
    record.update(overrides)
    return record


def test_poly_hair_curves_with_radius_bounded_evaluation_are_clean() -> None:
    summary = {"objects": {"rays": curves()}}

    assert check_finite(summary) == []
    assert check_hair_curves(summary) == []


def test_hair_curve_finite_checks_name_each_broken_value() -> None:
    summary = {
        "objects": {
            "rays": curves(
                control_positions_finite=False,
                radii_finite=False,
                evaluated_bounds_finite=False,
            )
        }
    }

    assert check_finite(summary) == [
        "non finite curve control positions: rays",
        "non finite curve radii: rays",
        "non finite evaluated curve bounds: rays",
    ]


def test_hair_curve_check_rejects_smoothing_and_evaluated_overshoot() -> None:
    summary = {
        "objects": {
            "rays": curves(
                curve_types=[0],
                evaluated_min=[-2.0, -0.1, -0.1],
                evaluated_max=[8.1, 0.1, 5.0],
            )
        }
    }

    assert check_hair_curves(summary) == [
        "non-POLY Hair Curves: rays has curve types [0]",
        "evaluated Hair Curves overshoot: rays reaches 1.899 m beyond its controls and radius",
    ]


def test_inside_check_excludes_only_semi_infinite_display_proxy_points() -> None:
    summary = {
        "objects": {
            "city": {"min": [-100.0, -100.0, 0.0], "max": [100.0, 100.0, 50.0]},
            "escaped_ray": curves(
                min=[0.0, 0.0, 1.0],
                max=[200.0, 0.0, 10.0],
                support_min=None,
                support_max=None,
            ),
            "physical_ray": curves(
                min=[0.0, 0.0, 1.0],
                max=[160.0, 0.0, 10.0],
                support_min=[0.0, 0.0, 1.0],
                support_max=[160.0, 0.0, 10.0],
            ),
        }
    }

    assert check_inside(summary, "city") == [
        "outside the drawn mesh: physical_ray reaches 160 m, 1.6 times the drawn mesh's 100 m"
    ]


def test_inside_check_uses_full_outer_support_extent_when_displayed() -> None:
    summary = {
        "collections": {
            "01 city mesh": ["support_mesh"],
            "01B outer traced support": ["support_mesh_outer"],
        },
        "objects": {
            "support_mesh": {"min": [-110.0, -110.0, 0.0], "max": [110.0, 110.0, 50.0]},
            "support_mesh_outer": {"min": [-250.0, -250.0, 0.0], "max": [250.0, 250.0, 50.0]},
            "full_atlas": {"min": [-245.0, -245.0, 0.0], "max": [245.0, 245.0, 50.0]},
        },
    }

    support = select_inside_support(summary, "support_mesh")

    assert support == "support_mesh_outer"
    assert check_inside(summary, support) == []


def test_inside_check_keeps_legacy_inner_support_without_displayed_outer_mesh() -> None:
    summary = {
        "collections": {
            "01 city mesh": ["support_mesh"],
            "01B outer traced support": ["support_mesh_outer"],
        },
        "objects": {
            "support_mesh": {"min": [-100.0, -100.0, 0.0], "max": [100.0, 100.0, 50.0]},
            "support_mesh_outer": {
                "hidden": True,
                "min": [-250.0, -250.0, 0.0],
                "max": [250.0, 250.0, 50.0],
            },
            "evidence": {"min": [-160.0, 0.0, 0.0], "max": [160.0, 0.0, 10.0]},
        },
    }

    support = select_inside_support(summary, "support_mesh")

    assert support == "support_mesh"
    assert check_inside(summary, support) == [
        "outside the drawn mesh: evidence reaches 160 m, 1.6 times the drawn mesh's 100 m"
    ]
