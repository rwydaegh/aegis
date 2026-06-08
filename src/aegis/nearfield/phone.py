"""Point-source near-field kernel for a hand-held device.

The source radiates a known free-space pattern from a point at ``position`` with
body-frame orientation ``rotation`` (a 3x3 rotation matrix mapping antenna-frame
vectors to world). Every body triangle sees a locally plane wave travelling along
the source -> centroid line of sight, with power density set by the inverse-square
spread and the sampled directivity.

The kernel reuses the AEGIS surface physics: the Fresnel power transmission
(``aegis.tissue.fresnel``) and the ReLU projection from the absorbed-power-density
law ``S_ab = S_inc * T_eff * ReLU(mu)``. It is written against the array backend,
so under JAX it is differentiable in ``position`` and ``rotation``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis._array_backend import xp
from aegis.nearfield.patterns import AntennaPattern3D
from aegis.tissue.fresnel import _fresnel_core


@dataclass
class PhoneSource:
    """A hand-held radiating source.

    Parameters
    ----------
    position : (3,) source location in world coordinates [m]
    rotation : (3, 3) antenna-frame -> world rotation matrix
    pattern : AntennaPattern3D directivity pattern
    radiated_power_w : total radiated power P_rad [W]. The EIRP along a
        direction is ``P_rad * D(k)``. Default 1 W gives results normalised
        per watt of radiated power (W/m^2 per W), matching the GOLIAT
        "normalized SAR" convention once divided by tissue density.
    """

    position: np.ndarray
    rotation: np.ndarray
    pattern: AntennaPattern3D
    radiated_power_w: float = 1.0

    @classmethod
    def from_euler(
        cls,
        position,
        pattern: AntennaPattern3D,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        radiated_power_w: float = 1.0,
    ) -> PhoneSource:
        """Build a source from intrinsic Z-Y-X Euler angles [rad]."""
        return cls(
            position=np.asarray(position, dtype=np.float64),
            rotation=euler_to_matrix(yaw, pitch, roll),
            pattern=pattern,
            radiated_power_w=radiated_power_w,
        )


def euler_to_matrix(yaw, pitch, roll):
    """Intrinsic Z-Y-X (yaw, pitch, roll) rotation matrix, backend-agnostic.

    Differentiable in the angles under the JAX backend.
    """
    cy, sy = xp.cos(yaw), xp.sin(yaw)
    cp, sp = xp.cos(pitch), xp.sin(pitch)
    cr, sr = xp.cos(roll), xp.sin(roll)
    rz = xp.stack(
        [
            xp.stack([cy, -sy, xp.zeros_like(cy)]),
            xp.stack([sy, cy, xp.zeros_like(cy)]),
            xp.stack([xp.zeros_like(cy), xp.zeros_like(cy), xp.ones_like(cy)]),
        ]
    )
    ry = xp.stack(
        [
            xp.stack([cp, xp.zeros_like(cp), sp]),
            xp.stack([xp.zeros_like(cp), xp.ones_like(cp), xp.zeros_like(cp)]),
            xp.stack([-sp, xp.zeros_like(cp), cp]),
        ]
    )
    rx = xp.stack(
        [
            xp.stack([xp.ones_like(cr), xp.zeros_like(cr), xp.zeros_like(cr)]),
            xp.stack([xp.zeros_like(cr), cr, -sr]),
            xp.stack([xp.zeros_like(cr), sr, cr]),
        ]
    )
    return rz @ ry @ rx


def incident_field(centroids, position, rotation, pattern: AntennaPattern3D, radiated_power_w):
    """Per-triangle incident power density and arrival direction.

    Returns
    -------
    s_inc : (M,) incident power density [W/m^2]
    k_hat : (M, 3) unit propagation direction (source -> centroid)
    """
    pos = xp.asarray(position)
    rot = xp.asarray(rotation)
    rel = centroids - pos[None, :]  # (M, 3) source -> centroid
    dist = xp.sqrt(xp.sum(rel * rel, axis=-1))  # (M,)
    k_hat = rel / dist[:, None]

    # Express the line of sight in the antenna body frame: dir_ant = R^T k_hat.
    dir_ant = k_hat @ rot  # (M,3) @ (3,3) == (R^T k)^T rows
    directivity = pattern.sample(dir_ant)  # (M,)

    s_inc = radiated_power_w * directivity / (4.0 * np.pi * dist * dist)
    return s_inc, k_hat


def compute_sab(
    centroids,
    normals,
    source: PhoneSource,
    t0: float,
    n_tilde: complex | None = None,
    fresnel: bool = True,
):
    """Absorbed power density per triangle for a phone source.

    Parameters
    ----------
    centroids : (M, 3) triangle centroids [m]
    normals : (M, 3) unit outward normals
    source : PhoneSource
    t0 : float normal-incidence Fresnel power transmission (tissue.T0)
    n_tilde : complex refractive index; required when ``fresnel=True`` to apply
        the angle-dependent (unpolarised) transmission T_eff(mu).
    fresnel : if False use the constant ``t0`` (geometric level-2 style).

    Returns
    -------
    sab : (M,) absorbed power density [W/m^2]
    """
    centroids = xp.asarray(centroids)
    normals = xp.asarray(normals)
    s_inc, k_hat = incident_field(centroids, source.position, source.rotation, source.pattern, source.radiated_power_w)
    mu = xp.sum(normals * (-k_hat), axis=-1)  # incidence cosine
    relu_mu = xp.maximum(mu, 0.0)

    if fresnel:
        if n_tilde is None:
            raise ValueError("n_tilde required when fresnel=True")
        # _fresnel_core returns (r_s, r_p, T_s, T_p, t_s, t_p); we want the
        # power transmissions T_s, T_p and average them (unpolarised source).
        _, _, t_pow_s, t_pow_p, _, _ = _fresnel_core(relu_mu, n_tilde)
        t_eff = 0.5 * (t_pow_s + t_pow_p)
    else:
        t_eff = t0

    return s_inc * t_eff * relu_mu


def compute_sab_batch(
    centroids,
    normals,
    positions,
    rotations,
    pattern: AntennaPattern3D,
    t0: float,
    n_tilde: complex,
    radiated_power_w: float = 1.0,
    fresnel: bool = True,
):
    """Vectorised absorbed power density for a batch of source poses.

    Evaluates ``B`` source configurations against one mesh in a single pass,
    which is the workhorse for the position/orientation sweep.

    Parameters
    ----------
    centroids : (M, 3)
    normals : (M, 3)
    positions : (B, 3) source positions [m]
    rotations : (B, 3, 3) antenna-frame -> world rotation matrices
    pattern, t0, n_tilde, radiated_power_w, fresnel : as in :func:`compute_sab`

    Returns
    -------
    sab : (B, M) absorbed power density [W/m^2]
    """
    centroids = xp.asarray(centroids)
    normals = xp.asarray(normals)
    positions = xp.asarray(positions)
    rotations = xp.asarray(rotations)

    rel = centroids[None, :, :] - positions[:, None, :]  # (B, M, 3)
    dist = xp.sqrt(xp.sum(rel * rel, axis=-1))  # (B, M)
    k_hat = rel / dist[..., None]

    # dir_ant[b, m] = R_b^T k_hat[b, m]
    dir_ant = xp.einsum("bmi,bij->bmj", k_hat, rotations)
    directivity = pattern.sample(dir_ant)  # (B, M)

    s_inc = radiated_power_w * directivity / (4.0 * np.pi * dist * dist)
    mu = xp.sum(normals[None, :, :] * (-k_hat), axis=-1)
    relu_mu = xp.maximum(mu, 0.0)

    if fresnel:
        _, _, t_pow_s, t_pow_p, _, _ = _fresnel_core(relu_mu, n_tilde)
        t_eff = 0.5 * (t_pow_s + t_pow_p)
    else:
        t_eff = t0

    return s_inc * t_eff * relu_mu
