"""Build the tile-texture material channel and measure what it is worth.

The pipeline in one line: read the textured 3D Tiles leaves, attach each
support-mesh face to the tile triangle it was built from, classify the texel
patch, and emit a Dirichlet material posterior for every face including the
96 percent no panorama sees.

Three measurements come out alongside the evidence, and they are the point of
the script rather than a by-product.

1. Held-out accuracy of the texture-derived class against the panorama-derived
   class, on spatially blocked folds so the number is a transfer to unseen walls
   rather than memorisation of the wall under test.
2. The same classifier and the same protocol run on the panorama's own pixels,
   at its native 7.7 mm and box-downsampled to the texture's 19.6 cm. That
   separates how much is lost to resolution from how much was never separable.
3. Which class pairs collapse, found by merging the worst-separated pair and
   refitting until every surviving pair is better than a coin.

Usage:

    python build_texture_evidence.py \\
        --tiles /path/to/korenmarkt-tiles-200m \\
        --mesh data/geometry/korenmarkt/inhouse_leaf_130m.ply \\
        --mesh-manifest data/geometry/korenmarkt/inhouse_leaf_130m_f64.json \\
        --panorama-semantics data/panoramas/korenmarkt/semantics/panorama_semantics.npz \\
        --semantics-json data/panoramas/korenmarkt/semantics/semantics.json \\
        --panorama data/panoramas/korenmarkt/panorama_z5.jpg \\
        --pose data/panoramas/korenmarkt/alignment/pose_aligned.json \\
        --output outputs/korenmarkt_texture_evidence
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
from typing import Any

import numpy as np
import trimesh
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from semantic_twin.concepts import ConceptCatalog  # noqa: E402
from semantic_twin.pano_geometry import (  # noqa: E402
    equirectangular_directions,
    panorama_to_world_matrix,
)
from semantic_twin.texture_evidence import (  # noqa: E402
    MaterialClassifier,
    MomentAccumulator,
    blocked_folds,
    build_texture_evidence,
    collapsing_pairs,
    confusion_matrix,
    fit_softmax,
    fit_temperature,
    image_lab_and_gradient,
    match_support_faces,
    pairwise_separability,
    posterior_top_mass,
    read_tile_surface,
    softmax_probability,
    texture_features,
)

Image.MAX_IMAGE_PIXELS = None

# Concept prompts grouped by the RF material they imply. The grouping is by
# dielectric behaviour, not by visual appearance, because that is what the
# exporter binds. Slate roof and cobblestone sit with dimension stone because
# ITU-R P.2040-4 has one stone row, which is the same collapse the concept
# catalogue already makes.
CONCEPT_GROUPS: dict[str, tuple[str, ...]] = {
    "brick": ("brick facade", "painted brick wall", "brick paving"),
    "stone": (
        "ashlar stone facade",
        "rubble stone masonry wall",
        "marble cladding",
        "slate roof",
        "cobblestone paving",
    ),
    "concrete_render": ("plaster facade", "exposed concrete wall", "paving slab", "concrete surface", "gravel"),
    "glass": ("glass curtain wall", "glass window", "shop window", "glass roof"),
    "metal": (
        "metal cladding panel",
        "corrugated metal sheet",
        "metal roller shutter",
        "metal roof",
        "metal surface",
        "metal door",
    ),
    "vegetation": ("foliage", "grass lawn"),
    "asphalt": ("asphalt road",),
    "wood": ("timber cladding", "wooden surface", "wooden door", "plywood hoarding", "oriented strand board panel"),
}

PANORAMA_SCALES = (1, 26)
SUPPORT_EDGES = np.array([16.0, 32.0, 64.0, 128.0])


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tiles", type=pathlib.Path, required=True)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--mesh-manifest", type=pathlib.Path, required=True)
    parser.add_argument("--panorama-semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--concepts", type=pathlib.Path, default=pathlib.Path("config/semantic_concepts.json"))
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--crop-radius-m", type=float, default=140.0)
    parser.add_argument("--grid-height", type=int, default=1536)
    parser.add_argument("--block-m", type=float, default=12.0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-texels", type=int, default=8)
    parser.add_argument("--min-purity", type=float, default=0.7)
    parser.add_argument("--collapse-threshold", type=float, default=0.55)
    parser.add_argument("--l2", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def input_provenance(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    """Size and digest of every input this run read.

    The panorama semantics are regenerated by the segmentation stage while this
    study is in progress, and the labelled-face count moves when they are. A run
    whose numbers cannot be tied to the exact bytes they came from is not a
    measurement, so the digest is recorded rather than the path alone.
    """
    record: dict[str, dict[str, Any]] = {}
    for name in ("mesh", "mesh_manifest", "panorama_semantics", "semantics_json", "panorama", "pose", "concepts"):
        path = getattr(args, name)
        if not path.exists():
            continue
        digest = hashlib.blake2b(digest_size=16)
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 22), b""):
                digest.update(block)
        record[name] = {"path": str(path), "bytes": path.stat().st_size, "blake2b_128": digest.hexdigest()}
    return record


def visible_faces(
    mesh: trimesh.Trimesh,
    pose: dict[str, Any],
    grid_height: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    """First-hit face index and range for a full equirectangular sphere of rays.

    The four cached perspective depth buffers only cover the horizontal band, so
    ground and roof faces never enter the labelled set through them. Casting the
    whole sphere once costs about ten seconds and recovers the paving and roof
    classes, which are exactly the ones the aerial texture is best placed to see.
    """
    height, width = int(grid_height), int(grid_height) * 2
    local = equirectangular_directions(width, height).reshape(-1, 3)
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose.get("pitch_correction_deg", 0.0)),
        roll_deg=float(pose.get("roll_correction_deg", 0.0)),
    )
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)
    directions = local @ rotation.T
    origins = np.broadcast_to(camera, directions.shape)
    locations, ray_index, triangle_index = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    face_ids = np.full(len(directions), -1, dtype=np.int64)
    range_m = np.full(len(directions), np.inf)
    face_ids[ray_index] = triangle_index
    range_m[ray_index] = np.linalg.norm(locations - camera, axis=1)
    return face_ids, range_m, ray_index, height, width


def concept_labels(
    face_ids: np.ndarray,
    semantics: np.lib.npyio.NpzFile,
    id2label: dict[str, str],
    face_count: int,
    height: int,
    width: int,
) -> tuple[np.ndarray, list[str]]:
    """Confidence-weighted panorama concept mass per support-mesh face."""
    concept = semantics["material_concept"]
    confidence = np.asarray(semantics["material_confidence"], dtype=np.float64)
    rows = np.repeat(np.arange(height) * concept.shape[0] // height, width)
    columns = np.tile(np.arange(width) * concept.shape[1] // width, height)
    labels = [id2label[str(index)] for index in range(len(id2label))]
    counts = np.zeros((face_count, len(labels)))
    hit = face_ids >= 0
    np.add.at(
        counts,
        (face_ids[hit], concept[rows, columns][hit].astype(np.int64)),
        confidence[rows, columns][hit],
    )
    return counts, labels


def group_counts(counts: np.ndarray, labels: list[str]) -> tuple[np.ndarray, list[str], dict[str, list[str]]]:
    """Fold concept counts into the RF material groups that are present."""
    present: dict[str, list[str]] = {}
    for name, prompts in CONCEPT_GROUPS.items():
        found = [prompt for prompt in prompts if prompt in labels]
        if found and counts[:, [labels.index(prompt) for prompt in found]].sum() > 0.0:
            present[name] = found
    names = list(present)
    grouped = np.zeros((len(counts), len(names)))
    for index, name in enumerate(names):
        for prompt in present[name]:
            grouped[:, index] += counts[:, labels.index(prompt)]
    return grouped, names, present


def group_material_matrix(
    catalog: ConceptCatalog,
    present: dict[str, list[str]],
    counts: np.ndarray,
    labels: list[str],
    names: list[str],
) -> np.ndarray:
    """Class by RF material probabilities, averaged over the prompts in each class.

    The weights are the observed pixel mass of each prompt, so a class whose
    stone is mostly cobbles inherits the cobble prompt's material spread rather
    than an unweighted average over prompts the site does not contain. Prompts
    the catalogue does not carry contribute nothing, which keeps the mapping
    traceable to `config/semantic_concepts.json` rather than invented here.
    """
    materials = catalog.taxonomy["materials"]
    matrix = np.zeros((len(names), len(materials)))
    unknown = materials.index("unknown")
    for index, name in enumerate(names):
        total = 0.0
        for prompt in present[name]:
            concept = catalog.by_prompt.get(prompt)
            if concept is None:
                continue
            mass = float(counts[:, labels.index(prompt)].sum())
            if mass <= 0.0:
                continue
            matrix[index] += mass * catalog.categorical_probability(concept, "materials")
            total += mass
        if total > 0.0:
            matrix[index] /= total
        else:
            matrix[index, unknown] = 1.0
    return matrix


def out_of_fold(
    features: np.ndarray,
    labels: np.ndarray,
    class_count: int,
    fold: np.ndarray,
    *,
    l2: float,
) -> np.ndarray:
    """Predictions for every row, each made by a model that never saw its block."""
    mean = features.mean(axis=0)
    scale = features.std(axis=0) + 1e-9
    standard = (features - mean) / scale
    probability = np.zeros((len(labels), class_count))
    for index in np.unique(fold):
        train, test = fold != index, fold == index
        if not train.any() or not test.any():
            continue
        weights = fit_softmax(standard[train], labels[train], class_count, l2=l2)
        probability[test] = softmax_probability(weights, standard[test])
    return probability


def score(probability: np.ndarray, labels: np.ndarray, class_count: int) -> dict[str, Any]:
    prediction = probability.argmax(axis=1)
    matrix = confusion_matrix(labels, prediction, class_count)
    recall = np.divide(np.diag(matrix), matrix.sum(axis=1), out=np.zeros(class_count), where=matrix.sum(axis=1) > 0)
    return {
        "n": int(len(labels)),
        "accuracy": float((prediction == labels).mean()),
        "balanced_accuracy": float(recall[matrix.sum(axis=1) > 0].mean()),
        "majority_baseline": float(np.bincount(labels, minlength=class_count).max() / len(labels)),
        "per_class_recall": recall.tolist(),
        "confusion": matrix.tolist(),
        "prediction": prediction,
    }


def panorama_face_features(
    panorama_path: pathlib.Path,
    face_ids: np.ndarray,
    face_count: int,
    height: int,
    width: int,
    scale: int,
    *,
    chunk_rows: int = 512,
) -> np.ndarray:
    """The descriptor of :mod:`texture_evidence`, read off the panorama instead.

    The ray grid is coarser than the panorama, so each ray owns a block of native
    pixels and every one of them is folded in. That keeps the control at the
    panorama's true angular sampling rather than at the raycast grid's, which is
    the whole point of running it. ``scale`` box-downsamples the panorama and
    then restores its size with nearest neighbour, so the pixel grid and the face
    ownership are untouched and only the angular detail is removed.

    The 16384 by 8192 panorama is 134 million pixels, so it is streamed in row
    blocks. :class:`MomentAccumulator` makes that exact rather than approximate,
    and one overlapping row on each side keeps the vertical gradient identical to
    a whole-image pass at the block seams.
    """
    image = Image.open(panorama_path).convert("RGB")
    if scale > 1:
        small = image.resize((max(image.width // scale, 1), max(image.height // scale, 1)), Image.BOX)
        image = small.resize((image.width, image.height), Image.NEAREST)
    native_height, native_width = image.height, image.width
    block_y = max(native_height // height, 1)
    block_x = max(native_width // width, 1)
    grid = face_ids.reshape(height, width)
    columns_index = np.minimum(np.arange(native_width) // block_x, width - 1)
    accumulator = MomentAccumulator(face_count)
    for start in range(0, native_height, chunk_rows):
        stop = min(start + chunk_rows, native_height)
        pad_low = 1 if start > 0 else 0
        pad_high = 1 if stop < native_height else 0
        window = np.asarray(image.crop((0, start - pad_low, native_width, stop + pad_high)))
        lab, gradient_column, gradient_row = image_lab_and_gradient(window)
        inner = slice(pad_low, pad_low + stop - start)
        rows_index = np.minimum(np.arange(start, stop) // block_y, height - 1)
        owner = grid[np.ix_(rows_index, columns_index)]
        hit = owner >= 0
        if not hit.any():
            continue
        rows, columns = np.nonzero(hit)
        accumulator.add(
            owner[hit],
            lab[inner][rows, columns],
            np.stack([gradient_column[inner][rows, columns], gradient_row[inner][rows, columns]], axis=1),
        )
    return accumulator.finish()


def collapse_until_separable(
    features: np.ndarray,
    labels: np.ndarray,
    names: list[str],
    fold: np.ndarray,
    *,
    l2: float,
    threshold: float,
) -> tuple[np.ndarray, list[list[str]], list[dict[str, Any]]]:
    """Merge the worst-separated pair and refit until every pair beats a coin."""
    groups = [[name] for name in names]
    current = labels.copy()
    history: list[dict[str, Any]] = []
    while len(groups) > 2:
        probability = out_of_fold(features, current, len(groups), fold, l2=l2)
        result = score(probability, current, len(groups))
        matrix = np.asarray(result["confusion"])
        separability = pairwise_separability(matrix)
        pairs = collapsing_pairs(matrix, threshold=threshold)
        history.append(
            {
                "classes": [" + ".join(group) for group in groups],
                "accuracy": result["accuracy"],
                "balanced_accuracy": result["balanced_accuracy"],
                "majority_baseline": result["majority_baseline"],
                "per_class_recall": result["per_class_recall"],
                "collapsing_pairs": [
                    [" + ".join(groups[i]), " + ".join(groups[j]), float(separability[i, j])] for i, j in pairs
                ],
            }
        )
        if not pairs:
            break
        worst = min(pairs, key=lambda pair: separability[pair[0], pair[1]])
        first, second = worst
        groups[first] = groups[first] + groups[second]
        del groups[second]
        current = np.where(current == second, first, np.where(current > second, current - 1, current))
    return current, groups, history


def main() -> None:
    args = arguments()
    args.output.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    start = time.perf_counter()
    manifest = json.loads(args.mesh_manifest.read_text())
    transform = np.asarray(manifest["alignment"]["ecef_to_local_enu_matrix"], dtype=np.float64)
    surface = read_tile_surface(args.tiles, transform, crop_radius_m=args.crop_radius_m)
    timings["read_tiles_s"] = time.perf_counter() - start
    print(f"[texture] {surface.triangle_count} textured triangles from {len(surface.tile_files)} tiles", flush=True)

    start = time.perf_counter()
    features = texture_features(surface)
    timings["texture_features_s"] = time.perf_counter() - start
    area = surface.area_m2()
    texel_density = np.divide(features.texel_count, area, out=np.zeros(len(area)), where=area > 0.0)
    order = np.argsort(texel_density)
    cumulative = np.cumsum(area[order]) / max(area.sum(), 1e-12)
    median_density = float(texel_density[order][np.searchsorted(cumulative, 0.5)])
    print(f"[texture] area-weighted median {median_density:.1f} texels per square metre", flush=True)

    start = time.perf_counter()
    mesh = trimesh.load(args.mesh, process=False)
    match = match_support_faces(mesh.triangles, surface)
    timings["match_s"] = time.perf_counter() - start
    print(f"[texture] matched {match.report['matched_fraction']:.1%} of support faces", flush=True)

    start = time.perf_counter()
    pose = json.loads(args.pose.read_text())
    face_ids, range_m, _, grid_h, grid_w = visible_faces(mesh, pose, args.grid_height)
    timings["raycast_s"] = time.perf_counter() - start
    face_count = len(mesh.faces)
    hit = face_ids >= 0
    pixels = np.bincount(face_ids[hit], minlength=face_count)
    range_sum = np.bincount(face_ids[hit], weights=range_m[hit], minlength=face_count)
    face_range = np.divide(range_sum, pixels, out=np.full(face_count, np.nan), where=pixels > 0)
    seen = pixels > 0
    print(f"[texture] {int(seen.sum())} of {face_count} faces are street visible ({seen.mean():.2%})", flush=True)

    semantics = np.load(args.panorama_semantics)
    semantics_meta = json.loads(args.semantics_json.read_text())
    counts, labels = concept_labels(face_ids, semantics, semantics_meta["concept_id2label"], face_count, grid_h, grid_w)
    grouped, names, present = group_counts(counts, labels)
    catalog = ConceptCatalog.load(args.concepts)
    material_matrix = group_material_matrix(catalog, present, counts, labels, names)

    named = counts[:, 1:].sum(axis=1)
    mass = grouped.sum(axis=1)
    purity = np.divide(grouped.max(axis=1), mass, out=np.zeros(face_count), where=mass > 0)
    grouped_share = np.divide(mass, named, out=np.zeros(face_count), where=named > 0)
    tile_index = match.tile_triangle
    texels = np.where(match.matched, features.texel_count[tile_index], 0)
    usable = (
        match.matched
        & (mass > 0.0)
        & (purity >= args.min_purity)
        & (grouped_share >= args.min_purity)
        & (texels >= args.min_texels)
    )
    labelled = np.flatnonzero(usable)
    truth = grouped[labelled].argmax(axis=1)
    print(f"[texture] {len(labelled)} labelled faces over {len(names)} classes", flush=True)

    fold = blocked_folds(mesh.triangles[labelled].mean(axis=1), block_m=args.block_m, folds=args.folds, seed=args.seed)
    texture_block = features.values[tile_index[labelled]]
    sources: dict[str, np.ndarray] = {"texture": texture_block}
    start = time.perf_counter()
    for scale in PANORAMA_SCALES:
        block = panorama_face_features(args.panorama, face_ids, face_count, grid_h, grid_w, scale)
        gsd_mm = 1000.0 * float(np.nanmedian(face_range[labelled])) * 2.0 * np.pi / (16384.0 / scale)
        sources[f"panorama_{gsd_mm:.0f}mm"] = block[labelled]
    timings["panorama_control_s"] = time.perf_counter() - start

    start = time.perf_counter()
    comparison: dict[str, Any] = {}
    for name, block in sources.items():
        blocked = score(out_of_fold(block, truth, len(names), fold, l2=args.l2), truth, len(names))
        random_fold = np.random.default_rng(args.seed).integers(0, args.folds, len(truth))
        random = score(out_of_fold(block, truth, len(names), random_fold, l2=args.l2), truth, len(names))
        blocked.pop("prediction")
        random.pop("prediction")
        comparison[name] = {"blocked": blocked, "random": random}
        print(
            f"[texture] {name:18s} blocked acc={blocked['accuracy']:.3f} "
            f"balanced={blocked['balanced_accuracy']:.3f} baseline={blocked['majority_baseline']:.3f}",
            flush=True,
        )
    geometry_block = np.hstack(
        [texture_block, mesh.face_normals[labelled][:, 2:3], mesh.triangles[labelled].mean(axis=1)[:, 2:3]]
    )
    geometry = score(out_of_fold(geometry_block, truth, len(names), fold, l2=args.l2), truth, len(names))
    geometry.pop("prediction")
    comparison["texture_plus_geometry"] = {"blocked": geometry}
    timings["evaluate_s"] = time.perf_counter() - start

    collapsed, groups, history = collapse_until_separable(
        texture_block, truth, names, fold, l2=args.l2, threshold=args.collapse_threshold
    )
    final_names = [" + ".join(group) for group in groups]
    print(f"[texture] classes survive as {final_names}", flush=True)

    probability = out_of_fold(texture_block, collapsed, len(groups), fold, l2=args.l2)
    final = score(probability, collapsed, len(groups))
    prediction = final.pop("prediction")
    support = {}
    edges = np.concatenate([[float(args.min_texels)], SUPPORT_EDGES, [np.inf]])
    labelled_texels = texels[labelled].astype(np.float64)
    temperatures = np.ones(len(SUPPORT_EDGES) + 1)
    for index in range(len(edges) - 1):
        inside = (labelled_texels >= edges[index]) & (labelled_texels < edges[index + 1])
        if inside.sum() >= 20:
            temperatures[index] = fit_temperature(probability[inside], collapsed[inside])
            support[f"[{edges[index]:.0f},{edges[index + 1]:.0f})"] = {
                "faces": int(inside.sum()),
                "accuracy": float((prediction[inside] == collapsed[inside]).mean()),
                "temperature": float(temperatures[index]),
                "mean_top_probability": float(probability[inside].max(axis=1).mean()),
            }
    print(f"[texture] collapsed accuracy {final['accuracy']:.3f} baseline {final['majority_baseline']:.3f}", flush=True)

    collapsed_material = np.zeros((len(groups), material_matrix.shape[1]))
    for index, group in enumerate(groups):
        weights = np.asarray([grouped[:, names.index(name)].sum() for name in group])
        weights = weights / max(weights.sum(), 1e-12)
        collapsed_material[index] = weights @ material_matrix[[names.index(name) for name in group]]

    mean = texture_block.mean(axis=0)
    scale = texture_block.std(axis=0) + 1e-9
    classifier = MaterialClassifier(
        weights=fit_softmax((texture_block - mean) / scale, collapsed, len(groups), l2=args.l2),
        mean=mean,
        scale=scale,
        class_labels=tuple(final_names),
        feature_names=tuple(features.names),
        support_edges=SUPPORT_EDGES,
        support_temperature=temperatures,
        material_labels=tuple(catalog.taxonomy["materials"]),
        material_matrix=collapsed_material,
    )
    classifier.save(args.output / "texture_material_classifier.npz")

    panorama_alpha = np.zeros((face_count, len(catalog.taxonomy["materials"])))
    for index, name in enumerate(names):
        panorama_alpha += np.outer(grouped[:, index], material_matrix[index])
    # The resolution term asks what a panorama at the capture point would have
    # resolved on this face. That distance is defined for every face, occluded
    # or not, so it comes from the geometry rather than from the first-hit range,
    # which exists only for the 4 percent the panorama actually reaches.
    emit_range = np.linalg.norm(mesh.triangles.mean(axis=1) - np.asarray(pose["position_enu_m"]), axis=1)
    evidence = build_texture_evidence(
        features,
        match,
        classifier,
        face_range_m=emit_range,
        panorama_alpha=panorama_alpha,
    )
    concentration = evidence.concentration()
    posterior = posterior_top_mass(concentration, evidence.material_probability)
    np.savez_compressed(
        args.output / "texture_material_evidence.npz",
        face_index=evidence.face_index,
        material_probability=evidence.material_probability.astype(np.float32),
        rows=evidence.rows.astype(np.int32),
        concentration=concentration.astype(np.float32),
        texel_count=evidence.texel_count.astype(np.int32),
        gsd_m=evidence.gsd_m.astype(np.float32),
        resolution=evidence.quality.resolution.astype(np.float32),
        incidence=evidence.quality.incidence.astype(np.float32),
        independence=evidence.quality.independence.astype(np.float32),
        material_labels=np.asarray(catalog.taxonomy["materials"]),
    )

    covered = np.zeros(face_count, dtype=bool)
    covered[evidence.face_index] = True
    face_area = mesh.area_faces
    report = {
        "site": args.mesh.stem,
        "inputs": input_provenance(args),
        "tiles": str(args.tiles),
        "tile_count": len(surface.tile_files),
        "textured_triangles": surface.triangle_count,
        "texel_total": int(features.texel_count.sum()),
        "area_weighted_median_texels_per_m2": median_density,
        "median_gsd_m": float(np.nanmedian(features.gsd_m)),
        "support_faces": face_count,
        "match": match.report,
        "coverage": {
            "panorama_visible_faces": int(seen.sum()),
            "panorama_visible_fraction": float(seen.mean()),
            "panorama_visible_area_fraction": float(face_area[seen].sum() / face_area.sum()),
            "texture_faces": int(covered.sum()),
            "texture_fraction": float(covered.mean()),
            "texture_area_fraction": float(face_area[covered].sum() / face_area.sum()),
            "gain_faces": float(covered.mean() / max(seen.mean(), 1e-12)),
            "gain_area": float(
                (face_area[covered].sum() / face_area.sum()) / max(face_area[seen].sum() / face_area.sum(), 1e-12)
            ),
            "matched_but_subtexel_faces": int(match.matched.sum() - covered.sum()),
        },
        "labels": {
            "labelled_faces": int(len(labelled)),
            "classes": names,
            "class_faces": {name: int((truth == index).sum()) for index, name in enumerate(names)},
            "concept_prompts": {name: list(prompts) for name, prompts in present.items()},
        },
        "comparison": comparison,
        "collapse_history": history,
        "final": {"classes": final_names, **final},
        "support_calibration": support,
        "evidence": evidence.report,
        "concentration": {
            "median": float(np.median(concentration)),
            "p10": float(np.percentile(concentration, 10)),
            "p90": float(np.percentile(concentration, 90)),
            "capped_by_panorama_faces": int((evidence.quality.independence < 1.0).sum()),
            "median_top_material_probability": float(np.median(evidence.material_probability.max(axis=1))),
            "median_posterior_top_mass": float(np.median(posterior)),
            "p90_posterior_top_mass": float(np.percentile(posterior, 90)),
            "uniform_posterior_top_mass": 1.0 / len(catalog.taxonomy["materials"]),
            "predicted_material_faces": {
                catalog.taxonomy["materials"][index]: int(count)
                for index, count in zip(*np.unique(evidence.material_probability.argmax(axis=1), return_counts=True))
            },
        },
        "protocol": {
            "block_m": args.block_m,
            "folds": args.folds,
            "min_texels": args.min_texels,
            "min_purity": args.min_purity,
            "collapse_threshold": args.collapse_threshold,
            "l2": args.l2,
            "seed": args.seed,
        },
        "timings_s": timings,
    }
    (args.output / "texture_evidence_manifest.json").write_text(json.dumps(report, indent=2))
    print(f"[texture] wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
