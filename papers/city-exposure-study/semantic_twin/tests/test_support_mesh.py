from __future__ import annotations

import pathlib
import struct

import numpy as np
import pytest
from semantic_twin.scene.camera_ground import camera_altitude, ground_elevation
from semantic_twin.scene.mesh import read_binary_ply, read_binary_ply_vertices


def _write_ply(path: pathlib.Path, vertices: np.ndarray, faces: np.ndarray) -> pathlib.Path:
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {len(vertices)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        f"element face {len(faces)}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    payload = bytearray(header.encode())
    payload += np.asarray(vertices, dtype="<f4").tobytes()
    for face in faces:
        payload += struct.pack("<B3i", 3, *(int(index) for index in face))
    path.write_bytes(bytes(payload))
    return path


def _slab(z: float, half: float = 10.0, offset: tuple[float, float] = (0.0, 0.0)) -> tuple[np.ndarray, np.ndarray]:
    x, y = offset
    vertices = np.array(
        [
            [x - half, y - half, z],
            [x + half, y - half, z],
            [x + half, y + half, z],
            [x - half, y + half, z],
        ],
        dtype=float,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return vertices, faces


def test_read_binary_ply_round_trips_vertices_and_faces(tmp_path: pathlib.Path) -> None:
    vertices, faces = _slab(3.5)
    path = _write_ply(tmp_path / "slab.ply", vertices, faces)
    read_vertices, read_faces = read_binary_ply(path)
    assert np.allclose(read_vertices, vertices)
    assert np.array_equal(read_faces, faces)
    assert np.allclose(read_binary_ply_vertices(path), vertices)


def test_read_binary_ply_rejects_an_unexpected_vertex_layout(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "coloured.ply"
    path.write_bytes(
        b"ply\nformat binary_little_endian 1.0\nelement vertex 1\nproperty float x\nproperty float y\n"
        b"property float z\nproperty uchar red\nelement face 0\n"
        b"property list uchar int vertex_indices\nend_header\n" + b"\x00" * 13
    )
    with pytest.raises(ValueError, match="float x, y, z"):
        read_binary_ply(path)


def test_ground_elevation_finds_the_surface_under_the_camera(tmp_path: pathlib.Path) -> None:
    vertices, faces = _slab(12.25)
    sample = ground_elevation(vertices, faces, 1.0, -2.0, ceiling_z_m=20.0, patch_m=2.0)
    assert sample.elevation_m == pytest.approx(12.25)
    assert sample.peak_to_peak_m == pytest.approx(0.0)
    assert sample.n_hits == sample.n_samples == 25


def test_ground_elevation_ignores_an_arcade_roof_above_the_ceiling() -> None:
    pavement_v, pavement_f = _slab(10.0)
    roof_v, roof_f = _slab(16.0)
    vertices = np.vstack([pavement_v, roof_v])
    faces = np.vstack([pavement_f, roof_f + len(pavement_v)])
    assert ground_elevation(vertices, faces, 0.0, 0.0, ceiling_z_m=13.0, patch_m=0.0).elevation_m == pytest.approx(10.0)
    assert ground_elevation(vertices, faces, 0.0, 0.0, ceiling_z_m=20.0, patch_m=0.0).elevation_m == pytest.approx(16.0)


def test_ground_elevation_reports_the_spread_across_a_step() -> None:
    low_v, low_f = _slab(10.0, half=2.0, offset=(-2.0, 0.0))
    high_v, high_f = _slab(10.6, half=2.0, offset=(2.0, 0.0))
    vertices = np.vstack([low_v, high_v])
    faces = np.vstack([low_f, high_f + len(low_v)])
    sample = ground_elevation(vertices, faces, 0.0, 0.0, ceiling_z_m=12.0, patch_m=3.0)
    assert sample.peak_to_peak_m == pytest.approx(0.6, abs=1e-6)
    assert sample.spread_m > 0.2


def test_ground_elevation_raises_rather_than_guessing_over_a_hole() -> None:
    vertices, faces = _slab(10.0, half=1.0)
    with pytest.raises(ValueError, match="no surface under"):
        ground_elevation(vertices, faces, 50.0, 50.0, ceiling_z_m=20.0, patch_m=0.0)


def test_camera_altitude_falls_back_to_the_scene_constant_without_a_mesh() -> None:
    scene = {"camera_ground_z_m": 50.0, "camera_height_m": 2.5}
    altitude, provenance = camera_altitude(scene, 0.0, 0.0)
    assert altitude == pytest.approx(52.5)
    assert "scene camera_ground_z_m" in provenance["altitude_source"]


def test_camera_altitude_prefers_the_ground_under_this_camera() -> None:
    scene = {"camera_ground_z_m": 50.0, "camera_height_m": 2.5}
    vertices, faces = _slab(50.4)
    altitude, provenance = camera_altitude(scene, 1.0, 1.0, support_mesh=(vertices, faces))
    assert altitude == pytest.approx(52.9)
    assert provenance["ground_minus_scene_constant_m"] == pytest.approx(0.4)
    assert "support mesh" in provenance["altitude_source"]
