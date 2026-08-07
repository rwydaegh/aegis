"""Route a pedestrian walk on the OSM street graph (no external routing API).

Builds a foot-network from an OSM XML file, runs Dijkstra between the nodes
nearest to origin/destination, writes a dense GPX.

Usage: python route_foot.py --osm-xml <map.osm> --from 51.05502,3.71966 \
    --to 51.05601,3.72207 --out data/walk.gpx
"""

from __future__ import annotations

import argparse
import heapq
import math
import pathlib
import xml.etree.ElementTree as ET

FOOT_HIGHWAYS = {
    "footway", "pedestrian", "path", "steps", "living_street", "residential",
    "service", "unclassified", "tertiary", "secondary", "primary", "cycleway",
    "track", "bridleway",
}


def haversine(a, b):
    la1, lo1 = a
    la2, lo2 = b
    x = math.radians(lo2 - lo1) * math.cos(math.radians((la1 + la2) / 2))
    y = math.radians(la2 - la1)
    return 6371000.0 * math.hypot(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm-xml", required=True)
    ap.add_argument("--from", dest="orig", required=True)
    ap.add_argument("--to", dest="dest", required=True)
    ap.add_argument("--out", default="data/walk.gpx")
    args = ap.parse_args()

    orig = tuple(map(float, args.orig.split(",")))
    dest = tuple(map(float, args.dest.split(",")))

    nodes = {}
    edges = {}
    root = ET.parse(args.osm_xml).getroot()
    for n in root.iter("node"):
        nodes[n.get("id")] = (float(n.get("lat")), float(n.get("lon")))
    n_ways = 0
    for w in root.iter("way"):
        tags = {t.get("k"): t.get("v") for t in w.iter("tag")}
        hw = tags.get("highway")
        if hw not in FOOT_HIGHWAYS or tags.get("foot") == "no":
            continue
        n_ways += 1
        refs = [nd.get("ref") for nd in w.iter("nd")]
        for a, b in zip(refs[:-1], refs[1:]):
            if a in nodes and b in nodes:
                d = haversine(nodes[a], nodes[b])
                edges.setdefault(a, []).append((b, d))
                edges.setdefault(b, []).append((a, d))
    print(f"graph: {len(edges)} routable nodes from {n_ways} foot ways")

    def nearest(pt):
        return min(edges, key=lambda k: haversine(nodes[k], pt))

    s, t = nearest(orig), nearest(dest)
    print(f"snap: origin {haversine(nodes[s], orig):.0f} m, "
          f"dest {haversine(nodes[t], dest):.0f} m")

    dist = {s: 0.0}
    prev = {}
    pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t:
            break
        if d > dist.get(u, math.inf):
            continue
        for v, w in edges.get(u, []):
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if t not in prev and t != s:
        raise SystemExit("no route found")

    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    path.reverse()
    pts = [nodes[k] for k in path]
    print(f"route: {len(pts)} nodes, {dist[t]:.0f} m")

    out = pathlib.Path(args.out)
    with out.open("w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<gpx version="1.1" creator="route_foot" '
                'xmlns="http://www.topografix.com/GPX/1/1">\n <trk><trkseg>\n')
        for la, lo in pts:
            f.write(f'  <trkpt lat="{la}" lon="{lo}"></trkpt>\n')
        f.write(' </trkseg></trk>\n</gpx>\n')
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
