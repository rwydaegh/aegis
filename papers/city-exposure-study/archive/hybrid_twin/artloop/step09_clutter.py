import math
import random

import bpy
import mathutils

vs = bpy.context.scene.view_settings
vs.view_transform = "Filmic"
vs.look = "Medium High Contrast"
vs.exposure = -0.3
bpy.data.objects["sun"].data.energy = 3.0

rnd = random.Random(7)
Z = 50.3


def cyl(name, x, y, z0, z1, r, material, verts=12):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=z1 - z0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, (z0 + z1) / 2))
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    bpy.context.collection.objects.link(ob)
    return ob


def sphere(name, x, y, z, r, material, sub=2):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(x, y, z))
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    bpy.context.collection.objects.link(ob)
    return ob


# ---- canal tour boat, moored along the quay ----
bx0, bx1 = -13.5, -9.5
by0, by1 = -18.0, -3.0
box("boat_hull", bx0, bx1, by0, by1, 48.55, 49.45, M["boat"])
box("boat_deck", bx0 + 0.25, bx1 - 0.25, by0 + 0.3, by1 - 0.3, 49.45, 49.55, M["canvas"])
for i in range(6):  # bench rows
    yy = by0 + 1.6 + i * 2.1
    box(f"boat_bench{i}", bx0 + 0.5, bx1 - 0.5, yy, yy + 0.45, 49.55, 49.95, M["frame"])
box("boat_bow", bx0 + 0.6, bx1 - 0.6, by1 - 0.3, by1 + 1.0, 48.7, 49.4, M["boat"])
box("boat_stern_console", bx0 + 0.9, bx1 - 0.9, by0 + 0.2, by0 + 1.0, 49.55, 50.25, M["boat"])

# ---- trees on the Graslei quay (between café terraces) ----
for (ty, r, hgt) in [(-38.5, 1.9, 6.0), (28.5, 2.2, 6.5)]:
    cyl("tree_trunk", -4.5, ty, Z, Z + hgt * 0.45, 0.22, M["trunk"])
    for k in range(7):
        a = k * 2.39996
        rr = r * (0.45 + 0.5 * rnd.random())
        sphere("tree_can", -4.5 + rr * math.cos(a) * 0.7, ty + rr * math.sin(a) * 0.7,
               Z + hgt * 0.45 + hgt * 0.3 + rnd.uniform(-0.7, 0.9), r * 0.62, M["leaf"])

# ---- cast-iron lamp posts along both quays ----
for ty in (-30, -14, 2, 18):
    cyl("lampp", -6.3, ty, Z, Z + 3.6, 0.07, M["lamp"])
    sphere("lampg", -6.3, ty, Z + 3.75, 0.19, mat("lampglass", (1.0, 0.85, 0.5), rough=0.3), sub=1)
    cyl("lampc", -6.3, ty, Z + 3.55, Z + 3.62, 0.16, M["lamp"], verts=8)
for ty in (-24, -6, 12):
    cyl("lampp2", -25.5, ty, Z, Z + 3.6, 0.07, M["lamp"])
    sphere("lampg2", -25.5, ty, Z + 3.75, 0.19, bpy.data.materials["lampglass"], sub=1)

# ---- café terrace in front of the two south cafés ----
for i in range(6):
    tx = -3.6 - (i % 2) * 2.0
    ty = -33.5 + (i // 2) * 2.4
    cyl(f"table{i}", tx, ty, Z, Z + 0.72, 0.05, M["lamp"])
    cyl(f"tabletop{i}", tx, ty, Z + 0.72, Z + 0.76, 0.42, M["frame"])
    for k in range(3):
        a = k * 2.1 + i
        cyl(f"chair{i}{k}", tx + 0.75 * math.cos(a), ty + 0.75 * math.sin(a), Z, Z + 0.45, 0.2, M["trunk"], verts=8)
# parasols
for (px, py) in [(-4.6, -32.3), (-2.7, -29.9)]:
    cyl("para_pole", px, py, Z, Z + 2.5, 0.04, M["lamp"])
    me = bpy.data.meshes.new("para")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=1.6, radius2=0.05, depth=0.7)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(px, py, Z + 2.6))
    bm.to_mesh(me)
    ob = bpy.data.objects.new("para", me)
    ob.data.materials.append(mat("parasol", (0.65, 0.12, 0.10), rough=0.8))
    bpy.context.collection.objects.link(ob)

# ---- bikes leaning on the quay rail + bollards ----
def bike(name, y, lean=0.12):
    for dy in (-0.35, 0.35):
        me = bpy.data.meshes.new(name)
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.34, radius2=0.34, depth=0.05)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=mathutils.Matrix.Rotation(math.radians(90), 3, "Y"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(-6.0 + lean, y + dy, Z + 0.34))
        bm.to_mesh(me)
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(M["lamp"])
        bpy.context.collection.objects.link(ob)
    box(f"{name}_frame", -6.05 + lean, -5.98 + lean, y - 0.3, y + 0.32, Z + 0.34, Z + 0.85, M["lamp"])
    box(f"{name}_bar", -6.06 + lean, -5.97 + lean, y - 0.42, y - 0.28, Z + 0.85, Z + 1.0, M["lamp"])

for yy in (-10.5, 8.2, 9.0):
    bike("bike", yy)

for ty in range(-40, 32, 6):  # bollards on the water edge
    cyl("bollard", -6.8, ty + 0.5, Z, Z + 0.55, 0.11, M["lamp"], verts=10)

# ---- Korenlei backdrop row (simple, across the water, behind camera-left frame edge) ----
for i, (s0, s1, h, col) in enumerate([(-44, -36, 12, (0.72, 0.66, 0.55)), (-36, -30, 14, (0.5, 0.26, 0.2)),
                                       (-30, -22, 11, (0.85, 0.82, 0.74)), (-22, -15, 13, (0.42, 0.22, 0.17))]):
    box(f"kb_{i}", -30.5, -24.5, s0, s1, Z, Z + h, mat(f"kb{i}", col, rough=0.85))

# subtle cobble bump on the graslei quay
q = bpy.data.objects["quay_graslei"]
cob = bpy.data.materials["cobble"]
nt = cob.node_tree
if "Bump" not in [n.type for n in nt.nodes]:
    nz = next(n for n in nt.nodes if n.type == "TEX_NOISE")
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])

bpy.context.scene.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/r4.png"
bpy.ops.render.render(write_still=True)
print("r4 done, objects:", len(bpy.data.objects))
