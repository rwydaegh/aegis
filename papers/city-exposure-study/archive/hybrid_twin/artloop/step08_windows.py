import bpy
import mathutils

bpy.context.scene.view_settings.view_transform = "Standard"
bpy.context.scene.view_settings.look = "None"

for ob in list(bpy.data.objects):
    if ob.name.startswith(("b_", "cut")):
        bpy.data.objects.remove(ob, do_unlink=True)


def window_unit(nmb, x0, wy0, wy1, wz0, wz1, sill=True):
    """Proud window: dark reveal panel + white frame + cross bars + stone sill."""
    box(f"{nmb}_g", x0 - 0.02, x0 + 0.02, wy0, wy1, wz0, wz1, M["glass"])
    t = 0.09
    for (fy0, fy1) in ((wy0 - t, wy0), (wy1, wy1 + t)):
        box(f"{nmb}_f", x0 - 0.06, x0 + 0.04, fy0, fy1, wz0 - t, wz1 + t, M["frame"])
    box(f"{nmb}_f", x0 - 0.06, x0 + 0.04, wy0, wy1, wz1, wz1 + t, M["frame"])
    box(f"{nmb}_f", x0 - 0.06, x0 + 0.04, wy0, wy1, wz0 - t, wz0, M["frame"])
    box(f"{nmb}_f", x0 - 0.04, x0 + 0.03, wy0, wy1, (wz0 + wz1) / 2 - 0.03, (wz0 + wz1) / 2 + 0.03, M["frame"])
    box(f"{nmb}_f", x0 - 0.04, x0 + 0.03, (wy0 + wy1) / 2 - 0.03, (wy0 + wy1) / 2 + 0.03, wz0, wz1, M["frame"])
    if sill:
        box(f"{nmb}_sill", x0 - 0.14, x0 + 0.05, wy0 - 0.10, wy1 + 0.10, wz0 - 0.13, wz0 - 0.02, M["stone"])


def building(bid, style, matwall, floor0=3.6, cafe=False,
             gable_frac=0.62, win_w=1.15, win_h=1.7, y_pad=0.5, name=None):
    x0, x1, y0, y1 = bb[bid]
    z0 = min(drec2[bid]["ground_z"], 50.3)
    h = drec2[bid]["h_final"]
    zwall = z0 + h * gable_frac
    ztop = z0 + h
    nmb = name or f"b_{bid}"
    box(nmb, x0, x1, y0 + 0.05, y1 - 0.05, z0, zwall, matwall)

    width = (y1 - y0) - 2 * y_pad
    n_cols = max(1, int(width / 2.1))
    n_fl = max(1, int((zwall - z0 - floor0) // 3.0))
    for fl in range(n_fl):
        zb = z0 + floor0 + fl * 3.0 + 0.55
        hh = win_h if fl == 0 else win_h * 0.88   # upper floors slightly shorter
        for cidx in range(n_cols):
            yc = y0 + y_pad + (cidx + 0.5) * width / n_cols
            window_unit(nmb, x0, yc - win_w / 2, yc + win_w / 2, zb, zb + hh)
    if cafe:
        gy0, gy1 = y0 + y_pad, y1 - y_pad
        box(f"{nmb}_shop", x0 - 0.03, x0 + 0.02, gy0, gy1, z0 + 0.35, z0 + floor0 - 0.6, M["glass"])
        n_mul = max(2, int((gy1 - gy0) / 1.4))
        for i in range(n_mul + 1):
            yy = gy0 + i * (gy1 - gy0) / n_mul
            box(f"{nmb}_shopf", x0 - 0.06, x0 + 0.03, yy - 0.05, yy + 0.05, z0 + 0.3, z0 + floor0 - 0.55, M["frame"])
        box(f"{nmb}_fascia", x0 - 0.10, x0 + 0.02, gy0 - 0.1, gy1 + 0.1, z0 + floor0 - 0.60, z0 + floor0 - 0.15, M["door"])
    else:
        yc = (y0 + y1) / 2
        box(f"{nmb}_door", x0 - 0.04, x0 + 0.06, yc - 0.65, yc + 0.65, z0 + 0.1, z0 + 2.5, M["door"])
        box(f"{nmb}_df", x0 - 0.07, x0 + 0.02, yc - 0.75, yc - 0.65, z0, z0 + 2.6, M["stone"])
        box(f"{nmb}_df", x0 - 0.07, x0 + 0.02, yc + 0.65, yc + 0.75, z0, z0 + 2.6, M["stone"])
        box(f"{nmb}_df", x0 - 0.07, x0 + 0.02, yc - 0.75, yc + 0.75, z0 + 2.5, z0 + 2.65, M["stone"])
        for side in (-1, 1):
            yc2 = yc + side * max(1.8, width / 3)
            if y0 + 0.4 < yc2 - 0.6 and yc2 + 0.6 < y1 - 0.4:
                window_unit(nmb, x0, yc2 - 0.6, yc2 + 0.6, z0 + 0.8, z0 + 2.4)

    box(f"{nmb}_cornice", x0 - 0.20, x0 + 0.1, y0 + 0.02, y1 - 0.02, zwall - 0.25, zwall, M["stone"])

    gw0, gw1 = y0 + 0.05, y1 - 0.05
    gh = ztop - zwall
    prof = {"step": [(5 - i) / 5 for i in range(5)],
            "bell": [1.0, 0.80, 0.60, 0.40, 0.25, 0.13],
            "spout": [0.5, 0.5, 0.5],
            "tri": [(9 - i) / 9 for i in range(9)]}[style]
    for i, f in enumerate(prof):
        yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
        yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
        box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1,
            zwall + gh * i / len(prof), zwall + gh * (i + 1) / len(prof), matwall)
    if style == "bell":
        box(f"{nmb}_finial", x0 + 0.05, x0 + 0.4, (gw0 + gw1) / 2 - 0.14, (gw0 + gw1) / 2 + 0.14, ztop, ztop + 0.6, M["stone"])

    yc = (y0 + y1) / 2
    window_unit(nmb, x0, yc - 0.4, yc + 0.4, zwall + 0.5, zwall + 1.35, sill=False)

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


for key, s0, s1, h, style, mw, opts in LAYOUT:
    building(key, style, mw, **{k: v for k, v in opts.items() if k != "n_cols"})

camo = bpy.data.objects["cam"]
camo.location = (-34.0, -16.0, 50.3 + 4.5)
target = mathutils.Vector((0.0, -3.0, 50.3 + 5.5))
d = target - mathutils.Vector(camo.location)
camo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

bpy.context.scene.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/r3.png"
bpy.ops.render.render(write_still=True)
print("r3 done, objects:", len(bpy.data.objects))
