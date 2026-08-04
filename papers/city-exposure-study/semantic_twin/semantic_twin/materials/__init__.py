"""Labels to electromagnetic response, and the line between a material and a surface.

The package is split along one distinction that used to be blurred.

A material is a recipe. It names an ITU-R P.2040-4 row and a roughness class and
nothing else, so the same brick spec serves every square in the study.
:mod:`~.itu` holds the rows, :mod:`~.roughness` holds the closure that turns a
height field into a specular fraction, and :mod:`~.catalogue` holds the named
specs and the table you get by evaluating them at one carrier.

A surface is a set of triangles that carries one. :mod:`~.binding` owns that,
and it owns provenance as a required per triangle field, so a run can say which
faces got their material from a photograph and which from the orientation of
their normal. :mod:`~.evidence` and :mod:`~.posterior` are the routes that
produce one from image evidence.

The two halves meet at exactly one place, the class index. A binding's
``face_class`` indexes the same tuple a table's ``permittivity`` does, and that
is the whole contract.

Three models sit alongside, none of them on the tracer's live path, because the
tracer takes one permittivity and one RMS height per class and cannot express
any of them. :mod:`~.foliage` treats a canopy as a participating medium rather
than an interface, which is what it physically is. :mod:`~.masonry` treats a
brick wall as a diffraction grating specified by construction documents.
:mod:`~.stack` treats a facade as layers, and holds the power mixture that says
what a posterior over material labels is worth. Read their own docstrings before
wiring any of them to a number.
"""

from __future__ import annotations

from .binding import (
    CLASS_NAMES,
    Provenance,
    SurfaceBinding,
    class_area_fractions,
    classify_faces,
    extend_classes,
    geometric_binding,
)
from .catalogue import (
    GEOMETRIC_CLASS_RULE,
    IMAGE_MATERIALS,
    MATERIAL_SUBSTITUTION,
    MATERIAL_VOCABULARY,
    P833_CANOPY,
    SURFACE_CLASSES,
    VEGETATION_NOTE,
    MaterialSpec,
    MaterialTable,
    load_table,
)
from .evidence import (
    CLUTTER_ENTITIES,
    SEMANTIC_PREFIX,
    VegetationBinding,
    bind_fishnet,
    bind_walk_entities,
    bind_walk_materials,
    bind_walk_vegetation,
    clutter_triangles,
)
from .itu import (
    MaterialEvaluation,
    MaterialLibrary,
    PowerLawMaterial,
    RadioMaterialParameters,
    radio_material_from_roughness,
)
from .posterior import POSTERIOR_PREFIX, bind_posterior, realised_composition, sample_face_materials
from .roughness import (
    GAUSSIAN_STRUCTURE,
    MASONRY_RULE,
    PERIODIC_STRUCTURES,
    QUADRATURE_RULE,
    SurfaceRoughnessLibrary,
    SurfaceRoughnessPrior,
    effective_rms_height,
    masonry_equivalent_rms_height,
    rayleigh_roughness_parameter,
    rayleigh_smooth_threshold_m,
    roughness_to_scattering_coefficient,
    specular_power_fraction,
)

__all__ = [
    "CLASS_NAMES",
    "CLUTTER_ENTITIES",
    "GAUSSIAN_STRUCTURE",
    "GEOMETRIC_CLASS_RULE",
    "IMAGE_MATERIALS",
    "MASONRY_RULE",
    "MATERIAL_SUBSTITUTION",
    "MATERIAL_VOCABULARY",
    "P833_CANOPY",
    "PERIODIC_STRUCTURES",
    "POSTERIOR_PREFIX",
    "QUADRATURE_RULE",
    "SEMANTIC_PREFIX",
    "SURFACE_CLASSES",
    "VEGETATION_NOTE",
    "MaterialEvaluation",
    "MaterialLibrary",
    "MaterialSpec",
    "MaterialTable",
    "PowerLawMaterial",
    "Provenance",
    "RadioMaterialParameters",
    "SurfaceBinding",
    "SurfaceRoughnessLibrary",
    "SurfaceRoughnessPrior",
    "VegetationBinding",
    "bind_fishnet",
    "bind_posterior",
    "bind_walk_entities",
    "bind_walk_materials",
    "bind_walk_vegetation",
    "class_area_fractions",
    "classify_faces",
    "clutter_triangles",
    "effective_rms_height",
    "extend_classes",
    "geometric_binding",
    "load_table",
    "masonry_equivalent_rms_height",
    "radio_material_from_roughness",
    "rayleigh_roughness_parameter",
    "rayleigh_smooth_threshold_m",
    "realised_composition",
    "roughness_to_scattering_coefficient",
    "sample_face_materials",
    "specular_power_fraction",
]
