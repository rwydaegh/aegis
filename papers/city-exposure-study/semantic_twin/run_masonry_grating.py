"""Run the masonry grating study."""

from __future__ import annotations

import argparse

from semantic_twin.materials.masonry import grating_study


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=grating_study.__doc__)
    parser.add_argument(
        "--stage",
        choices=("census", "rcwa", "kirchhoff", "maps", "model", "validate", "all"),
        default="all",
    )
    arguments = parser.parse_args(argv)
    grating_study.run(arguments.stage)


if __name__ == "__main__":
    main()
