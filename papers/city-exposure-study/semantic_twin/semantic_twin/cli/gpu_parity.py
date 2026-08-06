"""Compare the current Mitsuba SBR path across CPU and CUDA variants."""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import fields

from semantic_twin.transport.gpu_parity import ParityConfig, run_harness, run_variant


def _worker(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="internal variant worker")
    parser.add_argument("--config", required=True, type=pathlib.Path)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--rays", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--result", required=True, type=pathlib.Path)
    parser.add_argument("--origins-sha256", required=True)
    parser.add_argument("--directions-sha256", required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.config.read_text())
    tuple_fields = {"variants", "origin"}
    for name in tuple_fields:
        payload[name] = tuple(payload[name])
    allowed = {field.name for field in fields(ParityConfig)}
    config = ParityConfig(**{name: value for name, value in payload.items() if name in allowed})
    result = run_variant(
        config,
        args.variant,
        args.rays,
        args.artifact,
        {"origins": args.origins_sha256, "directions": args.directions_sha256},
    )
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--variants", nargs="+", default=["llvm_ad_rgb", "cuda_ad_rgb"])
    parser.add_argument("--face-class", help="optional one-dimensional NumPy array indexed by mesh face")
    parser.add_argument("--origin", nargs=3, type=float, metavar=("X", "Y", "Z"), default=(0.0, 0.0, 52.34))
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20_260_804)
    parser.add_argument("--epsilon", type=float, default=1.0e-5, help="absolute and dB comparison tolerance")
    parser.add_argument("--max-hit-mismatch-fraction", type=float, default=0.0)
    parser.add_argument("--max-material-mismatch-fraction", type=float, default=5.0e-4)
    parser.add_argument("--max-distance-error-m", type=float, default=5.0e-5)
    parser.add_argument("--max-scientific-error-db", type=float, default=1.0e-4)
    parser.add_argument("--max-device-error", type=float, default=1.0e-3)
    parser.add_argument(
        "--skip-device-sbr",
        action="store_true",
        help="run geometry and legacy-hybrid parity without requiring the device-resident prototype",
    )
    parser.add_argument("--ray-epsilon-m", type=float, default=1.0e-3)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--local-cells", type=int, default=256)
    parser.add_argument("--exit-bands", type=int, default=18)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--permittivity-real", type=float, default=5.31)
    parser.add_argument("--permittivity-imag", type=float, default=-0.4)
    parser.add_argument("--rms-height-m", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else None
    if arguments and arguments[0] == "_worker":
        return _worker(arguments[1:])
    if arguments is None:
        import sys

        if len(sys.argv) > 1 and sys.argv[1] == "_worker":
            return _worker(sys.argv[2:])
    args = _parser().parse_args(arguments)
    config = ParityConfig(
        mesh=args.mesh,
        output=args.output,
        variants=tuple(args.variants),
        face_class=args.face_class,
        origin=tuple(args.origin),
        rays=args.rays,
        repeats=args.repeats,
        seed=args.seed,
        epsilon=args.epsilon,
        max_hit_mismatch_fraction=args.max_hit_mismatch_fraction,
        max_material_mismatch_fraction=args.max_material_mismatch_fraction,
        max_distance_error_m=args.max_distance_error_m,
        max_scientific_error_db=args.max_scientific_error_db,
        max_device_error=args.max_device_error,
        require_device_sbr=not args.skip_device_sbr,
        ray_epsilon_m=args.ray_epsilon_m,
        frequency_hz=args.frequency_hz,
        local_cells=args.local_cells,
        exit_bands=args.exit_bands,
        max_bounces=args.max_bounces,
        permittivity_real=args.permittivity_real,
        permittivity_imag=args.permittivity_imag,
        rms_height_m=args.rms_height_m,
    )
    report = run_harness(config)
    print(report)
    payload = json.loads(report.read_text())
    return 0 if payload["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
