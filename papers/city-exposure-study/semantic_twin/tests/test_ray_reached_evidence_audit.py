from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.exposure.ray_reached_evidence_audit import (
    CATEGORY_NAMES,
    AuditReplayPlan,
    AuditReplaySource,
    RayReachedEvidenceAuditError,
    _record_arrays,
    _SeedCapture,
    _parse_diffuse_audit,
    _parse_specular_audit,
    _validate_category_closure,
    _validate_split_body_closure,
)


def _diffuse_detail() -> dict[str, object]:
    field = np.zeros((len(CATEGORY_NAMES), 2), dtype=np.float64)
    field[0] = (0.25, 0.125)
    field[2] = (0.0, 0.375)
    return {
        "first_diffuse_audit": {
            "category_names": CATEGORY_NAMES,
            "accepted_event_count": [3, 0, 2, 0, 0, 0, 0],
            "contribution_transfer": field.sum(axis=1).tolist(),
            "local_cell_mass": field.tolist(),
        }
    }


def _specular_detail() -> dict[str, object]:
    return {
        "order_one_specular_audit": {
            "category_names": CATEGORY_NAMES,
            "accepted_event_count": [2, 0, 1, 0, 0, 0, 0],
            "contribution_transfer": [0.3, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0],
            "atom_category": [0, 2, 0],
        }
    }


def test_category_counts_contributions_and_field_close_exactly() -> None:
    diffuse = _parse_diffuse_audit(_diffuse_detail(), 2)
    specular = _parse_specular_audit(_specular_detail(), 3)
    field = SimpleNamespace(
        bounced_mass=np.array([0.25, 0.5], dtype=np.float64),
        all_specular_mass=0.6,
        all_specular_atom_mass=np.array([0.1, 0.3, 0.2], dtype=np.float64),
    )

    _validate_category_closure(diffuse, specular, field)


def test_empty_specular_atom_category_is_a_valid_integer_partition() -> None:
    detail = {
        "order_one_specular_audit": {
            "category_names": CATEGORY_NAMES,
            "accepted_event_count": [0] * len(CATEGORY_NAMES),
            "contribution_transfer": [0.0] * len(CATEGORY_NAMES),
            "atom_category": [],
        }
    }

    specular = _parse_specular_audit(detail, 0)

    assert specular.atom_category.dtype == np.int64
    assert specular.atom_category.shape == (0,)


def test_category_closure_rejects_contribution_drift() -> None:
    detail = _diffuse_detail()
    detail["first_diffuse_audit"]["contribution_transfer"][0] += 0.01  # type: ignore[index]
    diffuse = _parse_diffuse_audit(detail, 2)
    specular = _parse_specular_audit(_specular_detail(), 3)
    field = SimpleNamespace(
        bounced_mass=np.array([0.25, 0.5], dtype=np.float64),
        all_specular_mass=0.6,
        all_specular_atom_mass=np.array([0.1, 0.3, 0.2], dtype=np.float64),
    )

    with pytest.raises(RayReachedEvidenceAuditError, match="contributions do not close"):
        _validate_category_closure(diffuse, specular, field)


def test_category_parser_rejects_vocabulary_reordering() -> None:
    detail = _diffuse_detail()
    detail["first_diffuse_audit"]["category_names"] = tuple(reversed(CATEGORY_NAMES))  # type: ignore[index]
    with pytest.raises(RayReachedEvidenceAuditError, match="vocabulary/order"):
        _parse_diffuse_audit(detail, 2)


def test_replay_plan_refuses_output_inside_sealed_source(tmp_path) -> None:
    campaign = tmp_path / "sealed"
    source = AuditReplaySource(tmp_path / "config.json", campaign)
    with pytest.raises(RayReachedEvidenceAuditError, match="sealed source"):
        AuditReplayPlan((source,), campaign / "replay")


def test_record_schema_retains_separate_component_body_metrics() -> None:
    capture = _SeedCapture.empty(points=2, cells=4, categories=len(CATEGORY_NAMES), surfaces=3)
    arrays = _record_arrays(capture)

    assert set(arrays) == {
        "diffuse_event_count",
        "diffuse_transfer",
        "diffuse_local_cell_mass",
        "specular_event_count",
        "specular_transfer",
        "specular_body_metrics",
        "first_diffuse_body_metrics",
        "body_coupling_seconds",
    }
    assert arrays["specular_body_metrics"].shape == (2, len(CATEGORY_NAMES), 6)
    assert arrays["first_diffuse_body_metrics"].shape == (2, len(CATEGORY_NAMES), 6)


def test_split_body_metrics_close_against_each_source_component() -> None:
    specular = np.zeros((len(CATEGORY_NAMES), 6), dtype=np.float64)
    diffuse = np.zeros_like(specular)
    expected = np.zeros((4, 6), dtype=np.float64)
    specular[0, (0, 3, 4, 5)] = (1.0, 2.0, 3.0, 4.0)
    diffuse[2, (0, 3, 4, 5)] = (5.0, 6.0, 7.0, 8.0)
    expected[1] = specular.sum(axis=0)
    expected[2] = diffuse.sum(axis=0)

    _validate_split_body_closure(specular, diffuse, expected)

    diffuse[2, 5] += 0.01
    with pytest.raises(RayReachedEvidenceAuditError, match="first-diffuse category body metrics"):
        _validate_split_body_closure(specular, diffuse, expected)
