from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.materials.vegetation_transport import (
    VegetationPathSegments,
    assess_p833_frequency,
    evaluate_p833_segments,
    plan_vegetation_transport,
    vegetation_evidence_from_atlas,
)


def _atlas() -> SimpleNamespace:
    return SimpleNamespace(
        triangle_count=3,
        triangle_ids=np.asarray([0, 2], dtype=np.int64),
        texel_offsets=np.asarray([0, 2, 3], dtype=np.int64),
        texel_row=np.asarray([0, 0, 1], dtype=np.int16),
        texel_column=np.asarray([0, 1, 0], dtype=np.int16),
        support_weight=np.asarray([2.0, 3.0, 4.0], dtype=np.float32),
        vegetation_form_names=np.asarray(["unresolved", "ground_vegetation", "woody_canopy"]),
        vegetation_subtype_names=np.asarray(["unresolved", "grass", "shrub", "tree", "forest"]),
        vegetation_form_posterior=np.asarray(
            [
                [0.0, 0.75, 0.25],
                [0.0, 0.20, 0.80],
                [0.0, 0.60, 0.40],
            ],
            dtype=np.float32,
        ),
        vegetation_subtype_posterior=np.asarray(
            [
                [0.0, 0.75, 0.10, 0.10, 0.05],
                [0.0, 0.20, 0.20, 0.50, 0.10],
                [0.0, 0.60, 0.10, 0.10, 0.20],
            ],
            dtype=np.float32,
        ),
        mesh_sha256="a" * 64,
    )


def test_atlas_vegetation_keeps_mixtures_and_marks_ground_evidence_off_ground() -> None:
    evidence = vegetation_evidence_from_atlas(_atlas(), np.asarray([0, 1, 1]))

    np.testing.assert_allclose(evidence.ground_probability, [0.75, 0.20, 0.60])
    np.testing.assert_allclose(evidence.woody_probability, [0.25, 0.80, 0.40])
    np.testing.assert_allclose(evidence.ground_probability_off_ground, [0.0, 0.0, 0.60])
    np.testing.assert_allclose(evidence.tree_probability, [0.10, 0.50, 0.10])
    assert evidence.report()["reduction"] == "none; all quantities are posterior mass"


def test_current_plan_changes_no_interface_and_never_blocks_a_canopy() -> None:
    plan = plan_vegetation_transport(_atlas(), np.asarray([0, 1, 1]))

    assert plan.ground_surface_model is None
    assert plan.woody_volume_geometry is None
    assert not plan.support_surface_changed
    assert not plan.support_surface_blocks_woody_evidence
    assert any("ground-cover interface model" in blocker for blocker in plan.blockers)
    assert any("closed canopy volume" in blocker for blocker in plan.blockers)
    document = plan.as_dict()
    assert not document["ground"]["interface_changed"]
    assert not document["woody"]["support_surface_blocks_evidence"]


@pytest.mark.parametrize("frequency_ghz", [3.5, 11.0, 37.0, 61.5])
def test_exact_ret_frequencies_are_labelled_tabulated(frequency_ghz: float) -> None:
    assessment = assess_p833_frequency(frequency_ghz * 1.0e9)

    assert assessment.table_relation == "tabulated"
    assert assessment.ret_parameters_usable
    assert not assessment.interpolation_required
    assert not assessment.extrapolation_required


@pytest.mark.parametrize("frequency_ghz", [7.0, 15.0, 28.0])
def test_fr3_and_fr2_gaps_are_explicit_but_bracketed(frequency_ghz: float) -> None:
    assessment = assess_p833_frequency(frequency_ghz * 1.0e9)

    assert assessment.table_relation == "between_tabulated_frequencies"
    assert assessment.ret_parameters_usable
    assert assessment.interpolation_required
    assert not assessment.extrapolation_required
    assert assessment.lower_tabulated_hz < assessment.frequency_hz < assessment.upper_tabulated_hz


@pytest.mark.parametrize(
    ("frequency_hz", "relation", "in_scope"),
    [
        (700.0e6, "below_ret_tables", True),
        (80.0e9, "above_ret_tables", True),
        (20.0e6, "below_ret_tables", False),
        (110.0e9, "above_ret_tables", False),
    ],
)
def test_ret_extrapolation_and_recommendation_scope_are_separate(
    frequency_hz: float,
    relation: str,
    in_scope: bool,
) -> None:
    assessment = assess_p833_frequency(frequency_hz)

    assert assessment.table_relation == relation
    assert assessment.recommendation_in_scope is in_scope
    assert assessment.extrapolation_required
    assert not assessment.ret_parameters_usable


def _segments() -> VegetationPathSegments:
    return VegetationPathSegments.from_geometry_bytes(
        path_index=np.asarray([0, 1, 1]),
        volume_id=np.asarray(["tree_a", "tree_a", "hedge_b"]),
        entry_point_m=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [5.0, 0.0, 0.0]]),
        exit_point_m=np.asarray([[2.0, 0.0, 0.0], [4.0, 0.0, 0.0], [6.0, 0.0, 0.0]]),
        geometry_source="registered watertight canopy mesh",
        geometry_bytes=b"exact canopy geometry",
        watertight=True,
        intersection_rule="ordered entry and exit intersections on each finite path segment",
    )


def test_p833_segment_budget_conserves_power_and_keeps_species_uncertainty() -> None:
    result = evaluate_p833_segments(_segments(), 28.0e9)

    assert len(result.candidates) > 3
    assert len({candidate.species for candidate in result.candidates}) == len(result.candidates)
    np.testing.assert_allclose(
        result.direct_transmission + result.first_event_scatter + result.first_event_absorption,
        1.0,
    )
    assert np.all(result.direct_transmission[:, 0] < 1.0)
    by_path = result.direct_transmission_by_path()
    np.testing.assert_allclose(by_path[:, 0], result.direct_transmission[:, 0])
    np.testing.assert_allclose(by_path[:, 1], result.direct_transmission[:, 1] * result.direct_transmission[:, 2])
    assert result.frequency.interpolation_required
    assert "do not choose species" in result.provenance["species_policy"]
    assert "first-event energy only" in result.provenance["scatter_term"]


def test_registered_chord_hook_applies_conserving_ensemble_to_path_power() -> None:
    result = evaluate_p833_segments(_segments(), 15.0e9)
    incident = np.asarray([2.0, 3.0])

    budget = result.apply_to_path_power(incident)

    assert budget["direct_power"].shape == (len(result.candidates), 2)
    np.testing.assert_allclose(
        budget["direct_power"] + budget["first_event_scatter_source_power"] + budget["absorbed_power"],
        np.broadcast_to(incident, (len(result.candidates), incident.size)),
        atol=2.0e-12,
    )
    assert np.all(budget["direct_power"] < incident[None, :])


def test_ret_extrapolation_is_refused_unless_the_run_labels_it() -> None:
    with pytest.raises(ValueError, match="outside the 1.3 to 61.5 GHz"):
        evaluate_p833_segments(_segments(), 80.0e9)

    result = evaluate_p833_segments(_segments(), 80.0e9, allow_ret_extrapolation=True)
    assert result.frequency.extrapolation_required
    assert result.provenance["ret_extrapolation_allowed"]


def test_non_watertight_geometry_cannot_supply_canopy_chords() -> None:
    with pytest.raises(ValueError, match="watertight"):
        VegetationPathSegments.from_geometry_bytes(
            path_index=np.asarray([0]),
            volume_id=np.asarray(["tree"]),
            entry_point_m=np.asarray([[0.0, 0.0, 0.0]]),
            exit_point_m=np.asarray([[1.0, 0.0, 0.0]]),
            geometry_source="open photogrammetry fragment",
            geometry_bytes=b"open fragment",
            watertight=False,
            intersection_rule="unpaired hit",
        )
