"""Manifest-backed membership, route, and material campaign contracts.

The manifest says which cities belong to the study. It does not make a city
ready merely by naming it. Readiness independently proves the admitted camera
set, the exact cached pedestrian route derived from that set, and the selected
material evidence. All checks are read-only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from . import paths
from .walk.route import admitted_route_positions
from .walk.site import street_route_request

SCHEMA = "city-cohort-manifest-v2"
COMPARABLE_COHORT = "comparable_city"
REGISTERED_SPAN_STREET = "registered_span_street_v1"
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
_ALLOWED_MATERIAL_MODES = frozenset({"atlas", "geometric"})
_LEGACY_COHORTS = frozenset({"primary_semantic_route", "geometric_transfer_extension"})


class CohortManifestError(ValueError):
    """Raised when a manifest violates the city cohort contract."""


@dataclass(frozen=True)
class RouteReadiness:
    """Read-only route evidence status for one manifest entry."""

    site: str
    kind: str
    ready: bool
    evidence: tuple[str, ...]
    missing: tuple[str, ...]
    invalid: tuple[str, ...]
    expected_cache: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "kind": self.kind,
            "ready": self.ready,
            "evidence": list(self.evidence),
            "missing": list(self.missing),
            "invalid": list(self.invalid),
            "expected_cache": self.expected_cache,
        }


@dataclass(frozen=True)
class MaterialReadiness:
    """Read-only material evidence status for one site and requested mode."""

    site: str
    mode: str
    primary: bool
    ready: bool
    evidence: tuple[str, ...]
    missing: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "mode": self.mode,
            "primary": self.primary,
            "ready": self.ready,
            "evidence": list(self.evidence),
            "missing": list(self.missing),
        }


@dataclass(frozen=True)
class CampaignReadiness:
    """Three independent gates for one opt-in comparable campaign."""

    site: str
    cohort: str
    member: bool
    route: RouteReadiness
    materials: MaterialReadiness

    @property
    def ready(self) -> bool:
        return self.member and self.route.ready and self.materials.ready

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "cohort": self.cohort,
            "member": self.member,
            "route": self.route.as_dict(),
            "materials": self.materials.as_dict(),
            "ready": self.ready,
        }


def default_manifest_path() -> Path:
    """Return the checked-in cohort manifest."""
    return paths.config_dir() / "city_cohort_manifest.json"


def load_manifest(path: Path | str | None = None) -> dict[str, Any]:
    """Read and structurally validate a cohort manifest."""
    manifest_path = Path(path) if path is not None else default_manifest_path()
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(document)
    return document


def validate_manifest(document: dict[str, Any]) -> None:
    """Validate identity, route, and material declarations without I/O."""
    if not isinstance(document, dict):
        raise CohortManifestError("manifest must be a JSON object")
    _validate_manifest_header(document)
    _validate_manifest_sites(document)


def _validate_manifest_header(document: dict[str, Any]) -> None:
    if document.get("schema") != SCHEMA:
        raise CohortManifestError(f"manifest schema must be {SCHEMA!r}")
    if document.get("study") != "city-exposure-study":
        raise CohortManifestError("manifest study must be city-exposure-study")
    contract = document.get("contract")
    if not isinstance(contract, dict):
        raise CohortManifestError("manifest contract must be an object")
    if contract.get("included_site_count") != len(INCLUDED_SITES):
        raise CohortManifestError("manifest included_site_count must be ten")
    if contract.get("cohort") != COMPARABLE_COHORT:
        raise CohortManifestError("manifest must declare the comparable_city cohort")
    if contract.get("route_contract") != REGISTERED_SPAN_STREET:
        raise CohortManifestError("manifest must declare the registered span street contract")
    if contract.get("route_radius_m") != 90.0 or contract.get("route_fragment") != 0:
        raise CohortManifestError("manifest must declare the fixed 90 m, fragment-zero route population")
    if contract.get("route_bridge_m") != 0.0:
        raise CohortManifestError("comparable routes must not infer link-graph bridges")
    if contract.get("primary_material_mode") != "atlas":
        raise CohortManifestError("the comparable cohort primary material mode must be atlas")
    if contract.get("times_square_policy") != "excluded":
        raise CohortManifestError("Times Square must be explicitly excluded")


def _validate_manifest_sites(document: dict[str, Any]) -> None:
    included = document.get("included_sites")
    if not isinstance(included, list) or len(included) != len(INCLUDED_SITES):
        raise CohortManifestError("manifest must contain exactly ten included_sites")
    names = tuple(_site_name(entry, "included_sites") for entry in included)
    if names != INCLUDED_SITES:
        raise CohortManifestError(f"included_sites must use canonical order {INCLUDED_SITES!r}")
    for entry in included:
        _validate_included_entry(entry)

    excluded = document.get("excluded_sites")
    if not isinstance(excluded, list) or len(excluded) != 1:
        raise CohortManifestError("manifest must contain one excluded site")
    excluded_entry = excluded[0]
    if _site_name(excluded_entry, "excluded_sites") != EXCLUDED_SITE:
        raise CohortManifestError("the sole excluded site must be newyork_timessquare")
    if excluded_entry.get("status") != "excluded" or excluded_entry.get("reason_code") != "invalid_geometry":
        raise CohortManifestError("Times Square exclusion must be marked invalid_geometry")


def _site_name(entry: Any, field: str) -> str:
    if not isinstance(entry, dict) or not isinstance(entry.get("site"), str) or not entry["site"]:
        raise CohortManifestError(f"every {field} entry needs a non-empty site")
    return entry["site"]


def _validate_included_entry(entry: dict[str, Any]) -> None:
    site = entry["site"]
    if not isinstance(entry.get("display_name"), str) or not entry["display_name"]:
        raise CohortManifestError(f"{site} needs a display_name")
    membership = entry.get("membership")
    if not isinstance(membership, dict) or membership.get("status") != "included":
        raise CohortManifestError(f"{site} must explicitly declare included membership")
    if membership.get("cohort") != COMPARABLE_COHORT:
        raise CohortManifestError(f"{site} has the wrong study cohort")
    if membership.get("legacy_cohort") not in _LEGACY_COHORTS:
        raise CohortManifestError(f"{site} has no valid legacy cohort compatibility declaration")
    _validate_geometry(entry, site)
    _validate_route(entry, site)
    _validate_materials(entry, site)


def _validate_geometry(entry: dict[str, Any], site: str) -> None:
    geometry = entry.get("geometry")
    if not isinstance(geometry, dict):
        raise CohortManifestError(f"{site} needs a geometry contract")
    for key in ("config", "mesh_glob"):
        value = geometry.get(key)
        if not isinstance(value, str) or _unsafe_relative_path(value):
            raise CohortManifestError(f"{site} needs a safe relative geometry {key}")


def _validate_route(entry: dict[str, Any], site: str) -> None:
    route = entry.get("route")
    if not isinstance(route, dict):
        raise CohortManifestError(f"{site} needs a route contract")
    required = {
        "contract": REGISTERED_SPAN_STREET,
        "kind": "street_route",
        "coordinate_policy": "registered_span_endpoints",
        "endpoint_policy": "furthest_registered_pair",
        "optimise": False,
    }
    for key, expected in required.items():
        if route.get(key) != expected:
            raise CohortManifestError(f"{site} route {key} must be {expected!r}")
    report = route.get("admitted_station_report")
    cache_dir = route.get("cache_dir")
    expected_report = f"outputs/site_semantics/{site}/walk_semantic_250m.json"
    if report != expected_report:
        raise CohortManifestError(f"{site} needs a site-scoped admitted station report")
    if not isinstance(cache_dir, str) or _unsafe_relative_path(cache_dir):
        raise CohortManifestError(f"{site} needs a safe route cache directory")
    if any(key in route for key in ("waypoints", "coordinates", "cache_glob")):
        raise CohortManifestError(f"{site} route must derive one exact cache key, not accept coordinates or a glob")


def _validate_materials(entry: dict[str, Any], site: str) -> None:
    materials = entry.get("materials")
    if not isinstance(materials, dict) or materials.get("primary_mode") != "atlas":
        raise CohortManifestError(f"{site} primary material mode must be atlas")
    if materials.get("allowed_modes") != ["atlas", "geometric"]:
        raise CohortManifestError(f"{site} must allow atlas primary runs and explicit geometric controls")
    for key in ("atlas_npz", "atlas_json"):
        value = materials.get(key)
        if not isinstance(value, str) or _unsafe_relative_path(value) or site not in Path(value).parts:
            raise CohortManifestError(f"{site} needs a site-scoped {key}")
    if Path(materials["atlas_npz"]).with_suffix(".json") != Path(materials["atlas_json"]):
        raise CohortManifestError(f"{site} atlas JSON and NPZ must be one canonical sidecar pair")


def _unsafe_relative_path(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts


def _manifest_root(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent.parent


def _readiness_root(*, manifest_path: Path | str | None, root: Path | str | None) -> Path:
    if root is not None:
        return Path(root).resolve()
    if manifest_path is not None:
        return _manifest_root(Path(manifest_path))
    return paths.root().resolve()


def _entry(document: dict[str, Any], site: str) -> dict[str, Any]:
    for entry in document["included_sites"]:
        if entry["site"] == site:
            return entry
    if site == EXCLUDED_SITE:
        raise CohortManifestError(f"{site} is excluded from this study because its geometry is invalid")
    raise CohortManifestError(f"{site} is not a member of the comparable city cohort")


def validate_study_membership(
    site: str,
    cohort: str,
    document: dict[str, Any] | None = None,
    *,
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """Return the member entry only when its declared cohort matches."""
    if document is None:
        document = load_manifest(manifest_path)
    else:
        validate_manifest(document)
    entry = _entry(document, site)
    membership = entry["membership"]
    declared = membership["cohort"] if cohort == COMPARABLE_COHORT else membership.get("legacy_cohort")
    if cohort != declared:
        raise CohortManifestError(f"{site} is not a member of cohort {cohort!r}")
    return entry


def _station_positions(report: Path) -> np.ndarray:
    document = json.loads(report.read_text(encoding="utf-8"))
    entries = document.get("stations_admitted")
    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("admitted station report needs at least two stations")
    positions = np.asarray([entry.get("position_enu_m") for entry in entries], dtype=np.float64)
    if positions.shape != (len(entries), 3) or not np.all(np.isfinite(positions)):
        raise ValueError("admitted station positions must be finite ENU triples")
    return positions


def expected_route_cache(
    entry: dict[str, Any],
    base: Path,
    *,
    crop_m: int = 250,
    radius_m: float = 90.0,
    fragment: int = 0,
    bridge_m: float = 0.0,
) -> tuple[Path, list[list[float]]]:
    """Resolve the sole cache named by a site's current admitted endpoints."""
    report = base / entry["route"]["admitted_station_report"]
    _station_positions(report)
    positions = admitted_route_positions(
        entry["site"],
        root=base,
        report=report.name,
        radius_m=radius_m,
        fragment=fragment,
        bridge_m=bridge_m,
    )
    _, waypoints, cache, optimise = street_route_request(
        entry["site"], positions, root=base, crop_m=crop_m, endpoints="span"
    )
    if optimise:
        raise AssertionError("a span request must contain exactly two ordered endpoints")
    return cache, [list(point) for point in waypoints]


def _valid_points(value: Any, *, minimum: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= minimum
        and all(
            isinstance(point, list)
            and len(point) == 2
            and all(
                isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number)
                for number in point
            )
            for point in value
        )
    )


def _is_exact_route_cache(path: Path, site: str, waypoints: list[list[float]]) -> bool:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if document.get("site") != site or document.get("optimised") is not False:
        return False
    if not _valid_points(document.get("polyline_llh"), minimum=2):
        return False
    recorded = document.get("waypoints_llh")
    return _valid_points(recorded, minimum=2) and np.array_equal(
        np.asarray(recorded, dtype=np.float64), np.asarray(waypoints, dtype=np.float64)
    )


def _route_status(entry: dict[str, Any], base: Path, contract: dict[str, Any]) -> RouteReadiness:
    site = entry["site"]
    report = base / entry["route"]["admitted_station_report"]
    report_name = str(report.relative_to(base))
    if not report.is_file():
        return RouteReadiness(site, "street_route", False, (), (report_name,), ())
    try:
        cache, waypoints = expected_route_cache(
            entry,
            base,
            crop_m=int(contract["crop_m"]),
            radius_m=float(contract["route_radius_m"]),
            fragment=int(contract["route_fragment"]),
            bridge_m=float(contract["route_bridge_m"]),
        )
    except (OSError, ValueError) as error:
        return RouteReadiness(site, "street_route", False, (), (), (f"{report_name}: {error}",))
    cache_name = str(cache.relative_to(base))
    if not cache.is_file():
        return RouteReadiness(site, "street_route", False, (report_name,), (cache_name,), (), cache_name)
    if not _is_exact_route_cache(cache, site, waypoints):
        return RouteReadiness(site, "street_route", False, (report_name,), (), (cache_name,), cache_name)
    return RouteReadiness(site, "street_route", True, (report_name, cache_name), (), (), cache_name)


def route_readiness(
    document: dict[str, Any] | None = None,
    *,
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
) -> tuple[RouteReadiness, ...]:
    """Return exact registered-endpoint route readiness for every member."""
    if document is None:
        document = load_manifest(manifest_path)
    else:
        validate_manifest(document)
    base = _readiness_root(manifest_path=manifest_path, root=root)
    return tuple(_route_status(entry, base, document["contract"]) for entry in document["included_sites"])


def material_readiness(
    site: str,
    mode: str,
    document: dict[str, Any] | None = None,
    *,
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
) -> MaterialReadiness:
    """Validate the selected material mode separately from route evidence."""
    if document is None:
        document = load_manifest(manifest_path)
    else:
        validate_manifest(document)
    entry = _entry(document, site)
    if mode not in _ALLOWED_MATERIAL_MODES or mode not in entry["materials"]["allowed_modes"]:
        raise CohortManifestError(f"{site} does not allow material mode {mode!r}")
    primary = mode == entry["materials"]["primary_mode"]
    if not primary:
        return MaterialReadiness(site, mode, False, True, (), ())
    base = _readiness_root(manifest_path=manifest_path, root=root)
    paths_expected = tuple(entry["materials"][key] for key in ("atlas_npz", "atlas_json"))
    evidence = tuple(relative for relative in paths_expected if (base / relative).is_file())
    missing = tuple(relative for relative in paths_expected if not (base / relative).is_file())
    return MaterialReadiness(site, mode, True, not missing, evidence, missing)


def campaign_readiness(
    site: str,
    cohort: str,
    route_contract: str,
    material_mode: str,
    *,
    document: dict[str, Any] | None = None,
    manifest_path: Path | str | None = None,
    root: Path | str | None = None,
) -> CampaignReadiness:
    """Apply the three independent gates for an opt-in comparable campaign."""
    if document is None:
        document = load_manifest(manifest_path)
    else:
        validate_manifest(document)
    entry = validate_study_membership(site, cohort, document)
    if route_contract != entry["route"]["contract"]:
        raise CohortManifestError(f"{site} does not declare route contract {route_contract!r}")
    base = _readiness_root(manifest_path=manifest_path, root=root)
    route = _route_status(entry, base, document["contract"])
    materials = material_readiness(site, material_mode, document, root=base)
    return CampaignReadiness(site, cohort, True, route, materials)
