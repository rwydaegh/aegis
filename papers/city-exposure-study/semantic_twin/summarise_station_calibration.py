"""Collect the station calibration into one table and one JSON.

Everything here is recomputed from the per station, per seed susceptibilities
``run_station_calibration.py`` stores, and the walk arm is recomputed from the
raw ``ladder250_*`` rows rather than copied out of
``coverage_ladder_cross_site_250m_15ghz.json``. Rebuilding a published number is
the only way to find out whether the report and the rows it was made from still
agree, and a disagreement is printed rather than resolved quietly.

Both reductions travel together everywhere, named. ``paired`` is the median over
standpoints of the per standpoint decibel difference, which is the reduction
paper.tex uses throughout. ``distribution`` is the decibel ratio of the two
distribution medians, which is what COVERAGE_LADDER.md quotes. Over the walk the
two differ by up to a factor of five and Tokyo changes sign between them.

One filter is applied and it is not cosmetic. A registered camera pose is not
automatically a standpoint: at the Zocalo seven of the twelve admitted poses sit
under the photogrammetric shell and escape no ray at all, which the walk's own
``min_sky_fraction`` test would reject. Every quantity is therefore reported
over all stations and over the stations that pass that same test, and the two
are never merged.

Usage
-----
    python summarise_station_calibration.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

STATION = SCRIPT_DIR / "outputs" / "station_calibration"
EXPOSURE = SCRIPT_DIR / "outputs" / "exposure_korenmarkt"
BOUNCE = SCRIPT_DIR / "outputs" / "bounce_budget"

MODEL_KEYS = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")

#: The walk's own enclosure test. ``build_walk`` refuses a candidate standpoint
#: whose sky fraction falls below this, because a point inside a building traces
#: to a susceptibility orders of magnitude below its neighbours and that is a
#: bad standpoint rather than an exposure result.
MIN_SKY_FRACTION = 0.01

SITES: tuple[str, ...] = (
    "prague_staromestske",
    "mexico_zocalo",
    "korenmarkt",
    "brussels_grandplace",
    "madrid_plazamayor",
    "tokyo_hachiko",
    "milan_duomo",
)


def load_rows(stem: str) -> dict[int, dict[str, Any]] | None:
    """One walk run's rows keyed by walk index, or None if it is not on disk.

    Two published files under ``outputs/exposure_korenmarkt`` carry malformed
    JSONL rows from two writers appending to one file, so a bad row is counted
    and skipped rather than allowed to abort a table.
    """
    path = EXPOSURE / f"{stem}_locations.jsonl"
    if not path.exists():
        return None
    rows: dict[int, dict[str, Any]] = {}
    bad = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        rows[int(row["index"])] = row
    if bad:
        print(f"[warn] {path.name} has {bad} malformed rows, skipped", flush=True)
    return rows


def spread(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return {"replicates": 0, "mean_db": None, "sd_db": None, "standard_error_db": None, "per_seed_db": []}
    sd = float(array.std(ddof=1)) if array.size > 1 else None
    return {
        "replicates": int(array.size),
        "mean_db": float(array.mean()),
        "sd_db": sd,
        "standard_error_db": None if sd is None else sd / float(np.sqrt(array.size)),
        "per_seed_db": [float(v) for v in array],
    }


def both_reductions(baseline: np.ndarray, values: np.ndarray) -> tuple[float, float]:
    """``(paired median, ratio of distribution medians)`` in decibels."""
    return (
        float(np.median(10.0 * np.log10(values / baseline))),
        float(10.0 * np.log10(np.median(values) / np.median(baseline))),
    )


def shift_over_seeds(
    base: list[list[float]],
    other: list[list[float]],
    select: np.ndarray | None = None,
) -> dict[str, Any]:
    """Both reductions per seed, then their mean and standard error."""
    paired: list[float] = []
    distribution: list[float] = []
    for seed_index in range(min(len(base), len(other))):
        a = np.asarray(base[seed_index], dtype=float)
        b = np.asarray(other[seed_index], dtype=float)
        if select is not None:
            a, b = a[select], b[select]
        if a.size == 0:
            continue
        first, second = both_reductions(a, b)
        paired.append(first)
        distribution.append(second)
    return {
        "standpoints": int(len(base[0]) if select is None else int(np.count_nonzero(select))),
        "paired_median_shift_db": spread(paired),
        "distribution_median_shift_db": spread(distribution),
    }


def per_station_shift(base: list[list[float]], other: list[list[float]]) -> list[float]:
    """Each station's own decibel shift, averaged over seeds."""
    a = np.asarray(base, dtype=float)
    b = np.asarray(other, dtype=float)
    return (10.0 * np.log10(b / a)).mean(axis=0).tolist()


def walk_arm(site: str, seeds: tuple[int, ...], rung: str) -> dict[str, Any]:
    """The same comparison over the published 80 standpoint walk, from raw rows."""
    paired: dict[str, list[float]] = {key: [] for key in MODEL_KEYS}
    distribution: dict[str, list[float]] = {key: [] for key in MODEL_KEYS}
    standpoints = 0
    used: list[int] = []
    for seed in seeds:
        base = load_rows(f"ladder250_{site}_s{seed}_geometric_15ghz")
        other = load_rows(f"ladder250_{site}_s{seed}_{rung}_15ghz")
        if base is None or other is None:
            continue
        shared = sorted(set(base) & set(other))
        if len(shared) != len(base) or len(shared) != len(other):
            print(f"[warn] {site} s{seed} {rung}: {len(base)} against {len(other)} rows, pairing on {len(shared)}")
        used.append(seed)
        standpoints = len(shared)
        for key in MODEL_KEYS:
            first, second = both_reductions(
                np.array([base[i][key] for i in shared]), np.array([other[i][key] for i in shared])
            )
            paired[key].append(first)
            distribution[key].append(second)
    return {
        "seeds": used,
        "standpoints": standpoints,
        "paired_median_shift_db": {key: spread(values) for key, values in paired.items()},
        "distribution_median_shift_db": {key: spread(values) for key, values in distribution.items()},
    }


def published_walk_coverage(site: str) -> dict[str, Any] | None:
    """First interaction coverage over the walk, from the bounce budget product.

    Four of the seven sites have one. The ``pooled`` field of that file mixes the
    walk standpoints with the station standpoints and therefore reads higher
    than the walk does on its own, so the walk only field is the one carried
    here and both are printed.
    """
    path = BOUNCE / f"{site}_250m_bounce_evidence.json"
    if not path.exists():
        return None
    document = json.loads(path.read_text())
    evidence = document["bounce_evidence"]
    walk = [
        row["walk"][0] for row in evidence["per_standpoint"] if row["kind"] == "walk" and row["walk"][0] is not None
    ]
    return {
        "walk_standpoints": len(walk),
        "pooled_over_walk_standpoints_bounce_1": evidence["pooled_walk_standpoints_only"]["walk"][
            "covered_fraction_by_power"
        ][0],
        "pooled_over_every_standpoint_bounce_1": evidence["pooled"]["walk"]["covered_fraction_by_power"][0],
        "median_over_walk_standpoints_bounce_1": float(np.median(walk)) if walk else None,
        "source": str(path.relative_to(SCRIPT_DIR)),
    }


def read(site: str, crop_m: int, tag: str, kind: str) -> dict[str, Any] | None:
    path = STATION / f"{site}_{crop_m}m{tag}_station_{kind}.json"
    return json.loads(path.read_text()) if path.exists() else None


def site_row(site: str, crop_m: int, tag: str, seeds: tuple[int, ...], baseline: str) -> dict[str, Any] | None:
    evidence = read(site, crop_m, tag, "evidence")
    exposure = read(site, crop_m, tag, "exposure")
    if evidence is None or exposure is None:
        return None

    row: dict[str, Any] = {
        "site": site,
        "crop_radius_m": crop_m,
        "mesh_triangles": evidence["mesh_triangles"],
        "ground_datum_m": evidence["ground_datum_m"],
        "bound_fraction_by_area": evidence["evidence_masks"]["walk"]["covered_fraction_by_area"],
        "stations": len(evidence["conventions"]["pose"]["stations"]),
        "sources": {
            "evidence": str((STATION / f"{site}_{crop_m}m{tag}_station_evidence.json").relative_to(SCRIPT_DIR)),
            "exposure": str((STATION / f"{site}_{crop_m}m{tag}_station_exposure.json").relative_to(SCRIPT_DIR)),
        },
        "conventions": {},
    }

    for convention, entry in evidence["conventions"].items():
        stations = entry["stations"]
        coverage = np.array([record["covered_by_power_walk"][0] for record in stations], dtype=float)
        sky = np.array([record["sky_fraction"] for record in stations], dtype=float)
        open_air = sky >= MIN_SKY_FRACTION
        per_rung = exposure["rungs"].get(convention, {})

        block: dict[str, Any] = {
            "first_interaction_coverage": {
                "pooled": entry["pooled"]["walk"]["covered_fraction_by_power"][:3],
                "per_station": coverage.tolist(),
                "median": float(np.median(coverage)),
                "min": float(coverage.min()),
                "stations_below_0p95": int(np.count_nonzero(coverage < 0.95)),
            },
            "sky_fraction": sky.tolist(),
            "stations_open_air": int(np.count_nonzero(open_air)),
            "stations_enclosed": int(np.count_nonzero(~open_air)),
            "camera_height_above_local_ground_m": [record["camera_height_above_local_ground_m"] for record in stations],
            "shifts": {},
        }
        for reference in dict.fromkeys([baseline, "walk"]):
            if reference not in per_rung:
                continue
            base = per_rung[reference]["per_seed"]
            against: dict[str, Any] = {}
            for materials, record in per_rung.items():
                if materials == reference:
                    continue
                against[materials] = {
                    "covered_fraction_by_area": record["covered_fraction_by_area"],
                    "all_stations": {key: shift_over_seeds(base[key], record["per_seed"][key]) for key in MODEL_KEYS},
                    "open_air_stations": {
                        key: shift_over_seeds(base[key], record["per_seed"][key], open_air) for key in MODEL_KEYS
                    },
                    "per_station_rooftop_db": per_station_shift(base["chi_rooftop"], record["per_seed"]["chi_rooftop"]),
                }
            block["shifts"][f"against_{reference}"] = against
        # Where the station population sits against the walk population in
        # absolute terms, on the no evidence rung so nothing about materials is
        # in it. This is the size of the standpoint bias the calibration set
        # carries, and its sign is not the same at every square.
        if baseline in per_rung:
            block["absolute_chi_rooftop"] = {
                "station_median_per_seed": [
                    float(np.median(values)) for values in per_rung[baseline]["per_seed"]["chi_rooftop"]
                ],
                "open_air_station_median_per_seed": [
                    float(np.median(np.asarray(values)[open_air])) if np.any(open_air) else None
                    for values in per_rung[baseline]["per_seed"]["chi_rooftop"]
                ],
                "rung": baseline,
            }
        row["conventions"][convention] = block

    walk_median: list[float] = []
    for seed in seeds:
        rows_on_disk = load_rows(f"ladder250_{site}_s{seed}_geometric_15ghz")
        if rows_on_disk:
            walk_median.append(float(np.median([entry["chi_rooftop"] for entry in rows_on_disk.values()])))
    row["walk_median_chi_rooftop_geometric_per_seed"] = walk_median
    row["walk_arm"] = {rung: walk_arm(site, seeds, rung) for rung in ("walk", "semantic")}
    row["published_walk_coverage"] = published_walk_coverage(site)
    return row


def cell(entry: dict[str, Any] | None) -> str:
    if not entry or entry.get("mean_db") is None:
        return "n/a"
    error = entry.get("standard_error_db")
    if error is None:
        return f"{entry['mean_db']:+.3f}, one seed"
    return f"{entry['mean_db']:+.3f} +/- {error:.3f}"


def table(rows: list[dict[str, Any]], convention: str, reference: str, rung: str, key: str, subset: str) -> str:
    """One markdown table: the station arm against the walk arm, both reductions."""
    lines = [
        "| Site | Stations | Bound area | Bounce 1 | Station paired | Station ratio of medians "
        "| Walk paired | Walk ratio of medians |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    body = 0
    for row in rows:
        block = row["conventions"].get(convention)
        if block is None:
            continue
        entry = block["shifts"].get(f"against_{reference}", {}).get(rung)
        if entry is None:
            continue
        walk = row["walk_arm"].get(rung, {}) if reference == "geometric" else {}
        count = entry[subset][key]["standpoints"]
        lines.append(
            "| "
            + " | ".join(
                [
                    row["site"],
                    f"{count} of {row['stations']}",
                    f"{100 * row['bound_fraction_by_area']:.1f} %",
                    f"{block['first_interaction_coverage']['pooled'][0]:.4f}",
                    cell(entry[subset][key]["paired_median_shift_db"]),
                    cell(entry[subset][key]["distribution_median_shift_db"]),
                    cell(walk.get("paired_median_shift_db", {}).get(key)),
                    cell(walk.get("distribution_median_shift_db", {}).get(key)),
                ]
            )
            + " |"
        )
        body += 1
    return "\n".join(lines) if body else ""


def pooled_scatter(rows: list[dict[str, Any]], convention: str, rung: str) -> dict[str, Any]:
    """Does a station's own shift track its own first interaction coverage?

    Fifty one stations is enough to ask, and it is the direct form of the
    question the cross square scatter of COVERAGE_LADDER.md asks indirectly
    through the bound area fraction.
    """
    coverage: list[float] = []
    shift: list[float] = []
    for row in rows:
        block = row["conventions"].get(convention)
        entry = (block or {}).get("shifts", {}).get("against_geometric", {}).get(rung)
        if entry is None:
            continue
        keep = np.asarray(block["sky_fraction"]) >= MIN_SKY_FRACTION
        coverage.extend(np.asarray(block["first_interaction_coverage"]["per_station"])[keep].tolist())
        shift.extend(np.asarray(entry["per_station_rooftop_db"])[keep].tolist())
    if len(coverage) < 3:
        return {"stations": len(coverage)}
    first = np.asarray(coverage)
    second = np.asarray(shift)
    return {
        "stations": int(first.size),
        "pearson_r": float(np.corrcoef(first, second)[0, 1]),
        "coverage": first.tolist(),
        "rooftop_shift_db": second.tolist(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+", default=list(SITES))
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--seeds", default="7,8,9,10")
    parser.add_argument("--baseline", default="geometric")
    parser.add_argument("--tag", default="")
    args = parser.parse_args(argv)
    seeds = tuple(int(value) for value in args.seeds.split(","))

    rows = [row for row in (site_row(site, args.crop_m, args.tag, seeds, args.baseline) for site in args.site) if row]
    if not rows:
        print("no station calibration on disk", flush=True)
        return 1

    summary = {
        "question": (
            "at the standpoints the panoramas occupied, where the first interaction evidence guarantee "
            "is exact rather than statistical, what does replacing the geometric orientation rule with "
            "image derived materials do"
        ),
        "crop_radius_m": args.crop_m,
        "frequency_hz": 15.0e9,
        "seeds": list(seeds),
        "baseline": args.baseline,
        "min_sky_fraction": MIN_SKY_FRACTION,
        "reductions": {
            "paired_median_shift_db": (
                "median over standpoints of the per standpoint decibel difference, the reduction paper.tex uses"
            ),
            "distribution_median_shift_db": (
                "decibel ratio of the two distribution medians, the reduction COVERAGE_LADDER.md quotes"
            ),
        },
        "error_bar": (
            "standard error over seeds. At the stations the standpoint set is fixed by the data, so a "
            "seed redraws only the ray streams and this bar is Monte Carlo ray noise alone. Over the "
            "walk a seed redraws the walk as well, so the walk columns carry the larger standpoint "
            "sampling term and the two bars are not comparable in kind"
        ),
        "rows": rows,
        "per_station_scatter": {
            convention: {rung: pooled_scatter(rows, convention, rung) for rung in ("walk", "semantic")}
            for convention in ("pose", "pedestrian")
        },
    }
    path = STATION / f"station_calibration_cross_site_{args.crop_m}m{args.tag}.json"
    path.write_text(json.dumps(summary, indent=2))

    for convention in ("pose", "pedestrian"):
        for subset in ("all_stations", "open_air_stations"):
            for rung in ("walk", "semantic"):
                for key in MODEL_KEYS:
                    built = table(rows, convention, args.baseline, rung, key, subset)
                    if built:
                        print(f"\n### {convention}, {subset}, {rung} rung against {args.baseline}, {key}\n")
                        print(built)
    print(f"\nwrote {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
