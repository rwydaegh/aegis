"""Score the vision model against the fixed prior it would replace.

Three questions, in the order they decide whether any of this is worth wiring in.

Does the model see anything the fixed prior does not, which is a question about
composition. Is it consistent enough to be trusted, which is a question about
calibration and has to be answered without ground truth. And does the difference
survive contact with the tracer, which is a question in decibels and is answered
by ``run_exposure.py`` with the binding this script writes.

    python3 analyse_material_vlm.py --out outputs/material_vlm
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

import numpy as np

from semantic_twin.facade_vlm import (
    MATERIAL_VOCABULARY,
    PERIODIC_RELIEF,
    VlmResponse,
    agreement,
    argmax_power_reflectance,
    expected_calibration_gap,
    material_power_reflectance,
    parse_response,
    pooled_posterior,
    posterior_power_reflectance,
    prompt_digest,
    reliability,
    total_variation,
)
from semantic_twin.materials import MaterialLibrary

ROOT = pathlib.Path(__file__).resolve().parent
CONFIG = ROOT / "config"

#: ``vistas_material_prior['Building']`` from
#: ``data/panoramas/korenmarkt/semantics/semantics.json``. Read from the file
#: rather than restated, but recorded here so the comparison is legible.
BUILDING_PRIOR_SOURCE = ROOT / "data" / "panoramas" / "korenmarkt" / "semantics" / "semantics.json"


def _decode(line: str) -> tuple[dict[str, Any], bool]:
    """Decode one transcript line, closing an unbalanced trailing brace.

    Several calls emitted the payload object correctly and dropped the closing
    brace of the wrapper around it. The repair is only ever appending closing
    braces, never editing content, and the count of repaired lines is reported so
    that a transport that starts truncating answers rather than wrappers is
    visible instead of silently absorbed.
    """
    try:
        return json.loads(line), False
    except json.JSONDecodeError:
        pass
    deficit = line.count("{") - line.count("}")
    if deficit <= 0:
        raise
    return json.loads(line.rstrip() + "}" * deficit), True


def load_all(out: pathlib.Path) -> tuple[list[VlmResponse], dict[str, Any], dict[str, Any]]:
    key = json.loads((out / "blind_key.json").read_text())["map"]
    crops = {record["crop_id"]: record for record in json.loads((out / "crops.json").read_text())["crops"]}
    responses: list[VlmResponse] = []
    rejected: list[dict[str, str]] = []
    repaired = 0
    for path in sorted((out / "raw").glob("*.jsonl")):
        draw = int(path.stem.split("_")[0].removeprefix("draw"))
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record, fixed_line = _decode(line)
            repaired += int(fixed_line)
            entry = key[record["crop_blind"]]
            try:
                responses.append(
                    parse_response(
                        record["payload"],
                        crop_id=entry["crop_id"],
                        source=entry["source"],
                        draw=draw,
                        model="claude-opus",
                    )
                )
            except ValueError as error:
                rejected.append({"blind": record["crop_blind"], "reason": str(error)})
    return responses, crops, {"rejected": rejected, "repaired_lines": repaired}


def by_source(responses: list[VlmResponse], source: str) -> list[VlmResponse]:
    return [r for r in responses if r.source == source]


def composition(responses: list[VlmResponse], crops: dict[str, Any]) -> dict[str, float]:
    weights = np.array([crops[r.crop_id]["face_area_m2"] for r in responses])
    return pooled_posterior(responses, weights)


def outer_layer_composition(responses: list[VlmResponse], crops: dict[str, Any]) -> dict[str, float]:
    """Area weighted composition of the outermost layer the model named.

    This is a different quantity from the material posterior and the difference
    is not cosmetic. At 15 GHz a render coat thicker than about two millimetres
    hides its substrate, so what the wave meets is the outer layer, while the
    posterior answers what the building is made of. The model does both and does
    not always give the same answer, which is a prompt design fault rather than a
    model fault, and it is measurable here.
    """
    weight: dict[str, float] = {name: 0.0 for name in MATERIAL_VOCABULARY}
    for response in responses:
        material = response.stack[0].material if response.stack else "unknown"
        weight[material] += float(crops[response.crop_id]["face_area_m2"])
    total = sum(weight.values())
    return {name: value / total for name, value in weight.items()}


def outer_layer_disagreement(responses: list[VlmResponse]) -> dict[str, Any]:
    rows = [
        {"crop_id": r.crop_id, "outer": r.stack[0].material, "posterior_top": r.top_material()}
        for r in responses
        if r.stack and r.stack[0].material != r.top_material()
    ]
    return {"count": len(rows), "of": len(responses), "examples": rows[:8]}


def top_counts(responses: list[VlmResponse]) -> dict[str, int]:
    out = {name: 0 for name in MATERIAL_VOCABULARY}
    for response in responses:
        out[response.top_material()] += 1
    return {name: count for name, count in out.items() if count}


def paired_source_gap(responses: list[VlmResponse]) -> dict[str, float]:
    """Panorama against tile texture on the same crop and the same draw."""
    index: dict[tuple[str, int, str], VlmResponse] = {}
    for response in responses:
        index[(response.crop_id, response.draw, response.source)] = response
    top1: list[float] = []
    distance: list[float] = []
    confidence_gap: list[float] = []
    for (crop_id, draw, source), response in index.items():
        if source != "panorama":
            continue
        other = index.get((crop_id, draw, "texture"))
        if other is None:
            continue
        top1.append(float(response.top_material() == other.top_material()))
        distance.append(total_variation(response.posterior, other.posterior))
        confidence_gap.append(response.stated_confidence - other.stated_confidence)
    return {
        "pairs": len(top1),
        "top1_agreement": float(np.mean(top1)) if top1 else float("nan"),
        "mean_total_variation": float(np.mean(distance)) if distance else float("nan"),
        "mean_confidence_gap_panorama_minus_texture": float(np.mean(confidence_gap))
        if confidence_gap
        else float("nan"),
    }


def reflectance_table(library: Any, frequency_hz: float, priors: dict[str, dict[str, float]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for angle in (0.0, 30.0, 45.0, 60.0, 75.0):
        cosine = float(np.cos(np.radians(angle)))
        reflectance = material_power_reflectance(frequency_hz, cosine, library)
        row: dict[str, Any] = {"materials_db": {k: round(10 * np.log10(v), 3) for k, v in reflectance.items()}}
        for name, prior in priors.items():
            mean = posterior_power_reflectance(prior, reflectance)
            mode = argmax_power_reflectance(prior, reflectance)
            row[name] = {
                "argmax_reflectance": mode,
                "posterior_mean_reflectance": mean,
                "mean_over_argmax_db": float(10 * np.log10(mean / mode)),
            }
        out[f"{angle:g}_deg"] = row
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "material_vlm")
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    args = parser.parse_args()

    responses, crops, notes = load_all(args.out)
    panorama = by_source(responses, "panorama")
    texture = by_source(responses, "texture")

    building_prior = json.loads(BUILDING_PRIOR_SOURCE.read_text())["vistas_material_prior"]["Building"]
    fixed = {name: float(building_prior.get(name, 0.0)) for name in MATERIAL_VOCABULARY}
    # The published prior spends mass on names outside this study's traceable
    # vocabulary, so the residue is folded onto unknown rather than dropped.
    fixed["unknown"] += max(0.0, 1.0 - sum(fixed.values()))

    library = MaterialLibrary.load(CONFIG / "itu_p2040_4.json")
    frequency = args.frequency_ghz * 1e9

    panorama_composition = composition(panorama, crops)
    texture_composition = composition(texture, crops)
    outer_panorama = outer_layer_composition(panorama, crops)

    patch_of = {record["crop_id"]: record["patch"] for record in crops.values()}
    same_crop = {r.crop_id: r.crop_id for r in responses}

    report: dict[str, Any] = {
        "prompt_digest": prompt_digest(),
        "responses": {
            "total": len(responses),
            "panorama": len(panorama),
            "texture": len(texture),
            "rejected": notes["rejected"],
            "repaired_transport_lines": notes["repaired_lines"],
            "crops": len(crops),
            "patches": len(set(patch_of.values())),
        },
        "legibility": {
            "panorama": float(np.mean([r.legible for r in panorama])),
            "texture": float(np.mean([r.legible for r in texture])),
        },
        "entropy_bits": {
            "panorama_mean": float(np.mean([r.entropy_bits() for r in panorama])),
            "texture_mean": float(np.mean([r.entropy_bits() for r in texture])),
        },
        "stated_confidence": {
            "panorama_mean": float(np.mean([r.stated_confidence for r in panorama])),
            "texture_mean": float(np.mean([r.stated_confidence for r in texture])),
        },
        "top_material_counts": {
            "panorama": top_counts(panorama),
            "texture": top_counts(texture),
        },
        "periodic_relief_fraction": {
            "panorama": float(np.mean([r.relief_pattern in PERIODIC_RELIEF for r in panorama])),
            "texture": float(np.mean([r.relief_pattern in PERIODIC_RELIEF for r in texture])),
        },
        "reported_course_pitch_mm": sorted(
            r.relief_pitch_mm
            for r in panorama
            if r.relief_pattern == "coursed_masonry" and r.relief_pitch_mm is not None
        ),
        "composition": {
            "fixed_building_prior": fixed,
            "vlm_panorama": panorama_composition,
            "vlm_texture": texture_composition,
            "vlm_panorama_outer_layer": outer_panorama,
            "outer_layer_disagreement": outer_layer_disagreement(panorama),
            "total_variation_vlm_vs_fixed": total_variation(panorama_composition, fixed),
            "total_variation_panorama_vs_texture": total_variation(panorama_composition, texture_composition),
        },
        "self_consistency": {
            "repeat_draw_panorama": agreement(panorama, same_crop).__dict__,
            "repeat_draw_texture": agreement(texture, same_crop).__dict__,
            "cross_view_panorama": agreement(panorama, patch_of).__dict__,
            "cross_view_texture": agreement(texture, patch_of).__dict__,
        },
        "cross_source": paired_source_gap(responses),
        "calibration": {
            "panorama_repeat_curve": reliability(panorama, same_crop),
            "panorama_cross_view_curve": reliability(panorama, patch_of),
            "texture_repeat_curve": reliability(texture, same_crop),
        },
        "reflectance": reflectance_table(
            library,
            frequency,
            {
                "fixed_building_prior": fixed,
                "vlm_panorama": panorama_composition,
                "vlm_texture": texture_composition,
                "vlm_panorama_outer_layer": outer_panorama,
            },
        ),
    }
    for name in ("panorama_repeat_curve", "panorama_cross_view_curve", "texture_repeat_curve"):
        report["calibration"][f"{name}_gap"] = expected_calibration_gap(report["calibration"][name])

    (args.out / "analysis.json").write_text(json.dumps(report, indent=2, default=float))

    print(
        f"responses {len(responses)} ({len(panorama)} panorama, {len(texture)} texture), rejected {len(notes['rejected'])}"
    )
    print(f"legible: panorama {report['legibility']['panorama']:.2f}, texture {report['legibility']['texture']:.2f}")
    print(
        f"entropy bits: panorama {report['entropy_bits']['panorama_mean']:.2f}, "
        f"texture {report['entropy_bits']['texture_mean']:.2f}"
    )
    print(f"top materials panorama: {report['top_material_counts']['panorama']}")
    print(f"top materials texture:  {report['top_material_counts']['texture']}")
    print("\ncomposition, area weighted:")
    for name in MATERIAL_VOCABULARY:
        print(
            f"  {name:14s} fixed {fixed[name]:.3f}   vlm panorama {panorama_composition[name]:.3f}   "
            f"vlm texture {texture_composition[name]:.3f}"
        )
    print(f"\ncross source top1 agreement {report['cross_source']['top1_agreement']:.3f}")
    for name, value in report["self_consistency"].items():
        print(
            f"{name}: top1 {value['top1_agreement']:.3f}, TV {value['mean_total_variation']:.3f}, pairs {value['pairs']}"
        )
    print("\nreflectance at 15 GHz:")
    for angle, row in report["reflectance"].items():
        line = "  ".join(
            f"{name} mean/argmax {row[name]['mean_over_argmax_db']:+.2f} dB"
            for name in ("fixed_building_prior", "vlm_panorama")
        )
        print(f"  {angle}: {line}")
    print(f"\n-> {args.out / 'analysis.json'}")


if __name__ == "__main__":
    main()
