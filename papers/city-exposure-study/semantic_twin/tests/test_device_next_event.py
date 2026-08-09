from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.illumination.sources import SourceSet
from semantic_twin.illumination.sphere import nearest_cell
from semantic_twin.materials.atlas_binding import AtlasMaterialBinding
from semantic_twin.propagation.geometry import DeviceIntersection, MitsubaGeometry
from semantic_twin.transport.device_kernel import DeviceSbrKernel
from semantic_twin.transport.device_next_event import (
    BoundDeviceSpecularFaceProposal,
    DeviceNextEventGather,
    DeviceSpecularFaceProposal,
    device_source_sample,
)
from semantic_twin.transport.device_tracer import DeviceEscapeTracer
from semantic_twin.transport.next_event import NextEventEstimator, NextEventGather
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


def _sources(positions: np.ndarray, weights: np.ndarray | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        sites=lambda: np.asarray(positions, dtype=np.float64),
        source_weights=weights,
    )


def _source_set(positions: np.ndarray, weights: np.ndarray | None = None) -> SourceSet:
    return SourceSet(
        positions=np.asarray(positions, dtype=np.float64),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=weights,
    )


def _write_plane(path: Path, *, extent: float = 100.0) -> Path:
    path.write_text(
        f"""ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
{-extent} {-extent} 0
{extent} {-extent} 0
{extent} {extent} 0
{-extent} {extent} 0
3 0 1 2
3 0 2 3
"""
    )
    return path


def _write_parallel_planes(path: Path, heights: tuple[float, ...]) -> Path:
    rows = [
        "ply",
        "format ascii 1.0",
        f"element vertex {4 * len(heights)}",
        "property float x",
        "property float y",
        "property float z",
        f"element face {2 * len(heights)}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    for height in heights:
        rows.extend(
            (
                f"-100 -100 {height}",
                f"100 -100 {height}",
                f"100 100 {height}",
                f"-100 100 {height}",
            )
        )
    for start in range(0, 4 * len(heights), 4):
        rows.extend((f"3 {start} {start + 1} {start + 2}", f"3 {start} {start + 2} {start + 3}"))
    path.write_text("\n".join(rows) + "\n")
    return path


def _write_cube(path: Path) -> Path:
    path.write_text(
        """ply
format ascii 1.0
element vertex 8
property float x
property float y
property float z
element face 12
property list uchar int vertex_indices
end_header
-10 -10 -10
10 -10 -10
10 10 -10
-10 10 -10
-10 -10 10
10 -10 10
10 10 10
-10 10 10
3 0 2 1
3 0 3 2
3 4 5 6
3 4 6 7
3 0 1 5
3 0 5 4
3 1 2 6
3 1 6 5
3 2 3 7
3 2 7 6
3 3 0 4
3 3 4 7
"""
    )
    return path


def _set_variant(variant: str) -> None:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant(variant)
    except ImportError as error:
        pytest.skip(str(error))


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_device_alias_sampler_represents_weighted_source_probabilities(variant: str) -> None:
    _set_variant(variant)
    gather = DeviceNextEventGather(
        _sources(
            np.array([[0.0, 0.0, 2.0], [1.0, 0.0, 2.0], [2.0, 0.0, 2.0]]),
            np.array([0.05, 0.15, 0.80]),
        )
    )
    # A stratified uniform sequence removes Monte Carlo uncertainty from this
    # validation of the exact device-side table lookup.
    uniform = (np.arange(1_000_000, dtype=np.float64) + 0.5) / 1_000_000
    draw = device_source_sample(gather, uniform, variant=variant)
    frequency = np.bincount(draw, minlength=3) / draw.size

    assert frequency == pytest.approx(gather.probabilities, abs=2.0e-6)


def test_device_gather_refuses_an_unsupported_higher_specular_suffix() -> None:
    with pytest.raises(NotImplementedError, match="at most one specular suffix"):
        DeviceNextEventGather(
            _sources(np.array([[0.0, 0.0, 2.0]])),
            specular_suffix_order=2,
        )


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_resident_plane_gather_is_repeatable_and_reduces_one_deposit_field(
    tmp_path: Path,
    variant: str,
) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    config = TraceConfig(
        rays=50_000,
        local_cells=128,
        max_bounces=1,
        roulette_start=2,
        batch=19_999,
        seed=73,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )

    def run() -> DeviceNextEventGather:
        gather = DeviceNextEventGather(_sources(np.array([[0.0, 0.0, 3.0]])))
        tracer.trace(np.array([0.0, 0.0, 1.0]), {}, next_event=gather)
        return gather

    first = run()
    second = run()

    assert first.connections > 0
    assert first.cleared == first.connections
    assert first.chi_bounce() > 0.0
    assert np.array_equal(first.bounced_mass(), second.bounced_mass())
    assert np.array_equal(first.chi_by_order(), second.chi_by_order())
    assert first.chi_bounce() == pytest.approx(first.bounced_mass().sum(), abs=0.0)
    assert first.chi_bounce() == pytest.approx(first.chi_by_order().sum(), rel=2.0e-15)
    assert first.as_dict()["direct_atoms"] == "exact_host_calculation_required_separately"
    assert first.as_dict()["specular_suffix_supported"] is True


def test_resident_gather_is_invariant_to_transfer_batch_size(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")

    def run(batch: int) -> DeviceNextEventGather:
        config = TraceConfig(
            rays=31_337,
            local_cells=128,
            max_bounces=1,
            roulette_start=2,
            batch=batch,
            seed=79,
        )
        tracer = DeviceEscapeTracer(
            geometry,
            np.zeros(geometry.face_count, dtype=np.int64),
            np.array([4.2 - 0.15j]),
            np.array([1.0]),
            config,
        )
        gather = DeviceNextEventGather(
            _sources(
                np.array([[-2.0, 0.0, 3.0], [2.0, 0.0, 3.0]]),
                np.array([0.2, 0.8]),
            )
        )
        tracer.trace(np.array([0.0, 0.0, 1.0]), {}, next_event=gather)
        return gather

    whole = run(31_337)
    split = run(7_003)

    assert np.array_equal(whole.bounced_mass(), split.bounced_mass())
    assert np.array_equal(whole.chi_by_order(), split.chi_by_order())
    assert whole.connections == split.connections
    assert whole.cleared == split.cleared


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
@pytest.mark.parametrize("local_cells", [64, 512, 4096])
def test_compact_resident_reduction_matches_rich_host_reduction(
    tmp_path: Path,
    variant: str,
    local_cells: int,
) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    config = TraceConfig(
        rays=4096,
        local_cells=local_cells,
        exit_bands=32,
        max_bounces=1,
        roulette_start=2,
        batch=4096,
        seed=912,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    sources = _sources(np.array([[0.0, 0.0, 3.0], [2.0, 0.0, 4.0]]))
    origin = np.array([0.0, 0.0, 1.0])

    rich_gather = DeviceNextEventGather(sources, max_order=1, collect_field=True)
    rich_gather.begin_trace(config.rays, tracer.local_grid)
    rich = tracer.kernel.trace_escape_records(origin, seed=config.seed, next_event=rich_gather)
    cells = nearest_cell(rich.all_launch_direction, tracer.local_grid)
    rich_gather.consume(rich.next_event, rich.all_launch_direction, launch_cells=cells)
    rich_gather.end_trace()

    compact_gather = DeviceNextEventGather(sources, max_order=1, collect_field=True)
    compact_gather.begin_trace(config.rays, tracer.local_grid)
    compact = tracer.kernel.trace_escape_records(
        origin,
        seed=config.seed,
        next_event=compact_gather,
        compact=True,
    )
    compact_gather.consume_reduced(compact.next_event)
    compact_gather.end_trace()

    assert compact.escaped == rich.escaped
    assert compact.zero_bounce == np.count_nonzero(rich.bounces == 0)
    assert compact.truncated == rich.truncated
    assert compact.roulette_killed == rich.roulette_killed
    expected_exit = np.zeros(config.exit_bands, dtype=np.float64)
    exit_band = np.clip(
        np.searchsorted(tracer.exit_sin_edges, rich.exit_direction[:, 2], side="right") - 1,
        0,
        config.exit_bands - 1,
    )
    np.add.at(expected_exit, exit_band, rich.throughput)
    np.testing.assert_allclose(compact.exit_power, expected_exit, rtol=2.0e-12, atol=1.0e-12)
    excess = rich.path_length - np.einsum(
        "ij,ij->i",
        rich.exit_direction,
        rich.last_vertex - origin,
    )
    assert compact.bounce_sum == pytest.approx(float(rich.bounces.sum()), abs=0.0)
    assert compact.delay_weight == pytest.approx(float(rich.throughput.sum(dtype=np.float64)), rel=2.0e-12)
    assert compact.delay_sum == pytest.approx(float(np.sum(rich.throughput * excess)), rel=2.0e-12)
    assert compact.truncated_throughput == pytest.approx(rich.truncated_throughput, rel=2.0e-12)
    np.testing.assert_allclose(compact_gather.chi_by_order(), rich_gather.chi_by_order(), rtol=2.0e-6)
    np.testing.assert_allclose(
        compact_gather.bounced_mass(),
        rich_gather.bounced_mass(),
        rtol=2.0e-6,
        atol=1.0e-10,
    )
    assert compact_gather.connections == rich_gather.connections
    assert compact_gather.cleared == rich_gather.cleared


def test_distinct_gathers_share_one_immutable_specular_face_binding(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(rays=2_003, local_cells=64, max_bounces=2, roulette_start=3, seed=83)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    proposal = DeviceSpecularFaceProposal.from_geometry(geometry)
    binding = BoundDeviceSpecularFaceProposal.bind(proposal, tracer.kernel)
    sources = _sources(np.array([[0.0, 0.0, 0.0]]))

    def run() -> DeviceNextEventGather:
        gather = DeviceNextEventGather(
            sources,
            max_order=2,
            specular_suffix_order=1,
            specular_face_proposal=binding,
        )
        tracer.trace(np.zeros(3), {}, next_event=gather)
        return gather

    first = run()
    second = run()

    assert first._face_triangles is proposal.triangles
    assert second._face_triangles is proposal.triangles
    assert first._specular_device_arrays is binding.device_arrays
    assert second._specular_device_arrays is binding.device_arrays
    assert not proposal.triangles.flags.writeable
    np.testing.assert_array_equal(first.bounced_mass(), second.bounced_mass())
    np.testing.assert_array_equal(first.specular_bounced_mass(), second.specular_bounced_mass())
    assert first.sampled_specular_diagnostics() == second.sampled_specular_diagnostics()


def test_resident_plane_gather_has_statistical_cpu_parity(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=160_000,
        local_cells=256,
        max_bounces=1,
        roulette_start=2,
        batch=80_000,
        seed=101,
    )
    sites = _sources(
        np.array([[-3.0, 0.0, 4.0], [3.0, 0.0, 4.0]]),
        np.array([0.3, 0.7]),
    )
    face_class = np.zeros(geometry.face_count, dtype=np.int64)
    permittivity = np.array([4.2 - 0.15j])
    roughness = np.array([1.0])
    device = DeviceEscapeTracer(geometry, face_class, permittivity, roughness, config)
    device_gather = DeviceNextEventGather(sites)
    device.trace(np.array([0.0, 0.0, 1.0]), {}, next_event=device_gather)

    cpu = SbrTracer(geometry, face_class, permittivity, roughness, config)
    cpu_gather = NextEventGather(
        geometry,
        sites,
        np.random.default_rng(config.seed + 1000),
        max_order=1,
    )
    cpu.trace(np.array([0.0, 0.0, 1.0]), {}, gather=cpu_gather)

    # The counter-based device stream intentionally differs from NumPy PCG.
    # Both estimates sample the same integral and agree within Monte Carlo error.
    assert device_gather.chi_bounce() == pytest.approx(cpu_gather.chi_bounce(), rel=0.025)
    assert device_gather.connections / config.rays == pytest.approx(
        cpu_gather.connections / config.rays,
        abs=0.01,
    )


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_shadow_visibility_blocks_a_real_sheet_and_passes_a_nonblocking_atlas_sheet(
    tmp_path: Path,
    variant: str,
) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(
        _write_parallel_planes(tmp_path / "sheet.ply", (2.0, 0.0)),
        variant=variant,
    )
    config = TraceConfig(rays=40_000, local_cells=128, max_bounces=1, roulette_start=2, seed=113)
    face_class = np.zeros(geometry.face_count, dtype=np.int64)
    sources = _sources(np.array([[0.0, 0.0, 3.0]]))

    blocking = DeviceEscapeTracer(
        geometry,
        face_class,
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    blocked_gather = DeviceNextEventGather(sources)
    blocking.trace(np.array([0.0, 0.0, 1.0]), {}, next_event=blocked_gather)

    valid = np.array([[True, True], [True, False]])
    nonblocking = np.zeros((geometry.face_count, 2, 2), dtype=bool)
    nonblocking[:2] = valid
    binding = AtlasMaterialBinding(
        face_to_atlas_row=np.arange(geometry.face_count, dtype=np.int32),
        material_probability=np.zeros((geometry.face_count, 2, 2, 1), dtype=np.float32),
        supported=np.zeros((geometry.face_count, 2, 2), dtype=bool),
        valid_texels=valid,
        material_names=("material",),
        material_class=np.array([0], dtype=np.int32),
        provenance={"rule": "upper sheet is non-blocking"},
        nonblocking=nonblocking,
    )
    pass_through = DeviceEscapeTracer(
        geometry,
        face_class,
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
        atlas_material=binding,
    )
    clear_gather = DeviceNextEventGather(sources)
    pass_through.trace(np.array([0.0, 0.0, 1.0]), {}, next_event=clear_gather)

    assert blocked_gather.connections > 0
    assert blocked_gather.cleared == 0
    assert blocked_gather.chi_bounce() == 0.0
    assert clear_gather.connections > 0
    assert clear_gather.cleared == clear_gather.connections
    assert clear_gather.chi_bounce() > 0.0


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_low_level_kernel_returns_aligned_order_rows(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant=variant)
    config = TraceConfig(rays=4096, max_bounces=1, roulette_start=2, seed=91)
    kernel = DeviceSbrKernel(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    gather = DeviceNextEventGather(_sources(np.array([[0.0, 0.0, 3.0]])))

    records = kernel.trace_escape_records(np.array([0.0, 0.0, 1.0]), next_event=gather)

    assert records.next_event is not None
    assert records.next_event.weight_by_order.shape == (2, config.rays)
    assert np.count_nonzero(records.next_event.weight_by_order[0]) == 0
    assert records.next_event.connections_by_order[0] == 0
    assert records.next_event.connections_by_order[1] > 0


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_resident_gather_records_all_three_bounce_orders(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant=variant)
    config = TraceConfig(rays=20_000, local_cells=128, max_bounces=3, roulette_start=4, seed=127)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    gather = DeviceNextEventGather(_sources(np.array([[0.0, 0.0, 5.0]])))

    tracer.trace(np.zeros(3), {}, next_event=gather)

    assert gather.chi_by_order().shape == (4,)
    assert gather.chi_by_order()[0] == 0.0
    assert np.all(gather.chi_by_order()[1:] > 0.0)
    assert np.array_equal(gather._connections_by_order[1:], np.full(3, config.rays, dtype=np.uint64))
    assert np.array_equal(gather._cleared_by_order[1:], np.full(3, config.rays, dtype=np.uint64))


def test_max_order_collapses_later_device_bounces_without_losing_mass(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(rays=4096, local_cells=128, max_bounces=3, roulette_start=4, seed=131)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    sources = _sources(np.array([[0.0, 0.0, 5.0]]))
    full = DeviceNextEventGather(sources, max_order=3)
    collapsed = DeviceNextEventGather(sources, max_order=1)

    tracer.trace(np.zeros(3), {}, next_event=full)
    tracer.trace(np.zeros(3), {}, next_event=collapsed)

    assert collapsed.chi_by_order().shape == (2,)
    assert collapsed.chi_by_order()[0] == 0.0
    assert collapsed.chi_by_order()[1] == pytest.approx(full.chi_by_order()[1:].sum(), rel=2.0e-15)
    assert collapsed.chi_bounce() == pytest.approx(full.chi_bounce(), rel=2.0e-15)
    assert collapsed.connections == full.connections
    assert collapsed.cleared == full.cleared


def test_first_material_interaction_device_gather_keeps_only_depth_zero_and_is_batch_invariant(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    sources = _sources(np.array([[0.0, 0.0, 5.0]]))

    def trace(batch: int, *, first_only: bool) -> DeviceNextEventGather:
        config = TraceConfig(
            rays=4096,
            local_cells=128,
            max_bounces=3,
            roulette_start=4,
            batch=batch,
            seed=137,
        )
        tracer = DeviceEscapeTracer(
            geometry,
            np.zeros(geometry.face_count, dtype=np.int64),
            np.array([4.2 - 0.15j]),
            np.array([1.0]),
            config,
        )
        gather = DeviceNextEventGather(
            sources,
            max_order=1 if first_only else 3,
            first_material_interaction_only=first_only,
        )
        tracer.trace(np.zeros(3), {}, next_event=gather)
        return gather

    all_depths = trace(4096, first_only=False)
    first_whole = trace(4096, first_only=True)
    first_split = trace(1003, first_only=True)

    assert first_whole.chi_by_order().shape == (2,)
    assert first_whole.chi_by_order()[0] == 0.0
    assert first_whole.chi_by_order()[1] > 0.0
    assert first_whole.chi_by_order()[1] == pytest.approx(all_depths.chi_by_order()[1], rel=2.0e-15)
    assert first_whole.connections < all_depths.connections
    assert first_whole.cleared < all_depths.cleared
    assert np.array_equal(first_whole.chi_by_order(), first_split.chi_by_order())
    assert first_whole.connections == first_split.connections
    assert first_whole.cleared == first_split.cleared


def test_production_estimator_keeps_direct_atoms_exact_and_device_diffuse_consistent(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=20_000,
        local_cells=128,
        max_bounces=1,
        roulette_start=2,
        batch=8192,
        seed=137,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    sources = _source_set(np.array([[0.0, 0.0, 3.0]]))
    estimator = NextEventEstimator(
        tracer,
        geometry,
        sources,
        samples=1,
        max_order=1,
        specular_order=0,
    )

    result, field = estimator.estimate_field(np.array([0.0, 0.0, 1.0]), seed=137)

    assert result.direct == pytest.approx(0.25, rel=1.0e-12)
    assert field.direct_atom_mass == pytest.approx([0.25], rel=1.0e-12)
    np.testing.assert_allclose(field.direct_k_hat, [[0.0, 0.0, -1.0]], atol=1.0e-12)
    assert field.direct_mass.sum() == pytest.approx(result.direct, rel=1.0e-12)
    assert field.bounced == pytest.approx(result.detail["bounced"], rel=2.0e-15)
    assert field.total == pytest.approx(result.total, rel=2.0e-15)
    assert field.includes_specular is False
    assert field.missing_specular is True
    assert field.maximum_completed_all_specular_order == 0
    assert field.maximum_completed_specular_suffix_order == 0
    assert result.detail["transport_kernel"] == "drjit_resident_next_event"
    assert result.detail["all_specular_order_1_included"] is False
    assert result.detail["all_specular_order_1_missing"] is True
    assert result.detail["mixed_specular_suffix_order_1_included"] is False
    assert result.detail["mixed_specular_suffix_order_1_missing"] is True
    assert result.detail["direct_evaluation"] == "exact_host_source_visibility_and_atoms"
    assert result.detail["device_next_event"]["field_collected"] is True

    scalar = estimator.estimate(np.array([0.0, 0.0, 1.0]), seed=137)
    assert scalar.total == pytest.approx(result.total, rel=2.0e-15)
    assert scalar.detail["by_order"] == pytest.approx(result.detail["by_order"], rel=2.0e-15)
    assert scalar.detail["device_next_event"]["field_collected"] is False


def test_production_estimator_preserves_weighted_direct_atoms_exactly(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(rays=1024, local_cells=64, max_bounces=1, roulette_start=2, seed=138)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )
    sources = _source_set(
        np.array([[0.0, 0.0, 3.0], [3.0, 0.0, 4.0]]),
        np.array([0.25, 0.75]),
    )
    estimator = NextEventEstimator(tracer, geometry, sources, max_order=1, specular_order=0)

    result, field = estimator.estimate_field(np.array([0.0, 0.0, 1.0]), seed=138)

    expected_mass = np.array([0.25 / 4.0, 0.75 / 18.0])
    expected_directions = np.array(
        [
            [0.0, 0.0, -1.0],
            [-3.0 / np.sqrt(18.0), 0.0, -3.0 / np.sqrt(18.0)],
        ]
    )
    assert result.direct == pytest.approx(float(expected_mass.sum()), rel=1.0e-12)
    np.testing.assert_allclose(field.direct_atom_mass, expected_mass, rtol=1.0e-12, atol=1.0e-15)
    np.testing.assert_allclose(field.direct_k_hat, expected_directions, rtol=1.0e-12, atol=1.0e-12)
    assert field.direct_atoms == pytest.approx(result.direct, rel=1.0e-12)
    assert field.direct_mass.sum() == pytest.approx(result.direct, rel=1.0e-12)


def test_production_estimator_refuses_implicit_specular_omission(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(rays=16, local_cells=16, max_bounces=1, seed=139)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0]),
        config,
    )

    with pytest.raises(NotImplementedError, match="specular_suffix_mode='sampled'"):
        NextEventEstimator(
            tracer,
            geometry,
            _source_set(np.array([[0.0, 0.0, 3.0]])),
        )


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_shadow_ray_is_reaimed_from_a_large_sloped_normal_lift(variant: str) -> None:
    _set_variant(variant)
    import drjit as dr
    import mitsuba as mi

    class DiskBlocker:
        def __init__(self) -> None:
            self.variant = variant

        @staticmethod
        def intersect_device(origin, direction, active):  # noqa: ANN001, ANN205
            distance = (5.0 - origin.z) / direction.z
            crossing_x = origin.x + distance * direction.x
            hit = active & (distance > 0.0) & (dr.abs(crossing_x - 5.0 / 7.0) < 0.1)
            return DeviceIntersection(
                hit,
                dr.select(hit, distance, 1.0e30),
                mi.Vector3f(0.0, 0.0, -1.0),
                dr.zeros(mi.UInt32, dr.width(active)),
                mi.Point2f(0.0),
            )

    kernel = SimpleNamespace(
        mi=mi,
        dr=dr,
        geometry=DiskBlocker(),
        face_class=np.zeros(1, dtype=np.uint32),
        _surface_nonblocking=lambda intersection, active: dr.zeros(mi.Bool, dr.width(active)),
    )
    gather = DeviceNextEventGather(
        _sources(np.array([[0.0, 0.0, 10.0]])),
        lift_m=2.0,
        min_connect_m=0.0,
    )
    ray_index = dr.arange(mi.UInt32, 1)
    state = gather._device_state(kernel, ray_index, 1, 17)
    normal = dr.normalize(mi.Vector3f(0.6, 0.0, 0.8))

    state.vertex(
        0,
        mi.Point3f(0.0),
        normal,
        mi.Float(1.0),
        mi.Float(0.0),
        mi.Bool(True),
        lambda sample: mi.Float(0.25 + 0.0 * sample),
    )
    batch = state.transfer(0)

    # The lifted start is (1.2, 0, 1.6). Re-aiming from there crosses z=5 at
    # x=5/7 and hits the disk. Reusing the unlifted vertical direction would
    # cross at x=1.2 and incorrectly mark the connection clear.
    assert batch.connections_by_order[1] == 1
    assert batch.cleared_by_order[1] == 0
    assert batch.weight_by_order[1, 0] == 0.0
