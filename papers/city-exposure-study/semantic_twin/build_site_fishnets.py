"""Run the fishnet chain over every usable registered panorama of a site.

The chain is the Korenmarkt one, three stages per panorama centre::

    crop_fused_semantics.py   fused equirectangular semantics -> crop label maps
    raycast_mesh_depth.py     support mesh -> first-hit range and face id buffer
    build_fishnet_surface.py  support triangles cut at the semantic islands

Korenmarkt and Milan ran that chain once each, on the one panorama the site
directory held.  Six sites carry a set of registered Street View panoramas
instead, so the chain runs once per panorama and the site output is the union of
those visible surface sets.  Nothing is merged across centres here.  Two centres
that see the same wall each emit their own faces for it, and de-duplicating them
is the propagation stage's problem, not this one's.

Which poses are admitted
------------------------

A pose is skipped when its recorded ``sky_conflict`` says the camera sits inside
the geometry: the segmentation calls more than ``--max-sky-hit-fraction`` of the
directions sky while the support mesh returns a first hit along them, and the
median range of those conflicts is under ``--min-conflict-range-m``.  A camera
outside the buildings has a handful of sky conflicts tens of metres away.  A
camera inside one has almost all of them, at arm's length, and its fishnet is
the inside of a wall.  The skyline residual does not see this, so it is reported
next to the verdict rather than used as the gate.

Where the surface sets land
---------------------------

``semantic_binding.bind`` globs ``*_fishnet.npz`` at the top of the directory it
is given and does not recurse, so the four NPZ files of every panorama are
written flat into ``outputs/<site>_fishnet_vistas`` with the panorama in the
file name, ``pano_07_<id>_h+00_000_fishnet.npz``.  That is what makes a
multi-centre site look to the binding like the single-centre Korenmarkt one:
faces from different centres are separate votes on the same support triangles,
which is the aggregation ``bind`` already performs.  The per-panorama manifests
stay in a subdirectory, where nothing globs them.

The intermediate crop label maps and mesh depth buffers are deleted once the
fishnet is written, since together they are an order of magnitude larger than
the surface set they produce and both stages rebuild them in seconds.  Pass
``--keep-intermediates`` to hold on to them.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python build_site_fishnets.py --site prague_staromestske
    ../../../.venv/bin/python build_site_fishnets.py --all-sites --workers 2
    ../../../.venv/bin/python build_site_fishnets.py --all-sites --flatten-only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent

#: The sites that carry registered Street View panoramas with segmented
#: semantics beside them and no fishnet of their own.
SITES = (
    "brussels_grandplace",
    "madrid_plazamayor",
    "mexico_zocalo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
)


def panorama_image(directory: pathlib.Path) -> pathlib.Path | None:
    """Highest zoom equirectangular image cached for one panorama."""
    candidates = sorted(directory.glob("panorama_z*.jpg"))
    return candidates[-1] if candidates else None


def pose_verdict(pose_path: pathlib.Path, *, max_sky_hit: float, min_conflict_range_m: float) -> dict[str, Any]:
    """Admit or reject one registered pose on its recorded sky conflict."""
    if not pose_path.exists():
        return {"admitted": False, "reason": "no pose_aligned.json"}
    pose = json.loads(pose_path.read_text())
    conflict = pose.get("sky_conflict")
    residual = pose.get("skyline_score_mean_deg")
    if conflict is None:
        return {"admitted": False, "reason": "pose carries no sky_conflict block", "residual_deg": residual}
    fraction = conflict.get("sky_with_mesh_hit_fraction")
    median_range = conflict.get("conflict_median_range_m")
    record = {
        "residual_deg": residual,
        "sky_with_mesh_hit_fraction": fraction,
        "conflict_median_range_m": median_range,
        "sky_conflict_mesh": conflict.get("mesh"),
    }
    if fraction is None or median_range is None:
        return {"admitted": False, "reason": "sky_conflict is incomplete", **record}
    if fraction > max_sky_hit and median_range < min_conflict_range_m:
        return {
            "admitted": False,
            "reason": (
                f"camera inside the geometry: {fraction:.3f} of sky directions hit the mesh at a median "
                f"{median_range:.2f} m"
            ),
            **record,
        }
    return {"admitted": True, **record}


def flatten(out: pathlib.Path) -> int:
    """Move one panorama's surface sets up to the site directory, named for it.

    Idempotent, so it can be run over a tree an earlier build left nested.
    """
    moved = 0
    for path in sorted(out.glob("*_fishnet.npz")):
        destination = out.parent / f"{out.name}_{path.name}"
        path.replace(destination)
        moved += 1
    return moved


def run(command: list[str], log: pathlib.Path) -> None:
    with log.open("a") as handle:
        handle.write("$ " + " ".join(command) + "\n")
        handle.flush()
        subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=True)


def build_one(job: dict[str, Any]) -> dict[str, Any]:
    """Crop, cast and cut one panorama centre."""
    directory = pathlib.Path(job["directory"])
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    log = out / "build.log"
    views = out / "views"
    depth = out / "mesh_depth"
    python = sys.executable
    started = time.perf_counter()
    try:
        crop = [
            python,
            "crop_fused_semantics.py",
            "--semantics",
            str(directory / "semantics"),
            "--out",
            str(views),
            "--size",
            str(job["size"]),
        ]
        if job["panorama"]:
            crop += ["--panorama", job["panorama"]]
        run(crop, log)
        run(
            [
                python,
                "raycast_mesh_depth.py",
                "--mesh",
                job["mesh"],
                "--pose",
                str(directory / "alignment" / "pose_aligned.json"),
                "--views",
                str(views),
                "--out",
                str(depth),
            ],
            log,
        )
        run(
            [
                python,
                "build_fishnet_surface.py",
                "--mesh",
                job["mesh"],
                "--pose",
                str(directory / "alignment" / "pose_aligned.json"),
                "--views",
                str(views),
                "--mesh-depth",
                str(depth),
                "--semantics-json",
                str(directory / "semantics" / "semantics.json"),
                "--out",
                str(out),
            ],
            log,
        )
    except subprocess.CalledProcessError as error:
        return {"panorama": directory.name, "status": "failed", "reason": f"{error.cmd[1]} exited {error.returncode}"}

    manifest = json.loads((out / "fishnet_manifest.json").read_text())
    faces = int(sum(view["triangles"] for view in manifest["views"]))
    area = float(sum(view["surface_area_m2"] for view in manifest["views"]))
    flatten(out)
    if not job["keep_intermediates"]:
        shutil.copy2(depth / "manifest.json", out / "mesh_depth_manifest.json")
        shutil.copy2(views / "crop_settings.json", out / "crop_settings.json")
        shutil.rmtree(views)
        shutil.rmtree(depth)
    return {
        "panorama": directory.name,
        "status": "built",
        "views": len(manifest["views"]),
        "faces": faces,
        "surface_area_m2": area,
        "occlusion_budget_fraction": manifest["site_occlusion_budget"]["occlusion_budget_fraction"],
        "seconds": round(time.perf_counter() - started, 1),
    }


def site_mesh(site: str, requested: str) -> pathlib.Path:
    """The requested crop for a site, picked by precision rather than by name.

    Asking for an exact filename says the wrong thing. Only Korenmarkt ever had
    two builds of the same crop: a `format_version: 2` one whose tile placement
    went through Blender in single precision and carries up to a metre of
    seaming, and an `_f64` rebuild that does not. Every other site was built
    after that fix, so its unsuffixed file is already the good one, and ten of
    them happen to carry an `_f64` copy as well.

    Requiring the suffix therefore stopped the 250 m build at Times Square,
    which has one mesh, at `format_version: 3`, and is fine. It also took
    Prague down with it, since the run stopped there. What matters is the
    format version in the manifest, so that is what is read.
    """
    directory = ROOT / "data" / "geometry" / site
    stem = requested[: -len("_f64.ply")] if requested.endswith("_f64.ply") else requested.removesuffix(".ply")
    for candidate in (f"{stem}_f64.ply", f"{stem}.ply"):
        path = directory / candidate
        manifest = path.with_suffix(".json")
        if not path.exists() or not manifest.exists():
            continue
        if int(json.loads(manifest.read_text()).get("format_version", 0)) >= 3:
            return path
    raise SystemExit(f"{site} has no double precision {stem} mesh")


def site_jobs(site: str, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mesh = site_mesh(site, args.mesh)
    out_root = ROOT / "outputs" / f"{site}_fishnet_vistas{args.out_suffix}"
    jobs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for directory in sorted((ROOT / "data" / "panoramas" / site).glob("pano_*")):
        verdict = pose_verdict(
            directory / "alignment" / "pose_aligned.json",
            max_sky_hit=args.max_sky_hit_fraction,
            min_conflict_range_m=args.min_conflict_range_m,
        )
        if not (directory / "semantics" / "panorama_semantics.npz").exists():
            verdict = {**verdict, "admitted": False, "reason": "no segmented panorama"}
        if not verdict["admitted"]:
            skipped.append({"panorama": directory.name, **verdict})
            continue
        image = panorama_image(directory)
        jobs.append(
            {
                "site": site,
                "directory": str(directory),
                "out": str(out_root / directory.name),
                "mesh": str(mesh.relative_to(ROOT)),
                "panorama": str(image) if image else None,
                "size": args.size,
                "keep_intermediates": args.keep_intermediates,
                "verdict": verdict,
            }
        )
    return jobs, skipped


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", action="append", choices=SITES)
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--mesh", default="inhouse_leaf_130m.ply")
    parser.add_argument(
        "--out-suffix",
        default="",
        help=(
            "appended to outputs/<site>_fishnet_vistas. A build against a different mesh "
            "belongs beside the old one and not on top of it, since the two are only "
            "comparable if both survive"
        ),
    )
    parser.add_argument("--size", type=int, default=1536)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-sky-hit-fraction", type=float, default=0.5)
    parser.add_argument("--min-conflict-range-m", type=float, default=2.0)
    parser.add_argument("--keep-intermediates", action="store_true")
    parser.add_argument(
        "--flatten-only",
        action="store_true",
        help="move already built surface sets up to the site directory and rewrite the site manifest",
    )
    return parser.parse_args()


def main() -> None:
    args = arguments()
    sites = list(SITES) if args.all_sites else list(args.site or [])
    if not sites:
        raise SystemExit("name a site with --site or run --all-sites")
    for site in sites:
        jobs, skipped = site_jobs(site, args)
        out_root = ROOT / "outputs" / f"{site}_fishnet_vistas{args.out_suffix}"
        out_root.mkdir(parents=True, exist_ok=True)
        print(f"[site] {site}: {len(jobs)} panoramas admitted, {len(skipped)} skipped", flush=True)
        results: list[dict[str, Any]] = []
        if args.flatten_only:
            for job in jobs:
                out = pathlib.Path(job["out"])
                manifest_path = out / "fishnet_manifest.json"
                if not manifest_path.exists():
                    results.append({"panorama": out.name, "status": "failed", "reason": "no fishnet_manifest.json"})
                    continue
                flatten(out)
                manifest = json.loads(manifest_path.read_text())
                results.append(
                    {
                        "panorama": out.name,
                        "status": "built",
                        "views": len(manifest["views"]),
                        "faces": int(sum(view["triangles"] for view in manifest["views"])),
                        "surface_area_m2": float(sum(view["surface_area_m2"] for view in manifest["views"])),
                        "occlusion_budget_fraction": manifest["site_occlusion_budget"]["occlusion_budget_fraction"],
                        "seconds": None,
                    }
                )
        elif jobs:
            with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
                for record in pool.map(build_one, jobs):
                    results.append(record)
                    print(f"[site] {site} {record['panorama']}: {record}", flush=True)
        built = [record for record in results if record["status"] == "built"]
        (out_root / "site_fishnet_manifest.json").write_text(
            json.dumps(
                {
                    "site": site,
                    "mesh": args.mesh,
                    "crop_size_px": args.size,
                    "semantics_source": "fused equirectangular panorama semantics, cut back into the crop geometry",
                    "admission": {
                        "max_sky_hit_fraction": args.max_sky_hit_fraction,
                        "min_conflict_range_m": args.min_conflict_range_m,
                        "rule": (
                            "a pose is rejected when more than max_sky_hit_fraction of its sky directions return a "
                            "mesh first hit and the median range of those conflicts is under min_conflict_range_m"
                        ),
                    },
                    "panoramas_present": len(jobs) + len(skipped),
                    "panoramas_built": len(built),
                    "fishnet_views": int(sum(record["views"] for record in built)),
                    "faces": int(sum(record["faces"] for record in built)),
                    "surface_area_m2": float(sum(record["surface_area_m2"] for record in built)),
                    "median_occlusion_budget_fraction": (
                        float(np.median([record["occlusion_budget_fraction"] for record in built])) if built else None
                    ),
                    "built": built,
                    "failed": [record for record in results if record["status"] != "built"],
                    "skipped": skipped,
                },
                indent=2,
            )
        )
        print(
            f"[site] {site}: {len(built)} built, {int(sum(r['faces'] for r in built))} faces, "
            f"{float(sum(r['surface_area_m2'] for r in built)):.1f} m2 -> {out_root}",
            flush=True,
        )


if __name__ == "__main__":
    main()
