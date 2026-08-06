"""Stage one of the propagation walkthrough blend: assemble and write a payload.

For a production-backed export, the walk, angular spectrum, and body exposure
come from the exact checked production files. One hero location also gets a
separate bounded host trace, normally 1,200 rays. Those polylines explain the
path geometry. They are not production MPCs and supply no exposure value. The
payload and manifest state this boundary and carry one shared checked identity.

Nothing above sees a photograph. The second half of this module collects what
does: the fishnet surface sets and their rejected tables, the mesh first hit and
the monocular depth the gate refused, the registered panorama poses with their
covariance, and the SMPL-X bystanders. Every one of those already exists under
``outputs`` and none of it reached the blend before. It is gathered here rather
than recomputed, so what the blend shows is the artifact the pipeline wrote, and
a site with no such artifact simply exports fewer layers. ``PAYLOAD.md`` lists
every array and what it means.

Run from the ``semantic_twin`` directory::

    python export_propagation_payload.py --site korenmarkt
    python export_propagation_payload.py --site newyork_timessquare --locations 60
    python export_propagation_payload.py --site krakow_rynek --no-evidence
    python export_propagation_payload.py --site tokyo_hachiko --rim-only
    python export_propagation_payload.py --production-stem korenmarkt_gpu_15ghz

Then hand the payload to Blender::

    ~/blender-4.5/blender --background --python propagation_blender.py -- \
        --payload outputs/propagation_viz/korenmarkt_payload.npz \
        --blend outputs/propagation_viz/korenmarkt_propagation.blend
"""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import time
from dataclasses import replace
from typing import Any

import numpy as np

from semantic_twin.exposure import BodyCoupler
from semantic_twin.exposure import study as exposure_study
from semantic_twin.exposure.execution import (
    PreparedScene,
    _array_sha256,
    _bind_materials,
    _face_source_area_fractions,
    _file_sha256,
)
from semantic_twin.exposure.reuse import (
    complete_output,
    same_models,
    same_output_generation,
    same_run_identity,
)
from semantic_twin.exposure.study import (
    MODELS,
    PHANTOM,
    PHANTOM_MASS_KG,
    REFERENCE_S0_W_M2,
    ground_datum,
    site_mesh,
)
from semantic_twin.illumination.roofline import silhouette as skyline
from semantic_twin.materials import CLASS_NAMES, Provenance, classify_faces, load_table
from semantic_twin.propagation import (
    TERMINATIONS,
    MitsubaGeometry,
    PathRecorder,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.runconfig import RunConfig
from semantic_twin.vision.surface_atlas import load_surface_atlas, sha256_file, to_surface_mesh
from semantic_twin.vision.provenance import (
    LEGACY_ADMISSION_GATE_VERSION,
    SKY_CONFLICT_INSIDE_GEOMETRY,
    SKY_CONFLICT_LARGE_MISMATCH,
    SKY_CONFLICT_UNKNOWN,
    AdmissionGate,
    Registration,
    Verdict,
)
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset
from semantic_twin.walk.site import site_walk

from .payload import ProductionData, read_production_data, stamp_bundle_identity, verify_bundle_identity

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[3]

CONFIG = SCRIPT_DIR / "config"
OUTPUT = SCRIPT_DIR / "outputs" / "propagation_viz"

#: The blend is meant to be opened on a laptop, so the shell that gets drawn is
#: smaller than the shell that gets traced. Occlusion at the far edge of a 250 m
#: crop changes the numbers and is why the crop is 250 m, but it is off camera
#: and carrying it would triple the file for nothing visible. The traced radius
#: is recorded in the payload so the blend can say which is which.
DEFAULT_DRAW_RADIUS_M = 110.0

# The roofline and visible-path arms explain geometry. The production escape
# run alone owns these numerical outputs.
NO_EXPOSURE_OUTPUT = ("rho", "body dose", "walk exposure")

# This atlas was accepted before admission manifests carried a version. Its
# exact manifest hash is the only unversioned input allowed to select v1.
SEALED_LEGACY_ADMISSION_MANIFESTS = {
    "80d8f0bb448d6677fc29c9c51e81036e9b54913d52f1480030095ac16f08d783",
}


def artifact_admission_gate(manifest: dict[str, Any]) -> AdmissionGate:
    """Select the gate recorded by an atlas, defaulting absent versions to v2."""
    atlas = manifest.get("surface_atlas")
    atlas = atlas if isinstance(atlas, dict) else {}
    admission = atlas.get("admission")
    admission = admission if isinstance(admission, dict) else None
    version = None if admission is None else admission.get("version")
    if version is not None:
        return AdmissionGate.from_dict(admission)

    manifest_record = atlas.get("manifest")
    manifest_sha256 = manifest_record.get("sha256") if isinstance(manifest_record, dict) else None
    transport = atlas.get("transport_binding")
    if not isinstance(transport, dict):
        transport = manifest.get("semantic_binding")
    if manifest_sha256 is None and isinstance(transport, dict):
        manifest_sha256 = transport.get("atlas_manifest_sha256")
    if manifest_sha256 in SEALED_LEGACY_ADMISSION_MANIFESTS:
        thresholds = admission or {}
        return AdmissionGate.legacy_v1(
            max_residual_deg=float(thresholds.get("max_residual_deg", 4.0)),
            max_sky_conflict=float(thresholds.get("max_sky_conflict", 0.5)),
            min_conflict_range_m=float(thresholds.get("min_conflict_range_m", 2.0)),
        )
    return AdmissionGate.from_dict(admission)


def stamp_surface_atlas_admission(manifest: dict[str, Any]) -> AdmissionGate:
    """Write the inferred gate and canonical camera cohort into an atlas record."""
    gate = artifact_admission_gate(manifest)
    atlas = manifest.get("surface_atlas")
    if not isinstance(atlas, dict):
        return gate
    camera_ids = atlas.get("camera_ids", [])
    if not isinstance(camera_ids, list) or any(not isinstance(value, str) or not value for value in camera_ids):
        raise ValueError("surface-atlas camera_ids must be a list of non-empty strings")
    if len(set(camera_ids)) != len(camera_ids):
        raise ValueError("surface-atlas camera_ids must be unique")
    atlas["admission"] = gate.as_dict()
    manifest["admitted_captures"] = list(camera_ids)
    return gate


#: Height above head, in metres, of each site population, read off the models
#: rather than restated here. MONOSTATIC_SBR.md section 2.7.
HEIGHT_BAND_M: dict[str, tuple[float, float]] = {
    name: model.height_band_m for name, model in MODELS.items() if model.height_band_m is not None
}

RANGE_BAND_M: dict[str, tuple[float, float]] = {
    name: model.range_band_m for name, model in MODELS.items() if model.range_band_m is not None
}


def network_markers(name: str, count: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Where the illumination model's sources sit, as points to draw.

    The model is a density on direction alone. It says how much power arrives
    from each elevation and nothing about range, because range was integrated
    out when it was derived, so drawing it needs the source geometry rather than
    the density. The only defensible choice is the geometry whose elevations
    reproduce the law the tracer actually integrates, and getting there took two
    corrections, of which the second reversed the first.

    Under the corrected law of section 2.7 the source population is simply the
    one the bands describe: heights uniform on the height band, drawn
    independently of position, and horizontal ranges uniform by area on the
    range band. That is what this function draws, and binning its elevations
    recovers `Q_S` to Poisson error.

    What it must not draw is the construction that reproduces the *uncorrected*
    `1/sin^3(el)` law, which is heights with density proportional to `h^2` and
    then ranges uniform by area inside `h*cot(el_max)` to `h*cot(el_min)`, each
    height getting its own annulus. That does reproduce `1/sin^3` exactly, and
    it was in this function until 2026-08-02, but the ranges it needs are 7.7 to
    803 m rather than 25 to 250 m, so it describes no deployment and it is not
    the population the bands name. ``tests/test_propagation.py`` pins it as
    rejected.

    Positions are relative to the observer's head, so the caller adds the
    standpoint.
    """
    if name not in HEIGHT_BAND_M:
        return {"positions": np.zeros((0, 3)), "height_band_m": np.zeros(2), "range_m": np.zeros(2)}
    low_h, high_h = HEIGHT_BAND_M[name]
    near, far = RANGE_BAND_M[name]

    height = rng.uniform(low_h, high_h, size=count)
    # Uniform areal density on the annulus is uniform in the squared radius.
    radius = np.sqrt(rng.uniform(near**2, far**2, size=count))
    azimuth = rng.uniform(0.0, 2.0 * np.pi, size=count)
    positions = np.column_stack([radius * np.cos(azimuth), radius * np.sin(azimuth), height])
    return {
        "positions": positions,
        "height_band_m": np.array([low_h, high_h]),
        "range_m": np.array([near, far]),
    }


#: The silhouette fan the rim is read off. 720 azimuths is half a degree, which
#: is 2 m of arc at 250 m, and 400 elevations is the grid ``measure_skyline.py``
#: checked at all eleven squares against an independently cast sky fraction,
#: agreeing to 0.037 at the worst square.
RIM_AZIMUTHS = 720
RIM_ELEVATIONS = 400


def facade_tip_rim(
    geometry: Any,
    standpoint: np.ndarray,
    *,
    azimuths: int = RIM_AZIMUTHS,
    elevations: int = RIM_ELEVATIONS,
) -> dict[str, Any]:
    """The skyline at one standpoint, and the direct flux each azimuth of it carries.

    A site sits on a facade tip, the top edge where a wall meets the sky, and
    there is no mast under it. So the source geometry is the skyline the
    pedestrian actually sees: one site per azimuth, at the elevation and the
    horizontal distance of the tip visible along that azimuth. The direct term
    is a mean over azimuth of ``cos^2(alpha) / d``, with no height band and no
    range band in it, because each azimuth holds one source distance rather than
    a distribution over one.

    The extraction is ``measure_skyline.skyline`` itself and not a copy of it,
    so what the blend draws is the silhouette the law was measured on.

    Offsets are relative to the standpoint, the way :func:`network_markers`
    returns them, so the caller adds it.
    """
    alpha, distance, found = skyline(geometry, standpoint, azimuths=azimuths, elevations=elevations)
    # Cell centres, matching the fan `skyline` casts. Half a cell of drift here
    # rotates the whole rim off the rooflines and nothing else in the pipeline
    # would say so, which is why ``tests/test_propagation_viz.py`` checks the two
    # against a silhouette whose answer is known in closed form.
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)

    good = found & np.isfinite(distance) & (distance > 0.0)
    reach = np.where(good, distance, 0.0)
    weight = np.zeros_like(alpha)
    weight[good] = np.cos(alpha[good]) ** 2 / distance[good]
    offset = np.column_stack(
        [reach * np.cos(azimuth), reach * np.sin(azimuth), reach * np.tan(np.where(good, alpha, 0.0))]
    )
    summary = {
        "law": "direct term proportional to the mean over azimuth of cos^2(alpha) / d",
        "azimuths": int(azimuths),
        "elevations": int(elevations),
        "direct_term": float(weight.mean()),
        "open_azimuth_fraction": float(1.0 - good.mean()),
        # The same sky the tracer measures by random casting, arrived at from the
        # silhouette instead. The two sit next to each other in the manifest and
        # disagreeing is the signal that the fan found a ceiling and not a tip.
        "sky_fraction_implied": float(np.mean((1.0 - np.sin(alpha)) / 2.0)),
        "alpha_deg_median": float(np.degrees(np.median(alpha[good]))) if good.any() else float("nan"),
        "distance_m_median": float(np.median(distance[good])) if good.any() else float("nan"),
        "distance_m_p95": float(np.percentile(distance[good], 95)) if good.any() else float("nan"),
        "weight_p05": float(np.percentile(weight[good], 5)) if good.any() else float("nan"),
        "weight_max": float(weight.max()) if weight.size else 0.0,
    }
    return {
        "offset": offset,
        "azimuth_rad": azimuth,
        "alpha_rad": np.where(good, alpha, 0.0),
        "distance_m": reach,
        "weight": weight,
        "found": good,
        "summary": summary,
    }


def next_event_connections(
    geometry: Any,
    path_vertices: np.ndarray,
    path_offsets: np.ndarray,
    rim: dict[str, Any],
    standpoint: np.ndarray,
    *,
    paths: int,
    seed: int,
) -> dict[str, Any]:
    """One shadow ray per scattering vertex, from the vertex to a sampled site.

    This is the step the estimator takes and the one a picture of a ray fan
    never shows. A ray leaves the head and bounces off the buildings, and at the
    head and again at every bounce it is connected to one site sampled on the
    facade tip. The connection is the contribution, and whether anything stands
    in the way of it is the whole of the visibility term.

    Measured, not drawn: every connection is cast against the same mesh the
    trace ran on. The head's connections come back clear by construction,
    because the tip is the silhouette from the head, and that is a check on the
    geometry rather than a result.

    Sites are sampled uniformly in azimuth, which is the source density the law
    assumes: one site per azimuth, no azimuth preferred. An estimator that
    importance samples the flux instead would draw the same picture with the
    lines crowded onto the near rooflines.

    The last vertex of a recorded path is where it left the scene rather than a
    surface it scattered off, so it gets no connection.
    """
    offsets = np.asarray(path_offsets, dtype=np.int64)
    vertices = np.asarray(path_vertices, dtype=np.float64)
    lengths = np.diff(offsets)
    tip = standpoint + rim["offset"]
    available = np.flatnonzero(rim["found"])
    rng = np.random.default_rng(seed)

    def empty(reason: str) -> dict[str, Any]:
        return {
            "path_index": np.zeros(0, dtype=np.int32),
            "vertex_index": np.zeros(0, dtype=np.int32),
            "origin": np.zeros((0, 3), dtype=np.float64),
            "site": np.zeros((0, 3), dtype=np.float64),
            "azimuth_index": np.zeros(0, dtype=np.int64),
            "weight": np.zeros(0, dtype=np.float64),
            "blocked": np.zeros(0, dtype=bool),
            "paths": np.zeros(0, dtype=np.int32),
            "summary": {
                "what_it_is": "no source connections; " + reason,
                "paths_drawn": 0,
                "connections": 0,
                "blocked_fraction": float("nan"),
                "blocked_fraction_from_the_head": float("nan"),
                "median_length_m": float("nan"),
                "surface_standoff_m": 0.02,
            },
        }

    if paths <= 0:
        return empty("zero paths were requested")
    if available.size == 0:
        return empty("no facade tips were found")
    if lengths.size == 0:
        return empty("no recorded paths were available")

    # Paths that bounced at least once, so the picture shows the connections a
    # ray makes after it has left the head and not only the fan from the head.
    pool = np.flatnonzero(lengths >= 3)
    if pool.size < paths:
        pool = np.arange(lengths.size)
    pick = np.unique(pool[np.linspace(0, pool.size - 1, min(paths, pool.size)).round().astype(int)])

    path_index, vertex_index, origin, azimuth = [], [], [], []
    for index in pick:
        start, stop = int(offsets[index]), int(offsets[index + 1])
        for step, point in enumerate(vertices[start : stop - 1]):
            path_index.append(int(index))
            vertex_index.append(step)
            origin.append(point)
            azimuth.append(int(rng.choice(available)))
    origin = np.asarray(origin, dtype=np.float64).reshape(-1, 3)
    azimuth = np.asarray(azimuth, dtype=np.int64)
    if origin.size == 0:
        return empty("recorded paths contain no connectable vertices")
    site = tip[azimuth]

    span = site - origin
    length = np.linalg.norm(span, axis=1)
    unit = span / np.maximum(length, 1.0e-12)[:, None]
    # Leave the surface before testing, or every connection from a bounce point
    # is blocked by the wall it bounced off. The far end has the same problem in
    # reverse: the tip is on the mesh, so the shadow ray hits it at its own
    # range and a bare hit flag would call every connection blocked.
    hit, distance, _, _ = geometry.intersect(origin + 0.02 * unit, unit)
    clearance = np.maximum(0.25, 0.01 * length)
    blocked = hit & (distance < length - clearance)
    return {
        "path_index": np.asarray(path_index, dtype=np.int32),
        "vertex_index": np.asarray(vertex_index, dtype=np.int32),
        "origin": origin,
        "site": site,
        "azimuth_index": azimuth,
        "weight": rim["weight"][azimuth],
        "blocked": blocked,
        "paths": pick.astype(np.int32),
        "summary": {
            "what_it_is": (
                "one shadow ray per scattering vertex, from the vertex to a site sampled "
                "uniformly in azimuth on the facade tip. Cast against the traced mesh."
            ),
            "paths_drawn": int(pick.size),
            "connections": int(length.size),
            "blocked_fraction": float(blocked.mean()) if length.size else float("nan"),
            "blocked_fraction_from_the_head": (
                float(blocked[np.asarray(vertex_index) == 0].mean()) if length.size else float("nan")
            ),
            "median_length_m": float(np.median(length)) if length.size else float("nan"),
            "surface_standoff_m": 0.02,
        },
    }


def store_rim(bundle: dict[str, Any], rim: dict[str, Any]) -> None:
    """Put the rim into a bundle, as six arrays and one block in the manifest."""
    bundle["payload"]["rim_offset_m"] = rim["offset"].astype(np.float32)
    bundle["payload"]["rim_azimuth_rad"] = rim["azimuth_rad"].astype(np.float32)
    bundle["payload"]["rim_alpha_rad"] = rim["alpha_rad"].astype(np.float32)
    bundle["payload"]["rim_distance_m"] = rim["distance_m"].astype(np.float32)
    bundle["payload"]["rim_weight"] = rim["weight"].astype(np.float32)
    bundle["payload"]["rim_found"] = rim["found"]
    bundle["manifest"]["hero"]["facade_tip_rim"] = rim["summary"]


def store_connections(bundle: dict[str, Any], connections: dict[str, Any]) -> None:
    """Put the next event connections into a bundle, as seven arrays and a block."""
    bundle["payload"]["nee_path_index"] = connections["path_index"]
    bundle["payload"]["nee_vertex_index"] = connections["vertex_index"]
    bundle["payload"]["nee_origin_m"] = connections["origin"].astype(np.float32)
    bundle["payload"]["nee_site_m"] = connections["site"].astype(np.float32)
    bundle["payload"]["nee_azimuth_index"] = connections["azimuth_index"].astype(np.int32)
    bundle["payload"]["nee_weight"] = connections["weight"].astype(np.float32)
    bundle["payload"]["nee_blocked"] = connections["blocked"]
    bundle["payload"]["nee_paths"] = connections["paths"]
    if "source_estimator_arm" in bundle["payload"]:
        bundle["manifest"]["hero"]["roofline_source_evidence"] = {
            **connections["summary"],
            "role": "source evidence only",
            "does_not_supply": list(NO_EXPOSURE_OUTPUT),
        }
    else:
        bundle["manifest"]["hero"]["next_event_estimation"] = connections["summary"]


def sphere_triangulation(grid: np.ndarray) -> np.ndarray:
    """Triangulate the direction grid, so the angular spectrum can be a surface.

    Done here rather than in the Blender stage because Blender ships its own
    Python without SciPy. The convex hull of points on a sphere is their
    Delaunay triangulation on that sphere, and the grid is a Fibonacci
    spiral, so the hull is well conditioned and no degenerate facet appears.
    """
    from scipy.spatial import ConvexHull

    hull = ConvexHull(np.asarray(grid, dtype=np.float64))
    simplices = hull.simplices
    # ConvexHull does not promise outward winding, so orient each facet by its
    # own centroid. A lobe lit from outside with inward normals reads as a hole.
    centroid = grid[simplices].mean(axis=1)
    a, b, c = grid[simplices[:, 0]], grid[simplices[:, 1]], grid[simplices[:, 2]]
    outward = np.einsum("ij,ij->i", np.cross(b - a, c - a), centroid) > 0.0
    return np.where(outward[:, None], simplices, simplices[:, ::-1])


def crop_for_drawing(
    vertices: np.ndarray, faces: np.ndarray, radius_m: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Faces whose centroid is inside ``radius_m``, reindexed to a compact vertex set."""
    centroid = vertices[faces].mean(axis=1)
    keep = np.linalg.norm(centroid[:, :2], axis=1) <= radius_m
    kept = faces[keep]
    used, remapped = np.unique(kept, return_inverse=True)
    return vertices[used], remapped.reshape(kept.shape), np.flatnonzero(keep)


def trace_site(args: Any) -> dict[str, Any]:
    started = time.perf_counter()
    mesh = site_mesh(args.site, args.crop_m)
    geometry = MitsubaGeometry(mesh, variant=args.variant)
    datum = ground_datum(geometry, radius_m=args.walk_radius_m)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, args.frequency_hz)
    print(f"{args.site}: {geometry.face_count} triangles, ground datum {datum:.3f} m", flush=True)

    config = TraceConfig(
        frequency_hz=args.frequency_hz,
        rays=args.rays,
        local_cells=args.local_cells,
        max_bounces=args.max_bounces,
        seed=args.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    if args.walk == "route":
        walk, provenance = site_walk(geometry, args.site, stride_m=args.walk_stride_m, path=args.walk_path)
        print(
            f"walk: capture route, {provenance['stations']} cameras over "
            f"{provenance['road_length_m']:.0f} m of street, {provenance['standpoints']} standpoints",
            flush=True,
        )
    else:
        walk = build_walk(geometry, ground_datum_m=datum, radius_m=args.walk_radius_m, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    coupler = BodyCoupler(PHANTOM, args.frequency_hz, body_mass_kg=PHANTOM_MASS_KG)

    scalars: list[dict[str, float]] = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, MODELS, ground_z_m=float(ground), seed=args.seed + index)
        row = result.scalars()
        for name in MODELS:
            body = coupler.couple(result.local_grid, result.rho[name], result.local_solid_angle, REFERENCE_S0_W_M2)
            row[f"{name}_peak_sab_w_m2"] = body.peak_sab_w_m2
            row[f"{name}_sar_wb_w_kg"] = body.sar_wb_w_kg
        scalars.append(row)
        if index % 10 == 0:
            print(f"  [{index + 1}/{picks.size}] chi_rooftop={row['chi_rooftop']:.4f}", flush=True)

    # The hero is the location whose rooftop susceptibility sits nearest the
    # median, so the rays drawn are a typical standpoint and not the best or
    # worst one in the set.
    rooftop = np.array([row["chi_rooftop"] for row in scalars])
    hero = int(np.argmin(np.abs(rooftop - np.median(rooftop))))
    print(f"hero location {hero}, chi_rooftop {rooftop[hero]:.4f} against median {np.median(rooftop):.4f}", flush=True)

    recorder = PathRecorder(capacity=args.paths, sky_distance_m=args.draw_radius_m * 1.6)
    hero_result = tracer.trace(
        points[hero], MODELS, ground_z_m=float(datums[hero]), seed=args.seed + hero, recorder=recorder
    )
    record = recorder.result()
    print(f"recorded {len(record)} paths, {record.vertices.shape[0]} vertices", flush=True)

    hero_body = {
        name: coupler.couple(
            hero_result.local_grid, hero_result.rho[name], hero_result.local_solid_angle, REFERENCE_S0_W_M2
        )
        for name in MODELS
    }
    body_sab = body_field(coupler, hero_result, "rooftop")

    rng = np.random.default_rng(args.seed)
    network = {name: network_markers(name, args.sources, rng) for name in MODELS}
    rim = facade_tip_rim(geometry, points[hero])
    print(
        f"rim: direct term {rim['summary']['direct_term']:.5f}, "
        f"tip {rim['summary']['alpha_deg_median']:.1f} deg up at "
        f"{rim['summary']['distance_m_median']:.1f} m, sky implied "
        f"{rim['summary']['sky_fraction_implied']:.4f} against {hero_result.sky_fraction:.4f} cast",
        flush=True,
    )

    vertices, faces, kept = crop_for_drawing(geometry.vertices, geometry.faces, args.draw_radius_m)
    print(f"drawing {faces.shape[0]} of {geometry.face_count} triangles inside {args.draw_radius_m:g} m", flush=True)

    payload: dict[str, Any] = {
        "mesh_vertices": vertices.astype(np.float32),
        "mesh_faces": faces.astype(np.int32),
        "mesh_face_class": face_class[kept].astype(np.int8),
        "walk_points": points.astype(np.float32),
        "walk_ground_z_m": datums.astype(np.float32),
        "path_vertices": record.vertices.astype(np.float32),
        "path_offsets": record.offsets.astype(np.int32),
        "path_throughput": record.throughput.astype(np.float32),
        "path_face_class": record.face_class.astype(np.int8),
        "path_exit_direction": record.exit_direction.astype(np.float32),
        "path_bounces": record.bounces.astype(np.int16),
        "path_termination": record.termination.astype(np.int8),
        "hero_index": np.array(hero),
        "hero_point": points[hero].astype(np.float32),
        "local_grid": hero_result.local_grid.astype(np.float32),
        "local_grid_faces": sphere_triangulation(hero_result.local_grid).astype(np.int32),
        "body_vertices": body_sab["vertices"].astype(np.float32),
        "body_faces": body_sab["faces"].astype(np.int32),
        "body_sab_w_m2": body_sab["sab"].astype(np.float32),
    }
    for name in MODELS:
        payload[f"rho_{name}"] = hero_result.rho[name].astype(np.float32)
        payload[f"walk_chi_{name}"] = np.array([row[f"chi_{name}"] for row in scalars], dtype=np.float32)
        payload[f"walk_peak_sab_{name}"] = np.array([row[f"{name}_peak_sab_w_m2"] for row in scalars], dtype=np.float32)
        payload[f"network_{name}"] = network[name]["positions"].astype(np.float32)

    manifest = {
        "site": args.site,
        "mesh": str(mesh.relative_to(SCRIPT_DIR)),
        "traced_crop_radius_m": args.crop_m,
        "drawn_radius_m": args.draw_radius_m,
        "traced_triangles": geometry.face_count,
        "drawn_triangles": int(faces.shape[0]),
        "ground_datum_m": datum,
        "frequency_hz": args.frequency_hz,
        "reference_s0_w_m2": REFERENCE_S0_W_M2,
        "class_names": list(CLASS_NAMES),
        "terminations": list(TERMINATIONS),
        "locations": int(picks.size),
        "walk_candidates": len(walk),
        # How the standpoints were chosen, written down so a blend can be told
        # apart from one built by the grid without opening it.
        "walk_provenance": {k: v for k, v in walk.provenance.items() if not isinstance(v, np.ndarray)},
        "trace_config": config.as_dict(),
        "surface_binding": binding.as_dict(),
        "hero": {
            "index": hero,
            "point_enu_m": points[hero].tolist(),
            "sky_fraction": hero_result.sky_fraction,
            "mean_bounces": hero_result.mean_bounces,
            "recorded_paths": len(record),
            "susceptibility": hero_result.susceptibility,
            "susceptibility_direct": hero_result.susceptibility_direct,
            "body": {name: value.as_dict() for name, value in hero_body.items()},
        },
        "walk_summary": {
            name: {
                "median_chi": float(np.median([row[f"chi_{name}"] for row in scalars])),
                "min_chi": float(np.min([row[f"chi_{name}"] for row in scalars])),
                "max_chi": float(np.max([row[f"chi_{name}"] for row in scalars])),
            }
            for name in MODELS
        },
        "network_height_band_m": {name: network[name]["height_band_m"].tolist() for name in MODELS},
        "seconds": time.perf_counter() - started,
        "storage_note": (
            "The path polylines here are a capped visualisation buffer, not a path table. "
            "The estimator itself still writes none, and PathRecorder is asserted to leave "
            "every traced number bit identical."
        ),
    }
    bundle = {"payload": payload, "manifest": manifest}
    store_rim(bundle, rim)
    connections = next_event_connections(
        geometry,
        record.vertices,
        record.offsets,
        rim,
        points[hero],
        paths=args.nee_paths,
        seed=args.seed,
    )
    store_connections(bundle, connections)
    print(
        f"connections: {connections['summary']['connections']} from "
        f"{connections['summary']['paths_drawn']} paths, "
        f"{connections['summary']['blocked_fraction']:.2f} blocked",
        flush=True,
    )
    return bundle


def load_production_run(files: Any) -> tuple[ProductionData, RunConfig]:
    """Load and prove the identity and completeness of one GPU exposure run."""
    data = read_production_data(files)
    run = _production_run_config(data)
    _validate_production_mode(data, run)
    return data, run


def _production_run_config(data: ProductionData) -> RunConfig:
    """Recover the run identity and validate the three output files together."""
    recorded = data.manifest.get("run")
    if not isinstance(recorded, dict):
        raise TypeError("production exposure manifest has no complete RunConfig record")
    try:
        run = RunConfig.from_dict(recorded)
    except (TypeError, ValueError) as error:
        raise ValueError("production exposure manifest has an invalid RunConfig record") from error
    if data.manifest.get("run_digest") != run.digest():
        raise ValueError("production exposure manifest run_digest does not match its RunConfig")
    if not complete_output(data.manifest, run, data.files.locations, data.files.spectra):
        raise ValueError("production exposure files are incomplete or their indices and shapes do not align")
    if not same_output_generation(data.manifest, data.files.locations, data.files.spectra):
        raise ValueError("production exposure files are not one sealed output generation")
    if not same_run_identity(data.manifest, run, MODELS) or not same_models(data.manifest, run, MODELS):
        raise ValueError("production exposure manifest does not match the recorded run or illumination models")
    if data.files.hashes() != data.input_identity:
        raise ValueError("production exposure files changed while they were being validated")
    return run


def _validate_production_mode(data: ProductionData, run: RunConfig) -> None:
    """Require the production algorithm and all redundant provenance to agree."""
    expected_trace = TraceConfig(
        frequency_hz=run.frequency_hz,
        rays=run.rays,
        local_cells=run.local_cells,
        exit_bands=run.exit_bands,
        max_bounces=run.max_bounces,
        roulette_start=run.effective_roulette_start,
        roulette_floor=run.roulette_floor,
        ray_epsilon_m=run.ray_epsilon_m,
        range_weighted_escape=run.range_weighted_escape,
        seed=run.seed,
        batch=run.batch,
    ).as_dict()
    if data.manifest.get("trace_config") != expected_trace:
        raise ValueError("production trace_config does not match its RunConfig")
    if data.manifest.get("site") != run.site:
        raise ValueError("production site does not match its RunConfig")
    if run.transport_kernel != "drjit" or run.variant != "cuda_ad_rgb":
        raise ValueError(
            "production visualization input must be a resident GPU run "
            f"(transport_kernel='drjit', variant='cuda_ad_rgb'); got {run.transport_kernel!r}, {run.variant!r}"
        )
    if run.estimator != "escape" or run.law != "band" or "rooftop" not in run.models:
        raise ValueError("production visualization input must contain the band-law rooftop escape estimator")
    transport = data.manifest.get("transport")
    if not isinstance(transport, dict) or transport.get("kernel") != "drjit":
        raise ValueError("production transport provenance does not identify the resident device kernel")
    semantic_binding = data.manifest.get("semantic_binding")
    face_digest = semantic_binding.get("face_class_sha256") if isinstance(semantic_binding, dict) else None
    if not isinstance(face_digest, str) or len(face_digest) != 64:
        raise ValueError("production semantic binding has no exact face-class SHA-256")
    mesh_digest = data.manifest.get("mesh_sha256")
    if not isinstance(mesh_digest, str) or len(mesh_digest) != 64:
        raise ValueError("production manifest has no exact source mesh SHA-256")
    if not isinstance(data.manifest.get("mesh"), str):
        raise TypeError("production manifest mesh must be a path string")
    reference_s0 = data.manifest.get("reference_s0_w_m2")
    if type(reference_s0) not in (int, float) or not np.isfinite(reference_s0) or reference_s0 <= 0.0:
        raise ValueError("production reference_s0_w_m2 must be a finite positive number")
    if not data.rows:
        raise ValueError("production visualization input contains no walk locations")


def _recorded_mesh(manifest: dict[str, Any]) -> pathlib.Path:
    path = pathlib.Path(manifest["mesh"])
    return path if path.is_absolute() else SCRIPT_DIR / path


def validate_face_class_digest(face_class: np.ndarray, manifest: dict[str, Any]) -> None:
    """Require the rebuilt material array to equal the production trace input."""
    recorded = manifest.get("semantic_binding", {}).get("face_class_sha256")
    if _array_sha256(face_class) != recorded:
        raise ValueError("current semantic face classes do not match the production exposure manifest")


def validate_face_source_digest(face_source: np.ndarray, manifest: dict[str, Any]) -> bool:
    """Validate per-face material provenance when the production run recorded it.

    Older production manifests predate ``face_source_sha256``. Their material
    source can still be rebuilt deterministically, but it cannot be claimed as
    byte-verified against the original run. The return value preserves that
    distinction in the visualization manifest.
    """
    recorded = manifest.get("semantic_binding", {}).get("face_source_sha256")
    if recorded is None:
        return False
    if _array_sha256(face_source) != recorded:
        raise ValueError("current per-face material sources do not match the production exposure manifest")
    return True


def validate_mesh_digest(mesh: pathlib.Path, manifest: dict[str, Any]) -> None:
    """Require the hero trace mesh bytes to equal the production trace input."""
    if _file_sha256(mesh) != manifest.get("mesh_sha256"):
        raise ValueError("current mesh bytes do not match the production exposure manifest")


def _production_scene(
    data: ProductionData,
    run: RunConfig,
    *,
    intersection_variant: str | None = None,
) -> tuple[Any, Any, Any, bool]:
    """Rebuild the exact mesh and material binding named by the production run."""
    mesh = _recorded_mesh(data.manifest)
    if not mesh.is_file():
        raise FileNotFoundError(f"production mesh does not exist: {mesh}")
    validate_mesh_digest(mesh, data.manifest)
    geometry = MitsubaGeometry(mesh, variant=intersection_variant or run.variant)
    datum = float(data.manifest["ground_datum_m"])
    geometric_class = classify_faces(geometry.vertices, geometry.faces, datum)
    scene = PreparedScene(
        mesh=mesh,
        geometry=geometry,
        datum=datum,
        datum_provenance=dict(data.manifest.get("ground_datum", {})),
        face_class=geometric_class,
        areas=geometry.face_areas(),
    )
    material = _bind_materials(run, scene, exposure_study._execution_environment())
    if material.table.as_dict() != data.manifest.get("surface_binding"):
        raise ValueError("current surface table does not match the production exposure manifest")
    recorded_binding = dict(data.manifest.get("semantic_binding", {}))
    for derived in (
        "face_class_sha256",
        "face_source_sha256",
        "face_source_labels",
        "face_source_area_fractions",
    ):
        recorded_binding.pop(derived, None)
    if material.provenance != recorded_binding:
        raise ValueError("current semantic face binding does not match the production exposure manifest")
    validate_face_class_digest(material.face_class, data.manifest)
    source_verified = validate_face_source_digest(material.face_source, data.manifest)
    recorded_source_fractions = data.manifest.get("semantic_binding", {}).get("face_source_area_fractions")
    current_source_fractions = _face_source_area_fractions(material.face_source, scene.areas)
    if recorded_source_fractions is not None and recorded_source_fractions != current_source_fractions:
        raise ValueError("current per-face material source areas do not match the production exposure manifest")
    return geometry, material, mesh, source_verified


def _body_from_row(row: dict[str, Any], model: str) -> dict[str, float]:
    prefix = f"{model}_"
    return {
        key.removeprefix(prefix): float(value)
        for key, value in row.items()
        if key.startswith(prefix)
        and key.removeprefix(prefix)
        in {
            "reference_s0_w_m2",
            "arriving_power_density_w_m2",
            "susceptibility",
            "peak_sab_w_m2",
            "mean_sab_w_m2",
            "absorbed_power_w",
            "sar_wb_w_kg",
        }
    }


def production_provenance(data: ProductionData, run: RunConfig) -> dict[str, Any]:
    """The exact source and estimator boundary stamped into a production blend."""
    transport = dict(data.manifest["transport"])
    transport["variant"] = run.variant
    return {
        "production_exposure": {
            "run_digest": run.digest(),
            "inputs": data.input_identity,
            "arrays": {
                "walk": "locations JSONL",
                "rho_rooftop": "spectra NPZ",
                "body_scalars": "locations JSONL",
                "body_surface_field": "recomputed by AEGIS from the stored rooftop rho",
            },
        },
        "estimator_arms": {
            "exposure": {
                "label": "GPU escape transport and rooftop body exposure",
                "estimator": "escape",
                "transport": transport,
                "produces": ["walk susceptibility", "rooftop rho", "body exposure"],
            },
            "source_evidence": {
                "label": "Roofline next-event and source evidence",
                "estimator": "next_event visualization evidence",
                "produces": ["facade-tip rim", "visible source connections"],
                "does_not_produce": list(NO_EXPOSURE_OUTPUT),
            },
        },
    }


def visible_path_config(config: TraceConfig, capacity: int) -> TraceConfig:
    """Trace only enough rays to fill the bounded visible-path buffer."""
    rays = min(config.rays, max(1, int(capacity)))
    return replace(config, rays=rays, batch=min(config.batch, rays))


def production_role_payload() -> dict[str, np.ndarray]:
    """Labels embedded only in a production-derived visualization payload."""
    return {
        "exposure_estimator_arm": np.array("GPU escape transport and rooftop body exposure"),
        "source_estimator_arm": np.array("Roofline next-event and source evidence"),
        "visible_path_role": np.array("bounded visualization trace only; supplies no exposure value"),
    }


SUPPORT_FALLBACK_FIELDS = (
    "support_full_vertices",
    "support_full_faces",
    "support_full_face_class",
    "support_full_face_source",
    "support_full_face_index",
)


def _array_manifest(array: np.ndarray) -> dict[str, Any]:
    """JSON-safe identity of one payload array."""
    value = np.asarray(array)
    return {
        "dtype": value.dtype.str,
        "shape": list(value.shape),
        "sha256": _array_sha256(value),
    }


def support_surface_fallback_manifest(
    payload: dict[str, Any],
    data: ProductionData,
    material: Any,
    areas: np.ndarray,
    *,
    source_verified: bool,
) -> dict[str, Any]:
    """Describe the whole-face fallback arrays sent to Blender.

    Atlas production runs resolve a material mixture at each ray hit. These
    per-face arrays remain useful as the geometric support and as the fallback
    for an unobserved or incompatible atlas texel. They are not a final
    hit-position material map.
    """
    semantic = dict(data.manifest.get("semantic_binding", {}))
    class_digest = _array_sha256(material.face_class)
    source_digest = _array_sha256(material.face_source)
    if class_digest != semantic.get("face_class_sha256"):
        raise ValueError("support-surface fallback class digest is not the production digest")
    return {
        "role": "whole-face geometric support and transport fallback",
        "is_final_hit_position_material_map": False,
        "fallback_rule": (
            "Used when the production material mode has no supported atlas texel at a hit. "
            "For non-atlas runs, these whole-face classes are the production binding."
        ),
        "mesh_sha256": data.manifest["mesh_sha256"],
        "face_class_sha256": class_digest,
        "face_source_sha256": source_digest,
        "face_source_production_verified": source_verified,
        "face_source_verification": (
            "matched production manifest"
            if source_verified
            else "rebuilt from the recorded deterministic binding; legacy production manifest has no source hash"
        ),
        "face_class_area_fractions": dict(data.manifest.get("class_area_fractions", {})),
        "face_source_area_fractions": _face_source_area_fractions(material.face_source, areas),
        "face_source_labels": {str(int(source)): source.name for source in Provenance},
        "face_index_rule": "zero-based triangle index in the exact production support mesh",
        "binding_provenance": {
            key: value
            for key, value in semantic.items()
            if key
            not in {
                "face_class_sha256",
                "face_source_sha256",
                "face_source_labels",
                "face_source_area_fractions",
            }
        },
        "payload_arrays": {name: _array_manifest(payload[name]) for name in SUPPORT_FALLBACK_FIELDS},
    }


def _atlas_path(run: RunConfig, material: Any) -> pathlib.Path:
    """Resolve the exact atlas path already named by the production binding."""
    recorded = getattr(material.atlas_material, "provenance", {}).get("atlas_npz")
    candidate = run.atlas_npz or recorded
    if not isinstance(candidate, str) or not candidate:
        raise ValueError("atlas production run does not identify its atlas NPZ")
    path = pathlib.Path(candidate)
    if path.is_absolute():
        return path
    local = pathlib.Path.cwd() / path
    return local if local.exists() else SCRIPT_DIR / path


ATLAS_TRANSPORT_STATE_NAMES = (
    "atlas_interface",
    "nonblocking_woody_vegetation",
    "geometric_fallback",
)


def atlas_transport_audit_arrays(
    audit: dict[str, np.ndarray],
    atlas: Any,
    binding: Any,
    geometric_class: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Map the production hit-position decision onto every audit triangle.

    The audit mesh can use two triangles for one clipped atlas cell. The
    returned arrays therefore have one row per audit triangle, while the count
    summary deduplicates by ``atlas_sparse_cell`` and matches the production
    transport manifest's cell counts.
    """
    required = (
        "atlas_source_triangle",
        "atlas_sparse_cell",
        "atlas_texel_row",
        "atlas_texel_column",
    )
    if missing := [name for name in required if name not in audit]:
        raise ValueError(f"atlas audit mesh is missing transport indices: {missing}")
    source = np.asarray(audit["atlas_source_triangle"], dtype=np.int64)
    sparse = np.asarray(audit["atlas_sparse_cell"], dtype=np.int64)
    texel_row = np.asarray(audit["atlas_texel_row"], dtype=np.int64)
    texel_column = np.asarray(audit["atlas_texel_column"], dtype=np.int64)
    count = source.size
    if any(values.shape != (count,) for values in (sparse, texel_row, texel_column)):
        raise ValueError("atlas audit transport indices must have one value per audit triangle")

    face_to_row = np.asarray(binding.face_to_atlas_row, dtype=np.int64)
    fallback = np.asarray(geometric_class)
    if fallback.shape != face_to_row.shape:
        raise ValueError("geometric fallback classes must match the production support faces")
    if count and (source.min() < 0 or source.max() >= face_to_row.size):
        raise ValueError("atlas audit source triangles leave the production support mesh")
    row = face_to_row[source]
    if np.any(row < 0):
        raise ValueError("an observed atlas audit triangle maps to a support face with no atlas row")

    supported_dense = np.asarray(binding.supported, dtype=bool)
    nonblocking_dense = np.asarray(binding.nonblocking, dtype=bool)
    probability_dense = np.asarray(binding.material_probability, dtype=np.float32)
    if probability_dense.ndim != 4 or supported_dense.shape != probability_dense.shape[:3]:
        raise ValueError("production atlas material probabilities and support mask disagree")
    if nonblocking_dense.shape != supported_dense.shape:
        raise ValueError("production atlas nonblocking and support masks disagree")
    height, width = supported_dense.shape[1:]
    if count and (
        np.any((texel_row < 0) | (texel_row >= height)) or np.any((texel_column < 0) | (texel_column >= width))
    ):
        raise ValueError("atlas audit texel indices leave the production binding resolution")

    supported = supported_dense[row, texel_row, texel_column]
    nonblocking = nonblocking_dense[row, texel_row, texel_column]
    if np.any(supported & nonblocking):
        raise ValueError("an atlas audit cell cannot be both an interface and nonblocking")
    probability = probability_dense[row, texel_row, texel_column]
    state = np.full(count, 2, dtype=np.int8)
    state[nonblocking] = 1
    state[supported] = 0
    dominant = np.full(count, -1, dtype=np.int16)
    if np.any(supported):
        dominant[supported] = np.argmax(probability[supported], axis=1).astype(np.int16)

    atlas_source_mask = np.asarray(atlas.source_mask)
    prior_weight = np.asarray(atlas.prior_weight, dtype=np.float32)
    concept_weight = np.asarray(atlas.concept_weight, dtype=np.float32)
    if any(values.ndim != 1 for values in (atlas_source_mask, prior_weight, concept_weight)):
        raise ValueError("surface-atlas source contribution arrays must be one-dimensional")
    if not (atlas_source_mask.size == prior_weight.size == concept_weight.size):
        raise ValueError("surface-atlas source contribution arrays disagree on cell count")
    if count and (sparse.min() < 0 or sparse.max() >= atlas_source_mask.size):
        raise ValueError("atlas audit sparse-cell indices leave the canonical atlas")

    unique_cells, first, inverse = np.unique(
        sparse,
        return_index=True,
        return_inverse=True,
    )
    unique_state = state[first]
    if np.any(state != unique_state[inverse]):
        raise ValueError("triangles from one atlas cell disagree on final transport state")
    counts = {
        name: int(np.count_nonzero(unique_state == code)) for code, name in enumerate(ATLAS_TRANSPORT_STATE_NAMES)
    }
    arrays = {
        "atlas_transport_state": state,
        "atlas_transport_material": dominant,
        "atlas_transport_probabilities": probability.astype(np.float32, copy=False),
        "atlas_geometric_fallback_class": fallback[source].astype(np.int16, copy=False),
        "atlas_source_mask": atlas_source_mask[sparse].astype(np.uint8, copy=False),
        "atlas_vistas_prior_weight": prior_weight[sparse],
        "atlas_sam3_concept_weight": concept_weight[sparse],
    }
    return arrays, counts


def attach_production_surface_atlas(
    payload: dict[str, Any],
    manifest: dict[str, Any],
    data: ProductionData,
    run: RunConfig,
    material: Any,
    geometry: Any,
) -> None:
    """Bridge the run's verified atlas artifact into its Blender payload."""
    if material.atlas_material is None:
        return
    npz_path = _atlas_path(run, material)
    json_path = npz_path.with_suffix(".json")
    if not npz_path.is_file() or not json_path.is_file():
        raise FileNotFoundError(f"production atlas needs its NPZ and sibling JSON: {npz_path}")

    semantic = dict(data.manifest.get("semantic_binding", {}))
    expected_npz_sha256 = semantic.get("atlas_npz_sha256")
    if not isinstance(expected_npz_sha256, str) or len(expected_npz_sha256) != 64:
        raise ValueError("atlas production binding does not record the exact atlas NPZ SHA-256")
    actual_npz_sha256 = sha256_file(npz_path)
    if expected_npz_sha256 != actual_npz_sha256:
        raise ValueError("surface atlas NPZ differs from the production material binding")

    atlas = load_surface_atlas(
        npz_path,
        json_path,
        expected_mesh_sha256=data.manifest["mesh_sha256"],
    )
    document = json.loads(json_path.read_text(encoding="utf-8"))
    manifest_sha256 = sha256_file(json_path)
    admission_gate = artifact_admission_gate(
        {
            "surface_atlas": {
                "admission": document.get("admission"),
                "manifest": {"sha256": manifest_sha256},
            }
        }
    )
    audit = to_surface_mesh(atlas, geometry.vertices, geometry.faces)
    arrays = audit.as_arrays()

    transport = dict(material.atlas_material.provenance)
    decision_arrays, state_counts = atlas_transport_audit_arrays(
        arrays,
        atlas,
        material.atlas_material,
        material.face_class,
    )
    arrays.update(decision_arrays)
    expected_state_counts = transport.get("transport_states")
    if expected_state_counts is not None and dict(expected_state_counts) != state_counts:
        raise ValueError("surface-atlas audit transport-state counts do not match the production material binding")
    payload.update(arrays)
    record = {
        "role": (
            "joint all-camera semantic and material evidence used by production transport. At each ray hit, "
            "transport derives the host-compatible material posterior from this atlas."
        ),
        "display_role": (
            "triangulated audit view of observed atlas cells; display winners do not replace the stored posteriors"
        ),
        "npz": {"path": str(npz_path.resolve()), "sha256": actual_npz_sha256},
        "manifest": {"path": str(json_path.resolve()), "sha256": manifest_sha256},
        "admission": admission_gate.as_dict(),
        "content_sha256": atlas.content_digest(),
        "mesh_sha256": atlas.mesh_sha256,
        "resolution": atlas.atlas_resolution,
        "observed_triangle_count": atlas.observed_triangle_count,
        "sparse_texel_count": atlas.cell_count,
        "camera_ids": [str(value) for value in atlas.station_ids],
        "cameras": list(document.get("cameras", [])),
        "vocabularies": dict(document.get("vocabularies", {})),
        "transport_binding": transport,
        "transport_audit": {
            "state_names": list(ATLAS_TRANSPORT_STATE_NAMES),
            "state_cell_counts": state_counts,
            "material_names": list(material.atlas_material.material_names),
            "source_mask_names": {
                "1": "Vistas prior only",
                "2": "SAM 3 concept only",
                "3": "Vistas prior and SAM 3 concept",
            },
            "role": (
                "exact production interface, nonblocking vegetation, or geometric fallback decision per atlas cell"
            ),
        },
        "payload_arrays": {name: _array_manifest(value) for name, value in arrays.items()},
    }
    manifest["surface_atlas"] = record
    stamp_surface_atlas_admission(manifest)
    # The scene builder uses this narrow key for object provenance. Keep it an
    # explicit reference to the canonical record rather than a second contract.
    manifest["all_camera_fused_atlas"] = {
        "record": "surface_atlas",
        "content_sha256": record["content_sha256"],
        "mesh_sha256": record["mesh_sha256"],
        "display_role": record["display_role"],
    }


def trace_production_site(args: Any, data: ProductionData, run: RunConfig) -> dict[str, Any]:
    """Combine production exposure results with one bounded display-only trace."""
    started = time.perf_counter()
    geometry, material, mesh, source_verified = _production_scene(
        data,
        run,
        intersection_variant=args.variant,
    )
    rows = data.rows
    points = np.array([[row[axis] for axis in ("x", "y", "z")] for row in rows], dtype=np.float64)
    datums = np.array([row["ground_z_m"] for row in rows], dtype=np.float64)
    rooftop = np.array([row["chi_rooftop"] for row in rows], dtype=np.float64)
    hero = int(np.argmin(np.abs(rooftop - np.median(rooftop))))
    walk_index = int(data.index[hero])
    hero_seed = run.seed + 1000 * walk_index

    # This trace supplies only the bounded ray polylines. Every exposure number,
    # angular spectrum and body value below is loaded from the production files.
    config = TraceConfig(**data.manifest["trace_config"])
    visual_config = visible_path_config(config, args.paths)
    tracer = SbrTracer(
        geometry,
        material.face_class,
        material.table.permittivity,
        material.table.rms_height_m,
        visual_config,
        atlas_material=material.atlas_material,
    )
    recorder = PathRecorder(capacity=args.paths, sky_distance_m=args.draw_radius_m * 1.6)
    tracer.trace(
        points[hero],
        {name: MODELS[name] for name in run.models},
        ground_z_m=float(datums[hero]),
        seed=hero_seed,
        recorder=recorder,
    )
    record = recorder.result()

    coupler = BodyCoupler(PHANTOM, run.frequency_hz, body_mass_kg=PHANTOM_MASS_KG)
    hero_rho = data.rho_rooftop[hero]
    reference_s0 = float(data.manifest["reference_s0_w_m2"])
    body_sab = body_field_from_spectrum(
        coupler,
        data.local_grid,
        hero_rho,
        data.solid_angle,
        reference_s0_w_m2=reference_s0,
    )
    coupled = coupler.couple(data.local_grid, hero_rho, data.solid_angle, reference_s0)
    recorded_body = _body_from_row(rows[hero], "rooftop")
    if set(recorded_body) != set(coupled.as_dict()) or any(
        not np.isclose(recorded_body[name], value, rtol=1.0e-10, atol=1.0e-12, equal_nan=True)
        for name, value in coupled.as_dict().items()
    ):
        raise ValueError("production rooftop body row does not match its stored angular spectrum")

    rng = np.random.default_rng(run.seed)
    network = {name: network_markers(name, args.sources, rng) for name in MODELS}
    rim = facade_tip_rim(geometry, points[hero])
    vertices, faces, kept = crop_for_drawing(geometry.vertices, geometry.faces, args.draw_radius_m)
    support_full_vertices = np.asarray(geometry.vertices, dtype=np.float32)
    support_full_faces = np.asarray(geometry.faces, dtype=np.int32)
    support_full_face_class = np.asarray(material.face_class).copy()
    support_full_face_source = np.asarray(material.face_source).copy()
    support_full_face_index = np.arange(geometry.face_count, dtype=np.int32)

    payload: dict[str, Any] = {
        "mesh_vertices": vertices.astype(np.float32),
        "mesh_faces": faces.astype(np.int32),
        "mesh_face_class": material.face_class[kept].astype(np.int8),
        "mesh_face_source": material.face_source[kept].astype(np.int8),
        "mesh_face_index": kept.astype(np.int32),
        "support_full_vertices": support_full_vertices,
        "support_full_faces": support_full_faces,
        "support_full_face_class": support_full_face_class,
        "support_full_face_source": support_full_face_source,
        "support_full_face_index": support_full_face_index,
        "walk_points": points.astype(np.float32),
        "walk_ground_z_m": datums.astype(np.float32),
        "path_vertices": record.vertices.astype(np.float32),
        "path_offsets": record.offsets.astype(np.int32),
        "path_throughput": record.throughput.astype(np.float32),
        "path_face_class": record.face_class.astype(np.int8),
        "path_exit_direction": record.exit_direction.astype(np.float32),
        "path_bounces": record.bounces.astype(np.int16),
        "path_termination": record.termination.astype(np.int8),
        "hero_index": np.array(hero),
        "hero_point": points[hero].astype(np.float32),
        "local_grid": data.local_grid.astype(np.float32),
        "local_grid_faces": sphere_triangulation(data.local_grid).astype(np.int32),
        "rho_rooftop": hero_rho.astype(np.float32),
        "body_vertices": body_sab["vertices"].astype(np.float32),
        "body_faces": body_sab["faces"].astype(np.int32),
        "body_sab_w_m2": body_sab["sab"].astype(np.float32),
        **production_role_payload(),
    }
    for name in run.models:
        payload[f"walk_chi_{name}"] = np.array([row[f"chi_{name}"] for row in rows], dtype=np.float32)
        payload[f"walk_peak_sab_{name}"] = np.array([row[f"{name}_peak_sab_w_m2"] for row in rows], dtype=np.float32)
    for name in MODELS:
        payload[f"network_{name}"] = network[name]["positions"].astype(np.float32)

    hero_body = {name: _body_from_row(rows[hero], name) for name in run.models}
    manifest = {
        "site": run.site,
        "mesh": str(mesh),
        "traced_crop_radius_m": run.crop_m,
        "drawn_radius_m": args.draw_radius_m,
        "traced_triangles": geometry.face_count,
        "drawn_triangles": int(faces.shape[0]),
        "ground_datum_m": float(data.manifest["ground_datum_m"]),
        "frequency_hz": run.frequency_hz,
        "reference_s0_w_m2": reference_s0,
        "class_names": list(material.table.class_names),
        "terminations": list(TERMINATIONS),
        "locations": len(rows),
        "walk_candidates": data.manifest.get("walk", {}).get("candidates_after_clearance"),
        "walk_provenance": data.manifest.get("walk", {}),
        "trace_config": data.manifest["trace_config"],
        "surface_binding": data.manifest["surface_binding"],
        "semantic_binding": data.manifest["semantic_binding"],
        "admitted_captures": list(data.manifest.get("semantic_binding", {}).get("image_ids", [])),
        "illumination_models": data.manifest["illumination_models"],
        "hero": {
            "index": hero,
            "production_walk_index": walk_index,
            "point_enu_m": points[hero].tolist(),
            "sky_fraction": float(rows[hero]["sky_fraction"]),
            "mean_bounces": float(rows[hero]["mean_bounces"]),
            "recorded_paths": len(record),
            "susceptibility": {name: float(rows[hero][f"chi_{name}"]) for name in run.models},
            "susceptibility_direct": {name: float(rows[hero][f"chi_{name}_direct"]) for name in run.models},
            "body": hero_body,
            "body_surface_field": {
                "role": "exact AEGIS absorbed power density, one value per body triangle",
                "vertices": _array_manifest(payload["body_vertices"]),
                "faces": _array_manifest(payload["body_faces"]),
                "sab_w_m2": _array_manifest(payload["body_sab_w_m2"]),
                "face_value_rule": "body_sab_w_m2[i] belongs exactly to body_faces[i]",
            },
            "visible_path_trace": {
                "role": "bounded visualization trace only",
                "transport_kernel": "numpy",
                "intersection_variant": args.variant,
                "frequency_hz": run.frequency_hz,
                "rays_cast": visual_config.rays,
                "seed": hero_seed,
                "seed_policy": "run seed + 1000 * production walk index",
                "paths_recorded": len(record),
                "does_not_supply": list(NO_EXPOSURE_OUTPUT),
            },
        },
        "walk_summary": {
            name: {
                "median_chi": float(np.median([row[f"chi_{name}"] for row in rows])),
                "min_chi": float(np.min([row[f"chi_{name}"] for row in rows])),
                "max_chi": float(np.max([row[f"chi_{name}"] for row in rows])),
            }
            for name in run.models
        },
        "network_height_band_m": {name: network[name]["height_band_m"].tolist() for name in MODELS},
        **production_provenance(data, run),
        "seconds": time.perf_counter() - started,
        "storage_note": (
            "The production run supplied the walk, rooftop spectrum, and body exposure. "
            "A separate bounded host trace supplied visible path polylines only."
        ),
    }
    manifest["support_display"] = {
        "full_vertices": int(support_full_vertices.shape[0]),
        "full_faces": int(support_full_faces.shape[0]),
        "inner_faces": int(faces.shape[0]),
        "outer_faces": int(support_full_faces.shape[0] - faces.shape[0]),
        "drawn_radius_m": float(args.draw_radius_m),
        "traced_radius_m": float(run.crop_m),
        "inner_face_index_sha256": _array_sha256(kept.astype(np.int32)),
    }
    manifest["support_surface_fallback"] = support_surface_fallback_manifest(
        payload,
        data,
        material,
        geometry.face_areas(),
        source_verified=source_verified,
    )
    attach_production_surface_atlas(payload, manifest, data, run, material, geometry)
    bundle = {"payload": payload, "manifest": manifest}
    store_rim(bundle, rim)
    connections = next_event_connections(
        geometry,
        record.vertices,
        record.offsets,
        rim,
        points[hero],
        paths=args.nee_paths,
        seed=run.seed,
    )
    store_connections(bundle, connections)
    return bundle


def body_field(coupler: BodyCoupler, result: Any, model: str) -> dict[str, np.ndarray]:
    """Per triangle absorbed power density on the phantom, plus its geometry.

    ``BodyMesh`` holds a triangle soup, ``(n_triangles, 3, 3)``, so the faces
    handed to Blender are the trivial index triples. That triples the vertex
    count against a shared mesh and it is the right trade here, because
    ``Sab`` is a per triangle quantity and a shared vertex would have to average
    across the faces that meet at it.
    """
    return body_field_from_spectrum(coupler, result.local_grid, result.rho[model], result.local_solid_angle)


def body_field_from_spectrum(
    coupler: BodyCoupler,
    local_grid: np.ndarray,
    rho: np.ndarray,
    solid_angle: float,
    *,
    reference_s0_w_m2: float = REFERENCE_S0_W_M2,
) -> dict[str, np.ndarray]:
    """Per-face body field derived from one stored angular spectrum."""
    from aegis.paths import PropagationPaths

    power = rho * solid_angle * reference_s0_w_m2
    keep = power > 0.0
    paths = PropagationPaths.from_powers(-local_grid[keep], power[keep])
    dosimetry = coupler.engine.compute(coupler.body, paths, level=coupler.level, body_mass=coupler.body_mass_kg)
    corners = np.asarray(coupler.body.vertices, dtype=np.float64)
    count = corners.shape[0]
    sab = np.asarray(dosimetry.sab, dtype=np.float64)
    if sab.shape != (count,):
        raise ValueError("AEGIS body Sab must contain exactly one value per body triangle")
    return {
        "vertices": corners.reshape(-1, 3),
        "faces": np.arange(3 * count, dtype=np.int64).reshape(count, 3),
        "sab": sab,
    }


# ---------------------------------------------------------------------------
# Evidence layers. Everything below reads artifacts the pipeline already wrote
# and recomputes none of them.
# ---------------------------------------------------------------------------

OUTPUTS = SCRIPT_DIR / "outputs"

#: How a rejection reason is grouped when it is aggregated back onto the support
#: triangle it came from. The split that matters is the one the pipeline itself
#: keeps: a transient object is geometry that belongs to the body layer and is
#: deferred, whereas clutter in front is geometry the tiles never captured and is
#: simply absent. Collapsing the two is the mistake this layer exists to expose.
REJECTION_GROUPS: dict[str, tuple[str, ...]] = {
    "transient": ("transient_object",),
    "clutter": ("clutter_in_front", "mesh_or_pose_conflict"),
    "occluded": ("occluded_by_support_mesh",),
    "other": (
        "degenerate_triangle",
        "behind_near_plane",
        "outside_crop",
        "subpixel_footprint",
        "no_semantic_support",
        "below_minimum_area",
        "grazing_plane",
        "not_support_surface",
    ),
}

FISHNET_SURFACE_GLOB = "*_fishnet.npz"
FISHNET_SURFACE_SUFFIX = "_fishnet.npz"
FISHNET_MANIFEST = "fishnet_manifest.json"
NPZ_GLOB = "*.npz"
REJECTED_V2_FIELDS = frozenset(
    {
        "rejected_vertices",
        "rejected_faces",
        "rejected_face_image",
        "rejected_face_record",
        "rejected_face_offsets",
        "rejected_geometry_kind",
    }
)


def _manifest_views(document: dict[str, Any], path: pathlib.Path) -> dict[str, tuple[int, int]]:
    """Return the exact view IDs and image shapes named by one artifact."""
    rows = document.get("views")
    if not isinstance(rows, list):
        raise ValueError(f"evidence manifest has no view table: {path}")
    views: dict[str, tuple[int, int]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("view"), str):
            raise ValueError(f"evidence manifest has an invalid view row: {path}")
        shape = row.get("shape")
        if not isinstance(shape, list) or len(shape) != 2 or any(int(value) <= 0 for value in shape):
            raise ValueError(f"evidence manifest has an invalid image shape: {path}")
        name = row["view"]
        if name in views:
            raise ValueError(f"evidence manifest repeats view {name}: {path}")
        views[name] = (int(shape[0]), int(shape[1]))
    return views


def _artifact_path(value: Any) -> pathlib.Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = pathlib.Path(value)
    return path if path.is_absolute() else SCRIPT_DIR / path


def _validate_fishnet_file(path: pathlib.Path, shape: tuple[int, int]) -> np.ndarray:
    with np.load(path) as surface:
        needed = {
            "vertices",
            "faces",
            "face_image",
            "face_class",
            "face_class_probability",
            "camera_position",
        }
        missing = needed.difference(surface.files)
        if missing:
            raise ValueError(f"fishnet {path.name} is missing arrays: {sorted(missing)}")
        vertices = surface["vertices"]
        faces = surface["faces"]
        face_count = faces.shape[0] if faces.ndim == 2 else -1
        valid_geometry = (
            vertices.ndim == 2 and vertices.shape[1:] == (3,) and faces.ndim == 2 and faces.shape[1:] == (3,)
        )
        if not valid_geometry:
            raise ValueError(f"fishnet geometry has invalid shapes: {path}")
        if surface["face_image"].shape != (face_count, 3, 2):
            raise ValueError(f"fishnet image triangles have the wrong shape: {path}")
        if surface["face_class"].shape != (face_count,) or surface["face_class_probability"].shape[0] != face_count:
            raise ValueError(f"fishnet face arrays disagree: {path}")
        camera = np.asarray(surface["camera_position"], dtype=np.float64)
        if camera.shape != (3,) or not np.isfinite(camera).all():
            raise ValueError(f"fishnet camera position is invalid: {path}")
        image = np.asarray(surface["face_image"])
        outside = image.size and (np.nanmax(image[..., 0]) > shape[1] + 1 or np.nanmax(image[..., 1]) > shape[0] + 1)
        if outside:
            raise ValueError(f"fishnet image coordinates exceed its manifest shape: {path}")
        return camera


def _validate_fishnet_directory(directory: pathlib.Path) -> dict[str, Any]:
    manifest_path = directory / FISHNET_MANIFEST
    if not manifest_path.is_file():
        raise ValueError(f"fishnet manifest is missing: {manifest_path}")
    document = json.loads(manifest_path.read_text())
    views = _manifest_views(document, manifest_path)
    files = {path.name.removesuffix(FISHNET_SURFACE_SUFFIX): path for path in directory.glob(FISHNET_SURFACE_GLOB)}
    if set(files) != set(views):
        raise ValueError(f"fishnet files and manifest view IDs disagree: {directory}")
    cameras = [_validate_fishnet_file(files[name], shape) for name, shape in views.items()]
    if cameras and not np.allclose(cameras, cameras[0], rtol=0.0, atol=1.0e-6):
        raise ValueError(f"fishnet views disagree on the camera position: {directory}")
    mesh = _artifact_path(document.get("mesh"))
    pose = _artifact_path(document.get("pose"))
    depth = _artifact_path(document.get("mesh_depth"))
    if mesh is None or pose is None or depth is None:
        raise ValueError(f"fishnet manifest does not identify mesh, pose, and mesh depth: {manifest_path}")
    if not mesh.is_file() or not pose.is_file() or not depth.is_dir():
        raise ValueError(f"fishnet manifest resolves to a missing mesh, pose, or mesh-depth directory: {manifest_path}")
    return {
        "directory": directory,
        "manifest": manifest_path,
        "mesh": mesh.resolve(),
        "pose": pose.resolve(),
        "mesh_depth": depth.resolve(),
        "views": views,
        "camera": cameras[0] if cameras else None,
    }


def _validate_mesh_depth_directory(directory: pathlib.Path, fishnet: dict[str, Any]) -> None:
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"mesh-depth manifest is missing: {manifest_path}")
    document = json.loads(manifest_path.read_text())
    mesh = _artifact_path(document.get("mesh"))
    pose = _artifact_path(document.get("pose"))
    if mesh is None or mesh.resolve() != fishnet["mesh"]:
        raise ValueError(f"fishnet and mesh depth use different support meshes: {directory}")
    if pose is None or pose.resolve() != fishnet["pose"]:
        raise ValueError(f"fishnet and mesh depth use different camera poses: {directory}")
    views = _manifest_views(document, manifest_path)
    if views != fishnet["views"]:
        raise ValueError(f"fishnet and mesh depth use different view IDs or image shapes: {directory}")
    files = {path.stem: path for path in directory.glob(NPZ_GLOB)}
    if set(files) != set(views):
        raise ValueError(f"mesh-depth files and manifest view IDs disagree: {directory}")
    for name, shape in views.items():
        _validate_mesh_depth_file(files[name], shape)
    recorded = document.get("camera_position_enu_m")
    if recorded is not None and fishnet["camera"] is not None:
        camera = np.asarray(recorded, dtype=np.float64)
        if camera.shape != (3,) or not np.allclose(camera, fishnet["camera"], rtol=0.0, atol=1.0e-6):
            raise ValueError(f"fishnet and mesh depth record different camera positions: {directory}")


def _validate_mesh_depth_file(path: pathlib.Path, shape: tuple[int, int]) -> None:
    with np.load(path) as depth:
        if "range_m" not in depth.files or "face_ids" not in depth.files:
            raise ValueError(f"mesh-depth file is incomplete: {path}")
        if depth["range_m"].shape != shape or depth["face_ids"].shape != shape:
            raise ValueError(f"mesh-depth arrays disagree with the manifest shape: {path}")


def _image_directory_matches(directory: pathlib.Path, views: dict[str, tuple[int, int]]) -> bool:
    """Whether an optional per-view depth product belongs to this family."""
    files = {path.stem: path for path in directory.glob(NPZ_GLOB)}
    if set(files) != set(views):
        return False
    for name, shape in views.items():
        with np.load(files[name]) as saved:
            arrays = [saved[key] for key in saved.files if np.asarray(saved[key]).ndim == 2]
            if not arrays or any(array.shape != shape for array in arrays):
                return False
    return True


def _select_vistas_family(site: str) -> tuple[dict[str, pathlib.Path], dict[str, Any] | None, dict[str, Any]]:
    names = (
        f"{site}_fishnet_vistas_250m_v2",
        f"{site}_fishnet_vistas_fused",
        f"{site}_fishnet_vistas",
    )
    report: dict[str, Any] = {"selection": "none", "excluded": {}}
    for directory in (OUTPUTS / name for name in names):
        if not directory.is_dir():
            continue
        manifest_path = directory / FISHNET_MANIFEST
        if not manifest_path.exists() or not any(directory.glob(FISHNET_SURFACE_GLOB)):
            report["selection"] = "incomplete Vistas artifact"
            return {"fishnet_vistas": directory}, None, report
        selected = _validate_fishnet_directory(directory)
        depth = pathlib.Path(selected["mesh_depth"])
        _validate_mesh_depth_directory(depth, selected)
        report.update(
            selection="validated coherent family",
            mesh=str(selected["mesh"]),
            pose=str(selected["pose"]),
            views={name: list(shape) for name, shape in selected["views"].items()},
        )
        return {"fishnet_vistas": directory, "mesh_depth": depth}, selected, report
    return {}, None, report


def _sam3_compatibility(sam3: pathlib.Path, selected: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        candidate = _validate_fishnet_directory(sam3)
    except (OSError, ValueError, KeyError) as error:
        return False, str(error)
    compatible = all(candidate[key] == selected[key] for key in ("mesh", "pose", "views"))
    return compatible, None if compatible else "mesh, pose, views, or image shapes differ from Vistas"


def _attach_optional_depth_products(
    site: str,
    found: dict[str, pathlib.Path],
    report: dict[str, Any],
    views: dict[str, tuple[int, int]],
) -> None:
    for key, name in (
        ("depth_gated", f"{site}_depth_fused"),
        ("depth_ungated", f"{site}_depth_consistency_two_models"),
    ):
        directory = OUTPUTS / name
        if not directory.is_dir():
            continue
        if _image_directory_matches(directory, views):
            found[key] = directory
        else:
            report["excluded"][key] = "view IDs or image shapes differ from the selected family"


def select_evidence_family(site: str) -> tuple[dict[str, pathlib.Path], dict[str, Any]]:
    """Select one mesh, pose, view, and image-shape compatible evidence family."""
    found, selected, report = _select_vistas_family(site)

    sam3 = OUTPUTS / f"{site}_fishnet_sam3"
    if sam3.is_dir():
        if selected is None:
            found["fishnet_sam3"] = sam3
        else:
            compatible, reason = _sam3_compatibility(sam3, selected)
            if compatible:
                found["fishnet_sam3"] = sam3
            else:
                report["excluded"]["fishnet_sam3"] = reason

    if selected is not None:
        _attach_optional_depth_products(site, found, report, selected["views"])

    bodies = OUTPUTS / f"{site}_dynamic_bodies"
    if bodies.is_dir():
        found["bodies"] = bodies
    return found, report


def evidence_directories(site: str) -> dict[str, pathlib.Path]:
    """Return only directories from one validated evidence family."""
    return select_evidence_family(site)[0]


def read_taxonomy(path: pathlib.Path) -> dict[int, str]:
    return {int(key): value for key, value in json.loads(path.read_text())["entity_id2label"].items()}


def taxonomy_file(site: str) -> pathlib.Path | None:
    """The Vistas id to name table for a site, wherever that site keeps it.

    Korenmarkt has one panorama and writes the table once at the site root. The
    sites the six site run added have several, and each capture keeps its own
    copy. It is the same 66 class table either way, so the first one found is
    the right one, and the alternative is a site whose fishnet exists on disk and
    silently never reaches the blend because the file it needs sits one
    directory deeper. That is what happened to New York.
    """
    root = SCRIPT_DIR / "data" / "panoramas" / site
    direct = root / "semantics" / "semantics.json"
    if direct.exists():
        return direct
    found = sorted(root.glob("*/semantics/semantics.json"))
    return found[0] if found else None


def class_palette(count: int) -> np.ndarray:
    """One tint per class id, deterministic and separated on neighbouring ids.

    A colour ramp is wrong for a taxonomy: adjacent Mapillary Vistas ids are
    unrelated classes, and a ramp invites reading a gradient into a lookup. Hues
    therefore walk the circle by the golden angle, which keeps neighbouring ids
    far apart, and saturation and value cycle on short periods so that two hues
    that do land close still differ. The names go in the manifest, so the mapping
    is inspectable rather than guessed from the picture.
    """
    import colorsys

    golden = 0.6180339887498949
    rgb = np.empty((max(count, 1), 3), dtype=np.float64)
    for index in range(rgb.shape[0]):
        hue = (index * golden) % 1.0
        saturation = 0.42 + 0.36 * ((index % 3) / 2.0)
        value = 0.96 - 0.30 * (index % 2)
        rgb[index] = colorsys.hsv_to_rgb(hue, saturation, value)
    return rgb


def posterior_entropy_bits(probability: np.ndarray) -> np.ndarray:
    """Shannon entropy of each row, in bits.

    This is the uncertainty an argmax throws away. A face the segmenter is sure
    about sits near zero, a face split between two classes sits near one bit, and
    a face the cutter assembled out of a genuinely mixed pixel set sits higher.
    """
    probability = np.asarray(probability, dtype=np.float64)
    return -(probability * np.log2(np.clip(probability, 1.0e-12, 1.0))).sum(axis=1)


def view_angles(stem: str) -> tuple[float, float]:
    """Pitch and yaw in degrees, from a view stem such as ``h+00_270``.

    Read from the tail rather than from a fixed offset. Some sites write the
    panorama id in front of the view, ``pano_07_CAoSFkNJSE0wb2dL_h+00_000``, and
    slicing the front of that returns a plausible pair of numbers for the wrong
    view rather than failing, which is the worst way for it to be wrong.
    """
    pitch, _, yaw = stem.rpartition("_")
    return float(pitch.rpartition("_")[2][1:]), float(yaw)


def evidence_pose(site: str, directories: dict[str, pathlib.Path]) -> dict[str, Any] | None:
    """The camera the evidence was actually built at, and how far the pose file has moved since.

    The fishnet writes its camera centre into every surface set. The pose file on
    disk is rewritten whenever the skyline alignment is re-run, and at Korenmarkt
    it has been: unprojecting the mesh first hit buffer with the current pose
    lands 0.94 m off the mesh, with the recorded centre 0.04 m. So the recorded
    centre wins for anything that unprojects a stored image, and the drift is
    reported rather than hidden. The rotation still comes from the pose file,
    because no rotation is recorded next to the buffers, and the residual above
    bounds how much that can cost.
    """
    from semantic_twin.pano_geometry import panorama_to_world_matrix

    pose_path = SCRIPT_DIR / "data" / "panoramas" / site / "alignment" / "pose_aligned.json"
    if not pose_path.exists():
        return None
    document = json.loads(pose_path.read_text())
    rotation = panorama_to_world_matrix(
        float(document["heading_deg"]),
        pitch_deg=float(document["pitch_correction_deg"]),
        roll_deg=float(document["roll_correction_deg"]),
    )
    stated = np.asarray(document["position_enu_m"], dtype=np.float64)
    recorded = stated
    source = "pose file, no surface set to read a camera centre from"
    fishnet = directories.get("fishnet_vistas")
    if fishnet is not None:
        views = sorted(fishnet.glob(FISHNET_SURFACE_GLOB))
        if views:
            recorded = np.load(views[0])["camera_position"].astype(np.float64)
            source = f"camera centre recorded in {views[0].name}"
    return {
        "position": recorded,
        "rotation": rotation,
        "position_source": source,
        "pose_file": str(pose_path.relative_to(SCRIPT_DIR)),
        "pose_file_position_enu_m": stated.tolist(),
        "drift_since_evidence_m": float(np.linalg.norm(recorded - stated)),
    }


def fishnet_layer(directory: pathlib.Path, class_count: int) -> dict[str, Any]:
    """One surface set per view, concatenated, with the evidence each face carries.

    The posterior itself is not shipped. At 59 columns for Vistas it is most of
    the file and no shader can read it, so it is reduced here to the two numbers
    a reader needs, the winning probability and the entropy of the whole row.
    """
    files = sorted(directory.glob(FISHNET_SURFACE_GLOB))
    vertices: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    columns: dict[str, list[np.ndarray]] = {name: [] for name in FISHNET_FACE_COLUMNS}
    view_index: list[np.ndarray] = []
    cameras: list[np.ndarray] = []
    offset = 0
    for index, path in enumerate(files):
        surface = np.load(path)
        vertices.append(surface["vertices"])
        faces.append(surface["faces"] + offset)
        offset += surface["vertices"].shape[0]
        probability = surface["face_class_probability"]
        columns["class"].append(surface["face_class"])
        columns["confidence"].append(surface["face_confidence"])
        columns["top_probability"].append(probability.max(axis=1))
        columns["entropy_bits"].append(posterior_entropy_bits(probability))
        columns["range_m"].append(surface["face_depth"])
        columns["visible_fraction"].append(surface["face_visible_fraction"])
        columns["area_m2"].append(surface["face_area_m2"])
        columns["solid_angle_sr"].append(surface["face_solid_angle_sr"])
        columns["pixel_support"].append(surface["face_pixel_support"])
        view_index.append(np.full(surface["faces"].shape[0], index))
        cameras.append(surface["camera_position"])
    keep = renderable_faces(np.concatenate(faces))
    layer = {
        "vertices": np.concatenate(vertices).astype(np.float32),
        "faces": np.concatenate(faces)[keep].astype(np.int32),
        "view": np.concatenate(view_index)[keep].astype(np.int8),
        "camera": np.stack(cameras).astype(np.float32),
        "class_rgb": class_palette(class_count).astype(np.float32),
    }
    for name, dtype in FISHNET_FACE_COLUMNS.items():
        layer[name] = np.concatenate(columns[name])[keep].astype(dtype)
    layer["views"] = [path.name.removesuffix(FISHNET_SURFACE_SUFFIX) for path in files]
    layer["dropped_faces"] = int(keep.size - keep.sum())
    return layer


def renderable_faces(faces: np.ndarray) -> np.ndarray:
    """Which faces Blender will keep, so the per face columns stay aligned to them.

    ``Mesh.validate`` silently removes a triangle whose corners repeat and the
    second copy of a triangle that already exists, and every per face colour
    after the first removal is then off by one. The fishnet emits two duplicate
    index triples per taxonomy at Korenmarkt, out of ten and sixteen thousand, so
    this is small and it is not nothing. Dropping them here rather than letting
    Blender do it keeps the columns honest, and the count goes in the manifest.
    """
    faces = np.asarray(faces)
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    _, first = np.unique(np.sort(faces, axis=1), axis=0, return_index=True)
    unique = np.zeros(faces.shape[0], dtype=bool)
    unique[first] = True
    return keep & unique


#: Per face columns the fishnet layer carries into the blend, and the type each
#: is stored as. Everything here is either a measured quantity or a reduction of
#: one, never a rendering choice.
FISHNET_FACE_COLUMNS: dict[str, Any] = {
    "class": np.int16,
    "confidence": np.float32,
    "top_probability": np.float32,
    "entropy_bits": np.float32,
    "range_m": np.float32,
    "visible_fraction": np.float32,
    "area_m2": np.float32,
    "solid_angle_sr": np.float32,
    "pixel_support": np.int32,
}


def support_mesh_of(directory: pathlib.Path) -> pathlib.Path | None:
    """The support mesh a fishnet run was cut against, read from its own manifest.

    A one panorama site writes one manifest beside its surfaces. A several
    panorama site writes a site level one and a per capture one under each, and
    the site level one names the mesh by basename rather than by path. Both
    shapes are read, and the basename is resolved against the per capture
    manifest that does carry a path, because guessing which city a bare
    ``inhouse_leaf_130m.ply`` belongs to is how you cut one square's semantics
    against another square's geometry.
    """
    for name in (FISHNET_MANIFEST, "site_fishnet_manifest.json"):
        path = directory / name
        if not path.exists():
            continue
        stated = SCRIPT_DIR / json.loads(path.read_text())["mesh"]
        if stated.exists():
            return stated
    for path in sorted(directory.glob(f"*/{FISHNET_MANIFEST}")):
        stated = SCRIPT_DIR / json.loads(path.read_text())["mesh"]
        if stated.exists():
            return stated
    return None


def triangle_soup(vertices: np.ndarray, faces: np.ndarray, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Selected triangles as an unshared soup, so a per triangle colour is exact."""
    corners = vertices[faces[indices]].reshape(-1, 3)
    return corners, np.arange(corners.shape[0], dtype=np.int32).reshape(-1, 3)


def support_evidence_layer(directory: pathlib.Path, class_count: int) -> dict[str, Any] | None:
    """Every support triangle any view considered, with what the pixels said about it.

    This is the layer that answers what the segmenter saw on a given wall and how
    much of that wall the cutter then refused. Accepted pieces contribute their
    pixel support and their class, weighted by that support. Rejected pieces
    contribute their projected image area under the group that rejected them.
    The two are the clean and the withheld halves of the same triangle and they
    are kept as separate channels, because a triangle can be both.
    """
    import trimesh

    from semantic_twin.scene.fishnet import REJECTION_REASONS

    support = support_mesh_of(directory)
    if support is None:
        return None
    mesh = trimesh.load(support, process=False, force="mesh")
    count = int(mesh.faces.shape[0])
    clean = np.zeros(count)
    confidence = np.zeros(count)
    histogram = np.zeros((count, max(class_count, 1)))
    groups = {name: np.zeros(count) for name in REJECTION_GROUPS}
    codes = {name: {REJECTION_REASONS[reason] for reason in reasons} for name, reasons in REJECTION_GROUPS.items()}

    for path in sorted(directory.glob(FISHNET_SURFACE_GLOB)):
        surface = np.load(path)
        source = surface["face_source_triangle"].astype(np.int64)
        support = surface["face_pixel_support"].astype(np.float64)
        np.add.at(clean, source, support)
        np.add.at(confidence, source, support * surface["face_confidence"])
        np.add.at(histogram, (source, surface["face_class"].astype(np.int64)), support)
        rejected = surface["rejected_source_triangle"].astype(np.int64)
        reason = surface["rejected_reason"].astype(np.int64)
        area = surface["rejected_image_area_px"].astype(np.float64)
        for name, wanted in codes.items():
            mask = np.isin(reason, list(wanted))
            np.add.at(groups[name], rejected[mask], area[mask])

    touched = np.flatnonzero(clean + sum(groups.values()) > 0.0)
    vertices, faces = triangle_soup(np.asarray(mesh.vertices), np.asarray(mesh.faces), touched)
    modal = histogram[touched].argmax(axis=1)
    modal[clean[touched] <= 0.0] = -1
    layer = {
        "vertices": vertices.astype(np.float32),
        "faces": faces,
        "class": modal.astype(np.int16),
        "clean_px": clean[touched].astype(np.float32),
        "confidence": np.divide(
            confidence[touched], clean[touched], out=np.zeros(touched.size), where=clean[touched] > 0.0
        ).astype(np.float32),
        "class_rgb": class_palette(class_count).astype(np.float32),
    }
    for name in REJECTION_GROUPS:
        layer[f"{name}_px"] = groups[name][touched].astype(np.float32)
    return layer


def rejected_layer(directory: pathlib.Path) -> dict[str, Any] | None:
    """The candidate surface the cutter refused, as geometry, with the reason.

    Version two fishnets carry each rejected fragment's own triangulation. Those
    fragments are kept one by one because their shape is the evidence. Version
    one files only name a source triangle. They retain the old deduplicated
    support-triangle drawing as an explicitly marked legacy fallback.
    """
    from semantic_twin.scene.fishnet import REJECTION_REASONS
    from semantic_twin.scene.fishnet.surface import REJECTED_GEOMETRY_KINDS

    vertices_parts: list[np.ndarray] = []
    faces_parts: list[np.ndarray] = []
    reasons_parts: list[np.ndarray] = []
    areas_parts: list[np.ndarray] = []
    sources_parts: list[np.ndarray] = []
    views_parts: list[np.ndarray] = []
    fragments_parts: list[np.ndarray] = []
    geometry_source_parts: list[np.ndarray] = []
    geometry_kind_parts: list[np.ndarray] = []
    image_triangle_parts: list[np.ndarray] = []
    legacy_pairs: dict[tuple[int, int], float] = {}
    format_versions: set[int] = set()
    unavailable_rows_by_reason: dict[int, int] = {}
    unavailable_area_by_reason: dict[int, float] = {}
    saw_version_two = False
    vertex_offset = 0
    fragment_offset = 0

    for view_index, path in enumerate(sorted(directory.glob(FISHNET_SURFACE_GLOB))):
        with np.load(path) as surface:
            format_version = int(surface["fishnet_format_version"]) if "fishnet_format_version" in surface.files else 1
            format_versions.add(format_version)
            exact = format_version >= 2 and REJECTED_V2_FIELDS.issubset(surface.files)
            if format_version >= 2 and not exact:
                missing = sorted(REJECTED_V2_FIELDS.difference(surface.files))
                raise ValueError(f"format-v2 rejected geometry is incomplete in {path.name}; missing {missing}")
            if not exact:
                for triangle, reason, area in zip(
                    surface["rejected_source_triangle"].astype(int),
                    surface["rejected_reason"].astype(int),
                    surface["rejected_image_area_px"].astype(float),
                    strict=True,
                ):
                    key = (int(triangle), int(reason))
                    legacy_pairs[key] = legacy_pairs.get(key, 0.0) + float(area)
                continue

            saw_version_two = True
            rejected_faces = surface["rejected_faces"].astype(np.int64)
            record_reason = surface["rejected_reason"].astype(np.int64)
            record_source = surface["rejected_source_triangle"].astype(np.int64)
            record_area = surface["rejected_image_area_px"].astype(np.float64)
            record = surface["rejected_face_record"].astype(np.int64)
            rejected_vertices = surface["rejected_vertices"].astype(np.float64)
            image = surface["rejected_face_image"].astype(np.float64)
            kind = surface["rejected_geometry_kind"].astype(np.uint8)
            if record_source.shape != record_reason.shape or record_area.shape != record_reason.shape:
                raise ValueError(f"rejected record columns disagree in {path.name}")
            if rejected_faces.ndim != 2 or rejected_faces.shape[1:] != (3,):
                raise ValueError(f"rejected_faces has the wrong shape in {path.name}")
            if image.shape != (rejected_faces.shape[0], 3, 2) or record.shape != (rejected_faces.shape[0],):
                raise ValueError(f"rejected face columns disagree in {path.name}")
            if kind.shape != record_reason.shape or np.any((kind < 0) | (kind > max(REJECTED_GEOMETRY_KINDS.values()))):
                raise ValueError(f"rejected_geometry_kind is invalid in {path.name}")
            if rejected_faces.size and (
                np.any(rejected_faces < 0)
                or np.any(rejected_faces >= rejected_vertices.shape[0])
                or np.any(record < 0)
                or np.any(record >= record_reason.shape[0])
            ):
                raise ValueError(f"rejected geometry has an out-of-range index in {path.name}")
            offsets = surface["rejected_face_offsets"].astype(np.int64)
            expected = np.concatenate([[0], np.cumsum(np.bincount(record, minlength=record_reason.shape[0]))])
            if not np.array_equal(offsets, expected):
                raise ValueError(f"rejected_face_offsets disagrees with face records in {path.name}")
            available = np.zeros(record_reason.shape[0], dtype=bool)
            available[np.unique(record)] = True
            for reason in np.unique(record_reason[~available]):
                mask = (~available) & (record_reason == reason)
                code = int(reason)
                unavailable_rows_by_reason[code] = unavailable_rows_by_reason.get(code, 0) + int(mask.sum())
                unavailable_area_by_reason[code] = unavailable_area_by_reason.get(code, 0.0) + float(
                    record_area[mask].sum()
                )
            fragment_offset += int(record_reason.shape[0])
            if rejected_faces.shape[0] == 0:
                continue

            signed_twice = (image[:, 1, 0] - image[:, 0, 0]) * (image[:, 2, 1] - image[:, 0, 1]) - (
                image[:, 2, 0] - image[:, 0, 0]
            ) * (image[:, 1, 1] - image[:, 0, 1])
            triangle_area = 0.5 * np.abs(signed_twice)
            total = np.zeros(record_reason.shape[0], dtype=np.float64)
            np.add.at(total, record, triangle_area)
            face_area = np.divide(
                record_area[record] * triangle_area,
                total[record],
                out=np.zeros(triangle_area.shape[0]),
                where=total[record] > 0.0,
            )

            vertices_parts.append(rejected_vertices)
            faces_parts.append(rejected_faces + vertex_offset)
            reasons_parts.append(record_reason[record].astype(np.int16))
            areas_parts.append(face_area.astype(np.float32))
            sources_parts.append(record_source[record].astype(np.int32))
            views_parts.append(np.full(record.shape[0], view_index, dtype=np.int16))
            fragments_parts.append((record + fragment_offset - record_reason.shape[0]).astype(np.int32))
            geometry_source_parts.append(np.ones(record.shape[0], dtype=np.uint8))
            geometry_kind_parts.append(kind[record])
            image_triangle_parts.append(image.reshape(-1, 6).astype(np.float32))
            vertex_offset += int(rejected_vertices.shape[0])

    if legacy_pairs:
        import trimesh

        support = support_mesh_of(directory)
        if support is None:
            if faces_parts:
                raise ValueError("legacy rejected rows need the support mesh for their explicit fallback")
            return None
        mesh = trimesh.load(support, process=False, force="mesh")
        ordered = sorted(legacy_pairs)
        triangles = np.array([pair[0] for pair in ordered], dtype=np.int64)
        fallback_vertices, fallback_faces = triangle_soup(np.asarray(mesh.vertices), np.asarray(mesh.faces), triangles)
        count = fallback_faces.shape[0]
        vertices_parts.append(fallback_vertices)
        faces_parts.append(fallback_faces + vertex_offset)
        reasons_parts.append(np.array([pair[1] for pair in ordered], dtype=np.int16))
        areas_parts.append(np.array([legacy_pairs[pair] for pair in ordered], dtype=np.float32))
        sources_parts.append(triangles.astype(np.int32))
        views_parts.append(np.full(count, -1, dtype=np.int16))
        fragments_parts.append(np.arange(fragment_offset, fragment_offset + count, dtype=np.int32))
        geometry_source_parts.append(np.zeros(count, dtype=np.uint8))
        geometry_kind_parts.append(np.full(count, 3, dtype=np.uint8))
        image_triangle_parts.append(np.full((count, 6), np.nan, dtype=np.float32))

    if not faces_parts and not saw_version_two:
        return None
    empty_vertices = np.zeros((0, 3), dtype=np.float32)
    empty_faces = np.zeros((0, 3), dtype=np.int32)
    empty_i16 = np.zeros(0, dtype=np.int16)
    empty_i32 = np.zeros(0, dtype=np.int32)
    empty_u8 = np.zeros(0, dtype=np.uint8)
    empty_f32 = np.zeros(0, dtype=np.float32)
    empty_image = np.zeros((0, 6), dtype=np.float32)
    return {
        "vertices": np.concatenate(vertices_parts).astype(np.float32) if vertices_parts else empty_vertices,
        "faces": np.concatenate(faces_parts).astype(np.int32) if faces_parts else empty_faces,
        "reason": np.concatenate(reasons_parts) if reasons_parts else empty_i16,
        "image_area_px": np.concatenate(areas_parts) if areas_parts else empty_f32,
        "source_triangle": np.concatenate(sources_parts) if sources_parts else empty_i32,
        "view": np.concatenate(views_parts) if views_parts else empty_i16,
        "fragment": np.concatenate(fragments_parts) if fragments_parts else empty_i32,
        "geometry_source": np.concatenate(geometry_source_parts) if geometry_source_parts else empty_u8,
        "geometry_kind": np.concatenate(geometry_kind_parts) if geometry_kind_parts else empty_u8,
        "image_triangle_px": np.concatenate(image_triangle_parts) if image_triangle_parts else empty_image,
        "reason_names": [name for name, _ in sorted(REJECTION_REASONS.items(), key=lambda item: item[1])],
        "reason_codes": [code for _, code in sorted(REJECTION_REASONS.items(), key=lambda item: item[1])],
        "geometry_source_names": ["legacy_source_triangle_fallback", "exact_rejected_fragment"],
        "geometry_kind_names": ["unavailable", "exact_cut_piece", "clipped_footprint", "legacy_source_triangle"],
        "fishnet_format_versions": sorted(format_versions),
        "view_names": [
            path.name.removesuffix(FISHNET_SURFACE_SUFFIX) for path in sorted(directory.glob(FISHNET_SURFACE_GLOB))
        ],
        "unavailable_rows_by_reason": unavailable_rows_by_reason,
        "unavailable_image_area_px_by_reason": unavailable_area_by_reason,
    }


def unproject(camera: np.ndarray, rotation: np.ndarray, stem: str, range_m: np.ndarray) -> np.ndarray:
    """Pixels of one crop, at their measured range, as points in scene ENU.

    The rays come from ``pano_geometry`` rather than from a reimplementation, so
    they are the rays ``raycast_mesh_depth.py`` cast, and ``range_m`` is a
    distance from the camera rather than a depth along the axis.
    """
    from semantic_twin.pano_geometry import PerspectiveView, perspective_directions

    pitch, yaw = view_angles(stem)
    height, width = range_m.shape
    local = perspective_directions(PerspectiveView(stem, yaw, pitch, 90.0), width, height).reshape(-1, 3)
    return camera + range_m.reshape(-1, 1) * (local @ rotation.T)


def depth_cloud(
    directory: pathlib.Path,
    range_key: str,
    pose: dict[str, Any],
    *,
    stride: int,
    decision_directory: pathlib.Path | None,
    extra: tuple[str, ...] = (),
    max_range_m: float = 150.0,
) -> dict[str, Any] | None:
    """One point per surviving pixel of every crop, at the range the named array gives.

    Two different clouds come out of this. The mesh first hit is what the twin
    uses, and colouring it by the decision map shows where the transient mask cut
    a hole in it. The monocular range is what the plausibility gate refused, and
    the point of drawing it is that the refusal is visible: at a fitted scale of
    0.41 the whole square collapses towards the camera.
    """
    points: list[np.ndarray] = []
    channels: dict[str, list[np.ndarray]] = {name: [] for name in ("decision", *extra)}
    views: list[np.ndarray] = []
    # Any name with a view in it, not just the ones that start with the view, so
    # a site whose buffers carry a panorama id in front of the crop is read
    # rather than silently skipped into an empty cloud.
    for index, path in enumerate(sorted(path for path in directory.glob("*.npz") if "h+" in path.stem)):
        stem = path.stem
        data = np.load(path)
        if range_key not in data.files:
            continue
        range_m = data[range_key].astype(np.float64)
        world = unproject(pose["position"], pose["rotation"], stem, range_m)
        decision = None
        if decision_directory is not None and (decision_directory / f"{stem}.npz").exists():
            decision = np.load(decision_directory / f"{stem}.npz")["decision"].ravel()
        grid = np.zeros(range_m.shape, dtype=bool)
        grid[::stride, ::stride] = True
        flat = range_m.ravel()
        keep = np.isfinite(flat) & (flat > 0.0) & (flat < max_range_m) & grid.ravel()
        kept = int(keep.sum())
        points.append(world[keep])
        views.append(np.full(kept, index))
        channels["decision"].append((decision[keep] if decision is not None else np.full(kept, -1)).astype(np.int16))
        for name in extra:
            if name in data.files:
                channels[name].append(data[name].astype(np.float32).ravel()[keep])
            else:
                channels[name].append(np.full(kept, np.nan, dtype=np.float32))
    if not points:
        return None
    layer = {
        "points": np.concatenate(points).astype(np.float32),
        "view": np.concatenate(views).astype(np.int8),
    }
    for name, pieces in channels.items():
        layer[name] = np.concatenate(pieces)
    return layer


def _registration_verdict_label(admission: Verdict) -> str:
    """Compact display label for one versioned admission verdict."""
    if admission.sky_conflict_state == SKY_CONFLICT_INSIDE_GEOMETRY:
        return "camera inside the geometry"
    if admission.sky_conflict_state == SKY_CONFLICT_LARGE_MISMATCH:
        return SKY_CONFLICT_LARGE_MISMATCH
    if admission.sky_conflict_state == SKY_CONFLICT_UNKNOWN:
        return "unknown diagnostics"
    if not admission.admitted:
        return "registration refused"
    return "usable"


def registration_layer(site: str, gate: AdmissionGate | None = None) -> dict[str, Any] | None:
    """Every pose registered against this site's geometry, with its covariance.

    The audit table is the filter: a pose belongs here when the mesh it was
    aligned against is this site's, which picks up the twelve walk captures at
    Korenmarkt alongside the one the semantics were run on. The position block of
    the seed study covariance becomes an ellipsoid, and the sky conflict fraction
    becomes the verdict, so a camera that sits inside the geometry is visible as
    such instead of being averaged into a residual.
    """
    from semantic_twin.pano_geometry import panorama_to_world_matrix

    gate = AdmissionGate() if gate is None else gate

    audit = OUTPUTS / "registration_sky_conflict.json"
    if not audit.exists():
        return None
    document = json.loads(audit.read_text())
    rows = [row for row in document["poses"] if str(row["mesh"]).startswith(f"data/geometry/{site}/")]
    if not rows:
        return None
    positions, rotations, sigmas, records = [], [], [], []
    for row in rows:
        pose_path = SCRIPT_DIR / row["pose_file"]
        if not pose_path.exists():
            continue
        pose = json.loads(pose_path.read_text())
        positions.append(np.asarray(pose["position_enu_m"], dtype=np.float64))
        rotations.append(
            panorama_to_world_matrix(
                float(pose["heading_deg"]),
                pitch_deg=float(pose["pitch_correction_deg"]),
                roll_deg=float(pose["roll_correction_deg"]),
            )
        )
        uncertainty = pose.get("pose_uncertainty", {})
        names = list(uncertainty.get("parameter_names", []))
        block = np.zeros((3, 3))
        if {"dx_m", "dy_m", "dz_m"} <= set(names):
            covariance = np.asarray(uncertainty["covariance"], dtype=np.float64)
            take = [names.index(name) for name in ("dx_m", "dy_m", "dz_m")]
            block = covariance[np.ix_(take, take)]
        values, vectors = np.linalg.eigh(block)
        sigmas.append(vectors * np.sqrt(np.clip(values, 0.0, None)))
        registration = Registration.from_pose(pose)
        admission = registration.verdict(gate)
        conflict = registration.sky_conflict
        verdict = _registration_verdict_label(admission)
        records.append(
            {
                "capture": row["capture"],
                "pose_file": row["pose_file"],
                "position_enu_m": positions[-1].tolist(),
                "skyline_residual_deg": row["skyline_residual_deg"],
                "sky_with_mesh_hit_fraction": conflict,
                "conflict_median_range_m": registration.conflict_median_range_m,
                "sky_conflict_state": admission.sky_conflict_state,
                "dz_at_bound": registration.dz_at_bound,
                "admitted": admission.admitted,
                "refused_because": list(admission.reasons),
                "admission_gate_version": gate.version,
                "position_sigma_m": float(np.sqrt(np.trace(block) / 3.0)),
                "verdict": verdict,
            }
        )
    if not records:
        return None
    return {
        "position": np.stack(positions).astype(np.float32),
        "rotation": np.stack(rotations).astype(np.float32),
        "sigma_vectors": np.stack(sigmas).astype(np.float32),
        "verdict": np.array([VERDICT_CODES[record["verdict"]] for record in records], dtype=np.int8),
        "residual_deg": np.array([record["skyline_residual_deg"] for record in records], dtype=np.float32),
        "sky_conflict": np.array(
            [
                np.nan if record["sky_with_mesh_hit_fraction"] is None else record["sky_with_mesh_hit_fraction"]
                for record in records
            ],
            dtype=np.float32,
        ),
        "records": records,
        "reading": document["reading"],
        "admission": gate.as_dict(),
    }


#: Verdict order, so the blend can colour a marker without parsing a string.
#: Every array name the evidence half writes starts with one of these, so a
#: reopened payload can be stripped back to the traced half exactly.
EVIDENCE_PREFIXES = (
    "fishnet_",
    "support_evidence_",
    "rejected_",
    "depth_mesh_",
    "depth_monocular_",
    "pano_",
    "body_layer_",
    "evidence_camera",
)

VERDICT_CODES = {
    "usable": 0,
    "suspect": 1,
    "camera inside the geometry": 2,
    "large sky-mesh mismatch": 3,
    "registration refused": 4,
    "unknown diagnostics": 5,
}


def body_layer(directory: pathlib.Path) -> dict[str, Any] | None:
    """The SMPL-X bystanders, already placed in scene ENU by the dynamic body stage.

    All of them share the SMPL-X topology, so the faces are stored once and only
    the vertices repeat. That is the difference between four megabytes and
    twelve for the eighteen people at Korenmarkt.
    """
    manifest_path = directory / "dynamic_bodies_manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    bodies = manifest.get("bodies", [])
    vertices, accepted, missing, faces = [], [], [], None
    for body in bodies:
        path = directory / f"{body['body_id']}.npz"
        if not path.exists():
            missing.append(body["body_id"])
            continue
        data = np.load(path, allow_pickle=True)
        if faces is None:
            faces = data["faces"]
        elif not np.array_equal(faces, data["faces"]):
            raise RuntimeError(
                f"{path.name} does not share the SMPL-X topology of the first body, so one face "
                "array cannot stand for all of them. Store them separately or fix the reconstruction."
            )
        vertices.append(data["vertices_enu_m"])
        accepted.append(body)
    if not vertices or faces is None:
        return None
    return {
        "vertices": np.stack(vertices).astype(np.float32),
        "faces": np.asarray(faces, dtype=np.int32),
        "records": accepted,
        "missing_body_ids": missing,
    }


def surface_offset_to_drawn_mesh(
    payload: dict[str, Any], centroids: np.ndarray, radius_m: float, samples: int = 512
) -> dict[str, float]:
    """How far the semantic surface sits from the mesh the rays were cast against.

    They are not the same build. The fishnet was cut against the 130 m support
    mesh, whose tile placement was read back through Blender in single precision,
    and the tracer runs on the 250 m double precision rebuild. So the semantic
    layer floats off the drawn geometry by a real amount and the reader is
    entitled to know it rather than discover it as z fighting.

    Faces beyond the drawn radius are excluded and counted separately. They are
    not misregistered, they are simply outside the shell the blend draws, and
    leaving them in turns a six centimetre disagreement into a forty metre one.
    """
    import trimesh

    mesh = trimesh.Trimesh(
        vertices=np.asarray(payload["mesh_vertices"], dtype=np.float64),
        faces=np.asarray(payload["mesh_faces"], dtype=np.int64),
        process=False,
    )
    inside = np.flatnonzero(np.linalg.norm(centroids[:, :2], axis=1) <= radius_m)
    rng = np.random.default_rng(0)
    picks = rng.choice(inside, size=min(samples, inside.size), replace=False)
    _, distance, _ = trimesh.proximity.closest_point(mesh, centroids[picks])
    return {
        "samples": int(picks.size),
        "median_m": float(np.median(distance)),
        "p95_m": float(np.percentile(distance, 95.0)),
        "max_m": float(distance.max()),
        "faces_outside_the_drawn_radius": int(centroids.shape[0] - inside.size),
        "drawn_radius_m": float(radius_m),
    }


def _store_array_fields(payload: dict[str, Any], prefix: str, layer: dict[str, Any]) -> None:
    for name, value in layer.items():
        if isinstance(value, np.ndarray):
            payload[f"{prefix}_{name}"] = value


def _optional_directory_manifest(directory: pathlib.Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if directory is None:
        return None, None
    path = directory / "manifest.json"
    if not path.exists():
        return None, f"auxiliary manifest is missing: {path.relative_to(SCRIPT_DIR)}"
    return json.loads(path.read_text()), None


def _attach_evidence_pose(
    site: str, payload: dict[str, Any], report: dict[str, Any], directories: dict[str, pathlib.Path]
) -> dict[str, Any] | None:
    pose = evidence_pose(site, directories)
    if pose is None:
        return None
    report["camera"] = {
        "position_enu_m": pose["position"].tolist(),
        "position_source": pose["position_source"],
        "pose_file": pose["pose_file"],
        "pose_file_position_enu_m": pose["pose_file_position_enu_m"],
        "drift_since_evidence_m": pose["drift_since_evidence_m"],
    }
    payload["evidence_camera"] = pose["position"].astype(np.float32)
    return pose


def _attach_one_fishnet(
    site: str,
    kind: str,
    directory: pathlib.Path,
    taxonomy: pathlib.Path | None,
    payload: dict[str, Any],
    report: dict[str, Any],
) -> None:
    source = str(directory.relative_to(SCRIPT_DIR))
    status = report["layer_status"]
    if taxonomy is None or not taxonomy.exists():
        wanted = (
            f"data/panoramas/{site}/semantics/semantics.json or a per-capture copy"
            if kind == "vistas"
            else f"outputs/{site}_sam3_projection_inputs/semantics.json"
        )
        reason = f"taxonomy sidecar is missing: {wanted}"
        status[f"fishnet_{kind}"] = {"status": "skipped", "directory": source, "reason": reason}
        print(f"[evidence] skipped fishnet {kind}: {reason}", flush=True)
        return
    if not any(directory.glob(FISHNET_SURFACE_GLOB)):
        reason = "directory contains no top-level *_fishnet.npz surfaces"
        status[f"fishnet_{kind}"] = {"status": "skipped", "directory": source, "reason": reason}
        print(f"[evidence] skipped fishnet {kind}: {reason} under {directory.name}", flush=True)
        return
    names = read_taxonomy(taxonomy)
    count = max(names) + 1
    layer = fishnet_layer(directory, count)
    _store_array_fields(payload, f"fishnet_{kind}", layer)
    report[f"fishnet_{kind}"] = {
        "directory": source,
        "views": layer["views"],
        "faces": int(layer["faces"].shape[0]),
        "class_names": [names.get(index, f"class {index}") for index in range(count)],
        "median_confidence": float(np.median(layer["confidence"])),
        "confidence_p05": float(np.percentile(layer["confidence"], 5.0)),
        "faces_dropped_as_degenerate_or_duplicate": layer["dropped_faces"],
        "faces_with_a_mixed_posterior": int((layer["entropy_bits"] > 0.05).sum()),
        "max_entropy_bits": float(layer["entropy_bits"].max()),
        "faces_below_half_visible": int((layer["visible_fraction"] < 0.5).sum()),
    }
    status[f"fishnet_{kind}"] = {"status": "built", "directory": source, "faces": int(layer["faces"].shape[0])}
    print(f"[evidence] fishnet {kind}: {layer['faces'].shape[0]} faces over {len(layer['views'])} views", flush=True)


def _support_skip_reason(vistas: pathlib.Path, taxonomy: pathlib.Path | None, report: dict[str, Any]) -> str:
    fishnet_status = report["layer_status"].get("fishnet_vistas", {})
    if fishnet_status.get("status") == "skipped":
        return f"Vistas fishnet was skipped: {fishnet_status['reason']}"
    if taxonomy is None or not taxonomy.exists():
        return "Vistas taxonomy sidecar is missing"
    if support_mesh_of(vistas) is None:
        return "fishnet manifest does not resolve to an existing support mesh"
    return "fishnet produced no drawable support evidence"


def _attach_support(
    args: Any,
    payload: dict[str, Any],
    report: dict[str, Any],
    vistas: pathlib.Path | None,
    taxonomy: pathlib.Path | None,
) -> None:
    if vistas is None:
        return
    support = None
    if taxonomy is not None and taxonomy.exists() and "fishnet_vistas_vertices" in payload:
        support = support_evidence_layer(vistas, max(read_taxonomy(taxonomy)) + 1)
    if support is None:
        reason = _support_skip_reason(vistas, taxonomy, report)
        for name in ("support_evidence", "rejected"):
            report["layer_status"][name] = {
                "status": "skipped",
                "directory": str(vistas.relative_to(SCRIPT_DIR)),
                "reason": reason,
            }
        print(f"[evidence] skipped support and refused layers: {reason}", flush=True)
        return
    refused = rejected_layer(vistas)
    if refused is None:
        raise RuntimeError("support evidence resolved but its refused-face layer did not")
    _store_array_fields(payload, "support_evidence", support)
    _store_array_fields(payload, "rejected", refused)
    report["rejected"] = {
        "reason_names": refused["reason_names"],
        "reason_codes": refused["reason_codes"],
        "triangles": int(refused["faces"].shape[0]),
        "geometry_source_names": refused["geometry_source_names"],
        "geometry_kind_names": refused["geometry_kind_names"],
        "fishnet_format_versions": refused["fishnet_format_versions"],
        "views": refused["view_names"],
        "exact_fragment_triangles": int(np.count_nonzero(refused["geometry_source"] == 1)),
        "legacy_source_triangle_fallbacks": int(np.count_nonzero(refused["geometry_source"] == 0)),
        "unavailable_rows_by_reason": {
            refused["reason_names"][code - 1]: count for code, count in refused["unavailable_rows_by_reason"].items()
        },
        "unavailable_image_area_px_by_reason": {
            refused["reason_names"][code - 1]: area
            for code, area in refused["unavailable_image_area_px_by_reason"].items()
        },
        "image_area_px_by_reason": {
            refused["reason_names"][code - 1]: float(refused["image_area_px"][refused["reason"] == code].sum())
            for code in np.unique(refused["reason"])
        },
    }
    report["support_evidence"] = {
        "triangles": int(support["faces"].shape[0]),
        "clean_px": float(support["clean_px"].sum()),
        **{f"{name}_px": float(support[f"{name}_px"].sum()) for name in REJECTION_GROUPS},
        "grouping": {name: list(reasons) for name, reasons in REJECTION_GROUPS.items()},
    }
    source = str(vistas.relative_to(SCRIPT_DIR))
    for name, layer in (("support_evidence", support), ("rejected", refused)):
        report["layer_status"][name] = {
            "status": "built",
            "directory": source,
            "triangles": int(layer["faces"].shape[0]),
        }
    centroids = payload["fishnet_vistas_vertices"][payload["fishnet_vistas_faces"]].mean(axis=1)
    report["semantic_surface_offset_from_drawn_mesh"] = surface_offset_to_drawn_mesh(
        payload, centroids.astype(np.float64), float(args.draw_radius_m)
    )
    print(
        f"[evidence] refused {refused['faces'].shape[0]} support triangles, {support['faces'].shape[0]} touched",
        flush=True,
    )


def _attach_mesh_depth(
    args: Any,
    payload: dict[str, Any],
    report: dict[str, Any],
    directories: dict[str, pathlib.Path],
    pose: dict[str, Any] | None,
) -> None:
    directory = directories.get("mesh_depth")
    if directory is None:
        return
    cloud = None
    if pose is not None:
        cloud = depth_cloud(
            directory, "range_m", pose, stride=args.depth_stride, decision_directory=directories.get("depth_gated")
        )
    if cloud is None:
        reason = "no evidence camera pose is available" if pose is None else "no NPZ contains a drawable range_m array"
        report["layer_status"]["depth_mesh"] = {
            "status": "skipped",
            "directory": str(directory.relative_to(SCRIPT_DIR)),
            "reason": reason,
        }
        print(f"[evidence] skipped mesh depth cloud: {reason}", flush=True)
        return
    _store_array_fields(payload, "depth_mesh", cloud)
    gated = directories.get("depth_gated")
    gated_manifest, gated_problem = _optional_directory_manifest(gated)
    report["depth_mesh"] = {
        "points": int(cloud["points"].shape[0]),
        "stride_px": args.depth_stride,
        "meaning": (
            "the mesh first hit the twin actually uses, coloured by the compatible fused depth decision"
            if gated is not None
            else "the mesh first hit the twin actually uses; no image-shape-compatible fused decision map exists"
        ),
        "decisions": gated_manifest.get("decisions") if gated_manifest else None,
    }
    report["layer_status"]["depth_mesh"] = {
        "status": "built_partial" if gated_problem else "built",
        "directory": str(directory.relative_to(SCRIPT_DIR)),
        "points": int(cloud["points"].shape[0]),
    }
    if gated_problem:
        report["layer_status"]["depth_mesh"]["reason"] = gated_problem
    print(f"[evidence] mesh first hit cloud: {cloud['points'].shape[0]} points", flush=True)


def _attach_monocular_depth(
    args: Any,
    payload: dict[str, Any],
    report: dict[str, Any],
    directories: dict[str, pathlib.Path],
    pose: dict[str, Any] | None,
) -> None:
    directory = directories.get("depth_ungated")
    if directory is None:
        return
    cloud = None
    if pose is not None:
        cloud = depth_cloud(
            directory,
            "unidepth_scaled_range_m",
            pose,
            stride=args.depth_stride,
            decision_directory=directory,
            extra=("z_score", "mesh_range_m"),
        )
    if cloud is None:
        reason = (
            "no evidence camera pose is available"
            if pose is None
            else "no NPZ contains a drawable unidepth_scaled_range_m array"
        )
        report["layer_status"]["depth_monocular"] = {
            "status": "skipped",
            "directory": str(directory.relative_to(SCRIPT_DIR)),
            "reason": reason,
        }
        print(f"[evidence] skipped monocular depth cloud: {reason}", flush=True)
        return
    _store_array_fields(payload, "depth_monocular", cloud)
    gated = directories.get("depth_gated")
    gated_manifest, gated_problem = _optional_directory_manifest(gated)
    plausibility = gated_manifest.get("scale_plausibility") if gated_manifest else None
    report["depth_monocular"] = {
        "points": int(cloud["points"].shape[0]),
        "stride_px": args.depth_stride,
        "meaning": (
            "the monocular surface at its per view fitted scale, which is the surface the "
            "plausibility gate refused. It is drawn so the refusal can be seen rather than "
            "taken on trust, and it is not evidence the twin uses."
        ),
        "scale_plausibility": plausibility,
    }
    report["layer_status"]["depth_monocular"] = {
        "status": "built_partial" if gated_problem else "built",
        "directory": str(directory.relative_to(SCRIPT_DIR)),
        "points": int(cloud["points"].shape[0]),
    }
    if gated_problem:
        report["layer_status"]["depth_monocular"]["reason"] = gated_problem
    print(f"[evidence] refused monocular cloud: {cloud['points'].shape[0]} points", flush=True)


def record_excluded_evidence_statuses(report: dict[str, Any]) -> None:
    """Record optional evidence that was present but failed family matching."""
    statuses = report.setdefault("layer_status", {})
    if "depth_monocular" in statuses:
        return
    family = report.get("family", {})
    excluded = family.get("excluded", {}) if isinstance(family, dict) else {}
    reason = excluded.get("depth_ungated") if isinstance(excluded, dict) else None
    if reason is None:
        reason = "no mesh, pose, view-ID, and image-shape matched monocular-depth artifact was found"
    statuses["depth_monocular"] = {
        "status": "absent",
        "reason": f"No matched monocular-depth layer was admitted: {reason}",
        "evidence_policy": "only a mesh, pose, view-ID, and image-shape matched family may be displayed",
    }


def _attach_registration(
    site: str,
    payload: dict[str, Any],
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    audit_name = "outputs/registration_sky_conflict.json"
    gate = stamp_surface_atlas_admission(manifest)
    registration = registration_layer(site, gate)
    if registration is None:
        reason = (
            "audit contains no usable pose files registered against this site's mesh"
            if (OUTPUTS / "registration_sky_conflict.json").exists()
            else f"registration audit is missing: {audit_name}"
        )
        report["layer_status"]["registration"] = {"status": "skipped", "audit": audit_name, "reason": reason}
        print(f"[evidence] skipped panorama captures: {reason}", flush=True)
        return
    for name in ("position", "rotation", "sigma_vectors", "verdict", "residual_deg", "sky_conflict"):
        payload[f"pano_{name}"] = registration[name]
    admitted_captures = [record["capture"] for record in registration["records"] if record["admitted"]]
    atlas = manifest.get("surface_atlas")
    atlas_reference = None
    if isinstance(atlas, dict):
        atlas_camera_ids = list(atlas.get("camera_ids", []))
        atlas_manifest = atlas.get("manifest")
        atlas_manifest_sha256 = atlas_manifest.get("sha256") if isinstance(atlas_manifest, dict) else None
        cohort_matches = set(admitted_captures) == set(atlas_camera_ids) and len(admitted_captures) == len(
            atlas_camera_ids
        )
        if gate.version == LEGACY_ADMISSION_GATE_VERSION and atlas_manifest_sha256 in SEALED_LEGACY_ADMISSION_MANIFESTS:
            if not cohort_matches:
                raise ValueError("sealed legacy registration cohort differs from the exact surface-atlas cameras")
            admitted_captures = atlas_camera_ids
        atlas_reference = {
            "manifest_sha256": atlas_manifest_sha256,
            "content_sha256": atlas.get("content_sha256"),
            "camera_ids": atlas_camera_ids,
            "admission": gate.as_dict(),
            "admitted_cohort_matches": cohort_matches,
        }
    report["registration"] = {
        "poses": registration["records"],
        "verdict_codes": VERDICT_CODES,
        "reading": registration["reading"],
        "audit": audit_name,
        "admission": registration["admission"],
        "admitted_captures": admitted_captures,
        "surface_atlas_reference": atlas_reference,
    }
    report["layer_status"]["registration"] = {
        "status": "built",
        "audit": audit_name,
        "poses": len(registration["records"]),
        "admission_version": gate.version,
        "admitted_captures": len(admitted_captures),
    }
    print(f"[evidence] {len(registration['records'])} registered poses", flush=True)


def _attach_bodies(payload: dict[str, Any], report: dict[str, Any], directory: pathlib.Path | None) -> None:
    if directory is None:
        return
    bodies = body_layer(directory)
    source = str(directory.relative_to(SCRIPT_DIR))
    if bodies is None:
        reason = (
            "dynamic body manifest is missing"
            if not (directory / "dynamic_bodies_manifest.json").exists()
            else "dynamic body manifest names no existing body NPZ files"
        )
        report["layer_status"]["bodies"] = {"status": "skipped", "directory": source, "reason": reason}
        print(f"[evidence] skipped bystander bodies: {reason}", flush=True)
        return
    payload["body_layer_vertices"] = bodies["vertices"]
    payload["body_layer_faces"] = bodies["faces"]
    report["bodies"] = {
        "count": int(bodies["vertices"].shape[0]),
        "triangles_each": int(bodies["faces"].shape[0]),
        "statures_m": [record["stature_m"] for record in bodies["records"]],
        "placed_range_m": [record["placed_range_m"] for record in bodies["records"]],
        "records": bodies["records"],
    }
    missing = bodies["missing_body_ids"]
    status = {
        "status": "built_partial" if missing else "built",
        "directory": source,
        "count": int(bodies["vertices"].shape[0]),
        "missing_body_ids": missing,
    }
    if missing:
        status["reason"] = "body NPZ files are missing for the listed IDs"
    report["layer_status"]["bodies"] = status
    print(f"[evidence] {bodies['vertices'].shape[0]} SMPL-X bystanders", flush=True)


def attach_evidence(args: Any, bundle: dict[str, Any]) -> None:
    """Add every evidence layer that exists for this site to the payload."""
    payload, manifest = bundle["payload"], bundle["manifest"]
    stamp_surface_atlas_admission(manifest)
    directories, family = select_evidence_family(args.site)
    report: dict[str, Any] = {
        "found": {key: str(path.relative_to(SCRIPT_DIR)) for key, path in sorted(directories.items())},
        "family": family,
        "layer_status": {},
        "note": "layers here are read from disk, not recomputed; see PAYLOAD.md",
    }
    manifest["evidence"] = report
    if not directories:
        print("[evidence] nothing on disk for this site", flush=True)
        return
    pose = _attach_evidence_pose(args.site, payload, report, directories)
    taxonomies = {
        "vistas": taxonomy_file(args.site),
        "sam3": OUTPUTS / f"{args.site}_sam3_projection_inputs" / "semantics.json",
    }
    for kind, key in (("vistas", "fishnet_vistas"), ("sam3", "fishnet_sam3")):
        if directory := directories.get(key):
            _attach_one_fishnet(args.site, kind, directory, taxonomies[kind], payload, report)
    _attach_support(args, payload, report, directories.get("fishnet_vistas"), taxonomies["vistas"])
    _attach_mesh_depth(args, payload, report, directories, pose)
    _attach_monocular_depth(args, payload, report, directories, pose)
    record_excluded_evidence_statuses(report)
    _attach_registration(args.site, payload, report, manifest)
    _attach_bodies(payload, report, directories.get("bodies"))


def reopen(args: Any, *, output_stem: str | None = None) -> dict[str, Any]:
    """Load a payload that was already traced, so the evidence can be rebuilt alone.

    Tracing Times Square is two hours on this machine and gathering its evidence
    is seconds. When only the second half changes, and it changed twice tonight,
    retracing to pick the change up is the wrong shape of loop.
    """
    stem = output_stem or args.site
    payload_path = args.out / f"{stem}_payload.npz"
    manifest_path = args.out / f"{stem}_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    with np.load(payload_path) as stored:
        verify_bundle_identity(stored, manifest)
        payload = {
            name: np.array(stored[name], copy=True) for name in stored.files if not name.startswith(EVIDENCE_PREFIXES)
        }
    manifest.pop("evidence", None)
    print(f"[reopen] {payload_path.name}, {len(payload)} traced arrays kept", flush=True)
    return {"payload": payload, "manifest": manifest}


def measure_rim(args: Any) -> dict[str, Any]:
    """Measure the facade tip rim into a payload that was already traced.

    The rim is one ray fan and takes a fifth of a second. Retracing Times Square
    to pick one up is two hours, and the trace is unchanged by it, so this
    reopens the payload whole, keeps every array in it including the evidence,
    and adds the six the rim needs.
    """
    payload_path = args.out / f"{args.site}_payload.npz"
    manifest_path = args.out / f"{args.site}_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    with np.load(payload_path) as stored:
        verify_bundle_identity(stored, manifest)
        payload = {name: np.array(stored[name], copy=True) for name in stored.files}
    bundle: dict[str, Any] = {
        "payload": payload,
        "manifest": manifest,
    }
    geometry = MitsubaGeometry(SCRIPT_DIR / manifest["mesh"], variant=args.variant)
    hero = bundle["payload"]["hero_point"].astype(np.float64)
    rim = facade_tip_rim(geometry, hero)
    store_rim(bundle, rim)
    connections = next_event_connections(
        geometry,
        bundle["payload"]["path_vertices"],
        bundle["payload"]["path_offsets"],
        rim,
        hero,
        paths=args.nee_paths,
        seed=args.seed,
    )
    store_connections(bundle, connections)
    print(
        f"[rim] {args.site}: direct term {rim['summary']['direct_term']:.5f}, "
        f"tip {rim['summary']['alpha_deg_median']:.1f} deg up at "
        f"{rim['summary']['distance_m_median']:.1f} m, sky implied "
        f"{rim['summary']['sky_fraction_implied']:.4f} against "
        f"{manifest['hero']['sky_fraction']:.4f} cast",
        flush=True,
    )
    print(
        f"[nee] {connections['summary']['connections']} connections from "
        f"{connections['summary']['paths_drawn']} paths, "
        f"{connections['summary']['blocked_fraction']:.2f} blocked, "
        f"{connections['summary']['blocked_fraction_from_the_head']:.2f} of those from the head",
        flush=True,
    )
    return bundle


def reopen_production(args: Any, data: ProductionData, run: RunConfig) -> tuple[dict[str, Any], str]:
    """Reopen the exact digest-named payload for a validated production run."""
    args.site = run.site
    output_stem = f"{run.site}_{run.frequency_ghz:g}ghz_{run.digest()}"
    bundle = reopen(args, output_stem=output_stem)
    recorded = bundle["manifest"].get("production_exposure")
    expected = production_provenance(data, run)["production_exposure"]
    if recorded != expected:
        raise ValueError("existing visualization payload does not match the named production exposure files")
    return bundle, output_stem


def publish_bundle(
    payload_path: pathlib.Path,
    manifest_path: pathlib.Path,
    payload: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    """Stamp and safely replace both files of one checked visualization bundle."""
    identity = stamp_bundle_identity(payload, manifest)
    payload_fd, payload_name = tempfile.mkstemp(prefix=f".{payload_path.name}.", suffix=".tmp", dir=payload_path.parent)
    manifest_fd, manifest_name = tempfile.mkstemp(
        prefix=f".{manifest_path.name}.", suffix=".tmp", dir=manifest_path.parent
    )
    try:
        with os.fdopen(payload_fd, "wb") as handle:
            np.savez_compressed(handle, **payload)
            handle.flush()
            os.fsync(handle.fileno())
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, indent=2, default=float) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Each rename is atomic. A reader that lands between them rejects the
        # crossed pair through verify_bundle_identity instead of building it.
        os.replace(payload_name, payload_path)
        os.replace(manifest_name, manifest_path)
    finally:
        for temporary in (payload_name, manifest_name):
            try:
                pathlib.Path(temporary).unlink()
            except FileNotFoundError:
                pass
    return identity


def export(args: Any) -> int:
    """Build and serialize the payload requested by a command namespace."""
    args.out.mkdir(parents=True, exist_ok=True)
    output_stem = args.site
    if args.rim_only:
        bundle = measure_rim(args)
    else:
        if getattr(args, "production_files", None) is not None:
            data, run = load_production_run(args.production_files)
            # The named production run is authoritative. This also lets an exact
            # three-file input for another city work without repeating --site.
            args.site = run.site
            output_stem = f"{run.site}_{run.frequency_ghz:g}ghz_{run.digest()}"
            if args.evidence_only:
                bundle, output_stem = reopen_production(args, data, run)
            else:
                bundle = trace_production_site(args, data, run)
        else:
            bundle = reopen(args) if args.evidence_only else trace_site(args)
        if args.evidence:
            attach_evidence(args, bundle)
    payload_path = args.out / f"{output_stem}_payload.npz"
    manifest_path = args.out / f"{output_stem}_manifest.json"
    identity = publish_bundle(payload_path, manifest_path, bundle["payload"], bundle["manifest"])
    size_mb = payload_path.stat().st_size / 1e6
    print(f"[done] {payload_path} ({size_mb:.1f} MB) and {manifest_path.name}, bundle {identity[:12]}")
    return 0
