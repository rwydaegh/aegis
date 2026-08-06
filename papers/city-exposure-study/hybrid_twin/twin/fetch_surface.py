"""Fetch the ground-surface layer from OSM: roads, footways, water, trees, barriers.

`fetch_osm.py` fetched buildings only. Clutter needs the things buildings sit
between: the quay edge to line with bollards, the carriageway to park cars along,
the water to reflect off, the mapped trees to keep where they are real.

    .venv/bin/python -m twin.fetch_surface --lat 51.0550 --lon 3.7220 --radius 220

Writes `data/osm_surface.json`. Idempotent, skips the network if the file already
covers the request (use --force to refetch).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib

import requests

MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)
UA = "aegis-hybrid-twin/0.2 (UGent research; robin.wydaeghe@ugent.be)"

# Each clause is (key, selector). Ways carry geometry, nodes carry points.
WAY_CLAUSES = (
    'way["highway"]',
    'way["area:highway"]',
    'way["footway"]',
    'way["natural"="water"]',
    'way["waterway"]',
    'way["barrier"]',
    'way["man_made"="quay"]',
    'way["natural"="wood"]',
    'way["landuse"~"grass|forest"]',
    'way["leisure"="park"]',
)
NODE_CLAUSES = (
    'node["natural"="tree"]',
    'node["highway"="street_lamp"]',
    'node["barrier"="bollard"]',
    'node["amenity"~"bench|waste_basket|bicycle_parking|restaurant|cafe|pub|bar"]',
    'node["highway"="bus_stop"]',
)


def query(bbox: str) -> str:
    parts = [f"  {c}({bbox});" for c in WAY_CLAUSES + NODE_CLAUSES]
    body = "\n".join(parts)
    return f"[out:json][timeout:90];\n(\n{body}\n);\nout body geom;\n"


def fetch(bbox: str) -> dict:
    last: Exception | None = None
    for url in MIRRORS:
        try:
            r = requests.post(url, data={"data": query(bbox)}, timeout=120,
                              headers={"User-Agent": UA})
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # try the next mirror
            print(f"  {url} failed: {exc}")
            last = exc
    raise RuntimeError(f"all Overpass mirrors failed, last: {last}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=51.0550)
    ap.add_argument("--lon", type=float, default=3.7220)
    ap.add_argument("--radius", type=float, default=220.0)
    ap.add_argument("--out", default="data/osm_surface.json")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    if out.exists() and not args.force:
        have = json.loads(out.read_text())
        if have.get("radius", 0) >= args.radius and have.get("lat") == args.lat:
            print(f"{out} already covers this request "
                  f"({len(have['ways'])} ways, {len(have['nodes'])} nodes). "
                  f"Use --force to refetch.")
            return

    dlat = args.radius / 111320.0
    dlon = args.radius / (111320.0 * math.cos(math.radians(args.lat)))
    bbox = (f"{args.lat - dlat},{args.lon - dlon},"
            f"{args.lat + dlat},{args.lon + dlon}")

    data = fetch(bbox)

    ways, nodes = [], []
    for el in data["elements"]:
        tags = el.get("tags", {})
        if el["type"] == "way" and "geometry" in el:
            ways.append({
                "id": el["id"],
                "tags": tags,
                "line": [(g["lon"], g["lat"]) for g in el["geometry"]],
            })
        elif el["type"] == "node":
            nodes.append({"id": el["id"], "tags": tags,
                          "lonlat": (el["lon"], el["lat"])})

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "bbox": bbox, "lat": args.lat, "lon": args.lon, "radius": args.radius,
        "ways": ways, "nodes": nodes,
    }, indent=1))

    def count(items: list, key: str) -> dict[str, int]:
        hist: dict[str, int] = {}
        for it in items:
            v = it["tags"].get(key)
            if v:
                hist[v] = hist.get(v, 0) + 1
        return dict(sorted(hist.items(), key=lambda kv: -kv[1]))

    print(f"{len(ways)} ways, {len(nodes)} nodes -> {out}")
    print(f"  highway: {count(ways, 'highway')}")
    print(f"  natural(node): {count(nodes, 'natural')}")
    print(f"  barrier(node): {count(nodes, 'barrier')}")
    print(f"  amenity(node): {count(nodes, 'amenity')}")


if __name__ == "__main__":
    main()
