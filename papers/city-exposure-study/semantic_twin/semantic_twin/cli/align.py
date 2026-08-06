"""Register one panorama against a site's support mesh."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.align import AlignmentConfig, run_alignment
from semantic_twin.vision.register import DEFAULT_SEEDS


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--panorama", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--bins", type=int, default=1024)
    parser.add_argument("--maxiter", type=int, default=600)
    parser.add_argument("--minimum-skyline-distance", type=float, default=8.0)
    parser.add_argument(
        "--skyline-percentile",
        type=float,
        default=90.0,
        help="Azimuthal filter percentile on the mesh skyline. 50 is the median filter that shaves roof peaks.",
    )
    parser.add_argument("--smoothing-size", type=int, default=11)
    parser.add_argument(
        "--dz-bounds",
        type=float,
        nargs=2,
        default=(-3.0, 3.0),
        help="Vertical search bound in metres around the measured camera altitude",
    )
    parser.add_argument(
        "--fit-bias",
        type=float,
        nargs=2,
        default=(0.0, 0.0),
        help=(
            "Bounds in degrees for a jointly fitted mesh-skyline elevation bias. Off by default because it is "
            "degenerate with dz: measured at Korenmarkt, three metres of altitude cost 0.05 degrees of residual "
            "once the bias is free. Useful as a diagnostic, not as a production parameter."
        ),
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--ground-from-mesh",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Replace the scene-wide camera_ground_z_m with a downward ray cast under this camera",
    )
    parser.add_argument("--ground-patch-m", type=float, default=3.0)
    parser.add_argument(
        "--camera-height-m",
        type=float,
        help=(
            "Override the scene's assumed rig height above the ground. Supply a measured value and a tight "
            "--dz-bounds to pin altitude externally, which is the only way the skyline bias becomes identifiable."
        ),
    )
    parser.add_argument(
        "--sky-conflict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also compute the sky-conflict metric, which is independent of the skyline objective",
    )
    parser.add_argument("--sky-conflict-width", type=int, default=512)
    parser.add_argument("--profile", action="store_true", help="Also profile each axis, which is slow")
    parser.add_argument("--profile-tolerance-deg", type=float, default=0.02)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    run_alignment(
        AlignmentConfig(
            mesh=args.mesh,
            semantics=args.semantics,
            semantics_json=args.semantics_json,
            pose=args.pose,
            panorama=args.panorama,
            out=args.out,
            bins=args.bins,
            maxiter=args.maxiter,
            minimum_skyline_distance=args.minimum_skyline_distance,
            skyline_percentile=args.skyline_percentile,
            smoothing_size=args.smoothing_size,
            dz_bounds=(args.dz_bounds[0], args.dz_bounds[1]),
            fit_bias=(args.fit_bias[0], args.fit_bias[1]),
            seeds=tuple(args.seeds),
            ground_from_mesh=args.ground_from_mesh,
            ground_patch_m=args.ground_patch_m,
            camera_height_m=args.camera_height_m,
            sky_conflict=args.sky_conflict,
            sky_conflict_width=args.sky_conflict_width,
            profile=args.profile,
            profile_tolerance_deg=args.profile_tolerance_deg,
        )
    )


if __name__ == "__main__":
    main()
