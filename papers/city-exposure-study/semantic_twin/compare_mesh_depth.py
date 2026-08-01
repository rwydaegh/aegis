"""Compare mesh first-hit range against UniDepth and label provisional blockers.

The output is intentionally conservative. A high residual is an *evidence
conflict*, not automatic geometry creation.  Only a nearer ML surface receives
the ``front_blocker`` decision, and that decision remains view-local until it
is corroborated by distinct panorama centres.

This stage exists to catch registration error, so it is not allowed to absorb
it.  The fitted UniDepth range scale is checked against a plausibility band and
across the crops of a single panorama before any pixel is classified.  An
implausible fit stops the run instead of reporting agreement.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import numpy as np
from PIL import Image

from infer_unidepth import DEFAULT_REFERENCE_LOG_SIGMA, relative_error_to_log_sigma

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

DECISIONS = {
    "no_mesh": 0,
    "agree": 1,
    "uncertain": 2,
    "front_blocker": 3,
    "mesh_or_pose_blocker": 4,
    "dynamic_object": 5,
}
COLOURS = np.asarray(
    [
        (90, 90, 90),  # no mesh
        (20, 190, 90),  # agreement
        (245, 192, 30),  # uncertain
        (235, 50, 42),  # ML surface in front of mesh
        (130, 55, 190),  # mesh is implausibly in front
        (35, 150, 245),  # person or vehicle: independently handled blocker
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
) -> dict[str, Any]:
    """Judge whether the fitted range scales can be a real metric factor.

    UniDepthV2 predicts metric range, so a correctly registered mesh needs a
    fitted scale near one.  Every crop of one panorama also shares a single
    camera centre, so the crops have to agree with each other.  A scale far from
    one, or crops that disagree, means the mesh and the panorama are not in the
    same place.  Fitting a free per-view scale would hide exactly that, turning
    a registration failure into a large "agreeing pixel" count.
    """
    if not band[0] < band[1] or band[0] <= 0.0:
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
    spread = None
    if len(scales) >= 2:
        finite = [scale for scale in scales.values() if np.isfinite(scale) and scale > 0.0]
        if len(finite) >= 2:
            spread = max(finite) / min(finite)
            if spread > max_spread:
                problems.append(
                    f"the crops of one panorama disagree by {spread:.2f}x, above the {max_spread:g}x limit; "
                    "one camera centre cannot have several metric scales"
                )
    if not scales:
        problems.append("no view produced a range scale at all")
    return {
        "ok": not problems,
        "problems": problems,
        "scales": dict(sorted(scales.items())),
        "cross_view_spread": spread,
        "plausible_band": list(band),
        "max_cross_view_spread": max_spread,
    }


def classify(
    mesh_range: np.ndarray,
    ml_range: np.ndarray,
    log_sigma: np.ndarray,
    labels: np.ndarray,
    *,
    scale: float,
    second_opinion_range: np.ndarray | None = None,
    second_opinion_scale: float | None = None,
    mesh_log_sigma: float = 0.35,
    dynamic_ids: set[int] = OBJECT_IDS,
) -> tuple[np.ndarray, np.ndarray]:
    """Return explicit decisions and normalised log-range residuals.

    ``mesh_log_sigma`` is a deliberately broad initial prior for rough tile
    geometry plus pose error. It will be replaced by an empirical, range-aware
    value when multiple physical panorama centres are available.
    """
    calibrated = ml_range * scale
    residual = np.log(np.maximum(mesh_range, 1e-5)) - np.log(np.maximum(calibrated, 1e-5))
    sigma_ml = np.asarray(log_sigma, dtype=np.float32)
    if second_opinion_range is not None:
        if second_opinion_scale is None:
            raise ValueError("a second-opinion range needs its fitted scale")
        disagreement = np.abs(
            np.log(np.maximum(calibrated, 1e-5)) - np.log(np.maximum(second_opinion_range * second_opinion_scale, 1e-5))
        )
        # Depth Anything has no native uncertainty. Half the cross-model gap is
        # a conservative independent-error proxy, with a nonzero floor.
        sigma_ml = np.sqrt(np.square(sigma_ml) + np.square(np.maximum(0.15, disagreement / 2.0)))
    sigma = np.sqrt(np.square(sigma_ml) + mesh_log_sigma**2)
    z_score = residual / np.maximum(sigma, 1e-5)
    decision = np.full(mesh_range.shape, DECISIONS["no_mesh"], dtype=np.uint8)
    has_mesh = np.isfinite(mesh_range) & (mesh_range > 0.0)
    decision[has_mesh & (np.abs(z_score) < 2.0)] = DECISIONS["agree"]
    decision[has_mesh & (np.abs(z_score) >= 2.0) & (np.abs(z_score) < 3.0)] = DECISIONS["uncertain"]
    decision[has_mesh & (z_score >= 3.0)] = DECISIONS["front_blocker"]
    decision[has_mesh & (z_score <= -3.0)] = DECISIONS["mesh_or_pose_blocker"]
    decision[np.isin(labels, list(dynamic_ids))] = DECISIONS["dynamic_object"]
    return decision, z_score.astype(np.float32)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--mesh-depth", type=pathlib.Path, required=True)
    parser.add_argument("--unidepth", type=pathlib.Path, required=True)
    parser.add_argument("--depth-anything", type=pathlib.Path)
    parser.add_argument("--sam-labels", type=pathlib.Path, required=True)
    parser.add_argument(
        "--semantics-json",
        type=pathlib.Path,
        help="Segmentation manifest used to resolve class names to ids.",
    )
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--reference-log-sigma", type=float, default=DEFAULT_REFERENCE_LOG_SIGMA)
    parser.add_argument(
        "--plausible-scale-band",
        type=float,
        nargs=2,
        default=list(PLAUSIBLE_SCALE_BAND),
        metavar=("LOW", "HIGH"),
    )
    parser.add_argument("--max-cross-view-scale-spread", type=float, default=MAX_CROSS_VIEW_SCALE_SPREAD)
    parser.add_argument(
        "--allow-implausible-scale",
        action="store_true",
        help="Classify anyway after an implausible range fit, for diagnosis only.",
    )
    return parser.parse_args()


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


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    static_ids, dynamic_ids = _class_ids(args.semantics_json)
    names = [f"h+00_{yaw:03d}" for yaw in args.yaws]

    scales: dict[str, float] = {}
    uncalibrated: dict[str, str] = {}
    for name in names:
        mesh = np.load(args.mesh_depth / f"{name}.npz")["range_m"]
        labels = np.load(args.sam_labels / f"{name}_labels.npy")
        with np.load(args.unidepth / f"{name}.npz") as depth:
            log_sigma = depth_log_sigma(depth, reference_log_sigma=args.reference_log_sigma)
            try:
                scales[name] = fit_log_scale(mesh, depth["range_m"], log_sigma, labels, static_ids=static_ids)
            except ValueError as error:
                uncalibrated[name] = str(error)
                print(f"[depth-compare] {name}: uncalibrated ({error})")

    report = scale_plausibility(
        scales,
        uncalibrated=uncalibrated,
        band=(float(args.plausible_scale_band[0]), float(args.plausible_scale_band[1])),
        max_spread=float(args.max_cross_view_scale_spread),
    )
    header = {
        "decisions": DECISIONS,
        "initial_mesh_log_sigma": 0.35,
        "reference_log_sigma": args.reference_log_sigma,
        "static_calibration_ids": sorted(static_ids),
        "dynamic_object_ids": sorted(dynamic_ids),
        "scale_plausibility": report,
        "front_blocker": "ML predicts a closer surface than the tile first hit, at z >= 3",
        "mesh_or_pose_blocker": "tile first hit is implausibly closer than ML depth, at z <= -3",
        "dynamic_object": "SAM person/vehicle/table mask, separately reconstructed as a dynamic layer",
    }
    if not report["ok"] and not args.allow_implausible_scale:
        (args.out / "manifest.json").write_text(json.dumps({**header, "status": "rejected", "views": []}, indent=2))
        for problem in report["problems"]:
            print(f"[depth-compare] {problem}", file=sys.stderr)
        raise SystemExit(
            "the fitted UniDepth range scales are not physically plausible, so mesh agreement cannot be "
            "reported; fix the registration, or pass --allow-implausible-scale to inspect the maps anyway"
        )

    manifest: list[dict[str, Any]] = [
        {"view": name, "status": "uncalibrated", "reason": reason} for name, reason in sorted(uncalibrated.items())
    ]
    for name in names:
        if name not in scales:
            continue
        scale = scales[name]
        mesh = np.load(args.mesh_depth / f"{name}.npz")["range_m"]
        labels = np.load(args.sam_labels / f"{name}_labels.npy")
        with np.load(args.unidepth / f"{name}.npz") as depth:
            ml_range = np.asarray(depth["range_m"])
            log_sigma = depth_log_sigma(depth, reference_log_sigma=args.reference_log_sigma)
        second_range = None
        second_scale = None
        if args.depth_anything is not None:
            second_range = np.load(args.depth_anything / f"{name}.npz")["range_m"]
            second_scale = fit_log_scale(mesh, second_range, log_sigma, labels, static_ids=static_ids)
        decision, z_score = classify(
            mesh,
            ml_range,
            log_sigma,
            labels,
            scale=scale,
            second_opinion_range=second_range,
            second_opinion_scale=second_scale,
            dynamic_ids=dynamic_ids,
        )
        np.savez_compressed(
            args.out / f"{name}.npz",
            decision=decision,
            z_score=z_score,
            mesh_range_m=mesh,
            unidepth_range_m=ml_range,
            unidepth_scaled_range_m=ml_range * scale,
            unidepth_log_sigma=log_sigma,
            scale=np.asarray(scale, dtype=np.float32),
            depth_anything_range_m=second_range if second_range is not None else np.asarray([], dtype=np.float32),
            depth_anything_scale=np.asarray(second_scale if second_scale is not None else np.nan, dtype=np.float32),
        )
        image = np.asarray(Image.open(args.views / f"{name}.jpg").convert("RGB"), dtype=np.uint8)
        coloured = COLOURS[decision]
        overlay = np.round(0.48 * image + 0.52 * coloured).astype(np.uint8)
        Image.fromarray(overlay).save(args.out / f"{name}_decisions_overlay.jpg", quality=95)
        counts = {label: int((decision == value).sum()) for label, value in DECISIONS.items()}
        manifest.append({"view": name, "unidepth_scale": scale, "depth_anything_scale": second_scale, "counts": counts})
        print(f"[depth-compare] {name}: UniDepth scale={scale:.3f}, front blockers={counts['front_blocker']}")

    status = "ok" if report["ok"] else "implausible_scale_accepted_by_flag"
    (args.out / "manifest.json").write_text(json.dumps({**header, "status": status, "views": manifest}, indent=2))


if __name__ == "__main__":
    main()
