"""The six panels the material question comes down to.

Panel a is what the two image sources look like on the same wall from the same
viewpoint, which is most of the answer about the photogrammetric texture.

Panel b is the whole traceable vocabulary as a function of incidence, with the
compositions marked, so the per bounce ceiling on any material model can be read
off directly against the angles a street canyon actually presents.

Panel c is the layered stack, which is the part of the proposal that had to be
built before it could be judged. It shows why an opaque coating collapses onto
its outer material and why a glazing unit does not.

Panel d is what each source says the square is made of.

Panel e is calibration, stated confidence against the agreement the model
realises on independent looks at the same wall.

Panel f is the answer. Every variant traced through the tracer against the brick
binding the pipeline uses today, with the bracket set by putting one material on
every facade in the square. Metal is the only thing on this axis with leverage.

    python3 plot_material_vlm.py --out outputs/material_vlm
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path("/home/user/aegis/theory/scripts")))

import matplotlib.pyplot as plt  # noqa: E402
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402
from PIL import Image  # noqa: E402

from semantic_twin.facade_vlm import (  # noqa: E402
    Layer,
    _layer_permittivity,
    half_space_power_reflectance,
    layered_power_reflectance,
    material_power_reflectance,
    posterior_power_reflectance,
    stack_power_reflectance,
)
from semantic_twin.materials import MaterialLibrary  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent
HERO_CROP = "h+00_225_r0128_c0000"

#: Composition rows of panel d, in the order they are stacked.
SEGMENTS = ("brick", "concrete", "plasterboard", "marble", "glass", "metal", "wood", "ceramic", "unknown")

#: Traced variants of panel f. Seeds are averaged where a variant has two.
TRACED = (
    ("every facade metal", ("pure_metal_m0", "pure_metal_m1")),
    ("every facade stone", ("pure_marble_m0", "pure_marble_m1")),
    ("VLM tile texture", ("vlm_texture_m0", "vlm_texture_m1")),
    ("VLM street capture", ("vlm_panorama_m0", "vlm_panorama_m1")),
    ("fixed prior, drawn", ("prior_draw_m0", "prior_draw_m1")),
    ("control, brick drawn", ("pure_brick_m0", "pure_brick_m1")),
    ("every facade render", ("pure_plasterboard_m0", "pure_plasterboard_m1")),
)


def traced_shift(ablation: dict, tags: tuple[str, ...], key: str) -> tuple[float, float, float]:
    """Seed averaged paired shift, and the p10 and p90 across standpoints."""
    rows = [ablation["variants"][t]["paired_shift_db"][key] for t in tags if t in ablation["variants"]]
    if not rows:
        return 0.0, 0.0, 0.0
    return (
        float(np.mean([r["median_db"] for r in rows])),
        float(np.mean([r["p10_db"] for r in rows])),
        float(np.mean([r["p90_db"] for r in rows])),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "material_vlm")
    parser.add_argument("--crop", default=HERO_CROP)
    parser.add_argument("--mode", choices=("png", "pdf"), default="png")
    args = parser.parse_args()

    analysis = json.loads((args.out / "analysis.json").read_text())
    ablation_path = args.out / "ablation.json"
    ablation = json.loads(ablation_path.read_text()) if ablation_path.exists() else None
    library = MaterialLibrary.load(ROOT / "config" / "itu_p2040_4.json")
    frequency = 15.0e9

    apply_monograph_style(mode=args.mode, constrained_layout=True)
    figure, axes = plt.subplots(2, 3, figsize=fig_size_ieee(columns=2, aspect=0.58))

    # Panel a, the two sources side by side.
    panel = axes[0, 0]
    left = np.asarray(Image.open(args.out / "crops" / f"{args.crop}_panorama.png"))
    right = np.asarray(Image.open(args.out / "crops" / f"{args.crop}_texture.png"))
    panel.imshow(np.concatenate([left, right], axis=1))
    panel.axvline(left.shape[1], color="white", linewidth=1.0)
    panel.set_xticks([left.shape[1] // 2, left.shape[1] + right.shape[1] // 2])
    panel.set_xticklabels(["street capture", "tile texture"])
    panel.set_yticks([])
    panel.set_title("(a) one wall, two sources", loc="left")

    # Panel b, the vocabulary against incidence with the compositions marked.
    panel = axes[0, 1]
    angles = np.linspace(0.0, 85.0, 120)
    cosines = np.cos(np.radians(angles))
    for label, key, style in (
        ("fixed prior, mean", "fixed_building_prior", "--"),
        ("VLM street, mean", "vlm_panorama", "-"),
    ):
        posterior = analysis["composition"][key]
        curve = [
            10
            * np.log10(posterior_power_reflectance(posterior, material_power_reflectance(frequency, float(c), library)))
            for c in cosines
        ]
        panel.plot(angles, curve, style, color="black", linewidth=2.2, alpha=0.35, label=label)
    for name in ("wood", "plasterboard", "brick", "concrete", "glass", "marble"):
        curve = [10 * np.log10(material_power_reflectance(frequency, float(c), library)[name]) for c in cosines]
        panel.plot(angles, curve, linewidth=0.9, label=name)
    panel.axvspan(60.0, 85.0, color="0.85", zorder=0, linewidth=0)
    panel.text(72.5, -3.2, "street canyon", ha="center", fontsize=5, color="0.35")
    panel.set_xlim(0, 85)
    panel.set_xlabel("incidence [deg]")
    panel.set_ylabel("power reflectance [dB]")
    panel.set_title("(b) the per bounce ceiling at 15 GHz", loc="left")
    panel.legend(fontsize=4.5, ncol=2, loc="lower right")

    # Panel c, the layered stack.
    panel = axes[0, 2]
    thickness = np.linspace(0.5, 40.0, 300)
    render = [
        stack_power_reflectance((Layer("plasterboard", t), Layer("brick", None)), frequency, 1.0, library)
        for t in thickness
    ]
    panel.plot(thickness, 10 * np.log10(render), linewidth=0.9, label="render on brick")
    glass = _layer_permittivity("glass", frequency, library)
    pane = [
        layered_power_reflectance(np.array([glass, complex(1.0, 0.0)]), np.array([t / 1000.0]), 1.0, frequency)
        for t in thickness
    ]
    panel.plot(thickness, 10 * np.log10(pane), linewidth=0.9, label="glass pane in air")
    for name, value, style in (
        ("brick half space", half_space_power_reflectance(_layer_permittivity("brick", frequency, library), 1.0), ":"),
        (
            "render half space",
            half_space_power_reflectance(_layer_permittivity("plasterboard", frequency, library), 1.0),
            "--",
        ),
        ("glass half space", half_space_power_reflectance(glass, 1.0), "-."),
    ):
        panel.axhline(10 * np.log10(value), linestyle=style, color="0.4", linewidth=0.8, label=name)
    panel.set_xlabel("outer layer thickness [mm]")
    panel.set_ylabel("power reflectance [dB]")
    panel.set_title("(c) the stack, at normal incidence", loc="left")
    panel.legend(fontsize=4.5, loc="lower right")

    # Panel d, what each source says the square is made of.
    panel = axes[1, 0]
    rows = (
        ("fixed prior", "fixed_building_prior"),
        ("VLM street", "vlm_panorama"),
        ("VLM street,\nouter layer", "vlm_panorama_outer_layer"),
        ("VLM texture", "vlm_texture"),
    )
    colours = plt.get_cmap("tab10")(np.linspace(0, 1, 10))
    positions = np.arange(len(rows))
    for index, name in enumerate(SEGMENTS):
        widths = [analysis["composition"][key].get(name, 0.0) for _, key in rows]
        lefts = [sum(analysis["composition"][key].get(m, 0.0) for m in SEGMENTS[:index]) for _, key in rows]
        panel.barh(positions, widths, left=lefts, height=0.68, label=name, color=colours[index % 10], linewidth=0)
    panel.set_yticks(positions)
    panel.set_yticklabels([label for label, _ in rows], fontsize=5)
    panel.invert_yaxis()
    panel.set_xlim(0, 1)
    panel.set_xlabel("area weighted share")
    panel.set_title("(d) what the square is made of", loc="left")
    panel.legend(fontsize=4.2, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.62))

    # Panel e, calibration without truth.
    panel = axes[1, 1]
    for label, key, marker in (
        ("street, cross view", "panorama_cross_view_curve", "o"),
        ("street, repeat draw", "panorama_repeat_curve", "s"),
        ("texture, repeat draw", "texture_repeat_curve", "^"),
    ):
        curve = analysis["calibration"][key]
        if not curve:
            continue
        x = [row["mean_stated_confidence"] for row in curve]
        y = [row["mean_realised_agreement"] for row in curve]
        size = [6.0 + 2.0 * row["count"] for row in curve]
        panel.plot(x, y, marker, markersize=3, label=label)
        panel.scatter(x, y, s=size, alpha=0.25)
    panel.plot([0, 1], [0, 1], color="0.5", linewidth=0.8, linestyle=":")
    panel.text(0.70, 0.44, "over confident", fontsize=4.5, color="0.45", rotation=38)
    panel.text(0.24, 0.72, "under confident", fontsize=4.5, color="0.45", rotation=38)
    panel.set_xlim(0, 1)
    panel.set_ylim(0, 1.05)
    panel.set_xlabel("stated confidence")
    panel.set_ylabel("realised agreement")
    panel.set_title("(e) calibration, with no ground truth", loc="left")
    panel.legend(fontsize=4.5, loc="lower right")

    # Panel f, the traced answer and its bracket.
    panel = axes[1, 2]
    if ablation is not None:
        labels = [label for label, _ in TRACED]
        positions = np.arange(len(TRACED))
        iso = [traced_shift(ablation, tags, "chi_isotropic") for _, tags in TRACED]
        roof = [traced_shift(ablation, tags, "chi_rooftop") for _, tags in TRACED]
        low = min(v[0] for v in iso if abs(v[0]) < 1.0)
        high = max(v[0] for v in iso if abs(v[0]) < 1.0)
        panel.axvspan(low, high, color="0.87", zorder=0, linewidth=0)
        panel.axvline(0.0, color="0.5", linewidth=0.8, linestyle=":")
        for offset, values, marker, label in (
            (-0.16, iso, "o", "isotropic"),
            (0.16, roof, "D", "rooftop"),
        ):
            centre = [v[0] for v in values]
            panel.plot(centre, positions + offset, marker, markersize=3, linestyle="none", label=label)
            for index, value in enumerate(values):
                panel.plot([value[1], value[2]], [positions[index] + offset] * 2, linewidth=0.7, color="0.55", zorder=0)
        panel.set_yticks(positions)
        panel.set_yticklabels(labels, fontsize=5)
        panel.set_xlabel("paired shift in chi vs brick [dB]")
        panel.set_xlim(-1.2, 5.2)
        panel.annotate(
            f"isotropic dielectric\nbracket, {high - low:.2f} dB",
            xy=(high, len(TRACED) - 2.0),
            xytext=(1.35, len(TRACED) - 1.9),
            fontsize=4.5,
            color="0.35",
            arrowprops={"arrowstyle": "->", "color": "0.55", "linewidth": 0.6},
        )
        panel.legend(fontsize=4.5, loc="center right")
    panel.set_title("(f) traced through the tracer", loc="left")

    suffix = "pdf" if args.mode == "pdf" else "png"
    path = args.out / f"material_vlm.{suffix}"
    figure.savefig(path, dpi=300 if suffix == "png" else None)
    print(f"-> {path}")


if __name__ == "__main__":
    main()
