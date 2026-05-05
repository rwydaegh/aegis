"""Prepare replay JSON from a plaza_run NPZ.

Bundles trajectories, per-slot P_abs, BS pose, and the Brussels Grand
Place OSM mesh (cached via scene_cache) into a single JSON the replay
HTML can fetch. Falls back to a synthetic facade ring if the OSM cache
is missing.
"""

from __future__ import annotations

import json

# Re-use the canonical loaders from the figures/ subdir.
import sys
from pathlib import Path

import numpy as np

_FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
sys.path.insert(0, str(_FIG_DIR))
from _data import CANONICAL_RUNS, OUTPUTS_DIR, load_canonical  # noqa: E402

# Scene cache.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_cache import load_or_scrape  # noqa: E402

REPLAY_DIR = Path(__file__).resolve().parent
DATA_PATH = REPLAY_DIR / "replay_data.json"

# Plaza dimensions match paths.py (FACADE_Y_M = 35) and
# scenario.py body_sampling_bounds (x in [-35, 35], y in [-30, 30]).
FACADE_Y = 35.0
FACADE_X = 40.0
PLAZA_HALF_X = 45.0
PLAZA_HALF_Y = 45.0
BUILDING_HEIGHT = 18.0

# Decimate the trajectory to keep payload small. 600 slots / decim_t = 60 keyframes.
DECIM_T_DEFAULT = 5  # 600 -> 120 frames (4 s of replay at 30 fps screen update)


def synthetic_plaza_buildings() -> list[dict]:
    """Build a ring of building blocks around the plaza perimeter.

    Visual approximation only; matches the y=±35 facade pair the
    deterministic path generator assumes, plus side walls so the BS
    looks plausibly mounted.
    """
    blocks = []
    block_depth = 6.0

    # North & south long facades (y = ±35), each split into 6 blocks for
    # visual variety.
    for y_sign in (-1, 1):
        for i in range(6):
            x_center = (i - 2.5) * (FACADE_X / 3.0)
            x_w = FACADE_X / 3.5
            blocks.append(
                {
                    "center": [x_center, y_sign * (FACADE_Y + block_depth / 2), BUILDING_HEIGHT / 2],
                    "size": [x_w, block_depth, BUILDING_HEIGHT - 2 * (i % 2)],
                }
            )

    # East & west short facades.
    for x_sign in (-1, 1):
        for j in range(4):
            y_center = (j - 1.5) * (FACADE_Y * 0.5)
            y_w = FACADE_Y * 0.45
            blocks.append(
                {
                    "center": [x_sign * (FACADE_X + block_depth / 2), y_center, BUILDING_HEIGHT / 2 - 1.5],
                    "size": [block_depth, y_w, BUILDING_HEIGHT - 3 - (j % 2) * 2],
                }
            )
    return blocks


def main(npz_label: str = "specular_aware", decim_t: int = DECIM_T_DEFAULT) -> Path:
    run = load_canonical(npz_label)
    run_npz_path = OUTPUTS_DIR / CANONICAL_RUNS[npz_label] if npz_label in CANONICAL_RUNS else None

    # Decimate time axis.
    t_keep = np.arange(0, run.n_slots, decim_t)
    body_xy = run.body_positions[t_keep, :, :2].astype(np.float32)
    p_abs = run.p_abs[t_keep, :, :].astype(np.float32)
    sumrate = run.sumrate[t_keep, :].astype(np.float32)

    # Posed mesh sidecar (optional). The HTML fetches the .bin separately
    # if the sidecar JSON is present.
    meshes_sidecar: dict | None = None
    if run_npz_path is not None:
        sidecar_path = REPLAY_DIR / f"meshes_{run_npz_path.stem}.json"
        if sidecar_path.exists():
            import json as _json
            meshes_sidecar = _json.loads(sidecar_path.read_text())
            print(f"posed-mesh sidecar found: {sidecar_path.name}")

    # Try the real OSM scrape; fall back to synthetic if unreachable.
    osm_mesh: dict | None = None
    try:
        mesh, scene_hash = load_or_scrape()
        osm_mesh = {
            "vertices_flat": mesh.vertices.astype(np.float32).flatten().tolist(),
            "vertices_shape": list(mesh.vertices.shape),
            "triangles_flat": mesh.triangles.astype(np.uint32).flatten().tolist(),
            "triangles_shape": list(mesh.triangles.shape),
            "hash": scene_hash,
        }
        print(f"loaded Brussels OSM mesh: {mesh.vertices.shape[0]} verts, {mesh.triangles.shape[0]} tris")
    except Exception as exc:
        print(f"OSM scrape unavailable ({exc}); falling back to synthetic ring")

    payload = {
        "scenario": {
            "label": npz_label,
            "phy_mode": run.phy_mode,
            "pose_mode": run.pose_mode,
            "paths_mode": run.paths_mode,
            "freq_hz": run.freq_hz,
            "tx_power_dbm": run.tx_power_dbm,
            "n_bodies": run.n_bodies,
            "n_slots_full": run.n_slots,
            "dt_s": run.dt_s,
            "decim_t": decim_t,
        },
        "osm_mesh": osm_mesh,  # may be None; client falls back to synthetic
        "buildings": synthetic_plaza_buildings() if osm_mesh is None else [],
        "ground": {
            "size": [2 * PLAZA_HALF_X, 2 * PLAZA_HALF_Y],
            "z": 0.0,
        },
        "bs": {
            # scenario.py: BS at (0, -40, 12) broadside (0, cos(5°), -sin(5°))
            "position": [0.0, -40.0, 12.0],
            "broadside": [0.0, float(np.cos(np.deg2rad(5))), -float(np.sin(np.deg2rad(5)))],
            "n_h": 8,
            "n_v": 8,
        },
        "tier": run.tier.tolist(),
        "body_budgets_w": run.body_budgets_w.tolist(),
        "precoder_names": run.precoder_names,
        "frames": {
            "t_keep": t_keep.tolist(),
            "body_xy_flat": body_xy.flatten().tolist(),  # (T*B*2,)
            "body_xy_shape": list(body_xy.shape),
            "p_abs_flat": p_abs.flatten().tolist(),  # (T*B*P,)
            "p_abs_shape": list(p_abs.shape),
            "sumrate_flat": sumrate.flatten().tolist(),
            "sumrate_shape": list(sumrate.shape),
        },
        "meshes_sidecar": meshes_sidecar,
    }

    DATA_PATH.write_text(json.dumps(payload))
    n_t, n_b, n_p = p_abs.shape
    size_kb = DATA_PATH.stat().st_size / 1024
    print(f"wrote {DATA_PATH} ({n_t} keyframes x {n_b} bodies x {n_p} precoders, {size_kb:.0f} KB)")
    return DATA_PATH


if __name__ == "__main__":
    main()
