"""AEGIS performance benchmarks for CodSpeed.

Run locally:  pytest benchmarks/ --codspeed
CI:           triggered automatically via .github/workflows/benchmarks.yml
"""

from __future__ import annotations

import numpy as np
import pytest
from pytest_codspeed import BenchmarkFixture

# ---------------------------------------------------------------------------
# Kernel benchmarks (levels 2-6)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="kernel_level2")
def test_kernel_level2(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.level2_geometric import level2_geometric
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    T0 = SKIN_28GHZ.T0

    def run():
        return level2_geometric(normals, k_hat, power, T0)

    run()
    benchmark(run)


@pytest.mark.benchmark(group="kernel_level3")
def test_kernel_level3(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.level3_fresnel import level3_fresnel
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    n_tilde = SKIN_28GHZ.n_complex

    def run():
        return level3_fresnel(normals, k_hat, power, n_tilde)

    run()
    benchmark(run)


@pytest.mark.benchmark(group="kernel_level4")
def test_kernel_level4(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.level4_polarisation import level4_polarisation
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    n_tilde = SKIN_28GHZ.n_complex

    def run():
        return level4_polarisation(normals, k_hat, power, n_tilde, q=0.3)

    run()
    benchmark(run)


@pytest.mark.benchmark(group="kernel_level5")
def test_kernel_level5(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.level5_curvature import level5_curvature
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    n_tilde = SKIN_28GHZ.n_complex
    T0 = SKIN_28GHZ.T0
    curvature_H = np.full(bench_mesh.n_triangles, 5.0)

    def run():
        return level5_curvature(normals, k_hat, power, n_tilde, T0, curvature_H, 28e9)

    run()
    benchmark(run)


@pytest.mark.benchmark(group="kernel_level6")
def test_kernel_level6(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.level6_diffraction import level6_diffraction
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    n_tilde = SKIN_28GHZ.n_complex
    T0 = SKIN_28GHZ.T0
    curvature_H = np.full(bench_mesh.n_triangles, 5.0)

    def run():
        return level6_diffraction(normals, k_hat, power, n_tilde, T0, curvature_H, 28e9)

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Unified spatial kernel (all corrections enabled)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="spatial_kernel")
def test_spatial_kernel_all_corrections(benchmark: BenchmarkFixture, bench_mesh, bench_paths) -> None:
    from aegis.kernels.spatial import spatial_kernel
    from aegis.tissue.dielectric import SKIN_28GHZ

    normals, k_hat, power = bench_mesh.normals, bench_paths.k_hat, bench_paths.power
    n_tilde = SKIN_28GHZ.n_complex
    T0 = SKIN_28GHZ.T0
    curvature_H = np.full(bench_mesh.n_triangles, 5.0)

    def run():
        return spatial_kernel(
            normals,
            k_hat,
            power,
            n_tilde,
            T0,
            28e9,
            fresnel=True,
            polarisation=True,
            q=0.3,
            curvature=True,
            diffraction=True,
            curvature_H=curvature_H,
        )

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Full engine compute (includes result building + spatial averaging)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="engine_compute")
def test_engine_compute_level3(benchmark: BenchmarkFixture, bench_mesh, bench_paths, bench_engine) -> None:
    bench_engine.compute(bench_mesh, bench_paths, level=3)

    def run():
        return bench_engine.compute(bench_mesh, bench_paths, level=3)

    benchmark(run)


# ---------------------------------------------------------------------------
# Fresnel computation (vectorized over angles)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="fresnel")
def test_fresnel_transmission_vectorized(benchmark: BenchmarkFixture) -> None:
    from aegis.tissue.dielectric import SKIN_28GHZ
    from aegis.tissue.fresnel import fresnel_transmission

    mu = np.linspace(0, 1, 10_000)
    n_tilde = SKIN_28GHZ.n_complex

    def run():
        return fresnel_transmission(mu, n_tilde)

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Geometry: Fibonacci sphere sampling
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="fibonacci_sphere")
def test_fibonacci_sphere_4096(benchmark: BenchmarkFixture) -> None:
    from aegis.geometry.projected_area import _fibonacci_sphere_cache, fibonacci_sphere

    def run():
        _fibonacci_sphere_cache.clear()
        return fibonacci_sphere(4096)

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Geometry: Projected area computation
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="projected_area")
def test_projected_area(benchmark: BenchmarkFixture, bench_mesh) -> None:
    from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere

    dirs = fibonacci_sphere(1024)

    def run():
        return compute_projected_area(bench_mesh.normals, bench_mesh.areas, dirs)

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Spatial averaging matrix precomputation
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="averaging_matrix")
def test_averaging_matrix_precompute(benchmark: BenchmarkFixture, bench_mesh) -> None:
    from aegis.geometry.averaging import precompute_averaging_matrix

    def run():
        return precompute_averaging_matrix(bench_mesh.centroids, bench_mesh.areas, 4e-4)

    run()
    benchmark(run)


# ---------------------------------------------------------------------------
# Analysis: exposure heatmap
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="exposure_heatmap")
def test_exposure_heatmap(benchmark: BenchmarkFixture, bench_mesh, bench_paths, bench_tissue) -> None:
    from aegis.analysis import exposure_heatmap

    def run():
        return exposure_heatmap(bench_mesh, bench_paths, bench_tissue)

    run()
    benchmark(run)
