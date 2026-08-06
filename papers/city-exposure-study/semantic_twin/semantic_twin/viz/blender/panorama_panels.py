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

from PIL import Image, ImageDraw, ImageFont


EQUIRECTANGULAR_PROJECTION = "equirectangular"
PRIMARY_PANEL_KEYS = ("photo", "full_support", "fused_entity", "host_gated_material", "final_transport")
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
    panorama.  The photo layer keeps only the linked photograph, while every
    scientific layer admits the support holdout and its one measured channel.
    """
    layers: list[tuple[str, tuple[str, ...]]] = []
    for spec in pipeline_panel_specs(include_audit=include_audit):
        if spec.key == "photo":
            shown = ("twin",)
        else:
            shown = tuple(dict.fromkeys(("twin", *spec.show_collections)))
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


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


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
    specs: Sequence[PanelSpec] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CompositionResult:
    """Compose synchronized panels as vertical curtains on a 2:1 canvas.

    The canvas is always ``(2 * height, height)``.  Each panel occupies a
    deterministic vertical slice.  This makes panel boundaries and source
    pixels easy to compare while preserving one registered projection.
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
    canvas = Image.new("RGB", (target_width, target_height), (18, 20, 24))
    slice_width = target_width // len(records)
    rendered: list[PanelRecord] = []
    for index, record in enumerate(records):
        left = index * slice_width
        right = target_width if index == len(records) - 1 else (index + 1) * slice_width
        bounds = (left, 0, right, target_height)
        panel = _load_panel(record, (right - left, target_height))
        canvas.paste(panel, (left, 0))
        rendered.append(_record_file(record, panel, bounds))
    output = pathlib.Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return CompositionResult(
        output,
        _sha256(output),
        canvas.size,
        tuple(rendered),
        "vertical_curtain_2_to_1",
        metadata=metadata or {},
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
    "records_from_paths",
    "stamp_pipeline_contract",
    "vertical_curtain",
    "write_composition_manifest",
]
