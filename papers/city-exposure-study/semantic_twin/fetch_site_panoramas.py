"""Fetch a spatially spread set of panoramas for one screened site.

`semantic_twin.panorama` acquires the one panorama nearest a scene's centre,
which is the right tool for a site with one camera and the wrong one here. A
site needs twelve to sixteen cameras, and which twelve decides how much of the
scene is ever observed.

They are chosen by farthest-point sampling over the walk recorded in
`outputs/city_screening/screening.json`: start from the panorama nearest the
site centre, then repeatedly add whichever candidate is farthest from everything
already chosen. That maximises the minimum separation of the set, which is the
selection rule the coverage measurement argues for. Extent binds harder than
count: widening a site from 60 m to 80 m lifts achievable surface coverage from
30.6 to 44.8 percent of scene area, worth more than tripling the camera count in
the middle, and the sixteen nearest the centre would be a dense cluster that
sees one ring of facades many times over.

Only panoramas from the walk's own capture date are eligible, so the set is
temporally coherent and does not mix a 2014 scaffold with a 2024 facade.

The screener picks that date by largest connected component, and at one site in
ten that rule picks the wrong thing. At Hachiko the 2018-05 component is 105
panoramas of the Shibuchika underground arcade and the Shibuya station concourse,
which beat every outdoor drive on count and produced thirteen panoramas with a
measured sky fraction of 0.000. An indoor panorama cannot be skyline-registered
at all, so ``--walk-date`` overrides the screener and names the capture date to
walk. Prefer it over relaxing the alignment: the failure is in the imagery, not
in the objective.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python fetch_site_panoramas.py \
      --scene config/prague_staromestske.json --count 14 --zoom 5
    ../../../.venv/bin/python fetch_site_panoramas.py \
      --scene config/tokyo_hachiko.json --count 14 --zoom 5 --walk-date 2023-09
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import asdict
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.panorama import (  # noqa: E402
    StreetViewTiles,
    download_panorama,
    load_support_mesh,
    native_zoom,
    pose_from_metadata,
    zoom_dimensions,
)
from semantic_twin.scene import inhouse_api_key, load_scene  # noqa: E402

DEFAULT_SCREENING = pathlib.Path("outputs/city_screening/screening.json")


def spread_subset(positions: np.ndarray, count: int) -> list[int]:
    """Farthest-point sampling, seeded with the point nearest the centre.

    Returns indices in the order they were chosen, so a truncated run still
    holds the most spread-out subset of what it managed.
    """
    if positions.shape[0] == 0:
        return []
    count = min(count, positions.shape[0])
    first = int(np.argmin(np.linalg.norm(positions, axis=1)))
    chosen = [first]
    distance = np.linalg.norm(positions - positions[first], axis=1)
    while len(chosen) < count:
        nxt = int(np.argmax(distance))
        if distance[nxt] <= 0.0:
            break
        chosen.append(nxt)
        distance = np.minimum(distance, np.linalg.norm(positions - positions[nxt], axis=1))
    return chosen


def site_row(screening: pathlib.Path, name: str) -> dict[str, Any]:
    rows = json.loads(screening.read_text())["rows"]
    for row in rows:
        if row["key"] == name:
            return row
    raise SystemExit(f"{name} is not in {screening}")


def select(
    row: dict[str, Any],
    count: int,
    walk_date: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose the spread subset of the site's walk, with its own provenance."""
    date = walk_date or row["walk_date"]
    walk = [p for p in row["panoramas"] if p["date"] == date and p["links"]]
    if not walk:
        dates = sorted({p["date"] for p in row["panoramas"] if p["links"]})
        raise SystemExit(f"{row['key']}: no linked panoramas dated {date}, available: {', '.join(dates)}")
    positions = np.array([[p["east_m"], p["north_m"]] for p in walk], dtype=np.float64)
    order = spread_subset(positions, count)
    picked = [walk[i] for i in order]
    taken = positions[order] if order else np.zeros((0, 2))
    separations = []
    for i in range(1, len(taken)):
        separations.append(float(np.linalg.norm(taken[i] - taken[:i], axis=1).min()))
    provenance = {
        "selection": "farthest-point sampling over the walk, seeded at the panorama nearest the centre",
        "walk_date": date,
        "screened_walk_date": row["walk_date"],
        "walk_date_overridden": walk_date is not None and walk_date != row["walk_date"],
        "walk_panoramas": len(walk),
        "selected": len(picked),
        "minimum_separation_m": round(min(separations), 2) if separations else None,
        "median_separation_m": round(float(np.median(separations)), 2) if separations else None,
        "extent_east_m": [round(float(taken[:, 0].min()), 1), round(float(taken[:, 0].max()), 1)]
        if len(taken)
        else None,
        "extent_north_m": [round(float(taken[:, 1].min()), 1), round(float(taken[:, 1].max()), 1)]
        if len(taken)
        else None,
        "screening_median_spacing_m": row["walk_spacing_m"],
    }
    return picked, provenance


def fetch(
    scene_path: pathlib.Path,
    *,
    count: int,
    zoom: int,
    screening: pathlib.Path,
    workers: int,
    out_root: pathlib.Path | None = None,
    walk_date: str | None = None,
) -> dict[str, Any]:
    scene = load_scene(scene_path)
    name = str(scene["name"])
    row = site_row(screening, name)
    picked, provenance = select(row, count, walk_date)
    out_dir = out_root or (SCRIPT_DIR / "data" / "panoramas" / name)
    out_dir.mkdir(parents=True, exist_ok=True)

    support_mesh = load_support_mesh(scene, root=SCRIPT_DIR)
    if support_mesh is None:
        raise SystemExit(f"{name}: source_mesh is missing, so no camera altitude can be measured")

    client = StreetViewTiles(inhouse_api_key())
    session = client.create_session()
    safe_session = {k: session[k] for k in ("expiry", "tileWidth", "tileHeight", "imageFormat")}
    requests = 1
    written = []
    zooms: dict[str, int] = {}
    for index, panorama in enumerate(picked):
        pano_dir = out_dir / f"pano_{index:02d}_{panorama['pano_id'][:16]}"
        pano_dir.mkdir(parents=True, exist_ok=True)
        cached = pano_dir / "metadata.json"
        # A photosphere tops out below the requested zoom, so the file already on
        # disk may carry a lower number than --zoom. Its own metadata says which,
        # and reading it back costs no request.
        settled = min(zoom, native_zoom(json.loads(cached.read_text()))) if cached.exists() else zoom
        if (pano_dir / f"panorama_z{settled}.jpg").exists():
            print(f"[skip] {pano_dir.name}", flush=True)
            written.append(pano_dir.name)
            zooms[pano_dir.name] = settled
            continue
        metadata = client.metadata(pano_id=panorama["pano_id"])
        requests += 1
        if "panoId" not in metadata:
            print(f"[warn] {panorama['pano_id']} returned no panorama, skipping", flush=True)
            continue
        settled = min(zoom, native_zoom(metadata))
        pose = pose_from_metadata(metadata, scene, support_mesh=support_mesh)
        cached.write_text(json.dumps(metadata, indent=2))
        (pano_dir / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
        (pano_dir / "session.json").write_text(json.dumps(safe_session, indent=2))
        width, height = zoom_dimensions(metadata, settled)
        tiles = -(-width // int(session["tileWidth"])) * -(-height // int(session["tileHeight"]))
        destination = download_panorama(client, metadata, pano_dir, zoom=settled, workers=workers, max_tiles=tiles + 8)
        requests += tiles
        written.append(pano_dir.name)
        zooms[pano_dir.name] = settled
        print(
            f"[panorama] {pano_dir.name} {metadata.get('date', 'undated')} {width}x{height} "
            f"enu=({pose.position_enu_m[0]:.1f}, {pose.position_enu_m[1]:.1f}, {pose.position_enu_m[2]:.2f}) "
            f"tiles={tiles} zoom={settled} -> {destination.name}",
            flush=True,
        )

    manifest = {
        "site": name,
        "zoom": zoom,
        "panorama_zoom": zooms,
        "panorama_dirs": written,
        "selection": provenance,
        "approximate_requests": requests,
    }
    (out_dir / "walk_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--count", type=int, default=14)
    parser.add_argument("--zoom", type=int, choices=range(0, 6), default=5)
    parser.add_argument("--screening", type=pathlib.Path, default=DEFAULT_SCREENING)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument(
        "--walk-date",
        help="capture date to walk, as YYYY-MM, overriding the screener's largest-component choice",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    manifest = fetch(
        args.scene,
        count=args.count,
        zoom=args.zoom,
        screening=args.screening,
        workers=args.workers,
        out_root=args.out,
        walk_date=args.walk_date,
    )
    selection = manifest["selection"]
    print(
        f"[done] {manifest['site']}: {len(manifest['panorama_dirs'])} panoramas, "
        f"minimum separation {selection['minimum_separation_m']} m, "
        f"about {manifest['approximate_requests']} requests"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
