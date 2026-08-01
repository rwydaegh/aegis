"""Validated mapping from open-vocabulary prompts to semantic evidence axes."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Concept:
    prompt: str
    kind: str
    entity: dict[str, float]
    material: dict[str, float]
    attributes: dict[str, float]


class ConceptCatalog:
    def __init__(self, taxonomy: dict[str, list[str]], concepts: list[Concept]) -> None:
        self.taxonomy = taxonomy
        self.concepts = concepts
        self.by_prompt = {concept.prompt: concept for concept in concepts}
        if len(self.by_prompt) != len(concepts):
            raise ValueError("concept prompts must be unique")
        self._validate()

    def _validate(self) -> None:
        entity_labels = set(self.taxonomy["entities"])
        material_labels = set(self.taxonomy["materials"])
        attribute_labels = set(self.taxonomy["attributes"])
        for concept in self.concepts:
            if concept.kind not in {"surface", "object"}:
                raise ValueError(f"invalid kind for {concept.prompt}: {concept.kind}")
            for name, values, labels in (
                ("entity", concept.entity, entity_labels),
                ("material", concept.material, material_labels),
            ):
                unknown = set(values) - labels
                if unknown or not np.isclose(sum(values.values()), 1.0):
                    raise ValueError(f"invalid {name} distribution for {concept.prompt}: {unknown}")
            unknown_attributes = set(concept.attributes) - attribute_labels
            if unknown_attributes or any(not 0.0 <= value <= 1.0 for value in concept.attributes.values()):
                raise ValueError(f"invalid attributes for {concept.prompt}: {unknown_attributes}")

    def categorical_probability(self, concept: Concept, axis: str) -> np.ndarray:
        labels = self.taxonomy[axis]
        evidence = concept.entity if axis == "entities" else concept.material
        return np.asarray([evidence.get(label, 0.0) for label in labels], dtype=np.float32)

    def attribute_probability(self, concept: Concept) -> np.ndarray:
        return np.asarray(
            [concept.attributes.get(label, 0.5) for label in self.taxonomy["attributes"]],
            dtype=np.float32,
        )

    @classmethod
    def load(cls, path: pathlib.Path) -> ConceptCatalog:
        document: dict[str, Any] = json.loads(path.read_text())
        concepts = [
            Concept(
                prompt=record["prompt"],
                kind=record["kind"],
                entity={name: float(value) for name, value in record["entity"].items()},
                material={name: float(value) for name, value in record["material"].items()},
                attributes={name: float(value) for name, value in record.get("attributes", {}).items()},
            )
            for record in document["concepts"]
        ]
        return cls(document["taxonomy"], concepts)
