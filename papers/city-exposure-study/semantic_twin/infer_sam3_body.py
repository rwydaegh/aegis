"""Reconstruct segmented people in panorama crops with SAM 3D Body."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.body_inference import (
    PERSON_WORDS,
    BodyInferenceConfig,
    infer_bodies,
    person_class_ids,
)

__all__ = ["PERSON_WORDS", "person_class_ids"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--view-names", nargs="+")
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--mhr-path", type=pathlib.Path)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    parser.add_argument("--min-pixels", type=int, default=600)
    parser.add_argument("--min-height-px", type=int, default=48)
    parser.add_argument("--max-people-per-view", type=int)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    infer_bodies(
        BodyInferenceConfig(
            views=args.views,
            semantics_json=args.semantics_json,
            out=args.out,
            checkpoint=args.checkpoint,
            view_names=tuple(args.view_names) if args.view_names else None,
            mhr_path=args.mhr_path,
            fov_deg=args.fov_deg,
            min_pixels=args.min_pixels,
            min_height_px=args.min_height_px,
            max_people_per_view=args.max_people_per_view,
        )
    )


if __name__ == "__main__":
    main()
