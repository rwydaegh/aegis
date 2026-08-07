"""Re-run skyline registration for a site against a named support mesh.

Every registration in this repository was fitted against `inhouse_leaf_130m.ply`,
which is confirmed rather than assumed: the candidate vertex count stored in each
`pose_aligned.json` reproduces the 130 m prune exactly at all six registered
sites, and reproduces no other crop.

That is the right crop for a low rise square and the wrong one for a high rise
canyon, because the geometry that forms the skyline in a canyon stands beyond
130 m. Truncating it lowers the modelled skyline, and the optimiser has one cheap
way to raise a skyline that is too low, which is to lower the camera. It does,
until it hits the vertical search bound, and the camera ends up under the
pavement. Every sky direction then returns a mesh first hit at sub metre range,
the sky conflict test reads 1.0, and the station is refused.

At Hachiko the chain is measured end to end. Taking `pano_00`, on the 130 m mesh
the robust residual at the untouched initial pose is 9.42 degrees and the fit
lands at 6.53 with the camera 2.96 m down against a 3.0 m bound. On the 250 m
mesh that same untouched pose already scores 2.59 degrees, so the fit had been
paying three metres of altitude to buy back geometry the crop had removed. Over
the site's three stations the median residual at the initial pose falls from 9.42
degrees to 4.42.

Times Square is a different diagnosis and this script does not rescue it. There
the 250 m crop scores 11.25 degrees at the initial pose against 11.91 at 130 m,
and a yaw scan over the whole circle moves the objective by under two degrees, so
the skyline carries almost no orientation information at all. See COVERAGE.md.

Run from the `semantic_twin` directory::

    python reregister_site.py --site tokyo_hachiko --crop-m 250
    python reregister_site.py --site tokyo_hachiko --crop-m 250 --dry-run
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from semantic_twin import paths

#: Written beside the pose it replaces, so a re-registration is always reversible
#: and the crop that produced each pose stays legible on disk.
BACKUP_SUFFIX = "pose_aligned_before_{crop}m.json"
INITIAL_POSE_NAME = "pose_initial.json"
ALIGNED_POSE_NAME = "pose_aligned.json"


@dataclass(frozen=True)
class RepairOptions:
    """Controls for a reversible site registration repair."""

    site: str
    crop_m: int = 250
    station_names: tuple[str, ...] | None = None
    cohort_dir: pathlib.Path | None = None
    dz_bounds: tuple[float, float] | None = None
    dry_run: bool = False
    no_backup: bool = False
    root_dir: pathlib.Path | None = None


def stations(
    site: str,
    *,
    root_dir: pathlib.Path | None = None,
    cohort_dir: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """Panorama directories carrying the inputs registration needs.

    By default, station discovery is scoped to the site's canonical panorama
    set.  ``cohort_dir`` is an explicit escape hatch for a deliberately
    selected capture cohort, such as a dated Google Street View pull.  It is
    resolved relative to ``root_dir`` (the study root) when given as a relative
    path, so a registration run cannot silently mix an old set with a newly
    acquired one merely because both happen to be under ``data/panoramas``.
    """
    study_root = paths.root() if root_dir is None else root_dir
    if cohort_dir is None:
        root = paths.panorama_set(site) if root_dir is None else study_root / "data" / "panoramas" / site
    else:
        root = pathlib.Path(cohort_dir).expanduser()
        if not root.is_absolute():
            root = study_root / root
        root = root.resolve()
    if not root.is_dir():
        if cohort_dir is None:
            raise SystemExit(f"no panorama directory for {site}")
        raise SystemExit(f"no cohort directory at {root}")
    found = sorted(f for f in root.glob("pano_*") if f.is_dir())
    if not found and (root / INITIAL_POSE_NAME).exists():
        found = [root]
    ready = []
    for folder in found:
        if not (folder / INITIAL_POSE_NAME).exists():
            continue
        if not (folder / "semantics" / "panorama_semantics.npz").exists():
            continue
        ready.append(folder)
    return ready


def panorama_image(folder: pathlib.Path) -> pathlib.Path | None:
    """The stitched panorama, whatever zoom it was acquired at."""
    found = sorted(folder.glob("panorama_z*.jpg")) or sorted(folder.glob("panorama*.jpg"))
    return found[0] if found else None


def read_pose(folder: pathlib.Path) -> dict[str, Any]:
    path = folder / "alignment" / ALIGNED_POSE_NAME
    return json.loads(path.read_text()) if path.exists() else {}


def summarise(pose: dict[str, Any]) -> str:
    if not pose:
        return "not registered"
    conflict = pose.get("sky_conflict") or {}
    hit = conflict.get("sky_with_mesh_hit_fraction")
    near = conflict.get("conflict_median_range_m")
    sky = "sky conflict unknown" if hit is None else f"sky {float(hit):.2f} at {float(near or 0.0):.1f} m"
    return (
        f"residual {float(pose.get('skyline_score_mean_deg', 99.0)):5.2f} deg, "
        f"z {float(pose['position_enu_m'][2]):8.2f} m, "
        f"dz at bound {bool(pose.get('skyline_dz_at_bound'))}, {sky}"
    )


def register(
    folder: pathlib.Path,
    mesh: pathlib.Path,
    *,
    dry_run: bool,
    dz_bounds: tuple[float, float] | None = None,
    root_dir: pathlib.Path | None = None,
) -> list[str]:
    image = panorama_image(folder)
    command = [
        sys.executable,
        "-m",
        "semantic_twin.cli.align",
        "--mesh",
        str(mesh),
        "--semantics",
        str(folder / "semantics" / "panorama_semantics.npz"),
        "--semantics-json",
        str(folder / "semantics" / "semantics.json"),
        "--pose",
        str(folder / INITIAL_POSE_NAME),
        "--out",
        str(folder / "alignment"),
    ]
    if image is not None:
        command += ["--panorama", str(image)]
    if dz_bounds is not None:
        command += ["--dz-bounds", str(dz_bounds[0]), str(dz_bounds[1])]
    if dry_run:
        return command
    result = subprocess.run(command, cwd=root_dir or paths.root(), capture_output=True, text=True)
    log = folder / "alignment" / "align.log"
    if result.returncode != 0:
        raise SystemExit(f"{folder.name}: registration failed\n{result.stdout}\n{result.stderr}")
    log.write_text(result.stdout)
    return command


def reregister_site(options: RepairOptions) -> list[str]:
    """Repair all selected registrations for one site and return changed stations."""
    study_root = options.root_dir or paths.root()
    try:
        mesh = paths.site_mesh(options.site, options.crop_m, root_dir=study_root)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    folders = stations(options.site, root_dir=study_root, cohort_dir=options.cohort_dir)
    if options.station_names:
        wanted = set(options.station_names)
        folders = [f for f in folders if f.name in wanted]
    if not folders:
        raise SystemExit(f"no station of {options.site} carries a pose and segmented semantics")

    print(f"{options.site}: {len(folders)} stations against {mesh.name}")
    changed = []
    for folder in folders:
        before = read_pose(folder)
        _back_up_pose(folder, before, enabled=not options.no_backup and not options.dry_run)
        command = register(
            folder,
            mesh,
            dry_run=options.dry_run,
            dz_bounds=options.dz_bounds,
            root_dir=study_root,
        )
        if options.dry_run:
            print(" ".join(command))
            continue
        after = read_pose(folder)
        after["crop_m"] = options.crop_m
        after["support_mesh"] = str(mesh.relative_to(study_root))
        if options.dz_bounds is not None:
            after["dz_bounds_rationale"] = (
                "clamped so the optical centre cannot sit below the pavement under it, which is what "
                "the unclamped search does whenever the modelled skyline is too low"
            )
        (folder / "alignment" / ALIGNED_POSE_NAME).write_text(json.dumps(after, indent=2))
        print(f"  {folder.name[:24]:25s} before: {summarise(before)}")
        print(f"  {'':25s} after:  {summarise(after)}")
        changed.append(folder.name)
    if not options.dry_run:
        print(f"{options.site}: re-registered {len(changed)} stations at {options.crop_m} m")
    return changed


def _back_up_pose(folder: pathlib.Path, pose: dict[str, Any], *, enabled: bool) -> None:
    if not pose or not enabled:
        return
    backup = folder / "alignment" / BACKUP_SUFFIX.format(crop=pose.get("crop_m", "unknown"))
    if not backup.exists():
        shutil.copy2(folder / "alignment" / ALIGNED_POSE_NAME, backup)
