"""Fidelity-level catalog served via ``GET /api/levels``."""

from __future__ import annotations

# Names and blurbs match the kernel modules in src/aegis/kernels/.
FIDELITY_LEVELS_API = [
    {
        "level": 0,
        "name": "Bound",
        "description": (
            "Worst-case absorbed power bound: O(1) in mesh size. "
            "Uniform per-triangle S_ab from a scalar bound, not a resolved hotspot map."
        ),
    },
    {
        "level": 1,
        "name": "Aggregate",
        "description": (
            "Total absorbed power via spherical-harmonic absorption directivity per path, O(N) in paths. "
            "Per-triangle S_ab is uniform because the spatial map is not resolved."
        ),
    },
    {
        "level": 2,
        "name": "Geometric ReLU",
        "description": (
            "Incoherent spatial map S_ab = T_0 * ReLU(n_hat \u00b7 (-k_hat)) weighted by path powers. "
            "Standard level for compliance-style assessment."
        ),
    },
    {
        "level": 3,
        "name": "Fresnel",
        "description": (
            "Like level 2 but with angle-dependent unpolarised Fresnel transmission T_avg(theta) instead of fixed T_0."
        ),
    },
    {
        "level": 4,
        "name": "Polarisation",
        "description": (
            "Polarisation-aware Fresnel (TM/TE splitting). Collapses to level 3 for unpolarised or circular waves."
        ),
    },
    {
        "level": 5,
        "name": "Curvature",
        "description": (
            "Adds a first-order physical optics curvature correction on top of the Fresnel map "
            "(level 3 baseline with extra ReLU-squared term)."
        ),
    },
    {
        "level": 6,
        "name": "Diffraction",
        "description": (
            "Smooths the shadow boundary by replacing sharp ReLU with a physical GELU kernel tied to local curvature."
        ),
    },
    {
        "level": 7,
        "name": "Coherent MIMO",
        "description": (
            "Coherent absorption map from the body-surface channel and precoding vector x using path phasors psi."
        ),
    },
    {
        "level": 8,
        "name": "ECBF",
        "description": (
            "Exposure-constrained beamforming: solves for the precoder that maximises signal power "
            "subject to absorbed power and transmit power limits."
        ),
    },
]
