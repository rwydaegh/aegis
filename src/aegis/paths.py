"""Propagation paths: the interface between ray tracers and dosimetry kernels.

PropagationPaths stores N paths arriving at the body. Each path has a direction
k_hat and a complex polarisation-amplitude vector psi. Incoherent kernels use
paths.power (derived from |psi|^2). Coherent kernels use psi directly.
"""

from __future__ import annotations

from collections.abc import Sequence
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

    def __len__(self) -> int:
        return self.n_paths

    @property
    def total_power(self) -> float:
        return float(np.sum(self.power))

    def subset(self, indices: np.ndarray | Sequence[int]) -> PropagationPaths:
        """Return paths restricted to the given index array (e.g. LOS-only)."""
        idx = np.asarray(indices, dtype=np.intp)
        return PropagationPaths(
            k_hat=self.k_hat[idx],
            psi=self.psi[idx],
            element_index=self.element_index[idx],
            delay=self.delay[idx],
            is_los=self.is_los[idx],
        )

    @property
    def los_paths(self) -> PropagationPaths:
        """Return only line-of-sight paths."""
        return self.subset(np.where(self.is_los)[0])

    @property
    def nlos_paths(self) -> PropagationPaths:
        """Return only non-line-of-sight paths."""
        return self.subset(np.where(~self.is_los)[0])

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

    @classmethod
    def from_spherical(
        cls,
        theta: np.ndarray,
        phi: np.ndarray,
        power: np.ndarray,
    ) -> PropagationPaths:
        """Construct from spherical arrival angles and scalar powers.

        Convenient for analytical scenarios (uniform illumination, sector
        beams, stochastic channel models) where paths are specified as
        (theta, phi) rather than Cartesian k_hat.

        Parameters
        ----------
        theta : (N,) zenith angle of arrival in radians (0 = +z)
        phi : (N,) azimuth angle of arrival in radians
        power : (N,) incident power density per path [W/m^2]
        """
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        if theta.ndim == 0:
            theta = theta[np.newaxis]
        if phi.ndim == 0:
            phi = phi[np.newaxis]

        k_hat = np.column_stack(
            [
                np.sin(theta) * np.cos(phi),
                np.sin(theta) * np.sin(phi),
                np.cos(theta),
            ]
        )
        return cls.from_powers(k_hat=k_hat, power=np.asarray(power))

    @classmethod
    def uniform_sphere(
        cls,
        n_paths: int,
        total_power: float = 1.0,
        seed: int | None = None,
    ) -> PropagationPaths:
        """Generate paths uniformly distributed over the sphere.

        Useful for worst-case analysis, Monte Carlo integration of the
        exposure integral, and testing. Each path carries equal power
        such that the total incident power density sums to ``total_power``.

        Parameters
        ----------
        n_paths : int
            Number of paths to generate.
        total_power : float
            Total incident power density [W/m^2], distributed equally.
        seed : int or None
            Random seed for reproducibility.
        """
        rng = np.random.default_rng(seed)
        # Uniform on sphere via Gaussian normalization
        raw = rng.standard_normal((n_paths, 3))
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        k_hat = raw / norms
        power = np.full(n_paths, total_power / n_paths)
        return cls.from_powers(k_hat=k_hat, power=power)

    @classmethod
    def concatenate(
        cls,
        paths_list: Sequence[PropagationPaths],
        *,
        reindex_elements: bool = True,
    ) -> PropagationPaths:
        """Concatenate multiple PropagationPaths into one.

        Parameters
        ----------
        paths_list : sequence of PropagationPaths
            Paths to concatenate. Empty entries are skipped.
        reindex_elements : bool
            If True (default), shift element_index so that each input's
            elements are disjoint. If False, keep element indices as-is
            (useful when paths already share a common antenna indexing).

        Returns
        -------
        PropagationPaths
            Combined paths with N = sum(N_i) total paths.
        """
        paths_list = [p for p in paths_list if p.n_paths > 0]
        if len(paths_list) == 0:
            empty = np.empty((0, 3), dtype=np.float64)
            empty_1d = np.empty(0, dtype=np.float64)
            return cls(
                k_hat=empty,
                psi=empty.astype(complex),
                element_index=np.empty(0, dtype=np.intp),
                delay=empty_1d,
                is_los=np.empty(0, dtype=bool),
            )
        if len(paths_list) == 1:
            return paths_list[0]

        k_hats = [p.k_hat for p in paths_list]
        psis = [p.psi for p in paths_list]
        delays = [p.delay for p in paths_list]
        is_loss = [p.is_los for p in paths_list]

        if reindex_elements:
            elem_indices = []
            offset = 0
            for p in paths_list:
                elem_indices.append(p.element_index + offset)
                offset += p.n_elements
        else:
            elem_indices = [p.element_index for p in paths_list]

        return cls(
            k_hat=np.concatenate(k_hats, axis=0),
            psi=np.concatenate(psis, axis=0),
            element_index=np.concatenate(elem_indices, axis=0),
            delay=np.concatenate(delays, axis=0),
            is_los=np.concatenate(is_loss, axis=0),
        )

    def __repr__(self) -> str:
        return f"PropagationPaths(n_paths={self.n_paths}, n_elements={self.n_elements})"
