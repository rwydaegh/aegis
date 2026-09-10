"""Stratified-tissue internal fields by the transfer-matrix method (TMM).

The paper's body channel collapses the depth integral into a single
half-space depth weight sqrt(sigma / 4 alpha) (Approximation 2). That is
exact for a homogeneous lossy half-space but says nothing about how the
field actually decays through the epidermis/dermis, fat, and into muscle.
This module solves the genuine multilayer problem so the visualisations can
show internal field vs depth under a hotspot, and so we can quantify how far
the single-layer approximation drifts at 28 GHz.

Model: a plane wave is incident from air (layer 0) at angle theta onto a
stack of parallel lossy dielectric slabs, terminated by a semi-infinite
muscle half-space. Each layer l has complex refractive index n_l and a
normal wavevector component k_{z,l} = k0 sqrt(n_l^2 - sin^2 theta). TE and
TM are solved independently with the standard 2x2 interface + propagation
transfer matrices. The forward/backward amplitudes in every layer are
recovered, giving the total tangential and normal field components, hence
|E(z)|^2 and the local SAR(z) = sigma |E(z)|^2 / (2 rho).

References: Born & Wolf Ch. 1.6 (stratified media); the convention here
keeps Re(k_z) >= 0 and Im(k_z) <= 0 so exp(-i k_z z) decays into the tissue.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.constants import C_0, EPS_0, MU_0
from aegis.tissue.fresnel import n_complex

# Mass densities [kg/m^3] for SAR normalisation (IT'IS / ICNIRP typical).
TISSUE_DENSITY = {
    "skin": 1109.0,
    "fat": 911.0,
    "muscle": 1090.0,
    "air": 1.2,
}


@dataclass
class Layer:
    """One slab in the stack."""

    name: str
    eps_r: float
    sigma: float
    thickness: float  # [m]; np.inf for the terminating half-space
    density: float = 1090.0

    def n_tilde(self, freq_hz: float) -> complex:
        return complex(n_complex(self.eps_r, self.sigma, freq_hz))


def default_stack(freq_hz: float = 28e9) -> list[Layer]:
    """Air | skin (epidermis+dermis) | fat | muscle half-space at 28 GHz.

    Tissue thicknesses are representative forearm/torso values; the dielectric
    parameters match the paper's SKIN/FAT/MUSCLE 28 GHz instances so the
    surface-side physics is consistent with the body channel.
    """
    return [
        Layer("air", 1.0, 0.0, np.inf, TISSUE_DENSITY["air"]),
        Layer("skin", 17.0, 25.0, 1.5e-3, TISSUE_DENSITY["skin"]),
        Layer("fat", 4.0, 2.0, 3.0e-3, TISSUE_DENSITY["fat"]),
        Layer("muscle", 25.0, 30.0, np.inf, TISSUE_DENSITY["muscle"]),
    ]


def _kz(n_tilde: complex, sin_theta: float, k0: float) -> complex:
    """Normal wavevector component, branch chosen to decay into +z."""
    kz = k0 * np.sqrt(n_tilde**2 - sin_theta**2 + 0j)
    # physics convention exp(-i k_z z): want Im(kz) <= 0 so amplitude decays
    if np.imag(kz) > 0:
        kz = -kz
    return kz


def _admittance(kz: complex, n_tilde: complex, freq_hz: float, pol: str) -> complex:
    """Tilted optical admittance eta such that H_tan = eta * E_tan.

    TE: eta = kz / (omega mu0).  TM: eta = omega eps0 n^2 / kz.  Both reduce
    to n/Z0 at normal incidence. These are the standard Macleod admittances;
    using them in the characteristic matrix keeps tangential E and H
    continuous across every interface by construction.
    """
    omega = 2 * np.pi * freq_hz
    if pol == "TE":
        return kz / (omega * MU_0)
    if pol == "TM":
        return omega * EPS_0 * n_tilde**2 / kz
    raise ValueError(pol)


def _char_matrix(kz: complex, eta: complex, thickness: float) -> np.ndarray:
    """Abeles characteristic matrix relating tangential (E, H) top->bottom.

    [E_top; H_top] = M [E_bot; H_bot]
    """
    delta = kz * thickness
    cos, sin = np.cos(delta), np.sin(delta)
    return np.array(
        [[cos, 1j * sin / eta], [1j * eta * sin, cos]],
        dtype=complex,
    )


@dataclass
class DepthProfile:
    """Internal field vs depth for one incident plane wave and polarisation."""

    z: np.ndarray  # depth from the air/skin interface [m], >= 0 into tissue
    E_abs: np.ndarray  # |E(z)| total [V/m] for unit incident |E|
    sar: np.ndarray  # local SAR(z) [W/kg] for unit incident |E|
    layer_of_z: np.ndarray  # index into the stack for each z
    boundaries: np.ndarray  # cumulative interface depths [m]
    power_transmission: float  # fraction of incident power crossing into tissue


def solve_layered(
    stack: list[Layer],
    freq_hz: float,
    theta_inc: float = 0.0,
    pol: str = "TE",
    *,
    n_z: int = 1200,
    depth_max: float | None = None,
    incident_amplitude: float = 1.0,
) -> DepthProfile:
    """Solve the stratified problem for one polarisation and incidence angle.

    Parameters
    ----------
    stack : list[Layer]
        Layer 0 is the incidence medium (air). The last layer is the
        terminating half-space (thickness ignored).
    theta_inc : float
        Incidence angle from the surface normal [rad].
    pol : {"TE", "TM"}
    n_z : int
        Depth samples across the rendered profile.
    depth_max : float
        Maximum depth [m]. Defaults to 3 skin depths into the final layer
        past the last finite interface.
    incident_amplitude : float
        Incident |E| in air [V/m]; fields scale linearly.

    Returns
    -------
    DepthProfile
    """
    omega = 2 * np.pi * freq_hz
    k0 = omega / C_0
    n = np.array([ly.n_tilde(freq_hz) for ly in stack])
    sin_theta = np.sin(theta_inc)
    kz = np.array([_kz(nl, sin_theta, k0) for nl in n])
    eta = np.array([_admittance(kz[li], n[li], freq_hz, pol) for li in range(len(stack))])

    L = len(stack)
    thick = np.array([ly.thickness for ly in stack])
    # cumulative interface depths (z=0 at air/first-tissue boundary)
    finite = thick.copy()
    finite[0] = 0.0
    finite[-1] = 0.0
    boundaries = np.concatenate([[0.0], np.cumsum(finite[1:-1])])  # interfaces after air

    # Characteristic-matrix product over the finite interior layers gives the
    # front-surface admittance seen looking into the stack, terminated by the
    # substrate admittance eta[-1]. Tangential (E, H) are continuous, so the
    # reflection coefficient follows from the input admittance Y = C/B.
    M = np.eye(2, dtype=complex)
    for li in range(1, L - 1):
        M = M @ _char_matrix(kz[li], eta[li], thick[li])
    bc = M @ np.array([1.0, eta[-1]], dtype=complex)  # [B, C] for unit substrate E
    B, C = bc[0], bc[1]
    Y_in = C / B  # input admittance at the air/skin interface
    r0 = (eta[0] - Y_in) / (eta[0] + Y_in)

    # The characteristic matrix uses tangential E. For TM, project the
    # specified total incident |E| onto the interface once.
    a_in = incident_amplitude * (np.cos(theta_inc) if pol == "TM" else 1.0)
    E_tan0 = a_in * (1.0 + r0)
    H_tan0 = a_in * eta[0] * (1.0 - r0)

    # Depth grid (z measured into the tissue from the air interface)
    if depth_max is None:
        alpha_last = -np.imag(kz[-1])  # decay rate of final layer [1/m]
        skin_depth = 1.0 / alpha_last if alpha_last > 1e-9 else 5e-3
        depth_max = float(boundaries[-1] + 3 * skin_depth) if L > 2 else 3 * skin_depth
    z = np.linspace(0.0, depth_max, n_z)

    # Layer index for each z: interface depths split air|...|muscle
    layer_of_z = np.searchsorted(boundaries, z, side="right")  # 1..L-1
    layer_of_z = np.clip(layer_of_z, 1, L - 1)

    # March the tangential (E, H) state to the top of each tissue layer, then
    # propagate analytically within the layer. The characteristic matrix is
    # written top->bottom, so stepping to the next layer applies M_l(thick).
    E_tan = np.zeros(n_z, dtype=complex)
    H_tan = np.zeros(n_z, dtype=complex)
    state_top = np.array([E_tan0, H_tan0], dtype=complex)  # top of layer 1
    for li in range(1, L):
        sel = layer_of_z == li
        if np.any(sel):
            z_local = z[sel] - boundaries[li - 1]
            cos, sin = np.cos(kz[li] * z_local), np.sin(kz[li] * z_local)
            # [E(z); H(z)] = Minv(z) [E_top; H_top]; Minv = char matrix with -z
            E_tan[sel] = cos * state_top[0] - 1j * sin / eta[li] * state_top[1]
            H_tan[sel] = -1j * eta[li] * sin * state_top[0] + cos * state_top[1]
        if li < L - 1:  # advance to the bottom face = top of the next layer
            cos, sin = np.cos(kz[li] * thick[li]), np.sin(kz[li] * thick[li])
            state_top = np.array(
                [
                    cos * state_top[0] - 1j * sin / eta[li] * state_top[1],
                    -1j * eta[li] * sin * state_top[0] + cos * state_top[1],
                ],
                dtype=complex,
            )

    # Normal E from D_z continuity. For TM, D_z = -(k_x/omega) H_tan, so
    # E_z = D_z / (eps0 n^2) jumps by 1/n^2 across each interface. TE has no
    # normal E component.
    if pol == "TM":
        k_x = k0 * sin_theta
        n2_of_z = np.array([n[li] ** 2 for li in layer_of_z])
        E_norm = -(k_x / (omega * EPS_0 * n2_of_z)) * H_tan
    else:
        E_norm = np.zeros(n_z, dtype=complex)

    E_total = np.sqrt(np.abs(E_tan) ** 2 + np.abs(E_norm) ** 2)

    # Local SAR(z) = sigma |E|^2 / (2 rho) using each z's layer properties.
    sigma_of_z = np.array([stack[li].sigma for li in layer_of_z])
    rho_of_z = np.array([stack[li].density for li in layer_of_z])
    sar = sigma_of_z * E_total**2 / (2 * rho_of_z)

    power_T = 1.0 - np.abs(r0) ** 2

    return DepthProfile(
        z=z,
        E_abs=E_total,
        sar=sar,
        layer_of_z=layer_of_z,
        boundaries=boundaries,
        power_transmission=float(power_T),
    )


def single_layer_reference(
    tissue_eps_r: float,
    tissue_sigma: float,
    freq_hz: float,
    theta_inc: float = 0.0,
    pol: str = "TE",
    *,
    n_z: int = 1200,
    depth_max: float | None = None,
) -> DepthProfile:
    """Half-space reference: air over a single semi-infinite tissue.

    Lets us compare the multilayer internal field against the homogeneous
    half-space that the paper's depth-weight approximation assumes.
    """
    stack = [
        Layer("air", 1.0, 0.0, np.inf, TISSUE_DENSITY["air"]),
        Layer("tissue", tissue_eps_r, tissue_sigma, np.inf, TISSUE_DENSITY["muscle"]),
    ]
    return solve_layered(stack, freq_hz, theta_inc, pol, n_z=n_z, depth_max=depth_max)
