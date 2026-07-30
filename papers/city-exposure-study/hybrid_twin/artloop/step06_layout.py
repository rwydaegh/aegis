import bpy
import math

Z_QUAY = 50.3
Z_WATER = 48.5

# ---------- env in quay-local frame: t across (water at t<0), s along ----------
box("quay_graslei", -7, 0.0, -45, 35, Z_QUAY - 3, Z_QUAY, M["cobble"])
box("ground_e", 0, 40, -45, 35, Z_QUAY - 3, Z_QUAY - 0.02, M["cobble"])
box("quaywall_e", -8, -7, -45, 35, Z_WATER - 2, Z_QUAY + 0.07, M["quay"])
box("water", -23, -8, -45, 35, Z_WATER - 2, Z_WATER, M["water"])
box("quaywall_w", -24, -23, -45, 35, Z_WATER - 2, Z_QUAY + 0.07, M["quay"])
box("quay_korenlei", -45, -24, -45, 35, Z_QUAY - 3, Z_QUAY, M["cobble"])

# ---------- row layout: (key, s0, s1, h, style, mat, opts) ----------
LAYOUT = [
    ("hA", -35.0, -27.5, 13.6, "bell", mat("plaster_w", (0.90, 0.87, 0.78)), dict(n_cols=2, cafe=True)),
    ("hB", -27.5, -20.5, 12.5, "step", brick_mat(4), dict(n_cols=2, cafe=True)),
    ("hC", -20.5, -12.2, 14.0, "bell", mat("plaster_c", (0.86, 0.82, 0.70), rough=0.7), dict(n_cols=2)),
    ("tol", -12.2, -7.4, 7.5, "bell", brick_mat(1), dict(n_cols=1, floor0=2.9, win_w=0.9, win_h=1.2)),
    ("korn", -7.4, 3.6, 17.7, "step", brick_mat(2), dict(n_cols=3)),
    ("spijker", 3.6, 15.6, 18.0, "tri", M["stone"], dict(n_cols=4, floor0=4.2, win_w=0.85, win_h=1.3, gable_frac=0.55)),
    ("annex", 15.6, 19.2, 8.5, "spout", mat("plaster_g", (0.80, 0.78, 0.70), rough=0.7), dict(n_cols=1, floor0=2.8, win_w=0.8, win_h=1.1)),
    ("hN", 19.2, 25.9, 12.0, "step", brick_mat(3, base=(0.38, 0.19, 0.14)), dict(n_cols=2, cafe=True)),
]
for key, s0, s1, h, style, mw, opts in LAYOUT:
    bb[key] = (0.0, 11.0, s0, s1)
    drec2[key] = {"h_final": h, "ground_z": Z_QUAY}
    building(key, style, mw, **opts)

# ---------- camera + sun ----------
cam = bpy.data.cameras.new("cam")
cam.lens = 26
camo = bpy.data.objects.new("cam", cam)
bpy.context.collection.objects.link(camo)
camo.location = (-31.0, -18.0, Z_QUAY + 1.7)
import mathutils
target = mathutils.Vector((0.0, -2.0, Z_QUAY + 6.5))
d = target - mathutils.Vector(camo.location)
camo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = camo

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.5
sun.data.angle = 0.05
sun.rotation_euler = (math.radians(55), 0, math.radians(215))  # from SW behind camera
bpy.context.collection.objects.link(sun)

bpy.context.scene.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/r1.png"
bpy.ops.render.render(write_still=True)
print("rendered r1, objects:", len(bpy.data.objects))
