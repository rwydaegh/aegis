"""Figure 24: the diffraction hole, bounded on the geometry that was traced.

The tracer has no diffraction term. This figure is the defence, and the defence
is a computation on the same meshes and the same standpoints rather than an
appeal to the literature. Everything plotted comes from
``outputs/diffraction_bound/*_diffraction_bound.json``, written by
``bound_diffraction.py``, and from the production location records in
``outputs/exposure_korenmarkt/city250_corrected_*_15ghz_locations.jsonl``.

Panel a is the construction, one standpoint's sky mask with every shadowed
direction carrying its knife edge gain. Panel b is the validation, the same mask
integrated over the visible directions against the production Monte Carlo. Panel
c is the bound over all sixty standpoints at two frequencies. Panel d is the
concession, which is that the bound is not small under the street small cell
model and is largest where the exposure itself is smallest.

    /home/user/aegis/.venv/bin/python FIGURES/make_diffraction_bound_figure.py

Writes PDF for the paper and PNG for looking at. The mask of panel a is cast
once and cached beside the bound outputs.
"""

from __future__ import annotations

import json
import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

from bound_diffraction import direction_grid, knife_edge_loss_db  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
BOUND = ROOT / "outputs" / "diffraction_bound"
EXPOSURE = ROOT / "outputs" / "exposure_korenmarkt"
MASK_CACHE = BOUND / "korenmarkt_mask_panel.npz"

SITES = {
    "korenmarkt": "Korenmarkt",
    "brussels_grandplace": "Grand-Place",
    "newyork_timessquare": "Times Square",
}
MODELS = {
    "isotropic": "isotropic",
    "rooftop": "macro rooftop",
    "street_small_cell": "street small cell",
}
COLOUR = {"isotropic": "#2f6fb5", "rooftop": "#d1622b", "street_small_cell": "#6a4c93"}
MARKER = {"korenmarkt": "o", "brussels_grandplace": "s", "newyork_timessquare": "^"}
INK = "#1a1a1a"
MUTED = "#8a8f98"

LIGHT_M_S = 299_792_458.0


# ---------------------------------------------------------------- data loading


def load_bounds() -> dict[str, dict]:
    return {site: json.loads((BOUND / f"{site}_diffraction_bound.json").read_text()) for site in SITES}


def load_locations(site: str) -> list[dict]:
    """Production records. A few lines are torn, so parse tolerantly."""
    out = []
    for line in (EXPOSURE / f"city250_corrected_{site}_15ghz_locations.jsonl").read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def uplift_db(row: dict, model: str, band: str) -> float:
    """Uplift on chi from the diffracted term, in dB.

    The reported bound multiplies the zero bounce diffracted term by the
    standpoint's own multipath gain chi/chi_direct before adding it to chi, so
    the ratio reduces to the diffracted term over the traced direct term.
    Returns nan where the direct term is exactly zero, which happens where the
    model's whole elevation support is occluded.
    """
    direct = row[f"{model}_direct_traced"]
    if direct <= 0.0:
        return float("nan")
    return 10.0 * np.log10(1.0 + row[f"{model}_diff_edge_{band}"] / direct)


# ------------------------------------------------------------------ panel a


def build_mask(n_azimuth: int = 720, n_elevation: int = 600) -> dict:
    """Cast the production grid at the most enclosed Korenmarkt standpoint."""
    if MASK_CACHE.exists():
        with np.load(MASK_CACHE) as data:
            return {k: data[k] for k in data.files}

    from scipy.spatial import cKDTree

    from semantic_twin.propagation.geometry import MitsubaGeometry

    payload = json.loads((BOUND / "korenmarkt_diffraction_bound.json").read_text())
    # Read for its side effect: the run this figure describes has to exist.
    (EXPOSURE / "city250_corrected_korenmarkt_15ghz_manifest.json").read_text()
    records = load_locations("korenmarkt")
    records.sort(key=lambda r: r["sky_fraction"])
    record = records[0]
    assert record["index"] == payload["standpoints"][0]["index"]

    unit, omega, _ = direction_grid(n_azimuth, n_elevation, 0.05)
    geometry = MitsubaGeometry(pathlib.Path(payload["mesh"]))
    origin = np.array([record["x"], record["y"], record["z"]], dtype=np.float64)
    origins = np.broadcast_to(origin, unit.shape)
    hit = np.zeros(unit.shape[0], dtype=bool)
    distance = np.zeros(unit.shape[0])
    for start in range(0, unit.shape[0], 400_000):
        stop = min(start + 400_000, unit.shape[0])
        h, t, _, _ = geometry.intersect(
            np.ascontiguousarray(origins[start:stop]), np.ascontiguousarray(unit[start:stop])
        )
        hit[start:stop] = h
        distance[start:stop] = np.where(h, t, np.inf)

    sky = ~hit
    sky_unit, blocked_unit = unit[sky], unit[~sky]
    blocked_range = distance[~sky]
    chord, nearest_sky = cKDTree(sky_unit).query(blocked_unit, k=1)
    theta = 2.0 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0))
    _, nearest_blocked = cKDTree(blocked_unit).query(sky_unit, k=1)
    edge_range = blocked_range[nearest_blocked][nearest_sky]

    lam = LIGHT_M_S / float(payload["frequency_hz"])
    gain_db = np.full(unit.shape[0], np.nan)
    gain_db[~sky] = -knife_edge_loss_db(theta * np.sqrt(2.0 * edge_range / lam))

    out = {
        "gain_db": gain_db.reshape(n_azimuth, n_elevation),
        "sky": sky.reshape(n_azimuth, n_elevation),
        "omega": omega.reshape(n_azimuth, n_elevation),
        "index": np.array([record["index"]]),
        "sky_fraction": np.array([record["sky_fraction"]]),
        "grid": np.array([n_azimuth, n_elevation]),
    }
    MASK_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(MASK_CACHE, **out)
    return out


def street_measure_below(degrees: float = 5.0) -> float:
    """Share of the street small cell illumination measure below an elevation."""
    from semantic_twin.propagation.directions import MODELS as LAWS

    unit, omega, elevation = direction_grid(720, 600, 0.05)
    model = LAWS["street_small_cell"]
    weight = model.density(unit, model.normalisation()) * omega
    return float(weight[elevation <= np.radians(degrees)].sum() / weight.sum())


def panel_mask(ax, mask: dict, street_share: float) -> None:
    n_azimuth, n_elevation = (int(v) for v in mask["grid"])
    az_edges = np.linspace(0.0, 360.0, n_azimuth + 1)
    el_edges = np.logspace(np.log10(0.05), np.log10(90.0), n_elevation + 1)
    grid = np.ma.masked_invalid(mask["gain_db"].T)

    mesh = ax.pcolormesh(
        az_edges,
        el_edges,
        grid,
        cmap="magma",
        norm=Normalize(vmin=-45.0, vmax=0.0),
        rasterized=True,
        shading="flat",
    )
    ax.set_facecolor("#cfe0f0")
    ax.set_ylim(0.0, 90.0)
    ax.set_xlim(0.0, 360.0)
    ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_yticks([0, 30, 60, 90])
    ax.set_xlabel("azimuth [deg]", labelpad=1.0)
    ax.set_ylabel("elevation [deg]")
    ax.tick_params(labelsize=7.5)

    bar = ax.figure.colorbar(mesh, ax=ax, pad=0.010, fraction=0.030, extend="min")
    bar.set_label("gain of one knife edge [dB]", fontsize=7.5)
    bar.ax.tick_params(labelsize=7.5)

    ax.axhline(5.0, color="#7fe3d4", lw=0.8, ls=(0, (3, 2)))
    ax.text(
        356.0,
        7.5,
        f"{100 * street_share:.1f} % of the street small cell measure is below this line",
        color="#7fe3d4",
        fontsize=7.2,
        ha="right",
        va="bottom",
    )
    sky = float(mask["sky_fraction"][0])
    ax.text(
        4.0,
        84.0,
        f"pale blue is sky, {100 * sky:.1f} % by solid angle. The bright rim just inside\n"
        "the skyline is where a single edge returns most of the field",
        color="#123a5e",
        fontsize=7.2,
        ha="left",
        va="top",
    )


# ------------------------------------------------------------------ panel b


def panel_validation(ax, bounds: dict) -> None:
    medians = {}
    for model, colour in COLOUR.items():
        errs = []
        for site, payload in bounds.items():
            x, y = [], []
            for row in payload["standpoints"]:
                traced = row[f"{model}_direct_traced"]
                if traced <= 0.0:
                    continue
                x.append(traced)
                y.append(100.0 * abs(row[f"{model}_direct"] - traced) / traced)
            errs += y
            ax.scatter(
                x,
                y,
                s=7,
                marker=MARKER[site],
                facecolor="none",
                edgecolor=colour,
                linewidth=0.55,
                alpha=0.9,
            )
        medians[model] = float(np.median(errs))
        ax.axhline(medians[model], color=colour, lw=0.8, ls="-", alpha=0.55)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(3e-3, 60.0)
    ax.set_xlabel(r"traced $\chi_\mathrm{dir}$, the direct term")
    ax.set_ylabel("disagreement [%]")
    for model, value in medians.items():
        ax.text(
            0.015,
            value * 1.28,
            f"median {value:.2f} %",
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="bottom",
            fontsize=7.0,
            color=COLOUR[model],
        )
    ax.set_title(
        "b  an independent quadrature over the\n     same mask reproduces the tracer",
        loc="left",
        fontsize=8.0,
    )


# ------------------------------------------------------------------ panel c


def ecdf(values: np.ndarray):
    """Cumulative fraction, always over all sixty standpoints.

    Where the bound is undefined the curve simply stops short of one, so the
    four standpoints it cannot express are visible rather than normalised away.
    """
    v = np.sort(values[np.isfinite(values)])
    return v, np.arange(1, v.size + 1) / values.size


def panel_bound(ax, bounds: dict, spread: tuple[float, float]) -> None:
    ax.axvspan(spread[0], spread[1], color=MUTED, alpha=0.18, lw=0)
    for model, colour in COLOUR.items():
        for band, style in (("15ghz", "-"), ("2ghz", "--")):
            pooled = np.array(
                [uplift_db(row, model, band) for payload in bounds.values() for row in payload["standpoints"]]
            )
            x, y = ecdf(pooled)
            ax.step(np.r_[x[0], x], np.r_[0.0, y], where="post", color=colour, lw=1.1, ls=style)
    ax.set_xscale("log")
    ax.set_xlim(0.02, 40.0)
    ax.set_ylim(0.0, 1.32)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel(r"upper bound on the uplift of $\chi$ [dB]")
    ax.set_ylabel("fraction of standpoints below")
    ax.set_title(
        "c  what a diffraction term could add,\n     over 60 standpoints in 3 squares",
        loc="left",
        fontsize=8.0,
    )
    ax.text(
        np.sqrt(spread[0] * spread[1]),
        1.30,
        "spread of $\\chi$ within\none square, 10th to\n90th percentile",
        ha="center",
        va="top",
        fontsize=6.9,
        color="#3d424a",
    )
    ax.text(
        0.022,
        1.30,
        "street curves stop at\n56 of 60, the rest\nundefined, see d",
        ha="left",
        va="top",
        fontsize=6.9,
        color=COLOUR["street_small_cell"],
    )


# ------------------------------------------------------------------ panel d


def panel_concession(ax, bounds: dict) -> None:
    for model, colour in COLOUR.items():
        for site, payload in bounds.items():
            x, y, xz, yz = [], [], [], []
            for row in payload["standpoints"]:
                total = row[f"{model}_total_traced"]
                value = uplift_db(row, model, "15ghz")
                if np.isfinite(value):
                    x.append(total)
                    y.append(value)
                else:
                    # The whole elevation support is occluded, so the uplift on
                    # the direct term is undefined. Quote the zero bounce
                    # diffracted term against the traced total instead, which is
                    # the same bound without the multipath multiplication.
                    xz.append(total)
                    yz.append(10.0 * np.log10(1.0 + row[f"{model}_diff_edge_15ghz"] / total))
            ax.scatter(
                x,
                y,
                s=7,
                marker=MARKER[site],
                facecolor="none",
                edgecolor=colour,
                linewidth=0.55,
                alpha=0.9,
            )
            if xz:
                ax.scatter(xz, yz, s=42, marker="*", color=colour, linewidth=0.0, zorder=5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"traced $\chi$ at that standpoint")
    ax.set_ylabel("upper bound on the uplift [dB]")
    ax.set_title(
        "d  the bound is largest where the\n     exposure itself is smallest",
        loc="left",
        fontsize=8.0,
    )
    ax.set_xlim(1.4e-5, 0.5)
    ax.set_ylim(0.03, 24.0)
    ax.annotate(
        "stars: 4 standpoints whose\nstreet small cell support is\nfully occluded, so the direct\nterm is exactly zero",
        xy=(1.7e-5, 0.038),
        xytext=(1.7e-5, 0.038),
        fontsize=6.9,
        color=COLOUR["street_small_cell"],
        ha="left",
        va="bottom",
    )


# ------------------------------------------------------------------ assembly


def within_square_spread() -> tuple[float, float]:
    """p10 to p90 of chi within a square, over the three sites and three models."""
    values = []
    for site in SITES:
        records = load_locations(site)
        for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell"):
            v = np.array([r[key] for r in records])
            v = 10.0 * np.log10(v[v > 0.0])
            values.append(np.percentile(v, 90) - np.percentile(v, 10))
    return float(min(values)), float(max(values))


def report(bounds: dict) -> None:
    """Print every number the caption is allowed to use."""
    for model in MODELS:
        for band in ("15ghz", "2ghz"):
            pooled = np.array(
                [uplift_db(row, model, band) for payload in bounds.values() for row in payload["standpoints"]]
            )
            finite = pooled[np.isfinite(pooled)]
            print(
                f"{model:18s} {band:6s} n={finite.size} median {np.median(finite):.3f} "
                f"p90 {np.percentile(finite, 90):.3f} max {finite.max():.3f} dB"
            )
        lin15 = np.array(
            [
                10 ** (u / 10) - 1
                for u in [uplift_db(r, model, "15ghz") for p in bounds.values() for r in p["standpoints"]]
                if np.isfinite(u)
            ]
        )
        lin2 = np.array(
            [
                10 ** (u / 10) - 1
                for u in [uplift_db(r, model, "2ghz") for p in bounds.values() for r in p["standpoints"]]
                if np.isfinite(u)
            ]
        )
        print(f"{model:18s} median 2 GHz over 15 GHz linear ratio {np.median(lin2) / np.median(lin15):.2f}")
        errs = np.array(
            [
                100.0 * abs(r[f"{model}_direct"] - r[f"{model}_direct_traced"]) / r[f"{model}_direct_traced"]
                for p in bounds.values()
                for r in p["standpoints"]
                if r[f"{model}_direct_traced"] > 0
            ]
        )
        print(f"{model:18s} validation median {np.median(errs):.2f} % max {errs.max():.2f} %")
    print("within square p10 to p90 spread, dB:", within_square_spread())


def figure_legend(fig) -> None:
    handles = [Line2D([], [], color=COLOUR[m], lw=1.2) for m in MODELS]
    labels = list(MODELS.values())
    handles += [Line2D([], [], color=INK, lw=1.0, ls="-"), Line2D([], [], color=INK, lw=1.0, ls="--")]
    labels += ["15 GHz", "2 GHz"]
    handles += [Line2D([], [], ls="none", marker=MARKER[s], mfc="none", mec=INK, mew=0.6, ms=3.2) for s in SITES]
    labels += list(SITES.values())
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=8,
        fontsize=7.4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.012),
        handlelength=1.3,
        handletextpad=0.4,
        columnspacing=1.15,
    )


def main() -> int:
    apply_monograph_style(
        extra_rc={
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "axes.titlesize": 8.0,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
        }
    )
    bounds = load_bounds()
    report(bounds)

    fig = plt.figure(figsize=fig_size_ieee(columns=2, aspect=0.52))
    grid = fig.add_gridspec(
        2,
        3,
        height_ratios=[0.80, 1.5],
        hspace=0.56,
        wspace=0.30,
        left=0.055,
        right=0.985,
        top=0.925,
        bottom=0.135,
    )
    ax_mask = fig.add_subplot(grid[0, :])
    panel_mask(ax_mask, build_mask(), street_measure_below(5.0))
    ax_mask.set_title(
        "a  the construction, at the most enclosed Korenmarkt standpoint: "
        "432 000 directions, every blocked one given a Fresnel-Kirchhoff parameter",
        loc="left",
        fontsize=8.0,
    )

    panel_validation(fig.add_subplot(grid[1, 0]), bounds)
    panel_bound(fig.add_subplot(grid[1, 1]), bounds, within_square_spread())
    panel_concession(fig.add_subplot(grid[1, 2]), bounds)
    figure_legend(fig)

    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"24_diffraction_bound.{suffix}", dpi=300)
    plt.close(fig)
    print("wrote 24_diffraction_bound.pdf and 24_diffraction_bound.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
