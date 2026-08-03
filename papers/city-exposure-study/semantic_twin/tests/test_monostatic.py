"""Closed form targets for the co-located branch.

Every target here is a number that exists outside the code. The Lambertian
cavity gain is derived in MONOSTATIC_SBR.md section 11.2, the image source and
flat plate returns in section 11.4, and the oracles are written out again in
this file rather than imported, so an error inside ``monostatic.py`` cannot
cancel itself against its own helper.

The first test in the file is the one that matters most, because it is the trap
the design document warns about twice. A ray that leaves the observation point
returns to that point with probability zero, so an estimator that waits for one
reports a clean, plausible, entirely wrong zero. ``test_specular_scene_is_the
_measure_zero_trap`` builds exactly that scene and asserts that the sampled
branch does return nothing while the enumerated branch returns the image source.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.propagation import ISOTROPIC, SbrTracer, SphereGeometry, TraceConfig
from semantic_twin.propagation.monostatic import (
    MonostaticConfig,
    MonostaticGather,
    half_space_first_order_return,
    specular_glints,
    to_db,
    trace_monostatic,
)

WAVELENGTH_M = 299_792_458.0 / 15.0e9
MODELS = {"isotropic": ISOTROPIC}

#: A mirror, and not the package's ``PEC_PERMITTIVITY``. That stand in has a
#: finite ``1e12`` imaginary part, which absorbs 2.8e-6 of the power at normal
#: incidence and 3.5e-6 at 45 degrees. The susceptibility targets it was chosen
#: for never resolve that, but a cavity summed over five interaction orders does,
#: at 2.5e-5, so the loss would be read as an estimator error. Nothing here needs
#: a physical material, only a lossless one.
MIRROR_PERMITTIVITY = complex(1.0, -1.0e24)

#: A Lambertian wall, and it takes an absurd roughness to get one. The Rayleigh
#: split sends the coherent share ``exp(-(4 pi s cos(th) / lam)**2)`` into the
#: specular lobe, and that share returns to one at grazing incidence however
#: rough the surface is. At ``s = 1 m`` a cosine sampled bounce lands inside the
#: transition about once in ten thousand, which is visible at 7e-5 against a
#: cavity target and reads as an estimator error rather than as the model doing
#: what it says. At ``s = 1e6 m`` the transition sits below ``cos(th) = 1.2e-8``,
#: which a cosine sample reaches with probability 1e-16.
LAMBERTIAN_M = 1.0e6

#: Smooth enough that the Rayleigh coherent share is one to machine precision,
#: so the surface is purely specular and the sampled branch must return zero.
MIRROR_M = 0.0


class TriangleGeometry:
    """Brute force triangle set, with the interface the tracer and gather need.

    Written here rather than imported because the mesh backend needs Mitsuba and
    these tests must run without it, and because a visibility oracle that shares
    no line with the estimator is the point of a validation file.
    """

    def __init__(self, vertices: np.ndarray, faces: np.ndarray) -> None:
        self.vertices = np.asarray(vertices, dtype=np.float64)
        self.faces = np.asarray(faces, dtype=np.int64)

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        origins = np.asarray(origins, dtype=np.float64)
        directions = np.asarray(directions, dtype=np.float64)
        count = origins.shape[0]
        best = np.full(count, np.inf)
        best_face = np.zeros(count, dtype=np.int64)
        best_normal = np.tile(np.array([0.0, 0.0, 1.0]), (count, 1))
        for index, face in enumerate(self.faces):
            a, b, c = self.vertices[face]
            edge1 = b - a
            edge2 = c - a
            pvec = np.cross(directions, edge2)
            det = pvec @ edge1
            parallel = np.abs(det) < 1.0e-14
            safe = np.where(parallel, 1.0, det)
            tvec = origins - a
            u = np.einsum("ij,ij->i", tvec, pvec) / safe
            qvec = np.cross(tvec, edge1)
            v = np.einsum("ij,ij->i", directions, qvec) / safe
            u_ok = (u >= 0.0) & (u <= 1.0)
            distance = (qvec @ edge2) / safe
            valid = (~parallel) & u_ok & (v >= 0.0) & (u + v <= 1.0) & (distance > 0.0) & (distance < best)
            normal = np.cross(edge1, edge2)
            normal = normal / np.linalg.norm(normal)
            best = np.where(valid, distance, best)
            best_face = np.where(valid, index, best_face)
            best_normal = np.where(valid[:, None], normal[None, :], best_normal)
        hit = np.isfinite(best)
        return hit, np.where(hit, best, 1.0e30), best_normal, best_face


def square_plate(side_m: float, height_z: float = 0.0) -> TriangleGeometry:
    """A rectangle under the origin, deliberately not centred on it.

    The diagonal of a centred rectangle runs through the foot of the
    perpendicular, which puts the specular point on the shared edge of both
    triangles and counts it twice. That is a real hazard on a real mesh and the
    geometry here is offset so the tests measure the estimator rather than that
    coincidence. How often it happens on the city meshes is reported instead.
    """
    vertices = np.array(
        [
            [-0.5 * side_m, -0.3 * side_m, height_z],
            [0.7 * side_m, -0.3 * side_m, height_z],
            [0.7 * side_m, 0.6 * side_m, height_z],
            [-0.5 * side_m, 0.6 * side_m, height_z],
        ]
    )
    return TriangleGeometry(vertices, np.array([[0, 1, 2], [0, 2, 3]]))


def cavity_first_order_gain(radius_m: float, albedo: float, wavelength_m: float) -> float:
    """MONOSTATIC_SBR.md section 11.2, rederived.

    Every wall point of a sphere is seen from the centre along its own normal, so
    ``cos(th_s) = 1`` and the range is the radius for every ray. A Lambertian wall
    of albedo ``rho`` has ``f_r = rho / pi``, and the receiver collects
    ``lam^2 / (4 pi r^2)`` of the sphere, so the order one gain is
    ``rho lam^2 / (4 pi^2 R^2)`` with no Monte Carlo variance at all.
    """
    return albedo * wavelength_m**2 / (4.0 * np.pi**2 * radius_m**2)


def image_source_gain(height_m: float, wavelength_m: float, reflectance: float = 1.0) -> float:
    """Free space spreading over the unfolded round trip, ``L = 2 h``."""
    return reflectance * (wavelength_m / (4.0 * np.pi * 2.0 * height_m)) ** 2


def plate_rcs_gain(area_m2: float, range_m: float, wavelength_m: float, reflectance: float = 1.0) -> float:
    """Radar equation with the physical optics normal incidence plate RCS.

    ``sigma = 4 pi A^2 / lam^2`` into ``g = sigma lam^2 / ((4 pi)^3 r^4)``.
    """
    sigma = 4.0 * np.pi * area_m2**2 / wavelength_m**2
    return reflectance * sigma * wavelength_m**2 / ((4.0 * np.pi) ** 3 * range_m**4)


def cavity_tracer(radius_m: float, max_bounces: int, rays: int = 4000) -> SbrTracer:
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=rays,
        local_cells=64,
        max_bounces=max_bounces,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=3,
        batch=rays,
    )
    return SbrTracer(
        SphereGeometry(radius_m),
        None,
        np.array([MIRROR_PERMITTIVITY]),
        np.array([LAMBERTIAN_M]),
        config,
    )


def plate_tracer(geometry: TriangleGeometry, rms_height_m: float, rays: int = 2000) -> SbrTracer:
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=rays,
        local_cells=64,
        max_bounces=2,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=5,
        batch=rays,
    )
    return SbrTracer(
        geometry,
        np.zeros(geometry.faces.shape[0], dtype=np.int64),
        np.array([MIRROR_PERMITTIVITY]),
        np.array([rms_height_m]),
        config,
    )


def gather_config(**kwargs) -> MonostaticConfig:
    return MonostaticConfig(shadow_epsilon_m=1.0e-9, **kwargs)


def test_specular_scene_is_the_measure_zero_trap():
    """A mirror returns everything and the sampled estimator finds none of it."""
    height = 3.0
    geometry = square_plate(400.0)
    tracer = plate_tracer(geometry, MIRROR_M)
    origin = np.array([0.0, 0.0, height])

    _, result = trace_monostatic(tracer, origin, MODELS, config=gather_config())

    assert result.gain_diffuse == 0.0, "a delta lobe cannot be connected to a point by sampling"
    assert result.gain_glint == pytest.approx(image_source_gain(height, WAVELENGTH_M), rel=1.0e-9, abs=0.0)
    assert result.gain > 0.0
    assert result.glint_facets == 1


def test_cavity_first_order_is_exact():
    """One bounce in a lossless Lambertian cavity, against the closed form."""
    radius = 10.0
    tracer = cavity_tracer(radius, max_bounces=1)
    _, result = trace_monostatic(tracer, np.zeros(3), MODELS, config=gather_config(), glints=False)

    target = cavity_first_order_gain(radius, 1.0, WAVELENGTH_M)
    assert result.gain_diffuse == pytest.approx(target, rel=1.0e-9, abs=0.0)
    assert result.relative_standard_error == pytest.approx(0.0, abs=1.0e-9)


def test_cavity_multiplies_by_order():
    """The lossless integrating sphere: order K returns what order one returns."""
    radius = 8.0
    bounces = 5
    tracer = cavity_tracer(radius, max_bounces=bounces)
    _, result = trace_monostatic(tracer, np.zeros(3), MODELS, config=gather_config(), glints=False)

    first = cavity_first_order_gain(radius, 1.0, WAVELENGTH_M)
    assert result.gain_diffuse == pytest.approx(bounces * first, rel=1.0e-8, abs=0.0)
    for order in range(1, bounces + 1):
        assert result.gain_by_order[order] == pytest.approx(first, rel=1.0e-8, abs=0.0)
    assert result.gain_by_order[0] == 0.0
    assert result.gain_by_order[bounces + 1 :].sum() == 0.0


def test_cavity_scales_as_wavelength_squared_and_inverse_area():
    """The aperture is `lam^2 / (4 pi)` and the range law is `1 / r^2`, once."""
    fine = cavity_tracer(10.0, max_bounces=1)
    coarse = cavity_tracer(20.0, max_bounces=1)
    _, near = trace_monostatic(fine, np.zeros(3), MODELS, config=gather_config(), glints=False)
    _, far = trace_monostatic(coarse, np.zeros(3), MODELS, config=gather_config(), glints=False)
    assert near.gain_diffuse / far.gain_diffuse == pytest.approx(4.0, rel=1.0e-8, abs=0.0)

    config = TraceConfig(
        frequency_hz=30.0e9,
        rays=4000,
        local_cells=64,
        max_bounces=1,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=3,
        batch=4000,
    )
    doubled = SbrTracer(SphereGeometry(10.0), None, np.array([MIRROR_PERMITTIVITY]), np.array([LAMBERTIAN_M]), config)
    _, high = trace_monostatic(doubled, np.zeros(3), MODELS, config=gather_config(), glints=False)
    assert near.gain_diffuse / high.gain_diffuse == pytest.approx(4.0, rel=1.0e-8, abs=0.0)


def test_cavity_range_profile_is_the_round_trip():
    """Order one in a cavity of radius R arrives as one line at `2R`."""
    radius = 12.3
    tracer = cavity_tracer(radius, max_bounces=1)
    _, result = trace_monostatic(tracer, np.zeros(3), MODELS, config=gather_config(range_bin_m=1.0), glints=False)

    assert result.mean_two_way_range_m == pytest.approx(2.0 * radius, rel=1.0e-6, abs=0.0)
    occupied = np.flatnonzero(result.range_profile > 0.0)
    assert occupied.size == 1
    assert occupied[0] == int(2.0 * radius / 1.0)


def test_large_plate_is_the_image_source():
    """A facet wider than its Fresnel zone is the infinite plane it lies in."""
    for height in (1.5, 3.0, 12.0):
        geometry = square_plate(400.0)
        glint = specular_glints(
            np.array([0.0, 0.0, height]),
            vertices=geometry.vertices,
            faces=geometry.faces,
            face_class=None,
            permittivity=np.array([MIRROR_PERMITTIVITY]),
            rms_height_m=np.array([MIRROR_M]),
            wavelength_m=WAVELENGTH_M,
            geometry=geometry,
            config=gather_config(),
        )
        assert glint.gain == pytest.approx(image_source_gain(height, WAVELENGTH_M), rel=1.0e-9, abs=0.0)
        assert glint.subfresnel_facets == 0


def test_small_plate_is_the_physical_optics_rcs():
    """A facet inside its Fresnel zone is the flat plate of the radar textbook."""
    range_m = 100.0
    side = 0.2
    vertices = np.array([[-side, -side, 0.0], [side, -side, 0.0], [0.0, side, 0.0]])
    geometry = TriangleGeometry(vertices, np.array([[0, 1, 2]]))
    area = 0.5 * np.linalg.norm(np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0]))
    assert area < 0.5 * WAVELENGTH_M * range_m, "the test is meaningless outside the sub Fresnel regime"

    glint = specular_glints(
        np.array([0.0, 0.0, range_m]),
        vertices=geometry.vertices,
        faces=geometry.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=geometry,
        config=gather_config(),
    )
    assert glint.gain == pytest.approx(plate_rcs_gain(area, range_m, WAVELENGTH_M), rel=1.0e-9, abs=0.0)
    assert glint.subfresnel_facets == 1


def test_plate_range_laws_are_r2_and_r4():
    """The two regimes carry different range exponents, which is how to tell them apart."""
    large = square_plate(400.0)
    near = specular_glints(
        np.array([0.0, 0.0, 5.0]),
        vertices=large.vertices,
        faces=large.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=large,
        config=gather_config(),
    )
    far = specular_glints(
        np.array([0.0, 0.0, 10.0]),
        vertices=large.vertices,
        faces=large.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=large,
        config=gather_config(),
    )
    assert near.gain / far.gain == pytest.approx(4.0, rel=1.0e-9, abs=0.0)

    small = TriangleGeometry(np.array([[-0.2, -0.2, 0.0], [0.2, -0.2, 0.0], [0.0, 0.2, 0.0]]), np.array([[0, 1, 2]]))
    close = specular_glints(
        np.array([0.0, 0.0, 100.0]),
        vertices=small.vertices,
        faces=small.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=small,
        config=gather_config(),
    )
    distant = specular_glints(
        np.array([0.0, 0.0, 200.0]),
        vertices=small.vertices,
        faces=small.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=small,
        config=gather_config(),
    )
    assert close.gain / distant.gain == pytest.approx(16.0, rel=1.0e-9, abs=0.0)


def test_glint_needs_the_foot_of_the_perpendicular_inside_the_facet():
    """Slide the observation point off the plate and the first order return goes."""
    geometry = square_plate(4.0)
    off = specular_glints(
        np.array([40.0, 0.0, 3.0]),
        vertices=geometry.vertices,
        faces=geometry.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=geometry,
        config=gather_config(),
    )
    assert off.gain == 0.0
    assert off.facets == 0


def test_glint_is_blocked_by_an_occluder():
    """Visibility is enforced on the way to the specular point."""
    plate = square_plate(40.0)
    blocker = square_plate(40.0, height_z=1.0)
    combined = TriangleGeometry(
        np.concatenate([plate.vertices, blocker.vertices]),
        np.concatenate([plate.faces, blocker.faces + plate.vertices.shape[0]]),
    )
    origin = np.array([0.0, 0.0, 3.0])
    glint = specular_glints(
        origin,
        vertices=combined.vertices,
        faces=combined.faces,
        face_class=None,
        permittivity=np.array([MIRROR_PERMITTIVITY]),
        rms_height_m=np.array([MIRROR_M]),
        wavelength_m=WAVELENGTH_M,
        geometry=combined,
        config=gather_config(),
    )
    assert glint.occluded_facets == 1
    assert glint.facets == 1
    assert glint.gain == pytest.approx(image_source_gain(2.0, WAVELENGTH_M), rel=1.0e-9, abs=0.0)


def test_gather_is_blocked_by_an_occluder():
    """A wall between the scattering surface and the observer removes the return."""
    radius = 10.0
    tracer = cavity_tracer(radius, max_bounces=1, rays=2000)
    _, open_result = trace_monostatic(tracer, np.zeros(3), MODELS, config=gather_config(), glints=False)
    assert open_result.gain_diffuse > 0.0
    assert open_result.blocked_fraction == 0.0

    class ShieldedSphere(SphereGeometry):
        """The cavity, plus an opaque shell just outside the observation point."""

        def intersect(self, origins, directions):
            hit, distance, normal, face = super().intersect(origins, directions)
            shell = np.linalg.norm(origins - self.centre, axis=1) > 0.5
            close = np.full(distance.shape, 0.1)
            return (
                np.where(shell, True, hit),
                np.where(shell, close, distance),
                normal,
                face,
            )

    shielded = cavity_tracer(radius, max_bounces=1, rays=2000)
    shielded.geometry = ShieldedSphere(radius)
    gather = MonostaticGather(np.zeros(3), shielded.geometry, shielded.wavelength_m, gather_config())
    shielded.trace(np.zeros(3), MODELS, gather=gather)
    total, _, _, _, _ = gather.finalise(shielded.config.rays)
    assert total == 0.0
    assert gather.blocked == gather.shadow_rays > 0


def test_attaching_a_gather_changes_no_traced_number():
    """The adjoint result is bit identical with the co-located branch attached."""
    tracer = cavity_tracer(9.0, max_bounces=3, rays=3000)
    plain = tracer.trace(np.zeros(3), MODELS, seed=11)
    gather = MonostaticGather(np.zeros(3), tracer.geometry, tracer.wavelength_m, gather_config())
    with_gather = tracer.trace(np.zeros(3), MODELS, seed=11, gather=gather)

    assert with_gather.susceptibility == plain.susceptibility
    assert with_gather.susceptibility_direct == plain.susceptibility_direct
    assert np.array_equal(with_gather.exit_profile, plain.exit_profile)
    for name in plain.rho:
        assert np.array_equal(with_gather.rho[name], plain.rho[name])
    assert with_gather.sky_fraction == plain.sky_fraction
    assert with_gather.mean_bounces == plain.mean_bounces
    assert with_gather.escaped_fraction == plain.escaped_fraction
    assert gather.shadow_rays > 0


def test_batching_does_not_move_the_answer():
    """Several batches accumulate the same total as one, to Monte Carlo noise."""
    single = cavity_tracer(10.0, max_bounces=2, rays=4000)
    _, one = trace_monostatic(single, np.zeros(3), MODELS, config=gather_config(), glints=False)

    split_config = TraceConfig(
        frequency_hz=15.0e9,
        rays=4000,
        local_cells=64,
        max_bounces=2,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=3,
        batch=1000,
    )
    split = SbrTracer(
        SphereGeometry(10.0), None, np.array([MIRROR_PERMITTIVITY]), np.array([LAMBERTIAN_M]), split_config
    )
    _, many = trace_monostatic(split, np.zeros(3), MODELS, config=gather_config(), glints=False)
    assert many.gain_diffuse == pytest.approx(one.gain_diffuse, rel=1.0e-8, abs=0.0)
    assert many.rays == one.rays == 4000


def test_scalars_carry_the_split_and_are_finite():
    tracer = cavity_tracer(10.0, max_bounces=2)
    _, result = trace_monostatic(tracer, np.zeros(3), MODELS, config=gather_config(), glints=False)
    row = result.scalars()
    assert row["mono_gain"] == pytest.approx(result.gain)
    assert row["mono_gain_db"] == pytest.approx(10.0 * np.log10(result.gain))
    assert row["mono_glint_share"] == 0.0
    assert row["mono_first_order_share"] == pytest.approx(0.5, rel=1.0e-6, abs=0.0)
    assert np.isfinite(list(row.values())).all()
    assert to_db(0.0) < -290.0


def rectangle(corners: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return corners, np.array([[0, 1, 2], [0, 2, 3]])


def occluded_scene() -> TriangleGeometry:
    """A near wall that hides a far wall and the ground behind it, from `S`.

    With `S` at ``(0, 0, 1.5)`` the near wall at ``x = 4`` reaches to ``z = 3``,
    which puts the whole of the far wall's lower plate and the whole of the
    ground beyond ``x = 4`` out of sight. Those are the surfaces an adjoint path
    can reach at its second interaction and a closed loop cannot.
    """
    plates = [
        np.array([[-6.0, -5.0, 0.0], [4.0, -5.0, 0.0], [4.0, 5.0, 0.0], [-6.0, 5.0, 0.0]]),
        np.array([[4.0, -5.0, 0.0], [8.0, -5.0, 0.0], [8.0, 5.0, 0.0], [4.0, 5.0, 0.0]]),
        np.array([[4.0, -5.0, 0.0], [4.0, 5.0, 0.0], [4.0, 5.0, 3.0], [4.0, -5.0, 3.0]]),
        np.array([[6.0, -5.0, 0.0], [6.0, 5.0, 0.0], [6.0, 5.0, 3.0], [6.0, -5.0, 3.0]]),
        np.array([[6.0, -5.0, 3.0], [6.0, 5.0, 3.0], [6.0, 5.0, 10.0], [6.0, -5.0, 10.0]]),
    ]
    vertices = np.concatenate(plates)
    faces = np.concatenate([rectangle(plate)[1] + 4 * i for i, plate in enumerate(plates)])
    return TriangleGeometry(vertices, faces)


def visible_faces(geometry: TriangleGeometry, origin: np.ndarray, samples: int = 40_000) -> np.ndarray:
    """Triangles with at least one point directly visible from ``origin``.

    Built by first hit sampling, which is what a panorama derived mask is: a
    triangle enters it when some of it was seen, not when all of it was.
    """
    from semantic_twin.propagation import fibonacci_sphere

    directions = fibonacci_sphere(samples)
    hit, _, _, face = geometry.intersect(np.tile(origin, (samples, 1)), directions)
    seen = np.zeros(geometry.faces.shape[0], dtype=bool)
    seen[face[hit]] = True
    return seen


def evidence_tracer(geometry: TriangleGeometry, rays: int = 20_000) -> SbrTracer:
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=rays,
        local_cells=64,
        max_bounces=3,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=17,
        batch=rays,
    )
    return SbrTracer(
        geometry,
        np.zeros(geometry.faces.shape[0], dtype=np.int64),
        np.array([complex(5.24, -0.46)]),
        np.array([LAMBERTIAN_M]),
        config,
    )


def test_a_closed_loop_lands_only_on_surfaces_the_observer_can_see():
    """The guarantee, on traced paths rather than on the argument for it.

    Both ends of a returning path are visible from the observation point: the
    first because the ray reached it unoccluded, the last because the return leg
    did. So at first and second order the whole chain is visible, exactly, while
    the adjoint path that keeps going is under no such constraint.
    """
    origin = np.array([0.0, 0.0, 1.5])
    geometry = occluded_scene()
    observed = visible_faces(geometry, origin)
    assert not observed.all(), "the scene must hide something for the test to mean anything"

    tracer = evidence_tracer(geometry)
    _, result = trace_monostatic(tracer, origin, MODELS, config=gather_config(), glints=False, observed=observed)
    ledger = result.coverage
    assert ledger["available"]

    for order in (1, 2, 3):
        assert ledger["closed_loop_last_surface_observed"][order] == pytest.approx(1.0, abs=0.0, rel=0.0)
    assert ledger["closed_loop_chain_observed"][1] == pytest.approx(1.0, abs=0.0, rel=0.0)
    assert ledger["closed_loop_chain_observed"][2] == pytest.approx(1.0, abs=0.0, rel=0.0)
    assert ledger["closed_loop_chain_observed_total"] > 0.99

    # Where the two columns part. How far apart they get is a property of the
    # scene and of how much of it the observer can see, so the size of the gap
    # is measured on the cities and only its sign is asserted here.
    assert ledger["open_path_last_surface_observed"][1] == pytest.approx(1.0, abs=0.0, rel=0.0)
    assert ledger["open_path_last_surface_observed"][2] < 1.0
    assert ledger["open_path_last_surface_observed"][3] < 0.95
    assert ledger["open_path_chain_observed"][2] < ledger["closed_loop_chain_observed"][2]
    assert ledger["open_path_chain_observed"][3] < ledger["closed_loop_chain_observed"][3]

    # The guarantee is over the two ends of the loop, not over the middle of it,
    # so a third order chain can still route through a surface nobody saw.
    assert ledger["closed_loop_chain_observed"][3] < 1.0


def test_the_ledger_is_absent_without_a_mask():
    tracer = evidence_tracer(occluded_scene(), rays=2000)
    _, result = trace_monostatic(tracer, np.array([0.0, 0.0, 1.5]), MODELS, config=gather_config(), glints=False)
    assert result.coverage == {"available": False}
    assert "mono_evidence_chain_share" not in result.scalars()


#: ITU-R P.2040-4 asphalt and concrete at 15 GHz with the stone sett paving
#: roughness, which is what ``config/itu_p2040_4.json`` binds the ground class to
#: and therefore the material every city number in this study stands on.
GROUND = complex(4.83, -0.568858253507591)
GROUND_ROUGHNESS_M = 0.0037859388972001826


def half_space_oracle(height_m: float, permittivity: complex, rms_height_m: float, wavelength_m: float) -> float:
    """``(A_e / (2 pi h^2)) int R (1 - kappa) mu^3 dmu``, reimplemented.

    Fresnel and the Rayleigh factor are written out again rather than imported,
    so this shares no line with the estimator or with the package helper it is
    checking.
    """
    mu = np.linspace(1.0e-9, 1.0, 40_001).astype(np.complex128)
    root = np.sqrt(permittivity - (1.0 - mu**2))
    te = (mu - root) / (mu + root)
    tm = (permittivity * mu - root) / (permittivity * mu + root)
    reflectance = np.real(0.5 * (np.abs(te) ** 2 + np.abs(tm) ** 2))
    g = 4.0 * np.pi * rms_height_m * np.real(mu) / wavelength_m
    coherent = np.exp(-np.minimum(g * g, 60.0))
    integral = float(np.trapezoid(reflectance * (1.0 - coherent) * np.real(mu) ** 3, np.real(mu)))
    return wavelength_m**2 / (4.0 * np.pi) / (2.0 * np.pi * height_m**2) * integral


def test_the_gather_reproduces_the_half_space_return():
    """The one closed form with a real material and a real angular integral.

    The cavity pins the aperture and the throughput chain but sees ``cos = 1`` at
    every vertex, so it cannot catch an error in the return lobe or in the range
    law. A half space under the observer exercises both: the estimator has to get
    ``mu^3`` right, and it has to get the angular dependence of Fresnel and of the
    Rayleigh split right, against an integral computed independently.
    """
    from semantic_twin.propagation import PlaneGeometry

    height = 1.5
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=400_000,
        local_cells=64,
        max_bounces=1,
        roulette_start=99,
        ray_epsilon_m=1.0e-9,
        seed=19,
        batch=400_000,
    )
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([GROUND]),
        np.array([GROUND_ROUGHNESS_M]),
        config,
    )
    _, result = trace_monostatic(tracer, np.array([0.0, 0.0, height]), MODELS, config=gather_config(), glints=False)

    target = half_space_oracle(height, GROUND, GROUND_ROUGHNESS_M, WAVELENGTH_M)
    assert result.gain_diffuse == pytest.approx(target, rel=0.01, abs=0.0)
    assert half_space_first_order_return(height, GROUND, GROUND_ROUGHNESS_M, WAVELENGTH_M) == pytest.approx(
        target, rel=1.0e-4, abs=0.0
    )
    # Half the rays go up and never come back, so the estimator sees 2e5 of them
    # and its own error bar has to be consistent with the residual.
    assert result.relative_standard_error < 0.01
    assert abs(result.gain_diffuse / target - 1.0) < 4.0 * result.relative_standard_error


def test_the_half_space_return_scales_as_inverse_height_squared():
    a = half_space_first_order_return(1.5, GROUND, GROUND_ROUGHNESS_M, WAVELENGTH_M)
    b = half_space_first_order_return(3.0, GROUND, GROUND_ROUGHNESS_M, WAVELENGTH_M)
    assert a / b == pytest.approx(4.0, rel=1.0e-12, abs=0.0)
