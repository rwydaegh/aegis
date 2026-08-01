"""Probabilistic multi-view evidence accumulation on shared 3D surface elements."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import numpy as np


def categorical_information(probability: np.ndarray) -> np.ndarray:
    """Normalised information above a uniform categorical distribution."""
    probability = np.asarray(probability, dtype=np.float64)
    if probability.shape[-1] <= 1:
        return np.ones(probability.shape[:-1], dtype=np.float64)
    clipped = np.clip(probability, 1e-12, 1.0)
    entropy = -np.sum(clipped * np.log(clipped), axis=-1)
    return np.clip(1.0 - entropy / np.log(probability.shape[-1]), 0.0, 1.0)


@dataclass(frozen=True)
class ObservationQuality:
    """Independent reliability terms for each image ray or region."""

    registration: np.ndarray
    geometry: np.ndarray
    resolution: np.ndarray
    incidence: np.ndarray
    visibility: np.ndarray
    independence: np.ndarray

    def combined(self) -> np.ndarray:
        factors = np.stack(
            [
                self.registration,
                self.geometry,
                self.resolution,
                self.incidence,
                self.visibility,
                self.independence,
            ],
            axis=0,
        )
        if np.any((factors < 0.0) | (factors > 1.0)):
            raise ValueError("observation quality factors must lie in [0, 1]")
        return np.prod(factors, axis=0)


@dataclass(frozen=True)
class SoftAssociation:
    """Candidate surface elements and probabilities for every observation."""

    surface_indices: np.ndarray
    probabilities: np.ndarray

    def normalised(self) -> SoftAssociation:
        indices = np.asarray(self.surface_indices, dtype=np.int64)
        probability = np.asarray(self.probabilities, dtype=np.float64)
        if indices.shape != probability.shape or indices.ndim != 2:
            raise ValueError("association arrays must have matching shape [observations, candidates]")
        if np.any(probability < 0.0):
            raise ValueError("association probabilities cannot be negative")
        total = probability.sum(axis=1, keepdims=True)
        probability = np.divide(probability, total, out=np.zeros_like(probability), where=total > 0.0)
        return SoftAssociation(indices, probability)


class EvidenceAccumulator:
    """Dirichlet and Beta posteriors over a fixed set of 3D surface elements.

    The accumulator is intentionally a rebuildable derivative. The immutable
    observation ledger remains the source of truth, allowing pose or geometry
    corrections to be replayed without double counting old projections.
    """

    def __init__(
        self,
        surface_count: int,
        entity_labels: list[str],
        material_labels: list[str],
        attribute_labels: list[str],
        *,
        categorical_prior: float = 0.25,
        attribute_prior: float = 0.5,
    ) -> None:
        if surface_count <= 0:
            raise ValueError("surface_count must be positive")
        self.entity_labels = list(entity_labels)
        self.material_labels = list(material_labels)
        self.attribute_labels = list(attribute_labels)
        self.entity_alpha = np.full((surface_count, len(entity_labels)), categorical_prior, dtype=np.float32)
        self.material_alpha = np.full((surface_count, len(material_labels)), categorical_prior, dtype=np.float32)
        self.attribute_alpha = np.full((surface_count, len(attribute_labels)), attribute_prior, dtype=np.float32)
        self.attribute_beta = np.full((surface_count, len(attribute_labels)), attribute_prior, dtype=np.float32)
        self.support_weight = np.zeros(surface_count, dtype=np.float32)
        self.observation_count = np.zeros(surface_count, dtype=np.uint32)

    @property
    def surface_count(self) -> int:
        return len(self.support_weight)

    @staticmethod
    def _validate_distribution(probability: np.ndarray, observations: int, classes: int, name: str) -> np.ndarray:
        value = np.asarray(probability, dtype=np.float64)
        if value.shape != (observations, classes):
            raise ValueError(f"{name} probability must have shape {(observations, classes)}")
        if np.any(value < 0.0) or not np.allclose(value.sum(axis=1), 1.0, atol=1e-5):
            raise ValueError(f"{name} rows must be nonnegative probability distributions")
        return value

    def update(
        self,
        association: SoftAssociation,
        quality: ObservationQuality,
        entity_probability: np.ndarray,
        material_probability: np.ndarray,
        attribute_probability: np.ndarray,
    ) -> None:
        association = association.normalised()
        observations, candidates = association.surface_indices.shape
        if np.any((association.surface_indices < 0) | (association.surface_indices >= self.surface_count)):
            raise IndexError("association refers to a surface outside the accumulator")
        entity = self._validate_distribution(
            entity_probability,
            observations,
            len(self.entity_labels),
            "entity",
        )
        material = self._validate_distribution(
            material_probability,
            observations,
            len(self.material_labels),
            "material",
        )
        attributes = np.asarray(attribute_probability, dtype=np.float64)
        if attributes.shape != (observations, len(self.attribute_labels)) or np.any(
            (attributes < 0.0) | (attributes > 1.0)
        ):
            raise ValueError("attribute probabilities must have shape [observations, attributes] and lie in [0, 1]")

        base_weight = np.asarray(quality.combined(), dtype=np.float64)
        if base_weight.shape != (observations,):
            raise ValueError("quality factors must have one value per observation")
        entity_weight = base_weight * categorical_information(entity)
        material_weight = base_weight * categorical_information(material)
        attribute_weight = base_weight[:, None] * np.abs(2.0 * attributes - 1.0)

        for candidate in range(candidates):
            surfaces = association.surface_indices[:, candidate]
            association_weight = association.probabilities[:, candidate]
            entity_increment = entity * (entity_weight * association_weight)[:, None]
            material_increment = material * (material_weight * association_weight)[:, None]
            attribute_scale = attribute_weight * association_weight[:, None]
            np.add.at(self.entity_alpha, surfaces, entity_increment.astype(np.float32))
            np.add.at(self.material_alpha, surfaces, material_increment.astype(np.float32))
            np.add.at(self.attribute_alpha, surfaces, (attribute_scale * attributes).astype(np.float32))
            np.add.at(self.attribute_beta, surfaces, (attribute_scale * (1.0 - attributes)).astype(np.float32))
            np.add.at(self.support_weight, surfaces, (base_weight * association_weight).astype(np.float32))
            np.add.at(self.observation_count, surfaces, association_weight > 0.0)

    def entity_posterior(self) -> np.ndarray:
        return self.entity_alpha / self.entity_alpha.sum(axis=1, keepdims=True)

    def material_posterior(self) -> np.ndarray:
        return self.material_alpha / self.material_alpha.sum(axis=1, keepdims=True)

    def attribute_posterior(self) -> np.ndarray:
        return self.attribute_alpha / (self.attribute_alpha + self.attribute_beta)

    def save(self, path: pathlib.Path) -> None:
        metadata = {
            "entity_labels": self.entity_labels,
            "material_labels": self.material_labels,
            "attribute_labels": self.attribute_labels,
            "representation": "Dirichlet entity/material and independent Beta attributes",
        }
        np.savez_compressed(
            path,
            metadata=np.asarray(json.dumps(metadata)),
            entity_alpha=self.entity_alpha,
            material_alpha=self.material_alpha,
            attribute_alpha=self.attribute_alpha,
            attribute_beta=self.attribute_beta,
            support_weight=self.support_weight,
            observation_count=self.observation_count,
        )

    @classmethod
    def load(cls, path: pathlib.Path) -> EvidenceAccumulator:
        """Restore posteriors from an NPZ checkpoint, rejecting anything else.

        Pickled payloads are refused, the archive handle is released before
        returning, and every array must match the shape and dtype implied by
        the stored label lists. A checkpoint that disagrees with its own
        metadata is a corrupted posterior, not something to load half of.
        """
        with np.load(path, allow_pickle=False) as document:
            metadata = json.loads(str(document["metadata"]))
            for key in ("entity_labels", "material_labels", "attribute_labels"):
                names = metadata.get(key)
                if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
                    raise ValueError(f"evidence metadata must carry a list of string {key}")
            surfaces = len(np.asarray(document["support_weight"]))
            result = cls(
                surfaces,
                metadata["entity_labels"],
                metadata["material_labels"],
                metadata["attribute_labels"],
            )
            expected = {
                "entity_alpha": ((surfaces, len(result.entity_labels)), np.float32),
                "material_alpha": ((surfaces, len(result.material_labels)), np.float32),
                "attribute_alpha": ((surfaces, len(result.attribute_labels)), np.float32),
                "attribute_beta": ((surfaces, len(result.attribute_labels)), np.float32),
                "support_weight": ((surfaces,), np.float32),
                "observation_count": ((surfaces,), np.uint32),
            }
            for name, (shape, dtype) in expected.items():
                array = np.asarray(document[name])
                if array.shape != shape or array.dtype != dtype:
                    raise ValueError(
                        f"{name} must have shape {shape} and dtype {np.dtype(dtype).name}, "
                        f"not {array.shape} and {array.dtype.name}"
                    )
                if not np.all(np.isfinite(array)) or np.any(array < 0.0):
                    raise ValueError(f"{name} must hold finite non-negative evidence counts")
                setattr(result, name, array)
        return result
