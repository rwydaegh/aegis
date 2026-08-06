"""Append candidate clutter node groups and print their socket interfaces.

The detachment test. If `car instancing` takes a curve or a mesh and a seed, we can
drive it against our own quay edge and road graph and ignore the street generator
entirely. If its inputs are internal handles from `street layout`, we cannot.

    ~/blender-4.5/blender -b -P tools/citygen/probe_nodegroups.py
"""

import pathlib

import bpy

BLEND = pathlib.Path(__file__).parent / "The_City_Generator_2.6" / "City_Generator2.0.blend"

WANT = [
    "car instancing",
    "side walk assets",
    "Street Procedural Elements",
    "distribute traffic points",
    "CityGenOptimised_Street_light",
    "Park",
    "decals",
    "plains to instances",
    "random extrude edges",
]


def describe(ng) -> None:
    print(f"\n--- {ng.name} ---")
    ins, outs = [], []
    for item in ng.interface.items_tree:
        if item.item_type != "SOCKET":
            continue
        entry = f"{item.socket_type.replace('NodeSocket', '')} {item.name}"
        default = getattr(item, "default_value", None)
        if default is not None and not hasattr(default, "__len__"):
            entry += f" = {default}"
        (ins if item.in_out == "INPUT" else outs).append(entry)
    print(f"  IN  ({len(ins)}):")
    for e in ins:
        print(f"    {e}")
    print(f"  OUT ({len(outs)}):")
    for e in outs:
        print(f"    {e}")
    # which other groups does it call
    nested = sorted({n.node_tree.name for n in ng.nodes
                     if n.type == "GROUP" and n.node_tree})
    if nested:
        print(f"  CALLS: {', '.join(nested)}")


def main() -> None:
    with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
        dst.node_groups = [n for n in src.node_groups if n in WANT]
    print(f"appended {len(bpy.data.node_groups)} node groups")
    for name in WANT:
        ng = bpy.data.node_groups.get(name)
        if ng is None:
            print(f"\n--- {name} --- NOT FOUND")
            continue
        describe(ng)


if __name__ == "__main__":
    main()
