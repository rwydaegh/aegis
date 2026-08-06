"""Measure the ray budget needed by the adjoint open-square estimator."""

from __future__ import annotations

import argparse
import json

from semantic_twin import paths
from semantic_twin.cli.sionna_scaling import _positive_counts, sample_metrics
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.sionna_check import write_ply
from semantic_twin.transport.sionna_forward import adjoint_transfer, open_square_environment


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=int, default=2187)
    parser.add_argument("--receivers", type=int, default=6)
    parser.add_argument(
        "--ray-budgets", type=_positive_counts, default=_positive_counts("5000,10000,20000,50000,100000")
    )
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--connections", type=int, default=1)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--connection-lift-m", type=float, default=1.0e-2)
    parser.add_argument("--validation-rms-height-m", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--tag", default="adjoint_ray_budget")
    return parser.parse_args(argv)


def run(args: argparse.Namespace):
    root = paths.root()
    environment = open_square_environment(source_count=int(args.sources))
    receivers = environment.receivers[: int(args.receivers)]
    cache_dir = root / "outputs" / "cross_validation" / "sionna_forward_scene" / "open_square_scaling"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mesh = cache_dir / "open_square_scaling.ply"
    mesh.write_bytes(write_ply(environment.vertices, environment.faces))
    geometry = MitsubaGeometry(mesh, variant=args.variant)

    rows = []
    for rays in args.ray_budgets:
        print(f"{rays} adjoint rays", flush=True)
        samples = adjoint_transfer(
            geometry,
            environment.sources,
            receivers,
            max_depth=int(args.max_depth),
            rays=int(rays),
            connections=int(args.connections),
            seeds=tuple(args.seed + index for index in range(int(args.seeds))),
            rms_height_m=float(args.validation_rms_height_m),
            connection_lift_m=float(args.connection_lift_m),
        )
        rows.append(
            {
                "rays": int(rays),
                **samples.summary(),
                "metrics": sample_metrics(samples),
            }
        )

    payload = {
        "question": "how many adjoint rays are needed at a production-like source-to-receiver ratio",
        "sources": int(environment.sources.shape[0]),
        "receivers": int(receivers.shape[0]),
        "max_depth": int(args.max_depth),
        "seeds": int(args.seeds),
        "connections": int(args.connections),
        "connection_lift_m": float(args.connection_lift_m),
        "validation_rms_height_m": float(args.validation_rms_height_m),
        "rows": rows,
    }
    output = root / "outputs" / "cross_validation" / f"{args.tag}.json"
    output.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {output.relative_to(root)}", flush=True)
    return output


def main(argv: list[str] | None = None) -> int:
    run(arguments(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
