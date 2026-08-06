"""Measure forward and adjoint scaling with the facade-tip source count."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import platform
import time

import numpy as np

from semantic_twin import paths
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.sionna_check import write_ply
from semantic_twin.transport.sionna_forward import (
    TransferSamples,
    adjoint_transfer,
    comparison,
    forward_transfer_subprocess,
    open_square_environment,
)


def _positive_counts(value: str) -> tuple[int, ...]:
    counts = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not counts or any(count < 1 for count in counts):
        raise argparse.ArgumentTypeError("source counts must be positive comma-separated integers")
    if len(set(counts)) != len(counts):
        raise argparse.ArgumentTypeError("source counts must be unique")
    return counts


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-counts", type=_positive_counts, default=_positive_counts("3,9,27,81,243,729"))
    parser.add_argument("--receivers", type=int, default=6)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--adjoint-rays", type=int, default=50_000)
    parser.add_argument("--adjoint-seeds", type=int, default=8)
    parser.add_argument("--validation-rms-height-m", type=float, default=1.0)
    parser.add_argument("--connection-lift-m", type=float, default=1.0e-2)
    parser.add_argument("--sionna-seeds", type=int, default=6)
    parser.add_argument("--fixed-per-source", type=int, default=20_000)
    parser.add_argument("--fixed-total", type=int, default=1_350_000)
    parser.add_argument("--minimum-per-source", type=int, default=256)
    parser.add_argument("--per-source-sweep", type=_positive_counts)
    parser.add_argument("--source-chunk", type=int, default=16)
    parser.add_argument(
        "--sionna-variant",
        choices=("cuda_ad_mono_polarized", "llvm_ad_mono_polarized"),
    )
    parser.add_argument("--max-paths-per-src", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--tag", default="sionna_source_scaling")
    return parser.parse_args(argv)


def sample_metrics(samples: TransferSamples) -> dict[str, object]:
    direct = np.asarray(samples.direct, dtype=np.float64)
    total = np.asarray(samples.total, dtype=np.float64)
    surplus_db = 10.0 * np.log10(total / direct)
    if surplus_db.shape[0] > 1:
        standard_deviation = np.std(surplus_db, axis=0, ddof=1)
        standard_error = standard_deviation / math.sqrt(surplus_db.shape[0])
    else:
        standard_deviation = np.full(surplus_db.shape[1], np.nan)
        standard_error = np.full(surplus_db.shape[1], np.nan)
    seconds = np.asarray(samples.seconds, dtype=np.float64)
    warmed = seconds[1:] if seconds.size > 1 else seconds
    median_variance = float(np.nanmedian(standard_deviation**2))
    warmed_mean = float(np.mean(warmed))
    return {
        "surplus_db_mean": np.mean(surplus_db, axis=0).tolist(),
        "surplus_db_standard_deviation": standard_deviation.tolist(),
        "surplus_db_standard_error": standard_error.tolist(),
        "median_single_seed_sd_db": float(np.nanmedian(standard_deviation)),
        "median_standard_error_db": float(np.nanmedian(standard_error)),
        "seconds": seconds.tolist(),
        "seconds_mean": float(np.mean(seconds)),
        "seconds_warmed_mean": warmed_mean,
        "median_variance_times_warmed_seconds": median_variance * warmed_mean,
    }


def run(args: argparse.Namespace) -> pathlib.Path:
    root = paths.root()
    receiver_count = int(args.receivers)
    if not 1 <= receiver_count <= 6:
        raise ValueError("the controlled environment has between one and six receivers")

    environment = open_square_environment(source_count=max(args.source_counts))
    cache_dir = root / "outputs" / "cross_validation" / "sionna_forward_scene" / "open_square_scaling"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mesh = cache_dir / "open_square_scaling.ply"
    mesh.write_bytes(write_ply(environment.vertices, environment.faces))
    geometry = MitsubaGeometry(mesh, variant=args.variant)
    receivers = environment.receivers[:receiver_count]

    # Compile and populate Mitsuba's caches before the measured sweep. The
    # source count changes only array sizes, while the scene stays fixed.
    warmup_case = open_square_environment(source_count=args.source_counts[0])
    print("adjoint warm-up", flush=True)
    adjoint_transfer(
        geometry,
        warmup_case.sources,
        receivers,
        max_depth=int(args.max_depth),
        rays=int(args.adjoint_rays),
        seeds=(int(args.seed) - 1,),
        rms_height_m=float(args.validation_rms_height_m),
        connection_lift_m=float(args.connection_lift_m),
    )

    rows = []
    started = time.time()
    for source_count in args.source_counts:
        case = open_square_environment(source_count=source_count)
        sources = case.sources
        print(f"{source_count} sources: adjoint", flush=True)
        adjoint = adjoint_transfer(
            geometry,
            sources,
            receivers,
            max_depth=int(args.max_depth),
            rays=int(args.adjoint_rays),
            seeds=tuple(args.seed + index for index in range(int(args.adjoint_seeds))),
            rms_height_m=float(args.validation_rms_height_m),
            connection_lift_m=float(args.connection_lift_m),
        )
        row: dict[str, object] = {
            "sources": int(source_count),
            "receivers": int(receiver_count),
            "adjoint": {**adjoint.summary(), "metrics": sample_metrics(adjoint)},
            "sionna": {},
        }

        if args.per_source_sweep is None:
            protocols = {
                "fixed_per_source": int(args.fixed_per_source),
                "fixed_total": max(int(args.minimum_per_source), int(args.fixed_total) // source_count),
            }
        else:
            protocols = {f"per_source_{samples}": int(samples) for samples in args.per_source_sweep}
        for protocol, samples_per_src in protocols.items():
            print(
                f"{source_count} sources: Sionna {protocol}, {samples_per_src} samples/source",
                flush=True,
            )
            sionna, runs = forward_transfer_subprocess(
                environment.vertices,
                environment.faces,
                sources,
                receivers,
                frequency_hz=15.0e9,
                cache_dir=cache_dir / str(source_count) / protocol,
                max_depth=int(args.max_depth),
                samples_per_src=samples_per_src,
                max_num_paths_per_src=int(args.max_paths_per_src),
                source_chunk=int(args.source_chunk),
                sionna_variant=args.sionna_variant,
                seeds=tuple(
                    args.seed + 10_000 + source_count + index * 1000 for index in range(int(args.sionna_seeds))
                ),
            )
            if any(run["path_buffer_saturated"] for run in runs):
                raise RuntimeError(f"Sionna path buffer saturated for {source_count} sources under {protocol}")
            row["sionna"][protocol] = {
                **sionna.summary(),
                "metrics": sample_metrics(sionna),
                "samples_per_source": samples_per_src,
                "nominal_total_samples": samples_per_src * source_count,
                "runs": runs,
                "comparison": comparison(adjoint, sionna),
            }
        rows.append(row)

    payload = {
        "question": "how runtime and error scale with the number of facade-tip sources",
        "environment": "controlled open square with balanced sources on three walls",
        "host": platform.node(),
        "elapsed_seconds": time.time() - started,
        "settings": {
            "source_counts": list(args.source_counts),
            "receivers": receiver_count,
            "max_depth": int(args.max_depth),
            "adjoint_rays": int(args.adjoint_rays),
            "adjoint_seeds": int(args.adjoint_seeds),
            "validation_rms_height_m": float(args.validation_rms_height_m),
            "connection_lift_m": float(args.connection_lift_m),
            "sionna_seeds": int(args.sionna_seeds),
            "fixed_per_source": int(args.fixed_per_source),
            "fixed_total": int(args.fixed_total),
            "minimum_per_source": int(args.minimum_per_source),
            "per_source_sweep": None if args.per_source_sweep is None else list(args.per_source_sweep),
            "source_chunk": int(args.source_chunk),
            "sionna_variant": args.sionna_variant or "automatic",
            "max_paths_per_src": int(args.max_paths_per_src),
            "seed": int(args.seed),
            "timing": (
                "the adjoint scene receives one unmeasured warm-up. The warmed mean also "
                "drops the first seed for each solver and case"
            ),
        },
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
