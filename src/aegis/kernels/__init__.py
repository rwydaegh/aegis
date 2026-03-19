"""Dosimetry kernels: fidelity levels 0-8.

Levels 0-6 are incoherent. Levels 7-8 are coherent MIMO.
"""

from aegis.kernels.level0_bound import level0_bound
from aegis.kernels.level1_aggregate import level1_aggregate
from aegis.kernels.level2_geometric import level2_geometric
from aegis.kernels.level3_fresnel import level3_fresnel
from aegis.kernels.level4_polarisation import level4_polarisation
from aegis.kernels.level5_curvature import level5_curvature
from aegis.kernels.level6_diffraction import level6_diffraction
from aegis.kernels.level7_coherent import level7_coherent
from aegis.kernels.level8_ecbf import level8_ecbf

__all__ = [
    "level0_bound",
    "level1_aggregate",
    "level2_geometric",
    "level3_fresnel",
    "level4_polarisation",
    "level5_curvature",
    "level6_diffraction",
    "level7_coherent",
    "level8_ecbf",
]
