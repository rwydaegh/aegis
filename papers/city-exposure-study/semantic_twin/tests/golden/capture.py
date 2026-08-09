"""Run every golden case and write its fixture, plus the manifest.

    python tests/golden/capture.py                # all cases
    python tests/golden/capture.py --tier fast    # one tier
    python tests/golden/capture.py --case exposure_korenmarkt_130m_walk
    python tests/golden/capture.py --seed-spread  # remeasure the physics scale

Run it from the study root, the directory that holds `run_exposure.py`.

The manifest records the machine, the git commit, the library versions and the
wall time of every case, because a golden lock whose provenance is not written
down is a set of numbers nobody can argue with later.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# The study root, so `import semantic_twin` works when this file is run as a
# script from anywhere. The cases themselves are subprocesses with cwd at the
# root and do not need it.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from golden.cases import CASES, CASES_BY_ID, GOLDEN_DIR, ROOT, Case


SOURCE_PATHSPECS = (
    ":(top)papers/city-exposure-study/semantic_twin",
    ":(top)src/aegis",
    ":(top,exclude,glob)papers/city-exposure-study/semantic_twin/tests/golden/*.json",
    ":(top,exclude)papers/city-exposure-study/semantic_twin/CODEX_PROMPT.md",
    ":(top,exclude)papers/city-exposure-study/semantic_twin/HANDOFF.md",
    ":(top,exclude,glob)papers/city-exposure-study/semantic_twin/docs/HANDOFF_*.md",
)

#: What the lock deliberately does not cover, and why. A hole nobody wrote down
#: reads later as a hole nobody noticed.
DELIBERATE_HOLES = {
    "next_event_walk_paths": (
        "run_next_event.py --walk-path street and --walk-path closest are not locked. "
        "Both ask the Google Routes API, and a network call does not belong in a golden "
        "test. Only --walk-path links, which walks the local capture chain, is covered."
    ),
    "cross_machine_bit_equality": (
        "Every reproducibility claim in this manifest was measured on the machine "
        "recorded above. tests/test_determinism.py records that the two elevation "
        "weighted susceptibilities drift one or two units in the last place across "
        "libm versions. The tolerance is sized for that and it was not tested."
    ),
    "coverage_ladder_breadth": (
        "The ladder is locked at one site and one seed, korenmarkt at 130 m on seed 7. "
        "Six more sites are admitted at 130 m and seven at 250 m, and the published "
        "error bar comes from several seeds. What is locked is the ladder arithmetic, "
        "not the published spread."
    ),
    "coverage_ladder_resumes": (
        "Not a hole any more, but worth recording because it was one for an afternoon. "
        "run_exposure.reusable() lets --coverage-ladder accept a rung already on disk "
        "whose settings match, which is right for a sweep that has to survive being "
        "stopped. It means a golden test on that flag re-reads three runs instead of "
        "making them: the case took 1.7 s and checked nothing but the two reports. The "
        "Case now carries a clears list, and both capture.py and the test delete the "
        "three golden tagged rungs first, so the run traces. It takes 53 s and it "
        "reproduced the reused numbers to the last bit. Only paths whose name holds "
        "'golden' can be deleted; Case.clear() raises on anything else."
    ),
    "clean_checkout": (
        "None of the end to end cases can run from a fresh clone. They read meshes under "
        "data/geometry, fishnet surfaces under outputs/<site>_fishnet_vistas, the fused "
        "walk under outputs/walk_korenmarkt, and outputs/evidence_coverage.json, which "
        "decides whether a fishnet rung is offered at all. outputs/ is 3.7 GB and "
        "gitignored, and the 250 m meshes are gitignored too. So the fixtures are a lock "
        "on this working tree, not a lock anyone can reproduce from git alone. The "
        "numeric tier is the part that does run anywhere: it needs no mesh and no "
        "outputs/."
    ),
    "materials_walk_variants": (
        "walk_material, walk_material_mixture, walk_material_over_entity and "
        "walk_material_facade_only are not locked. Plain walk and plain semantic are."
    ),
    "per_site_single_runs": (
        "There is no separate --site case for the eight squares other than korenmarkt, "
        "brussels_grandplace and prague_staromestske. They are not unlocked: cities_250m_all_sites traces every "
        "one of the eleven through the same run() the single site cases use, and its "
        "fixture keeps all eight standpoint rows per site, so a geometry regression at any "
        "square fails there and the failing key names the site. "
        "test_every_site_is_locked_by_the_sweep asserts each square separately off that "
        "fixture. What is genuinely not covered is the other nine at the 130 m crop, and a "
        "site whose mesh is missing at 250 m, which run_all_sites skips by design and "
        "sites_present would then record as fewer than eleven."
    ),
}

#: What was measured about reproducibility rather than assumed. Every line here
#: was run on the machine recorded in the manifest.
REPRODUCIBILITY = {
    "same_seed_rerun": (
        "Every case was run at least twice and reduced twice, and every fixture came "
        "back byte identical. That includes the eleven city sweep, captured once at "
        "294.7 s and once at 236.4 s of wall time for the same numbers to the last bit, "
        "and the coverage ladder, whose three rungs were once read from disk and once "
        "retraced from scratch, again for the same numbers."
    ),
    "worker_count": (
        "exposure_korenmarkt_130m_geometric at --workers 1 and at --workers 4 gives "
        "bit identical rows. The pool splits standpoints, it does not split rays."
    ),
    "blas_threads": (
        "The fast tier passes at rtol 1e-12 with OMP_NUM_THREADS, OPENBLAS_NUM_THREADS "
        "and MKL_NUM_THREADS all pinned to 1 and with all three unset."
    ),
    "seed_meaning": (
        "--seed moves the walk as well as the tracer, so two seeds do not sample the "
        "same standpoints. The spread recorded under seed_spread is therefore "
        "standpoint resampling and Monte Carlo noise together, and the resampling "
        "dominates. It is a scale for reading a failure, not a tolerance."
    ),
}

#: Numbers in these fixtures that are faithful records of a thin statistic. They
#: are locked because they are what the driver produces, not because they are
#: stable, and a reader must not take them for a converged answer.
THIN_STATISTICS = {
    "next_event_250m_default:korenmarkt": (
        "The published median at Korenmarkt is a median of TWO standpoints. "
        "run_next_event.py at its own defaults asks for 16 held out of 144, the capture "
        "route there is 49 m long and yields 14 standpoints, and the shrink rule "
        "held_out * points / (held_out + builders) rounds 14 * 16 / 144 down to 2. "
        "The p5 and p95 either side of it are therefore the two points themselves. "
        "Escalated as a paper question. The rule was not changed and this fixture "
        "records the behaviour as it stands."
    ),
    "next_event_korenmarkt_130m_fast:korenmarkt": (
        "Four held out standpoints, for the same reason and to a lesser degree."
    ),
    "coverage_ladder_korenmarkt_130m:paired_median_shift_db": (
        "Locked at eight standpoints, where the published ladder used 120. The paired "
        "median shift for the fishnet rung is 3.6e-8 dB. The distribution median shift is "
        "0.011749 dB and the largest absolute change is 0.459 %. The paired median alone "
        "hides the small changes at this standpoint count, so read all three statistics."
    ),
}


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _git_dirty(cwd: pathlib.Path, pathspecs: tuple[str, ...] = ()) -> bool:
    """Return Git dirty state, failing closed when status cannot be read."""
    command = ["git", "status", "--porcelain=v1", "--untracked-files=all"]
    if pathspecs:
        command.extend(("--", *pathspecs))
    try:
        status = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True
    return bool(status)


def _versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for name in ("numpy", "scipy", "mitsuba", "drjit", "trimesh"):
        try:
            module = __import__(name)
            out[name] = getattr(module, "__version__", "unknown")
        except Exception as exc:  # noqa: BLE001
            out[name] = f"missing ({exc.__class__.__name__})"
    return out


def machine() -> dict[str, object]:
    import os

    return {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "versions": _versions(),
        "env": {
            name: os.environ.get(name)
            for name in ("AEGIS_DATA_DIR", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def source_provenance() -> dict[str, object]:
    """Describe the source tree before fixture writes can make it dirty."""
    return {
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": _git_dirty(ROOT),
        "source_dirty": _git_dirty(ROOT, SOURCE_PATHSPECS),
    }


def case_provenance(source: dict[str, object]) -> dict[str, object]:
    """Return provenance for one fixture captured from ``source``."""
    return {
        "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": source["git_sha"],
        "git_dirty": source["git_dirty"],
        "source_dirty": source["source_dirty"],
    }


def run_case(case: Case, python: str, *, ran: set[str] | None = None) -> float:
    """Run the case's command as a subprocess. Returns wall seconds.

    A case with prerequisites runs them first unless they already ran in this
    process. ``--cities-report`` traces nothing and reads the per site rows off
    disk, so on its own it would aggregate whatever happened to be there.
    """
    ran = set() if ran is None else ran
    for name in case.prerequisites:
        if name in ran:
            continue
        print(f"  (prerequisite of {case.ident}: {name})", flush=True)
        run_case(CASES_BY_ID[name], python, ran=ran)
        ran.add(name)
    gone = case.clear()
    if gone:
        print(f"  (cleared {len(gone)} file(s) so {case.ident} traces rather than resumes)", flush=True)
    command = [python, *case.command()]
    print(f"\n$ {' '.join(command)}", flush=True)
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    seconds = time.perf_counter() - started
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-4000:])
        sys.stderr.write(proc.stderr[-4000:])
        raise RuntimeError(f"{case.ident} exited {proc.returncode}")
    print(f"  {seconds:.1f} s", flush=True)
    return seconds


def seed_spread(python: str, seeds: tuple[int, ...] = (7, 8, 9, 10, 11)) -> dict[str, object]:
    """How far the answer moves when only the seed moves.

    This is the yardstick a regression failure has to be read against. The seed
    drives two things at once in ``run_exposure.py``: which standpoints the walk
    draws, and every random number in the trace. So the spread below is the
    combined term, and it is dominated by the standpoint draw, which is what
    GROUND_DATUM.md already reports as the study's largest error.

    The pure Monte Carlo part is measured separately, at a fixed standpoint,
    under ``monte_carlo`` below.
    """
    import numpy as np

    from golden.cases import EXPOSURE_OUT

    keys = (
        "chi_isotropic",
        "chi_rooftop",
        "chi_street_small_cell",
        "sky_fraction",
        "mean_bounces",
        "isotropic_peak_sab_w_m2",
        "rooftop_peak_sab_w_m2",
        "isotropic_sar_wb_w_kg",
        "rooftop_sar_wb_w_kg",
    )
    base = CASES_BY_ID["exposure_korenmarkt_130m_geometric"]
    medians: dict[str, list[float]] = {key: [] for key in keys}
    indices: list[list[int]] = []
    for seed in seeds:
        argv = list(base.argv)
        argv[argv.index("--seed") + 1] = str(seed)
        argv[argv.index("--tag") + 1] = f"golden_spread_seed{seed}"
        probe = Case(
            ident=f"spread_seed{seed}",
            driver=base.driver,
            argv=tuple(argv),
            tier="spread",
            what_it_locks="seed spread probe",
        )
        rows_path = EXPOSURE_OUT / f"golden_spread_seed{seed}_15ghz_locations.jsonl"
        # These runs are deterministic and each takes about a minute, so a
        # completed one is reused rather than repeated. Completed means the
        # driver wrote its wall time into the manifest, which it only does after
        # the last standpoint.
        manifest = EXPOSURE_OUT / f"golden_spread_seed{seed}_15ghz_manifest.json"
        done = (
            rows_path.exists()
            and manifest.exists()
            and "wall_seconds" in json.loads(manifest.read_text())
            and len(rows_path.read_text().splitlines()) == 16
        )
        if done:
            print(f"reusing golden_spread_seed{seed}", flush=True)
        else:
            run_case(probe, python)
        rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
        indices.append([row["index"] for row in rows])
        for key in keys:
            medians[key].append(float(np.median([row[key] for row in rows])))

    summary = {}
    for key, values in medians.items():
        arr = np.asarray(values)
        summary[key] = {
            "medians": [float(v) for v in arr],
            "mean": float(arr.mean()),
            "std": float(arr.std(ddof=1)),
            "relative_range": float((arr.max() - arr.min()) / np.median(arr)),
            "db_range": float(10.0 * np.log10(arr.max() / arr.min())),
        }
    return {
        "note": (
            "run_exposure.py's --seed drives the walk and the trace together, so this "
            "spread is standpoint resampling plus Monte Carlo, not Monte Carlo alone"
        ),
        "case": base.ident,
        "seeds": list(seeds),
        "standpoint_sets_identical": all(row == indices[0] for row in indices),
        "median_over_16_standpoints": summary,
    }


def monte_carlo(seeds: int = 8) -> dict[str, object]:
    """Monte Carlo noise alone: one fixed standpoint, one fixed walk, eight trace seeds."""
    import numpy as np
    from semantic_twin.materials import classify_faces, load_table
    from semantic_twin.walk import build_walk, measure_ground_datum

    from semantic_twin.propagation import MODELS, MitsubaGeometry, SbrTracer, TraceConfig

    mesh = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
    geometry = MitsubaGeometry(mesh, variant="llvm_ad_rgb")
    datum = measure_ground_datum(geometry, radius_m=90.0)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum.z_m)
    binding = load_table(ROOT / "config", 15.0e9)
    walk = build_walk(geometry, ground_datum_m=datum.z_m, radius_m=90.0, spacing_m=3.0, seed=7)
    config = TraceConfig(frequency_hz=15.0e9, rays=200_000, local_cells=512, max_bounces=3, seed=7)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    out: dict[str, object] = {
        "note": "one standpoint, one walk, eight trace seeds, 200 000 rays",
        "rays": 200_000,
        "standpoints": {},
    }
    for index in (427, 213):
        origin = walk.points[index]
        ground = float(walk.ground_z_m[index])
        draws: dict[str, list[float]] = {name: [] for name in MODELS}
        for s in range(seeds):
            point = tracer.trace(origin, MODELS, ground_z_m=ground, seed=90_000 + s)
            for name in MODELS:
                draws[name].append(point.susceptibility[name])
        out["standpoints"][str(index)] = {  # type: ignore[index]
            name: {
                "mean": float(np.mean(values)),
                "relative_std": float(np.std(values, ddof=1) / np.mean(values)),
                "relative_range": float((max(values) - min(values)) / np.mean(values)),
            }
            for name, values in draws.items()
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["fast", "slow", "all"], default="all")
    parser.add_argument("--case", action="append", default=None)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--seed-spread", action="store_true", help="remeasure the physics scale as well")
    parser.add_argument("--skip-cases", action="store_true", help="only redo the manifest and the spread")
    args = parser.parse_args()

    selected = (
        []
        if args.skip_cases
        else [
            case
            for case in CASES
            if (args.case is None or case.ident in args.case) and (args.tier == "all" or case.tier == args.tier)
        ]
    )
    if not selected and not args.skip_cases:
        raise SystemExit("no cases selected")

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = GOLDEN_DIR / "MANIFEST.json"
    manifest: dict[str, object] = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("what", "reference outputs captured before the semantic_twin refactor")
    manifest.setdefault("study_root", str(ROOT))
    if "machine" not in manifest:
        manifest["machine"] = machine()
    manifest["provenance_rule"] = (
        "Each cases entry records the capture time and source state for that fixture. "
        "source_dirty covers executable study inputs and src/aegis while excluding golden JSON and local handoffs. "
        "The top-level captured_utc, git_sha, and git_dirty fields are a legacy fallback "
        "only for entries which have not yet been recaptured with per-case provenance."
    )
    cases_block: dict[str, object] = dict(manifest.get("cases", {}))  # type: ignore[arg-type]
    manifest["deliberate_holes"] = DELIBERATE_HOLES
    manifest["thin_statistics"] = THIN_STATISTICS
    manifest["reproducibility"] = REPRODUCIBILITY

    source = source_provenance()
    ran: set[str] = set()
    for case in selected:
        seconds = run_case(case, args.python, ran=ran)
        ran.add(case.ident)
        payload = case.reduce()
        case.fixture.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
        provenance = case_provenance(source)
        cases_block[case.ident] = {
            "tier": case.tier,
            "driver": case.driver,
            "command": " ".join([pathlib.Path(args.python).name, *case.command()]),
            "argv": list(case.argv),
            "what_it_locks": case.what_it_locks,
            "writes": list(case.writes),
            "prerequisites": list(case.prerequisites),
            "clears": list(case.clears),
            "wall_seconds": round(seconds, 2),
            "fixture": case.fixture.name,
            "fixture_bytes": case.fixture.stat().st_size,
            **provenance,
        }
        print(f"  wrote {case.fixture.name} ({case.fixture.stat().st_size / 1024:.1f} kB)", flush=True)

    # Everything about a case except its wall time and its numbers is a
    # description, and a description that drifts from cases.py is worse than no
    # description. Refresh those on every run, including a --skip-cases run,
    # which is how an edit to what_it_locks reaches the manifest without a
    # nine minute sweep.
    for case in CASES:
        entry = cases_block.get(case.ident)
        if entry is None:
            continue
        entry.update(
            {
                "tier": case.tier,
                "driver": case.driver,
                "argv": list(case.argv),
                "what_it_locks": case.what_it_locks,
                "writes": list(case.writes),
                "prerequisites": list(case.prerequisites),
                "clears": list(case.clears),
                "fixture": case.fixture.name,
                "fixture_bytes": case.fixture.stat().st_size if case.fixture.exists() else None,
            }
        )
    manifest["cases"] = cases_block
    if args.seed_spread:
        manifest["seed_spread"] = seed_spread(args.python)
        manifest["monte_carlo_noise"] = monte_carlo()
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"\nwrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
