import bpy
import mathutils

# floating chimneys on gable-front end buildings
for nm in list(bpy.data.objects.keys()):
    if nm.startswith(("b_spijker_chim", "b_annex_chim", "b_hN_chim", "b_tol_chim")):
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)

# spijker: replace stepped 'tri' gable with a smooth triangle prism
for nm in [n for n in bpy.data.objects.keys() if n.startswith("b_spijker_gab")]:
    bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
import bmesh
x0, x1, y0, y1 = bb["spijker"]
z0 = 50.3
h = drec2["spijker"]["h_final"]
zwall = z0 + h * 0.55
ztop = z0 + h
me = bpy.data.meshes.new("b_spijker_tri")
bm = bmesh.new()
gw0, gw1 = y0 + 0.05, y1 - 0.05
v = [bm.verts.new(p) for p in [
    (x0, gw0, zwall), (x0 + 0.45, gw0, zwall), (x0 + 0.45, gw1, zwall), (x0, gw1, zwall),
    (x0, (gw0 + gw1) / 2, ztop), (x0 + 0.45, (gw0 + gw1) / 2, ztop)]]
bm.faces.new([v[0], v[1], v[5], v[4]])
bm.faces.new([v[3], v[4], v[5], v[2]])
bm.faces.new([v[0], v[4], v[3]])
bm.faces.new([v[1], v[2], v[5]])
bm.to_mesh(me)
ob = bpy.data.objects.new("b_spijker_tri", me)
stone2 = mat("spijker_stone", (0.46, 0.42, 0.33), rough=0.95, noise=(16.0, (0.38, 0.34, 0.26)))
ob.data.materials.append(stone2)
bpy.context.collection.objects.link(ob)
# swap spijker body material to the warmer stone
bpy.data.objects["b_spijker"].data.materials[0] = stone2

# boat: wood deck, darker benches
wood = mat("deck_wood", (0.35, 0.24, 0.14), rough=0.8, noise=(20.0, (0.28, 0.18, 0.10)))
bpy.data.objects["boat_deck"].data.materials[0] = wood
for nm in [n for n in bpy.data.objects.keys() if n.startswith("boat_bench")]:
    bpy.data.objects[nm].data.materials[0] = mat("bench_blue", (0.10, 0.16, 0.28), rough=0.6)

# deepen brick saturation
for i in (1, 2, 3, 4):
    m = bpy.data.materials.get(f"brick_{i}")
    if not m:
        continue
    for n in m.node_tree.nodes:
        if n.type == "MIX":
            c = list(n.inputs[6].default_value)
            n.inputs[6].default_value = (min(1, c[0] * 1.15), c[1] * 0.85, c[2] * 0.8, 1)
            d = list(n.inputs[7].default_value)
            n.inputs[7].default_value = (d[0] * 0.9, d[1] * 0.75, d[2] * 0.7, 1)

# ---- money shot ----
sc = bpy.context.scene
sc.cycles.samples = 192
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/final_quay.png"
bpy.ops.render.render(write_still=True)
print("final_quay done")

# ---- closeup: café terrace, human eye height ----
camo = bpy.data.objects["cam"]
camo.data.lens = 30
camo.location = (-9.0, -25.5, 50.3 + 1.65)
target = mathutils.Vector((-1.5, -31.5, 50.3 + 4.0))
d = target - mathutils.Vector(camo.location)
camo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = "/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/final_terrace.png"
bpy.ops.render.render(write_still=True)
print("final_terrace done")

bpy.ops.wm.save_as_mainfile(filepath="/home/user/aegis/papers/city-exposure-study/hybrid_twin/artloop/graslei_art.blend")
print("saved graslei_art.blend, objects:", len(bpy.data.objects))
