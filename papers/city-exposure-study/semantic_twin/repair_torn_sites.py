"""Re-trace a site of a published cross city sweep, under the configuration it was published at.

Two rows of ``city250_corrected`` were destroyed by an interleaved write. New
York lost two of its eighty records and Prague gained a fragment of an eighty
first, so the two files parse to 78 and 80 rows and neither can be read as the
run it claims to be. That sweep is one leg of the standpoint sampling
comparison the abstract quotes, so the damage reaches the paper.

Repairing it is not the same as rerunning it. Three things that decide the
numbers changed after that sweep and none of them is recorded anywhere a rerun
would look: the ground datum rule, the height the walk's downward probe casts
from, and the Russian roulette start depth. The first two change which
standpoints are traced, so a naive rerun produces a different eighty points and
a comparison against the nine surviving sites would be meaningless. All three
are recorded in the published manifest, which is what this script reads.

Whether that is enough is a question rather than an assumption, so the same
command re-traces a site whose file is intact and compares the result against
the published one to the last bit. A repair whose control does not reproduce is
not a repair.

Usage
-----
    python repair_torn_sites.py --sites korenmarkt --verify
    python repair_torn_sites.py --sites newyork_timessquare prague_staromestske
    python repair_torn_sites.py --standpoint-rms
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time
from typing import Any

import numpy as np

import run_exposure
from run_exposure import OUTPUT, PHANTOM, PHANTOM_MASS_KG
from semantic_twin.exposure import BodyCoupler

#: The published sweep being repaired, and the tag the repair is written under.
#: A distinct tag is not optional. Nine of the eleven sites of the published
#: sweep are intact and must not be overwritten by anything, including by a run
#: that is expected to reproduce them.
PUBLISHED_PREFIX = "city250_corrected"
REPAIR_PREFIX = "city250_repair"

#: The other leg of the standpoint sampling comparison: the same eleven squares
#: under the corrected ground datum rule, which redrew most of the walks.
DATUM_PREFIX = "city250_datum"

#: The eight squares the standpoint sampling rms is taken over. Krakow and
#: Toulouse are excluded because their datum moved by more than a quarter of a
#: metre and their walks moved off a roof onto the square, which is a different
#: effect and a much larger one. Korenmarkt is excluded because its standpoints
#: did not change at all, which is what makes it the control that separates
#: standpoint sampling from everything else.
SMALL_MOVERS = (
    "brussels_grandplace",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "milan_duomo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
)

MODEL_KEYS = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")


def stem(prefix: str, site: str, frequency_hz: float) -> str:
    return f"{prefix}_{site}_{frequency_hz / 1e9:g}ghz"


def read_manifest(prefix: str, site: str, frequency_hz: float) -> dict[str, Any]:
    return json.loads((OUTPUT / f"{stem(prefix, site, frequency_hz)}_manifest.json").read_text())


def read_rows(prefix: str, site: str, frequency_hz: float) -> tuple[list[dict[str, Any]], int]:
    """Rows that parse, and how many lines did not.

    A torn JSONL is not an error to raise. It is the thing being measured, so
    the count of unparseable lines is returned beside the good rows.
    """
    path = OUTPUT / f"{stem(prefix, site, frequency_hz)}_locations.jsonl"
    rows: list[dict[str, Any]] = []
    torn = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
    return rows, torn


def repair(site: str, frequency_hz: float, workers: int | None, coupler: Any) -> pathlib.Path:
    """Re-trace one site at the configuration its published manifest records."""
    manifest = read_manifest(PUBLISHED_PREFIX, site, frequency_hz)
    trace = manifest["trace_config"]
    walk = manifest["walk"]
    datum = float(manifest["ground_datum_m"])
    probe = walk.get("probe_z_m")
    if probe is None:
        # Every run written before 3 August cast its downward probe from the
        # ground datum plus 200 m and did not record the fact. The absence of
        # the key is the record.
        probe = datum + 200.0
    print(
        f"{site}: published at datum {datum} m, probe {probe} m, "
        f"L={trace['max_bounces']}, roulette start {trace['roulette_start']}, "
        f"{trace['rays']} rays, seed {trace['seed']}, {manifest['locations_traced']} standpoints",
        flush=True,
    )
    return run_exposure.run(
        int(manifest["locations_requested"]),
        int(trace["rays"]),
        float(trace["frequency_hz"]),
        variant=manifest["variant"],
        seed=int(trace["seed"]),
        tag=f"{REPAIR_PREFIX}_{site}",
        local_cells=int(trace["local_cells"]),
        walk_radius_m=float(walk["radius_m"]),
        walk_spacing_m=float(walk["spacing_m"]),
        max_bounces=int(trace["max_bounces"]),
        materials=manifest["semantic_binding"]["materials"],
        site=site,
        coupler=coupler,
        crop_m=int(manifest["crop_radius_m"]),
        workers=workers,
        roulette_start=int(trace["roulette_start"]),
        ground_datum_m=datum,
        walk_probe_z_m=float(probe),
    )


def verify(site: str, frequency_hz: float) -> dict[str, Any]:
    """Compare a repaired site against the published file, field by field.

    Hex float comparison, not a tolerance. The estimator is claimed to be a pure
    function of its inputs and its seed, so the only honest test of whether the
    configuration was recovered is whether every value is the same value.

    Two exceptions, and both are named rather than absorbed into a tolerance.
    ``seconds`` is wall clock and cannot repeat. And a value that differs in its
    last representable digit is counted separately, because a reduction whose
    summation order depends on how a process pool split the work is not the same
    thing as a different scene.
    """
    published, torn = read_rows(PUBLISHED_PREFIX, site, frequency_hz)
    repaired, _ = read_rows(REPAIR_PREFIX, site, frequency_hz)
    by_index = {row["index"]: row for row in repaired}
    compared = 0
    mismatched: list[str] = []
    last_digit: list[str] = []
    missing = []
    moved = []
    for row in published:
        other = by_index.get(row["index"])
        if other is None:
            missing.append(row["index"])
            continue
        for axis in ("x", "y", "z"):
            if row[axis].hex() != other[axis].hex():
                moved.append(row["index"])
                break
        for key, value in row.items():
            if not isinstance(value, float) or key not in other or key == "seconds":
                continue
            compared += 1
            if math.isnan(value) and math.isnan(other[key]):
                continue
            if value.hex() == other[key].hex():
                continue
            where = f"{site} index {row['index']} {key}: {value!r} against {other[key]!r}"
            if math.isclose(value, other[key], rel_tol=4.0e-16, abs_tol=0.0):
                last_digit.append(where)
            else:
                mismatched.append(where)
    return {
        "site": site,
        "published_rows": len(published),
        "published_torn_lines": torn,
        "repaired_rows": len(repaired),
        "standpoints_missing_from_repair": missing,
        "standpoints_that_moved": sorted(set(moved)),
        "float_fields_compared": compared,
        "float_fields_mismatched": len(mismatched),
        "float_fields_differing_in_the_last_digit": len(last_digit),
        "last_digit_examples": last_digit[:5],
        "first_mismatches": mismatched[:10],
        "reproduces": not mismatched and not missing and not moved,
    }


def _median_db(rows: list[dict[str, Any]], key: str) -> float:
    return 10.0 * math.log10(float(np.median([row[key] for row in rows])))


def standpoint_rms(frequency_hz: float) -> pathlib.Path:
    """The per square median shift between the two datum rules, and its rms.

    This is the quantity the abstract calls standpoint sampling. It is a shift
    between two runs that differ in their ground datum, but the datum is not
    what moves the medians: at eight of the eleven squares the datum moves by
    under a quarter of a metre while between 56 and 76 of the 80 standpoints are
    replaced, because the walk chain is reordered and the stratified pick indexes
    along it. Korenmarkt keeps all 80 and does not move, which is what says the
    standpoints and not the datum are doing the work.

    A site that has been repaired is read from the repair, and the repair is
    only used where the published file is torn.
    """
    report: dict[str, Any] = {
        "generator": "repair_torn_sites.py --standpoint-rms",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "comparison": f"{DATUM_PREFIX} against {PUBLISHED_PREFIX}, per square median in dB",
        "sites": {},
        "rms_db": {},
        "worst_db": {},
    }
    per_site: dict[str, dict[str, float]] = {}
    for site in SMALL_MOVERS:
        old_rows, torn = read_rows(PUBLISHED_PREFIX, site, frequency_hz)
        source = PUBLISHED_PREFIX
        repaired_path = OUTPUT / f"{stem(REPAIR_PREFIX, site, frequency_hz)}_locations.jsonl"
        if torn or len(old_rows) != 80:
            if not repaired_path.exists():
                raise RuntimeError(
                    f"{site} is torn ({len(old_rows)} rows, {torn} unparseable lines) and has no "
                    f"repair on disk. Run --sites {site} first"
                )
            old_rows, _ = read_rows(REPAIR_PREFIX, site, frequency_hz)
            source = REPAIR_PREFIX
        new_rows, new_torn = read_rows(DATUM_PREFIX, site, frequency_hz)
        if new_torn or len(new_rows) != 80:
            raise RuntimeError(f"{DATUM_PREFIX} at {site} is itself unusable: {len(new_rows)} rows, {new_torn} torn")
        shifts = {key: _median_db(new_rows, key) - _median_db(old_rows, key) for key in MODEL_KEYS}
        per_site[site] = shifts
        report["sites"][site] = {
            "old_leg": source,
            "old_rows": len(old_rows),
            "new_rows": len(new_rows),
            "old_roulette_start": read_manifest(source, site, frequency_hz)["trace_config"]["roulette_start"],
            "new_roulette_start": read_manifest(DATUM_PREFIX, site, frequency_hz)["trace_config"]["roulette_start"],
            **{key: shifts[key] for key in MODEL_KEYS},
        }
    for key in MODEL_KEYS:
        values = np.array([per_site[site][key] for site in SMALL_MOVERS])
        report["rms_db"][key] = float(np.sqrt(np.mean(values**2)))
        worst = SMALL_MOVERS[int(np.argmax(np.abs(values)))]
        report["worst_db"][key] = {"site": worst, "shift_db": float(per_site[worst][key])}

    path = OUTPUT.parent / "mc_error" / f"standpoint_sampling_{frequency_hz / 1e9:g}ghz.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"wrote {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="*", default=[])
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--verify", action="store_true", help="compare the repair against the published file")
    parser.add_argument("--standpoint-rms", action="store_true")
    args = parser.parse_args()

    frequency_hz = args.frequency_ghz * 1e9
    if args.sites:
        coupler = BodyCoupler(PHANTOM, frequency_hz, body_mass_kg=PHANTOM_MASS_KG)
        for site in args.sites:
            repair(site, frequency_hz, args.workers, coupler)
    if args.verify:
        for site in args.sites:
            print(json.dumps(verify(site, frequency_hz), indent=2))
    if args.standpoint_rms:
        standpoint_rms(frequency_hz)


if __name__ == "__main__":
    main()
