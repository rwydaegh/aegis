"""S_ab heatmap rendering on body mesh.

Supports Plotly (interactive HTML) and matplotlib (static projection).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def plot_heatmap(
    vertices: np.ndarray,
    sab: np.ndarray,
    *,
    title: str = "Absorbed power density",
    sab_max: float | None = None,
    cmap: str = "inferno",
    out_path: str | Path | None = None,
    show: bool = True,
    backend: str = "plotly",
    camera: dict[str, Any] | None = None,
    width: int = 1200,
    height: int = 900,
) -> Any:
    """Render S_ab as a colored heatmap on the body mesh.

    Parameters
    ----------
    vertices : (M, 3, 3) triangle vertices
    sab : (M,) absorbed power density per triangle [W/m^2]
    title : plot title
    sab_max : colorbar upper limit. If None, uses max(sab).
    cmap : colormap name (matplotlib name)
    out_path : save HTML (plotly) or PNG (matplotlib) to this path
    show : open browser / display figure
    backend : "plotly" or "matplotlib"
    camera : plotly camera dict (eye, up, center)
    width, height : figure dimensions in pixels

    Returns
    -------
    Plotly Figure or matplotlib Figure depending on backend.
    """
    if backend == "plotly":
        return _plotly_heatmap(
            vertices,
            sab,
            title=title,
            sab_max=sab_max,
            cmap=cmap,
            out_path=out_path,
            show=show,
            camera=camera,
            width=width,
            height=height,
        )
    elif backend == "matplotlib":
        return _matplotlib_heatmap(
            vertices,
            sab,
            title=title,
            sab_max=sab_max,
            cmap=cmap,
            out_path=out_path,
            show=show,
        )
    else:
        raise ValueError(f"Unknown backend: {backend!r}. Use 'plotly' or 'matplotlib'.")


def _plotly_heatmap(
    vertices: np.ndarray,
    sab: np.ndarray,
    *,
    title: str,
    sab_max: float | None,
    cmap: str,
    out_path: str | Path | None,
    show: bool,
    camera: dict[str, Any] | None,
    width: int,
    height: int,
) -> Any:
    """Plotly Mesh3d interactive heatmap."""
    import matplotlib
    import plotly.graph_objects as go

    n_tri = vertices.shape[0]
    all_v = vertices.reshape(-1, 3)

    i_idx = np.arange(0, 3 * n_tri, 3)
    j_idx = np.arange(1, 3 * n_tri, 3)
    k_idx = np.arange(2, 3 * n_tri, 3)

    vmax = sab_max if sab_max is not None else float(np.max(sab))
    vmax = max(vmax, 1e-12)  # avoid division by zero
    sab_norm = np.clip(sab / vmax, 0, 1)

    colormap_fn = matplotlib.colormaps[cmap]
    colors_rgba = colormap_fn(sab_norm)
    face_colors = [f"rgb({int(c[0] * 255)},{int(c[1] * 255)},{int(c[2] * 255)})" for c in colors_rgba]

    mesh = go.Mesh3d(
        x=all_v[:, 0],
        y=all_v[:, 1],
        z=all_v[:, 2],
        i=i_idx,
        j=j_idx,
        k=k_idx,
        facecolor=face_colors,
        flatshading=True,
        hovertext=[f"S_ab = {s:.3f} W/m\u00b2" for s in sab],
        hoverinfo="text",
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.15, roughness=0.6),
        lightposition=dict(x=1000, y=1000, z=2000),
    )

    # Colorbar as invisible scatter trace
    colorscale = _inferno_colorscale() if cmap == "inferno" else _generic_colorscale(cmap)
    cbar_trace = go.Scatter3d(
        x=[None],
        y=[None],
        z=[None],
        mode="markers",
        marker=dict(
            size=0.001,
            color=[0, vmax],
            colorscale=colorscale,
            cmin=0,
            cmax=vmax,
            colorbar=dict(title="S_ab (W/m\u00b2)", thickness=20, len=0.7),
            showscale=True,
        ),
        hoverinfo="skip",
        showlegend=False,
    )

    if camera is None:
        camera = dict(
            eye=dict(x=0.0, y=-1.8, z=0.3),
            up=dict(x=0, y=0, z=1),
        )

    peak = float(np.max(sab))
    n_illum = int(np.sum(sab > 0))

    fig = go.Figure(data=[mesh, cbar_trace])
    fig.update_layout(
        title=dict(
            text=(
                f"{title}<br>"
                f"<span style='font-size:13px;color:#555'>"
                f"peak S_ab={peak:.3f} W/m\u00b2 | "
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
            camera=camera,
            bgcolor="rgb(30,30,35)",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        width=width,
        height=height,
        paper_bgcolor="rgb(30,30,35)",
        font_color="white",
    )

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(out_path), include_plotlyjs=True)

    if show:
        fig.show()

    return fig


def _matplotlib_heatmap(
    vertices: np.ndarray,
    sab: np.ndarray,
    *,
    title: str,
    sab_max: float | None,
    cmap: str,
    out_path: str | Path | None,
    show: bool,
) -> Any:
    """Matplotlib 2D projection heatmap (front view)."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize

    vmax = sab_max if sab_max is not None else float(np.max(sab))
    vmax = max(vmax, 1e-12)
    norm = Normalize(vmin=0, vmax=vmax)

    # Front view: project onto XZ plane (Y is depth)
    # Sort triangles by centroid Y (depth) for painter's algorithm
    centroids_y = np.mean(vertices[:, :, 1], axis=1)
    order = np.argsort(centroids_y)  # back to front

    polys = vertices[order][:, :, [0, 2]]  # take X, Z
    colors_arr = sab[order]

    fig, ax = plt.subplots(1, 1, figsize=(8, 10))
    pc = PolyCollection(
        polys,
        array=colors_arr,
        cmap=cmap,
        norm=norm,
        edgecolors="none",
    )
    ax.add_collection(pc)
    ax.autoscale()
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z (m)")
    ax.set_title(title)
    fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="S_ab (W/m\u00b2)")

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def _inferno_colorscale() -> list[list]:
    return [
        [0.0, "rgb(0,0,4)"],
        [0.25, "rgb(87,16,110)"],
        [0.5, "rgb(188,55,84)"],
        [0.75, "rgb(249,142,9)"],
        [1.0, "rgb(252,255,164)"],
    ]


def _generic_colorscale(cmap_name: str) -> list[list]:
    import matplotlib

    cm = matplotlib.colormaps[cmap_name]
    return [
        [i / 10, f"rgb({int(c[0] * 255)},{int(c[1] * 255)},{int(c[2] * 255)})"]
        for i, c in [(j, cm(j / 10)) for j in range(11)]
    ]
