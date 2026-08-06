"""Antenna array geometry and steering vectors.

AntennaArray is a frozen dataclass holding element positions in world
coordinates. The upa() factory builds a Uniform Planar Array. Steering
vectors encode per-element phase advances for a given direction of arrival.

Design doc: sections A1, B1, B2, B4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.constants import C_0


@dataclass(frozen=True)
class AntennaArray:
    """Planar antenna array with M elements at known positions.

    Attributes
    ----------
    element_positions : (M, 3) element positions in world coordinates [m].
    element_pattern : "isotropic" or "patch". Patch uses cos^q(theta) where
        theta is the angle from broadside, giving a realistic directional element.
    broadside : (3,) array normal direction, needed for patch pattern evaluation.
    reference_position : (3,) phase center / array center [m].
    """

    element_positions: np.ndarray = field(repr=False)
    element_pattern: str = "isotropic"
    broadside: np.ndarray = field(repr=False, default=None)
    reference_position: np.ndarray = field(repr=False, default=None)

    def __post_init__(self) -> None:
        if self.element_positions.ndim != 2 or self.element_positions.shape[1] != 3:
            raise ValueError(f"element_positions must be (M, 3), got {self.element_positions.shape}")
        if self.reference_position is None:
            object.__setattr__(
                self,
                "reference_position",
                self.element_positions.mean(axis=0),
            )
        else:
            ref = np.asarray(self.reference_position, dtype=np.float64)
            if ref.shape != (3,):
                raise ValueError(f"reference_position must be (3,), got {ref.shape}")
            object.__setattr__(self, "reference_position", ref)
        if self.broadside is not None:
            b = np.asarray(self.broadside, dtype=np.float64)
            b = b / np.linalg.norm(b)
            object.__setattr__(self, "broadside", b)

    @property
    def n_elements(self) -> int:
        return self.element_positions.shape[0]

    @classmethod
    def upa(
        cls,
        n_h: int,
        n_v: int,
        d_h: float,
        d_v: float,
        center: np.ndarray,
        broadside: np.ndarray,
        element_pattern: str = "isotropic",
    ) -> AntennaArray:
        """Uniform Planar Array.

        Parameters
        ----------
        n_h, n_v : horizontal and vertical element counts.
        d_h, d_v : horizontal and vertical element spacings [m].
        center : (3,) array center position in world coordinates [m].
        broadside : (3,) unit vector for array normal (main beam direction).
        element_pattern : "isotropic" or "patch". Default "patch".
        """
        center = np.asarray(center, dtype=np.float64)
        broadside = np.asarray(broadside, dtype=np.float64)
        broadside = broadside / np.linalg.norm(broadside)

        # Two axes perpendicular to broadside
        abs_b = np.abs(broadside)
        ref = np.zeros(3)
        ref[np.argmin(abs_b)] = 1.0
        e_h = np.cross(broadside, ref)
        e_h /= np.linalg.norm(e_h)
        e_v = np.cross(broadside, e_h)

        # Grid indices centered at zero
        h_idx = np.arange(n_h) - (n_h - 1) / 2.0
        v_idx = np.arange(n_v) - (n_v - 1) / 2.0
        hh, vv = np.meshgrid(h_idx, v_idx)  # (n_v, n_h) each

        local_h = hh.ravel() * d_h  # (M,)
        local_v = vv.ravel() * d_v  # (M,)

        positions = center + local_h[:, None] * e_h + local_v[:, None] * e_v

        return cls(
            element_positions=positions,
            element_pattern=element_pattern,
            broadside=broadside,
            reference_position=center,
        )

    def element_gain(self, k_hat: np.ndarray) -> np.ndarray:
        """Per-element amplitude gain for a direction or set of directions.

        For "patch": sqrt(D) * max(cos(theta), 0)^q with q = 1.5, where theta
        is the angle off broadside. The power pattern is D cos^3(theta) with
        D = 2(2q + 1) = 8 (9.0 dBi peak), the directivity that makes the
        pattern radiate exactly the input power over the front hemisphere.
        Comparable to the 8 dBi elements 3GPP TR 38.901 assumes for mmWave
        panels. (Before 2026-07 the amplitude was unnormalized, peak 0 dBi,
        under-reporting absolute exposure by ~9 dB.)

        Parameters
        ----------
        k_hat : (3,) or (N, 3) unit direction(s).

        Returns
        -------
        gain : scalar or (N,) real amplitude gain (multiply into psi).
        """
        if self.element_pattern == "isotropic" or self.broadside is None:
            if k_hat.ndim == 1:
                return np.float64(1.0)
            return np.ones(k_hat.shape[0])
        # Patch: energy-normalized cos^q amplitude with backside suppression
        q = 1.5
        amp = np.sqrt(2.0 * (2.0 * q + 1.0))
        cos_theta = k_hat @ self.broadside
        return amp * np.maximum(cos_theta, 0.0) ** q

    def steering_vector(self, k_hat: np.ndarray, freq_hz: float) -> np.ndarray:
        """Transmit steering vector for a single direction.

        Parameters
        ----------
        k_hat : (3,) unit direction of arrival at the body.
        freq_hz : frequency [Hz].

        Returns
        -------
        a : (M,) complex steering vector, including element gain.
        """
        k0 = 2 * np.pi * freq_hz / C_0
        offsets = self.element_positions - self.reference_position
        return self.element_gain(k_hat) * np.exp(1j * k0 * (offsets @ k_hat))

    def steering_matrix(self, k_hat: np.ndarray, freq_hz: float) -> np.ndarray:
        """Transmit steering matrix for N directions.

        Parameters
        ----------
        k_hat : (N, 3) unit directions of arrival.
        freq_hz : frequency [Hz].

        Returns
        -------
        A : (N, M) complex steering matrix. Row n is the steering vector
            for direction k_hat[n].
        """
        k0 = 2 * np.pi * freq_hz / C_0
        offsets = self.element_positions - self.reference_position
        gain = self.element_gain(k_hat)
        return gain[:, None] * np.exp(1j * k0 * (k_hat @ offsets.T))

    def __repr__(self) -> str:
        return f"AntennaArray(M={self.n_elements}, pattern={self.element_pattern!r})"
