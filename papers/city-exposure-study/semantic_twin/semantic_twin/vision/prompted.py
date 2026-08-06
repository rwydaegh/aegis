"""SAM 3 open-vocabulary concept segmentation as a first-class backend.

This is the material-resolving half of the segmentation stack. The dense
Mapillary Vistas backend in :mod:`semantic_twin.vision.dense` has one ``Building``
class, which is useless for RF: brick, render, ashlar stone, glass curtain wall
and metal cladding all land in it and their permittivity, conductivity and
roughness are not close. SAM 3 is prompted with the catalogue in
``config/semantic_concepts.json`` and returns per-instance masks for concepts
that name a material, so the material axis can be resolved inside a single
Vistas class.

Two things make this affordable at city scale.

*Text embeddings are cached.* The prompt catalogue is fixed, so encoding it once
and reusing it across every view and every panorama removes 11 ms per prompt per
view, which was 18 percent of the whole pass.

*Prompts are grounded in one batch.* ``Sam3Processor.set_text_prompt`` runs the
fusion encoder, the decoder and the mask head once per prompt. The same model
call accepts a batch of prompts against one image by pointing every entry of
``FindStage.img_ids`` at the same image, which measured 17.8 ms per prompt
against 61.8 ms serial on an RTX A6000. The decoder is 82 percent of the
remaining cost and scales linearly in prompt count, so the prompt catalogue size
is a direct time budget and :func:`semantic_twin.vision.vocabulary.gate_prompts` is what
keeps it down.

Note on resolution: ``Sam3Processor`` resizes every input to 1008 x 1008. Unlike
the Mapillary Vistas processor's 384, that is the resolution the model was
trained at, not a config accident, so it is recorded rather than overridden.

    python -m semantic_twin.cli.prompted \
      --views data/panoramas/korenmarkt/semantics/views \
      --concepts config/semantic_concepts.json \
      --out data/panoramas/korenmarkt/sam3
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import pathlib
import re
import subprocess
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image

from .vocabulary import ConceptCatalog

MODEL = "facebook/sam3"
CHECKPOINT_FILENAME = "sam3.pt"
DEFAULT_RESOLUTION = 1008
DEFAULT_THRESHOLD = 0.35
DEFAULT_PROMPT_BATCH = 32
PRODUCTION_CONCEPT_ID_COUNT = 61
# Reviewed, immutable SAM 3 weights and source used by this study. Production
# evidence accepts only this pair. Development runs may use another revision,
# but their provenance records that it is outside the reviewed production pair.
PRODUCTION_REVISION = "3c879f39826c281e95690f02c7821c4de09afae7"
PRODUCTION_REPOSITORY_COMMIT = "96914d2425f90a64f45ca977c2b5165418099543"
# SHA-256 of the parsed, canonically serialized semantic catalogue reviewed for
# this study. JSON whitespace and object-key order do not affect this identity.
PRODUCTION_CATALOGUE_SEMANTIC_SHA256 = "66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b"


@dataclass(frozen=True)
class ConceptPrediction:
    """View-local open-vocabulary instances, ready for spherical fusion."""

    masks: np.ndarray
    labels: np.ndarray
    kinds: np.ndarray
    scores: np.ndarray
    height: int
    width: int
    elapsed_s: float = 0.0
    asked_prompts: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        counts = {len(self.labels), len(self.kinds), len(self.scores), len(self.masks)}
        if len(counts) != 1:
            raise ValueError("masks, labels, kinds and scores must have the same length")

    def packed(self) -> np.ndarray:
        if not len(self.masks):
            return np.empty((0, 0), dtype=np.uint8)
        return np.packbits(self.masks.reshape(len(self.masks), -1).astype(np.uint8), axis=1)


def cache_key(
    *,
    model: str,
    resolution: int,
    threshold: float,
    view_size: int,
    catalog: ConceptCatalog,
    model_revision: str | None = None,
) -> str:
    """Identity of everything that changes the prediction, as one short digest.

    A cached view must never be reused across a different checkpoint, inference
    resolution, detection threshold, crop size or prompt vocabulary. Note what is
    deliberately *not* here: the entity, material and attribute distributions.
    They never reach the model, they are read fresh from the catalogue at fusion
    time, and hashing them would throw away a city of segmentation every time a
    prior was retuned. What the key cannot capture is which prompts a view was
    actually asked, because the gate decides that from the dense pass. The
    caller checks that separately against the stored ``asked_prompts``.
    """
    payload = json.dumps(
        {
            "model": model,
            "model_revision": model_revision,
            "resolution": int(resolution),
            "threshold": round(float(threshold), 6),
            "view_size": int(view_size),
            "prompts": sorted(catalog.prompts),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _is_commit(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[0-9a-fA-F]{40}", value.strip()))


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semantic_catalogue_identity(path: pathlib.Path, *, production: bool) -> dict[str, Any]:
    """Return the semantic catalogue identity and enforce the production pin.

    The byte digest remains useful for reproducing the exact file. Production
    acceptance uses a canonical digest of the parsed JSON, so harmless
    whitespace or object-key ordering changes do not invalidate the reviewed
    semantics.
    """
    document = json.loads(path.read_text())
    canonical = json.dumps(
        document,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    semantic_sha256 = hashlib.sha256(canonical).hexdigest()
    matches_reviewed = semantic_sha256 == PRODUCTION_CATALOGUE_SEMANTIC_SHA256
    identity = {
        "catalogue_sha256": _sha256_file(path),
        "catalogue_semantic_sha256": semantic_sha256,
        "matches_reviewed_production_catalogue": matches_reviewed,
        "required_production_catalogue_semantic_sha256": PRODUCTION_CATALOGUE_SEMANTIC_SHA256,
        "production_mode": production,
    }
    if production and not matches_reviewed:
        raise ValueError(
            "production SAM 3 inference requires the reviewed semantic catalogue "
            f"{PRODUCTION_CATALOGUE_SEMANTIC_SHA256}; received {semantic_sha256}"
        )
    return identity


def _snapshot_commit(path: pathlib.Path) -> str | None:
    """Read the resolved Hub commit from a standard Hugging Face cache path."""
    parts = path.absolute().parts
    try:
        index = parts.index("snapshots")
    except ValueError:
        return None
    candidate = parts[index + 1] if index + 1 < len(parts) else None
    return candidate.lower() if _is_commit(candidate) else None


def resolve_sam3_snapshot(
    revision: str | None,
    *,
    production: bool,
    downloader: Any | None = None,
) -> tuple[pathlib.Path | None, dict[str, Any]]:
    """Download and verify one immutable Hugging Face SAM 3 snapshot.

    A branch or tag is never treated as a pin. Development runs may keep the
    old mutable loader, but their manifest says that exact weights are
    unresolved. Production runs require the reviewed Hub commit.
    """
    requested = revision.strip() if revision is not None else None
    if production and (requested is None or requested.lower() != PRODUCTION_REVISION):
        raise ValueError(
            "production SAM 3 inference requires --sam-revision with the reviewed "
            f"40-character Hub commit {PRODUCTION_REVISION}; received {requested!r}"
        )
    if not _is_commit(requested):
        record = {
            "status": "unresolved",
            "repository": MODEL,
            "requested_revision": requested,
            "resolved_revision": None,
            "checkpoint_filename": CHECKPOINT_FILENAME,
            "checkpoint_sha256": None,
            "matches_reviewed_production_snapshot": False,
            "required_production_revision": PRODUCTION_REVISION,
            "production_mode": production,
            "note": "No immutable 40-character Hugging Face commit was supplied.",
        }
        return None, record

    if downloader is None:
        from huggingface_hub import hf_hub_download

        downloader = hf_hub_download
    checkpoint = pathlib.Path(downloader(repo_id=MODEL, filename=CHECKPOINT_FILENAME, revision=requested))
    config = pathlib.Path(downloader(repo_id=MODEL, filename="config.json", revision=requested))
    checkpoint_commit = _snapshot_commit(checkpoint)
    config_commit = _snapshot_commit(config)
    expected = requested.lower()
    if checkpoint_commit != expected or config_commit != expected:
        raise RuntimeError(
            "Hugging Face returned files outside the requested SAM 3 snapshot: "
            f"checkpoint={checkpoint_commit}, config={config_commit}, requested={expected}"
        )
    return checkpoint, {
        "status": "resolved",
        "repository": MODEL,
        "requested_revision": requested,
        "resolved_revision": expected,
        "checkpoint_filename": CHECKPOINT_FILENAME,
        "checkpoint_sha256": _sha256_file(checkpoint),
        "config_sha256": _sha256_file(config),
        "matches_reviewed_production_snapshot": expected == PRODUCTION_REVISION,
        "required_production_revision": PRODUCTION_REVISION,
        "production_mode": production,
    }


def _installed_repository_commit(module_file: pathlib.Path) -> str | None:
    """Find the commit of the installed SAM 3 source tree when it is available."""
    # The package directory and its direct parent cover an editable source
    # checkout. Walking higher can reach an unrelated project repository when
    # SAM 3 was copied into that project's virtual environment.
    for folder in (module_file.parent, module_file.parent.parent):
        if not (folder / ".git").exists():
            continue
        result = subprocess.run(
            ["git", "-C", str(folder), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        value = result.stdout.strip().lower()
        if result.returncode == 0 and _is_commit(value):
            return value
    try:
        direct_url = importlib.metadata.distribution("sam3").read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    if direct_url:
        commit = json.loads(direct_url).get("vcs_info", {}).get("commit_id")
        if _is_commit(commit):
            return str(commit).lower()
    return None


def verify_sam3_repository(
    expected_commit: str | None,
    actual_commit: str | None,
    *,
    production: bool,
) -> dict[str, Any]:
    """Verify and describe the source commit used by the installed SAM 3 code."""
    expected = expected_commit.strip().lower() if expected_commit is not None else None
    actual = actual_commit.strip().lower() if actual_commit is not None else None
    if production and expected != PRODUCTION_REPOSITORY_COMMIT:
        raise ValueError(
            "production SAM 3 inference requires --sam-repository-commit with the reviewed "
            f"source commit {PRODUCTION_REPOSITORY_COMMIT}; received {expected!r}"
        )
    if production and actual != PRODUCTION_REPOSITORY_COMMIT:
        raise RuntimeError(
            "production SAM 3 inference requires the installed source at reviewed commit "
            f"{PRODUCTION_REPOSITORY_COMMIT}; resolved {actual!r}"
        )
    if expected is not None and not _is_commit(expected):
        return {
            "status": "unresolved",
            "expected_commit": expected_commit,
            "resolved_commit": actual if _is_commit(actual) else None,
            "matches_reviewed_production_source": actual == PRODUCTION_REPOSITORY_COMMIT,
            "required_production_commit": PRODUCTION_REPOSITORY_COMMIT,
            "production_mode": production,
            "note": "The requested SAM 3 repository revision is mutable or malformed.",
        }
    if expected is not None and actual != expected:
        raise RuntimeError(f"installed SAM 3 repository commit {actual!r} does not match requested {expected!r}")
    if actual is None or not _is_commit(actual):
        if production:
            raise RuntimeError("production SAM 3 inference could not resolve the installed repository commit")
        return {
            "status": "unresolved",
            "expected_commit": expected,
            "resolved_commit": None,
            "matches_reviewed_production_source": False,
            "required_production_commit": PRODUCTION_REPOSITORY_COMMIT,
            "production_mode": production,
            "note": "The installed SAM 3 package has no verifiable Git commit metadata.",
        }
    return {
        "status": "resolved",
        "expected_commit": expected,
        "resolved_commit": actual,
        "matches_reviewed_production_source": actual == PRODUCTION_REPOSITORY_COMMIT,
        "required_production_commit": PRODUCTION_REPOSITORY_COMMIT,
        "production_mode": production,
    }


def save_prediction(path: pathlib.Path, prediction: ConceptPrediction, *, key: str) -> None:
    np.savez_compressed(
        path,
        packed_masks=prediction.packed(),
        mask_shape=np.asarray([prediction.height, prediction.width]),
        scores=prediction.scores.astype(np.float32),
        labels=prediction.labels.astype(str),
        kinds=prediction.kinds.astype(str),
        asked_prompts=np.asarray(prediction.asked_prompts, dtype=str),
        cache_key=np.asarray(key),
    )


def load_prediction(path: pathlib.Path, *, key: str) -> ConceptPrediction | None:
    """Read a cached view, refusing anything produced under different settings."""
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as stored:
        if "cache_key" not in stored or str(stored["cache_key"]) != key:
            return None
        height, width = (int(value) for value in stored["mask_shape"])
        labels = stored["labels"].astype(str)
        if len(labels):
            masks = (
                np.unpackbits(stored["packed_masks"], axis=1, count=height * width)
                .reshape(len(labels), height, width)
                .astype(bool)
            )
        else:
            masks = np.zeros((0, height, width), dtype=bool)
        asked = tuple(stored["asked_prompts"].astype(str)) if "asked_prompts" in stored else ()
        return ConceptPrediction(
            masks=masks,
            labels=labels,
            kinds=stored["kinds"].astype(str),
            scores=stored["scores"].astype(np.float32),
            height=height,
            width=width,
            asked_prompts=asked,
        )


def _numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().float().cpu().numpy()
    return np.asarray(value)


def select_instances(
    probability: np.ndarray,
    prompts: tuple[str, ...],
    kind_by_prompt: dict[str, str],
    *,
    threshold: float,
) -> tuple[np.ndarray, list[str], list[str], list[float]]:
    """Pick the surviving (prompt, query) pairs and name them, in mask order.

    ``probability`` is (prompt, query) from one batched grounding call. The
    returned boolean selects rows of the mask tensor, and the labels are read
    back from the same boolean in the same row-major order, which is the only
    thing keeping a mask attached to the prompt that produced it. Getting that
    alignment wrong mislabels every surface in the scene without raising
    anything, so it lives here rather than inline in the model call and is
    tested on its own.
    """
    if probability.ndim != 2:
        raise ValueError("probability must be a (prompt, query) array")
    if probability.shape[0] != len(prompts):
        raise ValueError(f"grounding returned {probability.shape[0]} prompt rows for {len(prompts)} prompts")
    keep = probability > threshold
    prompt_index, _query_index = np.nonzero(keep)
    labels = [prompts[index] for index in prompt_index]
    kinds = [kind_by_prompt[label] for label in labels]
    return keep, labels, kinds, probability[keep].tolist()


class Sam3ConceptBackend:
    """Prompted concept segmentation with a cached text encoder and batched grounding."""

    def __init__(
        self,
        catalog: ConceptCatalog,
        *,
        device: str = "cuda",
        resolution: int = DEFAULT_RESOLUTION,
        threshold: float = DEFAULT_THRESHOLD,
        prompt_batch: int = DEFAULT_PROMPT_BATCH,
        revision: str | None = None,
        repository_commit: str | None = None,
        production: bool = False,
    ) -> None:
        try:
            import torch
            from sam3.model.data_misc import FindStage
            from sam3.model.sam3_image_processor import Sam3Processor
            from sam3.model_builder import build_sam3_image_model
        except ImportError as exc:
            raise SystemExit(
                "SAM 3 is not installed. Follow https://github.com/facebookresearch/sam3 "
                "in a CUDA 12.6+ environment and authenticate with Hugging Face."
            ) from exc
        if not torch.cuda.is_available():
            raise SystemExit("SAM 3 needs a CUDA GPU and no CUDA device is visible")
        if prompt_batch < 1:
            raise ValueError("prompt_batch must be at least one")

        checkpoint_path, snapshot = resolve_sam3_snapshot(revision, production=production)
        source_commit = _installed_repository_commit(pathlib.Path(__import__("sam3").__file__))
        repository = verify_sam3_repository(repository_commit, source_commit, production=production)

        self.torch = torch
        self._find_stage = FindStage
        self.catalog = catalog
        self.device = device
        self.resolution = int(resolution)
        self.threshold = float(threshold)
        self.prompt_batch = int(prompt_batch)
        self.snapshot = snapshot
        self.repository = repository
        self.kind_by_prompt = {concept.prompt: concept.kind for concept in catalog.concepts}
        with self._context():
            if checkpoint_path is None:
                self.model = build_sam3_image_model()
            else:
                self.model = build_sam3_image_model(checkpoint_path=str(checkpoint_path), load_from_HF=False)
        self.processor = Sam3Processor(self.model, resolution=self.resolution, confidence_threshold=self.threshold)
        # Read back rather than echoed from the module constant, so the manifest
        # records what this install of SAM 3 would have used unprompted.
        self.processor_default_resolution = int(Sam3Processor(self.model).resolution)
        self._prompt_index = {concept.prompt: index for index, concept in enumerate(catalog.concepts)}
        self._text_features = self._encode_catalogue()

    def _context(self):
        if self.torch.cuda.is_available():
            return self.torch.autocast("cuda", dtype=self.torch.bfloat16)
        return nullcontext()

    def _encode_catalogue(self) -> dict[str, Any]:
        """Encode every prompt once, at construction, and never again.

        The text encoder was 11 ms per prompt per view, 18 percent of the pass,
        for a catalogue that never changes. Encoding the whole thing costs 22 ms
        once. Gated subsets are taken by indexing this result rather than by
        re-encoding, which keeps exactly one cache entry no matter how many
        distinct gate outcomes a city walk produces.
        """
        with self._context(), self.torch.inference_mode():
            encoded = self.model.backbone.forward_text(list(self.catalog.prompts), device=self.device)
        # language_features and language_embeds come back as (sequence, batch,
        # channels) and language_mask as (batch, sequence), so a prompt subset is
        # a gather on axis 1, 1 and 0 respectively. Nothing upstream guarantees
        # that layout. If it ever changes, the gathers would silently select
        # token positions instead of prompts and every mask would carry the wrong
        # label, so the layout is asserted here rather than trusted.
        count = len(self.catalog.concepts)
        layout = {
            name: tuple(encoded[name].shape) for name in ("language_features", "language_embeds", "language_mask")
        }
        if (
            layout["language_features"][1] != count
            or layout["language_embeds"][1] != count
            or layout["language_mask"][0] != count
        ):
            raise RuntimeError(f"unexpected SAM 3 text feature layout for {count} prompts: {layout}")
        return encoded

    def _text_for(self, prompts: tuple[str, ...]) -> dict[str, Any]:
        index = self.torch.as_tensor([self._prompt_index[prompt] for prompt in prompts], device=self.device)
        return {
            "language_features": self._text_features["language_features"].index_select(1, index),
            "language_embeds": self._text_features["language_embeds"].index_select(1, index),
            "language_mask": self._text_features["language_mask"].index_select(0, index),
        }

    def _ground(self, state: dict[str, Any], prompts: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
        count = len(prompts)
        state["backbone_out"].update(self._text_for(prompts))
        find = self._find_stage(
            img_ids=self.torch.zeros(count, device=self.device, dtype=self.torch.long),
            text_ids=self.torch.arange(count, device=self.device, dtype=self.torch.long),
            input_boxes=None,
            input_boxes_mask=None,
            input_boxes_label=None,
            input_points=None,
            input_points_mask=None,
        )
        # ``Sam3Processor`` only ever builds a one-prompt dummy, so the batched
        # path has to reach for the sized constructor directly. Without it the
        # geometry encoder grid-samples a batch-1 grid against batch-N features
        # and raises.
        outputs = self.model.forward_grounding(
            backbone_out=state["backbone_out"],
            find_input=find,
            geometric_prompt=self.model._get_dummy_prompt(num_prompts=count),
            find_target=None,
        )
        presence = outputs["presence_logit_dec"].sigmoid().unsqueeze(1)
        probability = (outputs["pred_logits"].sigmoid() * presence).squeeze(-1)
        return probability, outputs["pred_masks"]

    def predict(self, image: Image.Image, prompts: tuple[str, ...] | None = None) -> ConceptPrediction:
        """Segment one rectilinear view against a prompt subset."""
        import torch.nn.functional as functional

        asked = tuple(prompts) if prompts is not None else self.catalog.prompts
        unknown = set(asked) - set(self.kind_by_prompt)
        if unknown:
            raise ValueError(f"prompts outside the catalogue: {sorted(unknown)}")
        width, height = image.size
        masks: list[np.ndarray] = []
        labels: list[str] = []
        kinds: list[str] = []
        scores: list[float] = []
        started = time.perf_counter()
        with self._context(), self.torch.inference_mode():
            state = self.processor.set_image(image)
            backbone_out = state["backbone_out"]
            for start in range(0, len(asked), self.prompt_batch):
                group = asked[start : start + self.prompt_batch]
                # A fresh shallow copy per chunk, so this chunk's language keys
                # and anything ``forward_grounding`` inserts cannot be seen by
                # the next one. Chunking was checked against the fully serial
                # path on a real Korenmarkt view: identical instance counts and
                # a worst per-concept union-mask IoU of 0.9965.
                state["backbone_out"] = dict(backbone_out)
                probability, mask_logits = self._ground(state, group)
                keep, chunk_labels, chunk_kinds, chunk_scores = select_instances(
                    probability.float().cpu().numpy(),
                    group,
                    self.kind_by_prompt,
                    threshold=self.threshold,
                )
                if not chunk_labels:
                    continue
                # Only the survivors are upsampled. The full query tensor at crop
                # resolution would be tens of gigabytes.
                selected = mask_logits[self.torch.as_tensor(keep, device=mask_logits.device)]
                interpolated = functional.interpolate(
                    selected.unsqueeze(1).float(),
                    size=(height, width),
                    mode="bilinear",
                    align_corners=False,
                )
                # A logit above zero is exactly a sigmoid above one half, and
                # interpolating before the threshold keeps the values linear.
                masks.append((interpolated.squeeze(1) > 0.0).cpu().numpy())
                labels.extend(chunk_labels)
                kinds.extend(chunk_kinds)
                scores.extend(chunk_scores)
        stacked = np.concatenate(masks, axis=0) if masks else np.zeros((0, height, width), dtype=bool)
        return ConceptPrediction(
            masks=stacked,
            labels=np.asarray(labels, dtype=str),
            kinds=np.asarray(kinds, dtype=str),
            scores=np.asarray(scores, dtype=np.float32),
            height=height,
            width=width,
            elapsed_s=time.perf_counter() - started,
            asked_prompts=asked,
        )

    def manifest(self) -> dict[str, Any]:
        return {
            "model": MODEL,
            "revision": self.snapshot["resolved_revision"],
            "checkpoint_sha256": self.snapshot["checkpoint_sha256"],
            "repository_commit": self.repository["resolved_commit"],
            "huggingface_snapshot": self.snapshot,
            "sam3_repository": self.repository,
            "model_role": "open-vocabulary promptable concept segmentation for independent panorama views",
            "sam3_1_note": (
                "SAM 3.1 Object Multiplex is a video tracker and is not applied to discontinuous perspective views."
            ),
            "resolution": self.resolution,
            "resolution_status": (
                "Sam3Processor resizes every input to a fixed square. Unlike the Mapillary Vistas "
                "processor's 384, 1008 is the resolution SAM 3 was trained at, so raising it takes "
                "the ViT off its trained scale rather than recovering detail. Angular detail is "
                "bought with narrower crops, not larger ones."
            ),
            "processor_default_resolution": self.processor_default_resolution,
            "threshold": self.threshold,
            "prompt_batch": self.prompt_batch,
        }


@dataclass(frozen=True)
class PromptedRunConfig:
    """Inputs for prompted concept segmentation over prepared views."""

    views: pathlib.Path
    concepts: pathlib.Path
    out: pathlib.Path
    threshold: float
    resolution: int
    prompt_batch: int
    limit_views: int | None
    force: bool
    sam_revision: str | None = None
    sam_repository_commit: str | None = None
    production: bool = False


def run_prompted(config: PromptedRunConfig) -> None:
    catalogue_identity = semantic_catalogue_identity(config.concepts, production=config.production)
    catalog = ConceptCatalog.load(config.concepts)
    if config.production and len(catalog.id2label()) != PRODUCTION_CONCEPT_ID_COUNT:
        raise ValueError(
            f"production SAM 3 inference requires the fixed {PRODUCTION_CONCEPT_ID_COUNT}-ID concept vocabulary"
        )
    config.out.mkdir(parents=True, exist_ok=True)
    image_paths = [path for path in sorted(config.views.glob("*.jpg")) if not path.stem.endswith("_key")]
    if config.limit_views is not None:
        if config.limit_views < 1:
            raise SystemExit("--limit-views must be positive")
        image_paths = image_paths[: config.limit_views]
    if not image_paths:
        raise SystemExit(f"no views found under {config.views}")

    with Image.open(image_paths[0]) as probe:
        view_size = probe.size[0]
    key = cache_key(
        model=MODEL,
        resolution=config.resolution,
        threshold=config.threshold,
        view_size=view_size,
        catalog=catalog,
        model_revision=config.sam_revision if _is_commit(config.sam_revision) else None,
    )
    backend = Sam3ConceptBackend(
        catalog,
        resolution=config.resolution,
        threshold=config.threshold,
        prompt_batch=config.prompt_batch,
        revision=config.sam_revision,
        repository_commit=config.sam_repository_commit,
        production=config.production,
    )
    elapsed = 0.0
    for image_path in image_paths:
        destination = config.out / f"{image_path.stem}.npz"
        if not config.force and load_prediction(destination, key=key) is not None:
            print(f"[sam3] {image_path.name}: cached")
            continue
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        prediction = backend.predict(image)
        elapsed += prediction.elapsed_s
        save_prediction(destination, prediction, key=key)
        print(f"[sam3] {image_path.name}: {len(prediction.labels)} instances in {prediction.elapsed_s:.2f} s")

    manifest = {
        **backend.manifest(),
        "cache_key": key,
        "view_size": view_size,
        "taxonomy": catalog.taxonomy,
        "concepts": list(catalog.prompts),
        "views": len(image_paths),
        "inference_seconds": round(elapsed, 3),
        "concept_id_count": len(catalog.id2label()),
        "concept_catalogue_sha256": catalogue_identity["catalogue_sha256"],
        "concept_catalogue_identity": catalogue_identity,
    }
    (config.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
