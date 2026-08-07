"""What a material is, and the named ones this study ships.

The line this package draws, and the reason it has two halves.

A **material** is a recipe. :class:`MaterialSpec` names one ITU-R P.2040-4 row,
one roughness class, and optionally a participating medium model for the labels
that are not interfaces at all. It carries no frequency, no triangle and no
mesh. Two squares in two cities that both show brick share the same spec
object.

A **material evaluated** is :class:`MaterialTable`: the specs resolved against
``config/itu_p2040_4.json`` and ``config/surface_roughness.json`` at one
carrier, giving the complex permittivity and RMS height arrays the tracer
indexes. Still no triangles. Change the carrier and you get a different table
from the same specs.

A **surface that has a material** is :class:`~.binding.SurfaceBinding`, and it
lives in the next module along. It owns triangles, the class each one was given,
and where that class came from. It owns no permittivity.

Those three used to be one idea called a binding, which is why the object that
holds per class permittivity was named ``SurfaceBinding`` while the object that
holds per triangle classes was named ``SemanticBinding``. The names were the
wrong way round.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .itu import MaterialLibrary
from .roughness import (
    FINISH_ONLY_RULE,
    MASONRY_RULE,
    QUADRATURE_RULE,
    SurfaceRoughnessLibrary,
    effective_rms_height,
    finish_only_rms_height,
    masonry_equivalent_rms_height,
)


@dataclass(frozen=True)
class MaterialSpec:
    """One named material: which ITU row and which roughness class it stands for.

    ``medium`` names a participating medium model instead of an interface, and
    is the flag a transport estimator reads to decide whether a face is a
    boundary or a volume. Only vegetation sets it today. See
    :func:`~.foliage.medium_for_spec`.
    """

    itu_row: str
    roughness_class: str
    medium: str | None = None
    note: str = ""

    @property
    def is_interface(self) -> bool:
        """Whether this material describes a surface a ray can reflect off."""
        return self.medium is None


#: The participating medium tag understood by :func:`~.foliage.medium_for_spec`.
P833_CANOPY = "p833_canopy"

#: Recorded in every manifest, because it changes how the vegetation numbers
#: should be read. Recommendation ITU-R P.833 tabulates nothing anywhere in FR2
#: and nothing at all between 12.5 and 37 GHz, so at the 15 GHz carrier this
#: study leads on, every vegetation parameter is an interpolation across a gap
#: in the recommendation rather than a value read from it.
VEGETATION_NOTE = (
    "ITU-R P.833 has no tabulated data in FR2 and nothing between 12.5 and "
    "37 GHz, so every vegetation parameter at 15 GHz is an interpolation "
    "across a gap in the recommendation. Vegetation carries the P.2040 "
    "vacuum row only as a table placeholder rather than wood: a canopy volume fraction of 6.4e-5 gives "
    "a Maxwell-Garnett boundary reflectance of 1.9e-9 against the wood row's "
    "0.029, so the wood row would add 71.8 dB of reflection that is not there. "
    "Surface transport never evaluates that placeholder as an interface. "
    "Woody atlas evidence is non-blocking until registered watertight volume "
    "chords exist. With those chords, the P.833 participating-medium model "
    "supplies direct, scattered, and absorbed energy."
)

#: The four classes the orientation rule can produce, in index order. The index
#: is written into every ``face_class`` array, so the order is load bearing.
CLASS_NAMES = ("ground", "facade", "roof", "soffit")

#: Geometric class -> material. What a triangle gets when no photograph saw it.
SURFACE_CLASSES: dict[str, MaterialSpec] = {
    "ground": MaterialSpec("asphalt_concrete", "stone_sett_paving"),
    "facade": MaterialSpec("brick", "brick_wall_with_mortar_joints"),
    "roof": MaterialSpec("concrete", "concrete_board_marked_or_exposed_aggregate"),
    "soffit": MaterialSpec("concrete", "concrete_as_cast_smooth"),
}

#: RF material vocabulary -> material. The ITU row comes from
#: ``material_grounding`` in ``semantics.json``. The roughness class is the
#: coarsest defensible representative of that material as a metre scale outdoor
#: patch, taken from ``config/surface_roughness.json``.
IMAGE_MATERIALS: dict[str, MaterialSpec] = {
    "brick": MaterialSpec("brick", "brick_wall_with_mortar_joints"),
    "concrete": MaterialSpec("concrete", "concrete_board_marked_or_exposed_aggregate"),
    "plasterboard": MaterialSpec("plasterboard", "render_plaster_painted"),
    "wood": MaterialSpec("wood", "wood_cladding"),
    "plywood": MaterialSpec("plywood", "wood_cladding"),
    "chipboard": MaterialSpec("chipboard", "wood_cladding"),
    "glass": MaterialSpec("glass", "glass_glazing_unit"),
    "metal": MaterialSpec("metal", "metal_cladding_panel_smooth"),
    "marble": MaterialSpec("marble", "stone_ashlar_dressed"),
    "asphalt_concrete": MaterialSpec("asphalt_concrete", "asphalt_road_dense_graded"),
    # A canopy has no interface, so giving it one is not a coarse approximation,
    # it is a different object. Leaf area index times leaf thickness over canopy
    # depth puts the canopy volume fraction at 6.4e-5, and Maxwell-Garnett then
    # gives a boundary reflectance of 1.9e-9 against the 0.029 of the P.2040
    # wood row, which is 71.8 dB of reflection that is not there.
    #
    # ``medium`` says what the row cannot: this label is a volume, and a
    # transport estimator that can carry one should ask foliage.py for it
    # instead of reflecting off it. Surface transport excludes this row and
    # passes through woody evidence until valid canopy volume chords exist.
    "vegetation_effective": MaterialSpec(
        "vacuum_air",
        "glass_glazing_unit",
        medium=P833_CANOPY,
        note=VEGETATION_NOTE,
    ),
}

#: The RF material vocabulary this study can actually ground. Every name here is
#: reachable to a row in ``config/itu_p2040_4.json``, through
#: :data:`IMAGE_MATERIALS` or :data:`MATERIAL_SUBSTITUTION`. A model asked what a
#: wall is made of is not allowed to answer outside it, because a name with no row
#: cannot be traced. That constraint is what puts the list here rather than beside
#: the prompt that recites it.
MATERIAL_VOCABULARY: tuple[str, ...] = (
    "brick",
    "concrete",
    "plasterboard",
    "marble",
    "glass",
    "metal",
    "wood",
    "ceramic",
    "unknown",
)

#: RF materials with no ITU row, mapped to the nearest row that does have one.
#: Each substitution is a judgement, so each is listed rather than defaulted.
MATERIAL_SUBSTITUTION: dict[str, str] = {
    "ceramic": "marble",  # no P.2040 row, dense fired mineral
    "polymer": "wood",  # no P.2040 row, low permittivity dielectric
    "fabric": "wood",  # no P.2040 row, low permittivity dielectric
    "soil": "concrete",  # P.527-6 not P.2040, and not implemented here
    "water": "concrete",  # standing water is not modelled
}

#: The rule a manifest records when nothing overrode the orientation rule.
GEOMETRIC_CLASS_RULE = (
    "geometric: |n_z| decides ground/facade/roof/soffit, with the ground "
    "datum taken from the observation point's own downward hit"
)


@dataclass(frozen=True)
class MaterialTable:
    """The named materials, resolved at one carrier.

    ``permittivity`` and ``rms_height_m`` are indexed by position in
    ``class_names``, which is the same index a
    :class:`~.binding.SurfaceBinding` writes into its ``face_class`` array.
    That shared index is the whole contract between the two halves of this
    package.

    ``provenance`` is required. A table that cannot say which recommendation,
    which roughness library and which roughness rule produced it is not a
    result, and this study has already lost more time to unrecoverable
    provenance than to any physics.
    """

    frequency_hz: float
    class_names: tuple[str, ...]
    permittivity: np.ndarray  # (C,) complex relative permittivity
    rms_height_m: np.ndarray  # (C,) RMS height fed to the Rayleigh closure
    spec: dict[str, MaterialSpec]
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        count = len(self.class_names)
        if self.permittivity.shape != (count,) or self.rms_height_m.shape != (count,):
            raise ValueError(
                f"{count} classes but {self.permittivity.shape} permittivities and "
                f"{self.rms_height_m.shape} RMS heights"
            )
        missing = [name for name in self.class_names if name not in self.spec]
        if missing:
            raise ValueError(f"no material spec for {missing}")
        if not self.provenance:
            raise ValueError("a material table must record where its rows came from")

    @property
    def media(self) -> dict[str, str]:
        """Classes that name a participating medium rather than an interface."""
        return {name: self.spec[name].medium for name in self.class_names if self.spec[name].medium is not None}

    def index(self, name: str) -> int:
        return self.class_names.index(name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "frequency_hz": self.frequency_hz,
            "classes": {
                name: {
                    "itu_row": self.spec[name].itu_row,
                    "roughness_class": self.spec[name].roughness_class,
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


def load_table(
    config_dir: pathlib.Path,
    frequency_hz: float,
    *,
    allow_extrapolation: bool = False,
    class_names: tuple[str, ...] = CLASS_NAMES,
    class_binding: Mapping[str, MaterialSpec] | None = None,
    class_rule: str | None = None,
    roughness_rule: str = FINISH_ONLY_RULE,
) -> MaterialTable:
    """Evaluate the ITU rows and roughness priors bound to each class.

    ``roughness_rule`` picks how a two scale surface is collapsed to the one
    RMS height the Rayleigh closure takes. ``FINISH_ONLY_RULE`` is the
    production default and uses the measured monolithic finish. The historical
    ``QUADRATURE_RULE`` and research-only ``MASONRY_RULE`` are available only
    through an explicit argument. Neither changes a Gaussian class.
    """
    class_binding = dict(SURFACE_CLASSES) if class_binding is None else dict(class_binding)
    materials = MaterialLibrary.load(config_dir / "itu_p2040_4.json")
    roughness = SurfaceRoughnessLibrary.load(config_dir / "surface_roughness.json")
    reduce = _ROUGHNESS_RULES.get(roughness_rule)
    if reduce is None:
        raise ValueError(f"unknown roughness rule {roughness_rule!r}, expected one of {sorted(_ROUGHNESS_RULES)}")
    permittivity = np.zeros(len(class_names), dtype=np.complex128)
    rms = np.zeros(len(class_names), dtype=np.float64)
    rows: dict[str, Any] = {}
    for i, name in enumerate(class_names):
        spec = class_binding[name]
        evaluation = materials[spec.itu_row].evaluate(frequency_hz, allow_extrapolation=allow_extrapolation)
        permittivity[i] = complex(evaluation.relative_permittivity_real, -evaluation.relative_permittivity_imag)
        prior = roughness[spec.roughness_class]
        rms[i] = reduce(prior)
        rows[name] = {
            "applicability": evaluation.applicability,
            "uncertainty_multiplier": evaluation.uncertainty_multiplier,
            "roughness_structure": prior.structure,
            "roughness_evidence_grade": prior.evidence_grade,
            "periodic_relief_excluded": bool(prior.periodic_component) and roughness_rule == FINISH_ONLY_RULE,
        }
    periodic_relief_excluded = roughness_rule == FINISH_ONLY_RULE
    rule_status = {
        FINISH_ONLY_RULE: "production",
        QUADRATURE_RULE: "historical_sensitivity",
        MASONRY_RULE: "research_only",
    }[roughness_rule]
    return MaterialTable(
        frequency_hz=float(frequency_hz),
        class_names=tuple(class_names),
        permittivity=permittivity,
        rms_height_m=rms,
        spec=class_binding,
        provenance={
            "material_source": materials.source,
            "roughness_source": roughness.source["title"],
            "class_rule": class_rule or GEOMETRIC_CLASS_RULE,
            "roughness_rule": roughness_rule,
            "periodic_relief_excluded": periodic_relief_excluded,
            "roughness_rule_provenance": {
                "rule": roughness_rule,
                "status": rule_status,
                "periodic_relief_excluded": periodic_relief_excluded,
            },
            "rows": rows,
        },
    )


_ROUGHNESS_RULES = {
    FINISH_ONLY_RULE: finish_only_rms_height,
    QUADRATURE_RULE: effective_rms_height,
    MASONRY_RULE: masonry_equivalent_rms_height,
}
