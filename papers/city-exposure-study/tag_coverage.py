"""How much of each study city's building height is real OSM data vs our default?

If a city's buildings are mostly untagged, its mesh is a flat slab at the type
default and the cross-city comparison measures OSM tagging quality, not urban form.
"""

import json
import subprocess
import sys
import time

sys.path.insert(0, "/home/user/aegis/src")
from aegis.study.run_cities import DEFAULT_CITIES  # noqa: E402

RADIUS = 240  # matches the 180 m study radius with margin

rows = []
for spec in DEFAULT_CITIES:
    q = (
        f"[out:json][timeout:60];"
        f'(way["building"](around:{RADIUS},{spec["lat"]},{spec["lon"]}););'
        f"out tags;"
    )
    for attempt in range(3):
        p = subprocess.run(
            ["curl", "-s", "--max-time", "90", "-X", "POST", "-d", q,
             "https://overpass-api.de/api/interpreter"],
            capture_output=True, text=True,
        )
        try:
            els = json.loads(p.stdout)["elements"]
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        print(f"{spec['name']:12s} OVERPASS FAILED")
        continue

    n = len(els)
    n_h = n_lv = n_roof = 0
    heights = []
    for e in els:
        t = e.get("tags", {})
        has_h = "height" in t
        has_lv = "building:levels" in t
        n_h += has_h
        n_lv += has_lv
        n_roof += "roof:height" in t
        if has_h:
            try:
                heights.append(float(str(t["height"]).split()[0]))
            except Exception:
                pass
        elif has_lv:
            try:
                heights.append(float(t["building:levels"]) * 3.0)
            except Exception:
                pass
    real = n_h + n_lv - sum(1 for e in els if "height" in e.get("tags", {}) and "building:levels" in e.get("tags", {}))
    frac = real / n if n else 0.0
    hs = sorted(heights)
    med = hs[len(hs) // 2] if hs else float("nan")
    mx = max(hs) if hs else float("nan")
    rows.append((spec["name"], n, frac, n_roof, med, mx))
    print(f"{spec['name']:12s} n={n:5d}  real height {frac*100:5.1f}%  roof:height on {n_roof:4d}  "
          f"median {med:6.1f} m  max {mx:7.1f} m", flush=True)
    time.sleep(2)

print("\n--- sorted by how much is guessed ---")
for name, n, frac, n_roof, med, mx in sorted(rows, key=lambda r: r[2]):
    print(f"  {name:12s} {(1-frac)*100:5.1f}% of buildings get our default height")
