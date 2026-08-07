import bpy

# ---------- real bboxes for the front row ----------
ROW_IDS = ["494007824", "514020945", "514020946", "493993762", "494008001", "493993763"]
bb = {}
for bid in ROW_IDS:
    pts = ring_enu(by_id[bid]["ring"])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bb[bid] = (min(xs), max(xs), min(ys), max(ys))
    print(bid, named.get(bid), [round(v, 1) for v in bb[bid]],
          "h", drec2[bid]["h_final"], "gz", drec2[bid]["ground_z"])

FRONT = min(b[0] for b in bb.values())
print("row front line x =", round(FRONT, 1))

# ---------- rebuild env around the real front line ----------
for nm in ("water", "quay_graslei", "quay_korenlei", "quaywall_e", "quaywall_w", "ground_e"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)

Z_QUAY = 50.3
Z_WATER = 48.5
QW = FRONT - 7.0          # graslei quay wall (7 m walkway in front of the row)
box("quay_graslei", QW, FRONT + 30, 20, 130, Z_QUAY - 3, Z_QUAY, M["cobble"])
box("quaywall_e", QW - 1, QW, 20, 130, Z_WATER - 2, Z_QUAY + 0.06, M["quay"])
box("water", QW - 16, QW - 1, 20, 130, Z_WATER - 2, Z_WATER, M["water"])
box("quaywall_w", QW - 17, QW - 16, 20, 130, Z_WATER - 2, Z_QUAY + 0.06, M["quay"])
box("quay_korenlei", QW - 40, QW - 17, 20, 130, Z_QUAY - 3, Z_QUAY, M["cobble"])


def bool_cut(target, cutters):
    if not cutters:
        return
    for c in cutters:
        mod = target.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = c
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(c, do_unlink=True)


def building(bid, style, matwall, n_cols, floor0=3.6, cafe=False, arch=False,
             gable_frac=0.62, win_w=1.1, win_h=1.6, y_pad=0.55, name=None):
    """One rich gabled house on its real footprint bbox."""
    x0, x1, y0, y1 = bb[bid]
    gz = drec2[bid]["ground_z"]
    h = drec2[bid]["h_final"]
    z0 = min(gz, Z_QUAY)
    zwall = z0 + h * gable_frac
    ztop = z0 + h
    nmb = name or f"b_{bid}"

    body = box(nmb, x0, x1, y0 + 0.05, y1 - 0.05, z0, zwall, matwall)

    # window grid on front (west) face
    width = (y1 - y0) - 2 * y_pad
    n_fl = max(1, int((zwall - z0 - floor0) // 3.1))
    cutters = []
    wins = []
    for fl in range(n_fl):
        zb = z0 + floor0 + fl * 3.1 + 0.7
        for c in range(n_cols):
            yc = y0 + y_pad + (c + 0.5) * width / n_cols
            wy0, wy1 = yc - win_w / 2, yc + win_w / 2
            wz0, wz1 = zb, zb + win_h
            cutters.append(box(f"cut", x0 - 0.2, x0 + 0.35, wy0, wy1, wz0, wz1, matwall))
            wins.append((wy0, wy1, wz0, wz1))
    # ground floor: cafe glazing or door+windows
    if cafe:
        gy0, gy1 = y0 + y_pad, y1 - y_pad
        cutters.append(box("cut", x0 - 0.2, x0 + 0.35, gy0, gy1, z0 + 0.4, z0 + floor0 - 0.7, matwall))
        wins.append((gy0, gy1, z0 + 0.4, z0 + floor0 - 0.7))
    else:
        yc = (y0 + y1) / 2
        cutters.append(box("cut", x0 - 0.2, x0 + 0.35, yc - 0.7, yc + 0.7, z0 + 0.1, z0 + 2.6, matwall))
        for side in (-1, 1):
            yc2 = yc + side * max(1.8, width / 3)
            if y0 + 0.4 < yc2 - 0.6 and yc2 + 0.6 < y1 - 0.4:
                cutters.append(box("cut", x0 - 0.2, x0 + 0.35, yc2 - 0.6, yc2 + 0.6,
                                   z0 + 0.8, z0 + 2.5, matwall))
                wins.append((yc2 - 0.6, yc2 + 0.6, z0 + 0.8, z0 + 2.5))
        # door leaf
        box(f"{nmb}_door", x0 + 0.22, x0 + 0.30, yc - 0.65, yc + 0.65, z0 + 0.1, z0 + 2.55, M["door"])
    bool_cut(body, cutters)

    # glass, frames, sills
    for (wy0, wy1, wz0, wz1) in wins:
        box(f"{nmb}_g", x0 + 0.26, x0 + 0.30, wy0 + 0.05, wy1 - 0.05, wz0 + 0.05, wz1 - 0.05, M["glass"])
        box(f"{nmb}_fL", x0 + 0.24, x0 + 0.34, wy0, wy0 + 0.08, wz0, wz1, M["frame"])
        box(f"{nmb}_fR", x0 + 0.24, x0 + 0.34, wy1 - 0.08, wy1, wz0, wz1, M["frame"])
        box(f"{nmb}_fT", x0 + 0.24, x0 + 0.34, wy0, wy1, wz1 - 0.08, wz1, M["frame"])
        box(f"{nmb}_fM", x0 + 0.27, x0 + 0.31, wy0, wy1, (wz0 + wz1) / 2 - 0.03, (wz0 + wz1) / 2 + 0.03, M["frame"])
        box(f"{nmb}_sill", x0 - 0.10, x0 + 0.30, wy0 - 0.06, wy1 + 0.06, wz0 - 0.10, wz0, M["stone"])

    # cornice
    box(f"{nmb}_cornice", x0 - 0.18, x0 + 0.1, y0 + 0.02, y1 - 0.02, zwall - 0.22, zwall, M["stone"])

    # gable parapet on the front + pitched roof behind
    gw0, gw1 = y0 + 0.05, y1 - 0.05
    gh = ztop - zwall
    if style == "step":
        n_steps = 5
        for i in range(n_steps):
            f = (n_steps - i) / n_steps
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1,
                zwall + gh * i / n_steps, zwall + gh * (i + 1) / n_steps, matwall)
    elif style == "bell":
        prof = [1.0, 0.82, 0.62, 0.42, 0.26, 0.14]
        for i, f in enumerate(prof):
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1,
                zwall + gh * i / len(prof), zwall + gh * (i + 1) / len(prof), matwall)
        box(f"{nmb}_finial", x0 + 0.05, x0 + 0.4, (gw0 + gw1) / 2 - 0.15, (gw0 + gw1) / 2 + 0.15,
            ztop, ztop + 0.6, M["stone"])
    elif style == "spout":
        box(f"{nmb}_gab0", x0, x0 + 0.45, gw0 + (gw1 - gw0) * 0.25, gw1 - (gw1 - gw0) * 0.25,
            zwall, ztop, matwall)
    else:  # triangle
        n_tri = 7
        for i in range(n_tri):
            f = (n_tri - i) / n_tri
            yy0 = (gw0 + gw1) / 2 - (gw1 - gw0) / 2 * f
            yy1 = (gw0 + gw1) / 2 + (gw1 - gw0) / 2 * f
            box(f"{nmb}_gab{i}", x0, x0 + 0.45, yy0, yy1,
                zwall + gh * i / n_tri, zwall + gh * (i + 1) / n_tri, matwall)

    # gable windows (attic)
    yc = (y0 + y1) / 2
    box(f"{nmb}_gw", x0 - 0.05, x0 + 0.1, yc - 0.4, yc + 0.4, zwall + 0.5, zwall + 1.4, M["frame"])
    box(f"{nmb}_gwg", x0 + 0.02, x0 + 0.08, yc - 0.34, yc + 0.34, zwall + 0.56, zwall + 1.34, M["glass"])

    # pitched roof: ridge along x behind the gable
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

    # chimney
    box(f"{nmb}_chim", (x0 + x1) / 2, (x0 + x1) / 2 + 0.7, gw1 - 1.6, gw1 - 0.9,
        ridge_z - 0.5, ridge_z + 1.2, matwall)

    # awning for cafes
    if cafe:
        import math
        aw = bpy.data.meshes.new(f"{nmb}_aw")
        a0, a1 = y0 + 0.4, y1 - 0.4
        za, xa = z0 + floor0 - 0.5, x0 - 0.1
        v2 = [(xa, a0, za), (xa, a1, za), (xa - 2.2, a1, za - 0.9), (xa - 2.2, a0, za - 0.9)]
        aw.from_pydata(v2, [], [(0, 1, 2, 3)])
        ob2 = bpy.data.objects.new(f"{nmb}_aw", aw)
        ob2.data.materials.append(M["canvas"])
        bpy.context.collection.objects.link(ob2)
    return body


# ---------- the six real buildings, styled from knowledge + data ----------
building("494007824", "bell", mat("plaster_w", (0.90, 0.87, 0.78), rough=0.7, noise=(10.0, (0.82, 0.78, 0.68))), n_cols=3, cafe=True)      # 1725 plastered cafe house
building("514020945", "bell", brick_mat(1), n_cols=1, floor0=2.9, win_w=0.9, win_h=1.3)                                                     # Tolhuisje
building("514020946", "step", brick_mat(2), n_cols=4)                                                                                       # Korenmetershuis
building("493993762", "tri", M["stone"], n_cols=5, floor0=4.2, win_w=0.85, win_h=1.35, gable_frac=0.55, arch=True)                          # Het Spijker
building("494008001", "spout", mat("plaster_g", (0.80, 0.78, 0.70), rough=0.7), n_cols=1, floor0=2.8, win_w=0.8, win_h=1.2)                 # annex
building("493993763", "step", brick_mat(3, base=(0.38, 0.19, 0.14)), n_cols=2, cafe=True)                                                   # north cafe house

print("row built, objects:", len(bpy.data.objects))
