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
from semantic_twin.report import current_topology_convergence as report_module
from semantic_twin.report.current_topology_convergence import (
    EXPECTED_LOOKS,
    EXPECTED_SITES,
    EXTENDED_SEEDS,
    SHADOW_STANDPOINTS,
    CurrentTopologyConvergenceError,
    compare_current_topology_campaigns,
    write_current_topology_convergence,
)
from semantic_twin.report.roofline_campaign_comparison import _Campaign

POINTS = {
    "korenmarkt": 10,
    "prague_staromestske": 22,
    "madrid_plazamayor": 14,
    "mexico_zocalo": 11,
    "tokyo_hachiko": 16,
}

EXTENSION_SITES = (
    "brussels_grandplace",
    "london_trafalgar",
    "milan_duomo",
    "krakow_rynek",
    "toulouse_capitole",
)


def test_ten_city_route_extension_configs_match_the_sealed_production_contract() -> None:
    root = Path(__file__).parents[1]
    expected_seeds = list(range(7, 71))
    for site in EXTENSION_SITES:
        path = (
            root / "config" / f"roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_"
            "extension64_cuda_iid.json"
        )
        document = json.loads(path.read_text())
        run = document["run"]
        campaign = document["campaign"]
        source = document["source"]
        assert run["site"] == campaign["site"] == site
        assert run["walk_path"] == "provider_corridor"
        assert run["materials"] == campaign["material_mode"] == "atlas"
        assert run["rays"] == 200_000
        assert run["local_cells"] == 4096
        assert run["max_bounces"] == 1
        assert campaign["route_contract"] == "provider_corridor_v1"
        assert campaign["planned_seeds"] == expected_seeds
        assert campaign["convergence_looks"] == [16, 24, 32, 48, 64]
        assert campaign["specular_acceptance"] == "first_material_interaction_exact_order_1"
        assert campaign["transport_topology"] == "first_material_interaction_v1"
        expected_budget = {
            "london_trafalgar": 500_000_000,
            "milan_duomo": 400_000_000,
        }.get(site, 320_000_000)
        assert source["specular_candidate_budget"] == expected_budget
        assert source["specular_suffix_mode"] == "disabled"


def _identity(site: str, extended: bool) -> dict[str, object]:
    seeds = list(range(7, 71)) if extended else list(range(7, 23))
    looks = list(EXPECTED_LOOKS) if extended else [4, 8, 12, 16]
    name = (
        f"config/roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_"
        f"convergence{'64' if extended else ''}_cuda_iid.json"
    )
    files = [
        {"path": "config/city_cohort_manifest.json", "sha256": "a" * 64, "bytes": 10},
        {"path": f"data/geometry/{site}/mesh.ply", "sha256": "b" * 64, "bytes": 20},
        {"path": name, "sha256": ("c" if extended else "d") * 64, "bytes": 30 if extended else 25},
    ]
    return {
        "configuration": {
            "site": site,
            "planned_seeds": seeds,
            "convergence_looks": looks,
            "material_mode": "atlas",
            "reference_mode": "per_density_eirp",
            "route_contract": "provider_corridor_v1",
            "minimum_completed_specular_order": 1,
            "specular_acceptance": "first_material_interaction_exact_order_1",
            "transport_topology": "first_material_interaction_v1",
        },
        "inputs": {"files": files, "file_count": len(files), "bytes": sum(item["bytes"] for item in files)},
        "transport": {
            "tracer": {
                "configuration": {
                    "launch_sampling": "iid",
                    "rays": 200_000,
                    "local_cells": 4096,
                    "frequency_hz": 15_000_000_000,
                    "max_bounces": 1,
                }
            },
            "estimator": {"configuration": {"specular_suffix_mode": "disabled"}},
        },
        "body": {"phantom": "duke", "surface_elements": 56_024, "frequency_hz": 15_000_000_000.0},
        "sources": {"source_measure_rule": "physical_3d_edge_length"},
    }


def _campaign(tmp_path: Path, site: str, extended: bool) -> _Campaign:
    seeds = EXTENDED_SEEDS if extended else tuple(range(7, 23))
    points = POINTS[site]
    raw = np.zeros((len(seeds), points, len(FIRST_MATERIAL_INTERACTION_COMPONENTS)), dtype=np.float64)
    shadow = set(SHADOW_STANDPOINTS.get(site, ()))
    site_scale = 1.0 + EXPECTED_SITES.index(site) * 0.2
    for replica in range(len(seeds)):
        fluctuation = 1.0 + 0.04 * np.sin(replica + np.arange(points))
        raw[replica, :, 0] = [0.0 if point in shadow else site_scale * (1.0 + point / 20) for point in range(points)]
        raw[replica, :, 1] = [0.0 if point in shadow else site_scale * 0.2 for point in range(points)]
        raw[replica, :, 2] = site_scale * 0.03 * fluctuation
        raw[replica, :, 3] = np.sum(raw[replica, :, :3], axis=1)
    body = np.zeros((len(seeds), points, len(FIRST_MATERIAL_INTERACTION_COMPONENTS), len(BODY_METRICS)))
    factors = np.arange(1, len(BODY_METRICS) + 1, dtype=np.float64)
    body[:] = raw[:, :, :, None] * factors
    timings = np.full((len(seeds), points, len(TIMING_FIELDS)), 0.01, dtype=np.float64)
    root = tmp_path / ("extended" if extended else "sealed") / site
    root.mkdir(parents=True)
    (root / "campaign_identity.json").write_text(json.dumps({"sha256": ("1" if extended else "2") * 64}))
    (root / "manifest.json").write_text("{}\n")
    return _Campaign(
        root=root,
        identity={"sha256": ("1" if extended else "2") * 64},
        identity_data=_identity(site, extended),
        sampling="iid",
        manifest={},
        checkpoint={
            "schema_version": FIRST_MATERIAL_INTERACTION_SCHEMA_VERSION,
            "components": list(FIRST_MATERIAL_INTERACTION_COMPONENTS),
            "committed": [],
        },
        seeds=seeds,
        points=points,
        locations=tuple(
            {"standpoint": point, "position_m": [float(point), 0.0, 1.5], "body_yaw_deg": 90.0}
            for point in range(points)
        ),
        raw_transfer=raw,
        body_metrics=body,
        timings=timings,
        diagnostics=tuple(tuple({} for _ in range(points)) for _ in seeds),
        all_specular_transfer=raw[:, :, 1],
        suffix_transfer=None,
    )


@pytest.fixture
def campaign_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    extended = {site: _campaign(tmp_path, site, True) for site in EXPECTED_SITES}
    sealed = {site: _campaign(tmp_path, site, False) for site in EXPECTED_SITES}
    paths = {
        **{Path(f"extended-{site}"): campaign for site, campaign in extended.items()},
        **{Path(f"sealed-{site}"): campaign for site, campaign in sealed.items()},
    }
    loaded: list[Path] = []

    def load(path):
        loaded.append(Path(path))
        return paths[Path(path)]

    monkeypatch.setattr(report_module, "_load_campaign", load)
    monkeypatch.setattr(
        report_module,
        "_prefix_parity",
        lambda _extended, _sealed: {"status": "pass", "replicas": 16, "seeds": list(range(7, 23))},
    )
    extended_paths = {site: Path(f"extended-{site}") for site in EXPECTED_SITES}
    sealed_paths = {site: Path(f"sealed-{site}") for site in EXPECTED_SITES}
    return extended, sealed, extended_paths, sealed_paths, loaded


def test_report_covers_all_looks_components_points_strata_bootstrap_timing_and_gates(campaign_set) -> None:
    extended, sealed, extended_paths, sealed_paths, loaded = campaign_set
    peak_index = BODY_METRICS.index("peak_sab_w_m2")
    for campaigns in (extended, sealed):
        for campaign in campaigns.values():
            campaign.body_metrics[:, :, -1, peak_index] += 99.0

    report = compare_current_topology_campaigns(
        extended_paths, sealed_paths, bootstrap_replicates=100, bootstrap_seed=11
    )

    assert len(loaded) == 10
    assert report["authentication"] == {
        "status": "pass",
        "campaigns_authenticated": 10,
        "method": "identity wrapper, manifest, checkpoint, shard hash, schema, route, and seed checks",
    }
    assert report["strata"]["six_shadowed_points"]["standpoints"] == 6
    assert report["strata"]["67_nonshadowed_points"]["standpoints"] == 67
    assert set(report["sites"]["mexico_zocalo"]["looks"]) == {str(look) for look in EXPECTED_LOOKS}
    look64 = report["sites"]["mexico_zocalo"]["looks"]["64"]
    assert set(look64["components"]) == set(FIRST_MATERIAL_INTERACTION_COMPONENTS)
    assert set(look64["components"]["total"]["wbsar_m2_per_kg"]["route_quantiles"]) == {
        "q10",
        "q50",
        "q90",
    }
    assert look64["components"]["total"]["wbsar_m2_per_kg"]["whole_replica_bootstrap"]["replicates"] == 100
    assert len(look64["pointwise"]["total_transfer_m_inv2"]["estimate"]) == 11
    assert report["sites"]["korenmarkt"]["timing"]["looks"]["64"]["nonoverlapping_observed_compute_seconds"] > 0.0
    assert report["sites"]["tokyo_hachiko"]["closure"]["extended"]["status"] == "pass"
    assert report["sites"]["tokyo_hachiko"]["closure"]["extended"]["nonadditive_body_metrics_excluded"] == {
        "peak_sab_w_m2": "the peak of a summed body field is not the sum of component-field peaks"
    }
    assert report["promotion_gates"]["decision"] == "not_promoted_pending_author_judgment"
    assert report["lower_tail_assessment"]["mexico_zocalo"]["status"] in {
        "stabilized",
        "stabilized_with_rare_event_behavior",
        "remains_uncertain",
        "rare_event_behavior",
    }


def test_tail_status_preserves_rare_event_behavior_when_aggregate_criteria_pass() -> None:
    assert report_module._tail_status({"a": True, "b": True}, rare=True) == ("stabilized_with_rare_event_behavior")
    assert report_module._tail_status({"a": True, "b": True}, rare=False) == "stabilized"


def test_common_input_change_outside_plan_allowlist_is_rejected(campaign_set) -> None:
    extended, _sealed, extended_paths, sealed_paths, _loaded = campaign_set
    extended["madrid_plazamayor"].identity_data["sources"]["source_measure_rule"] = "horizontal_projection"

    with pytest.raises(CurrentTopologyConvergenceError, match="outside the plan allowlist: madrid"):
        compare_current_topology_campaigns(extended_paths, sealed_paths, bootstrap_replicates=100)


def test_closure_applies_relative_tolerance_to_component_sum(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path, "mexico_zocalo", True)
    mean_index = BODY_METRICS.index("mean_sab_w_m2")
    campaign.body_metrics[0, 0, -1, mean_index] += 1.4e-14

    closure = report_module._closure(campaign)

    assert closure["body_metric_max_abs_residual"] > 1.0e-14
    assert closure["body_metrics_pass"] is True
    assert closure["status"] == "pass"


def test_exact_prefix_parity_rejects_any_non_timing_shard_change(tmp_path: Path) -> None:
    extended = _campaign(tmp_path, "korenmarkt", True)
    sealed = _campaign(tmp_path, "korenmarkt", False)
    for campaign, different_timing in ((extended, True), (sealed, False)):
        checkpoint = campaign.root / "checkpoint"
        (checkpoint / "replicas").mkdir(parents=True)
        committed = []
        for replica, seed in enumerate(range(7, 23)):
            npz = checkpoint / "replicas" / f"seed_{seed}.npz"
            marker = np.array([replica], dtype=np.float64)
            np.savez(npz, raw_transfer=marker, timings=np.array([99.0 if different_timing else 1.0]))
            diagnostic = checkpoint / "replicas" / f"seed_{seed}.json"
            diagnostic.write_text(json.dumps({"accepted": replica, "wall_seconds": 99.0 if different_timing else 1.0}))
            committed.append(
                {"seed": seed, "path": f"replicas/{npz.name}", "diagnostics_path": f"replicas/{diagnostic.name}"}
            )
        campaign.checkpoint["committed"] = committed

    assert report_module._prefix_parity(extended, sealed)["status"] == "pass"
    changed_path = extended.root / "checkpoint" / "replicas" / "seed_11.npz"
    np.savez(changed_path, raw_transfer=np.array([999.0]), timings=np.array([99.0]))
    with pytest.raises(CurrentTopologyConvergenceError, match="scientific sealed-prefix parity failed"):
        report_module._prefix_parity(extended, sealed)


def test_writer_emits_json_csv_pdf_png_and_authenticated_manifest(campaign_set, tmp_path: Path) -> None:
    extended, sealed, extended_paths, sealed_paths, _loaded = campaign_set
    actual_extended = {site: campaign.root for site, campaign in extended.items()}
    actual_sealed = {site: campaign.root for site, campaign in sealed.items()}
    path_map = {
        **{path: extended[site] for site, path in actual_extended.items()},
        **{path: sealed[site] for site, path in actual_sealed.items()},
    }
    report_module._load_campaign = lambda path: path_map[Path(path)]

    artifacts = write_current_topology_convergence(
        actual_extended,
        actual_sealed,
        tmp_path / "report",
        bootstrap_replicates=100,
        bootstrap_seed=12,
    )

    assert all(path.is_file() for path in vars(artifacts).values())
    manifest = json.loads(artifacts.manifest.read_text())
    assert len(manifest["source_campaigns"]) == 10
    assert {record["path"] for record in manifest["files"]} == {
        artifacts.json.name,
        artifacts.csv.name,
        artifacts.pdf.name,
        artifacts.png.name,
    }
    assert all(len(record["sha256"]) == 64 for record in manifest["files"])


def test_shipped_convergence64_configs_change_only_identity_plan_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    for site in EXPECTED_SITES:
        prefix = f"roofline_campaign_{site}_provider_corridor_v1_first_material_interaction_v1_convergence"
        sealed = json.loads((root / "config" / f"{prefix}_cuda_iid.json").read_text())
        extended = json.loads((root / "config" / f"{prefix}64_cuda_iid.json").read_text())
        sealed_normal = copy.deepcopy(sealed)
        extended_normal = copy.deepcopy(extended)
        for document in (sealed_normal, extended_normal):
            document["run"].pop("tag")
            document["campaign"].pop("output_dir")
            document["campaign"].pop("planned_seeds")
            document["campaign"].pop("convergence_looks")
        assert extended_normal == sealed_normal
        assert extended["campaign"]["planned_seeds"] == list(range(7, 71))
        assert extended["campaign"]["convergence_looks"] == list(EXPECTED_LOOKS)
        assert extended["campaign"]["output_dir"] == f"outputs/experiments/current_topology_convergence64_v1/{site}"
        assert extended["run"]["max_bounces"] == 1
        assert extended["campaign"]["transport_topology"] == "first_material_interaction_v1"
