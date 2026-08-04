"""Fetch a spatially spread set of panoramas for one screened site.

`semantic_twin.acquire.streetview` acquires the one panorama nearest a scene's centre,
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

The screener picks that date by largest connected component, and at three sites
in eleven that rule picks the wrong thing. At Hachiko the 2018-05 component is
105 panoramas of the Shibuchika underground arcade and the Shibuya station
concourse, which beat every outdoor drive on count and produced thirteen
panoramas with a measured sky fraction of 0.000. At Rynek Glowny the 2024-11
component is 162 panoramas of the inside of the Cloth Hall, and at Place du
Capitole the 2018-12 component is 118 panoramas of the inside of the Capitole.
Both are third party virtual tours, both beat every outdoor capture on count,
and neither has a single station with open sky above it. An indoor panorama
cannot be skyline-registered at all, so ``--walk-date`` overrides the screener
and names the capture date to walk. Prefer it over relaxing the alignment: the
failure is in the imagery, not in the objective.

``--open-sky-m`` catches the rest of the same failure without a manual
override, and it is on by default. A candidate is dropped when the topmost tile
surface above its easting and northing sits more than that far above the
scene datum, which is what an arcade, a station concourse or a cathedral nave
looks like from above. It is a screen on the geometry rather than on the image,
so it costs no request and it runs before any tile is paid for. It is not a
substitute for the sky fraction measured on the segmented panorama, which is
the thing that finally decides whether a station registers, only a way of not
spending 400 requests to find that out. Where a walk mixes indoor and outdoor
stations, as the 2020-04 walk of the Rynek does at 55 of 118, the filter turns
an unusable set into a usable one.

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

from semantic_twin.acquire import load_support_mesh  # noqa: E402
from semantic_twin.acquire.streetview import (  # noqa: E402
    StreetViewTiles,
    download_panorama,
    google_api_key,
    native_zoom,
    pose_from_metadata,
    zoom_dimensions,
)
from semantic_twin import paths  # noqa: E402
from semantic_twin.scene.site_config import load_scene  # noqa: E402

DEFAULT_SCREENING = paths.screening()


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


def chain_subset(walk: list[dict[str, Any]], positions: np.ndarray, count: int) -> list[int]:
    """Consecutive panoramas along the capture, outward from the centre.

    Farthest-point sampling answers a different question. It spreads the cameras
    so that as much facade as possible is seen at least once, which is the right
    rule when the cameras are the evidence. It is the wrong rule when the cameras
    are the walk, because it deliberately leaves the gaps between them as wide as
    it can: at 14 cameras it produces 20 to 81 m between neighbours, out of a
    capture whose own frames are 2 to 11 m apart.

    This walks the links instead. Start at the panorama nearest the centre and
    take neighbours outward, alternating between the two ends, so a budget that
    runs out leaves a chain centred on the square rather than a chain running off
    one side of it.
    """
    if not walk:
        return []
    count = min(count, len(walk))
    index = {p["pano_id"]: i for i, p in enumerate(walk)}
    first = int(np.argmin(np.linalg.norm(positions, axis=1)))

    chosen = [first]
    seen = {first}
    # Two ends grown together. Each end holds the panoramas reachable from it
    # that nothing has taken yet, nearest first, so the chain stays a chain even
    # where the capture branches at a junction.
    frontier = [[first], [first]]
    while len(chosen) < count:
        grew = False
        for end in frontier:
            if len(chosen) >= count or not end:
                continue
            here = end[-1]
            # The screener writes links as bare identifiers. Objects carrying a
            # ``pano_id`` are accepted too, because that is what the provider
            # returns and what a future screener may keep.
            neighbours = [
                link if isinstance(link, str) else link.get("pano_id") for link in walk[here].get("links", [])
            ]
            options = [index[n] for n in neighbours if n in index and index[n] not in seen]
            if not options:
                end.clear()
                continue
            nxt = min(options, key=lambda i: float(np.linalg.norm(positions[i] - positions[here])))
            chosen.append(nxt)
            seen.add(nxt)
            end.append(nxt)
            grew = True
        if not grew:
            break
    return chosen


def topmost_surface(
    support_mesh: tuple[np.ndarray, np.ndarray],
    positions: np.ndarray,
) -> np.ndarray:
    """Height of the highest tile surface above each easting and northing.

    NaN where the crop holds nothing above the point, which happens at the rim
    of a mesh and is treated as unknown rather than as open sky.
    """
    try:
        import trimesh
        from trimesh.ray.ray_pyembree import RayMeshIntersector
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "the open sky filter needs the raycast extra: pip install trimesh embreex, "
            "or pass --open-sky-m 0 to select on count alone"
        ) from exc
    vertices, faces = support_mesh
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, np.float64), faces=np.asarray(faces), process=False)
    ceiling = float(mesh.vertices[:, 2].max()) + 50.0
    origins = np.column_stack([positions, np.full(len(positions), ceiling)])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (len(positions), 1))
    locations, index_ray, _ = RayMeshIntersector(mesh).intersects_location(origins, directions, multiple_hits=False)
    height = np.full(len(positions), np.nan)
    if len(index_ray):
        height[index_ray] = locations[:, 2]
    return height


def settled_directory(out_dir: pathlib.Path, index: int, pano_id: str) -> pathlib.Path:
    """Where a panorama sits on disk, whatever position it held when it arrived.

    A directory is named ``pano_{index}_{pano_id}``, and the index is only the
    position in the chosen set. That position is not a property of the
    panorama: change the count, the walk date or the open sky filter and every
    panorama after the first shifts by one. The skip test then looked inside
    the directory it was about to write, found nothing, and paid for a
    panorama that was already fully on disk under an older index.

    It cost 2,048 tile requests of a 15,000 per day cap on one Madrid run: four
    panoramas at 512 tiles each, all four downloaded the day before. Matching
    on the identifier makes the fetch what it should always have been, which is
    one download per panorama for as long as the file is kept.
    """
    tail = pano_id[:16]
    for existing in sorted(out_dir.glob(f"pano_*_{tail}")):
        if existing.is_dir():
            return existing
    return out_dir / f"pano_{index:02d}_{tail}"


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
    *,
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    ground_z_m: float | None = None,
    open_sky_m: float = 2.5,
    along_links: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose a subset of the site's walk, with its own provenance.

    Two rules, and they answer different questions. Spread maximises how much
    facade is seen at all. Chain follows the capture itself, which is what a walk
    from one end of a street to the other needs.
    """
    date = walk_date or row["walk_date"]
    walk = [p for p in row["panoramas"] if p["date"] == date and p["links"]]
    if not walk:
        dates = sorted({p["date"] for p in row["panoramas"] if p["links"]})
        raise SystemExit(f"{row['key']}: no linked panoramas dated {date}, available: {', '.join(dates)}")
    positions = np.array([[p["east_m"], p["north_m"]] for p in walk], dtype=np.float64)

    roofed = 0
    if open_sky_m > 0.0 and support_mesh is not None and ground_z_m is not None:
        above = topmost_surface(support_mesh, positions)
        outdoor = ~(above > ground_z_m + open_sky_m)
        roofed = int((~outdoor).sum())
        if not outdoor.any():
            raise SystemExit(
                f"{row['key']}: every one of the {len(walk)} panoramas dated {date} has tile surface more "
                f"than {open_sky_m} m above it, so the whole capture is indoors. Name another capture "
                f"date with --walk-date."
            )
        walk = [p for p, keep in zip(walk, outdoor, strict=True) if keep]
        positions = positions[outdoor]

    order = chain_subset(walk, positions, count) if along_links else spread_subset(positions, count)
    picked = [walk[i] for i in order]
    taken = positions[order] if order else np.zeros((0, 2))
    separations = []
    for i in range(1, len(taken)):
        separations.append(float(np.linalg.norm(taken[i] - taken[:i], axis=1).min()))
    provenance = {
        "selection": (
            "consecutive panoramas along the capture links, grown outward from the centre"
            if along_links
            else "farthest-point sampling over the walk, seeded at the panorama nearest the centre"
        ),
        "walk_date": date,
        "screened_walk_date": row["walk_date"],
        "walk_date_overridden": walk_date is not None and walk_date != row["walk_date"],
        "walk_panoramas": len(walk),
        "walk_panoramas_dropped_as_roofed": roofed,
        "open_sky_m": open_sky_m if open_sky_m > 0.0 else None,
        "open_sky_rule": (
            "a candidate is dropped when the topmost tile surface above it is more than open_sky_m "
            "above the scene ground datum, which is what an arcade or a concourse looks like from "
            "above. It screens the geometry, not the image, so it costs no request."
        )
        if open_sky_m > 0.0
        else None,
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
    open_sky_m: float = 2.5,
    along_links: bool = False,
) -> dict[str, Any]:
    scene = load_scene(scene_path)
    name = str(scene["name"])
    row = site_row(screening, name)

    support_mesh = load_support_mesh(scene, root=SCRIPT_DIR)
    if support_mesh is None:
        raise SystemExit(f"{name}: source_mesh is missing, so no camera altitude can be measured")

    picked, provenance = select(
        row,
        count,
        walk_date,
        support_mesh=support_mesh,
        ground_z_m=float(scene["camera_ground_z_m"]),
        open_sky_m=open_sky_m,
        along_links=along_links,
    )
    out_dir = out_root or (SCRIPT_DIR / "data" / "panoramas" / name)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = StreetViewTiles(google_api_key())
    session = client.create_session()
    safe_session = {k: session[k] for k in ("expiry", "tileWidth", "tileHeight", "imageFormat")}
    requests = 1
    written = []
    zooms: dict[str, int] = {}
    for index, panorama in enumerate(picked):
        pano_dir = settled_directory(out_dir, index, panorama["pano_id"])
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
    parser.add_argument(
        "--open-sky-m",
        type=float,
        default=2.5,
        help=(
            "drop a candidate whose topmost tile surface sits more than this far above the scene "
            "ground datum, which is what an arcade or a concourse looks like from above. 0 disables it."
        ),
    )
    parser.add_argument(
        "--along-links",
        action="store_true",
        help=(
            "take consecutive panoramas along the capture instead of spreading them out. Use this "
            "when the cameras are the walk rather than the evidence: it gives the capture's own "
            "spacing, a few metres, where spreading gives tens of metres."
        ),
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
        open_sky_m=args.open_sky_m,
        along_links=args.along_links,
    )
    selection = manifest["selection"]
    print(
        f"[done] {manifest['site']}: {len(manifest['panorama_dirs'])} panoramas, "
        f"minimum separation {selection['minimum_separation_m']} m, "
        f"{selection['walk_panoramas_dropped_as_roofed']} candidates dropped as roofed, "
        f"about {manifest['approximate_requests']} requests"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
