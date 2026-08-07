"""Layer 5: ten people walking the quay.

    .venv/bin/python -m twin.people --area graslei --n 10 --out data/twin/people.npz

Runs under the venv, not inside Blender, because SMPL-X needs torch and Blender's
bundled Python has neither. So this precomputes posed bodies to an npz and
`realise.py` loads them. Same split the Studio module already uses: heavy compute
offline, the renderer consumes a pack.

The bodies are real articulated SMPL-X meshes driven by AMASS walk clips, not
capsules, because at 28 GHz a person is the strongest reflector in the scene.
Computed from AEGIS's own tissue model, skin reflects at 0.679 against brick at
0.328, so a pedestrian is 6.3 dB brighter than the wall behind them and completely
opaque at about 9100 dB/m. Their silhouette is the physics.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, "/home/user/aegis/src")

from aegis.study.bodies import SmplxWalkPoser  # noqa: E402
from aegis.study.walk import sample_trajectory  # noqa: E402

from .anchor import Anchor, load  # noqa: E402

CLIPS = sorted(pathlib.Path("/home/user/aegis/data/poses").glob("*normal_walk*.npz"))
if not CLIPS:
    CLIPS = sorted(pathlib.Path("/home/user/aegis/data/poses").glob("*.npz"))


def quay_route(a: Anchor, centre, radius: float, *,
               standoff: float = 5.0, length: float = 52.0) -> np.ndarray:
    """The pavement in front of the transmitting facade.

    Deliberately not "the nicest walkway nearby". Two earlier versions of this
    picked a route by length, then by length weighted toward the study centre, and
    both put the walkers somewhere plausible but outside the beam. A scene that
    technically contains ten people and illuminates none of them is a silent
    failure, so the route is now tied to the thing the study is about: it runs along
    the frontage the small cell is mounted on, `standoff` metres out.
    """
    from .radiator import default_cell

    cell = default_cell(a)
    p = cell.position[:2]
    d = cell.boresight[:2]
    d = d / (np.linalg.norm(d) + 1e-9)
    # Walk the pavement the beam sweeps: from just in front of the panel, straight
    # down the boresight. Coupling the route to the deployment is the point.
    return np.array([p + d * 4.0, p + d * (4.0 + length)])


def build(a: Anchor, centre, radius: float, n: int = 10, seed: int = 0,
          speed: float = 1.35) -> dict:
    rng = np.random.default_rng(seed)
    route = quay_route(a, centre, radius)
    genders = ["neutral", "male", "female"]

    out_v, out_f, meta = [], [], []
    base = 0
    for i in range(n):
        clip = CLIPS[int(rng.integers(len(CLIPS)))]
        betas = rng.normal(0.0, 0.9, size=10)
        poser = SmplxWalkPoser(str(clip),
                               gender=genders[int(rng.integers(len(genders)))],
                               betas=betas)
        # Stagger entries so the group is spread along the route rather than
        # stacked at the start, and let half of them walk the other way.
        traj = sample_trajectory(route, speed_mps=speed, dt_s=0.5,
                                 entry_offset_s=float(rng.uniform(0, 26)))
        k = int(rng.integers(len(traj.positions)))
        pos = traj.positions[k]
        head = float(traj.headings_rad[k])
        if rng.random() < 0.5:
            head += np.pi
        pos = pos + rng.normal(0.0, 1.6, size=2)   # spread across the width

        body = poser.pose(position_xy=pos, heading_rad=head,
                          z_ground=a.terrain.at(*pos),
                          frame_idx=int(rng.integers(0, 90)))
        tri = np.asarray(body.vertices, dtype=np.float32)   # (N, 3, 3)
        v = tri.reshape(-1, 3)
        f = np.arange(len(v), dtype=np.int32).reshape(-1, 3) + base
        out_v.append(v)
        out_f.append(f)
        base += len(v)
        meta.append({"i": i, "xy": pos.tolist(), "heading": head,
                     "clip": clip.name, "n_tris": int(len(tri))})
        print(f"  person {i}: {len(tri)} tris at {np.round(pos, 1)} "
              f"heading {np.degrees(head):.0f} deg  [{clip.stem[:34]}]")

    return {
        "verts": np.concatenate(out_v),
        "faces": np.concatenate(out_f),
        "counts": np.array([len(f) for f in out_f], dtype=np.int32),
        "route": route.astype(np.float32),
        "meta": np.array([str(m) for m in meta], dtype=object),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/twin/people.npz")
    args = ap.parse_args()

    from .areas import AREAS
    cx, cy, radius = AREAS[args.area]

    a = load()
    print(f"[people] {args.n} walkers on the {args.area} spine")
    pack = build(a, (cx, cy), radius, n=args.n, seed=args.seed)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, verts=pack["verts"], faces=pack["faces"],
                        counts=pack["counts"], route=pack["route"])
    print(f"[people] {len(pack['faces'])} triangles total -> {out}")


if __name__ == "__main__":
    main()
