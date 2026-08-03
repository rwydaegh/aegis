"""Monte Carlo error bar for the exposure estimator, by replicating the ray stream.

The estimator is stochastic from the first interaction. Seeds are fixed, so a
run reproduces, but reproducible is not converged and until now no artefact
under ``outputs/`` carried a standard error. ``CODE_AUDIT.md`` section 4
reported one, measured by retracing a published run over eight seed streams,
and then the raw output of that measurement was discarded. This script is the
measurement, written down, so that the next reader has a file rather than a
markdown table.

What it does, and what it deliberately does not do. It holds the standpoints
fixed at the ones a published run traced, reads that run's own manifest for
every setting that changes a number, and varies only the per standpoint random
stream. So the spread it reports is the Monte Carlo error of the estimator at a
fixed set of observation points. It is not the standpoint sampling error, which
is a different quantity measured a different way, and the whole point of
separating them is that the paper compares the two.

The per standpoint seed is ``base + 1000 * walk_index``, which is the rule
``run_exposure.run`` already uses, so replica zero at the published base seed
retraces the published stream exactly and the run can be checked against the
stored file rather than trusted. Distinct bases one apart give streams that
never collide, because a collision would need ``base_a - base_b`` to be a
multiple of a thousand.

Usage
-----
    python run_seed_replicas.py --reference clean_geometric --seeds 7,8,9,10,11,12,13,14
    python run_seed_replicas.py --reference clean_walk9 \
        --walk-npz outputs/walk_korenmarkt/_pre_sam3/walk_semantic_conflict9.npz
    python run_seed_replicas.py --analyse --baseline clean_geometric --rung clean_walk9
"""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import time
from typing import Any

import numpy as np

from run_exposure import CONFIG, MODELS, OUTPUT as EXPOSURE_OUTPUT, ROOT, SEMANTICS, site_mesh
from semantic_twin.propagation import MitsubaGeometry, SbrTracer, TraceConfig, trace_standpoints
from semantic_twin.propagation.scene import classify_faces, load_bindings
from semantic_twin.propagation.semantic_binding import bind_from_walk

OUTPUT = ROOT / "outputs" / "mc_error"

#: The three illumination models the error bar is reported on. Their Monte Carlo
#: noise differs by more than a factor of ten, so reporting only the quiet one
#: would flatter the estimator.
MODEL_KEYS = ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")


def reference_paths(reference: str, frequency_hz: float) -> tuple[pathlib.Path, pathlib.Path]:
    stem = f"{reference}_{frequency_hz / 1e9:g}ghz"
    return (
        EXPOSURE_OUTPUT / f"{stem}_locations.jsonl",
        EXPOSURE_OUTPUT / f"{stem}_manifest.json",
    )


def load_reference(reference: str, frequency_hz: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The published run this replicates: its rows and the manifest that made them.

    Every setting comes out of the manifest rather than out of a default,
    because the defaults have moved since these runs were written. Both
    ``TraceConfig.max_bounces`` and ``roulette_start`` are derived from a module
    constant that changed on 3 August, after every run replicated here, so a
    retrace that took the current defaults would silently trace a different
    scene.
    """
    rows_path, manifest_path = reference_paths(reference, frequency_hz)
    if not rows_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"no published run called {reference} at {frequency_hz / 1e9:g} GHz")
    rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
    return rows, json.loads(manifest_path.read_text())


def build_tracer(manifest: dict[str, Any], walk_npz: pathlib.Path | None, variant: str) -> SbrTracer:
    """The tracer the published run used, rebuilt from its manifest.

    The ground datum is read rather than measured. The datum rule changed after
    these runs, and here it only enters through the orientation classification
    of the faces, so taking the published value is what makes the retrace a
    retrace.
    """
    site = manifest["site"]
    crop_m = int(manifest.get("crop_radius_m") or 130)
    mesh = site_mesh(site, crop_m)
    if str(mesh) != manifest["mesh"]:
        raise RuntimeError(f"mesh moved: manifest has {manifest['mesh']}, site_mesh resolves {mesh}")
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = float(manifest["ground_datum_m"])
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    areas = geometry.face_areas()
    trace = manifest["trace_config"]
    frequency_hz = float(trace["frequency_hz"])

    materials = manifest["semantic_binding"]["materials"]
    if materials == "geometric":
        binding = load_bindings(CONFIG, frequency_hz)
        covered = 0.0
    elif materials == "walk":
        if walk_npz is None:
            raise ValueError("a walk rung needs --walk-npz, because the published path was a scratch file")
        semantic = bind_from_walk(
            areas,
            face_class,
            walk_npz=walk_npz,
            semantics_path=SEMANTICS,
        )
        face_class = semantic.face_class
        binding = load_bindings(
            CONFIG,
            frequency_hz,
            class_names=semantic.class_names,
            class_binding=semantic.class_binding,
            class_rule=(
                "fused multi station walk semantic posterior where any station saw "
                "the triangle, geometric orientation rule everywhere else"
            ),
        )
        covered = float(semantic.covered_fraction_by_area)
        published = float(manifest["semantic_binding"]["covered_fraction_by_area"])
        if abs(covered - published) > 1e-9:
            raise RuntimeError(
                f"the binding behind {walk_npz.name} covers {covered:.6f} of area and the "
                f"published run covered {published:.6f}. That is a different binding, and "
                f"retracing against it would not be a retrace"
            )
    else:
        raise ValueError(f"this harness only replicates the geometric and walk rungs, not {materials!r}")

    config = TraceConfig(
        frequency_hz=frequency_hz,
        rays=int(trace["rays"]),
        local_cells=int(trace["local_cells"]),
        exit_bands=int(trace["exit_bands"]),
        max_bounces=int(trace["max_bounces"]),
        roulette_start=int(trace["roulette_start"]),
        roulette_floor=float(trace["roulette_floor"]),
        ray_epsilon_m=float(trace["ray_epsilon_m"]),
        seed=int(trace["seed"]),
        batch=int(trace["batch"]),
    )
    print(f"binding covers {covered:.6f} of area, tracer config {config.as_dict()}", flush=True)
    return SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)


def replicate(
    reference: str,
    seeds: tuple[int, ...],
    *,
    frequency_hz: float,
    walk_npz: pathlib.Path | None,
    variant: str,
    workers: int | None,
    limit: int | None,
    tag: str | None,
) -> pathlib.Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows, manifest = load_reference(reference, frequency_hz)
    if limit is not None:
        rows = rows[:limit]
    stem = f"{tag or reference}_{frequency_hz / 1e9:g}ghz"
    out_rows = OUTPUT / f"{stem}_replicas.jsonl"
    out_manifest = OUTPUT / f"{stem}_replicas_manifest.json"

    tracer = build_tracer(manifest, walk_npz, variant)
    published_seed = int(manifest["trace_config"]["seed"])
    started = time.perf_counter()

    out_manifest.write_text(
        json.dumps(
            {
                "generator": "run_seed_replicas.py",
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reference_run": reference,
                "reference_locations": str(reference_paths(reference, frequency_hz)[0]),
                "site": manifest["site"],
                "crop_radius_m": manifest.get("crop_radius_m"),
                "mesh": manifest["mesh"],
                "ground_datum_m": manifest["ground_datum_m"],
                "materials": manifest["semantic_binding"]["materials"],
                "walk_npz": str(walk_npz) if walk_npz else None,
                "published_walk_npz": manifest["semantic_binding"].get("walk_npz"),
                "trace_config": tracer.config.as_dict(),
                "standpoints": len(rows),
                "seeds": list(seeds),
                "per_standpoint_seed_rule": "base + 1000 * walk index, the rule run_exposure.run uses",
                "published_base_seed": published_seed,
                "python": platform.python_version(),
                "host": platform.node(),
            },
            indent=2,
        )
    )

    with out_rows.open("w") as handle:
        for replica, base in enumerate(seeds):
            standpoints = [
                (
                    np.array([row["x"], row["y"], row["z"]]),
                    float(row["ground_z_m"]),
                    base + 1000 * int(row["index"]),
                )
                for row in rows
            ]
            worst = 0.0
            for position, result in trace_standpoints(tracer, standpoints, MODELS, workers=workers):
                row = rows[position]
                scalars = result.scalars()
                record = {
                    "replica": replica,
                    "base_seed": base,
                    "index": int(row["index"]),
                    "seed": base + 1000 * int(row["index"]),
                    "sky_fraction": scalars["sky_fraction"],
                }
                for key in MODEL_KEYS:
                    record[key] = scalars[key]
                if base == published_seed:
                    worst = max(worst, max(abs(scalars[key] - row[key]) for key in MODEL_KEYS))
                handle.write(json.dumps(record) + "\n")
                handle.flush()
            elapsed = time.perf_counter() - started
            note = f", reproduces the published file to {worst:.2e}" if base == published_seed else ""
            print(f"replica {replica} at base seed {base} done{note} ({elapsed:.0f} s total)", flush=True)
    print(f"wrote {out_rows}")
    return out_rows


def _read_replicas(stem: str, frequency_hz: float, limit: int | None = None) -> dict[int, dict[str, np.ndarray]]:
    path = OUTPUT / f"{stem}_{frequency_hz / 1e9:g}ghz_replicas.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    by_replica: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if limit is not None and int(row["replica"]) >= limit:
            continue
        by_replica.setdefault(int(row["replica"]), []).append(row)
    out: dict[int, dict[str, np.ndarray]] = {}
    for replica, group in sorted(by_replica.items()):
        group.sort(key=lambda item: item["index"])
        out[replica] = {key: np.array([item[key] for item in group]) for key in MODEL_KEYS}
        out[replica]["index"] = np.array([item["index"] for item in group])
    return out


def _sd_interval(values: np.ndarray, confidence: float = 0.95) -> list[float]:
    """A 95 percent interval on a standard deviation estimated from few replicas.

    A standard deviation from eight draws is itself uncertain by about a
    quarter, which is the whole reason a disagreement with an earlier
    measurement has to be read against an interval rather than as a number. The
    interval is the chi squared one, which assumes the replicated quantity is
    normal. That assumption is worth stating because the quantity here is a
    median over 120 standpoints and a median moves in steps as ranks swap.
    """
    from scipy import stats

    count = values.size
    variance = float(values.var(ddof=1))
    low = (count - 1) * variance / stats.chi2.ppf(0.5 + confidence / 2.0, count - 1)
    high = (count - 1) * variance / stats.chi2.ppf(0.5 - confidence / 2.0, count - 1)
    return [float(np.sqrt(low)), float(np.sqrt(high))]


def analyse(baseline: str, rung: str, frequency_hz: float, limit: int | None = None) -> pathlib.Path:
    """Turn the replicas into the numbers the Discussion needs, and persist them.

    Three quantities, and they are not interchangeable. The per standpoint
    spread is what a single susceptibility in a table is good to. The spread of
    the median over the walk is what a distribution level number is good to, and
    it is smaller by roughly the square root of the standpoint count. The spread
    of the paired shift between two rungs is smaller again, because the two
    rungs share a ray stream and the common part cancels.
    """
    base = _read_replicas(baseline, frequency_hz, limit)
    report: dict[str, Any] = {
        "generator": "run_seed_replicas.py --analyse",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "baseline_run": baseline,
        "rung_run": rung,
        "replicas": len(base),
        "standpoints": int(base[0]["index"].size),
        "per_standpoint": {},
        "walk_median": {},
    }
    for key in MODEL_KEYS:
        stack = np.array([base[replica][key] for replica in sorted(base)])
        # Per standpoint spread, in dB, of the susceptibility itself.
        per_point_db = 10.0 * np.log10(stack)
        sd = per_point_db.std(axis=0, ddof=1)
        report["per_standpoint"][key] = {
            "sd_db_median": float(np.median(sd)),
            "sd_db_p90": float(np.quantile(sd, 0.9)),
            "sd_db_max": float(sd.max()),
        }
        medians_db = 10.0 * np.log10(np.median(stack, axis=1))
        report["walk_median"][key] = {
            "per_replica_db": [float(x) for x in medians_db],
            "mean_db": float(medians_db.mean()),
            "sd_db": float(medians_db.std(ddof=1)),
            "sd_db_95_interval": _sd_interval(medians_db),
            "standard_error_db": float(medians_db.std(ddof=1) / np.sqrt(medians_db.size)),
        }

    rung_replicas = _read_replicas(rung, frequency_hz, limit)
    shared = sorted(set(base) & set(rung_replicas))
    report["shift"] = {}
    report["crossings"] = {}
    for key in MODEL_KEYS:
        shifts = []
        crossings = []
        for replica in shared:
            low = base[replica][key]
            high = rung_replicas[replica][key]
            shifts.append(10.0 * np.log10(np.median(high) / np.median(low)))
            crossings.append(int(np.count_nonzero(np.abs(10.0 * np.log10(high / low)) > 1.0)))
        array = np.array(shifts)
        report["shift"][key] = {
            "per_replica_db": [float(x) for x in array],
            "mean_db": float(array.mean()),
            "sd_db": float(array.std(ddof=1)),
            "sd_db_95_interval": _sd_interval(array),
            "standard_error_db": float(array.std(ddof=1) / np.sqrt(array.size)),
            "statistic": "10 log10 of the ratio of the two medians over the walk, the published one",
        }
        # The control the crossing counts need: how many standpoints cross 1 dB
        # when nothing changes but the seed.
        control = [
            int(np.count_nonzero(np.abs(10.0 * np.log10(base[b][key] / base[a][key])) > 1.0))
            for a, b in zip(sorted(base)[:-1], sorted(base)[1:], strict=False)
        ]
        report["crossings"][key] = {
            "across_the_rung": crossings,
            "from_a_seed_change_alone": control,
        }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"mc_error_{baseline}_{report['replicas']}x_{frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"wrote {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", default="clean_geometric")
    parser.add_argument("--seeds", default="7,8,9,10,11,12,13,14")
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--walk-npz", default=None)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="trace only the first N standpoints, for a smoke test")
    parser.add_argument("--tag", default=None)
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--baseline", default="clean_geometric")
    parser.add_argument("--rung", default="clean_walk9")
    parser.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="analyse only the first N replicas, so the eight replica figure the audit reported "
        "and a longer run's figure can both be read off the same file",
    )
    args = parser.parse_args()

    frequency_hz = args.frequency_ghz * 1e9
    if args.analyse:
        analyse(args.baseline, args.rung, frequency_hz, args.replicas)
        return
    replicate(
        args.reference,
        tuple(int(x) for x in args.seeds.split(",")),
        frequency_hz=frequency_hz,
        walk_npz=pathlib.Path(args.walk_npz).resolve() if args.walk_npz else None,
        variant=args.variant,
        workers=args.workers,
        limit=args.limit,
        tag=args.tag,
    )


if __name__ == "__main__":
    main()
