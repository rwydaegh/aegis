"""Run the foliage treatment sensitivity study."""

from __future__ import annotations

import argparse

from semantic_twin.materials import foliage_study


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=foliage_study.__doc__)
    parser.add_argument("stages", nargs="*", default=None, help="sweep, leaf, figure")
    parser.add_argument("--rays", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=17)
    arguments = parser.parse_args(argv)
    foliage_study.run(arguments.stages, rays=arguments.rays, seed=arguments.seed)


if __name__ == "__main__":
    main()
