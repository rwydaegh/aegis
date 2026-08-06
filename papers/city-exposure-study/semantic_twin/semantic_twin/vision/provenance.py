"""What saw a surface, and how well.

Every other question this package answers is downstream of this one. A material
label is worth what the photograph behind it is worth, and the photograph is
worth what its pose is worth. Until now none of that travelled with the label.

The study has 83 registered poses. Twenty six of them put the camera inside a
building, and the skyline residual, which is the number every gate was written
against, cannot see it: a camera driven through a wall matches the inside of
that wall and scores well. Six of the twenty six pass the residual gate. So a
single residual is not a registration quality, and this module refuses to
pretend it is.

Three types, in the order a reader meets them.

:class:`Registration` is one camera's pose quality, read off the file the
registration wrote. It carries the residual, the seed ensemble spread, and the
independent sky conflict, and its verdict needs all three.

:class:`ViewProvenance` names one look: which site, which camera, which
provider, which segmenter, and the registration behind it.

:class:`EvidenceOrigin` is what a block of surface evidence has to carry before
it is allowed to exist. Constructing one without a channel, a projection rule
and, for the image channels, at least one look, raises.

:func:`survey` walks the panoramas on disk and counts, per site, how many poses
exist, how many are admitted, and how many are inside the geometry. That is the
query the audit had to be written by hand.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .. import paths, sites

#: How a pose was obtained.
SKYLINE_ENSEMBLE = "skyline_ensemble"
PROVIDER_METADATA = "provider_metadata"
UNREGISTERED = "unregistered"

#: Sources of surface evidence. ``NO_IMAGE`` is a real answer and the most
#: common one: the eleven city headline ran with the orientation rule, so every
#: surface in it would report ``NO_IMAGE`` if it were asked.
PANORAMA_ENTITY = "panorama_entity"
PANORAMA_MATERIAL = "panorama_material"
TILE_TEXTURE = "tile_texture"
FACADE_VLM = "facade_vlm"
NO_IMAGE = "no_image"

CHANNELS: tuple[str, ...] = (
    PANORAMA_ENTITY,
    PANORAMA_MATERIAL,
    TILE_TEXTURE,
    FACADE_VLM,
    NO_IMAGE,
)

#: Channels whose evidence came through a camera, so a pose stands behind every
#: label and the origin has to name it. The tile texture is deliberately not one
#: of these: it is bound to the geometry by its own UV map with no pose in
#: between, which is why ``texture.build_texture_evidence`` sets its
#: registration quality to one.
CAMERA_CHANNELS: frozenset[str] = frozenset({PANORAMA_ENTITY, PANORAMA_MATERIAL, FACADE_VLM})

#: How image evidence reached a triangle. Four rules are in the repository and
#: they do not agree on resolution, so which one spoke is part of the answer.
FACE_CENTROID = "face_centroid"
ADAPTIVE_TILES = "adaptive_tiles"
FISHNET_CUT = "fishnet_cut"
EQUIRECTANGULAR_RAYCAST = "equirectangular_raycast"
TILE_UV = "tile_uv"
NO_PROJECTION = "none"

PROJECTIONS: tuple[str, ...] = (
    FACE_CENTROID,
    ADAPTIVE_TILES,
    FISHNET_CUT,
    EQUIRECTANGULAR_RAYCAST,
    TILE_UV,
    NO_PROJECTION,
)


LEGACY_ADMISSION_GATE_VERSION = "registration-admission-v1"
ADMISSION_GATE_VERSION = "registration-admission-v2"

SKY_CONFLICT_CLEAR = "clear"
SKY_CONFLICT_LARGE_MISMATCH = "large sky-mesh mismatch"
SKY_CONFLICT_INSIDE_GEOMETRY = "inside the geometry"
SKY_CONFLICT_UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdmissionGate:
    """The production tests a pose has to pass, and their versioned policy.

    The defaults are the version-2 production contract. They are
    carried as an object rather than as three loose keyword arguments because a
    coverage number is only comparable between sites when the gate was the same,
    and a gate spread over three call sites is one nobody can quote.
    """

    version: str = ADMISSION_GATE_VERSION
    max_residual_deg: float = 4.0
    max_sky_conflict: float = 0.5
    min_conflict_range_m: float = 2.0
    require_complete_sky_diagnostics: bool = True
    require_interior_optimum: bool = True

    def __post_init__(self) -> None:
        if self.version not in (LEGACY_ADMISSION_GATE_VERSION, ADMISSION_GATE_VERSION):
            raise ValueError(f"unsupported admission gate version: {self.version!r}")
        expected_policy = {
            LEGACY_ADMISSION_GATE_VERSION: (False, False),
            ADMISSION_GATE_VERSION: (True, True),
        }[self.version]
        actual_policy = (self.require_complete_sky_diagnostics, self.require_interior_optimum)
        if actual_policy != expected_policy:
            raise ValueError(f"{self.version} requires diagnostic/boundary policy {expected_policy}")
        if self.max_residual_deg <= 0.0:
            raise ValueError("max_residual_deg must be positive")
        if not 0.0 < self.max_sky_conflict <= 1.0:
            raise ValueError("max_sky_conflict must lie in (0, 1]")
        if self.min_conflict_range_m <= 0.0:
            raise ValueError("min_conflict_range_m must be positive")

    @classmethod
    def legacy_v1(
        cls,
        *,
        max_residual_deg: float = 4.0,
        max_sky_conflict: float = 0.5,
        min_conflict_range_m: float = 2.0,
    ) -> AdmissionGate:
        """The named policy used by sealed artifacts built before the boundary gate.

        New builds use :class:`AdmissionGate` directly. This constructor exists
        only so an old manifest can be checked under the policy it records.
        """
        return cls(
            version=LEGACY_ADMISSION_GATE_VERSION,
            max_residual_deg=max_residual_deg,
            max_sky_conflict=max_sky_conflict,
            min_conflict_range_m=min_conflict_range_m,
            require_complete_sky_diagnostics=False,
            require_interior_optimum=False,
        )

    @classmethod
    def from_dict(cls, document: dict[str, Any] | None) -> AdmissionGate:
        """Restore a gate from its manifest stamp.

        An absent version means version 2. Version 1 must therefore be named
        explicitly, except where a caller has independently identified a
        sealed pre-version artifact and uses :meth:`legacy_v1`.
        """
        values = {} if document is None else dict(document)
        version = str(values.get("version", ADMISSION_GATE_VERSION))
        policy = {
            LEGACY_ADMISSION_GATE_VERSION: (False, False),
            ADMISSION_GATE_VERSION: (True, True),
        }.get(version)
        if policy is None:
            raise ValueError(f"unsupported admission gate version: {version!r}")
        return cls(
            version=version,
            max_residual_deg=float(values.get("max_residual_deg", 4.0)),
            max_sky_conflict=float(values.get("max_sky_conflict", 0.5)),
            min_conflict_range_m=float(values.get("min_conflict_range_m", 2.0)),
            require_complete_sky_diagnostics=bool(values.get("require_complete_sky_diagnostics", policy[0])),
            require_interior_optimum=bool(values.get("require_interior_optimum", policy[1])),
        )

    def as_dict(self) -> dict[str, Any]:
        """A complete policy stamp for reports and production manifests."""
        return {
            "version": self.version,
            "max_residual_deg": self.max_residual_deg,
            "max_sky_conflict": self.max_sky_conflict,
            "min_conflict_range_m": self.min_conflict_range_m,
            "require_complete_sky_diagnostics": self.require_complete_sky_diagnostics,
            "require_interior_optimum": self.require_interior_optimum,
            "inside_geometry_rule": (
                "sky_with_mesh_hit_fraction > max_sky_conflict AND conflict_median_range_m < min_conflict_range_m"
            ),
        }


@dataclass(frozen=True)
class Verdict:
    """Whether one pose is usable, and which test decided."""

    admitted: bool
    sky_conflict_state: str
    reasons: tuple[str, ...] = ()

    @property
    def inside_geometry(self) -> bool:
        return self.sky_conflict_state == SKY_CONFLICT_INSIDE_GEOMETRY


@dataclass(frozen=True)
class Registration:
    """How well one camera's pose is known, and what says so.

    ``residual_deg`` is the skyline objective at the fitted pose.
    ``position_sigma_m`` is the horizontal spread over independent optimiser
    seeds, which measures the width of the cost valley rather than a posterior.
    ``sky_conflict`` is the fraction of directions the segmentation calls sky
    where the support mesh returns a first hit, and it is the only one of the
    three that does not use the skyline objective at all.

    None means the file did not record it. That is kept distinct from zero
    throughout, because a pose registered before the sky conflict diagnostic
    existed is unknown rather than clean.
    """

    method: str = UNREGISTERED
    residual_deg: float | None = None
    position_sigma_m: float | None = None
    sky_conflict: float | None = None
    conflict_median_range_m: float | None = None
    dz_at_bound: bool | None = None

    def __post_init__(self) -> None:
        if self.sky_conflict is not None and not 0.0 <= self.sky_conflict <= 1.0:
            raise ValueError("sky_conflict is a fraction of directions and must lie in [0, 1]")
        for name in ("residual_deg", "position_sigma_m", "conflict_median_range_m"):
            value = getattr(self, name)
            if value is not None and (not np.isfinite(value) or value < 0.0):
                raise ValueError(f"{name} must be a finite non-negative number or None")

    @classmethod
    def unregistered(cls) -> Registration:
        """A look with no pose behind it, which is not the same as a bad pose."""
        return cls(method=UNREGISTERED)

    @classmethod
    def from_pose(cls, pose: dict[str, Any]) -> Registration:
        """Read one ``pose_aligned.json`` document.

        The three numbers sit in three different places in that file and one of
        them is behind a covariance matrix, which is most of why no caller ever
        carried all three.
        """
        conflict = pose.get("sky_conflict") or {}
        if "unavailable" in conflict:
            conflict = {}
        residual = pose.get("skyline_score_mean_deg")
        return cls(
            method=SKYLINE_ENSEMBLE if residual is not None else PROVIDER_METADATA,
            residual_deg=None if residual is None else float(residual),
            position_sigma_m=_position_sigma(pose),
            sky_conflict=_optional(conflict.get("sky_with_mesh_hit_fraction")),
            conflict_median_range_m=_optional(conflict.get("conflict_median_range_m")),
            dz_at_bound=(bool(pose["skyline_dz_at_bound"]) if "skyline_dz_at_bound" in pose else None),
        )

    @classmethod
    def from_file(cls, path: pathlib.Path) -> Registration:
        return cls.from_pose(json.loads(pathlib.Path(path).read_text()))

    def verdict(self, gate: AdmissionGate = AdmissionGate()) -> Verdict:
        """Admit or refuse this pose, and say which test decided.

        Two tests, and the second is not implied by the first. A camera inside a
        building matches the inside of that wall, so its residual is small while
        the sky it should be seeing is full of mesh.
        """
        reasons: list[str] = []
        if self.residual_deg is None:
            reasons.append("missing skyline residual diagnostic")
        elif self.residual_deg > gate.max_residual_deg:
            reasons.append(f"skyline residual {self.residual_deg:.2f} deg above {gate.max_residual_deg:.2f}")
        state = self._conflict_state(gate)
        if gate.require_complete_sky_diagnostics:
            if self.sky_conflict is None:
                reasons.append("missing sky_with_mesh_hit_fraction diagnostic")
            if self.conflict_median_range_m is None:
                reasons.append("missing conflict_median_range_m diagnostic")
        if state == SKY_CONFLICT_INSIDE_GEOMETRY:
            reasons.append(
                f"sky conflict {float(self.sky_conflict):.3f} of sky directions hit the mesh at a median "
                f"range of {float(self.conflict_median_range_m):.2f} m, so the camera is inside a building"
            )
        if gate.require_interior_optimum:
            if self.dz_at_bound is None:
                reasons.append("missing skyline_dz_at_bound diagnostic")
            elif self.dz_at_bound:
                reasons.append("vertical registration optimum is at the altitude search bound")
        return Verdict(admitted=not reasons, sky_conflict_state=state, reasons=tuple(reasons))

    def _conflict_state(self, gate: AdmissionGate) -> str:
        if self.sky_conflict is None:
            return SKY_CONFLICT_UNKNOWN
        if self.conflict_median_range_m is None:
            # Version 1 recorded the fraction first and treated an absent range
            # as non-conflicting. Preserve that label for sealed artifacts.
            return SKY_CONFLICT_CLEAR if gate.version == LEGACY_ADMISSION_GATE_VERSION else SKY_CONFLICT_UNKNOWN
        if self.sky_conflict > gate.max_sky_conflict:
            if self.conflict_median_range_m < gate.min_conflict_range_m:
                return SKY_CONFLICT_INSIDE_GEOMETRY
            return SKY_CONFLICT_LARGE_MISMATCH
        return SKY_CONFLICT_CLEAR

    def quality(self, gate: AdmissionGate = AdmissionGate()) -> float:
        """Reliability of this pose in [0, 1], for the evidence accumulator.

        :class:`~semantic_twin.vision.evidence.ObservationQuality` has carried a
        ``registration`` slot since it was written and every caller has passed
        one. This is the number that slot was for.

        A refused pose is zero, not small: an observation from a camera inside a
        wall is not weak evidence about the wall, it is evidence about nothing.
        Everything else falls off linearly in the residual over the gate and
        again in the sky conflict, so a pose that only just passes is worth less
        than one that passes easily. Version 2 refuses an unknown diagnostic.
        A large distant mismatch remains admitted but receives little weight.
        """
        if not self.verdict(gate).admitted:
            return 0.0
        residual = 0.0 if self.residual_deg is None else self.residual_deg
        from_residual = max(0.0, 1.0 - residual / gate.max_residual_deg)
        # A large distant mismatch is not the paired signature of a camera
        # inside geometry. Keep it as low-weight evidence rather than assigning
        # the same zero score as a refused inside-geometry pose.
        if gate.version == LEGACY_ADMISSION_GATE_VERSION:
            # This is the original v1 score, including its zero weight for a
            # missing sky diagnostic. Sealed artifacts use v1 for membership,
            # and reproducing its score avoids a second hidden policy change.
            conflict = gate.max_sky_conflict if self.sky_conflict is None else self.sky_conflict
            from_conflict = max(0.0, 1.0 - conflict / gate.max_sky_conflict)
        else:
            conflict = 1.0 if self.sky_conflict is None else self.sky_conflict
            from_conflict = max(0.0, 1.0 - conflict)
        return float(from_residual * from_conflict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "residual_deg": self.residual_deg,
            "position_sigma_m": self.position_sigma_m,
            "sky_with_mesh_hit_fraction": self.sky_conflict,
            "conflict_median_range_m": self.conflict_median_range_m,
            "dz_at_bound": self.dz_at_bound,
        }


def _optional(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _position_sigma(pose: dict[str, Any]) -> float | None:
    """One sigma horizontal spread of the pose, from the seed ensemble covariance."""
    uncertainty = pose.get("pose_uncertainty") or {}
    covariance = uncertainty.get("covariance")
    if not covariance:
        return None
    diagonal = np.diag(np.asarray(covariance, dtype=float))
    return float(np.sqrt(diagonal[0] + diagonal[1]))


@dataclass(frozen=True)
class ViewProvenance:
    """One look at a scene: who took it, with what, and how well it is placed.

    ``view`` is empty for a whole panorama and carries the rectilinear crop name
    when the evidence came from one view of it. ``backend`` and ``checkpoint``
    are the segmenter, because a model name alone does not pin a checkpoint.
    """

    site: str
    station: str
    provider: str
    registration: Registration
    view: str = ""
    backend: str = ""
    checkpoint: str | None = None

    def __post_init__(self) -> None:
        if not self.site or not self.station:
            raise ValueError("a look has to name the site and the camera it came from")
        if self.provider not in (sites.GOOGLE_STREETVIEW, sites.MAPILLARY):
            raise ValueError(f"unknown imagery provider: {self.provider!r}")

    @property
    def identifier(self) -> str:
        return f"{self.site}/{self.station}" + (f"#{self.view}" if self.view else "")

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "station": self.station,
            "provider": self.provider,
            "view": self.view,
            "backend": self.backend,
            "checkpoint": self.checkpoint,
            "registration": self.registration.as_dict(),
        }


@dataclass(frozen=True)
class EvidenceOrigin:
    """Where one block of surface evidence came from.

    This is the type the layer was missing. A surface could previously be asked
    what it was made of but not what saw it, so a material read off a camera
    inside a building and a material read off the orientation of its own
    triangle were indistinguishable once they reached the tracer.

    The invariants are enforced rather than documented, because the failure this
    layer already had was silence and not error: a channel outside the list, a
    projection rule outside the list, or an image channel with no look behind it
    all raise here instead of producing an unattributable label.
    """

    channel: str
    projection: str
    views: tuple[ViewProvenance, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if self.channel not in CHANNELS:
            raise ValueError(f"unknown evidence channel {self.channel!r}, expected one of {CHANNELS}")
        if self.projection not in PROJECTIONS:
            raise ValueError(f"unknown projection rule {self.projection!r}, expected one of {PROJECTIONS}")
        if self.channel in CAMERA_CHANNELS and not self.views:
            raise ValueError(f"{self.channel} evidence came through a camera and must name at least one look")
        if self.channel == NO_IMAGE and self.views:
            raise ValueError("no_image evidence cannot name a look")
        if self.channel == NO_IMAGE and self.projection != NO_PROJECTION:
            raise ValueError("no_image evidence was never projected")

    @classmethod
    def none(cls, note: str = "geometric orientation rule") -> EvidenceOrigin:
        """The honest origin of a surface no photograph reached."""
        return cls(channel=NO_IMAGE, projection=NO_PROJECTION, note=note)

    def registration_quality(self, gate: AdmissionGate = AdmissionGate()) -> np.ndarray:
        """Pose reliability of each look, in the order they were recorded."""
        return np.asarray([view.registration.quality(gate) for view in self.views], dtype=np.float64)

    def worst_registration(self, gate: AdmissionGate = AdmissionGate()) -> float:
        """Reliability of the weakest look, which is what a fused label inherits.

        A fused label is only as trustworthy as the worst pose that contributed
        to it, because a single misplaced camera can hand a facade the material
        of the building behind it and nothing downstream can tell.
        """
        quality = self.registration_quality(gate)
        return float(quality.min()) if quality.size else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "projection": self.projection,
            "note": self.note,
            "looks": [view.as_dict() for view in self.views],
        }


@dataclass(frozen=True)
class SiteRegistrationSurvey:
    """How much usable registration one site actually has.

    ``stations`` counts the cameras on disk, ``registered`` the ones that solved
    for a pose, and ``admitted`` the ones a gate would let through. The three
    are reported side by side because the study's evidence lists were written
    against the middle one and the number that matters is the last one.
    """

    site: str
    stations: int
    registered: int
    admitted: int
    inside_geometry: int
    unknown_conflict: int
    refused_on_residual: int
    per_station: dict[str, Verdict] = field(default_factory=dict)

    @property
    def usable_fraction(self) -> float:
        return self.admitted / self.stations if self.stations else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "stations_on_disk": self.stations,
            "stations_with_a_pose": self.registered,
            "stations_admitted": self.admitted,
            "stations_inside_the_geometry": self.inside_geometry,
            "stations_with_an_unknown_sky_conflict": self.unknown_conflict,
            "stations_refused_outside_inside_geometry": self.refused_on_residual,
            "usable_fraction_of_cameras_on_disk": round(self.usable_fraction, 4),
        }


def station_registrations(
    site: sites.Site,
    *,
    roles: tuple[str, ...] = ("stations", "walk", "multiview"),
) -> dict[str, Registration]:
    """Every camera of a site by name, with what is known about its pose.

    This is the handoff to the material binding. ``walk_semantic.npz`` already
    stores ``image_ids``, one per row, and those names are the keys here, so a
    binding can weight or drop a station by its pose without the file format
    growing a column and without any published number moving until someone
    chooses to use it.

    A camera with no pose file is absent rather than perfect. Callers that want
    a value for every row should ask for :meth:`Registration.unregistered`.
    """
    found: dict[str, Registration] = {}
    for role in roles:
        for station in site.stations(role):
            if station.name in found:
                continue
            pose_path = paths.panorama_pose(station)
            if pose_path.exists():
                found[station.name] = Registration.from_file(pose_path)
    return dict(sorted(found.items()))


def survey_site(
    site: sites.Site,
    *,
    gate: AdmissionGate = AdmissionGate(),
    roles: tuple[str, ...] = ("stations", "walk", "multiview"),
) -> SiteRegistrationSurvey:
    """Count one site's cameras by whether their pose survives the gate."""
    stations: list[pathlib.Path] = []
    for role in roles:
        stations.extend(site.stations(role))
    seen: dict[str, pathlib.Path] = {}
    for station in stations:
        seen.setdefault(station.name, station)

    verdicts = {
        name: registration.verdict(gate) for name, registration in station_registrations(site, roles=roles).items()
    }
    registered = len(verdicts)
    return SiteRegistrationSurvey(
        site=site.name,
        stations=len(seen),
        registered=registered,
        admitted=sum(1 for verdict in verdicts.values() if verdict.admitted),
        inside_geometry=sum(1 for verdict in verdicts.values() if verdict.inside_geometry),
        unknown_conflict=sum(1 for verdict in verdicts.values() if verdict.sky_conflict_state == "unknown"),
        refused_on_residual=sum(
            1 for verdict in verdicts.values() if not verdict.admitted and not verdict.inside_geometry
        ),
        per_station=verdicts,
    )


def survey(
    *,
    gate: AdmissionGate = AdmissionGate(),
    roles: tuple[str, ...] = ("stations", "walk", "multiview"),
) -> dict[str, SiteRegistrationSurvey]:
    """Registration health of every site with photographs, in study order.

    This exists so that "half the registrations are unusable" is a query rather
    than a claim somebody had to establish by hand and write into a document
    that then went stale.
    """
    return {site.name: survey_site(site, gate=gate, roles=roles) for site in sites.with_panoramas()}
