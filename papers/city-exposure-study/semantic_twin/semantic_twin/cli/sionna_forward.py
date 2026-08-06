"""Compare the facade-tip next-event estimator with ordinary forward Sionna RT."""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from semantic_twin import paths
from semantic_twin.illumination import build_source_set, silhouette
from semantic_twin.paths import site_mesh
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.sionna_forward import (
    adjoint_transfer,
    comparison,
    forward_transfer_subprocess,
    open_square_environment,
)
from semantic_twin.transport.sionna_check import write_ply
from semantic_twin.walk import build_walk, measure_ground_datum, site_walk


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("open-square", "city"), default="open-square")
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--receivers", type=int)
    parser.add_argument("--sources", type=int)
    parser.add_argument("--builders", type=int, default=128)
    parser.add_argument("--azimuths", type=int, default=1440)
    parser.add_argument("--elevations", type=int, default=600)
    parser.add_argument("--cell-m", type=float, default=1.0)
    parser.add_argument("--site-lift-m", type=float, default=0.5)
    parser.add_argument("--walk-path", choices=("links", "street", "closest"), default="links")
    parser.add_argument("--walk-stride-m", type=float, default=6.0)
    parser.add_argument("--walk", choices=("route", "grid"), default="route")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--head-height-m", type=float, default=1.5)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--adjoint-rays", type=int, default=200_000)
    parser.add_argument("--adjoint-connections", type=int, default=1)
    parser.add_argument("--adjoint-seeds", type=int, default=8)
    parser.add_argument("--validation-rms-height-m", type=float, default=1.0)
    parser.add_argument("--connection-lift-m", type=float, default=1.0e-2)
    parser.add_argument("--sionna-samples-per-src", type=int, default=200_000)
    parser.add_argument("--sionna-seeds", type=int, default=4)
    parser.add_argument("--source-chunk", type=int, default=8)
    parser.add_argument(
        "--sionna-variant",
        choices=("cuda_ad_mono_polarized", "llvm_ad_mono_polarized"),
    )
    parser.add_argument("--max-paths-per-src", type=int, default=4_000_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--tag", default="forward_sionna")
    return parser.parse_args(argv)


def _points_and_sources(
    args: argparse.Namespace,
    geometry: MitsubaGeometry,
    root: pathlib.Path,
    ground_datum_m: float,
) -> tuple[np.ndarray, np.ndarray, dict]:
    if args.walk == "route":
        walk, walk_provenance = site_walk(
            geometry,
            args.site,
            stride_m=args.walk_stride_m,
            head_height_m=args.head_height_m,
            path=args.walk_path,
            root=root,
        )
    else:
        walk = build_walk(
            geometry,
            ground_datum_m=ground_datum_m,
            radius_m=float(args.walk_radius_m),
            head_height_m=args.head_height_m,
            seed=args.seed,
        )
        walk_provenance = {"kind": walk.kind, **walk.provenance}
    points = np.asarray(walk.points, dtype=np.float64)
    if points.shape[0] < 3:
        raise RuntimeError(f"{args.site} has only {points.shape[0]} usable walk points")

    receiver_count = min(int(args.receivers or 4), max(1, points.shape[0] // 3))
    rng = np.random.default_rng(args.seed)
    order = rng.permutation(points.shape[0])
    receivers = points[order[:receiver_count]]
    pool = points[order[receiver_count:]]
    builder_count = min(int(args.builders), pool.shape[0])
    builder_index = np.linspace(0, pool.shape[0] - 1, builder_count).round().astype(int)
    builders = pool[builder_index]

    source_set = build_source_set(
        geometry,
        builders,
        silhouette,
        azimuths=int(args.azimuths),
        elevations=int(args.elevations),
        cell_m=float(args.cell_m),
        dims=3,
        site_lift_m=float(args.site_lift_m),
    )
    source_count = int(args.sources or 32)
    if len(source_set) < source_count:
        raise RuntimeError(f"asked for {source_count} sources, but the facade-tip set has {len(source_set)}")
    chosen = np.random.default_rng(args.seed + 2000).choice(len(source_set), size=source_count, replace=False)
    sources = source_set.positions[chosen]
    provenance = {
        "walk": walk_provenance,
        "receivers_available": int(points.shape[0]),
        "receivers_used": int(receivers.shape[0]),
        "builders_used": int(builders.shape[0]),
        "full_source_set": source_set.describe(),
        "source_subset": "uniform without replacement from the fixed facade-tip set",
        "sources_used": int(sources.shape[0]),
    }
    return receivers, sources, provenance


def run(args: argparse.Namespace) -> pathlib.Path:
    root = paths.root()
    if args.environment == "open-square":
        environment = open_square_environment(source_count=int(args.sources or 27))
        scene_dir = root / "outputs" / "cross_validation" / "sionna_forward_scene" / environment.name
        scene_dir.mkdir(parents=True, exist_ok=True)
        mesh = scene_dir / f"{environment.name}.ply"
        mesh.write_bytes(write_ply(environment.vertices, environment.faces))
        geometry = MitsubaGeometry(mesh, variant=args.variant)
        receiver_count = min(args.receivers or environment.receivers.shape[0], environment.receivers.shape[0])
        sources = environment.sources
        receivers = environment.receivers[:receiver_count]
        provenance = {
            "construction": "exact ground plane and three rectangular walls",
            "triangles": int(environment.faces.shape[0]),
            "sources_used": int(sources.shape[0]),
            "receivers_used": int(receivers.shape[0]),
        }
        case_name = environment.name
        ground_datum_m = 0.0
    else:
        mesh = site_mesh(args.site, args.crop_m, root_dir=root)
        geometry = MitsubaGeometry(mesh, variant=args.variant)
        datum = measure_ground_datum(geometry)
        receivers, sources, provenance = _points_and_sources(args, geometry, root, float(datum.z_m))
        case_name = args.site
        ground_datum_m = float(datum.z_m)

    print(f"{case_name}: {sources.shape[0]} facade-tip transmitters, {receivers.shape[0]} pedestrian receivers")
    print("running the adjoint next-event estimator")
    adjoint = adjoint_transfer(
        geometry,
        sources,
        receivers,
        frequency_hz=args.frequency_hz,
        max_depth=args.max_depth,
        rays=args.adjoint_rays,
        connections=args.adjoint_connections,
        seeds=tuple(args.seed + index for index in range(args.adjoint_seeds)),
        rms_height_m=args.validation_rms_height_m,
        connection_lift_m=args.connection_lift_m,
    )

    print("running ordinary forward links in Sionna RT")
    cache_dir = root / "outputs" / "cross_validation" / "sionna_forward_scene" / case_name
    sionna, sionna_runs = forward_transfer_subprocess(
        geometry.vertices,
        geometry.faces,
        sources,
        receivers,
        frequency_hz=args.frequency_hz,
        cache_dir=cache_dir,
        max_depth=args.max_depth,
        samples_per_src=args.sionna_samples_per_src,
        max_num_paths_per_src=args.max_paths_per_src,
        source_chunk=args.source_chunk,
        sionna_variant=args.sionna_variant,
        seeds=tuple(args.seed + 10_000 + index * 1000 for index in range(args.sionna_seeds)),
    )
    if any(run["path_buffer_saturated"] for run in sionna_runs):
        raise RuntimeError("Sionna's path buffer saturated. Raise --max-paths-per-src before reading this comparison.")

    payload = {
        "question": "does ordinary forward ray tracing reproduce the facade-tip next-event estimator",
        "environment": args.environment,
        "case": case_name,
        "mesh": str(mesh.relative_to(root)),
        "frequency_hz": float(args.frequency_hz),
        "max_depth": int(args.max_depth),
        "material": {
            "kind": "fully diffuse near-perfect reflector on every triangle",
            "reason": "removes material class, polarisation history, roughness matching, and specular path search",
            "adjoint_rms_height_m": float(args.validation_rms_height_m),
        },
        "antenna": {
            "kind": "one isotropic cross-polarised element at both ends",
            "reduction": "sum both receive and transmit ports, then divide by two transmitted polarisations",
        },
        "paths": {
            "sum": "incoherent",
            "diffuse_reflection": True,
            "specular_reflection": False,
            "refraction": False,
            "diffraction": False,
        },
        "normalisation": "mean source link gain divided by (wavelength / 4 pi)^2, in 1/m^2",
        "ground_datum_m": ground_datum_m,
        "provenance": provenance,
        "receivers": receivers.tolist(),
        "sources": sources.tolist(),
        "settings": {
            "adjoint_rays": int(args.adjoint_rays),
            "adjoint_connections": int(args.adjoint_connections),
            "adjoint_seeds": int(args.adjoint_seeds),
            "validation_rms_height_m": float(args.validation_rms_height_m),
            "connection_lift_m": float(args.connection_lift_m),
            "sionna_samples_per_src": int(args.sionna_samples_per_src),
            "sionna_seeds": int(args.sionna_seeds),
            "source_chunk": int(args.source_chunk),
            "sionna_variant": args.sionna_variant or "automatic",
            "max_paths_per_src": int(args.max_paths_per_src),
            "seed": int(args.seed),
        },
        "adjoint": adjoint.summary(),
        "sionna": {**sionna.summary(), "runs": sionna_runs},
        "comparison": comparison(adjoint, sionna),
    }
    out_dir = root / "outputs" / "cross_validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{case_name}_{args.crop_m}m" if args.environment == "city" else case_name
    path = out_dir / f"{args.tag}_{suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(payload["comparison"], indent=1))
    print(f"wrote {path.relative_to(root)}")
    return path


def main(argv: list[str] | None = None) -> int:
    run(arguments(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
