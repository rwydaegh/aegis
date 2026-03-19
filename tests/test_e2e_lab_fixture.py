"""Tracked E2E lab fixture: icosahedron STL matches synthetic test mesh."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from conftest import make_icosahedron

from aegis.geometry.mesh import BodyMesh

FIXTURE_STL = Path(__file__).resolve().parent / "fixtures" / "e2e_lab" / "e2e_icosahedron.stl"


def test_e2e_lab_stl_exists():
    assert FIXTURE_STL.is_file(), f"Missing {FIXTURE_STL} (regenerate per fixtures/e2e_lab/README.md)"


def test_e2e_lab_stl_matches_icosahedron():
    ref = make_icosahedron()
    disk = BodyMesh.load(FIXTURE_STL)
    assert disk.n_triangles == ref.n_triangles == 20
    np.testing.assert_allclose(disk.vertices, ref.vertices, rtol=0, atol=1e-5)
    np.testing.assert_allclose(disk.normals, ref.normals, rtol=0, atol=1e-5)


def test_bodymesh_stl_roundtrip(tmp_path):
    ref = make_icosahedron()
    p = tmp_path / "roundtrip.stl"
    ref.save_binary_stl(p)
    back = BodyMesh.load(p)
    assert back.n_triangles == ref.n_triangles
    np.testing.assert_allclose(back.vertices, ref.vertices, rtol=0, atol=1e-5)
