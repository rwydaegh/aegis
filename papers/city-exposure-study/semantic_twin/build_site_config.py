"""Write a scene config for a screened site, with the ground datum measured.

A site cannot be acquired without a config, because `fetch_site_panoramas.py`
needs an ENU origin to place a panorama in and a support mesh to cast a camera
altitude against, and `semantic_twin.scene.load_scene` refuses a config without
`camera_ground_z_m`. Three screened sites shipped a mesh and no config, and the
reason in every case was that the ground datum could not be measured under the
anchor by the method used at the time.

That method took the median of a 6 by 6 m patch of the topmost tile surface
under the seed panorama and refused any site whose patch spread exceeded 0.1 m.
It answers the question "what is under this one point", which is the wrong
question whenever the anchor happens to land on a building. At Rynek Glowny the
anchor is on the roof of the Cloth Hall, which stands in the middle of the
square, and the patch reads 269.6 m against a pavement at 250.9 m. At Place du
Capitole the anchor is in a small enclosed courtyard that the largest open
region of the crop does not reach within 25 m.

This measures the site datum instead of the anchor datum. It casts a downward
ray over a disc, histograms the topmost surface it finds, and takes the
dominant mode in the lower half of the relief. That is the largest single
horizontal surface in the crop that is not a roof, which for a city square is
the square. It does not care where the anchor sits.

Two sites already carry a `camera_ground_z_m` measured independently by the
patch method, and they are the check on this one:

    korenmarkt           50.911 measured against 50.837 shipped, +0.073 m
    brussels_grandplace  65.361 measured against 65.270 shipped, +0.092 m

Both agree to under 0.1 m, which is the same order as the patch spread the old
gate demanded, so the estimator reproduces the shipped constants where they
exist and keeps working where they do not.

What the constant is used for matters for reading that error bar.
`semantic_twin.scene.camera_ground.camera_altitude` casts under each camera's own
easting and northing and uses `camera_ground_z_m` only to set the ceiling the
ray starts from, at datum plus `search_up_m`. So the constant has to be within
a few metres of the pavement to keep an arcade roof out of the answer, and it
does not have to be the altitude of any particular camera.

Run from the `semantic_twin` directory::

    ../../../.venv/bin/python build_site_config.py --site london_trafalgar
    ../../../.venv/bin/python build_site_config.py --site krakow_rynek --dry-run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.screening import Candidate  # noqa: E402

DEFAULT_SCREENING = SCRIPT_DIR / "outputs" / "city_screening" / "screening.json"

#: Reproduced by this estimator to under 0.1 m, quoted in the config it writes.
DATUM_VALIDATION = {
    "korenmarkt": {"shipped_m": 50.83747424667166, "measured_m": 50.911},
    "brussels_grandplace": {"shipped_m": 65.2698432267606, "measured_m": 65.361},
}

FREQUENCY_NOTE = (
    "Same split as korenmarkt.json and milan_duomo.json. 28 and 39 GHz sit "
    "inside the ITU-R P.2040-4 validity band. 60 GHz does not for every "
    "material a masonry scene needs, since brick and asphalt_concrete are "
    "tabulated only to 40 GHz and PowerLawMaterial.evaluate raises rather than "
    "extrapolate silently, so it is listed separately as an explicit opt-in "
    "requiring allow_extrapolation=True, applicability "
    "indicative_extrapolation and an uncertainty multiplier of 1.585 from the "
    "0.585 octaves between 40 and 60 GHz. The material inventory for this site "
    "has not been built yet, so the note states the constraint rather than "
    "which materials trip it here."
)


def candidates() -> dict[str, Candidate]:
    from screen_cities import CANDIDATES  # noqa: PLC0415

    return {c.key: c for c in CANDIDATES}


def ground_datum(
    mesh_path: pathlib.Path,
    *,
    radius_m: float = 80.0,
    samples: int = 20000,
    bin_m: float = 0.5,
    band_m: float = 1.0,
    seed: int = 0,
) -> dict[str, Any]:
    """Dominant open ground surface of a crop, and how dominant it is.

    ``samples`` downward rays over a disc of ``radius_m``, histogrammed at
    ``bin_m``. The mode is searched only in the lower half of the relief so a
    site whose roofs happen to be flatter and more extensive than its square
    cannot win, and the returned datum is the median of the hits within
    ``band_m`` of the modal bin rather than the bin centre.
    """
    import trimesh
    from trimesh.ray.ray_pyembree import RayMeshIntersector

    mesh = trimesh.load(mesh_path, process=False)
    intersector = RayMeshIntersector(mesh)
    ceiling = float(mesh.vertices[:, 2].max()) + 50.0
    rng = np.random.default_rng(seed)
    angle = rng.uniform(0.0, 2.0 * np.pi, samples)
    distance = radius_m * np.sqrt(rng.random(samples))
    xy = np.column_stack([distance * np.cos(angle), distance * np.sin(angle)])
    origins = np.column_stack([xy, np.full(samples, ceiling)])
    locations, _, _ = intersector.intersects_location(
        origins, np.tile(np.array([0.0, 0.0, -1.0]), (samples, 1)), multiple_hits=False
    )
    if not len(locations):
        raise SystemExit(f"{mesh_path} has no surface under the crop")
    height = locations[:, 2]
    low, high = np.percentile(height, 0.5), np.percentile(height, 99.5)
    edges = np.arange(low, high + bin_m, bin_m)
    counts, _ = np.histogram(height, bins=edges)
    below_half = edges[:-1] < low + 0.5 * (high - low)
    peak = int(np.argmax(np.where(below_half, counts, -1)))
    centre = 0.5 * (edges[peak] + edges[peak + 1])
    band = np.abs(height - centre) < band_m
    return {
        "camera_ground_z_m": float(np.median(height[band])),
        "method": (
            f"dominant mode of the topmost tile surface over a {radius_m:g} m disc, "
            f"{samples} downward rays, {bin_m:g} m bins, mode searched below the midpoint "
            f"of the relief, datum is the median of hits within {band_m:g} m of the modal bin"
        ),
        "disc_radius_m": radius_m,
        "samples": int(samples),
        "hits": int(len(height)),
        "modal_share": float(band.mean()),
        "band_spread_m": float(height[band].std()),
        "relief_m": [float(low), float(high)],
        "anchor_topmost_surface_m": float(_anchor_height(intersector, ceiling)),
    }


def _anchor_height(intersector: Any, ceiling: float) -> float:
    locations, _, _ = intersector.intersects_location(
        np.array([[0.0, 0.0, ceiling]]), np.array([[0.0, 0.0, -1.0]]), multiple_hits=False
    )
    return float(locations[0, 2]) if len(locations) else float("nan")


def screening_row(name: str, screening: pathlib.Path) -> dict[str, Any]:
    for row in json.loads(screening.read_text())["rows"]:
        if row["key"] == name:
            return row
    raise SystemExit(f"{name} is not in {screening}")


def build(
    name: str,
    *,
    crop_m: int,
    screening: pathlib.Path,
    walk_date: str | None,
    radius_m: float,
) -> dict[str, Any]:
    candidate = candidates()[name]
    directory = SCRIPT_DIR / "data" / "geometry" / name
    mesh = directory / f"inhouse_leaf_{crop_m}m.ply"
    if not mesh.exists():
        raise SystemExit(f"no {crop_m} m mesh for {name}")
    manifest = json.loads(mesh.with_suffix(".json").read_text())
    row = screening_row(name, screening)
    datum = ground_datum(mesh, radius_m=radius_m)
    date = walk_date or row["walk_date"]
    epoch = next(e for e in row["epochs"] if e["date"] == date)
    return {
        "name": name,
        "location": {"lat": candidate.lat, "lon": candidate.lon, "radius_m": 50.0},
        "enu_origin": {"lat": candidate.lat, "lon": candidate.lon, "ellipsoid_height_m": 0.0},
        "camera_ground_z_m": datum["camera_ground_z_m"],
        "camera_ground_z_note": (
            "Measured by build_site_config.py as the dominant open ground surface of the crop, "
            "not as the surface under the anchor. "
            + datum["method"]
            + f". The modal band holds {datum['modal_share']:.3f} of the disc with a spread of "
            f"{datum['band_spread_m']:.3f} m, against a relief of {datum['relief_m'][0]:.1f} to "
            f"{datum['relief_m'][1]:.1f} m, and the topmost surface under the anchor itself is "
            f"{datum['anchor_topmost_surface_m']:.2f} m. The estimator reproduces the two "
            "independently measured constants in this repository to under 0.1 m: korenmarkt "
            "50.911 against 50.837 and brussels_grandplace 65.361 against 65.270. It is one "
            "scene-wide constant and carries the same weakness as every other config here, but "
            "camera_altitude only uses it to set the ceiling a per camera downward ray starts "
            "from, so a metre of error costs nothing and twenty metres costs everything."
        ),
        "camera_height_m": 2.5,
        "frequencies_hz": [28000000000.0, 39000000000.0],
        "extrapolated_frequencies_hz": [60000000000.0],
        "frequency_note": FREQUENCY_NOTE,
        "source_mesh": f"data/geometry/{name}/inhouse_leaf_{crop_m}m.ply",
        "source_mesh_manifest": f"data/geometry/{name}/inhouse_leaf_{crop_m}m.json",
        "geometry_selection": {
            "provider": "Inhouse Photorealistic 3D Tiles",
            "selection": "deepest available leaf tiles",
            "observed_geometric_error_m": manifest["source_geometric_error_range_m"]["max"],
            "acquisition_radius_m": manifest["source_acquisition"]["radius_m"],
            "crop_radius_m": manifest["crop_radius_m"],
            "leaf_tile_count": manifest["source_tile_count"],
            "triangle_count": manifest["after_triangle_count"],
            "tile_requests": manifest["source_acquisition"]["request_count"],
            "tile_bytes": manifest["source_acquisition"]["request_bytes"],
            "coverage_acceptance": (
                "Not established for this site. Korenmarkt and Milan chose their crop by keeping "
                "at least 99% of the 200 m projection in four validation views, and that sweep "
                "has not been run here."
            ),
        },
        "geometry_note": (
            "Standalone ENU support mesh. Inhouse triangulation supplies first-hit depth only. "
            "Semantic boundary resolution comes from the source image pixels."
        ),
        "walk_selection": {
            "walk_date": date,
            "screened_walk_date": row["walk_date"],
            "walk_date_overridden": date != row["walk_date"],
            "providers": epoch["providers"],
            "walk_panoramas": epoch["walk_count"],
            "median_spacing_m": epoch["median_spacing_m"],
            "span_m": epoch["span_m"],
            "azimuth_spread": epoch["azimuth_spread"],
        },
        "screening_provenance": {
            "screen_radius_m": 60.0,
            "panoramas_within_60m": len(row["panoramas"]),
            "distinct_capture_dates": row["distinct_dates"],
            "table": "outputs/city_screening/screening.json",
        },
        "mesh_defects": [
            "camera_ground_z_m is one constant for the whole site.",
            (
                "The anchor is not the centre of the open square at every site. "
                "build_site_config.py records the topmost surface under the anchor beside the "
                "datum so the offset is visible rather than inferred."
            ),
        ],
    }


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--crop-m", type=int, default=130)
    parser.add_argument("--screening", type=pathlib.Path, default=DEFAULT_SCREENING)
    parser.add_argument("--radius-m", type=float, default=80.0)
    parser.add_argument(
        "--walk-date",
        help="capture date to record, as YYYY-MM, overriding the screener's largest-component choice",
    )
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    scene = build(
        args.site,
        crop_m=args.crop_m,
        screening=args.screening,
        walk_date=args.walk_date,
        radius_m=args.radius_m,
    )
    text = json.dumps(scene, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    path = args.out or (SCRIPT_DIR / "config" / f"{args.site}.json")
    path.write_text(text)
    print(
        f"[config] {args.site}: camera_ground_z_m={scene['camera_ground_z_m']:.3f} m, "
        f"anchor surface {scene['camera_ground_z_note'].split('the anchor itself is ')[1].split(' m.')[0]} m, "
        f"walk {scene['walk_selection']['walk_date']} -> {path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
