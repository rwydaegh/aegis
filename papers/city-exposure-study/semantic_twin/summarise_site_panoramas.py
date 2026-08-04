"""Collect the per-panorama registration results for a site into one table.

Every panorama fetched by ``fetch_site_panoramas.py`` is registered on its own,
so the useful quantity is the distribution over a site rather than any single
residual. This reads the aligned poses and writes one JSON summary plus a
markdown table per site.

The two numbers to read first are the median skyline residual, which says how
well the modelled silhouette matches the segmented one, and the count of poses
whose recovered altitude landed on its search bound. A pose at its bound is not
a measurement: it is the bound, and every previously shipped pose in this
repository had that defect.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python summarise_site_panoramas.py \
      --site data/panoramas/prague_staromestske --out outputs/city_screening
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from typing import Any

from semantic_twin import paths

DEGREE_KEYS = ("skyline_score_mean_deg", "skyline_signed_residual_median_deg")


def read_pose(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def panorama_rows(site_dir: pathlib.Path) -> list[dict[str, Any]]:
    """One row per panorama directory that carries an aligned pose."""
    rows: list[dict[str, Any]] = []
    for pano_dir in sorted(site_dir.glob("pano_*")):
        aligned = read_pose(pano_dir / "alignment" / "pose_aligned.json")
        initial = read_pose(pano_dir / "pose_initial.json")
        metadata = read_pose(pano_dir / "metadata.json")
        if aligned is None or initial is None:
            rows.append({"name": pano_dir.name, "registered": False})
            continue
        provenance = aligned.get("provenance", {})
        rows.append(
            {
                "name": pano_dir.name,
                "registered": True,
                "pano_id": None if metadata is None else metadata.get("panoId"),
                "date": None if metadata is None else metadata.get("date"),
                "position_enu_m": aligned.get("position_enu_m"),
                "initial_enu_m": initial.get("position_enu_m"),
                "residual_deg": aligned.get("skyline_score_mean_deg"),
                "signed_residual_deg": aligned.get("skyline_signed_residual_median_deg"),
                "dz_at_bound": aligned.get("skyline_dz_at_bound"),
                "skyline_samples": aligned.get("n_observed_structural_skyline_samples"),
                "orientation_source": aligned.get("orientation_source"),
                "ground_minus_scene_constant_m": provenance.get("ground_minus_scene_constant_m"),
                "ground_spread_m": provenance.get("ground_spread_m"),
            }
        )
    return rows


def summarise(site_dir: pathlib.Path) -> dict[str, Any]:
    rows = panorama_rows(site_dir)
    done = [r for r in rows if r["registered"]]
    residuals = [r["residual_deg"] for r in done if r["residual_deg"] is not None]
    offsets = [r["ground_minus_scene_constant_m"] for r in done if r.get("ground_minus_scene_constant_m") is not None]
    moved = []
    for r in done:
        if r["position_enu_m"] and r["initial_enu_m"]:
            moved.append(sum((a - b) ** 2 for a, b in zip(r["position_enu_m"], r["initial_enu_m"], strict=True)) ** 0.5)
    return {
        "site": site_dir.name,
        "panoramas": len(rows),
        "registered": len(done),
        "dates": sorted({r["date"] for r in done if r.get("date")}),
        "residual_deg": {
            "median": round(statistics.median(residuals), 3) if residuals else None,
            "min": round(min(residuals), 3) if residuals else None,
            "max": round(max(residuals), 3) if residuals else None,
        },
        "poses_at_altitude_bound": sum(1 for r in done if r.get("dz_at_bound")),
        "poses_without_measured_orientation": sum(
            1 for r in done if r.get("orientation_source", "").startswith(("absent", "degenerate"))
        ),
        "ground_minus_scene_constant_m": {
            "min": round(min(offsets), 3) if offsets else None,
            "max": round(max(offsets), 3) if offsets else None,
        },
        "pose_correction_m": {
            "median": round(statistics.median(moved), 3) if moved else None,
            "max": round(max(moved), 3) if moved else None,
        },
        "panoramas_detail": rows,
    }


def markdown(summaries: list[dict[str, Any]]) -> str:
    header = (
        "| Site | Panoramas | Registered | Capture | Median residual | Best | Worst | At altitude bound |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    lines = []
    for s in summaries:
        r = s["residual_deg"]
        fmt = lambda v: "n/a" if v is None else f"{v:.2f} deg"  # noqa: E731
        lines.append(
            f"| {s['site']} | {s['panoramas']} | {s['registered']} | {', '.join(s['dates']) or 'n/a'} | "
            f"{fmt(r['median'])} | {fmt(r['min'])} | {fmt(r['max'])} | {s['poses_at_altitude_bound']} |"
        )
    return header + "\n".join(lines) + "\n"


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--out", type=pathlib.Path, default=paths.output("city_screening"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    summaries = [summarise(site) for site in args.site]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "panorama_registration.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    table = markdown(summaries)
    (args.out / "panorama_registration.md").write_text(table, encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
