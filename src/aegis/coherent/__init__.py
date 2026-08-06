"""Coherent MIMO dosimetry: field channel, Fresnel operator, exposure operator Q.

Levels 7-8 of the AEGIS fidelity hierarchy.
"""

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf, solve_ecbf_sweep
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
from aegis.coherent.multibody_ecbf import (
    MultibodyECBFDiagnostics,
    solve_multibody_ecbf,
)
from aegis.coherent.translation import (
    compute_static_path_gram,
    q_translate,
    q_translate_batch,
    translation_phasor,
)

__all__ = [
    "MultibodyECBFDiagnostics",
    "apply_fresnel_operator",
    "compute_body_channel",
    "compute_exposure_operator",
    "compute_field_channel",
    "compute_fresnel_operator",
    "compute_rho",
    "compute_static_path_gram",
    "eigendecompose_Q",
    "q_translate",
    "q_translate_batch",
    "solve_ecbf",
    "solve_ecbf_sweep",
    "solve_multibody_ecbf",
    "te_tm_basis",
    "translation_phasor",
]
