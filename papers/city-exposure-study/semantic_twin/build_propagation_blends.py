"""Build the propagation walkthrough blends for several sites, and zip them.

Drives ``export_propagation_payload.py`` then ``propagation_blender.py`` per
site, renders the contact sheet, and packages the blends with their manifests
and a written index into one archive that is small enough to move around.

    python build_propagation_blends.py                       # the default four sites
    python build_propagation_blends.py --sites korenmarkt    # just one
    python build_propagation_blends.py --skip-render         # blends only, much faster

The sites are chosen to span the range the study measured rather than to be
representative, because four sites cannot be representative of eleven and
pretending otherwise would be the worse choice.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
OUTPUT = SCRIPT_DIR / "outputs" / "propagation_viz"
BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"

#: site -> why it is in the set. Written into the index so the archive explains
#: its own contents to whoever opens it a month from now.
SITES: dict[str, str] = {
    "korenmarkt": (
        "The reference site. Everything else in this study was built and checked here "
        "first, and it is the only site with registered panorama semantics."
    ),
    "krakow_rynek": (
        "The most open square in the set, and the highest susceptibility under every "
        "illumination model. The upper end of what a European core does."
    ),
    "newyork_timessquare": (
        "The canyon. 18 percent sky against Krakow's 46, and the lowest isotropic "
        "susceptibility of the eleven. The lower end."
    ),
    "brussels_grandplace": (
        "The widest spread inside one square, 12.7 dB rooftop between its own "
        "standpoints. Where you stand matters most here."
    ),
}


def run(command: list[str], label: str) -> None:
    print(f"\n=== {label} ===\n{' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {result.returncode}")


def build(site: str, args: argparse.Namespace) -> dict[str, pathlib.Path]:
    payload = args.out / f"{site}_payload.npz"
    manifest = args.out / f"{site}_manifest.json"
    blend = args.out / f"{site}_propagation.blend"

    if not payload.exists() or args.retrace:
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "export_propagation_payload.py"),
                "--site",
                site,
                "--locations",
                str(args.locations),
                "--paths",
                str(args.paths),
                "--rays",
                str(args.rays),
                "--draw-radius-m",
                str(args.draw_radius_m),
                "--out",
                str(args.out),
            ],
            f"trace {site}",
        )

    command = [
        str(BLENDER),
        "--background",
        "--python",
        str(SCRIPT_DIR / "propagation_blender.py"),
        "--",
        "--payload",
        str(payload),
        "--manifest",
        str(manifest),
        "--blend",
        str(blend),
    ]
    if not args.skip_render:
        command += [
            "--render-dir",
            str(args.out / "figures"),
            "--samples",
            str(args.samples),
            "--resolution-scale",
            str(args.resolution_scale),
        ]
    run(command, f"blend {site}")
    return {"payload": payload, "manifest": manifest, "blend": blend}


def write_index(built: dict[str, dict[str, pathlib.Path]], path: pathlib.Path) -> pathlib.Path:
    """A README the archive carries with it, with each site's own numbers in it."""
    lines = [
        "# Propagation walkthrough blends",
        "",
        "One Blender file per city square. Everything in them is measured: the mesh is the",
        "support mesh the rays were cast against, the ray polylines are paths the estimator",
        "integrated, the lobe is the angular power spectrum it accumulated, and the colours",
        "on the phantom are the absorbed power density AEGIS returned for that spectrum.",
        "",
        "Attaching the path recorder leaves every traced number bit identical, and the test",
        "suite asserts it, so the rays drawn are the rays integrated rather than a redrawing.",
        "",
        "## What is in each file",
        "",
        "| Collection | What it shows |",
        "| --- | --- |",
        "| `twin` | The support mesh, tinted by the surface class that chose its material. |",
        "| `rays` | Five exclusive bundles of recorded paths. Thickness is the cube root of throughput. |",
        "| `arrival` | The angular power spectrum at the hero standpoint, one lobe per illumination model. |",
        "| `network` | Where the illumination model's sources sit, at true horizontal range and height. |",
        "| `walk` | Every traced standpoint, coloured by susceptibility in decibels. |",
        "| `body` | The duke phantom at the hero standpoint, coloured by absorbed power density. |",
        "",
        "The five ray bundles are, by colour: orange, straight to sky inside the rooftop",
        "elevation band; blue, straight to sky outside it; pale yellow, reached sky after at",
        "least one bounce, inside the band; cyan, the same outside it; dark red, never left",
        "the scene. The band split is the one worth looking at. An escape outside it carries",
        "nothing under that illumination model no matter how far the ray travelled.",
        "",
        "## Two things that are drawn rather than measured, and are marked as such",
        "",
        "The arrival lobe is normalised by its own peak, so the three models are shape",
        "comparable and not level comparable. Their levels differ by two orders of magnitude",
        "and drawing that faithfully would leave two of them invisible. Each lobe carries its",
        "own peak in `peak_rho_per_sr`. The lobe also has a radius floor, so it stays a closed",
        "surface rather than the pancake a directional model really makes, and it is drawn",
        "above the standpoint so it does not enclose the phantom standing there. Both are",
        "recorded as custom properties on the object.",
        "",
        "## The sites",
        "",
    ]
    for site, reason in SITES.items():
        if site not in built:
            continue
        manifest = json.loads(built[site]["manifest"].read_text())
        hero = manifest["hero"]
        lines += [
            f"### {site.replace('_', ' ')}",
            "",
            reason,
            "",
            f"- Traced against a {manifest['traced_crop_radius_m']:g} m crop of "
            f"{manifest['traced_triangles']:,} triangles, of which "
            f"{manifest['drawn_triangles']:,} inside {manifest['drawn_radius_m']:g} m are drawn.",
            f"- {manifest['locations']} standpoints traced at {manifest['frequency_hz'] / 1e9:g} GHz.",
            f"- Hero standpoint sees {hero['sky_fraction']:.4f} of the sphere as sky and averages "
            f"{hero['mean_bounces']:.2f} bounces.",
            "- Susceptibility there: "
            + ", ".join(f"{name} {value:.4f}" for name, value in hero["susceptibility"].items())
            + ".",
            f"- Peak absorbed power density on the phantom under rooftop illumination, "
            f"{hero['body']['rooftop']['peak_sab_w_m2']:.4g} W/m2 at "
            f"{manifest['reference_s0_w_m2']:g} W/m2 free space incident.",
            "",
        ]
    lines += [
        "## Regenerating",
        "",
        "```",
        "python build_propagation_blends.py",
        "```",
        "",
        "Payloads and manifests are beside the blends. A blend can be rebuilt from its",
        "payload alone, without retracing, which takes about a minute.",
        "",
    ]
    path.write_text("\n".join(lines))
    return path


def package(built: dict[str, dict[str, pathlib.Path]], index: pathlib.Path, archive: pathlib.Path) -> pathlib.Path:
    """Zip the blends, their manifests and the index. Payloads stay behind.

    A payload is the input to a blend, not a result, and including it would
    roughly double the archive to carry the same information twice.
    """
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.write(index, "README.md")
        for site, paths in built.items():
            bundle.write(paths["blend"], f"{site}/{paths['blend'].name}")
            bundle.write(paths["manifest"], f"{site}/{paths['manifest'].name}")
    return archive


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="*", default=list(SITES))
    parser.add_argument("--locations", type=int, default=60)
    parser.add_argument("--paths", type=int, default=900)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--draw-radius-m", type=float, default=110.0)
    parser.add_argument("--samples", type=int, default=48)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--retrace", action="store_true", help="Retrace even if a payload exists")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    parser.add_argument("--archive", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if not BLENDER.exists():
        raise SystemExit(f"no Blender at {BLENDER}")
    args.out.mkdir(parents=True, exist_ok=True)

    built: dict[str, dict[str, pathlib.Path]] = {}
    for site in args.sites:
        if site not in SITES:
            raise SystemExit(f"{site} is not one of {sorted(SITES)}")
        built[site] = build(site, args)

    index = write_index(built, args.out / "README.md")
    archive = package(built, index, args.archive or args.out / "propagation_blends.zip")

    print("\n=== built ===", flush=True)
    for site, paths in built.items():
        print(f"{site:24s} {paths['blend'].stat().st_size / 1e6:6.1f} MB", flush=True)
    print(f"{'archive':24s} {archive.stat().st_size / 1e6:6.1f} MB  {archive}", flush=True)
    if shutil.which("unzip") is None:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
