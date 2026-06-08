"""Near-field point-source exposure from a hand-held device (phone).

The hand-held antenna (IFA/PIFA on a smartphone) is electrically small, so its
Fraunhofer distance is only a few centimetres. At the 8-200 mm holding distances
of interest the radiated field is therefore locally a plane wave at every body
triangle, but with a per-triangle direction and amplitude set by the spherical
wavefront emanating from the source. The absorbed power density is

    S_ab(r) = EIRP * D(k_ant(r)) / (4 pi d(r)^2) * T_eff(mu(r)) * ReLU(mu(r)),

with d(r) the source-to-triangle distance, D the (measured) free-space
directivity sampled along the line of sight in the antenna frame, mu = n_hat .
(-k_hat) the local incidence cosine, and T_eff the Fresnel power transmission.

This reuses the AEGIS surface physics (Fresnel T0/T_eff, the spatial-averaging
matrix, the body mesh) and the surface-to-volume psSAR10g reduction derived in
``theory/psSAR10g.tex``. Everything is written against the array backend so it is
JAX-traceable end to end: gradients of any ICNIRP metric with respect to the
phone position and orientation are exact.
"""

from aegis.nearfield.metrics import IcnirpMetrics, compute_metrics
from aegis.nearfield.patterns import AntennaPattern3D
from aegis.nearfield.phone import PhoneSource, compute_sab

__all__ = [
    "AntennaPattern3D",
    "PhoneSource",
    "compute_sab",
    "IcnirpMetrics",
    "compute_metrics",
]
