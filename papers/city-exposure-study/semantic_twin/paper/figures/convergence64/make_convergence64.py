"""Plot the authenticated 64-replica convergence report for the supplement."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
FIGURE_DIR = Path(__file__).resolve().parent
PAPER_ROOT = FIGURE_DIR.parents[1]
SOURCE_DIR = ROOT / "outputs" / "experiments" / "current_topology_convergence64_v1" / "report"
SOURCE_STEM = "current_topology_convergence"
OUTPUT_STEM = "convergence64"

sys.path.insert(0, str(PAPER_ROOT / "figures"))
from _style.paper_style import paper_style, save_figure  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_report() -> tuple[dict, Path, Path]:
    manifest_path = SOURCE_DIR / f"{SOURCE_STEM}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "current_topology_convergence_artifacts_v1":
        raise ValueError("unexpected convergence report manifest schema")
    for record in manifest["files"]:
        source = SOURCE_DIR / record["path"]
        if source.stat().st_size != record["bytes"] or _sha256(source) != record["sha256"]:
            raise ValueError(f"convergence report artifact failed authentication: {source}")

    report_path = SOURCE_DIR / f"{SOURCE_STEM}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    gates = report.get("promotion_gates", {})
    required = (
        "all_manifests_and_identities_pass",
        "common_inputs_and_sealed_prefix_exact",
        "component_closure_pass",
    )
    if report.get("schema") != "current_topology_convergence_v1" or any(gates.get(name) != "pass" for name in required):
        raise ValueError("convergence report has an incomplete authentication gate")
    return report, report_path, manifest_path


def _plot(report: dict) -> None:
    looks = np.asarray((16, 24, 32, 48, 64))
    sites = (
        ("korenmarkt", "Korenmarkt"),
        ("prague_staromestske", "Prague"),
        ("madrid_plazamayor", "Madrid"),
        ("mexico_zocalo", "Mexico City"),
        ("tokyo_hachiko", "Tokyo Hachiko"),
    )
    colors = ("#0072B2", "#009E73", "#CC79A7", "#D55E00", "#E69F00")

    with paper_style("double", height_ratio=0.34, use_tex=True):
        figure, (left, right) = plt.subplots(1, 2)
        for (key, label), color in zip(sites, colors, strict=True):
            values = [
                report["sites"][key]["looks"][str(look)]["components"]["total"]["wbsar_m2_per_kg"][
                    "change_from_sealed_16_db"
                ]["q10"]
                for look in looks
            ]
            left.plot(looks, values, marker="o", markersize=3.0, color=color, label=label)

        shadow = report["strata"]["six_shadowed_points"]["looks"]
        for subset, label, color in (
            (slice(0, 3), "Mexico City", colors[3]),
            (slice(3, 6), "Tokyo Hachiko", colors[4]),
        ):
            values = [0.0]
            for previous, current in zip(looks[:-1], looks[1:], strict=True):
                previous_values = np.asarray(shadow[str(previous)]["pointwise"]["wbsar_m2_per_kg"]["estimate"][subset])
                current_values = np.asarray(shadow[str(current)]["pointwise"]["wbsar_m2_per_kg"]["estimate"][subset])
                values.append(float(np.max(np.abs(10.0 * np.log10(current_values / previous_values)))))
            right.plot(looks, values, marker="s", markersize=3.0, color=color, label=label)

        left.set_title("(a) Route lower-tail movement", loc="left")
        left.set_ylabel(r"wbSAR $q_{10}$ change from fixed 16 (dB)")
        left.legend(ncol=2, loc="upper right")
        right.set_title("(b) Shadowed route points", loc="left")
        right.set_ylabel("Maximum pointwise wbSAR change (dB)")
        right.legend(loc="upper right")
        for axis in (left, right):
            axis.set_xlabel("Replica look")
            axis.set_xticks(looks)
            axis.grid(color="0.86", linewidth=0.45)

        save_figure(figure, FIGURE_DIR / f"{OUTPUT_STEM}.pdf")
        save_figure(figure, FIGURE_DIR / f"{OUTPUT_STEM}.png", dpi=300)
        plt.close(figure)


def main() -> None:
    report, report_path, manifest_path = _load_report()
    _plot(report)
    outputs = {}
    for suffix in ("pdf", "png"):
        output = FIGURE_DIR / f"{OUTPUT_STEM}.{suffix}"
        outputs[suffix] = {"path": output.name, "bytes": output.stat().st_size, "sha256": _sha256(output)}
    audit = {
        "schema": "paper_current_topology_convergence64_figure_v1",
        "source": {
            "report_path": str(report_path.relative_to(ROOT)),
            "report_sha256": _sha256(report_path),
            "manifest_path": str(manifest_path.relative_to(ROOT)),
            "manifest_sha256": _sha256(manifest_path),
        },
        "lower_tail_assessment": report["lower_tail_assessment"],
        "outputs": outputs,
    }
    (FIGURE_DIR / f"{OUTPUT_STEM}.audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
