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

import argparse
import json
import pathlib
from dataclasses import asdict

import numpy as np

from semantic_twin import walk as walk_module
from semantic_twin.geo import EnuFrame
from semantic_twin.mapillary import pose_from_metadata, download_panorama_image, token
from semantic_twin.panorama import load_support_mesh
from semantic_twin.scene import load_scene

REPO = pathlib.Path(__file__).resolve().parent


def _frame(scene: dict) -> EnuFrame:
    origin = scene["enu_origin"]
    return EnuFrame(float(origin["lat"]), float(origin["lon"]), float(origin.get("ellipsoid_height_m", 0.0)))


def stage_select(args: argparse.Namespace) -> None:
    scene = load_scene(pathlib.Path(args.scene))
    frame = _frame(scene)
    latitude = float(scene["location"]["lat"])
    longitude = float(scene["location"]["lon"])
    access_token = token()

    sequences, seeds = walk_module.seed_sequences(
        access_token,
        latitude=latitude,
        longitude=longitude,
        half_width_m=args.seed_half_width_m,
        cells=args.seed_cells,
    )
    print(f"[walk] {seeds} panorama seeds name {len(sequences)} sequences", flush=True)
    images = walk_module.traverse(access_token, sequences, progress=True)
    stations = walk_module.stations_from_images(
        images.values(), frame, target_lat=latitude, target_lon=longitude, radius_m=args.radius_m
    )
    chosen = walk_module.select_walk(
        stations, count=args.count, separation_m=args.separation_m, per_sequence_cap=args.per_sequence_cap
    )
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "site": scene["name"],
        "traversal": {
            "method": "Mapillary sequence link graph, seeded by a tiled bounding box and expanded by sequence id",
            "bbox_seed_panoramas": seeds,
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
        "spread": walk_module.spread(chosen),
        "stations": [station.summary() for station in chosen],
        "candidates": [station.summary() for station in sorted(stations, key=lambda s: s.range_m)],
    }
    (out / "walk_selection.json").write_text(json.dumps(payload, indent=2))
    (out / "walk_metadata.json").write_text(json.dumps({s.image_id: s.metadata for s in chosen}, indent=2))
    (out / "walk_all_metadata.json").write_text(json.dumps({s.image_id: s.metadata for s in stations}, indent=2))
    print(json.dumps(payload["spread"], indent=2), flush=True)


def stage_download(args: argparse.Namespace) -> None:
    out = pathlib.Path(args.out)
    selection = json.loads((out / "walk_selection.json").read_text())
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
    (out / "walk_download.json").write_text(json.dumps({"stations": written}, indent=2))


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


def stage_fuse(args: argparse.Namespace) -> None:
    import trimesh
    from concurrent.futures import ProcessPoolExecutor

    from semantic_twin import walk as walk_module

    out = pathlib.Path(args.out)
    selection = json.loads((out / "walk_selection.json").read_text())
    download = json.loads((out / "walk_download.json").read_text())
    scene = load_scene(pathlib.Path(args.scene))
    mesh_path = str(REPO / scene["source_mesh"])
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
    stations = [walk_module.WalkStation(**{**record, "metadata": {}}) for record in selection["stations"]]
    centres = np.asarray(mesh.triangles_center, dtype=float)[:, :2]

    # Independence over the union faces only, which is where double counting
    # could occur at all.
    union_index = np.flatnonzero(union)
    sample = (
        union_index
        if len(union_index) <= args.independence_sample
        else np.random.default_rng(7).choice(union_index, args.independence_sample, replace=False)
    )
    parallax = walk_module.parallax_angles_deg(stations, centres[sample])
    independence = walk_module.parallax_independence(
        parallax, seen[:, sample].T, decorrelation_deg=args.decorrelation_deg
    )
    looks = walk_module.effective_looks(independence)
    raw = seen[:, sample].sum(axis=0)

    multi = raw >= 2
    report = {
        "site": scene["name"],
        "mesh": scene["source_mesh"],
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
            "sampled_union_faces": int(len(sample)),
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
        "viewing_geometry": _geometry_split(seen, cosine, near, area, single, union),
    }
    (out / "walk_coverage.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("single_capture", "fused", "independence")}, indent=2), flush=True)


def _geometry_split(seen, cosine, near, area, single, union) -> dict:
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


def stage_saturate(args: argparse.Namespace) -> None:
    """Raycast every available panorama position and find where coverage stops paying."""
    import trimesh
    from concurrent.futures import ProcessPoolExecutor

    from semantic_twin import walk as walk_module

    out = pathlib.Path(args.out)
    scene = load_scene(pathlib.Path(args.scene))
    frame = _frame(scene)
    metadata = json.loads((out / "walk_all_metadata.json").read_text())
    stations = walk_module.stations_from_images(
        metadata.values(),
        frame,
        target_lat=float(scene["location"]["lat"]),
        target_lon=float(scene["location"]["lon"]),
        radius_m=args.radius_m,
    )
    stations.sort(key=lambda station: station.range_m)
    print(f"[saturate] {len(stations)} panorama positions inside {args.radius_m:.0f} m", flush=True)

    mesh_path = str(REPO / scene["source_mesh"])
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=("select", "download", "fuse", "saturate"))
    parser.add_argument("--permutations", type=int, default=40)
    parser.add_argument("--recast", action="store_true")
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--decorrelation-deg", type=float, default=10.0)
    parser.add_argument("--independence-sample", type=int, default=40000)
    parser.add_argument("--scene", default=str(REPO / "config/korenmarkt.json"))
    parser.add_argument("--out", default=str(REPO / "outputs/walk_korenmarkt"))
    parser.add_argument("--panorama-root", default=str(REPO / "data/panoramas/korenmarkt_walk"))
    parser.add_argument("--radius-m", type=float, default=60.0)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--separation-m", type=float, default=8.0)
    parser.add_argument("--per-sequence-cap", type=int, default=6)
    parser.add_argument("--seed-half-width-m", type=float, default=150.0)
    parser.add_argument("--seed-cells", type=int, default=6)
    return parser


def main() -> None:
    args = _parser().parse_args()
    {"select": stage_select, "download": stage_download, "fuse": stage_fuse, "saturate": stage_saturate}[args.stage](
        args
    )


if __name__ == "__main__":
    main()
