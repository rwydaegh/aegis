"""Add an experimental agent fishnet to a production propagation blend."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import bpy
import numpy as np
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_twin.viz.blender import evidence  # noqa: E402
from semantic_twin.viz.blender.scene import attach_values  # noqa: E402


COLLECTION_NAME = "02H AI interpretation | experimental agent evidence"
SCENE_NAME = "13 VIEW - experimental AI interpretation"
OBJECT_NAME = "AI sees pale carved stone window lintels"

AGENT_PALETTE = (
    np.array(
        [
            [0, 0, 0],
            [190, 62, 47],
            [218, 202, 167],
            [255, 186, 73],
            [51, 173, 220],
            [40, 65, 91],
            [139, 91, 56],
            [232, 63, 142],
            [30, 30, 35],
            [190, 169, 132],
            [100, 190, 255],
            [245, 245, 245],
            [143, 111, 190],
            [105, 110, 118],
        ],
        dtype=np.float32,
    )
    / 255.0
)


class Payload(dict[str, np.ndarray]):
    """Small mapping with the NPZ interface used by the production builder."""

    @property
    def files(self) -> list[str]:
        return list(self)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fishnet", type=pathlib.Path, required=True)
    parser.add_argument("--comparison-report", type=pathlib.Path)
    parser.add_argument("--composition-report", type=pathlib.Path)
    parser.add_argument("--semantics-json", type=pathlib.Path)
    parser.add_argument("--prompt-file", type=pathlib.Path)
    parser.add_argument("--inventory-json", type=pathlib.Path)
    parser.add_argument("--source-image", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--render", type=pathlib.Path)
    parser.add_argument("--concept", default="pale carved stone decorative window lintel")
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def _entropy_bits(probability: np.ndarray) -> np.ndarray:
    probability = np.asarray(probability, dtype=np.float64)
    safe = np.where(probability > 0.0, probability, 1.0)
    return -(probability * np.log2(safe)).sum(axis=1)


def _payload(surface: Any, palette: np.ndarray) -> Payload:
    probability = np.asarray(surface["face_class_probability"])
    faces = np.asarray(surface["faces"], dtype=np.int32)
    return Payload(
        fishnet_sam3_vertices=np.asarray(surface["vertices"], dtype=np.float32),
        fishnet_sam3_faces=faces,
        fishnet_sam3_class=np.asarray(surface["face_class"], dtype=np.int16),
        fishnet_sam3_class_rgb=np.asarray(palette, dtype=np.float32),
        fishnet_sam3_confidence=np.asarray(surface["face_confidence"], dtype=np.float32),
        fishnet_sam3_top_probability=probability.max(axis=1).astype(np.float32),
        fishnet_sam3_entropy_bits=_entropy_bits(probability).astype(np.float32),
        fishnet_sam3_range_m=np.asarray(surface["face_depth"], dtype=np.float32),
        fishnet_sam3_visible_fraction=np.asarray(surface["face_visible_fraction"], dtype=np.float32),
        fishnet_sam3_area_m2=np.asarray(surface["face_area_m2"], dtype=np.float32),
        fishnet_sam3_solid_angle_sr=np.asarray(surface["face_solid_angle_sr"], dtype=np.float32),
        fishnet_sam3_pixel_support=np.asarray(surface["face_pixel_support"], dtype=np.int32),
        fishnet_sam3_view=np.zeros(faces.shape[0], dtype=np.int8),
    )


def _link_to_all_scenes(group: Any) -> None:
    for current in bpy.data.scenes:
        if group.name not in current.collection.children:
            current.collection.children.link(group)


def _look_at(camera: Any, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _taxonomy(path: pathlib.Path | None, concept: str) -> tuple[list[str], np.ndarray]:
    if path is None:
        names = ["unknown", concept]
        palette = np.array([[0.30, 0.30, 0.30], [0.02, 0.95, 0.38]], dtype=np.float32)
        return names, palette
    raw = json.loads(path.read_text())["entity_id2label"]
    upper = max(int(key) for key in raw)
    names = [raw.get(str(index), f"class {index}") for index in range(upper + 1)]
    if len(names) > len(AGENT_PALETTE):
        raise ValueError(f"agent palette has {len(AGENT_PALETTE)} entries for {len(names)} taxonomy states")
    return names, AGENT_PALETTE[: len(names)]


def _assign_class_materials(obj: Any, class_names: list[str], palette: np.ndarray, classes: np.ndarray) -> None:
    """Make categorical colours visible in Workbench and selectable by slot."""
    obj.data.materials.clear()
    for index, (name, rgb) in enumerate(zip(class_names, palette, strict=True)):
        material_name = f"AI {index:02d} | {name}"
        material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
        material.diffuse_color = (*[float(value) for value in rgb], 1.0)
        material.metallic = 0.0
        material.roughness = 0.65
        obj.data.materials.append(material)
    for polygon, class_id in zip(obj.data.polygons, classes, strict=True):
        polygon.material_index = int(class_id)


def _attach_inventory_physics(obj: Any, inventory: dict[str, Any] | None, classes: np.ndarray) -> None:
    if inventory is None:
        obj["rms_roughness_status"] = "not estimated in this segmentation-only probe"
        return
    records = {int(item["id"]): item for item in inventory["classes"]}
    roughness = np.array([records.get(int(value), {}).get("rms_roughness_mm", np.nan) for value in classes])
    roughness_confidence = np.array(
        [records.get(int(value), {}).get("roughness_confidence", np.nan) for value in classes]
    )
    correlation_length = np.array(
        [records.get(int(value), {}).get("correlation_length_mm", np.nan) for value in classes]
    )
    attach_values(obj, "value_rms_roughness_mm", roughness, "FACE")
    attach_values(obj, "value_roughness_confidence", roughness_confidence, "FACE")
    attach_values(obj, "value_correlation_length_mm", correlation_length, "FACE")
    obj["rf_material_by_class"] = json.dumps({str(key): value.get("itu_material") for key, value in records.items()})
    obj["rms_roughness_status"] = "agent proposal attached per face; not accepted into transport atlas"


def _make_review_scene(group: Any, camera_position: np.ndarray, target: np.ndarray, render: pathlib.Path | None) -> Any:
    old = bpy.data.scenes.get(SCENE_NAME)
    if old is not None:
        bpy.data.scenes.remove(old)
    review = bpy.data.scenes.new(SCENE_NAME)
    review["purpose"] = "Inspect experimental agent-proposed evidence against the real propagation support mesh"
    review["production_status"] = "not fused into the transport atlas"

    support = bpy.data.collections.get("01 city mesh")
    if support is not None:
        review.collection.children.link(support)
    review.collection.children.link(group)

    camera_data = bpy.data.cameras.new("cam_ai_interpretation")
    camera_data.lens = 55.0
    camera_data.sensor_width = 36.0
    camera_data.clip_start = 0.05
    camera_data.clip_end = 1000.0
    camera = bpy.data.objects.new("cam_ai_interpretation", camera_data)
    review.collection.objects.link(camera)
    camera.location = Vector(camera_position)
    _look_at(camera, Vector(target))
    review.camera = camera

    review.render.engine = "BLENDER_WORKBENCH"
    review.display.shading.light = "STUDIO"
    review.display.shading.color_type = "MATERIAL"
    review.display.shading.show_shadows = True
    review.display.shading.show_cavity = True
    review.display.shading.cavity_type = "WORLD"
    review.display.shading.background_type = "WORLD"
    review.display.shading.show_specular_highlight = False
    review.render.resolution_x = 1280
    review.render.resolution_y = 900
    review.render.resolution_percentage = 100
    review.render.image_settings.file_format = "PNG"
    review.view_settings.look = "AgX - Medium High Contrast"
    if review.world is None:
        review.world = bpy.data.worlds.new("AI interpretation world")
    review.world.color = (0.018, 0.021, 0.027)

    if render is not None:
        render.parent.mkdir(parents=True, exist_ok=True)
        review.render.filepath = str(render.resolve())
        with bpy.context.temp_override(scene=review):
            bpy.ops.render.render(write_still=True)
    return review


def main() -> int:
    args = arguments()
    comparison = json.loads(args.comparison_report.read_text()) if args.comparison_report else None
    composition = json.loads(args.composition_report.read_text()) if args.composition_report else None
    inventory_prompt = args.prompt_file.read_text() if args.prompt_file else "not supplied"
    inventory = json.loads(args.inventory_json.read_text()) if args.inventory_json else None
    class_names, palette = _taxonomy(args.semantics_json, args.concept)
    full_inventory = args.semantics_json is not None
    with np.load(args.fishnet) as surface:
        payload = _payload(surface, palette)
        camera_position = np.asarray(surface["camera_position"], dtype=np.float64)
        target = np.asarray(surface["face_centroid"], dtype=np.float64).mean(axis=0)
        source_triangle = np.asarray(surface["face_source_triangle"], dtype=np.int32)
        triangle_count = int(np.asarray(surface["faces"]).shape[0])
        surface_area_m2 = float(np.asarray(surface["face_area_m2"]).sum())
        group = bpy.data.collections.get(COLLECTION_NAME)
        if group is not None:
            for obj in list(group.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
        else:
            group = bpy.data.collections.new(COLLECTION_NAME)
        _link_to_all_scenes(group)

        manifest = {
            "evidence": {
                "fishnet_sam3": {
                    "class_names": class_names,
                    "views": ["h+00_315 crop rows 512:896, columns 1152:1536"],
                }
            }
        }
        made = evidence.build_fishnet(payload, manifest, "sam3", group)
        if made is None:
            raise RuntimeError("production fishnet builder did not create the AI layer")
        obj = next(iter(group.objects))
        object_name = "AI 13-state scene inventory" if full_inventory else OBJECT_NAME
        obj.name = object_name
        obj.data.name = object_name
        classes = np.asarray(surface["face_class"], dtype=np.int16)
        _assign_class_materials(obj, class_names, palette, classes)
        attach_values(obj, "value_source_triangle", source_triangle, "FACE")
        obj["prompt"] = (
            "free scene inventory followed by mutually exclusive dense composition" if full_inventory else args.concept
        )
        obj["source_image"] = str(args.source_image.resolve())
        obj["source_fishnet"] = str(args.fishnet.resolve())
        obj["layer_role"] = "what the AI currently thinks is present in this one image"
        obj["production_status"] = "experimental single-view evidence, not fused into current transport atlas"
        obj["transport_ready_geometry"] = True
        obj["used_by_current_production_run"] = False
        obj["pipeline"] = "free scene inventory -> SAM3 masks -> visibility gate -> fishnet cut -> atlas fusion"
        obj["hard_mask_note"] = "the dense draft composes SAM3 unions and deterministic residual evidence"
        present = set(int(value) for value in np.unique(classes))
        obj["class_ids_present"] = json.dumps(sorted(present))
        obj["class_ids_absent"] = json.dumps(sorted(set(range(len(class_names))) - present))
        if comparison is not None:
            obj["comparison_metrics"] = json.dumps(comparison["metrics_against_full_sam3_mask"])
            obj["mesh_eligible_metrics"] = json.dumps(comparison["metrics_against_mesh_eligible_sam3_mask"])
        if composition is not None:
            obj["image_coverage_excluding_unresolved"] = float(composition["covered_fraction_excluding_unresolved"])
        _attach_inventory_physics(obj, inventory, classes)
        obj.show_wire = False
        obj.show_all_edges = False
        obj.show_in_front = True
        obj.display.show_shadows = False
        modifier = obj.modifiers.new("2 mm display offset, exact mesh remains underneath", "DISPLACE")
        modifier.strength = 0.002
        modifier.mid_level = 0.0
        obj["display_offset_m"] = 0.002
        obj["display_offset_note"] = "reversible normal offset with no added faces; mesh datablock remains exact"

        group["description"] = (
            "Agent-proposed concepts projected through the same fishnet representation used by the digital twin. "
            "This collection is an experimental evidence layer until atlas fusion accepts it."
        )
        group["status"] = "experimental_13_state_fishnet" if full_inventory else "experimental_single_view"
        group["concepts"] = json.dumps(class_names)
        group["coverage_target_for_full_agent"] = 0.995
        group["current_surface_area_m2"] = surface_area_m2
        group["current_triangles"] = triangle_count

    text = bpy.data.texts.get("AI_INTERPRETATION_README") or bpy.data.texts.new("AI_INTERPRETATION_README")
    text.clear()
    text.write(
        "WHAT THIS LAYER IS\n"
        "==================\n"
        "This is experimental single-view AI evidence projected onto the real Korenmarkt support mesh.\n"
        "It uses the production FishnetSurface format and the production Blender fishnet builder.\n"
        "It is intentionally not fused into the final transport atlas yet.\n\n"
        f"Current interpretation: {'13-state agent inventory' if full_inventory else args.concept}\n"
        f"Current triangles: {triangle_count}\n"
        f"Current surface area: {surface_area_m2:.3f} m2\n"
        f"States present on mesh: {sorted(present)}\n"
        f"States without mesh geometry: {sorted(set(range(len(class_names))) - present)}\n\n"
        "PROMPT FOR THE FULL AGENT INVENTORY\n"
        "===================================\n" + inventory_prompt
    )
    if inventory is not None:
        inventory_text = bpy.data.texts.get("AI_SCENE_INVENTORY_PROPOSAL") or bpy.data.texts.new(
            "AI_SCENE_INVENTORY_PROPOSAL"
        )
        inventory_text.clear()
        inventory_text.write(json.dumps(inventory, indent=2) + "\n")
        group["inventory_status"] = "agent proposed and projected for review; not fused"
        group["inventory_classes"] = len(inventory["classes"])
        group["inventory_expected_coverage"] = float(inventory["coverage_audit"]["expected_coverage"])

    review = _make_review_scene(group, camera_position, target, args.render)
    bpy.context.window.scene = review
    bpy.context.view_layer.objects.active = next(iter(group.objects))
    next(iter(group.objects)).select_set(True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "collection": COLLECTION_NAME,
                "scene": SCENE_NAME,
                "object": object_name,
                "triangles": triangle_count,
                "surface_area_m2": surface_area_m2,
                "render": str(args.render) if args.render else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
