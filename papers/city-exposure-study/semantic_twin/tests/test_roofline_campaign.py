from __future__ import annotations

import dataclasses
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.exposure.coupler import BodyExposure
from semantic_twin.exposure.roofline_campaign import (
    PreparedRooflineCampaign,
    RooflineCampaignConfig,
    campaign_identity,
    component_measures,
    derive_point_seed,
    first_material_interaction_measures,
    reference_scale,
    run_roofline_campaign,
    seal_coupler_provenance,
    seal_transport_provenance,
    _validate_specular_acceptance,
)
from semantic_twin.illumination.curve import (
    HORIZONTAL_PROJECTED_EDGE_LENGTH,
    PHYSICAL_3D_EDGE_LENGTH,
    curve_from_polylines,
)
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.transport.model import Surplus
from semantic_twin.transport.next_event import NextEventField
from semantic_twin.transport.specular import OneBounceSpecularTransport
from semantic_twin.walk.model import PANORAMA_LINKS, Walk
from semantic_twin.walk.provider_corridor import PROVIDER_CORRIDOR_V1


class FakeSources:
    crop_area_m2 = 100.0
    density_per_m2 = 0.02
    eirp_w = 5.0
    physical_expected_count = 2.0
    curve = object()

    def __init__(self) -> None:
        self.positions = np.array([[1.0, 0.0, 1.5], [0.0, 2.0, 1.5]], dtype=np.float64)
        self.source_weights = np.array([1.0, 3.0], dtype=np.float64)

    def sites(self) -> np.ndarray:
        return self.positions

    def source_provenance(self):
        return {"law": "facade_tip", "curve": "sealed", "crop_area_m2": self.crop_area_m2}


class FakeEstimator:
    def __init__(self, fail_seed: int | None = None) -> None:
        self.sources = FakeSources()
        trace_config = SimpleNamespace(
            ray_epsilon_m=1.0e-3,
            as_dict=lambda: {"rays": 8, "local_cells": 2, "max_bounces": 1, "ray_epsilon_m": 1.0e-3},
        )
        self.tracer = SimpleNamespace(
            config=trace_config,
            geometry=SimpleNamespace(
                face_count=1,
                variant="llvm_ad_rgb",
                vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
                faces=np.array([[0, 1, 2]], dtype=np.int64),
            ),
            local_grid=np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float64),
            face_class=np.array([0], dtype=np.int64),
            permittivity=np.array([4.0 - 0.1j], dtype=np.complex128),
            rms_height_m=np.array([0.001], dtype=np.float64),
            atlas_material=None,
        )
        self.samples = 1
        self.max_order = 1
        self.connection_lift_m = 0.01
        self.specular_order = 1
        self.specular_candidate_budget = 100
        self.specular_refinement_relative_tolerance = 0.02
        self.specular_suffix_mode = "exact"
        self.sampled_specular_samples = 1
        self.sampled_specular_seed_offset = 2000
        self.deterministic_cache_size = 8
        self.specular_transport = None
        self.visible_face_candidates = SimpleNamespace(sample_levels=(4, 16), growth_factor=4, epsilon_m=0.001)
        self.source_quadrature = SimpleNamespace(strata_levels=(2, 4), growth_factor=2)
        self.gather_seed_offset = 1000
        self.fail_seed = fail_seed
        self.calls: list[int] = []

    def estimate_field(self, origin, *, ground_z_m=0.0, seed=None):
        assert ground_z_m == 0.0
        assert seed is not None
        self.calls.append(seed)
        if seed == self.fail_seed:
            raise RuntimeError("synthetic interruption")
        direction = np.array([[1.0, 0.0, 0.0]]) if seed % 2 else np.array([[-1.0, 0.0, 0.0]])
        direct_mass = np.array([0.25, 0.0], dtype=np.float64)
        field = NextEventField(
            local_grid=np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float64),
            solid_angle=2.0 * np.pi,
            direct_mass=direct_mass,
            bounced_mass=np.array([0.05, 0.0], dtype=np.float64),
            direct_k_hat=direction,
            direct_atom_mass=np.array([0.25], dtype=np.float64),
            specular_k_hat=direction,
            specular_atom_mass=np.array([0.125], dtype=np.float64),
            all_specular_k_hat=direction,
            all_specular_atom_mass=np.array([0.125], dtype=np.float64),
            all_specular_mass=0.125,
            specular_components_separable=True,
            includes_specular=True,
            missing_specular=True,
            specular_estimate_kind="exact_order_1",
            specular_bounce_cap=1,
            maximum_completed_all_specular_order=1,
            maximum_completed_specular_suffix_order=1,
            all_specular_diagnostics={"seconds": 0.02, "candidates": 4},
            specular_source_refinement=({"level": 8, "source_support_complete": True},),
        )
        detail = {
            "direct_seconds": 0.01,
            "stochastic_trace_seconds": 0.04,
            "specular_suffix_seconds": 0.03,
            "deterministic_specular_seconds": 0.07,
        }
        return Surplus("next_event", "facade_tip", field.direct, field.total, detail), field


class FirstMaterialInteractionFakeEstimator(FakeEstimator):
    """A sealed exact direct/all-specular/first-diffuse field for campaign tests."""

    def __init__(self) -> None:
        super().__init__()
        self.transport_topology = "first_material_interaction_v1"
        self.specular_suffix_mode = "disabled"

    def estimate_field(self, origin, *, ground_z_m=0.0, seed=None):
        surplus, field = super().estimate_field(origin, ground_z_m=ground_z_m, seed=seed)
        field = dataclasses.replace(
            field,
            maximum_completed_specular_suffix_order=0,
            all_specular_diagnostics={"seconds": 0.02, "candidates": 4, "candidate_support_complete": True},
            specular_work={"enabled": True, "support_complete": True},
        )
        detail = {
            **surplus.detail,
            "transport_topology": "first_material_interaction_v1",
            "first_material_interaction_nee_only": True,
            "mixed_specular_suffix_order_1": 0.0,
            "mixed_specular_suffix_order_1_included": False,
            "sampled_specular_suffix": {"enabled": False},
        }
        return dataclasses.replace(surplus, detail=detail), field


class FakeCoupler:
    def __init__(self) -> None:
        self.body = SimpleNamespace(
            name="fake",
            areas=np.array([1.0, 3.0], dtype=np.float64),
            normals=np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]], dtype=np.float64),
            vertices=np.array(
                [
                    [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0]],
                    [[1.0, 0.0, 0.0], [1.0, 3.0, 0.0], [1.0, 0.0, 2.0]],
                ],
                dtype=np.float64,
            ),
        )
        self.body_mass_kg = 10.0
        self.level = 2
        self.frequency_hz = 15.0e9
        self.engine = SimpleNamespace(T0=0.5)
        self.body_anterior_axis = np.array([0.0, -1.0, 0.0], dtype=np.float64)
        self.yaws: list[float] = []

    def couple_measure_with_sab(
        self,
        measure,
        reference_s0_w_m2,
        *,
        chunk_cells=512,
        body_yaw_deg=None,
    ):
        assert chunk_cells > 0
        assert body_yaw_deg is not None
        self.yaws.append(body_yaw_deg)
        directions, powers = measure.scaled_paths_data(reference_s0_w_m2)
        sab = np.zeros(2, dtype=np.float64)
        for direction, power in zip(directions, powers, strict=True):
            sab[0 if direction[0] >= 0.0 else 1] += power
        arriving = float(np.sum(powers, dtype=np.float64))
        absorbed = float(np.sum(sab * self.body.areas, dtype=np.float64))
        exposure = BodyExposure(
            reference_s0_w_m2=float(reference_s0_w_m2),
            arriving_power_density_w_m2=arriving,
            susceptibility=measure.total,
            peak_sab_w_m2=float(np.max(sab)),
            mean_sab_w_m2=absorbed / float(np.sum(self.body.areas)),
            absorbed_power_w=absorbed,
            sar_wb_w_kg=absorbed / self.body_mass_kg,
        )
        return exposure, sab


def prepared(
    tmp_path,
    estimator=None,
    *,
    seeds=(1, 2),
    material=None,
    looks=None,
    source_measure_rule=None,
    config=None,
):
    walk = Walk(
        points=np.array([[0.0, 0.0, 1.5], [0.0, 0.0, 1.5]], dtype=np.float64),
        ground_z_m=np.zeros(2, dtype=np.float64),
        step_m=np.array([0.0, 3.0], dtype=np.float64),
        provenance={"point_kind": ["camera_registered", "stride_interpolated"]},
        kind=PANORAMA_LINKS,
        site="test_square",
        body_yaw_deg=np.array([10.0, 20.0], dtype=np.float64),
    )
    if config is None:
        config = RooflineCampaignConfig(
            site="test_square",
            cohort="primary_semantic_route",
            material_mode="atlas",
            output_dir=tmp_path / "campaign",
            planned_seeds=seeds,
            convergence_looks=((1, 2) if len(seeds) == 2 else ()) if looks is None else looks,
            source_measure_rule=source_measure_rule,
        )
    selected_estimator = FakeEstimator() if estimator is None else estimator
    coupler = FakeCoupler()
    return PreparedRooflineCampaign(
        config=config,
        walk=walk,
        estimator=selected_estimator,
        coupler=coupler,
        source_provenance=selected_estimator.sources.source_provenance(),
        material_provenance={"material_mode": "atlas", "binding": "joint semantic atlas"}
        if material is None
        else material,
        input_provenance={"mesh_sha256": "abc"},
        transport_provenance=seal_transport_provenance(selected_estimator),
        coupler_provenance=seal_coupler_provenance(coupler),
    )


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_coupler_seal_distinguishes_level_two_backend_and_reduction_algorithm() -> None:
    numpy_coupler = FakeCoupler()
    numpy_coupler.level2_backend = "numpy"
    numpy_coupler.level2_algorithm = "numpy_float64_matmul_relu_direction_chunks_v1"
    numpy_coupler.level2_direction_block_size = None
    cuda_coupler = FakeCoupler()
    cuda_coupler.level2_backend = "cuda"
    cuda_coupler.level2_algorithm = "drjit_float64_dot_relu_power_block_reduce_fixed512_v1"
    cuda_coupler.level2_direction_block_size = 512

    numpy_seal = seal_coupler_provenance(numpy_coupler)
    cuda_seal = seal_coupler_provenance(cuda_coupler)

    assert "level2_backend" not in numpy_seal
    assert cuda_seal["level2_backend"] == "cuda"
    assert cuda_seal["level2_direction_block_size"] == 512
    assert cuda_seal["level2_algorithm"] == "drjit_float64_dot_relu_power_block_reduce_fixed512_v1"
    assert cuda_seal != numpy_seal


def test_default_campaign_identity_dict_is_legacy_byte_compatible(tmp_path):
    config = RooflineCampaignConfig(
        site="test_square",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path,
        planned_seeds=(1, 2),
        convergence_looks=(1, 2),
    )
    assert config.identity_dict() == {
        "schema_version": "roofline_body_campaign_v1",
        "site": "test_square",
        "cohort": "primary_semantic_route",
        "material_mode": "atlas",
        "planned_seeds": [1, 2],
        "reference_mode": "per_density_eirp",
        "sampling_claim": "full_declared_walk",
        "point_seed_derivation": "blake2b_64_person_AEGIS_NEE_v1(seed_u64,standpoint_u64)",
        "body_chunk_cells": 512,
        "convergence_looks": [1, 2],
        "minimum_completed_specular_order": 1,
        "specular_acceptance": "exact_complete",
    }


def test_first_material_interaction_campaign_persists_closed_named_components(tmp_path):
    config = RooflineCampaignConfig(
        site="test_square",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "first-material",
        planned_seeds=(1,),
        minimum_completed_specular_order=1,
        specular_acceptance="first_material_interaction_exact_order_1",
        transport_topology="first_material_interaction_v1",
    )
    campaign = prepared(
        tmp_path,
        estimator=FirstMaterialInteractionFakeEstimator(),
        seeds=(1,),
        config=config,
    )
    result = run_roofline_campaign(campaign)

    identity = json.loads((config.output_dir / "campaign_identity.json").read_text())
    assert identity["data"]["configuration"]["transport_topology"] == "first_material_interaction_v1"
    assert identity["data"]["components"] == ["direct", "all_specular", "first_diffuse", "total"]
    assert identity["data"]["transport"]["estimator"]["configuration"]["transport_topology"] == (
        "first_material_interaction_v1"
    )

    checkpoint = json.loads(result["checkpoint"].read_text())
    assert checkpoint["schema_version"] == "roofline_body_campaign_first_material_interaction_v1"
    assert checkpoint["components"] == ["direct", "all_specular", "first_diffuse", "total"]
    with np.load(config.output_dir / "checkpoint" / checkpoint["committed"][0]["path"], allow_pickle=False) as shard:
        raw_transfer = np.asarray(shard["raw_transfer"])
        body_metrics = np.asarray(shard["body_metrics"])
    np.testing.assert_allclose(raw_transfer[:, 1], 0.125, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(raw_transfer[:, 3], np.sum(raw_transfer[:, :3], axis=1), rtol=2.0e-12, atol=1.0e-15)
    np.testing.assert_allclose(
        body_metrics[:, 3, 4], np.sum(body_metrics[:, :3, 4], axis=1), rtol=2.0e-12, atol=1.0e-15
    )

    row = json.loads(result["locations"].read_text().splitlines()[0])
    assert set(row["components"]) == {"direct", "all_specular", "first_diffuse", "total"}
    assert row["specular_diagnostic_variants"][0]["data"]["first_material_interaction_nee_only"] is True
    assert json.loads(result["summary"].read_text())["components"] == [
        "direct",
        "all_specular",
        "first_diffuse",
        "total",
    ]


def test_first_material_interaction_measure_rejects_mixed_suffix(tmp_path):
    _, exact = FirstMaterialInteractionFakeEstimator().estimate_field(np.zeros(3), seed=1)
    scale = reference_scale(FirstMaterialInteractionFakeEstimator().sources, np.zeros(3), "per_density_eirp")
    measures = first_material_interaction_measures(exact, scale, "test")
    assert tuple(measures) == ("direct", "all_specular", "first_diffuse", "total")
    assert measures["total"].total == pytest.approx(
        measures["direct"].total + measures["all_specular"].total + measures["first_diffuse"].total
    )
    mixed = dataclasses.replace(
        exact,
        specular_k_hat=np.concatenate((exact.specular_k_hat, exact.specular_k_hat)),
        specular_atom_mass=np.concatenate((exact.specular_atom_mass, np.array([0.001]))),
        mixed_specular_k_hat=exact.specular_k_hat,
        mixed_specular_atom_mass=np.array([0.001]),
        mixed_specular_mass=0.001,
    )
    with pytest.raises(RuntimeError, match="mixed specular suffix"):
        first_material_interaction_measures(mixed, scale, "test")


def test_first_material_interaction_acceptance_refuses_mixed_suffix(tmp_path):
    _surplus, exact = FirstMaterialInteractionFakeEstimator().estimate_field(np.zeros(3), seed=1)
    config = RooflineCampaignConfig(
        site="test",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "first",
        planned_seeds=(1,),
        specular_acceptance="first_material_interaction_exact_order_1",
        transport_topology="first_material_interaction_v1",
    )
    detail = {
        "transport_topology": "first_material_interaction_v1",
        "first_material_interaction_nee_only": True,
        "mixed_specular_suffix_order_1": 0.0,
        "mixed_specular_suffix_order_1_included": False,
        "sampled_specular_suffix": {"enabled": False},
    }
    _validate_specular_acceptance(exact, detail, config)
    mixed = dataclasses.replace(
        exact,
        specular_k_hat=np.concatenate((exact.specular_k_hat, exact.specular_k_hat)),
        specular_atom_mass=np.concatenate((exact.specular_atom_mass, np.array([0.001]))),
        mixed_specular_k_hat=exact.specular_k_hat,
        mixed_specular_atom_mass=np.array([0.001]),
        mixed_specular_mass=0.001,
    )
    with pytest.raises(RuntimeError, match="no_mixed_suffix_mass"):
        _validate_specular_acceptance(mixed, detail, config)


def test_explicit_source_measure_rule_changes_sealed_identity(tmp_path):
    default = RooflineCampaignConfig(
        site="test_square",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "default",
        planned_seeds=(1,),
    )
    physical = dataclasses.replace(
        default,
        output_dir=tmp_path / "physical",
        source_measure_rule=PHYSICAL_3D_EDGE_LENGTH,
    )
    projected = dataclasses.replace(
        default,
        output_dir=tmp_path / "projected",
        source_measure_rule=HORIZONTAL_PROJECTED_EDGE_LENGTH,
    )

    assert "source_measure_rule" not in default.identity_dict()
    assert physical.identity_dict()["source_measure_rule"] == PHYSICAL_3D_EDGE_LENGTH
    assert projected.identity_dict()["source_measure_rule"] == HORIZONTAL_PROJECTED_EDGE_LENGTH
    assert physical.identity_dict() != projected.identity_dict()


def test_completed_endpoint_curve_writes_hashed_atomic_source_audit(tmp_path):
    curve = curve_from_polylines(
        [
            np.array([[1.0, 0.0, 2.0], [4.0, 0.0, 6.0]], dtype=np.float64),
            np.array([[10.0, 0.0, 2.0], [15.0, 0.0, 2.0]], dtype=np.float64),
        ]
    )
    estimator = FakeEstimator()
    estimator.sources = SourceSet.from_curve(
        curve,
        crop_area_m2=100.0,
        density_per_m2=0.02,
        eirp_w=5.0,
        source_measure_rule=HORIZONTAL_PROJECTED_EDGE_LENGTH,
    )
    campaign = prepared(
        tmp_path,
        estimator,
        seeds=(1,),
        looks=(),
        source_measure_rule=HORIZONTAL_PROJECTED_EDGE_LENGTH,
    )
    outputs = run_roofline_campaign(campaign)
    audit_json = campaign.config.output_dir / "source_curve_audit.json"
    audit_npz = campaign.config.output_dir / "source_curve_audit.npz"

    audit = json.loads(audit_json.read_text())
    manifest = json.loads(outputs["manifest"].read_text())
    assert audit["selected_source_measure_rule"] == HORIZONTAL_PROJECTED_EDGE_LENGTH
    assert audit["source_measure_rule_was_explicit"] is True
    assert audit["physical_3d_total_m"] == pytest.approx(10.0)
    assert audit["horizontal_projected_total_m"] == pytest.approx(8.0)
    assert audit["npz"]["sha256"] == _sha256(audit_npz)
    assert audit["npz"]["bytes"] == audit_npz.stat().st_size
    assert manifest["files"]["source_curve_audit.json"] == _sha256(audit_json)
    assert manifest["files"]["source_curve_audit.npz"] == _sha256(audit_npz)
    with np.load(audit_npz, allow_pickle=False) as payload:
        np.testing.assert_allclose(payload["segment_starts_m"], curve.segment_starts)
        np.testing.assert_allclose(payload["segment_ends_m"], curve.segment_ends)
        np.testing.assert_allclose(payload["midpoints_m"], curve.points)
        np.testing.assert_allclose(payload["physical_3d_lengths_m"], [5.0, 5.0])
        np.testing.assert_allclose(payload["horizontal_projected_lengths_m"], [3.0, 5.0])
        assert payload["selected_measure_rule"].item() == HORIZONTAL_PROJECTED_EDGE_LENGTH
    assert audit_npz.stat().st_size < 10_000


def test_legacy_curve_campaign_skips_source_audit_safely(tmp_path):
    campaign = prepared(tmp_path, seeds=(1,), looks=())
    outputs = run_roofline_campaign(campaign)
    manifest = json.loads(outputs["manifest"].read_text())

    assert not (campaign.config.output_dir / "source_curve_audit.json").exists()
    assert not (campaign.config.output_dir / "source_curve_audit.npz").exists()
    assert not any(name.startswith("source_curve_audit") for name in manifest["files"])


def test_legacy_summary_keys_remain_exactly_stable(tmp_path):
    outputs = run_roofline_campaign(prepared(tmp_path, seeds=(1,), looks=()))
    summary = json.loads(outputs["summary"].read_text())

    assert set(summary) == {
        "schema_version",
        "site",
        "cohort",
        "standpoints",
        "replicas",
        "seeds",
        "reference_mode",
        "timing_seconds_observed_total",
        "timing_observation_counts",
        "convergence",
    }
    assert "components" not in summary


def test_reference_normalization_cancels_d_ref_and_keeps_exact_four_pi():
    sources = FakeSources()
    origin = np.array([0.0, 0.0, 1.5])
    scale = reference_scale(sources, origin, "per_density_eirp")
    expected_d_ref = 0.25 / 1.0**2 + 0.75 / 2.0**2
    assert scale.transfer_m_inv2 == pytest.approx(expected_d_ref)
    assert scale.reference_s0_w_m2 == pytest.approx(100.0 * expected_d_ref / (4.0 * np.pi))
    physical = reference_scale(sources, origin, "physical")
    assert physical.reference_s0_w_m2 / scale.reference_s0_w_m2 == pytest.approx(
        sources.density_per_m2 * sources.eirp_w
    )

    _, field = FakeEstimator().estimate_field(origin, seed=1)
    direct = component_measures(field, scale, "identity")["direct"]
    _, incident = direct.scaled_paths_data(scale.reference_s0_w_m2)
    assert incident.sum() == pytest.approx(100.0 * 0.25 / (4.0 * np.pi))


def test_comparable_campaign_opt_in_separates_route_and_material_mode(tmp_path):
    with pytest.raises(ValueError, match="requires route_contract"):
        RooflineCampaignConfig(
            site="korenmarkt",
            cohort="comparable_city",
            material_mode="atlas",
            output_dir=tmp_path / "missing-route",
            planned_seeds=(1,),
        )

    primary = RooflineCampaignConfig(
        site="korenmarkt",
        cohort="comparable_city",
        route_contract="registered_span_street_v1",
        material_mode="atlas",
        output_dir=tmp_path / "primary",
        planned_seeds=(1,),
    )
    control = dataclasses.replace(primary, output_dir=tmp_path / "control", material_mode="geometric")
    assert primary.identity_dict()["route_contract"] == "registered_span_street_v1"
    assert control.material_mode == "geometric"

    with pytest.raises(ValueError, match="supports atlas primary runs"):
        dataclasses.replace(primary, material_mode="semantic")

    corridor = dataclasses.replace(
        primary,
        output_dir=tmp_path / "provider-corridor",
        route_contract=PROVIDER_CORRIDOR_V1,
    )
    assert corridor.identity_dict()["route_contract"] == PROVIDER_CORRIDOR_V1


@pytest.mark.parametrize(
    ("attribute", "value"),
    (
        ("variant", "cuda_ad_rgb"),
        ("tolerance", 0.03),
        ("face_growth", 8),
        ("source_growth", 3),
    ),
)
def test_transport_seal_changes_with_backend_and_adaptive_controls(attribute, value):
    baseline = FakeEstimator()
    changed = FakeEstimator()
    if attribute == "variant":
        changed.tracer.geometry.variant = value
    elif attribute == "tolerance":
        changed.specular_refinement_relative_tolerance = value
    elif attribute == "face_growth":
        changed.visible_face_candidates.growth_factor = value
    else:
        changed.source_quadrature.growth_factor = value
    assert seal_transport_provenance(changed) != seal_transport_provenance(baseline)


def test_transport_seal_covers_complete_atlas_state():
    def atlas():
        return SimpleNamespace(
            face_count=1,
            material_names=("brick",),
            provenance={"rule": "fixture"},
            face_to_atlas_row=np.array([0], dtype=np.int64),
            material_probability=np.ones((1, 1, 1, 1), dtype=np.float32),
            supported=np.ones((1, 1, 1), dtype=bool),
            valid_texels=np.ones((1, 1), dtype=bool),
            material_class=np.array([0], dtype=np.int64),
            nonblocking=np.zeros((1, 1, 1), dtype=bool),
        )

    baseline = FakeEstimator()
    changed = FakeEstimator()
    baseline.tracer.atlas_material = atlas()
    changed.tracer.atlas_material = atlas()
    changed.tracer.atlas_material.material_probability[0, 0, 0, 0] = 0.5
    assert seal_transport_provenance(changed) != seal_transport_provenance(baseline)


def test_transport_seal_covers_sampled_proposals_and_counter_controls():
    baseline = FakeEstimator()
    baseline.specular_transport = OneBounceSpecularTransport(baseline.tracer)
    baseline.specular_suffix_mode = "sampled"
    sealed = seal_transport_provenance(baseline)["estimator"]["configuration"]

    assert sealed["sampled_specular_samples"] == 1
    assert sealed["sampled_specular_seed_offset"] == 2000
    assert sealed["sampled_specular"]["face_proposal"] == "0.9_triangle_area_plus_0.1_uniform_full_support_v1"
    assert sealed["sampled_specular"]["counter_generator"] == "splitmix64_seed_counter_dimension_v1"
    assert sealed["sampled_specular"]["surface_support_complete"] is True

    changed = FakeEstimator()
    changed.specular_transport = OneBounceSpecularTransport(changed.tracer)
    changed.specular_suffix_mode = "sampled"
    changed.sampled_specular_seed_offset = 2001
    assert seal_transport_provenance(changed) != seal_transport_provenance(baseline)


def test_specular_acceptance_distinguishes_exact_adaptive_and_omitted(tmp_path):
    _, exact = FakeEstimator().estimate_field(np.zeros(3), seed=1)
    exact_config = RooflineCampaignConfig(
        site="test",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "exact",
        planned_seeds=(1,),
    )
    _validate_specular_acceptance(exact, {}, exact_config)
    assert exact.specular_order_one_complete is True
    assert exact.specular_complete_through_bounce_cap is True

    adaptive = dataclasses.replace(
        exact,
        maximum_completed_all_specular_order=0,
        maximum_completed_specular_suffix_order=0,
        specular_estimate_kind="finite_resolution_order_1",
        finite_resolution_specular_estimate=True,
        specular_numerically_converged=True,
    )
    adaptive_config = dataclasses.replace(
        exact_config,
        output_dir=tmp_path / "adaptive",
        minimum_completed_specular_order=0,
        specular_acceptance="adaptive_converged",
    )
    work = {
        "enabled": True,
        "numerically_converged": True,
        "stop_reason": "relative_tolerance_reached",
    }
    _validate_specular_acceptance(adaptive, {"finite_resolution_specular_work": work}, adaptive_config)
    assert adaptive.specular_order_one_complete is False
    assert adaptive.specular_complete_through_bounce_cap is False
    with pytest.raises(RuntimeError, match="numerical tolerance"):
        _validate_specular_acceptance(
            dataclasses.replace(adaptive, specular_numerically_converged=False),
            {"finite_resolution_specular_work": work},
            adaptive_config,
        )

    omitted = dataclasses.replace(
        exact,
        specular_k_hat=np.empty((0, 3)),
        specular_atom_mass=np.empty(0),
        all_specular_k_hat=np.empty((0, 3)),
        all_specular_atom_mass=np.empty(0),
        all_specular_mass=0.0,
        specular_components_separable=False,
        includes_specular=False,
        specular_estimate_kind="absent",
        maximum_completed_all_specular_order=0,
        maximum_completed_specular_suffix_order=0,
    )
    omitted_config = dataclasses.replace(
        exact_config,
        output_dir=tmp_path / "omitted",
        minimum_completed_specular_order=0,
        specular_acceptance="omitted_diagnostic",
    )
    _validate_specular_acceptance(omitted, {}, omitted_config)
    assert omitted.specular_order_one_complete is False
    assert omitted.specular_complete_through_bounce_cap is False


def test_combined_sampled_policy_uses_inclusion_not_formal_completion(tmp_path):
    _, exact = FakeEstimator().estimate_field(np.zeros(3), seed=1)
    combined = dataclasses.replace(
        exact,
        specular_estimate_kind="adaptive_all_sampled_mixed_order_1",
        finite_resolution_specular_estimate=True,
        specular_numerically_converged=True,
        maximum_completed_all_specular_order=0,
        maximum_completed_specular_suffix_order=0,
        all_specular_k_hat=exact.specular_k_hat,
        all_specular_atom_mass=exact.specular_atom_mass,
        specular_components_separable=True,
        sampled_specular_suffix_full_support=True,
    )
    config = RooflineCampaignConfig(
        site="test",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "combined",
        planned_seeds=(1,),
        minimum_completed_specular_order=0,
        specular_acceptance="adaptive_all_specular_sampled_mixed_order_1",
    )
    work = {"enabled": True, "numerically_converged": True, "stop_reason": "relative_tolerance_reached"}
    sampled = {
        "enabled": True,
        "samples_per_vertex": 2,
        "uncertainty_scope": "conditional_on_traced_diffuse_vertices; campaign replicas control total uncertainty",
        "sampling_identity": {
            "status": "experimental_opt_in",
            "surface_support_complete": True,
            "source_support": 4,
            "source_count": 4,
        },
    }
    _validate_specular_acceptance(
        combined,
        {"finite_resolution_specular_work": work, "sampled_specular_suffix": sampled},
        config,
    )
    assert combined.specular_order_one_complete is False
    assert combined.specular_complete_through_bounce_cap is False
    with pytest.raises(RuntimeError, match="field.specular_numerically_converged=False") as error:
        _validate_specular_acceptance(
            dataclasses.replace(combined, specular_numerically_converged=False),
            {
                "finite_resolution_specular_work": {
                    **work,
                    "numerically_converged": False,
                    "stop_reason": "candidate_budget_exhausted",
                },
                "sampled_specular_suffix": sampled,
            },
            config,
        )
    assert "work.numerically_converged=False" in str(error.value)
    assert "work.stop_reason='candidate_budget_exhausted'" in str(error.value)


def test_combined_sampled_policy_accepts_exact_all_specular_branch(tmp_path):
    _, exact = FakeEstimator().estimate_field(np.zeros(3), seed=1)
    combined = dataclasses.replace(
        exact,
        specular_estimate_kind="exact_all_sampled_mixed_order_1",
        finite_resolution_specular_estimate=False,
        specular_numerically_converged=True,
        maximum_completed_all_specular_order=1,
        maximum_completed_specular_suffix_order=0,
        all_specular_k_hat=exact.specular_k_hat,
        all_specular_atom_mass=exact.specular_atom_mass,
        specular_components_separable=True,
        sampled_specular_suffix_full_support=True,
    )
    config = RooflineCampaignConfig(
        site="test",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "combined-exact",
        planned_seeds=(1,),
        minimum_completed_specular_order=0,
        specular_acceptance="adaptive_all_specular_sampled_mixed_order_1",
    )
    work = {
        "enabled": True,
        "numerically_converged": True,
        "support_complete": True,
        "stop_reason": "full_reflection_and_source_support_enumerated",
    }
    sampled = {
        "enabled": True,
        "samples_per_vertex": 2,
        "uncertainty_scope": "conditional_on_traced_diffuse_vertices; campaign replicas control total uncertainty",
        "sampling_identity": {
            "status": "experimental_opt_in",
            "surface_support_complete": True,
            "source_support": 4,
            "source_count": 4,
        },
    }
    detail = {"finite_resolution_specular_work": work, "sampled_specular_suffix": sampled}
    _validate_specular_acceptance(combined, detail, config)

    with pytest.raises(RuntimeError, match="work.support_complete_when_exact=False"):
        _validate_specular_acceptance(
            combined,
            {
                "finite_resolution_specular_work": {**work, "support_complete": False},
                "sampled_specular_suffix": sampled,
            },
            config,
        )


def test_combined_sampled_policy_requires_zero_formal_minimum(tmp_path):
    with pytest.raises(ValueError, match="requires minimum_completed_specular_order=0"):
        RooflineCampaignConfig(
            site="test",
            cohort="primary_semantic_route",
            material_mode="atlas",
            output_dir=tmp_path / "bad-combined",
            planned_seeds=(1,),
            minimum_completed_specular_order=1,
            specular_acceptance="adaptive_all_specular_sampled_mixed_order_1",
        )


def test_two_replicas_reuse_direct_and_deterministic_specular_body_solves(tmp_path):
    campaign = prepared(tmp_path, seeds=(1, 2), looks=())
    run_roofline_campaign(campaign)

    assert campaign.coupler.yaws == [10.0] * 3 + [20.0] * 3 + [10.0, 20.0]
    assert len(campaign.coupler.yaws) == 8
    checkpoint = json.loads((campaign.config.output_dir / "checkpoint" / "index.json").read_text())
    second_diagnostics = json.loads(
        (campaign.config.output_dir / "checkpoint" / checkpoint["committed"][1]["diagnostics_path"]).read_text()
    )
    for point in second_diagnostics:
        assert point["body_component_cache_hits"] == {
            "direct": True,
            "all_specular": True,
            "specular": False,
            "diffuse": False,
        }


def test_campaign_resumes_a_committed_prefix_and_reduces_peak_after_field_mean(tmp_path):
    interrupted = FakeEstimator(fail_seed=derive_point_seed(2, 0))
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        run_roofline_campaign(prepared(tmp_path, interrupted))
    assert interrupted.calls == [derive_point_seed(1, 0), derive_point_seed(1, 1), derive_point_seed(2, 0)]

    resumed_estimator = FakeEstimator()
    campaign = prepared(tmp_path, resumed_estimator)
    outputs = run_roofline_campaign(campaign)
    assert resumed_estimator.calls == [derive_point_seed(2, 0), derive_point_seed(2, 1)]
    assert set(outputs) == {"manifest", "locations", "summary", "checkpoint"}

    rows = [json.loads(line) for line in outputs["locations"].read_text().splitlines()]
    assert len(rows) == 2
    first = rows[0]
    mean_replica_peak = first["components"]["total"]["body"]["mean_per_replica_peak_sab_w_m2"]["mean"]
    ensemble_peak = first["components"]["total"]["body"]["ensemble_field_peak_sab_w_m2"]
    unit = 100.0 / (4.0 * np.pi)
    assert mean_replica_peak == pytest.approx(0.4 * unit)
    assert ensemble_peak == pytest.approx(0.2375 * unit)
    assert first["reference"]["d_ref_m_inv2"] == pytest.approx(0.4375)
    assert first["reference"]["d_vis_m_inv2"] == pytest.approx(0.25)
    assert first["multipath_surplus"]["ratio"] == pytest.approx(1.7)
    total_absorbed = first["components"]["total"]["body"]["absorbed_power_w"]["mean"]
    component_absorbed = sum(
        first["components"][component]["body"]["absorbed_power_w"]["mean"]
        for component in ("direct", "specular", "diffuse")
    )
    assert total_absorbed == pytest.approx(component_absorbed)
    assert first["components"]["total"]["body"]["mean_sab_w_m2"]["mean"] == pytest.approx(total_absorbed / 4.0)
    assert first["components"]["total"]["body"]["sar_wb_w_kg"]["mean"] == pytest.approx(total_absorbed / 10.0)
    timing = first["timing_seconds_per_replica_mean"]
    assert timing["direct_shadow_seconds"] == pytest.approx(0.01)
    assert timing["stochastic_trace_seconds"] == pytest.approx(0.04)
    assert timing["specular_seconds"] == pytest.approx(0.07)
    assert timing["body_coupling_seconds"] is not None
    assert campaign.coupler.yaws == [10.0] * 3 + [20.0] * 3

    index = json.loads(outputs["checkpoint"].read_text())
    assert [entry["seed"] for entry in index["committed"]] == [1, 2]
    diagnostics_path = outputs["checkpoint"].parent / index["committed"][0]["diagnostics_path"]
    diagnostics = json.loads(diagnostics_path.read_text())
    assert diagnostics[0]["specular_bounce_cap"] == 1
    assert diagnostics[0]["specular_order_one_complete"] is True
    assert diagnostics[0]["specular_complete_through_bounce_cap"] is True
    assert diagnostics[0]["specular_result_complete"] is True
    manifest = json.loads(outputs["manifest"].read_text())
    assert len([name for name in manifest["files"] if name.endswith(".npz")]) >= 2


def test_campaign_refuses_identity_drift_and_unlabelled_cohorts(tmp_path):
    campaign = prepared(tmp_path, seeds=(1,))
    original_identity = campaign_identity(campaign)["sha256"]
    campaign.walk.step_m[1] = 4.0
    assert campaign_identity(campaign)["sha256"] != original_identity
    campaign.walk.step_m[1] = 3.0
    campaign.estimator.sources.positions[0, 0] = 1.25
    assert campaign_identity(campaign)["sha256"] != original_identity
    campaign.estimator.sources.positions[0, 0] = 1.0
    campaign.coupler.body.vertices[0, 0, 0] = 0.25
    with pytest.raises(ValueError, match="body coupler drifted"):
        campaign_identity(campaign)
    campaign.coupler.body.vertices[0, 0, 0] = 0.0
    run_roofline_campaign(campaign)
    changed = prepared(
        tmp_path,
        seeds=(1,),
        material={"material_mode": "atlas", "binding": "different semantic atlas"},
    )
    with pytest.raises(ValueError, match="different roofline campaign"):
        run_roofline_campaign(changed)

    with pytest.raises(ValueError, match="cannot use geometric materials"):
        RooflineCampaignConfig(
            site="test_square",
            cohort="primary_semantic_route",
            material_mode="geometric",
            output_dir=tmp_path / "bad",
            planned_seeds=(1,),
        )


def test_checkpoint_keeps_only_scalar_shards_and_bounded_surface_looks(tmp_path):
    outputs = run_roofline_campaign(prepared(tmp_path, seeds=(1, 2, 3), looks=(2,)))
    checkpoint_root = outputs["checkpoint"].parent
    scalar_shards = sorted((checkpoint_root / "replicas").glob("*.npz"))
    cumulative = sorted((checkpoint_root / "cumulative").glob("*.npz"))
    assert len(scalar_shards) == 3
    assert len(cumulative) == 2
    for path in scalar_shards:
        with np.load(path, allow_pickle=False) as payload:
            assert "total_sab" not in payload.files
            assert set(payload.files) == {"raw_transfer", "body_metrics", "timings", "field_meta", "reference"}

    index = json.loads(outputs["checkpoint"].read_text())
    assert index["cumulative_sab"]["replicas"] == 3
    assert [entry["replicas"] for entry in index["look_sab"]] == [2]

    orphan = checkpoint_root / "cumulative" / "sab_sum_9999_seed_0000000001.npz"
    orphan.write_bytes(b"orphan")
    temporary = checkpoint_root / "replicas" / ".seed_0000000001.npz.tmp-123"
    temporary.write_bytes(b"partial")
    run_roofline_campaign(prepared(tmp_path, seeds=(1, 2, 3), looks=(2,)))
    assert not orphan.exists()
    assert not temporary.exists()

    first_shard = checkpoint_root / index["committed"][0]["path"]
    first_shard.write_bytes(first_shard.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="hash validation"):
        run_roofline_campaign(prepared(tmp_path, seeds=(1, 2, 3), looks=(2,)))


def test_point_seed_is_unique_after_device_style_low_64_mask():
    values = [derive_point_seed(seed, point) for seed in (0, 1, 2**64 - 1) for point in range(20)]
    masked = [value & ((1 << 64) - 1) for value in values]
    assert values == masked
    assert len(masked) == len(set(masked))
