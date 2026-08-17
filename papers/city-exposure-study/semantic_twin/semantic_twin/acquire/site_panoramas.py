"""Acquire the selected panorama walk for one screened site."""

from __future__ import annotations

import json
import hashlib
import pathlib
from dataclasses import asdict, dataclass
from typing import Any

from semantic_twin import paths
from semantic_twin.acquire import load_support_mesh
from semantic_twin.acquire.panorama_selection import SelectionOptions, select
from semantic_twin.acquire.streetview import (
    StreetViewTiles,
    download_panorama,
    google_api_key,
    native_zoom,
    pose_from_metadata,
    zoom_dimensions,
)
from semantic_twin.scene.site_config import load_scene


@dataclass(frozen=True)
class FetchOptions:
    """Controls for selecting, downloading, and storing a site's panoramas."""

    count: int
    zoom: int
    screening: pathlib.Path
    workers: int
    out_root: pathlib.Path | None = None
    walk_date: str | None = None
    open_sky_m: float = 2.5
    along_links: bool = False


def settled_directory(out_dir: pathlib.Path, index: int, pano_id: str) -> pathlib.Path:
    """Find a panorama by identifier even if its old selection index changed."""
    for existing in sorted(out_dir.glob("pano_*")):
        metadata_path = existing / "metadata.json"
        if not existing.is_dir() or not metadata_path.is_file():
            continue
        try:
            cached_id = json.loads(metadata_path.read_text()).get("panoId")
        except (json.JSONDecodeError, OSError):
            continue
        if cached_id == pano_id:
            return existing

    tail = pano_id[:16]
    if len(pano_id) <= len(tail):
        legacy = sorted(path for path in out_dir.glob(f"pano_*_{tail}") if path.is_dir())
        if legacy:
            return legacy[0]
        return out_dir / f"pano_{index:02d}_{tail}"

    digest = hashlib.sha256(pano_id.encode()).hexdigest()[:12]
    settled = out_dir / f"pano_{index:02d}_{digest}_{tail}"
    for existing in sorted(out_dir.glob(f"pano_*_{digest}_{tail}")):
        if existing.is_dir():
            return existing
    return settled


def site_row(screening: pathlib.Path, name: str) -> dict[str, Any]:
    rows = json.loads(screening.read_text())["rows"]
    for row in rows:
        if row["key"] == name:
            return row
    raise SystemExit(f"{name} is not in {screening}")


def fetch_site_panoramas(scene_path: pathlib.Path, options: FetchOptions) -> dict[str, Any]:
    """Acquire the selected panoramas and write their walk manifest."""
    scene = load_scene(scene_path)
    name = str(scene["name"])
    row = site_row(options.screening, name)

    support_mesh = load_support_mesh(scene, root=paths.root())
    if support_mesh is None:
        raise SystemExit(f"{name}: source_mesh is missing, so no camera altitude can be measured")

    picked, provenance = select(
        row,
        SelectionOptions(
            count=options.count,
            walk_date=options.walk_date,
            support_mesh=support_mesh,
            ground_z_m=float(scene["camera_ground_z_m"]),
            open_sky_m=options.open_sky_m,
            along_links=options.along_links,
        ),
    )
    out_dir = options.out_root or paths.panorama_set(name)
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
        settled = min(options.zoom, native_zoom(json.loads(cached.read_text()))) if cached.exists() else options.zoom
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
        settled = min(options.zoom, native_zoom(metadata))
        pose = pose_from_metadata(metadata, scene, support_mesh=support_mesh)
        cached.write_text(json.dumps(metadata, indent=2))
        (pano_dir / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
        (pano_dir / "session.json").write_text(json.dumps(safe_session, indent=2))
        width, height = zoom_dimensions(metadata, settled)
        tiles = -(-width // int(session["tileWidth"])) * -(-height // int(session["tileHeight"]))
        destination = download_panorama(
            client,
            metadata,
            pano_dir,
            zoom=settled,
            workers=options.workers,
            max_tiles=tiles + 8,
        )
        requests += tiles
        written.append(pano_dir.name)
        zooms[pano_dir.name] = settled
        print(
            f"[panorama] {pano_dir.name} {metadata.get('date', 'undated')} {width}x{height} "
            f"enu=({pose.position_enu_m[0]:.1f}, {pose.position_enu_m[1]:.1f}, {pose.position_enu_m[2]:.2f}) "
            f"tiles={tiles} zoom={settled} -> {destination.name}",
            flush=True,
        )

    if len(written) != len(set(written)):
        raise RuntimeError(f"{name}: multiple selected panorama identifiers resolved to one cache directory")

    manifest = {
        "site": name,
        "zoom": options.zoom,
        "panorama_zoom": zooms,
        "panorama_dirs": written,
        "selection": provenance,
        "approximate_requests": requests,
    }
    (out_dir / "walk_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
