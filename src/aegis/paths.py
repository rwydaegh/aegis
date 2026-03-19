"""Propagation paths: the interface between ray tracers and dosimetry kernels.

PropagationPaths stores N paths arriving at the body. Each path has a direction
k_hat and a complex polarisation-amplitude vector psi. Incoherent kernels use
paths.power (derived from |psi|^2). Coherent kernels use psi directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.constants import Z_0


@dataclass(frozen=True)
class PropagationPaths:
    """Batch of N propagation paths arriving at the body.

    Attributes
    ----------
    k_hat : (N, 3) unit directions of arrival
    psi : (N, 3) complex polarisation-amplitude vectors (V/m / sqrt(W))
    element_index : (N,) originating antenna element index
    delay : (N,) propagation delay in seconds (optional metadata)
    is_los : (N,) line-of-sight flag (optional metadata)
    """

    k_hat: np.ndarray = field(repr=False)
    psi: np.ndarray = field(repr=False)
    element_index: np.ndarray = field(repr=False)
    delay: np.ndarray = field(repr=False)
    is_los: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        n = self.k_hat.shape[0]
        if self.k_hat.shape != (n, 3):
            raise ValueError(f"k_hat must be (N, 3), got {self.k_hat.shape}")
        if self.psi.shape != (n, 3):
            raise ValueError(f"psi must be (N, 3), got {self.psi.shape}")
        if self.element_index.shape != (n,):
            raise ValueError(f"element_index must be (N,), got {self.element_index.shape}")
        if self.delay.shape != (n,):
            raise ValueError(f"delay must be (N,), got {self.delay.shape}")
        if self.is_los.shape != (n,):
            raise ValueError(f"is_los must be (N,), got {self.is_los.shape}")
        if n > 0 and np.any(self.element_index < 0):
            raise ValueError("element_index must be non-negative")

    @property
    def n_paths(self) -> int:
        return self.k_hat.shape[0]

    @property
    def n_elements(self) -> int:
        return int(np.max(self.element_index)) + 1 if self.n_paths > 0 else 0

    @property
    def power(self) -> np.ndarray:
        """Per-path incident power density S_i = |psi_i|^2 / (2 * Z_0) [W/m^2].

        The factor 1/(2*Z_0) converts from |E|^2 to power density for a plane wave.
        """
        return np.sum(np.abs(self.psi) ** 2, axis=1) / (2 * Z_0)

    @classmethod
    def from_powers(
        cls,
        k_hat: np.ndarray,
        power: np.ndarray,
    ) -> PropagationPaths:
        """Construct from directions and scalar powers (incoherent-only use).

        Assigns an arbitrary perpendicular polarisation to each path and
        treats each path as from a separate virtual element.

        Parameters
        ----------
        k_hat : (N, 3) incident directions (will be normalised)
        power : (N,) incident power density per path [W/m^2]
        """
        k_hat = np.asarray(k_hat, dtype=np.float64)
        power = np.asarray(power, dtype=np.float64)

        if k_hat.ndim == 1:
            k_hat = k_hat[np.newaxis, :]
        if power.ndim == 0:
            power = power[np.newaxis]

        n = k_hat.shape[0]
        if power.shape != (n,):
            raise ValueError(f"power shape {power.shape} doesn't match k_hat ({n},)")

        # Normalise directions
        norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
        if n > 0 and np.any(norms[:, 0] <= 0):
            raise ValueError("k_hat rows must have positive norm (non-zero direction)")
        k_hat = k_hat / norms

        # Build arbitrary perpendicular polarisation for each k_hat
        # Pick the axis least aligned with k_hat as reference
        ref = np.zeros_like(k_hat)
        abs_k = np.abs(k_hat)
        min_axis = np.argmin(abs_k, axis=1)
        ref[np.arange(n), min_axis] = 1.0
        e_perp = np.cross(k_hat, ref)
        e_perp_norm = np.linalg.norm(e_perp, axis=1, keepdims=True)
        e_perp = e_perp / np.where(e_perp_norm > 0, e_perp_norm, 1.0)

        # psi such that |psi|^2 / (2*Z_0) = power
        amplitude = np.sqrt(2 * Z_0 * np.maximum(power, 0.0))
        psi = (amplitude[:, np.newaxis] * e_perp).astype(complex)

        return cls(
            k_hat=k_hat,
            psi=psi,
            element_index=np.arange(n, dtype=np.intp),
            delay=np.zeros(n, dtype=np.float64),
            is_los=np.ones(n, dtype=bool),
        )

    def __repr__(self) -> str:
        return f"PropagationPaths(n_paths={self.n_paths}, n_elements={self.n_elements})"
