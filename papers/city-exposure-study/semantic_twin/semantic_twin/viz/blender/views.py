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
            purpose="the rooftop angular power spectrum coupled to the body",
            camera="cam_lobe",
            layers=(PreparedLayer("Arrival shape", ("twin", "arrival")),),
        ),
        PreparedView(
            key="ranked_paths",
            name="04 VIEW - ranked recorded paths",
            purpose="one complete rooftop-weighted visual-trace sample per frame",
            camera="cam_rays",
            layers=(PreparedLayer("Ranked path", ("twin", "body", "path_animation", "cameras")),),
            frame_range_property="animation_path_frames",
        ),
        PreparedView(
            key="nee_explainer",
            name="05 VIEW - NEE explainer",
            purpose="one stored SBR chain and its qualitative roofline visibility connections per frame",
            camera="cam_rays",
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
            purpose="the final RF support classes beside the image evidence that proposed them",
            camera="cam_evidence",
            layers=(
                PreparedLayer("Final RF classes", ("twin",)),
                PreparedLayer("Semantic proposals", ("twin", "semantics")),
                PreparedLayer("Image coverage", ("twin", "evidence")),
                PreparedLayer("Refused evidence", ("twin", "refused")),
            ),
        ),
        PreparedView(
            key=PANORAMA_VIEW_KEY,
            name="07 VIEW - panorama registration",
            purpose="the registered source photograph, support holdout and one nearby registered capture marker",
            camera="cam_evidence",
            layers=(PreparedLayer("Registration", ("twin",)),),
        ),
        PreparedView(
            key="evidence_audit",
            name="08 VIEW - evidence audit",
            purpose="the image evidence and every surface decision kept separate",
            camera="cam_evidence",
            layers=(
                PreparedLayer("Semantic surfaces", ("twin", "semantics")),
                PreparedLayer("Image coverage", ("twin", "evidence")),
                PreparedLayer("Refused faces", ("twin", "refused")),
                PreparedLayer("Depth evidence", ("twin", "depth")),
            ),
        ),
    )


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
    for key in source.keys():
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
        "The displayed city mesh reaches 110 m. The transport used support out to 250 m.",
        "The rooftop source population is an analytic angular model. Its markers are not mapped transmitters.",
        "The NEE animation explains qualitative roofline visibility evidence. It supplies no production body dose.",
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
    import bpy

    raw_scene.name = RAW_SCENE_NAME
    raw_scene["prepared_view"] = False
    raw_scene["scene_role"] = "complete data archive; collections may start excluded in its view layer"

    available = tuple(groups)
    built: dict[str, Any] = {}
    specs = prepared_view_specs()
    for spec in specs:
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
        for layer_spec, layer in zip(spec.layers, view_layers, strict=True):
            excluded_collection_keys(layer_spec, available)
            _set_layer_visibility(layer, groups, layer_spec.show)

        camera = bpy.data.objects.get(spec.camera)
        if camera is None:
            raise RuntimeError(f"prepared scene {spec.name!r} has no camera {spec.camera!r}")
        made.camera = camera
        frame_start, frame_end = _frame_range(raw_scene, spec)
        made.frame_start = frame_start
        made.frame_end = frame_end
        made.frame_set(frame_start)
        _copy_timeline(raw_scene, made, frame_start, frame_end)
        made["prepared_view"] = True
        made["prepared_view_key"] = spec.key
        made["purpose"] = spec.purpose
        made["visibility_mechanism"] = "view-layer collection exclusion"
        made["shared_collection_datablocks"] = True
        made["visible_collections_by_view_layer"] = str({layer.name: list(layer.show) for layer in spec.layers})

        if spec.key == PANORAMA_VIEW_KEY:
            made["panorama_overlay_status"] = "hook not configured"
            if panorama_hook is not None:
                panorama_hook(made)
                made["panorama_overlay_status"] = "configured by panorama hook"
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
    made.render.resolution_x = int(made.render.resolution_x * resolution_scale)
    made.render.resolution_y = int(made.render.resolution_y * resolution_scale)
    if gpu:
        from .scene import use_gpu

        use_gpu()


def _render_prepared_layer(made: Any, layer: Any, path: Any) -> None:
    import bpy

    made.render.filepath = str(path)
    states = {other.name: other.use for other in made.view_layers}
    try:
        for other in made.view_layers:
            other.use = other == layer
        bpy.ops.render.render(write_still=True, scene=made.name, layer=layer.name)
    finally:
        for other in made.view_layers:
            other.use = states[other.name]


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
