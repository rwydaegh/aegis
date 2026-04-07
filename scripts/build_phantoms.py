"""Build GLB phantoms from MakeHuman (MPFB2) characters + Mixamo animations.

Usage: blender --background --python scripts/build_phantoms.py

Generates parametric human characters via MPFB2 (MakeHuman Plugin for Blender),
adds a Mixamo-compatible skeleton, imports Mixamo animation clips, and exports as GLB.
"""

import bpy
import os
from pathlib import Path

PHANTOM_DIR = Path(__file__).resolve().parent.parent / "data" / "phantoms"

# Character definitions: macro parameters + target dimensions
# Macro values are 0.0-1.0 floats for MPFB2's parametric sliders
# gender: 0.0=male, 1.0=female
# age: 0.0=baby, 0.25=child, 0.5=young adult, 1.0=old
# muscle/weight/height/proportions: 0.0=min, 1.0=max
CHARACTERS = [
    {
        "name": "adult_male",
        "target_height_m": 1.76,
        "target_mass_kg": 73,
        "macro": {
            "gender": 0.0,
            "age": 0.5,
            "muscle": 0.6,
            "weight": 0.5,
            "proportions": 0.5,
            "height": 0.7,
            "cupsize": 0.5,
            "firmness": 0.5,
            "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
        },
        "skin_color": (0.72, 0.54, 0.42, 1.0),
    },
    {
        "name": "adult_female",
        "target_height_m": 1.63,
        "target_mass_kg": 60,
        "macro": {
            "gender": 1.0,
            "age": 0.45,
            "muscle": 0.4,
            "weight": 0.45,
            "proportions": 0.5,
            "height": 0.5,
            "cupsize": 0.5,
            "firmness": 0.6,
            "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
        },
        "skin_color": (0.78, 0.60, 0.48, 1.0),
    },
    {
        "name": "boy_6y",
        "target_height_m": 1.15,
        "target_mass_kg": 19,
        "macro": {
            "gender": 0.0,
            "age": 0.18,
            "muscle": 0.3,
            "weight": 0.35,
            "proportions": 0.5,
            "height": 0.3,
            "cupsize": 0.5,
            "firmness": 0.5,
            "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
        },
        "skin_color": (0.76, 0.58, 0.46, 1.0),
    },
    {
        "name": "girl_8y",
        "target_height_m": 1.36,
        "target_mass_kg": 30,
        "macro": {
            "gender": 1.0,
            "age": 0.22,
            "muscle": 0.3,
            "weight": 0.35,
            "proportions": 0.5,
            "height": 0.4,
            "cupsize": 0.0,
            "firmness": 0.5,
            "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
        },
        "skin_color": (0.76, 0.58, 0.46, 1.0),
    },
]

# Mixamo animation clips: (fbx_file, action_name)
ANIMATIONS = [
    ("Idle.fbx", "idle"),
    ("Walking.fbx", "walking"),
    ("Talking On Phone.fbx", "phone_ear_r"),
    ("Sitting Idle.fbx", "sitting"),
]


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=True)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:
        bpy.data.armatures.remove(block)
    for block in bpy.data.actions:
        bpy.data.actions.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)


def get_armature():
    """Find the armature in the scene."""
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    return None


def get_meshes():
    """Find all mesh objects in the scene."""
    return [obj for obj in bpy.data.objects if obj.type == "MESH"]


def measure_height():
    """Measure the height of all mesh objects in the scene."""
    min_z = float("inf")
    max_z = float("-inf")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            for v in obj.data.vertices:
                world_co = obj.matrix_world @ v.co
                min_z = min(min_z, world_co.z)
                max_z = max(max_z, world_co.z)
    return max_z - min_z


def join_meshes():
    """Join all meshes into a single object."""
    meshes = get_meshes()
    if len(meshes) <= 1:
        return meshes[0] if meshes else None

    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def triangulate_mesh(mesh_obj):
    """Ensure all faces are triangles."""
    bpy.context.view_layer.objects.active = mesh_obj
    mod = mesh_obj.modifiers.new("Triangulate", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=mod.name)


def recalculate_normals(mesh_obj):
    """Recalculate normals to point outward."""
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def apply_skin_material(mesh_obj, color):
    """Apply a simple PBR skin-tone material."""
    mat = bpy.data.materials.new(name="Skin")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.7
        bsdf.inputs["Metallic"].default_value = 0.0

    mesh_obj.data.materials.clear()
    mesh_obj.data.materials.append(mat)


def generate_makehuman_character(macro_dict):
    """Generate a MakeHuman character using MPFB2."""
    from mpfb.services.humanservice import HumanService
    from mpfb.services.targetservice import TargetService

    basemesh = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro_dict,
    )

    print(f"  Generated MakeHuman mesh: {len(basemesh.data.vertices)} vertices")

    # Use MPFB2's native Mixamo-compatible rig so imported Mixamo actions
    # can be transferred by remapping their bone-name prefix.
    armature = HumanService.add_builtin_rig(basemesh, "mixamo")
    print(f"  Added mixamo rig: {len(armature.data.bones)} bones")

    # Bake shape keys into clean geometry for export
    TargetService.bake_targets(basemesh)

    return basemesh, armature


def get_mixamo_prefix(armature):
    """Return the Mixamo-style bone prefix used by an armature."""
    for bone in armature.data.bones:
        if ":" not in bone.name:
            continue
        prefix, _ = bone.name.split(":", 1)
        if "mixamo" in prefix.lower():
            return prefix
    return None


def retarget_action_prefix(action, source_prefix, target_prefix):
    """Rewrite bone fcurve data paths from one Mixamo prefix to another."""
    source_token = f'pose.bones["{source_prefix}:'
    target_token = f'pose.bones["{target_prefix}:'

    for fcurve in action.fcurves:
        if source_token in fcurve.data_path:
            fcurve.data_path = fcurve.data_path.replace(source_token, target_token)


def force_quaternion_pose_mode(armature):
    """Set all pose bones to quaternion rotation for clean glTF export."""
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"


def import_animation(anim_fbx_path, action_name, target_armature):
    """Import a Mixamo animation FBX and transfer its action."""
    bpy.ops.import_scene.fbx(filepath=str(anim_fbx_path))

    # Find the newly imported armature
    anim_armature = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE" and obj != target_armature:
            anim_armature = obj
            break

    if anim_armature is None:
        print(f"  WARNING: No armature found in {anim_fbx_path}")
        return

    if anim_armature.animation_data and anim_armature.animation_data.action:
        action = anim_armature.animation_data.action
        source_prefix = get_mixamo_prefix(anim_armature)
        target_prefix = get_mixamo_prefix(target_armature)
        if source_prefix and target_prefix:
            retarget_action_prefix(action, source_prefix, target_prefix)
        else:
            print(
                "  WARNING: Could not determine Mixamo prefixes "
                f"(source={source_prefix}, target={target_prefix})"
            )
        action.name = action_name
        print(
            f"  Imported action '{action_name}': "
            f"frames {action.frame_range[0]:.0f}-{action.frame_range[1]:.0f}"
        )
    else:
        print(f"  WARNING: No action found in {anim_fbx_path}")

    # Delete the imported armature and its meshes (keep the action)
    bpy.ops.object.select_all(action="DESELECT")
    anim_armature.select_set(True)
    for obj in bpy.data.objects:
        if obj != target_armature and obj.type in ("ARMATURE", "MESH", "EMPTY"):
            if obj not in get_meshes() or obj.parent == anim_armature:
                obj.select_set(True)
    bpy.ops.object.delete()


def create_phone_ear_l(action_r_name="phone_ear_r"):
    """Create a mirrored phone-to-left-ear action from the right-ear one.

    Swaps Left/Right bone channels and negates X-location and Y/Z-rotation
    curves to produce a true mirror of the phone-to-right-ear animation.
    """
    src = bpy.data.actions.get(action_r_name)
    if src is None:
        print("  WARNING: Cannot mirror phone action, source not found")
        return

    dst = src.copy()
    dst.name = "phone_ear_l"

    for fcurve in dst.fcurves:
        dp = fcurve.data_path

        # Swap Left <-> Right bone names
        if "Left" in dp:
            fcurve.data_path = dp.replace("Left", "Right")
        elif "Right" in dp:
            fcurve.data_path = dp.replace("Right", "Left")

        # Mirror transform values
        idx = fcurve.array_index
        if "location" in fcurve.data_path and idx == 0:
            for kp in fcurve.keyframe_points:
                kp.co.y = -kp.co.y
                kp.handle_left.y = -kp.handle_left.y
                kp.handle_right.y = -kp.handle_right.y
        elif "rotation_euler" in fcurve.data_path and idx in (1, 2):
            for kp in fcurve.keyframe_points:
                kp.co.y = -kp.co.y
                kp.handle_left.y = -kp.handle_left.y
                kp.handle_right.y = -kp.handle_right.y
        elif "rotation_quaternion" in fcurve.data_path and idx in (2, 3):
            for kp in fcurve.keyframe_points:
                kp.co.y = -kp.co.y
                kp.handle_left.y = -kp.handle_left.y
                kp.handle_right.y = -kp.handle_right.y

    print(f"  Created mirrored action 'phone_ear_l' ({len(dst.fcurves)} fcurves)")


def build_character(char_def):
    """Build a single character GLB from MakeHuman + Mixamo animations."""
    name = char_def["name"]
    target_height = char_def["target_height_m"]

    print(f"\n{'='*60}")
    print(f"Building {name} (MakeHuman + Mixamo)")
    print(f"  Target: {target_height}m, {char_def['target_mass_kg']}kg")
    print(f"{'='*60}")

    clear_scene()

    # Generate MakeHuman character
    print("  Generating MakeHuman character...")
    mesh_obj, armature = generate_makehuman_character(char_def["macro"])
    force_quaternion_pose_mode(armature)

    # Join all meshes (MPFB2 may create helper meshes)
    print("  Joining meshes...")
    mesh_obj = join_meshes()
    if mesh_obj is None:
        print("  ERROR: No meshes found!")
        return

    # Scale to target height
    current_height = measure_height()
    if current_height > 0:
        scale_factor = target_height / current_height
        print(
            f"  Scaling: {current_height:.3f}m -> {target_height:.2f}m "
            f"(factor {scale_factor:.3f})"
        )
        armature.scale = (scale_factor, scale_factor, scale_factor)
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Triangulate
    print("  Triangulating...")
    triangulate_mesh(mesh_obj)

    # Recalculate normals
    print("  Recalculating normals...")
    recalculate_normals(mesh_obj)

    # Apply skin material
    print("  Applying skin material...")
    apply_skin_material(mesh_obj, char_def["skin_color"])

    n_faces = len(mesh_obj.data.polygons)
    print(f"  Mesh: {len(mesh_obj.data.vertices)} verts, {n_faces} faces")

    # Clear any actions from character generation
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

    # Import Mixamo animations
    for anim_fbx, action_name in ANIMATIONS:
        anim_path = PHANTOM_DIR / anim_fbx
        if anim_path.exists():
            print(f"  Loading animation: {anim_fbx} -> {action_name}")
            import_animation(anim_path, action_name, armature)
        else:
            print(f"  WARNING: Animation file not found: {anim_path}")

    # Create mirrored phone-to-left-ear
    create_phone_ear_l()

    # Assign idle as the default action
    idle_action = bpy.data.actions.get("idle")
    if idle_action:
        if armature.animation_data is None:
            armature.animation_data_create()
        armature.animation_data.action = idle_action

    # Push all actions to NLA tracks so they export
    if armature.animation_data is None:
        armature.animation_data_create()
    for action in bpy.data.actions:
        track = armature.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        strip.name = action.name

    # Export as GLB
    output_path = str(PHANTOM_DIR / f"{name}.glb")
    print(f"  Exporting to {output_path}")
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_animation_mode="ACTIONS",
        export_normals=True,
        export_materials="EXPORT",
        export_colors=False,
        export_yup=True,
    )

    file_size = os.path.getsize(output_path)
    n_actions = len(bpy.data.actions)
    print(f"  Done: {file_size / 1024:.0f} KB, {n_faces} faces, {n_actions} animations")


def main():
    for char_def in CHARACTERS:
        build_character(char_def)

    print("\n" + "=" * 60)
    print("All characters built!")
    print("=" * 60)
    for char_def in CHARACTERS:
        name = char_def["name"]
        p = PHANTOM_DIR / f"{name}.glb"
        if p.exists():
            print(f"  {name}.glb: {p.stat().st_size / 1024:.0f} KB")
        else:
            print(f"  {name}.glb: MISSING")


if __name__ == "__main__":
    main()
