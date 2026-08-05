"""The translation from facade-tip next-event transport to forward Sionna RT."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.transport.sionna_forward import (
    FULLY_DIFFUSE_RMS_HEIGHT_M,
    adjoint_transfer,
    comparison,
    free_space_scale,
    forward_transfer_subprocess,
    open_square_environment,
    reduce_sionna_paths,
)
from semantic_twin.transport.sionna_check import write_ply
from semantic_twin.transport.tracer import fresnel_power_reflectance, specular_share


def test_open_square_is_small_exact_and_open_on_one_side() -> None:
    environment = open_square_environment()

    assert environment.vertices.shape == (16, 3)
    assert environment.faces.shape == (8, 3)
    assert environment.sources.shape == (27, 3)
    assert environment.receivers.shape == (6, 3)
    assert np.all(environment.sources[:, 2] == 20.5)
    assert np.all(environment.receivers[:, 2] == 1.5)
    assert np.any(environment.receivers[:, 1] < -40.0)


def test_open_square_can_balance_a_larger_source_set_across_walls() -> None:
    environment = open_square_environment(source_count=81)

    assert environment.sources.shape == (81, 3)
    assert np.count_nonzero(environment.sources[:, 1] == 40.0) == 27
    assert np.count_nonzero(environment.sources[:, 0] == -40.0) == 27
    assert np.count_nonzero(environment.sources[:, 0] == 40.0) == 27


def test_open_square_rejects_an_empty_source_set() -> None:
    with pytest.raises(ValueError, match="positive"):
        open_square_environment(source_count=0)


def test_path_reduction_averages_polarisations_and_splits_line_of_sight() -> None:
    wavelength = 0.02
    scale = free_space_scale(wavelength)
    gains = np.array(
        [
            [[0.01, 0.002], [0.02, 0.003], [0.03, 0.004]],
            [[0.04, 0.005], [0.05, 0.006], [0.06, 0.007]],
        ]
    )
    amplitude = np.zeros((2, 2, 3, 2, 2), dtype=np.complex128)
    field = np.sqrt(gains * scale)
    amplitude[:, 0, :, 0, :] = field
    amplitude[:, 1, :, 1, :] = field
    interactions = np.zeros((1, 2, 3, 2), dtype=np.uint32)
    interactions[..., 1] = 4
    valid = np.ones((2, 3, 2), dtype=bool)
    valid[1, 2, 1] = False
    paths = SimpleNamespace(
        a=(amplitude.real, amplitude.imag),
        interactions=interactions,
        valid=valid,
    )

    direct, total, paths_per_source = reduce_sionna_paths(paths, wavelength)

    assert np.allclose(direct, gains[..., 0])
    expected_total = gains.sum(axis=-1)
    expected_total[1, 2] = gains[1, 2, 0]
    assert np.allclose(total, expected_total)
    assert np.array_equal(paths_per_source, np.array([4, 4, 3]))


def test_validation_surface_removes_material_and_specular_differences() -> None:
    cosine = np.linspace(np.cos(np.radians(89.0)), 1.0, 100)
    reflectance = fresnel_power_reflectance(cosine, np.full(cosine.shape, PEC_PERMITTIVITY))
    coherent = specular_share(
        np.full(cosine.shape, FULLY_DIFFUSE_RMS_HEIGHT_M),
        cosine,
        299_792_458.0 / 15.0e9,
    )
    assert np.max(np.abs(10.0 * np.log10(reflectance))) < 0.001
    assert np.max(coherent) < 1.0e-20


def test_forward_and_adjoint_match_the_same_diffuse_plane_closed_form() -> None:
    """One normal forward trace and one adjoint trace meet at a known answer."""
    root = str(__file__).rsplit("/tests/", 1)[0]
    body = f"""
        import json
        import pathlib
        import tempfile
        import numpy as np
        import sys
        sys.path.insert(0, {root!r})

        from semantic_twin.propagation.geometry import PlaneGeometry
        from semantic_twin.transport.sionna_forward import (
            TransferSamples,
            adjoint_transfer,
            build_validation_scene,
            comparison,
            forward_transfer,
        )

        sources = np.array([[0.0, 0.0, 20.0]])
        receivers = np.array([[0.0, 0.0, 10.0]])
        adjoint = adjoint_transfer(
            PlaneGeometry(0.0),
            sources,
            receivers,
            max_depth=1,
            rays=100_000,
            seeds=(1, 2),
        )

        half = 500.0
        vertices = np.array([
            [-half, -half, 0.0],
            [half, -half, 0.0],
            [half, half, 0.0],
            [-half, half, 0.0],
        ])
        faces = np.array([[0, 1, 2], [0, 2, 3]])
        scene = build_validation_scene(
            vertices,
            faces,
            15.0e9,
            cache_dir=pathlib.Path(tempfile.mkdtemp()),
        )
        rows = [
            forward_transfer(
                scene,
                sources,
                receivers,
                max_depth=1,
                samples_per_src=100_000,
                max_num_paths_per_src=500_000,
                source_chunk=1,
                seed=seed,
            )
            for seed in (10, 11)
        ]
        sionna = TransferSamples(
            direct=np.array([row["direct"] for row in rows]),
            total=np.array([row["total"] for row in rows]),
            seconds=np.array([row["seconds"] for row in rows]),
        )
        print(json.dumps({{
            "adjoint_direct": float(adjoint.direct.mean()),
            "adjoint_bounced": float(adjoint.bounced.mean()),
            "sionna_direct": float(sionna.direct.mean()),
            "sionna_bounced": float(sionna.bounced.mean()),
            "saturated": any(row["path_buffer_saturated"] for row in rows),
            "comparison": comparison(adjoint, sionna),
        }}))
    """
    finished = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "DRJIT_NUM_THREADS": "2"},
    )
    if finished.returncode != 0:
        pytest.skip(f"Sionna unavailable in a subprocess: {finished.stderr.strip()[-400:]}")
    answer = json.loads(finished.stdout.strip().splitlines()[-1])

    direct_target = 1.0 / (20.0 - 10.0) ** 2
    bounced_target = 2.0 / (20.0 + 10.0) ** 2
    assert not answer["saturated"]
    assert answer["adjoint_direct"] == pytest.approx(direct_target, rel=1.0e-6)
    assert answer["sionna_direct"] == pytest.approx(direct_target, rel=1.0e-5)
    assert answer["adjoint_bounced"] == pytest.approx(bounced_target, rel=0.03)
    assert answer["sionna_bounced"] == pytest.approx(bounced_target, rel=0.01)
    assert answer["comparison"]["total"]["max_abs_db"] < 0.05


def test_forward_and_adjoint_match_in_a_two_surface_corner(tmp_path) -> None:
    """A finite corner checks visibility and two interaction orders."""
    vertices = np.array(
        [
            [-60.0, -60.0, 0.0],
            [60.0, -60.0, 0.0],
            [60.0, 60.0, 0.0],
            [-60.0, 60.0, 0.0],
            [0.0, -60.0, 0.0],
            [0.0, 60.0, 0.0],
            [0.0, 60.0, 50.0],
            [0.0, -60.0, 50.0],
        ]
    )
    faces = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
    mesh = tmp_path / "corner.ply"
    mesh.write_bytes(write_ply(vertices, faces))

    from semantic_twin.propagation.geometry import MitsubaGeometry

    geometry = MitsubaGeometry(mesh, variant="llvm_ad_rgb")
    sources = np.array([[12.0, 28.0, 18.0], [35.0, -15.0, 12.0], [-12.0, 28.0, 18.0]])
    receivers = np.array([[10.0, -20.0, 2.0], [18.0, 10.0, 2.0]])
    adjoint = adjoint_transfer(
        geometry,
        sources,
        receivers,
        max_depth=2,
        rays=150_000,
        seeds=(1, 2, 3),
    )
    sionna, runs = forward_transfer_subprocess(
        geometry.vertices,
        geometry.faces,
        sources,
        receivers,
        frequency_hz=15.0e9,
        cache_dir=tmp_path / "sionna",
        max_depth=2,
        samples_per_src=150_000,
        max_num_paths_per_src=1_500_000,
        source_chunk=3,
        seeds=(10, 11, 12),
    )
    residual = comparison(adjoint, sionna)

    assert not any(run["path_buffer_saturated"] for run in runs)
    assert residual["direct"]["max_abs_db"] < 0.001
    assert residual["total"]["max_abs_db"] < 0.1
