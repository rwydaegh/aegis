"""Build the propagation walkthrough blends for several sites, and zip them.

Drives ``export_propagation_payload.py`` then ``propagation_blender.py`` per
site, renders the contact sheet, and packages the blends with their manifests
and a written index into one archive. Eleven squares come to about 190 MB. The
four squares with no image evidence weigh under 9 MB each and the seven that
carry some weigh 10 to 37 MB, so most of the archive is the evidence layers.

    python build_propagation_blends.py                       # all eleven squares
    python build_propagation_blends.py --sites korenmarkt    # just one
    python build_propagation_blends.py --skip-render         # blends only, much faster

Every square the study built is in the set. The archive used to hold four, and
said so, because four cannot be representative of eleven and spanning the range
was the honest thing a subset could do. That caveat is spent: the set is now the
whole population the study measured, so nothing here is standing in for anything
else and no site was chosen over another.
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
#:
#: Every number quoted below is a median or a spread over the 80 standpoints of
#: the ``city250_L3_*`` sweep, the single writer eleven site run at the 250 m
#: crop on the fixed ground datum, tabulated in ``AGGREGATE_REBUILD.md`` and
#: drawn by ``FIGURES/make_eleven_cities_exposure.py``. Within square spreads are
#: p95 over p05 in decibels. Nothing here comes from the superseded
#: ``city250_corrected_*`` run, whose Krakow and Toulouse standpoints stood on a
#: roof.
SITES: dict[str, str] = {
    "korenmarkt": (
        "The reference site. Everything else in this study was built and checked here "
        "first, and it is the only square carrying every evidence layer: two semantic "
        "surfaces where the others have at most one, both depth clouds, and the 18 "
        "reconstructed bodies that exist nowhere else. Five of the other ten carry the "
        "Vistas fishnet and their registered poses, Milan adds a depth cloud to that, "
        "and Krakow, London, Tokyo and Toulouse carry no image evidence at all. On "
        "exposure it is unremarkable, eighth of eleven on isotropic median at 0.2916 "
        "and seventh on rooftop at 0.1626."
    ),
    "krakow_rynek": (
        "The square the ground datum fix moved furthest. The published run stood its "
        "walk 18.19 m up on the roof of the Cloth Hall, and coming down to the pavement "
        "cost 5.26 dB of rooftop susceptibility. At street level the Rynek is open but "
        "not the outlier it was drawn as: sky median 0.3138, third of the eleven behind "
        "London at 0.3304 and Mexico City at 0.3240. Its rooftop susceptibility spans "
        "2.86 dB across its own standpoints, the second narrowest of the eleven."
    ),
    "newyork_timessquare": (
        "The canyon. A sky median of 0.1210 against London's 0.3304, and the lowest "
        "isotropic susceptibility of the eleven at 0.1694. It is also the one square the "
        "street small cell model favours, at 0.0604, more than half again the next "
        "square, because a source down at street level is the one thing its towers do "
        "not block. Its rays bounce most, 1.48 per ray at the median against 0.91 at "
        "London, and arrive latest, 21.50 ns of excess delay."
    ),
    "brussels_grandplace": (
        "The widest spread inside one square. 12.89 dB of rooftop susceptibility and "
        "19.01 dB of street small cell between its own standpoints, both the largest of "
        "the eleven, because a walk here leaves an enclosed square for the narrow streets "
        "feeding it. Where you stand matters most here."
    ),
    "london_trafalgar": (
        "The most open square of the eleven, sky median 0.3304, and second on rooftop "
        "susceptibility at 0.2884. The openness is evenly shared: its rooftop spread "
        "across standpoints is 4.55 dB, third narrowest of the eleven, so Trafalgar is "
        "open almost everywhere rather than open in one place."
    ),
    "madrid_plazamayor": (
        "The square that carries the study's headline result on its own. Isotropic "
        "susceptibility spans 6.46 dB between Madrid's own standpoints, the largest "
        "within square spread of the eleven, against 3.71 dB spanned by the eleven "
        "square medians across three continents. Where a person stands in this one "
        "square matters more than which of the eleven squares they are standing in."
    ),
    "mexico_zocalo": (
        "The most exposed square of the eleven, and the top of both common rankings: "
        "isotropic median 0.3977 and rooftop median 0.3070. It also loses the most "
        "energy to the sky, an escaped fraction of 0.898, which is what a wide square "
        "under a low horizon does."
    ),
    "milan_duomo": (
        "The most uniform square in the set. Rooftop susceptibility spans 2.55 dB across "
        "its standpoints against Brussels' 12.89, the narrowest of the eleven. It is "
        "also the one square whose crop had to be widened past the standard, to 170 m "
        "from an acquisition ball of 320 m, because the cathedral's 109 m spire sits "
        "above what a 200 m ball reaches at this site's ellipsoidal height."
    ),
    "prague_staromestske": (
        "Nothing about Staromestske is extreme, which is the reason to keep it in view. "
        "Fourth of eleven on sky at 0.2882, fourth on isotropic median susceptibility at "
        "0.3584 and fifth on rooftop at 0.2377, at neither end of any panel of the eleven "
        "square figure. A set assembled only from its endpoints would not show that the "
        "middle is populated."
    ),
    "tokyo_hachiko": (
        "The second canyon, and a different one from Times Square. Median excess delay "
        "17.11 ns, second longest of the eleven behind Times Square's 21.50, so the "
        "energy that reaches a pedestrian here has also gone a long way round. But its "
        "sky median of 0.1739 is third from the bottom rather than last, and its street "
        "small cell susceptibility of 0.0161 is ordinary where Times Square's is the "
        "highest in the set. Deep is not one shape."
    ),
    "toulouse_capitole": (
        "The eleventh square, and the one that had no scene config until this build. Its "
        "published ground datum sat 13.94 m up on the roof of the Capitole, and coming "
        "down to the pavement cost 1.29 dB isotropic and 1.83 dB rooftop and moved it "
        "from second of eleven to seventh on isotropic median. What is left is a square "
        "of two halves: 11.40 dB of rooftop spread across its standpoints, second only "
        "to Brussels, under a single monumental facade with low arcades everywhere else."
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
        if args.gpu:
            command.append("--gpu")
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
        "One file per site holds every layer at once, in fourteen numbered collections you",
        "switch in the outliner. The blend opens on the square, not on the world origin.",
        "",
        "| Collection | On at open | What it shows |",
        "| --- | --- | --- |",
        "| `01 city mesh` | yes | The photogrammetric support mesh, tinted by the surface class that chose its material. |",
        "| `02 semantic surface` | no | The fishnet surface, one object per taxonomy, Mapillary Vistas and SAM 3. |",
        "| `03 image coverage` | no | Every support triangle a view considered, clean pixels against withheld. |",
        "| `04 refused faces` | no | What the cutter threw away, one object per reason it was thrown. |",
        "| `05 depth clouds` | no | The mesh first hit, and the monocular surface the plausibility gate refused. |",
        "| `06 panorama captures` | no | The registered poses as real cameras, with their covariance and sky conflict verdict. |",
        "| `07 bystander bodies` | no | The SMPL-X people the dynamic layer reconstructed and placed. |",
        "| `08 walk standpoints` | yes | Every traced standpoint, coloured by susceptibility in decibels. |",
        "| `09 ray paths by fate` | yes | Five exclusive bundles of recorded paths, thickness and `power_db` both carrying throughput. |",
        "| `10 ray paths by bounce` | no | The same paths cut at their reflections, one object per leg index. |",
        "| `11 arrival spectrum` | yes | The angular power spectrum at the hero standpoint, one lobe per illumination model. |",
        "| `12 transmitter positions` | yes | Where the illumination model's sources sit, at true horizontal range and height. |",
        "| `13 body exposure` | yes | The duke phantom at the hero standpoint, coloured by absorbed power density. |",
        "| `14 cameras` | yes | The figure cameras, plus one camera per registered panorama at its solved pose. |",
        "",
        "Every collection exists in every file whether or not the site had the data for it, so",
        "an empty `05 depth clouds` means that site has no depth buffers rather than meaning",
        "the layer was forgotten. Each object carries its measured quantities twice, once as",
        "an exact `value_` attribute and once as a colour attribute over a stated range, and",
        "lists what it carries as `colour_layers`. Everything is in one ENU frame, metres,",
        "with the hero standpoint at the origin. `PAYLOAD.md` in the repository says what",
        "each array is and where it was read from.",
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
        "All eleven squares the study built are here, so this archive is the measured set",
        "and not a sample of it. An earlier version of this archive held four and said in",
        "its own header that four cannot be representative of eleven. That caveat is spent.",
        "",
        "The numbers under each square are of two kinds and should not be read as one. The",
        "medians and spreads in the prose are the `city250_L3_*` sweep, 80 standpoints per",
        "square at the 250 m crop on the fixed ground datum, which is the run the paper",
        "quotes. The bulleted numbers under them are this blend's own trace, a separate and",
        "smaller run at 60 standpoints kept in step with the file you are looking at, so a",
        "susceptibility read off the standpoints in the viewport is that trace and not the",
        "sweep. They are the same estimator at the same crop radius and frequency, and they",
        "should agree to the sampling noise of 60 standpoints against 80 rather than exactly.",
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
    parser.add_argument(
        "--gpu", action="store_true", help="Render on the accelerator, and fail loudly if there is none"
    )
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
