"""Geometry and closed-form checks used by the transport package.

The tracer now lives in :mod:`semantic_twin.transport`. Its established public
names remain available here because the frozen golden capture imports this
package facade.
"""

from ..illumination import (
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
from .closed_form import PEC_PERMITTIVITY, ground_plane_susceptibility
from .geometry import MitsubaGeometry, PlaneGeometry, SphereGeometry  # noqa: F401
from ..transport.tracer import (
    DEFAULT_MAX_BOUNCES,
    TERMINATIONS,
    BounceEvidenceTally,
    PathRecord,
    PathRecorder,
    PointResult,
    SbrTracer,
    TraceConfig,
    trace_standpoints,
)

__all__ = [
    "DEFAULT_MAX_BOUNCES",
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
    "BounceEvidenceTally",
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
    "trace_standpoints",
]
