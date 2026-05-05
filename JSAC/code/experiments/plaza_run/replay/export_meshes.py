"""Export per-keyframe posed body meshes for the replay viewer.

Reads a brief 08 NPZ + recreates its scenario (same seed), poses each body
via SMPL-X for each keyframe, decimates the canonical T-pose once with
trimesh quadric simplification, and emits an indexed binary the HTML side
fetches.

Output layout (little-endian, v3):

    [0:32]  header (8 × uint32):
            magic = 0x504C5A4D ('PLZM')
            version = 3
            n_keyframes K
            n_bodies B
            n_verts_dec V_dec
            n_tris_dec  F_dec
            keyframe_period (slots/keyframe)
            reserved = 0
    [32:]                          triangles, uint32, (F_dec, 3) — shared
    [+K*B*V*3*4]                   verts (body-local), float32, (K, B, V, 3)
    [+K*B*4]                       headings, float32, (K, B)  — radians
    [+K*B*2*4]                     world_xy, float32, (K, B, 2)

Body-local verts: origin at the body root, feet on z=0. The JS layer
places the mesh at world (x, y, 0) and rotates by trajectory heading.

Vertex correspondence between the decimated mesh and the SMPL-X canonical
mesh is via single-NN against the T-pose (cKDTree). For each output vertex
we record the index of the nearest canonical SMPL-X vertex; posing then
just slices `posed_verts[donor_idx]`. Single-NN is approximate (won't be
exact on edge-collapse seams) but good enough for the viewer at decim ~14.

Run:

    python -m JSAC.code.experiments.plaza_run.replay.export_meshes \
        --npz outputs/plaza_run_seed42_..._bind.npz --target-faces 1500
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenario import (  # noqa: E402
    TIER_COUNTS,
    assign_bodies,
    discover_walks,
    load_pose_streams,
    smplx_body,
)

logger = logging.getLogger(__name__)

REPLAY_DIR = Path(__file__).resolve().parent
MAGIC = 0x504C5A4D  # 'PLZM'
VERSION = 3


def _decimate_topology(
    canonical_verts: np.ndarray,
    faces: np.ndarray,
    target_faces: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Decimate the canonical mesh; return (donor_idx, faces_dec).

    `donor_idx` is (V_dec,) int — for each surviving decimated vertex, the
    index of its single nearest neighbour in `canonical_verts`. Posing then
    slices `posed[donor_idx]` to get this vertex's world position.
    """
    import trimesh
    from scipy.spatial import cKDTree

    mesh = trimesh.Trimesh(vertices=canonical_verts, faces=faces, process=False)
    simplified = mesh.simplify_quadric_decimation(face_count=target_faces)
    tree = cKDTree(canonical_verts)
    _dists, donor_idx = tree.query(simplified.vertices, k=1)
    return donor_idx.astype(np.int64), np.asarray(simplified.faces, dtype=np.uint32)


def _pose_indexed(
    parametric,
    betas: np.ndarray,
    pose_axang: np.ndarray,
    *,
    override_global_orient: np.ndarray | None = None,
) -> np.ndarray:
    """Forward SMPL-X with given betas + pose; return (V, 3) indexed verts.

    `override_global_orient` replaces the AMASS-baked actor facing with a
    fixed Z-up baseline so the JS layer can rotate the mesh per-frame to
    match the trajectory heading. Pass `(π/2, 0, 0)` for Z-up T-pose
    facing +Y; the JS layer adds a z-rotation per slot.
    """
    import torch

    betas_t = torch.tensor(betas[:10], dtype=torch.float32).unsqueeze(0)
    body_pose_t = torch.tensor(pose_axang[3:66], dtype=torch.float32).unsqueeze(0)
    if override_global_orient is not None:
        go = np.asarray(override_global_orient, dtype=np.float32)
    else:
        go = pose_axang[:3].astype(np.float32)
    global_orient_t = torch.tensor(go, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        out = parametric._model(betas=betas_t, body_pose=body_pose_t, global_orient=global_orient_t)
    return out.vertices[0].numpy()  # (V, 3) float32


ZUP_GLOBAL_ORIENT = np.array([np.pi / 2, 0.0, 0.0], dtype=np.float32)


def export_meshes(
    npz_path: Path,
    *,
    target_faces: int = 1200,
    keyframe_period: int = 6,
    out_path: Path | None = None,
) -> Path:
    npz_path = Path(npz_path)
    out_path = out_path or REPLAY_DIR / f"meshes_{npz_path.stem}.bin"

    with np.load(npz_path, allow_pickle=False) as f:
        seed = int(f["seed"])
        n_bodies = int(f["n_bodies"])
        n_slots = int(f["n_slots"])
        body_positions = np.asarray(f["body_positions"]).astype(np.float64)

    if n_bodies != sum(TIER_COUNTS.values()):
        raise ValueError(f"NPZ n_bodies={n_bodies} doesn't match scenario {TIER_COUNTS}")

    rng = random.Random(seed)
    walks = discover_walks()
    bodies = assign_bodies(n_bodies, rng, walks)
    pose_streams = load_pose_streams(bodies)
    parametric = smplx_body()

    canonical = _pose_indexed(parametric, np.zeros(10), np.zeros(66), override_global_orient=ZUP_GLOBAL_ORIENT)
    faces = np.asarray(parametric._faces, dtype=np.int64)
    donor_idx, faces_dec = _decimate_topology(canonical, faces, target_faces)
    n_verts_dec = int(donor_idx.shape[0])
    n_faces_dec = int(faces_dec.shape[0])

    keyframe_slots = list(range(0, n_slots, keyframe_period))
    n_kf = len(keyframe_slots)

    logger.info(
        "decimated %d→%d tris, %d→%d verts; exporting %d keyframes × %d bodies (kp=%d)",
        len(faces),
        n_faces_dec,
        len(canonical),
        n_verts_dec,
        n_kf,
        n_bodies,
        keyframe_period,
    )

    # Body-local verts: origin at body root xy, feet on z=0. The JS layer
    # places the mesh at world (x, y, 0) and rotates by trajectory heading.
    out = np.zeros((n_kf, n_bodies, n_verts_dec, 3), dtype=np.float32)
    # Per (kf, body) heading angle in radians. Computed from velocity at
    # the keyframe slot via finite difference; the JS rotates mesh.z by this.
    headings = np.zeros((n_kf, n_bodies), dtype=np.float32)
    # Convenience: per (kf, body) world xy too (so JS can drop replay-data
    # interpolation and just use the keyframe sidecar table).
    world_xy = np.zeros((n_kf, n_bodies, 2), dtype=np.float32)

    for k_idx, slot in enumerate(keyframe_slots):
        pose_count = slot // 1  # advance pose every slot now (kp=6 → fine gait)
        for b in bodies:
            pose_axang, _trans = pose_streams[b.index].frame(pose_count, loop=True)
            betas = pose_streams[b.index].betas
            verts_full = _pose_indexed(parametric, betas, pose_axang, override_global_orient=ZUP_GLOBAL_ORIENT)
            v = verts_full[donor_idx].astype(np.float32)
            v[:, 2] -= float(v[:, 2].min())  # drop feet to z=0
            # Centre xy at body root (mean of x,y so JS rotation is well-behaved).
            v[:, 0] -= float(v[:, 0].mean())
            v[:, 1] -= float(v[:, 1].mean())
            out[k_idx, b.index] = v
            world_xy[k_idx, b.index] = body_positions[slot, b.index, :2].astype(np.float32)
            # Heading from finite-difference velocity. Look forward 5 slots if
            # possible to dampen Brownian heading noise.
            slot_a = slot
            slot_b = min(slot + 5, n_slots - 1)
            if slot_b > slot_a:
                dxy = body_positions[slot_b, b.index, :2] - body_positions[slot_a, b.index, :2]
                if np.linalg.norm(dxy) > 1e-3:
                    headings[k_idx, b.index] = float(np.arctan2(dxy[1], dxy[0]))
                elif k_idx > 0:
                    headings[k_idx, b.index] = headings[k_idx - 1, b.index]
        if (k_idx + 1) % 25 == 0:
            logger.info("  keyframe %d/%d done", k_idx + 1, n_kf)

    with out_path.open("wb") as f:
        f.write(
            struct.pack(
                "<8I",
                MAGIC,
                VERSION,
                n_kf,
                n_bodies,
                n_verts_dec,
                n_faces_dec,
                keyframe_period,
                0,
            )
        )
        f.write(faces_dec.astype(np.uint32).tobytes(order="C"))
        f.write(out.tobytes(order="C"))  # body-local verts
        f.write(headings.astype(np.float32).tobytes(order="C"))  # K*B
        f.write(world_xy.astype(np.float32).tobytes(order="C"))  # K*B*2

    size_mb = out_path.stat().st_size / 1024 / 1024
    logger.info(
        "wrote %s: %d KF × %d bodies × %d verts × %d tris (%.2f MB)",
        out_path,
        n_kf,
        n_bodies,
        n_verts_dec,
        n_faces_dec,
        size_mb,
    )

    sidecar = out_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "bin_path": out_path.name,
                "keyframe_slots": keyframe_slots,
                "n_keyframes": n_kf,
                "n_bodies": n_bodies,
                "n_verts_dec": n_verts_dec,
                "n_tris_dec": n_faces_dec,
                "keyframe_period": keyframe_period,
                "magic": "PLZM",
                "version": VERSION,
            }
        )
    )
    logger.info("wrote %s", sidecar)
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--npz", type=Path, required=True, help="brief 08 NPZ to source from")
    p.add_argument("--target-faces", type=int, default=1500)
    p.add_argument("--keyframe-period", type=int, default=30)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    export_meshes(
        args.npz,
        target_faces=args.target_faces,
        keyframe_period=args.keyframe_period,
        out_path=args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
