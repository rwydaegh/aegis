"""Measure sky fraction and skyline height for the city contact sheet."""

from __future__ import annotations

import json
import pathlib
import re

import numpy as np
import trimesh

from semantic_twin import paths

RUN_PREFIX = "city250_L3"
FREQ_GHZ = 15.0
SKYLINE_PERCENTILE = 99.5
GALLERY_RADIUS_M = 130
GALLERY_RADIUS_OVERRIDE = {"milan_duomo": 200}


def metric_mesh(site: str, root: pathlib.Path | None = None) -> pathlib.Path | None:
    study_root = root or paths.root()
    radius = GALLERY_RADIUS_OVERRIDE.get(site, GALLERY_RADIUS_M)
    directory = study_root / "data" / "geometry" / site
    for name in (f"inhouse_leaf_{radius}m_f64.ply", f"inhouse_leaf_{radius}m.ply"):
        if (directory / name).is_file():
            return directory / name
    return None


def walk_sky(site: str, exposure: pathlib.Path | None = None) -> tuple[float, float, float, int] | None:
    exposure_dir = exposure or paths.root() / "outputs" / "exposure_korenmarkt"
    path = exposure_dir / f"{RUN_PREFIX}_{site}_{FREQ_GHZ:g}ghz_locations.jsonl"
    if not path.exists():
        return None
    values = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            values.append(json.loads(line)["sky_fraction"])
        except json.JSONDecodeError:
            print(f"[warn] {path.name} has a torn record, not publishable")
            return None
    array = np.asarray(values, dtype=np.float64)
    return (
        float(np.median(array)),
        float(np.percentile(array, 5)),
        float(np.percentile(array, 95)),
        int(array.size),
    )


def measure_city_metrics(root: pathlib.Path | None = None) -> pathlib.Path:
    study_root = root or paths.root()
    exposure = study_root / "outputs" / "exposure_korenmarkt"
    out: dict[str, dict] = {}
    sites = sorted(directory.name for directory in (study_root / "data" / "geometry").iterdir() if directory.is_dir())
    for site in sites:
        path = metric_mesh(site, study_root)
        sky = walk_sky(site, exposure)
        if path is None or sky is None:
            print(f"{site:24s} skipped, no mesh or no run at {RUN_PREFIX}")
            continue
        manifest = json.loads((exposure / f"{RUN_PREFIX}_{site}_{FREQ_GHZ:g}ghz_manifest.json").read_text())
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

    target = study_root / "outputs" / "city_gallery" / "metrics.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"wrote {target}, {len(out)} sites")
    return target
