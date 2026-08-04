"""Collect the per-panorama registration results for a site into one table.

Every panorama fetched by ``fetch_site_panoramas.py`` is registered on its own,
so the useful quantity is the distribution over a site rather than any single
residual. This reads the aligned poses and writes one JSON summary plus a
markdown table per site.

The two numbers to read first are the median skyline residual, which says how
well the modelled silhouette matches the segmented one, and the count of poses
whose recovered altitude landed on its search bound. A pose at its bound is not
a measurement: it is the bound, and every previously shipped pose in this
repository had that defect.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python summarise_site_panoramas.py \
      --site data/panoramas/prague_staromestske --out outputs/city_screening
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from semantic_twin import paths
from semantic_twin.report.panorama_registration import write_summary


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=pathlib.Path, nargs="+", required=True)
    parser.add_argument("--out", type=pathlib.Path, default=paths.output("city_screening"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    print(write_summary(args.site, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
