"""A vision language model as the facade material backend, and the arithmetic that says whether it is worth it.

The material axis today resolves through a fixed table. Mask2Former assigns a
Mapillary Vistas entity per face, ``vistas_material_prior`` in ``semantics.json``
maps that entity to a distribution over the RF vocabulary, and
``semantic_binding.py`` takes the argmax. ``Building`` carries brick at 0.30
against plasterboard at 0.20 and concrete at 0.15, so ``Building`` resolves to
brick every time, in every city, and ``Building`` is 74 percent of bound face
observations. The fixed prior is therefore not a prior in the operational sense.
It is a constant.

This module adds a second backend rather than replacing that one. It does three
separable things and they should be judged separately.

*Layered stacks.* A facade is not a half space. Render over brick, a ventilated
cavity behind cladding and a glazing unit are all layered, and at 15 GHz the
outer layer is between a quarter and a full wavelength thick, which is exactly
where a stack neither reduces to its outer material nor to its substrate.
:func:`~semantic_twin.materials.stack.layered_power_reflectance` is a transfer
matrix over such a stack, so a model that names a stack can be answered
analytically. Nothing else in this repository can consume a stack.

*Posteriors instead of labels.* The reflectance of a patch whose material is
uncertain is not the reflectance of its most probable material. Mixing has to
happen in power, and
:func:`~semantic_twin.materials.stack.posterior_power_reflectance` and
:func:`~semantic_twin.materials.posterior.sample_face_materials` do it in the
two defensible ways: the ensemble mean, and a draw per face that keeps every
patch a single physical material and turns material ignorance into a spread on
the answer rather than a bias in it.

Both of those are electromagnetics, so neither lives in this file any more. They
sit in :mod:`semantic_twin.materials` and are imported back here, because the
question this module answers is what a wall looks like, not what it reflects.

*The model itself.* :func:`build_prompt` writes the question,
:func:`parse_response` validates the answer against the RF vocabulary, and the
calibration functions score it without ground truth, which is the only option
here because measurement has been ruled out for this study. What can be measured
without truth is whether the model agrees with itself on independent views of one
wall, and whether the confidence it states tracks that agreement. A model that is
confident and inconsistent is worse than the constant it replaced.

The transport is deliberately abstract. :class:`VlmResponse` records are read
from and written to JSON, so the same records can come from the Messages API
(:func:`anthropic_request_body` builds the call) or from any other harness that
can show an image to a vision model. Nothing downstream knows which.

``MATERIAL_VLM.md`` reports what this measured on Korenmarkt, and the verdict is
mostly negative: of the three things above, the posterior arithmetic earns its
place, the stack earns it only on glazing, and the model itself does not move
exposure enough to justify the evidence it needs. Read that before wiring any of
this into a production binding.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

# Re-exported under their old names, because every caller of this module still
# asks it for them. The redundant aliases are what marks them as re-exports.
from ..materials.posterior import sample_face_materials as sample_face_materials
from ..materials.stack import MATERIAL_VOCABULARY as MATERIAL_VOCABULARY
from ..materials.stack import Layer as Layer
from ..materials.stack import argmax_power_reflectance as argmax_power_reflectance
from ..materials.stack import half_space_power_reflectance as half_space_power_reflectance
from ..materials.stack import layer_permittivity as layer_permittivity
from ..materials.stack import layered_power_reflectance as layered_power_reflectance
from ..materials.stack import material_power_reflectance as material_power_reflectance
from ..materials.stack import posterior_power_reflectance as posterior_power_reflectance
from ..materials.stack import stack_power_reflectance as stack_power_reflectance

#: Old private name for :func:`~semantic_twin.materials.stack.layer_permittivity`.
_layer_permittivity = layer_permittivity

#: Outer finishes a facade actually wears, mapped onto the vocabulary above.
#: This is the vocabulary the model is asked to speak, because "cement render"
#: and "painted stucco" are what a facade looks like and "plasterboard" is what
#: ITU-R P.2040-4 has a row for. Keeping the two apart means the translation is
#: visible and arguable instead of buried in a prompt.
FINISH_TO_MATERIAL: dict[str, str] = {
    "fired_clay_brick": "brick",
    "painted_brick": "brick",
    "cement_render": "plasterboard",
    "lime_stucco": "plasterboard",
    "painted_render": "plasterboard",
    "exposed_concrete": "concrete",
    "precast_concrete_panel": "concrete",
    "natural_stone_ashlar": "marble",
    "natural_stone_rubble": "marble",
    "glazing": "glass",
    "glass_curtain_wall": "glass",
    "metal_cladding": "metal",
    "timber_cladding": "wood",
    "ceramic_tile": "ceramic",
    "unknown": "unknown",
}

#: Relief patterns a facade can carry, and whether the pattern is periodic. The
#: periodic ones are the ones ``MASONRY.md`` treats as a grating rather than as
#: roughness, so a model that names one is asking for the grating branch.
RELIEF_PATTERNS: tuple[str, ...] = (
    "coursed_masonry",
    "ashlar_joints",
    "rusticated",
    "panel_joints",
    "glazing_grid",
    "smooth",
    "none",
)

PERIODIC_RELIEF: frozenset[str] = frozenset(
    {"coursed_masonry", "ashlar_joints", "rusticated", "panel_joints", "glazing_grid"}
)


@dataclass(frozen=True)
class VlmResponse:
    """One model answer about one crop, already validated.

    ``posterior`` is over :data:`MATERIAL_VOCABULARY` and sums to one.
    ``stated_confidence`` is what the model said about itself and is kept
    separate from the posterior on purpose: the two are different claims and
    conflating them is how a calibration study stops being able to detect
    overconfidence.
    """

    crop_id: str
    source: str
    posterior: dict[str, float]
    stack: tuple[Layer, ...]
    relief_pattern: str
    relief_pitch_mm: float | None
    relief_depth_mm: float | None
    rms_height_mm: float | None
    stated_confidence: float
    legible: bool
    note: str = ""
    model: str = ""
    draw: int = 0

    def top_material(self) -> str:
        return max(self.posterior, key=lambda name: self.posterior[name])

    def entropy_bits(self) -> float:
        mass = np.array([self.posterior[name] for name in MATERIAL_VOCABULARY])
        mass = mass[mass > 0.0]
        return float(-(mass * np.log2(mass)).sum())

    def as_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["stack"] = [asdict(layer) for layer in self.stack]
        return record


def _normalised_posterior(raw: dict[str, Any]) -> dict[str, float]:
    unknown = [name for name in raw if name not in MATERIAL_VOCABULARY]
    if unknown:
        raise ValueError(f"posterior names outside the vocabulary: {sorted(unknown)}")
    mass = {name: float(raw.get(name, 0.0)) for name in MATERIAL_VOCABULARY}
    if any(value < 0.0 for value in mass.values()):
        raise ValueError("posterior mass must be non-negative")
    total = sum(mass.values())
    if total <= 0.0:
        raise ValueError("posterior carries no mass")
    return {name: value / total for name, value in mass.items()}


def parse_response(
    payload: dict[str, Any], *, crop_id: str, source: str, draw: int = 0, model: str = ""
) -> VlmResponse:
    """Validate one raw model answer, refusing anything the tracer cannot consume.

    Refusing is the point. A response naming a material with no ITU row, or a
    stack whose interior thickness is unstated, is dropped rather than coerced,
    because coercing it would put an invented number into a manifest that claims
    every number has a provenance.
    """
    posterior = _normalised_posterior(payload.get("material_posterior", {}))
    stack_records = payload.get("stack") or payload.get("layers") or []
    stack: list[Layer] = []
    for index, record in enumerate(stack_records):
        finish = str(record.get("material", record.get("finish", "unknown")))
        material = FINISH_TO_MATERIAL.get(finish, finish)
        thickness = record.get("thickness_mm")
        last = index == len(stack_records) - 1
        if thickness is None and not last:
            raise ValueError(f"{crop_id}: interior layer {index} has no thickness, the stack has no transfer matrix")
        stack.append(Layer(material=material, thickness_mm=None if last and thickness is None else float(thickness)))
    relief = payload.get("relief", {}) or {}
    pattern = str(relief.get("pattern", "none"))
    if pattern not in RELIEF_PATTERNS:
        raise ValueError(f"{crop_id}: relief pattern {pattern!r} is not one of {RELIEF_PATTERNS}")
    confidence = float(payload.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"{crop_id}: stated confidence {confidence} is outside [0, 1]")
    return VlmResponse(
        crop_id=crop_id,
        source=source,
        posterior=posterior,
        stack=tuple(stack),
        relief_pattern=pattern,
        relief_pitch_mm=_optional_float(relief.get("pitch_mm")),
        relief_depth_mm=_optional_float(relief.get("depth_mm")),
        rms_height_mm=_optional_float(payload.get("rms_height_mm")),
        stated_confidence=confidence,
        legible=bool(payload.get("legible", True)),
        note=str(payload.get("note", ""))[:400],
        model=model,
        draw=int(draw),
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    return number if number > 0.0 else None


PROMPT_VERSION = "facade-stack-v1"

PROMPT = """You are looking at one rectangular patch of a building facade in a European city
square. Report what the surface is made of, as a radio engineer would need it.

Answer with a single JSON object and nothing else:

{{
  "stack": [
    {{"material": "<finish>", "thickness_mm": <number>}},
    {{"material": "<finish>", "thickness_mm": null}}
  ],
  "relief": {{"pattern": "<pattern>", "pitch_mm": <number or null>, "depth_mm": <number or null>}},
  "rms_height_mm": <number or null>,
  "material_posterior": {{"<rf material>": <probability>, ...}},
  "confidence": <0 to 1>,
  "legible": <true or false>,
  "note": "<one short sentence, what you actually saw>"
}}

Rules.

"stack" is outermost layer first. The last entry is the substrate and takes
thickness_mm null. Give a thickness in millimetres for every layer above it. If
you cannot tell there is a coating, return a single substrate layer rather than
inventing one. Allowed finishes: {finishes}.

"relief" is the repeating surface structure you can see, not the microscopic
finish. Allowed patterns: {patterns}. "pitch_mm" is the vertical spacing between
repeats, so for brickwork it is one course, brick plus joint, typically 60 to 80
mm in Belgium. "depth_mm" is how far the recess sits behind the face.

"rms_height_mm" is the root mean square height of the finish between the
repeating features, so a smooth painted render is well under a tenth of a
millimetre and a rough stone face is millimetres. Return null rather than
guessing if the image does not resolve it.

"material_posterior" is a probability distribution over exactly these RF
materials: {materials}. It must sum to 1. This is the important field. Spread it
honestly: if the image is low resolution, shadowed, or oblique, a broad
posterior is the correct answer and a sharp one is a mistake. Put mass on
"unknown" if the patch is largely obscured by vegetation, scaffolding, signage
or people.

"confidence" is how much you would bet on your own top material. State it
independently of the posterior.

"legible" is false if the crop is too dark, too blurred, or too obstructed to
read the facade at all. Say so rather than guessing.
"""


def build_prompt() -> str:
    """The question, with the vocabularies interpolated so they cannot drift."""
    return PROMPT.format(
        finishes=", ".join(sorted(FINISH_TO_MATERIAL)),
        patterns=", ".join(RELIEF_PATTERNS),
        materials=", ".join(MATERIAL_VOCABULARY),
    )


def prompt_digest() -> str:
    """Short digest of the exact question asked, recorded beside every answer."""
    return hashlib.sha256(build_prompt().encode()).hexdigest()[:16]


def anthropic_request_body(
    image_png: bytes,
    *,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 1024,
    temperature: float = 1.0,
) -> dict[str, Any]:
    """The Messages API body for one crop, so the harness is a detail.

    Temperature defaults to 1 rather than 0 because the calibration study needs
    independent draws from the model's own distribution. A deterministic decode
    would report a repeat spread of zero and say nothing about whether the model
    is confident for a reason.
    """
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64.b64encode(image_png).decode(),
                        },
                    },
                    {"type": "text", "text": build_prompt()},
                ],
            }
        ],
    }


def png_bytes(image: np.ndarray) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(np.asarray(image, dtype=np.uint8), "RGB").save(buffer, format="PNG")
    return buffer.getvalue()


# The layered stack transfer matrix and the posterior power mixture used to
# live here. They are electromagnetics rather than image processing, so they
# moved to semantic_twin.materials.stack and semantic_twin.materials.posterior
# and are imported at the top of this module. This module keeps the names.


# --------------------------------------------------------------------------
# Calibration without ground truth
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AgreementReport:
    """Self consistency of a model across independent looks at one wall.

    There is no measured ground truth for these facades and there will not be,
    so this is the substitute and its limits should be stated wherever it is
    quoted. Agreement is necessary for correctness and not sufficient for it: a
    model that is wrong the same way twice scores perfectly here. What it does
    catch, and what a single pass cannot, is a model that is sharp and unstable,
    which is the failure mode that would do real damage downstream.
    """

    pairs: int
    top1_agreement: float
    mean_total_variation: float
    mean_stated_confidence: float
    per_group: dict[str, dict[str, float]] = field(default_factory=dict)


def total_variation(first: dict[str, float], second: dict[str, float]) -> float:
    return 0.5 * float(sum(abs(first.get(name, 0.0) - second.get(name, 0.0)) for name in MATERIAL_VOCABULARY))


def agreement(responses: list[VlmResponse], group_of: dict[str, str]) -> AgreementReport:
    """Score every within-group pair of responses.

    ``group_of`` maps a crop id to the physical wall it looks at, so pairs are
    two looks at one wall and never two different walls. Both the repeat draw
    case, where the crop is identical, and the cross view case, where the crop is
    not, are handled by choosing what a group means.
    """
    grouped: dict[str, list[VlmResponse]] = {}
    for response in responses:
        grouped.setdefault(group_of.get(response.crop_id, response.crop_id), []).append(response)
    top1: list[float] = []
    distance: list[float] = []
    per_group: dict[str, dict[str, float]] = {}
    for name, members in grouped.items():
        if len(members) < 2:
            continue
        local_top1: list[float] = []
        local_distance: list[float] = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                local_top1.append(float(members[i].top_material() == members[j].top_material()))
                local_distance.append(total_variation(members[i].posterior, members[j].posterior))
        top1.extend(local_top1)
        distance.extend(local_distance)
        per_group[name] = {
            "responses": float(len(members)),
            "top1_agreement": float(np.mean(local_top1)),
            "mean_total_variation": float(np.mean(local_distance)),
        }
    return AgreementReport(
        pairs=len(top1),
        top1_agreement=float(np.mean(top1)) if top1 else float("nan"),
        mean_total_variation=float(np.mean(distance)) if distance else float("nan"),
        mean_stated_confidence=float(np.mean([r.stated_confidence for r in responses])) if responses else float("nan"),
        per_group=per_group,
    )


def reliability(responses: list[VlmResponse], group_of: dict[str, str], *, bins: int = 4) -> list[dict[str, float]]:
    """Stated confidence against realised cross-look agreement, binned.

    This is the calibration curve that can be drawn without truth. Each response
    contributes its stated confidence and the fraction of its within-group
    partners that picked the same top material. A calibrated model puts those on
    the diagonal. A model above the diagonal is overconfident, which is the case
    that matters, because a confident wrong material is worse than the broad
    prior it replaced.
    """
    grouped: dict[str, list[VlmResponse]] = {}
    for response in responses:
        grouped.setdefault(group_of.get(response.crop_id, response.crop_id), []).append(response)
    points: list[tuple[float, float]] = []
    for members in grouped.values():
        if len(members) < 2:
            continue
        for index, response in enumerate(members):
            others = [m for k, m in enumerate(members) if k != index]
            hit = np.mean([float(response.top_material() == other.top_material()) for other in others])
            points.append((response.stated_confidence, float(hit)))
    if not points:
        return []
    confidence = np.array([p[0] for p in points])
    realised = np.array([p[1] for p in points])
    edges = np.linspace(0.0, 1.0, bins + 1)
    out: list[dict[str, float]] = []
    for low, high in zip(edges[:-1], edges[1:], strict=True):
        inside = (confidence >= low) & (confidence < high if high < 1.0 else confidence <= 1.0)
        if not inside.any():
            continue
        out.append(
            {
                "confidence_low": float(low),
                "confidence_high": float(high),
                "count": int(inside.sum()),
                "mean_stated_confidence": float(confidence[inside].mean()),
                "mean_realised_agreement": float(realised[inside].mean()),
                "gap": float(confidence[inside].mean() - realised[inside].mean()),
            }
        )
    return out


def expected_calibration_gap(curve: list[dict[str, float]]) -> float:
    """Count weighted mean absolute gap of a reliability curve."""
    if not curve:
        return float("nan")
    weight = np.array([row["count"] for row in curve], dtype=np.float64)
    gap = np.array([abs(row["gap"]) for row in curve], dtype=np.float64)
    return float((weight * gap).sum() / weight.sum())


def pooled_posterior(responses: list[VlmResponse], weights: np.ndarray | None = None) -> dict[str, float]:
    """Area or count weighted mean posterior over a set of responses.

    This is the site level composition, and it is the quantity with the leverage.
    A per face posterior only reaches the few percent of surface a camera sees,
    while a site level composition replaces the constant that the orientation
    rule applies to every facade in the crop.
    """
    if not responses:
        raise ValueError("no responses to pool")
    if weights is None:
        weights = np.ones(len(responses))
    weights = np.asarray(weights, dtype=np.float64)
    if weights.shape != (len(responses),):
        raise ValueError("weights must have one entry per response")
    if weights.sum() <= 0.0:
        raise ValueError("weights carry no mass")
    stacked = np.array([[r.posterior[name] for name in MATERIAL_VOCABULARY] for r in responses])
    pooled = (stacked * weights[:, None]).sum(axis=0) / weights.sum()
    return dict(zip(MATERIAL_VOCABULARY, (pooled / pooled.sum()).tolist(), strict=True))


def load_responses(path: str | pathlib.Path) -> list[VlmResponse]:
    """Read a JSONL transcript of validated responses."""
    out: list[VlmResponse] = []
    for line in pathlib.Path(path).read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out.append(
            parse_response(
                record["payload"],
                crop_id=record["crop_id"],
                source=record["source"],
                draw=int(record.get("draw", 0)),
                model=str(record.get("model", "")),
            )
        )
    return out


def save_responses(path: str | pathlib.Path, records: list[dict[str, Any]]) -> None:
    lines = [json.dumps(record, sort_keys=True) for record in records]
    pathlib.Path(path).write_text("\n".join(lines) + "\n")
