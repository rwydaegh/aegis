"""
Spike B: Interactive dosimetry heatmap in the browser.

Loads the Thelonious phantom, computes Sab for a frontal plane wave,
and renders an interactive 3D mesh with per-face color in Plotly.

Usage
-----
    py -3.12 examples/spike_b_heatmap.py
    py -3.12 examples/spike_b_heatmap.py --approach plotly
    py -3.12 examples/spike_b_heatmap.py --approach pyvista
"""

from __future__ import annotations

import argparse
import struct
import time
import webbrowser
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Geometry helpers (inlined from scripts/_geom.py to keep spike standalone)
# ---------------------------------------------------------------------------

def load_stl_binary(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load binary STL -> vertices (N,3,3), normals (N,3), centroids (N,3)."""
    with open(str(path), "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        vertices = np.zeros((n, 3, 3), dtype=np.float64)
        normals = np.zeros((n, 3), dtype=np.float64)
        for i in range(n):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)
    centroids = np.mean(vertices, axis=1)
    nrm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(nrm > 0, nrm, 1.0)
    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute area of each triangle from (N, 3, 3) vertex array."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)


# ---------------------------------------------------------------------------
# Tissue / Fresnel (inlined from scripts/_fresnel.py)
# ---------------------------------------------------------------------------

EPS_0 = 8.854187817e-12


def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    omega = 2 * np.pi * freq_hz
    eps_c = eps_r - 1j * sigma / (omega * EPS_0)
    n = np.sqrt(eps_c)
    return -n if np.real(n) < 0 else n


def tissue_T0(eps_r: float, sigma: float, freq_hz: float) -> float:
    n = n_complex(eps_r, sigma, freq_hz)
    r = (1 - n) / (1 + n)
    return float(1 - abs(r) ** 2)


# ---------------------------------------------------------------------------
# Dosimetry computation
# ---------------------------------------------------------------------------

def compute_sab(
    normals: np.ndarray,
    k_hat: np.ndarray,
    T_0: float,
    S_inc: float,
) -> np.ndarray:
    """Sab(r) = S_inc * T_0 * ReLU[n_hat . (-k_hat)]"""
    mu = normals @ (-k_hat)
    return S_inc * T_0 * np.maximum(0, mu)


# ---------------------------------------------------------------------------
# Plotly visualization
# ---------------------------------------------------------------------------

def render_plotly(
    vertices: np.ndarray,
    normals: np.ndarray,
    sab: np.ndarray,
    T_0: float,
    S_inc: float,
    out_path: Path,
) -> None:
    """Create interactive Plotly Mesh3d HTML with per-face Sab colors."""
    import plotly.graph_objects as go

    n_tri = vertices.shape[0]
    all_v = vertices.reshape(-1, 3)

    # Build face index arrays (each triangle uses 3 consecutive vertices)
    i_idx = np.arange(0, 3 * n_tri, 3)
    j_idx = np.arange(1, 3 * n_tri, 3)
    k_idx = np.arange(2, 3 * n_tri, 3)

    # Normalize Sab to [0, 1] for colormap
    sab_max = S_inc * T_0
    sab_norm = np.clip(sab / sab_max, 0, 1)

    # Map to inferno colormap via matplotlib
    from matplotlib.cm import inferno
    colors_rgba = inferno(sab_norm)
    face_colors = [
        f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})"
        for c in colors_rgba
    ]

    mesh = go.Mesh3d(
        x=all_v[:, 0],
        y=all_v[:, 1],
        z=all_v[:, 2],
        i=i_idx,
        j=j_idx,
        k=k_idx,
        facecolor=face_colors,
        flatshading=True,
        hovertext=[f"Sab = {s:.3f} W/m²" for s in sab],
        hoverinfo="text",
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.15, roughness=0.6),
        lightposition=dict(x=1000, y=1000, z=2000),
    )

    # Invisible trace for colorbar
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
            size=0.001,
            color=[0, sab_max],
            colorscale=colorscale,
            cmin=0, cmax=sab_max,
            colorbar=dict(
                title="Sab (W/m²)",
                thickness=20,
                len=0.7,
            ),
            showscale=True,
        ),
        hoverinfo="skip",
        showlegend=False,
    )

    n_illum = int(np.sum(sab > 0))
    peak_sab = float(np.max(sab))

    fig = go.Figure(data=[mesh, cbar_trace])
    fig.update_layout(
        title=dict(
            text=(
                f"Spike B: Dosimetry heatmap (Plotly)<br>"
                f"<span style='font-size:13px;color:#555'>"
                f"S_inc={S_inc} W/m² | T0={T_0:.4f} | "
                f"peak Sab={peak_sab:.3f} W/m² | "
                f"illuminated: {n_illum:,}/{n_tri:,}</span>"
            ),
            x=0.5,
            font=dict(size=16),
        ),
        scene=dict(
            xaxis_visible=False,
            yaxis_visible=False,
            zaxis_visible=False,
            aspectmode="data",
            camera=dict(
                eye=dict(x=0.0, y=-1.8, z=0.3),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="rgb(30,30,35)",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        width=1200,
        height=900,
        paper_bgcolor="rgb(30,30,35)",
        font_color="white",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs=True)
    print(f"  Wrote: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# PyVista / Trame visualization
# ---------------------------------------------------------------------------

def render_pyvista(
    vertices: np.ndarray,
    normals: np.ndarray,
    sab: np.ndarray,
    T_0: float,
    S_inc: float,
    out_path: Path,
) -> None:
    """Create interactive PyVista/Trame visualization."""
    import pyvista as pv

    n_tri = vertices.shape[0]

    # Build PolyData from triangles
    # faces format: [3, v0, v1, v2, 3, v0, v1, v2, ...]
    all_v = vertices.reshape(-1, 3)
    faces = np.column_stack([
        np.full(n_tri, 3),
        np.arange(0, 3 * n_tri, 3),
        np.arange(1, 3 * n_tri, 3),
        np.arange(2, 3 * n_tri, 3),
    ]).ravel()

    mesh = pv.PolyData(all_v, faces)
    mesh.cell_data["Sab"] = sab

    # Launch interactive plotter
    pl = pv.Plotter()
    pl.add_mesh(
        mesh,
        scalars="Sab",
        cmap="inferno",
        clim=[0, S_inc * T_0],
        show_edges=False,
        lighting=True,
        scalar_bar_args=dict(title="Sab (W/m²)"),
    )
    pl.set_background("black")
    pl.camera_position = [(0, -0.8, 0.2), (0, 0, 0.4), (0, 0, 1)]

    # Try Trame (browser-based) first, fall back to desktop
    try:
        from pyvista.trame import show as trame_show
        print("  Launching Trame (browser-based) viewer...")
        # Export to static HTML for comparison
        pl.export_html(str(out_path))
        print(f"  Wrote: {out_path}")
        pl.show()
    except ImportError:
        print("  Trame not available, using desktop PyVista viewer...")
        pl.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Spike B: dosimetry heatmap in browser")
    parser.add_argument("--stl", default=None, help="Path to STL file")
    parser.add_argument("--sinc", type=float, default=10.0, help="Incident power density (W/m²)")
    parser.add_argument("--freq", type=float, default=28e9, help="Frequency (Hz)")
    parser.add_argument("--approach", choices=["plotly", "pyvista", "both"], default="plotly")
    parser.add_argument("--k-hat", nargs=3, type=float, default=[0, -1, 0],
                        help="Wave direction (default: frontal)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    # Data is one level above aegis repo
    data_dir = root.parent / "data"
    stl_path = Path(args.stl) if args.stl else data_dir / "thelonious.stl"

    if not stl_path.exists():
        print(f"ERROR: STL file not found: {stl_path}")
        print("Set --stl or ensure data/thelonious.stl exists")
        return

    k_hat = np.array(args.k_hat, dtype=np.float64)
    k_hat = k_hat / np.linalg.norm(k_hat)

    # Skin at 28 GHz
    eps_r, sigma = 17.0, 25.0
    T_0 = tissue_T0(eps_r, sigma, args.freq)

    print("=" * 60)
    print("  SPIKE B: Dosimetry heatmap")
    print("=" * 60)
    print(f"  STL:    {stl_path}")
    print(f"  S_inc:  {args.sinc} W/m²")
    print(f"  freq:   {args.freq/1e9:.0f} GHz")
    print(f"  T_0:    {T_0:.4f}")
    print(f"  k_hat:  {k_hat}")

    # Load mesh
    print("\nLoading mesh...")
    t0 = time.perf_counter()
    vertices, normals, centroids = load_stl_binary(stl_path)
    areas = triangle_areas(vertices)
    t_load = time.perf_counter() - t0
    n_tri = len(areas)
    print(f"  {n_tri:,} triangles, {float(np.sum(areas))*1e4:.1f} cm² surface area")
    print(f"  Load time: {t_load*1e3:.0f} ms")

    # Compute Sab
    print("\nComputing Sab...")
    t0 = time.perf_counter()
    sab = compute_sab(normals, k_hat, T_0, args.sinc)
    t_comp = time.perf_counter() - t0

    n_illum = int(np.sum(sab > 0))
    P_abs = float(np.sum(sab * areas))
    print(f"  Peak Sab:     {np.max(sab):.4f} W/m²")
    print(f"  Illuminated:  {n_illum:,} / {n_tri:,} triangles")
    print(f"  P_abs:        {P_abs*1e3:.3f} mW")
    print(f"  Compute time: {t_comp*1e6:.0f} us")

    # Render
    out_dir = root / "examples" / "_output"

    if args.approach in ("plotly", "both"):
        print("\n--- Plotly approach ---")
        out_plotly = out_dir / "spike_b_plotly.html"
        t0 = time.perf_counter()
        render_plotly(vertices, normals, sab, T_0, args.sinc, out_plotly)
        t_render = time.perf_counter() - t0
        print(f"  Render time: {t_render:.1f} s")
        if not args.no_open:
            webbrowser.open(str(out_plotly))

    if args.approach in ("pyvista", "both"):
        print("\n--- PyVista approach ---")
        out_pv = out_dir / "spike_b_pyvista.html"
        try:
            render_pyvista(vertices, normals, sab, T_0, args.sinc, out_pv)
        except ImportError:
            print("  PyVista not installed. Run: pip install pyvista[all] trame")

    print("\nDone.")


if __name__ == "__main__":
    main()
