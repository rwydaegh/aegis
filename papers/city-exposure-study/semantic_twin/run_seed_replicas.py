"""Replicate fixed exposure standpoints over independent ray seeds."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.seed_replicas import SeedReplicaConfig, execute


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", default="clean_geometric")
    parser.add_argument("--seeds", default="7,8,9,10,11,12,13,14")
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--walk-npz", default=None)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="trace only the first N standpoints, for a smoke test")
    parser.add_argument("--tag", default=None)
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--baseline", default="clean_geometric")
    parser.add_argument("--rung", default="clean_walk9")
    parser.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="analyse only the first N replicas, so the eight replica figure the audit reported "
        "and a longer run's figure can both be read off the same file",
    )
    args = parser.parse_args(argv)
    execute(
        SeedReplicaConfig(
            reference=args.reference,
            seeds=tuple(int(value) for value in args.seeds.split(",")),
            frequency_hz=args.frequency_ghz * 1e9,
            walk_npz=pathlib.Path(args.walk_npz).resolve() if args.walk_npz else None,
            variant=args.variant,
            workers=args.workers,
            limit=args.limit,
            tag=args.tag,
            analyse_only=args.analyse,
            baseline=args.baseline,
            rung=args.rung,
            replicas=args.replicas,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
