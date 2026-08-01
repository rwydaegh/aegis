from __future__ import annotations

import io
import json
import pathlib
import struct

import numpy as np
import pytest
from PIL import Image

from semantic_twin.evidence import EvidenceAccumulator
from semantic_twin.texture_evidence import (
    PANORAMA_WIDTH_PX,
    TEXTURE_FEATURES,
    MaterialClassifier,
    MomentAccumulator,
    TileSurface,
    binary_chunk,
    blocked_folds,
    build_texture_evidence,
    collapsing_pairs,
    confusion_matrix,
    dominance_factor,
    fit_softmax,
    fit_temperature,
    match_support_faces,
    mesh_node_placements,
    pairwise_separability,
    panorama_resolution_ratio,
    posterior_top_mass,
    rasterize_uv_triangles,
    read_accessor,
    read_tile_surface,
    softmax_probability,
    srgb_to_lab,
    support_rows,
    texel_geometry,
    texture_features,
)

GLTF_JSON_CHUNK = 0x4E4F534A
GLTF_BIN_CHUNK = 0x004E4942

# A real Photorealistic 3D Tiles leaf placement. Reading it in single precision
# is the defect this module deliberately does not inherit.
ECEF_TRANSLATION = (4008982.414761939, 4937332.26941904, -260985.39804007116)


def _chunk(payload: bytes, kind: int, pad: bytes) -> bytes:
    payload = payload + pad * ((4 - len(payload) % 4) % 4)
    return struct.pack("<II", len(payload), kind) + payload


def write_glb(path: pathlib.Path, document: dict, blob: bytes) -> pathlib.Path:
    body = _chunk(json.dumps(document).encode("utf-8"), GLTF_JSON_CHUNK, b" ")
    body += _chunk(blob, GLTF_BIN_CHUNK, b"\x00")
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    return path


def jpeg_bytes(image: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(buffer, format="JPEG", quality=100)
    return buffer.getvalue()


def synthetic_tile(
    path: pathlib.Path,
    *,
    positions: np.ndarray,
    uv: np.ndarray,
    indices: np.ndarray,
    image: np.ndarray,
    translation: tuple[float, float, float] = ECEF_TRANSLATION,
) -> pathlib.Path:
    """Write a one-primitive textured GLB with the tile server's node layout."""
    index_bytes = indices.astype("<u2").tobytes()
    position_bytes = positions.astype("<f4").tobytes()
    uv_bytes = uv.astype("<f4").tobytes()
    texture_bytes = jpeg_bytes(image)
    blob = b""
    views = []
    for payload in (index_bytes, position_bytes, uv_bytes, texture_bytes):
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(payload)})
        blob += payload + b"\x00" * ((4 - len(payload) % 4) % 4)
    matrix = np.eye(4)
    matrix[:3, 3] = translation
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"matrix": matrix.T.ravel().tolist(), "mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1, "TEXCOORD_0": 2}, "indices": 0, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
        "textures": [{"source": 0}],
        "images": [{"mimeType": "image/jpeg", "bufferView": 3}],
        "accessors": [
            {"bufferView": 0, "componentType": 5123, "count": indices.size, "type": "SCALAR"},
            {"bufferView": 1, "componentType": 5126, "count": len(positions), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": len(uv), "type": "VEC2"},
        ],
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    return write_glb(path, document, blob)


def unit_quad() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    positions = np.array([[0.0, 0.0, 0.0], [8.0, 0.0, 0.0], [8.0, 0.0, 8.0], [0.0, 0.0, 8.0]])
    uv = np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])
    indices = np.array([0, 1, 2, 0, 2, 3])
    return positions, uv, indices


def test_binary_and_json_chunks_round_trip(tmp_path):
    positions, uv, indices = unit_quad()
    image = np.full((32, 32, 3), 40, dtype=np.uint8)
    path = synthetic_tile(tmp_path / "tile.glb", positions=positions, uv=uv, indices=indices, image=image)
    from semantic_twin.gltf import json_chunk

    document = json_chunk(path)
    blob = binary_chunk(path)
    assert read_accessor(document, blob, 1).shape == (4, 3)
    assert np.allclose(read_accessor(document, blob, 1).astype(np.float64), positions)
    assert np.allclose(read_accessor(document, blob, 2).astype(np.float64), uv)
    assert read_accessor(document, blob, 0).ravel().tolist() == indices.tolist()


def test_binary_chunk_rejects_a_container_without_one(tmp_path):
    path = tmp_path / "nobin.glb"
    body = _chunk(json.dumps({"asset": {"version": "2.0"}}).encode(), GLTF_JSON_CHUNK, b" ")
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    with pytest.raises(ValueError, match="no BIN chunk"):
        binary_chunk(path)


def test_node_placement_keeps_the_ecef_translation_in_double_precision(tmp_path):
    positions, uv, indices = unit_quad()
    path = synthetic_tile(
        tmp_path / "tile.glb", positions=positions, uv=uv, indices=indices, image=np.zeros((8, 8, 3), np.uint8)
    )
    from semantic_twin.gltf import YUP_TO_ZUP, json_chunk

    placements = mesh_node_placements(json_chunk(path))
    assert len(placements) == 1
    mesh_index, matrix = placements[0]
    assert mesh_index == 0
    expected = YUP_TO_ZUP[:3, :3] @ np.asarray(ECEF_TRANSLATION)
    assert np.allclose(matrix[:3, 3], expected, rtol=0.0, atol=0.0)
    # A float32 round trip loses metres at this magnitude, so exact equality is
    # the only assertion that proves the read never went through one.
    assert not np.allclose(matrix[:3, 3], np.float32(expected).astype(np.float64), rtol=0.0, atol=1e-9)


def test_read_tile_surface_places_triangles_in_the_requested_frame(tmp_path):
    positions, uv, indices = unit_quad()
    synthetic_tile(
        tmp_path / "tile.glb", positions=positions, uv=uv, indices=indices, image=np.zeros((16, 16, 3), np.uint8)
    )
    from semantic_twin.gltf import YUP_TO_ZUP

    transform = np.eye(4)
    transform[:3, 3] = -(YUP_TO_ZUP[:3, :3] @ np.asarray(ECEF_TRANSLATION))
    surface = read_tile_surface(tmp_path, transform)
    assert surface.triangle_count == 2
    assert np.allclose(surface.area_m2(), [32.0, 32.0])
    assert np.abs(surface.centroid()).max() < 10.0


def test_read_tile_surface_crops_by_radius(tmp_path):
    positions, uv, indices = unit_quad()
    synthetic_tile(
        tmp_path / "tile.glb", positions=positions, uv=uv, indices=indices, image=np.zeros((16, 16, 3), np.uint8)
    )
    from semantic_twin.gltf import YUP_TO_ZUP

    transform = np.eye(4)
    transform[:3, 3] = -(YUP_TO_ZUP[:3, :3] @ np.asarray(ECEF_TRANSLATION))
    with pytest.raises(ValueError, match="no textured triangles"):
        read_tile_surface(tmp_path, transform, crop_radius_m=0.5)


def test_read_tile_surface_needs_tiles(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_tile_surface(tmp_path, np.eye(4))


def test_rasterize_covers_every_texel_centre_of_a_full_atlas():
    uv = np.array(
        [
            [[0.0, 0.0], [16.0, 0.0], [16.0, 16.0]],
            [[0.0, 0.0], [16.0, 16.0], [0.0, 16.0]],
        ]
    )
    triangle, row, column = rasterize_uv_triangles(uv, 16, 16)
    assert set(zip(row.tolist(), column.tolist())) == {(r, c) for r in range(16) for c in range(16)}
    # The shared diagonal is inside both triangles, so its 16 texel centres are
    # emitted twice. Photogrammetry charts do not abut inside one atlas, so a
    # fill rule would only cost time here.
    assert len(triangle) == 256 + 16
    assert row.min() >= 0 and row.max() < 16
    assert column.min() >= 0 and column.max() < 16


def test_rasterize_drops_degenerate_and_subtexel_triangles():
    uv = np.array(
        [
            [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]],
            [[2.02, 2.02], [2.08, 2.02], [2.02, 2.08]],
        ]
    )
    triangle, _, _ = rasterize_uv_triangles(uv, 8, 8)
    assert triangle.size == 0


def test_rasterize_rejects_the_wrong_shape():
    with pytest.raises(ValueError, match=r"\[triangles, 3, 2\]"):
        rasterize_uv_triangles(np.zeros((4, 2)), 8, 8)


def test_srgb_to_lab_anchors():
    lab = srgb_to_lab(np.array([[255, 255, 255], [0, 0, 0], [128, 128, 128]], dtype=np.uint8))
    assert lab[0, 0] == pytest.approx(100.0, abs=1e-3)
    assert lab[1, 0] == pytest.approx(0.0, abs=1e-6)
    assert np.abs(lab[:, 1:]).max() < 1e-2


def test_texel_geometry_recovers_a_known_ground_sample_distance():
    # One texel spans 0.2 m along u and 0.2 m along v, so the gsd is 0.2 m and
    # the sampling is square.
    triangles = np.array([[[0.0, 0.0, 0.0], [12.8, 0.0, 0.0], [0.0, 0.0, 12.8]]])
    uv = np.array([[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]])
    surface = TileSurface(
        triangles=triangles,
        uv=uv,
        patch=np.zeros(1, dtype=np.int64),
        tile=np.zeros(1, dtype=np.int64),
        patches=[np.zeros((64, 64, 3), np.uint8)],
        tile_files=("tile.glb",),
    )
    gsd, anisotropy = texel_geometry(surface)
    assert gsd[0] == pytest.approx(0.2, rel=1e-9)
    assert anisotropy[0] == pytest.approx(1.0, rel=1e-9)


def test_texel_geometry_reports_a_stretched_chart():
    triangles = np.array([[[0.0, 0.0, 0.0], [64.0, 0.0, 0.0], [0.0, 0.0, 6.4]]])
    uv = np.array([[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]])
    surface = TileSurface(
        triangles=triangles,
        uv=uv,
        patch=np.zeros(1, dtype=np.int64),
        tile=np.zeros(1, dtype=np.int64),
        patches=[np.zeros((64, 64, 3), np.uint8)],
        tile_files=("tile.glb",),
    )
    _, anisotropy = texel_geometry(surface)
    assert anisotropy[0] == pytest.approx(0.1, rel=1e-9)


def test_texture_features_separate_two_flat_colours(tmp_path):
    image = np.zeros((32, 32, 3), np.uint8)
    image[:, :16] = (30, 90, 30)
    image[:, 16:] = (200, 200, 210)
    positions = np.array(
        [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 0.0, 4.0], [0.0, 0.0, 4.0], [8.0, 0.0, 0.0], [8.0, 0.0, 4.0]]
    )
    uv = np.array([[0.02, 0.98], [0.48, 0.98], [0.48, 0.02], [0.02, 0.02], [0.98, 0.98], [0.98, 0.02]])
    indices = np.array([0, 1, 2, 1, 4, 5])
    synthetic_tile(tmp_path / "tile.glb", positions=positions, uv=uv, indices=indices, image=image)
    surface = read_tile_surface(tmp_path, np.eye(4))
    features = texture_features(surface)
    assert features.values.shape == (2, len(TEXTURE_FEATURES))
    assert (features.texel_count > 0).all()
    lightness = features.values[:, TEXTURE_FEATURES.index("mean_lightness")]
    green = features.values[:, TEXTURE_FEATURES.index("green_texel_fraction")]
    assert lightness[1] > lightness[0] + 20.0
    assert green[0] > 0.9 and green[1] < 0.1


def test_moment_accumulator_is_exact_under_chunking():
    rng = np.random.default_rng(23)
    group = rng.integers(0, 5, 4000)
    lab = rng.normal(size=(4000, 3)) * np.array([20.0, 6.0, 9.0]) + np.array([40.0, 2.0, -8.0])
    gradient = rng.normal(size=(4000, 2))
    whole = MomentAccumulator(5)
    whole.add(group, lab, gradient)
    chunked = MomentAccumulator(5)
    for start in range(0, 4000, 137):
        stop = start + 137
        chunked.add(group[start:stop], lab[start:stop], gradient[start:stop])
    assert np.array_equal(whole.count, chunked.count)
    assert np.allclose(whole.finish(), chunked.finish(), rtol=0.0, atol=1e-9, equal_nan=True)


def test_moment_accumulator_leaves_untouched_groups_at_zero():
    accumulator = MomentAccumulator(3)
    accumulator.add(np.array([1, 1]), np.zeros((2, 3)), np.zeros((2, 2)))
    values = accumulator.finish()
    assert accumulator.count.tolist() == [0.0, 2.0, 0.0]
    assert np.all(values[0] == 0.0)
    assert np.all(values[2] == 0.0)


def test_moment_accumulator_validates_its_arguments():
    accumulator = MomentAccumulator(2)
    with pytest.raises(ValueError, match=r"\[pixels, 3\]"):
        accumulator.add(np.array([0]), np.zeros((1, 2)), np.zeros((1, 2)))
    with pytest.raises(IndexError):
        accumulator.add(np.array([5]), np.zeros((1, 3)), np.zeros((1, 2)))
    with pytest.raises(ValueError, match="size"):
        MomentAccumulator(0)


def test_moment_accumulator_matches_the_feature_name_list():
    accumulator = MomentAccumulator(1)
    accumulator.add(np.zeros(4, dtype=np.int64), np.zeros((4, 3)), np.zeros((4, 2)))
    assert accumulator.finish().shape == (1, len(TEXTURE_FEATURES))


def test_match_support_faces_survives_a_per_tile_offset():
    rng = np.random.default_rng(3)
    corners = rng.normal(size=(400, 3, 3)) * 0.4
    corners += np.repeat(rng.normal(size=(400, 1, 3)) * 25.0, 3, axis=1)
    surface = TileSurface(
        triangles=corners,
        uv=np.tile(np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]), (400, 1, 1)),
        patch=np.zeros(400, dtype=np.int64),
        tile=np.repeat(np.arange(4), 100),
        patches=[np.zeros((8, 8, 3), np.uint8)],
        tile_files=("a.glb", "b.glb", "c.glb", "d.glb"),
    )
    offsets = rng.normal(size=(4, 3)) * 0.3
    displaced = corners + offsets[surface.tile][:, None, :]
    match = match_support_faces(displaced, surface)
    assert match.matched.mean() > 0.95
    assert np.array_equal(match.tile_triangle[match.matched], np.flatnonzero(match.matched))
    assert match.report["median_tile_offset_m"] > 0.05


def test_match_support_faces_rejects_the_wrong_shape():
    surface = TileSurface(
        triangles=np.zeros((1, 3, 3)),
        uv=np.zeros((1, 3, 2)),
        patch=np.zeros(1, dtype=np.int64),
        tile=np.zeros(1, dtype=np.int64),
        patches=[np.zeros((4, 4, 3), np.uint8)],
        tile_files=("a.glb",),
    )
    with pytest.raises(ValueError, match=r"\[faces, 3, 3\]"):
        match_support_faces(np.zeros((4, 3)), surface)


def test_blocked_folds_keep_a_block_whole():
    centroids = np.array([[0.0, 0.0], [1.0, 1.0], [40.0, 0.0], [41.0, 1.0]])
    fold = blocked_folds(centroids, block_m=10.0, folds=2, seed=1)
    assert fold[0] == fold[1]
    assert fold[2] == fold[3]


def test_blocked_folds_validate_their_arguments():
    with pytest.raises(ValueError, match="folds"):
        blocked_folds(np.zeros((4, 2)), folds=1)
    with pytest.raises(ValueError, match="centroids"):
        blocked_folds(np.zeros(4))


def test_softmax_recovers_a_separable_problem():
    rng = np.random.default_rng(11)
    means = np.array([[-3.0, 0.0], [3.0, 0.0], [0.0, 4.0]])
    labels = rng.integers(0, 3, 600)
    features = means[labels] + rng.normal(size=(600, 2)) * 0.4
    weights = fit_softmax(features, labels, 3, l2=0.1)
    probability = softmax_probability(weights, features)
    assert np.allclose(probability.sum(axis=1), 1.0)
    assert (probability.argmax(axis=1) == labels).mean() > 0.97


def test_softmax_validates_its_inputs():
    with pytest.raises(ValueError, match="class_count"):
        fit_softmax(np.zeros((4, 2)), np.zeros(4, dtype=np.int64), 1)
    with pytest.raises(ValueError, match="index the class list"):
        fit_softmax(np.zeros((4, 2)), np.array([0, 1, 2, 5]), 3)


def test_temperature_flattens_an_overconfident_prediction():
    rng = np.random.default_rng(5)
    labels = rng.integers(0, 3, 900)
    sharp = np.full((900, 3), 0.005)
    sharp[np.arange(900), labels] = 0.99
    wrong = rng.random(900) < 0.4
    sharp[wrong] = np.roll(sharp[wrong], 1, axis=1)
    sharp /= sharp.sum(axis=1, keepdims=True)
    assert fit_temperature(sharp, labels) > 1.5


def test_temperature_leaves_a_calibrated_prediction_alone():
    rng = np.random.default_rng(6)
    probability = rng.dirichlet(np.ones(3) * 1.5, size=3000)
    labels = np.array([rng.choice(3, p=row) for row in probability])
    assert fit_temperature(probability, labels) == pytest.approx(1.0, abs=0.15)


def test_panorama_resolution_ratio_is_the_measured_linear_ratio():
    ratio = panorama_resolution_ratio(np.array([20.0]), np.array([0.196]))
    expected = 20.0 * (2.0 * np.pi / PANORAMA_WIDTH_PX) / 0.196
    assert ratio[0] == pytest.approx(expected, rel=1e-12)
    assert ratio[0] == pytest.approx(1.0 / 26.0, rel=0.05)


def test_panorama_resolution_ratio_saturates_past_the_crossover():
    ratio = panorama_resolution_ratio(np.array([520.0, 5000.0]), np.array([0.196, 0.196]))
    assert ratio[0] == pytest.approx(1.0, rel=0.05)
    assert ratio[1] == 1.0


def test_panorama_resolution_ratio_handles_a_missing_ground_sample_distance():
    ratio = panorama_resolution_ratio(np.array([20.0, 20.0]), np.array([np.nan, 0.0]))
    assert ratio.tolist() == [0.0, 0.0]


def test_support_rows_grow_with_texel_count_and_then_stop():
    counts = np.array([1, 4, 16, 64, 256, 100000])
    rows = support_rows(counts, maximum_rows=32)
    assert np.all(np.diff(rows) >= 0)
    assert rows[0] < rows[1] < rows[2] < rows[3]
    assert rows[-1] == 32
    assert rows.tolist()[:4] == [1, 2, 4, 8]


def test_dominance_factor_cannot_overturn_a_panorama_observation():
    rng = np.random.default_rng(17)
    materials = 6
    panorama = rng.random((500, materials)) * rng.integers(1, 40, size=(500, 1))
    panorama[:100] = 0.0
    requested = rng.random(500) * 50.0
    factor = dominance_factor(panorama, requested, headroom=0.5)
    allowed = requested * factor
    prior = 0.25
    before = (prior + panorama).argmax(axis=1)
    # The adversary puts every unit of texture mass on the runner-up.
    worst = np.argsort(prior + panorama, axis=1)[:, -2]
    after_alpha = prior + panorama.copy()
    after_alpha[np.arange(500), worst] += allowed
    seen = panorama.sum(axis=1) > 0.0
    assert np.array_equal(after_alpha.argmax(axis=1)[seen], before[seen])
    assert np.all(factor[~seen] == 1.0)


def test_posterior_top_mass_sits_between_the_prior_and_the_claim():
    probability = np.array([[0.7, 0.2, 0.1], [0.7, 0.2, 0.1]])
    mass = posterior_top_mass(np.array([0.0, 1e6]), probability, prior=0.25)
    assert mass[0] == pytest.approx(1.0 / 3.0)
    assert mass[1] == pytest.approx(0.7, abs=1e-4)
    growing = posterior_top_mass(np.array([0.1, 1.0, 10.0]), np.tile(probability[0], (3, 1)))
    assert np.all(np.diff(growing) > 0.0)


def test_posterior_top_mass_rejects_a_flat_probability_block():
    with pytest.raises(ValueError, match=r"\[faces, materials\]"):
        posterior_top_mass(np.array([1.0]), np.array([0.5, 0.5]))


def test_dominance_factor_validates_its_arguments():
    with pytest.raises(ValueError, match="headroom"):
        dominance_factor(np.zeros((2, 3)), np.zeros(2), headroom=1.0)
    with pytest.raises(ValueError, match=r"\[faces, materials\]"):
        dominance_factor(np.zeros(3), np.zeros(2))


def test_pairwise_separability_is_not_carried_by_the_larger_class():
    # 900 of class 0 all correct, 100 of class 1 all wrong. A raw pair accuracy
    # would read 0.9. The balanced number has to read 0.5.
    matrix = np.array([[900.0, 0.0], [100.0, 0.0]])
    assert pairwise_separability(matrix)[0, 1] == pytest.approx(0.5)
    assert collapsing_pairs(matrix) == [(0, 1)]


def test_collapsing_pairs_leaves_a_separable_pair_alone():
    matrix = np.array([[90.0, 10.0], [12.0, 88.0]])
    assert collapsing_pairs(matrix) == []


def test_confusion_matrix_counts_every_row():
    truth = np.array([0, 0, 1, 2, 2])
    prediction = np.array([0, 1, 1, 2, 0])
    matrix = confusion_matrix(truth, prediction, 3)
    assert matrix.sum() == 5
    assert matrix[0].tolist() == [1.0, 1.0, 0.0]
    assert matrix[2].tolist() == [1.0, 0.0, 1.0]


def small_classifier(*, temperature: np.ndarray | None = None) -> MaterialClassifier:
    weights = np.zeros((3, 2))
    weights[0] = [4.0, -4.0]
    material = np.array([[0.05, 0.9, 0.05], [0.05, 0.05, 0.9]])
    return MaterialClassifier(
        weights=weights,
        mean=np.zeros(2),
        scale=np.ones(2),
        class_labels=("masonry", "vegetation"),
        feature_names=("a", "b"),
        support_edges=np.array([16.0]),
        support_temperature=np.array([4.0, 1.0]) if temperature is None else temperature,
        material_labels=("unknown", "brick", "vegetation_effective"),
        material_matrix=material,
    )


def test_classifier_temperature_follows_texel_support():
    classifier = small_classifier()
    features = np.array([[1.0, 0.0], [1.0, 0.0]])
    probability = classifier.predict(features, np.array([8, 400]))
    assert probability[1].max() > probability[0].max()
    assert np.allclose(probability.sum(axis=1), 1.0)


def test_classifier_maps_class_onto_the_material_taxonomy():
    classifier = small_classifier()
    material = classifier.predict_material(np.array([[3.0, 0.0]]), np.array([400]))
    assert material.shape == (1, 3)
    assert np.allclose(material.sum(axis=1), 1.0)
    assert classifier.material_labels[material.argmax()] == "brick"


def test_classifier_round_trips_through_disk(tmp_path):
    classifier = small_classifier()
    classifier.save(tmp_path / "model.npz")
    restored = MaterialClassifier.load(tmp_path / "model.npz")
    assert restored.class_labels == classifier.class_labels
    assert restored.material_labels == classifier.material_labels
    assert np.array_equal(restored.weights, classifier.weights)
    assert np.array_equal(restored.support_temperature, classifier.support_temperature)
    assert np.allclose(
        restored.predict_material(np.array([[1.0, 0.0]]), np.array([50])),
        classifier.predict_material(np.array([[1.0, 0.0]]), np.array([50])),
    )


def test_classifier_rejects_an_inconsistent_shape():
    with pytest.raises(ValueError, match=r"\[features \+ 1, classes\]"):
        MaterialClassifier(
            weights=np.zeros((2, 2)),
            mean=np.zeros(2),
            scale=np.ones(2),
            class_labels=("a", "b"),
            feature_names=("x", "y"),
            support_edges=np.array([8.0]),
            support_temperature=np.array([1.0, 1.0]),
        )
    with pytest.raises(ValueError, match="one temperature per support bin"):
        MaterialClassifier(
            weights=np.zeros((3, 2)),
            mean=np.zeros(2),
            scale=np.ones(2),
            class_labels=("a", "b"),
            feature_names=("x", "y"),
            support_edges=np.array([8.0]),
            support_temperature=np.array([1.0]),
        )


def two_face_surface() -> tuple[TileSurface, np.ndarray]:
    triangles = np.array(
        [
            [[0.0, 0.0, 0.0], [6.4, 0.0, 0.0], [0.0, 0.0, 6.4]],
            [[20.0, 0.0, 0.0], [26.4, 0.0, 0.0], [20.0, 0.0, 6.4]],
        ]
    )
    image = np.zeros((32, 32, 3), np.uint8)
    image[:, :16] = (40, 120, 40)
    image[:, 16:] = (210, 205, 200)
    uv = np.array(
        [
            [[0.02, 0.02], [0.47, 0.02], [0.02, 0.47]],
            [[0.53, 0.02], [0.98, 0.02], [0.53, 0.47]],
        ]
    )
    surface = TileSurface(
        triangles=triangles,
        uv=uv,
        patch=np.zeros(2, dtype=np.int64),
        tile=np.zeros(2, dtype=np.int64),
        patches=[image],
        tile_files=("tile.glb",),
    )
    return surface, triangles


def test_build_texture_evidence_emits_rows_that_reflect_texel_support():
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    assert match.matched.all()
    classifier = MaterialClassifier(
        weights=np.zeros((len(features.names) + 1, 2)),
        mean=features.values.mean(axis=0),
        scale=features.values.std(axis=0) + 1e-9,
        class_labels=("vegetation", "masonry"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
        material_labels=("unknown", "brick", "vegetation_effective"),
        material_matrix=np.array([[0.0, 0.1, 0.9], [0.1, 0.9, 0.0]]),
    )
    evidence = build_texture_evidence(features, match, classifier, face_range_m=np.array([20.0, 20.0]))
    assert len(evidence.face_index) == 2
    assert np.array_equal(evidence.rows, support_rows(evidence.texel_count))
    assert np.all(evidence.quality.resolution < 0.1)
    assert np.all(evidence.concentration() > 0.0)
    assert evidence.report["faces_with_texture_evidence"] == 2.0


def test_texture_evidence_only_moves_the_material_axis():
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    weights = np.zeros((len(features.names) + 1, 2))
    weights[0] = [6.0, -6.0]
    classifier = MaterialClassifier(
        weights=weights,
        mean=features.values.mean(axis=0),
        scale=features.values.std(axis=0) + 1e-9,
        class_labels=("vegetation", "masonry"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
        material_labels=("unknown", "brick", "vegetation_effective"),
        material_matrix=np.array([[0.0, 0.05, 0.95], [0.05, 0.95, 0.0]]),
    )
    evidence = build_texture_evidence(features, match, classifier, face_range_m=np.array([400.0, 400.0]))
    accumulator = EvidenceAccumulator(2, ["facade", "road"], list(classifier.material_labels), ["rough", "wet"])
    before_entity = accumulator.entity_alpha.copy()
    before_attribute = accumulator.attribute_alpha.copy()
    before_material = accumulator.material_alpha.copy()
    evidence.apply(accumulator)
    assert np.array_equal(accumulator.entity_alpha, before_entity)
    assert np.array_equal(accumulator.attribute_alpha, before_attribute)
    assert np.array_equal(accumulator.attribute_beta, np.full_like(accumulator.attribute_beta, 0.5))
    added = accumulator.material_alpha - before_material
    assert added.sum() > 0.0
    assert np.allclose(added.sum(axis=1), evidence.concentration(), rtol=1e-3, atol=1e-3)
    assert np.all(added.argmax(axis=1) == evidence.material_probability.argmax(axis=1))


def test_texture_evidence_refuses_a_mismatched_accumulator():
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    classifier = MaterialClassifier(
        weights=np.zeros((len(features.names) + 1, 2)),
        mean=features.values.mean(axis=0),
        scale=features.values.std(axis=0) + 1e-9,
        class_labels=("a", "b"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
        material_labels=("unknown", "brick", "vegetation_effective"),
        material_matrix=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
    )
    evidence = build_texture_evidence(features, match, classifier, face_range_m=np.array([20.0, 20.0]))
    accumulator = EvidenceAccumulator(2, ["facade"], ["unknown", "brick"], ["rough"])
    with pytest.raises(ValueError, match="material labels differ"):
        evidence.apply(accumulator)


def test_texture_evidence_is_capped_where_the_panorama_has_spoken():
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    classifier = MaterialClassifier(
        weights=np.zeros((len(features.names) + 1, 2)),
        mean=features.values.mean(axis=0),
        scale=features.values.std(axis=0) + 1e-9,
        class_labels=("a", "b"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
        material_labels=("unknown", "brick", "vegetation_effective"),
        material_matrix=np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
    )
    panorama = np.array([[0.0, 0.0, 0.0], [0.0, 0.2, 0.0]])
    free = build_texture_evidence(features, match, classifier, face_range_m=np.array([400.0, 400.0]))
    capped = build_texture_evidence(
        features, match, classifier, face_range_m=np.array([400.0, 400.0]), panorama_alpha=panorama
    )
    assert capped.quality.independence[0] == 1.0
    assert capped.quality.independence[1] < 1.0
    assert capped.concentration()[1] < free.concentration()[1]
    assert capped.concentration()[0] == pytest.approx(free.concentration()[0])


def test_a_panorama_argmax_survives_the_texture_inside_the_accumulator():
    """The guarantee end to end, not just on the discount that implements it."""
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    materials = ("unknown", "brick", "vegetation_effective")
    classifier = MaterialClassifier(
        weights=np.zeros((len(features.names) + 1, 2)),
        mean=features.values.mean(axis=0),
        scale=features.values.std(axis=0) + 1e-9,
        class_labels=("a", "b"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
        material_labels=materials,
        material_matrix=np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]),
    )
    # The panorama is only just ahead on both faces, and the texture is certain
    # of the other class. This is the case the cap exists for.
    panorama = np.array([[0.0, 0.6, 0.4], [0.0, 3.0, 2.4]])
    accumulator = EvidenceAccumulator(2, ["facade"], list(materials), ["rough"])
    accumulator.material_alpha += panorama.astype(np.float32)
    winner = accumulator.material_posterior().argmax(axis=1)
    evidence = build_texture_evidence(
        features, match, classifier, face_range_m=np.array([400.0, 400.0]), panorama_alpha=panorama
    )
    evidence.apply(accumulator)
    assert np.array_equal(accumulator.material_posterior().argmax(axis=1), winner)
    assert np.all(evidence.concentration() <= 0.5 * np.array([0.2, 0.6]) + 1e-9)


def test_build_texture_evidence_needs_a_material_mapping():
    surface, triangles = two_face_surface()
    features = texture_features(surface)
    match = match_support_faces(triangles, surface)
    classifier = MaterialClassifier(
        weights=np.zeros((len(features.names) + 1, 2)),
        mean=np.zeros(len(features.names)),
        scale=np.ones(len(features.names)),
        class_labels=("a", "b"),
        feature_names=tuple(features.names),
        support_edges=np.array([16.0]),
        support_temperature=np.array([1.0, 1.0]),
    )
    with pytest.raises(ValueError, match="class to material mapping"):
        build_texture_evidence(features, match, classifier, face_range_m=np.array([20.0, 20.0]))
