"""The figure table for the walkthrough blend, and rendering it.

One figure names what it is about, not which camera took it. Every entry says
which collections are lit, which objects inside them are narrowed to, and which
colour layer each of those is shaded by. The saved blend keeps every collection it
built, so this table drives the renders and nothing else: switching a layer here
cannot change what is in the file.

Two skips are worth knowing about, and both were bugs that shipped. A figure whose
subject object the site never built used to render as a picture of the bare mesh,
which looks like the layer exists and is empty, and New York shipped two of those.
A figure that lights the mesh plus one empty overlay is a figure of the mesh, and
Krakow shipped that one. Both are refused with a line saying which site lacked what.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence

import bpy

from .payload import connection_render_layers
from .scene import BUILT, COLLECTION_NAMES, show_layer, use_gpu
from .style import MODEL_NAMES, RAY_STYLE

FIGURE_VIEWS: tuple[dict[str, object], ...] = (
    {"name": "01_the_square", "camera": "cam_overview", "show": ("twin",)},
    {
        # The band clouds are in this collection and are left out of every
        # figure that shows it. They are a shell of points in the air, they are
        # not where a base station is, and a picture captioned where the sources
        # are would be saying that they are.
        "name": "02_where_the_sources_are",
        "camera": "cam_overview",
        "show": ("twin", "network"),
        "hide": ("skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"skyline_rim": "direct_flux"},
    },
    {"name": "03_exposure_along_the_walk", "camera": "cam_overview", "show": ("twin", "walk")},
    {"name": "04_the_rays_from_one_standpoint", "camera": "cam_rays", "show": ("twin", "rays")},
    {"name": "05_standing_in_the_ray_fan", "camera": "cam_pedestrian", "show": ("twin", "rays")},
    {"name": "06_what_arrives", "camera": "cam_lobe", "show": ("twin", "arrival")},
    {"name": "07_the_body", "camera": "cam_body", "show": ("twin", "body")},
    {
        "name": "08_what_the_segmenter_said",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_vistas"),
        "layers": {"fishnet_vistas": "class"},
    },
    {
        "name": "09_how_sure_the_segmenter_was",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_vistas"),
        "layers": {"fishnet_vistas": "confidence"},
    },
    {
        # The cut surface alone, with the mesh switched off. Five sixths of the
        # faces are at zero entropy and render as black, so against the world
        # background this is a map of the mixed ones and nothing else, which is
        # the question. Photographed from above because the split faces are
        # scattered over all four crops and no ground level bearing sees them
        # all.
        "name": "10_where_the_posterior_is_split",
        "camera": "cam_overview",
        "show": ("semantics",),
        "objects": ("fishnet_vistas",),
        "layers": {"fishnet_vistas": "entropy_bits"},
    },
    {
        "name": "11_the_material_taxonomy",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_sam3"),
        "layers": {"fishnet_sam3": "class"},
    },
    {"name": "12_what_the_cutter_refused", "camera": "cam_evidence", "show": ("twin", "refused")},
    {
        "name": "13_clean_against_withheld",
        "camera": "cam_evidence",
        "show": ("twin", "evidence"),
        "layers": {"support_evidence": "withheld_fraction"},
    },
    {
        "name": "14_the_first_hit_the_twin_uses",
        "camera": "cam_evidence",
        "show": ("depth",),
        "objects": ("depth_mesh",),
        "layers": {"depth_mesh": "decision"},
    },
    {
        "name": "15_the_depth_the_gate_refused",
        "camera": "cam_evidence",
        "show": ("twin", "depth"),
        "objects": ("support_mesh", "depth_monocular"),
        "layers": {"depth_monocular": "decision"},
    },
    {"name": "16_where_the_panoramas_stand", "camera": "cam_registration", "show": ("twin", "panoramas")},
    {"name": "17_the_bystanders", "camera": "cam_bystanders", "show": ("twin", "bodies")},
    {"name": "18_how_deep_the_bounces_go", "camera": "cam_rays", "show": ("twin", "bounces")},
    {
        # The method itself. A few dozen rays leave the head and bounce, and
        # every vertex of them, the head included, throws one thin line at a
        # site sampled on the facade tip. The lines are the estimate. The rim is
        # shown with them because a connection has to be seen landing on
        # something, and the band clouds are hidden for the same reason as in
        # figure two.
        "name": "21_next_event_estimation",
        "camera": "cam_rays",
        "show": ("twin", "network", "nee", "body"),
        "hide": ("skyline_sites", "skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"estimator_connections": "visibility", "skyline_rim": "direct_flux"},
    },
    {
        # The same rim from where it matters. The overview shows that the sources
        # ring the standpoint, and this shows what the person under them sees:
        # the skyline, lit along the part of it that delivers.
        "name": "22_the_skyline_from_the_standpoint",
        "camera": "cam_pedestrian",
        "show": ("twin", "network"),
        "hide": ("skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"skyline_rim": "direct_flux"},
    },
    {
        # The same fan as figure four, shaded by the power each segment carries
        # rather than by what became of it. Thickness says the same thing, so
        # the two readings agree and the colour is the one you can put a number
        # against.
        "name": "20_how_much_power_each_ray_carries",
        "camera": "cam_rays",
        "show": ("twin", "rays"),
        "layers": dict.fromkeys(RAY_STYLE, "power_db"),
    },
    {
        "name": "19_everything_at_once",
        # Not from outside and not from overhead. The ray fan is a thousand
        # polylines through one point, so any camera aimed at that point turns
        # the whole frame into a starburst and nothing else in the scene
        # survives it. From the capture point the fan converges twenty metres
        # away and sits in a corner of the picture, which leaves the walls, the
        # cloud, the walk and the bystanders room to be seen next to it.
        "camera": "cam_evidence",
        "show": (
            "twin",
            "rays",
            "arrival",
            "network",
            "walk",
            "body",
            "semantics",
            "depth",
            "panoramas",
            "bodies",
        ),
        # Three things are left out of the everything shot and each is left out
        # for a reason that is not aesthetic. ``evidence`` and ``refused`` are
        # drawn on the same support triangles the semantics are cut from, so
        # showing them together is z fighting rather than information. The
        # monocular cloud is the surface the gate refused and putting it in a
        # picture captioned everything would say the twin uses it. ``bounces``
        # is the ray fan a second time, and the two taxonomies cover the same
        # walls as each other, so Vistas is shown and SAM 3 has figure 11.
        "hide": (
            "depth_monocular",
            "fishnet_sam3",
            "skyline_rim_beyond_the_drawn_mesh",
            *(f"sources_{name}" for name in MODEL_NAMES),
        ),
        "layers": {"fishnet_vistas": "class", "depth_mesh": "decision"},
    },
)


def render_every_figure(
    render_dir: pathlib.Path,
    blend_stem: str,
    *,
    samples: int = 64,
    resolution_scale: float = 1.0,
    gpu: bool = False,
    only: Sequence[str] | None = None,
) -> list[str]:
    """One PNG per entry in :data:`FIGURE_VIEWS` the scene can actually take.

    Renders happen after the blend is saved, so the shipped file is the one the
    figures came from and no render setting or visibility toggle leaks into it. A
    figure whose camera or objects the payload never produced is skipped rather than
    raising, because a site with no panorama still has twelve of them.

    Takes plain arguments rather than an ``argparse.Namespace``. The package holds
    functions and the top level holds the flags, so a caller that is not the command
    line can render a subset without building a namespace to satisfy a signature.
    """
    scene = bpy.context.scene
    if gpu:
        print(f"[render] {use_gpu()}", flush=True)
    scene.cycles.samples = samples
    scene.render.resolution_x = int(1920 * resolution_scale)
    scene.render.resolution_y = int(1080 * resolution_scale)
    scene.render.image_settings.file_format = "PNG"
    render_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for figure in FIGURE_VIEWS:
        name, camera = str(figure["name"]), str(figure["camera"])
        shown = tuple(figure["show"])
        if only is not None and not any(name.startswith(wanted) for wanted in only):
            continue
        lit = {COLLECTION_NAMES.get(key, key) for key in shown}
        layers = connection_render_layers(dict(figure.get("layers", {})), bpy.data.objects.keys())
        # A figure is about the object its layer entry names, and a site that never
        # built that object has nothing to say in that frame.
        subject = {obj_name for obj_name in layers if obj_name not in bpy.data.objects}
        if camera not in bpy.data.objects or subject:
            print(f"[render] skipped {name}, this site has no {', '.join(sorted(subject)) or camera}", flush=True)
            continue
        # The mesh is scenery in most of these, so a figure that shows the mesh and
        # one empty layer is a figure of the mesh.
        over = [key for key in shown if key != "twin"]
        if over and not any(BUILT[key].objects for key in over if key in BUILT):
            print(f"[render] skipped {name}, this site built none of {', '.join(over)}", flush=True)
            continue
        wanted = figure.get("objects")
        dropped = set(figure.get("hide", ()))
        for group in bpy.data.collections:
            group.hide_render = group.name not in lit
            for obj in group.objects:
                obj.hide_render = (
                    group.name not in lit or obj.name in dropped or (wanted is not None and obj.name not in wanted)
                )
        for obj_name, channel in layers.items():
            if obj_name in bpy.data.objects:
                show_layer(bpy.data.objects[obj_name], channel)
        scene.camera = bpy.data.objects[camera]
        path = (render_dir / f"{blend_stem}_{name}.png").resolve()
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(str(path))
        print(f"[render] {name} from {camera}", flush=True)
    return written
