"""Sky fraction and skyline height per city, for the contact sheet."""

import json
import pathlib

import re

import numpy as np
import trimesh

ROOT = pathlib.Path("/home/user/aegis/papers/city-exposure-study/semantic_twin")
RAYS = 120_000


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5**0.5) * i
    return np.column_stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)])


dirs = fib(RAYS)
out = {}
sites = sorted(d.name for d in (ROOT / "data/geometry").iterdir() if d.is_dir())
paths = []
for site in sites:
    # Prefer the largest double precision crop the site actually has.
    candidates = sorted((ROOT / "data/geometry" / site).glob("inhouse_leaf_*_f64.ply"))
    if not candidates:
        candidates = sorted((ROOT / "data/geometry" / site).glob("inhouse_leaf_*.ply"))
    chosen = [c for c in candidates if "130m" in c.name] or candidates[-1:]
    paths.extend(str(c) for c in chosen)
for path in paths:
    site = pathlib.Path(path).parent.name
    name = pathlib.Path(path).name
    if site in out:
        continue
    mesh = trimesh.load(path, process=False, force="mesh")
    lo, hi = mesh.bounds
    cx, cy = 0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1])
    top = np.array([[cx, cy, hi[2] + 5.0]])
    loc, _, _ = mesh.ray.intersects_location(ray_origins=top, ray_directions=np.array([[0.0, 0.0, -1.0]]))
    if len(loc) == 0:
        continue
    ground = float(np.median(loc[:, 2]))
    eye = np.array([cx, cy, ground + 1.5])
    idx = mesh.ray.intersects_first(ray_origins=np.repeat(eye[None, :], RAYS, axis=0), ray_directions=dirs)
    z = mesh.vertices[:, 2]
    out[site] = {
        "sky": float((idx < 0).mean()),
        "skyline_m": float(np.percentile(z, 99.5) - np.percentile(z, 2.0)),
        "triangles": int(len(mesh.faces)),
        "mesh": name,
        "crop_radius_m": float(re.search(r"_(\d+)m", name).group(1)),
    }
    print(
        f"{site:24s} sky {out[site]['sky']:.3f}  skyline {out[site]['skyline_m']:6.1f} m  "
        f"r={out[site]['crop_radius_m']:.0f} m  {name}"
    )

target = ROOT / "outputs/city_gallery/metrics.json"
target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(f"wrote {target}, {len(out)} sites")
