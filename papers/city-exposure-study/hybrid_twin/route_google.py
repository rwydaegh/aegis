"""Pedestrian walk from the Google Routes API (computeRoutes, WALK mode).

Replaces the offline Dijkstra of route_foot.py when the key has Routes API
enabled. Writes the same dense GPX format.

Usage: python route_google.py --from 51.05460,3.71960 --to 51.05610,3.72210 \
    [--via lat,lon ...] --out data/walk.gpx
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import urllib.request

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def decode_polyline(s: str) -> list[tuple[float, float]]:
    pts, idx, lat, lon = [], 0, 0, 0
    while idx < len(s):
        for which in (0, 1):
            shift = result = 0
            while True:
                b = ord(s[idx]) - 63
                idx += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if which == 0:
                lat += delta
            else:
                lon += delta
        pts.append((lat / 1e5, lon / 1e5))
    return pts


def waypoint(s: str) -> dict:
    la, lo = map(float, s.split(","))
    return {"location": {"latLng": {"latitude": la, "longitude": lo}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="orig", required=True)
    ap.add_argument("--to", dest="dest", required=True)
    ap.add_argument("--via", action="append", default=[])
    ap.add_argument("--out", default="data/walk.gpx")
    args = ap.parse_args()

    body = {
        "origin": waypoint(args.orig),
        "destination": waypoint(args.dest),
        "travelMode": "WALK",
        "polylineQuality": "HIGH_QUALITY",
    }
    if args.via:
        body["intermediates"] = [waypoint(v) for v in args.via]

    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": os.environ["GOOGLE_API_KEY"],
            "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,"
            "routes.polyline.encodedPolyline",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        route = json.load(r)["routes"][0]

    pts = decode_polyline(route["polyline"]["encodedPolyline"])
    print(f"route: {route['distanceMeters']} m, {route['duration']}, "
          f"{len(pts)} polyline points")

    out = pathlib.Path(args.out)
    with out.open("w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<gpx version="1.1" creator="route_google" '
                'xmlns="http://www.topografix.com/GPX/1/1">\n <trk><trkseg>\n')
        for la, lo in pts:
            f.write(f'  <trkpt lat="{la}" lon="{lo}"></trkpt>\n')
        f.write(' </trkseg></trk>\n</gpx>\n')
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
