"""Export a study scene as a Replay artifact for the AEGIS viewer.

Builds one city, places the deployment, picks one served user, and walks it
through a few frames, computing the coherent per-face S_ab at each. Emits the
``ReplayArtifact`` JSON the viewer's Replay tab loads (scene, array panel, body
mesh, per-frame S_ab + rays). This is the bridge from the study pipeline to the
3D viewer (Plan 5).

Rays are synthesized: the served sector -> body LOS segment plus arrival-
direction stubs from the strongest center paths (the Sionna bridge keeps arrival
directions, not full bounce polylines), so they show arrival geometry honestly,
not exact reflection points.

Usage:
    python -m aegis.study.replay_export --config configs/study/ghent_mvp.yaml \
        --out aegis-web/public/study_ghent.json --frames 6
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _canonical_body(stl_path):
    from aegis.geometry.mesh import BodyMesh

    body = BodyMesh.load(Path(stl_path), name="duke")
    soup = np.asarray(body.vertices, dtype=float)  # (M, 3, 3)
    verts = soup.reshape(-1, 3)
    faces = [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(soup.shape[0])]
    return body, verts.tolist(), faces


def _city_mesh(city):  # pragma: no cover - heavy
    """The real ray-traced city geometry as an indexed triangle mesh.

    This is exactly the mesh the deterministic arm bounces rays off
    (``CityCache.mesh``): true polygonal footprints extruded to per-building
    height with parsed roof shapes, not axis-aligned bounding boxes. The Ghent
    core is ~7k triangles (~0.4 MB JSON), so there is no size reason to send a
    box caricature. Coordinates are server Z-up (ENU), rounded to the cm.
    """
    m = city.mesh
    verts = np.round(np.asarray(m.vertices, dtype=float), 2)
    tris = np.asarray(m.triangles, dtype=int)
    return {"vertices": verts.tolist(), "triangles": tris.tolist()}


def _site_marker_boxes(sites):  # pragma: no cover - trivial
    """A small marker box at each base-station rooftop site (server Z-up)."""
    boxes = []
    for s in sites:
        p = np.asarray(s.position, dtype=float)
        boxes.append({"center": [float(p[0]), float(p[1]), float(p[2])], "size": [4.0, 4.0, 4.0], "kind": "blocker"})
    return boxes


def build_artifact(cfg, out_dir, seed, frames, city_latlon=(51.0536, 3.7253)):  # pragma: no cover - heavy
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.precoder import Precoder
    from aegis.study.bodies import StaticPhantomPoser
    from aegis.study.channel_det import center_paths
    from aegis.study.city import CityCache
    from aegis.study.deployment import build_sites, sectors_illuminating, select_rooftop_sites
    from aegis.study.precoding import mrt_for_user, user_channel_vector
    from aegis.study.run import _build_agents
    from aegis.tissue.dielectric import TissueModel

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    eq = cfg.deployment.equipment
    freq = eq.freq_hz
    torso_z = 1.1

    lat, lon = float(city_latlon[0]), float(city_latlon[1])
    city = CityCache.build(lat, lon, cfg.cities.radius_m, out_dir / "city")
    n_sites = max(1, int(round(3 * cfg.deployment.densification)))
    site_xy = select_rooftop_sites(
        city.candidates,
        n_sites,
        rng,
        min_spacing_m=60.0,
        height_band_m=(cfg.deployment.site_height_min_m, cfg.deployment.site_height_max_m),
        mount_height_m=cfg.deployment.mount_height_m,
    )
    if site_xy.shape[0] == 0:
        site_xy = np.array([[0.0, 0.0, 15.0]])
    sites = build_sites(
        site_xy,
        cfg.deployment.sectoring.sectors,
        cfg.deployment.sectoring.az_coverage_deg,
        cfg.deployment.sectoring.max_range_m,
        freq,
        eq.array,
        eq.tx_power_dbm,
        downtilt_deg=cfg.deployment.sectoring.downtilt_deg,
        rng=rng,
    )

    from aegis.study.covariates import data_dir

    agents = _build_agents(cfg, city, rng, 0, cfg.mobility.n_agents, out_dir / "routes", seed=seed)
    engine = DosimetryEngine(TissueModel.from_database("Skin", freq))
    poser = StaticPhantomPoser(BodyMesh.load(data_dir() / "duke.stl", name="duke"))
    _, cverts, cfaces = _canonical_body(data_dir() / "duke.stl")

    # Pick the agent with the most illuminated slots, and sample frames from
    # those lit slots (evenly-spaced slots can miss the covered stretch).
    def lit_slots(agent):
        pos = np.asarray(agent.trajectory.positions)
        return [t for t, p in enumerate(pos) if sectors_illuminating(np.array([p[0], p[1], torso_z]), sites)]

    # Rank agents by how many slots are geometrically illuminated, then for each
    # (best first) scan its lit slots and keep only those that actually trace
    # paths (geometric wedge/range coverage does not guarantee a non-shadowed
    # ray-traced path in a dense core). Stop once we have `frames` real frames.
    ranked = sorted(agents, key=lambda a: len(lit_slots(a)), reverse=True)
    if not lit_slots(ranked[0]):
        raise RuntimeError("no agent is illuminated anywhere; check deployment/walk coverage")

    def _frame_for(pos_xy, fi):
        body = poser.pose(pos_xy, heading_rad=0.0, z_ground=0.0)
        lit = sectors_illuminating(np.array([pos_xy[0], pos_xy[1], torso_z]), sites)
        if not lit:
            return None, None
        sector = lit[0]
        rx = np.array([pos_xy[0], pos_xy[1], torso_z])
        center, viz = center_paths(
            city.sionna_scene,
            sector,
            rx,
            freq,
            engine="sionna",
            samples_per_src=getattr(cfg.channel, "samples_per_src", 3_000_000),
            diffraction=getattr(cfg.channel, "diffraction", True),
            max_center_paths=getattr(cfg.channel, "max_center_paths", 16),
            return_viz=True,
        )
        if center is None or center.k_hat is None or center.k_hat.shape[0] == 0:
            return None, None
        per_elem = expand_paths_to_array(center, sector.array, freq)
        x = mrt_for_user(user_channel_vector(per_elem, sector.m_ant), sector.tx_power_w).x
        result = engine.compute(body, per_elem, level=cfg.dosimetry.level, precoder=Precoder(x=x))
        body_centroid = rx.tolist()
        k = np.asarray(center.k_hat)
        # Real Sionna per-bounce rays (TX -> reflection/diffraction points -> RX),
        # keep the lowest-order strongest few. Fall back to a LOS stub if empty.
        rays = sorted(viz, key=lambda v: (v.get("order", 9), v.get("length", 1e9)))[:10]
        paths = [{"vertices": r["vertices"], "order": int(r.get("order", 1))} for r in rays if len(r["vertices"]) >= 2]
        if not paths:
            paths = [{"vertices": [sector.position.tolist(), body_centroid], "order": 0}]
        frame = {
            "ue_index": 0,
            "condition": "LOS" if bool(np.any(center.is_los)) else "NLOS",
            "precoder": "mrt",
            "realization": 0,
            "body_pos": [float(pos_xy[0]), float(pos_xy[1]), 0.0],
            "paths": paths,
            "sab": np.asarray(result.sab, dtype=float).tolist(),
            "scalars": {"p_abs": float(result.p_abs), "n_paths": int(k.shape[0]), "frame": int(fi)},
        }
        return frame, sector

    frame_list = []
    ue_positions = []
    serving_sector = None
    for agent in ranked[:4]:
        positions = np.asarray(agent.trajectory.positions)
        for t in lit_slots(agent):
            frame, sector = _frame_for(positions[t], len(frame_list))
            if frame is None:
                continue
            serving_sector = serving_sector or sector
            frame_list.append(frame)
            ue_positions.append(frame["body_pos"][:2] + [torso_z])
            if len(frame_list) >= frames:
                break
        if len(frame_list) >= frames:
            break

    if not frame_list:
        raise RuntimeError("no traced paths at any illuminated slot; try another seed or denser sampling")

    panel = {
        "position": serving_sector.position.tolist(),
        "elements": np.asarray(serving_sector.array.element_positions, dtype=float).tolist(),
        "n_h": int(eq.array[0]),
        "n_v": int(eq.array[1]),
        "M": int(serving_sector.m_ant),
    }
    # Buildings render as the real ray-traced triangle mesh (scene.mesh); only
    # the base-station site markers stay as boxes. No realizations: with a single
    # static city, ReplayContent falls back to scene.boxes for the markers.
    artifact = {
        "meta": {"source": "aegis.study", "city_latlon": [lat, lon], "freq_hz": float(freq)},
        "scene": {
            "ground": {"size": float(2 * cfg.cities.radius_m)},
            "mesh": _city_mesh(city),
            "boxes": _site_marker_boxes(sites),
        },
        "array": panel,
        "body": {"vertices": cverts, "faces": cfaces},
        "ues": ue_positions,
        "frames": frame_list,
    }
    return artifact


def main(argv=None) -> int:
    from aegis.study.config import StudyConfig

    ap = argparse.ArgumentParser(description="Export a study scene as a Replay artifact")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--work", default="results/replay_export")
    args = ap.parse_args(argv)

    cfg = StudyConfig.from_yaml(args.config)
    seed = args.seed if args.seed is not None else cfg.channel.seed
    artifact = build_artifact(cfg, Path(args.work), seed, args.frames)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(artifact), encoding="utf-8")
    print(f"wrote {args.out}: {len(artifact['frames'])} frames, {len(artifact['body']['faces'])} faces")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
