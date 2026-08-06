"""Compute an upper bound on the power that diffraction could add."""

from __future__ import annotations

import argparse

from semantic_twin.propagation import diffraction_bound


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument(
        "--locations",
        default=None,
        help="locations jsonl of the production run, defaults to the corrected 250 m one",
    )
    parser.add_argument("--mesh", default=None)
    parser.add_argument("--standpoints", type=int, default=20, help="how many, taken lowest sky fraction first")
    parser.add_argument("--azimuth", type=int, default=720)
    parser.add_argument("--elevation", type=int, default=600)
    parser.add_argument("--elevation-floor-deg", type=float, default=0.05)
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args(argv)
    config = diffraction_bound.DiffractionBoundConfig(
        site=arguments.site,
        locations=arguments.locations,
        mesh=arguments.mesh,
        standpoints=arguments.standpoints,
        azimuth=arguments.azimuth,
        elevation=arguments.elevation,
        elevation_floor_deg=arguments.elevation_floor_deg,
        out=arguments.out,
    )
    diffraction_bound.run(config)


if __name__ == "__main__":
    main()
