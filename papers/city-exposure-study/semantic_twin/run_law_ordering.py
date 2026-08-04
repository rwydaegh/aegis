"""Command-line entry point for the cross-city illumination-law comparison."""

import argparse
import pathlib

from semantic_twin.report import law_ordering as study
from semantic_twin.report.law_ordering import OUTPUT, run

# Kept literal because the site-registry regression test reads command metadata
# without importing optional plotting and tracing dependencies.
LABEL = {
    "brussels_grandplace": "Brussels",
    "korenmarkt": "Ghent",
    "krakow_rynek": "Krakow",
    "london_trafalgar": "London",
    "madrid_plazamayor": "Madrid",
    "mexico_zocalo": "Mexico City",
    "milan_duomo": "Milan",
    "newyork_timessquare": "New York",
    "prague_staromestske": "Prague",
    "tokyo_hachiko": "Tokyo",
    "toulouse_capitole": "Toulouse",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=study.__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT / "eleven_city_law_ordering.json")
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
