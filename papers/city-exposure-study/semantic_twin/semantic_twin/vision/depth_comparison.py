"""Fuse two monocular depth models with the tile mesh into a blockage decision.

The output is intentionally conservative. A high residual is an *evidence
conflict*, not automatic geometry creation.  Only a nearer ML surface receives
the ``front_blocker`` decision, and that decision remains view-local until it
is corroborated by distinct panorama centres.

Two models are used because one is not enough to tell a real foreground object
from its own metric drift.  The fusion rule is a consensus rule:

* a ``front_blocker`` needs *every* model to place a surface nearer than the
  mesh first hit, at three sigma.  Taking the minimum over models means the
  weakest claim decides, so a model on its own can never open a blocker,
* the gap between the models is folded into each model's log-range sigma, so
  where they disagree every residual shrinks toward zero,
* the two mechanisms point the same way on purpose.  Disagreement can only
  remove a blocker, never create one,
* and ``agree`` additionally requires the models to be consistent with *each
  other*, so a pixel where the sigma inflation has swallowed a large conflict
  is reported as ``uncertain`` rather than as agreement.

This stage exists to catch registration error, so it is not allowed to absorb
it.  Both fitted range scales are checked against a plausibility band and
across the crops of a single panorama before any pixel is classified.  An
implausible fit stops the run by default.  With ``--on-implausible-scale
degrade`` it instead emits ``no_depth_evidence`` on every mesh pixel, which
falls the cutter back to the mesh first hit plus the class test, and records
the degradation in the manifest.  It never invents a blocker.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from semantic_twin.vision.depth_models import DEFAULT_REFERENCE_LOG_SIGMA, relative_error_to_log_sigma

__all__ = [
    "AGREEMENT_Z",
    "BLOCKER_Z",
    "COLOURS",
    "DECISIONS",
    "DEFAULT_REFERENCE_LOG_SIGMA",
    "DYNAMIC_OBJECT_LABELS",
    "DepthComparisonConfig",
    "MAX_CROSS_VIEW_SCALE_SPREAD",
    "MIN_DISAGREEMENT_LOG_SIGMA",
    "OBJECT_IDS",
    "PLAUSIBLE_SCALE_BAND",
    "SECOND_OPINION_LOG_SIGMA",
    "STATIC_CALIBRATION_IDS",
    "STATIC_CALIBRATION_LABELS",
    "classify",
    "compare_mesh_depth",
    "depth_log_sigma",
    "fit_log_scale",
    "scale_plausibility",
]

# Legacy defaults preserve the small unit-test fixtures.  Real runs resolve
# ids from the segmentation manifest, since Mapillary Vistas and a material
# head do not share a numeric taxonomy.
STATIC_CALIBRATION_IDS = {1, 2, 5, 6}
OBJECT_IDS = {9, 10, 11, 12, 13}
STATIC_CALIBRATION_LABELS = {
    "building",
    "wall",
    "road",
    "pedestrian area",
    "rail track",
    "sidewalk",
    "terrain",
}
DYNAMIC_OBJECT_LABELS = {
    "person",
    "bicyclist",
    "motorcyclist",
    "other rider",
    "bus",
    "car",
    "caravan",
    "truck",
    "trailer",
    "other vehicle",
    "motorcycle",
    "bicycle",
    "wheeled slow",
    "ego vehicle",
}

# UniDepthV2 is a metric model, so a correctly registered support mesh has to
# agree with it up to a factor near one. A factor of two either way is already a
# generous allowance for tile geometry error and residual pose error.
PLAUSIBLE_SCALE_BAND = (0.5, 2.0)
# All crops of one panorama share a camera centre, so their fitted scales cannot
# genuinely differ by much.
MAX_CROSS_VIEW_SCALE_SPREAD = 1.5

# Depth Anything V2 Metric Outdoor publishes no uncertainty field, so its
# log-range sigma is a stated prior of the same kind as the mesh prior, pinned
# to the same anchor that UniDepth's error ranking is pinned to.
SECOND_OPINION_LOG_SIGMA = DEFAULT_REFERENCE_LOG_SIGMA
# Two models that happen to land on the same number are not thereby exact, so
# the cross-model gap enters as an extra sigma with a floor rather than as a
# free precision gain.
MIN_DISAGREEMENT_LOG_SIGMA = 0.15
# A blocker is a three-sigma claim that every model supports.  Agreement is the
# two-sigma band, both against the mesh and between the models themselves.
BLOCKER_Z = 3.0
AGREEMENT_Z = 2.0

DECISIONS = {
    "no_mesh": 0,
    "agree": 1,
    "uncertain": 2,
    "front_blocker": 3,
    "mesh_or_pose_blocker": 4,
    "dynamic_object": 5,
    "no_depth_evidence": 6,
}
COLOURS = np.asarray(
    [
        (90, 90, 90),  # no mesh
        (20, 190, 90),  # agreement
        (245, 192, 30),  # uncertain
        (235, 50, 42),  # ML surface in front of mesh
        (130, 55, 190),  # mesh is implausibly in front
        (35, 150, 245),  # person or vehicle: independently handled blocker
        (140, 140, 140),  # depth evidence withheld: mesh first hit decides alone
    ],
    dtype=np.uint8,
)


def fit_log_scale(
    mesh_range: np.ndarray,
    ml_range: np.ndarray,
    log_sigma: np.ndarray,
    labels: np.ndarray,
    *,
    static_ids: set[int] = STATIC_CALIBRATION_IDS,
) -> float:
    """Fit only one global scale using reliable static support in a crop.

    ``log_sigma`` grows where the depth model expects to be wrong, so the
    percentile keeps the most reliable 60 percent of static pixels.
    """
    calibration = (
        np.isfinite(mesh_range)
        & np.isfinite(ml_range)
        & (mesh_range > 0.0)
        & (ml_range > 0.0)
        & np.isin(labels, list(static_ids))
        & (log_sigma <= np.nanpercentile(log_sigma, 60.0))
    )
    if calibration.sum() < 100:
        raise ValueError("not enough reliable static pixels to calibrate UniDepth range")
    return float(np.exp(np.median(np.log(mesh_range[calibration]) - np.log(ml_range[calibration]))))


def scale_plausibility(
    scales: dict[str, float],
    *,
    uncalibrated: dict[str, str] | None = None,
    band: tuple[float, float] = PLAUSIBLE_SCALE_BAND,
    max_spread: float = MAX_CROSS_VIEW_SCALE_SPREAD,
    model: str = "",
) -> dict[str, Any]:
    """Judge whether the fitted range scales can be a real metric factor.

    UniDepthV2 predicts metric range, so a correctly registered mesh needs a
    fitted scale near one.  Every crop of one panorama also shares a single
    camera centre, so the crops have to agree with each other.  A scale far from
    one, or crops that disagree, means the mesh and the panorama are not in the
    same place.  Fitting a free per-view scale would hide exactly that, turning
    a registration failure into a large "agreeing pixel" count.
    """
    if band[0] >= band[1] or band[0] <= 0.0:
        raise ValueError("the plausibility band must be a positive increasing interval")
    if max_spread < 1.0:
        raise ValueError("max_spread is a ratio of fitted scales and cannot be below one")
    problems = [f"{view}: {reason}" for view, reason in sorted((uncalibrated or {}).items())]
    for view, scale in sorted(scales.items()):
        if not np.isfinite(scale) or not band[0] <= scale <= band[1]:
            problems.append(
                f"{view}: fitted range scale {scale:.3f} is outside the plausible band "
                f"{band[0]:g}-{band[1]:g} for a metric depth model"
            )
    finite = [scale for scale in scales.values() if np.isfinite(scale) and scale > 0.0]
    spread = max(finite) / min(finite) if len(finite) >= 2 else None
    if spread is not None and spread > max_spread:
        problems.append(
            f"the crops of one panorama disagree by {spread:.2f}x, above the {max_spread:g}x limit; "
            "one camera centre cannot have several metric scales"
        )
    if not scales:
        problems.append("no view produced a range scale at all")
    if model:
        problems = [f"{model}: {problem}" for problem in problems]
    return {
        "ok": not problems,
        "problems": problems,
        "model": model,
        "scales": dict(sorted(scales.items())),
        "cross_view_spread": spread,
        "plausible_band": list(band),
        "max_cross_view_spread": max_spread,
    }


def _log(values: np.ndarray) -> np.ndarray:
    return np.log(np.maximum(np.asarray(values, dtype=np.float64), 1e-5))


def classify(
    mesh_range: np.ndarray,
    ml_range: np.ndarray,
    log_sigma: np.ndarray,
    labels: np.ndarray,
    *,
    scale: float,
    second_opinion_range: np.ndarray | None = None,
    second_opinion_scale: float | None = None,
    second_opinion_log_sigma: float = SECOND_OPINION_LOG_SIGMA,
    mesh_log_sigma: float = 0.35,
    dynamic_ids: set[int] = OBJECT_IDS,
    depth_evidence: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Fuse the depth models with the mesh into one decision per pixel.

    The returned residual is the *consensus* one: the largest signed number of
    sigmas that every supplied model supports, and zero where the models fall on
    opposite sides of the mesh.  Thresholding that statistic is what makes a
    blocker a claim no model contradicts.

    ``mesh_log_sigma`` is a deliberately broad initial prior for rough tile
    geometry plus pose error. It will be replaced by an empirical, range-aware
    value when multiple physical panorama centres are available.

    ``depth_evidence=False`` is the degraded path taken when the fitted range
    scales are not plausible.  Every mesh pixel becomes ``no_depth_evidence``,
    which withholds the distance test entirely rather than reporting agreement
    or inventing a blocker.  The class-driven ``dynamic_object`` decision does
    not depend on any fitted scale, so it survives the degradation.
    """
    mesh_range = np.asarray(mesh_range, dtype=np.float64)
    has_mesh = np.isfinite(mesh_range) & (mesh_range > 0.0)
    dynamic = np.isin(labels, list(dynamic_ids))
    if not depth_evidence:
        decision = np.where(has_mesh, DECISIONS["no_depth_evidence"], DECISIONS["no_mesh"]).astype(np.uint8)
        decision[dynamic] = DECISIONS["dynamic_object"]
        return decision, np.zeros(mesh_range.shape, dtype=np.float32)

    log_mesh = _log(mesh_range)
    log_models = [_log(ml_range) + math.log(scale)]
    sigmas = [np.asarray(log_sigma, dtype=np.float64)]
    if second_opinion_range is not None:
        if second_opinion_scale is None:
            raise ValueError("a second-opinion range needs its fitted scale")
        log_models.append(_log(second_opinion_range) + math.log(second_opinion_scale))
        sigmas.append(np.full(mesh_range.shape, float(second_opinion_log_sigma)))

    # Where the models disagree, every one of them becomes less certain.  This
    # can only shrink a residual toward zero, so it can only remove a blocker.
    inflated = list(sigmas)
    model_conflict = np.zeros(mesh_range.shape, dtype=np.float64)
    if len(log_models) > 1:
        disagreement = np.max(log_models, axis=0) - np.min(log_models, axis=0)
        extra = np.square(np.maximum(MIN_DISAGREEMENT_LOG_SIGMA, disagreement / 2.0))
        inflated = [np.sqrt(np.square(sigma) + extra) for sigma in sigmas]
        pair_sigma = np.sqrt(sum(np.square(sigma) for sigma in sigmas))
        model_conflict = disagreement / np.maximum(pair_sigma, 1e-5)

    z_scores = np.stack(
        [
            (log_mesh - log_model) / np.maximum(np.sqrt(np.square(sigma) + mesh_log_sigma**2), 1e-5)
            for log_model, sigma in zip(log_models, inflated, strict=True)
        ]
    )
    z_low = z_scores.min(axis=0)
    z_high = z_scores.max(axis=0)
    consensus = np.where(z_low > 0.0, z_low, np.where(z_high < 0.0, z_high, 0.0))

    decision = np.full(mesh_range.shape, DECISIONS["no_mesh"], dtype=np.uint8)
    decision[has_mesh] = DECISIONS["uncertain"]
    agreed = (np.abs(z_scores).max(axis=0) < AGREEMENT_Z) & (model_conflict < AGREEMENT_Z)
    decision[has_mesh & agreed] = DECISIONS["agree"]
    decision[has_mesh & (z_low >= BLOCKER_Z)] = DECISIONS["front_blocker"]
    decision[has_mesh & (z_high <= -BLOCKER_Z)] = DECISIONS["mesh_or_pose_blocker"]
    decision[dynamic] = DECISIONS["dynamic_object"]
    return decision, consensus.astype(np.float32)


@dataclass(frozen=True)
class DepthComparisonConfig:
    views: pathlib.Path
    mesh_depth: pathlib.Path
    unidepth: pathlib.Path
    sam_labels: pathlib.Path
    out: pathlib.Path
    depth_anything: pathlib.Path | None = None
    semantics_json: pathlib.Path | None = None
    yaws: tuple[int, ...] = (0, 90, 180, 270)
    reference_log_sigma: float = DEFAULT_REFERENCE_LOG_SIGMA
    plausible_scale_band: tuple[float, float] = PLAUSIBLE_SCALE_BAND
    max_cross_view_scale_spread: float = MAX_CROSS_VIEW_SCALE_SPREAD
    second_opinion_log_sigma: float = SECOND_OPINION_LOG_SIGMA
    on_implausible_scale: str = "stop"


def depth_log_sigma(document: Any, *, reference_log_sigma: float) -> np.ndarray:
    """Read a log-depth sigma from a UniDepth NPZ, new layout or legacy.

    Runs made before the uncertainty field was named honestly stored the raw
    UniDepth output under ``log_error``. It is the same error ranking, so it is
    anchored the same way rather than trusted as a standard deviation.
    """
    if "log_sigma" in document.files:
        return np.asarray(document["log_sigma"], dtype=np.float32)
    legacy = "relative_error" if "relative_error" in document.files else "log_error"
    return relative_error_to_log_sigma(document[legacy], reference_log_sigma=reference_log_sigma)


def _class_ids(semantics_json: pathlib.Path | None) -> tuple[set[int], set[int]]:
    if semantics_json is None:
        return STATIC_CALIBRATION_IDS, OBJECT_IDS
    entity_id2label = json.loads(semantics_json.read_text())["entity_id2label"]
    label2id = {name.casefold(): int(class_id) for class_id, name in entity_id2label.items()}
    static_ids = {label2id[name] for name in STATIC_CALIBRATION_LABELS if name in label2id}
    dynamic_ids = {label2id[name] for name in DYNAMIC_OBJECT_LABELS if name in label2id}
    if not static_ids:
        raise ValueError("segmentation manifest has no static calibration classes")
    return static_ids, dynamic_ids


def _fit_scales(
    config: DepthComparisonConfig,
    names: list[str],
    static_ids: set[int],
) -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
    scales: dict[str, float] = {}
    second_scales: dict[str, float] = {}
    uncalibrated: dict[str, str] = {}
    second_uncalibrated: dict[str, str] = {}
    for name in names:
        mesh = np.load(config.mesh_depth / f"{name}.npz")["range_m"]
        labels = np.load(config.sam_labels / f"{name}_labels.npy")
        with np.load(config.unidepth / f"{name}.npz") as depth:
            log_sigma = depth_log_sigma(depth, reference_log_sigma=config.reference_log_sigma)
            try:
                scales[name] = fit_log_scale(mesh, depth["range_m"], log_sigma, labels, static_ids=static_ids)
            except ValueError as error:
                uncalibrated[name] = str(error)
                print(f"[depth-compare] {name}: uncalibrated ({error})")
        if config.depth_anything is None:
            continue
        second = np.load(config.depth_anything / f"{name}.npz")["range_m"]
        try:
            second_scales[name] = fit_log_scale(mesh, second, log_sigma, labels, static_ids=static_ids)
        except ValueError as error:
            second_uncalibrated[name] = str(error)
    return scales, second_scales, uncalibrated, second_uncalibrated


def _comparison_reports(
    config: DepthComparisonConfig,
    scales: dict[str, float],
    second_scales: dict[str, float],
    uncalibrated: dict[str, str],
    second_uncalibrated: dict[str, str],
) -> list[dict[str, Any]]:
    band = (float(config.plausible_scale_band[0]), float(config.plausible_scale_band[1]))
    max_spread = float(config.max_cross_view_scale_spread)
    reports = [
        scale_plausibility(scales, uncalibrated=uncalibrated, band=band, max_spread=max_spread, model="unidepth")
    ]
    if config.depth_anything is not None:
        reports.append(
            scale_plausibility(
                second_scales,
                uncalibrated=second_uncalibrated,
                band=band,
                max_spread=max_spread,
                model="depth_anything",
            )
        )
    return reports


def _classify_view(
    config: DepthComparisonConfig,
    name: str,
    scale: float,
    second_scale: float | None,
    dynamic_ids: set[int],
    *,
    depth_evidence: bool,
) -> dict[str, Any]:
    mesh = np.load(config.mesh_depth / f"{name}.npz")["range_m"]
    labels = np.load(config.sam_labels / f"{name}_labels.npy")
    with np.load(config.unidepth / f"{name}.npz") as depth:
        ml_range = np.asarray(depth["range_m"])
        log_sigma = depth_log_sigma(depth, reference_log_sigma=config.reference_log_sigma)
    second_range = None
    if config.depth_anything is not None and second_scale is not None:
        second_range = np.load(config.depth_anything / f"{name}.npz")["range_m"]
    decision, z_score = classify(
        mesh,
        ml_range,
        log_sigma,
        labels,
        scale=scale,
        second_opinion_range=second_range,
        second_opinion_scale=second_scale if second_range is not None else None,
        second_opinion_log_sigma=config.second_opinion_log_sigma,
        dynamic_ids=dynamic_ids,
        depth_evidence=depth_evidence,
    )
    np.savez_compressed(
        config.out / f"{name}.npz",
        decision=decision,
        z_score=z_score,
        mesh_range_m=mesh,
        unidepth_range_m=ml_range,
        unidepth_scaled_range_m=ml_range * scale,
        unidepth_log_sigma=log_sigma,
        scale=np.asarray(scale, dtype=np.float32),
        depth_anything_range_m=second_range if second_range is not None else np.asarray([], dtype=np.float32),
        depth_anything_scale=np.asarray(second_scale if second_scale is not None else np.nan, dtype=np.float32),
        depth_evidence=np.asarray(depth_evidence),
    )
    image = np.asarray(Image.open(config.views / f"{name}.jpg").convert("RGB"), dtype=np.uint8)
    overlay = np.round(0.48 * image + 0.52 * COLOURS[decision]).astype(np.uint8)
    Image.fromarray(overlay).save(config.out / f"{name}_decisions_overlay.jpg", quality=95)
    counts = {label: int((decision == value).sum()) for label, value in DECISIONS.items()}
    print(
        f"[depth-compare] {name}: UniDepth scale={scale:.3f}, front blockers={counts['front_blocker']}, "
        f"withheld={counts['no_depth_evidence']}"
    )
    return {"view": name, "unidepth_scale": scale, "depth_anything_scale": second_scale, "counts": counts}


def compare_mesh_depth(config: DepthComparisonConfig) -> None:
    args = config
    args.out.mkdir(parents=True, exist_ok=True)
    static_ids, dynamic_ids = _class_ids(args.semantics_json)
    names = [f"h+00_{yaw:03d}" for yaw in args.yaws]

    scales, second_scales, uncalibrated, second_uncalibrated = _fit_scales(args, names, static_ids)
    # Both models are load-bearing, so both fits are gated.  A second opinion
    # whose own metric claim is broken cannot corroborate anything.
    reports = _comparison_reports(args, scales, second_scales, uncalibrated, second_uncalibrated)
    problems = [problem for report in reports for problem in report["problems"]]
    plausible = not problems
    header = {
        "decisions": DECISIONS,
        "initial_mesh_log_sigma": 0.35,
        "reference_log_sigma": args.reference_log_sigma,
        "second_opinion_log_sigma": args.second_opinion_log_sigma,
        "static_calibration_ids": sorted(static_ids),
        "dynamic_object_ids": sorted(dynamic_ids),
        "scale_plausibility": {"ok": plausible, "problems": problems, "per_model": reports},
        "on_implausible_scale": args.on_implausible_scale,
        "fusion": "front_blocker needs every depth model to agree; cross-model disagreement only widens sigma",
        "front_blocker": "every model puts a surface nearer than the tile first hit, at z >= 3",
        "mesh_or_pose_blocker": "every model puts the tile first hit implausibly near, at z <= -3",
        "dynamic_object": "SAM person/vehicle/table mask, separately reconstructed as a dynamic layer",
        "no_depth_evidence": "range fit not plausible, distance test withheld and the mesh first hit decides alone",
    }
    if not plausible:
        for problem in problems:
            print(f"[depth-compare] {problem}", file=sys.stderr)
    if not plausible and args.on_implausible_scale == "stop":
        (args.out / "manifest.json").write_text(json.dumps({**header, "status": "rejected", "views": []}, indent=2))
        raise SystemExit(
            "the fitted range scales are not physically plausible, so mesh agreement cannot be reported; fix the "
            "registration, or pass --on-implausible-scale degrade to withhold the distance test and keep going"
        )
    depth_evidence = plausible or args.on_implausible_scale == "classify"

    manifest: list[dict[str, Any]] = [
        {"view": name, "status": "uncalibrated", "reason": reason} for name, reason in sorted(uncalibrated.items())
    ]
    for name in names:
        if name not in scales:
            continue
        scale = scales[name]
        second_scale = second_scales.get(name)
        manifest.append(_classify_view(args, name, scale, second_scale, dynamic_ids, depth_evidence=depth_evidence))

    status = "ok" if plausible else f"implausible_scale_{args.on_implausible_scale}"
    (args.out / "manifest.json").write_text(json.dumps({**header, "status": status, "views": manifest}, indent=2))
