"""Stage one of the propagation walkthrough blend: trace, and write a payload.

This produces the numbers a Blender scene needs to show how the estimator
works at one site, plus the image side evidence the twin was built from. It
runs the same tracer, the same walk builder, the same surface binding and the
same body coupler as ``run_exposure.py``, so what the blend draws is what the
study computed rather than an illustration of it.

Two things are traced per site. Every walk location is traced at production ray
count and reduced to its scalars, which is what colours the walk. One hero
location is traced again with a :class:`PathRecorder` attached, which keeps the
polyline of a capped number of rays. The recorder is a passive observer and the
test suite asserts that attaching it returns a bit identical result, so the rays
in the blend are the rays that were integrated.

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

Then hand the payload to Blender::

    ~/blender-4.5/blender --background --python propagation_blender.py -- \
        --payload outputs/propagation_viz/korenmarkt_payload.npz \
        --blend outputs/propagation_viz/korenmarkt_propagation.blend
"""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any

import numpy as np

from semantic_twin.exposure import BodyCoupler
from semantic_twin.exposure.study import (
    MODELS,
    PHANTOM,
    PHANTOM_MASS_KG,
    REFERENCE_S0_W_M2,
    ground_datum,
    site_mesh,
)
from semantic_twin.illumination.roofline import silhouette as skyline
from semantic_twin.materials import CLASS_NAMES, classify_faces, load_table
from semantic_twin.propagation import (
    TERMINATIONS,
    MitsubaGeometry,
    PathRecorder,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset
from semantic_twin.walk.site import site_walk

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[3]

CONFIG = SCRIPT_DIR / "config"
OUTPUT = SCRIPT_DIR / "outputs" / "propagation_viz"

#: The blend is meant to be opened on a laptop, so the shell that gets drawn is
#: smaller than the shell that gets traced. Occlusion at the far edge of a 250 m
#: crop changes the numbers and is why the crop is 250 m, but it is off camera
#: and carrying it would triple the file for nothing visible. The traced radius
#: is recorded in the payload so the blend can say which is which.
DEFAULT_DRAW_RADIUS_M = 110.0


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
        "weight_max": float(weight.max()),
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
    # Paths that bounced at least once, so the picture shows the connections a
    # ray makes after it has left the head and not only the fan from the head.
    pool = np.flatnonzero(lengths >= 3)
    if pool.size < paths:
        pool = np.arange(lengths.size)
    pick = np.unique(pool[np.linspace(0, pool.size - 1, min(paths, pool.size)).round().astype(int)])

    tip = standpoint + rim["offset"]
    available = np.flatnonzero(rim["found"])
    rng = np.random.default_rng(seed)

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


def body_field(coupler: BodyCoupler, result: Any, model: str) -> dict[str, np.ndarray]:
    """Per triangle absorbed power density on the phantom, plus its geometry.

    ``BodyMesh`` holds a triangle soup, ``(n_triangles, 3, 3)``, so the faces
    handed to Blender are the trivial index triples. That triples the vertex
    count against a shared mesh and it is the right trade here, because
    ``Sab`` is a per triangle quantity and a shared vertex would have to average
    across the faces that meet at it.
    """
    from aegis.paths import PropagationPaths

    power = result.rho[model] * result.local_solid_angle * REFERENCE_S0_W_M2
    keep = power > 0.0
    paths = PropagationPaths.from_powers(-result.local_grid[keep], power[keep])
    dosimetry = coupler.engine.compute(coupler.body, paths, level=coupler.level, body_mass=coupler.body_mass_kg)
    corners = np.asarray(coupler.body.vertices, dtype=np.float64)
    count = corners.shape[0]
    return {
        "vertices": corners.reshape(-1, 3),
        "faces": np.arange(3 * count, dtype=np.int64).reshape(count, 3),
        "sab": np.asarray(dosimetry.sab, dtype=np.float64),
    }


# ---------------------------------------------------------------------------
# Evidence layers. Everything below reads artifacts the pipeline already wrote
# and recomputes none of them.
# ---------------------------------------------------------------------------

OUTPUTS = SCRIPT_DIR / "outputs"

#: Sky conflict verdict thresholds, taken from the reading note the audit writes
#: into ``outputs/registration_sky_conflict.json`` rather than invented here: a
#: healthy pose sits below a few percent, and a pose above half has the camera
#: inside the geometry, in which case its skyline residual is not an error bar.
POSE_SUSPECT_SKY_CONFLICT = 0.05
POSE_UNUSABLE_SKY_CONFLICT = 0.5

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


def evidence_directories(site: str) -> dict[str, pathlib.Path]:
    """Which evidence products exist for a site, by convention on the name.

    The fused fishnet is preferred over the unfused one because it is built from
    the gated depth decisions, which is what the gate produces at a site whose
    monocular scale was refused. A site with none of these directories exports
    the propagation layers alone and nothing here raises.
    """
    candidates = {
        "fishnet_vistas": (f"{site}_fishnet_vistas_fused", f"{site}_fishnet_vistas"),
        "fishnet_sam3": (f"{site}_fishnet_sam3",),
        "mesh_depth": (f"{site}_mesh_depth",),
        "depth_gated": (f"{site}_depth_fused",),
        "depth_ungated": (f"{site}_depth_consistency_two_models",),
        "bodies": (f"{site}_dynamic_bodies",),
    }
    found: dict[str, pathlib.Path] = {}
    for key, names in candidates.items():
        for name in names:
            if (OUTPUTS / name).is_dir():
                found[key] = OUTPUTS / name
                break
    return found


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
        views = sorted(fishnet.glob("*_fishnet.npz"))
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
    files = sorted(directory.glob("*_fishnet.npz"))
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
    layer["views"] = [path.name.replace("_fishnet.npz", "") for path in files]
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
    for name in ("fishnet_manifest.json", "site_fishnet_manifest.json"):
        path = directory / name
        if not path.exists():
            continue
        stated = SCRIPT_DIR / json.loads(path.read_text())["mesh"]
        if stated.exists():
            return stated
    for path in sorted(directory.glob("*/fishnet_manifest.json")):
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

    for path in sorted(directory.glob("*_fishnet.npz")):
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

    Deduplicated on the pair of source triangle and reason, because one triangle
    is refused once per view and often in several pieces within a view, and
    drawing it once per row would put ten coincident copies of the same wall in
    the scene. The image area is summed over the rows that were merged.
    """
    from semantic_twin.scene.fishnet import REJECTION_REASONS

    import trimesh

    support = support_mesh_of(directory)
    if support is None:
        return None
    mesh = trimesh.load(support, process=False, force="mesh")
    pairs: dict[tuple[int, int], float] = {}
    for path in sorted(directory.glob("*_fishnet.npz")):
        surface = np.load(path)
        for triangle, reason, area in zip(
            surface["rejected_source_triangle"].astype(int),
            surface["rejected_reason"].astype(int),
            surface["rejected_image_area_px"].astype(float),
            strict=True,
        ):
            pairs[(int(triangle), int(reason))] = pairs.get((int(triangle), int(reason)), 0.0) + area
    ordered = sorted(pairs)
    triangles = np.array([pair[0] for pair in ordered], dtype=np.int64)
    reasons = np.array([pair[1] for pair in ordered], dtype=np.int16)
    areas = np.array([pairs[pair] for pair in ordered], dtype=np.float32)
    vertices, faces = triangle_soup(np.asarray(mesh.vertices), np.asarray(mesh.faces), triangles)
    return {
        "vertices": vertices.astype(np.float32),
        "faces": faces,
        "reason": reasons,
        "image_area_px": areas,
        "reason_names": [name for name, _ in sorted(REJECTION_REASONS.items(), key=lambda item: item[1])],
        "reason_codes": [code for _, code in sorted(REJECTION_REASONS.items(), key=lambda item: item[1])],
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


def registration_layer(site: str) -> dict[str, Any] | None:
    """Every pose registered against this site's geometry, with its covariance.

    The audit table is the filter: a pose belongs here when the mesh it was
    aligned against is this site's, which picks up the twelve walk captures at
    Korenmarkt alongside the one the semantics were run on. The position block of
    the seed study covariance becomes an ellipsoid, and the sky conflict fraction
    becomes the verdict, so a camera that sits inside the geometry is visible as
    such instead of being averaged into a residual.
    """
    from semantic_twin.pano_geometry import panorama_to_world_matrix

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
        conflict = float(row["sky_with_mesh_hit_fraction"])
        verdict = "usable"
        if conflict > POSE_UNUSABLE_SKY_CONFLICT:
            verdict = "camera inside the geometry"
        elif conflict > POSE_SUSPECT_SKY_CONFLICT:
            verdict = "suspect"
        records.append(
            {
                "capture": row["capture"],
                "pose_file": row["pose_file"],
                "position_enu_m": positions[-1].tolist(),
                "skyline_residual_deg": row["skyline_residual_deg"],
                "sky_with_mesh_hit_fraction": conflict,
                "conflict_median_range_m": row.get("conflict_median_range_m"),
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
        "sky_conflict": np.array([record["sky_with_mesh_hit_fraction"] for record in records], dtype=np.float32),
        "records": records,
        "reading": document["reading"],
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

VERDICT_CODES = {"usable": 0, "suspect": 1, "camera inside the geometry": 2}


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
    vertices, faces = [], None
    for body in bodies:
        path = directory / f"{body['body_id']}.npz"
        if not path.exists():
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
    if not vertices or faces is None:
        return None
    return {
        "vertices": np.stack(vertices).astype(np.float32),
        "faces": np.asarray(faces, dtype=np.int32),
        "records": bodies[: len(vertices)],
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


def attach_evidence(args: Any, bundle: dict[str, Any]) -> None:
    """Add every evidence layer that exists for this site to the payload.

    Kept out of :func:`trace_site` on purpose. None of this is traced, none of it
    changes a traced number, and a site with no panorama still gets a blend.
    """
    payload, manifest = bundle["payload"], bundle["manifest"]
    directories = evidence_directories(args.site)
    report: dict[str, Any] = {
        "found": {key: str(path.relative_to(SCRIPT_DIR)) for key, path in sorted(directories.items())},
        "note": "layers here are read from disk, not recomputed; see PAYLOAD.md",
    }
    manifest["evidence"] = report
    if not directories:
        print("[evidence] nothing on disk for this site", flush=True)
        return

    pose = evidence_pose(args.site, directories)
    if pose is not None:
        report["camera"] = {
            "position_enu_m": pose["position"].tolist(),
            "position_source": pose["position_source"],
            "pose_file": pose["pose_file"],
            "pose_file_position_enu_m": pose["pose_file_position_enu_m"],
            "drift_since_evidence_m": pose["drift_since_evidence_m"],
        }
        payload["evidence_camera"] = pose["position"].astype(np.float32)

    taxonomies = {
        "vistas": taxonomy_file(args.site),
        "sam3": OUTPUTS / f"{args.site}_sam3_projection_inputs" / "semantics.json",
    }
    for kind, key in (("vistas", "fishnet_vistas"), ("sam3", "fishnet_sam3")):
        directory = directories.get(key)
        if directory is None or taxonomies[kind] is None or not taxonomies[kind].exists():
            continue
        if not any(directory.glob("*_fishnet.npz")):
            # A fishnet directory can hold a manifest and no surfaces, because
            # the manifest is written whether or not the build succeeded. Tokyo
            # is the case on disk: four panoramas present, zero built. That is a
            # recorded failure rather than a programming error, so it is skipped
            # and named instead of reaching np.concatenate with nothing.
            print(f"no fishnet surfaces under {directory.name}, skipping the {kind} layer")
            continue
        names = read_taxonomy(taxonomies[kind])
        count = max(names) + 1
        layer = fishnet_layer(directory, count)
        for name, value in layer.items():
            if isinstance(value, np.ndarray):
                payload[f"fishnet_{kind}_{name}"] = value
        report[f"fishnet_{kind}"] = {
            "directory": str(directory.relative_to(SCRIPT_DIR)),
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
        print(
            f"[evidence] fishnet {kind}: {layer['faces'].shape[0]} faces over {len(layer['views'])} views", flush=True
        )

    vistas = directories.get("fishnet_vistas")
    taxonomy = taxonomies["vistas"]
    support = None
    if vistas is not None and taxonomy is not None and taxonomy.exists():
        support = support_evidence_layer(vistas, max(read_taxonomy(taxonomy)) + 1)
    if support is not None:
        for name, value in support.items():
            if isinstance(value, np.ndarray):
                payload[f"support_evidence_{name}"] = value
        refused = rejected_layer(vistas)
        for name, value in (refused or {}).items():
            if isinstance(value, np.ndarray):
                payload[f"rejected_{name}"] = value
        report["rejected"] = {
            "reason_names": refused["reason_names"],
            "reason_codes": refused["reason_codes"],
            "triangles": int(refused["faces"].shape[0]),
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
        centroids = payload["fishnet_vistas_vertices"][payload["fishnet_vistas_faces"]].mean(axis=1)
        report["semantic_surface_offset_from_drawn_mesh"] = surface_offset_to_drawn_mesh(
            payload, centroids.astype(np.float64), float(args.draw_radius_m)
        )
        print(
            f"[evidence] refused {refused['faces'].shape[0]} support triangles, {support['faces'].shape[0]} touched",
            flush=True,
        )

    cloud = (
        depth_cloud(
            directories["mesh_depth"],
            "range_m",
            pose,
            stride=args.depth_stride,
            decision_directory=directories.get("depth_gated"),
        )
        if pose is not None and "mesh_depth" in directories
        else None
    )
    if cloud is not None:
        for name, value in cloud.items():
            payload[f"depth_mesh_{name}"] = value
        gated = directories.get("depth_gated")
        report["depth_mesh"] = {
            "points": int(cloud["points"].shape[0]),
            "stride_px": args.depth_stride,
            "meaning": "the mesh first hit the twin actually uses, coloured by the fused depth decision",
            "decisions": json.loads((gated / "manifest.json").read_text())["decisions"] if gated else None,
        }
        print(f"[evidence] mesh first hit cloud: {cloud['points'].shape[0]} points", flush=True)

    cloud = (
        depth_cloud(
            directories["depth_ungated"],
            "unidepth_scaled_range_m",
            pose,
            stride=args.depth_stride,
            decision_directory=directories["depth_ungated"],
            extra=("z_score", "mesh_range_m"),
        )
        if pose is not None and "depth_ungated" in directories
        else None
    )
    if cloud is not None:
        for name, value in cloud.items():
            payload[f"depth_monocular_{name}"] = value
        gated = directories.get("depth_gated")
        plausibility = None
        if gated is not None:
            plausibility = json.loads((gated / "manifest.json").read_text()).get("scale_plausibility")
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
        print(f"[evidence] refused monocular cloud: {cloud['points'].shape[0]} points", flush=True)

    registration = registration_layer(args.site)
    if registration is not None:
        for name in ("position", "rotation", "sigma_vectors", "verdict", "residual_deg", "sky_conflict"):
            payload[f"pano_{name}"] = registration[name]
        report["registration"] = {
            "poses": registration["records"],
            "verdict_codes": VERDICT_CODES,
            "reading": registration["reading"],
            "audit": "outputs/registration_sky_conflict.json",
        }
        print(f"[evidence] {len(registration['records'])} registered poses", flush=True)

    if "bodies" in directories:
        bodies = body_layer(directories["bodies"])
        if bodies is not None:
            payload["body_layer_vertices"] = bodies["vertices"]
            payload["body_layer_faces"] = bodies["faces"]
            report["bodies"] = {
                "count": int(bodies["vertices"].shape[0]),
                "triangles_each": int(bodies["faces"].shape[0]),
                "statures_m": [record["stature_m"] for record in bodies["records"]],
                "placed_range_m": [record["placed_range_m"] for record in bodies["records"]],
                "records": bodies["records"],
            }
            print(f"[evidence] {bodies['vertices'].shape[0]} SMPL-X bystanders", flush=True)


def reopen(args: Any) -> dict[str, Any]:
    """Load a payload that was already traced, so the evidence can be rebuilt alone.

    Tracing Times Square is two hours on this machine and gathering its evidence
    is seconds. When only the second half changes, and it changed twice tonight,
    retracing to pick the change up is the wrong shape of loop.
    """
    payload_path = args.out / f"{args.site}_payload.npz"
    manifest_path = args.out / f"{args.site}_manifest.json"
    stored = np.load(payload_path)
    manifest = json.loads(manifest_path.read_text())
    manifest.pop("evidence", None)
    payload = {name: stored[name] for name in stored.files if not name.startswith(EVIDENCE_PREFIXES)}
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
    stored = np.load(payload_path)
    manifest = json.loads(manifest_path.read_text())
    bundle: dict[str, Any] = {
        "payload": {name: stored[name] for name in stored.files},
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


def export(args: Any) -> int:
    """Build and serialize the payload requested by a command namespace."""
    args.out.mkdir(parents=True, exist_ok=True)
    if args.rim_only:
        bundle = measure_rim(args)
    else:
        bundle = reopen(args) if args.evidence_only else trace_site(args)
        if args.evidence:
            attach_evidence(args, bundle)
    payload_path = args.out / f"{args.site}_payload.npz"
    np.savez_compressed(payload_path, **bundle["payload"])
    manifest_path = args.out / f"{args.site}_manifest.json"
    manifest_path.write_text(json.dumps(bundle["manifest"], indent=2, default=float) + "\n")
    size_mb = payload_path.stat().st_size / 1e6
    print(f"[done] {payload_path} ({size_mb:.1f} MB) and {manifest_path.name}")
    return 0
