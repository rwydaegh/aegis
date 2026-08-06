"""Label a support mesh from one panorama and export a Sionna RT scene."""

from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.scene import semantic_projection  # noqa: E402


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.35)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    semantic_projection.project_semantics(
        semantic_projection.SemanticProjectionConfig(
            mesh=args.mesh,
            semantics=args.semantics,
            semantics_json=args.semantics_json,
            pose=args.pose,
            out=args.out,
            min_confidence=args.min_confidence,
        )
    )


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    main(argv)
