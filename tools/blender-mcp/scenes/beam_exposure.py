"""Parametric FR2 beamforming exposure scene, built inside Blender.

Everything geometric here comes out of the array maths rather than being placed
by eye: the radiation lobe is the array factor evaluated on a spherical grid,
and the colour on the phantom is the AEGIS surface equation

    Sab(r) = Sinc(r) * T0 * ReLU(n_hat . (-k_hat))

evaluated per vertex. That makes the scene checkable - verify() re-derives the
lobe peak direction from the mesh and compares it against the steering vector,
so a wrong sign or a transposed axis shows up as a number instead of as a
picture that looks vaguely plausible.

Run it through the socket:  exec(open(<this file>).read())
"""

import json
import math
import os

import bpy
import numpy as np
from mathutils import Vector

C0 = 299792458.0

CONFIG = {
    # Array: a 16x16 FR2 panel at half-wavelength spacing. At 26 GHz that is a
    # 9.2 cm panel, which is genuinely how small FR2 radio heads are.
    "freq_hz": 26.0e9,
    "n_x": 16,
    "n_z": 16,
    "spacing_lambda": 0.5,
    # Conducted power. With 256 elements this lands near 54 dBm EIRP, typical
    # for an FR2 small cell.
    "p_tx_w": 1.0,
    # Mast carrying the panel, and the panel's mechanical boresight (+Y).
    "mast_pos": (0.0, -4.5, 0.0),
    "mast_height": 4.5,
    # Pedestrian: torso point the beam is steered onto.
    "phantom_pos": (0.8, 0.0, 0.0),
    "target_z": 1.30,
    "phantom_stl": "duke.stl",
    # Power transmission coefficient into skin at 26 GHz.
    "T0": 0.40,
    # Lobe drawing: radius maps 0 dB -> lobe_len, -dyn_range dB -> 0.
    "lobe_len": 4.5,
    "lobe_dyn_range_db": 25.0,
    "lobe_n_theta": 180,
    "lobe_n_phi": 360,
    # ICNIRP 2020 local absorbed power density limit, general public, >6 GHz.
    "apd_limit_w_m2": 20.0,
    # Look. The beam and the skin map are emissive, so the ambient level has to
    # stay low or they wash out against the sky.
    "sky_strength": 0.34,
    "sun_energy": 2.0,
    "sun_elevation_deg": 7.0,
    "lobe_emission": 2.0,
    "lobe_alpha": 0.18,
    "skin_emission": 0.50,
    # Gamma on the normalised APD before colour mapping. Nearer 1.0 keeps the
    # hot spot tight; small values smear it over the whole body.
    "skin_gamma": 0.80,
    "ground_roughness": 0.42,
    "window_emission": 3.0,
    # Thin atmosphere so the beam reads as a volume, not a glowing shell.
    "fog_density": 0.007,
    "cam_pos": (6.0, -7.2, 1.88),
    "cam_look": (0.70, -0.60, 1.40),
    "cam_lens": 42.0,
}


# --------------------------------------------------------------------------
# scene helpers
# --------------------------------------------------------------------------


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.lights):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def new_mesh_object(name, verts, faces, collection=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def principled(name, base_color, roughness=0.5, metallic=0.0, emission=None, emission_strength=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    return mat


# --------------------------------------------------------------------------
# array maths
# --------------------------------------------------------------------------


def array_geometry():
    """Panel centre, boresight, steering unit vector and element spacing."""
    cfg = CONFIG
    lam = C0 / cfg["freq_hz"]
    d = cfg["spacing_lambda"] * lam

    centre = np.array([cfg["mast_pos"][0], cfg["mast_pos"][1], cfg["mast_height"]], dtype=float)
    boresight = np.array([0.0, 1.0, 0.0])

    target = np.array([cfg["phantom_pos"][0], cfg["phantom_pos"][1], cfg["target_z"]], dtype=float)
    steer = target - centre
    steer /= np.linalg.norm(steer)

    return centre, boresight, steer, d, lam


def power_pattern(u, steer, d, lam):
    """Normalised power pattern of the steered panel, for unit vectors u.

    Separable rectangular array, so the array factor is a product of two
    Dirichlet kernels. u has shape (..., 3); the return has shape (...).
    """
    cfg = CONFIG
    k = 2.0 * math.pi / lam

    # Element pattern: a broadside patch, zero into the back half-space.
    element = np.clip(u[..., 1], 0.0, None)

    af = np.ones(u.shape[:-1], dtype=float)
    for axis, count in ((0, cfg["n_x"]), (2, cfg["n_z"])):
        psi = k * d * (u[..., axis] - steer[axis])
        denom = np.sin(psi / 2.0)
        num = np.sin(count * psi / 2.0)
        # Grating lobes aside, psi -> 0 is the broadside limit where the ratio
        # tends to the element count.
        kernel = np.where(np.abs(denom) < 1e-12, float(count), num / denom)
        af *= np.abs(kernel)

    # Power pattern, normalised so the steered peak is 1.
    pattern = (af * element) ** 2
    peak = pattern.max()
    return pattern / peak if peak > 0 else pattern


def peak_gain_linear():
    """Peak gain of the panel, elements times element directivity."""
    # A broadside patch with a cos-shaped pattern has about 2x isotropic.
    return CONFIG["n_x"] * CONFIG["n_z"] * 2.0


# --------------------------------------------------------------------------
# build steps
# --------------------------------------------------------------------------


def facade_material(name):
    """Dark concrete with lit windows.

    The Brick texture already randomises between Color1 and Color2 per brick,
    so that alone gives a believable lit/unlit window pattern. An extra noise
    gate was the wrong tool: driven from the same scaled mapping it ran at
    tens of cycles per window and speckled the whole facade.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.040, 0.041, 0.047, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.62

    coord = tree.nodes.new("ShaderNodeTexCoord")

    brick = tree.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.5
    brick.squash = 1.0
    brick.inputs["Scale"].default_value = 9.0
    brick.inputs["Mortar Size"].default_value = 0.055
    brick.inputs["Mortar Smooth"].default_value = 0.02
    brick.inputs["Bias"].default_value = 0.0
    brick.inputs["Brick Width"].default_value = 0.42
    brick.inputs["Row Height"].default_value = 0.26
    # Most bricks land near Color2 (dark), a minority near Color1 (lit).
    brick.inputs["Color1"].default_value = (1.0, 0.66, 0.30, 1.0)
    brick.inputs["Color2"].default_value = (0.02, 0.02, 0.03, 1.0)
    brick.inputs["Mortar"].default_value = (0.0, 0.0, 0.0, 1.0)

    # Fac is 0 in the mortar lines, so it keeps frames between the windows.
    strength = tree.nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    strength.inputs[1].default_value = CONFIG["window_emission"]

    links = tree.links
    links.new(coord.outputs["Object"], brick.inputs["Vector"])
    links.new(brick.outputs["Color"], bsdf.inputs["Emission Color"])
    links.new(brick.outputs["Fac"], strength.inputs[0])
    links.new(strength.outputs["Value"], bsdf.inputs["Emission Strength"])
    return mat


def add_atmosphere():
    """Thin homogeneous fog in the world volume, for beam visibility."""
    density = CONFIG["fog_density"]
    if density <= 0.0:
        return None
    world = bpy.context.scene.world
    tree = world.node_tree
    scatter = tree.nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Density"].default_value = density
    scatter.inputs["Anisotropy"].default_value = 0.55
    output = next(n for n in tree.nodes if n.type == "OUTPUT_WORLD")
    tree.links.new(scatter.outputs["Volume"], output.inputs["Volume"])
    return scatter


def build_environment():
    """Ground plane plus a few blockout buildings for scale and occlusion."""
    bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        principled(
            "Asphalt",
            (0.030, 0.031, 0.036),
            roughness=CONFIG["ground_roughness"],
        )
    )

    concrete = facade_material("Facade")
    glass_trim = principled("Trim", (0.04, 0.045, 0.06), roughness=0.15, metallic=0.8)

    # x, y, footprint, height
    blocks = [
        (-16.0, 14.0, 11.0, 22.0),
        (-2.0, 20.0, 9.0, 15.0),
        (14.0, 16.0, 12.0, 27.0),
        (18.0, -8.0, 10.0, 12.0),
        (-19.0, -10.0, 9.0, 17.0),
    ]
    for i, (x, y, foot, height) in enumerate(blocks):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, height / 2.0))
        block = bpy.context.active_object
        block.name = f"Building_{i}"
        block.scale = (foot, foot * 0.8, height)
        block.data.materials.append(concrete)

        # A thin band near the top so the blocks read as buildings, not boxes.
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, height * 0.97))
        band = bpy.context.active_object
        band.name = f"Building_{i}_band"
        band.scale = (foot * 1.02, foot * 0.82, height * 0.02)
        band.data.materials.append(glass_trim)

    return ground


def build_mast_and_panel(centre, d):
    """Lamppost-style mast with the phased array panel on top."""
    cfg = CONFIG
    metal = principled("Mast", (0.06, 0.065, 0.07), roughness=0.35, metallic=0.9)

    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.075,
        depth=cfg["mast_height"],
        location=(cfg["mast_pos"][0], cfg["mast_pos"][1], cfg["mast_height"] / 2.0),
        vertices=24,
    )
    mast = bpy.context.active_object
    mast.name = "Mast"
    mast.data.materials.append(metal)

    # Panel body. Physical aperture is (n-1)*d plus a small margin.
    width = (cfg["n_x"] - 1) * d
    height = (cfg["n_z"] - 1) * d
    margin = 2.5 * d
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=tuple(centre))
    panel = bpy.context.active_object
    panel.name = "ArrayPanel"
    panel.scale = (width + margin, 0.035, height + margin)
    panel.data.materials.append(principled("PanelBody", (0.02, 0.02, 0.025), roughness=0.4))

    # Individual radiating elements, so the panel reads as an array up close.
    patch_mat = principled(
        "Patch",
        (0.55, 0.42, 0.10),
        roughness=0.3,
        metallic=0.85,
        emission=(1.0, 0.55, 0.12),
        emission_strength=1.5,
    )
    verts, faces = [], []
    half = 0.36 * d
    for ix in range(cfg["n_x"]):
        for iz in range(cfg["n_z"]):
            cx = centre[0] + (ix - (cfg["n_x"] - 1) / 2.0) * d
            cz = centre[2] + (iz - (cfg["n_z"] - 1) / 2.0) * d
            y = centre[1] + 0.019
            base = len(verts)
            verts += [
                (cx - half, y, cz - half),
                (cx + half, y, cz - half),
                (cx + half, y, cz + half),
                (cx - half, y, cz + half),
            ]
            faces.append((base, base + 1, base + 2, base + 3))
    patches = new_mesh_object("ArrayElements", verts, faces)
    patches.data.materials.append(patch_mat)

    return panel, patches


def build_lobe(centre, steer, d, lam):
    """Radiation lobe as a radial surface: r(u) scaled from the pattern in dB."""
    cfg = CONFIG
    n_theta, n_phi = cfg["lobe_n_theta"], cfg["lobe_n_phi"]
    dyn = cfg["lobe_dyn_range_db"]

    theta = np.linspace(1e-4, math.pi - 1e-4, n_theta)
    phi = np.linspace(0.0, 2.0 * math.pi, n_phi, endpoint=False)
    th, ph = np.meshgrid(theta, phi, indexing="ij")

    u = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], axis=-1)

    pattern = power_pattern(u, steer, d, lam)
    with np.errstate(divide="ignore"):
        db = 10.0 * np.log10(np.maximum(pattern, 1e-30))
    radius = np.clip((db + dyn) / dyn, 0.0, None) * cfg["lobe_len"]

    points = centre[None, None, :] + radius[..., None] * u

    verts = [tuple(p) for p in points.reshape(-1, 3)]
    faces = []
    for i in range(n_theta - 1):
        for j in range(n_phi):
            j2 = (j + 1) % n_phi
            a = i * n_phi + j
            b = i * n_phi + j2
            c = (i + 1) * n_phi + j2
            e = (i + 1) * n_phi + j
            faces.append((a, b, c, e))

    lobe = new_mesh_object("BeamLobe", verts, faces)

    # Colour the lobe by pattern level so the sidelobe structure is visible.
    colours = lobe.data.color_attributes.new(name="level", type="FLOAT_COLOR", domain="POINT")
    norm = np.clip((db + dyn) / dyn, 0.0, 1.0).reshape(-1)
    ramp = np.array([turbo(v) for v in norm], dtype=np.float32)
    flat = np.concatenate([ramp, np.ones((ramp.shape[0], 1), dtype=np.float32)], axis=1)
    colours.data.foreach_set("color", flat.reshape(-1))

    lobe.data.materials.append(
        emissive_attribute_material(
            "LobeGlow",
            strength=CONFIG["lobe_emission"],
            alpha=CONFIG["lobe_alpha"],
        )
    )
    lobe.data.shade_smooth()
    return lobe, radius, u


def turbo(t):
    """Compact approximation of the turbo colormap, t in [0, 1]."""
    t = float(np.clip(t, 0.0, 1.0))
    stops = [
        (0.00, (0.19, 0.07, 0.23)),
        (0.25, (0.10, 0.60, 0.85)),
        (0.50, (0.35, 0.93, 0.40)),
        (0.72, (0.98, 0.83, 0.16)),
        (0.88, (0.98, 0.40, 0.09)),
        (1.00, (0.85, 0.10, 0.05)),
    ]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:], strict=False):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(a + f * (b - a) for a, b in zip(c0, c1, strict=True))
    return stops[-1][1]


def emissive_attribute_material(name, strength=4.0, alpha=1.0):
    """Emission driven by a POINT colour attribute named 'level'."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    attr = tree.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "level"
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = strength
    output = tree.nodes.new("ShaderNodeOutputMaterial")

    tree.links.new(attr.outputs["Color"], emission.inputs["Color"])

    if alpha < 1.0:
        transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
        mix = tree.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        tree.links.new(transparent.outputs["BSDF"], mix.inputs[1])
        tree.links.new(emission.outputs["Emission"], mix.inputs[2])
        tree.links.new(mix.outputs["Shader"], output.inputs["Surface"])
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
    else:
        tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat


def import_phantom():
    """Load a phantom STL from the repo data directory."""
    data_dir = os.environ.get("AEGIS_DATA_DIR", "/home/user/aegis/data")
    path = os.path.join(data_dir, CONFIG["phantom_stl"])
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    new = list(set(bpy.data.objects) - before)
    if not new:
        raise RuntimeError("STL import produced no object")

    phantom = new[0]
    phantom.name = "Phantom"
    return phantom


def forward_from_feet(phantom):
    """Unit vector in the phantom's local XY plane pointing where it faces."""
    mesh = phantom.data
    count = len(mesh.vertices)
    co = np.empty(count * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)

    z = co[:, 2]
    z0, z1 = z.min(), z.max()
    height = z1 - z0

    foot = co[z < z0 + 0.045 * height]
    ankle = co[(z > z0 + 0.075 * height) & (z < z0 + 0.16 * height)]
    if len(foot) < 8 or len(ankle) < 8:
        # Fall back to the whole-body axis if the slabs came out empty.
        return Vector((0.0, 1.0)).normalized()

    delta = foot[:, :2].mean(axis=0) - ankle[:, :2].mean(axis=0)
    vec = Vector((float(delta[0]), float(delta[1])))
    if vec.length < 1e-6:
        return Vector((0.0, 1.0))
    print(f"[phantom] forward from feet: ({vec.x:.4f}, {vec.y:.4f})")
    return vec.normalized()


def place_phantom(phantom):
    """Stand the phantom on the ground at the configured spot, facing the mast.

    The STL arrives in metres in its own frame, so the placement is derived
    from its bounding box rather than assumed.
    """
    cfg = CONFIG
    bpy.context.view_layer.objects.active = phantom
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    # Which way does this mesh face? Toes reach further forward than heels, so
    # the vector from the ankle band to the foot slab points forward. Cheaper
    # and more reliable than assuming an STL export convention.
    forward = forward_from_feet(phantom)

    # Turn that forward vector to point at the mast.
    to_mast = Vector(
        (
            CONFIG["mast_pos"][0] - cfg["phantom_pos"][0],
            CONFIG["mast_pos"][1] - cfg["phantom_pos"][1],
        )
    ).normalized()
    yaw = math.atan2(to_mast.y, to_mast.x) - math.atan2(forward.y, forward.x)
    phantom.rotation_euler = (0.0, 0.0, yaw)
    bpy.context.view_layer.update()

    corners = [phantom.matrix_world @ Vector(c) for c in phantom.bound_box]
    min_z = min(c.z for c in corners)
    height = max(c.z for c in corners) - min_z

    phantom.location = (
        cfg["phantom_pos"][0],
        cfg["phantom_pos"][1],
        phantom.location.z - min_z,
    )
    bpy.context.view_layer.update()
    return height


def paint_absorbed_power(phantom, centre, steer, d, lam):
    """Evaluate Sab per vertex and write it as a colour attribute."""
    cfg = CONFIG
    mesh = phantom.data
    matrix = phantom.matrix_world
    normal_matrix = matrix.to_3x3().inverted().transposed()

    count = len(mesh.vertices)
    positions = np.empty(count * 3, dtype=np.float64)
    normals = np.empty(count * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", positions)
    mesh.vertices.foreach_get("normal", normals)
    positions = positions.reshape(-1, 3)
    normals = normals.reshape(-1, 3)

    # Into world space.
    world = np.array([(matrix @ Vector(p))[:] for p in positions], dtype=np.float64)
    world_n = np.array(
        [(normal_matrix @ Vector(n)).normalized()[:] for n in normals],
        dtype=np.float64,
    )

    delta = world - centre[None, :]
    dist = np.linalg.norm(delta, axis=1)
    dist = np.maximum(dist, 1e-6)
    k_hat = delta / dist[:, None]

    pattern = power_pattern(k_hat, steer, d, lam)
    gain = pattern * peak_gain_linear()

    # Incident power density from the panel, then the AEGIS surface equation.
    s_inc = cfg["p_tx_w"] * gain / (4.0 * math.pi * dist**2)
    cos_inc = np.clip(np.einsum("ij,ij->i", world_n, -k_hat), 0.0, None)
    s_ab = s_inc * cfg["T0"] * cos_inc

    peak = s_ab.max()
    norm = s_ab / peak if peak > 0 else s_ab

    # Gamma lifts the low end so the falloff away from the spot stays legible.
    shaped = norm ** CONFIG["skin_gamma"]
    ramp = np.array([turbo(v) for v in shaped], dtype=np.float32)
    flat = np.concatenate([ramp, np.ones((ramp.shape[0], 1), dtype=np.float32)], axis=1)

    existing = mesh.color_attributes.get("level")
    if existing:
        mesh.color_attributes.remove(existing)
    attr = mesh.color_attributes.new(name="level", type="FLOAT_COLOR", domain="POINT")
    attr.data.foreach_set("color", flat.reshape(-1))

    mat = skin_material()
    mesh.materials.clear()
    mesh.materials.append(mat)
    mesh.shade_smooth()

    return {
        "peak_s_ab": float(peak),
        "peak_s_inc": float(s_inc.max()),
        "mean_s_ab_lit": float(s_ab[cos_inc > 0].mean()),
        "lit_fraction": float((cos_inc > 0).mean()),
        "limit_fraction": float(peak / cfg["apd_limit_w_m2"]),
        "closest_m": float(dist.min()),
        "vertices": count,
    }


def skin_material():
    """Skin shaded by the 'level' attribute, with a glow on the hot spot."""
    mat = bpy.data.materials.new("SkinAPD")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    attr = tree.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "level"
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.42
    bsdf.inputs["Emission Strength"].default_value = CONFIG["skin_emission"]
    output = tree.nodes.new("ShaderNodeOutputMaterial")

    tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


def build_lighting():
    """Nishita sky plus a sun, so the scene needs no external HDRI."""
    world = bpy.data.worlds.new("Sky") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    sky = tree.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(CONFIG["sun_elevation_deg"])
    sky.sun_rotation = math.radians(200.0)
    sky.altitude = 30.0
    background = tree.nodes.new("ShaderNodeBackground")
    background.inputs["Strength"].default_value = CONFIG["sky_strength"]
    output = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(sky.outputs["Color"], background.inputs["Color"])
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])

    bpy.ops.object.light_add(type="SUN", location=(10.0, -18.0, 20.0))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = CONFIG["sun_energy"]
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(58.0), 0.0, math.radians(28.0))
    return sun


def build_camera(centre, target):
    bpy.ops.object.camera_add(location=CONFIG["cam_pos"])
    cam = bpy.context.active_object
    cam.name = "HeroCam"
    cam.data.lens = CONFIG["cam_lens"]

    look_at = Vector(CONFIG["cam_look"])
    direction = look_at - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 12
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    return scene


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------


def verify(centre, steer, radius, u, phantom_height, apd_stats):
    """Re-derive facts from the built scene and report them as numbers."""
    report = {}

    # The lobe's longest radius must point along the steering vector.
    flat_index = int(np.argmax(radius))
    peak_dir = u.reshape(-1, 3)[flat_index]
    cos_err = float(np.clip(np.dot(peak_dir, steer), -1.0, 1.0))
    report["lobe_peak_error_deg"] = math.degrees(math.acos(cos_err))
    report["steer_vector"] = [round(float(v), 4) for v in steer]
    report["lobe_peak_vector"] = [round(float(v), 4) for v in peak_dir]

    # Off-broadside steering angle, for context on how hard the steer is.
    report["steer_off_boresight_deg"] = math.degrees(
        math.acos(float(np.clip(np.dot(steer, [0.0, 1.0, 0.0]), -1.0, 1.0)))
    )

    # Nothing may sit below the ground plane.
    lowest = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        zs = [(obj.matrix_world @ Vector(c)).z for c in obj.bound_box]
        lowest[obj.name] = round(min(zs), 4)
    report["min_z_by_object"] = lowest
    report["objects_below_ground"] = [name for name, z in lowest.items() if z < -0.01]

    # A phantom that is not roughly human-sized means the STL units were wrong.
    report["phantom_height_m"] = round(phantom_height, 3)
    report["phantom_height_plausible"] = 1.4 < phantom_height < 2.2

    report["polygons"] = sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.type == "MESH")
    report["apd"] = apd_stats
    return report


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def build():
    clear_scene()
    centre, boresight, steer, d, lam = array_geometry()

    build_environment()
    build_mast_and_panel(centre, d)
    lobe, radius, u = build_lobe(centre, steer, d, lam)

    phantom = import_phantom()
    height = place_phantom(phantom)
    apd_stats = paint_absorbed_power(phantom, centre, steer, d, lam)

    build_lighting()
    add_atmosphere()
    target = np.array([CONFIG["phantom_pos"][0], CONFIG["phantom_pos"][1], CONFIG["target_z"]])
    build_camera(centre, target)
    configure_render()

    report = verify(centre, steer, radius, u, height, apd_stats)
    report["wavelength_mm"] = round(lam * 1000.0, 3)
    report["element_spacing_mm"] = round(d * 1000.0, 3)
    report["aperture_cm"] = [
        round((CONFIG["n_x"] - 1) * d * 100.0, 2),
        round((CONFIG["n_z"] - 1) * d * 100.0, 2),
    ]
    report["peak_gain_dbi"] = round(10.0 * math.log10(peak_gain_linear()), 2)
    report["eirp_dbm"] = round(10.0 * math.log10(CONFIG["p_tx_w"] * peak_gain_linear() * 1000.0), 2)
    return report


print(json.dumps(build(), indent=2, default=str))
