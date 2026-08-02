"""Support mesh, surface classes and their electromagnetic parameters.

The support mesh carries no material labels of its own. The semantic twin's
per-pixel posteriors exist only inside the panorama frusta, so binding them to
all 158k triangles of the 130 m crop is a separate job. What this module does
instead is an explicit, reproducible geometric rule: a triangle is ground,
facade, roof or soffit according to its normal and its height above the local
ground datum, and each class carries one ITU-R P.2040-4 row and one roughness
class from ``config/surface_roughness.json``.

This is a placeholder for the semantic binding, not a substitute for it, and
``SurfaceBinding.provenance`` says so in the manifest that every run writes.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..materials import MaterialLibrary, SurfaceRoughnessLibrary

CLASS_NAMES = ("ground", "facade", "roof", "soffit")

#: Class -> (ITU-R P.2040-4 row, roughness class in config/surface_roughness.json)
CLASS_BINDING: dict[str, tuple[str, str]] = {
    "ground": ("asphalt_concrete", "stone_sett_paving"),
    "facade": ("brick", "brick_wall_with_mortar_joints"),
    "roof": ("concrete", "concrete_board_marked_or_exposed_aggregate"),
    "soffit": ("concrete", "concrete_as_cast_smooth"),
}


@dataclass(frozen=True)
class SurfaceBinding:
    """Per class electromagnetic parameters evaluated at one carrier."""

    frequency_hz: float
    class_names: tuple[str, ...]
    permittivity: np.ndarray  # (C,) complex relative permittivity
    rms_height_m: np.ndarray  # (C,) median RMS height of the height field
    binding: dict[str, tuple[str, str]] = field(default_factory=lambda: dict(CLASS_BINDING))
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "frequency_hz": self.frequency_hz,
            "classes": {
                name: {
                    "itu_row": self.binding[name][0],
                    "roughness_class": self.binding[name][1],
                    "relative_permittivity": [
                        float(self.permittivity[i].real),
                        float(self.permittivity[i].imag),
                    ],
                    "rms_height_m": float(self.rms_height_m[i]),
                }
                for i, name in enumerate(self.class_names)
            },
            "provenance": self.provenance,
        }


def load_bindings(
    config_dir: pathlib.Path,
    frequency_hz: float,
    *,
    allow_extrapolation: bool = False,
    class_names: tuple[str, ...] = CLASS_NAMES,
    class_binding: dict[str, tuple[str, str]] | None = None,
    class_rule: str | None = None,
) -> SurfaceBinding:
    """Evaluate the ITU rows and roughness priors bound to each surface class."""
    class_binding = dict(CLASS_BINDING) if class_binding is None else class_binding
    materials = MaterialLibrary.load(config_dir / "itu_p2040_4.json")
    roughness = SurfaceRoughnessLibrary.load(config_dir / "surface_roughness.json")
    permittivity = np.zeros(len(class_names), dtype=np.complex128)
    rms = np.zeros(len(class_names), dtype=np.float64)
    rows: dict[str, Any] = {}
    for i, name in enumerate(class_names):
        itu_row, roughness_class = class_binding[name]
        evaluation = materials[itu_row].evaluate(frequency_hz, allow_extrapolation=allow_extrapolation)
        permittivity[i] = complex(evaluation.relative_permittivity_real, -evaluation.relative_permittivity_imag)
        prior = roughness[roughness_class]
        rms[i] = _effective_rms_height(prior)
        rows[name] = {
            "applicability": evaluation.applicability,
            "uncertainty_multiplier": evaluation.uncertainty_multiplier,
            "roughness_structure": prior.structure,
            "roughness_evidence_grade": prior.evidence_grade,
        }
    return SurfaceBinding(
        frequency_hz=float(frequency_hz),
        class_names=tuple(class_names),
        permittivity=permittivity,
        rms_height_m=rms,
        binding=class_binding,
        provenance={
            "material_source": materials.source,
            "roughness_source": roughness.source["title"],
            "class_rule": class_rule
            or (
                "geometric: |n_z| decides ground/facade/roof/soffit, with the ground "
                "datum taken from the observation point's own downward hit"
            ),
            "rows": rows,
        },
    )


def _effective_rms_height(prior: Any) -> float:
    """Wall scale RMS height, folding in the periodic component when present.

    ``config/surface_roughness.json`` is emphatic that the monolithic finish and
    the metre scale facade structure are different quantities. A metre scale
    patch is what a tracer facet stands for, so the periodic relief is the one
    that governs. Where a periodic component is tabulated its relief amplitude
    is combined in quadrature with the finish, which is the crudest defensible
    way to feed a two scale surface into a single Rayleigh closure. It
    overstates the coherent loss for a strictly periodic grating, which
    redirects rather than destroys power, so the resulting specular fractions
    are a lower bound and the diffuse share an upper bound.
    """
    finish = float(prior.rms_height_m)
    periodic = prior.periodic_component
    if not periodic:
        return finish
    step_mm = periodic.get("step_height_mm")
    if step_mm is None:
        return finish
    relief = float(step_mm) / 1000.0
    return float(np.hypot(finish, relief / np.sqrt(12.0)))


def classify_faces(
    vertices: np.ndarray,
    faces: np.ndarray,
    ground_datum_m: float,
    *,
    facade_cosine: float = 0.5,
    roof_height_m: float = 4.0,
) -> np.ndarray:
    """Assign a surface class index to every triangle.

    ``ground_datum_m`` is the z of the walkable surface. Upward facing faces
    within ``roof_height_m`` of it are ground, above it they are roof.
    """
    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    normals = np.cross(b - a, c - a)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, np.where(norms > 0.0, norms, 1.0))
    centroid_z = (a[:, 2] + b[:, 2] + c[:, 2]) / 3.0

    index = np.full(faces.shape[0], CLASS_NAMES.index("facade"), dtype=np.int8)
    up = normals[:, 2] > facade_cosine
    down = normals[:, 2] < -facade_cosine
    index[up & (centroid_z <= ground_datum_m + roof_height_m)] = CLASS_NAMES.index("ground")
    index[up & (centroid_z > ground_datum_m + roof_height_m)] = CLASS_NAMES.index("roof")
    index[down] = CLASS_NAMES.index("soffit")
    return index


def class_area_fractions(face_class: np.ndarray, area: np.ndarray) -> dict[str, float]:
    total = float(area.sum())
    return {name: float(area[face_class == i].sum() / total) for i, name in enumerate(CLASS_NAMES)}
