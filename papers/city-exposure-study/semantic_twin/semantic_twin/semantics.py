"""Dense panorama semantics, with an open-vocabulary material backend on top.

Two segmentation backends run over the same rectilinear views, and they resolve
different axes on purpose.

*Mask2Former on Mapillary Vistas* is dense. Every pixel gets exactly one of 65
street-scene classes, the partition is complete, and at native resolution it is
strong on small infrastructure: Pole, Street Light, Traffic Sign, Utility Pole,
Curb, Bike Rack. It owns the **entity** axis, and nothing overwrites it.

*SAM 3* is open vocabulary and returns overlapping instances with no coverage
guarantee. It owns the **material** axis, because Vistas cannot express material
at all: one ``Building`` class covers brick, render, ashlar stone, glass curtain
wall and metal cladding, whose permittivity, conductivity and roughness are not
close to each other.

The two combine as a cascade rather than a vote.

1. The dense pass runs first and partitions the view.
2. Its class histogram gates the prompt set: a facade-material prompt is not
   asked of a view with no building pixels. Prompts whose entity support is
   unknown are never gated away.
3. SAM 3 runs on the surviving prompts.
4. The material axis is dense everywhere. Where no concept fires it is the
   Vistas class prior ``p(material | entity)``, which for ``Building`` is
   deliberately flat. Where a concept fires **and its entity support contains
   the Vistas class underneath it**, the concept's sharper distribution
   replaces the prior. That last condition is what stops a ``brick facade`` mask
   spilling onto a pedestrian: Vistas resolves who is standing there, SAM 3
   resolves what the wall behind them is made of.

Every pixel therefore keeps a dense entity, a dense material distribution, and a
record of which backend supplied the material.

Run after :mod:`semantic_twin.panorama`::

    ../../../.venv/bin/python -m semantic_twin.semantics \
        --panorama data/panoramas/korenmarkt/panorama_z5.jpg \
        --out data/panoramas/korenmarkt/semantics \
        --backend hybrid --concepts config/semantic_concepts.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from .concepts import BackendBridge, ConceptCatalog, PromptGate, gate_prompts
from .pano_geometry import (
    PerspectiveView,
    directions_to_equirectangular,
    inference_views,
    perspective_directions,
    view_pixel_coordinates,
)

MODEL = "facebook/mask2former-swin-large-mapillary-vistas-semantic"
BRIDGE = "mask2former_mapillary_vistas"

# The processor saved with the Mapillary Vistas checkpoint carries
# ``{"height": 384, "width": 384}`` with ``do_resize`` on, so an unmodified
# processor downsamples every crop to 384 x 384 and returns 96 x 96 mask logits
# no matter how large the crop was.  The inference resolution is therefore set
# explicitly here instead of being inherited from the checkpoint.  Measured on
# one real Korenmarkt crop on an RTX A6000, distinct Vistas classes recovered
# against wall-clock cost per crop:
#
#     384 -> 96 x 96 logits,   15 classes,   97 ms
#    1024 -> 256 x 256,        26 classes,  348 ms
#    1536 -> 384 x 384,        32 classes,  666 ms
#    2048 -> 512 x 512,        31 classes, 1240 ms, 97.0 percent agreement with 1536
#
# 1536 is where the small mmWave clutter appears: Pole, Street Light, Utility
# Pole, Traffic Light, Traffic Sign front and back, Bike Rack, Mailbox, Curb,
# On Rails, Parking and Other Rider are only recovered there.  2048 costs 1.9x
# more and 5.3 GiB of device memory for no additional class, so the default
# stops at 1536.  Crops are extracted at the same size so the model sees native
# pixels: on a 1024 crop, upsampling to 1536 recovered no extra class.
DEFAULT_INFERENCE_SIZE = 1536
DEFAULT_VIEW_SIZE = 1536

# A dense class occupying fewer pixels than this in a view is not taken as
# evidence that the class is present, so it does not unlock its concept prompts.
# 256 pixels is 0.011 percent of a 1536 x 1536 crop, which is small enough to
# keep a distant drainpipe or a single overhead cable while still shutting off
# the facade prompts on a view that is entirely sky and pavement.
DEFAULT_GATE_MIN_PIXELS = 256


@dataclass(frozen=True)
class ViewPrediction:
    view: PerspectiveView
    image_file: str
    labels_file: str
    confidence_file: str
    concept_file: str = ""
    prompts_asked: int = 0
    prompts_skipped: int = 0
    concept_instances: int = 0
    concept_seconds: float = 0.0


MATERIAL_HINTS = {
    "sky": "none",
    "person": "human_tissue",
    "bicyclist": "human_tissue",
    "motorcyclist": "human_tissue",
    "bird": "animal_tissue",
    "ground animal": "animal_tissue",
    "vegetation": "vegetation",
    "water": "water",
    "road": "asphalt",
    "lane marking - general": "road_paint",
    "lane marking - crosswalk": "road_paint",
    "sidewalk": "concrete",
    "curb": "concrete",
    "terrain": "soil",
    "sand": "soil",
    "snow": "snow",
    "building": "unknown_building",
    "wall": "unknown_wall",
    "bridge": "concrete",
    "tunnel": "concrete",
    "pole": "metal",
    "utility pole": "metal",
    "traffic light": "metal",
    "traffic sign (front)": "metal",
    "traffic sign (back)": "metal",
    "street light": "metal",
    "fire hydrant": "metal",
    "bench": "unknown_furniture",
    "bike rack": "metal",
    "bollard": "metal",
    "trash can": "metal",
    "car": "vehicle_composite",
    "truck": "vehicle_composite",
    "bus": "vehicle_composite",
    "motorcycle": "vehicle_composite",
    "bicycle": "vehicle_composite",
    "boat": "vehicle_composite",
    "caravan": "vehicle_composite",
    "trailer": "vehicle_composite",
}


def material_hints(id2label: dict[int, str]) -> tuple[np.ndarray, list[str]]:
    """Map an entity vocabulary to a compact, explicitly provisional RF layer.

    Superseded by :func:`vistas_material_prior` for anything that has to reach
    an RF library row. It is retained because ``project_semantics.py`` writes
    its ``material_hint`` raster into ``scene.xml``, and because a single winning
    name is a useful quicklook even where the real evidence is a distribution.
    """
    names = ["unknown"]
    per_entity = np.zeros(max(id2label, default=-1) + 1, dtype=np.uint16)
    for class_id, label in id2label.items():
        hint = MATERIAL_HINTS.get(label.casefold(), "unknown")
        if hint not in names:
            names.append(hint)
        per_entity[class_id] = names.index(hint)
    return per_entity, names


def vistas_material_prior(
    id2label: dict[int, str],
    catalog: ConceptCatalog,
    bridge: BackendBridge,
) -> np.ndarray:
    """Dense-class-by-material prior table, one row per Vistas class.

    A Vistas class alone does not determine a material, so every row is a
    distribution. Classes the bridge has no entry for fall back to all mass on
    ``unknown``, which keeps them visible as unresolved rather than guessed.
    """
    materials = catalog.taxonomy["materials"]
    unknown_index = materials.index("unknown")
    table = np.zeros((max(id2label, default=-1) + 1, len(materials)), dtype=np.float32)
    for class_id, label in id2label.items():
        distribution = bridge.material_prior.get(label)
        if not distribution:
            table[class_id, unknown_index] = 1.0
            continue
        for material, mass in distribution.items():
            table[class_id, materials.index(material)] = mass
    return table


def concept_support_table(
    id2label: dict[int, str],
    catalog: ConceptCatalog,
    bridge: BackendBridge,
) -> np.ndarray:
    """Concept-by-dense-class compatibility, row 0 reserved for no concept.

    True means the concept may claim the material of a pixel that the dense pass
    assigned to that class. This is the guard that keeps the two backends
    complementary: without it a broad open-vocabulary facade mask silently
    repaints the people and vehicles standing in front of the facade.

    Concepts that name an entity are admissible over that entity's dense
    classes. Material-only concepts have no entity to route on, so they are
    admissible where the dense class prior does not already exclude their
    material.
    """
    columns = max(id2label, default=-1) + 1
    table = np.zeros((len(catalog.concepts) + 1, columns), dtype=bool)
    for index, concept in enumerate(catalog.concepts):
        admissible = bridge.admissible_classes(concept)
        for class_id, label in id2label.items():
            table[index + 1, class_id] = label in admissible
    return table


@dataclass(frozen=True)
class MaterialLayer:
    """Dense material evidence with the backend that supplied each pixel.

    ``prior_mass`` is deliberately not called a probability. On a concept-backed
    pixel it is the winning share of that concept's hand-written material
    distribution, and on a prior-backed pixel it is the winning share of the
    dense class prior. Neither carries the detection score, which lives in
    ``detection_confidence``. Multiplying them is not the posterior either, so
    the two are kept apart and named for what they are.
    """

    material: np.ndarray
    prior_mass: np.ndarray
    concept: np.ndarray
    detection_confidence: np.ndarray
    source: np.ndarray
    source_names: tuple[str, ...] = ("vistas_prior", "concept_backend")

    def concept_fraction(self) -> float:
        return float(np.count_nonzero(self.source == 1) / self.source.size) if self.source.size else 0.0


def resolve_material(
    entity: np.ndarray,
    concept: np.ndarray,
    confidence: np.ndarray,
    *,
    prior_table: np.ndarray,
    concept_material: np.ndarray,
    support_table: np.ndarray,
) -> MaterialLayer:
    """Sharpen the dense material prior with concept evidence where it is admissible.

    A concept only claims a pixel when the dense class underneath it is in that
    concept's entity support. Rejected pixels keep the dense prior, so the output
    is dense whatever the open-vocabulary pass did or did not find.

    The full per-pixel distribution is never materialised. Both tables are a few
    dozen rows, so reducing them first and indexing afterwards is exact and
    keeps an 8192 x 4096 sphere inside a few hundred megabytes instead of
    several gigabytes. The distribution stays reconstructible downstream from
    the emitted concept and entity rasters plus the tables in the manifest.
    """
    if not entity.shape == concept.shape == confidence.shape:
        raise ValueError("entity, concept and confidence rasters must have the same shape")
    admissible = (concept > 0) & support_table[concept, entity]
    prior_choice, prior_share = prior_table.argmax(axis=1), prior_table.max(axis=1)
    concept_choice, concept_share = concept_material.argmax(axis=1), concept_material.max(axis=1)
    return MaterialLayer(
        material=np.where(admissible, concept_choice[concept], prior_choice[entity]).astype(np.uint16),
        prior_mass=np.where(admissible, concept_share[concept], prior_share[entity]).astype(np.float16),
        concept=np.where(admissible, concept, 0).astype(np.uint16),
        # Zeroed wherever the concept was rejected. Leaving the fused layer
        # confidence through would advertise a confident detection for a concept
        # that is not in the output.
        detection_confidence=np.where(admissible, confidence, np.float16(0.0)).astype(np.float16),
        source=admissible.astype(np.uint8),
    )


class Mask2FormerBackend:
    """CPU/GPU semantic baseline with the Mapillary Vistas vocabulary."""

    def __init__(
        self,
        model_name: str = MODEL,
        device: str = "auto",
        *,
        inference_size: int = DEFAULT_INFERENCE_SIZE,
    ) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
        except ImportError as exc:
            raise SystemExit("install optional dependencies with `pip install -r requirements-semantics.txt`") from exc

        if inference_size < 32:
            raise ValueError("inference_size must be at least 32 pixels")
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch = torch
        self.device = device
        self.model_name = model_name
        self.inference_size = int(inference_size)
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.processor_saved_size = dict(getattr(self.processor, "size", {}) or {})
        self.model = Mask2FormerForUniversalSegmentation.from_pretrained(model_name, use_safetensors=True).to(device)
        self.model.eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        # The Hub revision the weights actually came from. A model name alone
        # does not pin a checkpoint, because the same name can be re-uploaded.
        self.checkpoint_digest = getattr(self.model.config, "_commit_hash", None)

    def predict(self, image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        import torch.nn.functional as functional

        inputs = self.processor(
            images=image,
            return_tensors="pt",
            size={"height": self.inference_size, "width": self.inference_size},
        )
        inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
        with self.torch.inference_mode():
            outputs = self.model(**inputs)
        class_probability = outputs.class_queries_logits.softmax(dim=-1)[..., :-1]
        mask_probability = outputs.masks_queries_logits.sigmoid()
        mask_probability = functional.interpolate(
            mask_probability,
            size=image.size[::-1],
            mode="bilinear",
            align_corners=False,
        )
        semantic_probability = self.torch.einsum("bqc,bqhw->bchw", class_probability, mask_probability)[0]
        scores, labels = semantic_probability.max(dim=0)
        return (
            labels.detach().cpu().numpy().astype(np.uint16),
            scores.detach().cpu().numpy().astype(np.float16),
        )


def perspective_crop(panorama_rgb: np.ndarray, view: PerspectiveView, *, width: int, height: int) -> Image.Image:
    """Sample one rectilinear view from an already decoded panorama array.

    This is :func:`pano_geometry.extract_perspective` with the decode hoisted
    out. That function re-materialises the panorama on every call, which on the
    16384 x 8192 Korenmarkt image is 403 MB per view: 1.54 s per view against
    0.61 s here, so 40 s against 16 s over the 26 inference views.
    """
    if panorama_rgb.ndim != 3 or panorama_rgb.shape[2] != 3:
        raise ValueError("panorama_rgb must be a decoded (rows, columns, 3) RGB array")
    directions = perspective_directions(view, width, height)
    u, v = directions_to_equirectangular(directions)
    xs = u * panorama_rgb.shape[1] - 0.5
    ys = np.clip(v * panorama_rgb.shape[0] - 0.5, 0.0, panorama_rgb.shape[0] - 1.0)
    coords = np.stack([ys, xs], axis=0)
    channels = [map_coordinates(panorama_rgb[:, :, c], coords, order=1, mode="grid-wrap") for c in range(3)]
    return Image.fromarray(np.stack(channels, axis=2).astype(np.uint8), "RGB")


@dataclass(frozen=True)
class _ViewFootprint:
    """Where on the equirectangular output one perspective view can land.

    The frustum maps to a geodesically convex region, so its latitude extent and
    its longitude extent inside any latitude band are both attained on its
    border. Sampling the border once therefore bounds the region exactly enough
    to skip the output rows and columns a view cannot reach. A view that
    strictly contains a pole wraps every longitude, and is not culled in yaw.
    """

    centre: np.ndarray
    centre_yaw_deg: float
    yaw_offset_deg: np.ndarray
    pitch_deg: np.ndarray
    minimum_pitch_deg: float
    maximum_pitch_deg: float
    contains_pole: bool
    margin_deg: float
    width: int

    def column_spans(self, pitch_low_deg: float, pitch_high_deg: float) -> tuple[tuple[int, int], ...]:
        """Output column ranges this view can touch inside one latitude band."""
        if pitch_high_deg < self.minimum_pitch_deg - self.margin_deg:
            return ()
        if pitch_low_deg > self.maximum_pitch_deg + self.margin_deg:
            return ()
        if self.contains_pole:
            return ((0, self.width),)
        in_band = (self.pitch_deg >= pitch_low_deg - self.margin_deg) & (
            self.pitch_deg <= pitch_high_deg + self.margin_deg
        )
        if not np.any(in_band):
            return ()
        offsets = self.yaw_offset_deg[in_band]
        return _column_spans(
            self.centre_yaw_deg,
            float(offsets.min()) - self.margin_deg,
            float(offsets.max()) + self.margin_deg,
            self.width,
        )


def _column_spans(centre_yaw_deg: float, low_offset_deg: float, high_offset_deg: float, width: int) -> tuple:
    if high_offset_deg - low_offset_deg >= 360.0:
        return ((0, width),)
    start = int(np.floor(((centre_yaw_deg + low_offset_deg) / 360.0 + 0.5) * width - 0.5))
    stop = int(np.ceil(((centre_yaw_deg + high_offset_deg) / 360.0 + 0.5) * width - 0.5)) + 1
    span = stop - start
    if span >= width:
        return ((0, width),)
    start %= width
    if start + span <= width:
        return ((start, start + span),)
    return ((start, width), (0, start + span - width))


def _view_footprint(
    view: PerspectiveView,
    view_width: int,
    view_height: int,
    output_width: int,
    output_height: int,
    *,
    samples: int = 256,
) -> _ViewFootprint:
    grid = perspective_directions(view, samples, samples)
    border = np.concatenate((grid[0], grid[-1], grid[1:-1, 0], grid[1:-1, -1]))
    yaw_deg = np.degrees(np.arctan2(border[:, 0], border[:, 1]))
    pitch_deg = np.degrees(np.arcsin(np.clip(border[:, 2], -1.0, 1.0)))
    centre_yaw_deg = float(np.degrees(np.arctan2(*perspective_directions(view, 1, 1)[0, 0, :2])))
    offsets = (yaw_deg - centre_yaw_deg + 180.0) % 360.0 - 180.0
    # The border grid samples pixel centres, so it sits half a cell inside the
    # true frustum edge. One whole cell, plus one output pixel, covers that.
    margin_deg = view.fov_deg / samples + max(360.0 / output_width, 180.0 / output_height)
    north = _contains_pole(view, view_width, view_height, 1.0)
    south = _contains_pole(view, view_width, view_height, -1.0)
    return _ViewFootprint(
        centre=perspective_directions(view, 1, 1)[0, 0],
        centre_yaw_deg=centre_yaw_deg,
        yaw_offset_deg=offsets,
        pitch_deg=pitch_deg,
        minimum_pitch_deg=-90.0 if south else float(pitch_deg.min()),
        maximum_pitch_deg=90.0 if north else float(pitch_deg.max()),
        contains_pole=north or south,
        margin_deg=margin_deg,
        width=output_width,
    )


def _contains_pole(view: PerspectiveView, view_width: int, view_height: int, sign: float) -> bool:
    pole = np.array([[[0.0, 0.0, sign]]])
    px, py, valid = view_pixel_coordinates(pole, view, view_width, view_height)
    if not bool(valid[0, 0]):
        return False
    # A pole sitting exactly on the frustum edge, as it does for a 90 degree
    # view centred at 45 degrees elevation, does not sweep every longitude.
    return 0 < int(px[0, 0]) < view_width - 1 and 0 < int(py[0, 0]) < view_height - 1


def present_classes(labels: np.ndarray, id2label: dict[int, str], *, minimum_pixels: int) -> frozenset[str]:
    """Dense classes with enough area in one view to be taken as present."""
    values, counts = np.unique(labels, return_counts=True)
    return frozenset(
        id2label[int(value)]
        for value, count in zip(values, counts, strict=True)
        if count >= minimum_pixels and int(value) in id2label
    )


def fuse_layers(
    views: list[PerspectiveView],
    layers: dict[str, list[tuple[np.ndarray, np.ndarray]]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
    require_nonzero: bool = False,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Fuse several co-registered layers over the sphere in one geometric pass.

    Overlap is resolved by confidence times angular distance from the view
    centre, independently per layer. Every view is bounded to its
    equirectangular footprint first, so a view is only evaluated on the rows and
    columns it can actually reach. That cull is what took one panorama from
    roughly 73 s to 17 s at the default 8192 pixel output width.

    Fusing the layers together rather than one call each shares the expensive
    half of the work. The projection, the footprint spans and the direction
    block depend only on the view, not on what is painted in it, so the four
    concept layers cost one traversal instead of four.

    ``require_nonzero`` switches from a dense partition, where label zero is a
    real class and any valid sample beats no sample, to a sparse layer where
    zero means "nothing here" and only a positive score can claim a pixel.
    """
    if not layers:
        raise ValueError("fuse_layers needs at least one layer")
    counts = {len(items) for items in layers.values()} | {len(views)}
    if len(counts) != 1:
        raise ValueError("every layer must supply one raster pair per view")
    shapes = [next(iter(layers.values()))[index][0].shape for index in range(len(views))]
    for name, per_view in layers.items():
        for index, (raster, confidence) in enumerate(per_view):
            if raster.shape != shapes[index] or confidence.shape != shapes[index]:
                raise ValueError(f"layer {name} disagrees with the others on the raster shape of view {index}")
    outputs = {
        name: (
            np.zeros((height, width), dtype=np.uint16),
            np.zeros((height, width), dtype=np.float16),
            np.full((height, width), 0.0 if require_nonzero else -np.inf, dtype=np.float32),
        )
        for name in layers
    }
    footprints = [
        _view_footprint(view, shape[1], shape[0], width, height) for view, shape in zip(views, shapes, strict=True)
    ]

    yaw = ((np.arange(width) + 0.5) / width - 0.5) * 2.0 * np.pi
    sin_yaw, cos_yaw = np.sin(yaw), np.cos(yaw)
    for y0 in range(0, height, row_chunk):
        y1 = min(y0 + row_chunk, height)
        pitch = (0.5 - (np.arange(y0, y1) + 0.5) / height) * np.pi
        directions = np.empty((y1 - y0, width, 3), dtype=np.float64)
        directions[..., 0] = sin_yaw[None, :] * np.cos(pitch)[:, None]
        directions[..., 1] = cos_yaw[None, :] * np.cos(pitch)[:, None]
        directions[..., 2] = np.sin(pitch)[:, None]
        pitch_low = float(np.degrees(pitch[-1]))
        pitch_high = float(np.degrees(pitch[0]))
        for index, (view, footprint, shape) in enumerate(zip(views, footprints, shapes, strict=True)):
            for x0, x1 in footprint.column_spans(pitch_low, pitch_high):
                block = directions[:, x0:x1]
                px, py, valid = view_pixel_coordinates(block, view, shape[1], shape[0])
                if not np.any(valid):
                    continue
                flat = py.astype(np.intp) * shape[1] + px
                angular = np.clip(block @ footprint.centre, 0.0, 1.0) ** 4
                for name, per_view in layers.items():
                    labels, confidence = per_view[index]
                    flat_labels = labels.reshape(-1)[flat]
                    sampled_confidence = confidence.reshape(-1)[flat].astype(np.float32)
                    score = sampled_confidence * angular
                    labels_out, confidence_out, best_out = outputs[name]
                    best = best_out[y0:y1, x0:x1]
                    take = valid & (score > best)
                    if require_nonzero:
                        take &= flat_labels > 0
                    best[take] = score[take]
                    labels_out[y0:y1, x0:x1][take] = flat_labels[take]
                    confidence_out[y0:y1, x0:x1][take] = sampled_confidence[take].astype(np.float16)
    return {name: (labels, confidence) for name, (labels, confidence, _best) in outputs.items()}


def fuse_predictions(
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]],
    *,
    width: int,
    height: int,
    row_chunk: int = 128,
    require_nonzero: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse one layer over the sphere. See :func:`fuse_layers`."""
    fused = fuse_layers(
        [view for view, _labels, _confidence in predictions],
        {"layer": [(labels, confidence) for _view, labels, confidence in predictions]},
        width=width,
        height=height,
        row_chunk=row_chunk,
        require_nonzero=require_nonzero,
    )
    return fused["layer"]


def palette(n: int) -> np.ndarray:
    """Stable high-contrast colours, with class zero left black."""
    rng = np.random.default_rng(0xAE615)
    colours = rng.integers(32, 256, size=(n, 3), dtype=np.uint8)
    if n:
        colours[0] = 0
    return colours


@dataclass
class ConceptPass:
    """Optional open-vocabulary pass bolted onto the dense one."""

    catalog: ConceptCatalog
    bridge: BackendBridge
    backend: Any
    cache_dir: pathlib.Path
    cache_key: str
    minimum_pixels: int = DEFAULT_GATE_MIN_PIXELS
    gates: list[PromptGate] = field(default_factory=list)
    elapsed_s: float = 0.0

    def run_view(
        self,
        view: PerspectiveView,
        image: Image.Image | None,
        labels: np.ndarray,
        id2label: dict[int, str],
        *,
        force: bool,
    ) -> tuple[Any, PromptGate | None]:
        """Segment one view against its gated prompts, or return the cached one.

        The gate is evaluated before the cache is consulted, because which
        prompts a view was asked is part of what determines the answer and the
        cache key cannot see it: the gate is decided from the dense labels, not
        from the catalogue. A stored view is only accepted when it was asked the
        same prompt set, so changing ``minimum_pixels`` or the entity-support
        table re-segments rather than quietly reusing a differently gated run.

        A cache hit returns no gate, because the gate that produced the stored
        answer belongs to the run that wrote it and reporting this run's gate
        against it would be a quiet lie in the manifest.
        """
        from .sam3_concepts import load_prediction, save_prediction

        destination = self.cache_dir / f"{view.name}.npz"
        present = present_classes(labels, id2label, minimum_pixels=self.minimum_pixels)
        gate = gate_prompts(self.catalog, self.bridge, present, view=view.name)
        if not force:
            cached = load_prediction(destination, key=self.cache_key)
            if cached is not None and set(cached.asked_prompts) == set(gate.prompts):
                return cached, None
        if image is None:
            raise ValueError(f"{view.name} has no usable cached concepts and no image to segment")
        self.gates.append(gate)
        prediction = self.backend.predict(image, gate.prompts)
        self.elapsed_s += prediction.elapsed_s
        save_prediction(destination, prediction, key=self.cache_key)
        return prediction, gate


def file_digest(path: pathlib.Path, *, chunk: int = 1 << 22) -> str:
    """Content digest of a source file, streamed so a 22 MB panorama is cheap."""
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            sha.update(block)
    return sha.hexdigest()[:16]


def dense_cache_settings(backend: Any, view_size: int, panorama: pathlib.Path | None = None) -> dict[str, Any]:
    """Everything about the dense pass that makes its cached views comparable.

    The panorama digest is here because the view directory is named after the
    site, not after the capture. Two panoramas of the same square written into
    one tree would otherwise share crops and label maps.
    """
    return {
        "model": getattr(backend, "model_name", MODEL),
        "checkpoint": getattr(backend, "checkpoint_digest", None),
        "inference_size": int(getattr(backend, "inference_size", DEFAULT_INFERENCE_SIZE)),
        "view_size": int(view_size),
        "panorama": file_digest(panorama) if panorama is not None else None,
    }


def reusable_dense_cache(views_dir: pathlib.Path, settings: dict[str, Any]) -> bool:
    """Whether cached view labels were produced under exactly these settings.

    A mismatch recomputes. It never warns and never partially reuses, because
    an untyped cache is the reason every semantic output in this repository ran
    at the checkpoint processor's 384 without anyone noticing, and because a
    label map from another model or another resolution produces a plausible
    wrong number with no trace of where it came from.
    """
    stamp = views_dir / "cache_settings.json"
    if not stamp.exists():
        return False
    return json.loads(stamp.read_text()) == settings


def predict_views(
    panorama: Image.Image,
    backend: Any,
    views_dir: pathlib.Path,
    *,
    view_size: int,
    force: bool = False,
    concepts: ConceptPass | None = None,
    panorama_path: pathlib.Path | None = None,
) -> tuple[list[tuple[PerspectiveView, np.ndarray, np.ndarray]], list[ViewPrediction], dict[str, Any]]:
    """Segment every inference view, decoding the panorama exactly once.

    The dense pass always runs. When ``concepts`` is supplied the dense labels
    of each view immediately gate that view's prompt set, so the open-vocabulary
    model never sees a prompt the dense partition has already ruled out.
    """
    panorama_rgb = np.asarray(panorama.convert("RGB"))
    settings = dense_cache_settings(backend, view_size, panorama_path)
    reuse = not force and reusable_dense_cache(views_dir, settings)
    predictions: list[tuple[PerspectiveView, np.ndarray, np.ndarray]] = []
    manifest: list[ViewPrediction] = []
    concept_predictions: dict[str, Any] = {}
    for view in inference_views():
        image_path = views_dir / f"{view.name}.jpg"
        labels_path = views_dir / f"{view.name}_labels.npy"
        confidence_path = views_dir / f"{view.name}_confidence.npy"
        image: Image.Image | None = None
        if reuse and labels_path.exists() and confidence_path.exists():
            labels = np.load(labels_path)
            confidence = np.load(confidence_path)
        else:
            image = perspective_crop(panorama_rgb, view, width=view_size, height=view_size)
            image.save(image_path, quality=95)
            labels, confidence = backend.predict(image)
            np.save(labels_path, labels)
            np.save(confidence_path, confidence)
        predictions.append((view, labels, confidence))
        record = ViewPrediction(view, str(image_path), str(labels_path), str(confidence_path))
        if concepts is not None:
            if image is None and image_path.exists():
                with Image.open(image_path) as source:
                    image = source.convert("RGB")
            prediction, gate = concepts.run_view(view, image, labels, backend.id2label, force=force)
            concept_predictions[view.name] = prediction
            asked = gate.prompts if gate is not None else prediction.asked_prompts
            record = ViewPrediction(
                view,
                str(image_path),
                str(labels_path),
                str(confidence_path),
                concept_file=str(concepts.cache_dir / f"{view.name}.npz"),
                prompts_asked=len(asked),
                prompts_skipped=len(gate.skipped) if gate is not None else len(concepts.catalog.concepts) - len(asked),
                concept_instances=len(prediction.labels),
                concept_seconds=round(float(getattr(prediction, "elapsed_s", 0.0)), 3),
            )
        manifest.append(record)
        print(f"[semantic] {view.name}")
    (views_dir / "cache_settings.json").write_text(json.dumps(settings, indent=2))
    return predictions, manifest, concept_predictions


def _fuse_concept_layers(
    concept_predictions: dict[str, Any],
    catalog: ConceptCatalog,
    *,
    width: int,
    height: int,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    from .fuse_concepts import layer_rules, view_layers

    concept_ids = {name: index for index, name in enumerate(["unlabelled", *catalog.prompts])}
    rules = layer_rules(catalog)
    by_name = {view.name: view for view in inference_views()}
    views: list[PerspectiveView] = []
    layers: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {rule.name: [] for rule in rules}
    for name, prediction in concept_predictions.items():
        per_view = view_layers(
            prediction.masks,
            prediction.labels,
            prediction.kinds,
            prediction.scores,
            concept_ids,
            rules,
        )
        views.append(by_name[name])
        for layer_name, pair in per_view.items():
            layers[layer_name].append(pair)
    return fuse_layers(views, layers, width=width, height=height, require_nonzero=True)


def run(args: argparse.Namespace) -> None:
    out = args.out
    views_dir = out / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    backend = Mask2FormerBackend(args.model, args.device, inference_size=args.inference_size)

    concepts: ConceptPass | None = None
    catalog: ConceptCatalog | None = None
    if args.backend == "hybrid":
        from .sam3_concepts import MODEL as SAM3_MODEL
        from .sam3_concepts import Sam3ConceptBackend, cache_key

        if args.concepts is None:
            raise SystemExit("--backend hybrid needs --concepts pointing at the concept catalogue")
        catalog = ConceptCatalog.load(args.concepts)
        if BRIDGE not in catalog.bridges:
            raise SystemExit(f"the catalogue has no {BRIDGE} bridge, so prompts cannot be gated or fused")
        concept_dir = out / "concepts"
        concept_dir.mkdir(parents=True, exist_ok=True)
        concepts = ConceptPass(
            catalog=catalog,
            bridge=catalog.bridges[BRIDGE],
            backend=Sam3ConceptBackend(
                catalog,
                resolution=args.concept_resolution,
                threshold=args.concept_threshold,
                prompt_batch=args.prompt_batch,
            ),
            cache_dir=concept_dir,
            cache_key=cache_key(
                model=SAM3_MODEL,
                resolution=args.concept_resolution,
                threshold=args.concept_threshold,
                view_size=args.view_size,
                catalog=catalog,
            ),
            minimum_pixels=args.gate_min_pixels,
        )

    # Read before the run, because predict_views rewrites the stamp on its way
    # out. Without it the wall clock below is unreadable: a warm re-run over
    # cached views does fusion only and reports 8 to 11 s against a cold 58 s,
    # and nothing in the output said which of the two you were looking at.
    dense_cache_reused = not args.force and reusable_dense_cache(
        views_dir, dense_cache_settings(backend, args.view_size, args.panorama)
    )

    with Image.open(args.panorama) as panorama:
        predictions, manifest, concept_predictions = predict_views(
            panorama,
            backend,
            views_dir,
            view_size=args.view_size,
            force=args.force,
            concepts=concepts,
            panorama_path=args.panorama,
        )

    output_width = args.output_width
    output_height = output_width // 2
    labels, confidence = fuse_predictions(predictions, width=output_width, height=output_height)
    entity_to_material, material_names = material_hints(backend.id2label)
    material = entity_to_material[labels]
    arrays: dict[str, np.ndarray] = {
        "entity": labels,
        "material_hint": material,
        "confidence": confidence,
    }
    document: dict[str, Any] = {
        "backend": args.backend,
        "model": args.model,
        "entity_id2label": backend.id2label,
        "material_id2label": dict(enumerate(material_names)),
        "material_status": "provisional hints, refine with concept/material backend",
        "view_size": args.view_size,
        "inference_size": backend.inference_size,
        "processor_saved_size": backend.processor_saved_size,
        "checkpoint": backend.checkpoint_digest,
        "inference_size_status": "set explicitly, not inherited from the checkpoint processor",
        "shape": [output_height, output_width],
        "output_width": output_width,
        "dense_cache_reused": bool(dense_cache_reused),
        "wall_clock_covers": (
            "fusion only, the per-view labels came from the cache"
            if dense_cache_reused
            else "the full dense pass, 26 views segmented from the panorama"
        ),
    }

    if concepts is not None and catalog is not None:
        layer_data = _fuse_concept_layers(concept_predictions, catalog, width=output_width, height=output_height)
        prior_table = vistas_material_prior(backend.id2label, catalog, concepts.bridge)
        support_table = concept_support_table(backend.id2label, catalog, concepts.bridge)
        resolved = resolve_material(
            labels,
            layer_data["material"][0],
            layer_data["material"][1],
            prior_table=prior_table,
            concept_material=catalog.material_matrix(),
            support_table=support_table,
        )
        arrays.update(
            rf_material=resolved.material,
            rf_material_prior_mass=resolved.prior_mass,
            material_concept=resolved.concept,
            material_confidence=resolved.detection_confidence,
            material_source=resolved.source,
            support_concept=layer_data["support"][0],
            support_confidence=layer_data["support"][1],
            clutter_concept=layer_data["clutter"][0],
            clutter_confidence=layer_data["clutter"][1],
            dynamic_clutter_concept=layer_data["dynamic_clutter"][0],
            dynamic_clutter_confidence=layer_data["dynamic_clutter"][1],
        )
        rf_colours = palette(len(catalog.taxonomy["materials"]))
        Image.fromarray(rf_colours[resolved.material], "RGB").save(out / "panorama_rf_materials.png")
        asked = sum(len(gate.prompts) for gate in concepts.gates)
        offered = len(catalog.concepts) * len(concepts.gates)
        document.update(
            concept_backend=concepts.backend.manifest(),
            concept_cache_key=concepts.cache_key,
            concept_id2label=catalog.id2label(),
            rf_material_id2label=dict(enumerate(catalog.taxonomy["materials"])),
            material_source_id2label=dict(enumerate(resolved.source_names)),
            material_grounding={
                name: {"library": binding.library, "row": binding.row, "status": binding.status}
                for name, binding in catalog.material_grounding.items()
            },
            vistas_material_prior=concepts.bridge.material_prior,
            gate={
                "minimum_pixels": concepts.minimum_pixels,
                "views_segmented": len(concepts.gates),
                "views_from_cache": len(manifest) - len(concepts.gates),
                "prompts_offered": offered,
                "prompts_asked": asked,
                "saved_fraction": round(1.0 - asked / offered, 4) if offered else None,
                "per_view": [gate.as_dict() for gate in concepts.gates],
            },
            material_resolution={
                "concept_backed_fraction": round(resolved.concept_fraction(), 4),
                "prior_mass_status": (
                    "rf_material_prior_mass is the winning share of a hand-written distribution, "
                    "the concept's own where the concept was admitted and the dense class prior "
                    "otherwise. It is not a posterior and it does not include the detection score, "
                    "which is material_confidence and is zero wherever no concept was admitted."
                ),
                "rule": (
                    "concept evidence replaces the dense class prior only where that concept is "
                    "admissible over the dense class at the pixel: an entity-bearing concept needs "
                    "the class in its entity support, a material-only concept needs the class prior "
                    "to carry some mass on its material. Elsewhere the prior stands."
                ),
            },
            concept_seconds=round(concepts.elapsed_s, 2),
        )

    np.savez_compressed(out / "panorama_semantics.npz", **arrays)
    colours = palette(max(backend.id2label, default=0) + 1)
    Image.fromarray(colours[labels], "RGB").save(out / "panorama_entities.png")
    material_colours = palette(len(material_names))
    Image.fromarray(material_colours[material], "RGB").save(out / "panorama_material_hints.png")
    document["views"] = [asdict(record) for record in manifest]
    document["wall_clock_seconds"] = round(time.perf_counter() - started, 2)
    (out / "semantics.json").write_text(json.dumps(document, indent=2))
    print(f"[semantic] -> {out / 'panorama_semantics.npz'} in {document['wall_clock_seconds']:.1f} s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument(
        "--backend",
        choices=("mask2former", "hybrid"),
        default="mask2former",
        help="hybrid adds the SAM 3 concept pass and resolves the RF material axis.",
    )
    parser.add_argument("--concepts", type=pathlib.Path, help="concept catalogue, required by --backend hybrid")
    parser.add_argument("--view-size", type=int, default=DEFAULT_VIEW_SIZE)
    parser.add_argument(
        "--inference-size",
        type=int,
        default=DEFAULT_INFERENCE_SIZE,
        help="Square input the segmenter actually sees, instead of the checkpoint processor's 384.",
    )
    parser.add_argument("--concept-resolution", type=int, default=1008)
    parser.add_argument("--concept-threshold", type=float, default=0.35)
    parser.add_argument("--prompt-batch", type=int, default=32)
    parser.add_argument("--gate-min-pixels", type=int, default=DEFAULT_GATE_MIN_PIXELS)
    parser.add_argument("--output-width", type=int, default=8192)
    parser.add_argument("--force", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
