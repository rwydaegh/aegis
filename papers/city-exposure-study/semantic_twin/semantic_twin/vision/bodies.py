"""Dependency-light dynamic-body artifacts for SAM 3D Body reconstruction.

SAM 3D Body reconstructs a person in a rectilinear camera frame.  This module
keeps that reconstruction distinct from its ENU placement: humans are transient
geometry, never evidence that is baked into the static semantic atlas.

It also holds the two ends of the body pipeline that are pure arithmetic and can
therefore be tested without a GPU: turning a segmentation label map into person
instances to reconstruct, and turning one reconstruction plus the recovered
camera pose into a placement with its uncertainty.  The model call itself lives
in ``infer_sam3_body.py`` and the runner in ``build_dynamic_bodies.py``.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage

from ..pano_geometry import view_basis


def _points(value: np.ndarray, name: str) -> np.ndarray:
    points = np.asarray(value, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points):
        raise ValueError(f"{name} must have shape (N, 3) with N > 0")
    if not np.all(np.isfinite(points)):
        raise ValueError(f"{name} must contain finite values")
    return points


def _vector(value: np.ndarray, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be one finite three-vector")
    return vector


@dataclass(frozen=True)
class CameraBasisENU:
    """World basis for SAM camera coordinates: right, forward and up.

    SAM camera vertices use ``x`` right, ``y`` down and ``z`` forward.  ENU is
    X east, Y north, Z up.  The basis vectors are supplied by the calibrated
    rectilinear crop, rather than inferred from an equirectangular image.
    """

    right_enu: np.ndarray
    forward_enu: np.ndarray
    up_enu: np.ndarray

    def __post_init__(self) -> None:
        right = _vector(self.right_enu, "right_enu")
        forward = _vector(self.forward_enu, "forward_enu")
        up = _vector(self.up_enu, "up_enu")
        matrix = np.column_stack((right, forward, up))
        if not np.allclose(matrix.T @ matrix, np.eye(3), atol=1e-5):
            raise ValueError("camera basis must be orthonormal")
        if np.linalg.det(matrix) <= 0.0:
            raise ValueError("camera basis must be right-handed")
        object.__setattr__(self, "right_enu", right)
        object.__setattr__(self, "forward_enu", forward)
        object.__setattr__(self, "up_enu", up)

    @property
    def matrix(self) -> np.ndarray:
        return np.column_stack((self.right_enu, self.forward_enu, self.up_enu))


@dataclass(frozen=True)
class PersonInstance:
    """One person-shaped connected component of a crop's label map.

    The mask and box are what SAM 3D Body is conditioned on, so they are kept
    exactly as the segmenter drew them rather than dilated or squared off.
    ``mean_confidence`` is the segmenter's own per-pixel confidence over the
    component, which is what decides whether the crop is worth a GPU call.
    """

    instance_id: str
    view_id: str
    mask: np.ndarray
    bbox_xyxy: tuple[int, int, int, int]
    pixel_count: int
    mean_confidence: float

    def __post_init__(self) -> None:
        mask = np.asarray(self.mask, dtype=bool)
        if mask.ndim != 2 or not mask.any():
            raise ValueError("a person instance needs a nonempty 2D mask")
        left, top, right, bottom = self.bbox_xyxy
        if not (0 <= left < right <= mask.shape[1] and 0 <= top < bottom <= mask.shape[0]):
            raise ValueError("bbox_xyxy must be a nonempty box inside the mask")
        object.__setattr__(self, "mask", mask)


def person_instances(
    labels: np.ndarray,
    person_class_ids: set[int],
    *,
    view_id: str,
    confidence: np.ndarray | None = None,
    min_pixels: int = 600,
    min_height_px: int = 48,
) -> list[PersonInstance]:
    """Split the person classes of one label map into instances, largest first.

    Semantic segmentation gives no instances, so connectivity supplies them.
    Two people who overlap in the image merge into one component, which SAM 3D
    Body then resolves itself from the box: it detects and reconstructs each
    person inside the crop it is given.  The size floors exist because a person
    a few pixels tall carries no recoverable pose and would spend a GPU call to
    produce noise.
    """
    labels = np.asarray(labels)
    if labels.ndim != 2:
        raise ValueError("labels must be a 2D label map")
    if confidence is not None:
        confidence = np.asarray(confidence, dtype=np.float64)
        if confidence.shape != labels.shape:
            raise ValueError("confidence must match the label resolution")
    if min_pixels < 1 or min_height_px < 1:
        raise ValueError("the instance size floors must be positive")

    people = np.isin(labels, list(person_class_ids))
    components, count = ndimage.label(people)
    instances: list[PersonInstance] = []
    for index in range(1, count + 1):
        mask = components == index
        pixels = int(mask.sum())
        if pixels < min_pixels:
            continue
        rows, columns = np.nonzero(mask)
        top, bottom = int(rows.min()), int(rows.max()) + 1
        if bottom - top < min_height_px:
            continue
        left, right = int(columns.min()), int(columns.max()) + 1
        instances.append(
            PersonInstance(
                instance_id="",
                view_id=view_id,
                mask=mask,
                bbox_xyxy=(left, top, right, bottom),
                pixel_count=pixels,
                mean_confidence=float(confidence[mask].mean()) if confidence is not None else 1.0,
            )
        )
    instances.sort(key=lambda instance: instance.pixel_count, reverse=True)
    return [
        PersonInstance(
            instance_id=f"{view_id}_person_{rank:03d}",
            view_id=instance.view_id,
            mask=instance.mask,
            bbox_xyxy=instance.bbox_xyxy,
            pixel_count=instance.pixel_count,
            mean_confidence=instance.mean_confidence,
        )
        for rank, instance in enumerate(instances)
    ]


def camera_basis_from_pose(rotation: np.ndarray, yaw_deg: float, pitch_deg: float = 0.0) -> CameraBasisENU:
    """ENU basis of one rectilinear crop of a panorama with a recovered pose.

    The crop axes come from :func:`pano_geometry.view_basis`, which is the same
    convention the depth buffer and the surface cutter use, so a body and the
    walls behind it land in one frame rather than in two that nearly agree.
    """
    rotation = np.asarray(rotation, dtype=np.float64)
    if rotation.shape != (3, 3) or not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-6):
        raise ValueError("rotation must be an orthonormal 3x3 matrix")
    right, forward, up = view_basis(yaw_deg, pitch_deg)
    return CameraBasisENU(rotation @ right, rotation @ forward, rotation @ up)


def pinhole_intrinsics(width: int, height: int, fov_deg: float = 90.0) -> np.ndarray:
    """Exact intrinsics of one perspective crop, so no FOV has to be estimated."""
    if width < 1 or height < 1 or not 0.0 < fov_deg < 180.0:
        raise ValueError("a crop needs positive dimensions and a field of view in (0, 180)")
    focal = width / (2.0 * math.tan(math.radians(fov_deg) / 2.0))
    return np.array([[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]], dtype=np.float64)


def enu_to_camera(points: np.ndarray, origin_enu_m: np.ndarray, basis: CameraBasisENU) -> np.ndarray:
    """Inverse of the placement transform, back into SAM camera coordinates.

    Reprojecting through this rather than through the untransformed camera-frame
    prediction is what makes the reprojection residual a test of the placement.
    Projecting the raw prediction only ever re-tests the intrinsics.
    """
    points = _points(points, "points")
    offset = points - _vector(origin_enu_m, "origin_enu_m")
    return np.stack([offset @ basis.right_enu, -(offset @ basis.up_enu), offset @ basis.forward_enu], axis=1)


def project_camera_points(points: np.ndarray, intrinsics: np.ndarray) -> np.ndarray:
    """Project SAM camera-frame points, x right and y down, into pixels."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    if np.any(points[:, 2] <= 0.0):
        raise ValueError("points must lie strictly in front of the camera")
    return (points @ np.asarray(intrinsics, dtype=np.float64).T)[:, :2] / points[:, 2:3]


# A range correction outside this band is not a correction, it is a different
# person.  SAM 3D Body predicts a metric translation of its own, so when the
# depth evidence disagrees by more than this the safe move is to keep the
# model's own number and record the conflict.
PLAUSIBLE_RANGE_CORRECTION = (0.5, 2.0)


def range_corrected_translation(
    pred_cam_t_m: np.ndarray,
    evidence_range_m: float | None,
    *,
    band: tuple[float, float] = PLAUSIBLE_RANGE_CORRECTION,
) -> tuple[np.ndarray, str, float | None]:
    """Rescale the model translation onto an independently measured range.

    The bearing to a person is well determined: it is the box centre through
    known intrinsics.  The range is the weak axis, because it comes from the
    apparent size of a body whose real size is unknown.  So the correction is
    radial only, which moves the body along the ray it was seen on and never
    sideways.  Returns the translation, the provenance, and the metric
    disagreement between the model and the evidence.
    """
    translation = _vector(pred_cam_t_m, "pred_cam_t_m")
    model_range = float(np.linalg.norm(translation))
    if model_range <= 0.0:
        raise ValueError("pred_cam_t_m must have a positive range")
    if evidence_range_m is None or not np.isfinite(evidence_range_m) or evidence_range_m <= 0.0:
        return translation, "sam_metric_translation", None
    ratio = float(evidence_range_m) / model_range
    disagreement = abs(float(evidence_range_m) - model_range)
    if not band[0] <= ratio <= band[1]:
        return translation, "sam_metric_translation_evidence_implausible", disagreement
    return translation * ratio, "range_corrected_along_bearing", disagreement


@dataclass(frozen=True)
class BodyUncertainty:
    """Explicit uncertainty fields in metres or pixels, never hidden defaults."""

    reconstruction_std_m: float | None = None
    camera_pose_std_m: float | None = None
    floor_std_m: float | None = None
    reprojection_rmse_px: float | None = None
    depth_mesh_disagreement_m: float | None = None

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value is not None and (not np.isfinite(value) or value < 0.0):
                raise ValueError(f"{name} must be a finite non-negative number or None")


@dataclass(frozen=True)
class DynamicBodyArtifact:
    """Raw and ENU-placed SAM 3D Body result, serializable without Blender.

    ``vertices_camera_raw_m`` is exactly the model mesh.  ``vertices_enu_m``
    is the camera-translated and world-transformed result, optionally shifted
    vertically so its lowest vertex meets a ray-cast support-floor point.  A
    floor shift deliberately changes only Z: camera-ray placement retains the
    measured horizontal location and heading.
    """

    body_id: str
    source_view_id: str
    vertices_camera_raw_m: np.ndarray
    faces: np.ndarray
    keypoints_camera_raw_m: np.ndarray
    pred_cam_t_m: np.ndarray
    camera_origin_enu_m: np.ndarray
    camera_basis_enu: CameraBasisENU
    vertices_enu_unfloored_m: np.ndarray
    keypoints_enu_unfloored_m: np.ndarray
    vertices_enu_m: np.ndarray
    keypoints_enu_m: np.ndarray
    floor_point_enu_m: np.ndarray | None
    floor_shift_enu_m: np.ndarray
    placement_provenance: str
    uncertainty: BodyUncertainty

    def __post_init__(self) -> None:
        if not self.body_id or not self.source_view_id:
            raise ValueError("body_id and source_view_id must be nonempty")
        vertices = _points(self.vertices_camera_raw_m, "vertices_camera_raw_m")
        faces = np.asarray(self.faces, dtype=np.int64)
        if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces):
            raise ValueError("faces must have shape (M, 3) with M > 0")
        if np.any(faces < 0) or np.any(faces >= len(vertices)):
            raise ValueError("faces must index vertices_camera_raw_m")
        _points(self.keypoints_camera_raw_m, "keypoints_camera_raw_m")
        for name in (
            "pred_cam_t_m",
            "camera_origin_enu_m",
            "floor_shift_enu_m",
        ):
            _vector(getattr(self, name), name)
        for name in (
            "vertices_enu_unfloored_m",
            "keypoints_enu_unfloored_m",
            "vertices_enu_m",
            "keypoints_enu_m",
        ):
            _points(getattr(self, name), name)
        if self.floor_point_enu_m is not None:
            _vector(self.floor_point_enu_m, "floor_point_enu_m")
        if self.placement_provenance not in {"camera_transform_only", "support_floor_vertical_alignment"}:
            raise ValueError("placement_provenance is not recognized")

    def save(self, path: str | Path) -> None:
        """Write compressed portable geometry and JSON metadata to one NPZ."""
        destination = Path(path)
        metadata = {
            "body_id": self.body_id,
            "source_view_id": self.source_view_id,
            "placement_provenance": self.placement_provenance,
            "uncertainty": asdict(self.uncertainty),
        }
        np.savez_compressed(
            destination,
            vertices_camera_raw_m=self.vertices_camera_raw_m,
            faces=self.faces,
            keypoints_camera_raw_m=self.keypoints_camera_raw_m,
            pred_cam_t_m=self.pred_cam_t_m,
            camera_origin_enu_m=self.camera_origin_enu_m,
            camera_right_enu=self.camera_basis_enu.right_enu,
            camera_forward_enu=self.camera_basis_enu.forward_enu,
            camera_up_enu=self.camera_basis_enu.up_enu,
            vertices_enu_unfloored_m=self.vertices_enu_unfloored_m,
            keypoints_enu_unfloored_m=self.keypoints_enu_unfloored_m,
            vertices_enu_m=self.vertices_enu_m,
            keypoints_enu_m=self.keypoints_enu_m,
            floor_point_enu_m=np.array([]) if self.floor_point_enu_m is None else self.floor_point_enu_m,
            floor_shift_enu_m=self.floor_shift_enu_m,
            metadata_json=np.array(json.dumps(metadata, sort_keys=True)),
        )

    @classmethod
    def load(cls, path: str | Path) -> DynamicBodyArtifact:
        """Read an artifact written by :meth:`save`."""
        with np.load(Path(path), allow_pickle=False) as archive:
            metadata = json.loads(str(archive["metadata_json"].item()))
            floor = archive["floor_point_enu_m"]
            return cls(
                body_id=metadata["body_id"],
                source_view_id=metadata["source_view_id"],
                vertices_camera_raw_m=archive["vertices_camera_raw_m"],
                faces=archive["faces"],
                keypoints_camera_raw_m=archive["keypoints_camera_raw_m"],
                pred_cam_t_m=archive["pred_cam_t_m"],
                camera_origin_enu_m=archive["camera_origin_enu_m"],
                camera_basis_enu=CameraBasisENU(
                    archive["camera_right_enu"], archive["camera_forward_enu"], archive["camera_up_enu"]
                ),
                vertices_enu_unfloored_m=archive["vertices_enu_unfloored_m"],
                keypoints_enu_unfloored_m=archive["keypoints_enu_unfloored_m"],
                vertices_enu_m=archive["vertices_enu_m"],
                keypoints_enu_m=archive["keypoints_enu_m"],
                floor_point_enu_m=None if not len(floor) else floor,
                floor_shift_enu_m=archive["floor_shift_enu_m"],
                placement_provenance=metadata["placement_provenance"],
                uncertainty=BodyUncertainty(**metadata["uncertainty"]),
            )


def build_dynamic_body_artifact(
    *,
    body_id: str,
    source_view_id: str,
    vertices_camera_raw_m: np.ndarray,
    faces: np.ndarray,
    keypoints_camera_raw_m: np.ndarray,
    pred_cam_t_m: np.ndarray,
    camera_origin_enu_m: np.ndarray,
    camera_basis_enu: CameraBasisENU,
    support_floor_point_enu_m: np.ndarray | None = None,
    uncertainty: BodyUncertainty = BodyUncertainty(),
) -> DynamicBodyArtifact:
    """Convert one calibrated SAM 3D Body prediction to an explicit ENU artifact.

    The raw MHR output is first shifted by ``pred_cam_t_m``.  Camera coordinates
    are then mapped as ``x*right - y*up + z*forward`` to honour the image-space
    down axis.  ``support_floor_point_enu_m`` is optional evidence from a mesh
    ray hit.  If supplied, the final output gets a vertical-only translation
    that aligns the lowest reconstructed vertex with its Z coordinate.
    """
    vertices = _points(vertices_camera_raw_m, "vertices_camera_raw_m")
    keypoints = _points(keypoints_camera_raw_m, "keypoints_camera_raw_m")
    cam_t = _vector(pred_cam_t_m, "pred_cam_t_m")
    origin = _vector(camera_origin_enu_m, "camera_origin_enu_m")
    translated_vertices = vertices + cam_t
    translated_keypoints = keypoints + cam_t
    basis = camera_basis_enu

    def to_enu(camera_points: np.ndarray) -> np.ndarray:
        return (
            origin
            + camera_points[:, 0:1] * basis.right_enu
            - camera_points[:, 1:2] * basis.up_enu
            + camera_points[:, 2:3] * basis.forward_enu
        )

    unfloored_vertices = to_enu(translated_vertices)
    unfloored_keypoints = to_enu(translated_keypoints)
    if support_floor_point_enu_m is None:
        floor_point = None
        shift = np.zeros(3, dtype=np.float64)
        provenance = "camera_transform_only"
    else:
        floor_point = _vector(support_floor_point_enu_m, "support_floor_point_enu_m")
        shift = np.array((0.0, 0.0, floor_point[2] - np.min(unfloored_vertices[:, 2])))
        provenance = "support_floor_vertical_alignment"
    return DynamicBodyArtifact(
        body_id=body_id,
        source_view_id=source_view_id,
        vertices_camera_raw_m=vertices,
        faces=faces,
        keypoints_camera_raw_m=keypoints,
        pred_cam_t_m=cam_t,
        camera_origin_enu_m=origin,
        camera_basis_enu=basis,
        vertices_enu_unfloored_m=unfloored_vertices,
        keypoints_enu_unfloored_m=unfloored_keypoints,
        vertices_enu_m=unfloored_vertices + shift,
        keypoints_enu_m=unfloored_keypoints + shift,
        floor_point_enu_m=floor_point,
        floor_shift_enu_m=shift,
        placement_provenance=provenance,
        uncertainty=uncertainty,
    )
