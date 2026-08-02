"""Adjoint shoot and bounce propagation core for the semantic twin.

Streaming by design. A trace reduces to per location scalars and one angular
power spectrum on a few hundred cell grid, and the paths are discarded. Nothing
in this package writes a path or a ray table.

The one exception is :class:`~.tracer.PathRecorder`, which keeps the polyline of
a capped number of rays so a figure can show the paths the estimator integrated.
It is opt in, bounded by a capacity set at the call site, and off in every
production run.
"""

from .closed_form import PEC_PERMITTIVITY, ground_plane_susceptibility
from .directions import (
    ISOTROPIC,
    MODELS,
    ROOFTOP,
    ROOFTOP_FIXED_HEIGHT,
    ROOFTOP_PATHLOSS,
    STREET_SMALL_CELL,
    STREET_SMALL_CELL_FIXED_HEIGHT,
    STREET_SMALL_CELL_PATHLOSS,
    VARIANTS,
    IlluminationModel,
    elevation_band_measure,
    fibonacci_sphere,
    measure_below,
)
from .geometry import MitsubaGeometry, PlaneGeometry, SphereGeometry
from .tracer import TERMINATIONS, PathRecord, PathRecorder, PointResult, SbrTracer, TraceConfig

__all__ = [
    "ISOTROPIC",
    "MODELS",
    "PEC_PERMITTIVITY",
    "ROOFTOP",
    "ROOFTOP_FIXED_HEIGHT",
    "ROOFTOP_PATHLOSS",
    "STREET_SMALL_CELL",
    "STREET_SMALL_CELL_FIXED_HEIGHT",
    "STREET_SMALL_CELL_PATHLOSS",
    "TERMINATIONS",
    "VARIANTS",
    "IlluminationModel",
    "MitsubaGeometry",
    "PathRecord",
    "PathRecorder",
    "PlaneGeometry",
    "PointResult",
    "SbrTracer",
    "SphereGeometry",
    "TraceConfig",
    "elevation_band_measure",
    "fibonacci_sphere",
    "ground_plane_susceptibility",
    "measure_below",
]
