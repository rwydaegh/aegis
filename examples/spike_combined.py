"""
Combined spike: body mesh with dosimetry heatmap inside a voxel environment.

This is the Phase -1 proof of concept showing the full AEGIS visualization:
- Thelonious phantom with Sab heatmap (Spike B)
- Synthetic urban voxel environment (Spike A)
- Both rendered together in an interactive Plotly scene

Usage
-----
    py -3.12 examples/spike_combined.py
    py -3.12 examples/spike_combined.py --voxel-json path/to/voxels.json
"""

from __future__ import annotations

import argparse
import time
import webbrowser
from pathlib import Path

import numpy as np

# Reuse spike modules
from spike_b_heatmap import (
    load_stl_binary,
    triangle_areas,
    tissue_T0,
    compute_sab,
)
from spike_a_voxel_env import VoxelScene


def render_combined(
    vertices: np.ndarray,
    normals: np.ndarray,
    sab: np.ndarray,
    T_0: float,
    S_inc: float,
    voxel_scene: VoxelScene,
    out_path: Path,
    body_offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Render body mesh + voxel environment in a single Plotly scene."""
    import plotly.graph_objects as go
    from matplotlib.cm import inferno

    n_tri = vertices.shape[0]

    # --- Body mesh trace ---
    offset = np.array(body_offset)
    body_v = vertices.copy().reshape(-1, 3) + offset

    i_idx = np.arange(0, 3 * n_tri, 3)
    j_idx = np.arange(1, 3 * n_tri, 3)
    k_idx = np.arange(2, 3 * n_tri, 3)

    sab_max = S_inc * T_0
    sab_norm = np.clip(sab / sab_max, 0, 1)
    colors_rgba = inferno(sab_norm)
    face_colors = [
        f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})"
        for c in colors_rgba
    ]

    body_mesh = go.Mesh3d(
        x=body_v[:, 0],
        y=body_v[:, 1],
        z=body_v[:, 2],
        i=i_idx,
        j=j_idx,
        k=k_idx,
        facecolor=face_colors,
        flatshading=True,
        hovertext=[f"Sab = {s:.3f} W/m²" for s in sab],
        hoverinfo="text",
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.15, roughness=0.6),
        lightposition=dict(x=100, y=100, z=200),
        name="Body (Sab)",
    )

    # --- Voxel environment trace ---
    pos = voxel_scene.positions
    mat_colors = {
        "concrete": "rgb(180,180,180)",
        "asphalt": "rgb(100,100,100)",
        "vegetation": "rgb(40,160,40)",
        "water": "rgb(30,100,220)",
        "brick": "rgb(200,80,50)",
        "glass": "rgb(150,210,240)",
        "unknown": "rgb(200,200,200)",
    }
    voxel_color_strs = [mat_colors.get(m, "rgb(200,200,200)") for m in voxel_scene.materials]

    env_scatter = go.Scatter3d(
        x=pos[:, 0],
        y=pos[:, 1],
        z=pos[:, 2],
        mode="markers",
        marker=dict(size=2.5, color=voxel_color_strs, opacity=0.6),
        hovertext=[f"Material: {m}" for m in voxel_scene.materials],
        hoverinfo="text",
        name="Environment",
    )

    # --- Colorbar ---
    colorscale = [
        [0.0, "rgb(0,0,4)"],
        [0.25, "rgb(87,16,110)"],
        [0.5, "rgb(188,55,84)"],
        [0.75, "rgb(249,142,9)"],
        [1.0, "rgb(252,255,164)"],
    ]
    cbar_trace = go.Scatter3d(
        x=[None], y=[None], z=[None], mode="markers",
        marker=dict(
            size=0.001, color=[0, sab_max], colorscale=colorscale,
            cmin=0, cmax=sab_max,
            colorbar=dict(title="Sab (W/m²)", thickness=20, len=0.5),
            showscale=True,
        ),
        hoverinfo="skip", showlegend=False,
    )

    fig = go.Figure(data=[env_scatter, body_mesh, cbar_trace])
    fig.update_layout(
        title=dict(
            text=(
                "AEGIS: Body dosimetry in urban environment<br>"
                "<span style='font-size:12px;color:#888'>"
                f"S_inc={S_inc} W/m² | T0={T_0:.4f} | "
                f"{n_tri:,} body triangles | {voxel_scene.n_voxels:,} env voxels"
                "</span>"
            ),
            x=0.5, font=dict(size=16),
        ),
        scene=dict(
            xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)",
            aspectmode="data",
            camera=dict(eye=dict(x=1.2, y=-1.5, z=0.6), up=dict(x=0, y=0, z=1)),
            bgcolor="rgb(20,20,25)",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        width=1400, height=900,
        paper_bgcolor="rgb(20,20,25)",
        font_color="white",
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0.5)"),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs=True)
    print(f"  Wrote: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Combined spike: body + environment")
    parser.add_argument("--stl", default=None)
    parser.add_argument("--voxel-json", default=None)
    parser.add_argument("--sinc", type=float, default=10.0)
    parser.add_argument("--freq", type=float, default=28e9)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    data_dir = root.parent / "data"
    stl_path = Path(args.stl) if args.stl else data_dir / "thelonious.stl"
    out_dir = root / "examples" / "_output"

    eps_r, sigma = 17.0, 25.0
    T_0 = tissue_T0(eps_r, sigma, args.freq)
    k_hat = np.array([0.0, -1.0, 0.0])

    print("=" * 60)
    print("  COMBINED SPIKE: Body + Environment")
    print("=" * 60)

    # Load body mesh
    print("\nLoading body mesh...")
    vertices, normals, centroids = load_stl_binary(stl_path)
    areas = triangle_areas(vertices)
    n_orig = len(areas)
    print(f"  {n_orig:,} triangles")

    # Compute Sab on full mesh
    sab = compute_sab(normals, k_hat, T_0, args.sinc)
    print(f"  Peak Sab: {np.max(sab):.4f} W/m²")

    # Subsample for combined view (keep Plotly responsive)
    max_tri = 4000
    if n_orig > max_tri:
        step = n_orig // max_tri
        idx = np.arange(0, n_orig, step)[:max_tri]
        vertices = vertices[idx]
        normals = normals[idx]
        sab = sab[idx]
        areas = areas[idx]
        print(f"  Subsampled to {len(idx):,} triangles for combined view")

    # Load or generate environment
    if args.voxel_json:
        print(f"\nLoading voxel environment: {args.voxel_json}")
        voxel_scene = VoxelScene.from_json(args.voxel_json)
    else:
        print("\nGenerating synthetic urban environment...")
        voxel_scene = VoxelScene.synthetic_urban(size=15, voxel_size=1.0)
    print(f"  {voxel_scene.n_voxels:,} voxels")

    # Place body in the scene
    body_zmin = vertices[:, :, 2].min()
    body_offset = (0.0, 0.0, 1.0 - body_zmin)

    # Render combined
    print("\nRendering combined scene...")
    t0 = time.perf_counter()
    out_path = out_dir / "spike_combined.html"
    render_combined(
        vertices, normals, sab, T_0, args.sinc,
        voxel_scene, out_path,
        body_offset=body_offset,
    )
    print(f"  Render time: {time.perf_counter() - t0:.1f} s")

    if not args.no_open:
        webbrowser.open(str(out_path))

    print("\nDone.")


if __name__ == "__main__":
    main()
