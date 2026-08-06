from __future__ import annotations

import pytest

from semantic_twin.exposure.output_policy import (
    ARTIFACTS,
    PROFILES,
    ArtifactClass,
    OutputProfile,
    RetentionCost,
    STANDPOINT_REQUIRED_FIELDS,
    artifact,
    expand_model_fields,
    profile,
)


MODELS = ("isotropic", "rooftop", "street_small_cell")


def test_profiles_are_monotone_and_have_no_unknown_artifacts() -> None:
    assert set(PROFILES) == set(OutputProfile)
    minimal = set(profile("minimal").artifact_names)
    standard = set(profile(OutputProfile.STANDARD).artifact_names)
    full = set(profile("full").artifact_names)

    assert minimal <= standard <= full
    assert OutputProfile.FULL.includes(OutputProfile.MINIMAL)
    assert OutputProfile.STANDARD.includes("minimal")
    assert not OutputProfile.MINIMAL.includes(OutputProfile.STANDARD)
    assert all(name in ARTIFACTS for names in (minimal, standard, full) for name in names)


def test_every_artifact_has_a_schema_and_profile_membership() -> None:
    for name, spec in ARTIFACTS.items():
        assert spec.name == name
        assert spec.profiles
        assert len(spec.required_fields) == len(set(spec.required_fields))
        assert len(spec.optional_fields) == len(set(spec.optional_fields))
        assert set(spec.required_fields).isdisjoint(spec.optional_fields)
        assert all(field for field in spec.required_fields + spec.optional_fields)
        for selected in spec.profiles:
            assert spec.included_in(selected)


def test_sealed_provenance_includes_the_runtime_stage_ledger() -> None:
    assert "stage_seconds" in profile("minimal").fields()


def test_minimal_keeps_exact_body_fields_per_standpoint() -> None:
    fields = profile("minimal").fields(models=MODELS)
    assert "index" in fields
    assert "seconds" in fields
    for model in MODELS:
        assert f"{model}_peak_sab_w_m2" in fields
        assert f"{model}_sar_wb_w_kg" in fields
    assert STANDPOINT_REQUIRED_FIELDS[6:] == ("{model}_peak_sab_w_m2", "{model}_sar_wb_w_kg")


def test_standard_keeps_reusable_spectrum_and_body_inputs() -> None:
    fields = profile("standard").fields(models=MODELS)
    assert {"index", "rho_rooftop", "local_grid", "solid_angle"} <= set(fields)
    assert {f"rho_{model}" for model in MODELS} <= set(fields)
    assert {"illumination_models", "reference_s0_w_m2", "trace_config", "run"} <= set(fields)
    assert {"body", "local_grid", "solid_angle", "rho_rooftop"} <= set(fields)
    assert artifact("body_coupling_inputs").artifact_class is ArtifactClass.BODY_COUPLING


def test_full_keeps_blender_and_bounded_path_evidence_fields() -> None:
    fields = profile("full").fields(models=("rooftop",))
    assert {"mesh_vertices", "walk_points", "body_sab_w_m2", "rho_rooftop"} <= set(fields)
    assert {"path_vertices", "path_offsets", "path_throughput", "path_termination"} <= set(fields)
    assert {"nee_path_index", "nee_blocked", "nee_paths"} <= set(fields)
    assert "audit_products" in profile("full").artifact_names


def test_model_field_expansion_rejects_duplicate_models() -> None:
    assert expand_model_fields(("{model}_sar_wb_w_kg",), ("rooftop",)) == ("rooftop_sar_wb_w_kg",)
    with pytest.raises(ValueError, match="unique"):
        expand_model_fields(("{model}_peak_sab_w_m2",), ("rooftop", "rooftop"))


def test_retention_cost_order_matches_the_profile_ladder() -> None:
    assert RetentionCost.TINY.rank < RetentionCost.MODERATE.rank < RetentionCost.HIGH.rank
    assert artifact("sealed_provenance").retention_cost is RetentionCost.TINY
    assert artifact("path_evidence").retention_cost is RetentionCost.HIGH
