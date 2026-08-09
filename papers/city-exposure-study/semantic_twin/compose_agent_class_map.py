"""Compose a dense mutually exclusive agent map from SAM3 and semantic seeds."""

from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib
import numpy as np
from PIL import Image, ImageDraw
from skimage import color, feature, morphology, transform

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from run_sam3_surface_probe import _slug


CLASS_NAMES = {
    1: "red brick",
    2: "mortar joints",
    3: "carved stone",
    4: "window glass",
    5: "dark interior",
    6: "wooden frames",
    7: "metalwork",
    8: "cables",
    9: "plaster wall",
    10: "sky",
    11: "foreground rail",
    12: "unresolved",
    13: "unobserved support",
}

TAXONOMY_NAMES = {
    0: "Unknown",
    1: "exposed red brick masonry",
    2: "mortar joints and recessed masonry seams",
    3: "pale carved stone trim and ornaments",
    4: "window glazing interface",
    5: "unknown dark window interior opening",
    6: "painted wooden window frames and mullions",
    7: "pole architectural metalwork",
    8: "unknown suspended cable",
    9: "adjacent plaster wall",
    10: "sky",
    11: "railing foreground construction element",
    12: "unknown unresolved remainder",
    13: "unknown unobserved support",
}

PALETTE = np.array(
    [
        [0, 0, 0],
        [190, 62, 47],
        [218, 202, 167],
        [255, 186, 73],
        [51, 173, 220],
        [40, 65, 91],
        [139, 91, 56],
        [232, 63, 142],
        [30, 30, 35],
        [190, 169, 132],
        [100, 190, 255],
        [245, 245, 245],
        [143, 111, 190],
        [105, 110, 118],
    ],
    dtype=np.uint8,
)

PROMPTS = {
    1: "brick masonry wall",
    3: "pale carved stone decorative window lintel",
    4: "window glass pane",
    6: "wooden window frame",
    7: "black metal wall ornament",
    10: "sky",
}


def _mask(directory: pathlib.Path, image_stem: str, prompt: str) -> np.ndarray:
    path = directory / f"{image_stem}__{_slug(prompt)}__union_mask.png"
    if not path.exists():
        return np.zeros((384, 384), dtype=bool)
    return np.asarray(Image.open(path).convert("L")) > 0


def _line_masks(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray = color.rgb2gray(rgb)
    edges = feature.canny(gray, sigma=1.0)
    lines = transform.probabilistic_hough_line(
        edges,
        threshold=12,
        line_length=45,
        line_gap=5,
        rng=np.random.default_rng(4),
    )
    cable_image = Image.new("1", (rgb.shape[1], rgb.shape[0]))
    rail_image = Image.new("1", (rgb.shape[1], rgb.shape[0]))
    cable_draw = ImageDraw.Draw(cable_image)
    rail_draw = ImageDraw.Draw(rail_image)
    for (x0, y0), (x1, y1) in lines:
        dx, dy = x1 - x0, y1 - y0
        length = float(np.hypot(dx, dy))
        if length >= 110 and abs(dy) <= 0.12 * max(abs(dx), 1):
            cable_draw.line((x0, y0, x1, y1), fill=1, width=2)
        if length >= 42 and min(y0, y1) >= 330 and abs(dy) >= 0.15 * max(abs(dx), 1):
            rail_draw.line((x0, y0, x1, y1), fill=1, width=4)
    return np.asarray(cable_image, dtype=bool), np.asarray(rail_image, dtype=bool)


def compose(args: argparse.Namespace) -> dict[str, object]:
    rgb = np.asarray(Image.open(args.crop).convert("RGB"))
    height, width = rgb.shape[:2]
    stem = args.crop.stem
    sam = {key: _mask(args.sam3, stem, prompt) for key, prompt in PROMPTS.items()}
    if args.stone_mask is not None:
        sam[3] = np.asarray(Image.open(args.stone_mask).convert("L")) > 0

    vistas = np.load(args.vistas_labels)[args.row : args.row + height, args.column : args.column + width]
    labels = np.full((height, width), 12, dtype=np.int16)

    building = vistas == 17
    labels[building & sam[1]] = 1

    lab = color.rgb2lab(rgb)
    mortar_pool = building & sam[1]
    mortar_score = lab[..., 0] - 2.0 * lab[..., 1]
    target = min(int(round(0.08 * labels.size)), int(np.count_nonzero(mortar_pool)))
    mortar = np.zeros(labels.shape, dtype=bool)
    if target:
        candidates = np.flatnonzero(mortar_pool)
        selected = candidates[np.argpartition(mortar_score.ravel()[candidates], -target)[-target:]]
        mortar.ravel()[selected] = True
    labels[mortar] = 2
    labels[building & sam[3]] = 3

    wood = building & sam[6] & ~sam[4]
    labels[wood] = 6
    labels[building & sam[4]] = 4
    luminance = color.rgb2gray(rgb)
    labels[building & sam[4] & (luminance < 0.26)] = 5
    labels[building & sam[7]] = 7

    cable, rail = _line_masks(rgb)
    cable = cable | morphology.opening(luminance < 0.34, footprint=np.ones((1, 55), dtype=bool))
    labels[cable & (luminance < 0.52)] = 8
    labels[:, :18][building[:, :18]] = 9
    labels[(vistas == 27) | sam[10]] = 10
    labels[rail & (luminance > 0.42)] = 11

    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "crop_labels.npy", labels)
    full_labels = np.full((args.full_height, args.full_width), 13, dtype=np.int16)
    full_confidence = np.zeros((args.full_height, args.full_width), dtype=np.float32)
    full_labels[args.row : args.row + height, args.column : args.column + width] = labels
    full_confidence[args.row : args.row + height, args.column : args.column + width] = 1.0
    np.save(args.output / "h+00_315_labels.npy", full_labels)
    np.save(args.output / "h+00_315_confidence.npy", full_confidence)
    taxonomy = {"entity_id2label": {str(key): value for key, value in TAXONOMY_NAMES.items()}}
    (args.output / "semantics.json").write_text(json.dumps(taxonomy, indent=2) + "\n")

    colour = PALETTE[labels]
    overlay = np.clip(0.38 * rgb + 0.62 * colour, 0, 255).astype(np.uint8)
    figure, axis = plt.subplots(figsize=(10.8, 8.2), facecolor="#111317")
    axis.imshow(overlay)
    axis.set_axis_off()
    axis.set_title("Agent inventory composed into one 13-state map", color="white", fontsize=18, pad=14)
    counts = {key: int(np.count_nonzero(labels == key)) for key in CLASS_NAMES}
    handles = [
        Patch(
            facecolor=PALETTE[key] / 255.0,
            edgecolor="white" if key == 8 else "none",
            label=f"{key:02d}  {CLASS_NAMES[key]}  ({counts[key] / labels.size:.1%})",
        )
        for key in CLASS_NAMES
    ]
    legend = axis.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=True,
        facecolor="#171a20",
        edgecolor="#555a64",
        labelcolor="white",
        fontsize=10,
    )
    legend.get_frame().set_alpha(1.0)
    figure.text(
        0.02,
        0.02,
        "SAM3 seeds + Vistas support/sky + deterministic residual composition.\n"
        "Unresolved is explicit; unobserved support exists outside this crop.",
        color="#d8dbe0",
        fontsize=10,
    )
    figure.savefig(
        args.output / "agent_13_class_image.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor()
    )
    plt.close(figure)

    report: dict[str, object] = {
        "classes": {str(key): {"name": CLASS_NAMES[key], "pixels": counts[key]} for key in CLASS_NAMES},
        "crop_shape": [height, width],
        "covered_fraction_excluding_unresolved": 1.0 - counts[12] / labels.size,
        "sam3_seed_prompts": {str(key): prompt for key, prompt in PROMPTS.items()},
        "composition": "SAM3 union seeds, Vistas building and sky, image-derived mortar and long-line residuals",
        "warning": "draft agent interpretation for visual audit, not accepted transport state",
    }
    (args.output / "composition_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop", type=pathlib.Path, required=True)
    parser.add_argument("--sam3", type=pathlib.Path, required=True)
    parser.add_argument("--stone-mask", type=pathlib.Path)
    parser.add_argument("--vistas-labels", type=pathlib.Path, required=True)
    parser.add_argument("--row", type=int, required=True)
    parser.add_argument("--column", type=int, required=True)
    parser.add_argument("--full-height", type=int, required=True)
    parser.add_argument("--full-width", type=int, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compose(args), indent=2))


if __name__ == "__main__":
    main()
