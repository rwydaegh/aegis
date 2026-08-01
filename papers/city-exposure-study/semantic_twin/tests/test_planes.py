from __future__ import annotations

import numpy as np
from semantic_twin.planes import (
    UNASSIGNED,
    cluster_table,
    face_adjacency,
    face_geometry,
    flatten_cluster,
    plane_basis,
    rebuild,
    segment_planes,
    weld,
)


def _grid(rows: int, columns: int, spacing: float = 2.0, height=None):
    """A triangulated rectangular grid in the z = height(x, y) plane."""
    vertices = []
    for i in range(rows + 1):
        for j in range(columns + 1):
            z = 0.0 if height is None else height(i * spacing, j * spacing)
            vertices.append([i * spacing, j * spacing, z])
    faces = []
    index = lambda i, j: i * (columns + 1) + j  # noqa: E731
    for i in range(rows):
        for j in range(columns):
            faces.append([index(i, j), index(i + 1, j), index(i + 1, j + 1)])
            faces.append([index(i, j), index(i + 1, j + 1), index(i, j + 1)])
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)


def test_weld_merges_split_vertices():
    vertices = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1e-6], [1.0, 0.0, 0.0]])
    faces = np.array([[0, 1, 2]])
    welded = weld(vertices, faces)
    assert welded[0] == welded[1]
    assert welded[2] != welded[0]


def test_adjacency_finds_shared_edges():
    vertices, faces = _grid(1, 1)
    starts, neighbours = face_adjacency(faces, weld(vertices, faces))
    assert len(starts) == len(faces) + 1
    assert set(neighbours[starts[0] : starts[1]]) == {1}


def test_flat_grid_becomes_one_cluster():
    vertices, faces = _grid(4, 4)
    clusters, label = segment_planes(vertices, faces, min_area_m2=1.0)
    assert len(clusters) == 1
    assert np.all(label == 0)
    assert clusters[0].area_m2 == 64.0
    assert clusters[0].residual_m < 1e-9
    assert abs(abs(float(clusters[0].normal[2])) - 1.0) < 1e-9


def test_a_bent_panel_does_not_join_a_flat_one():
    flat_vertices, flat_faces = _grid(4, 4)
    fold_vertices, fold_faces = _grid(4, 4, height=lambda x, y: 0.6 * x)
    fold_vertices = fold_vertices + np.array([10.0, 0.0, 0.0])
    vertices = np.concatenate([flat_vertices, fold_vertices])
    faces = np.concatenate([flat_faces, fold_faces + len(flat_vertices)])
    clusters, _ = segment_planes(vertices, faces, min_area_m2=1.0)
    assert len(clusters) == 2
    normals = np.array([cluster.normal for cluster in clusters])
    assert np.min(np.abs(normals[:, 2])) < 0.9


def test_small_regions_stay_as_built():
    vertices, faces = _grid(1, 1)
    clusters, label = segment_planes(vertices, faces, min_area_m2=100.0)
    assert clusters == []
    assert np.all(label == UNASSIGNED)


def test_flatten_gives_every_face_the_same_normal():
    vertices, faces = _grid(6, 6, height=lambda x, y: 0.01 * np.sin(x) * np.cos(y))
    clusters, _ = segment_planes(vertices, faces, min_area_m2=1.0)
    assert len(clusters) == 1
    flat_vertices, flat_faces = flatten_cluster(vertices, faces, clusters[0])
    _, _, normal = face_geometry(flat_vertices, flat_faces)
    assert np.all(normal @ clusters[0].normal > 1.0 - 1e-6)


def test_rebuild_shrinks_a_flat_wall_and_keeps_its_area():
    vertices, faces = _grid(8, 8)
    new_vertices, new_faces, report = rebuild(vertices, faces, min_area_m2=1.0)
    _, area, _ = face_geometry(new_vertices, new_faces)
    assert report["clusters"] == 1
    assert len(new_faces) < len(faces) / 8
    assert abs(float(area.sum()) - 256.0) < 1e-6


def test_rebuild_keeps_the_faces_it_did_not_cluster():
    vertices, faces = _grid(4, 4)
    spike = np.array([[4.0, 4.0, 3.0]])
    vertices = np.concatenate([vertices, spike])
    faces = np.concatenate([faces, np.array([[0, 1, len(vertices) - 1]])])
    _, new_faces, report = rebuild(vertices, faces, min_area_m2=1.0)
    assert report["kept_triangles"] >= 1
    assert report["clusters"] == 1


def test_plane_basis_is_orthonormal():
    for normal in (np.array([0.0, 0.0, 1.0]), np.array([0.6, 0.8, 0.0])):
        u, v = plane_basis(normal)
        assert abs(float(u @ v)) < 1e-12
        assert abs(float(u @ normal)) < 1e-12
        assert abs(float(np.linalg.norm(u)) - 1.0) < 1e-12
        assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-12


def test_cluster_table_carries_the_plane_equation():
    vertices, faces = _grid(4, 4)
    clusters, _ = segment_planes(vertices, faces, min_area_m2=1.0)
    table = cluster_table(clusters)
    assert table["count"] == 1
    plane = table["planes"][0]
    assert abs(plane["offset_m"]) < 1e-9
    assert plane["area_m2"] == 64.0
