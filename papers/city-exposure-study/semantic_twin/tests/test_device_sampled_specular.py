from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from semantic_twin.materials.atlas_binding import AtlasMaterialBinding
from semantic_twin.exposure.roofline_campaign import _sampled_suffix_accepted
from semantic_twin.illumination.curve import FacadeTipCurve
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.device_kernel import DeviceSbrKernel
from semantic_twin.transport.device_next_event import (
    BoundDeviceSpecularFaceProposal,
    DeviceNextEventGather,
    device_specular_face_sample,
)
from semantic_twin.transport.device_tracer import DeviceEscapeTracer
from semantic_twin.transport.next_event import NextEventEstimator
from semantic_twin.transport.specular import (
    OneBounceSpecularTransport,
    ReceiverVisibleFaceCandidates,
    StratifiedSourceQuadrature,
    SpecularSurfaces,
)
from semantic_twin.transport.specular_sampling import SampledOneBounceSpecularEstimator
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


class Sources:
    def __init__(self, positions: np.ndarray, weights: np.ndarray | None = None) -> None:
        self.positions = np.asarray(positions, dtype=np.float64)
        self.source_weights = weights

    def sites(self) -> np.ndarray:
        return self.positions


def _set_variant(variant: str) -> None:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant(variant)
    except ImportError as error:
        pytest.skip(str(error))


def _write_triangles(path: Path, triangles: np.ndarray) -> Path:
    triangle = np.asarray(triangles, dtype=np.float64)
    vertices = triangle.reshape(-1, 3)
    rows = [
        "ply",
        "format ascii 1.0",
        f"element vertex {vertices.shape[0]}",
        "property float x",
        "property float y",
        "property float z",
        f"element face {triangle.shape[0]}",
        "property list uchar int vertex_indices",
        "end_header",
    ]
    rows.extend(" ".join(format(float(value), ".17g") for value in vertex) for vertex in vertices)
    rows.extend(f"3 {start} {start + 1} {start + 2}" for start in range(0, vertices.shape[0], 3))
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


def _reflector() -> np.ndarray:
    return np.array([[[-10.0, -10.0, 0.0], [10.0, -10.0, 0.0], [0.0, 10.0, 0.0]]])


def _kernel(
    geometry: MitsubaGeometry,
    config: TraceConfig,
    *,
    permittivity: np.ndarray | None = None,
    roughness: np.ndarray | None = None,
    atlas: AtlasMaterialBinding | None = None,
) -> DeviceSbrKernel:
    return DeviceSbrKernel(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([PEC_PERMITTIVITY]) if permittivity is None else permittivity,
        np.array([0.0]) if roughness is None else roughness,
        config,
        atlas_material=atlas,
    )


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_full_support_face_alias_represents_the_declared_area_mixture(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    triangles = np.array(
        [
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            [[10.0, 0.0, 0.0], [16.0, 0.0, 0.0], [10.0, 1.0, 0.0]],
        ]
    )
    geometry = MitsubaGeometry(_write_triangles(tmp_path / "area.ply", triangles), variant=variant)
    config = TraceConfig(rays=8, batch=8, local_cells=16, max_bounces=2)
    kernel = _kernel(geometry, config)
    gather = DeviceNextEventGather(Sources([[0.0, 0.0, 5.0]]), specular_suffix_order=1)
    uniform = (np.arange(1_000_000, dtype=np.float64) + 0.5) / 1_000_000

    draw = device_specular_face_sample(gather, kernel, uniform)
    frequency = np.bincount(draw, minlength=2) / draw.size

    expected = np.array([0.9 * 0.25 + 0.05, 0.9 * 0.75 + 0.05])
    np.testing.assert_allclose(gather.face_probabilities, expected, rtol=0.0, atol=2.0e-16)
    np.testing.assert_allclose(frequency, expected, rtol=0.0, atol=2.0e-6)
    assert np.all(gather.face_probabilities > 0.0)
    assert gather.face_probabilities.sum() == pytest.approx(1.0, rel=1.0e-15)


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_one_face_resident_image_solve_matches_the_cpu_oracle(tmp_path: Path, variant: str) -> None:
    _set_variant(variant)
    geometry = MitsubaGeometry(_write_triangles(tmp_path / "reflector.ply", _reflector()), variant=variant)
    config = TraceConfig(rays=1, batch=1, local_cells=8, max_bounces=2, seed=17)
    kernel = _kernel(geometry, config)
    sources = Sources([[4.0, 0.0, 4.0]])
    gather = DeviceNextEventGather(
        sources,
        max_order=2,
        epsilon_m=config.ray_epsilon_m,
        specular_suffix_order=1,
        sampled_specular_samples=4,
    )

    import drjit as dr
    import mitsuba as mi

    state = gather._device_state(kernel, dr.arange(mi.UInt32, 1), 1, config.seed)
    normal = dr.normalize(mi.Vector3f(1.0, 0.0, -1.0))
    state.vertex(
        0,
        mi.Point3f(-4.0, 0.0, 4.0),
        normal,
        mi.Float(1.0),
        mi.Float(0.0),
        mi.Bool(True),
        lambda sample: mi.Float(0.25 + 0.0 * sample),
    )
    batch = state.transfer(0)

    cpu = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        config,
    )
    oracle = SampledOneBounceSpecularEstimator(OneBounceSpecularTransport(cpu), sources).estimate_suffix(
        np.array([[-4.0, 0.0, 4.0]]),
        np.array([[1.0, 0.0, -1.0]]) / math.sqrt(2.0),
        np.array([1.0 / np.pi]),
        np.array([[0.0, -1.0, 0.0]]),
        np.array([1]),
        samples_per_vertex=4,
        seed=config.seed + gather.sampled_specular_seed_offset,
    )

    measured = float(batch.specular_weight_by_order[2, 0]) / gather.sampled_specular_samples
    assert measured == pytest.approx(oracle.transfer, rel=2.0e-5)
    assert measured == pytest.approx(1.0 / (128.0 * np.pi), rel=2.0e-5)
    assert batch.specular_candidates_by_order[2] == 4
    assert batch.specular_geometric_by_order[2] == 4
    assert batch.specular_visible_by_order[2] == 4
    assert batch.specular_accepted_by_order[2] == 4


def test_sampled_specular_is_batch_invariant_and_uses_original_launch_bins(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    sources = Sources([[0.0, 0.0, 0.0]])

    def run(batch: int) -> DeviceNextEventGather:
        config = TraceConfig(
            rays=12_007,
            batch=batch,
            local_cells=128,
            max_bounces=3,
            roulette_start=4,
            seed=23,
        )
        tracer = DeviceEscapeTracer(
            geometry,
            np.zeros(geometry.face_count, dtype=np.int64),
            np.array([4.2 - 0.15j]),
            np.array([1.0e-3]),
            config,
        )
        gather = DeviceNextEventGather(
            sources,
            max_order=3,
            specular_suffix_order=1,
            sampled_specular_samples=2,
        )
        tracer.trace(np.zeros(3), {}, next_event=gather)
        return gather

    whole = run(12_007)
    split = run(3_001)

    np.testing.assert_array_equal(whole.specular_bounced_mass(), split.specular_bounced_mass())
    np.testing.assert_allclose(
        whole.chi_specular_suffix_by_order(),
        split.chi_specular_suffix_by_order(),
        rtol=2.0e-15,
        atol=0.0,
    )
    assert whole.specular_candidates == split.specular_candidates == 4 * 12_007
    assert whole.specular_accepted == split.specular_accepted
    assert whole.chi_specular_suffix() > 0.0
    assert np.count_nonzero(whole.specular_bounced_mass()) > 1
    assert _sampled_suffix_accepted(whole.sampled_specular_diagnostics())


def test_sampled_specular_seed_is_repeatable_but_not_constant(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    sources = Sources([[0.0, 0.0, 0.0]])

    def run(seed: int) -> DeviceNextEventGather:
        config = TraceConfig(
            rays=4_096,
            batch=1_337,
            local_cells=64,
            max_bounces=3,
            roulette_start=4,
            seed=seed,
        )
        tracer = DeviceEscapeTracer(
            geometry,
            np.zeros(geometry.face_count, dtype=np.int64),
            np.array([4.2 - 0.15j]),
            np.array([1.0e-3]),
            config,
        )
        gather = DeviceNextEventGather(
            sources,
            max_order=3,
            specular_suffix_order=1,
            sampled_specular_samples=2,
        )
        tracer.trace(np.zeros(3), {}, next_event=gather)
        return gather

    first = run(47)
    repeated = run(47)
    changed = run(48)

    np.testing.assert_array_equal(first.specular_bounced_mass(), repeated.specular_bounced_mass())
    np.testing.assert_array_equal(first.chi_specular_suffix_by_order(), repeated.chi_specular_suffix_by_order())
    assert not np.array_equal(first.specular_bounced_mass(), changed.specular_bounced_mass())


def test_resident_atlas_reflection_response_matches_the_cpu_oracle(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_triangles(tmp_path / "reflector.ply", _reflector()), variant="llvm_ad_rgb")
    valid = np.array([[True, True], [True, False]])
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, valid] = np.array([0.25, 0.75], dtype=np.float32)
    atlas = AtlasMaterialBinding(
        face_to_atlas_row=np.array([0], dtype=np.int32),
        material_probability=probability,
        supported=valid[None, ...],
        valid_texels=valid,
        material_names=("smooth", "rough"),
        material_class=np.array([1, 2], dtype=np.int32),
        provenance={"fixture": True},
    )
    permittivity = np.array([PEC_PERMITTIVITY, 4.0 - 0.2j, 9.0 - 0.4j])
    roughness = np.array([0.0, 0.0, 3.0e-4])
    config = TraceConfig(rays=1, batch=1, local_cells=8, max_bounces=2, seed=29)
    kernel = _kernel(geometry, config, permittivity=permittivity, roughness=roughness, atlas=atlas)
    sources = Sources([[4.0, 0.0, 4.0]])
    gather = DeviceNextEventGather(
        sources,
        max_order=2,
        epsilon_m=config.ray_epsilon_m,
        specular_suffix_order=1,
    )

    import drjit as dr
    import mitsuba as mi

    state = gather._device_state(kernel, dr.arange(mi.UInt32, 1), 1, config.seed)
    state.vertex(
        0,
        mi.Point3f(-4.0, 0.0, 4.0),
        dr.normalize(mi.Vector3f(1.0, 0.0, -1.0)),
        mi.Float(1.0),
        mi.Float(0.0),
        mi.Bool(True),
        lambda sample: mi.Float(0.25 + 0.0 * sample),
    )
    batch = state.transfer(0)

    cpu = SbrTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        permittivity,
        roughness,
        config,
        atlas_material=atlas,
    )
    oracle = SampledOneBounceSpecularEstimator(OneBounceSpecularTransport(cpu), sources).estimate_suffix(
        np.array([[-4.0, 0.0, 4.0]]),
        np.array([[1.0, 0.0, -1.0]]) / math.sqrt(2.0),
        np.array([1.0 / np.pi]),
        np.array([[0.0, -1.0, 0.0]]),
        np.array([1]),
        samples_per_vertex=1,
        seed=config.seed + gather.sampled_specular_seed_offset,
    )

    assert batch.specular_weight_by_order[2, 0] == pytest.approx(oracle.transfer, rel=3.0e-5)
    assert batch.specular_accepted_by_order[2] == 1


@pytest.mark.parametrize("variant", ["llvm_ad_rgb", "cuda_ad_rgb"])
def test_sampled_specular_visibility_passes_nonblocking_atlas_on_both_legs(
    tmp_path: Path,
    variant: str,
) -> None:
    _set_variant(variant)
    import drjit as dr
    import mitsuba as mi

    geometry = MitsubaGeometry(_write_parallel_planes(tmp_path / "sheets.ply", (2.0, 0.0)), variant=variant)
    valid = np.array([[True, True], [True, False]])
    probability = np.zeros((geometry.face_count, 2, 2, 1), dtype=np.float32)
    supported = np.zeros((geometry.face_count, 2, 2), dtype=bool)
    nonblocking = np.zeros_like(supported)
    nonblocking[:2] = valid
    binding = AtlasMaterialBinding(
        face_to_atlas_row=np.arange(geometry.face_count, dtype=np.int32),
        material_probability=probability,
        supported=supported,
        valid_texels=valid,
        material_names=("material",),
        material_class=np.array([0], dtype=np.int32),
        provenance={"fixture": "upper sheet is a nonblocking atlas cell"},
        nonblocking=nonblocking,
    )
    blocking_binding = AtlasMaterialBinding(
        face_to_atlas_row=np.arange(geometry.face_count, dtype=np.int32),
        material_probability=probability,
        supported=supported,
        valid_texels=valid,
        material_names=("material",),
        material_class=np.array([0], dtype=np.int32),
        provenance={"fixture": "upper sheet is a blocking atlas cell"},
    )
    config = TraceConfig(rays=4_096, batch=4_096, local_cells=16, max_bounces=2, seed=5)
    source = Sources([[0.0, 0.0, 3.0]])
    ray_index = dr.arange(mi.UInt32, config.rays)
    unit = mi.Float(1.0) + mi.Float(0.0) * mi.Float(ray_index)
    zero = mi.Float(0.0) * mi.Float(ray_index)
    active = ray_index >= 0

    def run(atlas: AtlasMaterialBinding):
        kernel = _kernel(
            geometry,
            config,
            permittivity=np.array([4.2 - 0.15j]),
            roughness=np.array([1.0]),
            atlas=atlas,
        )
        gather = DeviceNextEventGather(
            source,
            max_order=2,
            specular_suffix_order=1,
            sampled_specular_samples=1,
        )
        state = gather._device_state(kernel, ray_index, config.rays, config.seed)
        # Both endpoint legs for the lower reflector cross the upper sheet.
        # The upper sheet itself is rejected when sampled as the reflector.
        state.vertex(
            0,
            mi.Point3f(zero, zero, unit),
            mi.Vector3f(zero, zero, -unit),
            unit,
            zero,
            active,
            lambda sample: zero + 0.25,
        )
        return state.transfer(0)

    blocked = run(blocking_binding)
    clear = run(binding)

    assert blocked.specular_candidates_by_order[2] == clear.specular_candidates_by_order[2] == config.rays
    assert blocked.specular_geometric_by_order[2] == clear.specular_geometric_by_order[2] > 0
    assert blocked.specular_visible_by_order[2] == 0
    assert blocked.specular_accepted_by_order[2] == 0
    assert clear.specular_visible_by_order[2] > 0
    assert clear.specular_accepted_by_order[2] == clear.specular_visible_by_order[2]


def test_production_estimator_composes_device_sampled_suffix_and_exact_atoms(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=20_003,
        batch=5_001,
        local_cells=128,
        max_bounces=3,
        roulette_start=4,
        seed=31,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    sources = SourceSet(
        positions=np.array([[1.0, 0.0, 0.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )
    estimator = NextEventEstimator(
        tracer,
        geometry,
        sources,
        max_order=3,
        specular_order=1,
        specular_suffix_mode="sampled",
        sampled_specular_samples=2,
    )

    result, field = estimator.estimate_field(np.zeros(3), seed=31)

    assert result.detail["transport_kernel"] == "drjit_resident_next_event"
    assert result.detail["sampled_specular_suffix_full_support"] is True
    assert result.detail["sampled_specular_suffix"]["trials"] >= 3 * config.rays
    assert result.detail["mixed_specular_suffix_order_1"] > 0.0
    assert result.detail["all_specular_order_1_included"] is True
    assert field.includes_specular is True
    assert field.sampled_specular_suffix_full_support is True
    assert field.mixed_specular_mass == pytest.approx(result.detail["mixed_specular_suffix_order_1"], rel=2e-15)
    assert field.all_specular_mass == pytest.approx(result.detail["all_specular_order_1"], rel=2e-15)
    assert field.total == pytest.approx(result.total, rel=2e-15)
    assert np.sum(result.detail["by_order"], dtype=np.float64) == pytest.approx(result.detail["bounced"], rel=2e-15)
    assert result.direct + result.detail["bounced"] == pytest.approx(result.total, rel=2e-15)
    assert field.direct_atoms == pytest.approx(result.direct, rel=2e-15)
    assert field.specular == pytest.approx(field.all_specular_mass + field.mixed_specular_mass, rel=2e-15)
    assert field.bounced == pytest.approx(result.detail["bounced"], rel=2e-15)
    assert field.directional_measure(result.total).total == pytest.approx(1.0, rel=2e-15)


def test_production_estimator_binds_face_proposal_once_and_reuses_exact_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=4_097,
        batch=2_003,
        local_cells=64,
        max_bounces=3,
        roulette_start=4,
        seed=37,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    original = BoundDeviceSpecularFaceProposal.bind.__func__
    calls: list[int] = []

    def counted_bind(cls, proposal, kernel):  # noqa: ANN001, ANN202
        calls.append(id(proposal))
        return original(cls, proposal, kernel)

    monkeypatch.setattr(BoundDeviceSpecularFaceProposal, "bind", classmethod(counted_bind))
    estimator = NextEventEstimator(
        tracer,
        geometry,
        SourceSet(
            positions=np.array([[1.0, 0.0, 0.0]]),
            cell_m=1.0,
            dims=3,
            azimuths=0,
            builders=0,
        ),
        max_order=3,
        specular_order=1,
        specular_suffix_mode="sampled",
    )

    first_result, first_field = estimator.estimate_field(np.zeros(3), seed=37)
    second_result, second_field = estimator.estimate_field(np.zeros(3), seed=37)

    assert len(calls) == 1
    assert estimator._device_specular_face_proposal is not None
    assert first_result.total == second_result.total
    np.testing.assert_array_equal(first_field.bounced_mass, second_field.bounced_mass)
    np.testing.assert_array_equal(first_field.specular_atom_mass, second_field.specular_atom_mass)
    np.testing.assert_array_equal(first_field.specular_k_hat, second_field.specular_k_hat)


def test_sampled_device_suffix_does_not_inherit_incomplete_specular_transport_support(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=2_003,
        batch=2_003,
        local_cells=64,
        max_bounces=2,
        roulette_start=3,
        seed=43,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    complete = OneBounceSpecularTransport(tracer).surfaces
    incomplete = SpecularSurfaces(
        complete.triangles[:1],
        complete.normals[:1],
        complete.face_index[:1],
        complete.material_class[:1],
        support_complete=False,
        scene_face_count=complete.scene_face_count,
    )
    estimator = NextEventEstimator(
        tracer,
        geometry,
        SourceSet(
            positions=np.array([[0.0, 0.0, 0.0]]),
            cell_m=1.0,
            dims=3,
            azimuths=0,
            builders=0,
        ),
        max_order=2,
        specular_order=1,
        specular_transport=OneBounceSpecularTransport(tracer, incomplete),
        specular_suffix_mode="sampled",
    )

    result, _field = estimator.estimate_field(np.zeros(3), seed=43)
    identity = result.detail["sampled_specular_suffix"]["sampling_identity"]

    assert identity["face_count"] == geometry.face_count
    assert identity["surface_scene_face_count"] == geometry.face_count
    assert identity["surface_support_complete"] is True


def test_production_estimator_composes_device_sampled_suffix_with_adaptive_all_specular(
    tmp_path: Path,
) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_cube(tmp_path / "cube.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(
        rays=4_096,
        batch=1_003,
        local_cells=64,
        max_bounces=3,
        roulette_start=4,
        seed=7,
    )
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    points = np.column_stack(
        (
            np.linspace(-3.5, 3.5, 32),
            np.zeros(32),
            np.full(32, 20.0),
        )
    )
    sources = SourceSet.from_curve(FacadeTipCurve(points, np.ones(32), {"fixture": True}))
    estimator = NextEventEstimator(
        tracer,
        geometry,
        sources,
        max_order=3,
        specular_order=1,
        specular_suffix_mode="sampled",
        sampled_specular_samples=1,
        specular_candidate_budget=100,
        visible_face_candidates=ReceiverVisibleFaceCandidates((3,)),
        source_quadrature=StratifiedSourceQuadrature((1,)),
        specular_refinement_relative_tolerance=0.1,
    )

    result, field = estimator.estimate_field(np.zeros(3), seed=7)
    work = result.detail["finite_resolution_specular_work"]

    assert field.specular_estimate_kind == "adaptive_all_sampled_mixed_order_1"
    assert field.finite_resolution_specular_estimate is True
    assert work["enabled"] is True
    assert work["method"] == "adaptive_receiver_faces_and_probability_strata"
    assert work["support_complete"] is False
    assert result.detail["all_specular_order_1_included"] is True
    assert result.detail["all_specular_order_1"] > 0.0
    assert result.detail["mixed_specular_suffix_order_1"] > 0.0
    assert result.detail["sampled_specular_suffix_full_support"] is True
    assert result.detail["sampled_specular_suffix"]["accepted"] > 0
    identity = result.detail["sampled_specular_suffix"]["sampling_identity"]
    assert identity["face_proposal"] == "0.9_triangle_area_plus_0.1_uniform_full_support_v1"
    assert identity["source_proposal"] == "existing_normalized_discrete_source_weights_v1"
    assert identity["counter_generator"] == "splitmix64_seed_counter_dimension_v1"
    assert identity["source_support"] == identity["source_count"]
    assert identity["surface_support_complete"] is True
    assert result.detail["direct_evaluation"] == "exact_host_source_visibility_and_atoms"
    assert field.direct_atoms == pytest.approx(result.direct, rel=2e-15)
    assert field.total == pytest.approx(result.total, rel=2e-15)


def test_device_estimator_refuses_exact_order_one_and_higher_orders(tmp_path: Path) -> None:
    _set_variant("llvm_ad_rgb")
    geometry = MitsubaGeometry(_write_triangles(tmp_path / "reflector.ply", _reflector()), variant="llvm_ad_rgb")
    config = TraceConfig(rays=16, batch=16, local_cells=8, max_bounces=2, seed=41)
    tracer = DeviceEscapeTracer(
        geometry,
        np.zeros(geometry.face_count, dtype=np.int64),
        np.array([4.2 - 0.15j]),
        np.array([1.0e-3]),
        config,
    )
    sources = SourceSet(
        positions=np.array([[4.0, 0.0, 4.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )

    with pytest.raises(NotImplementedError, match="specular_suffix_mode='sampled'"):
        NextEventEstimator(
            tracer,
            geometry,
            sources,
            specular_order=1,
            specular_suffix_mode="exact",
        )
    with pytest.raises(ValueError, match="maximum completed specular order is one"):
        NextEventEstimator(
            tracer,
            geometry,
            sources,
            specular_order=2,
            specular_suffix_mode="sampled",
        )
