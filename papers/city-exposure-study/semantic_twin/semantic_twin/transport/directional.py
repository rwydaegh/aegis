"""Exact directional transfer measures exchanged with the body adapter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _directions(value: np.ndarray, name: str) -> np.ndarray:
    directions = np.asarray(value, dtype=np.float64)
    if directions.ndim != 2 or directions.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3), got {directions.shape}")
    if not np.all(np.isfinite(directions)):
        raise ValueError(f"{name} must be finite")
    norms = np.linalg.norm(directions, axis=1)
    if np.any(norms <= 0.0):
        raise ValueError(f"{name} rows must have positive norms")
    if not np.allclose(norms, 1.0, rtol=1.0e-7, atol=1.0e-7):
        raise ValueError(f"{name} rows must be unit directions")
    return directions


def _masses(value: np.ndarray, count: int, name: str) -> np.ndarray:
    masses = np.asarray(value, dtype=np.float64)
    if masses.ndim != 1 or masses.shape != (count,):
        raise ValueError(f"{name} must have shape ({count},), got {masses.shape}")
    if not np.all(np.isfinite(masses)):
        raise ValueError(f"{name} must be finite")
    if np.any(masses < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    return masses


@dataclass(frozen=True)
class DirectionalMeasure:
    """Dimensionless transfer split into exact atoms and diffuse cells.

    Directions are physical body arrival directions in the current world/body
    frame. Masses are normalized transfer factors, not power densities. The
    transport-side :class:`~semantic_twin.transport.next_event.NextEventField`
    performs the one raw-transfer normalization before constructing this object.
    A body adapter supplies only the paired free-space incident density when
    converting it to propagation paths.
    """

    atom_k_hat: np.ndarray
    atom_mass: np.ndarray
    diffuse_k_hat: np.ndarray
    diffuse_mass: np.ndarray
    reference_id: str | None = None

    def __post_init__(self) -> None:
        atom_k_hat = _directions(self.atom_k_hat, "atom_k_hat")
        diffuse_k_hat = _directions(self.diffuse_k_hat, "diffuse_k_hat")
        atom_mass = _masses(self.atom_mass, atom_k_hat.shape[0], "atom_mass")
        diffuse_mass = _masses(self.diffuse_mass, diffuse_k_hat.shape[0], "diffuse_mass")
        object.__setattr__(self, "atom_k_hat", atom_k_hat)
        object.__setattr__(self, "atom_mass", atom_mass)
        object.__setattr__(self, "diffuse_k_hat", diffuse_k_hat)
        object.__setattr__(self, "diffuse_mass", diffuse_mass)

    @classmethod
    def empty(cls) -> "DirectionalMeasure":
        """Return an empty valid measure."""
        directions = np.empty((0, 3), dtype=np.float64)
        return cls(directions, np.empty(0, dtype=np.float64), directions, np.empty(0, dtype=np.float64))

    @property
    def atomic_total(self) -> float:
        """Total dimensionless transfer in exact atoms."""
        return float(np.sum(self.atom_mass, dtype=np.float64))

    @property
    def diffuse_total(self) -> float:
        """Total dimensionless transfer in diffuse grid cells."""
        return float(np.sum(self.diffuse_mass, dtype=np.float64))

    @property
    def total(self) -> float:
        """Total dimensionless transfer in both components."""
        return self.atomic_total + self.diffuse_total

    @property
    def total_transfer(self) -> float:
        """Total dimensionless transfer factor."""
        return self.total

    @property
    def n_atoms(self) -> int:
        return int(self.atom_mass.size)

    @property
    def n_diffuse(self) -> int:
        return int(self.diffuse_mass.size)

    def scaled_paths_data(self, reference_s0_w_m2: float) -> tuple[np.ndarray, np.ndarray]:
        """Return concatenated physical directions and incident powers."""
        if not np.isfinite(reference_s0_w_m2) or reference_s0_w_m2 < 0.0:
            raise ValueError("reference_s0_w_m2 must be nonnegative and finite")
        directions = np.concatenate((self.atom_k_hat, self.diffuse_k_hat), axis=0)
        masses = np.concatenate((self.atom_mass, self.diffuse_mass), axis=0)
        powers = masses * float(reference_s0_w_m2)
        return directions, powers
