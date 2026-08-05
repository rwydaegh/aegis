"""Checks over the plain summary extracted from a Blender build artefact."""

from __future__ import annotations

from semantic_twin.viz.blender.audit import check_finite, check_hair_curves, check_inside


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
