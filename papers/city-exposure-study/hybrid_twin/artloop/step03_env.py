import bpy

# ---------- render + world ----------
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 720

w = bpy.data.worlds.new("W") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
sc.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sun_elevation = 0.32
sky.sun_rotation = 3.9   # low warm sun from SW so the east-bank row catches light
sky.sun_intensity = 0.7
bg = nt.nodes.new("ShaderNodeBackground")
out = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(sky.outputs[0], bg.inputs[0])
nt.links.new(bg.outputs[0], out.inputs[0])


def mat(name, color, rough=0.85, spec=0.3, metal=0.0, alpha=1.0, transmit=0.0, noise=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmit:
        b.inputs["Transmission Weight"].default_value = transmit
        m.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.45
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    if noise:
        # cheap procedural mottling: noise -> color mix
        n = m.node_tree.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = noise[0]
        mixn = m.node_tree.nodes.new("ShaderNodeMix")
        mixn.data_type = "RGBA"
        mixn.inputs["Factor"].default_value = 0.0
        mixn.inputs[6].default_value = (*color, 1)
        mixn.inputs[7].default_value = (*noise[1], 1)
        m.node_tree.links.new(n.outputs["Fac"], mixn.inputs["Factor"])
        m.node_tree.links.new(mixn.outputs[2], b.inputs["Base Color"])
    return m


# palette
M = {
    "water":  mat("water", (0.05, 0.10, 0.09), rough=0.05),
    "cobble": mat("cobble", (0.36, 0.33, 0.30), rough=0.95, noise=(28.0, (0.28, 0.26, 0.25))),
    "quay":   mat("quaystone", (0.52, 0.50, 0.46), rough=0.9, noise=(9.0, (0.44, 0.42, 0.39))),
    "glass":  mat("glass", (0.35, 0.45, 0.45), rough=0.08, transmit=0.9),
    "frame":  mat("frame_white", (0.88, 0.87, 0.82), rough=0.5),
    "door":   mat("door_green", (0.10, 0.22, 0.15), rough=0.5),
    "tile":   mat("rooftile", (0.42, 0.18, 0.12), rough=0.85, noise=(40.0, (0.35, 0.14, 0.10))),
    "lamp":   mat("lamp_iron", (0.05, 0.08, 0.06), rough=0.4, metal=0.6),
    "leaf":   mat("leaf", (0.16, 0.30, 0.10), rough=0.9, noise=(6.0, (0.10, 0.22, 0.07))),
    "trunk":  mat("trunk", (0.25, 0.18, 0.12), rough=0.9),
    "boat":   mat("boat_hull", (0.12, 0.14, 0.18), rough=0.5),
    "canvas": mat("canvas", (0.75, 0.72, 0.62), rough=0.9),
    "stone":  mat("graslei_limestone", (0.55, 0.52, 0.45), rough=0.9, noise=(14.0, (0.47, 0.44, 0.37))),
}


def brick_mat(i, base=(0.45, 0.22, 0.16)):
    import random
    rnd = random.Random(i)
    c = tuple(min(1, max(0, ch + rnd.uniform(-0.07, 0.07))) for ch in base)
    dark = tuple(ch * 0.75 for ch in c)
    return mat(f"brick_{i}", c, rough=0.9, noise=(35.0, dark))


NS_M = M  # stash in namespace

# ---------- ground, water, quays ----------
Z_QUAY = 50.4      # quay deck level (from audited ground_z ~49-51)
Z_WATER = 48.6

def box(name, x0, x1, y0, y1, z0, z1, material):
    me = bpy.data.meshes.new(name)
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me.from_pydata(v, [], f)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    bpy.context.collection.objects.link(ob)
    return ob

# canal runs N-S between x=-78 (Korenlei) and x=-64 (Graslei wall)
box("water", -80, -62, 20, 130, Z_WATER - 2, Z_WATER, M["water"])
box("quay_graslei", -64, -40, 20, 130, Z_QUAY - 3.0, Z_QUAY, M["cobble"])
box("quay_korenlei", -100, -78, 20, 130, Z_QUAY - 3.0, Z_QUAY, M["cobble"])
box("quaywall_e", -65.0, -64.0, 20, 130, Z_WATER - 2, Z_QUAY + 0.05, M["quay"])
box("quaywall_w", -78.0, -77.0, 20, 130, Z_WATER - 2, Z_QUAY + 0.05, M["quay"])
# backdrop ground behind the row
box("ground_e", -40, 20, 20, 130, Z_QUAY - 0.4, Z_QUAY + 0.2, M["cobble"])

print("env ok, objects:", len(bpy.data.objects))
