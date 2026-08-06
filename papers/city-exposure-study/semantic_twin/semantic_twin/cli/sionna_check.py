"""Cross validate the adjoint estimator against Sionna RT."""

from __future__ import annotations

import argparse

from semantic_twin.transport import sionna_check as sionna_domain
from semantic_twin.transport.sionna_check import (
    MODES,
    compare,
    convergence,
    plane_harness,
    sampling_convergence,
    tessellation_experiment,
)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=sionna_domain.__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    plane = sub.add_parser("plane", help="three way harness check on a dielectric half space")
    plane.add_argument("--local", action="store_true")
    plane.add_argument("--gpu", default="L4")

    site = sub.add_parser("site", help="cross validate one site")
    site.add_argument("--site", default="korenmarkt")
    site.add_argument("--crop-m", type=int, default=250)
    site.add_argument("--locations", type=int, default=8)
    site.add_argument("--sky-samples", type=int, default=900)
    site.add_argument("--rays", type=int, default=200_000)
    site.add_argument("--samples-per-src", type=int, default=200_000)
    site.add_argument("--target-chunk", type=int, default=32)
    site.add_argument("--max-paths", type=int, default=16_000_000)
    site.add_argument("--max-depth", type=int, default=4)
    site.add_argument("--modes", default=",".join(MODES))
    site.add_argument("--diffraction", action="store_true")
    site.add_argument("--local", action="store_true")
    site.add_argument("--gpu", default="L4")

    tess = sub.add_parser("tessellation", help="why the specular branches disagree, in one knob")
    tess.add_argument("--local", action="store_true")
    tess.add_argument("--gpu", default="L4")
    tess.add_argument("--cell-m", type=float, default=1.0)
    tess.add_argument("--sky-samples", type=int, default=1500)
    tess.add_argument("--jitters-mm", default="0,1,5,20,50,200")
    tess.add_argument("--tag", default="")

    budget = sub.add_parser("sampling", help="does the oracle depend on its own search budget")
    budget.add_argument("--local", action="store_true")
    budget.add_argument("--gpu", default="L4")
    budget.add_argument("--sky-samples", type=int, default=600)

    curve = sub.add_parser("convergence", help="bounce count and dynamic range curves")
    curve.add_argument("--site", default="korenmarkt")
    curve.add_argument("--crop-m", type=int, default=250)
    curve.add_argument("--locations", type=int, default=12)
    curve.add_argument("--bounce-rays", type=int, default=200_000)
    curve.add_argument("--range-rays", type=int, default=100_000)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if args.command == "plane":
        plane_harness(local=args.local, gpu=args.gpu)
    elif args.command == "tessellation":
        tessellation_experiment(
            local=args.local,
            gpu=args.gpu,
            cell_m=args.cell_m,
            sky_samples=args.sky_samples,
            jitters_m=tuple(float(value) * 1e-3 for value in args.jitters_mm.split(",")),
            tag=args.tag,
        )
    elif args.command == "sampling":
        sampling_convergence(local=args.local, gpu=args.gpu, sky_samples=args.sky_samples)
    elif args.command == "site":
        compare(
            args.site,
            modes=tuple(args.modes.split(",")),
            crop_m=args.crop_m,
            locations=args.locations,
            sky_samples=args.sky_samples,
            rays=args.rays,
            samples_per_src=args.samples_per_src,
            target_chunk=args.target_chunk,
            max_num_paths_per_src=args.max_paths,
            max_depth=args.max_depth,
            diffraction=args.diffraction,
            local=args.local,
            gpu=args.gpu,
        )
    else:
        convergence(
            args.site,
            crop_m=args.crop_m,
            locations=args.locations,
            bounce_rays=args.bounce_rays,
            range_rays=args.range_rays,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
