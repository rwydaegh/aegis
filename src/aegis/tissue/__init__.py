"""Tissue electromagnetic properties: Fresnel, Cole-Cole, IT'IS database."""

from aegis.tissue.dielectric import (
    FAT_28GHZ,
    MUSCLE_28GHZ,
    SKIN_28GHZ,
    SKIN_60GHZ,
    TissueModel,
)
from aegis.tissue.fresnel import T0, fresnel_transmission, n_complex

__all__ = [
    "FAT_28GHZ",
    "MUSCLE_28GHZ",
    "SKIN_28GHZ",
    "SKIN_60GHZ",
    "T0",
    "TissueModel",
    "fresnel_transmission",
    "n_complex",
]
