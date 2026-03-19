"""AEGIS - Adaptive Electromagnetic Geometric Illumination & Safety."""

__version__ = "0.3.0"

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
