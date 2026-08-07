"""The reproducible city cohort and route-readiness checks.

The cohort manifest is deliberately a contract, not an acquisition script. It
names the ten intended sites and the one excluded site, but it does not carry
Google route coordinates. A panorama route reads positions from registered
capture evidence; a street route reads a previously cached Google Routes reply.
This keeps validation read-only and prevents a readiness check from silently
buying or inventing a route.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import paths

SCHEMA = "city-cohort-manifest-v1"
INCLUDED_SITES = (
    "korenmarkt",
    "prague_staromestske",
    "brussels_grandplace",
    "madrid_plazamayor",
    "mexico_zocalo",
    "tokyo_hachiko",
    "london_trafalgar",
    "milan_duomo",
    "krakow_rynek",
    "toulouse_capitole",
)
EXCLUDED_SITE = "newyork_timessquare"
_PRIMARY_SITES = frozenset(INCLUDED_SITES[:6])
_GEOMETRIC_SITES = frozenset(INCLUDED_SITES[6:])
_COHORTS = frozenset({"primary_semantic_route", "geometric_extension"})
_ROUTE_KINDS = frozenset({"panorama_links", "street_route"})


class CohortManifestError(ValueError):
    """Raised when a manifest violates the ten-city cohort contract."""


@dataclass(frozen=True)
class RouteReadiness:
    """Read-only route evidence status for one manifest entry."""

    site: str
    kind: str
    ready: bool
    evidence: tuple[str, ...]
    missing: tuple[str, ...]
    invalid: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "kind": self.kind,
            "ready": self.ready,
            "evidence": list(self.evidence),
            "missing": list(self.missing),
            "invalid": list(self.invalid),
        }


def default_manifest_path() -> Path:
    """Return the checked-in cohort manifest."""
    return paths.config_dir() / "city_cohort_manifest.json"


def load_manifest(path: Path | str | None = None) -> dict[str, Any]:
    """Read and validate a cohort manifest without inspecting any input data."""
    manifest_path = Path(path) if path is not None else default_manifest_path()
    document = json.loads(manifest_path.read_text())
    validate_manifest(document)
    return document


def validate_manifest(document: dict[str, Any]) -> None:
    """Validate the structural and scientific identity contract.

    This intentionally does not require meshes, semantic reports, or route
    caches to exist. Those are environmental readiness facts returned by
    :func:`route_readiness` and a caller can inspect them before launching a
    campaign.
    """
    if not isinstance(document, dict):
        raise CohortManifestError("manifest must be a JSON object")
    if document.get("schema") != SCHEMA:
        raise CohortManifestError(f"manifest schema must be {SCHEMA!r}")
    if document.get("study") != "city-exposure-study":
        raise CohortManifestError("manifest study must be city-exposure-study")
    contract = document.get("contract")
    if not isinstance(contract, dict):
        raise CohortManifestError("manifest contract must be an object")
    if contract.get("included_site_count") != len(INCLUDED_SITES):
        raise CohortManifestError("manifest included_site_count must be ten")
    if contract.get("times_square_policy") != "excluded":
        raise CohortManifestError("Times Square must be explicitly excluded")

    included = document.get("included_sites")
    if not isinstance(included, list) or len(included) != len(INCLUDED_SITES):
        raise CohortManifestError("manifest must contain exactly ten included_sites")
    names = tuple(_site_name(entry, "included_sites") for entry in included)
    if names != INCLUDED_SITES:
        raise CohortManifestError(f"included_sites must use canonical order {INCLUDED_SITES!r}")

    excluded = document.get("excluded_sites")
    if not isinstance(excluded, list) or len(excluded) != 1:
        raise CohortManifestError("manifest must contain one excluded site")
    excluded_entry = excluded[0]
    if _site_name(excluded_entry, "excluded_sites") != EXCLUDED_SITE:
        raise CohortManifestError("the sole excluded site must be newyork_timessquare")
    if excluded_entry.get("status") != "excluded" or excluded_entry.get("reason_code") != "invalid_geometry":
        raise CohortManifestError("Times Square exclusion must be marked invalid_geometry")

    for entry in included:
        _validate_included_entry(entry)


def _site_name(entry: Any, field: str) -> str:
    if not isinstance(entry, dict) or not isinstance(entry.get("site"), str) or not entry["site"]:
        raise CohortManifestError(f"every {field} entry needs a non-empty site")
    return entry["site"]


def _validate_included_entry(entry: dict[str, Any]) -> None:
    site = entry["site"]
    if not isinstance(entry.get("display_name"), str) or not entry["display_name"]:
        raise CohortManifestError(f"{site} needs a display_name")
    if entry.get("cohort") not in _COHORTS:
        raise CohortManifestError(f"{site} has an unknown cohort")
    geometry = entry.get("geometry")
    if not isinstance(geometry, dict) or not isinstance(geometry.get("config"), str):
        raise CohortManifestError(f"{site} needs a config path")
    if not isinstance(geometry.get("mesh_glob"), str) or "{site}" in geometry["mesh_glob"]:
        raise CohortManifestError(f"{site} needs a concrete mesh_glob")
    route = entry.get("route")
    if not isinstance(route, dict) or route.get("kind") not in _ROUTE_KINDS:
        raise CohortManifestError(f"{site} has an unknown route kind")
    if route.get("coordinate_policy") not in {"registered_capture_positions", "cached_google_routes_only"}:
        raise CohortManifestError(f"{site} has an unsafe coordinate policy")
    expected_cohort = "primary_semantic_route" if site in _PRIMARY_SITES else "geometric_extension"
    expected_kind = "panorama_links" if site in _PRIMARY_SITES else "street_route"
    if entry["cohort"] != expected_cohort or route["kind"] != expected_kind:
        raise CohortManifestError(f"{site} has the wrong cohort/route contract")
    if route["kind"] == "panorama_links":
        required = route.get("required_inputs")
        if not isinstance(required, list) or not required or not all(isinstance(path, str) for path in required):
            raise CohortManifestError(f"{site} panorama route needs required_inputs")
        if any(_unsafe_relative_path(path) for path in required):
            raise CohortManifestError(f"{site} panorama route has an unsafe input path")
        if route.get("coordinate_policy") != "registered_capture_positions":
            raise CohortManifestError(f"{site} panorama route must use registered positions")
        if "cache_glob" in route:
            raise CohortManifestError(f"{site} panorama route must not declare a route cache")
    else:
        cache_glob = route.get("cache_glob")
        if not isinstance(cache_glob, str) or "{site}" not in cache_glob or not cache_glob.endswith(".json"):
            raise CohortManifestError(f"{site} street route needs a site-scoped JSON cache glob")
        if _unsafe_relative_path(cache_glob):
            raise CohortManifestError(f"{site} street route has an unsafe cache path")
        if route.get("coordinate_policy") != "cached_google_routes_only":
            raise CohortManifestError(f"{site} street route must use cached coordinates")
        if "required_inputs" in route:
            raise CohortManifestError(f"{site} street route must not invent required inputs")


def _unsafe_relative_path(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts


def _manifest_root(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent.parent


def _is_valid_route_cache(path: Path, site: str) -> bool:
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if document.get("site") != site:
        return False
    polyline = document.get("polyline_llh")
    waypoints = document.get("waypoints_llh")
    if not isinstance(polyline, list) or len(polyline) < 2:
        return False
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        return False
    return all(
        isinstance(point, list)
        and len(point) == 2
        and all(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in point
        )
        for point in polyline + waypoints
    )


def route_readiness(
    document: dict[str, Any] | None = None,
    *,
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
) -> tuple[RouteReadiness, ...]:
    """Return route evidence status for every included site.

    ``root`` is the study root containing ``data/`` and ``outputs/``. It is
    optional for tests and staging checks. No network request or file write is
    performed.
    """
    if document is None:
        document = load_manifest(manifest_path)
    else:
        validate_manifest(document)
    # An explicit root wins over the manifest's inferred checkout. This is
    # useful when validating a frozen manifest against a separately staged
    # input tree, while the manifest-only form still infers its own root.
    if root is not None:
        base = Path(root)
    elif manifest_path is not None:
        base = _manifest_root(Path(manifest_path))
    else:
        base = paths.root()
    base = base.resolve()
    statuses: list[RouteReadiness] = []
    for entry in document["included_sites"]:
        site = entry["site"]
        route = entry["route"]
        evidence: list[str] = []
        missing: list[str] = []
        invalid: list[str] = []
        if route["kind"] == "panorama_links":
            for relative in route["required_inputs"]:
                path = base / relative
                if path.is_file():
                    evidence.append(relative)
                else:
                    missing.append(relative)
        else:
            pattern = route["cache_glob"].replace("{site}", site)
            candidates = sorted(base.glob(pattern))
            valid = [path for path in candidates if _is_valid_route_cache(path, site)]
            evidence.extend(str(path.relative_to(base)) for path in valid)
            invalid.extend(str(path.relative_to(base)) for path in candidates if path not in valid)
            if not valid:
                missing.append(pattern)
        # A stale or malformed cache beside a valid one is an audit warning,
        # not a reason to refuse the valid response. The caller still receives
        # ``invalid`` so it can clean the cache before sealing a run.
        statuses.append(
            RouteReadiness(site, route["kind"], not missing, tuple(evidence), tuple(missing), tuple(invalid))
        )
    return tuple(statuses)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and report the ten-city cohort route contract")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None, help="study root containing data/ and outputs/")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable readiness JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        statuses = route_readiness(manifest_path=args.manifest, root=args.root)
    except (CohortManifestError, OSError, json.JSONDecodeError) as error:
        print(f"cohort manifest error: {error}")
        return 2
    if args.as_json:
        print(json.dumps([status.as_dict() for status in statuses], indent=2))
    else:
        for status in statuses:
            state = "ready" if status.ready else "blocked"
            print(f"{status.site:24} {status.kind:16} {state}")
            for missing in status.missing:
                print(f"  missing: {missing}")
            for invalid in status.invalid:
                print(f"  invalid: {invalid}")
    return 0 if all(status.ready for status in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
