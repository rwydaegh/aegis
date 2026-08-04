"""Photographs to surface evidence, and the provenance that says what it is worth.

This is the arm of the study that reads the imagery. It is also the arm with the
widest gap between what the code can do and what the published numbers used, and
the package is laid out so that gap is visible rather than buried.

State it plainly, because every module here inherits it. The eleven city
headline ran with ``--materials geometric``, which classifies a surface by the
orientation of its own triangle and never calls this package at all. The
prompted segmenter ran on 2 of 96 panoramas. Of 83 registered camera poses, 26
put the camera inside a building and 6 of those pass the residual gate that was
supposed to catch them. So the machinery below is built, partly validated, and
largely bypassed. Closing that is not a refactor, and this pass does not attempt
it. What this pass does is make the state of it answerable.

**Provenance is the organising idea.** A label is worth what the photograph
behind it is worth, and the photograph is worth what its pose is worth.
:mod:`~.provenance` carries all three as types, and
:class:`~.provenance.EvidenceOrigin` refuses to exist without naming its channel,
its projection rule and, for the camera channels, the looks behind it. A surface
can now be asked what saw it and how well, and ``no photograph reached me`` is a
first class answer rather than a missing key.

Reading order.

    provenance   what saw a surface, how well, and the gate that decides
    vocabulary   what the evidence is allowed to say: the taxonomy and the catalogue
    views        cutting a panorama into rectilinear crops, and where each lands back

    dense        Mask2Former on Mapillary Vistas, the entity axis
    prompted     SAM 3 on the concept catalogue, the material axis
    fuse         many views into one sphere
    layers       overlapping instances into non-exclusive layers
    material     the cascade where a concept may overwrite the dense class prior
    panorama     the command that runs all of the above over one panorama

    register     fitting a pose to the segmented skyline
    conflict     where the image and the geometry disagree, independent of that fit
    align        the command that registers one panorama and writes its pose

    project      pixels into triangles, as adaptive tiles
    atlas        triangle-local decal atlases, sub-triangle and non-destructive
    ledger       the sparse, replayable observation store behind them

    evidence     Dirichlet and Beta posteriors over shared surface elements
    captures     which panoramas a site has, and how independent they are

    tiles        the photogrammetry tile texture as a readable surface
    appearance   what a patch of that texture looks like
    texture      the texture as a material channel, capped so it cannot lead
    vlm          a vision language model as a facade material backend
    bodies       people reconstructed from images, as transient geometry

Two things this package deliberately does not own.
:mod:`semantic_twin.pano_geometry` holds the panorama camera model and is shared
with the mesh cutter and the acquisition code, so it stays at the package root.
:mod:`semantic_twin.materials.evidence` is the consumer. It turns this package's
output into a per-triangle material binding.
"""

from __future__ import annotations

from .captures import (
    WalkStation,
    effective_looks,
    parallax_angles_deg,
    parallax_independence,
    select_walk,
    spread,
    stations_from_images,
)
from .conflict import DepthConflictState, SkyConflict, sky_conflict
from .evidence import (
    EvidenceAccumulator,
    ObservationQuality,
    SoftAssociation,
    categorical_information,
)
from .provenance import (
    CAMERA_CHANNELS,
    CHANNELS,
    FACADE_VLM,
    NO_IMAGE,
    PANORAMA_ENTITY,
    PANORAMA_MATERIAL,
    PROJECTIONS,
    TILE_TEXTURE,
    AdmissionGate,
    EvidenceOrigin,
    Registration,
    SiteRegistrationSurvey,
    Verdict,
    ViewProvenance,
    station_registrations,
    survey,
    survey_site,
)
from .vocabulary import (
    BackendBridge,
    Concept,
    ConceptCatalog,
    MaterialBinding,
    PromptGate,
    gate_prompts,
    is_object,
)

__all__ = [
    "CAMERA_CHANNELS",
    "CHANNELS",
    "FACADE_VLM",
    "NO_IMAGE",
    "PANORAMA_ENTITY",
    "PANORAMA_MATERIAL",
    "PROJECTIONS",
    "TILE_TEXTURE",
    "AdmissionGate",
    "BackendBridge",
    "Concept",
    "ConceptCatalog",
    "DepthConflictState",
    "EvidenceAccumulator",
    "EvidenceOrigin",
    "MaterialBinding",
    "ObservationQuality",
    "PromptGate",
    "Registration",
    "SiteRegistrationSurvey",
    "SkyConflict",
    "SoftAssociation",
    "Verdict",
    "ViewProvenance",
    "WalkStation",
    "categorical_information",
    "effective_looks",
    "gate_prompts",
    "is_object",
    "parallax_angles_deg",
    "parallax_independence",
    "select_walk",
    "sky_conflict",
    "spread",
    "station_registrations",
    "stations_from_images",
    "survey",
    "survey_site",
]
