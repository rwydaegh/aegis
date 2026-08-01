"""Reproducible, static-only two-view feature-pose evidence.

This adapter deliberately does *not* write a camera pose.  It uses labelled
rectilinear crops to remove sky and movable classes before matching, then
records a calibrated relative-pose estimate with a separately supplied metric
baseline.  The resulting JSON is evidence for a later mesh-aware registration
stage, not an absolute world-space camera transform.

OpenCV is an optional runtime dependency.  Importing this module, resolving
labels, and validating a planned command do not import :mod:`cv2`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .multiview_pose import PinholeIntrinsics, PixelCorrespondences, RelativePose, estimate_relative_pose


# Labels are compared after whitespace/case normalization.  The set is
# intentionally conservative: false negatives only reduce pose evidence,
# whereas matching a moving truck to a static support mesh corrupts it.
DEFAULT_DYNAMIC_CLASS_NAMES = frozenset(
    {
        "bird",
        "ground animal",
        "person",
        "bicyclist",
        "motorcyclist",
        "other rider",
        "car",
        "caravan",
        "motorcycle",
        "on rails",
        "other vehicle",
        "trailer",
        "truck",
        "wheeled slow",
        "bus",
        "boat",
        "bicycle",
        "ego vehicle",
        "car mount",
        "van",
        "tram",
    }
)
SKY_CLASS_NAMES = frozenset({"sky"})


def _normalise_label(name: str) -> str:
    return " ".join(str(name).casefold().replace("_", " ").split())


@dataclass(frozen=True)
class LabelResolver:
    """Map integer entity IDs to names from an optional semantic manifest."""

    names: dict[int, str]

    @classmethod
    def from_manifest(cls, path: Path | None) -> "LabelResolver":
        """Read either baseline ``entity_id2label`` or SAM ``concept_id2label``.

        A missing manifest is valid only for a label map with no excluded IDs.
        It is useful for testing or a caller which supplies no dynamic/sky
        labels, but a production run should provide both manifests so class IDs
        are auditable in the output evidence.
        """
        if path is None:
            return cls({})
        try:
            document = json.loads(path.read_text())
        except OSError as exc:
            raise ValueError(f"cannot read semantics manifest: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON semantics manifest: {path}") from exc
        values = document.get("entity_id2label", document.get("concept_id2label"))
        if not isinstance(values, dict):
            raise ValueError(f"manifest needs entity_id2label or concept_id2label: {path}")
        try:
            return cls({int(key): _normalise_label(str(value)) for key, value in values.items()})
        except (TypeError, ValueError) as exc:
            raise ValueError(f"manifest label IDs must be integers: {path}") from exc

    def names_for(self, ids: np.ndarray) -> np.ndarray:
        """Resolve an integer map to object names, preserving unknown IDs."""
        label_ids = np.asarray(ids)
        if label_ids.ndim != 2 or not np.issubdtype(label_ids.dtype, np.integer):
            raise ValueError("entity labels must be a two-dimensional integer array")
        flat = label_ids.reshape(-1)
        names = np.fromiter((self.names.get(int(value), "<unknown>") for value in flat), dtype=object, count=len(flat))
        return names.reshape(label_ids.shape)

    def excluded_ids(
        self,
        *,
        dynamic_names: Sequence[str] = tuple(DEFAULT_DYNAMIC_CLASS_NAMES),
        sky_names: Sequence[str] = tuple(SKY_CLASS_NAMES),
    ) -> set[int]:
        excluded = {_normalise_label(name) for name in (*dynamic_names, *sky_names)}
        return {identifier for identifier, name in self.names.items() if name in excluded}


def static_label_mask(
    labels: np.ndarray,
    resolver: LabelResolver,
    *,
    dynamic_names: Sequence[str] = tuple(DEFAULT_DYNAMIC_CLASS_NAMES),
    sky_names: Sequence[str] = tuple(SKY_CLASS_NAMES),
) -> np.ndarray:
    """Return pixels eligible for static matching.

    Unknown labels remain eligible, because rejecting them wholesale can leave
    no façade features for a taxonomy with incomplete coverage.  The evidence
    record includes every excluded known class so this decision stays visible.
    """
    entity = np.asarray(labels)
    if entity.ndim != 2 or not np.issubdtype(entity.dtype, np.integer):
        raise ValueError("entity labels must be a two-dimensional integer array")
    excluded = resolver.excluded_ids(dynamic_names=dynamic_names, sky_names=sky_names)
    return ~np.isin(entity, list(excluded))


def correspondence_static_mask(
    points_a: np.ndarray,
    points_b: np.ndarray,
    labels_a: np.ndarray,
    labels_b: np.ndarray,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
) -> np.ndarray:
    """Sample two label masks at rounded SIFT centres and reject out-of-bounds.

    SIFT reports subpixel positions.  Nearest-pixel sampling is intentional for
    this binary gate; semantic boundary uncertainty is handled by later depth
    and mesh agreement, not hidden by morphologically expanding object masks.
    """
    first, second = np.asarray(points_a, dtype=float), np.asarray(points_b, dtype=float)
    if first.ndim != 2 or first.shape[1] != 2 or second.shape != first.shape:
        raise ValueError("points_a and points_b must have matching shape (N, 2)")
    if labels_a.shape != mask_a.shape or labels_b.shape != mask_b.shape:
        raise ValueError("labels and static masks must have matching shapes")

    def sample(points: np.ndarray, mask: np.ndarray) -> np.ndarray:
        x = np.rint(points[:, 0]).astype(np.int64)
        y = np.rint(points[:, 1]).astype(np.int64)
        inside = (x >= 0) & (x < mask.shape[1]) & (y >= 0) & (y < mask.shape[0])
        output = np.zeros(len(points), dtype=bool)
        output[inside] = mask[y[inside], x[inside]]
        return output

    return sample(first, mask_a) & sample(second, mask_b)


def _require_cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on optional environment
        raise RuntimeError(
            "OpenCV is required only to run refinement. Install it with "
            "`python -m pip install opencv-python` (or opencv-python-headless)."
        ) from exc
    return cv2


def _camera_matrix(intrinsics: PinholeIntrinsics) -> np.ndarray:
    return np.array(
        [[intrinsics.fx, 0.0, intrinsics.cx], [0.0, intrinsics.fy, intrinsics.cy], [0.0, 0.0, 1.0]], dtype=np.float64
    )


def _load_entity_labels(path: Path, image_shape: tuple[int, int]) -> np.ndarray:
    try:
        labels = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot load entity label map: {path}") from exc
    if labels.ndim != 2 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError(f"entity label map must be a 2D integer NPY: {path}")
    if labels.shape != image_shape:
        raise ValueError(f"entity label map shape {labels.shape} does not match image shape {image_shape}: {path}")
    return labels


@dataclass(frozen=True)
class RefinementEvidence:
    """Serialisable relative-pose evidence, explicitly not a source-pose edit."""

    source_images: tuple[str, str]
    source_entity_maps: tuple[str, str]
    source_manifests: tuple[str | None, str | None]
    candidate_matches: int
    static_matches: int
    homography_inliers: int
    essential_inliers: int
    relative_pose: RelativePose
    excluded_labels_a: list[str]
    excluded_labels_b: list[str]
    ratio_threshold: float
    ransac_threshold_px: float

    def as_json(self) -> dict[str, Any]:
        pose = self.relative_pose
        return {
            "schema": "semantic_twin.two_view_refinement.v1",
            "claim": "calibrated relative pose evidence only; not an absolute camera pose or source-pose update",
            "source_images": list(self.source_images),
            "source_entity_maps": list(self.source_entity_maps),
            "source_semantics_manifests": list(self.source_manifests),
            "static_filter": {
                "excluded_labels_a": self.excluded_labels_a,
                "excluded_labels_b": self.excluded_labels_b,
                "unknown_labels_retained": True,
            },
            "matching": {
                "detector": "OpenCV SIFT",
                "matcher": "BFMatcher L2 cross-check disabled, two-neighbour Lowe ratio test",
                "ratio_threshold": self.ratio_threshold,
                "candidate_matches": self.candidate_matches,
                "static_matches": self.static_matches,
            },
            "ransac": {
                "homography": {
                    "method": "OpenCV RANSAC",
                    "threshold_px": self.ransac_threshold_px,
                    "inliers": self.homography_inliers,
                },
                "essential": {
                    "method": "OpenCV RANSAC",
                    "threshold_px": self.ransac_threshold_px,
                    "inliers": self.essential_inliers,
                },
                "core_inliers": "essential only: homography remains a planar-scene diagnostic and is not intersected to avoid rejecting a valid facade-dominated pair",
            },
            "relative_pose_b_from_a": {
                "rotation": pose.rotation_b_from_a.tolist(),
                "translation_direction": pose.translation_direction_b.tolist(),
                "external_metric_baseline_m": pose.scale_from_prior,
                "translation_with_external_scale_m": None
                if pose.translation_b_from_a is None
                else pose.translation_b_from_a.tolist(),
                "cheirality_inliers": pose.cheirality_inliers,
                "core_source_match_indices": pose.source_indices.tolist(),
            },
            "limitations": [
                "Two-view geometry does not determine an absolute world pose.",
                "The external baseline supplies magnitude only, not a trusted world-frame direction.",
                "Dynamic masking is label-taxonomy dependent. Depth and support-mesh agreement remain required before semantic projection.",
            ],
        }


def _label_names_for_ids(resolver: LabelResolver, labels: np.ndarray) -> list[str]:
    used = {int(identifier) for identifier in np.unique(labels)}
    excluded = resolver.excluded_ids()
    return sorted(resolver.names[identifier] for identifier in used & excluded if identifier in resolver.names)


def refine_two_views(args: argparse.Namespace) -> RefinementEvidence:
    """Run optional-OpenCV SIFT matching and write non-destructive evidence."""
    validate_inputs(args)
    cv2 = _require_cv2()
    image_a = cv2.imread(str(args.image_a), cv2.IMREAD_GRAYSCALE)
    image_b = cv2.imread(str(args.image_b), cv2.IMREAD_GRAYSCALE)
    if image_a is None or image_b is None:
        raise ValueError("OpenCV could not decode one of the rectilinear images")
    labels_a = _load_entity_labels(args.labels_a, image_a.shape)
    labels_b = _load_entity_labels(args.labels_b, image_b.shape)
    resolver_a, resolver_b = (
        LabelResolver.from_manifest(args.semantics_a),
        LabelResolver.from_manifest(args.semantics_b),
    )
    valid_a, valid_b = static_label_mask(labels_a, resolver_a), static_label_mask(labels_b, resolver_b)

    sift = cv2.SIFT_create()
    keypoints_a, descriptors_a = sift.detectAndCompute(image_a, None)
    keypoints_b, descriptors_b = sift.detectAndCompute(image_b, None)
    if descriptors_a is None or descriptors_b is None:
        raise ValueError("SIFT found no descriptors in one of the images")
    pairs = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False).knnMatch(descriptors_a, descriptors_b, k=2)
    accepted = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < args.ratio * pair[1].distance]
    if len(accepted) < 8:
        raise ValueError(f"SIFT ratio test retained only {len(accepted)} matches, need at least 8")
    points_a = np.array([keypoints_a[match.queryIdx].pt for match in accepted], dtype=float)
    points_b = np.array([keypoints_b[match.trainIdx].pt for match in accepted], dtype=float)
    static = correspondence_static_mask(points_a, points_b, labels_a, labels_b, valid_a, valid_b)
    if int(static.sum()) < 8:
        raise ValueError(f"static semantic filtering retained only {int(static.sum())} matches, need at least 8")

    static_a, static_b = points_a[static], points_b[static]
    _, homography_mask = cv2.findHomography(static_a, static_b, cv2.RANSAC, args.ransac_threshold_px)
    camera_a, camera_b = _camera_matrix(args.intrinsics_a), _camera_matrix(args.intrinsics_b)
    # OpenCV's focal-length overload assumes shared intrinsics. Normalising the
    # pixels makes the essential RANSAC calibrated even when focal lengths differ.
    normalised_a = cv2.undistortPoints(static_a.reshape(-1, 1, 2), camera_a, None).reshape(-1, 2)
    normalised_b = cv2.undistortPoints(static_b.reshape(-1, 1, 2), camera_b, None).reshape(-1, 2)
    threshold_normalised = args.ransac_threshold_px / max(args.intrinsics_a.fx, args.intrinsics_a.fy)
    essential, essential_mask = cv2.findEssentialMat(
        normalised_a,
        normalised_b,
        focal=1.0,
        pp=(0.0, 0.0),
        method=cv2.RANSAC,
        prob=0.999,
        threshold=threshold_normalised,
    )
    if essential is None or essential_mask is None:
        raise ValueError("essential-matrix RANSAC failed")
    essential_inliers = essential_mask.reshape(-1).astype(bool)
    if int(essential_inliers.sum()) < 8:
        raise ValueError(f"essential RANSAC retained only {int(essential_inliers.sum())} matches, need at least 8")

    # Core is intentionally called with the essential-RANSAC inlier mask.  It
    # handles calibrated bearings, its own eight-point re-estimation, and
    # cheirality selection. Homography evidence is recorded but not intersected.
    matches = PixelCorrespondences(static_a, static_b)
    relative = estimate_relative_pose(
        matches,
        args.intrinsics_a,
        args.intrinsics_b,
        robust_filter=lambda _: essential_inliers,
        scale_from_prior=args.baseline_m,
    )
    homography_inliers = 0 if homography_mask is None else int(homography_mask.reshape(-1).astype(bool).sum())
    evidence = RefinementEvidence(
        (str(args.image_a), str(args.image_b)),
        (str(args.labels_a), str(args.labels_b)),
        (
            None if args.semantics_a is None else str(args.semantics_a),
            None if args.semantics_b is None else str(args.semantics_b),
        ),
        len(accepted),
        int(static.sum()),
        homography_inliers,
        int(essential_inliers.sum()),
        relative,
        _label_names_for_ids(resolver_a, labels_a),
        _label_names_for_ids(resolver_b, labels_b),
        args.ratio,
        args.ransac_threshold_px,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence.as_json(), indent=2) + "\n")
    return evidence


def validate_inputs(args: argparse.Namespace) -> None:
    """Fail before OpenCV loads if paths, intrinsics, or scale are invalid."""
    for name in ("image_a", "image_b", "labels_a", "labels_b"):
        path = getattr(args, name)
        if not path.is_file():
            raise ValueError(f"--{name.replace('_', '-')} must name an existing file: {path}")
    for name in ("semantics_a", "semantics_b"):
        path = getattr(args, name)
        if path is not None and not path.is_file():
            raise ValueError(f"--{name.replace('_', '-')} must name an existing file when supplied: {path}")
    if not 0.0 < args.ratio < 1.0:
        raise ValueError("--ratio must be strictly between 0 and 1")
    if args.ransac_threshold_px <= 0.0:
        raise ValueError("--ransac-threshold-px must be positive")
    if args.baseline_m <= 0.0:
        raise ValueError("--baseline-m must be positive")


def _intrinsics_from_namespace(args: argparse.Namespace, suffix: str) -> PinholeIntrinsics:
    return PinholeIntrinsics(
        getattr(args, f"fx_{suffix}"),
        getattr(args, f"fy_{suffix}"),
        getattr(args, f"cx_{suffix}"),
        getattr(args, f"cy_{suffix}"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-a", type=Path, required=True, help="rectilinear image for camera A")
    parser.add_argument("--image-b", type=Path, required=True, help="rectilinear image for camera B")
    parser.add_argument("--labels-a", type=Path, required=True, help="2D integer NPY entity labels aligned to image A")
    parser.add_argument("--labels-b", type=Path, required=True, help="2D integer NPY entity labels aligned to image B")
    parser.add_argument("--semantics-a", type=Path, help="optional entity/concept ID manifest for image A")
    parser.add_argument("--semantics-b", type=Path, help="optional entity/concept ID manifest for image B")
    for suffix in ("a", "b"):
        parser.add_argument(f"--fx-{suffix}", type=float, required=True)
        parser.add_argument(f"--fy-{suffix}", type=float, required=True)
        parser.add_argument(f"--cx-{suffix}", type=float, required=True)
        parser.add_argument(f"--cy-{suffix}", type=float, required=True)
    parser.add_argument(
        "--baseline-m", type=float, required=True, help="external metric camera separation prior in metres"
    )
    parser.add_argument("--ratio", type=float, default=0.72, help="Lowe SIFT ratio threshold")
    parser.add_argument("--ransac-threshold-px", type=float, default=1.5)
    parser.add_argument("--out", type=Path, required=True, help="JSON evidence output, never a pose file")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.intrinsics_a = _intrinsics_from_namespace(args, "a")
    args.intrinsics_b = _intrinsics_from_namespace(args, "b")
    validate_inputs(args)
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    evidence = refine_two_views(args)
    print(f"[two-view-refine] {evidence.essential_inliers} essential inliers -> {args.out}")


if __name__ == "__main__":
    main()
