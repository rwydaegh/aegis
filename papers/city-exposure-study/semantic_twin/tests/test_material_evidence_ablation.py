from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    FIRST_MATERIAL_INTERACTION_COMPONENTS,
    FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
    TIMING_FIELDS,
)
from semantic_twin.exposure.roofline_setup import load_roofline_setup
from semantic_twin.report import material_evidence_ablation as report_module
from semantic_twin.report.material_evidence_ablation import (
    ABLATION_LABEL,
    IDENTITY_ALLOWLIST,
    MaterialEvidenceAblationError,
    compare_material_campaigns,
    write_material_evidence_ablation,
)
from semantic_twin.report.roofline_campaign_comparison import _Campaign


def _identity(mode: str) -> dict[str, object]:
    site = "fixture_square"
    config_name = (
        f"config/roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_"
        f"convergence_cuda_iid{'_geometric_control' if mode == 'geometric' else ''}.json"
    )
    files = [
        {"path": "config/city_cohort_manifest.json", "sha256": "a" * 64, "bytes": 10},
        {"path": "data/geometry/fixture_square/mesh.ply", "sha256": "b" * 64, "bytes": 20},
        {"path": config_name, "sha256": ("c" if mode == "atlas" else "d") * 64, "bytes": 30},
    ]
    if mode == "atlas":
        files.extend(
            [
                {
                    "path": "outputs/site_semantics/fixture_square/joint_atlas_250m_r8.npz",
                    "sha256": "e" * 64,
                    "bytes": 40,
                },
                {
                    "path": "outputs/site_semantics/fixture_square/joint_atlas_250m_r8.json",
                    "sha256": "f" * 64,
                    "bytes": 50,
                },
            ]
        )
    return {
        "configuration": {
            "site": site,
            "material_mode": mode,
            "planned_seeds": [7, 8, 9],
            "reference_mode": "per_density_eirp",
            "transport_topology": "first_material_interaction_v1",
        },
        "materials": {
            "material_mode": mode,
            "binding": "joint atlas" if mode == "atlas" else "geometric classes",
            "face_class_sha256": ("1" if mode == "atlas" else "2") * 64,
        },
        "inputs": {
            "files": files,
            "file_count": len(files),
            "bytes": sum(record["bytes"] for record in files),
            "mesh": "data/geometry/fixture_square/mesh.ply",
            "ground_datum": {"level_m": 1.0},
        },
        "transport": {
            "tracer": {
                "configuration": {"rays": 200_000, "local_cells": 4096, "frequency_hz": 15e9},
                "geometry": {"faces_sha256": "3" * 64, "vertices_sha256": "4" * 64},
                "atlas_material": {"supported_sha256": "5" * 64} if mode == "atlas" else None,
                "face_class_sha256": ("6" if mode == "atlas" else "7") * 64,
                "permittivity_sha256": ("8" if mode == "atlas" else "9") * 64,
                "rms_height_sha256": ("a" if mode == "atlas" else "b") * 64,
            },
            "estimator": {
                "configuration": {
                    "max_order": 1,
                    "specular_transport": {
                        "support_complete": True,
                        "triangles_sha256": "c" * 64,
                        "material_class_sha256": ("d" if mode == "atlas" else "e") * 64,
                    },
                }
            },
        },
        "sources": {"curve_sha256": "f" * 64, "source_measure_rule": "physical_3d_edge_length"},
        "body": {"phantom": "duke", "surface_elements": 56_024},
        "walk": {"points_sha256": "0" * 64, "body_yaw_sha256": "1" * 64},
    }


def _campaign(tmp_path: Path, mode: str) -> _Campaign:
    seeds = (7, 8, 9)
    points = 3
    components = len(FIRST_MATERIAL_INTERACTION_COMPONENTS)
    raw = np.zeros((len(seeds), points, components), dtype=np.float64)
    scale = 1.08 if mode == "atlas" else 1.0
    for replica in range(len(seeds)):
        raw[replica, :, 0] = np.array([1.0, 0.0, 2.0])
        raw[replica, :, 1] = scale * np.array([0.2, 0.1, 0.4])
        raw[replica, :, 2] = scale * np.array([0.03, 0.2, 0.06]) * (1.0 + 0.01 * replica)
        raw[replica, :, 3] = np.sum(raw[replica, :, :3], axis=1)
    body = np.zeros((len(seeds), points, components, len(BODY_METRICS)), dtype=np.float64)
    for component in range(components):
        body[:, :, component, :] = raw[:, :, component, None] * np.arange(1, len(BODY_METRICS) + 1)
    timings = np.full((len(seeds), points, len(TIMING_FIELDS)), 0.01, dtype=np.float64)
    identity_data = _identity(mode)
    return _Campaign(
        root=tmp_path / mode,
        identity={"sha256": ("2" if mode == "atlas" else "3") * 64},
        identity_data=identity_data,
        sampling="iid",
        manifest={},
        checkpoint={
            "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
            "components": list(FIRST_MATERIAL_INTERACTION_COMPONENTS),
        },
        seeds=seeds,
        points=points,
        locations=tuple(
            {"standpoint": index, "position_m": [float(index), 0.0, 1.5], "body_yaw_deg": 90.0}
            for index in range(points)
        ),
        raw_transfer=raw,
        body_metrics=body,
        timings=timings,
        diagnostics=tuple(tuple({} for _ in range(points)) for _ in seeds),
        all_specular_transfer=None,
        suffix_transfer=None,
    )


@pytest.fixture
def paired_campaigns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[_Campaign, _Campaign]:
    atlas = _campaign(tmp_path, "atlas")
    geometric = _campaign(tmp_path, "geometric")
    campaigns = {Path("atlas"): atlas, Path("geometric"): geometric}
    monkeypatch.setattr(report_module, "_load_campaign", lambda path: campaigns[Path(path)])
    return atlas, geometric


def test_current_contract_pair_reports_metrics_components_strata_and_uncertainty(paired_campaigns) -> None:
    report = compare_material_campaigns("atlas", "geometric")

    assert report["ablation"] == ABLATION_LABEL
    assert report["compatibility"]["status"] == "pass"
    assert report["compatibility"]["allowlist"] == list(IDENTITY_ALLOWLIST)
    assert report["standpoints"] == 3
    assert report["direct_strata"]["direct_visible_in_both"]["indices"] == [0, 2]
    assert report["direct_strata"]["zero_direct_in_both"]["indices"] == [1]
    assert report["paired_seed_uncertainty"]["total_transfer_m_inv2"]["status"] == "available"
    assert set(report["component_decomposition"]) == set(FIRST_MATERIAL_INTERACTION_COMPONENTS)
    assert report["metrics"]["total_transfer_m_inv2"]["route_quantile_change_db"]["q50"] > 0.0


def test_identity_change_outside_closed_allowlist_is_rejected(paired_campaigns) -> None:
    _atlas, geometric = paired_campaigns
    geometric.identity_data["transport"]["tracer"]["configuration"]["rays"] = 100_000

    with pytest.raises(MaterialEvidenceAblationError, match="outside the material allowlist.*rays"):
        compare_material_campaigns("atlas", "geometric")


def test_route_change_is_rejected_before_numerical_comparison(paired_campaigns) -> None:
    _atlas, geometric = paired_campaigns
    changed = list(geometric.locations)
    changed[1] = {**changed[1], "body_yaw_deg": 91.0}
    object.__setattr__(geometric, "locations", tuple(changed))

    with pytest.raises(MaterialEvidenceAblationError, match="route position, ground, yaw, or order"):
        compare_material_campaigns("atlas", "geometric")


def test_report_writer_emits_all_authenticated_artifacts(paired_campaigns, tmp_path: Path) -> None:
    artifacts = write_material_evidence_ablation("atlas", "geometric", tmp_path / "report")

    assert all(path.is_file() for path in vars(artifacts).values())
    manifest = json.loads(artifacts.manifest.read_text(encoding="utf-8"))
    assert {record["path"] for record in manifest["files"]} == {
        artifacts.json.name,
        artifacts.csv.name,
        artifacts.pdf.name,
        artifacts.png.name,
    }
    assert all(len(record["sha256"]) == 64 for record in manifest["files"])


def test_shipped_geometric_controls_change_only_declared_setup_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    for site in ("madrid_plazamayor", "mexico_zocalo"):
        prefix = f"roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid"
        atlas = json.loads((root / "config" / f"{prefix}.json").read_text(encoding="utf-8"))
        geometric = json.loads((root / "config" / f"{prefix}_geometric_control.json").read_text(encoding="utf-8"))
        atlas_normal = copy.deepcopy(atlas)
        geometric_normal = copy.deepcopy(geometric)
        for document in (atlas_normal, geometric_normal):
            document["run"].pop("materials")
            document["run"].pop("tag")
            document["run"].pop("atlas_npz", None)
            document["campaign"].pop("material_mode")
            document["campaign"].pop("output_dir")
        assert atlas_normal == geometric_normal
        assert geometric["run"]["materials"] == "geometric"
        assert geometric["campaign"]["material_mode"] == "geometric"


@pytest.mark.local_data
def test_shipped_geometric_controls_load_against_local_route_evidence() -> None:
    root = Path(__file__).resolve().parents[1]
    for site in ("madrid_plazamayor", "mexico_zocalo"):
        prefix = f"roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid"
        setup = load_roofline_setup(root / "config" / f"{prefix}_geometric_control.json")
        assert setup.run.materials == "geometric"
        assert setup.campaign.material_mode == "geometric"
        assert setup.campaign.transport_topology == "first_material_interaction_v1"


@pytest.mark.local_data
def test_pulled_madrid_campaign_pair_passes_real_artifact_authentication() -> None:
    root = Path(__file__).resolve().parents[1]
    campaign_root = root / "outputs" / "roofline_campaign"
    atlas = campaign_root / "madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid"
    geometric = campaign_root / (
        "madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control"
    )
    if not geometric.is_dir():
        pytest.skip("pulled Madrid geometric campaign is not present")

    report = compare_material_campaigns(atlas, geometric)

    assert report["site"] == "madrid_plazamayor"
    assert report["standpoints"] == 14
    assert report["seeds"] == list(range(7, 23))
    assert report["compatibility"]["status"] == "pass"
    assert report["component_decomposition"]["direct"]["total_transfer_m_inv2"]["pointwise_change_db_quantiles"] == {
        "q10": 0.0,
        "q50": 0.0,
        "q90": 0.0,
    }
