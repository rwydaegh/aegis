"""Contract and read-only readiness tests for the ten-city cohort."""

from __future__ import annotations

import json

import numpy as np
import pytest

from semantic_twin import cohort as cohort_contract
from semantic_twin import paths
from semantic_twin.cohort import (
    COMPARABLE_COHORT,
    EXCLUDED_SITE,
    INCLUDED_SITES,
    REGISTERED_SPAN_STREET,
    CohortManifestError,
    campaign_readiness,
    expected_route_cache,
    load_manifest,
    material_readiness,
    route_readiness,
    validate_manifest,
    validate_study_membership,
)
from semantic_twin.walk.links import LinkGraph
from semantic_twin.walk.provider_corridor import PROVIDER_CORRIDOR_V1


def _entry(manifest, site="korenmarkt"):
    return next(item for item in manifest["included_sites"] if item["site"] == site)


def _stage_route_inputs(root, entry, monkeypatch):
    site = entry["site"]
    report = root / entry["route"]["admitted_station_report"]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "stations_admitted": [
                    {"station": "a", "position_enu_m": [-10.0, 0.0, 2.5]},
                    {"station": "middle", "position_enu_m": [0.0, 2.0, 2.5]},
                    {"station": "b", "position_enu_m": [20.0, 0.0, 2.5]},
                ]
            }
        )
    )
    geometry = root / "data" / "geometry" / site
    geometry.mkdir(parents=True, exist_ok=True)
    mesh = geometry / "inhouse_leaf_250m_f64.ply"
    mesh.write_text("ply\n")
    mesh.with_suffix(".json").write_text(json.dumps({"format_version": 3, "anchor": {"lat_deg": 51.0, "lon_deg": 3.0}}))
    paths.forget_disk_reads()
    monkeypatch.setattr(
        cohort_contract,
        "admitted_route_positions",
        lambda *_args, **_kwargs: np.array([[-10.0, 0.0, 2.5], [0.0, 2.0, 2.5], [20.0, 0.0, 2.5]], dtype=np.float64),
    )
    cache, waypoints = expected_route_cache(entry, root)
    return report, cache, waypoints


def _write_exact_cache(cache, site, waypoints):
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(
            {
                "site": site,
                "distance_m": 30.0,
                "polyline_llh": [waypoints[0], waypoints[1]],
                "waypoints_llh": waypoints,
                "optimised": False,
                "source": "fixture",
            }
        )
    )


def _stage_atlas(root, entry):
    for key in ("atlas_npz", "atlas_json"):
        path = root / entry["materials"][key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"atlas")


def test_manifest_names_toulouse_and_krakow_but_excludes_times_square():
    manifest = load_manifest()

    assert tuple(entry["site"] for entry in manifest["included_sites"]) == INCLUDED_SITES
    assert "toulouse_capitole" in INCLUDED_SITES
    assert tuple(entry["site"] for entry in manifest["excluded_sites"]) == (EXCLUDED_SITE,)
    assert manifest["excluded_sites"][0]["reason_code"] == "invalid_geometry"
    assert _entry(manifest, "krakow_rynek")["membership"]["input_status"] == "pending_panorama_acquisition"


def test_manifest_separates_membership_route_and_material_contracts():
    manifest = load_manifest()

    for entry in manifest["included_sites"]:
        assert entry["membership"]["cohort"] == COMPARABLE_COHORT
        assert entry["route"]["contract"] == REGISTERED_SPAN_STREET
        assert entry["route"]["coordinate_policy"] == "registered_span_endpoints"
        assert entry["materials"]["primary_mode"] == "atlas"
        assert entry["materials"]["allowed_modes"] == ["atlas", "geometric"]
        assert not {"waypoints", "coordinates", "cache_glob"} & entry["route"].keys()


def test_validation_rejects_membership_route_and_material_drift_independently():
    manifest = load_manifest()
    manifest["included_sites"][0]["membership"]["cohort"] = "other"
    with pytest.raises(CohortManifestError, match="wrong study cohort"):
        validate_manifest(manifest)

    manifest = load_manifest()
    manifest["included_sites"][0]["route"]["endpoint_policy"] = "all"
    with pytest.raises(CohortManifestError, match="endpoint_policy"):
        validate_manifest(manifest)

    manifest = load_manifest()
    manifest["included_sites"][0]["materials"]["primary_mode"] = "geometric"
    with pytest.raises(CohortManifestError, match="primary material mode"):
        validate_manifest(manifest)


def test_membership_refuses_times_square_and_wrong_legacy_cohort():
    manifest = load_manifest()
    with pytest.raises(CohortManifestError, match="excluded"):
        validate_study_membership(EXCLUDED_SITE, COMPARABLE_COHORT, manifest)
    with pytest.raises(CohortManifestError, match="not a member"):
        validate_study_membership("korenmarkt", "geometric_transfer_extension", manifest)


def test_route_readiness_requires_admitted_report_before_any_cache(tmp_path):
    manifest = load_manifest()
    status = route_readiness(manifest, root=tmp_path)[0]

    assert not status.ready
    assert status.missing == ("outputs/site_semantics/korenmarkt/walk_semantic_250m.json",)
    assert status.expected_cache is None
    assert not (tmp_path / "data" / "street_routes").exists()


def test_route_readiness_accepts_only_the_exact_endpoint_key(monkeypatch, tmp_path):
    manifest = load_manifest()
    entry = _entry(manifest)
    report, cache, waypoints = _stage_route_inputs(tmp_path, entry, monkeypatch)
    wrong = cache.with_name(f"{entry['site']}_0000000000000000.json")
    _write_exact_cache(wrong, entry["site"], waypoints)

    status = route_readiness(manifest, root=tmp_path)[0]
    assert not status.ready
    assert status.evidence == (str(report.relative_to(tmp_path)),)
    assert status.missing == (str(cache.relative_to(tmp_path)),)
    assert status.expected_cache == str(cache.relative_to(tmp_path))

    _write_exact_cache(cache, entry["site"], waypoints)
    status = route_readiness(manifest, root=tmp_path)[0]
    assert status.ready
    assert status.evidence == (str(report.relative_to(tmp_path)), str(cache.relative_to(tmp_path)))
    assert str(wrong.relative_to(tmp_path)) not in status.evidence

    explicit_legacy = route_readiness(manifest, root=tmp_path, route_contract=REGISTERED_SPAN_STREET)[0]
    assert json.dumps(explicit_legacy.as_dict(), sort_keys=True) == json.dumps(status.as_dict(), sort_keys=True)


def test_provider_corridor_readiness_is_opt_in_and_report_hash_invalidates_seal(monkeypatch, tmp_path):
    manifest = load_manifest()
    entry = _entry(manifest)
    report = tmp_path / entry["route"]["admitted_station_report"]
    report.parent.mkdir(parents=True)
    report.write_text('{"stations_admitted":[{"station":"a"},{"station":"b"}]}', encoding="utf-8")
    stations = [
        {"name": "a", "node": "a", "camera_enu_m": np.array([0.0, 0.0, 2.5])},
        {"name": "b", "node": "b", "camera_enu_m": np.array([10.0, 0.0, 2.5])},
    ]
    graph = LinkGraph(
        position={"a": np.array([0.0, 0.0]), "b": np.array([10.0, 0.0])},
        neighbours={"a": ("b",), "b": ("a",)},
    )
    monkeypatch.setattr(cohort_contract, "load_admitted_stations", lambda *args, **kwargs: stations)
    monkeypatch.setattr(cohort_contract, "load_link_graph", lambda *args, **kwargs: graph)
    monkeypatch.setattr(cohort_contract, "provider_graph_input_paths", lambda *args, **kwargs: ())

    first = route_readiness(manifest, root=tmp_path, route_contract=PROVIDER_CORRIDOR_V1)[0]
    report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    changed = route_readiness(manifest, root=tmp_path, route_contract=PROVIDER_CORRIDOR_V1)[0]

    assert first.ready and first.kind == "provider_corridor"
    assert first.expected_cache is None
    assert first.selection_sha256 != changed.selection_sha256


def test_route_readiness_rejects_endpoint_content_under_the_right_key(monkeypatch, tmp_path):
    manifest = load_manifest()
    entry = _entry(manifest)
    _, cache, waypoints = _stage_route_inputs(tmp_path, entry, monkeypatch)
    _write_exact_cache(cache, entry["site"], list(reversed(waypoints)))

    status = route_readiness(manifest, root=tmp_path)[0]
    assert not status.ready
    assert status.invalid == (str(cache.relative_to(tmp_path)),)


def test_primary_materials_require_both_atlas_files_but_control_is_explicit(tmp_path):
    manifest = load_manifest()
    entry = _entry(manifest)
    atlas = material_readiness(entry["site"], "atlas", manifest, root=tmp_path)
    control = material_readiness(entry["site"], "geometric", manifest, root=tmp_path)

    assert not atlas.ready
    assert set(atlas.missing) == {entry["materials"]["atlas_npz"], entry["materials"]["atlas_json"]}
    assert control.ready and not control.primary
    with pytest.raises(CohortManifestError, match="does not allow"):
        material_readiness(entry["site"], "semantic", manifest, root=tmp_path)


def test_campaign_readiness_combines_three_independent_gates(monkeypatch, tmp_path):
    manifest = load_manifest()
    entry = _entry(manifest)
    _, cache, waypoints = _stage_route_inputs(tmp_path, entry, monkeypatch)
    _write_exact_cache(cache, entry["site"], waypoints)

    before = campaign_readiness(
        entry["site"], COMPARABLE_COHORT, REGISTERED_SPAN_STREET, "atlas", document=manifest, root=tmp_path
    )
    assert before.member and before.route.ready and not before.materials.ready and not before.ready

    _stage_atlas(tmp_path, entry)
    after = campaign_readiness(
        entry["site"], COMPARABLE_COHORT, REGISTERED_SPAN_STREET, "atlas", document=manifest, root=tmp_path
    )
    assert after.ready


def test_krakow_is_not_reported_ready_without_pending_inputs(tmp_path):
    manifest = load_manifest()
    status = campaign_readiness(
        "krakow_rynek",
        COMPARABLE_COHORT,
        REGISTERED_SPAN_STREET,
        "atlas",
        document=manifest,
        root=tmp_path,
    )
    assert not status.ready
    assert status.route.missing == ("outputs/site_semantics/krakow_rynek/walk_semantic_250m.json",)
