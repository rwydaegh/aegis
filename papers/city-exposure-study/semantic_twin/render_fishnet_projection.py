"""Render a SAM3 mask and its fishnet projection side by side."""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from semantic_twin.scene.fishnet import load_fishnet, rasterize_fishnet


def projection_metrics(reference: np.ndarray, projected: np.ndarray) -> dict[str, float | int]:
    """Return binary overlap metrics for equally shaped masks."""
    reference = np.asarray(reference, dtype=bool)
    projected = np.asarray(projected, dtype=bool)
    if reference.shape != projected.shape:
        raise ValueError("reference and projected masks must have equal shapes")
    true_positive = int(np.count_nonzero(reference & projected))
    false_positive = int(np.count_nonzero(~reference & projected))
    false_negative = int(np.count_nonzero(reference & ~projected))
    union = true_positive + false_positive + false_negative
    return {
        "reference_pixels": int(np.count_nonzero(reference)),
        "projected_pixels": int(np.count_nonzero(projected)),
        "true_positive_pixels": true_positive,
        "false_positive_pixels": false_positive,
        "false_negative_pixels": false_negative,
        "iou": true_positive / union if union else 1.0,
        "precision": true_positive / (true_positive + false_positive) if projected.any() else 1.0,
        "recall": true_positive / (true_positive + false_negative) if reference.any() else 1.0,
    }


def _overlay(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha: float) -> np.ndarray:
    rendered = np.asarray(image, dtype=np.float64).copy()
    rendered[mask] = (1.0 - alpha) * rendered[mask] + alpha * np.asarray(color)
    return np.clip(rendered, 0, 255).astype(np.uint8)


def _difference_overlay(image: np.ndarray, reference: np.ndarray, projected: np.ndarray) -> np.ndarray:
    rendered = np.asarray(image, dtype=np.float64).copy()
    classes = (
        (reference & projected, np.array([20.0, 230.0, 120.0])),
        (reference & ~projected, np.array([245.0, 55.0, 65.0])),
        (~reference & projected, np.array([40.0, 155.0, 255.0])),
    )
    for mask, color in classes:
        rendered[mask] = 0.3 * rendered[mask] + 0.7 * color
    return np.clip(rendered, 0, 255).astype(np.uint8)


def _crop_face_segments(
    face_image: np.ndarray,
    *,
    row: int,
    column: int,
    height: int,
    width: int,
) -> list[np.ndarray]:
    offset = np.array([column, row], dtype=np.float64)
    segments = []
    for triangle in np.asarray(face_image, dtype=np.float64):
        local = triangle - offset
        if (
            local[:, 0].max() >= 0
            and local[:, 0].min() <= width
            and local[:, 1].max() >= 0
            and local[:, 1].min() <= height
        ):
            segments.append(np.vstack([local, local[0]]))
    return segments


def _set_equal_3d(ax: Any, points: np.ndarray) -> None:
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    centre = 0.5 * (lower + upper)
    span = np.maximum(upper - lower, 1e-6)
    radius = 0.53 * float(span.max())
    ax.set_xlim(centre[0] - radius, centre[0] + radius)
    ax.set_ylim(centre[1] - radius, centre[1] + radius)
    ax.set_zlim(centre[2] - radius, centre[2] + radius)
    ax.set_box_aspect((1, 1, 1))


def render(args: argparse.Namespace) -> dict[str, Any]:
    crop = np.asarray(Image.open(args.crop).convert("RGB"))
    reference = np.asarray(Image.open(args.mask).convert("L")) > 0
    supplied_overlay = np.asarray(Image.open(args.overlay).convert("RGB"))
    if crop.shape[:2] != reference.shape or supplied_overlay.shape[:2] != reference.shape:
        raise ValueError("crop, overlay, and mask must have equal image dimensions")

    surface = load_fishnet(args.fishnet)
    raster = rasterize_fishnet(surface, (args.full_height, args.full_width))
    projected_full = raster.class_map == args.class_id
    crop_slice = np.s_[args.row : args.row + reference.shape[0], args.column : args.column + reference.shape[1]]
    projected = projected_full[crop_slice]
    metrics = projection_metrics(reference, projected)

    with np.load(args.mesh_depth) as depth:
        face_ids = np.asarray(depth["face_ids"])[crop_slice]
    eligible = reference & (face_ids >= 0)
    eligible_metrics = projection_metrics(eligible, projected)
    source_ids = np.unique(face_ids[eligible])
    source_ids = source_ids[source_ids >= 0]

    mesh = trimesh.load(args.mesh, process=False, force="mesh")
    coarse_triangles = np.asarray(mesh.vertices)[np.asarray(mesh.faces)[source_ids]]
    fishnet_triangles = surface.vertices[surface.faces]

    figure = plt.figure(figsize=(15.5, 13), facecolor="#111317")
    grid = figure.add_gridspec(2, 2, hspace=0.13, wspace=0.08)
    axes = [
        figure.add_subplot(grid[0, 0]),
        figure.add_subplot(grid[0, 1]),
        figure.add_subplot(grid[1, 0]),
    ]
    ax_3d = figure.add_subplot(grid[1, 1], projection="3d")

    axes[0].imshow(supplied_overlay)
    axes[0].set_title("A  SAM3 union in the source image\n13,943 selected pixels", color="white", fontsize=14)

    projected_overlay = _overlay(crop, projected, (35, 185, 255), 0.62)
    axes[1].imshow(projected_overlay)
    segments = _crop_face_segments(
        surface.face_image,
        row=args.row,
        column=args.column,
        height=reference.shape[0],
        width=reference.shape[1],
    )
    axes[1].add_collection(LineCollection(segments, colors="#fff1a8", linewidths=0.48, alpha=0.72))
    axes[1].set_title(
        f"B  Metric fishnet projected back into the camera\n{surface.triangle_count} cut triangles, yellow edges",
        color="white",
        fontsize=14,
    )

    axes[2].imshow(_difference_overlay(crop, reference, projected))
    axes[2].set_title(
        "C  Pixel comparison\n"
        f"IoU {metrics['iou']:.1%}  |  precision {metrics['precision']:.1%}  |  recall {metrics['recall']:.1%}",
        color="white",
        fontsize=14,
    )
    axes[2].text(
        0.02,
        0.025,
        "green = agreement   red = SAM3 not represented   blue = fishnet spill",
        transform=axes[2].transAxes,
        color="white",
        fontsize=10,
        bbox={"facecolor": "#111317", "alpha": 0.75, "edgecolor": "none", "pad": 5},
    )

    coarse_collection = Poly3DCollection(
        coarse_triangles,
        facecolors=(0.62, 0.64, 0.68, 0.18),
        edgecolors=(0.82, 0.84, 0.88, 0.72),
        linewidths=0.75,
    )
    fishnet_collection = Poly3DCollection(
        fishnet_triangles,
        facecolors=(0.05, 0.83, 0.46, 0.80),
        edgecolors=(0.02, 0.12, 0.08, 0.85),
        linewidths=0.38,
    )
    ax_3d.add_collection3d(coarse_collection)
    ax_3d.add_collection3d(fishnet_collection)
    _set_equal_3d(ax_3d, coarse_triangles.reshape(-1, 3))
    ax_3d.view_init(elev=16, azim=-52)
    ax_3d.set_xlabel("east [m]", color="#d7d9dc")
    ax_3d.set_ylabel("north [m]", color="#d7d9dc")
    ax_3d.set_zlabel("up [m]", color="#d7d9dc")
    ax_3d.set_title(
        f"D  Scene geometry\n{len(source_ids)} original support triangles → {surface.triangle_count} RF-ready pieces",
        color="white",
        fontsize=14,
        pad=14,
    )
    ax_3d.set_facecolor("#111317")
    for axis in (ax_3d.xaxis, ax_3d.yaxis, ax_3d.zaxis):
        axis.set_pane_color((0.07, 0.08, 0.10, 1.0))
        axis._axinfo["grid"]["color"] = (0.34, 0.36, 0.40, 0.35)
    ax_3d.tick_params(colors="#d7d9dc", labelsize=8)

    for ax in axes:
        ax.set_axis_off()
        ax.set_facecolor("#111317")
    figure.suptitle(
        "SAM3 semantic evidence becomes a cut metric surface",
        color="white",
        fontsize=20,
        y=0.975,
    )
    figure.text(
        0.5,
        0.018,
        f"Mask area on mesh: {int(eligible.sum()):,}/{int(reference.sum()):,} px  |  "
        f"mesh-eligible recall: {eligible_metrics['recall']:.1%}  |  "
        f"metric surface area: {surface.face_area_m2.sum():.2f} m²",
        ha="center",
        color="#d7d9dc",
        fontsize=11,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)

    report: dict[str, Any] = {
        "source_mask": str(args.mask),
        "fishnet": str(args.fishnet),
        "output": str(args.output),
        "crop_origin_row_column": [args.row, args.column],
        "crop_shape": list(reference.shape),
        "metrics_against_full_sam3_mask": metrics,
        "metrics_against_mesh_eligible_sam3_mask": eligible_metrics,
        "sam3_pixels_with_mesh_hit": int(eligible.sum()),
        "sam3_pixels_without_mesh_hit": int(np.count_nonzero(reference & ~eligible)),
        "original_support_triangles_under_mask": int(len(source_ids)),
        "emitted_source_triangles": int(np.unique(surface.face_source_triangle).size),
        "fishnet_triangles": surface.triangle_count,
        "fishnet_vertices": int(surface.vertices.shape[0]),
        "surface_area_m2": float(surface.face_area_m2.sum()),
        "solid_angle_sr": float(surface.face_solid_angle_sr.sum()),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop", type=pathlib.Path, required=True)
    parser.add_argument("--overlay", type=pathlib.Path, required=True)
    parser.add_argument("--mask", type=pathlib.Path, required=True)
    parser.add_argument("--fishnet", type=pathlib.Path, required=True)
    parser.add_argument("--mesh-depth", type=pathlib.Path, required=True)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--row", type=int, required=True)
    parser.add_argument("--column", type=int, required=True)
    parser.add_argument("--full-height", type=int, required=True)
    parser.add_argument("--full-width", type=int, required=True)
    parser.add_argument("--class-id", type=int, default=1)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args), indent=2))


if __name__ == "__main__":
    main()
