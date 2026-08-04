"""Physical optics on brickwork, with the disorder carried in closed form.

Two jobs. First, a Kirchhoff phase-screen model of the same unit cell that
:mod:`~.rcwa` solves rigorously, so the two can be compared and the
error of the cheap method can be stated rather than assumed. Second, and this is
the part a rigorous periodic solver cannot do at all, the ensemble average over
unit-to-unit disorder.

The disorder model. A wall is a lattice of tiles, one brick face plus its share
of the surrounding joint. Tile ``j`` sits at lattice site ``r_j`` displaced
laterally by ``eps_j``, and its brick face sits proud of or behind the wall
plane by ``delta_j``. Both are zero mean and independent between tiles. Writing
``T_j`` for the tile's aperture transform, the scattered spectrum is

    U(dk) = sum_j T_j(dk) exp(-i dk . (r_j + eps_j))

whose second moment separates exactly into a coherent and an incoherent part:

    <|U|^2> = |Tbar|^2 |chi_t|^2 |sum_j exp(-i dk.r_j)|^2
              + N [ var(T) + |Tbar|^2 (1 - |chi_t|^2) ]

The first term is a comb, because the lattice sum is a comb. The second is
smooth, because it has lost the lattice. ``chi_t`` and ``chi_p`` are the
characteristic functions of the lateral and piston disorder, and for Gaussian
offsets ``|chi_p|^2 = exp(-(k0 sigma (cos th_i + cos th_s))^2)``, which at the
specular direction is exactly the Ament factor that the effective-roughness
literature fits. Here it is derived from a declared manufacturing tolerance
instead, and it arrives with the residual comb still attached.

Validity. The phase-screen approximation replaces the true surface field by the
incident field times a local plane-interface reflection coefficient and a piston
phase. It needs local radii of curvature large against the wavelength and no
multiple scattering inside the joint groove, and it ignores edge diffraction at
the arris of every brick. A recessed joint is a sharp-edged groove roughly one
wavelength wide at 28 GHz, so none of those conditions holds cleanly, and the
error is measured against RCWA rather than argued about.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..roughness import wavelength_m
from .wall import MasonryWall

TWO_PI = 2.0 * math.pi


def fresnel_reflection(permittivity: complex, theta_deg: float, polarisation: str) -> complex:
    """Plane-interface reflection coefficient from vacuum into a half space.

    Uses the ``exp(-i omega t)`` convention, so a lossy material carries a
    positive imaginary permittivity.
    """
    theta = math.radians(theta_deg)
    cos_i = math.cos(theta)
    sin_squared = math.sin(theta) ** 2
    root = np.sqrt(complex(permittivity) - sin_squared)
    if root.real < 0.0:
        root = -root
    if polarisation.lower() in ("te", "s"):
        return complex((cos_i - root) / (cos_i + root))
    if polarisation.lower() in ("tm", "p"):
        return complex((permittivity * cos_i - root) / (permittivity * cos_i + root))
    raise ValueError(f"unknown polarisation '{polarisation}', expected 'te' or 'tm'")


def _sinc(values: np.ndarray) -> np.ndarray:
    return np.sinc(values / math.pi)


def _rectangle_transform(
    delta_kx: np.ndarray,
    delta_ky: np.ndarray,
    rectangle: tuple[float, float, float, float],
) -> np.ndarray:
    """``int exp(-i dk . r) dS`` over an axis aligned rectangle, in square metres."""
    x0, y0, width, height = rectangle
    phase = np.exp(-1j * (delta_kx * (x0 + 0.5 * width) + delta_ky * (y0 + 0.5 * height)))
    return width * height * _sinc(0.5 * delta_kx * width) * _sinc(0.5 * delta_ky * height) * phase


@dataclass(frozen=True)
class DisorderModel:
    """Unit-to-unit scatter of a laid wall.

    ``piston_sigma_m`` is the standard deviation of the face-plane offset of one
    laid unit, the quantity that survives as an effective RMS height. ``lateral``
    is the standard deviation of a unit's in-plane position about its nominal
    lattice site. The two act on completely different parts of the answer: the
    piston term attenuates every order including the specular one, whereas the
    lateral term leaves the specular order untouched and kills the high orders
    first, because its attenuation goes as the order's transverse momentum.
    """

    piston_sigma_m: float = 0.0
    lateral_x_sigma_m: float = 0.0
    lateral_y_sigma_m: float = 0.0
    source: str = ""

    def piston_coherence(self, psi: np.ndarray) -> np.ndarray:
        """``|chi_p|^2`` at the given out-of-plane momentum transfer."""
        return np.exp(-((np.asarray(psi) * self.piston_sigma_m) ** 2))

    def lateral_coherence(self, delta_kx: np.ndarray, delta_ky: np.ndarray) -> np.ndarray:
        """``|chi_t|^2`` at the given transverse momentum transfer."""
        exponent = (np.asarray(delta_kx) * self.lateral_x_sigma_m) ** 2 + (
            np.asarray(delta_ky) * self.lateral_y_sigma_m
        ) ** 2
        return np.exp(-exponent)


@dataclass(frozen=True)
class KirchhoffSolution:
    """Coherent orders and the incoherent budget that disorder moved out of them."""

    m: np.ndarray
    n: np.ndarray
    kx: np.ndarray
    ky: np.ndarray
    kz: np.ndarray
    propagating: np.ndarray
    efficiency: np.ndarray
    amplitude: np.ndarray
    ordered_efficiency: np.ndarray
    incoherent_fraction: float
    frequency_hz: float
    theta_deg: float
    phi_deg: float
    polarisation: str

    @property
    def total_coherent(self) -> float:
        return float(np.sum(self.efficiency))

    @property
    def specular_efficiency(self) -> float:
        return float(self.efficiency[self.order_index(0, 0)])

    @property
    def coherent_diffuse(self) -> float:
        """Power in the comb, excluding the specular order."""
        return self.total_coherent - self.specular_efficiency

    def order_index(self, m: int, n: int) -> int:
        hit = np.nonzero((self.m == m) & (self.n == n))[0]
        if hit.size == 0:
            raise KeyError(f"order ({m}, {n}) is outside the retained harmonics")
        return int(hit[0])


def _order_geometry(
    wall: MasonryWall,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float,
    harmonics: tuple[int, int],
) -> dict[str, np.ndarray]:
    lam = float(wavelength_m(frequency_hz))
    k0 = TWO_PI / lam
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    kx_inc = k0 * math.sin(theta) * math.cos(phi)
    ky_inc = k0 * math.sin(theta) * math.sin(phi)
    m_max, n_max = harmonics
    m_span = np.arange(-m_max, m_max + 1)
    n_span = np.arange(-n_max, n_max + 1)
    m_grid, n_grid = np.meshgrid(m_span, n_span, indexing="ij")
    m_index = m_grid.ravel()
    n_index = n_grid.ravel()
    delta_kx = m_index * TWO_PI / wall.cell_x_m
    delta_ky = n_index * TWO_PI / wall.cell_y_m
    kx = kx_inc + delta_kx
    ky = ky_inc + delta_ky
    kz_squared = k0**2 - kx**2 - ky**2
    kz = np.sqrt(np.asarray(kz_squared, dtype=np.complex128))
    return {
        "k0": np.array(k0),
        "m": m_index,
        "n": n_index,
        "delta_kx": delta_kx,
        "delta_ky": delta_ky,
        "kx": kx,
        "ky": ky,
        "kz": kz,
        "propagating": kz_squared > 1e-9,
        "cos_i": np.array(math.cos(theta)),
    }


def _aperture_transforms(
    wall: MasonryWall,
    delta_kx: np.ndarray,
    delta_ky: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Geometry-only transforms of the cell, in square metres.

    Returns the whole-cell rectangle transform, the coherent sum of the brick
    face transforms, and the incoherent sum of their squared magnitudes. The
    joint grid is never rasterised: it is the complement of the brick faces
    inside the cell, so a uniform mortar-valued background plus a per-brick
    correction reproduces it exactly and analytically.
    """
    cell_transform = _rectangle_transform(delta_kx, delta_ky, (0.0, 0.0, wall.cell_x_m, wall.cell_y_m))
    shape = np.broadcast(delta_kx, delta_ky).shape
    coherent = np.zeros(shape, dtype=np.complex128)
    incoherent = np.zeros(shape, dtype=np.float64)
    for rectangle in wall.unit_rectangles():
        patch = _rectangle_transform(delta_kx, delta_ky, rectangle)
        coherent = coherent + patch
        incoherent = incoherent + np.abs(patch) ** 2
    return cell_transform, coherent, incoherent


def _face_weights(
    *,
    brick_reflection: complex,
    mortar_reflection: complex,
    piston_coherence: np.ndarray,
    lateral_coherence: np.ndarray,
    recess_phase: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean and variance of the per-brick complex weight under disorder.

    A brick carries reflection ``a`` at a random face offset and sits on a fixed
    mortar background of ``b = R_m exp(-i psi d)``, so the object that scatters
    is the contrast ``c = a exp(i psi delta) - b`` placed at a randomly displaced
    lattice site. Writing ``p`` and ``t`` for the piston and lateral coherence
    amplitudes, the two moments are

        <c exp(-i dk . eps)> = (a p - b) t
        var                  = (1 - t^2)(|a|^2 + |b|^2 - 2 p Re(a b*)) + t^2 (1 - p^2) |a|^2

    which reduce to ``(1 - p^2)|a|^2`` for lateral order and to
    ``(1 - t^2)|a - b|^2`` for a flush face plane, as they must.
    """
    a = complex(brick_reflection)
    b = mortar_reflection * recess_phase
    p = np.asarray(piston_coherence, dtype=np.float64)
    t = np.sqrt(np.clip(np.asarray(lateral_coherence, dtype=np.float64), 0.0, 1.0))
    mean_weight = (a * p - b) * t
    cross = np.real(a * np.conj(b))
    variance = (1.0 - t**2) * (abs(a) ** 2 + np.abs(b) ** 2 - 2.0 * p * cross) + t**2 * (1.0 - p**2) * abs(a) ** 2
    return mean_weight, np.maximum(variance, 0.0), b


def kirchhoff_orders(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    harmonics: tuple[int, int] = (40, 20),
    disorder: DisorderModel | None = None,
) -> KirchhoffSolution:
    """Coherent Floquet orders of a disordered brick wall.

    ``ordered_efficiency`` is the same calculation with the disorder switched
    off, so the ratio of the two is exactly how much of the comb the tolerance
    class destroyed.
    """
    disorder = disorder or DisorderModel()
    geometry = _order_geometry(wall, frequency_hz, theta_deg, phi_deg, harmonics)
    k0 = float(geometry["k0"])
    cos_i = float(geometry["cos_i"])
    kz = geometry["kz"]
    psi = k0 * cos_i + np.real(kz)
    brick_reflection = fresnel_reflection(wall.brick_permittivity, theta_deg, polarisation)
    mortar_reflection = fresnel_reflection(wall.mortar_permittivity, theta_deg, polarisation)
    recess_phase = np.exp(-1j * psi * wall.joint.recess_m)
    piston_amplitude = np.exp(-0.5 * (psi * disorder.piston_sigma_m) ** 2)
    lateral = disorder.lateral_coherence(geometry["delta_kx"], geometry["delta_ky"])
    cell_transform, brick_coherent, _ = _aperture_transforms(wall, geometry["delta_kx"], geometry["delta_ky"])
    cell_area = wall.cell_x_m * wall.cell_y_m

    def efficiencies(piston: np.ndarray, lateral_power: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        mean_weight, _, background = _face_weights(
            brick_reflection=brick_reflection,
            mortar_reflection=mortar_reflection,
            piston_coherence=piston,
            lateral_coherence=lateral_power,
            recess_phase=recess_phase,
        )
        amplitude = (background * cell_transform + mean_weight * brick_coherent) / cell_area
        power = np.abs(amplitude) ** 2 * np.real(kz) / (k0 * cos_i)
        return np.where(geometry["propagating"], power, 0.0), amplitude

    disordered, amplitude = efficiencies(piston_amplitude, lateral)
    ordered, _ = efficiencies(np.ones_like(piston_amplitude), np.ones_like(lateral))

    incoherent = incoherent_power_fraction(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        phi_deg=phi_deg,
        polarisation=polarisation,
        disorder=disorder,
    )
    return KirchhoffSolution(
        m=geometry["m"],
        n=geometry["n"],
        kx=geometry["kx"],
        ky=geometry["ky"],
        kz=kz,
        propagating=geometry["propagating"],
        efficiency=disordered,
        amplitude=amplitude,
        ordered_efficiency=ordered,
        incoherent_fraction=incoherent,
        frequency_hz=float(frequency_hz),
        theta_deg=float(theta_deg),
        phi_deg=float(phi_deg),
        polarisation=polarisation,
    )


def hemisphere_grid(samples: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Regular grid of direction cosines over the upper hemisphere.

    Returns ``(u, v, inside)``. A direction-cosine grid is used rather than a
    grid in angle because the diffraction orders are equally spaced in direction
    cosine and not in angle, so this is the frame where a comb looks like a comb.
    """
    axis = np.linspace(-1.0, 1.0, samples)
    u, v = np.meshgrid(axis, axis, indexing="ij")
    return u, v, (u**2 + v**2) < 1.0


def incoherent_differential(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    disorder: DisorderModel,
    direction_cosine_u: np.ndarray,
    direction_cosine_v: np.ndarray,
) -> np.ndarray:
    """Incoherent scattered power per unit solid angle, dimensionless per steradian.

    This is the smooth part that disorder moved out of the comb. It is not a
    Lambertian pedestal and it is not a directive lobe with a fitted exponent:
    its angular shape is the transform of a single brick face, whose width is
    set by the unit dimensions and therefore by the same construction standard
    that set the lattice.
    """
    lam = float(wavelength_m(frequency_hz))
    k0 = TWO_PI / lam
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    cos_i = math.cos(theta)
    u = np.asarray(direction_cosine_u, dtype=np.float64)
    v = np.asarray(direction_cosine_v, dtype=np.float64)
    radial = u**2 + v**2
    cos_s = np.sqrt(np.clip(1.0 - radial, 0.0, 1.0))
    delta_kx = k0 * (u - math.sin(theta) * math.cos(phi))
    delta_ky = k0 * (v - math.sin(theta) * math.sin(phi))
    psi = k0 * (cos_i + cos_s)
    brick_reflection = fresnel_reflection(wall.brick_permittivity, theta_deg, polarisation)
    mortar_reflection = fresnel_reflection(wall.mortar_permittivity, theta_deg, polarisation)
    piston_amplitude = np.exp(-0.5 * (psi * disorder.piston_sigma_m) ** 2)
    _, _, brick_power = _aperture_transforms(wall, delta_kx, delta_ky)
    _, variance, _ = _face_weights(
        brick_reflection=brick_reflection,
        mortar_reflection=mortar_reflection,
        piston_coherence=piston_amplitude,
        lateral_coherence=disorder.lateral_coherence(delta_kx, delta_ky),
        recess_phase=np.exp(-1j * psi * wall.joint.recess_m),
    )
    spectrum = variance * brick_power
    cell_area = wall.cell_x_m * wall.cell_y_m
    density = k0**2 * cos_s**2 * spectrum / (4.0 * math.pi**2 * cell_area * cos_i)
    return np.where(radial < 1.0, density, 0.0)


def incoherent_power_fraction(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    disorder: DisorderModel,
    samples: int = 361,
) -> float:
    """Hemisphere integral of :func:`incoherent_differential`.

    Integrated in direction cosines, where the solid angle element is
    ``du dv / cos(theta_s)``.
    """
    if disorder.piston_sigma_m <= 0.0 and disorder.lateral_x_sigma_m <= 0.0 and disorder.lateral_y_sigma_m <= 0.0:
        return 0.0
    u, v, inside = hemisphere_grid(samples)
    density = incoherent_differential(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        phi_deg=phi_deg,
        polarisation=polarisation,
        disorder=disorder,
        direction_cosine_u=u,
        direction_cosine_v=v,
    )
    cos_s = np.sqrt(np.clip(1.0 - u**2 - v**2, 1e-12, 1.0))
    cell = (2.0 / (samples - 1)) ** 2
    return float(np.sum(np.where(inside, density / cos_s, 0.0)) * cell)


def specular_retention(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    piston_sigma_m: float = 0.0,
) -> float:
    """Closed form share of the flat-wall specular power that a brick wall keeps.

    The elevation is a two-level height field: a fraction ``f`` of it is mortar
    sitting ``d`` behind the face, the rest is brick face scattered about the
    plane by the tolerance class. The specular amplitude is the area average of
    the two, so

        eta_spec / eta_flat = | (1 - f) exp(-psi^2 sigma^2 / 2) + f exp(-i psi d) |^2

    with ``psi = 2 k0 cos(theta)``. Everything in it comes from a construction
    document: ``f`` from the format and joint width, ``d`` from the pointing
    specification, ``sigma`` from the EN 771-1 range class.

    The second term is the one a Gaussian roughness model cannot produce. It is
    periodic in ``psi d`` rather than decaying, so the joint recess costs the
    wall nothing when the round trip through it is a whole wavelength and costs
    it the most when the round trip is half of one. This is checked against the
    full Kirchhoff solve rather than asserted.
    """
    k0 = TWO_PI / float(wavelength_m(frequency_hz))
    psi = 2.0 * k0 * math.cos(math.radians(theta_deg))
    mortar = wall.joint_area_fraction
    brick_term = (1.0 - mortar) * math.exp(-0.5 * (psi * piston_sigma_m) ** 2)
    mortar_term = mortar * np.exp(-1j * psi * wall.joint.recess_m)
    return float(abs(brick_term + mortar_term) ** 2)


def equivalent_rms_height_m(wall: MasonryWall, *, piston_sigma_m: float = 0.0) -> float:
    """The Gaussian RMS height that reproduces :func:`specular_retention` at small phase.

    Expanding the two-level form to second order in ``psi d`` and first order in
    ``psi sigma`` gives ``exp(-(psi s)^2)`` with

        s^2 = f (1 - f) d^2 + (1 - f) sigma^2

    so the effective roughness of brickwork is a joint recess weighted by the
    joint area fraction, plus the unit scatter weighted by the brick area
    fraction. Nothing in it is fitted.

    The equivalence holds only while ``2 k0 d cos(theta)`` stays below about two,
    which is ``d < lambda / (2 pi cos theta)``. Above that the recess term starts
    to oscillate and no RMS height describes it. Use
    :func:`gaussian_equivalence_limit_m` to test the case in hand.
    """
    mortar = wall.joint_area_fraction
    recess = abs(wall.joint.recess_m)
    return math.sqrt(mortar * (1.0 - mortar) * recess**2 + (1.0 - mortar) * piston_sigma_m**2)


def gaussian_equivalence_limit_m(frequency_hz: float, theta_deg: float) -> float:
    """Largest joint recess for which an equivalent RMS height still describes the wall."""
    lam = float(wavelength_m(frequency_hz))
    cosine = max(math.cos(math.radians(theta_deg)), 1e-6)
    return lam / (TWO_PI * cosine)


def phase_screen_recess_limit_m(joint_width_m: float) -> float:
    """Deepest joint recess at which this module was checked against RCWA.

    Measured rather than argued, and the controlling variable is not what it
    first appears. Comparing the phase screen against the Fourier modal method on
    the same masonry cells (``outputs/masonry_grating/rcwa.json`` and
    ``rcwa_spectrum.json``) over 7, 10, 15 and 28 GHz shows the error tracking
    the groove *aspect ratio*, depth over width, and not the depth in
    wavelengths. At an aspect of one half the specular order agrees within 11
    percent from 7 to 28 GHz, including where the recess is half a wavelength
    deep. At an aspect of one the specular order is 23 to 34 percent low and the
    diffuse is 1.8 times high on the one comparison run to convergence.

    The physical reading is that a groove is a waveguide stub. What decides
    whether the field reaches its floor is how deep it is relative to how wide it
    is, and a phase screen assumes the field always reaches the floor. So the
    limit is a fraction of the joint width, not a fraction of the wavelength.

    This bounds one of the two failure modes and the caller has to carry the
    other. At 28 GHz and 60 degrees incidence, an aspect of one half fails just
    as badly, 34 percent low on the specular, because the groove floor is
    shadowed over ``d tan(theta)`` and a phase screen has no shadowing. The same
    geometry at 10 GHz is fine, because there the joint is a third of a
    wavelength wide and the wave does not resolve the shadow. Use
    ``phase_screen_incidence_limit_deg`` alongside this.
    """
    if joint_width_m <= 0.0:
        raise ValueError("joint width must be positive")
    return 0.5 * joint_width_m


def phase_screen_incidence_limit_deg(joint_width_m: float, frequency_hz: float) -> float:
    """Largest incidence angle at which the phase screen was checked against RCWA.

    Grazing incidence shadows the joint groove, which a phase screen cannot
    represent, but the wave only responds to that shadow once it can resolve the
    joint. Two grazing cases were run, both at 60 degrees and both at an aspect
    of one half: 10 GHz, where a 10 mm joint is a third of a wavelength, agrees
    to 7 percent, and 28 GHz, where the same joint is nearly a whole wavelength,
    is 34 percent low. The boundary is bracketed by those two and has not been
    located, so this returns 60 degrees only where the joint is narrower than
    half a wavelength and 45 degrees otherwise, which puts every untested case on
    the conservative side.
    """
    if joint_width_m <= 0.0:
        raise ValueError("joint width must be positive")
    return 60.0 if joint_width_m < 0.5 * float(wavelength_m(frequency_hz)) else 45.0


def order_angular_width_deg(patch_size_m: float, frequency_hz: float, theta_deg: float) -> float:
    """Angular width a diffraction order has when the illuminated patch is finite.

    An order is a delta function only for an infinite wall. A patch ``W`` across
    gives every order a width of about ``lambda / W`` in direction cosine, which
    is what decides whether a receiver can resolve the comb at all.
    """
    lam = float(wavelength_m(frequency_hz))
    cos_theta = max(math.cos(math.radians(theta_deg)), 1e-6)
    return float(math.degrees(lam / (patch_size_m * cos_theta)))


@dataclass(frozen=True)
class BistaticMap:
    """Combined comb and pedestal on a direction-cosine grid, at a stated resolution."""

    direction_cosine_u: np.ndarray
    direction_cosine_v: np.ndarray
    coherent: np.ndarray
    incoherent: np.ndarray
    resolution_deg: float
    order_spacing_deg: float
    frequency_hz: float
    theta_deg: float

    @property
    def total(self) -> np.ndarray:
        return self.coherent + self.incoherent

    @property
    def coherent_share(self) -> float:
        total = float(np.sum(self.total))
        return float(np.sum(self.coherent)) / total if total > 0.0 else float("nan")

    def modulation_depth(self, *, exclude_specular_deg: float = 5.0, window_orders: float = 1.5) -> float:
        """Ripple of the return about its own smooth trend, in decibels.

        The question this exists to answer is local: does the pattern carry
        structure at the spacing of the diffraction orders, or does it not. The
        overall fall-off from specular towards the horizon is not that structure,
        so it is divided out by comparing the map against a copy of itself
        blurred over a window of ``window_orders`` order spacings. Zero means a
        featureless lobe. A clean resolved comb runs to tens of decibels.
        """
        from scipy.ndimage import gaussian_filter

        step = float(self.direction_cosine_u[1, 0] - self.direction_cosine_u[0, 0])
        blur = max(window_orders * math.radians(self.order_spacing_deg) / max(step, 1e-9), 1.0)
        total = self.total
        floor = 1e-12 * max(float(total.max()), 1e-30)
        smooth = gaussian_filter(total, blur, mode="nearest")
        inside = (self.direction_cosine_u**2 + self.direction_cosine_v**2) < 0.9
        specular_u = math.sin(math.radians(self.theta_deg))
        separation = np.degrees(np.hypot(self.direction_cosine_u - specular_u, self.direction_cosine_v))
        region = inside & (separation > exclude_specular_deg) & (smooth > floor) & (total > floor)
        if np.count_nonzero(region) < 64:
            return float("nan")
        ratio = np.log10(total[region] / smooth[region])
        return float(10.0 * (np.percentile(ratio, 90.0) - np.percentile(ratio, 10.0)))


def bistatic_map(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    disorder: DisorderModel | None = None,
    patch_size_m: float = 1.0,
    receiver_resolution_deg: float = 0.0,
    samples: int = 401,
    harmonics: tuple[int, int] = (40, 20),
) -> BistaticMap:
    """Render the full bistatic response the way an instrument would see it.

    Every coherent order is a delta function on an infinite wall, so it is laid
    onto the grid as a Gaussian whose width is the larger of the finite-patch
    width and the receiver beam. The incoherent pedestal is evaluated directly.
    Comparing the two on one grid is what turns the comb-or-lobe question into a
    number. The receiver beam is applied to both parts, because an instrument
    integrates over its beam whatever it is looking at.
    """
    disorder = disorder or DisorderModel()
    solution = kirchhoff_orders(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        phi_deg=phi_deg,
        polarisation=polarisation,
        harmonics=harmonics,
        disorder=disorder,
    )
    lam = float(wavelength_m(frequency_hz))
    k0 = TWO_PI / lam
    u, v, inside = hemisphere_grid(samples)
    patch_width = lam / patch_size_m
    beam_width = math.radians(receiver_resolution_deg)
    width = max(patch_width, beam_width, 2.0 / (samples - 1))

    coherent = np.zeros_like(u)
    keep = solution.propagating & (solution.efficiency > 0.0)
    order_u = solution.kx[keep] / k0
    order_v = solution.ky[keep] / k0
    weights = solution.efficiency[keep]
    norm = 1.0 / (TWO_PI * width**2)
    for centre_u, centre_v, weight in zip(order_u, order_v, weights, strict=True):
        squared = (u - centre_u) ** 2 + (v - centre_v) ** 2
        coherent += weight * norm * np.exp(-0.5 * squared / width**2)

    incoherent = incoherent_differential(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        phi_deg=phi_deg,
        polarisation=polarisation,
        disorder=disorder,
        direction_cosine_u=u,
        direction_cosine_v=v,
    )
    cos_s = np.sqrt(np.clip(1.0 - u**2 - v**2, 1e-12, 1.0))
    pedestal = np.where(inside, incoherent / cos_s, 0.0)
    if beam_width > 0.0:
        # A receiver integrates over its beam whatever it is looking at, so the
        # smooth part has to be blurred by the same beam as the comb. Leaving it
        # sharp lets the single-unit diffraction fringes of the pedestal, whose
        # spacing is close to the order spacing because a brick nearly fills its
        # cell, masquerade as unresolved comb.
        from scipy.ndimage import gaussian_filter

        step = float(u[1, 0] - u[0, 0])
        pedestal = gaussian_filter(pedestal, beam_width / max(step, 1e-9), mode="nearest")
    separations = np.full(1, np.nan)
    if order_u.size > 1:
        directions = np.stack([order_u, order_v, np.sqrt(np.clip(1.0 - order_u**2 - order_v**2, 0.0, 1.0))], axis=-1)
        cosines = np.clip(directions @ directions.T, -1.0, 1.0)
        np.fill_diagonal(cosines, -1.0)
        separations = np.degrees(np.arccos(cosines.max(axis=1)))
    return BistaticMap(
        direction_cosine_u=u,
        direction_cosine_v=v,
        coherent=np.where(inside, coherent, 0.0),
        incoherent=np.where(inside, pedestal, 0.0),
        resolution_deg=float(math.degrees(width)),
        order_spacing_deg=float(np.median(separations)),
        frequency_hz=float(frequency_hz),
        theta_deg=float(theta_deg),
    )
