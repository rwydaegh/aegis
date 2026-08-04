"""Closed form references the estimator is checked against.

MONOSTATIC_SBR.md section 11.1. A ground plane under the observation point is
the cheapest test in the set and the one that catches the most, because a
naive amplitude accumulating estimator returns exactly 1 against a target of
exactly 2 with no visible noise.
"""

from __future__ import annotations

import numpy as np


def ground_plane_susceptibility(elevation_deg: float | np.ndarray, permittivity: complex) -> np.ndarray:
    """Band averaged `K_tot(u_ext)` for a plane wave over a half space.

    The direct wave and the specularly reflected wave arrive at `S` from two
    distinct local directions with an excess path `2*h*sin(el)`. Once the
    interference term is averaged over a band wide enough that `2*pi*B*tau`
    exceeds a cycle, which every FR2 or FR3 carrier bandwidth is at metre scale
    standoffs, the two add in power:

        K = 1 + (|Gamma_TE|**2 + |Gamma_TM|**2) / 2

    For a perfect conductor `|Gamma| = 1` in both polarisations and `K = 2`
    exactly at every elevation, which is the angle independent, non trivial
    target section 11.1 asks for.
    """
    from ..transport.tracer import fresnel_power_reflectance

    cosine = np.cos(np.radians(90.0 - np.asarray(elevation_deg, dtype=np.float64)))
    return 1.0 + fresnel_power_reflectance(cosine, np.asarray(permittivity))


def ground_plane_susceptibility_te_only(elevation_deg: float | np.ndarray, permittivity: complex) -> np.ndarray:
    """The same quantity computed from TE alone, which is the wrong answer.

    Kept because it is the specific mistake the dielectric test has to be able
    to reject. Near the pseudo Brewster angle of concrete, around 24 degrees
    elevation, TM is smaller than TE by nearly three orders of magnitude, so
    ``1.226`` and ``1.452`` are separated by about 0.9 dB. The perfect conductor
    case cannot see that difference at all, since both coefficients have unit
    magnitude at every angle.
    """
    cosine = np.cos(np.radians(90.0 - np.asarray(elevation_deg, dtype=np.float64)))
    cos_i = np.clip(cosine, 0.0, 1.0).astype(np.complex128)
    root = np.sqrt(np.asarray(permittivity) - (1.0 - cos_i**2))
    te = (cos_i - root) / (cos_i + root)
    return 1.0 + np.abs(te) ** 2


def ground_plane_band_average(sin_edges: np.ndarray, permittivity: complex, samples: int = 4096) -> np.ndarray:
    """Closed form ``K_tot`` averaged over equal solid angle elevation bands.

    The tracer reports a band average, so comparing it against the closed form
    at the band centre would build the band width into the residual. This
    integrates the closed form over the same bands, uniformly in ``sin(el)``,
    which is the equal solid angle measure.
    """
    sin_edges = np.asarray(sin_edges, dtype=np.float64)
    out = np.zeros(sin_edges.size - 1)
    for i in range(out.size):
        grid = np.linspace(sin_edges[i], sin_edges[i + 1], samples)
        elevation = np.degrees(np.arcsin(np.clip(grid, -1.0, 1.0)))
        out[i] = float(np.mean(ground_plane_susceptibility(elevation, permittivity)))
    return out


#: Stand in for infinite conductivity. Large but finite, so the perfect
#: conductor target is 2 to about 1e-5 rather than to machine precision.
PEC_PERMITTIVITY = complex(1.0, -1.0e12)
