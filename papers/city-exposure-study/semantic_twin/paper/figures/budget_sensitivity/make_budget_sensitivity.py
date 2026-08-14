"""Authenticate and stage the compact roofline-budget sensitivity figure.

The numerical reporter owns the figure. This wrapper verifies the report and
its artifact manifest before copying the PDF and PNG into the paper tree. It
then writes a small paper-facing audit. Run with ``--check`` to validate the
source without writing figure assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


SEMANTIC_TWIN_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REPORT_DIR = SEMANTIC_TWIN_ROOT / "outputs" / "experiments" / "roofline_budget_sensitivity_v1"
REPORT = REPORT_DIR / "roofline_budget_sensitivity_v1.json"
MANIFEST = REPORT_DIR / "roofline_budget_sensitivity_v1_manifest.json"
SOURCE_PDF = REPORT_DIR / "roofline_budget_sensitivity_v1.pdf"
SOURCE_PNG = REPORT_DIR / "roofline_budget_sensitivity_v1.png"
OUTPUT_PDF = HERE / "budget_sensitivity.pdf"
OUTPUT_PNG = HERE / "budget_sensitivity.png"
AUDIT = HERE / "budget_sensitivity.audit.json"

REPORT_SCHEMA = "aegis.roofline-budget-sensitivity-report.v1"
MANIFEST_SCHEMA = "aegis.roofline-budget-sensitivity-artifacts.v1"
EXPECTED_ARMS = ((25_000, 4096), (50_000, 4096), (100_000, 4096), (200_000, 1024), (200_000, 2048))
EXPECTED_DIRECTIONAL_Q90 = {
    (25_000, 4096): 0.8774980143368515,
    (50_000, 4096): 0.6789419645795945,
    (100_000, 4096): 0.40021795550889805,
    (200_000, 1024): 0.49126480809041534,
    (200_000, 2048): 0.45543106112995413,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _artifact(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    record = manifest.get("artifacts", {}).get(path.name)
    if not isinstance(record, dict):
        raise ValueError(f"manifest has no record for {path.name}")
    if not path.is_file():
        raise ValueError(f"missing report artifact: {path}")
    if path.stat().st_size != int(record["bytes"]):
        raise ValueError(f"byte count mismatch: {path}")
    if _sha256(path) != record["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {path}")
    return record


def authenticate() -> dict[str, Any]:
    """Return a compact, authenticated report summary for the manuscript."""
    report = _read_json(REPORT)
    manifest = _read_json(MANIFEST)
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unexpected budget-sensitivity report schema")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("report_schema") != REPORT_SCHEMA:
        raise ValueError("unexpected budget-sensitivity manifest schema")
    if report.get("baseline") != {"rays": 200_000, "cells": 4096}:
        raise ValueError("report does not retain the declared production baseline")
    artifacts = {path.name: _artifact(manifest, path) for path in (REPORT, SOURCE_PDF, SOURCE_PNG)}
    arms = {(int(row["rays"]), int(row["cells"])): row for row in report.get("budgets", [])}
    if not set(EXPECTED_ARMS).issubset(arms):
        raise ValueError("report lacks a required cheaper budget arm")

    directional_q90: dict[str, float] = {}
    for arm, expected in EXPECTED_DIRECTIONAL_Q90.items():
        row = arms[arm]
        values = [
            float(site["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"])
            for site in row["sites"].values()
        ]
        maximum = max(values)
        if abs(maximum - expected) > 1.0e-12 or maximum <= 0.1:
            raise ValueError(f"directional gate evidence drifted for {arm}")
        if row["recommendation"]["migration_recommended"] is not False:
            raise ValueError(f"report unexpectedly recommends migrating {arm}")
        if not all(site["deterministic_invariance"]["status"] == "pass" for site in row["sites"].values()):
            raise ValueError(f"deterministic invariance failed for {arm}")
        directional_q90[f"rays_{arm[0]}_cells_{arm[1]}"] = maximum

    parity = report.get("sealed_baseline_replay_parity", {})
    if not parity or not all(row.get("status") == "pass" for row in parity.values()):
        raise ValueError("sealed baseline replay parity failed")
    return {
        "source_report_sha256": artifacts[REPORT.name]["sha256"],
        "source_manifest_sha256": _sha256(MANIFEST),
        "schedule_identity_sha256": manifest["schedule_identity_sha256"],
        "directional_q90_normalized_l1_max": directional_q90,
        "baseline_replay_parity": "pass",
        "source_artifacts": artifacts,
    }


def stage() -> dict[str, Any]:
    """Copy authenticated figure assets and write their paper-facing audit."""
    audit = authenticate()
    HERE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_PDF, OUTPUT_PDF)
    shutil.copyfile(SOURCE_PNG, OUTPUT_PNG)
    audit["schema_version"] = "roofline_budget_sensitivity_figure_audit_v1"
    audit["outputs"] = {
        "pdf": {"path": OUTPUT_PDF.name, "bytes": OUTPUT_PDF.stat().st_size, "sha256": _sha256(OUTPUT_PDF)},
        "png": {"path": OUTPUT_PNG.name, "bytes": OUTPUT_PNG.stat().st_size, "sha256": _sha256(OUTPUT_PNG)},
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="authenticate source files without staging assets")
    args = parser.parse_args(argv)
    audit = authenticate() if args.check else stage()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
