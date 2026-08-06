"""Fetch OSM building footprints (with height tags) for a bbox via Overpass.

Usage: python fetch_osm.py --lat 51.0550 --lon 3.7220 --radius 200 --out data/osm_buildings.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib

import requests

OVERPASS = "https://overpass-api.de/api/interpreter"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=float, default=200.0)
    ap.add_argument("--out", default="data/osm_buildings.json")
    args = ap.parse_args()

    dlat = args.radius / 111320.0
    dlon = args.radius / (111320.0 * math.cos(math.radians(args.lat)))
    bbox = f"{args.lat - dlat},{args.lon - dlon},{args.lat + dlat},{args.lon + dlon}"

    query = f"""
    [out:json][timeout:60];
    (
      way["building"]({bbox});
      relation["building"]({bbox});
    );
    out body geom;
    """
    r = requests.post(OVERPASS, data={"data": query}, timeout=90,
                      headers={"User-Agent": "aegis-hybrid-twin/0.1 (UGent research)"})
    r.raise_for_status()
    data = r.json()

    buildings = []
    for el in data["elements"]:
        if el["type"] == "way" and "geometry" in el:
            ring = [(g["lon"], g["lat"]) for g in el["geometry"]]
            buildings.append({"id": el["id"], "tags": el.get("tags", {}), "ring": ring})
        elif el["type"] == "relation":
            outer = []
            for m in el.get("members", []):
                if m.get("role") == "outer" and "geometry" in m:
                    outer.append([(g["lon"], g["lat"]) for g in m["geometry"]])
            if outer:
                buildings.append({"id": el["id"], "tags": el.get("tags", {}),
                                  "ring": max(outer, key=len), "relation": True})

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"bbox": bbox, "lat": args.lat, "lon": args.lon,
                               "radius": args.radius, "buildings": buildings}, indent=1))

    tagged = sum(1 for b in buildings
                 if "height" in b["tags"] or "building:levels" in b["tags"])
    print(f"{len(buildings)} buildings, {tagged} with height/levels tags")


if __name__ == "__main__":
    main()
