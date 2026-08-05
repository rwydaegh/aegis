from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin import paths
from semantic_twin.exposure.execution import PreparedScene, _bind_materials
from semantic_twin.materials import AtlasMaterialBinding, bind_surface_atlas
from semantic_twin.materials.atlas import FALLBACK_BOUND, FALLBACK_HOST_CONFLICT, JointSemanticMaterialAtlas
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.device_kernel import DeviceSbrKernel
from semantic_twin.transport.tracer import SbrTracer, TraceConfig, fresnel_power_reflectance, specular_share


def atlas_binding(
    probability: np.ndarray,
    *,
    face_to_row: np.ndarray | None = None,
    supported: np.ndarray | None = None,
    material_class: np.ndarray | None = None,
) -> AtlasMaterialBinding:
    probability = np.asarray(probability, dtype=np.float32)
    rows, height, width, materials = probability.shape
    valid = np.fromfunction(lambda row, column: row / (height - 1) + column / (width - 1) <= 1.0, (height, width))
    if supported is None:
        supported = (probability.sum(axis=-1) > 0.0) & valid[None, ...]
    return AtlasMaterialBinding(
        face_to_atlas_row=np.asarray([0, -1] if face_to_row is None else face_to_row, dtype=np.int32),
        material_probability=probability,
        supported=np.asarray(supported, dtype=bool),
        valid_texels=valid,
        material_names=tuple(f"material_{index}" for index in range(materials)),
        material_class=np.asarray(
            np.arange(1, materials + 1) if material_class is None else material_class,
            dtype=np.int32,
        ),
        provenance={"rule": "test"},
    )


class Geometry:
    face_count = 2

    def barycentric_uv(self, _face: np.ndarray, position: np.ndarray) -> np.ndarray:
        return np.asarray(position[:, :2], dtype=np.float64)


def tracer(binding: AtlasMaterialBinding) -> SbrTracer:
    return SbrTracer(
        Geometry(),
        np.array([0, 0]),
        np.array([2.5 - 0.05j, 4.2 - 0.15j, 7.0 - 0.4j]),
        np.array([0.001, 0.0, 0.006]),
        TraceConfig(rays=1),
        atlas_material=binding,
    )


def test_face_and_barycentric_coordinates_select_one_common_atlas_texel() -> None:
    probability = np.zeros((1, 3, 3, 2), dtype=np.float32)
    probability[0, 0, 0] = (1.0, 0.0)
    probability[0, 0, 2] = (0.0, 1.0)
    binding = atlas_binding(probability)

    posterior, supported, nonblocking = binding.lookup(
        np.array([0, 0, 1]),
        np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]]),
    )

    np.testing.assert_array_equal(supported, [True, True, False])
    np.testing.assert_array_equal(nonblocking, [False, False, False])
    np.testing.assert_array_equal(posterior, [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])


def test_one_hot_atlas_response_equals_the_named_half_space() -> None:
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (1.0, 0.0)
    instance = tracer(atlas_binding(probability))
    cosine = np.array([0.37])

    reflectance, share, nonblocking = instance._surface_response(
        cosine,
        np.array([0]),
        np.array([0]),
        np.array([[0.0, 0.0, 0.0]]),
    )

    np.testing.assert_allclose(reflectance, fresnel_power_reflectance(cosine, instance.permittivity[[1]]))
    np.testing.assert_allclose(share, specular_share(instance.rms_height_m[[1]], cosine, instance.wavelength_m))
    assert not nonblocking.any()


def test_atlas_mixture_is_convex_in_reflected_power_and_reflectance_weighted_share() -> None:
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (0.25, 0.75)
    instance = tracer(atlas_binding(probability))
    cosine = np.array([0.62])
    component_r = fresnel_power_reflectance(cosine[:, None], instance.permittivity[[1, 2]][None, :])
    component_s = specular_share(instance.rms_height_m[[1, 2]][None, :], cosine[:, None], instance.wavelength_m)

    reflectance, share, nonblocking = instance._surface_response(
        cosine,
        np.array([0]),
        np.array([0]),
        np.array([[0.0, 0.0, 0.0]]),
    )

    expected_r = 0.25 * component_r[:, 0] + 0.75 * component_r[:, 1]
    expected_s = (
        0.25 * component_r[:, 0] * component_s[:, 0] + 0.75 * component_r[:, 1] * component_s[:, 1]
    ) / expected_r
    np.testing.assert_allclose(reflectance, expected_r)
    np.testing.assert_allclose(share, expected_s)
    assert component_r.min() <= reflectance[0] <= component_r.max()
    assert not nonblocking.any()


def test_unsupported_face_and_texel_use_the_geometric_face_material() -> None:
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (1.0, 0.0)
    instance = tracer(atlas_binding(probability))
    cosine = np.array([0.4, 0.8])
    fallback = np.array([0, 0])

    reflectance, share, nonblocking = instance._surface_response(
        cosine,
        fallback,
        np.array([0, 1]),
        np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
    )

    expected_r = fresnel_power_reflectance(cosine, instance.permittivity[fallback])
    expected_s = specular_share(instance.rms_height_m[fallback], cosine, instance.wavelength_m)
    np.testing.assert_allclose(reflectance, expected_r)
    np.testing.assert_allclose(share, expected_s)
    assert not nonblocking.any()


def test_binding_removes_non_structural_mass_and_falls_back_when_none_remains() -> None:
    probability = np.zeros((1, 2, 2, 3), dtype=np.float32)
    probability[0, 0, 0] = (0.2, 0.3, 0.5)
    probability[0, 0, 1] = (1.0, 0.0, 0.0)
    atlas = SimpleNamespace(
        material_names=np.array(["unknown", "brick", "metal"]),
        material_probability=probability,
        material_support=np.array([[[1.0, 1.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0, -1], dtype=np.int32),
        mesh_sha256="a" * 64,
    )

    table, binding = bind_surface_atlas(
        atlas,
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([0, 1]),
    )

    assert table.class_names[-2:] == ("atlas:brick", "atlas:metal")
    np.testing.assert_allclose(binding.material_probability[0, 0, 0], [0.375, 0.625])
    np.testing.assert_array_equal(binding.material_probability[0, 0, 1], [0.0, 0.0])
    assert binding.supported[0, 0, 0]
    assert not binding.supported[0, 0, 1]


def test_participating_vegetation_does_not_promote_residual_brick_to_certainty() -> None:
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (0.7, 0.3)
    probability[0, 0, 1] = (1.0, 0.0)
    atlas = SimpleNamespace(
        material_names=np.array(["vegetation_effective", "brick"]),
        material_probability=probability,
        material_support=np.array([[[1.0, 1.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0], dtype=np.int32),
        mesh_sha256="a" * 64,
    )

    table, binding = bind_surface_atlas(
        atlas,
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([1]),
    )

    assert table.class_names[-1] == "atlas:brick"
    np.testing.assert_array_equal(binding.material_probability[0, 0, 0], [0.0])
    np.testing.assert_array_equal(binding.material_probability[0, 0, 1], [0.0])
    assert not binding.supported[0, 0, 0]
    assert not binding.supported[0, 0, 1]
    assert binding.provenance["excluded_volume_material_names"] == ["vegetation_effective"]
    assert binding.provenance["refused_by_insufficient_structural_mass"] == 2


@pytest.mark.parametrize("structural_mass", [0.49, 0.5])
def test_interface_requires_a_strict_structural_majority(structural_mass: float) -> None:
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (1.0 - structural_mass, structural_mass)
    atlas = SimpleNamespace(
        material_names=np.array(["unknown", "brick"]),
        material_probability=probability,
        material_support=np.array([[[1.0, 0.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0], dtype=np.int32),
        mesh_sha256="a" * 64,
    )

    _table, binding = bind_surface_atlas(
        atlas,
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([1]),
    )

    assert not binding.supported[0, 0, 0]
    np.testing.assert_array_equal(binding.material_probability[0, 0, 0], [0.0])


def test_dense_vistas_vegetation_is_nonblocking_without_canopy_chords() -> None:
    probability = np.zeros((1, 2, 2, 3), dtype=np.float32)
    probability[0, 0, 0] = (0.92, 0.06, 0.02)
    entity = np.zeros((1, 2, 2, 2), dtype=np.float32)
    entity[0, 0, 0] = (0.92, 0.08)
    atlas = SimpleNamespace(
        material_names=np.array(["vegetation_effective", "unknown", "brick"]),
        material_probability=probability,
        entity_names=np.array(["Vegetation", "Terrain"]),
        entity_probability=entity,
        material_support=np.array([[[1.0, 0.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0], dtype=np.int32),
        mesh_sha256="a" * 64,
    )

    _table, binding = bind_surface_atlas(
        atlas,
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([1]),
    )

    assert binding.nonblocking[0, 0, 0]
    assert not binding.supported[0, 0, 0]
    assert binding.provenance["nonblocking_vegetation_texels"] == 1


def test_explicit_grass_keeps_the_geometric_ground_interface() -> None:
    probability = np.zeros((1, 2, 2, 3), dtype=np.float32)
    probability[0, 0, 0] = (0.8, 0.18, 0.02)
    entity = np.zeros((1, 2, 2, 1), dtype=np.float32)
    entity[0, 0, 0, 0] = 1.0
    atlas = SimpleNamespace(
        material_names=np.array(["vegetation_effective", "unknown", "brick"]),
        material_probability=probability,
        entity_names=np.array(["Vegetation"]),
        entity_probability=entity,
        material_support=np.array([[[1.0, 0.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0], dtype=np.int32),
        triangle_ids=np.array([0], dtype=np.int64),
        texel_offsets=np.array([0, 1], dtype=np.int64),
        texel_row=np.array([0], dtype=np.int16),
        texel_column=np.array([0], dtype=np.int16),
        vegetation_form_names=np.array(["ground_vegetation", "woody_canopy"]),
        vegetation_form_posterior=np.array([[0.8, 0.2]], dtype=np.float32),
        vegetation_subtype_names=np.array(["grass", "tree"]),
        vegetation_subtype_posterior=np.array([[0.8, 0.2]], dtype=np.float32),
        mesh_sha256="a" * 64,
    )

    _table, binding = bind_surface_atlas(
        atlas,
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([0]),
    )

    assert not binding.nonblocking[0, 0, 0]
    assert not binding.supported[0, 0, 0]
    assert binding.provenance["vegetation"]["explicit_ground_texels"] == 1


def test_binding_refuses_an_unrecognised_material_name() -> None:
    atlas = SimpleNamespace(
        material_names=np.array(["brick", "invented_material"]),
        material_probability=np.zeros((1, 2, 2, 2), dtype=np.float32),
        material_support=np.zeros((1, 2, 2), dtype=np.float32),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0], dtype=np.int32),
        mesh_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="unsupported material name"):
        bind_surface_atlas(
            atlas,
            paths.root() / "config",
            15.0e9,
            geometric_class=np.array([0]),
        )


def test_binding_rejects_fractional_material_and_face_class_indices() -> None:
    probability = np.zeros((1, 2, 2, 1), dtype=np.float32)
    probability[0, 0, 0, 0] = 1.0
    valid = np.array([[True, True], [True, False]])
    with pytest.raises(ValueError, match="material_class must contain integer"):
        AtlasMaterialBinding(
            face_to_atlas_row=np.array([0], dtype=np.int32),
            material_probability=probability,
            supported=(probability[..., 0] > 0.0),
            valid_texels=valid,
            material_names=("brick",),
            material_class=np.array([1.5]),
            provenance={"rule": "test"},
        )

    atlas = SimpleNamespace(
        material_names=np.array(["brick"]),
        material_probability=probability,
        material_support=np.array([[[1.0, 0.0], [0.0, 0.0]]]),
        valid_texels=valid,
        face_to_atlas_row=np.array([0], dtype=np.int32),
        mesh_sha256="a" * 64,
    )
    with pytest.raises(ValueError, match="geometric_class must contain finite integer"):
        bind_surface_atlas(
            atlas,
            paths.root() / "config",
            15.0e9,
            geometric_class=np.array([0.5]),
        )
    with pytest.raises(ValueError, match="face_class must contain finite integer"):
        SbrTracer(
            Geometry(),
            np.array([0.5, 0.0]),
            np.array([2.5 - 0.05j]),
            np.array([0.001]),
            TraceConfig(rays=1),
        )


def joint_ground_atlas(road_weight: float) -> JointSemanticMaterialAtlas:
    building_weight = 1.0 - road_weight
    fallback = FALLBACK_BOUND if road_weight > building_weight else FALLBACK_HOST_CONFLICT
    return JointSemanticMaterialAtlas(
        atlas_resolution=2,
        triangle_count=1,
        mesh_sha256="a" * 64,
        entity_names=np.array(["Road", "Building"]),
        material_names=np.array(["asphalt_concrete", "brick"]),
        station_ids=np.array(["camera"]),
        station_weight=np.array([1.0], dtype=np.float32),
        triangle_ids=np.array([0], dtype=np.int64),
        texel_offsets=np.array([0, 1], dtype=np.int64),
        texel_row=np.array([0], dtype=np.uint16),
        texel_column=np.array([0], dtype=np.uint16),
        entity_offsets=np.array([0, 2], dtype=np.int64),
        entity_index=np.array([0, 1], dtype=np.uint16),
        entity_weight=np.array([road_weight, building_weight], dtype=np.float32),
        joint_offsets=np.array([0, 2], dtype=np.int64),
        joint_entity=np.array([0, 1], dtype=np.uint16),
        joint_material=np.array([0, 1], dtype=np.uint16),
        joint_weight=np.array([road_weight, building_weight], dtype=np.float32),
        support_weight=np.array([1.0], dtype=np.float32),
        observation_count=np.array([2], dtype=np.uint32),
        camera_count=np.array([1], dtype=np.uint16),
        station_mask=np.array([1], dtype=np.uint64),
        source_mask=np.array([1], dtype=np.uint8),
        concept_weight=np.array([0.0], dtype=np.float32),
        prior_weight=np.array([1.0], dtype=np.float32),
        compatible_weight=np.array([road_weight], dtype=np.float32),
        incompatible_weight=np.array([building_weight], dtype=np.float32),
        fallback_state=np.array([fallback], dtype=np.uint8),
        entity_label=np.array([0], dtype=np.int16),
        material_label=np.array([0], dtype=np.int16),
        entity_confidence=np.array([road_weight], dtype=np.float32),
        material_confidence=np.array([road_weight], dtype=np.float32),
        mean_entity_score=np.array([1.0], dtype=np.float32),
        mean_concept_confidence=np.array([0.0], dtype=np.float32),
        vegetation_form_names=np.array([], dtype="U1"),
        vegetation_subtype_names=np.array([], dtype="U1"),
        vegetation_form_posterior=np.zeros((1, 0), dtype=np.float32),
        vegetation_subtype_posterior=np.zeros((1, 0), dtype=np.float32),
    )


def test_ground_transport_excludes_building_brick_from_the_host_compatible_mixture() -> None:
    table, binding = bind_surface_atlas(
        joint_ground_atlas(0.6),
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([0]),
    )

    assert table.class_names[-2:] == ("atlas:asphalt_concrete", "atlas:brick")
    np.testing.assert_allclose(binding.material_probability[0, 0, 0], [1.0, 0.0])
    assert binding.supported[0, 0, 0]
    assert binding.provenance["transport_posterior"].startswith("material marginal of host-compatible")


def test_host_conflict_cell_falls_back_even_when_its_material_is_structurally_routable() -> None:
    _table, binding = bind_surface_atlas(
        joint_ground_atlas(0.4),
        paths.root() / "config",
        15.0e9,
        geometric_class=np.array([0]),
    )

    assert not binding.supported[0, 0, 0]
    np.testing.assert_array_equal(binding.material_probability[0, 0, 0], [0.0, 0.0])
    assert binding.provenance["refused_by_host_compatibility"] == 1


def test_atlas_material_mode_loads_the_exact_mesh_bound_artifact(tmp_path: Path) -> None:
    mesh = tmp_path / "support.ply"
    mesh.write_bytes(b"exact support mesh")
    atlas_path = tmp_path / "joint_atlas.npz"
    atlas_path.write_bytes(b"atlas")
    atlas_path.with_suffix(".json").write_text("{}\n")
    probability = np.zeros((1, 2, 2, 2), dtype=np.float32)
    probability[0, 0, 0] = (0.4, 0.6)
    loaded = SimpleNamespace(
        material_names=np.array(["brick", "metal"]),
        material_probability=probability,
        material_support=np.array([[[1.0, 0.0], [0.0, 0.0]]]),
        valid_texels=np.array([[True, True], [True, False]]),
        face_to_atlas_row=np.array([0, -1], dtype=np.int32),
        mesh_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(),
    )
    environment = SimpleNamespace(
        site_walk_semantics=lambda _site, _crop: None,
        site_fishnet=lambda _site: None,
        site_surface_atlas=lambda _site, _crop: atlas_path,
        load_surface_atlas=lambda path, *_args, **_kwargs: loaded if path == atlas_path else None,
        bind_surface_atlas=bind_surface_atlas,
        material_config=paths.root() / "config",
    )
    scene = PreparedScene(
        mesh=mesh,
        geometry=SimpleNamespace(),
        datum=0.0,
        datum_provenance={},
        face_class=np.array([0, 1]),
        areas=np.array([1.0, 2.0]),
    )
    run = RunConfig(
        site="test",
        law="band",
        estimator="escape",
        next_event=None,
        materials="atlas",
    )

    material = _bind_materials(run, scene, environment)

    assert material.atlas_material is not None
    assert material.provenance["mesh_sha256"] == loaded.mesh_sha256
    np.testing.assert_array_equal(material.face_class, scene.face_class)
    np.testing.assert_array_equal(material.face_source, [0, 0])


def test_atlas_material_mode_rejects_a_different_support_mesh(tmp_path: Path) -> None:
    mesh = tmp_path / "support.ply"
    mesh.write_bytes(b"support mesh")
    atlas_path = tmp_path / "atlas.npz"
    atlas_path.write_bytes(b"atlas")
    atlas_path.with_suffix(".json").write_text("{}\n")
    environment = SimpleNamespace(
        site_walk_semantics=lambda _site, _crop: None,
        site_fishnet=lambda _site: None,
        site_surface_atlas=lambda _site, _crop: atlas_path,
        load_surface_atlas=lambda *_args, **_kwargs: SimpleNamespace(mesh_sha256="0" * 64),
    )
    scene = PreparedScene(mesh, SimpleNamespace(), 0.0, {}, np.array([0]), np.array([1.0]))
    run = RunConfig(site="test", law="band", estimator="escape", next_event=None, materials="atlas")

    with pytest.raises(ValueError, match="different support mesh"):
        _bind_materials(run, scene, environment)


def _write_plane(path: Path) -> Path:
    path.write_text(
        """ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 2
property list uchar int vertex_indices
end_header
-100 -100 0
100 -100 0
100 100 0
-100 100 0
3 0 1 2
3 0 2 3
"""
    )
    return path


def _write_triangle(path: Path) -> Path:
    path.write_text(
        """ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
element face 1
property list uchar int vertex_indices
end_header
0 0 0
10 0 0
0 10 0
3 0 1 2
"""
    )
    return path


def test_device_prim_uv_selects_the_same_three_corner_texels_as_cpu_barycentrics(tmp_path: Path) -> None:
    mi = pytest.importorskip("mitsuba")
    dr = pytest.importorskip("drjit")
    try:
        mi.set_variant("llvm_ad_rgb")
    except ImportError as error:
        pytest.skip(str(error))
    geometry = MitsubaGeometry(_write_triangle(tmp_path / "triangle.ply"), variant="llvm_ad_rgb")
    probability = np.zeros((1, 2, 2, 3), dtype=np.float32)
    probability[0, 0, 0, 0] = 1.0
    probability[0, 0, 1, 1] = 1.0
    probability[0, 1, 0, 2] = 1.0
    valid = np.array([[True, True], [True, False]])
    binding = AtlasMaterialBinding(
        face_to_atlas_row=np.array([0], dtype=np.int32),
        material_probability=probability,
        supported=valid[None, ...],
        valid_texels=valid,
        material_names=("corner_0", "corner_1", "corner_2"),
        material_class=np.array([1, 2, 3], dtype=np.int32),
        provenance={"rule": "test"},
    )
    permittivity = np.array([2.0 - 0.01j, 3.0 - 0.03j, 6.0 - 0.1j, 12.0 - 0.5j])
    kernel = DeviceSbrKernel(
        geometry,
        np.zeros(1, dtype=np.int32),
        permittivity,
        np.zeros(4),
        TraceConfig(rays=3, max_bounces=1),
        atlas_material=binding,
    )
    points = np.array([[0.1, 0.1, 1.0], [9.8, 0.1, 1.0], [0.1, 9.8, 1.0]])
    origins = mi.Point3f(mi.Float(points[:, 0]), mi.Float(points[:, 1]), mi.Float(points[:, 2]))
    directions = mi.Vector3f(mi.Float([0.0, 0.0, 0.0]), mi.Float([0.0, 0.0, 0.0]), mi.Float([-1.0, -1.0, -1.0]))
    active = mi.Bool([True, True, True])
    intersection = geometry.intersect_device(origins, directions, active)
    dr.eval(intersection.hit, intersection.distance, intersection.face, intersection.barycentric_uv)
    hit_position = points + np.asarray(intersection.distance)[:, None] * np.array([0.0, 0.0, -1.0])
    cpu_uv = geometry.barycentric_uv(np.zeros(3, dtype=np.int64), hit_position)
    device_uv = np.asarray(intersection.barycentric_uv).T

    np.testing.assert_allclose(device_uv, cpu_uv, atol=2e-7)
    reflectance, _share, nonblocking = kernel._surface_response(
        mi.Float([1.0, 1.0, 1.0]),
        mi.UInt32([0, 0, 0]),
        intersection,
        intersection.hit,
    )
    dr.eval(reflectance)
    expected = fresnel_power_reflectance(np.ones(3), permittivity[[1, 2, 3]])
    np.testing.assert_allclose(np.asarray(reflectance), expected, rtol=2e-6, atol=1e-7)
    assert not np.asarray(nonblocking).any()


def test_llvm_device_one_hot_atlas_matches_ordinary_face_material(tmp_path: Path) -> None:
    mi = pytest.importorskip("mitsuba")
    try:
        mi.set_variant("llvm_ad_rgb")
    except ImportError as error:
        pytest.skip(str(error))
    geometry = MitsubaGeometry(_write_plane(tmp_path / "plane.ply"), variant="llvm_ad_rgb")
    config = TraceConfig(rays=2048, max_bounces=1, roulette_start=2, seed=73)
    permittivity = np.array([1.0 + 0.0j, 4.2 - 0.15j])
    rms = np.array([0.0, 0.0])
    ordinary = DeviceSbrKernel(geometry, np.array([1, 1]), permittivity, rms, config)
    valid = np.array([[True, True], [True, False]])
    probability = np.zeros((2, 2, 2, 1), dtype=np.float32)
    probability[..., 0] = valid[None, ...]
    binding = AtlasMaterialBinding(
        face_to_atlas_row=np.array([0, 1], dtype=np.int32),
        material_probability=probability,
        supported=np.broadcast_to(valid, (2, 2, 2)).copy(),
        valid_texels=valid,
        material_names=("material",),
        material_class=np.array([1], dtype=np.int32),
        provenance={"rule": "test"},
    )
    atlas = DeviceSbrKernel(
        geometry,
        np.array([1, 1]),
        permittivity,
        rms,
        config,
        atlas_material=binding,
    )

    expected = ordinary.trace_escape_records(np.array([0.0, 0.0, 1.0]))
    actual = atlas.trace_escape_records(np.array([0.0, 0.0, 1.0]))

    np.testing.assert_array_equal(actual.ray_index, expected.ray_index)
    np.testing.assert_array_equal(actual.bounces, expected.bounces)
    np.testing.assert_array_equal(actual.throughput, expected.throughput)
    np.testing.assert_array_equal(actual.exit_direction, expected.exit_direction)
