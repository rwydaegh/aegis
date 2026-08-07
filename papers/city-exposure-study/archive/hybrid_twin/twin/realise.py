"""Realise the twin in Blender: geometry, materials, clutter, camera, render.

    ~/blender-4.5/blender -b -P twin/realise.py -- --area graslei --render hero.png

Runs inside Blender, so it is the only module here that imports bpy. Everything it
builds comes from the pure-Python layers (`anchor`, `facade`, `clutter`), which is
what lets the same scene description also go to Sionna without a second authoring
pass.

Materials are procedural rather than flat colour on purpose. "A texture painted on a
box face" is the first named failure mode in the MineBench rubric, and the fix is
that brick has to have depth in the normal, glass has to be actually reflective, and
two adjacent houses have to differ by more than their albedo.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from twin import anchor as anchor_mod  # noqa: E402
from twin import clutter as clutter_mod  # noqa: E402
from twin import facade as facade_mod  # noqa: E402
from twin import radiator as radiator_mod  # noqa: E402

CITYGEN = pathlib.Path("/home/user/aegis/tools/citygen/The_City_Generator_2.6"
                       "/City_Generator2.0.blend")

from twin.areas import AREAS, CAMERAS  # noqa: E402

# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------

def _principled(name: str, base, rough: float, spec: float = 0.5,
                metal: float = 0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    return mat


def _world_coords(nt, scale: float):
    """Object-space texture coordinates at true metre scale.

    The generated meshes carry no UV map, so any texture left on the default
    coordinate input collapses to a degenerate projection and renders as vertical
    stripes. Object coordinates are in metres here, because every vertex is already
    in scene ENU and the objects sit at the origin.
    """
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    return mp


def _per_object_tint(nt, spread: float = 0.14):
    """A hue and value jitter that differs per building but is stable per object.

    This is the direct answer to "an entire facade is brick and the next building is
    all stone": one material, many buildings, none of them identical. Without it a
    terrace reads as a single extruded ribbon no matter how good the brick is.
    """
    info = nt.nodes.new("ShaderNodeObjectInfo")
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = 0.5
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 2.0 * spread
    nt.links.new(info.outputs["Random"], sub.inputs[0])
    nt.links.new(sub.outputs["Value"], mul.inputs[0])
    return info, mul


def _brick(name: str, base, mortar, scale: float = 14.0):
    """Brick with real relief in the normal, plus per-brick colour variation.

    The per-brick randomisation comes from the Brick texture's own Color1/Color2
    mix rather than a separate noise gate. An earlier attempt at this used a noise
    node on the same scaled mapping as the brick, which oscillated at about 63
    cycles per brick and rendered as television static.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    # Real Flemish brick is about 210 x 65 mm. With object coordinates in metres
    # and the texture's own 0.5 x 0.22 cell, scale 2.4 lands near 0.21 x 0.09 m.
    mp = _world_coords(nt, 2.4)
    tex = nt.nodes.new("ShaderNodeTexBrick")
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    tex.inputs["Scale"].default_value = 1.0
    tex.inputs["Color1"].default_value = (*base, 1.0)
    tex.inputs["Color2"].default_value = (*[c * 0.78 for c in base], 1.0)
    tex.inputs["Mortar"].default_value = (*mortar, 1.0)
    tex.inputs["Mortar Size"].default_value = 0.022
    tex.inputs["Mortar Smooth"].default_value = 0.1
    tex.inputs["Bias"].default_value = 0.0
    tex.inputs["Brick Width"].default_value = 0.5
    tex.inputs["Row Height"].default_value = 0.22

    _info, jitter = _per_object_tint(nt, spread=0.16)
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    nt.links.new(tex.outputs["Color"], hsv.inputs["Color"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.inputs[1].default_value = 1.0
    nt.links.new(jitter.outputs["Value"], add.inputs[0])
    nt.links.new(add.outputs["Value"], hsv.inputs["Value"])
    hsv.inputs["Saturation"].default_value = 1.05

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.88
    return mat


def _stone(name: str, base, noise_scale: float = 9.0, rough: float = 0.72,
           tint: bool = True, bump_strength: float = 0.16):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    mp = _world_coords(nt, 1.0)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.80 for c in base], 1.0)
    ramp.color_ramp.elements[1].color = (*base, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    out = ramp.outputs["Color"]
    if tint:
        _info, jitter = _per_object_tint(nt, spread=0.13)
        hsv = nt.nodes.new("ShaderNodeHueSaturation")
        nt.links.new(ramp.outputs["Color"], hsv.inputs["Color"])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.inputs[1].default_value = 1.0
        nt.links.new(jitter.outputs["Value"], add.inputs[0])
        nt.links.new(add.outputs["Value"], hsv.inputs["Value"])
        out = hsv.outputs["Color"]

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    nt.links.new(out, bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def _cobble(name: str, base):
    """Sett paving. OSM tags 86 ways in this block `surface=sett`, so the cobble is
    measured, not invented, and it is also the surface whose roughness matters most
    at 28 GHz because ground bounces arrive near grazing."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    mp = _world_coords(nt, 5.5)          # ~18 cm setts
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    col = nt.nodes.new("ShaderNodeTexVoronoi")
    col.feature = "F1"
    col.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], col.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*[c * 0.62 for c in base], 1.0)
    ramp.color_ramp.elements[1].color = (*[c * 1.15 for c in base], 1.0)
    nt.links.new(col.outputs["Distance"], ramp.inputs["Fac"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.55
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.82
    return mat


def _person(name: str):
    """Skin above the shoulders and hands, clothing below, tinted per person.

    Ten identical grey mannequins is the uniform-detail failure mode wearing a
    literal uniform. Splitting on world height is crude and reads correctly at
    street distance, which is where these bodies are seen. The RT export ignores
    this entirely and binds one skin radio material to the whole body, because at
    28 GHz clothing is a fraction of a wavelength thick.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    # Shoulder line sits near 51.8 m in this scene's ENU frame.
    grad = nt.nodes.new("ShaderNodeMath")
    grad.operation = "SUBTRACT"
    grad.inputs[1].default_value = 51.75
    nt.links.new(sep.outputs["Z"], grad.inputs[0])
    step = nt.nodes.new("ShaderNodeMath")
    step.operation = "GREATER_THAN"
    step.inputs[1].default_value = 0.0
    nt.links.new(grad.outputs["Value"], step.inputs[0])

    info = nt.nodes.new("ShaderNodeObjectInfo")
    cloth = nt.nodes.new("ShaderNodeValToRGB")
    cloth.color_ramp.interpolation = "CONSTANT"
    for pos, col in ((0.0, (0.09, 0.11, 0.16)), (0.2, (0.35, 0.13, 0.12)),
                     (0.4, (0.13, 0.20, 0.17)), (0.6, (0.55, 0.50, 0.42)),
                     (0.8, (0.16, 0.16, 0.18))):
        e = cloth.color_ramp.elements.new(pos) if pos > 0 else \
            cloth.color_ramp.elements[0]
        e.position = pos
        e.color = (*col, 1.0)
    nt.links.new(info.outputs["Random"], cloth.inputs["Fac"])

    skin = nt.nodes.new("ShaderNodeValToRGB")
    skin.color_ramp.elements[0].color = (0.42, 0.26, 0.19, 1.0)
    skin.color_ramp.elements[1].color = (0.72, 0.53, 0.42, 1.0)
    nt.links.new(info.outputs["Random"], skin.inputs["Fac"])

    mix = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(step.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(cloth.outputs["Color"], mix.inputs[1])
    nt.links.new(skin.outputs["Color"], mix.inputs[2])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.68
    return mat


def build_materials() -> dict:
    """One material per semantic tag class, keyed the way the mesh tags are."""
    m = {}
    m["wall:brick"] = _brick("wall_brick", (0.44, 0.20, 0.15), (0.62, 0.58, 0.52))
    m["wall:plasterboard"] = _stone("wall_plaster", (0.86, 0.83, 0.75), 11.0)
    m["wall:marble"] = _stone("wall_marble", (0.80, 0.78, 0.73), 6.0)
    m["wall:concrete"] = _stone("wall_concrete", (0.60, 0.59, 0.57), 8.0)
    m["wall:wood"] = _principled("wall_wood", (0.32, 0.20, 0.11), 0.72)
    # Dielectric, not metal. At `metal=0.35` the pane reflects the sky at every
    # angle equally and 200 windows render as 200 identical sage rectangles, which
    # is what the earlier hero shots show. A dielectric obeys Fresnel: nearly black
    # face on, bright at grazing, so a row of windows picks up the raking light the
    # way glass does and the facade stops looking printed.
    m["glass"] = _principled("glass_dark", (0.018, 0.026, 0.032), 0.045,
                             spec=1.0, metal=0.0)
    m["sill"] = _stone("trim_stone", (0.76, 0.74, 0.69), 14.0)
    m["cornice"] = _stone("cornice_stone", (0.72, 0.70, 0.65), 12.0)
    m["roof"] = _principled("roof_tile", (0.20, 0.17, 0.17), 0.80)
    m["door"] = _principled("door_wood", (0.10, 0.14, 0.12), 0.45)
    m["frame"] = _principled("window_frame", (0.88, 0.87, 0.84), 0.40)
    m["ground:sett"] = _cobble("ground_sett", (0.115, 0.110, 0.105))
    m["ground:paving"] = _stone("ground_paving", (0.20, 0.195, 0.185), 5.0,
                                rough=0.85, tint=False, bump_strength=0.25)
    m["ground:asphalt"] = _principled("ground_asphalt", (0.045, 0.045, 0.05), 0.9)
    m["person"] = _person("person")
    m["panel"] = _principled("panel_radome", (0.86, 0.86, 0.84), 0.35)
    m["bracket"] = _principled("bracket", (0.22, 0.22, 0.24), 0.42, metal=0.85)
    m["element"] = _principled("element", (0.72, 0.66, 0.30), 0.30, metal=1.0)
    # Roughness 0.035 was a mirror, and a mirror reflects the row as a second row
    # of equal sharpness, which is the single strongest tell that a render is CG.
    # A canal under a light breeze sits nearer 0.09.
    m["water"] = _principled("water", (0.012, 0.028, 0.032), 0.09, spec=1.0)
    m["quay"] = _stone("quay_stone", (0.30, 0.29, 0.26), 9.0)
    return m


def material_for(tag, mats: dict):
    _layer, cls, mat = tag
    if cls == "wall":
        return mats.get(f"wall:{mat}", mats["wall:brick"])
    return mats.get(cls, mats["wall:concrete"])


def build_people(path, mats, collection) -> int:
    """Load the precomputed SMPL-X walkers. One object per person, so Blender's
    per-object random gives each of them a different skin and clothing tone."""
    import numpy as _np
    pack = _np.load(str(path))
    verts, faces, counts = pack["verts"], pack["faces"], pack["counts"]
    off_f, off_v = 0, 0
    for i, n in enumerate(counts):
        f = faces[off_f:off_f + n] - off_v
        nv = int(f.max()) + 1
        v = verts[off_v:off_v + nv]
        me = bpy.data.meshes.new(f"person_{i}")
        me.from_pydata([tuple(map(float, q)) for q in v], [],
                       [list(map(int, t)) for t in f])
        me.validate(verbose=False)
        me.materials.append(mats["person"])
        me.shade_smooth()
        collection.objects.link(bpy.data.objects.new(f"person_{i}", me))
        off_f += n
        off_v += nv
    return len(counts)


def build_radiator(a, mats, collection, area: str, show_lobe: bool):
    cell = radiator_mod.default_cell(a, area)
    mesh_to_object(radiator_mod.panel_mesh(cell), "smallcell_panel",
                   mats, collection)
    if show_lobe:
        lobe = radiator_mod.lobe_mesh(cell)
        ob = mesh_to_object(lobe, "smallcell_lobe", mats, collection)
        glow = bpy.data.materials.new("lobe_glow")
        glow.use_nodes = True
        nt = glow.node_tree
        for node in list(nt.nodes):
            if node.type != "OUTPUT_MATERIAL":
                nt.nodes.remove(node)
        emit = nt.nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (0.15, 0.62, 1.0, 1.0)
        emit.inputs["Strength"].default_value = 2.4
        trans = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = 0.82
        nt.links.new(trans.outputs[0], mix.inputs[1])
        nt.links.new(emit.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        glow.blend_method = "BLEND"
        ob.data.materials.clear()
        ob.data.materials.append(glow)
        ob.visible_shadow = False
    return cell


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def mesh_to_object(mesh, name: str, mats: dict, collection):
    verts, faces, tags = mesh.verts, mesh.faces, mesh.tags
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [list(f) for f in faces])
    me.validate(verbose=False)

    # Metre-scale box-projected UVs from the generator. Without these every 2D
    # texture degenerates, most visibly brick into vertical stripes.
    uv = me.uv_layers.new(name="UVMap")
    loop_uv = []
    for face_uvs in mesh.uvs:
        loop_uv.extend(face_uvs)
    if len(loop_uv) == len(me.loops):
        for i, (u, v) in enumerate(loop_uv):
            uv.data[i].uv = (u, v)
    else:
        print(f"[twin] UV mismatch on {name}: "
              f"{len(loop_uv)} uvs vs {len(me.loops)} loops")

    slots: dict = {}
    for tag in tags:
        mat = material_for(tag, mats)
        if mat.name not in slots:
            slots[mat.name] = len(slots)
            me.materials.append(mat)
    for poly, tag in zip(me.polygons, tags, strict=False):
        poly.material_index = slots[material_for(tag, mats).name]

    me.shade_flat()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def river_width(w) -> float:
    """Water width by name. The Leie is about 28 m through Graslei."""
    return 28.0 if "leie" in (w.tags.get("name") or "").lower() else 14.0


def _nearest_on_line(p: np.ndarray, line: np.ndarray) -> tuple[np.ndarray, float]:
    """Closest point on a polyline, and the distance to it."""
    a_i, b_i = line[:-1], line[1:]
    ab = b_i - a_i
    denom = (ab * ab).sum(axis=1)
    denom[denom < 1e-12] = 1e-12
    t = np.clip(((p - a_i) * ab).sum(axis=1) / denom, 0.0, 1.0)
    proj = a_i + t[:, None] * ab
    d = np.linalg.norm(proj - p, axis=1)
    k = int(d.argmin())
    return proj[k], float(d[k])


def _inside_ring(ring: np.ndarray, x: float, y: float) -> bool:
    xs, ys = ring[:, 0], ring[:, 1]
    x2, y2 = np.roll(xs, -1), np.roll(ys, -1)
    cond = (ys > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xin = (x2 - xs) * (y - ys) / (y2 - ys) + xs
    return int((cond & (x < xin)).sum()) % 2 == 1


def water_bodies(a, centre=None, radius: float = 1e9) -> list:
    """Every water feature that will actually be built, as (kind, geometry).

    Terrain and water used to filter by different rules: the hole was cut wherever
    any water way said so, but the sheet was only laid within a radius of the study
    centre. Beyond that radius the two disagreed and the result was a hole with
    nothing under it, which renders as the black wedge that sat over the north
    canal in every plate. One list, consulted by both, is the fix.
    """
    c = np.array(centre if centre is not None else (0.0, 0.0), dtype=float)
    out = []
    for w in a.ways_of("waterline"):
        line = np.asarray(w.line, dtype=float)
        if len(line) >= 2 and np.linalg.norm(line - c, axis=1).min() <= radius:
            out.append(("line", line, river_width(w) / 2.0))
    for w in a.ways_of("water"):
        ring = np.asarray(w.line, dtype=float)
        if len(ring) >= 3 and np.linalg.norm(ring - c, axis=1).min() <= radius:
            out.append(("poly", ring, 0.0))
    return out


def water_sdf(bodies, p: np.ndarray) -> tuple[float, np.ndarray]:
    """Signed distance to the nearest bank, negative in the water, plus the
    outward normal, so a wet vertex can be pushed onto the bank rather than merely
    deleted.

    Polygons are included and not only the widthed centrelines. Snapping the
    centrelines alone straightened the Leie and left every polygon-cut channel as
    a 4 m staircase, which is the same defect surviving in half the scene.
    """
    best = (1e9, np.array([1.0, 0.0]))
    for kind, geom, half in bodies:
        if kind == "line":
            q, d = _nearest_on_line(p, geom)
            s = d - half
        else:
            q, d = _nearest_on_line(p, np.vstack([geom, geom[:1]]))
            s = -d if _inside_ring(geom, float(p[0]), float(p[1])) else d
        if s < best[0]:
            n = (p - q) / (d + 1e-9) if d > 1e-6 else np.array([1.0, 0.0])
            # For a centreline that vector already points away from the water. For
            # a polygon it points from the ring towards whichever side `p` is on,
            # so inside the ring it has to be flipped to face out.
            if kind == "poly" and s < 0:
                n = -n
            best = (s, n)
    return best


def _in_water(a, x: float, y: float, *, margin: float = 1.0, bodies=None) -> bool:
    """Is this ground sample inside the canal.

    The terrain grid is a filtered ground surface and interpolates straight across
    the Leie, so without this the quay is paved over its own river: the water sheet
    sits 1.85 m below a continuous cobble lid and never appears in any shot.
    """
    p = np.array([x, y])
    for kind, geom, half in (bodies if bodies is not None else water_bodies(a)):
        if kind == "line":
            if facade_mod._seg_dist(p, geom) < half - margin:
                return True
        elif _inside_ring(geom, x, y):
            return True
    return False


def ground_grid(a, half: float, centre, bodies, step: float = 2.0):
    """One sampled grid over the block, with each vertex marked wet or dry.

    Terrain and water are cut from this single grid so that they tile the same
    plane and cannot disagree about where the bank is. Building them separately is
    what produced every water artefact in this scene in turn: a cobble lid over the
    canal, then a staircase bank, then a hole with nothing under it, then a black
    wedge where an offset ribbon tied itself in a bowtie.
    """
    n = int(2 * half / step) + 1
    cx, cy = centre
    verts, wet = [], []
    for j in range(n):
        for i in range(n):
            x = cx - half + i * step
            y = cy - half + j * step
            verts.append([x, y, a.terrain.at(x, y) - 0.05])
            wet.append(_in_water(a, x, y, bodies=bodies))

    # Dropping whole quads leaves the bank as a 4 m staircase, which reads as a
    # rendering fault rather than a quay. Pulling the wet vertices of a mixed quad
    # out onto the bank first straightens the same edge to the river line, and
    # costs nothing extra because the quad count does not change.
    # Against a frozen mask, and applied afterwards. Reading and writing `wet` in
    # the same pass let each newly dried vertex dry its neighbour in turn, and the
    # bank walked inward across the whole channel until the river had drained.
    was_wet = list(wet)
    for j in range(n):
        for i in range(n):
            k = j * n + i
            if not was_wet[k]:
                continue
            nb = [k - 1 if i else k, k + 1 if i < n - 1 else k,
                  k - n if j else k, k + n if j < n - 1 else k]
            dry = [v for v in nb if not was_wet[v]]
            if not dry:
                continue
            # Bisect towards the nearest dry neighbour rather than stepping along
            # the signed distance. Where a river centreline runs inside a water
            # polygon, both bodies claim the vertex and `water_sdf` reports the
            # deeper of the two, so the sdf version tried to move a vertex 8 m to
            # a boundary that is not on the outside of the union at all, hit its
            # own sanity clamp, and gave up: that is the staircase that survived
            # on the south channel while the Leie came out clean. The union
            # predicate is the only thing here that is unambiguously right, so
            # search on it directly.
            p = np.array(verts[k][:2])
            best = None
            for v in dry:
                lo, hi = p, np.array(verts[v][:2])
                for _ in range(14):
                    mid = (lo + hi) / 2.0
                    if _in_water(a, float(mid[0]), float(mid[1]), bodies=bodies):
                        lo = mid
                    else:
                        hi = mid
                d = float(np.linalg.norm(hi - p))
                if best is None or d < best[0]:
                    best = (d, hi)
            verts[k][0], verts[k][1] = float(best[1][0]), float(best[1][1])
            verts[k][2] = a.ground_global - 0.05
            wet[k] = False      # it is on the bank now, so its quads survive

    # Flatten the strip of ground next to the water to quay level. The DEM is a
    # filtered surface that dips as it crosses the channel, so a vertex snapped up
    # onto the bank stood up to 1.7 m above its unsnapped neighbour and the join
    # rendered as a row of pale flaps along both banks, like teeth. A quay is flat;
    # this makes it flat, and it is the surface a grazing ray reflects off.
    # Flat in both directions, not just raised. Clamping only the vertices below
    # quay level left the ones the DEM puts above it standing as a row of blocks
    # along the water, which read as broken wall panels. A quay deck is a built
    # flat surface; the DEM's undulation across it is filtering, not topography.
    band = int(np.ceil(9.0 / step))
    lip = a.ground_global - 0.05
    for j in range(n):
        for i in range(n):
            k = j * n + i
            if wet[k] or abs(verts[k][2] - lip) < 1e-3:
                continue
            near = any(was_wet[(j + dj) * n + (i + di)]
                       for dj in range(-band, band + 1)
                       for di in range(-band, band + 1)
                       if 0 <= j + dj < n and 0 <= i + di < n)
            if near:
                verts[k][2] = lip
    return n, verts, wet


def build_terrain(a, mats, collection, grid) -> list:
    n, verts, wet = grid
    faces = []
    for j in range(n - 1):
        for i in range(n - 1):
            k = j * n + i
            quad = [k, k + 1, k + n + 1, k + n]
            # Every corner dry, not merely one. Keeping the mixed quads dragged
            # their still-wet corners along at raw DEM height, and since the DEM
            # dips as it crosses the channel that built a 29 degree apron of
            # pavement running down into the river along the whole bank. The snap
            # has already pulled the real boundary vertices out onto the
            # waterline, so all-dry is exactly the quay and nothing else.
            if not all(not wet[v] for v in quad):
                continue        # leave the canal open
            faces.append(quad)
    me = bpy.data.meshes.new("terrain")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(verbose=False)
    # Metre-scale UVs, same reason the walls needed them: without a UV map the
    # cobble collapses and the ground renders as a flat grey plane.
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        x, y, _z = verts[loop.vertex_index]
        uv.data[loop.index].uv = (x, y)
    me.materials.append(mats["ground:sett"])
    ob = bpy.data.objects.new("terrain", me)
    collection.objects.link(ob)
    return faces


def build_quay_wall(a, mats, collection, verts, faces, bodies, *,
                    foot: float = 1.4) -> None:
    """Skin the open bank edge with a vertical stone wall down past the water.

    Without it the quay is a single sheet of polygons and any camera at eye level
    on the far bank sees the pavement edge-on as a line with nothing under it. The
    wall is also the surface a 28 GHz ray actually hits when it grazes the quay, so
    this is geometry the propagation run needs, not only the picture.
    """
    use: dict[tuple[int, int], int] = {}
    for f in faces:
        for i in range(4):
            e = (f[i], f[(i + 1) % 4])
            use[tuple(sorted(e))] = use.get(tuple(sorted(e)), 0) + 1
    z_bed = a.ground_global - 1.9 - foot
    wv, wf = [], []
    for (u, v), count in use.items():
        if count != 1:
            continue
        pu, pv = verts[u], verts[v]
        # Only the river bank, not the four outer edges of the terrain patch.
        # On `max` this wall came out as a row of detached slabs: a bank edge runs
        # between a vertex snapped onto the waterline and an ordinary grid vertex
        # up to a cell inland, so the inland end failed the test and every second
        # panel was dropped. One endpoint on the water is what makes an edge a
        # bank, so the test belongs on `min`.
        if min(water_sdf(bodies, np.array(pu[:2]))[0],
               water_sdf(bodies, np.array(pv[:2]))[0]) > 0.6:
            continue
        k = len(wv)
        wv += [tuple(pu), tuple(pv), (pv[0], pv[1], z_bed), (pu[0], pu[1], z_bed)]
        wf.append([k, k + 1, k + 2, k + 3])
    if not wf:
        return
    me = bpy.data.meshes.new("quay_wall")
    me.from_pydata(wv, [], wf)
    me.validate(verbose=False)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        x, y, z = wv[loop.vertex_index]
        uv.data[loop.index].uv = (x + y, z)
    me.materials.append(mats["quay"])
    collection.objects.link(bpy.data.objects.new("quay_wall", me))
    print(f"[realise] quay wall {len(wf)} panels")


def build_water(a, mats, collection, grid) -> None:
    """The complement of the terrain, one sheet, flat at the water line.

    A quad with any wet corner belongs to the water; a quad with any dry corner
    belongs to the terrain. Boundary quads are therefore in both, 1.9 m apart in z,
    so the terrain hides the water's ragged outer row and the visible edge is the
    snapped bank the two meshes share. Nothing is coplanar with anything, which is
    what the previous ribbon got wrong: overlapping faces at identical z make rays
    self-intersect and the whole canal renders black.
    """
    n, verts, wet = grid
    z = a.ground_global - 1.9
    faces = []
    for j in range(n - 1):
        for i in range(n - 1):
            k = j * n + i
            quad = [k, k + 1, k + n + 1, k + n]
            if any(wet[v] for v in quad):
                faces.append(quad)
    if not faces:
        return
    me = bpy.data.meshes.new("water")
    me.from_pydata([(v[0], v[1], z) for v in verts], [], faces)
    me.validate(verbose=False)
    me.materials.append(mats["water"])
    ob = bpy.data.objects.new("water", me)
    collection.objects.link(ob)
    print(f"[realise] water {len(faces)} quads")


# --------------------------------------------------------------------------
# Clutter
# --------------------------------------------------------------------------

CITYGEN_PICK = {
    "car": ["parking car", "01 car body"],
    "van": ["parking car", "01 car body"],
    "tree": ["Tree 04 MR.002", "Tree 04 MR.003", "Tree 04 MR.004",
             "Tree 04 MR.005"],
    "lamp": ["Street Lamp Model.001", "Street Lamp Model.000"],
    "bench": ["street_seating"],
    "bin": ["metal_trash_can", "metal_trash_can_rust"],
}


def load_citygen_assets(kinds) -> dict:
    """Append only the objects we will actually instance, and hide the originals."""
    want, need = [], set()
    for k in kinds:
        need.update(CITYGEN_PICK.get(k, []))
    if not need or not CITYGEN.exists():
        return {}
    loaded: list = []
    with bpy.data.libraries.load(str(CITYGEN), link=False) as (src, dst):
        want = [o for o in src.objects if o in need]
        dst.objects = want
        loaded = dst.objects
    # After the context manager exits, `dst.objects` holds the datablocks
    # themselves. Looking them back up by name is unreliable, partly because
    # several City Generator objects carry a trailing space ("Low poly car ").
    hidden = bpy.data.collections.new("_citygen_source")
    bpy.context.scene.collection.children.link(hidden)
    hidden.hide_render = True
    hidden.hide_viewport = True
    out: dict = {}
    for ob in loaded:
        if ob is None:
            continue
        hidden.objects.link(ob)
        out[ob.name] = ob
    missing = need - set(out)
    if missing:
        print(f"[twin] citygen assets not found: {sorted(missing)}")
    return out


def proxy_object(inst, mats, collection, idx: int):
    """Geometry for clutter classes City Generator has no asset for.

    Bollards, bike racks and cafe terraces were being planned and then silently
    dropped because they had no entry in CITYGEN_PICK, which is how a quay with 127
    mapped hospitality POIs rendered as bare pavement. Simple proxies beat absence:
    at street distance a bollard is a post, and in the RT export all of these are
    boxes anyway.
    """
    from twin.meshkit import Mesh, box, cylinder

    m = Mesh()
    x, y, z = inst.xy[0], inst.xy[1], inst.z
    k = inst.kind
    if k == "bollard":
        cylinder(m, (x, y, z), 0.08, 0.85, ("clutter", "bracket", "metal"),
                 segments=8)
        cylinder(m, (x, y, z + 0.85), 0.09, 0.06, ("clutter", "bracket", "metal"),
                 segments=8)
    elif k == "bicycle":
        for o in (-0.35, 0.35):
            cylinder(m, (x + o * math.sin(inst.yaw), y - o * math.cos(inst.yaw),
                         z), 0.33, 0.05, ("clutter", "bracket", "metal"),
                     segments=10)
        box(m, (x, y, z + 0.45), (1.0, 0.06, 0.28), inst.yaw,
            ("clutter", "bracket", "metal"))
    elif k == "terrace":
        s_ = inst.scale
        for dx in (-1.0, 1.0):
            for dy in (-0.8, 0.8):
                cx_ = x + dx * s_ * math.cos(inst.yaw) - dy * s_ * math.sin(inst.yaw)
                cy_ = y + dx * s_ * math.sin(inst.yaw) + dy * s_ * math.cos(inst.yaw)
                cylinder(m, (cx_, cy_, z), 0.34, 0.74,
                         ("clutter", "door", "wood"), segments=8)
                box(m, (cx_, cy_, z + 0.74), (0.78, 0.78, 0.04), inst.yaw,
                    ("clutter", "sill", "marble"))
        cylinder(m, (x, y, z), 0.04, 2.25, ("clutter", "bracket", "metal"),
                 segments=6)
        box(m, (x, y, z + 2.25), (3.0 * s_, 3.0 * s_, 0.08), inst.yaw + 0.4,
            ("clutter", "panel", "plasterboard"))
    else:
        return None
    return mesh_to_object(m, f"{k}_{idx:04d}", mats, collection)


def place_clutter(plan, assets: dict, collection, seed: int, mats=None) -> int:
    """Linked duplicates, so a hundred cars cost one car's memory."""
    rng = np.random.default_rng(seed + 991)
    placed = 0
    for inst in plan.instances:
        names = CITYGEN_PICK.get(inst.kind)
        if not names:
            if mats is not None and proxy_object(inst, mats, collection,
                                                 placed) is not None:
                placed += 1
            continue
        pool = [assets[n] for n in names if n in assets]
        if not pool:
            continue
        src = pool[int(rng.integers(len(pool)))]
        ob = src.copy()  # shares mesh data
        ob.name = f"{inst.kind}_{placed:04d}"
        ob.location = (inst.xy[0], inst.xy[1], inst.z)
        ob.rotation_euler = (0.0, 0.0, inst.yaw)
        s = inst.scale * (0.85 if inst.kind == "tree" else 1.0)
        ob.scale = (s, s, s)
        ob.hide_render = False
        ob.hide_viewport = False
        collection.objects.link(ob)
        placed += 1
    return placed


# --------------------------------------------------------------------------
# World, camera, render
# --------------------------------------------------------------------------

def setup_world(sun_elev_deg: float = 26.0, sun_azim_deg: float = 262.0) -> None:
    world = bpy.data.worlds.new("sky")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_azim_deg)
    sky.altitude = 10.0
    sky.air_density = 1.6
    sky.dust_density = 2.2
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.32

    light = bpy.data.lights.new("sun", type="SUN")
    light.energy = 2.1
    light.angle = math.radians(1.6)
    light.color = (1.0, 0.93, 0.82)
    ob = bpy.data.objects.new("sun", light)
    el = math.radians(sun_elev_deg)
    az = math.radians(sun_azim_deg)
    ob.rotation_euler = (math.pi / 2 - el, 0.0, az + math.pi / 2)
    bpy.context.scene.collection.objects.link(ob)


def place_camera(loc, target, lens: float = 28.0):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    ob = bpy.data.objects.new("cam", cam)
    ob.location = loc
    d = np.array(target, dtype=float) - np.array(loc, dtype=float)
    ob.rotation_euler = (
        math.acos(d[2] / (np.linalg.norm(d) + 1e-9)),
        0.0,
        math.atan2(d[1], d[0]) - math.pi / 2,
    )
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def hero_camera(a, buildings, centre):
    """Stand off the row, perpendicular to it, at quay height.

    Derived from the row's own principal axis rather than from a weighted centroid.
    The centroid version put the camera 148 m out looking at featureless blocks,
    which is the "visible primitives" failure mode arriving by way of bad framing
    rather than bad geometry. A terrace is a line, so the shot that reads is the one
    square to the line at a distance where windows are still legible.
    """
    cx, cy = centre
    pts = np.array([b.centroid for b in buildings])
    focus = pts.mean(axis=0)

    # Principal axis of the row.
    d = pts - focus
    _u, _sv, vt = np.linalg.svd(d, full_matrices=False)
    along = vt[0] / np.linalg.norm(vt[0])
    normal = np.array([-along[1], along[0]])

    # Face the side the water is on, else the side away from the block centre.
    # Both the surface polygons and the river centrelines tell us which way is
    # water. The centreline is the more reliable of the two here: the Leie passes
    # within 28 m of the row, while the nearest `natural=water` polygon is 56 m off.
    wpts = [w.line for w in a.ways if w.kind in {"water", "waterline"}]
    wpts = np.vstack(wpts) if wpts else np.empty((0, 2))
    if len(wpts):
        wpts = wpts[np.linalg.norm(wpts - focus, axis=1) < 60.0]
    if len(wpts):
        if np.dot(wpts.mean(axis=0) - focus, normal) < 0:
            normal = -normal
    elif np.dot(focus - np.array([cx, cy]), normal) < 0:
        normal = -normal

    # Distance so the row fills a 28 mm frame: half-length along the axis, times
    # the cotangent of the half field of view, plus a little air.
    half_len = float(np.abs(d @ along).max())
    hfov = math.atan(18.0 / 28.0)          # 36 mm sensor, 28 mm lens
    dist = float(np.clip(1.15 * half_len / math.tan(hfov), 34.0, 72.0))

    top = float(np.percentile([b.top_z for b in buildings], 75))
    aim3 = np.array([focus[0], focus[1],
                     a.ground_global + 0.62 * (top - a.ground_global)])

    # The analytic stand-off gives a sensible *radius*, but it says nothing about
    # what is at that point. Squaring up to the row put the first preset 1.0 m from
    # a facade with no water in frame. Scoring the ring settles both: the same
    # criteria that ranked the contact sheet pick the shipped camera, so a new city
    # gets a framed hero shot without anyone authoring coordinates for it.
    cands = candidate_eyes(a, buildings, focus, aim3, ring=dist)
    if cands:
        s, eye_xy, clear, water, infront, _rad, _th = max(cands, key=lambda c: c[0])
        z_eye = max(a.terrain.at(*eye_xy), a.ground_global) + 2.20
        print(f"[realise] hero eye={np.round(eye_xy, 1)} clear={clear:.1f} m "
              f"water={water:.2f} row={infront}/{len(buildings)} score={s:.3f}")
        return np.array([eye_xy[0], eye_xy[1], z_eye]), aim3

    stand = focus + normal * dist - along * half_len * 0.35
    z_eye = max(a.terrain.at(*stand), a.ground_global) + 2.20
    return np.array([stand[0], stand[1], z_eye]), aim3


def clearance(a, p) -> float:
    """Distance from a point to the nearest building footprint."""
    return min(facade_mod._seg_dist(p, np.vstack([b.ring, b.ring[:1]]))
               for b in a.buildings)


def water_in_shot(a, eye, aim) -> float:
    """Fraction of the sight line that runs over water.

    Foreground water is not decoration on a canal quay, it is the reason the view
    exists: it separates the camera from the row, fills the bottom of the frame,
    and doubles the facade through its reflection. The first hero preset had none,
    which is most of why it read as a car park with houses at the far end.
    """
    lines = [(np.asarray(w.line, dtype=float), river_width(w) / 2.0)
             for w in a.ways_of("waterline") if len(w.line) >= 2]
    if not lines:
        return 0.0
    eye, aim = np.asarray(eye, dtype=float)[:2], np.asarray(aim, dtype=float)[:2]
    n = 24
    hits = sum(1 for i in range(n)
               if any(facade_mod._seg_dist(eye + (aim - eye) * ((i + 0.5) / n), ln)
                      < half for ln, half in lines))
    return hits / n


def frame_fill(top_z: float, eye_z: float, dist: float, *, lens: float = 28.0,
               aspect: float = 720.0 / 1280.0) -> float:
    """How much of the frame height the row occupies, as a fraction.

    Rewarding clearance alone has an obvious runaway: the emptiest, safest, most
    water-covered spot in any city is far away, so the scorer walked backwards
    until the quay was 100 m off and the subject was a strip along the horizon
    under half a frame of cobbles. Distance has to cost something, and the honest
    cost is how small it makes the thing being photographed.
    """
    return (top_z - eye_z) / max(dist, 1e-6) / (18.0 * aspect / lens)


def candidate_eyes(a, sel, focus, aim, *, ring: float, n: int = 8,
                   top_z: float | None = None, lens: float = 28.0) -> list:
    """Viewpoints that are outdoors, clear of walls, and looking at something big
    enough to be the subject.

    A bare ring of azimuths puts a third of its cameras inside the block. Scoring
    first is cheap, and the number that matters is clearance: the previous authored
    preset stood 1.0 m from a facade, which no amount of lens choice recovers.
    """
    if top_z is None:
        top_z = float(np.percentile([b.top_z for b in sel], 75))
    out = []
    bodies = water_bodies(a, focus, 2.0 * ring + 60.0)
    for k in range(n * 6):
        th = 2 * math.pi * k / (n * 6)
        best = None
        for rad in (r * ring for r in (0.45, 0.6, 0.75, 1.0, 1.25, 1.5)):
            eye = focus + np.array([math.cos(th), math.sin(th)]) * rad
            clear = clearance(a, eye)
            if clear < 5.0:
                continue
            # Clearance only knows about walls, so on its own it rated a viewpoint
            # in the middle of the river as the best in the scene: maximum water
            # along the sight line, nothing nearby to collide with. The camera
            # floated at quay height out in the Leie and the near bank rose in
            # front of it as a wall across the bottom of the frame.
            if _in_water(a, float(eye[0]), float(eye[1]), margin=-2.0,
                         bodies=bodies):
                continue
            water = water_in_shot(a, eye, aim)
            # How much of the row is actually in front of this camera.
            view = (aim[:2] - eye) / (np.linalg.norm(aim[:2] - eye) + 1e-9)
            infront = sum(1 for b in sel
                          if np.dot(b.centroid - eye, view) > 0.3 * rad)
            fill = frame_fill(top_z, a.ground_global + 2.2,
                              float(np.linalg.norm(aim[:2] - eye)), lens=lens)
            s = (min(clear, 25.0) / 25.0) * (0.35 + 1.4 * water) \
                * (infront / max(len(sel), 1)) \
                * math.exp(-((fill - 0.62) / 0.26) ** 2)
            if best is None or s > best[0]:
                best = (s, eye, clear, water, infront, rad)
        if best:
            out.append((th, *best))
    # Keep the best in each of `n` azimuth buckets, so the sheet stays a sheet.
    buckets: dict[int, tuple] = {}
    for th, s, eye, clear, water, infront, rad in out:
        b = int(n * th / (2 * math.pi)) % n
        if b not in buckets or s > buckets[b][0]:
            buckets[b] = (s, eye, clear, water, infront, rad, th)
    return [buckets[k] for k in sorted(buckets)]


def render(path: str, res=(1280, 720), samples: int = 64) -> None:
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.5
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# --------------------------------------------------------------------------

def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei", choices=sorted(AREAS))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--render", default="")
    ap.add_argument("--save", default="")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--no-clutter", action="store_true")
    ap.add_argument("--no-readings", action="store_true",
                    help="ignore director readings and use the regional prior, "
                         "which is the A/B for whether reading the street helped")
    ap.add_argument("--people", default="data/twin/people.npz")
    ap.add_argument("--no-people", action="store_true")
    ap.add_argument("--lobe", action="store_true")
    ap.add_argument("--preset-camera", action="store_true",
                    help="use the authored camera in areas.py instead of the "
                         "scored one")
    args = ap.parse_args(argv)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials):
        for b in list(block):
            block.remove(b)

    cx, cy, radius = AREAS[args.area]
    a = anchor_mod.load()
    mats = build_materials()

    col_b = bpy.data.collections.new("buildings")
    col_c = bpy.data.collections.new("clutter")
    col_g = bpy.data.collections.new("ground")
    for c in (col_b, col_c, col_g):
        bpy.context.scene.collection.children.link(c)

    sel = [b for b in a.buildings
           if np.linalg.norm(b.centroid - np.array([cx, cy])) < radius]
    print(f"[twin] area={args.area} buildings={len(sel)}")

    readings = {} if args.no_readings else facade_mod.load_readings(args.area)
    print(f"[twin] director readings: {len(readings)} of {len(sel)} buildings")

    tris = 0
    for b in sel:
        spec = facade_mod.spec_for(b, readings)
        m = facade_mod.build(b, spec, a)
        tris += m.n_tris
        mesh_to_object(m, f"b_{b.osm_id}", mats, col_b)
    print(f"[twin] building triangles: {tris}")

    eye, target = hero_camera(a, sel, (cx, cy))
    # Terrain must reach the camera, or the shot opens on a hole in the world.
    reach = float(np.linalg.norm(eye[:2] - np.array([cx, cy]))) + 45.0
    half = max(radius + 25.0, reach)
    bodies = water_bodies(a, (cx, cy), half)
    grid = ground_grid(a, half, (cx, cy), bodies)
    faces = build_terrain(a, mats, col_g, grid)
    build_water(a, mats, col_g, grid)
    build_quay_wall(a, mats, col_g, grid[1], faces, bodies)

    if not args.no_clutter:
        plan = clutter_mod.build_plan(
            a, seed=args.seed, frontage=(cx, cy, radius),
            ground_floor={k: s.ground_floor for k, s in readings.items()})
        plan.instances = [i for i in plan.instances
                          if (i.xy[0] - cx) ** 2 + (i.xy[1] - cy) ** 2 < radius ** 2]
        assets = load_citygen_assets({i.kind for i in plan.instances})
        n = place_clutter(plan, assets, col_c, args.seed, mats=mats)
        print(f"[twin] clutter placed: {n} of {len(plan.instances)} planned")

    col_p = bpy.data.collections.new("people")
    col_r = bpy.data.collections.new("radiator")
    for c in (col_p, col_r):
        bpy.context.scene.collection.children.link(c)

    if not args.no_people and pathlib.Path(args.people).exists():
        n = build_people(args.people, mats, col_p)
        print(f"[twin] people: {n}")

    cell = build_radiator(a, mats, col_r, args.area, args.lobe)
    bud = cell.budget()
    print(f"[twin] small cell on {cell.host_id} at "
          f"{np.round(cell.position, 1)}  EIRP {bud['eirp_dbm']:.1f} dBm  "
          f"HPBW {bud['hpbw_deg']:.1f} deg")

    setup_world()

    if args.save:
        bpy.ops.wm.save_as_mainfile(filepath=args.save)
        print(f"[twin] saved {args.save}")

    if args.render:
        # The authored preset is opt-in, not the default. It used to win silently,
        # so `hero_camera` computed a viewpoint, printed it, and was then thrown
        # away at render time: every improvement to the scorer landed in the
        # contact sheet and none of it reached the shipped picture. An authored
        # camera also does not survive "now do Paris", which is the whole point.
        preset = CAMERAS.get(args.area) if args.preset_camera else None
        if preset:
            (ex, ey), (tx, ty), lens = preset
            top = float(np.percentile([b.top_z for b in sel], 75))
            eye = np.array([ex, ey, max(a.terrain.at(ex, ey),
                                        a.ground_global) + 1.65])
            target = np.array([tx, ty,
                               a.ground_global + 0.55 * (top - a.ground_global)])
        else:
            lens = 28.0
        place_camera(eye, target, lens=lens)
        print(f"[twin] camera {np.round(eye, 1)} -> {np.round(target, 1)}")
        render(args.render, samples=args.samples)
        print(f"[twin] rendered {args.render}")


if __name__ == "__main__":
    main()
