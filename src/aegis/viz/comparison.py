"""Side-by-side level comparison of S_ab maps.

Shows how different fidelity levels produce different S_ab distributions
on the same body and paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def plot_level_comparison(
    vertices: np.ndarray,
    results: dict[int, np.ndarray],
    *,
    title: str = "Fidelity level comparison",
    cmap: str = "inferno",
    sab_max: float | None = None,
    out_path: str | Path | None = None,
    show: bool = True,
    backend: str = "matplotlib",
) -> Any:
    """Side-by-side S_ab maps from different fidelity levels.

    Parameters
    ----------
    vertices : (M, 3, 3) triangle vertices
    results : dict mapping level number -> (M,) S_ab array
    title : overall figure title
    cmap : colormap name
    sab_max : shared colorbar max. If None, uses the global max across all levels.
    out_path : save to this path (PNG for matplotlib, HTML for plotly)
    show : display the figure
    backend : "matplotlib" or "plotly"

    Returns
    -------
    Figure object
    """
    if backend == "matplotlib":
        return _matplotlib_comparison(
            vertices,
            results,
            title=title,
            cmap=cmap,
            sab_max=sab_max,
            out_path=out_path,
            show=show,
        )
    elif backend == "plotly":
        return _plotly_comparison(
            vertices,
            results,
            title=title,
            cmap=cmap,
            sab_max=sab_max,
            out_path=out_path,
            show=show,
        )
    raise ValueError(f"Unknown backend: {backend!r}")


def _matplotlib_comparison(
    vertices: np.ndarray,
    results: dict[int, np.ndarray],
    *,
    title: str,
    cmap: str,
    sab_max: float | None,
    out_path: str | Path | None,
    show: bool,
) -> Any:
    """Matplotlib side-by-side front-view projections."""
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import Normalize

    levels = sorted(results.keys())
    n = len(levels)

    if sab_max is None:
        sab_max = max(float(np.max(sab)) for sab in results.values())
    sab_max = max(sab_max, 1e-12)

    norm = Normalize(vmin=0, vmax=sab_max)

    # Sort by depth for painter's algorithm
    centroids_y = np.mean(vertices[:, :, 1], axis=1)
    order = np.argsort(centroids_y)

    fig, axes = plt.subplots(1, n, figsize=(5 * n, 8))
    if n == 1:
        axes = [axes]

    for ax, level in zip(axes, levels, strict=True):
        sab = results[level]
        polys = vertices[order][:, :, [0, 2]]
        colors_arr = sab[order]

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
        ax.set_title(f"Level {level}")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")

        p_abs = float(np.sum(sab * _triangle_areas(vertices)))
        peak = float(np.max(sab))
        ax.text(
            0.02,
            0.02,
            f"P_abs={p_abs * 1e3:.2f} mW\npeak={peak:.3f} W/m\u00b2",
            transform=ax.transAxes,
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            verticalalignment="bottom",
        )

    fig.suptitle(title, fontsize=14, fontweight="bold")
    fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        ax=axes,
        label="S_ab (W/m\u00b2)",
        shrink=0.8,
    )
    plt.tight_layout()

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def _plotly_comparison(
    vertices: np.ndarray,
    results: dict[int, np.ndarray],
    *,
    title: str,
    cmap: str,
    sab_max: float | None,
    out_path: str | Path | None,
    show: bool,
) -> Any:
    """Plotly subplots with 3D meshes for each level."""
    import matplotlib
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    levels = sorted(results.keys())
    n = len(levels)
    n_tri = vertices.shape[0]

    if sab_max is None:
        sab_max = max(float(np.max(sab)) for sab in results.values())
    sab_max = max(sab_max, 1e-12)

    all_v = vertices.reshape(-1, 3)
    i_idx = np.arange(0, 3 * n_tri, 3)
    j_idx = np.arange(1, 3 * n_tri, 3)
    k_idx = np.arange(2, 3 * n_tri, 3)

    colormap_fn = matplotlib.colormaps[cmap]

    fig = make_subplots(
        rows=1,
        cols=n,
        subplot_titles=[f"Level {lv}" for lv in levels],
        specs=[[{"type": "scene"}] * n],
    )

    for col, level in enumerate(levels, 1):
        sab = results[level]
        sab_norm = np.clip(sab / sab_max, 0, 1)
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
            hovertext=[f"L{level}: {s:.3f} W/m\u00b2" for s in sab],
            hoverinfo="text",
            lighting=dict(ambient=0.5, diffuse=0.6, specular=0.15),
            scene=f"scene{col}" if col > 1 else "scene",
        )
        fig.add_trace(mesh, row=1, col=col)

        scene_key = f"scene{col}" if col > 1 else "scene"
        fig.update_layout(
            **{
                scene_key: dict(
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
            }
        )

    fig.update_layout(
        title=title,
        width=500 * n,
        height=700,
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


def _triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute triangle areas from (M, 3, 3) vertices."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
