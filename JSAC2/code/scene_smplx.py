"""SMPL-X parametric body adapter for the JSAC2 Kirchhoff pipeline.

Replaces the rigid `Thelonious.stl` phantom in `pose_sweep.py` /
`animate_pose.py` with the SMPL-X parametric body so that the
`theta -> mesh -> channel` pipeline is differentiable in pose.

Two entry points:

- `make_body_smplx(theta_axis_angle, world_centroid, betas, gender)`
  takes a (22, 3) or (66,) axis-angle pose and returns a `Body` with
  the same interface (`mesh`, `centroids`, `normals`, `areas`,
  `intersector`) as the existing `kirchhoff.Body`.

- `make_body_yaw_smplx(yaw_deg, world_centroid, baseline_pose)` is the
  drop-in replacement for `pose_sweep.make_body(yaw, ...)`. It applies
  `yaw_deg` at spine2 (joint index 6) on top of a hardcoded
  "phone-holding" baseline pose.

SMPL-X is in Y-up coordinates. The JSAC2 scene is Z-up. We rotate the
posed mesh by `R = rot_x(-90 deg)` so SMPL-Y maps to world-Z, then
translate the (origin-centred) SMPL-X mesh so its centroid lands at
`world_centroid`. We additionally yaw the body by 180 deg around world-Z
so the user faces the BS (the BS is at (0,0,8) and the body at
(30,0,1.2), so the user must face the -x direction to look at the BS).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import trimesh

from JSAC2.code.kirchhoff import Body


# Joint indices in the (22, 3) axis-angle array.
# joint 0 = global_orient (pelvis); joints 1..21 = body_pose.
JOINT_PELVIS = 0
JOINT_SPINE1 = 3
JOINT_SPINE2 = 6  # the prompt's "L4-L5 spine joint" — we use this for torso yaw
JOINT_SPINE3 = 9
JOINT_NECK = 12
JOINT_HEAD = 15
JOINT_L_SHOULDER = 16
JOINT_R_SHOULDER = 17
JOINT_L_ELBOW = 18
JOINT_R_ELBOW = 19


def default_baseline_pose() -> np.ndarray:
    """Hardcoded "user holding phone in front of chest, slight forward lean".

    Returns axis-angle pose of shape (22, 3) in SMPL-X local-joint
    convention (joint 0 = global_orient, joints 1..21 = body_pose).

    Empirical verification (with neutral betas, no global yaw) places the
    wrists at roughly `[+/-0.19, -0.07, -0.28]` in SMPL-X frame:
    upper-torso height, ~28 cm in front of the chest plane. The torso
    has a slight forward lean (~13 deg total at spine1+spine2).
    """
    pose = np.zeros((22, 3), dtype=np.float64)
    # Mild forward torso lean: ~8 deg at spine1 + ~5 deg at spine2.
    pose[JOINT_SPINE1] = [np.deg2rad(8.0), 0.0, 0.0]
    pose[JOINT_SPINE2] = [np.deg2rad(5.0), 0.0, 0.0]
    # Shoulders: rotate around local Z by +/-70 deg to bring arms down.
    pose[JOINT_L_SHOULDER] = [0.0, 0.0, -np.deg2rad(70.0)]
    pose[JOINT_R_SHOULDER] = [0.0, 0.0, +np.deg2rad(70.0)]
    # Elbows: flex around local Y by +/-100 deg to bring forearms forward.
    pose[JOINT_L_ELBOW] = [0.0, +np.deg2rad(100.0), 0.0]
    pose[JOINT_R_ELBOW] = [0.0, -np.deg2rad(100.0), 0.0]
    return pose


@lru_cache(maxsize=4)
def _load_smplx_model(gender: str):
    """Load (or fetch from cache) an SMPL-X torch model + faces.

    Cached so that repeated `make_body_smplx` calls in a sweep don't pay
    the ~1 s SMPL-X PyTorch model construction cost on every call.
    """
    try:
        import smplx as smplx_pkg
    except ImportError as err:
        raise ImportError(
            "smplx is required for the SMPL-X body adapter. "
            "Install with: pip install aegis[body]"
        ) from err

    from pathlib import Path

    model_root = Path.home() / ".aegis" / "models"
    npz = model_root / "smplx" / f"SMPLX_{gender.upper()}.npz"
    if not npz.exists():
        raise FileNotFoundError(
            f"SMPL-X model file not found at {npz}. "
            "Register at https://smpl-x.is.tue.mpg.de/, download "
            "models_smplx_v1_1.zip, then run "
            "`python scripts/fetch_smplx.py <path/to/zip>` in the AEGIS repo."
        )
    model = smplx_pkg.create(
        str(model_root),
        model_type="smplx",
        gender=gender,
        use_pca=False,
        flat_hand_mean=True,
    )
    faces = np.asarray(model.faces, dtype=np.int64)
    return model, faces


def _smplx_to_world_rotation() -> np.ndarray:
    """3x3 matrix mapping SMPL-X canonical (Y-up, body faces +z) to JSAC2 scene.

    World convention: Z-up, body at x=+30 facing the BS at lower x. So we
    need SMPL +y -> world +z (vertical) and SMPL +z (body-forward) -> world -x
    (toward BS). With body facing -x, the body's left arm extends to -y and
    right arm to +y; the chest-front side is at -x.
    """
    Rx = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float64,
    )  # rot_x(-90 deg): SMPL +y -> world +z, SMPL +z -> world -y
    Rz = np.array(
        [
            [0.0, 1.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )  # rot_z(-90 deg): world +y -> world -x, sending body-forward to -x
    return Rz @ Rx


def _pose_smplx_vertices(
    theta_axis_angle: np.ndarray, betas: np.ndarray, gender: str
) -> tuple[np.ndarray, np.ndarray]:
    """Run SMPL-X forward, return `(vertices_world_frame, faces)`.

    `theta_axis_angle` is shape (22, 3) or (66,). `betas` is (10,) or
    larger (only first 10 entries are used). The returned vertices are
    rotated from SMPL-X (Y-up) to the JSAC2 world frame (Z-up, body
    facing -x toward the BS) but NOT yet translated to the world
    centroid — the caller does that.
    """
    import torch

    theta = np.asarray(theta_axis_angle, dtype=np.float64).reshape(-1)
    if theta.size != 66:
        raise ValueError(
            f"theta_axis_angle must have 66 entries (22 joints x 3); got {theta.size}"
        )
    if betas is None:
        betas = np.zeros(10, dtype=np.float64)
    betas = np.asarray(betas, dtype=np.float64).reshape(-1)
    if betas.size < 10:
        raise ValueError(f"betas must have >=10 entries; got {betas.size}")
    betas = betas[:10]

    model, faces = _load_smplx_model(gender)

    global_orient = torch.tensor(theta[:3], dtype=torch.float32).unsqueeze(0)
    body_pose = torch.tensor(theta[3:66], dtype=torch.float32).unsqueeze(0)
    betas_t = torch.tensor(betas, dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        out = model(
            global_orient=global_orient,
            body_pose=body_pose,
            betas=betas_t,
            return_verts=True,
        )
    verts_smplx = out.vertices[0].detach().cpu().numpy().astype(np.float64)

    # Rotate SMPL-X (Y-up, facing -z) to JSAC2 world (Z-up, facing -x).
    R = _smplx_to_world_rotation()
    verts_world = verts_smplx @ R.T
    return verts_world, faces


def make_body_smplx(
    theta_axis_angle: np.ndarray,
    world_centroid: np.ndarray,
    betas: np.ndarray | None = None,
    gender: str = "neutral",
    face_azimuth_rad: float | None = None,
    *,
    verbose: bool = False,
) -> Body:
    """Build a kirchhoff `Body` from SMPL-X pose parameters.

    Parameters
    ----------
    theta_axis_angle : (22, 3) or (66,) array
        SMPL-X axis-angle pose. theta[0] = global_orient (pelvis),
        theta[1..21] = body_pose joints in SMPL-X canonical order.
    world_centroid : (3,) array
        Where to place the SMPL-X mesh centroid in JSAC2 world coords.
    betas : (10,) array or None
        SMPL-X shape coefficients. None -> zeros (mean shape).
    gender : "neutral" | "male" | "female"
    verbose : bool
        If True, print mesh face count and centroid.

    Returns
    -------
    Body
        With `mesh` (trimesh.Trimesh, ~10475 verts, ~20908 faces),
        `centroids`, `normals`, `areas`, `intersector` populated as in
        the existing kirchhoff Body interface.
    """
    verts, faces = _pose_smplx_vertices(theta_axis_angle, betas, gender)
    # Default rotation puts the body facing world -x (azimuth = pi).
    # If face_azimuth_rad is given, rotate about world +Z by
    # (face_azimuth_rad - pi) so the chest-front aims at that azimuth.
    if face_azimuth_rad is not None:
        delta_yaw = float(face_azimuth_rad) - np.pi
        c, s = np.cos(delta_yaw), np.sin(delta_yaw)
        Rz = np.array([[c, -s, 0.0],
                       [s,  c, 0.0],
                       [0.0, 0.0, 1.0]], dtype=np.float64)
        verts = verts @ Rz.T
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    delta = np.asarray(world_centroid, dtype=np.float64) - mesh.centroid
    mesh.apply_translation(delta)
    if verbose:
        print(
            f"  SMPL-X body: {len(mesh.faces)} faces, "
            f"{len(mesh.vertices)} verts, centroid={mesh.centroid}"
        )
    return Body(mesh)


def make_body_yaw_smplx(
    yaw_deg: float,
    world_centroid: np.ndarray,
    baseline_pose: np.ndarray | None = None,
    betas: np.ndarray | None = None,
    gender: str = "neutral",
    *,
    verbose: bool = False,
) -> Body:
    """Drop-in replacement for `pose_sweep.make_body`.

    Applies a torso yaw of `yaw_deg` degrees at the spine2 joint
    (SMPL-X joint index 6) on top of `baseline_pose`. The yaw rotation
    in the SMPL-X joint-local frame is around the local +Y axis, which
    after our world-frame rotation maps to a rotation around world-Z
    of the upper torso + arms + head relative to the pelvis + hips.
    """
    if baseline_pose is None:
        baseline_pose = default_baseline_pose()
    pose = np.asarray(baseline_pose, dtype=np.float64).copy().reshape(22, 3)
    # Add yaw at spine2: the local +Y axis is the natural vertical /
    # twist axis in SMPL-X joint frames.
    pose[JOINT_SPINE2, 1] += np.deg2rad(yaw_deg)
    return make_body_smplx(
        pose, world_centroid, betas=betas, gender=gender, verbose=verbose
    )
