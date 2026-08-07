"""Where the base stations are.

This study has two illumination laws and they are alternatives, not layers. The
band law puts sites in a height band and a range band and hands the tracer an
angular density. The facade tip law reads the rooflines the geometry has and
hands the tracer a set of points to connect to. Every published number was
written by the first. The second is the declared replacement.

The choice between them used to be a string compared in a switch inside one
dataclass, which hid that they were alternatives and forced the newer law to be
built in a different file. Here each law is a class, each class registers its own
tag, and :mod:`~.model` says what the two shapes have in common and where they
part company.

Reading order: :mod:`~.model` for the protocols and the registry,
:mod:`~.bands` for the legacy control, :mod:`~.roofline` and :mod:`~.sources` for
the facade tip law, :mod:`~.catalogue` for the models the study ships,
:mod:`~.measure` for the two reductions figures read, and :mod:`~.sphere` for the
direction grid the density is evaluated on.
"""

from __future__ import annotations

from .bands import BandLaw, BandPathlossLaw, FixedHeightLaw
from .catalogue import (
    BAND_LAWS,
    ISOTROPIC,
    LAWS,
    MODELS,
    ROOFTOP,
    ROOFTOP_FIXED_HEIGHT,
    ROOFTOP_HEIGHT_BAND_M,
    ROOFTOP_PATHLOSS,
    ROOFTOP_RANGE_BAND_M,
    STREET_HEIGHT_BAND_M,
    STREET_RANGE_BAND_M,
    STREET_SMALL_CELL,
    STREET_SMALL_CELL_FIXED_HEIGHT,
    STREET_SMALL_CELL_PATHLOSS,
    VARIANTS,
)
from .curve import (
    FacadeTipCurve,
    build_facade_tip_curve,
    build_mesh_edge_curve,
    curve_from_polylines,
    merge_segments,
    polyline_segments,
    silhouette_polyline,
)
from .measure import elevation_band_measure, measure_below
from .model import (
    LAW_REGISTRY,
    QUADRATURE,
    AngularIllumination,
    ElevationLaw,
    IlluminationModel,
    Isotropic,
    PlacedIllumination,
    credited_by,
    register_law,
    solid_angle_of_band,
)
from .roofline import FACADE_TIP_FAMILY, FACADE_TIP_LAW, Roofline, extract_roofline, silhouette
from .sources import SITE_LIFT_M, SourceSet, build_source_set, thin
from .sphere import fibonacci_sphere, nearest_cell, sample_sphere

__all__ = [
    "BAND_LAWS",
    "FACADE_TIP_FAMILY",
    "FACADE_TIP_LAW",
    "ISOTROPIC",
    "LAWS",
    "LAW_REGISTRY",
    "MODELS",
    "QUADRATURE",
    "ROOFTOP",
    "ROOFTOP_FIXED_HEIGHT",
    "ROOFTOP_HEIGHT_BAND_M",
    "ROOFTOP_PATHLOSS",
    "ROOFTOP_RANGE_BAND_M",
    "SITE_LIFT_M",
    "STREET_HEIGHT_BAND_M",
    "STREET_RANGE_BAND_M",
    "STREET_SMALL_CELL",
    "STREET_SMALL_CELL_FIXED_HEIGHT",
    "STREET_SMALL_CELL_PATHLOSS",
    "VARIANTS",
    "AngularIllumination",
    "BandLaw",
    "BandPathlossLaw",
    "FacadeTipCurve",
    "ElevationLaw",
    "FixedHeightLaw",
    "IlluminationModel",
    "Isotropic",
    "PlacedIllumination",
    "Roofline",
    "SourceSet",
    "build_source_set",
    "build_facade_tip_curve",
    "build_mesh_edge_curve",
    "curve_from_polylines",
    "credited_by",
    "elevation_band_measure",
    "extract_roofline",
    "fibonacci_sphere",
    "measure_below",
    "merge_segments",
    "nearest_cell",
    "register_law",
    "sample_sphere",
    "polyline_segments",
    "silhouette",
    "silhouette_polyline",
    "solid_angle_of_band",
    "thin",
]
