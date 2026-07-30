"""List what is inside the City Generator .blend without installing the addon.

The question this answers: can the clutter and vehicle systems be appended as
standalone node groups and driven against our own geometry, or are they welded to
the addon's own street generator?

    ~/blender-4.5/blender -b -P tools/citygen/inspect_blend.py
"""

import pathlib

import bpy

BLEND = pathlib.Path(__file__).parent / "The_City_Generator_2.6" / "City_Generator2.0.blend"

KEYS = ("car", "vehicle", "tree", "lamp", "light", "street", "prop", "asset",
        "bench", "sign", "bin", "clutter", "facade", "building", "road", "people",
        "person", "pedestrian", "bike", "bollard")


def main() -> None:
    print(f"[blend] {BLEND}  ({BLEND.stat().st_size / 1e6:.0f} MB)")
    with bpy.data.libraries.load(str(BLEND), link=True) as (src, _dst):
        buckets = {
            "node_groups": list(src.node_groups),
            "collections": list(src.collections),
            "objects": list(src.objects),
            "materials": list(src.materials),
            "images": list(src.images),
            "worlds": list(src.worlds),
        }

    for name, items in buckets.items():
        print(f"\n=== {name}: {len(items)} ===")
        if not items:
            continue
        hits = [i for i in items if any(k in i.lower() for k in KEYS)]
        # show every node group, they are the interface we care about
        show = items if name == "node_groups" else hits[:60]
        for i in sorted(show):
            print(f"  {i}")
        if name != "node_groups" and len(hits) > 60:
            print(f"  ... and {len(hits) - 60} more matching")


if __name__ == "__main__":
    main()
