"""S2 / S3 scene constructors for the v4 PoC.

S2 (body-shadowed LOS, attenuated by wall): the BS-to-phone direct path is
present but heavily attenuated; the body of the user (the phone holder)
provides a body-mediated cascaded contribution via the per-triangle
Kirchhoff render. This is a refinement of the S1 PoC (which used
visibility-only) that exercises the v4 spine eq. (hbody) for the first time.

S3 (true NLOS, body-as-RIS rescue): the BS-to-phone direct path is
extinguished (wall blocks); the only path to the phone goes THROUGH the
body's reflective surface. Pose-tuning the body becomes the only knob.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .kirchhoff import BSPathDict, Body, C0


@dataclass
class BSArray:
    """Uniform rectangular planar array."""

    n_x: int = 8
    n_y: int = 8
    spacing: float = None  # m, default lambda/2 at f_c
    center: np.ndarray = None  # (3,) world position of array centroid
    normal: np.ndarray = None  # (3,) panel-normal direction (boresight)
    f_c: float = 28e9

    def __post_init__(self):
        wavelength = C0 / self.f_c
        if self.spacing is None:
            self.spacing = wavelength / 2.0
        if self.center is None:
            self.center = np.array([0.0, 0.0, 8.0])
        if self.normal is None:
            self.normal = np.array([1.0, 0.0, 0.0])
        # Build per-element world positions in the panel plane (orthogonal to
        # `normal`). We use a simple right-handed basis (e1 along world-y, e2
        # along world-z) when normal is along x, else use Gram-Schmidt.
        n = self.normal / np.linalg.norm(self.normal)
        # Build two unit vectors perpendicular to n.
        # Pick a reference up = world z; if collinear, use world y.
        up = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(up, n)) > 0.99:
            up = np.array([0.0, 1.0, 0.0])
        e1 = up - np.dot(up, n) * n
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        # Element grid in (i, j) -> position
        offsets_x = (np.arange(self.n_x) - (self.n_x - 1) / 2) * self.spacing
        offsets_y = (np.arange(self.n_y) - (self.n_y - 1) / 2) * self.spacing
        self.positions = np.array(
            [self.center + ox * e1 + oy * e2 for oy in offsets_y for ox in offsets_x]
        )  # (M, 3) flattened in row-major
        self.M = self.n_x * self.n_y
        self.boresight = n


def los_path_dict(bs: BSArray, r_target: np.ndarray) -> BSPathDict:
    """Build the LOS path dictionary at r_target (body centroid or phone).

    One path per BS element, k_hat from element to target, amp = (1/r) exp(i k r)
    times the per-element steering phase exp(-i k k_hat . r_j). The plane-wave
    representation at r_target uses phase exp(-i k0 k_hat . r), so the
    per-element amplitude reference is the panel centroid.
    """
    k0 = 2 * np.pi * bs.f_c / C0
    M = bs.M
    d = r_target[None, :] - bs.positions  # (M, 3)
    r = np.linalg.norm(d, axis=1)  # (M,)
    k_hat = d / np.maximum(r[:, None], 1e-9)
    # Vertical polarization (z-axis). We could refine to per-element polarization
    # but this is fine for the PoC.
    psi_v = np.array([0.0, 0.0, 1.0], dtype=np.complex128)
    psi = np.tile(psi_v[None, :], (M, 1))
    # amp absorbs free-space spreading (lambda/4pi/r) and the carrier phase
    # exp(i k0 r). The lambda/4pi factor converts radiated W to V/m^2-style
    # field amplitude using effective aperture; this is the standard Friis
    # convention for per-element link budget.
    wavelength = C0 / bs.f_c
    amp = (wavelength / (4 * np.pi)) * np.exp(1j * k0 * r) / np.maximum(r, 1e-9)
    return BSPathDict(j_idx=np.arange(M), k_hat=k_hat, psi=psi, amp=amp)


def los_h_at_phone(bs: BSArray, r_phone: np.ndarray, scene_loss_db: float = 0.0) -> np.ndarray:
    """Direct LOS channel coefficient h_LOS[j] at r_phone.

    For a vertical-polarized phone antenna and isotropic BS elements, this is
    the per-element Green function (1/r) exp(i k0 r), with the panel-side
    scene loss factored in.
    """
    k0 = 2 * np.pi * bs.f_c / C0
    wavelength = C0 / bs.f_c
    d = r_phone[None, :] - bs.positions  # (M, 3)
    r = np.linalg.norm(d, axis=1)
    h = (wavelength / (4 * np.pi)) * np.exp(1j * k0 * r) / np.maximum(r, 1e-9)
    h *= 10 ** (-scene_loss_db / 20.0)
    return h
