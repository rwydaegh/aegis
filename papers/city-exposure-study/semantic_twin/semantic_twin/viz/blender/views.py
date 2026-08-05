"""Prepared ways to read one propagation blend.

The data scene owns the objects. Prepared scenes link those same collections
and use view-layer exclusions to select a small, readable subject. No mesh,
curve, material or image datablock is copied by this module, and changing one
prepared view cannot change which collections another view renders. A panorama
hook may add its own display-only projection mesh to that scene.

The panorama scene is useful today as a registration view. A later panorama
camera and compositor can be installed through ``panorama_hook`` without
changing the scene or view-layer layout. The hook links the source image from
its recorded path. It does not pack the image into the blend.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

RAW_SCENE_NAME = "99 DATA - raw layers and audit"
PANORAMA_VIEW_KEY = "panorama_registration"


@dataclass(frozen=True)
class PreparedLayer:
    """One view layer and the collection keys it admits."""

    name: str
    show: tuple[str, ...]


@dataclass(frozen=True)
class PreparedView:
    """One scene prepared around a single question."""

    key: str
    name: str
    purpose: str
    camera: str
    layers: tuple[PreparedLayer, ...]
    frame_range_property: str | None = None
    requires_objects: tuple[str, ...] = ()


def prepared_view_specs() -> tuple[PreparedView, ...]:
    """The stable scenes saved in every propagation blend."""
    return (
        PreparedView(
            key="exposure_overview",
            name="01 VIEW - exposure overview",
            purpose="the traced walk in the city that produced its exposure values",
            camera="cam_walk",
            layers=(PreparedLayer("Exposure", ("twin", "walk")),),
        ),
        PreparedView(
            key="body_exposure",
            name="02 VIEW - body exposure at hero",
            purpose="absorbed power density on the body at the representative standpoint",
            camera="cam_body",
            layers=(PreparedLayer("Body exposure", ("twin", "body")),),
        ),
        PreparedView(
            key="arrival_shape",
            name="03 VIEW - arrival angular shape",
            purpose=(
                "rooftop angular power by direction from the receiver toward its apparent source, "
                "used as input to the body model"
            ),
            camera="cam_lobe",
            layers=(PreparedLayer("Arrival shape", ("twin", "arrival")),),
        ),
        PreparedView(
            key="ranked_paths",
            name="04 VIEW - ranked recorded paths",
            purpose="one complete rooftop-weighted visual-trace sample per frame",
            camera="cam_path_animation",
            layers=(PreparedLayer("Ranked path", ("twin", "body", "path_animation", "cameras")),),
            frame_range_property="animation_path_frames",
        ),
        PreparedView(
            key="nee_explainer",
            name="05 VIEW - NEE explainer",
            purpose="one stored SBR chain and its qualitative roofline visibility connections per frame",
            camera="cam_path_animation",
            layers=(
                PreparedLayer(
                    "NEE explanation",
                    ("twin", "body", "nee_animation"),
                ),
            ),
            frame_range_property="animation_nee_frames",
        ),
        PreparedView(
            key="material_binding",
            name="06 VIEW - material binding",
            purpose=(
                "the whole-face geometric fallback beside the joint hit-position atlas and legacy single-view evidence"
            ),
            camera="cam_evidence",
            layers=(
                PreparedLayer("Whole-face geometric fallback", ("twin",)),
                PreparedLayer("All-camera fused evidence", ("twin", "fused_semantics")),
                PreparedLayer("Legacy single-panorama fishnets", ("twin", "semantics")),
                PreparedLayer("Image coverage", ("twin", "evidence")),
                PreparedLayer("Refused evidence", ("twin", "refused")),
            ),
        ),
        PreparedView(
            key=PANORAMA_VIEW_KEY,
            name="07 VIEW - panorama registration",
            purpose="the registered source photograph and panorama capture poses, kept separate from exposure standpoints",
            camera="cam_evidence",
            layers=(
                PreparedLayer("Registered photograph", ("twin",)),
                PreparedLayer("Panorama capture poses", ("twin", "panoramas", "cameras")),
                PreparedLayer("Exposure standpoints", ("twin", "walk")),
            ),
        ),
        PreparedView(
            key="evidence_audit",
            name="08 VIEW - evidence audit",
            purpose="the image evidence and every surface decision kept separate",
            camera="cam_evidence",
            layers=(
                PreparedLayer("All-camera fused surface", ("twin", "fused_semantics")),
                PreparedLayer("Semantic surfaces", ("twin", "semantics")),
                PreparedLayer("Image coverage", ("twin", "evidence")),
                PreparedLayer("Refused faces", ("twin", "refused")),
                PreparedLayer("Depth evidence", ("twin", "depth")),
            ),
        ),
        PreparedView(
            key="full_support",
            name="09 VIEW - full traced support",
            purpose="the exact support mesh and its whole-face geometric fallback over the full transport crop",
            camera="cam_full_support",
            layers=(
                PreparedLayer("Full support", ("twin", "outer_support", "support_extent", "walk")),
                PreparedLayer("Inner geometric fallback", ("twin", "support_extent", "walk")),
            ),
        ),
        PreparedView(
            key="fused_surface",
            name="10 VIEW - all-camera fused surface",
            purpose="joint semantic and material evidence from every admitted panorama on the common support",
            camera="cam_evidence",
            layers=(
                PreparedLayer("Fused evidence", ("twin", "fused_semantics", "panoramas")),
                PreparedLayer("Whole-face geometric fallback", ("twin",)),
            ),
            requires_objects=("fused_semantics",),
        ),
    )


def available_view_specs(groups: Mapping[str, Any]) -> tuple[PreparedView, ...]:
    """Keep optional prepared views only when their evidence geometry exists."""
    specs = prepared_view_specs()
    available = set(groups)
    for spec in specs:
        missing = set(spec.requires_objects).difference(available)
        if missing:
            raise KeyError(f"prepared view {spec.name!r} requires unknown collections: {', '.join(sorted(missing))}")
    return tuple(spec for spec in specs if all(len(groups[key].objects) > 0 for key in spec.requires_objects))


def excluded_collection_keys(layer: PreparedLayer, available: Sequence[str]) -> tuple[str, ...]:
    """Collection keys excluded by one prepared layer, in source order."""
    known = set(available)
    unknown = set(layer.show).difference(known)
    if unknown:
        raise KeyError(f"prepared layer {layer.name!r} names unknown collections: {', '.join(sorted(unknown))}")
    shown = set(layer.show)
    return tuple(key for key in available if key not in shown)


def _copy_scene_settings(source: Any, target: Any) -> None:
    """Copy the small set of scene-owned settings used by this builder."""
    target.unit_settings.system = source.unit_settings.system
    target.unit_settings.scale_length = source.unit_settings.scale_length
    target.render.engine = source.render.engine
    target.render.resolution_x = source.render.resolution_x
    target.render.resolution_y = source.render.resolution_y
    target.render.resolution_percentage = source.render.resolution_percentage
    target.render.pixel_aspect_x = source.render.pixel_aspect_x
    target.render.pixel_aspect_y = source.render.pixel_aspect_y
    target.render.film_transparent = source.render.film_transparent
    target.render.fps = source.render.fps
    target.render.fps_base = source.render.fps_base
    target.render.image_settings.file_format = source.render.image_settings.file_format
    target.render.image_settings.color_mode = source.render.image_settings.color_mode
    target.render.image_settings.color_depth = source.render.image_settings.color_depth
    target.view_settings.view_transform = source.view_settings.view_transform
    target.view_settings.look = source.view_settings.look
    target.view_settings.exposure = source.view_settings.exposure
    target.view_settings.gamma = source.view_settings.gamma
    target.world = source.world
    if hasattr(source, "cycles") and hasattr(target, "cycles"):
        target.cycles.samples = source.cycles.samples


def _copy_scene_properties(source: Any, target: Any) -> None:
    existing = set(target.keys())
    for key in source.keys():  # noqa: SIM118 - Blender Scene does not implement __iter__
        if key in existing:
            continue
        value = source[key]
        # Blender owns structured groups such as ``cycles``. They are settings,
        # not provenance, and assigning one IDPropertyGroup to another scene is
        # forbidden. Custom array properties expose ``to_list`` and are safe to
        # copy as ordinary values.
        if hasattr(value, "to_dict"):
            continue
        if hasattr(value, "to_list"):
            value = value.to_list()
        target[key] = value


def _copy_root_objects(source: Any, target: Any) -> None:
    """Link scene-root objects such as the sun, without copying their data."""
    for obj in source.collection.objects:
        if obj.name not in target.collection.objects:
            target.collection.objects.link(obj)


def _set_layer_visibility(layer: Any, groups: Mapping[str, Any], shown: Sequence[str]) -> None:
    admitted = set(shown)
    for key, group in groups.items():
        linked = layer.layer_collection.children.get(group.name)
        if linked is None:
            raise RuntimeError(f"prepared scene has no linked collection {group.name!r}")
        linked.exclude = key not in admitted


def _copy_timeline(source: Any, target: Any, frame_start: int, frame_end: int) -> None:
    for marker in source.timeline_markers:
        if frame_start <= marker.frame <= frame_end:
            target.timeline_markers.new(marker.name, frame=marker.frame)


def _frame_range(source: Any, spec: PreparedView) -> tuple[int, int]:
    if spec.frame_range_property and spec.frame_range_property in source:
        values = list(source[spec.frame_range_property])
        if len(values) == 2 and int(values[1]) >= int(values[0]):
            return int(values[0]), int(values[1])
    return int(source.frame_start), int(source.frame_end)


def _write_start_here(raw_scene: Any, specs: Sequence[PreparedView]) -> None:
    import bpy

    text = bpy.data.texts.get("README_START_HERE") or bpy.data.texts.new("README_START_HERE")
    text.clear()
    lines = [
        "START HERE",
        "",
        "Open scene 01 for the exposure walk. The numbered VIEW scenes each answer one question.",
        "Scene 99 preserves every layer for audit work.",
        "",
        "Scientific scope",
        "",
        "Production exposure is the 200,000-ray GPU escape transport recorded in the production manifest.",
        "Displayed paths are a separate 1,200-ray visual retrace. They are samples, not a production MPC decomposition.",
        "Close views show the exact inner support and keep their original framing.",
        "On atlas runs, supported ray hits use the joint posterior at the hit position.",
        "The whole-face classes shown on the support are the geometric fallback.",
        "Scene 09 adds the exact muted outer support when the payload carries the full trace mesh.",
        "Its two rings mark the close-view and trace radii. They are reference markers, not propagation surfaces.",
        "The rooftop source population is an analytic angular model. Its markers are not mapped transmitters.",
        "The NEE animation explains qualitative roofline visibility evidence. It supplies no production body dose.",
        "Panorama capture poses and walk exposure standpoints are separate collections and separate view layers.",
        "The all-camera fused evidence and legacy single-panorama fishnets are also separate.",
        "Arrival lobes point from the receiver toward the apparent source, the reciprocal escape direction.",
        "Physical wave travel and the body coupler use the opposite vector, k_hat = -local_grid.",
        "",
        "Prepared scenes",
        "",
    ]
    lines.extend(f"{spec.name}: {spec.purpose}." for spec in specs)
    lines.extend(
        [
            f"{raw_scene.name}: complete data archive.",
            "",
            "Visibility is set with view-layer collection exclusions. The scientific collections share geometry datablocks.",
            "The panorama scene alone adds a display-only support overlay. It does not change production geometry.",
        ]
    )
    text.write("\n".join(lines) + "\n")


def _new_prepared_scene(raw_scene: Any, groups: Mapping[str, Any], spec: PreparedView) -> tuple[Any, list[Any]]:
    import bpy

    existing = bpy.data.scenes.get(spec.name)
    if existing is not None and existing != raw_scene:
        bpy.data.scenes.remove(existing)
    made = bpy.data.scenes.new(spec.name)
    _copy_scene_settings(raw_scene, made)
    _copy_scene_properties(raw_scene, made)
    _copy_root_objects(raw_scene, made)
    for group in groups.values():
        made.collection.children.link(group)

    first = made.view_layers[0]
    first.name = spec.layers[0].name
    view_layers = [first, *(made.view_layers.new(layer.name) for layer in spec.layers[1:])]
    available = tuple(groups)
    for layer_spec, layer in zip(spec.layers, view_layers, strict=True):
        excluded_collection_keys(layer_spec, available)
        _set_layer_visibility(layer, groups, layer_spec.show)
    return made, view_layers


def _set_prepared_camera_timeline(raw_scene: Any, made: Any, spec: PreparedView) -> None:
    import bpy

    camera = bpy.data.objects.get(spec.camera)
    if camera is None:
        raise RuntimeError(f"prepared scene {spec.name!r} has no camera {spec.camera!r}")
    made.camera = camera
    frame_start, frame_end = _frame_range(raw_scene, spec)
    made.frame_start = frame_start
    made.frame_end = frame_end
    made.frame_set(frame_start)
    _copy_timeline(raw_scene, made, frame_start, frame_end)


def _route_panorama_hook_collections(made: Any, view_layers: Sequence[Any], before_hook: set[str]) -> None:
    hook_groups = [group for group in made.collection.children if group.name not in before_hook]
    photograph_layer, capture_pose_layer = view_layers[:2]
    for group in hook_groups:
        marked = bool(group.get("panorama_overlay_collection", False))
        role = str(group.get("panorama_overlay_role", ""))
        admitted_layer = (
            capture_pose_layer if role == "registered acquisition cameras and projection planes" else photograph_layer
        )
        for layer in view_layers:
            linked = layer.layer_collection.children.get(group.name)
            if linked is None:
                raise RuntimeError(f"panorama hook collection {group.name!r} is not linked to its view layer")
            linked.exclude = not (marked and layer == admitted_layer)
    made["panorama_hook_collections"] = [group.name for group in hook_groups]
    made["panorama_overlay_collections"] = [
        group.name for group in hook_groups if bool(group.get("panorama_overlay_collection", False))
    ]


def _run_panorama_hook(
    made: Any,
    view_layers: Sequence[Any],
    panorama_hook: Callable[[Any], None] | None,
) -> None:
    made["panorama_overlay_status"] = "hook not configured"
    if panorama_hook is None:
        return
    before_hook = {group.name for group in made.collection.children}
    panorama_hook(made)
    made["panorama_overlay_status"] = "configured by panorama hook"
    _route_panorama_hook_collections(made, view_layers, before_hook)


def _stamp_prepared_view(made: Any, spec: PreparedView) -> None:
    made["prepared_view"] = True
    made["prepared_view_key"] = spec.key
    made["purpose"] = spec.purpose
    made["visibility_mechanism"] = "view-layer collection exclusion"
    made["shared_collection_datablocks"] = True
    made["visible_collections_by_view_layer"] = str({layer.name: list(layer.show) for layer in spec.layers})
    made["prepared_render_base_resolution_x"] = int(made.render.resolution_x)
    made["prepared_render_base_resolution_y"] = int(made.render.resolution_y)


def build_prepared_scenes(
    raw_scene: Any,
    groups: Mapping[str, Any],
    *,
    panorama_hook: Callable[[Any], None] | None = None,
) -> dict[str, Any]:
    """Build linked prepared scenes and leave the raw archive intact.

    ``panorama_hook`` is the extension point for an exact equirectangular
    camera, externally linked source image and compositor. It receives the
    already linked panorama scene and may replace its camera or node graph. The
    source image stays outside the blend and is never packed by this function.
    """
    raw_scene.name = RAW_SCENE_NAME
    raw_scene["prepared_view"] = False
    raw_scene["scene_role"] = "complete data archive; collections may start excluded in its view layer"

    built: dict[str, Any] = {}
    specs = available_view_specs(groups)
    for spec in specs:
        made, view_layers = _new_prepared_scene(raw_scene, groups, spec)
        _set_prepared_camera_timeline(raw_scene, made, spec)
        if spec.key == PANORAMA_VIEW_KEY:
            _run_panorama_hook(made, view_layers, panorama_hook)
        _stamp_prepared_view(made, spec)
        built[spec.key] = made

    _write_start_here(raw_scene, specs)
    return built


def set_default_scene(prepared: Mapping[str, Any], key: str = "exposure_overview") -> None:
    """Choose which prepared scene opens, after every scene has been built."""
    import bpy

    wanted = prepared[key]
    if bpy.context.window is not None:
        bpy.context.window.scene = wanted


def activate_raw_scene(raw_scene: Any, *, clear_root_exclusions: bool = False) -> None:
    """Return Blender to the archive before running legacy mutable renders.

    The raw scene starts with its heavy evidence collections excluded. Legacy
    figure rendering selects collections with render flags, so its root view
    layer must admit every collection first. Callers opt into that mutation
    only after saving the blend.
    """
    import bpy

    if bpy.context.window is not None:
        bpy.context.window.scene = raw_scene
    if clear_root_exclusions:
        for child in raw_scene.view_layers[0].layer_collection.children:
            child.exclude = False


def activate_prepared_scene(prepared: Mapping[str, Any], key: str, layer_name: str | None = None) -> Any:
    """Activate one prepared scene and, optionally, one of its audit layers."""
    import bpy

    made = prepared[key]
    if bpy.context.window is not None:
        bpy.context.window.scene = made
        if layer_name is not None:
            layer = made.view_layers.get(layer_name)
            if layer is None:
                raise KeyError(f"scene {made.name!r} has no view layer {layer_name!r}")
            bpy.context.window.view_layer = layer
    return made


def _configure_prepared_render(
    prepared: Mapping[str, Any],
    key: str,
    made: Any,
    *,
    samples: int | None,
    resolution_scale: float,
    gpu: bool,
) -> None:
    # Collections and animated objects are shared between scenes. Evaluating a
    # later prepared scene can therefore leave their global hide state at that
    # scene's frame. Activate this scene and evaluate its own first frame before
    # rendering, even on CPU.
    activate_prepared_scene(prepared, key)
    made.frame_set(made.frame_start)
    if samples is not None:
        made.cycles.samples = samples
    base_x = int(made.get("prepared_render_base_resolution_x", made.render.resolution_x))
    base_y = int(made.get("prepared_render_base_resolution_y", made.render.resolution_y))
    made.render.resolution_x = max(1, round(base_x * resolution_scale))
    made.render.resolution_y = max(1, round(base_y * resolution_scale))
    if gpu:
        from .scene import use_gpu

        use_gpu()


def _render_prepared_layer(made: Any, layer: Any, path: Any) -> None:
    import bpy

    window = bpy.context.window
    if window is None:
        raise RuntimeError("prepared rendering requires an active Blender window context")
    if layer.name not in made.view_layers:
        raise ValueError(f"view layer {layer.name!r} does not belong to scene {made.name!r}")

    original_path = made.render.filepath
    states = {other.name: other.use for other in made.view_layers}
    compositor = None
    compositor_layer = None
    node_name = made.get("panorama_compositor_render_layer_node")
    if node_name and made.use_nodes and made.node_tree is not None:
        compositor = made.node_tree.nodes.get(str(node_name))
        if compositor is None or not hasattr(compositor, "layer"):
            raise RuntimeError(f"panorama compositor render-layer node {node_name!r} is missing")
        compositor_layer = compositor.layer
    try:
        made.render.filepath = str(path)
        for other in made.view_layers:
            other.use = other == layer
        if compositor is not None:
            compositor.layer = layer.name
        window.scene = made
        window.view_layer = layer
        if bpy.context.scene != made or bpy.context.view_layer != layer:
            raise RuntimeError(f"could not activate scene {made.name!r} and view layer {layer.name!r}")
        # Shared animated objects are evaluated from the active window scene.
        # A ``scene=`` operator override does not provide that guarantee.
        bpy.ops.render.render(write_still=True)
    finally:
        made.render.filepath = original_path
        if compositor is not None:
            compositor.layer = compositor_layer
        for other in made.view_layers:
            other.use = states[other.name]


def render_prepared_frames(
    prepared: Mapping[str, Any],
    render_dir: Any,
    key: str,
    *,
    frames: Sequence[int] | None = None,
    layer_name: str | None = None,
    samples: int | None = None,
    resolution_scale: float = 1.0,
    gpu: bool = False,
) -> list[str]:
    """Render deterministic numbered frames from one prepared animation.

    The prepared scene is made active before each frame is evaluated. The
    caller's active scene and view layer, both scene frames, and the prepared
    render settings are restored before returning.
    """
    import bpy
    import pathlib

    if key not in prepared:
        raise KeyError(f"unknown prepared scene key {key!r}")
    if resolution_scale <= 0.0:
        raise ValueError("prepared render resolution scale must be positive")

    made = prepared[key]
    layer = made.view_layers.get(layer_name) if layer_name is not None else made.view_layers[0]
    if layer is None:
        raise KeyError(f"scene {made.name!r} has no view layer {layer_name!r}")
    selected = (
        tuple(range(int(made.frame_start), int(made.frame_end) + 1)) if frames is None else tuple(map(int, frames))
    )
    if not selected:
        return []
    if len(set(selected)) != len(selected):
        raise ValueError("prepared animation frames must be unique")
    outside = [frame for frame in selected if frame < made.frame_start or frame > made.frame_end]
    if outside:
        raise ValueError(
            f"prepared animation frames outside scene range {made.frame_start}:{made.frame_end}: {outside}"
        )

    window = bpy.context.window
    if window is None:
        raise RuntimeError("prepared rendering requires an active Blender window context")
    destination = pathlib.Path(render_dir)
    destination.mkdir(parents=True, exist_ok=True)
    previous_scene = window.scene
    previous_layer = window.view_layer
    previous_scene_frame = int(previous_scene.frame_current)
    made_frame = int(made.frame_current)
    render_state = {
        "filepath": made.render.filepath,
        "resolution_x": int(made.render.resolution_x),
        "resolution_y": int(made.render.resolution_y),
        "samples": int(made.cycles.samples) if hasattr(made, "cycles") else None,
    }
    written: list[str] = []
    try:
        _configure_prepared_render(
            prepared,
            key,
            made,
            samples=samples,
            resolution_scale=resolution_scale,
            gpu=gpu,
        )
        for frame in selected:
            # Activate before every frame. This matters because collections and
            # animated objects are shared by all prepared scenes.
            activate_prepared_scene(prepared, key, layer.name)
            made.frame_set(frame)
            if bpy.context.scene != made or bpy.context.view_layer != layer or made.frame_current != frame:
                raise RuntimeError(f"could not evaluate prepared scene {made.name!r} at frame {frame}")
            path = (destination / f"{key}_frame_{frame:04d}.png").resolve()
            _render_prepared_layer(made, layer, path)
            written.append(str(path))
    finally:
        made.render.filepath = render_state["filepath"]
        made.render.resolution_x = render_state["resolution_x"]
        made.render.resolution_y = render_state["resolution_y"]
        if render_state["samples"] is not None:
            made.cycles.samples = render_state["samples"]
        made.frame_set(made_frame)
        window.scene = previous_scene
        previous_scene.frame_set(previous_scene_frame)
        window.view_layer = previous_layer
    return written


def render_prepared_scenes(
    prepared: Mapping[str, Any],
    render_dir: Any,
    *,
    only: Sequence[str] | None = None,
    all_layers: bool = False,
    samples: int | None = None,
    resolution_scale: float = 1.0,
    gpu: bool = False,
) -> list[str]:
    """Render ready-to-read scene stills without changing archive visibility."""
    import pathlib

    if resolution_scale <= 0.0:
        raise ValueError("prepared render resolution scale must be positive")
    destination = pathlib.Path(render_dir)
    destination.mkdir(parents=True, exist_ok=True)
    allowed = set(only) if only is not None else None
    written: list[str] = []
    for key, made in prepared.items():
        if allowed is not None and key not in allowed:
            continue
        _configure_prepared_render(
            prepared,
            key,
            made,
            samples=samples,
            resolution_scale=resolution_scale,
            gpu=gpu,
        )
        layers = tuple(made.view_layers) if all_layers else (made.view_layers[0],)
        for layer in layers:
            suffix = f"_{layer.name.lower().replace(' ', '_')}" if all_layers else ""
            path = (destination / f"{key}{suffix}.png").resolve()
            _render_prepared_layer(made, layer, path)
            written.append(str(path))
    return written
