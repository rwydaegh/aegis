"""Validated mapping from open-vocabulary prompts to semantic evidence axes.

The catalogue carries three things that have to stay consistent with each other:

1. the concept prompts and their entity, material and attribute distributions,
2. the binding from every material label to the RF library row that supplies its
   dielectric model, so an unbound label is visible rather than silent,
3. the bridge to the dense Mapillary Vistas backend: which Vistas classes can
   support each concept, and what material spread a bare Vistas class carries.

The concept distributions are priors. A prompt firing is evidence about what a
surface looks like, and appearance does not determine permittivity. Concepts
that carry a known ambiguity record it in ``caveat``.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

KINDS = ("surface", "object")
UNBOUND_STATUS = ("no_model", "no_row", "different_recommendation", "different_library", "not_a_material")

# Smallest share a dense class prior must give a material before a material-only
# prompt is allowed to claim that material over the class. See
# :meth:`BackendBridge.material_compatible` for why this is not zero.
MATERIAL_PRIOR_FLOOR = 0.05


@dataclass(frozen=True)
class Concept:
    prompt: str
    kind: str
    entity: dict[str, float]
    material: dict[str, float]
    attributes: dict[str, float]
    caveat: str = ""


@dataclass(frozen=True)
class MaterialBinding:
    """Where one concept-axis material label gets its dielectric model."""

    material: str
    library: str
    row: str | None
    status: str
    note: str = ""

    @property
    def bound_to_itu_p2040(self) -> bool:
        return self.status == "bound" and self.row is not None


@dataclass(frozen=True)
class BackendBridge:
    """Routing and prior tables shared with one dense segmentation backend."""

    name: str
    entity_support: dict[str, tuple[str, ...]]
    material_prior: dict[str, dict[str, float]]

    def concept_support(self, concept: Concept) -> frozenset[str] | None:
        """Dense classes that can carry this concept, or None if it names no entity.

        A concept with mass on the ``unknown`` entity is a material-only prompt.
        It is asked of every view, because it exists to keep working where the
        dense pass got the entity wrong, and its admissibility is decided by
        :meth:`material_compatible` instead.
        """
        labels: set[str] = set()
        for entity, mass in concept.entity.items():
            if mass <= 0.0:
                continue
            if entity == "unknown":
                return None
            labels.update(self.entity_support.get(entity, ()))
        return frozenset(labels)

    def material_compatible(self, material: str, *, floor: float = MATERIAL_PRIOR_FLOOR) -> frozenset[str]:
        """Dense classes whose prior gives a material more than a token share.

        This is the admissibility rule for the material-only prompts, and it was
        added because they were the least constrained thing in the pipeline
        rather than the most. Measured at Korenmarkt: ``metal surface`` claimed
        20 percent of the sphere, 78 percent of it over Sidewalk and Pedestrian
        Area, which is a cobbled square. Neither class carries any metal mass in
        its prior, so requiring agreement with the prior removes that claim
        without a hand-written exclusion list.

        The floor is what stops "more than zero" being read as permission.
        ``Building`` carries 0.03 metal for the occasional clad frontage, and
        without a floor that trace is enough to let ``metal surface`` overwrite a
        deliberately flat facade prior with 0.96 metal. At millimetre wave a
        wrong metal is the most consequential material error there is, so the
        threshold is explicit and recorded rather than implied by a comparison
        against zero.
        """
        return frozenset(
            label for label, distribution in self.material_prior.items() if distribution.get(material, 0.0) >= floor
        )

    def admissible_classes(self, concept: Concept, *, floor: float = MATERIAL_PRIOR_FLOOR) -> frozenset[str]:
        """Dense classes over which this concept may claim the material axis."""
        support = self.concept_support(concept)
        if support is not None:
            return support
        # Ties are broken by name so the routing cannot depend on JSON key order.
        dominant = max(sorted(concept.material), key=lambda name: concept.material[name])
        return self.material_compatible(dominant, floor=floor)


@dataclass(frozen=True)
class LibraryCoverage:
    """Which rows of an RF material library any prompt can actually reach."""

    library: str
    reachable: tuple[str, ...]
    unreachable: tuple[str, ...]
    unbound_materials: tuple[str, ...]

    @property
    def fraction(self) -> float:
        total = len(self.reachable) + len(self.unreachable)
        return len(self.reachable) / total if total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "library": self.library,
            "reachable_rows": list(self.reachable),
            "unreachable_rows": list(self.unreachable),
            "reachable_count": len(self.reachable),
            "row_count": len(self.reachable) + len(self.unreachable),
            "materials_without_a_row_in_this_library": list(self.unbound_materials),
        }


class ConceptCatalog:
    def __init__(
        self,
        taxonomy: dict[str, list[str]],
        concepts: list[Concept],
        *,
        material_grounding: dict[str, MaterialBinding] | None = None,
        bridges: dict[str, BackendBridge] | None = None,
        grounding_note: str = "",
    ) -> None:
        self.taxonomy = taxonomy
        self.concepts = concepts
        self.material_grounding = material_grounding or {}
        self.bridges = bridges or {}
        self.grounding_note = grounding_note
        self.by_prompt = {concept.prompt: concept for concept in concepts}
        if len(self.by_prompt) != len(concepts):
            raise ValueError("concept prompts must be unique")
        self._validate()

    @property
    def prompts(self) -> tuple[str, ...]:
        return tuple(concept.prompt for concept in self.concepts)

    def concept_ids(self) -> dict[str, int]:
        """Prompt to raster value, with zero reserved for "nothing detected"."""
        return {name: index for index, name in enumerate(["unlabelled", *self.prompts])}

    def id2label(self) -> dict[int, str]:
        return dict(enumerate(["unlabelled", *self.prompts]))

    def _validate(self) -> None:
        entity_labels = set(self.taxonomy["entities"])
        material_labels = set(self.taxonomy["materials"])
        attribute_labels = set(self.taxonomy["attributes"])
        for concept in self.concepts:
            if concept.kind not in KINDS:
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
        self._validate_grounding(material_labels)
        self._validate_bridges(entity_labels, material_labels)

    def _validate_grounding(self, material_labels: set[str]) -> None:
        if not self.material_grounding:
            return
        missing = material_labels - set(self.material_grounding)
        if missing:
            raise ValueError(f"material labels with no grounding record: {sorted(missing)}")
        extra = set(self.material_grounding) - material_labels
        if extra:
            raise ValueError(f"grounding records for materials outside the taxonomy: {sorted(extra)}")
        for binding in self.material_grounding.values():
            if binding.status == "bound":
                if not binding.row:
                    raise ValueError(f"{binding.material} is marked bound but names no row")
            elif binding.status not in UNBOUND_STATUS:
                raise ValueError(f"{binding.material} has an unrecognised grounding status: {binding.status}")

    def _validate_bridges(self, entity_labels: set[str], material_labels: set[str]) -> None:
        for bridge in self.bridges.values():
            unknown_entities = set(bridge.entity_support) - entity_labels
            if unknown_entities:
                raise ValueError(f"{bridge.name} routes entities outside the taxonomy: {sorted(unknown_entities)}")
            for dense_label, distribution in bridge.material_prior.items():
                unknown = set(distribution) - material_labels
                if unknown or not np.isclose(sum(distribution.values()), 1.0):
                    raise ValueError(f"{bridge.name} prior for {dense_label} is invalid: {sorted(unknown)}")

    def categorical_probability(self, concept: Concept, axis: str) -> np.ndarray:
        labels = self.taxonomy[axis]
        evidence = concept.entity if axis == "entities" else concept.material
        return np.asarray([evidence.get(label, 0.0) for label in labels], dtype=np.float32)

    def attribute_probability(self, concept: Concept) -> np.ndarray:
        return np.asarray(
            [concept.attributes.get(label, 0.5) for label in self.taxonomy["attributes"]],
            dtype=np.float32,
        )

    def material_matrix(self) -> np.ndarray:
        """Concept-by-material probabilities, row 0 reserved for unlabelled."""
        materials = self.taxonomy["materials"]
        matrix = np.zeros((len(self.concepts) + 1, len(materials)), dtype=np.float32)
        matrix[0, materials.index("unknown")] = 1.0
        for index, concept in enumerate(self.concepts):
            matrix[index + 1] = self.categorical_probability(concept, "materials")
        return matrix

    def reachable_materials(self) -> frozenset[str]:
        """Material labels that at least one prompt can put probability mass on."""
        return frozenset(
            material
            for concept in self.concepts
            for material, mass in concept.material.items()
            if mass > 0.0 and material != "unknown"
        )

    def library_coverage(self, library_rows: list[str], *, library: str = "itu_p2040_4") -> LibraryCoverage:
        """Audit which rows of an RF material library a prompt can reach.

        ``library_rows`` is the row list of the library itself, so the audit
        reports what the library offers rather than what the taxonomy happens to
        name. Rows nothing can reach are the honest output here.
        """
        reachable_labels = self.reachable_materials()
        bound_rows = {
            binding.row: binding.material
            for binding in self.material_grounding.values()
            if binding.library == library and binding.row is not None
        }
        reachable = tuple(row for row in library_rows if bound_rows.get(row) in reachable_labels)
        unreachable = tuple(row for row in library_rows if row not in reachable)
        unbound = tuple(
            sorted(
                material
                for material in reachable_labels
                if self.material_grounding.get(material, _UNBOUND).library != library
            )
        )
        return LibraryCoverage(library=library, reachable=reachable, unreachable=unreachable, unbound_materials=unbound)

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
                caveat=str(record.get("caveat", "")),
            )
            for record in document["concepts"]
        ]
        grounding_document = document.get("material_grounding", {})
        grounding = {
            material: MaterialBinding(
                material=material,
                library=str(record.get("library", "none")),
                row=record.get("row"),
                status=str(record.get("status", "no_model")),
                note=str(record.get("note", "")),
            )
            for material, record in grounding_document.get("materials", {}).items()
        }
        bridges = {
            name: BackendBridge(
                name=name,
                entity_support={entity: tuple(labels) for entity, labels in record.get("entity_support", {}).items()},
                material_prior={
                    dense_label: {material: float(value) for material, value in distribution.items()}
                    for dense_label, distribution in record.get("material_prior", {}).items()
                    if dense_label != "prior_note"
                },
            )
            for name, record in document.get("backend_bridge", {}).items()
            if name != "bridge_note"
        }
        return cls(
            document["taxonomy"],
            concepts,
            material_grounding=grounding,
            bridges=bridges,
            grounding_note=str(grounding_document.get("grounding_note", "")),
        )


_UNBOUND = MaterialBinding(material="", library="none", row=None, status="no_model")


@dataclass(frozen=True)
class PromptGate:
    """Which prompts one view is worth asking, and why the rest were skipped."""

    view: str
    prompts: tuple[str, ...]
    ungated: tuple[str, ...] = field(default_factory=tuple)
    skipped: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "view": self.view,
            "asked": len(self.prompts),
            "always_asked": len(self.ungated),
            "skipped": list(self.skipped),
        }


def gate_prompts(
    catalog: ConceptCatalog,
    bridge: BackendBridge,
    present_labels: frozenset[str],
    *,
    view: str = "",
) -> PromptGate:
    """Ask a concept only where the dense pass found a class that could carry it.

    This is the cheap half of the cascade. The dense backend has already
    partitioned the view, so a facade-material prompt on a view with no building
    pixels is known to be wasted work before the open-vocabulary model is
    touched. Concepts with unknown entity support are never skipped.
    """
    asked: list[str] = []
    ungated: list[str] = []
    skipped: list[str] = []
    for concept in catalog.concepts:
        support = bridge.concept_support(concept)
        if support is None:
            asked.append(concept.prompt)
            ungated.append(concept.prompt)
        elif support & present_labels:
            asked.append(concept.prompt)
        else:
            skipped.append(concept.prompt)
    return PromptGate(view=view, prompts=tuple(asked), ungated=tuple(ungated), skipped=tuple(skipped))
