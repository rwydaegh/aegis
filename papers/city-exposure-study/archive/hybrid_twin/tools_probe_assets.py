"""What is actually inside the City Generator asset collections.

Instancing a known object at a measured position is far more robust than driving a
41-socket node group. This tells me which of the two each clutter class needs, and
gives me triangle counts so the RT budget is known before anything is built.

    ~/blender-4.5/blender -b -P tools_probe_assets.py
"""

import pathlib

import bpy

BLEND = (pathlib.Path("/home/user/aegis/tools/citygen/The_City_Generator_2.6")
         / "City_Generator2.0.blend")

WANT = ["Car Assets", "car model", "trees", "Street Lights", "Side Walk Assets",
        "Universal side walk assets ", "traffic signs", "railings", "decals"]


def main() -> None:
    with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c in WANT]

    for name in WANT:
        col = bpy.data.collections.get(name)
        if col is None:
            print(f"\n=== {name} === NOT FOUND")
            continue
        objs = [o for o in col.all_objects]
        print(f"\n=== {name} === {len(objs)} objects")
        for o in sorted(objs, key=lambda o: o.name)[:25]:
            if o.type != "MESH":
                print(f"  {o.name:38s} [{o.type}]")
                continue
            me = o.data
            tris = sum(max(0, len(p.vertices) - 2) for p in me.polygons)
            bb = [o.matrix_world @ __import__("mathutils").Vector(c)
                  for c in o.bound_box]
            xs = [v.x for v in bb]
            ys = [v.y for v in bb]
            zs = [v.z for v in bb]
            dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
            print(f"  {o.name:38s} {tris:6d} tris  "
                  f"{dims[0]:5.2f} x {dims[1]:5.2f} x {dims[2]:5.2f} m")
        if len(objs) > 25:
            print(f"  ... and {len(objs) - 25} more")


if __name__ == "__main__":
    main()
