"""Fuse overlapping SAM 3 concept instances into spherical semantic layers."""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .concepts import Concept, ConceptCatalog
from .pano_geometry import inference_views, perspective_directions, view_pixel_coordinates
from .semantics import palette

KIND_ID = {"surface": 1, "object": 2}
LAYER_NAMES = ("support", "material", "clutter", "dynamic_clutter")


@dataclass(frozen=True)
class LayerRule:
    """One non-exclusive diagnostic semantic layer.

    These layers deliberately do not form a partition. A glass-window mask may
    coexist with its brick-façade support, and a person may coexist with the
    support it occludes. Projection consumes the exported layers explicitly,
    rather than this diagnostic compositor deciding what exists in 3D.
    """

    name: str
    labels: frozenset[str]
    priority_bonus: dict[str, float]


def _is_dynamic_clutter(concept: Concept) -> bool:
    """Classify only clearly movable/transient object prompts as dynamic."""
    if concept.kind != "object":
        return False
    movable = concept.attributes.get("movable", 0.0)
    transient = concept.attributes.get("transient", 0.0)
    fixed = concept.attributes.get("fixed", 0.0)
    return transient >= 0.5 or movable >= 0.8 or (movable >= 0.5 and fixed < 0.5)


def layer_rules(catalog: ConceptCatalog) -> tuple[LayerRule, ...]:
    """Build non-exclusive layer rules from the concept taxonomy.

    A material-detail bonus is only a display/export ordering hint. It makes a
    window, door, or an explicitly material-only mask visible over its broad
    support mask while leaving both labels in separate arrays.
    """
    surfaces = [concept for concept in catalog.concepts if concept.kind == "surface"]
    clutter = [concept for concept in catalog.concepts if concept.kind == "object"]
    structural_entities = {"facade", "road", "pavement", "ground", "water", "vegetation"}
    material_bonus: dict[str, float] = {}
    for concept in surfaces:
        structural_mass = sum(concept.entity.get(entity, 0.0) for entity in structural_entities)
        # Detail concepts (notably window/door and material-only prompts) are
        # rendered over their support, not allowed to erase it from the file.
        material_bonus[concept.prompt] = 0.75 * (1.0 - structural_mass)
    return (
        LayerRule("support", frozenset(concept.prompt for concept in surfaces), {}),
        LayerRule("material", frozenset(concept.prompt for concept in surfaces), material_bonus),
        LayerRule("clutter", frozenset(concept.prompt for concept in clutter), {}),
        LayerRule(
            "dynamic_clutter",
            frozenset(concept.prompt for concept in clutter if _is_dynamic_clutter(concept)),
            {},
        ),
    )


def load_concepts(path: pathlib.Path) -> tuple[dict[str, int], dict[int, str]]:
    catalog = ConceptCatalog.load(path)
    names = ["unlabelled", *(concept.prompt for concept in catalog.concepts)]
    return ({name: index for index, name in enumerate(names)}, dict(enumerate(names)))


def unpack_masks(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    prediction = np.load(path)
    height, width = prediction["mask_shape"].astype(int)
    labels = prediction["labels"].astype(str)
    if not len(labels):
        return np.zeros((0, height, width), dtype=bool), labels, prediction["kinds"], prediction["scores"]
    packed = prediction["packed_masks"]
    masks = np.unpackbits(packed, axis=1, count=height * width).reshape(len(labels), height, width).astype(bool)
    return masks, labels, prediction["kinds"].astype(str), prediction["scores"].astype(np.float32)


def _select_layer(
    masks: np.ndarray,
    labels: np.ndarray,
    scores: np.ndarray,
    concept_ids: dict[str, int],
    rule: LayerRule,
) -> tuple[np.ndarray, np.ndarray]:
    """Keep a layer-local winner without discarding other layers."""
    height, width = masks.shape[1:]
    priority = np.zeros((height, width), dtype=np.float32)
    confidence = np.zeros((height, width), dtype=np.float16)
    concept = np.zeros((height, width), dtype=np.uint16)
    for index, (label, score) in enumerate(zip(labels, scores, strict=True)):
        label = str(label)
        if label not in rule.labels:
            continue
        candidate_priority = float(score) + rule.priority_bonus.get(label, 0.0)
        take = masks[index] & (candidate_priority > priority)
        priority[take] = candidate_priority
        confidence[take] = score
        concept[take] = concept_ids[label]
    return concept, confidence


def view_layers(
    masks: np.ndarray,
    labels: np.ndarray,
    kinds: np.ndarray,
    scores: np.ndarray,
    concept_ids: dict[str, int],
    rules: tuple[LayerRule, ...],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Extract every layer independently from one perspective view.

    ``kinds`` remains an explicit input because the on-disk SAM artifact is
    validated here before the catalog-derived rules are applied.
    """
    if len(labels) != len(kinds) or len(labels) != len(scores):
        raise ValueError("SAM prediction labels, kinds, and scores have different lengths")
    unknown = set(labels.astype(str)) - set(concept_ids)
    if unknown:
        raise ValueError(f"SAM prediction contains concepts missing from catalog: {sorted(unknown)}")
    return {rule.name: _select_layer(masks, labels, scores, concept_ids, rule) for rule in rules}


def fuse_layer(
    layer_views: list[tuple[object, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
    row_chunk: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Stitch one semantic layer over perspective crops on the sphere."""
    concept_out = np.zeros((height, width), dtype=np.uint16)
    confidence_out = np.zeros((height, width), dtype=np.float16)
    priority_out = np.zeros((height, width), dtype=np.float32)
    yaw = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    for y0 in range(0, height, row_chunk):
        y1 = min(y0 + row_chunk, height)
        pitch = (0.5 - (np.arange(y0, y1) + 0.5) / height) * np.pi
        yy, pp = np.meshgrid(yaw, pitch)
        cos_pitch = np.cos(pp)
        directions = np.stack([np.sin(yy) * cos_pitch, np.cos(yy) * cos_pitch, np.sin(pp)], axis=2)
        for view, concept, confidence in layer_views:
            px, py, valid = view_pixel_coordinates(directions, view, concept.shape[1], concept.shape[0])
            sampled_confidence = np.where(valid, confidence[py, px], 0.0)
            centre = perspective_directions(view, 1, 1)[0, 0]
            angular_weight = np.clip(directions @ centre, 0.0, 1.0) ** 4
            score = sampled_confidence * angular_weight
            take = valid & (concept[py, px] > 0) & (score > priority_out[y0:y1])
            priority_out[y0:y1][take] = score[take]
            concept_out[y0:y1][take] = concept[py[take], px[take]]
            confidence_out[y0:y1][take] = sampled_confidence[take].astype(np.float16)
    return concept_out, confidence_out


def _rgba_layer(concept: np.ndarray, confidence: np.ndarray, colours: np.ndarray, alpha: float) -> Image.Image:
    rgb = colours[concept]
    opacity = np.where(concept > 0, np.clip(confidence.astype(np.float32) * alpha, 0.0, 1.0), 0.0)
    return Image.fromarray(np.dstack((rgb, (opacity * 255).astype(np.uint8))), "RGBA")


def _legend_entries(layer_data: dict[str, tuple[np.ndarray, np.ndarray]], id2label: dict[int, str]) -> list[str]:
    entries: list[str] = []
    for layer_name in LAYER_NAMES:
        labels = layer_data[layer_name][0]
        ids, counts = np.unique(labels[labels > 0], return_counts=True)
        if len(ids):
            order = np.argsort(counts)[::-1][:6]
            names = ", ".join(id2label[int(ids[index])] for index in order)
            entries.append(f"{layer_name}: {names}")
    return entries


def render_layer_diagnostics(
    layer_data: dict[str, tuple[np.ndarray, np.ndarray]],
    id2label: dict[int, str],
    out: pathlib.Path,
    panorama: pathlib.Path | None,
) -> None:
    """Write equirectangular-safe diagnostic rasters, never projection inputs."""
    colours = palette(len(id2label))
    for layer_name, (concept, confidence) in layer_data.items():
        Image.fromarray(colours[concept], "RGB").save(out / f"panorama_{layer_name}.png")
        _rgba_layer(concept, confidence, colours, 0.78).save(out / f"panorama_{layer_name}.png.rgba.png")

    if panorama is None:
        return
    with Image.open(panorama) as source:
        source = source.convert("RGBA").resize(layer_data["support"][0].shape[::-1])
    composed = source
    # Low-alpha support retains the scene context. Material and clutter remain
    # independent artifacts and are composed only for human inspection.
    for layer_name, alpha in (("support", 0.22), ("material", 0.58), ("clutter", 0.68)):
        concept, confidence = layer_data[layer_name]
        composed = Image.alpha_composite(composed, _rgba_layer(concept, confidence, colours, alpha))
    draw = ImageDraw.Draw(composed)
    lines = ["SAM concept layers: diagnostic only", *_legend_entries(layer_data, id2label)]
    line_height = 18
    box_height = 10 + line_height * len(lines)
    left, top = min(8, composed.width - 1), min(8, composed.height - 1)
    right = max(left, min(composed.width - 1, 900))
    bottom = max(top, min(composed.height - 1, top + box_height))
    draw.rectangle((left, top, right, bottom), fill=(0, 0, 0, 190))
    for index, line in enumerate(lines):
        draw.text((16, 13 + index * line_height), line, fill=(255, 255, 255, 255))
    composed.save(out / "panorama_layered_overlay.png")


def fuse(args: argparse.Namespace) -> None:
    catalog = ConceptCatalog.load(args.concepts)
    concept_ids, id2label = load_concepts(args.concepts)
    rules = layer_rules(catalog)
    views = {view.name: view for view in inference_views()}
    layers: dict[str, list[tuple[object, np.ndarray, np.ndarray]]] = {rule.name: [] for rule in rules}
    instance_offset = 0
    for path in sorted(args.predictions.glob("*.npz")):
        if path.stem not in views:
            continue
        masks, labels, kinds, scores = unpack_masks(path)
        view_data = view_layers(
            masks,
            labels,
            kinds,
            scores,
            concept_ids,
            rules,
        )
        instance_offset += len(masks)
        for layer_name, (concept, confidence) in view_data.items():
            layers[layer_name].append((views[path.stem], concept, confidence))

    found = {view.name for view, *_ in layers["support"]}
    if set(views) != found:
        missing = sorted(set(views) - found)
        raise SystemExit(f"missing SAM predictions for: {', '.join(missing)}")

    width, height = args.output_width, args.output_width // 2
    layer_data = {
        layer_name: fuse_layer(layer_views, width=width, height=height, row_chunk=args.row_chunk)
        for layer_name, layer_views in layers.items()
    }
    support_concept, support_confidence = layer_data["support"]
    clutter_concept, clutter_confidence = layer_data["clutter"]

    args.out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out / "panorama_concepts.npz",
        # Compatibility winner for older consumers. It is intentionally not a
        # projection target because it flattens concurrent physical evidence.
        concept=np.where(clutter_concept > 0, clutter_concept, support_concept),
        kind=np.where(clutter_concept > 0, KIND_ID["object"], KIND_ID["surface"]).astype(np.uint8),
        confidence=np.where(clutter_concept > 0, clutter_confidence, support_confidence).astype(np.float16),
        support_concept=support_concept,
        support_confidence=support_confidence,
        material_concept=layer_data["material"][0],
        material_confidence=layer_data["material"][1],
        clutter_concept=clutter_concept,
        clutter_confidence=clutter_confidence,
        dynamic_clutter_concept=layer_data["dynamic_clutter"][0],
        dynamic_clutter_confidence=layer_data["dynamic_clutter"][1],
    )
    colours = palette(len(id2label))
    # Keep this stable filename as the material-detail quicklook. The support
    # façade remains available separately, so a broad prompt cannot hide a
    # detected window in the default image anymore.
    Image.fromarray(colours[layer_data["material"][0]], "RGB").save(args.out / "panorama_concepts.png")
    render_layer_diagnostics(layer_data, id2label, args.out, args.panorama)
    manifest = {
        "concept_id2label": id2label,
        "kind_id2label": {0: "unlabelled", 1: "surface", 2: "object"},
        "shape": [height, width],
        "source_instances_before_cross_view_deduplication": instance_offset,
        "layers": {
            "support": "all static-surface candidates, independently stitched",
            "material": "surface material-detail candidates with a window/door/material ordering hint",
            "clutter": "all object candidates, independently stitched",
            "dynamic_clutter": "object candidates with movable or transient probability at least 0.5",
        },
        "overlap_policy": "layer-local confidence with angular-centre weighting; layers are non-exclusive",
        "projection_note": "diagnostic layers do not alter camera geometry or projection; resolve support/depth conflicts during 3D fusion",
    }
    (args.out / "concepts.json").write_text(json.dumps(manifest, indent=2))
    print(f"[concept-fusion] {instance_offset} view-local instances")
    print(f"[concept-fusion] -> {args.out / 'panorama_concepts.npz'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument(
        "--panorama",
        type=pathlib.Path,
        help="optional equirectangular source image for a diagnostic alpha overlay",
    )
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--row-chunk", type=int, default=128)
    fuse(parser.parse_args())


if __name__ == "__main__":
    main()
