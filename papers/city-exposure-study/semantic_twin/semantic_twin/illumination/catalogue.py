"""The illumination models this study ships, and the two registries over them.

Nothing is derived here. Every constant is the one that was captured before the
refactor and every description string is the one that goes into a manifest, so a
run written yesterday and a run written today describe themselves identically.

:data:`MODELS` is the three the study reports. Adding to it changes the schema of
every streamed row, so alternatives live in :data:`VARIANTS` instead.
"""

from __future__ import annotations

from .bands import BandLaw, BandPathlossLaw, FixedHeightLaw
from .model import LAW_REGISTRY, ElevationLaw, Isotropic

#: Height above the pedestrian head, and horizontal range, of each site
#: population. These are the model for the band laws, not a comment beside it.
ROOFTOP_HEIGHT_BAND_M = (13.5, 43.5)
ROOFTOP_RANGE_BAND_M = (25.0, 250.0)
STREET_HEIGHT_BAND_M = (2.5, 6.5)
STREET_RANGE_BAND_M = (10.0, 150.0)

ISOTROPIC = Isotropic(
    name="isotropic",
    description="Uniform over 4 pi. Equals 1 in free space by construction.",
)

ROOFTOP = BandLaw(
    name="rooftop",
    height_band_m=ROOFTOP_HEIGHT_BAND_M,
    range_band_m=ROOFTOP_RANGE_BAND_M,
    description=(
        "Macro sites of uniform areal density, height above head 13.5 to 43.5 m drawn "
        "independently of position, horizontal range 25 to 250 m. Density on dOmega goes "
        "as the count of sites per steradian, which is the cubed slant range depth of the "
        "height band along that direction. MONOSTATIC_SBR.md section 2.7, corrected "
        "2026-08-02."
    ),
)

STREET_SMALL_CELL = BandLaw(
    name="street_small_cell",
    height_band_m=STREET_HEIGHT_BAND_M,
    range_band_m=STREET_RANGE_BAND_M,
    description=(
        "Street furniture small cells, height above head 2.5 to 6.5 m drawn independently "
        "of position, horizontal range 10 to 150 m. MONOSTATIC_SBR.md section 2.7, "
        "corrected 2026-08-02."
    ),
)

ROOFTOP_PATHLOSS = BandPathlossLaw(
    name="rooftop_pathloss",
    height_band_m=ROOFTOP_HEIGHT_BAND_M,
    range_band_m=ROOFTOP_RANGE_BAND_M,
    description=(
        "The rooftop population with every site weighted by its own free space spreading "
        "1/r^2, r the slant range. Density on dOmega is then the plain slant range depth "
        "of the height band, not its cube. Equal EIRP per site, no power control."
    ),
)

STREET_SMALL_CELL_PATHLOSS = BandPathlossLaw(
    name="street_small_cell_pathloss",
    height_band_m=STREET_HEIGHT_BAND_M,
    range_band_m=STREET_RANGE_BAND_M,
    description=(
        "The street small cell population with every site weighted by its own free space "
        "spreading 1/r^2, r the slant range."
    ),
)

#: What shipped before 2026-08-02. Every published susceptibility, every crop
#: convergence table and every cross city figure dated before then was computed
#: with these, so they are kept rather than deleted. They are the fixed height
#: law read over the window of a height band, which is the defect section 2.7
#: records.
ROOFTOP_FIXED_HEIGHT = FixedHeightLaw(
    name="rooftop_fixed_height",
    elevation_min_deg=3.1,
    elevation_max_deg=60.1,
    description=(
        "Uncorrected rooftop model, kept so numbers published before 2026-08-02 can be "
        "reproduced. Derived for sites at one fixed height, then given the support of a "
        "height band it does not describe. MONOSTATIC_SBR.md section 2.7."
    ),
)

STREET_SMALL_CELL_FIXED_HEIGHT = FixedHeightLaw(
    name="street_small_cell_fixed_height",
    elevation_min_deg=0.95,
    elevation_max_deg=33.0,
    description=(
        "Uncorrected street small cell model, kept so numbers published before 2026-08-02 "
        "can be reproduced. MONOSTATIC_SBR.md section 2.7."
    ),
)

#: The three the study reports.
MODELS: dict[str, ElevationLaw] = {model.name: model for model in (ISOTROPIC, ROOFTOP, STREET_SMALL_CELL)}

#: Every model this module defines, including the path loss weighted variants and
#: the two uncorrected ones, for ablations and for reproducing old numbers.
VARIANTS: dict[str, ElevationLaw] = {
    model.name: model
    for model in (
        ISOTROPIC,
        ROOFTOP,
        STREET_SMALL_CELL,
        ROOFTOP_PATHLOSS,
        STREET_SMALL_CELL_PATHLOSS,
        ROOFTOP_FIXED_HEIGHT,
        STREET_SMALL_CELL_FIXED_HEIGHT,
    )
}

#: The law tags, read off the registry rather than listed. Importing this module
#: is what guarantees the shipped laws have registered, which is why the snapshot
#: is taken here and not in ``model.py``.
LAWS: tuple[str, ...] = tuple(LAW_REGISTRY)

#: The tags whose window and shape both follow from a height band and a range
#: band rather than from a pair of hand written elevation limits.
BAND_LAWS: tuple[str, ...] = tuple(tag for tag, cls in LAW_REGISTRY.items() if issubclass(cls, BandLaw))
