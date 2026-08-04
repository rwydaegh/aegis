"""Resolving the material axis, where the two backends meet.

The dense backend has one ``Building`` class. Brick, render, ashlar stone, glass
curtain wall and metal cladding all land in it and their permittivity,
conductivity and roughness are not close, so the dense pass cannot express
material at all. The open-vocabulary backend can, and this is where its answer
is allowed to overwrite the dense one.

The rule is a cascade, not a vote.

The material axis is dense everywhere. Where no concept fires it is the dense
class prior ``p(material | entity)``, which for ``Building`` is deliberately
flat. Where a concept fires **and its entity support contains the dense class
underneath it**, the concept's sharper distribution replaces the prior. That
last condition is what stops a ``brick facade`` mask spilling onto a pedestrian:
the dense pass resolves who is standing there, the prompted pass resolves what
the wall behind them is made of.

:func:`material_hints` is the older single-winner table, kept because
``project_semantics.py`` writes its raster into ``scene.xml`` and because one
winning name is a useful quicklook even where the real evidence is a
distribution.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .vocabulary import BackendBridge, ConceptCatalog


MATERIAL_HINTS = {
    "sky": "none",
    "person": "human_tissue",
    "bicyclist": "human_tissue",
    "motorcyclist": "human_tissue",
    "bird": "animal_tissue",
    "ground animal": "animal_tissue",
    "vegetation": "vegetation",
    "water": "water",
    "road": "asphalt",
    "lane marking - general": "road_paint",
    "lane marking - crosswalk": "road_paint",
    "sidewalk": "concrete",
    "curb": "concrete",
    "terrain": "soil",
    "sand": "soil",
    "snow": "snow",
    "building": "unknown_building",
    "wall": "unknown_wall",
    "bridge": "concrete",
    "tunnel": "concrete",
    "pole": "metal",
    "utility pole": "metal",
    "traffic light": "metal",
    "traffic sign (front)": "metal",
    "traffic sign (back)": "metal",
    "street light": "metal",
    "fire hydrant": "metal",
    "bench": "unknown_furniture",
    "bike rack": "metal",
    "bollard": "metal",
    "trash can": "metal",
    "car": "vehicle_composite",
    "truck": "vehicle_composite",
    "bus": "vehicle_composite",
    "motorcycle": "vehicle_composite",
    "bicycle": "vehicle_composite",
    "boat": "vehicle_composite",
    "caravan": "vehicle_composite",
    "trailer": "vehicle_composite",
}


def material_hints(id2label: dict[int, str]) -> tuple[np.ndarray, list[str]]:
    """Map an entity vocabulary to a compact, explicitly provisional RF layer.

    Superseded by :func:`vistas_material_prior` for anything that has to reach
    an RF library row. It is retained because ``project_semantics.py`` writes
    its ``material_hint`` raster into ``scene.xml``, and because a single winning
    name is a useful quicklook even where the real evidence is a distribution.
    """
    names = ["unknown"]
    per_entity = np.zeros(max(id2label, default=-1) + 1, dtype=np.uint16)
    for class_id, label in id2label.items():
        hint = MATERIAL_HINTS.get(label.casefold(), "unknown")
        if hint not in names:
            names.append(hint)
        per_entity[class_id] = names.index(hint)
    return per_entity, names


def vistas_material_prior(
    id2label: dict[int, str],
    catalog: ConceptCatalog,
    bridge: BackendBridge,
) -> np.ndarray:
    """Dense-class-by-material prior table, one row per Vistas class.

    A Vistas class alone does not determine a material, so every row is a
    distribution. Classes the bridge has no entry for fall back to all mass on
    ``unknown``, which keeps them visible as unresolved rather than guessed.
    """
    materials = catalog.taxonomy["materials"]
    unknown_index = materials.index("unknown")
    table = np.zeros((max(id2label, default=-1) + 1, len(materials)), dtype=np.float32)
    for class_id, label in id2label.items():
        distribution = bridge.material_prior.get(label)
        if not distribution:
            table[class_id, unknown_index] = 1.0
            continue
        for material, mass in distribution.items():
            table[class_id, materials.index(material)] = mass
    return table


def concept_support_table(
    id2label: dict[int, str],
    catalog: ConceptCatalog,
    bridge: BackendBridge,
) -> np.ndarray:
    """Concept-by-dense-class compatibility, row 0 reserved for no concept.

    True means the concept may claim the material of a pixel that the dense pass
    assigned to that class. This is the guard that keeps the two backends
    complementary: without it a broad open-vocabulary facade mask silently
    repaints the people and vehicles standing in front of the facade.

    Concepts that name an entity are admissible over that entity's dense
    classes. Material-only concepts have no entity to route on, so they are
    admissible where the dense class prior does not already exclude their
    material.
    """
    columns = max(id2label, default=-1) + 1
    table = np.zeros((len(catalog.concepts) + 1, columns), dtype=bool)
    for index, concept in enumerate(catalog.concepts):
        admissible = bridge.admissible_classes(concept)
        for class_id, label in id2label.items():
            table[index + 1, class_id] = label in admissible
    return table


@dataclass(frozen=True)
class MaterialLayer:
    """Dense material evidence with the backend that supplied each pixel.

    ``prior_mass`` is deliberately not called a probability. On a concept-backed
    pixel it is the winning share of that concept's hand-written material
    distribution, and on a prior-backed pixel it is the winning share of the
    dense class prior. Neither carries the detection score, which lives in
    ``detection_confidence``. Multiplying them is not the posterior either, so
    the two are kept apart and named for what they are.
    """

    material: np.ndarray
    prior_mass: np.ndarray
    concept: np.ndarray
    detection_confidence: np.ndarray
    source: np.ndarray
    source_names: tuple[str, ...] = ("vistas_prior", "concept_backend")

    def concept_fraction(self) -> float:
        return float(np.count_nonzero(self.source == 1) / self.source.size) if self.source.size else 0.0


def resolve_material(
    entity: np.ndarray,
    concept: np.ndarray,
    confidence: np.ndarray,
    *,
    prior_table: np.ndarray,
    concept_material: np.ndarray,
    support_table: np.ndarray,
) -> MaterialLayer:
    """Sharpen the dense material prior with concept evidence where it is admissible.

    A concept only claims a pixel when the dense class underneath it is in that
    concept's entity support. Rejected pixels keep the dense prior, so the output
    is dense whatever the open-vocabulary pass did or did not find.

    The full per-pixel distribution is never materialised. Both tables are a few
    dozen rows, so reducing them first and indexing afterwards is exact and
    keeps an 8192 x 4096 sphere inside a few hundred megabytes instead of
    several gigabytes. The distribution stays reconstructible downstream from
    the emitted concept and entity rasters plus the tables in the manifest.
    """
    if not entity.shape == concept.shape == confidence.shape:
        raise ValueError("entity, concept and confidence rasters must have the same shape")
    admissible = (concept > 0) & support_table[concept, entity]
    prior_choice, prior_share = prior_table.argmax(axis=1), prior_table.max(axis=1)
    concept_choice, concept_share = concept_material.argmax(axis=1), concept_material.max(axis=1)
    return MaterialLayer(
        material=np.where(admissible, concept_choice[concept], prior_choice[entity]).astype(np.uint16),
        prior_mass=np.where(admissible, concept_share[concept], prior_share[entity]).astype(np.float16),
        concept=np.where(admissible, concept, 0).astype(np.uint16),
        # Zeroed wherever the concept was rejected. Leaving the fused layer
        # confidence through would advertise a confident detection for a concept
        # that is not in the output.
        detection_confidence=np.where(admissible, confidence, np.float16(0.0)).astype(np.float16),
        source=admissible.astype(np.uint8),
    )
