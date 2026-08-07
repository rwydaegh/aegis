import bpy
import math
import mathutils

# ---- lighting/exposure ----
sun = bpy.data.objects["sun"]
sun.data.energy = 2.2
w = bpy.context.scene.world
for n in w.node_tree.nodes:
    if n.type == "TEX_SKY":
        n.sun_intensity = 0.35
        n.sun_elevation = 0.38
bpy.context.scene.view_settings.look = "AgX - Punchy"

# ---- darker reflective glazing ----
g = bpy.data.materials["glass"]
b = g.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.03, 0.05, 0.06, 1)
b.inputs["Roughness"].default_value = 0.04
b.inputs["Transmission Weight"].default_value = 0.0
b.inputs["Metallic"].default_value = 0.4

wat = bpy.data.materials["water"].node_tree.nodes["Principled BSDF"]
wat.inputs["Base Color"].default_value = (0.02, 0.06, 0.05, 1)
wat.inputs["Roughness"].default_value = 0.02

# ---- rebuild buildings with denser, shallower, visible windows ----
for ob in list(bpy.data.objects):
    if ob.name.startswith(("b_", "cut")):
        bpy.data.objects.remove(ob, do_unlink=True)

def building(bid, style, matwall, n_cols=None, floor0=3.6, cafe=False, arch=False,
             gable_frac=0.62, win_w=1.15, win_h=1.7, y_pad=0.5, name=None):
    x0, x1, y0, y1 = bb[bid]
    gz = drec2[bid]["ground_z"]
    h = drec2[bid]["h_final"]
    z0 = min(gz, 50.3)
    zwall = z0 + h * gable_frac
    ztop = z0 + h
    nmb = name or f"b_{bid}"
    body = box(nmb, x0, x1, y0 + 0.05, y1 - 0.05, z0, zwall, matwall)

    width = (y1 - y0) - 2 * y_pad
    if n_cols is None:
        n_cols = max(1, int(width / 2.1))
    n_fl = max(1, int((zwall - z0 - floor0) // 3.0))
    cutters, wins = [], []
    for fl in range(n_fl):
        zb = z0 + floor0 + fl * 3.0 + 0.55
        for cidx in range(n_cols):
            yc = y0 + y_pad + (cidx + 0.5) * width / n_cols
            wy0, wy1 = yc - win_w / 2, yc + win_w / 2
            wz0, wz1 = zb, zb + win_h
            cutters.append(box("cut", x0 - 0.2, x0 + 0.25, wy0, wy1, wz0, wz1, matwall))
            wins.append((wy0, wy1, wz0, wz1))
    if cafe:
        gy0, gy1 = y0 + y_pad, y1 - y_pad
        cutters.append(box("cut", x0 - 0.2, x0 + 0.25, gy0, gy1, z0 + 0.35, z0 + floor0 - 0.6, matwall))
        wins.append((gy0, gy1, z0 + 0.35, z0 + floor0 - 0.6))
    else:
        yc = (y0 + y1) / 2
        cutters.append(box("cut", x0 - 0.2, x0 + 0.25, yc - 0.7, yc + 0.7, z0 + 0.1, z0 + 2.6, matwall))
        box(f"{nmb}_door", x0 + 0.10, x0 + 0.18, yc - 0.65, yc + 0.65, z0 + 0.1, z0 + 2.55, M["door"])
        for side in (-1, 1):
            yc2 = yc + side * max(1.8, width / 3)
            if y0 + 0.4 < yc2 - 0.6 and yc2 + 0.6 < y1 - 0.4:
                cutters.append(box("cut", x0 - 0.2, x0 + 0.25, yc2 - 0.6, yc2 + 0.6, z0 + 0.8, z0 + 2.5, matwall))
                wins.append((yc2 - 0.6, yc2 + 0.6, z0 + 0.8, z0 + 2.5))
    bool_cut(body, cutters)

    for (wy0, wy1, wz0, wz1) in wins:
        box(f"{nmb}_g", x0 + 0.16, x0 + 0.20, wy0 + 0.04, wy1 - 0.04, wz0 + 0.04, wz1 - 0.04, M["glass"])
        for (fy0, fy1) in ((wy0, wy0 + 0.09), (wy1 - 0.09, wy1)):
            box(f"{nmb}_f", x0 + 0.06, x0 + 0.18, fy0, fy1, wz0, wz1, M["frame"])
        box(f"{nmb}_f", x0 + 0.06, x0 + 0.18, wy0, wy1, wz1 - 0.09, wz1, M["frame"])
        box(f"{nmb}_f", x0 + 0.06, x0 + 0.18, wy0, wy1, wz0, wz0 + 0.06, M["frame"])
        box(f"{nmb}_f", x0 + 0.10, x0 + 0.16, wy0, wy1, (wz0 + wz1) / 2 - 0.035, (wz0 + wz1) / 2 + 0.035, M["frame"])
        box(f"{nmb}_f", x0 + 0.10, x0 + 0.16, (wy0 + wy1) / 2 - 0.035, (wy0 + wy1) / 2 + 0.035, wz0, wz1, M["frame"])
        box(f"{nmb}_sill", x0 - 0.12, x0 + 0.20, wy0 - 0.07, wy1 + 0.07, wz0 - 0.11, wz0, M["stone"])

    box(f"{nmb}_cornice", x0 - 0.20, x0 + 0.1, y0 + 0.02, y1 - 0.02, zwall - 0.25, zwall, M["stone"])

    gw0, gw1 = y0 + 0.05, y1 - 0.05
    gh = ztop - zwall
    if style == "step":
        n_steps = 5
        for i in range(n_steps):
            f = (n_steps - i) / n_steps
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1, zwall + gh * i / n_steps, zwall + gh * (i + 1) / n_steps, matwall)
    elif style == "bell":
        prof = [1.0, 0.80, 0.60, 0.40, 0.25, 0.13]
        for i, f in enumerate(prof):
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1, zwall + gh * i / len(prof), zwall + gh * (i + 1) / len(prof), matwall)
        box(f"{nmb}_finial", x0 + 0.05, x0 + 0.4, (gw0 + gw1) / 2 - 0.14, (gw0 + gw1) / 2 + 0.14, ztop, ztop + 0.6, M["stone"])
    elif style == "spout":
        box(f"{nmb}_gab0", x0, x0 + 0.45, gw0 + (gw1 - gw0) * 0.25, gw1 - (gw1 - gw0) * 0.25, zwall, ztop, matwall)
    else:
        n_tri = 9
        for i in range(n_tri):
            f = (n_tri - i) / n_tri
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1, zwall + gh * i / n_tri, zwall + gh * (i + 1) / n_tri, matwall)

    yc = (y0 + y1) / 2
    box(f"{nmb}_gw", x0 - 0.05, x0 + 0.12, yc - 0.4, yc + 0.4, zwall + 0.5, zwall + 1.4, M["frame"])
    box(f"{nmb}_gwg", x0 + 0.02, x0 + 0.09, yc - 0.34, yc + 0.34, zwall + 0.56, zwall + 1.34, M["glass"])

    import bmesh
    me = bpy.data.meshes.new(f"{nmb}_roof")
    bm = bmesh.new()
    rx0, rx1 = x0 + 0.45, x1
    ridge_z = ztop - 0.3
    v = [bm.verts.new(p) for p in [
        (rx0, gw0, zwall), (rx1, gw0, zwall), (rx1, gw1, zwall), (rx0, gw1, zwall),
        (rx0, (gw0 + gw1) / 2, ridge_z), (rx1, (gw0 + gw1) / 2, ridge_z)]]
    bm.faces.new([v[0], v[1], v[5], v[4]])
    bm.faces.new([v[4], v[5], v[2], v[3]])
    bm.faces.new([v[1], v[2], v[5]])
    bm.faces.new([v[0], v[4], v[3]])
    bm.to_mesh(me)
    ob = bpy.data.objects.new(f"{nmb}_roof", me)
    ob.data.materials.append(M["tile"])
    bpy.context.collection.objects.link(ob)
    box(f"{nmb}_chim", (x0 + x1) / 2, (x0 + x1) / 2 + 0.7, gw1 - 1.6, gw1 - 0.9, ridge_z - 0.5, ridge_z + 1.2, matwall)

    if cafe:
        aw = bpy.data.meshes.new(f"{nmb}_aw")
        a0, a1 = y0 + 0.4, y1 - 0.4
        za, xa = z0 + floor0 - 0.45, x0 - 0.05
        v2 = [(xa, a0, za), (xa, a1, za), (xa - 2.0, a1, za - 0.8), (xa - 2.0, a0, za - 0.8)]
        aw.from_pydata(v2, [], [(0, 1, 2, 3)])
        ob2 = bpy.data.objects.new(f"{nmb}_aw", aw)
        ob2.data.materials.append(M["canvas"])
        bpy.context.collection.objects.link(ob2)
    return body


NS_building = building  # override in namespace
for key, s0, s1, h, style, mw, opts in LAYOUT:
    building(key, style, mw, **{k: v for k, v in opts.items() if k != "n_cols"})

# ---- camera: raised, sees water ----
camo = bpy.data.objects["cam"]
camo.location = (-33.0, -20.0, 50.3 + 5.5)
camo.data.lens = 24
target = mathutils.Vector((0.0, -1.0, 50.3 + 5.0))
d = target - mathutils.Vector(camo.location)
camo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

bpy.context.scene.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/r2.png"
bpy.ops.render.render(write_still=True)
print("r2 done, objects:", len(bpy.data.objects))
