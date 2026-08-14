"""Promote the authenticated ray-reached coverage report figure into the paper."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIGURE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "outputs" / "experiments" / "ray_reached_evidence_coverage_v1" / "report"
SOURCE_STEM = "ray_reached_evidence_coverage"
OUTPUT_STEM = "ray_reached_evidence"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest_path = SOURCE_DIR / f"{SOURCE_STEM}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ray_reached_evidence_coverage_artifacts_v1":
        raise ValueError("unexpected ray-reached report manifest schema")
    records = {record["path"]: record for record in manifest["files"]}
    for record in records.values():
        source = SOURCE_DIR / record["path"]
        if source.stat().st_size != record["bytes"] or _sha256(source) != record["sha256"]:
            raise ValueError(f"ray-reached report artifact failed authentication: {source}")

    outputs = {}
    for suffix in ("pdf", "png"):
        source_name = f"{SOURCE_STEM}.{suffix}"
        destination = FIGURE_DIR / f"{OUTPUT_STEM}.{suffix}"
        shutil.copyfile(SOURCE_DIR / source_name, destination)
        outputs[suffix] = {
            "path": destination.name,
            "bytes": destination.stat().st_size,
            "sha256": _sha256(destination),
        }

    report_path = SOURCE_DIR / f"{SOURCE_STEM}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema") != "ray_reached_evidence_coverage_v1" or not report.get("complete"):
        raise ValueError("ray-reached report is incomplete")
    audit = {
        "schema": "paper_ray_reached_evidence_figure_v1",
        "source": {
            "report_path": str(report_path.relative_to(ROOT)),
            "report_sha256": _sha256(report_path),
            "manifest_path": str(manifest_path.relative_to(ROOT)),
            "manifest_sha256": _sha256(manifest_path),
        },
        "headline": report["headline"],
        "outputs": outputs,
    }
    (FIGURE_DIR / f"{OUTPUT_STEM}.audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
