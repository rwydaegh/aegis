"""The skyline as a function of one angle, drawn three ways, at every city.

Almost everything in this study reduces to one curve. Call it ``theta(phi)``: at
each compass direction ``phi``, the elevation ``theta`` of the top edge where
surface meets sky. The source set sits on that curve. The direct term is a sum
along it. The registration that puts a photograph on the mesh is a fit of one
version of it to another. The sky fraction is an average over it.

So it is worth looking at directly, rather than only at the numbers that come out
of it. This script draws it three ways at one standpoint in each city.

**From the panorama.** The bottom edge of the sky in the segmented image, turned
into world directions through the registered pose. This is the measurement. It
knows about railings, cables, trees and cranes, and about buildings that the
photogrammetry rounded off.

**From the mesh, by vertex.** The highest mesh vertex in each azimuth bin. This is
what `align_skyline.mesh_skyline` computes and what the registration objective
actually fits against. It is drawn both raw and after the percentile filter the
registration applies, because that filter is not neutral and the gap between the
two is a bias nobody sees otherwise.

**From the mesh, by ray.** The highest elevation along each azimuth that still
hits something, found by casting. This is the honest silhouette: it is what a
camera at that point would see, and unlike the vertex envelope it cannot report a
vertex that is hidden behind a nearer wall.

The third is the one the source construction uses, so the useful reading is the
bottom panel: how far the other two sit from it, as a function of direction. A
flat offset is a calibration. Structure is a finding.

The other question the picture answers is whether the curve is well behaved. It
is not smooth and should not be, since a roofline genuinely jumps at every
building edge, so the statistics reported alongside separate the jumps from the
noise between them.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.ndimage import percentile_filter  # noqa: E402

from semantic_twin.align_skyline import mesh_skyline  # noqa: E402
from semantic_twin.pano_geometry import panorama_to_world_matrix  # noqa: E402
from semantic_twin.propagation.geometry import MitsubaGeometry  # noqa: E402
from semantic_twin.propagation.skyline import silhouette  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent

SITES = [
    "korenmarkt",
    "brussels_grandplace",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "milan_duomo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
    "toulouse_capitole",
]

#: Above this, a step between neighbouring bins is a building edge rather than
#: noise on a single roof. Ten degrees at these distances is several storeys.
EDGE_STEP_DEG = 10.0

#: Classes that can hold a base station. Everything else along the sky boundary is
#: a pole, a tree, a crane or a sign, and the point of naming them is that this is
#: where the photograph and the mesh disagree. A pole two metres from the camera
#: is a thin line in the picture and a metre and a half of blob in the
#: photogrammetry, so the mesh reports it as skyline across a wide wedge of
#: azimuth while the photograph sees sky around it.
STRUCTURAL = {"building", "wall", "bridge", "tunnel", "barrier", "fence"}


def find_panorama(site: str) -> pathlib.Path | None:
    """A registered panorama folder for this site, or nothing.

    Two layouts exist. The earliest sites are one folder per site, the later ones
    a folder per panorama under the site. Both are read here rather than one being
    renamed, because the names are what the acquisition wrote.
    """
    root = ROOT / "data" / "panoramas" / site
    if not root.is_dir():
        return None
    candidates = [root] if (root / "pose_initial.json").exists() else sorted(root.glob("pano_*"))
    best = None
    best_residual = np.inf
    for folder in candidates:
        pose_path = folder / "alignment" / "pose_aligned.json"
        semantics = folder / "semantics" / "panorama_semantics.npz"
        if not pose_path.exists() or not semantics.exists():
            continue
        pose = json.loads(pose_path.read_text())
        residual = float(pose.get("skyline_score_mean_deg", np.inf))
        if residual < best_residual:
            best, best_residual = folder, residual
    return best


def panorama_curve(
    folder: pathlib.Path, pose: dict, n_bins: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Elevation of the sky boundary against world azimuth, and what holds it up.

    Columns where the image has no sky at all are returned as ``nan`` rather than
    filled. A filled column is a fabricated observation, and the whole point of
    drawing this is to see where the measurement stops existing.

    The third return is whether the class just under the boundary is something a
    base station could stand on. It is read a few pixels below the edge, because
    the edge pixel itself is a blend of the two classes it separates.
    """
    data = np.load(folder / "semantics" / "panorama_semantics.npz")
    entity = data["entity"]
    labels = json.loads((folder / "semantics" / "semantics.json").read_text())["entity_id2label"]
    sky_id = next((int(k) for k, v in labels.items() if str(v).lower() == "sky"), None)
    if sky_id is None:
        raise RuntimeError(f"no sky class in {folder}")

    height, width = entity.shape
    columns = np.linspace(0, width - 1, n_bins, dtype=np.int32)
    sky = entity[:, columns] == sky_id
    # The bottom 28 percent of an equirectangular panorama is the car and the road
    # under it, and no skyline lives there. Same cut the registration uses.
    limit = int(height * 0.72)
    rows = np.arange(limit)[:, None]
    boundary = np.max(np.where(sky[:limit], rows, -1), axis=0).astype(float)
    has_sky = boundary >= 0

    u = (columns + 0.5) / width
    v = (boundary + 0.5) / height
    yaw = (u - 0.5) * 2.0 * np.pi
    pitch = (0.5 - v) * np.pi
    cp = np.cos(pitch)
    local = np.stack([np.sin(yaw) * cp, np.cos(yaw) * cp, np.sin(pitch)], axis=1)

    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    world = local @ rotation.T
    phi = np.arctan2(world[:, 0], world[:, 1]) % (2.0 * np.pi)
    theta = np.arcsin(np.clip(world[:, 2] / np.linalg.norm(world, axis=1), -1.0, 1.0))
    theta[~has_sky] = np.nan

    under = np.clip(np.rint(boundary + max(2, height // 256)).astype(int), 0, height - 1)
    names = np.array([str(labels.get(str(int(c)), "")).lower() for c in entity[under, columns]])
    structural = np.isin(names, list(STRUCTURAL)) & has_sky
    return phi, theta, structural


def resample(phi: np.ndarray, theta: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Put a curve given at scattered azimuths onto the shared grid.

    A tilted camera does not sample world azimuth evenly, so the panorama curve
    arrives unevenly spaced and has to be resampled before it can be differenced
    against the mesh curves. Gaps stay gaps: a grid point further than one grid
    step from any measured azimuth is left empty rather than interpolated across.
    """
    good = np.isfinite(theta)
    if good.sum() < 2:
        return np.full_like(grid, np.nan)
    order = np.argsort(phi[good])
    x = phi[good][order]
    y = theta[good][order]
    wide_x = np.r_[x - 2.0 * np.pi, x, x + 2.0 * np.pi]
    wide_y = np.r_[y, y, y]
    out = np.interp(grid, wide_x, wide_y)
    step = grid[1] - grid[0]
    nearest = np.abs(grid[:, None] - wide_x[None, :]).min(axis=1)
    out[nearest > 1.5 * step] = np.nan
    return out


def ray_curve(geometry: MitsubaGeometry, camera: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """The cast silhouette, on the shared azimuth grid.

    ``silhouette`` measures azimuth from east and this plot measures it from
    north, so the fan is asked for the directions the grid names rather than being
    called and rotated afterwards.
    """
    n = grid.size
    alpha, _, found = silhouette(geometry, camera, azimuths=n, elevations=600)
    # The fan's own azimuths are (i + 0.5) * 2 pi / n measured from east. Convert
    # each to the north referenced angle and put the value where it belongs.
    own = (np.arange(n) + 0.5) * (2.0 * np.pi / n)
    phi = (np.pi / 2.0 - own) % (2.0 * np.pi)
    theta = np.where(found, alpha, np.nan)
    order = np.argsort(phi)
    return resample(phi[order], theta[order], grid)


def statistics(grid: np.ndarray, curves: dict[str, np.ndarray]) -> dict:
    """How rough the curve is, and how far the three versions sit apart."""
    out: dict = {}
    for name, curve in curves.items():
        step = np.diff(np.degrees(curve))
        finite = step[np.isfinite(step)]
        out[name] = {
            "defined_fraction": float(np.mean(np.isfinite(curve))),
            "median_deg": float(np.nanmedian(np.degrees(curve))),
            "p95_deg": float(np.nanpercentile(np.degrees(curve), 95)),
            "median_abs_step_deg": float(np.median(np.abs(finite))) if finite.size else float("nan"),
            "edge_fraction": float(np.mean(np.abs(finite) > EDGE_STEP_DEG)) if finite.size else float("nan"),
        }
    reference = curves["mesh, by ray"]
    for name in ("panorama", "mesh, by vertex", "mesh, by vertex, filtered"):
        if name not in curves:
            continue
        delta = np.degrees(curves[name] - reference)
        good = np.isfinite(delta)
        out[name]["minus_ray_median_deg"] = float(np.median(delta[good])) if good.any() else float("nan")
        out[name]["minus_ray_rms_deg"] = float(np.sqrt(np.mean(delta[good] ** 2))) if good.any() else float("nan")
    return out


def draw(
    ax_top,
    ax_bottom,
    grid: np.ndarray,
    curves: dict[str, np.ndarray],
    title: str,
    structural: np.ndarray | None = None,
) -> None:
    degrees = np.degrees(grid)
    if structural is not None:
        # Shaded where the photograph says the sky boundary is not a building.
        # Every large disagreement between the picture and the mesh falls in one
        # of these bands, which is the argument for reading the class and not
        # only the shape.
        ax_top.fill_between(
            degrees, 0, 1, where=~structural, transform=ax_top.get_xaxis_transform(),
            color="#f0a800", alpha=0.16, lw=0, zorder=0,
        )
        ax_bottom.fill_between(
            degrees, 0, 1, where=~structural, transform=ax_bottom.get_xaxis_transform(),
            color="#f0a800", alpha=0.16, lw=0, zorder=0,
        )
    style = {
        "panorama": ("#d62728", 1.1, "-"),
        "mesh, by ray": ("#1f77b4", 1.1, "-"),
        "mesh, by vertex": ("#7f7f7f", 0.8, "-"),
        "mesh, by vertex, filtered": ("#2ca02c", 0.9, "--"),
    }
    for name, curve in curves.items():
        colour, width, dash = style[name]
        ax_top.plot(degrees, np.degrees(curve), dash, color=colour, lw=width, label=name)
    ax_top.set_ylabel("elevation, deg")
    ax_top.set_title(title, fontsize=9)
    ax_top.set_xlim(0, 360)
    ax_top.grid(alpha=0.25, lw=0.4)

    reference = curves["mesh, by ray"]
    for name in ("panorama", "mesh, by vertex", "mesh, by vertex, filtered"):
        if name not in curves:
            continue
        colour, width, dash = style[name]
        ax_bottom.plot(
            degrees, np.degrees(curves[name] - reference), dash, color=colour, lw=width
        )
    ax_bottom.axhline(0.0, color="k", lw=0.6)
    ax_bottom.set_xlabel("azimuth from north, deg")
    ax_bottom.set_ylabel("minus ray, deg")
    ax_bottom.set_xlim(0, 360)
    ax_bottom.grid(alpha=0.25, lw=0.4)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=SITES)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--bins", type=int, default=1440)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "skyline_function")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    grid = (np.arange(args.bins) + 0.5) * (2.0 * np.pi / args.bins)

    summary = {}
    panels = []
    for site in args.sites:
        folder = find_panorama(site)
        if folder is None:
            print(f"{site:24s} no registered panorama with semantics, skipped")
            continue
        mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m_f64.ply"
        if not mesh.exists():
            mesh = ROOT / "data" / "geometry" / site / f"inhouse_leaf_{args.crop_m}m.ply"
        if not mesh.exists():
            print(f"{site:24s} no {args.crop_m} m mesh, skipped")
            continue

        pose = json.loads((folder / "alignment" / "pose_aligned.json").read_text())
        camera = np.asarray(pose["position_enu_m"], dtype=np.float64)
        geometry = MitsubaGeometry(mesh, variant=args.variant)

        phi, theta, structural_column = panorama_curve(folder, pose, args.bins)
        curves = {
            "panorama": resample(phi, theta, grid),
            "mesh, by ray": ray_curve(geometry, camera, grid),
        }
        # Carried onto the shared grid as a number and then thresholded, since a
        # boolean cannot be interpolated. Half is the natural cut: it marks a grid
        # point structural when the columns nearest it mostly were.
        structural = resample(phi, structural_column.astype(float), grid)
        structural = np.nan_to_num(structural, nan=1.0) > 0.5
        # The vertex envelope is written on a bin index that runs from south, so
        # it is rebuilt on the shared grid the same way the others are.
        raw = mesh_skyline(geometry.vertices, camera, args.bins, smoothing_size=1)
        filtered = percentile_filter(raw, 90.0, size=11, mode="wrap")
        centres = ((np.arange(args.bins) + 0.5) / args.bins - 0.5) * 2.0 * np.pi % (2.0 * np.pi)
        order = np.argsort(centres)
        curves["mesh, by vertex"] = resample(centres[order], raw[order], grid)
        curves["mesh, by vertex, filtered"] = resample(centres[order], filtered[order], grid)

        stats = statistics(grid, curves)
        # The same difference, split by what the photograph says is holding the
        # boundary up. If the disagreement lives in the non structural part, the
        # mesh and the picture agree about buildings and differ about clutter,
        # which is a different problem with a different fix.
        delta = np.degrees(curves["panorama"] - curves["mesh, by ray"])
        for name, mask in (("structural", structural), ("clutter", ~structural)):
            good = np.isfinite(delta) & mask
            stats["panorama"][f"minus_ray_rms_deg_{name}"] = (
                float(np.sqrt(np.mean(delta[good] ** 2))) if good.any() else float("nan")
            )
            stats["panorama"][f"azimuth_fraction_{name}"] = float(np.mean(mask))

        summary[site] = {
            "panorama": str(folder.relative_to(ROOT)),
            "camera_enu_m": camera.tolist(),
            "registration_residual_deg": pose.get("skyline_score_mean_deg"),
            "curves": stats,
        }
        panels.append((site, curves))

        figure, (ax_top, ax_bottom) = plt.subplots(
            2, 1, figsize=(7.2, 4.4), sharex=True, height_ratios=[2, 1]
        )
        draw(ax_top, ax_bottom, grid, curves, f"{site}, {folder.name}", structural)
        ax_top.legend(fontsize=7, loc="upper right", ncol=2, framealpha=0.9)
        figure.tight_layout()
        figure.savefig(args.out / f"{site}_skyline_function.png", dpi=170)
        plt.close(figure)

        stat = summary[site]["curves"]
        print(
            f"{site:24s} defined {stat['panorama']['defined_fraction']:.2f}  "
            f"pano minus ray {stat['panorama']['minus_ray_median_deg']:+6.2f} deg median, "
            f"{stat['panorama']['minus_ray_rms_deg']:5.2f} rms  "
            f"vertex minus ray {stat['mesh, by vertex']['minus_ray_median_deg']:+6.2f}  "
            f"edges {stat['mesh, by ray']['edge_fraction']:.3f}"
        )

    if panels:
        columns = 2
        rows = (len(panels) + columns - 1) // columns
        figure, axes = plt.subplots(rows, columns, figsize=(11.0, 1.9 * rows), sharex=True)
        axes = np.atleast_2d(axes).reshape(-1)
        for ax, (site, curves) in zip(axes, panels):
            for name, curve in curves.items():
                if name == "mesh, by vertex":
                    continue
                colour = {"panorama": "#d62728", "mesh, by ray": "#1f77b4"}.get(name, "#2ca02c")
                ax.plot(np.degrees(grid), np.degrees(curve), color=colour, lw=0.7)
            ax.set_title(site, fontsize=8)
            ax.set_xlim(0, 360)
            ax.grid(alpha=0.2, lw=0.3)
        for ax in axes[len(panels) :]:
            ax.axis("off")
        figure.supxlabel("azimuth from north, deg", fontsize=9)
        figure.supylabel("elevation, deg", fontsize=9)
        figure.tight_layout()
        figure.savefig(args.out / "all_cities_skyline_function.png", dpi=170)
        plt.close(figure)

    (args.out / "skyline_function.json").write_text(json.dumps(summary, indent=1))
    print(f"\nwrote {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
