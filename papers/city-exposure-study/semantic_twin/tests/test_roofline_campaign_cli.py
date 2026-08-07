from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin import paths
from semantic_twin.cli import roofline_campaign as command
from semantic_twin.exposure import roofline_setup
from semantic_twin.exposure.roofline_setup import (
    PreparationBackend,
    RooflineSetupConfig,
    load_roofline_setup,
    preflight_report,
    prepare_roofline_campaign,
)
from semantic_twin.runconfig import NextEventConfig, RunConfig
from semantic_twin.walk.model import PANORAMA_LINKS, Walk


def setup_document(root, *, output="outputs/roofline/test"):
    return {
        "study_root": str(root),
        "run": {
            "site": "korenmarkt",
            "crop_m": 250,
            "law": "roofline",
            "models": ["isotropic"],
            "estimator": "next_event",
            "next_event": {
                "builders": 1,
                "held_out": 1,
                "azimuths": 32,
                "elevations": 8,
                "connections": 1,
            },
            "walk": "route",
            "walk_path": "links",
            "locations": 0,
            "materials": "atlas",
            "rays": 64,
            "local_cells": 32,
            "tag": "test",
        },
        "campaign": {
            "site": "korenmarkt",
            "cohort": "primary_semantic_route",
            "material_mode": "atlas",
            "output_dir": output,
            "planned_seeds": [7, 8],
            "convergence_looks": [1, 2],
        },
        "source": {"specular_candidate_budget": 1000},
    }


def test_load_setup_freezes_full_route_and_resolves_paths(tmp_path):
    document = setup_document(tmp_path)
    document["run"]["atlas_npz"] = "outputs/site_semantics/korenmarkt/joint_atlas_250m_r8.npz"
    config = tmp_path / "campaign.json"
    config.write_text(json.dumps(document))
    setup = load_roofline_setup(config)
    assert setup.study_root == tmp_path.resolve()
    assert setup.run.locations == 0
    assert setup.run.walk_path == "links"
    assert setup.campaign.output_dir == tmp_path / "outputs/roofline/test"
    assert setup.campaign.planned_seeds == (7, 8)
    assert setup.run.atlas_npz == str(tmp_path / "outputs/site_semantics/korenmarkt/joint_atlas_250m_r8.npz")
    assert setup.setup_file == config.resolve()


def test_combined_sampled_setup_requires_room_for_the_mixed_suffix(tmp_path):
    document = setup_document(tmp_path)
    document["run"]["max_bounces"] = 1
    document["campaign"]["minimum_completed_specular_order"] = 0
    document["campaign"]["specular_acceptance"] = "adaptive_all_specular_sampled_mixed_order_1"
    document["source"].update({"specular_suffix_mode": "sampled", "sampled_specular_samples": 1})
    config = tmp_path / "bad-sampled.json"
    config.write_text(json.dumps(document))

    with pytest.raises(ValueError, match="requires max_bounces>=2"):
        load_roofline_setup(config)


@pytest.mark.parametrize(
    ("name", "site", "variant", "kernel", "acceptance"),
    (
        (
            "roofline_campaign_korenmarkt_pilot_llvm.json",
            "korenmarkt",
            "llvm_ad_rgb",
            "numpy",
            "adaptive_converged",
        ),
        (
            "roofline_campaign_korenmarkt_pilot_cuda.json",
            "korenmarkt",
            "cuda_ad_rgb",
            "drjit",
            "omitted_diagnostic",
        ),
        (
            "roofline_campaign_prague_pilot_llvm.json",
            "prague_staromestske",
            "llvm_ad_rgb",
            "numpy",
            "adaptive_converged",
        ),
        (
            "roofline_campaign_korenmarkt_pilot_llvm_sampled_specular.json",
            "korenmarkt",
            "llvm_ad_rgb",
            "numpy",
            "adaptive_all_specular_sampled_mixed_order_1",
        ),
        (
            "roofline_campaign_korenmarkt_pilot_cuda_sampled_specular.json",
            "korenmarkt",
            "cuda_ad_rgb",
            "drjit",
            "adaptive_all_specular_sampled_mixed_order_1",
        ),
        (
            "roofline_campaign_prague_pilot_cuda_sampled_specular.json",
            "prague_staromestske",
            "cuda_ad_rgb",
            "drjit",
            "adaptive_all_specular_sampled_mixed_order_1",
        ),
    ),
)
def test_shipped_pilot_configs_load(name, site, variant, kernel, acceptance):
    setup = load_roofline_setup(paths.root() / "config" / name)
    assert setup.run.site == site
    assert setup.run.variant == variant
    assert setup.run.transport_kernel == kernel
    assert setup.run.locations == 0
    assert setup.run.rays == 200_000
    assert setup.run.local_cells == 4096
    assert setup.campaign.specular_acceptance == acceptance
    assert setup.source.specular_order == (0 if acceptance == "omitted_diagnostic" else 1)
    if acceptance == "adaptive_all_specular_sampled_mixed_order_1":
        assert setup.campaign.minimum_completed_specular_order == 0
        assert setup.source.specular_suffix_mode == "sampled"
        assert setup.source.sampled_specular_samples == 1
        assert setup.source.sampled_specular_seed_offset == 2000


def test_shipped_cuda_convergence_configs_load():
    configs = (
        ("roofline_campaign_korenmarkt_convergence_cuda_iid.json", "korenmarkt", "iid"),
        (
            "roofline_campaign_korenmarkt_convergence_cuda_rotated_fibonacci.json",
            "korenmarkt",
            "rotated_fibonacci",
        ),
        ("roofline_campaign_prague_convergence_cuda_iid.json", "prague_staromestske", "iid"),
        (
            "roofline_campaign_prague_convergence_cuda_rotated_fibonacci.json",
            "prague_staromestske",
            "rotated_fibonacci",
        ),
    )
    setups = [load_roofline_setup(paths.root() / "config" / name) for name, _, _ in configs]
    assert [setup.run.site for setup in setups] == [site for _, site, _ in configs]
    assert all(setup.run.variant == "cuda_ad_rgb" for setup in setups)
    assert all(setup.run.transport_kernel == "drjit" for setup in setups)
    assert [setup.run.launch_sampling for setup in setups] == [mode for _, _, mode in configs]
    assert all(setup.run.walk == "route" for setup in setups)
    assert all(setup.run.materials == "atlas" for setup in setups)
    assert all(setup.run.max_bounces == 3 for setup in setups)
    assert all(setup.run.rays == 200_000 for setup in setups)
    assert all(setup.run.local_cells == 4096 for setup in setups)
    assert all(setup.campaign.planned_seeds == tuple(range(7, 23)) for setup in setups)
    assert all(setup.campaign.convergence_looks == (4, 8, 12, 16) for setup in setups)
    assert len({setup.campaign.output_dir for setup in setups}) == len(setups)
    assert len({setup.run.tag for setup in setups}) == len(setups)
    for setup in setups:
        assert setup.campaign.specular_acceptance == "adaptive_all_specular_sampled_mixed_order_1"
        assert setup.campaign.minimum_completed_specular_order == 0
        assert setup.source.specular_order == 1
        assert setup.source.specular_suffix_mode == "sampled"
        assert setup.source.sampled_specular_samples == 1
        assert setup.source.sampled_specular_seed_offset == 2000


def test_preparation_builds_sources_from_every_declared_standpoint(monkeypatch, tmp_path):
    mesh = tmp_path / "mesh.ply"
    mesh.write_text("mesh")
    phantom = tmp_path / "duke.stl"
    phantom.write_text("body")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "itu_p2040_4.json").write_text("{}")
    (config_dir / "surface_roughness.json").write_text("{}")
    atlas = tmp_path / "atlas.npz"
    atlas.write_text("atlas")
    atlas.with_suffix(".json").write_text("{}")

    points = np.array(
        [[0.0, 0.0, 1.5], [2.0, 0.0, 1.5], [4.0, 0.0, 1.5], [6.0, 0.0, 1.5]],
        dtype=np.float64,
    )
    walk = Walk(
        points,
        np.zeros(4),
        np.array([0.0, 2.0, 2.0, 2.0]),
        {"point_kind": ["camera_registered"] * 4},
        kind=PANORAMA_LINKS,
        site="korenmarkt",
        body_yaw_deg=np.array([90.0] * 4),
    )
    geometry = SimpleNamespace(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
    )
    scene = SimpleNamespace(mesh=mesh, geometry=geometry, datum_provenance={"rule": "fixture"})
    table = SimpleNamespace(
        permittivity=np.array([4.0 - 0.1j]),
        rms_height_m=np.array([0.001]),
        as_dict=lambda: {"name": "fixture"},
    )
    material = SimpleNamespace(
        face_class=np.array([0]),
        face_source=np.array([1]),
        table=table,
        provenance={"rule": "fixture atlas"},
        atlas_material=object(),
    )
    captured: dict[str, object] = {}

    def build_sources(_geometry, standpoints, _silhouette, **kwargs):
        captured["standpoints"] = np.array(standpoints, copy=True)
        captured["source_options"] = kwargs
        return SimpleNamespace(source_provenance=lambda: {"law": "fixture curve"})

    class Tracer:
        def __init__(self, *args, **kwargs):
            captured["tracer_args"] = args
            captured["tracer_options"] = kwargs

    class Specular:
        def __init__(self, tracer, **kwargs):
            self.tracer = tracer
            captured["specular_options"] = kwargs

    class Estimator:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            captured["estimator"] = self

    class Coupler:
        def __init__(self, *args, **kwargs):
            captured["coupler_args"] = args
            captured["coupler_options"] = kwargs

    backend = PreparationBackend(
        prepare_scene=lambda _run, _environment: scene,
        bind_materials=lambda _run, _scene, _environment: material,
        build_walk=lambda _run, _scene, _environment: walk,
        trace_config=lambda _run, _environment: object(),
        build_sources=build_sources,
        silhouette=lambda: None,
        tracer_type=Tracer,
        specular_type=Specular,
        estimator_type=Estimator,
        coupler_type=Coupler,
    )
    environment = SimpleNamespace(
        phantom=phantom,
        phantom_mass_kg=72.4,
        material_config=config_dir,
        semantics=tmp_path / "unused-semantics.json",
        site_surface_atlas=lambda _site, _crop: atlas,
        site_walk_semantics=lambda _site, _crop: None,
        site_fishnet=lambda _site: None,
    )
    run = RunConfig(
        site="korenmarkt",
        crop_m=250,
        law="roofline",
        estimator="next_event",
        next_event=NextEventConfig(builders=1, held_out=1, azimuths=32, elevations=8),
        walk="route",
        walk_path="links",
        locations=0,
        materials="atlas",
        atlas_npz=str(atlas),
        rays=64,
    )
    campaign = roofline_setup.RooflineCampaignConfig(
        site="korenmarkt",
        cohort="primary_semantic_route",
        material_mode="atlas",
        output_dir=tmp_path / "outputs" / "out",
        planned_seeds=(7,),
    )
    setup_file = tmp_path / "campaign.json"
    setup_file.write_text("{}")
    setup = RooflineSetupConfig(tmp_path, run, campaign, setup_file=setup_file)
    monkeypatch.setattr(roofline_setup, "seal_transport_provenance", lambda _value: {"transport": "sealed"})
    monkeypatch.setattr(roofline_setup, "seal_coupler_provenance", lambda _value: {"body": "sealed"})
    monkeypatch.setattr(roofline_setup, "PreparedRooflineCampaign", lambda **kwargs: SimpleNamespace(**kwargs))

    prepared = prepare_roofline_campaign(setup, environment, backend=backend)
    np.testing.assert_array_equal(captured["standpoints"], points)
    assert captured["source_options"]["azimuths"] == 32
    assert prepared.walk is walk
    assert prepared.estimator.sources.source_provenance() == {"law": "fixture curve"}
    assert prepared.estimator.deterministic_cache_size == 12
    staged = {record["path"] for record in prepared.input_provenance["files"]}
    assert "atlas.npz" in staged
    assert "atlas.json" in staged
    assert "campaign.json" in staged
    assert prepared.input_provenance["source_standpoint_contract"]["random_builder_evaluation_split"] is False


def test_preflight_reports_work_and_checkpoint_bound(monkeypatch):
    class Sized(SimpleNamespace):
        def __len__(self):
            return int(self.size)

    work = SimpleNamespace(enabled=True, reason=None, as_dict=lambda: {"enabled": True, "candidates": 12})
    transport = SimpleNamespace(
        work_estimate=lambda **_kwargs: work,
        surfaces=SimpleNamespace(triangles=np.zeros((3, 3, 3))),
    )
    tracer = SimpleNamespace(config=SimpleNamespace(max_bounces=3, rays=64))
    sources = Sized(
        size=2,
        support_length_m=20.0,
        crop_area_m2=100.0,
        source_hash="hash",
    )
    estimator = SimpleNamespace(
        tracer=tracer,
        max_order=3,
        samples=1,
        specular_transport=transport,
        specular_order=1,
        specular_candidate_budget=100,
        specular_refinement_relative_tolerance=0.02,
        visible_face_candidates=SimpleNamespace(sample_levels=(2,)),
        source_quadrature=SimpleNamespace(strata_levels=(1,)),
        sources=sources,
    )
    walk = Sized(
        size=3,
        identity=lambda: {"standpoints": 3},
        provenance={"point_kind": ["camera_registered"] * 3},
        step_m=np.array([0.0, 2.0, 2.0]),
    )
    config = SimpleNamespace(
        site="korenmarkt",
        cohort="primary_semantic_route",
        material_mode="atlas",
        convergence_looks=(1, 2),
        planned_seeds=(7, 8, 9),
        output_dir="out",
        specular_acceptance="exact_complete",
    )
    prepared = SimpleNamespace(
        config=config,
        estimator=estimator,
        coupler=SimpleNamespace(body=SimpleNamespace(areas=np.ones(10))),
        walk=walk,
        input_provenance={"files": []},
        material_provenance={"material_mode": "atlas", "binding": {"covered_fraction_by_area": 0.8}},
    )
    monkeypatch.setattr(roofline_setup, "campaign_identity", lambda _prepared: "campaign-hash")
    report = preflight_report(prepared)
    assert report["ready_to_trace"] is True
    assert report["specular_work"]["candidates"] == 12
    assert report["checkpoint_storage_bound"]["body_field_bytes_each"] == 240
    assert report["checkpoint_storage_bound"]["body_field_bytes_total_uncompressed"] == 720


def test_cli_dry_run_writes_manifests_without_tracing(monkeypatch, tmp_path):
    output = tmp_path / "out"
    setup = SimpleNamespace(
        study_root=paths.root().resolve(),
        campaign=SimpleNamespace(output_dir=output),
    )
    prepared = object()
    report = {
        "ready_to_trace": True,
        "campaign_identity": "identity",
        "staged_inputs": {"staging_contract": "fixture", "files": []},
    }
    monkeypatch.setattr(command, "load_roofline_setup", lambda *_args, **_kwargs: setup)
    monkeypatch.setattr(command, "prepare_roofline_campaign", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(command, "preflight_report", lambda value: report if value is prepared else None)
    traced = []
    monkeypatch.setattr(command, "run_roofline_campaign", lambda value: traced.append(value))
    args = argparse.Namespace(
        config=tmp_path / "config.json",
        study_root=None,
        dry_run=True,
        preflight_output=None,
        staging_manifest=None,
    )
    assert command.run(args, environment=object()) == 0
    assert traced == []
    assert json.loads((output / "preflight.json").read_text()) == report
    staging = json.loads((output / "staged_inputs.json").read_text())
    assert staging["campaign_identity"] == "identity"
    assert staging["staging_contract"] == "fixture"


@pytest.mark.parametrize(
    "name",
    (
        "roofline_campaign_korenmarkt_pilot_llvm.json",
        "roofline_campaign_korenmarkt_pilot_cuda.json",
        "roofline_campaign_prague_pilot_llvm.json",
        "roofline_campaign_korenmarkt_pilot_llvm_sampled_specular.json",
    ),
)
def test_every_shipped_pilot_runs_through_dry_run_command(monkeypatch, tmp_path, name):
    prepared = object()
    report = {
        "ready_to_trace": True,
        "campaign_identity": name,
        "staged_inputs": {"staging_contract": "fixture", "files": []},
    }
    monkeypatch.setattr(command, "prepare_roofline_campaign", lambda *_args, **_kwargs: prepared)
    monkeypatch.setattr(command, "preflight_report", lambda value: report if value is prepared else None)
    traced = []
    monkeypatch.setattr(command, "run_roofline_campaign", lambda value: traced.append(value))
    args = command.arguments(
        [
            "--config",
            str(paths.root() / "config" / name),
            "--dry-run",
            "--preflight-output",
            str(tmp_path / f"{name}.preflight.json"),
            "--staging-manifest",
            str(tmp_path / f"{name}.staging.json"),
        ]
    )
    assert command.run(args, environment=object()) == 0
    assert traced == []
    assert json.loads((tmp_path / f"{name}.preflight.json").read_text()) == report


def test_cli_dry_run_records_preparation_refusal(monkeypatch, tmp_path):
    output = tmp_path / "out"
    setup = SimpleNamespace(
        study_root=paths.root().resolve(),
        campaign=SimpleNamespace(output_dir=output),
    )
    monkeypatch.setattr(command, "load_roofline_setup", lambda *_args, **_kwargs: setup)
    monkeypatch.setattr(
        command,
        "prepare_roofline_campaign",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("missing exact atlas")),
    )
    args = argparse.Namespace(
        config=tmp_path / "config.json",
        study_root=None,
        dry_run=True,
        preflight_output=None,
        staging_manifest=None,
    )
    assert command.run(args, environment=object()) == 2
    failure = json.loads((output / "preflight.json").read_text())
    assert failure["ready_to_trace"] is False
    assert "missing exact atlas" in failure["refusal_reason"]
    assert not (output / "staged_inputs.json").exists()
