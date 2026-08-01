"""Dependency-light dynamic-body artifacts for SAM 3D Body reconstruction.

SAM 3D Body reconstructs a person in a rectilinear camera frame.  This module
keeps that reconstruction distinct from its ENU placement: humans are transient
geometry, never evidence that is baked into the static semantic atlas.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


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
