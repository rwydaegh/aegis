"""Pack the final hybrid twin (scenes/hybrid/*.ply + scene.xml materials) into
a single colored GLB for browser viewing.

Run: ~/blender-4.5/blender -b -P pack_viewer.py
"""

import pathlib
import xml.etree.ElementTree as ET

import bpy

ROOT = pathlib.Path(__file__).parent
SCENE = ROOT / "scenes" / "hybrid"

COLORS = {
    "brick": (0.55, 0.26, 0.20, 1.0),
    "plasterboard": (0.91, 0.88, 0.80, 1.0),
    "marble": (0.81, 0.81, 0.78, 1.0),
    "concrete": (0.60, 0.60, 0.60, 1.0),
    "glass": (0.50, 0.70, 0.80, 1.0),
    "wood": (0.30, 0.48, 0.23, 1.0),
    "metal": (0.69, 0.71, 0.73, 1.0),
    "medium_dry_ground": (0.45, 0.42, 0.36, 1.0),
}


def mat_for(name):
    key = name.replace("mat-", "").replace("itu_", "")
    m = bpy.data.materials.get(key)
    if m is None:
        m = bpy.data.materials.new(key)
        m.diffuse_color = COLORS.get(key, (0.8, 0.5, 0.8, 1.0))
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = COLORS.get(key, (0.8, 0.5, 0.8, 1.0))
        bsdf.inputs["Roughness"].default_value = 0.9
    return m


bpy.ops.wm.read_factory_settings(use_empty=True)

root = ET.parse(SCENE / "scene.xml").getroot()
n = 0
for shape in root.iter("shape"):
    fn = next((s.get("value") for s in shape.iter("string") if s.get("name") == "filename"), None)
    ref = next((r.get("id") for r in shape.iter("ref")), "mat-itu_concrete")
    if not fn:
        continue
    bpy.ops.wm.ply_import(filepath=str(SCENE / fn))
    obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else bpy.context.active_object
    obj.data.materials.clear()
    obj.data.materials.append(mat_for(ref))
    n += 1

print(f"imported {n} shapes")
out = ROOT / "viewer" / "twin.glb"
out.parent.mkdir(exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB")
print(f"wrote {out}")
