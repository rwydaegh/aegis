"""Coherent MIMO dosimetry: field channel, Fresnel operator, exposure operator Q.

Levels 7-8 of the AEGIS fidelity hierarchy.
"""

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)
from aegis.coherent.field_channel import compute_field_channel
from aegis.coherent.fresnel_operator import (
    apply_fresnel_operator,
    compute_fresnel_operator,
    te_tm_basis,
)

__all__ = [
    "apply_fresnel_operator",
    "compute_body_channel",
    "compute_exposure_operator",
    "compute_field_channel",
    "compute_fresnel_operator",
    "compute_rho",
    "eigendecompose_Q",
    "solve_ecbf",
    "te_tm_basis",
]
