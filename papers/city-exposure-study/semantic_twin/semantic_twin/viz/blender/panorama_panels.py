"""Synchronized 360-degree pipeline panels.

The panel layer is deliberately separate from Blender's scene construction.  A
panel is a named view of an existing collection and channel.  The same
registered equirectangular camera is used for every panel.  This module also
contains the small, deterministic image composers used for paper plates.  It
does not load ``bpy`` at import time, so panel manifests can be checked in the
ordinary Python test runner.

Evidence weights and evidence confidence are different quantities.  The panel
names keep that distinction explicit.  Missing legacy or depth evidence is
recorded as unavailable and is never replaced with a Vistas-only image.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


EQUIRECTANGULAR_PROJECTION = "equirectangular"
PRIMARY_PANEL_KEYS = ("photo", "full_support", "fused_entity", "host_gated_material", "final_transport")
PUBLICATION_PANEL_KEYS = (
    "photo",
    "raw_sam3",
    "full_support",
    "fused_entity",
    "host_gated_material",
    "final_transport",
)
CURTAIN_LABELS = {
    "photo": ("PHOTO", "registered source"),
    "raw_sam3": ("SAM 3", "single-view concepts"),
    "full_support": ("SUPPORT", "traced geometry"),
    "fused_entity": ("ENTITY", "all-view posterior"),
    "host_gated_material": ("RF MATERIAL", "host-gated posterior"),
    "final_transport": ("TRANSPORT", "final tracer state"),
}
CURTAIN_ACCENTS = (
    (103, 209, 255, 255),
    (255, 92, 154, 255),
    (91, 221, 184, 255),
    (195, 131, 255, 255),
    (255, 190, 83, 255),
    (92, 231, 255, 255),
)
AUDIT_PANEL_KEYS = (
    "vistas_weight",
    "sam3_weight",
    "source_overlap",
    "confidence",
    "camera_count",
    "observation_count",
    "legacy_refusal_depth_status",
)


@dataclass(frozen=True)
class PanelSpec:
    """One synchronized panel and the production channel it displays."""

    key: str
    title: str
    channel: str
    collection_key: str | None
    role: str
    required: bool = True
    unavailable_reason: str = ""
    show_collections: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return self.title


RAW_SAM3_PANEL_SPEC = PanelSpec(
    "raw_sam3",
    "SAM 3 surface concepts (single-panorama image space)",
    "support_concept",
    None,
    (
        "SAM 3 surface-concept winner after spherical reprojection of the perspective views; "
        "before all-camera Atlas fusion and distinct from the raw overlapping instance masks"
    ),
    unavailable_reason="pinned SAM 3 panorama semantics are unavailable",
)


@dataclass(frozen=True)
class PanelRecord:
    """A panel path and its reproducibility facts."""

    spec: PanelSpec
    path: pathlib.Path | None
    status: str
    dimensions: tuple[int, int] | None = None
    sha256: str | None = None
    slice_bounds: tuple[int, int, int, int] | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.spec.key,
            "title": self.spec.title,
            "channel": self.spec.channel,
            "role": self.spec.role,
            "collection_key": self.spec.collection_key,
            "path": str(self.path) if self.path is not None else None,
            "status": self.status,
            "reason": self.reason,
            "dimensions": list(self.dimensions) if self.dimensions is not None else None,
            "sha256": self.sha256,
            "slice_bounds": list(self.slice_bounds) if self.slice_bounds is not None else None,
        }


@dataclass(frozen=True)
class CompositionResult:
    """An output image and the panel manifest written beside it."""

    output_path: pathlib.Path
    output_sha256: str
    dimensions: tuple[int, int]
    panels: tuple[PanelRecord, ...]
    layout: str
    projection: str = EQUIRECTANGULAR_PROJECTION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result = dict(self.metadata)
        result.update(
            {
                "layout": self.layout,
                "projection": self.projection,
                "output_path": str(self.output_path),
                "output_sha256": self.output_sha256,
                "dimensions": list(self.dimensions),
                "panels": [panel.as_dict() for panel in self.panels],
            }
        )
        return result


def primary_panel_specs() -> tuple[PanelSpec, ...]:
    """Return the causal five-panel scientific composition."""
    return (
        PanelSpec("photo", "Registered photograph", "photo", None, "linked source panorama", show_collections=()),
        PanelSpec(
            "full_support",
            "Full traced support",
            "full_support",
            "outer_support",
            "exact traced support mesh",
            show_collections=("outer_support", "support_extent"),
        ),
        PanelSpec(
            "fused_entity",
            "Fused entity semantics (all-camera projection-aligned fusion)",
            "entity_posterior_winner",
            "entity_semantics",
            "joint all-camera entity posterior winner for display; not per-pixel segmentation",
            unavailable_reason="production fused entity atlas is unavailable",
            show_collections=("entity_semantics",),
        ),
        PanelSpec(
            "host_gated_material",
            "RF material Atlas (posterior display)",
            "transport_posterior_dominant",
            "transport_material",
            "projection-aligned all-camera posterior argmax for display; transport retains the full posterior",
            unavailable_reason="production host-gated material mixture is unavailable",
            show_collections=("transport_material",),
        ),
        PanelSpec(
            "final_transport",
            "Final transport state",
            "transport_state",
            "transport_state",
            "exact final host-gated transport state per atlas cell",
            unavailable_reason="production final transport state is unavailable",
            show_collections=("transport_state",),
        ),
    )


def publication_panel_specs() -> tuple[PanelSpec, ...]:
    """Return the paper sequence including image-space SAM 3 evidence.

    The SAM 3 raster is composed outside Blender because it already lives in
    the registered equirectangular image domain.  Rendering it through a 3-D
    mesh would introduce the very depth fighting this panel is meant to avoid.
    """
    primary = primary_panel_specs()
    return (primary[0], RAW_SAM3_PANEL_SPEC, *primary[1:])


def audit_panel_specs() -> tuple[PanelSpec, ...]:
    """Return audit panels with truthful names for weights and uncertainty."""
    return (
        PanelSpec(
            "vistas_weight",
            "Vistas evidence weight",
            "vistas_prior_weight",
            "vistas_contribution",
            "accumulated Mapillary Vistas prior weight",
            unavailable_reason="Vistas prior weight is unavailable",
            show_collections=("vistas_contribution",),
        ),
        PanelSpec(
            "sam3_weight",
            "SAM 3 evidence weight",
            "sam3_concept_weight",
            "sam3_contribution",
            "accumulated SAM 3 concept weight",
            unavailable_reason="SAM 3 concept weight is unavailable",
            show_collections=("sam3_contribution",),
        ),
        PanelSpec(
            "source_overlap",
            "Source overlap",
            "source_contribution_state",
            "source_contribution",
            "Vistas prior and SAM 3 concept source mask",
            unavailable_reason="source overlap mask is unavailable",
            show_collections=("source_contribution",),
        ),
        PanelSpec(
            "confidence",
            "Atlas confidence",
            "confidence",
            "atlas_confidence",
            "fused atlas confidence, separate from evidence weights",
            unavailable_reason="fused atlas confidence is unavailable",
            show_collections=("atlas_confidence",),
        ),
        PanelSpec(
            "camera_count",
            "Camera count",
            "camera_count",
            "atlas_camera_count",
            "number of admitted panorama cameras observing each cell",
            unavailable_reason="atlas camera count is unavailable",
            show_collections=("atlas_camera_count",),
        ),
        PanelSpec(
            "observation_count",
            "Observation count",
            "observation_count",
            "atlas_observation_count",
            "number of image observations contributing to each cell",
            unavailable_reason="atlas observation count is unavailable",
            show_collections=("atlas_observation_count",),
        ),
        PanelSpec(
            "legacy_refusal_depth_status",
            "Legacy refusal and depth status",
            "status",
            None,
            "truthful unavailable legacy refusal and depth evidence status",
            required=False,
            unavailable_reason="legacy refusal or depth evidence unavailable",
            show_collections=("refused", "depth"),
        ),
    )


def pipeline_panel_specs(*, include_audit: bool = True) -> tuple[PanelSpec, ...]:
    """Return panel specs in causal order, optionally followed by the audit."""
    return primary_panel_specs() + (audit_panel_specs() if include_audit else ())


def pipeline_layer_specs(*, include_audit: bool = True) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return prepared-scene layer names and collection keys.

    These layers are intentionally all camera views of the same registered
    panorama.  The photo and traced-support layers keep the support holdout,
    which is transparent over the linked photograph and suppresses back
    surfaces in the translucent support copy.  Atlas layers render their own
    measured surface without the coplanar holdout.  Keeping both there would
    make Cycles choose between equal-depth faces and create a false triangle
    stipple.
    """
    layers: list[tuple[str, tuple[str, ...]]] = []
    for spec in pipeline_panel_specs(include_audit=include_audit):
        if spec.key in {"photo", "full_support"}:
            shown = tuple(dict.fromkeys(("twin", *spec.show_collections)))
        else:
            shown = spec.show_collections
        layers.append((spec.title, shown))
    return tuple(layers)


def stamp_pipeline_contract(target: Any, *, capture: str, projection: str = EQUIRECTANGULAR_PROJECTION) -> None:
    """Stamp the shared-camera contract on a Blender scene or camera object."""
    target["panorama_pipeline_capture"] = str(capture)
    target["panorama_pipeline_projection"] = str(projection)
    target["panorama_pipeline_camera_contract"] = (
        "All primary and audit panels use this registered equirectangular camera, pose, crop, and resolution."
    )
    target["panorama_pipeline_atlas_scope"] = (
        "Fused entity and RF material panels are projection-aligned all-camera atlas displays, not per-pixel segmentation."
    )
    target["panorama_pipeline_material_scope"] = (
        "Material colour is a posterior argmax for display. Host-gated transport retains the full compatible posterior."
    )
    target["panorama_pipeline_weight_scope"] = "Vistas and SAM 3 panels show evidence weights. They are not confidence."


def panel_spec_map(*, include_audit: bool = True) -> dict[str, PanelSpec]:
    return {spec.key: spec for spec in pipeline_panel_specs(include_audit=include_audit)}


def _mapping_value(mapping: Mapping[str, Any] | None, *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def panel_availability(
    specs: Sequence[PanelSpec] | None = None,
    *,
    collections: Mapping[str, Any] | None = None,
    channels: Sequence[str] = (),
    manifest: Mapping[str, Any] | None = None,
) -> tuple[PanelRecord, ...]:
    """Describe which panels are available without inventing missing evidence.

    ``collections`` may contain Blender collections or plain objects with an
    ``objects`` attribute.  ``channels`` is useful for payload-only callers.
    """
    selected = tuple(specs or pipeline_panel_specs())
    channel_set = set(channels)
    records: list[PanelRecord] = []
    for spec in selected:
        available = False
        if spec.collection_key is None:
            available = spec.key == "photo"
        elif spec.channel in channel_set:
            available = True
        elif collections is not None:
            group = collections.get(spec.collection_key)
            if group is not None:
                populated = len(getattr(group, "objects", ())) > 0
                status = group.get("status") if isinstance(group, Mapping) else None
                available = bool(populated or status == "built")
        status = "available" if available else "unavailable"
        reason = None if available else spec.unavailable_reason
        if not available and spec.key == "fused_entity":
            reason = "production fused hybrid atlas unavailable; Vistas-only raster is not substituted"
        if spec.key == "legacy_refusal_depth_status" and not available:
            refusal = _mapping_value(manifest, "evidence", "rejected", "status")
            depth = _mapping_value(manifest, "evidence", "depth_mesh", "status")
            reason = f"legacy refusal status={refusal or 'unavailable'}; depth status={depth or 'unavailable'}"
        records.append(PanelRecord(spec, None, status, reason=reason))
    return tuple(records)


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_sam3_concept_panel(
    panorama_path: pathlib.Path | str,
    semantics_path: pathlib.Path | str,
    semantics_metadata_path: pathlib.Path | str,
    output_path: pathlib.Path | str,
    *,
    dimensions: tuple[int, int] | None = None,
    opacity: float = 0.82,
) -> PanelRecord:
    """Render the pinned SAM 3 surface concepts directly in panorama space.

    This is deliberately not called a raw instance-mask panel.  SAM 3 runs on
    overlapping perspective views and can return overlapping instances.  The
    stored ``support_concept`` raster is their deterministic spherical winner,
    before projection into the multi-camera surface Atlas.  Keeping that scope
    in the title and provenance prevents the image from being mistaken for the
    fused Atlas or for untouched model logits.
    """
    if not 0.0 < opacity <= 1.0:
        raise ValueError("SAM 3 panel opacity must be in (0, 1]")
    panorama = pathlib.Path(panorama_path).resolve()
    semantics = pathlib.Path(semantics_path).resolve()
    metadata_path = pathlib.Path(semantics_metadata_path).resolve()
    output = pathlib.Path(output_path).resolve()
    for source in (panorama, semantics, metadata_path):
        if not source.is_file():
            raise FileNotFoundError(source)

    metadata = json.loads(metadata_path.read_text())
    concept_backend = metadata.get("concept_backend")
    if not isinstance(concept_backend, Mapping) or not str(concept_backend.get("model", "")).endswith("sam3"):
        raise ValueError("semantic metadata does not identify a pinned SAM 3 concept backend")

    with np.load(semantics, allow_pickle=False) as arrays:
        if "support_concept" not in arrays:
            raise ValueError("semantic raster has no SAM 3 support_concept channel")
        concept = np.asarray(arrays["support_concept"], dtype=np.int32)
    if concept.ndim != 2 or concept.size == 0 or np.any(concept < 0):
        raise ValueError("support_concept must be a nonempty nonnegative 2-D raster")

    source_size = (int(concept.shape[1]), int(concept.shape[0]))
    target_size = dimensions or source_size
    if target_size[0] <= 0 or target_size[1] <= 0:
        raise ValueError("SAM 3 panel dimensions must be positive")
    if target_size != source_size:
        concept = np.asarray(
            Image.fromarray(concept, mode="I").resize(target_size, Image.Resampling.NEAREST),
            dtype=np.int32,
        )

    with Image.open(panorama) as source:
        photograph = source.convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
    photograph_array = np.asarray(photograph, dtype=np.float32)
    from ...vision.fuse import palette

    colours = palette(int(concept.max(initial=0)) + 1)
    overlay = colours[concept].astype(np.float32)
    present = concept > 0
    composed = photograph_array.copy()
    composed[present] = (1.0 - opacity) * photograph_array[present] + opacity * overlay[present]
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(np.rint(composed), 0, 255).astype(np.uint8)).save(output)

    labels = metadata.get("concept_id2label", {})
    provenance = {
        "panel": {
            "key": RAW_SAM3_PANEL_SPEC.key,
            "title": RAW_SAM3_PANEL_SPEC.title,
            "channel": RAW_SAM3_PANEL_SPEC.channel,
            "role": RAW_SAM3_PANEL_SPEC.role,
        },
        "panorama_path": str(panorama),
        "panorama_sha256": _sha256(panorama),
        "semantics_path": str(semantics),
        "semantics_sha256": _sha256(semantics),
        "semantics_metadata_path": str(metadata_path),
        "semantics_metadata_sha256": _sha256(metadata_path),
        "concept_backend": concept_backend,
        "concept_id2label": labels,
        "dimensions": list(target_size),
        "opacity": opacity,
        "labelled_fraction": float(np.count_nonzero(present) / present.size),
        "scope": RAW_SAM3_PANEL_SPEC.role,
    }
    output.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return PanelRecord(
        RAW_SAM3_PANEL_SPEC,
        output,
        "available",
        dimensions=target_size,
        sha256=_sha256(output),
    )


def render_sam3_raw_instance_panel(
    view_path: pathlib.Path | str,
    concept_cache_path: pathlib.Path | str,
    output_path: pathlib.Path | str,
    *,
    opacity: float = 0.22,
) -> pathlib.Path:
    """Render the un-fused overlapping SAM 3 instances for one source view.

    Unlike :func:`render_sam3_concept_panel`, this diagnostic reads the packed
    model masks before spherical reprojection or Atlas fusion.  All instances
    are retained.  Low-score masks are drawn first so high-score instances
    remain legible, while repeated overlaps remain visibly denser.
    """
    if not 0.0 < opacity <= 1.0:
        raise ValueError("raw SAM 3 instance opacity must be in (0, 1]")
    view = pathlib.Path(view_path).resolve()
    cache = pathlib.Path(concept_cache_path).resolve()
    output = pathlib.Path(output_path).resolve()
    for source in (view, cache):
        if not source.is_file():
            raise FileNotFoundError(source)

    with np.load(cache, allow_pickle=False) as arrays:
        required = {"packed_masks", "mask_shape", "scores", "labels", "kinds"}
        missing = sorted(required.difference(arrays.files))
        if missing:
            raise ValueError(f"SAM 3 concept cache is missing arrays: {missing}")
        packed_masks = np.asarray(arrays["packed_masks"], dtype=np.uint8)
        mask_shape = tuple(int(value) for value in arrays["mask_shape"])
        scores = np.asarray(arrays["scores"], dtype=np.float32)
        labels = np.asarray(arrays["labels"], dtype=str)
        kinds = np.asarray(arrays["kinds"], dtype=str)
        cache_key = str(arrays["cache_key"]) if "cache_key" in arrays else None
    if len(mask_shape) != 2 or min(mask_shape) <= 0:
        raise ValueError("raw SAM 3 mask_shape must contain two positive dimensions")
    if packed_masks.ndim != 2 or not (len(packed_masks) == len(scores) == len(labels) == len(kinds)):
        raise ValueError("raw SAM 3 instance arrays do not share one instance dimension")
    pixel_count = mask_shape[0] * mask_shape[1]
    expected_bytes = (pixel_count + 7) // 8
    if packed_masks.shape[1] != expected_bytes:
        raise ValueError("raw SAM 3 packed masks do not match mask_shape")

    with Image.open(view) as source:
        photograph = source.convert("RGB").resize((mask_shape[1], mask_shape[0]), Image.Resampling.LANCZOS)
    composed = np.asarray(photograph, dtype=np.float32).copy()
    unique_labels = sorted(set(labels.tolist()))
    label_ids = {label: index + 1 for index, label in enumerate(unique_labels)}
    from ...vision.fuse import palette

    colours = palette(len(unique_labels) + 1).astype(np.float32)
    for index in np.argsort(scores, kind="stable"):
        mask = np.unpackbits(packed_masks[index], count=pixel_count).reshape(mask_shape).astype(bool)
        if not np.any(mask):
            continue
        colour = colours[label_ids[str(labels[index])]]
        composed[mask] = (1.0 - opacity) * composed[mask] + opacity * colour

    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(np.rint(composed), 0, 255).astype(np.uint8)).save(output)
    provenance = {
        "panel": "raw_sam3_instances",
        "scope": "un-fused overlapping model masks for one source perspective view",
        "view_path": str(view),
        "view_sha256": _sha256(view),
        "concept_cache_path": str(cache),
        "concept_cache_sha256": _sha256(cache),
        "cache_key": cache_key,
        "dimensions": [mask_shape[1], mask_shape[0]],
        "instance_count": int(len(labels)),
        "labels": labels.tolist(),
        "kinds": kinds.tolist(),
        "scores": scores.astype(float).tolist(),
        "opacity_per_instance": opacity,
        "draw_order": "ascending score, highest score last",
    }
    output.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return output


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    stem = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for name in (stem, f"/usr/share/fonts/truetype/dejavu/{stem}"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _label_curtain(
    canvas: Image.Image,
    records: Sequence[PanelRecord],
    cuts: Sequence[int],
) -> tuple[Image.Image, list[dict[str, str]]]:
    """Add compact publication labels without obscuring scene landmarks."""
    width, height = canvas.size
    scale = max(height / 832.0, 0.5)
    margin = max(6, round(11 * scale))
    top = max(8, round(18 * scale))
    card_height = max(40, round(60 * scale))
    radius = max(6, round(10 * scale))
    title_font = _font(max(11, round(17 * scale)), bold=True)
    detail_font = _font(max(9, round(11 * scale)))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    labels: list[dict[str, str]] = []
    for index, record in enumerate(records):
        left, right = cuts[index : index + 2]
        heading, detail = CURTAIN_LABELS.get(record.spec.key, (record.spec.title.upper(), record.spec.role))
        labels.append({"key": record.spec.key, "heading": heading, "detail": detail})
        card_left = left + margin
        card_right = right - margin
        if card_right <= card_left:
            continue
        accent = CURTAIN_ACCENTS[index % len(CURTAIN_ACCENTS)]
        draw.rounded_rectangle(
            (card_left, top, card_right, top + card_height),
            radius=radius,
            fill=(9, 14, 22, 218),
            outline=(255, 255, 255, 70),
            width=max(1, round(scale)),
        )
        draw.rounded_rectangle(
            (card_left, top, card_left + max(4, round(6 * scale)), top + card_height),
            radius=max(2, round(4 * scale)),
            fill=accent,
        )
        text_left = card_left + max(12, round(17 * scale))
        draw.text(
            (text_left, top + max(5, round(7 * scale))),
            f"{index + 1:02d}  {heading}",
            fill=(250, 252, 255, 255),
            font=title_font,
        )
        draw.text(
            (text_left, top + max(23, round(32 * scale))),
            detail,
            fill=(202, 213, 226, 255),
            font=detail_font,
        )
        if index:
            draw.line((left, 0, left, height), fill=(255, 255, 255, 105), width=max(1, round(scale)))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"), labels


def _placeholder(size: tuple[int, int], title: str, reason: str) -> Image.Image:
    image = Image.new("RGB", size, (38, 42, 48))
    draw = ImageDraw.Draw(image)
    title_font = _font(max(12, size[1] // 22))
    body_font = _font(max(10, size[1] // 36))
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(220, 150, 50), width=max(1, size[1] // 180))
    draw.text((size[0] // 16, size[1] // 4), title, fill=(250, 240, 220), font=title_font)
    draw.multiline_text((size[0] // 16, size[1] // 2), reason, fill=(230, 190, 120), font=body_font, spacing=4)
    return image


def _load_panel(record: PanelRecord, size: tuple[int, int]) -> Image.Image:
    if record.path is None or record.status != "available":
        return _placeholder(size, record.spec.title, record.reason or record.spec.unavailable_reason)
    image = Image.open(record.path).convert("RGB")
    if image.size != size:
        resampling = getattr(Image, "Resampling", Image)
        image = image.resize(size, resampling.LANCZOS)
    return image


def _record_file(record: PanelRecord, image: Image.Image, bounds: tuple[int, int, int, int]) -> PanelRecord:
    return PanelRecord(
        record.spec,
        record.path,
        record.status,
        dimensions=image.size,
        sha256=record.sha256,
        slice_bounds=bounds,
        reason=record.reason,
    )


def records_from_paths(
    paths: Mapping[str, pathlib.Path | str],
    *,
    specs: Sequence[PanelSpec] | None = None,
    dimensions: tuple[int, int] | None = None,
    collections: Mapping[str, Any] | None = None,
    channels: Sequence[str] = (),
    manifest: Mapping[str, Any] | None = None,
) -> tuple[PanelRecord, ...]:
    """Create panel records and verify image dimensions and file hashes."""
    selected = tuple(specs or pipeline_panel_specs())
    available = panel_availability(selected, collections=collections, channels=channels, manifest=manifest)
    records: list[PanelRecord] = []
    for record in available:
        value = paths.get(record.spec.key)
        if value is None:
            records.append(
                PanelRecord(
                    record.spec,
                    None,
                    "unavailable",
                    reason=record.reason or "panel image was not supplied",
                )
            )
            continue
        path = pathlib.Path(value).resolve()
        if not path.is_file():
            records.append(PanelRecord(record.spec, path, "unavailable", reason=f"panel image does not exist: {path}"))
            continue
        with Image.open(path) as image:
            size = tuple(int(value) for value in image.size)
        if dimensions is not None and size != dimensions:
            raise ValueError(f"panel {record.spec.key!r} is {size}, expected synchronized dimensions {dimensions}")
        records.append(PanelRecord(record.spec, path, "available", dimensions=size, sha256=_sha256(path)))
    return tuple(records)


def _require_synchronized_dimensions(records: Sequence[PanelRecord]) -> None:
    dimensions = {record.dimensions for record in records if record.status == "available" and record.dimensions}
    if len(dimensions) > 1:
        ordered = sorted(dimensions)
        raise ValueError(f"panel images do not share synchronized registered dimensions: {ordered}")


def _metadata(
    *,
    capture: str | None,
    residual_deg: float | None,
    image_sha256: str | None,
    atlas_sha256: str | None,
    blend_sha256: str | None,
    projection: str,
    dimensions: tuple[int, int],
) -> dict[str, Any]:
    return {
        "capture": capture,
        "registration_residual_deg": residual_deg,
        "image_sha256": image_sha256,
        "atlas_sha256": atlas_sha256,
        "blend_sha256": blend_sha256,
        "projection": projection,
        "dimensions": list(dimensions),
    }


def compose_vertical_curtain(
    panels: Mapping[str, pathlib.Path | str] | Sequence[PanelRecord],
    output_path: pathlib.Path | str,
    *,
    width: int | None = None,
    height: int | None = None,
    cut_positions: Sequence[int] | None = None,
    label_panels: bool = False,
    specs: Sequence[PanelSpec] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CompositionResult:
    """Compose synchronized panels as one registered 360-degree curtain.

    The canvas is always ``(2 * height, height)``.  Each panel occupies a
    deterministic longitude interval from the same registered projection.
    Source panels are scaled to the shared canvas before their intervals are
    cropped, so the horizontal axis spans 360 degrees exactly once.
    """
    selected = tuple(specs or pipeline_panel_specs())
    if isinstance(panels, Mapping):
        records = records_from_paths(panels, specs=selected)
    else:
        records = tuple(panels)
    if not records:
        raise ValueError("at least one panel is required")
    _require_synchronized_dimensions(records)
    source_size = next((record.dimensions for record in records if record.dimensions), None)
    if source_size is None:
        source_size = (int(width or 1024), int(height or 512))
    target_height = int(height or source_size[1])
    target_width = int(width or 2 * target_height)
    if target_width != 2 * target_height:
        raise ValueError("vertical curtain output must have a 2:1 width-to-height ratio")
    if cut_positions is None:
        cuts = tuple(index * target_width // len(records) for index in range(len(records))) + (target_width,)
    else:
        cuts = tuple(int(position) for position in cut_positions)
        if len(cuts) != len(records) + 1:
            raise ValueError("cut_positions must contain one more position than the panel count")
        if cuts[0] != 0 or cuts[-1] != target_width:
            raise ValueError("cut_positions must begin at 0 and end at the output width")
        if any(left >= right for left, right in zip(cuts, cuts[1:])):
            raise ValueError("cut_positions must be strictly increasing")
    canvas = Image.new("RGB", (target_width, target_height), (18, 20, 24))
    rendered: list[PanelRecord] = []
    for index, record in enumerate(records):
        left, right = cuts[index : index + 2]
        bounds = (left, 0, right, target_height)
        panel = _load_panel(record, (target_width, target_height)).crop(bounds)
        canvas.paste(panel, (left, 0))
        rendered.append(_record_file(record, panel, bounds))
    labels: list[dict[str, str]] = []
    if label_panels:
        canvas, labels = _label_curtain(canvas, records, cuts)
    output = pathlib.Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return CompositionResult(
        output,
        _sha256(output),
        canvas.size,
        tuple(rendered),
        "registered_360_vertical_curtain",
        metadata={
            **(metadata or {}),
            "cut_positions": list(cuts),
            "panel_labels": labels,
        },
    )


def compose_aligned_comparison(
    panels: Mapping[str, pathlib.Path | str] | Sequence[PanelRecord],
    output_path: pathlib.Path | str,
    *,
    specs: Sequence[PanelSpec] | None = None,
    panel_width: int | None = None,
    panel_height: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CompositionResult:
    """Stack complete synchronized panels for aligned full-panel comparison."""
    selected = tuple(specs or pipeline_panel_specs())
    records = records_from_paths(panels, specs=selected) if isinstance(panels, Mapping) else tuple(panels)
    if not records:
        raise ValueError("at least one panel is required")
    _require_synchronized_dimensions(records)
    source_size = next((record.dimensions for record in records if record.dimensions), None) or (1024, 512)
    size = (int(panel_width or source_size[0]), int(panel_height or source_size[1]))
    canvas = Image.new("RGB", (size[0], size[1] * len(records)), (18, 20, 24))
    rendered: list[PanelRecord] = []
    for index, record in enumerate(records):
        panel = _load_panel(record, size)
        top = index * size[1]
        bounds = (0, top, size[0], top + size[1])
        canvas.paste(panel, (0, top))
        rendered.append(_record_file(record, panel, bounds))
    output = pathlib.Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return CompositionResult(
        output,
        _sha256(output),
        canvas.size,
        tuple(rendered),
        "aligned_full_panel_comparison",
        metadata=metadata or {},
    )


def write_composition_manifest(result: CompositionResult, path: pathlib.Path | str) -> pathlib.Path:
    """Write the JSON audit beside a composed image."""
    destination = pathlib.Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n")
    return destination


def composition_metadata(
    asset: Any,
    *,
    atlas_sha256: str | None = None,
    blend_path: pathlib.Path | str | None = None,
    dimensions: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Build the shared provenance block from a :class:`PanoramaAsset`."""
    blend = pathlib.Path(blend_path) if blend_path is not None else None
    blend_hash = _sha256(blend) if blend is not None and blend.is_file() else None
    size = dimensions or (int(asset.width), int(asset.height))
    return _metadata(
        capture=str(asset.capture),
        residual_deg=float(asset.skyline_residual_deg),
        image_sha256=str(asset.image_sha256),
        atlas_sha256=atlas_sha256 or getattr(asset, "atlas_panorama_sha256", None),
        blend_sha256=blend_hash,
        projection=EQUIRECTANGULAR_PROJECTION,
        dimensions=size,
    )


# Short aliases used by callers that treat the figure as a plate.
vertical_curtain = compose_vertical_curtain
aligned_full_panel_comparison = compose_aligned_comparison
panel_manifest = write_composition_manifest


__all__ = [
    "AUDIT_PANEL_KEYS",
    "EQUIRECTANGULAR_PROJECTION",
    "PRIMARY_PANEL_KEYS",
    "PUBLICATION_PANEL_KEYS",
    "RAW_SAM3_PANEL_SPEC",
    "CompositionResult",
    "PanelRecord",
    "PanelSpec",
    "aligned_full_panel_comparison",
    "audit_panel_specs",
    "compose_aligned_comparison",
    "compose_vertical_curtain",
    "composition_metadata",
    "panel_availability",
    "panel_manifest",
    "panel_spec_map",
    "pipeline_layer_specs",
    "pipeline_panel_specs",
    "primary_panel_specs",
    "publication_panel_specs",
    "records_from_paths",
    "render_sam3_concept_panel",
    "render_sam3_raw_instance_panel",
    "stamp_pipeline_contract",
    "vertical_curtain",
    "write_composition_manifest",
]
