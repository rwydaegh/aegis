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

The ordinary face binding meets transport at the class index. The joint atlas
adds a second contract. At an observed hit texel, transport mixes the power
responses of its host-compatible material posterior. It keeps the support mesh
unchanged and uses the face class wherever atlas evidence is refused or absent.
Woody vegetation is the exception: without registered canopy chords its atlas
cells are non-blocking, since the support face is not a physical interface.

Three richer models sit alongside. :mod:`~.foliage` treats a canopy as a participating medium rather
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
from .atlas_binding import (
    ATLAS_MATERIAL_RULE,
    ATLAS_PREFIX,
    MIN_INTERFACE_POSTERIOR,
    NON_STRUCTURAL_MATERIALS,
    AtlasMaterialBinding,
    bind_surface_atlas,
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
    FINISH_ONLY_RULE,
    GAUSSIAN_STRUCTURE,
    MASONRY_RULE,
    PERIODIC_STRUCTURES,
    QUADRATURE_RULE,
    SurfaceRoughnessLibrary,
    SurfaceRoughnessPrior,
    effective_rms_height,
    finish_only_rms_height,
    masonry_equivalent_rms_height,
    rayleigh_roughness_parameter,
    rayleigh_smooth_threshold_m,
    roughness_to_scattering_coefficient,
    specular_power_fraction,
)
from .support import (
    BUILT_HOST_ENTITIES,
    EMBEDDED_SUBFACE_ENTITIES,
    GROUND_HOST_ENTITIES,
    HOST_SURFACE_CLASS_RULE,
    SUPPORT_COMPATIBILITY_VERSION,
    SupportKind,
    entity_support_kind,
    entity_supports_geometric_class,
)
from .vegetation_transport import (
    GROUND_SURFACE_POLICY,
    WOODY_VOLUME_POLICY,
    AtlasVegetationEvidence,
    P833FrequencyAssessment,
    P833SegmentTransport,
    VegetationPathSegments,
    VegetationTransportPlan,
    assess_p833_frequency,
    evaluate_p833_segments,
    plan_vegetation_transport,
    vegetation_evidence_from_atlas,
)

__all__ = [
    "ATLAS_MATERIAL_RULE",
    "ATLAS_PREFIX",
    "AtlasMaterialBinding",
    "AtlasVegetationEvidence",
    "CLASS_NAMES",
    "BUILT_HOST_ENTITIES",
    "CLUTTER_ENTITIES",
    "GAUSSIAN_STRUCTURE",
    "EMBEDDED_SUBFACE_ENTITIES",
    "FINISH_ONLY_RULE",
    "GEOMETRIC_CLASS_RULE",
    "GROUND_HOST_ENTITIES",
    "GROUND_SURFACE_POLICY",
    "HOST_SURFACE_CLASS_RULE",
    "IMAGE_MATERIALS",
    "MASONRY_RULE",
    "MATERIAL_SUBSTITUTION",
    "MATERIAL_VOCABULARY",
    "MIN_INTERFACE_POSTERIOR",
    "NON_STRUCTURAL_MATERIALS",
    "P833_CANOPY",
    "P833FrequencyAssessment",
    "P833SegmentTransport",
    "PERIODIC_STRUCTURES",
    "POSTERIOR_PREFIX",
    "QUADRATURE_RULE",
    "SEMANTIC_PREFIX",
    "SURFACE_CLASSES",
    "SUPPORT_COMPATIBILITY_VERSION",
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
    "SupportKind",
    "VegetationBinding",
    "VegetationPathSegments",
    "VegetationTransportPlan",
    "WOODY_VOLUME_POLICY",
    "assess_p833_frequency",
    "bind_fishnet",
    "bind_surface_atlas",
    "bind_posterior",
    "bind_walk_entities",
    "bind_walk_materials",
    "bind_walk_vegetation",
    "class_area_fractions",
    "classify_faces",
    "clutter_triangles",
    "effective_rms_height",
    "finish_only_rms_height",
    "entity_support_kind",
    "entity_supports_geometric_class",
    "extend_classes",
    "evaluate_p833_segments",
    "geometric_binding",
    "load_table",
    "masonry_equivalent_rms_height",
    "plan_vegetation_transport",
    "radio_material_from_roughness",
    "rayleigh_roughness_parameter",
    "rayleigh_smooth_threshold_m",
    "realised_composition",
    "roughness_to_scattering_coefficient",
    "sample_face_materials",
    "specular_power_fraction",
    "vegetation_evidence_from_atlas",
]
