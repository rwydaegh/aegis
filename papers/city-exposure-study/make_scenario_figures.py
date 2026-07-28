"""Scenario figures for the ten-city study.

Renders, from each city's run artifacts (results/cities/<city>/):
- the traced geometry top-down (buildings colored by height, roads, water),
- the deployment (site markers + sector wedges at their true azimuths),
- every agent's walk, colored by its time-averaged absorbed power.

Outputs figures/cities_scenarios.{pdf,png} (2x5 grid, shared exposure scale)
and figures/scenario_<city>.{pdf,png} (single-city detail with a legend).

Usage:
    python papers/city-exposure-study/make_scenario_figures.py \
        [--results results/cities] [--detail ghent]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LogNorm
from matplotlib.patches import Wedge

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "ieee"])
except Exception:
    pass

HERE = Path(__file__).parent
FIGS = HERE / "figures"

# Exposure color scale shared across every panel so cities are comparable.
EXPO_NORM = LogNorm(vmin=1e-12, vmax=1e-3)
EXPO_CMAP = plt.get_cmap("plasma")

_LAYERS = [
    # (glob pattern, facecolor or "height", zorder)
    ("scene_ground.ply", "0.96", 0),
    ("scene_asphalt.ply", "0.88", 1),
    ("scene_water.ply", "#cadfef", 1),
    ("scene_wood.ply", "height", 2),
    ("scene_concrete.ply", "height", 2),
]


def _draw_mesh(ax, city_dir: Path, height_cmap, height_norm=None):
    """Draw the traced meshes top-down. Building height maps to gray level with
    a per-city norm (0 to the city's p97 roof height) so Manhattan does not
    saturate to solid black while Amsterdam stays readable; the gray ramp is
    capped at 0.8 so the tallest roof is dark, never ink-black."""
    height_layers = []
    for fname, style, z in _LAYERS:
        fp = city_dir / "city" / fname
        if not fp.exists():
            continue
        m = trimesh.load(fp, process=False)
        v = np.asarray(m.vertices)
        f = np.asarray(m.faces)
        if f.size == 0:
            continue
        tris = v[f][:, :, :2]
        zmax = v[f][:, :, 2].max(axis=1)
        if style == "height":
            height_layers.append((tris, zmax, z))
        else:
            ax.add_collection(PolyCollection(tris, facecolors=style, edgecolors="none", antialiaseds=False, zorder=z))
    if not height_layers:
        return
    if height_norm is None:
        all_z = np.concatenate([zm for _, zm, _ in height_layers])
        top = float(np.percentile(all_z[all_z > 1.0], 97)) if np.any(all_z > 1.0) else 20.0
        height_norm = plt.Normalize(0.0, max(top, 10.0))
    for tris, zmax, z in height_layers:
        order = np.argsort(zmax)
        colors = height_cmap(0.08 + 0.72 * np.clip(height_norm(np.maximum(zmax[order], 0.0)), 0, 1))
        ax.add_collection(
            PolyCollection(tris[order], facecolors=colors, edgecolors="none", antialiaseds=False, zorder=z)
        )


def _draw_sites(ax, scene: dict, wedge_r: float, lw: float = 0.5, ms: float = 14):
    for s in scene.get("sites", []):
        x, y = s["position"][0], s["position"][1]
        for sec in s.get("sectors", []):
            az = sec["boresight_az_deg"]
            half = sec["az_coverage_deg"] / 2.0
            ax.add_patch(
                Wedge(
                    (x, y), wedge_r, az - half, az + half, facecolor="#c1121f", alpha=0.12, edgecolor="none", zorder=3
                )
            )
            ang = np.radians(az)
            ax.plot(
                [x, x + wedge_r * np.cos(ang)],
                [y, y + wedge_r * np.sin(ang)],
                color="#c1121f",
                lw=lw,
                alpha=0.6,
                zorder=3,
            )
        ax.scatter([x], [y], marker="^", s=ms, c="#c1121f", edgecolors="black", linewidths=0.4, zorder=5)


def _draw_agents(ax, scene: dict, lw: float = 0.9):
    segs, colors, user_ends = [], [], []
    for a in scene.get("agents", []):
        pos = np.asarray(a["positions"], dtype=float)
        if pos.shape[0] < 2:
            continue
        e = a.get("exposure_w")
        e = max(float(e), EXPO_NORM.vmin) if e is not None else EXPO_NORM.vmin
        segs.append(pos)
        colors.append(EXPO_CMAP(EXPO_NORM(e)))
        if a.get("is_user"):
            user_ends.append(pos[-1])
    ax.add_collection(LineCollection(segs, colors=colors, linewidths=lw, zorder=4, capstyle="round"))
    if user_ends:
        ue = np.asarray(user_ends)
        ax.scatter(ue[:, 0], ue[:, 1], s=3.5, c="black", marker="o", zorder=5, linewidths=0)


def _panel(ax, city_dir: Path, radius: float, wedge_r: float, height_cmap, lw=0.9):
    scene = json.loads((city_dir / "scene.json").read_text())
    _draw_mesh(ax, city_dir, height_cmap)
    _draw_agents(ax, scene, lw=lw)
    _draw_sites(ax, scene, wedge_r)
    ax.set_xlim(-radius, radius)
    ax.set_ylim(-radius, radius)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    return scene


def grid_figure(results: Path, cities: list[dict], radius: float):
    height_cmap = plt.get_cmap("Greys")
    fig, axes = plt.subplots(2, 5, figsize=(7.16, 3.35))
    for ax, c in zip(axes.ravel(), cities, strict=False):
        name = c["name"]
        _panel(ax, results / name, radius, wedge_r=35.0, height_cmap=height_cmap, lw=0.7)
        med = c.get("median")
        ax.set_title(f"{name.replace('_', ' ').title()}", fontsize=6, pad=2)
        ax.text(
            0.03,
            0.03,
            f"med {med:.0e} W",
            transform=ax.transAxes,
            fontsize=4.5,
            va="bottom",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=0.6),
        )
    for ax in axes.ravel()[len(cities) :]:
        ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.90, top=0.94, bottom=0.02, wspace=0.05, hspace=0.12)
    cax = fig.add_axes([0.915, 0.12, 0.015, 0.72])
    sm = plt.cm.ScalarMappable(norm=EXPO_NORM, cmap=EXPO_CMAP)
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("per-person absorbed power [W]", fontsize=6)
    cb.ax.tick_params(labelsize=5)
    fig.savefig(FIGS / "cities_scenarios.pdf")
    fig.savefig(FIGS / "cities_scenarios.png", dpi=300)
    plt.close(fig)
    print(f"wrote {FIGS / 'cities_scenarios'}.pdf/.png")


def detail_figure(results: Path, name: str, radius: float):
    height_cmap = plt.get_cmap("Greys")
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    _panel(ax, results / name, radius, wedge_r=60.0, height_cmap=height_cmap, lw=1.3)
    ax.set_title(f"{name.replace('_', ' ').title()}: deployment and walks", fontsize=8)
    sm = plt.cm.ScalarMappable(norm=EXPO_NORM, cmap=EXPO_CMAP)
    cb = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("per-person absorbed power [W]", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    # legend proxies
    from matplotlib.lines import Line2D

    handles = [
        Line2D([], [], marker="^", color="#c1121f", mec="black", mew=0.4, ls="", ms=5, label="site (3 sectors)"),
        Line2D([], [], color=EXPO_CMAP(0.7), lw=1.3, label="pedestrian walk"),
        Line2D([], [], marker="o", color="black", ls="", ms=2.5, label="served user"),
    ]
    ax.legend(handles=handles, fontsize=5.5, loc="lower right", frameon=True, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(FIGS / f"scenario_{name}.pdf")
    fig.savefig(FIGS / f"scenario_{name}.png", dpi=300)
    plt.close(fig)
    print(f"wrote {FIGS / f'scenario_{name}'}.pdf/.png")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/cities")
    ap.add_argument("--detail", default="ghent")
    ap.add_argument("--radius", type=float, default=190.0)
    args = ap.parse_args(argv)
    results = Path(args.results)
    FIGS.mkdir(parents=True, exist_ok=True)

    summary = json.loads((results / "cities_summary.json").read_text())
    cities = summary.get("cities", [])
    if not cities:
        raise SystemExit("no cities in summary")
    grid_figure(results, cities, args.radius)
    detail_figure(results, args.detail, args.radius)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
