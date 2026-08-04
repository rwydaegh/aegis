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

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

#: Written beside the pose it replaces, so a re-registration is always reversible
#: and the crop that produced each pose stays legible on disk.
BACKUP_SUFFIX = "pose_aligned_before_{crop}m.json"


def stations(site: str) -> list[pathlib.Path]:
    """Panorama directories of a site that carry the inputs registration needs."""
    root = SCRIPT_DIR / "data" / "panoramas" / site
    if not root.is_dir():
        raise SystemExit(f"no panorama directory for {site}")
    found = sorted(f for f in root.glob("pano_*") if f.is_dir())
    if not found and (root / "pose_initial.json").exists():
        found = [root]
    ready = []
    for folder in found:
        if not (folder / "pose_initial.json").exists():
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
    path = folder / "alignment" / "pose_aligned.json"
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
) -> list[str]:
    image = panorama_image(folder)
    command = [
        sys.executable,
        "-m",
        "semantic_twin.vision.align",
        "--mesh",
        str(mesh),
        "--semantics",
        str(folder / "semantics" / "panorama_semantics.npz"),
        "--semantics-json",
        str(folder / "semantics" / "semantics.json"),
        "--pose",
        str(folder / "pose_initial.json"),
        "--out",
        str(folder / "alignment"),
    ]
    if image is not None:
        command += ["--panorama", str(image)]
    if dz_bounds is not None:
        command += ["--dz-bounds", str(dz_bounds[0]), str(dz_bounds[1])]
    if dry_run:
        return command
    result = subprocess.run(command, cwd=SCRIPT_DIR, capture_output=True, text=True)
    log = folder / "alignment" / "align.log"
    if result.returncode != 0:
        raise SystemExit(f"{folder.name}: registration failed\n{result.stdout}\n{result.stderr}")
    log.write_text(result.stdout)
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", required=True)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--station", action="append", help="Limit to named station directories")
    parser.add_argument(
        "--dz-bounds",
        type=float,
        nargs=2,
        help=(
            "Vertical search bound in metres around the measured camera altitude, passed through to "
            "vision.align. The default there is -3 3, which permits a camera half a metre under its own "
            "pavement. Every one of the 25 poses the sky conflict test calls inside the geometry has dived "
            "more than 1.5 m and the median is 2.97 m, against a median of 0.58 m among the 41 admitted "
            "poses, so -1.5 3 keeps the rig at least a metre above the ground it is standing on and "
            "excludes no pose that was ever any good."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the commands and change nothing")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Overwrite the existing pose without keeping a copy. Off by default and rarely what you want.",
    )
    args = parser.parse_args()

    mesh = SCRIPT_DIR / "data" / "geometry" / args.site / f"inhouse_leaf_{args.crop_m}m.ply"
    if not mesh.exists():
        raise SystemExit(f"no {args.crop_m} m mesh for {args.site} at {mesh}")

    dz_bounds = tuple(args.dz_bounds) if args.dz_bounds else None
    folders = stations(args.site)
    if args.station:
        wanted = set(args.station)
        folders = [f for f in folders if f.name in wanted]
    if not folders:
        raise SystemExit(f"no station of {args.site} carries a pose and segmented semantics")

    print(f"{args.site}: {len(folders)} stations against {mesh.name}")
    changed = []
    for folder in folders:
        before = read_pose(folder)
        if before and not args.no_backup and not args.dry_run:
            backup = folder / "alignment" / BACKUP_SUFFIX.format(crop=before.get("crop_m", "unknown"))
            if not backup.exists():
                shutil.copy2(folder / "alignment" / "pose_aligned.json", backup)
        command = register(folder, mesh, dry_run=args.dry_run, dz_bounds=dz_bounds)
        if args.dry_run:
            print(" ".join(command))
            continue
        after = read_pose(folder)
        after["crop_m"] = args.crop_m
        after["support_mesh"] = str(mesh.relative_to(SCRIPT_DIR))
        if dz_bounds is not None:
            after["dz_bounds_rationale"] = (
                "clamped so the optical centre cannot sit below the pavement under it, which is what "
                "the unclamped search does whenever the modelled skyline is too low"
            )
        (folder / "alignment" / "pose_aligned.json").write_text(json.dumps(after, indent=2))
        print(f"  {folder.name[:24]:25s} before: {summarise(before)}")
        print(f"  {'':25s} after:  {summarise(after)}")
        changed.append(folder.name)
    if not args.dry_run:
        print(f"{args.site}: re-registered {len(changed)} stations at {args.crop_m} m")


if __name__ == "__main__":
    main()
