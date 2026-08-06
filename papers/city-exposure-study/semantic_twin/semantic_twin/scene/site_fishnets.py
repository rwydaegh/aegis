"""Build fishnets over every usable registered panorama of a site.

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

A pose passes the same versioned production gate as the walk and atlas builders.
It needs complete diagnostics, a skyline residual at most 4 degrees, an interior
vertical optimum, and no inside-geometry signature. The inside signature is a
sky-hit fraction above ``--max-sky-hit-fraction`` AND a median conflict range
below ``--min-conflict-range-m``. A large distant mismatch remains a separate,
visible state.

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

import json
import pathlib
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin import paths, sites
from semantic_twin.vision.provenance import AdmissionGate, Registration

#: The sites that carry registered panoramas with segmented semantics beside
#: them. Korenmarkt and Milan are here even though each has only one camera:
#: they were left out while the list meant "sites with no fishnet of their own",
#: and the result was that the 250 m build covered nine squares of eleven and
#: said nothing about the two it never looked at.
SITES = tuple(site.name for site in sites.with_registered_stations())


@dataclass(frozen=True)
class FishnetBuildOptions:
    """Settings shared by every panorama and site in one fishnet build."""

    mesh_name: str = "inhouse_leaf_130m.ply"
    out_suffix: str = ""
    size: int = 1536
    workers: int = 2
    max_residual_deg: float = 4.0
    max_sky_hit_fraction: float = 0.5
    min_conflict_range_m: float = 2.0
    keep_intermediates: bool = False
    flatten_only: bool = False

    @property
    def admission_gate(self) -> AdmissionGate:
        return AdmissionGate(
            max_residual_deg=self.max_residual_deg,
            max_sky_conflict=self.max_sky_hit_fraction,
            min_conflict_range_m=self.min_conflict_range_m,
        )


def panorama_image(directory: pathlib.Path) -> pathlib.Path | None:
    """Highest zoom equirectangular image cached for one panorama."""
    candidates = sorted(directory.glob("panorama_z*.jpg"))
    return candidates[-1] if candidates else None


def pose_verdict(
    pose_path: pathlib.Path,
    *,
    max_sky_hit: float,
    min_conflict_range_m: float,
    max_residual_deg: float = 4.0,
) -> dict[str, Any]:
    """Admit or reject one registered pose with the shared production gate."""
    gate = AdmissionGate(
        max_residual_deg=max_residual_deg,
        max_sky_conflict=max_sky_hit,
        min_conflict_range_m=min_conflict_range_m,
    )
    if not pose_path.exists():
        return {
            "admitted": False,
            "reason": "missing pose artifact: alignment/pose_aligned.json",
            "refused_because": ["missing pose artifact: alignment/pose_aligned.json"],
            "admission_gate_version": gate.version,
        }
    pose = json.loads(pose_path.read_text())
    conflict = pose.get("sky_conflict") if isinstance(pose.get("sky_conflict"), dict) else {}
    registration = Registration.from_pose(pose)
    verdict = registration.verdict(gate)
    record = {
        "residual_deg": registration.residual_deg,
        "sky_with_mesh_hit_fraction": registration.sky_conflict,
        "conflict_median_range_m": registration.conflict_median_range_m,
        "sky_conflict_mesh": conflict.get("mesh"),
        "sky_conflict_state": verdict.sky_conflict_state,
        "dz_at_bound": registration.dz_at_bound,
        "admission_gate_version": gate.version,
        "refused_because": list(verdict.reasons),
    }
    return {
        "admitted": verdict.admitted,
        "reason": ". ".join(verdict.reasons) if verdict.reasons else None,
        **record,
    }


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
        subprocess.run(command, cwd=paths.root(), stdout=handle, stderr=subprocess.STDOUT, check=True)


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
    stem = requested[: -len("_f64.ply")] if requested.endswith("_f64.ply") else requested.removesuffix(".ply")
    prefix = f"{paths.GOOGLE_MESH_STEM}_"
    encoded = stem.removeprefix(prefix).removesuffix("m")
    if stem.startswith(prefix) and encoded.isdigit():
        try:
            return paths.site_mesh(site, int(encoded))
        except FileNotFoundError as error:
            raise SystemExit(f"{site} has no double precision {stem} mesh") from error

    directory = paths.geometry_dir(site)
    for name in (f"{stem}_f64.ply", f"{stem}.ply"):
        candidate = directory / name
        manifest = paths.mesh_manifest(candidate)
        if not candidate.exists() or not manifest.exists():
            continue
        if int(json.loads(manifest.read_text()).get("format_version", 0)) >= paths.MIN_MESH_FORMAT_VERSION:
            return candidate
    raise SystemExit(f"{site} has no double precision {stem} mesh")


def panorama_dirs(site: str) -> list[pathlib.Path]:
    """Every panorama directory a site has, in either of the two layouts.

    A site fetched by ``fetch_site_panoramas.py`` gets one ``pano_NN_<id>``
    directory per camera. The two sites acquired before that script existed,
    Korenmarkt and Milan, put their single camera's files straight into the site
    directory instead. Globbing ``pano_*`` therefore returned nothing for them,
    silently: no error, no job, no fishnet, and the 250 m build simply skipped
    two of the eleven squares while reporting success on nine.
    """
    return list(sites.Site.get(site).stations())


def site_jobs(
    site: str,
    options: FishnetBuildOptions,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mesh = site_mesh(site, options.mesh_name)
    out_root = paths.outputs_dir() / f"{site}_fishnet_vistas{options.out_suffix}"
    jobs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for directory in panorama_dirs(site):
        verdict = pose_verdict(
            directory / "alignment" / "pose_aligned.json",
            max_residual_deg=options.max_residual_deg,
            max_sky_hit=options.max_sky_hit_fraction,
            min_conflict_range_m=options.min_conflict_range_m,
        )
        missing_semantics: list[str] = []
        if not (directory / "semantics" / "panorama_semantics.npz").exists():
            missing_semantics.append("missing dense semantic artifact: semantics/panorama_semantics.npz")
        if not (directory / "semantics" / "semantics.json").exists():
            missing_semantics.append("missing semantic metadata artifact: semantics/semantics.json")
        if missing_semantics:
            previous = list(verdict.get("refused_because", []))
            verdict = {
                **verdict,
                "admitted": False,
                "reason": ". ".join([*previous, *missing_semantics]),
                "refused_because": [*previous, *missing_semantics],
            }
        if not verdict["admitted"]:
            skipped.append({"panorama": directory.name, **verdict})
            continue
        image = panorama_image(directory)
        jobs.append(
            {
                "site": site,
                "directory": str(directory),
                "out": str(out_root / directory.name),
                "mesh": str(mesh.relative_to(paths.root())),
                "panorama": str(image) if image else None,
                "size": options.size,
                "keep_intermediates": options.keep_intermediates,
                "verdict": verdict,
            }
        )
    return jobs, skipped


def build_sites(
    selected_sites: list[str],
    options: FishnetBuildOptions,
) -> None:
    """Build and summarise the fishnets for a set of registered sites."""
    for site in selected_sites:
        jobs, skipped = site_jobs(site, options)
        out_root = paths.outputs_dir() / f"{site}_fishnet_vistas{options.out_suffix}"
        out_root.mkdir(parents=True, exist_ok=True)
        print(f"[site] {site}: {len(jobs)} panoramas admitted, {len(skipped)} skipped", flush=True)
        results: list[dict[str, Any]] = []
        if options.flatten_only:
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
            with ProcessPoolExecutor(max_workers=max(1, options.workers)) as pool:
                for record in pool.map(build_one, jobs):
                    results.append(record)
                    print(f"[site] {site} {record['panorama']}: {record}", flush=True)
        built = [record for record in results if record["status"] == "built"]
        (out_root / "site_fishnet_manifest.json").write_text(
            json.dumps(
                {
                    "site": site,
                    "mesh": options.mesh_name,
                    "crop_size_px": options.size,
                    "semantics_source": "fused equirectangular panorama semantics, cut back into the crop geometry",
                    "admission": {
                        **options.admission_gate.as_dict(),
                        "rule": (
                            "a pose needs complete diagnostics, residual at or below the limit, an interior vertical "
                            "optimum, and no paired inside-geometry signature"
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
