import json
import pathlib

import bpy

ROOT = pathlib.Path("/home/user/aegis/papers/city-exposure-study/hybrid_twin")

# wipe default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

osm = json.load(open(ROOT / "data" / "osm_buildings.json"))
dec = json.load(open(ROOT / "data" / "decisions.json"))
mats = json.load(open(ROOT / "data" / "materials.json"))

blds = osm["buildings"] if isinstance(osm, dict) and "buildings" in osm else osm
by_id = {str(b.get("id", b.get("osm_id"))): b for b in blds}
drec = {str(r.get("id", r.get("osm_id"))): r for r in (dec if isinstance(dec, list) else dec.get("buildings", []))}

# Graslei east-bank row: find buildings by name and neighbors near the quay.
# The quay runs roughly N-S near x ~ -100..-60 in ENU (walk started at Korenlei).
named = {str(b.get("id")): (b.get("tags", {}) or {}).get("name") for b in blds if (b.get("tags", {}) or {}).get("name")}
print("named buildings:", {k: v for k, v in named.items()})

# print footprint bbox + height + material for a few knowns
for bid in ["493993762", "107539763", "493993759", "493993669"]:
    b = by_id.get(bid)
    r = drec.get(bid, {})
    if not b:
        continue
    poly = b.get("footprint") or b.get("polygon") or b.get("points")
    if poly:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        print(bid, named.get(bid), "bbox x", round(min(xs), 1), round(max(xs), 1),
              "y", round(min(ys), 1), round(max(ys), 1),
              "h", r.get("height_final", r.get("height")), "ground", r.get("ground_z"),
              "mat", mats.get(bid))
    else:
        print(bid, "keys:", list(b.keys()))
