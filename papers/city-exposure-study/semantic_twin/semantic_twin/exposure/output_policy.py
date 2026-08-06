"""Retention profiles for production-walk outputs.

The profiles describe what a walk keeps after it finishes.  They do not write
files and they do not change a trace.  Field names below come from the current
locations JSONL rows, spectra NPZ, production manifest, CDF checkpoint, and
Blender payload schemas.

``minimal`` keeps the sealed run identity and the two body values needed for
the headline result.  ``standard`` also keeps one angular spectrum per source
model that was traced and the input facts needed to re-couple those models or
compute new observables without another trace.  It does not synthesize a new
source law.  ``full`` adds the bounded path record, audit data, Blender arrays,
and image evidence used to explain one run.

The body field is named ``*_sar_wb_w_kg`` in the current row schema.  This
module does not create a separate ``wbSAR`` key.  A producer must supply that
field from the AEGIS body result before a minimal output can be sealed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


class OutputProfile(str, Enum):
    """A named amount of data retained from one production walk."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"

    @property
    def rank(self) -> int:
        """Return the profile order used by the inclusion checks."""
        return (OutputProfile.MINIMAL, OutputProfile.STANDARD, OutputProfile.FULL).index(self)

    def includes(self, other: OutputProfile | str) -> bool:
        """Return whether this profile includes ``other``."""
        return self.rank >= coerce_profile(other).rank


class ArtifactClass(str, Enum):
    """The role an output artifact plays in a production walk."""

    SEALED_PROVENANCE = "sealed_provenance"
    STANDPOINT_SCALARS = "standpoint_scalars"
    RESTART_FACTS = "restart_facts"
    STOPPING_FACTS = "stopping_facts"
    ANGULAR_SPECTRUM = "angular_spectrum"
    BODY_COUPLING = "body_coupling"
    AUDIT = "audit"
    BLENDER = "blender"
    PATH_EVIDENCE = "path_evidence"


class RetentionCost(str, Enum):
    """Relative disk and transfer cost of keeping an artifact."""

    TINY = "tiny"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @property
    def rank(self) -> int:
        """Return a comparable retention-cost rank."""
        return tuple(RetentionCost).index(self)


class RecomputationCost(str, Enum):
    """Relative cost of rebuilding an artifact after it is discarded."""

    NONE = "none"
    CHEAP = "cheap"
    BODY_COUPLING = "body_coupling"
    TRACE = "trace"
    TRACE_AND_EVIDENCE = "trace_and_evidence"

    @property
    def rank(self) -> int:
        """Return a comparable recomputation-cost rank."""
        return tuple(RecomputationCost).index(self)


# The manifest fields are the fields written by ``exposure.execution._manifest``
# and sealed by ``_output_generation``.  ``wall_seconds`` is written only after
# the streamed rows finish, so it is optional while a run is in progress.
SEALED_PROVENANCE_FIELDS = (
    "generator",
    "created_utc",
    "site",
    "mesh",
    "mesh_sha256",
    "mesh_triangles",
    "crop_radius_m",
    "ground_datum_m",
    "ground_datum_source",
    "ground_datum",
    "reference_s0_w_m2",
    "trace_config",
    "surface_binding",
    "semantic_binding",
    "class_area_fractions",
    "class_area_fraction_basis",
    "frequency_note",
    "crop_bound_note",
    "walk",
    "locations_requested",
    "locations_traced",
    "illumination_models",
    "body",
    "variant",
    "transport",
    "python",
    "storage_policy",
    "run_digest",
    "run",
    "output_generation",
)
SEALED_PROVENANCE_OPTIONAL_FIELDS = ("wall_seconds", "stage_seconds")

# These are the exact body-result suffixes currently used in one JSONL row.
# The prefixes are source-model names such as ``rooftop``.
SAB_MAX_FIELD = "{model}_peak_sab_w_m2"
WB_SAR_FIELD = "{model}_sar_wb_w_kg"

# These are the exact identity and scalar keys currently used in one JSONL row.
STANDPOINT_REQUIRED_FIELDS = (
    "index",
    "x",
    "y",
    "z",
    "ground_z_m",
    "seconds",
    SAB_MAX_FIELD,
    WB_SAR_FIELD,
)
STANDPOINT_OPTIONAL_FIELDS = (
    "point_kind",
    "sky_fraction",
    "mean_bounces",
    "mean_excess_delay_ns",
    "escaped_fraction",
    "truncated_throughput_share",
    "chi_{model}",
    "chi_{model}_direct",
    "multipath_gain_{model}",
    "{model}_reference_s0_w_m2",
    "{model}_arriving_power_density_w_m2",
    "{model}_susceptibility",
    "{model}_mean_sab_w_m2",
    "{model}_absorbed_power_w",
)

# The CDF campaign records these exact top-level stopping facts.  A single
# production walk can retain the same shape with one empty ``looks`` list.
RESTART_FIELDS = (
    "output_generation",
    "locations_requested",
    "locations_traced",
    "run_digest",
    "run",
    "trace_config",
    "walk",
    "storage_policy",
)
RESTART_OPTIONAL_FIELDS = ("created_utc", "wall_seconds")
# ``CheckpointStore`` keeps these keys in its append-only index.  Keeping the
# index is small, and it records the exact prefix that a restart may use.
CHECKPOINT_INDEX_FIELDS = (
    "schema",
    "identity_sha256",
    "standpoint_array_sha256",
    "tissue_database_sha256",
    "model_names",
    "planned_seeds",
    "local_grid",
    "local_grid_dtype",
    "local_grid_sha256",
    "solid_angle",
    "entries",
)
CHECKPOINT_SHARD_FIELDS = (
    "schema",
    "replica",
    "base_seed",
    "chi",
    "chi_direct",
    "body_peak_rooftop",
    "body_mean_rooftop",
    "body_sab_rooftop",
    "trace_seconds",
    "rho",
)
STOPPING_FIELDS = (
    "schema",
    "independent_unit",
    "aggregation",
    "bootstrap",
    "planned_look_coverage",
    "thresholds",
    "looks",
    "stopped",
    "stop_at_replicas",
    "cap_reached",
)
STOPPING_OPTIONAL_FIELDS = (
    "route_sample",
    "direct_susceptibility",
    "body_peak_rooftop",
    "body_mean_linearity_check",
    "body_peak_retained_field_check",
)

# Standard/full production writes one angular spectrum per source model traced
# by the run.  ``rho_rooftop`` remains the compatibility name required by old
# readers and manifests.  It is a duplicate only when rooftop is among the
# traced models, which the production executor requires.
ANGULAR_SPECTRUM_FIELDS = ("index", "local_grid", "solid_angle", "rho_{model}")
ANGULAR_SPECTRUM_OPTIONAL_FIELDS = ("rho_rooftop",)
RHO_ACCUMULATOR_FIELDS = ("rho",)
SOURCE_LAW_FIELDS = ("illumination_models", "reference_s0_w_m2", "trace_config", "run")

# These fields are enough to compose the stored spectrum with AEGIS again.
BODY_COUPLING_FIELDS = (
    "body",
    "local_grid",
    "solid_angle",
    "rho_{model}",
    "reference_s0_w_m2",
)
BODY_COUPLING_OPTIONAL_FIELDS = ("body_vertices", "body_faces")

# Blender's production payload writes these names.  The path buffer is bounded,
# so it is an explanatory trace and never a replacement for the exposure rows.
BLENDER_FIELDS = (
    "mesh_vertices",
    "mesh_faces",
    "mesh_face_class",
    "walk_points",
    "walk_ground_z_m",
    "walk_chi_{model}",
    "walk_peak_sab_{model}",
    "local_grid",
    "rho_{model}",
    "body_vertices",
    "body_faces",
    "body_sab_w_m2",
)
BLENDER_OPTIONAL_FIELDS = (
    "mesh_face_source",
    "mesh_face_index",
    "support_full_vertices",
    "support_full_faces",
    "support_full_face_class",
    "support_full_face_source",
    "support_full_face_index",
    "local_grid_faces",
    "hero_index",
    "hero_point",
    "network_{model}",
    "rim_offset_m",
    "rim_azimuth_rad",
    "rim_alpha_rad",
    "rim_distance_m",
    "rim_weight",
    "rim_found",
)
PATH_FIELDS = (
    "path_vertices",
    "path_offsets",
    "path_throughput",
    "path_face_class",
    "path_exit_direction",
    "path_bounces",
    "path_termination",
)
PATH_OPTIONAL_FIELDS = (
    "nee_path_index",
    "nee_vertex_index",
    "nee_origin_m",
    "nee_site_m",
    "nee_azimuth_index",
    "nee_weight",
    "nee_blocked",
    "nee_paths",
)
AUDIT_FIELDS = (
    "output_generation",
    "run_digest",
    "trace_config",
    "surface_binding",
    "semantic_binding",
    "illumination_models",
    "body",
    "walk",
    "transport",
)
EVIDENCE_PREFIX_FIELDS = (
    "fishnet_",
    "support_evidence_",
    "rejected_",
    "depth_mesh_",
    "depth_monocular_",
    "pano_",
    "body_layer_",
    "evidence_camera",
)
AUDIT_OPTIONAL_FIELDS = (
    "hero",
    "walk_summary",
    "evidence",
    "storage_note",
    "records",
    "admission",
) + EVIDENCE_PREFIX_FIELDS


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """Describe one retained artifact and its profile membership."""

    name: str
    artifact_class: ArtifactClass
    retention_cost: RetentionCost
    recomputation_cost: RecomputationCost
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    profiles: frozenset[OutputProfile] = frozenset()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("artifact name cannot be empty")
        if not self.profiles:
            raise ValueError(f"artifact {self.name!r} belongs to no output profile")
        required = set(self.required_fields)
        optional = set(self.optional_fields)
        if len(required) != len(self.required_fields):
            raise ValueError(f"artifact {self.name!r} repeats a required field")
        if len(optional) != len(self.optional_fields):
            raise ValueError(f"artifact {self.name!r} repeats an optional field")
        overlap = required & optional
        if overlap:
            raise ValueError(f"artifact {self.name!r} lists fields as both required and optional: {sorted(overlap)}")

    def included_in(self, profile: OutputProfile | str) -> bool:
        """Return whether this artifact is retained by ``profile``."""
        selected = coerce_profile(profile)
        return selected in self.profiles

    def fields(
        self,
        profile: OutputProfile | str | None = None,
        *,
        models: Iterable[str] = (),
        include_optional: bool = True,
    ) -> tuple[str, ...]:
        """Return this artifact's exact fields, expanding ``{model}`` names.

        ``profile`` checks membership but does not alter the field list.  A
        profile controls whether the artifact is kept.  The optional fields
        describe fields that are present when a richer producer writes them.
        """
        if profile is not None and not self.included_in(profile):
            raise ValueError(f"artifact {self.name!r} is not included in {coerce_profile(profile).value}")
        fields = self.required_fields + (self.optional_fields if include_optional else ())
        return expand_model_fields(fields, models)


@dataclass(frozen=True, slots=True)
class OutputProfileSpec:
    """Describe the artifacts retained by one output profile."""

    profile: OutputProfile
    artifact_names: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        if len(set(self.artifact_names)) != len(self.artifact_names):
            raise ValueError(f"{self.profile.value} repeats an artifact")

    @property
    def artifacts(self) -> tuple[ArtifactSpec, ...]:
        """Return the immutable artifact descriptions for this profile."""
        return tuple(ARTIFACTS[name] for name in self.artifact_names)

    def includes(self, artifact: str | ArtifactSpec) -> bool:
        """Return whether this profile retains ``artifact``."""
        name = artifact.name if isinstance(artifact, ArtifactSpec) else artifact
        return name in self.artifact_names

    def fields(self, *, models: Iterable[str] = (), include_optional: bool = True) -> tuple[str, ...]:
        """Return the unique field names supplied by every retained artifact."""
        result: list[str] = []
        seen: set[str] = set()
        for artifact in self.artifacts:
            for field in artifact.fields(models=models, include_optional=include_optional):
                if field not in seen:
                    result.append(field)
                    seen.add(field)
        return tuple(result)


def coerce_profile(value: OutputProfile | str) -> OutputProfile:
    """Convert a profile name to :class:`OutputProfile`."""
    if isinstance(value, OutputProfile):
        return value
    try:
        return OutputProfile(str(value))
    except ValueError as error:
        raise ValueError(f"unknown output profile {value!r}") from error


def expand_model_fields(fields: Iterable[str], models: Iterable[str]) -> tuple[str, ...]:
    """Expand ``{model}`` field templates for the declared source models."""
    model_names = tuple(str(model) for model in models)
    if len(set(model_names)) != len(model_names):
        raise ValueError("models must be unique")
    expanded: list[str] = []
    for field in fields:
        if "{model}" not in field:
            expanded.append(field)
        else:
            expanded.extend(field.replace("{model}", model) for model in model_names)
    return tuple(dict.fromkeys(expanded))


_ALL_PROFILES = frozenset(OutputProfile)
_STANDARD_PROFILES = frozenset((OutputProfile.STANDARD, OutputProfile.FULL))
_FULL_PROFILE = frozenset((OutputProfile.FULL,))


ARTIFACTS: Mapping[str, ArtifactSpec] = MappingProxyType(
    {
        "sealed_provenance": ArtifactSpec(
            "sealed_provenance",
            ArtifactClass.SEALED_PROVENANCE,
            RetentionCost.TINY,
            RecomputationCost.TRACE,
            SEALED_PROVENANCE_FIELDS,
            SEALED_PROVENANCE_OPTIONAL_FIELDS,
            _ALL_PROFILES,
            "The manifest and its output-generation seal identify one exact result.",
        ),
        "standpoint_scalars": ArtifactSpec(
            "standpoint_scalars",
            ArtifactClass.STANDPOINT_SCALARS,
            RetentionCost.LOW,
            RecomputationCost.TRACE,
            STANDPOINT_REQUIRED_FIELDS,
            STANDPOINT_OPTIONAL_FIELDS,
            _ALL_PROFILES,
            "Per-location rows, including wbSAR and peak absorbed power density.",
        ),
        "restart_facts": ArtifactSpec(
            "restart_facts",
            ArtifactClass.RESTART_FACTS,
            RetentionCost.TINY,
            RecomputationCost.TRACE,
            RESTART_FIELDS,
            RESTART_OPTIONAL_FIELDS,
            _ALL_PROFILES,
            "Counts, identity, and publication facts needed for safe resume.",
        ),
        "checkpoint_index": ArtifactSpec(
            "checkpoint_index",
            ArtifactClass.RESTART_FACTS,
            RetentionCost.TINY,
            RecomputationCost.TRACE,
            CHECKPOINT_INDEX_FIELDS,
            (),
            _ALL_PROFILES,
            "The append-only checkpoint index and its committed replica prefix.",
        ),
        "checkpoint_shards": ArtifactSpec(
            "checkpoint_shards",
            ArtifactClass.RESTART_FACTS,
            RetentionCost.HIGH,
            RecomputationCost.TRACE,
            CHECKPOINT_SHARD_FIELDS,
            (),
            _FULL_PROFILE,
            "Per-replica fields needed to rebuild the complete CDF checkpoint.",
        ),
        "stopping_facts": ArtifactSpec(
            "stopping_facts",
            ArtifactClass.STOPPING_FACTS,
            RetentionCost.TINY,
            RecomputationCost.TRACE,
            STOPPING_FIELDS,
            STOPPING_OPTIONAL_FIELDS,
            _ALL_PROFILES,
            "CDF looks and stop state from the fixed-walk stopping record.",
        ),
        "angular_spectra": ArtifactSpec(
            "angular_spectra",
            ArtifactClass.ANGULAR_SPECTRUM,
            RetentionCost.MODERATE,
            RecomputationCost.TRACE,
            ANGULAR_SPECTRUM_FIELDS,
            ANGULAR_SPECTRUM_OPTIONAL_FIELDS,
            _STANDARD_PROFILES,
            "Per-standpoint angular power spectra and their shared local grid.",
        ),
        "source_law_facts": ArtifactSpec(
            "source_law_facts",
            ArtifactClass.ANGULAR_SPECTRUM,
            RetentionCost.TINY,
            RecomputationCost.TRACE,
            SOURCE_LAW_FIELDS,
            (),
            _STANDARD_PROFILES,
            "Declared source laws and trace settings needed to interpret spectra.",
        ),
        "rho_accumulator": ArtifactSpec(
            "rho_accumulator",
            ArtifactClass.ANGULAR_SPECTRUM,
            RetentionCost.MODERATE,
            RecomputationCost.TRACE,
            RHO_ACCUMULATOR_FIELDS,
            ("local_grid", "solid_angle", "model_names", "base_seed", "replica"),
            _STANDARD_PROFILES,
            "Running per-model angular transfer sums from completed replicas.",
        ),
        "body_coupling_inputs": ArtifactSpec(
            "body_coupling_inputs",
            ArtifactClass.BODY_COUPLING,
            RetentionCost.LOW,
            RecomputationCost.BODY_COUPLING,
            BODY_COUPLING_FIELDS,
            BODY_COUPLING_OPTIONAL_FIELDS,
            _STANDARD_PROFILES,
            "Inputs for recomputing AEGIS body coupling without another trace.",
        ),
        "audit_products": ArtifactSpec(
            "audit_products",
            ArtifactClass.AUDIT,
            RetentionCost.MODERATE,
            RecomputationCost.TRACE_AND_EVIDENCE,
            AUDIT_FIELDS,
            AUDIT_OPTIONAL_FIELDS,
            _FULL_PROFILE,
            "Identity, hero summaries, and evidence decisions used in review.",
        ),
        "blender_payload": ArtifactSpec(
            "blender_payload",
            ArtifactClass.BLENDER,
            RetentionCost.HIGH,
            RecomputationCost.TRACE_AND_EVIDENCE,
            BLENDER_FIELDS,
            BLENDER_OPTIONAL_FIELDS,
            _FULL_PROFILE,
            "Arrays consumed by the propagation Blender exporter.",
        ),
        "path_evidence": ArtifactSpec(
            "path_evidence",
            ArtifactClass.PATH_EVIDENCE,
            RetentionCost.HIGH,
            RecomputationCost.TRACE_AND_EVIDENCE,
            PATH_FIELDS,
            PATH_OPTIONAL_FIELDS,
            _FULL_PROFILE,
            "A bounded PathRecord and selected next-event evidence arrays.",
        ),
    }
)


PROFILES: Mapping[OutputProfile, OutputProfileSpec] = MappingProxyType(
    {
        OutputProfile.MINIMAL: OutputProfileSpec(
            OutputProfile.MINIMAL,
            (
                "sealed_provenance",
                "standpoint_scalars",
                "restart_facts",
                "checkpoint_index",
                "stopping_facts",
            ),
            "Sealed identity, headline body values, and restart/stopping facts.",
        ),
        OutputProfile.STANDARD: OutputProfileSpec(
            OutputProfile.STANDARD,
            (
                "sealed_provenance",
                "standpoint_scalars",
                "restart_facts",
                "checkpoint_index",
                "stopping_facts",
                "angular_spectra",
                "source_law_facts",
                "rho_accumulator",
                "body_coupling_inputs",
            ),
            "Minimal output plus reusable spectra and body-coupling inputs.",
        ),
        OutputProfile.FULL: OutputProfileSpec(
            OutputProfile.FULL,
            (
                "sealed_provenance",
                "standpoint_scalars",
                "restart_facts",
                "checkpoint_index",
                "stopping_facts",
                "angular_spectra",
                "source_law_facts",
                "rho_accumulator",
                "body_coupling_inputs",
                "checkpoint_shards",
                "audit_products",
                "blender_payload",
                "path_evidence",
            ),
            "Standard output plus audit, Blender, path, and evidence products.",
        ),
    }
)


def profile(value: OutputProfile | str) -> OutputProfileSpec:
    """Return the named immutable profile specification."""
    return PROFILES[coerce_profile(value)]


def artifact(value: str) -> ArtifactSpec:
    """Return the named immutable artifact specification."""
    try:
        return ARTIFACTS[value]
    except KeyError as error:
        raise ValueError(f"unknown output artifact {value!r}") from error


def profile_names(value: OutputProfile | str) -> tuple[str, ...]:
    """Return artifact names in the named profile."""
    return profile(value).artifact_names


# Short aliases make the registry convenient to use from drivers while keeping
# the descriptive names above available to schema and audit code.
Profile = OutputProfile
Artifact = ArtifactSpec
ProfileSpec = OutputProfileSpec
ArtifactKind = ArtifactClass
OutputArtifact = ArtifactSpec
OUTPUT_PROFILES = PROFILES
OUTPUT_ARTIFACTS = ARTIFACTS
MINIMAL = OutputProfile.MINIMAL
STANDARD = OutputProfile.STANDARD
FULL = OutputProfile.FULL
get_profile = profile
get_artifact = artifact

__all__ = [
    "Artifact",
    "ArtifactClass",
    "ArtifactKind",
    "ArtifactSpec",
    "ARTIFACTS",
    "OUTPUT_ARTIFACTS",
    "OUTPUT_PROFILES",
    "OutputProfile",
    "OutputArtifact",
    "OutputProfileSpec",
    "PROFILES",
    "Profile",
    "ProfileSpec",
    "MINIMAL",
    "STANDARD",
    "FULL",
    "RecomputationCost",
    "RetentionCost",
    "artifact",
    "get_artifact",
    "get_profile",
    "coerce_profile",
    "expand_model_fields",
    "profile",
    "profile_names",
    "ANGULAR_SPECTRUM_FIELDS",
    "AUDIT_FIELDS",
    "BLENDER_FIELDS",
    "BODY_COUPLING_FIELDS",
    "CHECKPOINT_INDEX_FIELDS",
    "CHECKPOINT_SHARD_FIELDS",
    "EVIDENCE_PREFIX_FIELDS",
    "RHO_ACCUMULATOR_FIELDS",
    "PATH_FIELDS",
    "RESTART_FIELDS",
    "SEALED_PROVENANCE_FIELDS",
    "SAB_MAX_FIELD",
    "STANDPOINT_REQUIRED_FIELDS",
    "STOPPING_FIELDS",
    "WB_SAR_FIELD",
]
