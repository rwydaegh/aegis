"""How much of a connected panorama chain each site can actually supply.

The exposure method puts the transmitter and the receiver at the same point and
its evidence is the photograph taken at that point. BOUNCE_BUDGET.md measures how
far that reaches: the first surface interaction lands on photographed geometry
with probability 0.999 at a panorama position and about 0.1 past forty metres. So
a route made of panorama positions is the only walk the method has evidence for
along its whole length, and the question this script answers is whether such a
route exists.

It reports, per site, how many panoramas are on disk, how many registered, how
many the admission gate admitted, whether those admitted cameras form one chain
in the provider's link graph or several fragments, how long the chain is along
the road, and what the spacing between standpoints is. It also reports the
spacing of the underlying link graph, which is the spacing a route would have if
every panorama of the drive were on disk rather than the spread out subset the
acquisition selected.

The detour ratio divides the road length by the straight hops between the
registered camera positions, and those are two different measurements of the same
walk: the road runs through the provider's published positions and the hops run
through the skyline registered ones, which differ by 1 to 6 m. So a ratio a
fraction below one means the route is straight, not that the road is shorter than
the line.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python summarise_panorama_routes.py \
      --out outputs/panorama_routes
"""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin import paths
from semantic_twin.report.panorama_routes import build_report, write_report
from semantic_twin.sites import STUDY_ORDER


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=paths.root())
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--site", action="append", default=None)
    args = parser.parse_args()

    rows, rendered = build_report(args.site or sorted(STUDY_ORDER), args.root)
    print(rendered)
    if args.out is not None:
        write_report(rows, rendered, args.out)


if __name__ == "__main__":
    main()
