"""3D render of the Ghent study scene: real traced geometry, sites and walks if present.

Falls back gracefully: with only the city meshes it renders the city. With a
scene.json it adds base-station sites, sector wedges, and the pedestrian walks
coloured by per-person absorbed power.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

pv.OFF_SCREEN = True

MATERIALS = {
    "scene_concrete.ply": ("#b8b2a7", 1.0, "buildings"),
    "scene_asphalt.ply": ("#4a4a4a", 1.0, "road"),
    "scene_water.ply": ("#4a7fa5", 1.0, "water"),
}


def _load(path):
    m = trimesh.load(path, process=False)
    v = np.asarray(m.vertices)
    f = np.asarray(m.faces)
    faces = np.hstack([np.full((len(f), 1), 3), f]).ravel()
    return pv.PolyData(v, faces)


def render(run_dir, out_path, cam="hero"):
    run_dir = Path(run_dir)
    city = run_dir / "city"

    pl = pv.Plotter(off_screen=True, window_size=(1800, 1150))
    pl.set_background("#eef2f6", top="#ffffff")

    for fname, (color, opacity, label) in MATERIALS.items():
        fp = city / fname
        if not fp.exists():
            continue
        mesh = _load(fp)
        if label == "buildings":
            mesh["height"] = mesh.points[:, 2]
            pl.add_mesh(mesh, scalars="height", cmap="bone_r", clim=(0, 60),
                        show_scalar_bar=False, smooth_shading=False,
                        specular=0.25, specular_power=15, opacity=opacity)
        else:
            pl.add_mesh(mesh, color=color, opacity=opacity, show_scalar_bar=False)
        print(f"  {label:10s} {mesh.n_cells:6d} tris")

    scene_fp = run_dir / "scene.json"
    if scene_fp.exists():
        scene = json.loads(scene_fp.read_text())

        # base-station sites: mast + sector wedges on the ground
        for s in scene.get("sites", []):
            px, py, pz = s["position"][:3]
            pl.add_mesh(pv.Cylinder(center=(px, py, pz / 2), direction=(0, 0, 1),
                                    radius=0.6, height=max(pz, 1.0)),
                        color="#8a8a8a", show_scalar_bar=False)
            pl.add_mesh(pv.Sphere(radius=3.0, center=(px, py, pz)),
                        color="#e63946", show_scalar_bar=False)
            for sec in s.get("sectors", []):
                half = sec["az_coverage_deg"] / 2.0
                a0 = np.deg2rad(sec["boresight_az_deg"] - half)
                a1 = np.deg2rad(sec["boresight_az_deg"] + half)
                r = sec["max_range_m"]
                th = np.linspace(a0, a1, 32)
                pts = np.column_stack([px + r * np.cos(th), py + r * np.sin(th),
                                       np.full(th.size, 0.4)])
                pts = np.vstack([[px, py, 0.4], pts])
                faces = np.hstack([[3, 0, i, i + 1] for i in range(1, len(pts) - 1)])
                pl.add_mesh(pv.PolyData(pts, faces), color="#ffa62b", opacity=0.10,
                            show_scalar_bar=False)

        # walks, coloured by per-person absorbed power
        exposures = [a.get("exposure_w") or 1e-13 for a in scene.get("agents", [])]
        if exposures:
            lo, hi = np.log10(min(exposures)), np.log10(max(exposures))
            for a in scene["agents"]:
                pos = np.asarray(a["positions"], dtype=float)
                if pos.shape[0] < 2:
                    continue
                if pos.shape[1] == 2:
                    pos = np.column_stack([pos, np.zeros(len(pos))])
                pos = pos.copy()
                pos[:, 2] = 1.0
                e = np.log10(max(a.get("exposure_w") or 1e-13, 1e-13))
                t = (e - lo) / max(hi - lo, 1e-9)
                poly = pv.Spline(pos, max(len(pos) * 4, 40)).tube(radius=1.1)
                poly["exposure"] = np.full(poly.n_points, e)
                pl.add_mesh(poly, scalars="exposure", cmap="inferno", clim=(lo, hi),
                            show_scalar_bar=False)
                head = pv.Cylinder(center=(pos[0, 0], pos[0, 1], 0.9), direction=(0, 0, 1),
                                   radius=0.35, height=1.75)
                pl.add_mesh(head, color=pv.LookupTable(cmap="inferno").map_value(t),
                            show_scalar_bar=False)
            pl.add_scalar_bar(title="log10 absorbed power [W]", n_labels=5,
                              width=0.28, height=0.05, position_x=0.68, position_y=0.03)
            print(f"  walks      {len(scene['agents']):6d} agents")
        print(f"  sites      {len(scene.get('sites', [])):6d}")
    else:
        print("  (no scene.json: city only, no sites or walks)")

    pl.enable_lightkit()
    if cam == "hero":
        pl.camera_position = [(430, -430, 300), (0, 0, 25), (0, 0, 1)]
    elif cam == "street":
        pl.camera_position = [(120, -120, 22), (0, 20, 12), (0, 0, 1)]
    else:
        pl.camera_position = "xy"
        pl.camera.zoom(1.3)
    pl.screenshot(str(out_path))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cam", default="hero", choices=["hero", "street", "top"])
    args = ap.parse_args()
    render(args.run_dir, args.out, args.cam)
