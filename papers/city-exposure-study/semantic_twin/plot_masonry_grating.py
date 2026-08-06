"""Plot the masonry grating study."""

import argparse

from semantic_twin.viz.masonry_grating import FIGURES_BY_NAME, plot_masonry_grating


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure", choices=(*FIGURES_BY_NAME, "all"), default="all")
    return parser.parse_args()


def main() -> None:
    plot_masonry_grating(arguments().figure)


if __name__ == "__main__":
    main()
