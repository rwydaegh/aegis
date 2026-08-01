"""Compare mesh first-hit range against UniDepth and label provisional blockers.

The output is intentionally conservative. A high residual is an *evidence
conflict*, not automatic geometry creation.  Only a nearer ML surface receives
the ``front_blocker`` decision, and that decision remains view-local until it
is corroborated by distinct panorama centres.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image

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
    log_error: np.ndarray,
    labels: np.ndarray,
    *,
    static_ids: set[int] = STATIC_CALIBRATION_IDS,
) -> float:
    """Fit only one global scale using reliable static support in a crop."""
    calibration = (
        np.isfinite(mesh_range)
        & np.isfinite(ml_range)
        & (mesh_range > 0.0)
        & (ml_range > 0.0)
        & np.isin(labels, list(static_ids))
        & (log_error <= np.nanpercentile(log_error, 60.0))
    )
    if calibration.sum() < 100:
        raise ValueError("not enough reliable static pixels to calibrate UniDepth range")
    return float(np.exp(np.median(np.log(mesh_range[calibration]) - np.log(ml_range[calibration]))))


def classify(
    mesh_range: np.ndarray,
    ml_range: np.ndarray,
    log_error: np.ndarray,
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
    sigma_ml = np.asarray(log_error, dtype=np.float32)
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
    return parser.parse_args()


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    static_ids = STATIC_CALIBRATION_IDS
    dynamic_ids = OBJECT_IDS
    if args.semantics_json is not None:
        entity_id2label = json.loads(args.semantics_json.read_text())["entity_id2label"]
        label2id = {name.casefold(): int(class_id) for class_id, name in entity_id2label.items()}
        static_ids = {label2id[name] for name in STATIC_CALIBRATION_LABELS if name in label2id}
        dynamic_ids = {label2id[name] for name in DYNAMIC_OBJECT_LABELS if name in label2id}
        if not static_ids:
            raise ValueError("segmentation manifest has no static calibration classes")
    manifest = []
    for yaw in args.yaws:
        name = f"h+00_{yaw:03d}"
        mesh = np.load(args.mesh_depth / f"{name}.npz")["range_m"]
        depth = np.load(args.unidepth / f"{name}.npz")
        labels = np.load(args.sam_labels / f"{name}_labels.npy")
        try:
            scale = fit_log_scale(
                mesh,
                depth["range_m"],
                depth["log_error"],
                labels,
                static_ids=static_ids,
            )
        except ValueError as error:
            manifest.append({"view": name, "status": "uncalibrated", "reason": str(error)})
            print(f"[depth-compare] {name}: uncalibrated ({error})")
            continue
        second_range = None
        second_scale = None
        if args.depth_anything is not None:
            second_range = np.load(args.depth_anything / f"{name}.npz")["range_m"]
            second_scale = fit_log_scale(
                mesh,
                second_range,
                depth["log_error"],
                labels,
                static_ids=static_ids,
            )
        decision, z_score = classify(
            mesh,
            depth["range_m"],
            depth["log_error"],
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
            unidepth_range_m=depth["range_m"],
            unidepth_scaled_range_m=depth["range_m"] * scale,
            unidepth_log_error=depth["log_error"],
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
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "decisions": DECISIONS,
                "initial_mesh_log_sigma": 0.35,
                "static_calibration_ids": sorted(static_ids),
                "dynamic_object_ids": sorted(dynamic_ids),
                "front_blocker": "ML predicts a closer surface than the tile first hit, at z >= 3",
                "mesh_or_pose_blocker": "tile first hit is implausibly closer than ML depth, at z <= -3",
                "dynamic_object": "SAM person/vehicle/table mask, separately reconstructed as a dynamic layer",
                "views": manifest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
