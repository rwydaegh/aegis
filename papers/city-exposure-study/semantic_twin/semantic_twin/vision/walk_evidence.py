"""Build one twin from a walk of linked panoramas, and measure what that bought.

Stages, each independently runnable so a long acquisition is never repeated:

``select``    traverse the Mapillary sequence link graph and choose the walk
``download``  fetch the selected panoramas and write an initial pose for each
``fuse``      accumulate the walk's evidence and report the three comparisons

The comparisons are the point. Fusion raises every coverage number by
construction, so the report separates the union, which can only grow, from the
effective independent look count, which cannot be inflated by parking two
cameras next to each other.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass

import numpy as np

from semantic_twin import paths
from semantic_twin.acquire import load_support_mesh
from semantic_twin.acquire.mapillary import (
    download_panorama_image,
    pose_from_metadata,
    seed_sequence_ids,
    token,
    traverse,
)
from semantic_twin.scene.enu import EnuFrame
from semantic_twin.scene.site_config import load_scene
from semantic_twin.vision import captures

REPO = pathlib.Path(__file__).resolve().parents[2]
WALK_SELECTION_FILE = "walk_selection.json"
WALK_DOWNLOAD_FILE = "walk_download.json"


@dataclass(frozen=True)
class WalkEvidenceConfig:
    """Inputs shared by the independently runnable walk evidence stages."""

    stage: str
    permutations: int = 40
    recast: bool = False
    clean_majority: float = 0.5
    min_overlap_faces: int = 200
    max_residual_deg: float = 4.0
    grid_height: int = 1536
    workers: int = 4
    decorrelation_deg: float = 10.0
    independence_sample: int = 40000
    scene: str = str(REPO / "config/korenmarkt.json")
    mesh: str = "data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply"
    out: str = str(REPO / "outputs/walk_korenmarkt")
    panorama_root: str = str(REPO / "data/panoramas/korenmarkt_walk")
    radius_m: float = 60.0
    count: int = 12
    separation_m: float = 8.0
    per_sequence_cap: int = 6
    seed_half_width_m: float = 150.0
    seed_cells: int = 6


def _frame(scene: dict) -> EnuFrame:
    origin = scene["enu_origin"]
    return EnuFrame(float(origin["lat"]), float(origin["lon"]), float(origin.get("ellipsoid_height_m", 0.0)))


def _mesh_path(args: WalkEvidenceConfig, scene: dict) -> str:
    """Support mesh to trace against, defaulting to the scene's declared one.

    The default is overridable because coverage is measurably sensitive to it.
    The single-precision ``inhouse_leaf_130m.ply`` displaces whole tiles by up to
    0.61 m against the double-precision ``_f64`` build, which moves the fused
    area fraction by about 4.6 percent relative, downward. The rest of the study
    reads tile placement in double precision, so this does too.
    """
    if args.mesh:
        mesh = pathlib.Path(args.mesh)
        return str(mesh if mesh.is_absolute() else REPO / mesh)
    crop_m = round(float(scene["geometry_selection"]["crop_radius_m"]))
    return str(paths.site_mesh(str(scene["name"]), crop_m, root_dir=REPO))


def stage_select(args: WalkEvidenceConfig) -> None:
    scene = load_scene(pathlib.Path(args.scene))
    frame = _frame(scene)
    latitude = float(scene["location"]["lat"])
    longitude = float(scene["location"]["lon"])
    access_token = token()

    seeds = seed_sequence_ids(
        access_token,
        latitude=latitude,
        longitude=longitude,
        half_width_m=args.seed_half_width_m,
        cells=args.seed_cells,
    )
    sequences = seeds.sequence_ids
    print(f"[walk] {seeds.seed_images} panorama seeds name {len(sequences)} sequences", flush=True)
    images = traverse(access_token, sequences, progress=True)
    stations = captures.stations_from_images(
        images.values(), frame, target_lat=latitude, target_lon=longitude, radius_m=args.radius_m
    )
    chosen = captures.select_walk(
        stations, count=args.count, separation_m=args.separation_m, per_sequence_cap=args.per_sequence_cap
    )
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "site": scene["name"],
        "traversal": {
            "method": "Mapillary sequence link graph, seeded by a tiled bounding box and expanded by sequence id",
            "bbox_seed_panoramas": seeds.seed_images,
            "sequences_named": sorted(sequences),
            "images_after_expansion": len(images),
            "panoramas_in_radius": len(stations),
            "radius_m": args.radius_m,
            "note": (
                "The bounding-box endpoint is sampled and incomplete. Sequence expansion is what "
                "recovers the full membership, and the two counts above are not comparable."
            ),
        },
        "selection": {
            "count": args.count,
            "separation_m": args.separation_m,
            "per_sequence_cap": args.per_sequence_cap,
        },
        "spread": captures.spread(chosen),
        "stations": [station.summary() for station in chosen],
        "candidates": [station.summary() for station in sorted(stations, key=lambda s: s.range_m)],
    }
    (out / WALK_SELECTION_FILE).write_text(json.dumps(payload, indent=2))
    (out / "walk_metadata.json").write_text(json.dumps({s.image_id: s.metadata for s in chosen}, indent=2))
    (out / "walk_all_metadata.json").write_text(json.dumps({s.image_id: s.metadata for s in stations}, indent=2))
    print(json.dumps(payload["spread"], indent=2), flush=True)


def stage_download(args: WalkEvidenceConfig) -> None:
    out = pathlib.Path(args.out)
    selection = json.loads((out / WALK_SELECTION_FILE).read_text())
    metadata = json.loads((out / "walk_metadata.json").read_text())
    scene = load_scene(pathlib.Path(args.scene))
    support = load_support_mesh(scene)
    destination = pathlib.Path(args.panorama_root)
    written = []
    for index, station in enumerate(selection["stations"]):
        image_id = station["image_id"]
        folder = destination / f"walk_{index:02d}_{image_id}"
        folder.mkdir(parents=True, exist_ok=True)
        record = metadata[image_id]
        (folder / "metadata.json").write_text(json.dumps(record, indent=2))
        pose = pose_from_metadata(record, scene, support_mesh=support)
        (folder / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
        name = "panorama_original.jpg" if record.get("thumb_original_url") else "panorama_thumb_2048.jpg"
        if not (folder / name).exists():
            download_panorama_image(record, folder / name)
        written.append({"image_id": image_id, "folder": str(folder), "image": name, "pose": asdict(pose)})
        print(f"[walk] {index:02d} {image_id} tilt={pose.tilt_deg - 90.0:+.2f} deg -> {folder}", flush=True)
    (out / WALK_DOWNLOAD_FILE).write_text(json.dumps({"stations": written}, indent=2))


def _station_visibility(job: tuple) -> dict:
    """First-hit faces of a full sphere cast from one camera centre.

    The set of faces a panorama can see is a property of where the camera *is*,
    not of how it is turned: a full sphere has no outside. So this stage needs
    the position only, and inherits the position's uncertainty rather than the
    orientation's. That is what lets the coverage curve be computed before the
    skyline registration has run, and it is why the curve is not contingent on
    the registration succeeding.
    """
    import trimesh

    from semantic_twin.pano_geometry import equirectangular_directions

    mesh_path, position, grid_height, image_id = job
    mesh = trimesh.load(mesh_path, process=False)
    height, width = grid_height, 2 * grid_height
    camera = np.asarray(position, dtype=np.float64)
    directions = equirectangular_directions(width, height).reshape(-1, 3)
    origins = np.broadcast_to(camera, directions.shape)
    locations, _, index_tri = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    face_count = len(mesh.faces)

    rays = np.bincount(index_tri, minlength=face_count)
    seen = rays > 0
    # Viewing geometry of every hit, so that "seen" can be graded rather than
    # counted. A face caught at 70 m and 80 degrees off normal is in the union
    # but is not evidence of the same kind as one caught at 8 m head on.
    to_camera = camera - locations
    distance = np.linalg.norm(to_camera, axis=1)
    unit = to_camera / np.maximum(distance, 1e-9)[:, None]
    cosine = np.abs(np.einsum("ij,ij->i", unit, mesh.face_normals[index_tri]))
    best_cos = np.zeros(face_count)
    np.maximum.at(best_cos, index_tri, cosine)
    near = np.full(face_count, np.inf)
    np.minimum.at(near, index_tri, distance)
    return {
        "image_id": image_id,
        "seen": seen,
        "rays": rays.astype(np.int32),
        "best_cosine": best_cos.astype(np.float32),
        "nearest_range_m": near.astype(np.float32),
    }


def coverage_curve(seen: np.ndarray, area: np.ndarray, order: list[int]) -> list[dict]:
    """Directly observed fraction as panoramas are added one at a time.

    ``seen`` is ``[stations, faces]``. The curve is cumulative over ``order``, so
    the first entry is the single-capture baseline this walk is measured against
    and the last is the full fusion. Reporting the whole curve rather than the
    endpoint is what answers whether coverage saturates.
    """
    union = np.zeros(seen.shape[1], dtype=bool)
    total_area = float(area.sum())
    curve = []
    for count, index in enumerate(order, start=1):
        union |= seen[index]
        curve.append(
            {
                "n_panoramas": count,
                "added_image_index": int(index),
                "faces": int(union.sum()),
                "face_fraction": float(union.mean()),
                "area_fraction": float(area[union].sum() / total_area),
            }
        )
    return curve


def stage_fuse(args: WalkEvidenceConfig) -> None:
    from concurrent.futures import ProcessPoolExecutor

    import trimesh

    out = pathlib.Path(args.out)
    selection = json.loads((out / WALK_SELECTION_FILE).read_text())
    download = json.loads((out / WALK_DOWNLOAD_FILE).read_text())
    scene = load_scene(pathlib.Path(args.scene))
    mesh_path = _mesh_path(args, scene)
    mesh = trimesh.load(mesh_path, process=False)
    area = np.asarray(mesh.area_faces, dtype=float)
    face_count = len(mesh.faces)

    jobs = [
        (mesh_path, record["pose"]["position_enu_m"], args.grid_height, record["image_id"])
        for record in download["stations"]
    ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_station_visibility, jobs))
    order_ids = [record["image_id"] for record in download["stations"]]
    seen = np.stack([result["seen"] for result in results])
    cosine = np.stack([result["best_cosine"] for result in results])
    near = np.stack([result["nearest_range_m"] for result in results])
    np.savez_compressed(
        out / "walk_visibility.npz",
        image_ids=np.asarray(order_ids),
        seen=seen,
        rays=np.stack([result["rays"] for result in results]),
        best_cosine=cosine,
        nearest_range_m=near,
        face_area=area,
    )

    union = seen.any(axis=0)
    single = seen[0]
    stations = [captures.WalkStation(**{**record, "metadata": {}}) for record in selection["stations"]]
    centres = np.asarray(mesh.triangles_center, dtype=float)[:, :2]

    # Independence over the union faces only, which is where double counting
    # could occur at all.
    union_index = np.flatnonzero(union)
    sample = (
        union_index
        if len(union_index) <= args.independence_sample
        else np.random.default_rng(7).choice(union_index, args.independence_sample, replace=False)
    )
    parallax = captures.parallax_angles_deg(stations, centres[sample])
    independence = captures.parallax_independence(parallax, seen[:, sample].T, decorrelation_deg=args.decorrelation_deg)
    looks = captures.effective_looks(independence)
    raw = seen[:, sample].sum(axis=0)

    multi = raw >= 2
    report = {
        "site": scene["name"],
        "mesh": pathlib.Path(mesh_path).name,
        "support_faces": face_count,
        "grid_height": args.grid_height,
        "geometry_note": (
            "A full-sphere first-hit cast depends on camera position only, so these counts do not "
            "wait on the skyline registration and do not inherit its orientation covariance."
        ),
        "single_capture": {
            "image_id": order_ids[0],
            "faces": int(single.sum()),
            "face_fraction": float(single.mean()),
            "area_fraction": float(area[single].sum() / area.sum()),
        },
        "fused": {
            "n_panoramas": len(order_ids),
            "faces": int(union.sum()),
            "face_fraction": float(union.mean()),
            "area_fraction": float(area[union].sum() / area.sum()),
        },
        "curve": coverage_curve(seen, area, list(range(len(order_ids)))),
        "per_station": [
            {
                "image_id": order_ids[index],
                "range_from_centre_m": selection["stations"][index]["range_m"],
                "faces": int(seen[index].sum()),
                "face_fraction": float(seen[index].mean()),
                "area_fraction": float(area[seen[index]].sum() / area.sum()),
            }
            for index in range(len(order_ids))
        ],
        "independence": {
            "decorrelation_deg": args.decorrelation_deg,
            "sampled_union_faces": len(sample),
            "raw_looks_mean": float(raw.mean()),
            "effective_looks_mean": float(looks.mean()),
            "effective_over_raw": float(looks.sum() / raw.sum()),
            "faces_with_two_or_more_raw_looks": int(multi.sum()),
            "effective_looks_where_two_or_more": float(looks[multi].mean()) if multi.any() else 0.0,
            "note": (
                "Kish effective sample size under a parallax kernel. It is bounded above by the raw "
                "look count, so it can never inflate the evidence a union appears to supply."
            ),
        },
        "viewing_geometry": _geometry_split(cosine, near, area, single, union),
    }
    (out / "walk_coverage.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("single_capture", "fused", "independence")}, indent=2), flush=True)


def _geometry_split(cosine, near, area, single, union) -> dict:
    """Grade the newly covered faces, since a union counts weak looks too."""
    best_cos = cosine.max(axis=0)
    best_near = near.min(axis=0)
    gained = union & ~single

    def describe(mask, cos_source, range_source):
        if not mask.any():
            return {"faces": 0}
        angle = np.degrees(np.arccos(np.clip(cos_source[mask], 0.0, 1.0)))
        distance = range_source[mask]
        finite = np.isfinite(distance)
        return {
            "faces": int(mask.sum()),
            "incidence_deg": {
                "median": float(np.median(angle)),
                "p90": float(np.percentile(angle, 90)),
                "fraction_beyond_70_deg": float((angle > 70.0).mean()),
            },
            "range_m": {
                "median": float(np.median(distance[finite])),
                "p90": float(np.percentile(distance[finite], 90)),
                "fraction_beyond_40_m": float((distance[finite] > 40.0).mean()),
            },
            "area_fraction": float(area[mask].sum() / area.sum()),
        }

    return {
        "single_capture_faces": describe(single, cosine[0], near[0]),
        "faces_gained_by_fusion": describe(gained, best_cos, best_near),
        "all_fused_faces": describe(union, best_cos, best_near),
        "note": (
            "Coverage is not accuracy. A face is in the union if any panorama first-hits it, "
            "including at a grazing angle from far away, so the incidence and range distributions "
            "of the gained faces are reported next to the count."
        ),
    }


def saturation_curves(seen: np.ndarray, area: np.ndarray, *, permutations: int, rng_seed: int = 3) -> dict:
    """Coverage against panorama count, averaged over acquisition orders.

    Nearest-first is the order a real acquisition would use, but it is also the
    order most likely to manufacture an apparent saturation, because it spends
    its first captures where the surface is densest. Averaging over random orders
    separates the shape of the curve from the shape of the selection rule, and
    the spread across orders is the error bar on any claimed saturation point.
    """
    stations, faces = seen.shape
    total_area = float(area.sum())
    rng = np.random.default_rng(rng_seed)
    counts = np.zeros((permutations, stations))
    areas = np.zeros((permutations, stations))
    for trial in range(permutations):
        order = rng.permutation(stations)
        union = np.zeros(faces, dtype=bool)
        for position, index in enumerate(order):
            union |= seen[index]
            counts[trial, position] = union.sum()
            areas[trial, position] = area[union].sum() / total_area
    marginal = np.diff(counts.mean(axis=0), prepend=0.0)
    return {
        "permutations": permutations,
        "mean_faces": counts.mean(axis=0).tolist(),
        "mean_face_fraction": (counts.mean(axis=0) / faces).tolist(),
        "mean_area_fraction": areas.mean(axis=0).tolist(),
        "face_fraction_p10": (np.percentile(counts, 10, axis=0) / faces).tolist(),
        "face_fraction_p90": (np.percentile(counts, 90, axis=0) / faces).tolist(),
        "marginal_faces_per_panorama": marginal.tolist(),
    }


def stage_saturate(args: WalkEvidenceConfig) -> None:
    """Raycast every available panorama position and find where coverage stops paying."""
    from concurrent.futures import ProcessPoolExecutor

    import trimesh

    out = pathlib.Path(args.out)
    scene = load_scene(pathlib.Path(args.scene))
    frame = _frame(scene)
    metadata = json.loads((out / "walk_all_metadata.json").read_text())
    stations = captures.stations_from_images(
        metadata.values(),
        frame,
        target_lat=float(scene["location"]["lat"]),
        target_lon=float(scene["location"]["lon"]),
        radius_m=args.radius_m,
    )
    stations.sort(key=lambda station: station.range_m)
    print(f"[saturate] {len(stations)} panorama positions inside {args.radius_m:.0f} m", flush=True)

    mesh_path = _mesh_path(args, scene)
    support = load_support_mesh(scene)
    cache = out / "walk_saturation.npz"
    if cache.exists() and not args.recast:
        document = np.load(cache, allow_pickle=False)
        seen, ranges, image_ids = document["seen"], document["range_from_centre_m"], document["image_ids"]
        area = document["face_area"]
        order = [list(image_ids).index(station.image_id) for station in stations]
        seen, ranges = seen[order], ranges[order]
    else:
        jobs = []
        for station in stations:
            pose = pose_from_metadata(station.metadata, scene, support_mesh=support)
            jobs.append((mesh_path, pose.position_enu_m, args.grid_height, station.image_id))
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(_station_visibility, jobs))
        seen = np.stack([result["seen"] for result in results])
        ranges = np.array([station.range_m for station in stations])
        area = np.asarray(trimesh.load(mesh_path, process=False).area_faces, dtype=float)
        np.savez_compressed(
            cache,
            image_ids=np.asarray([station.image_id for station in stations]),
            seen=seen,
            range_from_centre_m=ranges,
            face_area=area,
        )

    report = {"site": scene["name"], "grid_height": args.grid_height, "arms": {}}
    for label, limit in (("within_60m", 60.0), ("within_80m", args.radius_m)):
        inside = ranges <= limit
        if inside.sum() < 2:
            continue
        subset = seen[inside]
        report["arms"][label] = {
            "radius_m": limit,
            "n_panoramas": int(inside.sum()),
            "nearest_first": coverage_curve(subset, area, list(range(len(subset)))),
            "random_order": saturation_curves(subset, area, permutations=args.permutations),
            "ceiling": {
                "faces": int(subset.any(axis=0).sum()),
                "face_fraction": float(subset.any(axis=0).mean()),
                "area_fraction": float(area[subset.any(axis=0)].sum() / area.sum()),
            },
        }
    report["interpretation"] = _saturation_verdict(report["arms"])
    (out / "walk_saturation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["interpretation"], indent=2), flush=True)


def _saturation_verdict(arms: dict) -> dict:
    """State plainly whether the curve has turned over, and what bounds it."""
    verdict = {}
    for label, arm in arms.items():
        marginal = np.asarray(arm["random_order"]["marginal_faces_per_panorama"], dtype=float)
        fraction = np.asarray(arm["random_order"]["mean_face_fraction"], dtype=float)
        n = len(marginal)
        late = marginal[max(1, n - 5) :].mean()
        verdict[label] = {
            "n_panoramas": arm["n_panoramas"],
            "ceiling_face_fraction": arm["ceiling"]["face_fraction"],
            "marginal_faces_first": float(marginal[1]) if n > 1 else 0.0,
            "marginal_faces_last_five": float(late),
            "marginal_decay_ratio": float(late / marginal[1]) if n > 1 and marginal[1] else 0.0,
            "panoramas_for_90_percent_of_ceiling": int(
                np.searchsorted(fraction, 0.9 * arm["ceiling"]["face_fraction"]) + 1
            ),
            "panoramas_for_95_percent_of_ceiling": int(
                np.searchsorted(fraction, 0.95 * arm["ceiling"]["face_fraction"]) + 1
            ),
        }
    return verdict


# Mapillary Vistas classes that are objects passing through the scene rather than
# the scene. These are what a second capture from a few metres away resolves,
# because they move between captures and the facade behind them does not.
TRANSIENT_CLASSES = (
    "Person",
    "Bicyclist",
    "Motorcyclist",
    "Other Rider",
    "Bicycle",
    "Boat",
    "Bus",
    "Car",
    "Caravan",
    "Motorcycle",
    "Other Vehicle",
    "Trailer",
    "Truck",
    "Wheeled Slow",
)


def _station_semantics(job: tuple) -> dict:
    """Bind every panorama pixel to a support-mesh face through the aligned pose.

    Unlike the coverage stage this one does need the orientation, so it consumes
    the skyline-registered pose and inherits its covariance. Stations whose
    registration is poor therefore contaminate the semantic result in a way they
    cannot contaminate the coverage result, which is why the two are reported
    separately rather than merged into one table.
    """
    import trimesh

    from semantic_twin.pano_geometry import equirectangular_directions, panorama_to_world_matrix

    mesh_path, pose, semantics_path, transient_ids, grid_height, image_id, material_count = job
    mesh = trimesh.load(mesh_path, process=False)
    height, width = grid_height, 2 * grid_height
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)
    directions = (equirectangular_directions(width, height).reshape(-1, 3)) @ rotation.T
    origins = np.broadcast_to(camera, directions.shape)
    _, index_ray, index_tri = mesh.ray.intersects_location(origins, directions, multiple_hits=False)

    rf_material = None
    material_source = None
    with np.load(semantics_path) as document:
        entity = document["entity"]
        # Present only for panoramas segmented with ``--backend hybrid``. The
        # dense pass alone cannot fill it: Mapillary Vistas has one ``Building``
        # class and no material axis at all.
        if "rf_material" in document.files:
            rf_material = document["rf_material"]
            material_source = document["material_source"]
    rows = np.repeat(np.arange(height) * entity.shape[0] // height, width)
    columns = np.tile(np.arange(width) * entity.shape[1] // width, height)
    labels = entity[rows, columns]

    face_count = len(mesh.faces)
    hit_labels = labels[index_ray]
    transient = np.isin(hit_labels, list(transient_ids))
    total = np.bincount(index_tri, minlength=face_count)
    blocked = np.bincount(index_tri, weights=transient.astype(float), minlength=face_count)
    # Modal non-transient class per face, which is the label a single capture
    # would assign and therefore the thing two captures can agree or disagree on.
    clean = ~transient
    classes = int(labels.max()) + 1
    tally = np.zeros((face_count, classes), dtype=np.int32)
    np.add.at(tally, (index_tri[clean], hit_labels[clean]), 1)
    record = {
        "image_id": image_id,
        "rays": total.astype(np.int32),
        "transient_rays": blocked.astype(np.int32),
        "modal_class": np.where(tally.sum(axis=1) > 0, tally.argmax(axis=1), -1).astype(np.int16),
        "clean_rays": tally.sum(axis=1).astype(np.int32),
        "view_transient_fraction": float(transient.mean()) if len(transient) else 0.0,
        "view_transient_pixels": int(transient.sum()),
        "view_mesh_rays": len(index_ray),
    }
    if rf_material is None:
        return record
    # Same rays, same transient mask, same modal reduction. The only thing that
    # differs from the entity axis above is which raster is read, which is what
    # makes the two bindings comparable.
    hit_material = rf_material[rows, columns][index_ray]
    material_tally = np.zeros((face_count, material_count), dtype=np.int32)
    np.add.at(material_tally, (index_tri[clean], hit_material[clean]), 1)
    concept = material_source[rows, columns][index_ray]
    record["modal_material"] = np.where(material_tally.sum(axis=1) > 0, material_tally.argmax(axis=1), -1).astype(
        np.int16
    )
    record["material_counts"] = material_tally
    record["concept_rays"] = np.bincount(index_tri[clean], weights=concept[clean], minlength=face_count).astype(
        np.int32
    )
    return record


def _semantic_jobs(
    args: WalkEvidenceConfig,
    selection: dict,
    download: dict,
    mesh_path: str,
) -> tuple[list[tuple], list[dict], list[dict], list[str], list[str] | None]:
    """Admit registered stations and build their independent semantic jobs."""
    jobs, kept, skipped, backends = [], [], [], []
    material_names: list[str] | None = None
    for index, record in enumerate(download["stations"]):
        folder = pathlib.Path(record["folder"])
        aligned = folder / "alignment/pose_aligned.json"
        semantics = folder / "semantics/panorama_semantics.npz"
        if not aligned.exists() or not semantics.exists():
            skipped.append({"image_id": record["image_id"], "reason": "missing registration or semantics"})
            continue
        pose = json.loads(aligned.read_text())
        residual = float(pose.get("skyline_score_mean_deg", 99.0))
        if residual > args.max_residual_deg:
            skipped.append(
                {"image_id": record["image_id"], "reason": f"skyline residual {residual:.2f} deg", "residual": residual}
            )
            continue
        meta = json.loads((folder / "semantics/semantics.json").read_text())
        transient = {int(k) for k, v in meta["entity_id2label"].items() if v in TRANSIENT_CLASSES}
        vocabulary = meta.get("rf_material_id2label")
        if vocabulary is not None:
            names = [vocabulary[str(index)] for index in range(len(vocabulary))]
            if material_names is not None and names != material_names:
                raise SystemExit("stations disagree on the RF material vocabulary, refusing to fuse them")
            material_names = names
        backends.append(meta.get("backend", "mask2former"))
        jobs.append(
            (
                mesh_path,
                pose,
                str(semantics),
                transient,
                args.grid_height,
                record["image_id"],
                0 if vocabulary is None else len(vocabulary),
            )
        )
        kept.append(
            {
                "image_id": record["image_id"],
                "sequence_id": selection["stations"][index]["sequence_id"],
                "captured_at": selection["stations"][index]["captured_at"],
                "skyline_residual_deg": residual,
            }
        )
    return jobs, kept, skipped, backends, material_names


def stage_semantic(args: WalkEvidenceConfig) -> None:
    """Transient occlusion recovered by fusion, and whether captures agree."""
    from concurrent.futures import ProcessPoolExecutor

    import trimesh

    out = pathlib.Path(args.out)
    selection = json.loads((out / WALK_SELECTION_FILE).read_text())
    download = json.loads((out / WALK_DOWNLOAD_FILE).read_text())
    scene = load_scene(pathlib.Path(args.scene))
    mesh_path = _mesh_path(args, scene)
    area = np.asarray(trimesh.load(mesh_path, process=False).area_faces, dtype=float)

    jobs, kept, skipped, backends, material_names = _semantic_jobs(args, selection, download, mesh_path)
    if len(jobs) < 2:
        raise SystemExit("fewer than two usable stations, nothing to cross-validate")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_station_semantics, jobs))

    rays = np.stack([result["rays"] for result in results])
    blocked = np.stack([result["transient_rays"] for result in results])
    modal = np.stack([result["modal_class"] for result in results])
    clean = np.stack([result["clean_rays"] for result in results])

    seen = rays > 0
    # A face is cleanly observed by a station when most of the rays reaching it
    # from that station land on the facade rather than on something in front.
    clean_seen = seen & (clean >= args.clean_majority * np.maximum(rays, 1))
    lost_single = seen[0] & ~clean_seen[0]
    lost_fused = seen.any(axis=0) & ~clean_seen.any(axis=0)

    report = {
        "site": scene["name"],
        "mesh": pathlib.Path(mesh_path).name,
        "stations_used": kept,
        "stations_skipped": skipped,
        "occlusion": {
            "per_view_transient_pixel_fraction": {
                "values": [round(result["view_transient_fraction"], 5) for result in results],
                "median": float(np.median([result["view_transient_fraction"] for result in results])),
                "max": float(np.max([result["view_transient_fraction"] for result in results])),
            },
            "single_capture": {
                "faces_seen": int(seen[0].sum()),
                "faces_lost_to_transients": int(lost_single.sum()),
                "fraction_of_seen_lost": float(lost_single.sum() / max(seen[0].sum(), 1)),
                "area_fraction_of_seen_lost": float(area[lost_single].sum() / max(area[seen[0]].sum(), 1e-9)),
            },
            "fused": {
                "faces_seen": int(seen.any(axis=0).sum()),
                "faces_lost_to_transients": int(lost_fused.sum()),
                "fraction_of_seen_lost": float(lost_fused.sum() / max(seen.any(axis=0).sum(), 1)),
                "area_fraction_of_seen_lost": float(area[lost_fused].sum() / max(area[seen.any(axis=0)].sum(), 1e-9)),
            },
            "note": (
                "A face counts as lost when it is reached but fewer than the clean-majority share of "
                "its rays land on the facade. Fusion recovers a face when any one station has a clean "
                "look at it."
            ),
        },
        "agreement": _agreement(modal, clean_seen, kept, area, args),
    }
    arrays = {
        "image_ids": np.asarray([record["image_id"] for record in kept]),
        "rays": rays,
        "transient_rays": blocked,
        "modal_class": modal,
        "clean_rays": clean,
    }
    if material_names is not None and all("modal_material" in result for result in results):
        modal_material = np.stack([result["modal_material"] for result in results])
        concept_rays = np.stack([result["concept_rays"] for result in results])
        material_counts = np.sum([result["material_counts"] for result in results], axis=0)
        arrays.update(
            modal_material=modal_material,
            material_counts=material_counts.astype(np.int32),
            concept_rays=concept_rays,
            material_names=np.asarray(material_names),
        )
        bound = clean_seen.any(axis=0)
        report["material"] = {
            "backend_per_station": backends,
            "vocabulary": material_names,
            "note": (
                "modal_material is the modal RF material over the same non-transient rays "
                "that produced modal_class, so the entity and material bindings differ only "
                "in which raster they read."
            ),
            "concept_backed_ray_fraction": float(concept_rays.sum() / max(clean.sum(), 1)),
            "cleanly_seen_faces": int(bound.sum()),
            "material_share_over_cleanly_seen_faces": {
                material_names[index]: float(share)
                for index, share in enumerate(material_counts[bound].sum(axis=0) / max(material_counts[bound].sum(), 1))
                if share > 0.0
            },
            "agreement": _agreement(
                modal_material,
                clean_seen,
                kept,
                area,
                args,
                axis="modal non-transient SAM 3 RF material per face",
                caveat=(
                    "Material agreement between independent captures. Lower than entity agreement "
                    "is expected and is not a defect on its own: the material vocabulary is finer "
                    "and an open-vocabulary detector has no coverage guarantee, so a face can fall "
                    "back to the dense class prior in one capture and be concept-backed in another."
                ),
            ),
        }
    elif material_names is not None:
        report["material"] = {
            "backend_per_station": backends,
            "status": "mixed backends, refusing to emit a material axis only some stations carry",
        }
    np.savez_compressed(out / "walk_semantic.npz", **arrays)
    (out / "walk_semantic.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"occlusion": report["occlusion"], "agreement": report["agreement"]}, indent=2)[:3000], flush=True)


def _agreement(modal, clean_seen, kept, area, args, *, axis: str = "", caveat: str = "") -> dict:
    """Do independent captures assign the same class where they overlap.

    Split by whether the two stations belong to the same Mapillary sequence,
    because same-sequence agreement shares a camera, a day and an exposure and is
    therefore a much weaker test than cross-sequence agreement. Reporting one
    pooled number would let the easy comparisons carry the hard ones.
    """
    stations = len(kept)
    pairs = {"same_sequence": [], "cross_sequence": []}
    for first in range(stations):
        for second in range(first + 1, stations):
            both = clean_seen[first] & clean_seen[second]
            if both.sum() < args.min_overlap_faces:
                continue
            agree = modal[first][both] == modal[second][both]
            key = "same_sequence" if kept[first]["sequence_id"] == kept[second]["sequence_id"] else "cross_sequence"
            pairs[key].append(
                {
                    "a": kept[first]["image_id"],
                    "b": kept[second]["image_id"],
                    "overlap_faces": int(both.sum()),
                    "agreement": float(agree.mean()),
                    "area_weighted_agreement": float(area[both][agree].sum() / max(area[both].sum(), 1e-9)),
                }
            )
    summary = {}
    for key, values in pairs.items():
        if not values:
            summary[key] = {"n_pairs": 0}
            continue
        rates = np.array([entry["agreement"] for entry in values])
        weights = np.array([entry["overlap_faces"] for entry in values], dtype=float)
        summary[key] = {
            "n_pairs": len(values),
            "median_agreement": float(np.median(rates)),
            "overlap_weighted_agreement": float((rates * weights).sum() / weights.sum()),
            "min_agreement": float(rates.min()),
            "max_agreement": float(rates.max()),
            "total_overlap_faces": int(weights.sum()),
        }
    return {
        "summary": summary,
        "pairs": pairs,
        "axis": axis or "modal non-transient Mapillary Vistas entity class per face",
        "caveat": caveat
        or (
            "This is entity agreement, not material agreement. The material axis needs the SAM 3 "
            "concept pass, and without it material is a deterministic function of entity and would "
            "only restate this number."
        ),
    }


def run_stage(args: WalkEvidenceConfig) -> None:
    """Run one walk evidence stage from validated command arguments."""
    stages = {
        "select": stage_select,
        "download": stage_download,
        "fuse": stage_fuse,
        "saturate": stage_saturate,
        "semantic": stage_semantic,
    }
    stages[args.stage](args)
