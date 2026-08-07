"""Contract and read-only readiness tests for the ten-city cohort."""

from __future__ import annotations

import json

import pytest

from semantic_twin.cohort import (
    EXCLUDED_SITE,
    INCLUDED_SITES,
    CohortManifestError,
    load_manifest,
    route_readiness,
    validate_manifest,
)


def test_manifest_names_the_canonical_ten_and_excludes_times_square():
    manifest = load_manifest()

    assert tuple(entry["site"] for entry in manifest["included_sites"]) == INCLUDED_SITES
    assert tuple(entry["site"] for entry in manifest["excluded_sites"]) == (EXCLUDED_SITE,)
    assert manifest["excluded_sites"][0]["reason_code"] == "invalid_geometry"


def test_manifest_contains_no_route_coordinate_arrays():
    manifest = load_manifest()

    for entry in manifest["included_sites"]:
        route = entry["route"]
        assert route["coordinate_policy"] in {"registered_capture_positions", "cached_google_routes_only"}
        assert "waypoints" not in route
        assert "coordinates" not in route


def test_validation_rejects_missing_street_cache_glob():
    manifest = load_manifest()
    manifest["included_sites"][-1]["route"].pop("cache_glob")

    with pytest.raises(CohortManifestError, match="street route needs"):
        validate_manifest(manifest)


def test_validation_rejects_moving_a_site_between_route_cohorts():
    manifest = load_manifest()
    manifest["included_sites"][0]["cohort"] = "geometric_extension"

    with pytest.raises(CohortManifestError, match="wrong cohort/route"):
        validate_manifest(manifest)


def test_panorama_readiness_checks_evidence_without_writing(tmp_path):
    manifest = load_manifest()
    for entry in manifest["included_sites"]:
        if entry["route"]["kind"] == "panorama_links":
            entry["route"]["required_inputs"] = ["outputs/site_semantics/example.json"]
            break
    manifest_path = tmp_path / "config" / "city_cohort_manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(json.dumps(manifest))
    statuses = route_readiness(manifest_path=manifest_path)

    first = statuses[0]
    assert not first.ready
    assert first.missing == ("outputs/site_semantics/example.json",)
    assert not list(tmp_path.rglob("*")) == []


def test_street_readiness_accepts_only_a_valid_cached_response(tmp_path):
    manifest = load_manifest()
    entry = next(item for item in manifest["included_sites"] if item["route"]["kind"] == "street_route")
    site = entry["site"]
    route_dir = tmp_path / "data" / "street_routes"
    route_dir.mkdir(parents=True)
    (route_dir / f"{site}_bad.json").write_text(json.dumps({"site": site, "polyline_llh": []}))
    (route_dir / f"{site}_good.json").write_text(
        json.dumps(
            {
                "site": site,
                "polyline_llh": [[1.0, 2.0], [1.1, 2.1]],
                "waypoints_llh": [[1.0, 2.0], [1.1, 2.1]],
            }
        )
    )
    statuses = route_readiness(manifest, root=tmp_path)

    status = next(item for item in statuses if item.site == site)
    assert status.ready
    assert status.evidence == (f"data/street_routes/{site}_good.json",)
    assert status.invalid == (f"data/street_routes/{site}_bad.json",)
