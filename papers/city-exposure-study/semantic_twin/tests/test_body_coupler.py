from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from semantic_twin.exposure import BodyCoupler, BodyExposure
from semantic_twin.illumination import fibonacci_sphere


def _real_level_two_coupler() -> BodyCoupler:
    pytest.importorskip("aegis")
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.tissue import TissueModel

    corners = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 3.0],
            [2.0, 0.0, 3.0],
            [2.0, 1.0, 3.0],
            [0.0, 1.0, 3.0],
        ],
        dtype=np.float64,
    )
    quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    triangles = np.asarray(
        [[corners[a], corners[b], corners[c]] for a, b, c, _d in quads]
        + [[corners[a], corners[c], corners[d]] for a, _b, c, d in quads]
    )
    body = BodyMesh.from_arrays(triangles, name="couple-many-box")
    tissue = TissueModel.from_database("Skin", 15.0e9)
    coupler = BodyCoupler.__new__(BodyCoupler)
    coupler.body = body
    coupler.tissue = tissue
    coupler.engine = DosimetryEngine(tissue)
    coupler.level = 2
    coupler.body_mass_kg = 70.0
    coupler.frequency_hz = 15.0e9
    return coupler


def test_couple_many_forced_chunks_match_normal_level_two_coupling() -> None:
    coupler = _real_level_two_coupler()
    cells = 37
    chunk_cells = 7
    grid = fibonacci_sphere(cells)
    solid_angle = 4.0 * np.pi / cells
    rng = np.random.default_rng(481)
    spectra = np.stack(
        (
            np.full(cells, 1.0 / (4.0 * np.pi)),
            np.abs(rng.normal(size=cells)),
            np.eye(cells, dtype=np.float64)[11] / solid_angle,
        )
    )
    reference_s0 = 0.73

    expected = tuple(coupler.couple(grid, rho, solid_angle, reference_s0) for rho in spectra)
    actual = coupler.couple_many(
        grid,
        spectra,
        solid_angle,
        reference_s0,
        chunk_cells=chunk_cells,
    )

    assert chunk_cells < cells
    assert len(actual) == len(expected)
    for chunked, normal in zip(actual, expected, strict=True):
        for field in fields(BodyExposure):
            assert getattr(chunked, field.name) == pytest.approx(
                getattr(normal, field.name),
                rel=2.0e-14,
                abs=1.0e-15,
            ), field.name
