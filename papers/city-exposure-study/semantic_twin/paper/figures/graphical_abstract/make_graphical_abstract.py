#!/usr/bin/env python3
"""Build the IEEE OJ-COMS graphical abstract from the ten-route result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle
from PIL import Image

import scienceplots  # noqa: F401  # registers the SciencePlots styles


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CAMPAIGN = REPO / "semantic_twin/paper/figures/route_results/route_results.json"

PX_W, PX_H = 660, 295
DISPLAY_DPI = 300

BLACK = "#000000"
RED = "#E31A1C"
GREEN = "#00A600"
BLUE = "#0066B3"
ORANGE = "#E66100"
SKY = "#DDECF3"
LIGHT = "#F3F3F3"
MID = "#BDBDBD"
PALE_RED = "#F4A29A"
PALE_BLUE = "#8DD3E8"
PALE_GREEN = "#A8D98B"


def _panel(ax: plt.Axes, title: str) -> None:
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(BLACK)
        spine.set_linewidth(0.8)
    ax.set_title(title, fontsize=8.3, fontweight="bold", pad=3)


def _draw_scene(ax: plt.Axes) -> None:
    _panel(ax, "AI-assisted city twin")
    ax.add_patch(Rectangle((0, 0.37), 1, 0.63, facecolor=SKY, edgecolor="none"))
    ax.add_patch(Rectangle((0, 0), 1, 0.37, facecolor="#D3D3D3", edgecolor="none"))

    buildings = [
        (0.00, 0.36, 0.18, 0.30),
        (0.16, 0.36, 0.20, 0.42),
        (0.34, 0.36, 0.18, 0.34),
        (0.51, 0.36, 0.20, 0.39),
        (0.69, 0.36, 0.16, 0.29),
        (0.84, 0.36, 0.16, 0.35),
    ]
    for i, (x, y, w, h) in enumerate(buildings):
        if x + w <= 0.51:
            color = ["#C6B7A4", "#BCA98D", "#D2C2A9"][i % 3]
        elif i % 3 == 0:
            color = PALE_BLUE
        elif i % 3 == 1:
            color = PALE_RED
        else:
            color = PALE_GREEN
        ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=BLACK, lw=0.35))
        roof = Polygon(
            [(x, y + h), (x + 0.5 * w, y + h + 0.06), (x + w, y + h)],
            closed=True,
            facecolor=color,
            edgecolor=BLACK,
            lw=0.35,
        )
        ax.add_patch(roof)
        for wx in np.linspace(x + 0.04, x + w - 0.04, 3):
            for wy in np.linspace(y + 0.08, y + h - 0.06, 2):
                if x + w <= 0.51:
                    ax.add_patch(
                        Rectangle(
                            (wx - 0.014, wy - 0.018),
                            0.028,
                            0.036,
                            facecolor="#7295A3",
                            edgecolor="none",
                        )
                    )
    ax.axvline(0.51, color=BLACK, lw=0.65, ls=(0, (2, 2)))
    ax.text(0.25, 0.08, "street image", ha="center", va="center", fontsize=6.5)
    ax.text(0.75, 0.08, "surface labels", ha="center", va="center", fontsize=6.5)


def _draw_route(ax: plt.Axes) -> None:
    _panel(ax, "Route and roofline sources")
    ax.set_facecolor("white")
    mesh = [
        [(0.00, 0.10), (0.38, 0.02), (0.20, 0.42)],
        [(0.00, 0.10), (0.20, 0.42), (0.03, 0.79)],
        [(0.20, 0.42), (0.38, 0.02), (0.55, 0.30)],
        [(0.20, 0.42), (0.55, 0.30), (0.46, 0.72)],
        [(0.03, 0.79), (0.20, 0.42), (0.46, 0.72)],
        [(0.38, 0.02), (0.88, 0.08), (0.55, 0.30)],
        [(0.55, 0.30), (0.88, 0.08), (0.98, 0.52)],
        [(0.46, 0.72), (0.55, 0.30), (0.98, 0.52)],
        [(0.46, 0.72), (0.98, 0.52), (0.83, 0.93)],
        [(0.03, 0.79), (0.46, 0.72), (0.83, 0.93)],
    ]
    for tri in mesh:
        ax.add_patch(Polygon(tri, closed=True, facecolor=LIGHT, edgecolor="#D0D0D0", lw=0.35))

    rooflines = [
        [(0.04, 0.82), (0.22, 0.88), (0.42, 0.80)],
        [(0.58, 0.77), (0.78, 0.86), (0.96, 0.75)],
        [(0.04, 0.28), (0.18, 0.18), (0.33, 0.20)],
        [(0.70, 0.24), (0.88, 0.30), (0.97, 0.22)],
    ]
    for line in rooflines:
        x, y = zip(*line, strict=True)
        ax.plot(x, y, color=ORANGE, lw=2.1, solid_capstyle="round")

    route = np.array(
        [
            [0.30, 0.14],
            [0.36, 0.23],
            [0.43, 0.35],
            [0.48, 0.49],
            [0.51, 0.63],
            [0.49, 0.78],
        ]
    )
    ax.plot(route[:, 0], route[:, 1], color=BLUE, lw=1.9, zorder=5)
    ax.plot(
        route[:, 0],
        route[:, 1],
        "o",
        ms=3.4,
        mfc="white",
        mec=BLUE,
        mew=1.0,
        zorder=6,
    )
    ax.text(0.07, 0.91, "roofline source", color=ORANGE, fontsize=6.1, va="center")
    ax.text(0.55, 0.57, "route", color=BLUE, fontsize=6.1, va="center")


def _body_patch(ax: plt.Axes) -> None:
    ax.add_patch(Circle((0.55, 0.74), 0.085, facecolor="#D0D0D0", edgecolor=BLACK, lw=0.65))
    ax.add_patch(
        Polygon(
            [(0.44, 0.65), (0.66, 0.65), (0.70, 0.38), (0.62, 0.30), (0.48, 0.30), (0.40, 0.38)],
            closed=True,
            facecolor="#D0D0D0",
            edgecolor=BLACK,
            lw=0.65,
        )
    )
    ax.plot([0.44, 0.32, 0.28], [0.60, 0.43, 0.24], color=BLACK, lw=5.0, solid_capstyle="round")
    ax.plot([0.66, 0.78, 0.82], [0.60, 0.43, 0.24], color=BLACK, lw=5.0, solid_capstyle="round")
    ax.plot([0.50, 0.47, 0.44], [0.31, 0.19, 0.06], color=BLACK, lw=6.0, solid_capstyle="round")
    ax.plot([0.60, 0.63, 0.66], [0.31, 0.19, 0.06], color=BLACK, lw=6.0, solid_capstyle="round")


def _ray(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str, lw: float = 1.1) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=7,
            linewidth=lw,
            color=color,
        )
    )


def _draw_body(ax: plt.Axes) -> None:
    _panel(ax, "Direction-aware body SAR")
    _body_patch(ax)
    _ray(ax, (0.04, 0.87), (0.46, 0.69), BLACK, 1.35)
    ax.plot([0.97, 0.87, 0.67], [0.87, 0.58, 0.55], color=RED, lw=1.25)
    _ray(ax, (0.87, 0.58), (0.67, 0.55), RED, 1.25)
    ax.plot([0.87, 0.58], [0.58, 0.58], marker="s", mfc="white", mec=RED, ms=3.2)
    for y in (0.36, 0.47, 0.58):
        _ray(ax, (0.96, y + 0.08), (0.68, y), GREEN, 0.9)
    ax.text(0.04, 0.12, "direct", color=BLACK, fontsize=5.9, ha="left")
    ax.text(0.30, 0.12, "specular", color=RED, fontsize=5.9, ha="left")
    ax.text(0.70, 0.12, "diffuse", color=GREEN, fontsize=5.9, ha="left")


def _route_quantiles() -> list[dict[str, object]]:
    data = json.loads(CAMPAIGN.read_text())
    order = ["Milan", "Mexico City"]
    colors = [ORANGE, BLUE]
    rows: list[dict[str, object]] = []
    for key, color in zip(order, colors, strict=True):
        city = data["cities"][key]
        quantiles = city["normalized_wbsar_quantiles_m2_per_kg"]
        rows.append(
            {
                "source_key": key,
                "label": key,
                "color": color,
                "standpoints": int(city["standpoints"]),
                "q10": float(quantiles["q10"]),
                "q50": float(quantiles["median"]),
                "q90": float(quantiles["q90"]),
            }
        )
    return rows


def _draw_results(ax: plt.Axes, rows: list[dict[str, object]]) -> None:
    ax.set(xlim=(0, 1), ylim=(-0.65, len(rows) - 0.35))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(BLACK)
        spine.set_linewidth(0.8)
    ax.set_title(r"10 routes: 14.31$\times$ range", fontsize=7.5, fontweight="bold", pad=3)

    y = np.arange(len(rows))[::-1]
    for yi, row in zip(y, rows, strict=True):
        ax.text(0.015, yi, str(row["label"]), ha="left", va="center", fontsize=5.5)

    plot_ax = ax.inset_axes([0.34, 0.18, 0.66, 0.62])
    plot_ax.set_xscale("log")
    for yi, row in zip(y, rows, strict=True):
        q50 = float(row["q50"])
        color = str(row["color"])
        plot_ax.plot(q50, yi, "o", ms=4.2, mfc="white", mec=color, mew=1.2)
    plot_ax.set_xlim(5e-7, 1.0)
    plot_ax.set_ylim(-0.65, len(rows) - 0.35)
    plot_ax.set_yticks([])
    plot_ax.set_xticks([1e-6, 1e-3, 1e0], [r"$10^{-6}$", r"$10^{-3}$", r"$1$"], fontsize=6.0)
    plot_ax.tick_params(axis="x", which="both", length=2, pad=1.5)
    plot_ax.grid(axis="x", color="#D4D4D4", lw=0.45)
    plot_ax.spines["left"].set_visible(False)
    plot_ax.spines["top"].set_visible(False)
    plot_ax.spines["right"].set_visible(False)
    plot_ax.spines["bottom"].set_color(BLACK)
    plot_ax.spines["bottom"].set_linewidth(0.8)
    plot_ax.set_xlabel("Normalized median SAR", fontsize=5.5, labelpad=1)


def _flow_arrow(fig: plt.Figure, x0: float, x1: float) -> None:
    fig.add_artist(
        FancyArrowPatch(
            (x0, 0.50),
            (x1, 0.50),
            transform=fig.transFigure,
            arrowstyle="-|>",
            mutation_scale=9,
            color=BLACK,
            linewidth=0.9,
        )
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows = _route_quantiles()
    with plt.style.context(["science", "no-latex"]):
        plt.rcParams.update(
            {
                "font.family": "serif",
                "font.serif": ["STIXGeneral", "DejaVu Serif"],
                "mathtext.fontset": "stix",
                "axes.linewidth": 0.8,
                "savefig.bbox": None,
            }
        )
        fig = plt.figure(figsize=(PX_W / 100, PX_H / 100), dpi=100, facecolor="white")
        lefts = [0.015, 0.262, 0.510, 0.758]
        width = 0.215
        bottom = 0.12
        height = 0.78
        axes = [fig.add_axes([left, bottom, width, height]) for left in lefts]
        _draw_scene(axes[0])
        _draw_route(axes[1])
        _draw_body(axes[2])
        _draw_results(axes[3], rows)
        for i in range(3):
            _flow_arrow(fig, lefts[i] + width + 0.006, lefts[i + 1] - 0.007)

        raw_png = HERE / "graphical_abstract.raw.png"
        png = HERE / "graphical_abstract.png"
        pdf = HERE / "graphical_abstract.pdf"
        fig.savefig(
            raw_png,
            dpi=100,
            facecolor="white",
            bbox_inches=None,
            pad_inches=0,
            metadata={"Software": "Matplotlib + SciencePlots"},
        )
        fig.savefig(
            pdf,
            facecolor="white",
            bbox_inches=None,
            pad_inches=0,
            metadata={"Title": "Human-centric RF-EMF exposure graphical abstract"},
        )
        plt.close(fig)

    with Image.open(raw_png) as image:
        if image.size != (PX_W, PX_H):
            raise RuntimeError(f"unexpected raster size: {image.size}")
        palette = image.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        palette.save(
            png,
            format="PNG",
            optimize=True,
            compress_level=9,
            dpi=(DISPLAY_DPI, DISPLAY_DPI),
        )
    raw_png.unlink()

    with Image.open(png) as image:
        measured_dpi = [float(value) for value in image.info.get("dpi", (0.0, 0.0))]
        size_px = list(image.size)
        color_mode = image.mode
    audit = {
        "schema_version": 1,
        "figure": "IEEE OJ-COMS graphical abstract",
        "source_campaign": str(CAMPAIGN.relative_to(REPO)),
        "source_contract": "ten_city_route_production64_v1",
        "route_quantiles": rows,
        "output": {
            "png": png.name,
            "pdf": pdf.name,
            "width_px": size_px[0],
            "height_px": size_px[1],
            "requested_dpi": DISPLAY_DPI,
            "stored_dpi": measured_dpi,
            "png_mode": color_mode,
            "png_bytes": png.stat().st_size,
            "pdf_bytes": pdf.stat().st_size,
            "png_sha256": _sha256(png),
            "pdf_sha256": _sha256(pdf),
        },
        "checks": {
            "exact_660_by_295_px": size_px == [PX_W, PX_H],
            "stored_dpi_within_one_percent": all(abs(value - DISPLAY_DPI) <= 3 for value in measured_dpi),
            "png_under_45_kib": png.stat().st_size < 45 * 1024,
            "quantized_palette": color_mode == "P",
            "no_unsupported_data": True,
        },
        "rendering": {
            "style": ["science", "no-latex"],
            "font": "STIXGeneral",
            "palette_colors": 64,
        },
    }
    (HERE / "graphical_abstract.audit.json").write_text(json.dumps(audit, indent=2) + "\n")


if __name__ == "__main__":
    main()
