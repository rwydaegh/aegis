"""Build a propagation walkthrough blend from a sealed payload.

This is the reusable Blender orchestration layer for
``propagation_blender.py``.  The root script only adds the study directory to
``sys.path`` and delegates through ``semantic_twin.cli`` so the orchestration
can be imported and tested without starting Blender. Blender itself is imported
inside :func:`build_blend` only, never while this module is imported by ordinary
Python.
"""

from __future__ import annotations

import functools
import json
from typing import Any

import numpy as np


def build_blend(args: Any) -> int:
    """Build, prepare, save, and optionally render one propagation blend."""
    import bpy

    from . import animation, estimator, evidence, panorama, renders, scene, views
    from .payload import verify_bundle_identity

    asset_root = args.asset_root.resolve()
    manifest_path = args.manifest or args.payload.with_name(args.payload.name.replace("_payload.npz", "_manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    payload = np.load(args.payload)
    verify_bundle_identity(payload, manifest)

    scene.reset_scene()
    hero = payload["hero_point"].astype(np.float64)
    ground_z = float(payload["walk_ground_z_m"][int(payload["hero_index"])])

    twin = estimator.build_twin(payload, manifest["class_names"], scene.collection("twin"))
    support_summary = scene.build_support_display(
        payload,
        manifest,
        twin,
        scene.collection("outer_support"),
        scene.collection("support_extent"),
        ground_z_m=ground_z,
    )
    atlas_audit_groups = {
        key: scene.collection(key)
        for key in (
            "entity_semantics",
            "atlas_confidence",
            "atlas_camera_count",
            "atlas_observation_count",
            "transport_state",
            "transport_material",
            "transport_fallback",
            "vistas_contribution",
            "sam3_contribution",
            "source_contribution",
        )
    }
    fused_summary = scene.build_fused_semantic_surface(
        payload,
        manifest,
        scene.collection("fused_semantics"),
        audit_collections=atlas_audit_groups,
    )
    rays = estimator.build_rays(
        payload,
        manifest["terminations"],
        scene.collection("rays"),
        base_radius=args.ray_radius_m,
        drawn_radius_m=float(manifest["drawn_radius_m"]),
    )
    legs = estimator.build_ray_depth(
        payload,
        manifest["terminations"],
        scene.collection("bounces"),
        base_radius=args.ray_radius_m,
        drawn_radius_m=float(manifest["drawn_radius_m"]),
    )
    connections: dict[str, object] = {}
    if "nee_origin_m" in payload.files:
        connections = estimator.build_next_event(
            payload,
            manifest["terminations"],
            scene.collection("nee"),
            drawn_radius_m=float(manifest["drawn_radius_m"]),
            ray_radius=args.nee_ray_radius_m,
            line_radius=args.nee_line_radius_m,
            sky_leg_m=args.nee_sky_leg_m,
        )
    peaks = estimator.build_arrival(
        payload,
        hero,
        scene.collection("arrival"),
        scale_m=args.lobe_scale_m,
        offset_m=args.lobe_offset_m,
        floor=args.lobe_floor,
    )
    sources = estimator.build_network(
        payload,
        hero,
        manifest,
        scene.collection("network"),
        width_scale=args.rim_width_scale,
        site_step=args.rim_site_step,
    )
    walk_range = estimator.build_walk(
        payload,
        scene.collection("walk"),
        args.walk_model,
        manifest.get("walk_provenance"),
        hero_index=int(payload["hero_index"]),
    )
    sab_range = estimator.build_body(payload, hero, ground_z, scene.collection("body"))

    layers = evidence.build_all(
        payload,
        manifest,
        scene.collection,
        point_radius_m=args.point_radius_m,
        pose_sigma_scale=args.pose_sigma_scale,
    )
    layers["all_camera_fused_atlas"] = fused_summary
    layers["support_display"] = support_summary

    cameras = scene.collection("cameras")
    scene.build_cameras(twin, hero, ground_z, cameras)
    scene.build_walk_camera(
        twin,
        payload["walk_points"],
        cameras,
        aspect=bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y,
    )
    scene.build_evidence_cameras(twin, payload, hero, cameras)
    scene.build_full_support_camera(hero, float(manifest["traced_crop_radius_m"]), cameras)
    scene.build_lighting(hero)
    animation_summary = animation.build_path_animation(
        payload,
        manifest["terminations"],
        path_collection=scene.collection("path_animation"),
        nee_collection=scene.collection("nee_animation"),
        dense_ray_collection=scene.collection("rays"),
        dense_bounce_collection=scene.collection("bounces"),
        drawn_radius_m=float(manifest["drawn_radius_m"]),
        ranked_count=args.animation_paths,
        nee_count=args.animation_nee_paths,
        radius_m=1.45 * args.ray_radius_m,
        escaped_proxy_m=args.animation_escape_leg_m,
    )
    # Stamp collection status only after the late-built animation collections
    # contain their objects. Otherwise, the file says they are empty even while
    # their frames render correctly.
    scene.hide_heavy_collections()
    scene.frame_the_viewport(twin, hero)

    scene.stamp_scene(
        manifest,
        rays=rays,
        legs=legs,
        connections=connections,
        layers=layers,
        root=asset_root,
    )
    bpy.context.scene["support_display"] = json.dumps(support_summary)
    bpy.context.scene["all_camera_fused_atlas"] = json.dumps(fused_summary)

    raw_scene = bpy.context.scene
    panorama_asset = None
    panorama_hook = None
    panorama_scene_hooks = ()
    panorama_capture = panorama.default_panorama_capture(manifest, asset_root)
    if panorama_capture is not None:
        panorama_asset = panorama.select_panorama_asset(manifest, asset_root, capture=panorama_capture)
        panorama_hook = functools.partial(
            panorama.configure_panorama_scene,
            asset=panorama_asset,
            blend_path=args.blend,
            support_collection_name=scene.COLLECTION_NAMES["twin"],
        )
        panorama_scene_hooks = panorama.prepared_capture_scene_hooks(
            panorama_asset,
            blend_path=args.blend,
            support_collection_name=scene.COLLECTION_NAMES["twin"],
        )
    prepared = views.build_prepared_scenes(
        raw_scene,
        scene.BUILT,
        panorama_hook=panorama_hook,
        panorama_scene_hooks=panorama_scene_hooks,
        include_panorama_pipeline=panorama_asset is not None,
    )
    views.set_default_scene(prepared)

    args.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()), compress=True)

    if args.prepared_render_dir is not None:
        views.render_prepared_scenes(
            prepared,
            args.prepared_render_dir,
            all_layers=args.prepared_render_layers,
            samples=args.samples,
            resolution_scale=args.resolution_scale,
            gpu=args.gpu,
        )

    if args.render_dir is not None:
        # The legacy figure table mutates collection render flags and material
        # channels. Run it in the complete archive after the prepared default
        # has been saved, so no prepared scene inherits its view-layer state.
        views.activate_raw_scene(raw_scene, clear_root_exclusions=True)
        renders.render_every_figure(
            args.render_dir,
            args.blend.stem,
            samples=args.samples,
            resolution_scale=args.resolution_scale,
            gpu=args.gpu,
            only=args.figures,
        )

    print(f"[twin] {len(twin.data.polygons)} triangles inside {manifest['drawn_radius_m']:g} m", flush=True)
    print(f"[support] {json.dumps(support_summary)}", flush=True)
    print(f"[rays] {rays}", flush=True)
    print(f"[bounces] {legs}", flush=True)
    print(f"[arrival] peak rho per sr { {k: round(v, 5) for k, v in peaks.items()} }", flush=True)
    print(f"[network] {json.dumps(sources)}", flush=True)
    print(f"[nee] {json.dumps(connections)}", flush=True)
    print(f"[animation] {json.dumps(animation_summary)}", flush=True)
    if panorama_asset is not None:
        print(
            f"[panorama] linked {panorama_asset.provider} {panorama_asset.image_id}, "
            f"registration residual {panorama_asset.skyline_residual_deg:.3f} deg",
            flush=True,
        )
    print(f"[walk] chi range {walk_range[0]:.2f} to {walk_range[1]:.2f} dB", flush=True)
    print(f"[body] Sab {sab_range[0]:.4g} to {sab_range[1]:.4g} W/m2", flush=True)
    print(f"[evidence] {json.dumps(layers, default=str)}", flush=True)
    print(f"[done] {args.blend} ({args.blend.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


__all__ = ["build_blend"]
