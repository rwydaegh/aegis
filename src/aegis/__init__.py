"""AEGIS - Adaptive Electromagnetic Geometric Illumination & Safety."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from aegis._version import __version__
except ImportError:
    __version__ = "0.0.0+unknown"

if TYPE_CHECKING:
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


def __getattr__(name: str) -> Any:
    if name == "BodyMesh":
        from aegis.geometry.mesh import BodyMesh

        return BodyMesh
    if name == "DosimetryEngine":
        from aegis.engine import DosimetryEngine

        return DosimetryEngine
    if name == "DosimetryResult":
        from aegis.result import DosimetryResult

        return DosimetryResult
    if name == "Precoder":
        from aegis.precoder import Precoder

        return Precoder
    if name == "PropagationPaths":
        from aegis.paths import PropagationPaths

        return PropagationPaths
    if name == "TissueModel":
        from aegis.tissue.dielectric import TissueModel

        return TissueModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
