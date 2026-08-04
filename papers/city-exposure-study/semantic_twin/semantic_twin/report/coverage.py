"""Coverage ladder calculations and Markdown rendering."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np


def _against_baseline(baseline: np.ndarray, values: np.ndarray) -> dict[str, float | int]:
    """How far one rung sits from the no evidence rung, paired standpoint by standpoint.

    Both rungs trace the same walk on the same per standpoint seeds, so the ray
    stream is common to the two and the difference carries no independent Monte
    Carlo noise from it. What the difference does carry is the standpoint draw,
    which is why the shift is replicated over seeds rather than quoted from one.
    """
    count = min(baseline.size, values.size)
    ratio = values[:count] / baseline[:count]
    return {
        # Median of the paired per location ratios: how far a typical location
        # moves.
        "median_ratio": float(np.median(ratio)),
        "median_shift_db": float(10.0 * np.log10(np.median(ratio))),
        # Ratio of the two distribution medians: how far the published
        # distribution moves. Larger than the paired figure at Korenmarkt, which
        # says the shift is concentrated in a minority of locations rather than
        # spread evenly.
        "distribution_median_shift_db": float(10.0 * np.log10(np.quantile(values, 0.5) / np.quantile(baseline, 0.5))),
        "spread_db_p95_over_p05": float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05))),
        "p95_ratio": float(np.quantile(ratio, 0.95)),
        "max_absolute_change": float(np.max(np.abs(ratio - 1.0))),
        "locations_moved_more_than_1_db": int(np.count_nonzero(np.abs(10.0 * np.log10(ratio)) > 1.0)),
    }


def _one_value(values: list[float]) -> float | list[float]:
    """A bound fraction does not depend on the seed, so a spread in it is a fault."""
    unique = sorted(set(values))
    return unique[0] if len(unique) == 1 else unique


def _spread(values: list[float]) -> dict[str, Any]:
    array = np.array(values, dtype=float)
    if array.size == 0:
        return {"replicates": 0, "mean_db": None, "sd_db": None, "standard_error_db": None, "per_seed_db": []}
    sd = float(array.std(ddof=1)) if array.size > 1 else None
    return {
        "replicates": int(array.size),
        "mean_db": float(array.mean()),
        "sd_db": sd,
        "standard_error_db": None if sd is None else sd / float(np.sqrt(array.size)),
        "per_seed_db": [float(x) for x in array],
    }


def ladder_markdown(rows: list[dict[str, Any]]) -> str:
    """The per square table, bound fraction first and never on its own."""
    header = (
        "| Site | Rung | Bound area | Stations or views | Standpoints | "
        "Rooftop shift | Isotropic shift | Street shift |"
    )
    lines = [header, "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        bound = row["covered_fraction_by_area"]
        bound_cell = f"{100 * bound:.1f} %" if isinstance(bound, float) else "inconsistent across seeds"
        evidence = row["stations"] if row["stations"] is not None else row["views"]
        kind = "stations" if row["stations"] is not None else "views"
        cells = [
            row["site"],
            row["rung"],
            bound_cell,
            "not recorded" if evidence is None else f"{evidence} {kind}",
            f"{sum(row['locations'])} over {len(row['seeds'])} seeds",
        ]
        for key in ("chi_rooftop", "chi_isotropic", "chi_street_small_cell"):
            spread = row["shift_db"][key]
            if spread["mean_db"] is None:
                cells.append("n/a")
            elif spread["standard_error_db"] is None:
                cells.append(f"{spread['mean_db']:+.3f} dB, one seed")
            else:
                cells.append(f"{spread['mean_db']:+.3f} +/- {spread['standard_error_db']:.3f} dB")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def coverage_report(
    frequency_hz: float,
    tag_suffix: str = "",
    *,
    site: str = "korenmarkt",
    crop_m: int = 130,
    seed: int = 7,
    output: pathlib.Path,
    rungs_for: Callable[[str, int, int], Sequence[tuple[str, str, str]]],
    key_for: Callable[[str, int, int], str],
    model_keys: Sequence[str],
    compare_to_baseline: Callable[[np.ndarray, np.ndarray], dict[str, float | int]],
) -> pathlib.Path:
    """How far does the exposure distribution move as image evidence grows?

    This is the experiment that says whether the material assignment matters at
    all. Everything except the material binding is held fixed, so the only
    thing varying between the three runs is the fraction of scene area whose
    material came from an image rather than from which way the triangle points.

    ``tag_suffix`` reads a rerun of the same rungs written under suffixed
    tags, so a rerun at a different bounce budget does not overwrite the
    published ladder and can be compared against it.
    """
    from semantic_twin.report import empirical_cdf, read_rows

    entries: list[dict[str, Any]] = []
    baseline: dict[str, np.ndarray] | None = None
    for stem, _materials, description in rungs_for(site, crop_m, seed):
        full = f"{stem}{tag_suffix}_{frequency_hz / 1e9:g}ghz"
        rows_path = output / f"{full}_locations.jsonl"
        manifest_path = output / f"{full}_manifest.json"
        if not rows_path.exists() or not manifest_path.exists():
            continue
        rows = read_rows(rows_path, site=site).rows
        manifest = json.loads(manifest_path.read_text())
        binding = manifest["semantic_binding"]
        columns = {key: np.array([row[key] for row in rows]) for key in model_keys}
        values = columns["chi_rooftop"]
        entry: dict[str, Any] = {
            "run": stem,
            # The suffixed stem, because the figure below reloads these rows and
            # rebuilding the name from ``run`` would silently read the published
            # ladder while the table above described the rerun.
            "stem": full,
            "site": site,
            "crop_radius_m": crop_m,
            "seed": seed,
            "evidence": description,
            # A bound run is a run in which this fraction of the triangle area
            # carries image evidence and the rest still falls back to the
            # orientation rule. It travels beside every shift below because a
            # shift without it is not interpretable.
            "covered_fraction_by_area": binding.get("covered_fraction_by_area", 0.0),
            "covered_fraction_by_face": binding.get("covered_fraction_by_face", 0.0),
            "stations": binding.get("stations"),
            "views": len(binding["views"]) if isinstance(binding.get("views"), list) else None,
            # Every fishnet in this study was cut against a smaller mesh than the
            # 250 m run uses, so the join from the cut mesh's triangle numbering
            # to the run's is done by centroid and normal and can drop triangles.
            # How many it kept is part of the result, not an implementation
            # detail, so it is carried rather than left inside the manifest.
            "mesh_match": binding.get("mesh_match"),
            "binding_source": binding.get("walk_npz") or binding.get("fishnet_dir"),
            "locations": len(rows),
            "chi_rooftop": {
                "p05": float(np.quantile(values, 0.05)),
                "p50": float(np.quantile(values, 0.50)),
                "p95": float(np.quantile(values, 0.95)),
                "mean": float(values.mean()),
            },
        }
        if baseline is None:
            baseline = columns
        else:
            entry["against_no_evidence"] = compare_to_baseline(baseline["chi_rooftop"], values)
            entry["by_model"] = {
                key: compare_to_baseline(baseline[key], columns[key]) for key in model_keys if key in baseline
            }
        entries.append(entry)

    summary = {
        "question": (
            "how far does the exposure distribution move as the fraction of scene area carrying image evidence grows"
        ),
        "site": site,
        "crop_radius_m": crop_m,
        "seed": seed,
        "frequency_hz": frequency_hz,
        "ladder": entries,
    }
    path = output / f"coverage_ladder{key_for(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))

    if len(entries) >= 2:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, panel = plt.subplots(figsize=(5.2, 4.0))
        for entry, colour in zip(entries, ("0.55", "tab:blue", "tab:red"), strict=False):
            rows = read_rows(output / f"{entry['stem']}_locations.jsonl", site=site).rows
            ordered, probability = empirical_cdf(np.array([r["chi_rooftop"] for r in rows]))
            panel.step(
                ordered,
                probability,
                where="post",
                color=colour,
                linewidth=1.6,
                label=f"{100 * entry['covered_fraction_by_area']:.1f} % of area from images",
            )
        panel.set_xscale("log")
        panel.set_xlabel("rooftop susceptibility $\\chi_S$")
        panel.set_ylabel("fraction of walk locations")
        panel.set_title(
            f"{site}, {crop_m} m crop, {frequency_hz / 1e9:g} GHz\nexposure against image evidence coverage",
            fontsize=10,
        )
        panel.legend(fontsize=8, loc="lower right")
        panel.grid(alpha=0.25)
        figure_path = output / f"coverage_ladder{key_for(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.png"
        figure.tight_layout()
        figure.savefig(figure_path, dpi=170)
        figure.savefig(figure_path.with_suffix(".pdf"))
        plt.close(figure)
        print(f"wrote {figure_path}")
    print(f"wrote {path}")
    return path


def coverage_ladder_report(
    sites: list[str],
    crop_m: int,
    seeds: tuple[int, ...],
    frequency_hz: float,
    *,
    tag_suffix: str = "",
    refused: dict[str, str] | None = None,
    failures: dict[str, str] | None = None,
    output: pathlib.Path,
    key_for: Callable[[str, int, int], str],
    model_keys: Sequence[str],
    one_value: Callable[[list[float]], float | list[float]],
    spread: Callable[[list[float]], dict[str, Any]],
    plotter: Callable[[list[dict[str, Any]], pathlib.Path, int, float], pathlib.Path | None],
    markdown: Callable[[list[dict[str, Any]]], str],
) -> pathlib.Path | None:
    """Does the single square material negative travel? One row per square.

    The shift is a mean over the seeds and its error bar is their standard
    error. The bound area fraction sits beside it in the same row and is not
    optional: a 4.6 percent bound run is a run in which 95.4 percent of the area
    still came from the orientation rule, and quoting the shift without it
    invites the reader to read it as the effect of knowing the materials.

    The bound fraction is a property of where a camera could stand rather than
    of how good the segmentation is, so the rows are ordered by site name and
    not by it.
    """
    rows: list[dict[str, Any]] = []
    for site in sites:
        per_rung: dict[str, dict[str, Any]] = {}
        for seed in seeds:
            path = output / f"coverage_ladder{key_for(site, crop_m, seed)}{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
            if not path.exists():
                continue
            for entry in json.loads(path.read_text())["ladder"]:
                if "against_no_evidence" not in entry:
                    continue
                rung = entry["run"].rsplit("_", 1)[-1]
                record = per_rung.setdefault(
                    rung,
                    {
                        "rung": rung,
                        "evidence": entry["evidence"],
                        "covered_fraction_by_area": [],
                        "stations": entry["stations"],
                        "views": entry["views"],
                        "locations": [],
                        "seeds": [],
                        "shift_db": {key: [] for key in model_keys},
                        "paired_median_shift_db": {key: [] for key in model_keys},
                        "locations_moved_more_than_1_db": [],
                    },
                )
                record["covered_fraction_by_area"].append(entry["covered_fraction_by_area"])
                record["locations"].append(entry["locations"])
                record["seeds"].append(seed)
                record["locations_moved_more_than_1_db"].append(
                    entry["against_no_evidence"]["locations_moved_more_than_1_db"]
                )
                for key in model_keys:
                    against = entry.get("by_model", {}).get(key)
                    if against is None:
                        continue
                    record["shift_db"][key].append(against["distribution_median_shift_db"])
                    record["paired_median_shift_db"][key].append(against["median_shift_db"])
        for rung in per_rung.values():
            rung["covered_fraction_by_area"] = one_value(rung["covered_fraction_by_area"])
            rung["shift_db"] = {key: spread(values) for key, values in rung["shift_db"].items()}
            rung["paired_median_shift_db"] = {
                key: spread(values) for key, values in rung["paired_median_shift_db"].items()
            }
            rows.append({"site": site, **rung})
    if not rows:
        print("no ladder to report", flush=True)
        return None
    summary = {
        "question": "does the single square material negative travel to the other squares",
        "crop_radius_m": crop_m,
        "frequency_hz": frequency_hz,
        "seeds": list(seeds),
        "shift_definition": (
            "ratio of the two distribution medians in dB, the walk or fishnet rung against the "
            "geometric rung on the same standpoints, averaged over the seeds"
        ),
        "standard_error": "standard deviation over the seeds divided by the square root of their count",
        "bound_fraction_note": (
            "covered_fraction_by_area is the fraction of the crop's triangle area carrying image "
            "evidence. The rest falls back to the orientation rule. It is set by where a camera "
            "could stand against how far the crop reaches, not by segmentation quality, so it does "
            "not rank the squares by evidence quality."
        ),
        "rows": rows,
        "sites_refused": refused or {},
        "rungs_failed": failures or {},
    }
    path = output / f"coverage_ladder_cross_site_{crop_m}m{tag_suffix}_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))
    plotter(rows, path.with_suffix(".png"), crop_m, frequency_hz)
    print(markdown(rows), flush=True)
    print(f"wrote {path}", flush=True)
    return path


def plot_cross_site_ladder(
    rows: list[dict[str, Any]],
    path: pathlib.Path,
    crop_m: int,
    frequency_hz: float,
) -> pathlib.Path | None:
    """Shift against bound area, one point per square, with the noise floor on it.

    Plotting the shift against the bound fraction rather than against the site
    name is the whole question in one panel: if knowing the materials mattered,
    the squares that know more of them would move further, and the cloud would
    have a slope.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, panel = plt.subplots(figsize=(5.4, 4.0))
    markers = {"walk": "o", "semantic": "s"}
    for rung, marker in markers.items():
        chosen = [row for row in rows if row["rung"] == rung and isinstance(row["covered_fraction_by_area"], float)]
        if not chosen:
            continue
        x = [100.0 * row["covered_fraction_by_area"] for row in chosen]
        y = [row["shift_db"]["chi_rooftop"]["mean_db"] for row in chosen]
        error = [row["shift_db"]["chi_rooftop"]["standard_error_db"] or 0.0 for row in chosen]
        panel.errorbar(x, y, yerr=error, fmt=marker, capsize=3, label=f"{rung} rung", linewidth=1.2, markersize=5)
        for row, px, py in zip(chosen, x, y, strict=True):
            panel.annotate(row["site"].split("_")[0], (px, py), fontsize=7, xytext=(4, 3), textcoords="offset points")
    panel.axhline(0.0, color="0.4", linewidth=0.8)
    panel.set_xlabel("percent of triangle area carrying image evidence")
    panel.set_ylabel("shift of the distribution median, dB")
    panel.set_title(
        f"{crop_m} m crop, {frequency_hz / 1e9:g} GHz, rooftop model\nexposure shift against how much of the "
        "square a camera saw",
        fontsize=10,
    )
    panel.legend(fontsize=8)
    panel.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    print(f"wrote {path}", flush=True)
    return path
