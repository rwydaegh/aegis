"""Diffraction order geometry for a doubly periodic facade.

A masonry facade is a two-dimensional lattice, not a random height field. The
scattered field of any periodic surface lives on a discrete set of directions
fixed by the lattice and the wavelength, and nothing about the material or the
relief depth can move them. This module computes that set.

Coordinates are wall local throughout the package. The facade occupies the plane
``z = 0`` with outward normal ``+z``, ``x`` runs horizontally along the wall and
``y`` runs vertically up it. An incidence direction is given by the polar angle
``theta`` from the outward normal and the azimuth ``phi`` measured from ``+x`` in
the wall plane, so a street level link between two points at pedestrian height is
``phi`` near zero or 180 degrees at large ``theta``, while a rooftop base station
illuminating the same facade is nearer ``phi = 90``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .mmwave import wavelength_m

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class Lattice:
    """A planar Bravais lattice given by its two primitive translation vectors.

    Bond patterns differ in their primitive cell, not only in their appearance.
    Stack bond is a plain rectangle. Running bond is a centred rectangle, whose
    reciprocal lattice carries half integer vertical orders paired with odd
    horizontal ones, so the two bonds are distinguishable in the far field.
    """

    a1: tuple[float, float]
    a2: tuple[float, float]
    name: str = "lattice"

    def __post_init__(self) -> None:
        if abs(self.area_m2) < 1e-12:
            raise ValueError("lattice vectors must be linearly independent")

    @property
    def area_m2(self) -> float:
        return float(self.a1[0] * self.a2[1] - self.a1[1] * self.a2[0])

    def reciprocal(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Primitive reciprocal vectors ``b1``, ``b2`` with ``b_i . a_j = 2 pi d_ij``."""
        det = self.area_m2
        (a1x, a1y), (a2x, a2y) = self.a1, self.a2
        b1 = (TWO_PI * a2y / det, -TWO_PI * a2x / det)
        b2 = (-TWO_PI * a1y / det, TWO_PI * a1x / det)
        return b1, b2


def rectangular_lattice(pitch_x_m: float, pitch_y_m: float, name: str = "rectangular") -> Lattice:
    return Lattice((pitch_x_m, 0.0), (0.0, pitch_y_m), name)


def centred_rectangular_lattice(pitch_x_m: float, pitch_y_m: float, name: str = "centred") -> Lattice:
    """Running bond: every course is offset by half a unit length from the one below."""
    return Lattice((pitch_x_m, 0.0), (0.5 * pitch_x_m, pitch_y_m), name)


def incident_wavevector(frequency_hz: float, theta_deg: float, phi_deg: float) -> np.ndarray:
    """Incident wavevector in wall coordinates, travelling towards the wall."""
    k0 = TWO_PI / float(wavelength_m(frequency_hz))
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    return k0 * np.array(
        [math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), -math.cos(theta)],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class DiffractionOrders:
    """Every Floquet order of one lattice at one frequency and incidence.

    ``propagating`` marks the orders that carry power away from the wall. The
    rest are evanescent and are retained because the count of them is what sets
    the convergence requirement of any rigorous solve.
    """

    m: np.ndarray
    n: np.ndarray
    kx: np.ndarray
    ky: np.ndarray
    kz: np.ndarray
    propagating: np.ndarray
    frequency_hz: float
    lattice: Lattice

    @property
    def count(self) -> int:
        return int(np.count_nonzero(self.propagating))

    @property
    def theta_deg(self) -> np.ndarray:
        k0 = TWO_PI / float(wavelength_m(self.frequency_hz))
        transverse = np.hypot(self.kx, self.ky) / k0
        return np.degrees(np.arcsin(np.clip(transverse, 0.0, 1.0)))

    @property
    def phi_deg(self) -> np.ndarray:
        return np.degrees(np.arctan2(self.ky, self.kx))

    def directions(self) -> np.ndarray:
        """Unit vectors of the propagating orders, pointing away from the wall."""
        k0 = TWO_PI / float(wavelength_m(self.frequency_hz))
        stack = np.stack([self.kx, self.ky, np.real(self.kz)], axis=-1) / k0
        return stack[self.propagating]

    def select(self, m: int, n: int) -> int:
        """Index of one order, by its integer labels."""
        hit = np.nonzero((self.m == m) & (self.n == n))[0]
        if hit.size == 0:
            raise KeyError(f"order ({m}, {n}) is outside the computed range")
        return int(hit[0])

    def angular_separations_deg(self) -> np.ndarray:
        """Angle between each propagating order and its nearest neighbour."""
        directions = self.directions()
        if directions.shape[0] < 2:
            return np.zeros(directions.shape[0])
        cosines = np.clip(directions @ directions.T, -1.0, 1.0)
        np.fill_diagonal(cosines, -1.0)
        return np.degrees(np.arccos(cosines.max(axis=1)))


def diffraction_orders(
    lattice: Lattice,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float,
    *,
    order_limit: int | None = None,
) -> DiffractionOrders:
    """All orders ``k_t = k_t_inc + m b1 + n b2`` out to a limit that covers the visible ones."""
    k0 = TWO_PI / float(wavelength_m(frequency_hz))
    k_inc = incident_wavevector(frequency_hz, theta_deg, phi_deg)
    b1, b2 = lattice.reciprocal()
    if order_limit is None:
        shortest = min(math.hypot(*b1), math.hypot(*b2))
        order_limit = int(math.ceil(2.0 * k0 / shortest)) + 2
    span = np.arange(-order_limit, order_limit + 1)
    m_grid, n_grid = np.meshgrid(span, span, indexing="ij")
    m_flat = m_grid.ravel()
    n_flat = n_grid.ravel()
    kx = k_inc[0] + m_flat * b1[0] + n_flat * b2[0]
    ky = k_inc[1] + m_flat * b1[1] + n_flat * b2[1]
    kz_squared = (k0**2 - kx**2 - ky**2).astype(np.complex128)
    kz = np.sqrt(kz_squared)
    propagating = kz_squared.real > 1e-12
    return DiffractionOrders(
        m=m_flat,
        n=n_flat,
        kx=kx,
        ky=ky,
        kz=kz,
        propagating=propagating,
        frequency_hz=float(frequency_hz),
        lattice=lattice,
    )


def grating_order_angles_deg(
    pitch_m: float,
    frequency_hz: float,
    incidence_deg: float,
) -> np.ndarray:
    """One dimensional grating equation ``sin(theta_m) = sin(theta_i) + m lam / d``.

    Kept separate from :func:`diffraction_orders` because it is the closed form
    that gets quoted, and because a reader checking the two dimensional result
    should be able to check it against three lines of trigonometry.
    """
    lam = float(wavelength_m(frequency_hz))
    sin_i = math.sin(math.radians(incidence_deg))
    limit = int(math.floor((1.0 + abs(sin_i)) * pitch_m / lam)) + 1
    orders = np.arange(-limit, limit + 1)
    sines = sin_i + orders * lam / pitch_m
    keep = np.abs(sines) <= 1.0
    return np.degrees(np.arcsin(sines[keep]))
