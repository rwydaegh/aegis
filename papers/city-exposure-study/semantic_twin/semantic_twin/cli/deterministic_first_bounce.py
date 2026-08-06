"""Converge a deterministic one-bounce reference on the open square."""

from __future__ import annotations

import argparse
import json

from semantic_twin import paths
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.deterministic_reference import first_bounce_reference
from semantic_twin.transport.sionna_check import SPEED_OF_LIGHT_M_S, write_ply
from semantic_twin.transport.sionna_forward import FULLY_DIFFUSE_RMS_HEIGHT_M, open_square_environment


def _resolutions(value: str) -> tuple[int, ...]:
    result = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not result or any(item < 1 for item in result):
        raise argparse.ArgumentTypeError("resolutions must be positive comma-separated integers")
    return result


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolutions", type=_resolutions, default=_resolutions("16,32,64,128"))
    parser.add_argument("--sources", type=int, default=27)
    parser.add_argument("--receivers", type=int, default=6)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--validation-rms-height-m", type=float, default=FULLY_DIFFUSE_RMS_HEIGHT_M)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--tag", default="deterministic_first_bounce_open_square")
    return parser.parse_args(argv)


def run(args: argparse.Namespace):
    root = paths.root()
    environment = open_square_environment(source_count=int(args.sources))
    receivers = environment.receivers[: int(args.receivers)]
    cache_dir = root / "outputs" / "cross_validation" / "deterministic_first_bounce"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mesh = cache_dir / "open_square.ply"
    mesh.write_bytes(write_ply(environment.vertices, environment.faces))
    geometry = MitsubaGeometry(mesh, variant=args.variant)

    rows = []
    for resolution in args.resolutions:
        print(f"{resolution} subdivisions", flush=True)
        answer = first_bounce_reference(
            geometry,
            environment.vertices,
            environment.faces,
            environment.sources,
            receivers,
            permittivity=PEC_PERMITTIVITY,
            rms_height_m=float(args.validation_rms_height_m),
            wavelength_m=SPEED_OF_LIGHT_M_S / float(args.frequency_hz),
            subdivisions=resolution,
        )
        rows.append(
            {
                "subdivisions": answer.subdivisions,
                "surface_samples": answer.surface_samples,
                "seconds": answer.seconds,
                "direct": answer.direct.tolist(),
                "bounced": answer.bounced.tolist(),
                "total": answer.total.tolist(),
            }
        )

    payload = {
        "question": "what is the deterministic first-bounce transfer in the controlled open square",
        "method": "equal-area subtriangle centroid quadrature with exact visibility rays",
        "sources": int(environment.sources.shape[0]),
        "receivers": int(receivers.shape[0]),
        "frequency_hz": float(args.frequency_hz),
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
