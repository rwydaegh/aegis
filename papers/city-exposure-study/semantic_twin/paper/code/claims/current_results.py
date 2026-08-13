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

AGGREGATE_DIR = CAMPAIGN_ROOT / "current_five_city_first_material_interaction"
AGGREGATE_PATH = AGGREGATE_DIR / "current_five_city_first_material_interaction.json"
AGGREGATE_MANIFEST_PATH = AGGREGATE_DIR / "current_five_city_first_material_interaction_manifest.json"

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
