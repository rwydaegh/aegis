"""Build one twin from a walk of linked panoramas and measure its evidence."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.walk_evidence import WalkEvidenceConfig, coverage_curve, run_stage, saturation_curves

REPO = pathlib.Path(__file__).resolve().parent
__all__ = ["coverage_curve", "saturation_curves"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("select", "download", "fuse", "saturate", "semantic"))
    parser.add_argument("--permutations", type=int, default=40)
    parser.add_argument("--recast", action="store_true")
    parser.add_argument("--clean-majority", type=float, default=0.5)
    parser.add_argument("--min-overlap-faces", type=int, default=200)
    parser.add_argument("--max-residual-deg", type=float, default=4.0)
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--decorrelation-deg", type=float, default=10.0)
    parser.add_argument("--independence-sample", type=int, default=40000)
    parser.add_argument("--scene", default=str(REPO / "config/korenmarkt.json"))
    parser.add_argument("--mesh", default="data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply")
    parser.add_argument("--out", default=str(REPO / "outputs/walk_korenmarkt"))
    parser.add_argument("--panorama-root", default=str(REPO / "data/panoramas/korenmarkt_walk"))
    parser.add_argument("--radius-m", type=float, default=60.0)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--separation-m", type=float, default=8.0)
    parser.add_argument("--per-sequence-cap", type=int, default=6)
    parser.add_argument("--seed-half-width-m", type=float, default=150.0)
    parser.add_argument("--seed-cells", type=int, default=6)
    return parser


def main() -> None:
    run_stage(WalkEvidenceConfig(**vars(_parser().parse_args())))


if __name__ == "__main__":
    main()
