import json
import math

import numpy as np

A, F = 6378137.0, 1 / 298.257223563
E2 = F * (2 - F)
LAT0, LON0 = 51.0550, 3.7220


def llh_to_ecef(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1 - E2 * math.sin(la) ** 2)
    return np.array([(n + h) * math.cos(la) * math.cos(lo),
                     (n + h) * math.cos(la) * math.sin(lo),
                     (n * (1 - E2) + h) * math.sin(la)])


def enu_rotation(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return np.array([
        [-math.sin(lo), math.cos(lo), 0],
        [-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)],
        [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)],
    ])


P0 = llh_to_ecef(LAT0, LON0, 0.0)
R_ENU = enu_rotation(LAT0, LON0)


def ring_enu(ring):
    return [(R_ENU @ (llh_to_ecef(lat, lon, 0.0) - P0))[:2] for lon, lat in ring[:-1]]


NS = globals()
drec2 = {str(r["id"]): r for r in json.load(open("/home/user/aegis/papers/city-exposure-study/hybrid_twin/data/decisions.json"))["decisions"]}

# candidates: centroid in the Graslei band (east bank of the canal)
rows = []
for bid, b in by_id.items():
    ring = b.get("ring")
    if not ring or len(ring) < 4:
        continue
    pts = ring_enu(ring)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    if -70 < cx < -10 and 10 < cy < 130:
        r = drec2.get(bid, {})
        rows.append((round(cy, 1), round(cx, 1), bid, named.get(bid),
                     r.get("h_final"), r.get("ground_z"), mats.get(bid), round(r.get("area_m2", 0))))
for row in sorted(rows):
    print(row)
print(len(rows), "candidates")
