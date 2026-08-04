"""Segment one panorama end to end, and record what produced the answer.

This is the runner. Two backends run over the same rectilinear views and they
resolve different axes on purpose, so the order they run in is part of the
method rather than an implementation detail:

1. The dense pass runs first and partitions the view.
2. Its class histogram gates the prompt set, so a facade material prompt is
   never asked of a view with no building pixels. Prompts whose entity support
   is unknown are never gated away.
3. The prompted pass runs on the surviving prompts.
4. :func:`~semantic_twin.vision.material.resolve_material` lets a concept
   overwrite the dense class prior only where that concept is admissible over
   the dense class at the pixel.

Every pixel therefore keeps a dense entity, a dense material distribution, and a
record of which backend supplied the material.

Run after a panorama has been acquired, by
:mod:`semantic_twin.acquire.streetview` at ten of the eleven sites and by
:mod:`semantic_twin.acquire.mapillary` for the Korenmarkt walk::

    ../../../.venv/bin/python -m semantic_twin.cli.panorama \
        --panorama data/panoramas/korenmarkt/panorama_z5.jpg \
        --out data/panoramas/korenmarkt/semantics \
        --backend hybrid --concepts config/semantic_concepts.json
"""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from ..pano_geometry import PerspectiveView, inference_views
from .dense import (
    BRIDGE,
    DEFAULT_GATE_MIN_PIXELS,
    Mask2FormerBackend,
    dense_cache_settings,
    reusable_dense_cache,
)
from .fuse import fuse_layers, fuse_predictions, palette
from .material import concept_support_table, material_hints, resolve_material, vistas_material_prior
from .views import perspective_crop, present_classes
from .vocabulary import BackendBridge, ConceptCatalog, PromptGate, gate_prompts


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


@dataclass(frozen=True)
class PanoramaRunConfig:
    """Inputs for end-to-end panorama segmentation."""

    panorama: pathlib.Path
    out: pathlib.Path
    model: str
    device: str
    backend: str
    concepts: pathlib.Path | None
    view_size: int
    inference_size: int
    concept_resolution: int
    concept_threshold: float
    prompt_batch: int
    gate_min_pixels: int
    output_width: int
    force: bool


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
        from .prompted import load_prediction, save_prediction

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
    from .layers import layer_rules, view_layers

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


def vegetation_from_concepts(
    concept: np.ndarray,
    confidence: np.ndarray,
    catalog: ConceptCatalog,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resolve vegetation form only where a vegetation prompt supplied evidence.

    Dense ``Vegetation`` has no form information. Its pixels therefore stay at
    the reserved ``unresolved`` value instead of being treated as canopy. The
    subtype is diagnostic and may remain unresolved even when the form is known.
    """
    form_table, subtype_table = catalog.vegetation_tables()
    if concept.size and (int(concept.min()) < 0 or int(concept.max()) >= len(form_table)):
        raise ValueError("vegetation concept raster names a concept outside the catalogue")
    form = form_table[concept]
    subtype = subtype_table[concept]
    resolved_confidence = np.where(form > 0, confidence, 0.0).astype(np.float16)
    return form, subtype, resolved_confidence


def run(config: PanoramaRunConfig) -> None:
    out = config.out
    views_dir = out / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    backend = Mask2FormerBackend(config.model, config.device, inference_size=config.inference_size)

    concepts: ConceptPass | None = None
    catalog: ConceptCatalog | None = None
    if config.backend == "hybrid":
        from .prompted import MODEL as SAM3_MODEL
        from .prompted import Sam3ConceptBackend, cache_key

        if config.concepts is None:
            raise SystemExit("--backend hybrid needs --concepts pointing at the concept catalogue")
        catalog = ConceptCatalog.load(config.concepts)
        if BRIDGE not in catalog.bridges:
            raise SystemExit(f"the catalogue has no {BRIDGE} bridge, so prompts cannot be gated or fused")
        concept_dir = out / "concepts"
        concept_dir.mkdir(parents=True, exist_ok=True)
        concepts = ConceptPass(
            catalog=catalog,
            bridge=catalog.bridges[BRIDGE],
            backend=Sam3ConceptBackend(
                catalog,
                resolution=config.concept_resolution,
                threshold=config.concept_threshold,
                prompt_batch=config.prompt_batch,
            ),
            cache_dir=concept_dir,
            cache_key=cache_key(
                model=SAM3_MODEL,
                resolution=config.concept_resolution,
                threshold=config.concept_threshold,
                view_size=config.view_size,
                catalog=catalog,
            ),
            minimum_pixels=config.gate_min_pixels,
        )

    # Read before the run, because predict_views rewrites the stamp on its way
    # out. Without it the wall clock below is unreadable: a warm re-run over
    # cached views does fusion only and reports 8 to 11 s against a cold 58 s,
    # and nothing in the output said which of the two you were looking at.
    dense_cache_reused = not config.force and reusable_dense_cache(
        views_dir, dense_cache_settings(backend, config.view_size, config.panorama)
    )

    with Image.open(config.panorama) as panorama:
        predictions, manifest, concept_predictions = predict_views(
            panorama,
            backend,
            views_dir,
            view_size=config.view_size,
            force=config.force,
            concepts=concepts,
            panorama_path=config.panorama,
        )

    output_width = config.output_width
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
        "backend": config.backend,
        "model": config.model,
        "entity_id2label": backend.id2label,
        "material_id2label": dict(enumerate(material_names)),
        "material_status": "provisional hints, refine with concept/material backend",
        "view_size": config.view_size,
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
        vegetation_form, vegetation_subtype, vegetation_confidence = vegetation_from_concepts(
            layer_data["vegetation"][0],
            layer_data["vegetation"][1],
            catalog,
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
            vegetation_concept=layer_data["vegetation"][0],
            vegetation_form=vegetation_form,
            vegetation_subtype=vegetation_subtype,
            vegetation_confidence=vegetation_confidence,
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
            vegetation_form_id2label=dict(enumerate(catalog.vegetation_forms)),
            vegetation_subtype_id2label=dict(enumerate(catalog.vegetation_subtypes)),
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
            vegetation_resolution={
                "rule": (
                    "a vegetation form is written only where a vegetation-specific open-vocabulary "
                    "prompt won its independent layer; dense Vegetation alone remains unresolved"
                ),
                "tree_trunk": "an object with wood material evidence, never a woody canopy volume",
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
