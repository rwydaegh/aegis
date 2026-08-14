"""Authenticated numerical claims for the current five-city manuscript.

The claim functions read the immutable production outputs. They do not import
the simulation package and do not write into ``semantic_twin/outputs``. This
keeps the manuscript audit runnable in PaperMaker9000's small environment.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import struct
import zipfile
from pathlib import Path
from typing import Any

from papermaker.claims import claim


SEMANTIC_TWIN_ROOT = Path(__file__).resolve().parents[3]
PAPER_ROOT = SEMANTIC_TWIN_ROOT / "paper"
OUTPUT_ROOT = SEMANTIC_TWIN_ROOT / "outputs"
CAMPAIGN_ROOT = OUTPUT_ROOT / "roofline_campaign"
EXPERIMENT_ROOT = OUTPUT_ROOT / "experiments"

AGGREGATE_DIR = CAMPAIGN_ROOT / "current_five_city_first_material_interaction"
AGGREGATE_PATH = AGGREGATE_DIR / "current_five_city_first_material_interaction.json"
AGGREGATE_MANIFEST_PATH = AGGREGATE_DIR / "current_five_city_first_material_interaction_manifest.json"
RAY_REACHED_REPORT_DIR = EXPERIMENT_ROOT / "ray_reached_evidence_coverage_v1" / "report"
CONVERGENCE64_REPORT_DIR = EXPERIMENT_ROOT / "current_topology_convergence64_v1" / "report"

CITY_SLUGS = {
    "Korenmarkt": "korenmarkt",
    "Madrid": "madrid_plazamayor",
    "Mexico": "mexico_zocalo",
    "Prague": "prague_staromestske",
    "Tokyo": "tokyo_hachiko",
}
CAMPAIGN_SUFFIX = "provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid"
EXPECTED_SEEDS = list(range(7, 23))
EXPECTED_STANDPOINTS = {
    "Korenmarkt": 10,
    "Madrid": 14,
    "Mexico": 11,
    "Prague": 22,
    "Tokyo": 16,
}
EXPECTED_WBSAR_QUANTILES = {
    "Korenmarkt": {
        "q10": 0.0578327438321708,
        "q50": 0.06204518535491678,
        "q90": 0.0686717408320388,
    },
    "Madrid": {
        "q10": 0.020913294077888663,
        "q50": 0.02238105138497516,
        "q90": 0.02317093976407998,
    },
    "Mexico": {
        "q10": 9.92187947769122e-7,
        "q50": 0.12906154022429828,
        "q90": 0.2957983257792987,
    },
    "Prague": {
        "q10": 0.012157461907945675,
        "q50": 0.0130731658075402,
        "q90": 0.014593757806466821,
    },
    "Tokyo": {
        "q10": 0.00003656217959315326,
        "q50": 0.009673886624732418,
        "q90": 0.025200369144298053,
    },
}
EXPECTED_TOTAL_TRANSFER_CHANGE_DB = {
    "Korenmarkt": 0.0000819350556661845,
    "Madrid": 0.000408320201322325,
    "Mexico": 0.04362524009941786,
    "Prague": 0.00015589567357771397,
    "Tokyo": 0.019731518973211258,
}
EXPECTED_ZERO_STANDPOINTS = {
    "Mexico": [0, 1, 3],
    "Tokyo": [13, 14, 15],
}
EXPECTED_POOLED_MEDIAN_WBSAR_SHARES_PERCENT = {
    "direct": 77.66194473787252,
    "all_specular": 21.390850539012177,
    "first_diffuse": 0.41895042544439237,
}
FIELD_META_NAMES = (
    "includes_specular",
    "missing_specular",
    "maximum_completed_all_specular_order",
    "maximum_completed_specular_suffix_order",
    "direct_atom_count",
    "specular_atom_count",
    "nonzero_diffuse_cell_count",
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"expected JSON object: {path}"
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        assert isinstance(value, dict), f"expected JSON object per line: {path}"
        rows.append(value)
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assert_close(actual: float, expected: float, *, atol: float = 1e-12) -> None:
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=atol), f"expected {expected!r}, found {actual!r}"


def _quantile(values: list[float], probability: float) -> float:
    """Return NumPy's default linear quantile without a NumPy dependency."""
    ordered = sorted(float(value) for value in values)
    assert ordered, "cannot take a quantile of an empty sequence"
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _campaign_directory(city: str, *, geometric: bool = False) -> Path:
    suffix = CAMPAIGN_SUFFIX + ("_geometric_control" if geometric else "")
    return CAMPAIGN_ROOT / f"{CITY_SLUGS[city]}_{suffix}"


def _verify_mapping_manifest(root: Path, manifest: dict[str, Any]) -> int:
    files = manifest.get("files")
    assert isinstance(files, dict), f"manifest has no file mapping: {root}"
    for relative, expected in files.items():
        path = root / relative
        assert path.is_file(), f"manifested file is missing: {path}"
        actual = _sha256(path)
        assert actual == expected, f"SHA-256 mismatch: {path}"
    return len(files)


def _verify_list_manifest(root: Path, manifest: dict[str, Any]) -> int:
    files = manifest.get("files")
    assert isinstance(files, list), f"manifest has no file list: {root}"
    for record in files:
        assert isinstance(record, dict), f"invalid manifest record: {root}"
        path = root / str(record["path"])
        assert path.is_file(), f"manifested file is missing: {path}"
        assert path.stat().st_size == int(record["bytes"]), f"byte count mismatch: {path}"
        assert _sha256(path) == record["sha256"], f"SHA-256 mismatch: {path}"
    return len(files)


def _verify_aggregate_artifacts() -> dict[str, Any]:
    manifest = _read_json(AGGREGATE_MANIFEST_PATH)
    assert manifest["schema_version"] == "roofline_multicity_artifacts_v1"
    artifacts = manifest.get("artifacts")
    assert isinstance(artifacts, dict) and len(artifacts) == 4
    for relative, record in artifacts.items():
        path = AGGREGATE_DIR / relative
        assert path.is_file(), f"aggregate artifact is missing: {path}"
        assert path.stat().st_size == int(record["bytes"])
        assert _sha256(path) == record["sha256"], f"SHA-256 mismatch: {path}"
    return manifest


def _verify_campaign(city: str, *, geometric: bool = False) -> tuple[Path, dict[str, Any]]:
    root = _campaign_directory(city, geometric=geometric)
    manifest = _read_json(root / "manifest.json")
    assert manifest["schema_version"] == ("roofline_body_campaign_first_material_interaction_v1")
    assert _verify_mapping_manifest(root, manifest) == 42
    identity = _read_json(root / "campaign_identity.json")
    assert manifest["identity_sha256"] == identity["sha256"]
    return root, identity


def _load_aggregate() -> dict[str, Any]:
    _verify_aggregate_artifacts()
    result = _read_json(AGGREGATE_PATH)
    assert result["schema_version"] == "roofline_multicity_results_v1"
    return result


def _read_npy_f64(npz_path: Path, member: str) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """Read a C-order float64 NPY member using only the Python standard library."""
    with zipfile.ZipFile(npz_path) as archive:
        payload = archive.read(member)
    assert payload[:6] == b"\x93NUMPY", f"invalid NPY header: {npz_path}:{member}"
    major = payload[6]
    if major == 1:
        header_size = struct.unpack_from("<H", payload, 8)[0]
        header_start = 10
    else:
        header_size = struct.unpack_from("<I", payload, 8)[0]
        header_start = 12
    header = ast.literal_eval(payload[header_start : header_start + header_size].decode("latin1").strip())
    assert header["fortran_order"] is False
    assert header["descr"] in ("<f8", "=f8"), f"unsupported NPY dtype {header['descr']}: {npz_path}:{member}"
    shape = tuple(int(value) for value in header["shape"])
    count = math.prod(shape)
    data_start = header_start + header_size
    values = struct.unpack_from(f"<{count}d", payload, data_start)
    assert data_start + count * 8 == len(payload)
    return shape, values


def _abs_db_errors(values: list[float], reference: list[float]) -> list[float]:
    assert len(values) == len(reference)
    return [abs(10.0 * math.log10(value / ref)) for value, ref in zip(values, reference)]


@claim("current_campaign_contract")
def current_campaign_contract() -> dict[str, Any]:
    """The paper result is five authenticated 15 GHz fixed-route campaigns."""
    aggregate = _load_aggregate()
    assert set(aggregate["cities"]) == set(CITY_SLUGS)
    manifest_files = 0
    fields = 0
    for city, expected_points in EXPECTED_STANDPOINTS.items():
        root, identity = _verify_campaign(city)
        manifest_files += len(_read_json(root / "manifest.json")["files"])
        result = aggregate["cities"][city]
        assert result["standpoints"] == expected_points
        assert result["replicas"] == 16
        assert result["seeds"] == EXPECTED_SEEDS
        assert result["transport_topology"] == "first_material_interaction_v1"
        assert result["components"] == ["direct", "all_specular", "first_diffuse", "total"]
        data = identity["data"]
        assert data["configuration"]["route_contract"] == "provider_corridor_v1"
        assert data["configuration"]["reference_mode"] == "per_density_eirp"
        assert data["transport"]["tracer"]["configuration"]["rays"] == 200_000
        assert data["transport"]["tracer"]["configuration"]["local_cells"] == 4096
        assert data["body"]["frequency_hz"] == 15_000_000_000.0
        assert data["body"]["surface_elements"] == 56_024
        fields += expected_points * 16
    assert manifest_files == 210
    assert fields == 1_168
    primary_rays = fields * 200_000
    assert primary_rays == 233_600_000
    return {
        "cities": 5,
        "standpoints": sum(EXPECTED_STANDPOINTS.values()),
        "city_replica_runs": 5 * 16,
        "standpoint_replica_fields": fields,
        "primary_rays": primary_rays,
        "passive_output_cells": 4096,
        "authenticated_campaign_files": manifest_files,
        "frequency_hz": 15_000_000_000.0,
        "body_surface_elements": 56_024,
        "normalization": "per unit rho_A P_EIRP",
    }


@claim("five_city_wbsar_route_quantiles")
def five_city_wbsar_route_quantiles() -> dict[str, Any]:
    """Route q10, q50, and q90 values are recomputed from all 73 standpoints."""
    aggregate = _load_aggregate()
    result: dict[str, Any] = {}
    for city, expected in EXPECTED_WBSAR_QUANTILES.items():
        record = aggregate["cities"][city]
        values = [float(row["wbsar"]) for row in record["route"]]
        assert len(values) == EXPECTED_STANDPOINTS[city]
        computed = {
            "q10": _quantile(values, 0.1),
            "q50": _quantile(values, 0.5),
            "q90": _quantile(values, 0.9),
        }
        stored = record["route_quantile_uncertainty"]["quantiles"]["wbsar"]
        for name, value in computed.items():
            _assert_close(value, expected[name])
            _assert_close(value, float(stored[name]["estimate"]))
        result[city] = computed
    return {"unit": "m^2 kg^-1 per unit rho_A P_EIRP", "cities": result}


@claim("route_median_contrast_factor")
def route_median_contrast_factor() -> dict[str, Any]:
    """The largest and smallest selected-route medians differ by a factor of 13.34."""
    medians = {city: values["q50"] for city, values in EXPECTED_WBSAR_QUANTILES.items()}
    largest_city = max(medians, key=medians.get)
    smallest_city = min(medians, key=medians.get)
    factor = medians[largest_city] / medians[smallest_city]
    _assert_close(factor, 13.341229355979571)
    assert round(factor, 2) == 13.34
    return {
        "factor": factor,
        "reported_factor": 13.34,
        "largest_route_median": largest_city,
        "smallest_route_median": smallest_city,
        "scope": "contrast among five selected routes, not a city ranking",
    }


@claim("six_shadowed_standpoints")
def six_shadowed_standpoints() -> dict[str, Any]:
    """Six points have zero direct and order-1 specular transport but positive diffuse transport."""
    aggregate = _load_aggregate()
    found: dict[str, list[int]] = {}
    finite_surplus = 0
    diffuse_largest = 0
    direct_largest = 0
    for city, record in aggregate["cities"].items():
        city_zeros: list[int] = []
        for row in record["route"]:
            components = row["component_body"]
            direct = float(components["direct"]["sar_wb_w_kg"])
            specular = float(components["all_specular"]["sar_wb_w_kg"])
            diffuse = float(components["first_diffuse"]["sar_wb_w_kg"])
            total = float(components["total"]["sar_wb_w_kg"])
            if direct == 0.0 and specular == 0.0:
                assert diffuse > 0.0
                _assert_close(diffuse, total, atol=1e-18)
                assert row["multipath_surplus_db"] is None
                city_zeros.append(int(row["standpoint"]))
            else:
                assert row["multipath_surplus_db"] is not None
                finite_surplus += 1
            largest = max((direct, "direct"), (specular, "specular"), (diffuse, "diffuse"))[1]
            direct_largest += largest == "direct"
            diffuse_largest += largest == "diffuse"
        if city_zeros:
            found[city] = city_zeros
    assert found == EXPECTED_ZERO_STANDPOINTS
    assert finite_surplus == 67
    assert direct_largest == 67
    assert diffuse_largest == 6
    return {
        "count": 6,
        "standpoints": found,
        "finite_multipath_surplus_points": finite_surplus,
        "largest_component_counts": {"direct": direct_largest, "first_diffuse": diffuse_largest},
    }


@claim("raw_component_closure")
def raw_component_closure() -> dict[str, Any]:
    """Direct, specular, and diffuse fields close to total across all 1,168 fields."""
    maximum = 0.0
    fields = 0
    for city in CITY_SLUGS:
        root, _identity = _verify_campaign(city)
        for seed in EXPECTED_SEEDS:
            shard = root / "checkpoint" / "replicas" / f"seed_{seed:010d}.npz"
            shape, values = _read_npy_f64(shard, "raw_transfer.npy")
            assert shape == (EXPECTED_STANDPOINTS[city], 4)
            for offset in range(0, len(values), 4):
                residual = abs(values[offset] + values[offset + 1] + values[offset + 2] - values[offset + 3])
                maximum = max(maximum, residual)
                fields += 1
    assert fields == 1_168
    _assert_close(maximum, 1.734723475976807e-18, atol=1e-24)
    return {"fields": fields, "maximum_absolute_residual_m_inv2": maximum}


@claim("pooled_median_wbsar_component_shares")
def pooled_median_wbsar_component_shares() -> dict[str, Any]:
    """Pooled component medians are rebuilt from all body-metric replica shards."""
    aggregate = _load_aggregate()
    shares: dict[str, list[float]] = {
        "direct": [],
        "all_specular": [],
        "first_diffuse": [],
    }
    for city in CITY_SLUGS:
        root, identity = _verify_campaign(city)
        points = EXPECTED_STANDPOINTS[city]
        components = identity["data"]["components"]
        body_metrics = identity["data"]["body_metrics"]
        assert components == ["direct", "all_specular", "first_diffuse", "total"]
        assert body_metrics[5] == "sar_wb_w_kg"
        component_count = len(components)
        metric_count = len(body_metrics)
        accumulated = [0.0] * (points * component_count * metric_count)
        for seed in EXPECTED_SEEDS:
            shard = root / "checkpoint" / "replicas" / f"seed_{seed:010d}.npz"
            shape, values = _read_npy_f64(shard, "body_metrics.npy")
            assert shape == (points, component_count, metric_count)
            for index, value in enumerate(values):
                accumulated[index] += value / len(EXPECTED_SEEDS)

        for point in range(points):
            values: dict[str, float] = {}
            for component_index, component in enumerate(components):
                offset = (point * component_count + component_index) * metric_count + 5
                values[component] = accumulated[offset]
            assert values["total"] > 0.0
            aggregate_row = aggregate["cities"][city]["route"][point]["component_body"]
            for component in components:
                _assert_close(
                    values[component],
                    float(aggregate_row[component]["sar_wb_w_kg"]),
                    atol=1e-14,
                )
            for component in shares:
                shares[component].append(100.0 * values[component] / values["total"])

    assert all(len(values) == 73 for values in shares.values())
    medians = {component: _quantile(values, 0.5) for component, values in shares.items()}
    for component, expected in EXPECTED_POOLED_MEDIAN_WBSAR_SHARES_PERCENT.items():
        _assert_close(medians[component], expected)
    return {
        "statistic": "componentwise median of the 73 standpoint shares",
        "standpoints": 73,
        "share_percent": medians,
        "reported_share_percent": {
            "direct": 77.662,
            "all_specular": 21.391,
            "first_diffuse": 0.419,
        },
        "note": "componentwise medians need not sum to 100 percent",
    }


@claim("directional_component_representation")
def directional_component_representation() -> dict[str, Any]:
    """Sealed shards distinguish direct/specular atoms from passive diffuse cells."""
    atom_min = {"direct": math.inf, "all_specular": math.inf}
    atom_max = {"direct": -math.inf, "all_specular": -math.inf}
    diffuse_min = math.inf
    diffuse_max = -math.inf
    rows_verified = 0
    for city in CITY_SLUGS:
        root, identity = _verify_campaign(city)
        points = EXPECTED_STANDPOINTS[city]
        local_cells = int(identity["data"]["transport"]["tracer"]["configuration"]["local_cells"])
        assert local_cells == 4096
        checkpoint = _read_json(root / "checkpoint" / "index.json")
        assert checkpoint["components"] == ["direct", "all_specular", "first_diffuse", "total"]
        locations = _read_jsonl(root / "locations.jsonl")
        assert len(locations) == points
        observed_ranges = [{name: [math.inf, -math.inf] for name in FIELD_META_NAMES} for _ in range(points)]

        for seed in EXPECTED_SEEDS:
            shard = root / "checkpoint" / "replicas" / f"seed_{seed:010d}.npz"
            meta_shape, meta_values = _read_npy_f64(shard, "field_meta.npy")
            raw_shape, raw_values = _read_npy_f64(shard, "raw_transfer.npy")
            assert meta_shape == (points, len(FIELD_META_NAMES))
            assert raw_shape == (points, 4)
            diagnostics = json.loads(
                (root / "checkpoint" / "replicas" / f"seed_{seed:010d}.json").read_text(encoding="utf-8")
            )
            assert isinstance(diagnostics, list) and len(diagnostics) == points
            for point in range(points):
                offset = point * len(FIELD_META_NAMES)
                row = meta_values[offset : offset + len(FIELD_META_NAMES)]
                assert row[0] == 1.0
                assert row[2] == 1.0
                assert row[3] == 0.0
                direct_atoms, specular_atoms, diffuse_cells = row[4:7]
                assert direct_atoms.is_integer() and direct_atoms >= 0.0
                assert specular_atoms.is_integer() and specular_atoms >= 0.0
                assert diffuse_cells.is_integer() and 0.0 <= diffuse_cells <= local_cells
                raw_offset = point * 4
                assert (direct_atoms == 0.0) == (raw_values[raw_offset] == 0.0)
                assert (specular_atoms == 0.0) == (raw_values[raw_offset + 1] == 0.0)
                assert (diffuse_cells == 0.0) == (raw_values[raw_offset + 2] == 0.0)
                atom_min["direct"] = min(atom_min["direct"], direct_atoms)
                atom_max["direct"] = max(atom_max["direct"], direct_atoms)
                atom_min["all_specular"] = min(atom_min["all_specular"], specular_atoms)
                atom_max["all_specular"] = max(atom_max["all_specular"], specular_atoms)
                diffuse_min = min(diffuse_min, diffuse_cells)
                diffuse_max = max(diffuse_max, diffuse_cells)
                for index, name in enumerate(FIELD_META_NAMES):
                    observed_ranges[point][name][0] = min(observed_ranges[point][name][0], row[index])
                    observed_ranges[point][name][1] = max(observed_ranges[point][name][1], row[index])
                diagnostic = diagnostics[point]
                assert diagnostic["transport_topology"] == "first_material_interaction_v1"
                assert diagnostic["first_material_interaction_nee_only"] is True
                assert diagnostic["specular_estimate_kind"] == "exact_order_1"
                assert diagnostic["sampled_specular_suffix"]["enabled"] is False
                rows_verified += 1

        for point, location in enumerate(locations):
            stored = location["field_metadata_range"]
            assert set(stored) == set(FIELD_META_NAMES)
            for name in FIELD_META_NAMES:
                assert stored[name] == observed_ranges[point][name]

    assert rows_verified == 1_168
    return {
        "standpoint_replica_rows": rows_verified,
        "direct": {
            "representation": "exact directional atoms",
            "atom_count_range": [int(atom_min["direct"]), int(atom_max["direct"])],
        },
        "all_specular": {
            "representation": "exact order-1 directional atoms",
            "atom_count_range": [
                int(atom_min["all_specular"]),
                int(atom_max["all_specular"]),
            ],
        },
        "first_diffuse": {
            "representation": "nonzero passive angular output cells",
            "nonzero_cell_count_range": [int(diffuse_min), int(diffuse_max)],
            "cell_capacity": 4096,
        },
        "launch_cells": False,
    }


@claim("replica_convergence_12_to_16")
def replica_convergence_12_to_16() -> dict[str, Any]:
    """The final nested-replica change is authenticated for every fixed route."""
    aggregate = _load_aggregate()
    audit_path = PAPER_ROOT / "figures" / "convergence" / "convergence.audit.json"
    audit = _read_json(audit_path)
    assert audit["schema_version"] in {
        "five_city_convergence_figure_audit_v1",
        "five_city_convergence_figure_audit_v2",
    }
    assert audit["source"]["sha256"] == _sha256(AGGREGATE_PATH)
    result: dict[str, Any] = {}
    for city, expected in EXPECTED_TOTAL_TRANSFER_CHANGE_DB.items():
        record = aggregate["cities"][city]
        transition = record["convergence"]["look_to_look"][-1]
        assert (transition["from_replicas"], transition["to_replicas"]) == (12, 16)
        value = float(transition["total_transfer"]["maximum_abs_db"])
        _assert_close(value, expected)
        audited = audit["cities"][city]
        route_median = float(record["tail_instability"]["look_to_look"][-1]["route_quantile_abs_change_db"]["q50"])
        _assert_close(route_median, float(audited["route_q50_abs_change_db_12_to_16"]))
        result[city] = {
            "maximum_total_transfer_change_db": value,
            "route_median_wbsar_change_db": route_median,
            "p90_standard_error_db": float(audited["p90_standard_error_db_at_16"]),
            "lower_decile_worst_change_db": float(audited["final_lower_decile_worst_abs_change_db_12_to_16"]),
        }
    assert max(item["route_median_wbsar_change_db"] for item in result.values()) < 0.00006
    return {"transition": [12, 16], "cities": result}


@claim("replica_convergence_48_to_64")
def replica_convergence_48_to_64() -> dict[str, Any]:
    """The current-contract 64-replica extension authenticates the two lower tails."""
    report_path = CONVERGENCE64_REPORT_DIR / "current_topology_convergence.json"
    report = _read_json(report_path)
    manifest = _read_json(CONVERGENCE64_REPORT_DIR / "current_topology_convergence_manifest.json")
    assert manifest["schema"] == "current_topology_convergence_artifacts_v1"
    assert _verify_list_manifest(CONVERGENCE64_REPORT_DIR, manifest) == 4
    assert report["schema"] == "current_topology_convergence_v1"
    assert report["contract"]["seeds"] == list(range(7, 71))
    assert report["contract"]["looks"] == [16, 24, 32, 48, 64]
    gates = report["promotion_gates"]
    for name in (
        "all_manifests_and_identities_pass",
        "common_inputs_and_sealed_prefix_exact",
        "component_closure_pass",
    ):
        assert gates[name] == "pass"

    expected = {
        "Korenmarkt": {
            "site": "korenmarkt",
            "q10_change_db": 0.00007229028053766958,
            "shadow_change_db": None,
            "bootstrap_width_db": 0.00022232758404101718,
        },
        "Prague": {
            "site": "prague_staromestske",
            "q10_change_db": 0.000020278871491302847,
            "shadow_change_db": None,
            "bootstrap_width_db": 0.00021814219482941877,
        },
        "Madrid": {
            "site": "madrid_plazamayor",
            "q10_change_db": 0.0000061470067256932265,
            "shadow_change_db": None,
            "bootstrap_width_db": 0.00037805244663012116,
        },
        "Mexico": {
            "site": "mexico_zocalo",
            "status": "stabilized_with_rare_event_behavior",
            "rare_event_ratio": 5737.844506023721,
            "q10_change_db": 0.0034408407908050015,
            "shadow_change_db": 0.012484950417289281,
            "bootstrap_width_db": 0.3638279391681467,
        },
        "Tokyo": {
            "site": "tokyo_hachiko",
            "status": "stabilized",
            "rare_event_ratio": 2.3793787286360097,
            "q10_change_db": 0.004914586580220958,
            "shadow_change_db": 0.010443295223947286,
            "bootstrap_width_db": 0.05379368852716219,
        },
    }
    result = {}
    for city, values in expected.items():
        site = report["sites"][values["site"]]
        q10_at_48 = float(site["looks"]["48"]["components"]["total"]["wbsar_m2_per_kg"]["route_quantiles"]["q10"])
        q10_at_64 = float(site["looks"]["64"]["components"]["total"]["wbsar_m2_per_kg"]["route_quantiles"]["q10"])
        q10_change = abs(10.0 * math.log10(q10_at_64 / q10_at_48))
        interval = site["looks"]["64"]["components"]["total"]["wbsar_m2_per_kg"]["whole_replica_bootstrap"][
            "quantiles"
        ]["q10"]["interval_relative_to_estimate_db"]
        bootstrap_width = float(interval[1]) - float(interval[0])
        _assert_close(q10_change, values["q10_change_db"])
        _assert_close(bootstrap_width, values["bootstrap_width_db"])
        shadow_change = values["shadow_change_db"]
        if shadow_change is None:
            assert site["shadow_standpoints"] == []
            assert values["site"] not in report["lower_tail_assessment"]
        else:
            assert site["shadow_standpoints"]
            tail = report["lower_tail_assessment"][values["site"]]
            assert tail["status"] == values["status"]
            assert all(tail["criteria_pass"].values())
            _assert_close(tail["first_diffuse_replica_max_to_median_ratio"], values["rare_event_ratio"])
            _assert_close(tail["q10_48_to_64_abs_db"]["wbsar_m2_per_kg"], q10_change)
            _assert_close(tail["shadow_point_48_to_64_max_abs_db"], shadow_change)
            _assert_close(tail["q10_bootstrap_95_width_db"], bootstrap_width)
        result[city] = {
            "q10_change_db": q10_change,
            "shadow_point_max_change_db": shadow_change,
            "q10_bootstrap_95_width_db": bootstrap_width,
        }
    return {
        "transition": [48, 64],
        "sealed_prefix_exact": True,
        "lower_tail_status": result,
        "scope": "finite-replica uncertainty conditional on the fixed registered routes",
    }


@claim("ray_reached_evidence_coverage")
def ray_reached_evidence_coverage() -> dict[str, Any]:
    """Pooled retained non-direct transport is partitioned by exact evidence state."""
    report_path = RAY_REACHED_REPORT_DIR / "ray_reached_evidence_coverage.json"
    report = _read_json(report_path)
    manifest = _read_json(RAY_REACHED_REPORT_DIR / "ray_reached_evidence_coverage_manifest.json")
    assert manifest["schema"] == "ray_reached_evidence_coverage_artifacts_v1"
    assert _verify_list_manifest(RAY_REACHED_REPORT_DIR, manifest) == 4
    assert report["schema"] == "ray_reached_evidence_coverage_v1"
    assert report["input_schema"] == "ray_reached_evidence_replay_v1"
    assert report["authenticated"] is True and report["complete"] is True
    assert report["standpoints"] == 73
    assert report["checks"]["closure"]["status"] == "pass"
    assert report["checks"]["parity"]["status"] == "pass"

    headline = report["headline"]
    panorama = float(headline["panorama_informed_sar_fraction"])
    fallback = float(headline["geometric_fallback_sar_fraction"])
    _assert_close(panorama, 0.7590277699014926)
    _assert_close(fallback, 0.24097223009850738)
    _assert_close(panorama + fallback, 1.0)
    expected_table = {
        "order_1_specular": {
            "component": "specular",
            "panorama_informed": 0.806433729576005,
            "no_panorama_evidence": 0.08774141679005237,
            "host_incompatible": 0.10530373486292556,
            "other_fallback": 0.0005211187710170229,
        },
        "first_diffuse": {
            "component": "first_diffuse",
            "panorama_informed": 0.13336718410343135,
            "no_panorama_evidence": 0.44345147385166056,
            "host_incompatible": 0.42313964955266,
            "other_fallback": 0.00004169249224817807,
        },
        "combined_non_direct": {
            "component": "non_direct",
            "panorama_informed": 0.7590277699014926,
            "no_panorama_evidence": 0.11279507119363207,
            "host_incompatible": 0.12768980746784794,
            "other_fallback": 0.0004873514370273951,
        },
    }
    table_rows: dict[str, dict[str, float]] = {}
    for label, values in expected_table.items():
        categories = report["pooled"][values["component"]]["categories"]
        table_row = {
            "panorama_informed": float(categories["atlas_interface"]["body_fraction"]["sar_wb_w_kg"]),
            "no_panorama_evidence": float(categories["geometric_no_panorama_evidence"]["body_fraction"]["sar_wb_w_kg"]),
            "host_incompatible": float(
                categories["geometric_evidence_refused_host_compatibility"]["body_fraction"]["sar_wb_w_kg"]
            ),
            "other_fallback": sum(
                float(categories[name]["body_fraction"]["sar_wb_w_kg"])
                for name in (
                    "geometric_evidence_refused_insufficient_structural_mass",
                    "geometric_evidence_refused_atlas_state",
                    "geometric_fallback_other",
                )
            ),
        }
        for category, expected_value in values.items():
            if category != "component":
                _assert_close(table_row[category], expected_value)
        _assert_close(sum(table_row.values()), 1.0)
        assert categories["nonblocking_woody_atlas"]["body_fraction"]["sar_wb_w_kg"] == 0.0
        table_rows[label] = table_row
    assert report["pooled"]["specular"]["event_count"] == 689_888
    assert report["pooled"]["first_diffuse"]["event_count"] == 95_389_603
    return {
        "denominator": headline["denominator"],
        "non_direct_wbsar_fraction": {
            "panorama_informed": panorama,
            "geometric_fallback": fallback,
        },
        "table_rows": table_rows,
        "accepted_events": {"order_1_specular": 689_888, "first_diffuse": 95_389_603},
    }


@claim("controlled_depth1_validation")
def controlled_depth1_validation() -> dict[str, Any]:
    """Controlled depth-1 validation values are recomputed from authenticated sidecars."""
    audit = _read_json(PAPER_ROOT / "figures" / "validation" / "validation.audit.json")
    assert audit["schema_version"] == "controlled_depth1_validation_figure_audit_v1"
    assert audit["controlled_experiment"]["interaction_depth"] == 1
    assert audit["controlled_experiment"]["sources"] == 27
    assert audit["controlled_experiment"]["receivers"] == 6
    assert audit["estimators"]["deterministic_surface_quadrature"]["surface_samples"] == 2_097_152

    for source in audit["sources"].values():
        path = SEMANTIC_TWIN_ROOT / source["path_from_semantic_twin_root"]
        assert _sha256(path) == source["sha256"], f"validation source drifted: {path}"

    values = audit["plotted_values"]
    quadrature = [float(value) for value in values["deterministic_surface_quadrature_m_inv2"]]
    adjoint = [float(value) for value in values["adjoint_first_diffuse_mean_m_inv2"]]
    forward = [float(value) for value in values["independent_forward_tracer_mean_m_inv2"]]
    adjoint_errors = _abs_db_errors(adjoint, quadrature)
    forward_errors = _abs_db_errors(forward, quadrature)
    adjoint_median = _quantile(adjoint_errors, 0.5)
    forward_median = _quantile(forward_errors, 0.5)
    _assert_close(adjoint_median, 0.024039060615950708)
    _assert_close(max(adjoint_errors), 0.061565053096781466)
    _assert_close(forward_median, 0.0008604960835487314)
    _assert_close(max(forward_errors), 0.022231233245833856)

    raw = _read_json(OUTPUT_ROOT / "cross_validation" / "forward_sionna_open_depth1_50k_open_square.json")
    adjoint_forward_bounced_max = float(raw["comparison"]["bounced"]["max_abs_db"])
    adjoint_forward_total_max = float(raw["comparison"]["total"]["max_abs_db"])
    _assert_close(adjoint_forward_bounced_max, 0.06213970570928458)
    _assert_close(adjoint_forward_total_max, 0.03443936192255103)
    return {
        "scope": "controlled open-square first-diffuse component validation",
        "adjoint_vs_quadrature_bounced_abs_error_db": {
            "median": adjoint_median,
            "maximum": max(adjoint_errors),
        },
        "forward_vs_quadrature_bounced_abs_error_db": {
            "median": forward_median,
            "maximum": max(forward_errors),
        },
        "adjoint_vs_forward_abs_error_db": {
            "bounced_maximum": adjoint_forward_bounced_max,
            "total_maximum": adjoint_forward_total_max,
        },
    }


@claim("paired_material_evidence_control")
def paired_material_evidence_control() -> dict[str, Any]:
    """Madrid and Mexico controls preserve the campaign except for the material layer."""
    expected = {
        "Madrid": {
            "q10": 0.23336114034232122,
            "q50": 0.24866405147308124,
            "q90": 0.2686331876751526,
        },
        "Mexico": {
            "q10": 24.83505022714946,
            "q50": -0.15810883480369037,
            "q90": 0.10387367330083926,
        },
    }
    results: dict[str, Any] = {}
    for city in ("Madrid", "Mexico"):
        report_root = CAMPAIGN_ROOT / "material_evidence_ablation" / CITY_SLUGS[city]
        report = _read_json(report_root / "material_evidence_ablation.json")
        report_manifest = _read_json(report_root / "material_evidence_ablation_manifest.json")
        assert report["schema"] == "material_evidence_ablation_v1"
        assert report["compatibility"]["status"] == "pass"
        assert _verify_list_manifest(report_root, report_manifest) == 4
        atlas_root, atlas_identity = _verify_campaign(city)
        geometric_root, geometric_identity = _verify_campaign(city, geometric=True)
        # Reports retain the production machine's absolute path. Match the
        # authenticated campaign directory name so a copied artifact bundle
        # remains auditable from another checkout.
        assert Path(report["campaigns"]["atlas"]["directory"]).name == atlas_root.name
        assert Path(report["campaigns"]["geometric"]["directory"]).name == geometric_root.name
        assert report["campaigns"]["atlas"]["identity_sha256"] == atlas_identity["sha256"]
        assert report["campaigns"]["geometric"]["identity_sha256"] == geometric_identity["sha256"]
        assert report["seeds"] == EXPECTED_SEEDS
        assert report["standpoints"] == EXPECTED_STANDPOINTS[city]

        metric = report["metrics"]["wbsar_m2_per_kg"]
        quantiles = metric["route_quantiles"]
        recomputed: dict[str, float] = {}
        for name in ("q10", "q50", "q90"):
            value = 10.0 * math.log10(quantiles["atlas"][name] / quantiles["geometric"][name])
            _assert_close(value, expected[city][name])
            _assert_close(value, metric["route_quantile_change_db"][name])
            recomputed[name] = value

        direct = report["component_decomposition"]["direct"]["wbsar_m2_per_kg"]
        for name in ("q50", "q90"):
            assert direct["route_quantile_change_db"][name] == 0.0
        if city == "Madrid":
            _assert_close(
                report["component_decomposition"]["all_specular"]["wbsar_m2_per_kg"]["route_quantile_change_db"]["q50"],
                1.888528380371959,
            )
            _assert_close(
                report["component_decomposition"]["first_diffuse"]["wbsar_m2_per_kg"]["route_quantile_change_db"][
                    "q50"
                ],
                -12.431544270210049,
            )
        results[city] = recomputed
    return {
        "change_definition": "10 log10(atlas/geometric)",
        "wbsar_route_quantile_change_db": results,
        "madrid_component_q50_change_db": {
            "all_specular": 1.888528380371959,
            "first_diffuse": -12.431544270210049,
        },
        "interpretation": "paired evidence-layer sensitivity, not a reflectance-only or accuracy test",
    }


@claim("roofline_budget_sensitivity")
def roofline_budget_sensitivity() -> dict[str, Any]:
    """Every cheaper current-contract budget arm fails the directional gate."""
    root = OUTPUT_ROOT / "experiments" / "roofline_budget_sensitivity_v1"
    report_path = root / "roofline_budget_sensitivity_v1.json"
    manifest_path = root / "roofline_budget_sensitivity_v1_manifest.json"
    report = _read_json(report_path)
    manifest = _read_json(manifest_path)
    assert report["schema"] == "aegis.roofline-budget-sensitivity-report.v1"
    assert manifest["schema"] == "aegis.roofline-budget-sensitivity-artifacts.v1"
    assert manifest["report_schema"] == report["schema"]
    artifacts = manifest["artifacts"]
    for name, record in artifacts.items():
        path = root / name
        assert path.is_file(), f"manifested budget artifact is missing: {path}"
        assert path.stat().st_size == int(record["bytes"])
        assert _sha256(path) == record["sha256"], f"budget artifact hash mismatch: {path}"

    assert report["baseline"] == {"rays": 200_000, "cells": 4096}
    expected = {
        (25_000, 4096): (0.8774980143368515, 0.7073621561957917),
        (50_000, 4096): (0.6789419645795945, 0.5638407601543206),
        (100_000, 4096): (0.40021795550889805, 0.21725892861448737),
        (200_000, 1024): (0.49126480809041534, 0.0020697456764675313),
        (200_000, 2048): (0.45543106112995413, 0.0008867400199698488),
    }
    rows = {(int(row["rays"]), int(row["cells"])): row for row in report["budgets"]}
    assert set(expected).issubset(rows)
    baseline = rows[(200_000, 4096)]
    ray_reduced_arms = ((25_000, 4096), (50_000, 4096), (100_000, 4096))
    maximum_q50 = 0.0
    ray_reduced_q90_variance_time_ratios: list[float] = []
    results: dict[str, dict[str, float]] = {}
    for arm, (directional_expected, mexico_expected) in expected.items():
        row = rows[arm]
        sites = row["sites"]
        directional = max(
            float(site["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"]) for site in sites.values()
        )
        mexico = sites["mexico_zocalo"]
        shadow_change = float(mexico["normalized_wbSAR"]["maximum_absolute_db"])
        _assert_close(directional, directional_expected)
        _assert_close(shadow_change, mexico_expected)
        assert directional > 0.1
        assert row["recommendation"]["migration_recommended"] is False
        for site in sites.values():
            invariance = site["deterministic_invariance"]
            assert invariance["status"] == "pass"
            for component in ("direct", "all_specular"):
                assert invariance[component]["body_metrics_byte_exact"] is True
                assert invariance[component]["raw_byte_exact"] is True
        maximum_q50 = max(
            maximum_q50,
            *(abs(float(site["normalized_wbSAR"]["route_quantile_difference_db"]["q50"])) for site in sites.values()),
        )
        results[f"rays_{arm[0]}_cells_{arm[1]}"] = {
            "directional_q90_normalized_l1_max": directional,
            "mexico_shadow_wbsar_maximum_abs_db": shadow_change,
        }
    _assert_close(maximum_q50, 0.0007973445109199489)
    ray_25000_wall_time_ratios = [
        float(site["timing"]["estimator_wall_seconds"]["ratio"]) for site in rows[(25_000, 4096)]["sites"].values()
    ]
    ray_25000_wall_time_ratio_range = {
        "minimum": min(ray_25000_wall_time_ratios),
        "maximum": max(ray_25000_wall_time_ratios),
    }
    _assert_close(ray_25000_wall_time_ratio_range["minimum"], 0.9912406567927025)
    _assert_close(ray_25000_wall_time_ratio_range["maximum"], 1.0638558906935487)
    baseline_specular_seconds = [
        float(site["timing"]["specular_seconds"]["seconds"]) for site in baseline["sites"].values()
    ]
    baseline_specular_seconds_range = {
        "minimum": min(baseline_specular_seconds),
        "maximum": max(baseline_specular_seconds),
    }
    _assert_close(baseline_specular_seconds_range["minimum"], 8.058428761999494)
    _assert_close(baseline_specular_seconds_range["maximum"], 23.785232650004218)
    baseline_stochastic_trace_seconds = [
        float(site["timing"]["stochastic_trace_seconds"]["seconds"]) for site in baseline["sites"].values()
    ]
    baseline_stochastic_trace_seconds_range = {
        "minimum": min(baseline_stochastic_trace_seconds),
        "maximum": max(baseline_stochastic_trace_seconds),
    }
    _assert_close(baseline_stochastic_trace_seconds_range["minimum"], 1.1504173969979092)
    _assert_close(baseline_stochastic_trace_seconds_range["maximum"], 2.3965218109888156)
    for arm in ray_reduced_arms:
        ray_reduced_q90_variance_time_ratios.extend(
            float(site["variance_time_efficiency"]["q90_ratio"]) for site in rows[arm]["sites"].values()
        )
    minimum_ray_reduced_q90_variance_time_ratio = min(ray_reduced_q90_variance_time_ratios)
    _assert_close(minimum_ray_reduced_q90_variance_time_ratio, 3.1598358725295483)
    assert all(row["status"] == "pass" for row in report["sealed_baseline_replay_parity"].values())
    return {
        "production_budget": report["baseline"],
        "migration_recommended": False,
        "maximum_abs_route_q50_wbsar_difference_db": maximum_q50,
        "ray_25000_estimator_wall_time_ratio_range": ray_25000_wall_time_ratio_range,
        "baseline_specular_seconds_range": baseline_specular_seconds_range,
        "baseline_stochastic_trace_seconds_range": baseline_stochastic_trace_seconds_range,
        "minimum_ray_reduced_q90_variance_time_ratio": minimum_ray_reduced_q90_variance_time_ratio,
        "cheaper_arms": results,
    }
