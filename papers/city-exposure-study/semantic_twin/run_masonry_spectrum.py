"""Run the rigorous masonry spectrum study."""

from __future__ import annotations

import argparse

from semantic_twin.materials.masonry import spectrum_study


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=spectrum_study.__doc__)
    parser.add_argument("--stage", choices=("converge", "spectrum", "all"), default="all")
    parser.add_argument("--memory-budget-gib", type=float, default=18.0)
    parser.add_argument("--time-budget-s", type=float, default=2400.0)
    parser.add_argument("--multiplier", type=float, default=1.5)
    arguments = parser.parse_args(argv)
    spectrum_study.run(
        arguments.stage,
        memory_budget_gib=arguments.memory_budget_gib,
        time_budget_s=arguments.time_budget_s,
        multiplier=arguments.multiplier,
    )


if __name__ == "__main__":
    main()
