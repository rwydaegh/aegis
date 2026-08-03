"""Sky fraction and skyline height per city, for the contact sheet.

Both numbers used to be measured against a ground level taken from a single ray
dropped at the centre of the crop. That is the estimator `GROUND_DATUM.md`
retired. At Krakow the centre of the square is the Sukiennice and at Toulouse it
is the Capitole, so the observer stood on a monument at one site and inside one
at the other, and the sheet reported Krakow as the most open square of the eleven
and Toulouse as the most enclosed. Neither was true.

So neither number is measured at an anchor here any more.

Sky fraction is the median over the standpoints of that square's own walk in the
published eleven city run, which is the same quantity the middle panel of figure
16 draws, so the sheet and the headline figure cannot disagree. Skyline height is
measured above the ground datum that run used, rather than above a low
percentile of vertex height, because the tiles carry underground structure and a
low quantile lands in a car park.

    python measure_city_metrics.py

Writes outputs/city_gallery/metrics.json, which make_city_sheet.py reads.
"""

from __future__ import annotations

import json
import pathlib
import re

import numpy as np
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent
EXPOSURE = ROOT / "outputs" / "exposure_korenmarkt"

#: The published cross city run. AGGREGATE_REBUILD.md records what it replaced.
RUN_PREFIX = "city250_L3"
FREQ_GHZ = 15.0
#: The tiles reach well above the tallest building at a few sites, so the
#: skyline is a high percentile of vertex height rather than the maximum.
SKYLINE_PERCENTILE = 99.5


#: The radius each gallery tile was rendered at, which is the crop the skyline
#: number has to describe. Milan predates the set and has no 130 m build.
GALLERY_RADIUS_M = 130
GALLERY_RADIUS_OVERRIDE = {"milan_duomo": 200}


def metric_mesh(site: str) -> pathlib.Path | None:
    """The crop the gallery render shows, which is what the numbers describe.

    A skyline read off a wider crop is a different city. At Tokyo the 250 m crop
    reaches towers the 130 m tile in the sheet does not contain, and it doubles
    the number.
    """
    radius = GALLERY_RADIUS_OVERRIDE.get(site, GALLERY_RADIUS_M)
    directory = ROOT / "data/geometry" / site
    for name in (f"inhouse_leaf_{radius}m_f64.ply", f"inhouse_leaf_{radius}m.ply"):
        if (directory / name).is_file():
            return directory / name
    return None


def walk_sky(site: str) -> tuple[float, float, float, int] | None:
    """Median, 5th and 95th percentile sky fraction over the published walk."""
    path = EXPOSURE / f"{RUN_PREFIX}_{site}_{FREQ_GHZ:g}ghz_locations.jsonl"
    if not path.exists():
        return None
    values = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            values.append(json.loads(line)["sky_fraction"])
        except json.JSONDecodeError:
            # A torn line is two writers on one tag. Say so rather than average
            # over whatever survived.
            print(f"[warn] {path.name} has a torn record, not publishable")
            return None
    array = np.asarray(values, dtype=np.float64)
    return (
        float(np.median(array)),
        float(np.percentile(array, 5)),
        float(np.percentile(array, 95)),
        int(array.size),
    )


def main() -> None:
    out: dict[str, dict] = {}
    sites = sorted(directory.name for directory in (ROOT / "data/geometry").iterdir() if directory.is_dir())
    for site in sites:
        path = metric_mesh(site)
        sky = walk_sky(site)
        if path is None or sky is None:
            print(f"{site:24s} skipped, no mesh or no run at {RUN_PREFIX}")
            continue
        manifest = json.loads((EXPOSURE / f"{RUN_PREFIX}_{site}_{FREQ_GHZ:g}ghz_manifest.json").read_text())
        datum = float(manifest["ground_datum_m"])
        mesh = trimesh.load(path, process=False, force="mesh")
        z = np.asarray(mesh.vertices)[:, 2]
        median, low, high, count = sky
        out[site] = {
            "sky_median": median,
            "sky_p05": low,
            "sky_p95": high,
            "standpoints": count,
            "skyline_m": float(np.percentile(z, SKYLINE_PERCENTILE) - datum),
            "ground_datum_m": datum,
            "triangles": int(len(mesh.faces)),
            "mesh": path.name,
            "crop_radius_m": float(re.search(r"_(\d+)m", path.name).group(1)),
            "run": f"{RUN_PREFIX}_{site}_{FREQ_GHZ:g}ghz",
        }
        print(
            f"{site:24s} sky {median:.3f} over {count:3d} standpoints  "
            f"skyline {out[site]['skyline_m']:6.1f} m above {datum:9.3f} m  {path.name}"
        )

    target = ROOT / "outputs/city_gallery/metrics.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"wrote {target}, {len(out)} sites")


if __name__ == "__main__":
    main()
