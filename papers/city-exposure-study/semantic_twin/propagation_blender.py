"""Stage two of the propagation walkthrough: build the blend from the payload.

Everything in the scene is measured. The mesh is the support mesh the rays were
cast against, the ray polylines are the paths the estimator integrated, the lobe
is the angular power spectrum it accumulated, and the colours on the phantom are
the absorbed power density AEGIS returned for that spectrum. Nothing is drawn to
illustrate a number that was computed elsewhere.

The blend is deliberately austere. No textures, no packed images, no tile
imports, vertex colours only, and compression on. A textured 3D Tiles scene of
the same square is around ten times the size and says nothing about propagation,
so ``render_showcase.py`` remains the place to go for a photographic view.

Run it through headless Blender::

    ~/blender-4.5/blender --background --python propagation_blender.py -- \
        --payload outputs/propagation_viz/korenmarkt_payload.npz \
        --manifest outputs/propagation_viz/korenmarkt_manifest.json \
        --blend outputs/propagation_viz/korenmarkt_propagation.blend

Collections, and what each one answers:

``twin``       the geometry, tinted by the surface class that set its material
``rays``       five exclusive bundles of the recorded paths, thickness by throughput
``arrival``    the angular power spectrum at the hero standpoint, one lobe per model
``network``    the sources, on the facade tips, brightest where the flux comes from
``nee``        a few dozen rays with the connection each of them makes to a site
``walk``       every traced standpoint, coloured by its susceptibility
``body``       the phantom at the hero standpoint, coloured by absorbed power density
``semantics``  the fishnet surface sets, one per taxonomy, with their evidence
``evidence``   every support triangle a view considered, clean against withheld
``refused``    what the cutter threw away, one object per reason it was thrown
``depth``      the mesh first hit, and the monocular depth the gate refused
``panoramas``  the registered poses, their covariance and their sky conflict verdict
``bodies``     the SMPL-X bystanders the dynamic layer reconstructed and placed

The last six are only built when the payload carries them, and all of them start
hidden, so a site with no panorama opens exactly as it did before and a site with
one opens just as fast.

A layer is a named attribute, not an object. Every object in those collections
carries its measured quantities twice: once as a float or integer attribute
holding the exact value, which the spreadsheet editor will show, and once as a
colour attribute holding the shaded version. Switching what a surface shows is
therefore a click in the colour attribute list rather than a rebuild, and the
exact number survives next to the picture of it.

**This file is the runner and nothing else.** It was 2,116 lines and the largest
module in the study, and every line of its arithmetic was unreachable outside
Blender because line one was ``import bpy``. The work is now in
:mod:`semantic_twin.viz.blender`, split into what needs Blender and what does
not, and what does not has tests. What is left here is ``argparse`` and ``main``,
which is the rule the refactor applies everywhere: the package holds functions,
the top level holds the command line.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    # Blender runs this with its own interpreter and its own path, so the study
    # package has to be put there. Nothing in ``semantic_twin.viz.blender``
    # imports anything heavy at module scope, which is what makes that safe.
    sys.path.insert(0, str(ROOT))

from semantic_twin.viz.blender import estimator, evidence, renders, scene  # noqa: E402
from semantic_twin.viz.blender.style import MODEL_NAMES  # noqa: E402


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument("--walk-model", default="rooftop", choices=list(MODEL_NAMES))
    parser.add_argument("--lobe-scale-m", type=float, default=7.0)
    parser.add_argument("--lobe-offset-m", type=float, default=13.0)
    parser.add_argument("--lobe-floor", type=float, default=0.14)
    parser.add_argument("--ray-radius-m", type=float, default=0.11)
    parser.add_argument(
        "--rim-width-scale",
        type=float,
        default=0.04,
        help="Rim radius in metres per square root metre of slant range",
    )
    parser.add_argument(
        "--rim-site-step",
        type=int,
        default=10,
        help="One drawn site every this many azimuths. Ten of 720 is every five degrees",
    )
    parser.add_argument("--nee-ray-radius-m", type=float, default=0.09)
    parser.add_argument("--nee-line-radius-m", type=float, default=0.05)
    parser.add_argument(
        "--nee-sky-leg-m",
        type=float,
        default=30.0,
        help="Drawn length of the leg that left the scene, which in 09 runs to the sky sphere",
    )
    parser.add_argument("--point-radius-m", type=float, default=0.09, help="Drawn size of one depth cloud point")
    parser.add_argument(
        "--pose-sigma-scale",
        type=float,
        default=10.0,
        help="Life sizes the pose covariance ellipsoid is drawn at. One sigma here is centimetres",
    )
    parser.add_argument("--render-dir", type=pathlib.Path, help="Also render one PNG per camera")
    parser.add_argument(
        "--gpu", action="store_true", help="Render on the accelerator, and fail loudly if there is none"
    )
    parser.add_argument(
        "--figures",
        nargs="+",
        help="Render only the figures whose name starts with one of these, for iterating on one layer",
    )
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def main() -> int:
    import bpy

    args = arguments()
    payload = np.load(args.payload)
    manifest_path = args.manifest or args.payload.with_name(args.payload.name.replace("_payload.npz", "_manifest.json"))
    manifest = json.loads(manifest_path.read_text())

    scene.reset_scene()
    hero = payload["hero_point"].astype(np.float64)
    ground_z = float(payload["walk_ground_z_m"][int(payload["hero_index"])])

    twin = estimator.build_twin(payload, manifest["class_names"], scene.collection("twin"))
    rays = estimator.build_rays(
        payload, manifest["terminations"], scene.collection("rays"), base_radius=args.ray_radius_m
    )
    legs = estimator.build_ray_depth(payload, scene.collection("bounces"), base_radius=args.ray_radius_m)
    connections: dict[str, object] = {}
    if "nee_origin_m" in payload.files:
        connections = estimator.build_next_event(
            payload,
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
    walk_range = estimator.build_walk(payload, scene.collection("walk"), args.walk_model)
    sab_range = estimator.build_body(payload, hero, ground_z, scene.collection("body"))

    layers = evidence.build_all(
        payload,
        manifest,
        scene.collection,
        point_radius_m=args.point_radius_m,
        pose_sigma_scale=args.pose_sigma_scale,
    )

    cameras = scene.collection("cameras")
    scene.build_cameras(twin, hero, ground_z, cameras)
    scene.build_evidence_cameras(twin, payload, hero, ground_z, cameras)
    scene.build_lighting(hero)
    scene.hide_heavy_collections()
    scene.frame_the_viewport(twin, hero)

    scene.stamp_scene(
        manifest,
        rays=rays,
        legs=legs,
        connections=connections,
        layers=layers,
        root=ROOT,
    )

    args.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()), compress=True)

    if args.render_dir is not None:
        renders.render_every_figure(
            args.render_dir,
            args.blend.stem,
            samples=args.samples,
            resolution_scale=args.resolution_scale,
            gpu=args.gpu,
            only=args.figures,
        )

    print(f"[twin] {len(twin.data.polygons)} triangles inside {manifest['drawn_radius_m']:g} m", flush=True)
    print(f"[rays] {rays}", flush=True)
    print(f"[bounces] {legs}", flush=True)
    print(f"[arrival] peak rho per sr { {k: round(v, 5) for k, v in peaks.items()} }", flush=True)
    print(f"[network] {json.dumps(sources)}", flush=True)
    print(f"[nee] {json.dumps(connections)}", flush=True)
    print(f"[walk] chi range {walk_range[0]:.2f} to {walk_range[1]:.2f} dB", flush=True)
    print(f"[body] Sab {sab_range[0]:.4g} to {sab_range[1]:.4g} W/m2", flush=True)
    print(f"[evidence] {json.dumps(layers, default=str)}", flush=True)
    print(f"[done] {args.blend} ({args.blend.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
