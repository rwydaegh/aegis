"""AEGIS - Adaptive Electromagnetic Geometric Illumination & Safety."""

try:
    from aegis._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import TissueModel

__all__ = [
    "BodyMesh",
    "DosimetryEngine",
    "DosimetryResult",
    "Precoder",
    "PropagationPaths",
    "TissueModel",
]
