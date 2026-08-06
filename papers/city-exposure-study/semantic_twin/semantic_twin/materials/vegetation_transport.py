"""Production contract between vegetation semantics and radio transport.

Vegetation evidence describes two different physical things. Grass is a thin
cover on a ground interface. Shrubs, trees, and forest are lossy volumes in
air. Neither can be represented by assigning ``wood`` or a vacuum permittivity
to a support-mesh triangle.

This module keeps that distinction explicit. It reads the complete posterior
from the common surface atlas without reducing it to one winning label. In the
current scene it leaves the support surface unchanged. Grass has no validated
ground-cover interface model in this project, and the panorama atlas does not
contain closed canopy volumes. Woody evidence is therefore reported as volume
evidence that still needs geometry, not as an opaque surface.

When a later geometry stage supplies measured entry and exit points through a
closed canopy volume, :func:`evaluate_p833_segments` provides the P.833 energy
budget for each chord. It keeps every species candidate rather than choosing a
species from the labels ``shrub``, ``tree``, or ``forest``. Those labels do not
identify a P.833 species.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .binding import CLASS_NAMES
from .foliage import TABULATED_FREQUENCIES_GHZ, RetParameters, ret_parameter_candidates

P833_RECOMMENDATION_MIN_HZ = 30.0e6
P833_RECOMMENDATION_MAX_HZ = 100.0e9
P833_RET_MIN_HZ = min(TABULATED_FREQUENCIES_GHZ) * 1.0e9
P833_RET_MAX_HZ = max(TABULATED_FREQUENCIES_GHZ) * 1.0e9

GROUND_FORM = "ground_vegetation"
WOODY_FORM = "woody_canopy"
GRASS_SUBTYPE = "grass"
WOODY_SUBTYPES = ("shrub", "tree", "forest")

GROUND_SURFACE_POLICY = (
    "Keep the geometric ground interface. The project has no validated electromagnetic model for a grass layer, "
    "including its moisture, thickness, and soil substrate."
)
WOODY_VOLUME_POLICY = (
    "Keep woody vegetation as non-blocking volume evidence until registered closed canopy geometry supplies exact "
    "entry and exit points. Never bind it to wood, vacuum, or another support-surface material."
)


@dataclass(frozen=True)
class P833FrequencyAssessment:
    """Where one requested carrier lies relative to the P.833 RET tables."""

    frequency_hz: float
    recommendation_in_scope: bool
    table_relation: str
    lower_tabulated_hz: float | None
    upper_tabulated_hz: float | None
    nearest_tabulated_hz: float
    nearest_gap_octaves: float
    interpolation_required: bool
    extrapolation_required: bool
    parameter_method: str

    @property
    def ret_parameters_usable(self) -> bool:
        """Whether the RET table brackets this carrier without extrapolation."""
        return self.recommendation_in_scope and not self.extrapolation_required

    def as_dict(self) -> dict[str, Any]:
        return {
            "frequency_hz": self.frequency_hz,
            "recommendation_scope_hz": [P833_RECOMMENDATION_MIN_HZ, P833_RECOMMENDATION_MAX_HZ],
            "recommendation_in_scope": self.recommendation_in_scope,
            "ret_table_extent_hz": [P833_RET_MIN_HZ, P833_RET_MAX_HZ],
            "table_relation": self.table_relation,
            "lower_tabulated_hz": self.lower_tabulated_hz,
            "upper_tabulated_hz": self.upper_tabulated_hz,
            "nearest_tabulated_hz": self.nearest_tabulated_hz,
            "nearest_gap_octaves": self.nearest_gap_octaves,
            "interpolation_required": self.interpolation_required,
            "extrapolation_required": self.extrapolation_required,
            "ret_parameters_usable": self.ret_parameters_usable,
            "parameter_method": self.parameter_method,
        }


def assess_p833_frequency(frequency_hz: float) -> P833FrequencyAssessment:
    """Classify a carrier without hiding a gap in the recommendation tables.

    P.833 covers 30 MHz to 100 GHz through several separate models. The
    radiative energy transfer tables used for a participating medium cover only
    1.3 to 61.5 GHz and have a large 12.5 to 37 GHz gap. Inside that extent the
    recommendation asks for the nearest matching species row. The assessment
    still marks non-tabulated carriers as requiring interpolation because the
    selected row was not measured at the requested carrier.
    """
    frequency_hz = float(frequency_hz)
    if not np.isfinite(frequency_hz) or frequency_hz <= 0.0:
        raise ValueError("frequency must be finite and positive")
    table = np.asarray(TABULATED_FREQUENCIES_GHZ, dtype=np.float64) * 1.0e9
    exact = np.flatnonzero(np.isclose(table, frequency_hz, rtol=1.0e-12, atol=0.0))
    lower_values = table[table < frequency_hz]
    upper_values = table[table > frequency_hz]
    lower = float(lower_values[-1]) if lower_values.size else None
    upper = float(upper_values[0]) if upper_values.size else None
    nearest = float(table[np.argmin(np.abs(np.log2(frequency_hz / table)))])
    in_scope = P833_RECOMMENDATION_MIN_HZ <= frequency_hz <= P833_RECOMMENDATION_MAX_HZ

    if exact.size:
        relation = "tabulated"
        lower = upper = float(table[exact[0]])
        interpolate = extrapolate = False
    elif frequency_hz < P833_RET_MIN_HZ:
        relation = "below_ret_tables"
        interpolate = False
        extrapolate = True
    elif frequency_hz > P833_RET_MAX_HZ:
        relation = "above_ret_tables"
        interpolate = False
        extrapolate = True
    else:
        relation = "between_tabulated_frequencies"
        interpolate = True
        extrapolate = False
    return P833FrequencyAssessment(
        frequency_hz=frequency_hz,
        recommendation_in_scope=in_scope,
        table_relation=relation,
        lower_tabulated_hz=lower,
        upper_tabulated_hz=upper,
        nearest_tabulated_hz=nearest,
        nearest_gap_octaves=float(abs(np.log2(frequency_hz / nearest))),
        interpolation_required=interpolate,
        extrapolation_required=extrapolate,
        parameter_method="nearest complete species row in log frequency, as instructed by P.833 section 3.2.1.4",
    )


@dataclass(frozen=True)
class AtlasVegetationEvidence:
    """Mixture-preserving vegetation evidence for every sparse atlas cell."""

    triangle_id: np.ndarray
    texel_row: np.ndarray
    texel_column: np.ndarray
    support_weight: np.ndarray
    ground_probability: np.ndarray
    woody_probability: np.ndarray
    grass_probability: np.ndarray
    shrub_probability: np.ndarray
    tree_probability: np.ndarray
    forest_probability: np.ndarray
    ground_probability_off_ground: np.ndarray
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        count = np.asarray(self.triangle_id).size
        for name in (
            "texel_row",
            "texel_column",
            "support_weight",
            "ground_probability",
            "woody_probability",
            "grass_probability",
            "shrub_probability",
            "tree_probability",
            "forest_probability",
            "ground_probability_off_ground",
        ):
            value = np.asarray(getattr(self, name))
            if value.shape != (count,):
                raise ValueError(f"{name} must have one value per atlas cell")
            if name != "texel_row" and name != "texel_column" and np.any(~np.isfinite(value)):
                raise ValueError(f"{name} must be finite")
        probabilities = np.column_stack(
            (
                self.ground_probability,
                self.woody_probability,
                self.grass_probability,
                self.shrub_probability,
                self.tree_probability,
                self.forest_probability,
                self.ground_probability_off_ground,
            )
        )
        if np.any((probabilities < 0.0) | (probabilities > 1.0 + 1.0e-6)):
            raise ValueError("vegetation probabilities must lie in [0, 1]")
        if not self.provenance:
            raise ValueError("vegetation evidence must record its provenance")

    @property
    def has_ground_evidence(self) -> bool:
        return bool(np.any(self.ground_probability > 0.0))

    @property
    def has_woody_evidence(self) -> bool:
        return bool(np.any(self.woody_probability > 0.0))

    def report(self) -> dict[str, Any]:
        weight = np.asarray(self.support_weight, dtype=np.float64)

        def supported_mass(probability: np.ndarray) -> float:
            return float(np.dot(weight, np.asarray(probability, dtype=np.float64)))

        return {
            "cells": int(self.triangle_id.size),
            "support_weight": float(weight.sum()),
            "expected_supported_weight": {
                "ground_vegetation": supported_mass(self.ground_probability),
                "woody_canopy": supported_mass(self.woody_probability),
                "grass": supported_mass(self.grass_probability),
                "shrub": supported_mass(self.shrub_probability),
                "tree": supported_mass(self.tree_probability),
                "forest": supported_mass(self.forest_probability),
                "ground_vegetation_off_ground": supported_mass(self.ground_probability_off_ground),
            },
            "reduction": "none; all quantities are posterior mass",
            "provenance": dict(self.provenance),
        }


def vegetation_evidence_from_atlas(
    atlas: Any,
    geometric_face_class: np.ndarray,
) -> AtlasVegetationEvidence:
    """Extract grass and woody mixtures from a joint atlas without argmax."""
    geometric = np.asarray(geometric_face_class, dtype=np.int64)
    triangle_count = int(atlas.triangle_count)
    if geometric.shape != (triangle_count,):
        raise ValueError("geometric_face_class must have one value per support triangle")
    if geometric.size and (geometric.min() < 0 or geometric.max() >= len(CLASS_NAMES)):
        raise ValueError("geometric_face_class leaves the structural class vocabulary")

    triangle_ids = np.asarray(atlas.triangle_ids, dtype=np.int64)
    offsets = np.asarray(atlas.texel_offsets, dtype=np.int64)
    if offsets.shape != (triangle_ids.size + 1,):
        raise ValueError("atlas texel offsets do not index observed triangles")
    cell_triangle = np.repeat(triangle_ids, np.diff(offsets))
    cells = cell_triangle.size
    form_names = tuple(str(name) for name in atlas.vegetation_form_names)
    subtype_names = tuple(str(name) for name in atlas.vegetation_subtype_names)
    form = np.asarray(atlas.vegetation_form_posterior, dtype=np.float64)
    subtype = np.asarray(atlas.vegetation_subtype_posterior, dtype=np.float64)
    if form.shape != (cells, len(form_names)) or subtype.shape != (cells, len(subtype_names)):
        raise ValueError("atlas vegetation posterior does not match its vocabularies")
    if np.any(~np.isfinite(form)) or np.any(form < 0.0) or np.any(form.sum(axis=1) > 1.0 + 2.0e-6):
        raise ValueError("atlas vegetation form posterior is invalid")
    if np.any(~np.isfinite(subtype)) or np.any(subtype < 0.0) or np.any(subtype.sum(axis=1) > 1.0 + 2.0e-6):
        raise ValueError("atlas vegetation subtype posterior is invalid")

    def channel(values: np.ndarray, names: tuple[str, ...], name: str) -> np.ndarray:
        return values[:, names.index(name)] if name in names else np.zeros(cells, dtype=np.float64)

    ground = channel(form, form_names, GROUND_FORM)
    woody = channel(form, form_names, WOODY_FORM)
    grass = channel(subtype, subtype_names, GRASS_SUBTYPE)
    shrub = channel(subtype, subtype_names, "shrub")
    tree = channel(subtype, subtype_names, "tree")
    forest = channel(subtype, subtype_names, "forest")
    ground_face = geometric[cell_triangle] == CLASS_NAMES.index("ground")
    mesh_sha = str(getattr(atlas, "mesh_sha256", ""))
    return AtlasVegetationEvidence(
        triangle_id=cell_triangle,
        texel_row=np.asarray(atlas.texel_row, dtype=np.int16),
        texel_column=np.asarray(atlas.texel_column, dtype=np.int16),
        support_weight=np.asarray(atlas.support_weight, dtype=np.float64),
        ground_probability=ground,
        woody_probability=woody,
        grass_probability=grass,
        shrub_probability=shrub,
        tree_probability=tree,
        forest_probability=forest,
        ground_probability_off_ground=np.where(ground_face, 0.0, ground),
        provenance={
            "atlas_mesh_sha256": mesh_sha or None,
            "atlas_content_sha256": atlas.content_digest() if hasattr(atlas, "content_digest") else None,
            "form_vocabulary": list(form_names),
            "subtype_vocabulary": list(subtype_names),
            "surface_policy": GROUND_SURFACE_POLICY,
            "volume_policy": WOODY_VOLUME_POLICY,
        },
    )


@dataclass(frozen=True)
class VegetationTransportPlan:
    """What production transport may do with one atlas today."""

    evidence: AtlasVegetationEvidence
    ground_surface_model: str | None
    woody_volume_geometry: str | None
    support_surface_changed: bool
    support_surface_blocks_woody_evidence: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.report(),
            "ground": {
                "surface_model": self.ground_surface_model,
                "interface_changed": self.support_surface_changed,
                "policy": GROUND_SURFACE_POLICY,
            },
            "woody": {
                "volume_geometry": self.woody_volume_geometry,
                "support_surface_blocks_evidence": self.support_surface_blocks_woody_evidence,
                "policy": WOODY_VOLUME_POLICY,
            },
            "blockers": list(self.blockers),
            "required_data": [
                "a validated grass, moisture, soil, and layer-thickness interface model",
                "registered closed canopy volumes or exact path entry and exit points",
                "seasonal leaf state",
                "species evidence or an explicit P.833 species ensemble policy",
            ],
        }


def plan_vegetation_transport(
    atlas: Any,
    geometric_face_class: np.ndarray,
) -> VegetationTransportPlan:
    """Build the safe current plan. It changes no surface and adds no blocker."""
    evidence = vegetation_evidence_from_atlas(atlas, geometric_face_class)
    blockers: list[str] = []
    if evidence.has_ground_evidence:
        blockers.append("grass evidence present, but no validated ground-cover interface model is configured")
    if evidence.has_woody_evidence:
        blockers.append("woody evidence present, but the atlas supplies no closed canopy volume or path chords")
    if np.any(evidence.ground_probability_off_ground > 0.0):
        blockers.append("some ground-vegetation posterior lies on a non-ground support face and is diagnostic only")
    return VegetationTransportPlan(
        evidence=evidence,
        ground_surface_model=None,
        woody_volume_geometry=None,
        support_surface_changed=False,
        support_surface_blocks_woody_evidence=False,
        blockers=tuple(blockers),
    )


@dataclass(frozen=True)
class VegetationPathSegments:
    """Measured chords through registered closed vegetation volumes.

    Each row is one entry and exit pair for one traced path. A path may have
    several rows when it crosses several volumes. The segment length is derived
    from the points, so a caller cannot supply a canopy depth independently of
    the registered geometry.
    """

    path_index: np.ndarray
    volume_id: np.ndarray
    entry_point_m: np.ndarray
    exit_point_m: np.ndarray
    geometry_source: str
    geometry_sha256: str
    watertight: bool
    intersection_rule: str

    def __post_init__(self) -> None:
        count = np.asarray(self.path_index).size
        if np.asarray(self.path_index).shape != (count,) or not np.issubdtype(
            np.asarray(self.path_index).dtype, np.integer
        ):
            raise ValueError("path_index must be a one-dimensional integer array")
        if np.asarray(self.volume_id).shape != (count,):
            raise ValueError("volume_id must have one value per segment")
        if np.asarray(self.entry_point_m).shape != (count, 3) or np.asarray(self.exit_point_m).shape != (count, 3):
            raise ValueError("entry and exit points must have shape (segments, 3)")
        if np.any(~np.isfinite(self.entry_point_m)) or np.any(~np.isfinite(self.exit_point_m)):
            raise ValueError("entry and exit points must be finite")
        if count and np.any(np.asarray(self.path_index) < 0):
            raise ValueError("path_index cannot be negative")
        if any(not str(value) for value in np.asarray(self.volume_id).tolist()):
            raise ValueError("volume identifiers must be nonempty")
        if not self.geometry_source or not self.intersection_rule:
            raise ValueError("volume chords must name their geometry source and intersection rule")
        if len(self.geometry_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.geometry_sha256.lower()
        ):
            raise ValueError("geometry_sha256 must be a 64-character hexadecimal digest")
        if not self.watertight:
            raise ValueError("P.833 path chords require closed, watertight volume geometry")
        if np.any(self.length_m <= 0.0):
            raise ValueError("every vegetation chord must have positive length")

    @property
    def length_m(self) -> np.ndarray:
        return np.linalg.norm(np.asarray(self.exit_point_m) - np.asarray(self.entry_point_m), axis=1)

    @property
    def segment_count(self) -> int:
        return int(np.asarray(self.path_index).size)

    @property
    def path_count(self) -> int:
        return int(np.max(self.path_index) + 1) if self.segment_count else 0

    @classmethod
    def from_geometry_bytes(
        cls,
        *,
        path_index: np.ndarray,
        volume_id: np.ndarray,
        entry_point_m: np.ndarray,
        exit_point_m: np.ndarray,
        geometry_source: str,
        geometry_bytes: bytes,
        watertight: bool,
        intersection_rule: str,
    ) -> VegetationPathSegments:
        """Build a chord set and bind it to the exact volume artifact bytes."""
        return cls(
            path_index=np.asarray(path_index, dtype=np.int64),
            volume_id=np.asarray(volume_id),
            entry_point_m=np.asarray(entry_point_m, dtype=np.float64),
            exit_point_m=np.asarray(exit_point_m, dtype=np.float64),
            geometry_source=geometry_source,
            geometry_sha256=hashlib.sha256(geometry_bytes).hexdigest(),
            watertight=watertight,
            intersection_rule=intersection_rule,
        )


@dataclass(frozen=True)
class P833SegmentTransport:
    """Species ensemble energy budget for exact canopy path segments."""

    frequency: P833FrequencyAssessment
    candidates: tuple[RetParameters, ...]
    path_index: np.ndarray
    segment_length_m: np.ndarray
    direct_transmission: np.ndarray
    first_event_scatter: np.ndarray
    first_event_absorption: np.ndarray
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        shape = (len(self.candidates), np.asarray(self.path_index).size)
        for name in ("direct_transmission", "first_event_scatter", "first_event_absorption"):
            value = np.asarray(getattr(self, name))
            if value.shape != shape:
                raise ValueError(f"{name} must have shape (candidates, segments)")
            if np.any((value < 0.0) | (value > 1.0 + 1.0e-12)):
                raise ValueError(f"{name} must lie in [0, 1]")
        total = self.direct_transmission + self.first_event_scatter + self.first_event_absorption
        if not np.allclose(total, 1.0, atol=1.0e-12):
            raise ValueError("P.833 segment energy fractions must sum to one")

    def direct_transmission_by_path(self, path_count: int | None = None) -> np.ndarray:
        """Multiply straight-through power over every volume crossed by a path."""
        count = (
            int(path_count)
            if path_count is not None
            else (int(np.max(self.path_index) + 1) if self.path_index.size else 0)
        )
        if count < 0 or (self.path_index.size and np.max(self.path_index) >= count):
            raise ValueError("path_count does not cover every vegetation segment")
        result = np.ones((len(self.candidates), count), dtype=np.float64)
        for candidate in range(len(self.candidates)):
            np.multiply.at(result[candidate], self.path_index, self.direct_transmission[candidate])
        return result

    def energy_budget_by_path(
        self,
        path_count: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return direct, first-event scattered, and absorbed path fractions.

        Segments are consumed in their stored order. Energy scattered or
        absorbed in a later canopy is weighted by the direct energy that
        reached it. The three arrays conserve incident path power for every
        P.833 species candidate, including paths that cross several volumes.
        """
        count = (
            int(path_count)
            if path_count is not None
            else (int(np.max(self.path_index) + 1) if self.path_index.size else 0)
        )
        if count < 0 or (self.path_index.size and np.max(self.path_index) >= count):
            raise ValueError("path_count does not cover every vegetation segment")
        shape = (len(self.candidates), count)
        direct = np.ones(shape, dtype=np.float64)
        scatter = np.zeros(shape, dtype=np.float64)
        absorption = np.zeros(shape, dtype=np.float64)
        for segment, path in enumerate(np.asarray(self.path_index, dtype=np.int64)):
            arriving = direct[:, path].copy()
            scatter[:, path] += arriving * self.first_event_scatter[:, segment]
            absorption[:, path] += arriving * self.first_event_absorption[:, segment]
            direct[:, path] *= self.direct_transmission[:, segment]
        if not np.allclose(direct + scatter + absorption, 1.0, atol=2.0e-12):
            raise AssertionError("composed P.833 path energy does not conserve power")
        return direct, scatter, absorption

    def apply_to_path_power(
        self,
        incident_power: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """Apply the species-ensemble budget to traced path power.

        This is the production hook for a path solver with registered
        watertight canopy chords. It returns one row per P.833 species
        candidate. No unsupported mean species is chosen. Scattered power is a
        source term for a volume solver, not received power.
        """
        power = np.asarray(incident_power, dtype=np.float64)
        if power.ndim != 1 or np.any(~np.isfinite(power)) or np.any(power < 0.0):
            raise ValueError("incident_power must be a finite nonnegative vector")
        direct, scatter, absorption = self.energy_budget_by_path(path_count=power.size)
        return {
            "direct_power": direct * power[None, :],
            "first_event_scatter_source_power": scatter * power[None, :],
            "absorbed_power": absorption * power[None, :],
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency.as_dict(),
            "candidates": [candidate.provenance() for candidate in self.candidates],
            "segments": int(self.path_index.size),
            "paths": int(np.max(self.path_index) + 1) if self.path_index.size else 0,
            "segment_length_m": {
                "minimum": float(self.segment_length_m.min()) if self.segment_length_m.size else 0.0,
                "median": float(np.median(self.segment_length_m)) if self.segment_length_m.size else 0.0,
                "maximum": float(self.segment_length_m.max()) if self.segment_length_m.size else 0.0,
            },
            "provenance": dict(self.provenance),
        }


def evaluate_p833_segments(
    segments: VegetationPathSegments,
    frequency_hz: float,
    *,
    leaf_state: str = "in_leaf",
    allow_ret_extrapolation: bool = False,
) -> P833SegmentTransport:
    """Evaluate P.833 extinction, first scatter, and absorption on real chords.

    The direct term can attenuate an already traced finite path. The scattered
    term is reported but must be transported by a participating-medium solver
    before it can contribute at the receiver. This function never folds it
    back into direct power.
    """
    assessment = assess_p833_frequency(frequency_hz)
    if not assessment.recommendation_in_scope:
        raise ValueError("frequency lies outside the stated 30 MHz to 100 GHz scope of Recommendation ITU-R P.833")
    if assessment.extrapolation_required and not allow_ret_extrapolation:
        raise ValueError(
            "frequency lies outside the 1.3 to 61.5 GHz P.833 radiative-energy-transfer tables; "
            "set allow_ret_extrapolation=True only for an explicitly labelled sensitivity run"
        )
    candidates = ret_parameter_candidates(frequency_hz, leaf_state=leaf_state)
    if not candidates:
        raise ValueError(f"no complete P.833 RET rows exist for leaf_state={leaf_state!r}")
    length = np.asarray(segments.length_m, dtype=np.float64)
    extinction = np.asarray([candidate.sigma_tau_per_m for candidate in candidates], dtype=np.float64)[:, None]
    albedo = np.asarray([candidate.albedo for candidate in candidates], dtype=np.float64)[:, None]
    direct = np.exp(-extinction * length[None, :])
    interaction = 1.0 - direct
    scatter = albedo * interaction
    absorption = (1.0 - albedo) * interaction
    return P833SegmentTransport(
        frequency=assessment,
        candidates=candidates,
        path_index=np.asarray(segments.path_index, dtype=np.int64),
        segment_length_m=length,
        direct_transmission=direct,
        first_event_scatter=scatter,
        first_event_absorption=absorption,
        provenance={
            "recommendation": "ITU-R P.833-10 (09/2021), section 3.2.1.4, Tables 5 to 8",
            "geometry_source": segments.geometry_source,
            "geometry_sha256": segments.geometry_sha256,
            "watertight": segments.watertight,
            "intersection_rule": segments.intersection_rule,
            "leaf_state": leaf_state,
            "species_policy": "all species with a complete row; semantic shrub/tree/forest labels do not choose species",
            "direct_term": "Beer-Lambert exp(-sigma_tau times measured chord length)",
            "scatter_term": "first-event energy only; a volume transport solver must propagate it",
            "ret_extrapolation_allowed": allow_ret_extrapolation,
        },
    )


__all__ = [
    "GROUND_SURFACE_POLICY",
    "P833_RECOMMENDATION_MAX_HZ",
    "P833_RECOMMENDATION_MIN_HZ",
    "P833_RET_MAX_HZ",
    "P833_RET_MIN_HZ",
    "WOODY_VOLUME_POLICY",
    "AtlasVegetationEvidence",
    "P833FrequencyAssessment",
    "P833SegmentTransport",
    "VegetationPathSegments",
    "VegetationTransportPlan",
    "assess_p833_frequency",
    "evaluate_p833_segments",
    "plan_vegetation_transport",
    "vegetation_evidence_from_atlas",
]
