"""Export per-keyframe posed body meshes for the replay viewer.

Reads a brief 08 NPZ + recreates its scenario (same seed), poses each body
via SMPL-X for each keyframe, decimates the canonical T-pose once with
trimesh quadric simplification, and emits an indexed binary the HTML side
fetches.

Output layout (little-endian):

    [0:8]  header (uint32, 4 bytes each):
            magic = 0x504C5A4D ('PLZM')
            version = 2
            n_keyframes K
            n_bodies B
            n_verts_dec V_dec
            n_tris_dec  F_dec
            keyframe_period (slots/keyframe)
            reserved = 0
    [8:8+12*F_dec]  triangles, uint32, shape (F_dec, 3)  — shared across (K,B)
    payload float32, shape (K, B, V_dec, 3) packed C-order.

The shared topology + indexed vertices give a real connected mesh per body
and shrink the wire payload by ~3× vs sending triangle soup.

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
VERSION = 2


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


def _pose_indexed(parametric, betas: np.ndarray, pose_axang: np.ndarray) -> np.ndarray:
    """Forward SMPL-X with given betas + pose; return (V, 3) indexed verts."""
    import torch

    betas_t = torch.tensor(betas[:10], dtype=torch.float32).unsqueeze(0)
    body_pose_t = torch.tensor(pose_axang[3:66], dtype=torch.float32).unsqueeze(0)
    global_orient_t = torch.tensor(pose_axang[:3], dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        out = parametric._model(betas=betas_t, body_pose=body_pose_t, global_orient=global_orient_t)
    return out.vertices[0].numpy()  # (V, 3) float32


def export_meshes(
    npz_path: Path,
    *,
    target_faces: int = 1500,
    keyframe_period: int = 30,
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

    canonical = _pose_indexed(parametric, np.zeros(10), np.zeros(66))
    faces = np.asarray(parametric._faces, dtype=np.int64)
    donor_idx, faces_dec = _decimate_topology(canonical, faces, target_faces)
    n_verts_dec = int(donor_idx.shape[0])
    n_faces_dec = int(faces_dec.shape[0])

    keyframe_slots = list(range(0, n_slots, keyframe_period))
    n_kf = len(keyframe_slots)

    logger.info(
        "decimated %d→%d tris, %d→%d verts; exporting %d keyframes × %d bodies",
        len(faces),
        n_faces_dec,
        len(canonical),
        n_verts_dec,
        n_kf,
        n_bodies,
    )

    out = np.zeros((n_kf, n_bodies, n_verts_dec, 3), dtype=np.float32)
    for k_idx, slot in enumerate(keyframe_slots):
        pose_count = slot // keyframe_period
        for b in bodies:
            pose_axang, _trans = pose_streams[b.index].frame(pose_count, loop=True)
            betas = pose_streams[b.index].betas
            verts_full = _pose_indexed(parametric, betas, pose_axang)
            v = verts_full[donor_idx].astype(np.float32)
            v[:, 2] -= float(v[:, 2].min())  # drop feet to z=0
            world_pos = body_positions[slot, b.index].astype(np.float32)
            v[:, 0] += world_pos[0]
            v[:, 1] += world_pos[1]
            out[k_idx, b.index] = v
        if (k_idx + 1) % 5 == 0:
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
        f.write(out.tobytes(order="C"))

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
