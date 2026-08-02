"""Adjoint shoot and bounce propagation core for the semantic twin.

Streaming by design. A trace reduces to per location scalars and one angular
power spectrum on a few hundred cell grid, and the paths are discarded. Nothing
in this package writes a path or a ray table.
"""

from .closed_form import PEC_PERMITTIVITY, ground_plane_susceptibility
from .directions import ISOTROPIC, MODELS, ROOFTOP, STREET_SMALL_CELL, fibonacci_sphere
from .geometry import MitsubaGeometry, PlaneGeometry, SphereGeometry
from .tracer import PointResult, SbrTracer, TraceConfig

__all__ = [
    "ISOTROPIC",
    "MODELS",
    "PEC_PERMITTIVITY",
    "ROOFTOP",
    "STREET_SMALL_CELL",
    "MitsubaGeometry",
    "PlaneGeometry",
    "PointResult",
    "SbrTracer",
    "SphereGeometry",
    "TraceConfig",
    "fibonacci_sphere",
    "ground_plane_susceptibility",
]
