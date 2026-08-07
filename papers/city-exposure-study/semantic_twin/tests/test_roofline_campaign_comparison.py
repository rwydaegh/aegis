"""Small synthetic fixtures for paired roofline campaign reports."""

from __future__ import annotations

import hashlib
import json
import copy
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.exposure.roofline_campaign import (
    BODY_METRICS,
    COMPONENTS,
    REFERENCE_FIELDS,
    SCHEMA_VERSION,
    TIMING_FIELDS,
)
from semantic_twin.exposure.roofline_setup import load_roofline_setup
from semantic_twin.report.roofline_campaign_comparison import (
    CampaignComparisonError,
    _cdf_movement,
    _normalise_launch_sampling,
    _route_cdf,
    _standard_error,
    compare_campaigns,
    write_report,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_campaign(
    root: Path,
    mode: str,
    *,
    seeds: tuple[int, ...] = tuple(range(1, 17)),
    incompatible: bool = False,
    suffix_mode: str = "sampled",
) -> None:
    points = 3
    identity_data = {
        "schema_version": SCHEMA_VERSION,
        "configuration": {
            "site": "fixture",
            "cohort": "primary_semantic_route",
            "material_mode": "atlas",
            "planned_seeds": list(seeds),
            "convergence_looks": [4, 8, 12, 16],
        },
        "transport": {
            "estimator": {"configuration": {"specular_suffix_mode": suffix_mode}},
            "tracer": {"configuration": {"rays": 32, "launch_sampling": mode}},
        },
        "walk": {"points": [[0.0, 0.0, 1.5], [1.0, 0.0, 1.5], [2.0, 0.0, 1.5]]},
    }
    if incompatible:
        identity_data["configuration"]["material_mode"] = "walk"
    identity_hash = hashlib.sha256(
        json.dumps(identity_data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    identity = {"sha256": identity_hash, "data": identity_data}
    root.mkdir(parents=True)
    (root / "campaign_identity.json").write_text(json.dumps(identity), encoding="utf-8")
    checkpoint = root / "checkpoint"
    replicas = checkpoint / "replicas"
    replicas.mkdir(parents=True)
    committed = []
    for seed_index, seed in enumerate(seeds):
        raw = np.zeros((points, len(COMPONENTS)), dtype=np.float64)
        raw[:, 0] = [1.0, 2.0, 3.0]
        raw[:, 1] = 0.25 + seed_index * (0.01 if mode == "iid" else 0.02)
        raw[:, 2] = [0.10 + seed_index * (0.02 if mode == "iid" else 0.03), 0.2, 0.3]
        raw[:, 3] = np.sum(raw[:, :3], axis=1)
        body = np.zeros((points, len(COMPONENTS), len(BODY_METRICS)), dtype=np.float64)
        body[:, :, 0] = raw
        body[:, :, 1] = raw
        body[:, :, 2] = raw
        body[:, :, 3] = raw
        body[:, :, 4] = raw
        body[:, :, 5] = raw
        timings = np.ones((points, len(TIMING_FIELDS)), dtype=np.float64) * (seed_index + 1)
        field_meta = np.zeros((points, 7), dtype=np.float64)
        reference = np.ones((points, len(REFERENCE_FIELDS)), dtype=np.float64)
        shard = replicas / f"seed_{seed:010d}.npz"
        np.savez_compressed(
            shard, raw_transfer=raw, body_metrics=body, timings=timings, field_meta=field_meta, reference=reference
        )
        diagnostics = []
        for _ in range(points):
            diagnostic = {
                "sampled_specular_suffix": {
                    "enabled": suffix_mode == "sampled",
                    "trials": 100 if suffix_mode == "sampled" else 0,
                    "accepted": 2 + seed_index if suffix_mode == "sampled" else 0,
                    "candidates": 100 if suffix_mode == "sampled" else 0,
                }
            }
            if suffix_mode == "sampled":
                diagnostic["all_specular_transfer"] = 0.25
            diagnostics.append(diagnostic)
        diagnostics_path = replicas / f"seed_{seed:010d}.json"
        diagnostics_path.write_text(json.dumps(diagnostics), encoding="utf-8")
        committed.append(
            {
                "seed": seed,
                "path": f"replicas/{shard.name}",
                "sha256": _sha256(shard),
                "diagnostics_path": f"replicas/{diagnostics_path.name}",
                "diagnostics_sha256": _sha256(diagnostics_path),
            }
        )
    checkpoint_document = {
        "schema_version": SCHEMA_VERSION,
        "identity_sha256": identity["sha256"],
        "points": points,
        "surfaces": 1,
        "components": list(COMPONENTS),
        "body_metrics": list(BODY_METRICS),
        "reference_fields": list(REFERENCE_FIELDS),
        "timing_fields": list(TIMING_FIELDS),
        "convergence_looks": [4, 8, 12, 16],
        "committed": committed,
    }
    (checkpoint / "index.json").write_text(json.dumps(checkpoint_document), encoding="utf-8")
    locations = [{"standpoint": index, "position_m": [float(index), 0.0, 1.5]} for index in range(points)]
    (root / "locations.jsonl").write_text("\n".join(json.dumps(row) for row in locations) + "\n", encoding="utf-8")
    (root / "summary.json").write_text(json.dumps({"replicas": len(seeds), "seeds": list(seeds)}), encoding="utf-8")
    files = {
        "campaign_identity.json": _sha256(root / "campaign_identity.json"),
        "locations.jsonl": _sha256(root / "locations.jsonl"),
        "summary.json": _sha256(root / "summary.json"),
        "checkpoint/index.json": _sha256(checkpoint / "index.json"),
    }
    files.update({f"checkpoint/{entry['path']}": entry["sha256"] for entry in committed})
    files.update({f"checkpoint/{entry['diagnostics_path']}": entry["diagnostics_sha256"] for entry in committed})
    (root / "manifest.json").write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "identity_sha256": identity["sha256"], "files": files}),
        encoding="utf-8",
    )


def test_paired_report_contains_differences_cdf_variances_timings_and_suffix(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    report = compare_campaigns(iid, fibonacci)

    look = report["looks"]["16"]
    assert report["compatibility"]["paired_seeds"] == list(range(1, 17))
    assert look["linear_db_differences"]["raw_transfer"]["direct"]["difference_linear"] == [0.0, 0.0, 0.0]
    assert "q10" in look["route_cdf"]["raw_transfer"]["total"]["iid"]["linear"]
    assert "wasserstein" in look["route_cdf"]["raw_transfer"]["total"]
    assert "stochastic_raw_transfer" in look["across_seed_variance_ratios"]
    assert "stochastic_trace_seconds" in look["component_work_timings"]
    assert look["deterministic_invariants"]["direct"]["status"] == "pass"
    assert look["deterministic_invariants"]["direct_body_metrics"]["status"] == "pass"
    assert look["deterministic_invariants"]["all_specular"]["status"] == "pass"
    assert look["sampled_suffix"]["iid"]["accepted"] > 0
    assert look["sampled_suffix"]["impact"]["status"] == "not_persisted"
    convergence = report["within_mode_convergence"]["iid"]
    assert "4_to_8" in convergence["look_to_look"]
    assert "maximum_abs_db" in convergence["look_to_look"]["4_to_8"]["total_transfer"]["pointwise"]
    assert "p90_db_delta_approximation" in convergence["standard_error"]["16"]["total_transfer"]


def test_incompatible_campaigns_are_rejected(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci", incompatible=True)

    with pytest.raises(CampaignComparisonError, match="incompatible"):
        compare_campaigns(iid, fibonacci)


def test_unpaired_seed_prefix_is_rejected(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci", seeds=tuple(range(2, 18)))

    with pytest.raises(CampaignComparisonError, match="paired by seed"):
        compare_campaigns(iid, fibonacci)


def test_single_replica_standard_error_is_unavailable_not_zero() -> None:
    report = _standard_error(np.asarray([[2.0, 4.0]], dtype=np.float64))

    assert report["replicas"] == 1
    assert report["status"] == "unavailable"
    assert report["reason"] == "at least two replicas are required for a standard error"
    assert report["by_standpoint_linear"] is None
    assert report["by_standpoint_db_delta_approximation"] is None
    assert report["p90_linear"] is None
    assert report["maximum_linear"] is None
    assert report["p90_db_delta_approximation"] is None
    assert report["maximum_db_delta_approximation"] is None


def test_route_cdf_wasserstein_and_db_differences_use_linear_power_math() -> None:
    report = _route_cdf(
        np.asarray([1.0, 10.0], dtype=np.float64),
        np.asarray([10.0, 100.0], dtype=np.float64),
    )

    assert report["wasserstein"] == {"linear": pytest.approx(49.5), "db": pytest.approx(10.0)}
    assert report["difference"]["linear"]["q50"] == pytest.approx(49.5)
    assert report["difference"]["db"]["q50"] == pytest.approx(10.0)
    assert report["paired_point_difference"]["db"] == pytest.approx([10.0, 10.0])


def test_zero_values_leave_db_cdf_and_wasserstein_explicitly_unavailable() -> None:
    report = _route_cdf(
        np.asarray([0.0, 1.0], dtype=np.float64),
        np.asarray([0.0, 10.0], dtype=np.float64),
    )

    assert report["wasserstein"]["db"] is None
    assert report["iid"]["db"]["count"] == 1
    assert report["rotated_fibonacci"]["db"]["count"] == 1
    assert report["difference"]["db"]["minimum"] is None
    assert report["paired_point_difference"]["db"] == [None, 10.0]


def test_look_movement_labels_are_not_sampling_modes() -> None:
    report = _cdf_movement(
        np.asarray([1.0, 2.0], dtype=np.float64),
        np.asarray([2.0, 4.0], dtype=np.float64),
        previous_look=4,
        current_look=8,
    )

    assert report["from_look"] == 4
    assert report["to_look"] == 8
    assert "from" in report and "to" in report


def test_exact_suffix_without_persisted_all_specular_is_not_called_deterministic(
    tmp_path: Path,
) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid", suffix_mode="exact")
    _write_campaign(fibonacci, "rotated_fibonacci", suffix_mode="exact")

    report = compare_campaigns(iid, fibonacci)

    assert report["looks"]["16"]["deterministic_invariants"]["all_specular"]["status"] == "unavailable"


def test_checkpoint_hash_and_path_integrity_are_required(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    checkpoint = iid / "checkpoint" / "index.json"
    document = json.loads(checkpoint.read_text(encoding="utf-8"))
    document["committed"][0].pop("sha256")
    checkpoint.write_text(json.dumps(document), encoding="utf-8")
    manifest = iid / "manifest.json"
    manifest_document = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_document["files"]["checkpoint/index.json"] = _sha256(checkpoint)
    manifest.write_text(json.dumps(manifest_document), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="hashes are required"):
        compare_campaigns(iid, fibonacci)

    iid_path = tmp_path / "iid_path"
    _write_campaign(iid_path, "iid")
    checkpoint = iid_path / "checkpoint" / "index.json"
    document = json.loads(checkpoint.read_text(encoding="utf-8"))
    document["committed"][0]["path"] = "../outside.npz"
    checkpoint.write_text(json.dumps(document), encoding="utf-8")
    manifest = iid_path / "manifest.json"
    manifest_document = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_document["files"]["checkpoint/index.json"] = _sha256(checkpoint)
    manifest.write_text(json.dumps(manifest_document), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="escapes the campaign directory"):
        compare_campaigns(iid_path, fibonacci)


def test_manifest_must_cover_required_campaign_artifacts(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    manifest_path = iid / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].pop("locations.jsonl")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="manifest"):
        compare_campaigns(iid, fibonacci)


def test_locations_must_keep_three_finite_coordinates(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    for root in (iid, fibonacci):
        locations_path = root / "locations.jsonl"
        locations = [json.loads(line) for line in locations_path.read_text(encoding="utf-8").splitlines()]
        locations[0]["position_m"] = [0.0, 0.0]
        locations_path.write_text("\n".join(json.dumps(row) for row in locations) + "\n", encoding="utf-8")
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["locations.jsonl"] = _sha256(locations_path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="locations"):
        compare_campaigns(iid, fibonacci)


def test_identity_wrapper_hash_is_verified_before_pairing(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    for root in (iid, fibonacci):
        identity_path = root / "campaign_identity.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["data"]["tampered_after_sealing"] = True
        identity_path.write_text(json.dumps(identity), encoding="utf-8")
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["campaign_identity.json"] = _sha256(identity_path)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="identity SHA-256 wrapper is invalid"):
        compare_campaigns(iid, fibonacci)


def test_written_report_is_strict_json_without_nan(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    output = write_report(iid, fibonacci, tmp_path / "comparison.json")
    document = json.loads(output.read_text(encoding="utf-8"))

    json.dumps(document, allow_nan=False)


def test_nonfinite_optional_diagnostics_are_rejected(tmp_path: Path) -> None:
    iid = tmp_path / "iid"
    fibonacci = tmp_path / "fibonacci"
    _write_campaign(iid, "iid")
    _write_campaign(fibonacci, "rotated_fibonacci")

    index_path = iid / "checkpoint" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    diagnostics_path = iid / "checkpoint" / index["committed"][0]["diagnostics_path"]
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    diagnostics[0]["all_specular_transfer"] = float("nan")
    diagnostics_path.write_text(json.dumps(diagnostics), encoding="utf-8")
    index["committed"][0]["diagnostics_sha256"] = _sha256(diagnostics_path)
    index_path.write_text(json.dumps(index), encoding="utf-8")
    manifest_path = iid / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["checkpoint/index.json"] = _sha256(index_path)
    manifest["files"][f"checkpoint/{index['committed'][0]['diagnostics_path']}"] = _sha256(diagnostics_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(CampaignComparisonError, match="finite"):
        compare_campaigns(iid, fibonacci)


@pytest.mark.parametrize("site", ["korenmarkt", "prague"])
def test_shipped_convergence_configs_seal_the_same_campaign_identity(site: str) -> None:
    root = Path(__file__).resolve().parents[1]
    iid = load_roofline_setup(root / f"config/roofline_campaign_{site}_convergence_cuda_iid.json")
    fibonacci = load_roofline_setup(root / f"config/roofline_campaign_{site}_convergence_cuda_rotated_fibonacci.json")

    assert iid.campaign.identity_dict() == fibonacci.campaign.identity_dict()
    assert iid.run.tag != fibonacci.run.tag
    assert iid.campaign.output_dir != fibonacci.campaign.output_dir
    assert iid.run.launch_sampling == "iid"
    assert fibonacci.run.launch_sampling == "rotated_fibonacci"

    iid_identity = {
        "configuration": iid.campaign.identity_dict(),
        "transport": {"tracer": {"configuration": {"launch_sampling": iid.run.launch_sampling}}},
    }
    fibonacci_identity = copy.deepcopy(iid_identity)
    fibonacci_identity["transport"]["tracer"]["configuration"]["launch_sampling"] = fibonacci.run.launch_sampling
    left, _ = _normalise_launch_sampling(iid_identity)
    right, _ = _normalise_launch_sampling(fibonacci_identity)
    assert left == right
