"""External cross validation of the adjoint estimator against Sionna RT.

Everything in `tests/test_propagation.py` is either an invariant the estimator
was built to satisfy or a closed form derived from the same physics the
estimator implements. That suite is strong against implementation error and
blind to formulation error, and the illumination correction of 2026-08-02 is
the proof: it moved eleven cities by up to 6.3 dB and no test failed. This
module supplies the missing rung, an independent solver answering the same
question on the same triangles with the same dielectrics.

The oracle is Sionna RT 2.0.1. MONOSTATIC_SBR.md section 10.2 already argued
that Sionna cannot be the engine, for reasons that all survive here: material
is per Mitsuba shape rather than per texel, co-located source and target are an
explicit deleted degeneracy, and there is no way to inject a primary visibility
atlas. None of those disqualify it as an oracle, because an oracle is asked one
scalar question per source direction and does not have to be efficient.

What is being compared
----------------------
The estimator's susceptibility is

    chi = integral over 4 pi of  T(u_s) Q(u_s) dOmega(u_s)

where `T(u_s)` is the total power arriving at the standpoint from a distant
source in direction `u_s`, divided by what the same source delivers with every
building deleted, so `T = 1` in free space. That is exactly what the adjoint
estimator of `tracer.py` accumulates: a ray leaving the standpoint and escaping
towards `u_s` with power throughput `w` is the reverse of a path carrying the
fraction `w` from a source at `u_s`, so

    chi_hat = (4 pi / N) sum_j  w_j Q(u_ext,j)

is a Monte Carlo integral of `T Q` over the sphere.

`T` is a question Sionna can answer. Put a transmitter at the standpoint and a
receiver at `x + R u_s` with `R` far outside the crop, take the incoherent power
sum over paths, and divide by the free space reference:

    T(u_s) = 0.5 * sum over rx and tx polarisations of |a|^2 / (lam / (4 pi R))^2

The transmitter sits at the standpoint rather than at the sky point for a
practical reason and not a physical one: Sionna's shoot and bounce launches
`samples_per_src` rays from each source, and a source 20 km away would put
essentially all of them past the crop. Reciprocity makes the two arrangements
the same number, and the candidate generator connects each interaction point to
every target with a shadow ray, so a distant target costs nothing extra.

The factor 0.5 and the sum over both transmit and both receive polarisations is
the unpolarised average, which is what `tracer.py` transports. Verified against
free space: a cross polarised isotropic pair at 1 km returns `|a| = lam/(4 pi d)`
on each co-polarised port and nothing on the cross terms, so the sum is
`2 (lam/4 pi d)^2` and `T = 1`.

Four things had to be matched before the comparison meant anything
------------------------------------------------------------------
1. **The dielectric.** Sionna's `fresnel_reflection_coefficients_simplified` is
   character for character the half space formula `tracer.fresnel_power_reflectance`
   uses, including the `eta = eps' - j eps''` sign convention. But
   `RadioMaterial` puts it through `itu_coefficients_single_layer_slab`, and at
   the default 0.1 m thickness the brick facade's slab resonance is worth 3.0 dB
   against the half space. At 2 m it is below 1e-4 dB for every class here. The
   thickness is therefore not a free parameter, it is the thickness at which
   Sionna stops modelling something the estimator does not model, and
   `SLAB_THICKNESS_M` is pinned by test.

2. **The source range.** The estimator has no source range at all: an escaping
   ray is weighted by `Q(u_ext)` wherever its last vertex sits, which is the
   plane wave limit. A Sionna source at finite `R` sees each last vertex at a
   slightly different spreading, an error of order `2 |x_K - x| / R`. Measured
   on the dielectric ground plane, the residual against the closed form is
   0.015 dB at R = 2 km and 0.002 dB at R = 20 km, scaling as 1/R exactly as
   predicted. `SOURCE_RANGE_M` is 20 km.

3. **The scattering split.** `tracer.py` sends the whole Fresnel-reflected power
   either into the mirror direction, with probability `exp(-g^2)`, or into a
   cosine lobe. Sionna scales the specular Jones matrix by `sqrt(1 - S^2)` and
   the diffuse one by `S`, with `S` a per material constant. The two agree
   exactly at `S = 0` against zero roughness, and exactly at `S = 1` against
   roughness large enough to drive `exp(-g^2)` to zero, and only approximately
   in between, because the Rayleigh share depends on incidence angle and `S`
   does not. So the comparison runs three configurations: `specular` and
   `diffuse` are exact roughness matches and bracket the physics, `production` is
   the shipped roughness against the flux averaged `S` of `matched_scattering`
   and its residual is a model difference rather than an error.

4. **Diffraction.** Off in both, for the primary comparison, because the
   estimator has no diffraction at all and a comparison that left it on in the
   oracle would attribute a missing physical mechanism to a disagreement in the
   ones that are present. `compare(..., diffraction=True)` turns Sionna's first
   order wedge diffraction on, which measures the omission that PAPER_METHODS
   section 9.3 currently only bounds, and section 7 of CROSS_VALIDATION.md
   reports it.

What the comparison cannot see, stated rather than hidden: both tools read the
same triangles through the same Mitsuba BVH, so the line of sight part of `T` is
a shared computation and agreement on it is not evidence. `susceptibility` and
`scene_transfer` therefore split `T` into its zero interaction part and the rest,
and the multipath residual is where the two implementations are actually
independent. The illumination density `Q` is likewise the estimator's own and is
applied to both sides, so this cannot validate the illumination law.

The oracle's specular branch is not usable on a tessellated surface
-------------------------------------------------------------------
`tessellation_experiment` found this and CROSS_VALIDATION.md section 5 reports
it. On a flat plane whose exact isotropic susceptibility is 0.6405 irrespective
of tessellation, Sionna returns 0.6320 when the plane is two triangles and 452
when it is 160,000 triangles carrying 0.2 mm of vertex jitter, keeping 3671
specular paths per source direction where the correct answer is one. The count
and the energy rise and fall together as the jitter is swept, the diffuse branch
run over the same geometries is indifferent to it, and the estimator is
indifferent to it, so the fault is in the image method rather than in this
harness or in the estimator. `MODES[0]` is kept because it is the only exact
model match Sionna's specular path solver admits, and its city numbers are
reported as a diagnostic rather than as agreement.
"""

from __future__ import annotations

import io
import math
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .directions import IlluminationModel
from .tracer import DEFAULT_MAX_BOUNCES

SPEED_OF_LIGHT_M_S = 299_792_458.0
VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12

#: Slab thickness at which Sionna's ITU single layer slab is the half space the
#: estimator implements. Pinned by ``test_slab_thickness_is_a_half_space``.
SLAB_THICKNESS_M = 2.0

#: Range at which a Sionna point source is the estimator's plane wave. The
#: residual against the ground plane closed form is 0.002 dB here.
SOURCE_RANGE_M = 20_000.0

#: RMS height that saturates the Rayleigh split to fully diffuse. ``exp(-g^2)``
#: with ``g = 4 pi s cos/lam`` is below 1e-26 for every incidence within 89 deg
#: of the normal at 15 GHz, which is the ``S = 1`` Sionna configuration.
FULLY_DIFFUSE_RMS_HEIGHT_M = 1.0

#: The three configurations the report runs. The first two are exact model
#: matches, the third is the shipped model against its closest Sionna analogue.
MODES = ("specular", "diffuse", "production")


def conductivity_from_permittivity(permittivity: np.ndarray, frequency_hz: float) -> np.ndarray:
    """Sionna's conductivity, in S/m, from the ITU complex permittivity.

    ``permittivity`` is ``eps' - j eps''`` as ``scene.load_bindings`` returns it,
    and Sionna forms ``eta = eps_r - j sigma / (omega eps_0)``, so the imaginary
    part is carried as a conductivity and nothing else changes.
    """
    imaginary = -np.asarray(permittivity).imag
    return imaginary * 2.0 * np.pi * float(frequency_hz) * VACUUM_PERMITTIVITY_F_M


def free_space_reference(range_m: float, wavelength_m: float) -> float:
    """``(lam / (4 pi R))^2``, the power transfer of an isotropic pair in the open."""
    return float((wavelength_m / (4.0 * np.pi * float(range_m))) ** 2)


def rayleigh_specular_share(rms_height_m: np.ndarray, wavelength_m: float) -> np.ndarray:
    """Flux weighted mean of ``exp(-g^2)`` over incidence angle.

    The Rayleigh share the tracer applies is ``exp(-(a cos)^2)`` with
    ``a = 4 pi s / lam``. Averaging it over a hemisphere with the ``cos`` weight
    that flux carries gives ``(1 - exp(-a^2)) / a^2`` in closed form, which is
    the single number Sionna's constant scattering coefficient has to stand for.
    """
    a = 4.0 * np.pi * np.asarray(rms_height_m, dtype=np.float64) / float(wavelength_m)
    a_sq = a * a
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(
            a_sq > 1.0e-12, (1.0 - np.exp(-np.minimum(a_sq, 700.0))) / np.where(a_sq > 0.0, a_sq, 1.0), 1.0
        )
    return np.clip(share, 0.0, 1.0)


def matched_scattering_coefficient(rms_height_m: np.ndarray, wavelength_m: float) -> np.ndarray:
    """Sionna's ``S`` such that ``S^2`` is the tracer's mean diffuse power share."""
    return np.sqrt(np.clip(1.0 - rayleigh_specular_share(rms_height_m, wavelength_m), 0.0, 1.0))


def mode_materials(
    mode: str,
    rms_height_m: np.ndarray,
    wavelength_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """``(tracer rms height, Sionna scattering coefficient)`` for one comparison mode."""
    rms = np.asarray(rms_height_m, dtype=np.float64)
    if mode == "specular":
        return np.zeros_like(rms), np.zeros_like(rms)
    if mode == "diffuse":
        return np.full_like(rms, FULLY_DIFFUSE_RMS_HEIGHT_M), np.ones_like(rms)
    if mode == "production":
        return rms, matched_scattering_coefficient(rms, wavelength_m)
    raise ValueError(f"unknown comparison mode {mode!r}")


# ---------------------------------------------------------------------------
# Sky sampling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkySample:
    """Source directions drawn from a mixture of the illumination models.

    Sampling each model in turn and evaluating the mixture density as the
    proposal bounds every importance weight by the number of components, which
    is what makes a few hundred Sionna solves enough. With three models the
    weight `Q_m / p` can never exceed 3, so no single direction can dominate the
    estimate and the variance is finite by construction rather than by luck.
    """

    directions: np.ndarray  # (N, 3)
    proposal: np.ndarray  # (N,) mixture density on the sphere, sr^-1
    density: dict[str, np.ndarray]  # model -> Q(u) in sr^-1
    model_names: tuple[str, ...]

    def __len__(self) -> int:
        return int(self.directions.shape[0])

    def weight(self, name: str) -> np.ndarray:
        return self.density[name] / self.proposal


def _elevation_cdf(model: IlluminationModel, samples: int = 20_001) -> tuple[np.ndarray, np.ndarray]:
    """Elevation abscissae and the normalised cumulative of ``q(alpha)``."""
    low = math.radians(model.elevation_min_deg)
    high = math.radians(model.elevation_max_deg)
    grid = np.linspace(low, high, samples)
    for knot in model.knots():
        if low < knot < high:
            grid = np.insert(grid, int(np.searchsorted(grid, knot)), knot)
    directions = np.column_stack([np.cos(grid), np.zeros_like(grid), np.sin(grid)])
    density = model.weight(directions) * np.cos(grid)
    cumulative = np.concatenate([[0.0], np.cumsum(0.5 * (density[1:] + density[:-1]) * np.diff(grid))])
    total = cumulative[-1]
    if total <= 0.0:
        raise ValueError(f"illumination model {model.name!r} has no support")
    return grid, cumulative / total


def sample_sky(
    models: dict[str, IlluminationModel],
    count: int,
    rng: np.random.Generator,
) -> SkySample:
    """Draw ``count`` source directions from the equal mixture of ``models``."""
    names = tuple(models)
    per_model = np.array_split(np.arange(count), len(names))
    elevation = np.zeros(count)
    for name, index in zip(names, per_model, strict=True):
        if index.size == 0:
            continue
        grid, cumulative = _elevation_cdf(models[name])
        elevation[index] = np.interp(rng.random(index.size), cumulative, grid)
    azimuth = rng.uniform(0.0, 2.0 * np.pi, size=count)
    directions = np.column_stack(
        [np.cos(elevation) * np.cos(azimuth), np.cos(elevation) * np.sin(azimuth), np.sin(elevation)]
    )
    density = {name: models[name].density(directions) for name in names}
    proposal = np.mean([density[name] for name in names], axis=0)
    return SkySample(directions=directions, proposal=proposal, density=density, model_names=names)


def susceptibility(transfer: np.ndarray, sky: SkySample) -> dict[str, tuple[float, float]]:
    """``chi`` and its standard error per illumination model, from sampled ``T``.

    ``transfer`` is ``T(u_s)`` at ``sky.directions``. The estimator is the plain
    importance sampling mean, so the reported error is the Monte Carlo error over
    source directions and nothing else.
    """
    values = np.asarray(transfer, dtype=np.float64)
    out: dict[str, tuple[float, float]] = {}
    for name in sky.model_names:
        terms = values * sky.weight(name)
        out[name] = (float(terms.mean()), float(terms.std(ddof=1) / np.sqrt(terms.size)))
    return out


def band_transfer(transfer: np.ndarray, sky: SkySample, sin_edges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Solid angle average of ``T`` inside each ``sin(elevation)`` band.

    This is the quantity ``PointResult.exit_profile`` reports, so it compares the
    two tools resolved in elevation with no illumination model in the way. The
    isotropic component of the proposal is what makes the uniform measure
    available: the weight is ``1 / (4 pi p)``, again bounded by the number of
    mixture components.
    """
    values = np.asarray(transfer, dtype=np.float64)
    edges = np.asarray(sin_edges, dtype=np.float64)
    weight = 1.0 / (4.0 * np.pi * sky.proposal)
    band = np.clip(np.searchsorted(edges, sky.directions[:, 2], side="right") - 1, 0, edges.size - 2)
    profile = np.zeros(edges.size - 1)
    error = np.zeros(edges.size - 1)
    solid_angle = 2.0 * np.pi * np.diff(edges)
    for i in range(profile.size):
        inside = band == i
        terms = np.where(inside, values * weight, 0.0) * 4.0 * np.pi / solid_angle[i]
        profile[i] = terms.mean()
        error[i] = terms.std(ddof=1) / np.sqrt(terms.size)
    return profile, error


# ---------------------------------------------------------------------------
# Scene construction
# ---------------------------------------------------------------------------


def write_ply(vertices: np.ndarray, faces: np.ndarray) -> bytes:
    """Little endian binary PLY, float32 vertices and int32 indices.

    Written here rather than through a mesh library so the bytes Sionna reads
    are the float32 vertex buffer Mitsuba already gave the estimator, with no
    reprocessing, no vertex merging and no normal generation in between.
    """
    v = np.ascontiguousarray(vertices, dtype="<f4")
    f = np.ascontiguousarray(faces, dtype="<i4")
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        f"element vertex {v.shape[0]}\n"
        "property float x\nproperty float y\nproperty float z\n"
        f"element face {f.shape[0]}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    ).encode("ascii")
    body = io.BytesIO()
    body.write(header)
    body.write(v.tobytes())
    counts = np.full((f.shape[0], 1), 3, dtype="<u1")
    for chunk in range(0, f.shape[0], 200_000):
        stop = min(chunk + 200_000, f.shape[0])
        body.write(np.hstack([counts[chunk:stop].view("<u1"), f[chunk:stop].view("<u1")]).tobytes())
    return body.getvalue()


def split_mesh_by_class(
    vertices: np.ndarray,
    faces: np.ndarray,
    face_class: np.ndarray,
    class_names: tuple[str, ...],
) -> dict[str, bytes]:
    """One PLY per surface class, because Sionna binds material per shape.

    MONOSTATIC_SBR.md section 10.1 lists this as the reason Sionna cannot carry
    the per texel roughness posterior. For a cross check against the four class
    geometric binding it costs four shapes and nothing else.
    """
    out: dict[str, bytes] = {}
    for index, name in enumerate(class_names):
        selected = faces[np.asarray(face_class) == index]
        if selected.size == 0:
            continue
        used = np.unique(selected)
        remap = np.full(int(np.asarray(vertices).shape[0]), -1, dtype=np.int64)
        remap[used] = np.arange(used.size)
        out[name] = write_ply(np.asarray(vertices)[used], remap[selected])
    return out


def build_scene(
    ply_bytes: dict[str, bytes],
    permittivity: dict[str, complex],
    scattering: dict[str, float],
    frequency_hz: float,
    *,
    cache_dir: pathlib.Path,
    thickness_m: float = SLAB_THICKNESS_M,
) -> Any:
    """A Sionna scene over the same triangles, one shape and one material per class."""
    import mitsuba as mi
    import sionna.rt as rt

    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    description: dict[str, Any] = {"type": "scene"}
    for name, payload in ply_bytes.items():
        path = cache_dir / f"{name}.ply"
        if not path.exists() or path.stat().st_size != len(payload):
            path.write_bytes(payload)
        eta = complex(permittivity[name])
        description[f"obj-{name}"] = {
            "type": "ply",
            "filename": str(path),
            "face_normals": True,
            "bsdf": {
                "type": "radio-material",
                "id": f"mat-{name}",
                "thickness": float(thickness_m),
                "relative_permittivity": float(eta.real),
                "conductivity": float(conductivity_from_permittivity(np.array([eta]), frequency_hz)[0]),
                "scattering_coefficient": float(scattering[name]),
            },
        }
    scene = rt.Scene(mi.load_dict(description))
    scene.frequency = float(frequency_hz)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="cross")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="cross")
    return scene


def scene_transfer(
    scene: Any,
    origin: np.ndarray,
    directions: np.ndarray,
    *,
    range_m: float = SOURCE_RANGE_M,
    max_depth: int = 4,
    samples_per_src: int = 100_000,
    diffuse: bool = False,
    diffraction: bool = False,
    seed: int = 1,
    target_chunk: int = 128,
    max_num_paths_per_src: int = 4_000_000,
) -> dict[str, np.ndarray]:
    """``T(u_s)`` at each direction, split into its zero interaction part and the rest.

    The split is not cosmetic. Both tools read the same triangles through the
    same Mitsuba BVH, so the line of sight term is a shared computation and
    agreement on it says nothing about the transport. ``multipath`` is where the
    implementations are independent.
    """
    import sionna.rt as rt

    origin = np.asarray(origin, dtype=np.float64)
    directions = np.asarray(directions, dtype=np.float64)
    reference = free_space_reference(range_m, SPEED_OF_LIGHT_M_S / float(scene.frequency))
    solver = rt.PathSolver()
    total = np.zeros(directions.shape[0])
    direct = np.zeros(directions.shape[0])

    for start in range(0, directions.shape[0], target_chunk):
        stop = min(start + target_chunk, directions.shape[0])
        for name in list(scene.transmitters):
            scene.remove(name)
        for name in list(scene.receivers):
            scene.remove(name)
        scene.add(rt.Transmitter("tx", position=[float(v) for v in origin]))
        for i in range(start, stop):
            position = origin + float(range_m) * directions[i]
            scene.add(rt.Receiver(f"rx{i}", position=[float(v) for v in position]))
        paths = solver(
            scene,
            max_depth=int(max_depth),
            los=True,
            specular_reflection=True,
            diffuse_reflection=bool(diffuse),
            refraction=False,
            diffraction=bool(diffraction),
            samples_per_src=int(samples_per_src),
            max_num_paths_per_src=int(max_num_paths_per_src),
            synthetic_array=True,
            seed=int(seed),
        )
        real, imaginary = paths.a
        amplitude = np.asarray(real) + 1j * np.asarray(imaginary)
        power = 0.5 * (np.abs(amplitude) ** 2).sum(axis=(1, 3))[:, 0, :] / reference
        interactions = np.asarray(paths.interactions)
        line_of_sight = np.all(interactions == 0, axis=0) if interactions.ndim == 3 else interactions == 0
        total[start:stop] = power.sum(axis=1)
        direct[start:stop] = np.where(line_of_sight[:, 0, :], power, 0.0).sum(axis=1)

    return {"total": total, "direct": direct, "multipath": total - direct}


# ---------------------------------------------------------------------------
# Running the oracle somewhere with a GPU
# ---------------------------------------------------------------------------

#: Everything the oracle needs to answer, as one serialisable dictionary. The
#: worker imports nothing from this package, so the same payload runs locally,
#: in a container, or on a rented GPU with no source tree behind it.
PAYLOAD_KEYS = (
    "ply",
    "permittivity",
    "scattering",
    "frequency_hz",
    "origins",
    "directions",
    "range_m",
    "max_depth",
    "samples_per_src",
    "diffuse",
    "diffraction",
    "seed",
    "target_chunk",
)


def build_payload(
    ply_bytes: dict[str, bytes],
    permittivity: dict[str, complex],
    scattering: dict[str, float],
    frequency_hz: float,
    origins: np.ndarray,
    directions: np.ndarray,
    **options: Any,
) -> dict[str, Any]:
    """Pack one site, one mode and every standpoint into a single remote call."""
    import gzip

    payload: dict[str, Any] = {
        "ply": {name: gzip.compress(data, 6) for name, data in ply_bytes.items()},
        "permittivity": {name: [float(complex(v).real), float(complex(v).imag)] for name, v in permittivity.items()},
        "scattering": {name: float(v) for name, v in scattering.items()},
        "frequency_hz": float(frequency_hz),
        "origins": np.asarray(origins, dtype=np.float64).tolist(),
        "directions": np.asarray(directions, dtype=np.float64).tolist(),
        "range_m": float(options.get("range_m", SOURCE_RANGE_M)),
        "max_depth": int(options.get("max_depth", 4)),
        "samples_per_src": int(options.get("samples_per_src", 100_000)),
        "diffuse": bool(options.get("diffuse", False)),
        "diffraction": bool(options.get("diffraction", False)),
        "seed": int(options.get("seed", 1)),
        "target_chunk": int(options.get("target_chunk", 128)),
        "max_num_paths_per_src": int(options.get("max_num_paths_per_src", 16_000_000)),
    }
    return payload


def run_payload(payload: dict[str, Any], workdir: str | None = None) -> dict[str, Any]:
    """Answer one payload. Self contained, so it can run inside a Modal container.

    Deliberately imports only numpy, Sionna and the standard library, and inlines
    the two dozen lines of scene construction rather than importing them, because
    a worker that needs this repository on its path is a worker that cannot be
    rented.
    """
    import gzip
    import pathlib as _pathlib
    import tempfile
    import time

    import mitsuba as mi
    import numpy as np  # noqa: F811
    import sionna.rt as rt

    started = time.perf_counter()
    root = _pathlib.Path(workdir or tempfile.mkdtemp())
    root.mkdir(parents=True, exist_ok=True)
    speed_of_light = 299_792_458.0
    vacuum_permittivity = 8.8541878128e-12
    frequency = float(payload["frequency_hz"])

    description: dict[str, Any] = {"type": "scene"}
    for name, blob in payload["ply"].items():
        path = root / f"{name}.ply"
        path.write_bytes(gzip.decompress(blob))
        real, imaginary = payload["permittivity"][name]
        description[f"obj-{name}"] = {
            "type": "ply",
            "filename": str(path),
            "face_normals": True,
            "bsdf": {
                "type": "radio-material",
                "id": f"mat-{name}",
                "thickness": SLAB_THICKNESS_M,
                "relative_permittivity": float(real),
                "conductivity": float(-imaginary * 2.0 * np.pi * frequency * vacuum_permittivity),
                "scattering_coefficient": float(payload["scattering"][name]),
            },
        }
    scene = rt.Scene(mi.load_dict(description))
    scene.frequency = frequency
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="cross")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="cross")

    origins = np.asarray(payload["origins"], dtype=np.float64)
    directions = np.asarray(payload["directions"], dtype=np.float64)
    range_m = float(payload["range_m"])
    reference = (speed_of_light / frequency / (4.0 * np.pi * range_m)) ** 2
    solver = rt.PathSolver()
    chunk = int(payload["target_chunk"])

    total = np.zeros((origins.shape[0], directions.shape[0]))
    direct = np.zeros((origins.shape[0], directions.shape[0]))
    # Sionna's path buffer is a fixed allocation per source, and a diffuse run
    # writes one path per shot ray per target into it. Overflowing it does not
    # raise, it silently drops paths, and on the dielectric plane it cost a
    # clean factor of four in the scattered power while still looking like a
    # smooth function of elevation. The high water mark comes back with the
    # answer so the caller can refuse a saturated run rather than publish it.
    high_water = 0
    for location, origin in enumerate(origins):
        for start in range(0, directions.shape[0], chunk):
            stop = min(start + chunk, directions.shape[0])
            for name in list(scene.transmitters):
                scene.remove(name)
            for name in list(scene.receivers):
                scene.remove(name)
            scene.add(rt.Transmitter("tx", position=[float(v) for v in origin]))
            for i in range(start, stop):
                position = origin + range_m * directions[i]
                scene.add(rt.Receiver(f"rx{i}", position=[float(v) for v in position]))
            paths = solver(
                scene,
                max_depth=int(payload["max_depth"]),
                los=True,
                specular_reflection=True,
                diffuse_reflection=bool(payload["diffuse"]),
                refraction=False,
                diffraction=bool(payload["diffraction"]),
                samples_per_src=int(payload["samples_per_src"]),
                max_num_paths_per_src=int(payload["max_num_paths_per_src"]),
                synthetic_array=True,
                seed=int(payload["seed"]) + location,
            )
            real_part, imaginary_part = paths.a
            amplitude = np.asarray(real_part) + 1j * np.asarray(imaginary_part)
            power = 0.5 * (np.abs(amplitude) ** 2).sum(axis=(1, 3))[:, 0, :] / reference
            interactions = np.asarray(paths.interactions)
            if interactions.ndim == 4:
                line_of_sight = np.all(interactions == 0, axis=0)[:, 0, :]
            else:
                line_of_sight = np.all(interactions == 0, axis=0)
            total[location, start:stop] = power.sum(axis=1)
            direct[location, start:stop] = np.where(line_of_sight, power, 0.0).sum(axis=1)
            high_water = max(high_water, int(np.asarray(paths.valid).sum()))

    return {
        "total": total.tolist(),
        "direct": direct.tolist(),
        "seconds": time.perf_counter() - started,
        "variant": mi.variant(),
        "paths_high_water": high_water,
        "max_num_paths_per_src": int(payload["max_num_paths_per_src"]),
    }


def modal_app(gpu: str = "L4", timeout_s: int = 7200) -> tuple[Any, Any]:
    """The Modal app and the remote entry point, built on demand.

    The paper's own box is four shared cores. Sionna is a GPU tool wearing a CPU
    fallback, and the shoot and bounce candidate generator connects every
    interaction point to every target, so the cost is the product of ray count,
    depth and sky sample count. That product is what a rented L4 is for.
    """
    import sys

    import modal
    from modal._vendor import cloudpickle

    # The container has Sionna and numpy and nothing else. `run_payload` is
    # written to need nothing else either, so registering this module for by
    # value pickling ships the worker itself rather than an import of it. Modal
    # vendors its own cloudpickle and serialises with that one, so the
    # registration has to happen in the vendored copy's registry.
    cloudpickle.register_pickle_by_value(sys.modules[run_payload.__module__])

    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install("libgl1", "libglib2.0-0")
        .pip_install("sionna-rt>=2.0,<3.0", "numpy<3", "scipy")
    )
    app = modal.App("semantic-twin-cross-validation")
    worker = run_payload

    @app.function(image=image, gpu=gpu, timeout=timeout_s, serialized=True, max_containers=4)
    def solve(payload: dict) -> dict:
        return worker(payload, workdir="/tmp/scene")

    return app, solve


# ---------------------------------------------------------------------------
# Convergence, which turns two parameters into two measurements
# ---------------------------------------------------------------------------


def recorded_susceptibility(
    record: Any,
    models: dict[str, IlluminationModel],
    local_grid: np.ndarray,
    *,
    throughput_floor: float = 0.0,
) -> dict[str, float]:
    """Rebuild ``chi`` from a ``PathRecorder`` polyline dump, optionally pruned.

    With Russian roulette disabled the throughput of a ray is monotonically non
    increasing, because every interaction multiplies it by a power reflectance
    at most one. Killing a ray the moment it falls below a floor is therefore
    exactly the same set of deposits as keeping only the escaping rays whose
    final throughput clears the floor, which makes the dynamic range prune a
    post hoc filter on a single trace rather than one trace per threshold. That
    equivalence is what makes the `D` curve affordable, and it is only valid
    with roulette off, so the caller has to arrange that.

    The estimator rebuilt here is (6) of PAPER_METHODS, cell counts and all, not
    the flat `(4 pi / N)` form, so it reproduces the production number rather
    than an equivalent one.
    """
    from .directions import nearest_cell

    offsets = np.asarray(record.offsets)
    vertices = np.asarray(record.vertices)
    throughput = np.asarray(record.throughput)
    termination = np.asarray(record.termination)
    exit_direction = np.asarray(record.exit_direction)

    first = offsets[:-1]
    last = offsets[1:] - 1
    departure = vertices[first + 1] - vertices[first]
    norms = np.linalg.norm(departure, axis=1, keepdims=True)
    departure = departure / np.where(norms > 0.0, norms, 1.0)
    cell = nearest_cell(departure, local_grid)
    final = throughput[last]

    escaped = termination == 0
    kept = escaped & (final >= float(throughput_floor))
    counts = np.zeros(local_grid.shape[0])
    np.add.at(counts, cell, 1.0)
    counts = np.maximum(counts, 1.0)
    solid_angle = 4.0 * np.pi / local_grid.shape[0]

    out: dict[str, float] = {}
    for name, model in models.items():
        normalisation = model.normalisation()
        rho = np.zeros(local_grid.shape[0])
        contribution = np.where(kept, final * model.density(exit_direction, normalisation), 0.0)
        np.add.at(rho, cell, contribution)
        out[name] = float(np.sum(rho / counts) * solid_angle)
    return out


def bounce_curve(
    geometry: Any,
    face_class: np.ndarray,
    permittivity: np.ndarray,
    rms_height_m: np.ndarray,
    points: np.ndarray,
    models: dict[str, IlluminationModel],
    *,
    frequency_hz: float,
    depths: tuple[int, ...] = (1, 2, 3, 4, 5, 6),
    rays: int = 200_000,
    local_cells: int = 512,
    seed: int = 7,
) -> dict[str, Any]:
    """``chi`` at each interaction depth, roulette off, on a set of standpoints.

    Section 9.1 of MONOSTATIC_SBR.md asks for the roulette disabled, and the
    reason is not bias. Russian roulette is unbiased, so it cannot move the
    expectation of ``chi``, but it converts the deep bounce tail from a small
    deterministic term into a rare large one, and a variance that grows with
    depth is exactly what would let a systematic drift hide inside the error
    bars of a convergence table. Disabling it makes the ``L`` to ``L+1`` step
    the only thing that moves between two runs sharing a seed.
    """
    from .tracer import SbrTracer, TraceConfig

    values = {name: np.zeros((points.shape[0], len(depths))) for name in models}
    for column, depth in enumerate(depths):
        config = TraceConfig(
            frequency_hz=frequency_hz,
            rays=rays,
            local_cells=local_cells,
            max_bounces=int(depth),
            roulette_start=int(depth) + 1,
            seed=seed,
        )
        tracer = SbrTracer(geometry, face_class, permittivity, rms_height_m, config)
        for row, point in enumerate(points):
            result = tracer.trace(point, models, seed=seed + row)
            for name in models:
                values[name][row, column] = result.susceptibility[name]
    return {"depths": list(depths), "chi": {name: values[name].tolist() for name in models}}


def dynamic_range_curve(
    geometry: Any,
    face_class: np.ndarray,
    permittivity: np.ndarray,
    rms_height_m: np.ndarray,
    points: np.ndarray,
    models: dict[str, IlluminationModel],
    *,
    frequency_hz: float,
    thresholds_db: tuple[float, ...] = (5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0, 60.0),
    max_bounces: int = DEFAULT_MAX_BOUNCES,
    rays: int = 100_000,
    local_cells: int = 512,
    seed: int = 7,
) -> dict[str, Any]:
    """``chi`` retained as a function of the throughput floor, on one trace per point.

    The floor is referenced to the strongest component a standpoint can have,
    which in this estimator is unambiguous: a ray that escapes without touching
    anything carries throughput exactly 1, and no ray can ever carry more. So
    ``D`` dB below the strongest component is the floor ``10^(-D/10)`` on the
    throughput, and no per location renormalisation is needed.
    """
    from .tracer import PathRecorder, SbrTracer, TraceConfig

    config = TraceConfig(
        frequency_hz=frequency_hz,
        rays=rays,
        local_cells=local_cells,
        max_bounces=int(max_bounces),
        roulette_start=int(max_bounces) + 1,
        seed=seed,
        batch=rays,
    )
    tracer = SbrTracer(geometry, face_class, permittivity, rms_height_m, config)
    values = {name: np.zeros((points.shape[0], len(thresholds_db))) for name in models}
    reference = {name: np.zeros(points.shape[0]) for name in models}
    for row, point in enumerate(points):
        recorder = PathRecorder(capacity=rays)
        result = tracer.trace(point, models, seed=seed + row, recorder=recorder)
        record = recorder.result()
        for name in models:
            reference[name][row] = result.susceptibility[name]
        for column, threshold in enumerate(thresholds_db):
            pruned = recorded_susceptibility(
                record,
                models,
                tracer.local_grid,
                throughput_floor=10.0 ** (-float(threshold) / 10.0),
            )
            for name in models:
                values[name][row, column] = pruned[name]
    return {
        "thresholds_db": list(thresholds_db),
        "chi": {name: values[name].tolist() for name in models},
        "chi_unpruned": {name: reference[name].tolist() for name in models},
    }


def median_change_db(values: np.ndarray) -> np.ndarray:
    """Absolute change in dB between consecutive columns, median over rows."""
    values = np.asarray(values, dtype=np.float64)
    ratio = values[:, 1:] / np.where(values[:, :-1] > 0.0, values[:, :-1], np.nan)
    return np.nanmedian(np.abs(10.0 * np.log10(ratio)), axis=0)


def smallest_converged(change_db: np.ndarray, first: int, threshold: float = 0.5) -> int | None:
    """Smallest parameter value whose step to the next one is under ``threshold`` dB."""
    for offset, value in enumerate(np.asarray(change_db)):
        if float(value) < float(threshold):
            return first + offset
    return None


# ---------------------------------------------------------------------------
# The study
# ---------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "cross_validation"

#: Korenmarkt is the site every other result in this paper is anchored on.
#: Brussels Grand Place is the deepest canyon in the eleven and the site whose
#: susceptibility is most sensitive to the illumination range cap, so if the two
#: tools are going to part company anywhere it is there.
STUDY_SITES = ("korenmarkt", "brussels_grandplace")

#: Where the published 250 m runs live, and the tag they carry. The comparison
#: reads its standpoints and its estimator side from these rather than
#: regenerating them, so what is being cross validated is the run the paper
#: reports and not a re-derivation of it.
PRODUCTION_DIR = ROOT / "outputs" / "exposure_korenmarkt"
PRODUCTION_TAG = "city250_corrected"


def site_mesh(site: str, crop_m: int) -> pathlib.Path:
    for name in (f"inhouse_leaf_{crop_m}m_f64.ply", f"inhouse_leaf_{crop_m}m.ply"):
        candidate = ROOT / "data" / "geometry" / site / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no {crop_m} m mesh for {site}")


def load_site(site: str, crop_m: int, frequency_hz: float, *, variant: str) -> dict[str, Any]:
    """Geometry, the four class geometric binding, and the production standpoints.

    The geometric binding is used at both sites rather than Korenmarkt's
    panorama semantics, for two reasons that point the same way: only Korenmarkt
    has semantics at all, so a semantic run could not be repeated at the second
    site, and section 9.3 of PAPER_METHODS already measures that swapping the
    semantics for the geometric rule moves the answer far less than the spread
    this comparison is trying to resolve.
    """
    import json

    from .geometry import MitsubaGeometry
    from .scene import CLASS_NAMES, classify_faces, load_bindings

    manifest = json.loads((PRODUCTION_DIR / f"{PRODUCTION_TAG}_{site}_15ghz_manifest.json").read_text())
    rows = [
        json.loads(line)
        for line in (PRODUCTION_DIR / f"{PRODUCTION_TAG}_{site}_15ghz_locations.jsonl").read_text().splitlines()
        if line.strip()
    ]
    if manifest["semantic_binding"]["materials"] != "geometric":
        raise ValueError(f"{site} was published with {manifest['semantic_binding']['materials']!r} materials")
    if manifest["crop_radius_m"] != crop_m:
        raise ValueError(f"{site} was published at {manifest['crop_radius_m']} m, not {crop_m} m")

    geometry = MitsubaGeometry(site_mesh(site, crop_m), variant=variant)
    if int(geometry.face_count) != int(manifest["mesh_triangles"]):
        raise ValueError("the mesh on disk is not the one the published run used")
    datum = float(manifest["ground_datum_m"])
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_bindings(ROOT / "config", frequency_hz)
    return {
        "geometry": geometry,
        "face_class": face_class,
        "binding": binding,
        "class_names": CLASS_NAMES,
        "ground_datum_m": datum,
        "rows": rows,
        "trace_config": manifest["trace_config"],
        "mesh": str(site_mesh(site, crop_m)),
    }


def _standpoints(rows: list[dict[str, Any]], count: int) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """``count`` of the published standpoints, spread evenly through the set of 80.

    Taking the standpoints from the published run rather than rebuilding the
    walk does two things at once. It removes any chance of the comparison
    landing on a different set of points than the paper reports, and it carries
    each point's published `chi` along with it, so the estimator half of the
    comparison can be checked against the number that is actually in the paper
    instead of only against a fresh trace of the same code.
    """
    picks = np.unique(np.linspace(0, len(rows) - 1, count).round().astype(int))
    chosen = [rows[i] for i in picks]
    points = np.array([[row["x"], row["y"], row["z"]] for row in chosen])
    return points, np.array([row["index"] for row in chosen]), chosen


def tracer_reference(
    geometry: Any,
    face_class: np.ndarray,
    permittivity: np.ndarray,
    rms_height_m: np.ndarray,
    points: np.ndarray,
    models: dict[str, IlluminationModel],
    *,
    frequency_hz: float,
    rays: int,
    max_bounces: int,
    walk_index: np.ndarray | None = None,
    local_cells: int = 512,
    seed: int = 7,
) -> dict[str, Any]:
    """The estimator's own answer at the same standpoints, split the same way.

    ``walk_index`` reproduces the published per location seed, ``seed + 1000 *
    index``, so a `production` mode run here is the published run at the same
    standpoints rather than an independent redraw. It is not bit identical to it:
    the published manifest starts Russian roulette at interaction 3 and
    ``TraceConfig`` now starts it at 4, so the ray streams diverge wherever
    roulette fires. The measured gap is reported in CROSS_VALIDATION.md section
    6.4 and is 0.001 dB isotropic.
    """
    from .tracer import SbrTracer, TraceConfig

    config = TraceConfig(
        frequency_hz=frequency_hz,
        rays=rays,
        local_cells=local_cells,
        max_bounces=max_bounces,
        seed=seed,
    )
    tracer = SbrTracer(geometry, face_class, permittivity, rms_height_m, config)
    total = {name: [] for name in models}
    direct = {name: [] for name in models}
    profile = []
    scalars = []
    for row, point in enumerate(points):
        offset = int(walk_index[row]) if walk_index is not None else row
        result = tracer.trace(point, models, seed=seed + 1000 * offset)
        for name in models:
            total[name].append(result.susceptibility[name])
            direct[name].append(result.susceptibility_direct[name])
        profile.append(result.exit_profile.tolist())
        scalars.append(result.scalars())
    return {
        "total": {name: total[name] for name in models},
        "direct": {name: direct[name] for name in models},
        "exit_profile": profile,
        "exit_sin_edges": tracer.exit_sin_edges.tolist(),
        "scalars": scalars,
        "trace_config": config.as_dict(),
    }


def compare(
    site: str,
    *,
    modes: tuple[str, ...] = MODES,
    crop_m: int = 250,
    frequency_hz: float = 15.0e9,
    locations: int = 8,
    sky_samples: int = 900,
    rays: int = 200_000,
    max_depth: int = 4,
    samples_per_src: int = 200_000,
    target_chunk: int = 32,
    max_num_paths_per_src: int = 16_000_000,
    seed: int = 7,
    variant: str = "llvm_ad_rgb",
    gpu: str = "L4",
    local: bool = False,
    diffraction: bool = False,
) -> pathlib.Path:
    """Run both tools at one site and write the comparison."""
    import json
    import time

    from .directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    site_data = load_site(site, crop_m, frequency_hz, variant=variant)
    geometry = site_data["geometry"]
    face_class = site_data["face_class"]
    binding = site_data["binding"]
    class_names = site_data["class_names"]
    points, picks, published = _standpoints(site_data["rows"], locations)
    wavelength = SPEED_OF_LIGHT_M_S / frequency_hz

    rng = np.random.default_rng(seed)
    sky = sample_sky(models, sky_samples, rng)
    ply = split_mesh_by_class(geometry.vertices, geometry.faces, face_class, class_names)
    permittivity = {name: complex(binding.permittivity[i]) for i, name in enumerate(class_names) if name in ply}

    report: dict[str, Any] = {
        "site": site,
        "mesh": site_data["mesh"],
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "frequency_hz": frequency_hz,
        "ground_datum_m": site_data["ground_datum_m"],
        "standpoints": points.tolist(),
        "standpoint_walk_index": picks.tolist(),
        "published_trace_config": site_data["trace_config"],
        "published_chi": [{name: row[f"chi_{name}"] for name in models} for row in published],
        "sky_samples": int(sky_samples),
        "sky_directions": sky.directions.tolist(),
        "source_range_m": SOURCE_RANGE_M,
        "slab_thickness_m": SLAB_THICKNESS_M,
        "sionna": {"max_depth": max_depth, "samples_per_src": samples_per_src, "diffraction": diffraction},
        "surface_binding": binding.as_dict(),
        "class_names": list(class_names),
        "modes": {},
    }

    remote = None
    context = None
    if not local:
        app, remote = modal_app(gpu=gpu)
        context = app.run()
        context.__enter__()
    try:
        for mode in modes:
            rms, scattering_by_class = mode_materials(mode, binding.rms_height_m, wavelength)
            scattering = {name: float(scattering_by_class[i]) for i, name in enumerate(class_names) if name in ply}
            started = time.perf_counter()
            payload = build_payload(
                ply,
                permittivity,
                scattering,
                frequency_hz,
                points,
                sky.directions,
                range_m=SOURCE_RANGE_M,
                max_depth=max_depth,
                samples_per_src=samples_per_src,
                diffuse=mode != "specular",
                diffraction=diffraction,
                seed=seed,
                target_chunk=target_chunk,
                max_num_paths_per_src=max_num_paths_per_src,
            )
            if remote is None:
                answer = run_payload(payload)
            else:
                answer = remote.remote(payload)
            oracle_total = np.asarray(answer["total"])
            oracle_direct = np.asarray(answer["direct"])
            saturated = answer["paths_high_water"] >= answer["max_num_paths_per_src"]
            print(
                f"[{site}/{mode}] oracle {answer['seconds']:.0f}s on {answer['variant']}, "
                f"paths {answer['paths_high_water']}/{answer['max_num_paths_per_src']}"
                f"{' SATURATED' if saturated else ''}",
                flush=True,
            )
            if saturated:
                raise RuntimeError(
                    f"{site}/{mode}: Sionna's path buffer saturated, so paths were silently dropped. "
                    "Lower target_chunk or samples_per_src, or raise max_num_paths_per_src."
                )

            ours = tracer_reference(
                geometry,
                face_class,
                binding.permittivity,
                rms,
                points,
                models,
                frequency_hz=frequency_hz,
                rays=rays,
                max_bounces=max_depth,
                walk_index=picks,
                seed=seed,
            )
            print(f"[{site}/{mode}] estimator {time.perf_counter() - started:.0f}s total", flush=True)

            per_location = []
            for row in range(points.shape[0]):
                chi_total = susceptibility(oracle_total[row], sky)
                chi_direct = susceptibility(oracle_direct[row], sky)
                chi_multipath = susceptibility(oracle_total[row] - oracle_direct[row], sky)
                profile, profile_error = band_transfer(
                    oracle_total[row], sky, np.asarray(ours["exit_sin_edges"], dtype=np.float64)
                )
                per_location.append(
                    {
                        "oracle_chi": {k: v[0] for k, v in chi_total.items()},
                        "oracle_chi_stderr": {k: v[1] for k, v in chi_total.items()},
                        "oracle_chi_direct": {k: v[0] for k, v in chi_direct.items()},
                        "oracle_chi_multipath": {k: v[0] for k, v in chi_multipath.items()},
                        "oracle_chi_multipath_stderr": {k: v[1] for k, v in chi_multipath.items()},
                        "oracle_exit_profile": profile.tolist(),
                        "oracle_exit_profile_stderr": profile_error.tolist(),
                        "ours_chi": {name: ours["total"][name][row] for name in models},
                        "ours_chi_direct": {name: ours["direct"][name][row] for name in models},
                        "ours_chi_multipath": {
                            name: ours["total"][name][row] - ours["direct"][name][row] for name in models
                        },
                        "ours_exit_profile": ours["exit_profile"][row],
                        "ours_scalars": ours["scalars"][row],
                        "published_chi": {name: published[row][f"chi_{name}"] for name in models},
                        # Kept raw so the scalar can be reopened. A cross
                        # validation that only stores the summary cannot be
                        # asked afterwards which directions caused a
                        # disagreement, and that is the question a disagreement
                        # immediately raises.
                        "oracle_transfer": oracle_total[row].tolist(),
                        "oracle_transfer_direct": oracle_direct[row].tolist(),
                    }
                )
            report["modes"][mode] = {
                "tracer_rms_height_m": rms.tolist(),
                "sionna_scattering_coefficient": scattering,
                "oracle_seconds": answer["seconds"],
                "oracle_variant": answer["variant"],
                "oracle_paths_high_water": answer["paths_high_water"],
                "trace_config": ours["trace_config"],
                "exit_sin_edges": ours["exit_sin_edges"],
                "locations": per_location,
            }
    finally:
        if context is not None:
            context.__exit__(None, None, None)

    suffix = "_diffraction" if diffraction else ""
    path = OUTPUT / f"{site}_{crop_m}m_{frequency_hz / 1e9:g}ghz{suffix}.json"
    path.write_text(json.dumps(report, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def plane_harness(*, frequency_hz: float = 15.0e9, local: bool = False, gpu: str = "L4") -> pathlib.Path:
    """Three way check of the harness itself, before any city is touched.

    Both exactly matched modes have a closed form over a dielectric half space:
    the specular one is `1 + R(theta)`, and the fully diffuse one is
    `1 + 2 sin(alpha) times the mean of R over cos(theta)`, because a cosine lobe
    about the normal exits at elevation `alpha` with density `sin(alpha)/pi` and
    the departure hemisphere integrates uniformly in `cos(theta)`. If the oracle
    misses either target the city comparison is meaningless, so this runs first.
    """
    import json

    from .closed_form import ground_plane_susceptibility
    from .scene import load_bindings
    from .tracer import fresnel_power_reflectance

    OUTPUT.mkdir(parents=True, exist_ok=True)
    binding = load_bindings(ROOT / "config", frequency_hz)
    permittivity = complex(binding.permittivity[0])
    half = 3.0e3
    vertices = np.array([[-half, -half, 0.0], [half, -half, 0.0], [half, half, 0.0], [-half, half, 0.0]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    ply = {"ground": write_ply(vertices, faces)}
    elevation = np.array([2.0, 3.0, 5.0, 10.0, 20.0, 24.0, 30.0, 45.0, 60.0, 80.0])
    directions = np.column_stack(
        [np.cos(np.radians(elevation)), np.zeros_like(elevation), np.sin(np.radians(elevation))]
    )
    origin = np.array([[0.0, 0.0, 1.5]])

    cosine = np.linspace(0.0, 1.0, 20_001)
    mean_reflectance = float(
        np.trapezoid(fresnel_power_reflectance(cosine, np.full(cosine.shape, permittivity)), cosine)
    )
    targets = {
        "specular": ground_plane_susceptibility(elevation, permittivity),
        "diffuse": 1.0 + 2.0 * np.sin(np.radians(elevation)) * mean_reflectance,
    }

    out: dict[str, Any] = {
        "frequency_hz": frequency_hz,
        "permittivity": [permittivity.real, permittivity.imag],
        "mean_reflectance_over_cos": mean_reflectance,
        "elevation_deg": elevation.tolist(),
        "source_range_m": SOURCE_RANGE_M,
        "modes": {},
    }
    remote = None
    context = None
    if not local:
        app, remote = modal_app(gpu=gpu)
        context = app.run()
        context.__enter__()
    try:
        for mode, target in targets.items():
            payload = build_payload(
                ply,
                {"ground": permittivity},
                {"ground": 0.0 if mode == "specular" else 1.0},
                frequency_hz,
                origin,
                directions,
                max_depth=1,
                samples_per_src=500_000,
                target_chunk=int(directions.shape[0]),
                diffuse=mode != "specular",
                seed=3,
            )
            answer = run_payload(payload) if remote is None else remote.remote(payload)
            value = np.asarray(answer["total"])[0]
            residual = 10.0 * np.log10(value / target)
            out["modes"][mode] = {
                "closed_form": target.tolist(),
                "oracle": value.tolist(),
                "residual_db": residual.tolist(),
                "max_abs_residual_db": float(np.max(np.abs(residual))),
                "seconds": answer["seconds"],
                "variant": answer["variant"],
                "paths_high_water": answer["paths_high_water"],
                "max_num_paths_per_src": answer["max_num_paths_per_src"],
                "path_buffer_saturated": answer["paths_high_water"] >= answer["max_num_paths_per_src"],
            }
            print(f"[plane/{mode}] max |residual| {np.max(np.abs(residual)):.4f} dB", flush=True)
    finally:
        if context is not None:
            context.__exit__(None, None, None)

    path = OUTPUT / "plane_harness.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def jittered_plane(
    half_m: float,
    cell_m: float,
    jitter_m: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """A ground plane cut into ``cell_m`` quads with vertex heights jittered.

    One knob, one prediction. The surface stays a single valued height field of
    the same mean plane, so the power it returns upward is unchanged and any
    energy conserving estimator has to give the same answer for every jitter.
    """
    count = int(round(2.0 * half_m / cell_m)) + 1
    axis = np.linspace(-half_m, half_m, count)
    x, y = np.meshgrid(axis, axis, indexing="ij")
    z = rng.normal(0.0, jitter_m, size=x.shape) if jitter_m > 0.0 else np.zeros_like(x)
    vertices = np.column_stack([x.ravel(), y.ravel(), z.ravel()])
    index = np.arange(count * count).reshape(count, count)
    a = index[:-1, :-1].ravel()
    b = index[1:, :-1].ravel()
    c = index[1:, 1:].ravel()
    d = index[:-1, 1:].ravel()
    faces = np.concatenate([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    return vertices, faces


def tessellation_experiment(
    *,
    frequency_hz: float = 15.0e9,
    half_m: float = 200.0,
    cell_m: float = 1.0,
    jitters_m: tuple[float, ...] = (0.0, 0.001, 0.005, 0.02, 0.05, 0.2),
    rays: int = 200_000,
    samples_per_src: int = 200_000,
    sky_samples: int = 1500,
    seed: int = 5,
    local: bool = False,
    gpu: str = "L4",
    variant: str = "llvm_ad_rgb",
    tag: str = "",
) -> pathlib.Path:
    """Why the two tools part company on specular reflection, in one knob.

    A ground plane under the observer has an exact isotropic susceptibility,
    `0.5 + 0.5 <R>`, and the derivation is one line: half the departure sphere
    escapes unobstructed with unit throughput, the other half meets the plane
    once and comes back weighted by a reflectance averaged uniformly in
    `cos(theta)`, which is the measure the lower hemisphere carries. Roughening
    the plane by a height jitter cannot change it. The jitter redirects the
    reflected power, it does not create or destroy any, so long as the surface
    stays single valued and the shadowing it introduces is small.

    That makes the jitter a control the two tools have to be indifferent to, and
    the one that is not indifferent is the one adding energy. Sweeping it turns
    "the two disagree on the city mesh" into a mechanism with a number on it.
    """
    import json

    from .directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
    from .geometry import MitsubaGeometry
    from .scene import load_bindings
    from .tracer import SbrTracer, TraceConfig, fresnel_power_reflectance

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    binding = load_bindings(ROOT / "config", frequency_hz)
    permittivity = complex(binding.permittivity[0])
    cosine = np.linspace(0.0, 1.0, 20_001)
    mean_reflectance = float(
        np.trapezoid(fresnel_power_reflectance(cosine, np.full(cosine.shape, permittivity)), cosine)
    )
    target = 0.5 + 0.5 * mean_reflectance

    sky = sample_sky(models, sky_samples, np.random.default_rng(seed))
    origin = np.array([0.0, 0.0, 1.5])
    out: dict[str, Any] = {
        "frequency_hz": frequency_hz,
        "half_m": half_m,
        "cell_m": cell_m,
        "permittivity": [permittivity.real, permittivity.imag],
        "mean_reflectance_over_cos": mean_reflectance,
        "closed_form_chi_isotropic": target,
        "sky_samples": sky_samples,
        "rows": [],
    }

    remote = None
    context = None
    if not local:
        app, remote = modal_app(gpu=gpu)
        context = app.run()
        context.__enter__()
    try:
        for jitter in jitters_m:
            rng = np.random.default_rng(seed)
            vertices, faces = jittered_plane(half_m, cell_m, jitter, rng)
            cache = OUTPUT / "tessellation"
            cache.mkdir(parents=True, exist_ok=True)
            path = cache / f"plane_{jitter:g}.ply"
            path.write_bytes(write_ply(vertices, faces))

            geometry = MitsubaGeometry(path, variant=variant)
            row: dict[str, Any] = {
                "jitter_m": jitter,
                "triangles": int(faces.shape[0]),
                "facet_slope_noise_rad": float(jitter / cell_m),
                "ours": {},
                "oracle": {},
            }
            # Both branches, on the same triangles, at the same jitter. Running
            # only the specular one would leave "Sionna is wrong" and "the
            # harness is wrong" indistinguishable, and they are the two answers
            # that matter.
            for branch, tracer_rms, scattering in (
                ("specular", 0.0, 0.0),
                ("diffuse", FULLY_DIFFUSE_RMS_HEIGHT_M, 1.0),
            ):
                config = TraceConfig(
                    frequency_hz=frequency_hz, rays=rays, local_cells=512, max_bounces=1, roulette_start=2, seed=seed
                )
                tracer = SbrTracer(geometry, None, np.array([permittivity]), np.array([tracer_rms]), config)
                ours = tracer.trace(origin, models, seed=seed)
                payload = build_payload(
                    {"ground": write_ply(vertices, faces)},
                    {"ground": permittivity},
                    {"ground": scattering},
                    frequency_hz,
                    origin[None, :],
                    sky.directions,
                    max_depth=1,
                    samples_per_src=samples_per_src,
                    target_chunk=8 if branch == "diffuse" else 32,
                    diffuse=branch == "diffuse",
                    seed=seed,
                )
                answer = run_payload(payload) if remote is None else remote.remote(payload)
                transfer = np.asarray(answer["total"])[0]
                oracle = susceptibility(transfer, sky)
                row["ours"][branch] = {name: ours.susceptibility[name] for name in models}
                row["oracle"][branch] = {
                    "chi": {name: value[0] for name, value in oracle.items()},
                    "chi_stderr": {name: value[1] for name, value in oracle.items()},
                    "max_transfer": float(transfer.max()),
                    "paths_high_water": answer["paths_high_water"],
                    "saturated": answer["paths_high_water"] >= answer["max_num_paths_per_src"],
                }
                print(
                    f"[tessellation] jitter {jitter * 1000:7.2f} mm  {branch:9s} "
                    f"ours {row['ours'][branch]['isotropic']:8.4f}  "
                    f"oracle {row['oracle'][branch]['chi']['isotropic']:10.4f}  "
                    f"closed form {target:.4f}  max T {row['oracle'][branch]['max_transfer']:9.2f}",
                    flush=True,
                )
            out["rows"].append(row)
    finally:
        if context is not None:
            context.__exit__(None, None, None)

    path = OUTPUT / f"tessellation_experiment{tag}.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def sampling_convergence(
    *,
    frequency_hz: float = 15.0e9,
    half_m: float = 200.0,
    cell_m: float = 1.0,
    jitters_m: tuple[float, ...] = (0.0, 2.0e-4),
    budgets: tuple[int, ...] = (25_000, 50_000, 100_000, 200_000, 400_000, 800_000),
    sky_samples: int = 600,
    seed: int = 5,
    local: bool = False,
    gpu: str = "L4",
) -> pathlib.Path:
    """Does the oracle's specular answer depend on its own search budget?

    ``samples_per_src`` is the number of rays Sionna shoots to *find* candidate
    specular chains. It is a numerical budget and a converged physical answer
    cannot depend on it. This separates the two readings of section 5 of
    CROSS_VALIDATION.md that are otherwise hard to tell apart: a real multi facet
    effect converges as the budget grows, a candidate generation artifact that
    survives deduplication does not.
    """
    import json

    from .directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
    from .scene import load_bindings

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    binding = load_bindings(ROOT / "config", frequency_hz)
    permittivity = complex(binding.permittivity[0])
    sky = sample_sky(models, sky_samples, np.random.default_rng(seed))
    origin = np.array([0.0, 0.0, 1.5])
    out: dict[str, Any] = {
        "frequency_hz": frequency_hz,
        "half_m": half_m,
        "cell_m": cell_m,
        "sky_samples": sky_samples,
        "budgets": list(budgets),
        "rows": [],
    }

    remote = None
    context = None
    if not local:
        app, remote = modal_app(gpu=gpu)
        context = app.run()
        context.__enter__()
    try:
        for jitter in jitters_m:
            vertices, faces = jittered_plane(half_m, cell_m, jitter, np.random.default_rng(seed))
            ply = write_ply(vertices, faces)
            for budget in budgets:
                payload = build_payload(
                    {"ground": ply},
                    {"ground": permittivity},
                    {"ground": 0.0},
                    frequency_hz,
                    origin[None, :],
                    sky.directions,
                    max_depth=1,
                    samples_per_src=int(budget),
                    target_chunk=16,
                    diffuse=False,
                    seed=seed,
                )
                answer = run_payload(payload) if remote is None else remote.remote(payload)
                transfer = np.asarray(answer["total"])[0]
                row = {
                    "jitter_m": jitter,
                    "triangles": int(faces.shape[0]),
                    "samples_per_src": int(budget),
                    "oracle_chi": {name: value[0] for name, value in susceptibility(transfer, sky).items()},
                    "oracle_max_transfer": float(transfer.max()),
                    "paths_per_source": answer["paths_high_water"] / 16.0,
                    "saturated": answer["paths_high_water"] >= answer["max_num_paths_per_src"],
                }
                out["rows"].append(row)
                print(
                    f"[sampling] jitter {jitter * 1000:6.2f} mm  budget {budget:8d}  "
                    f"chi {row['oracle_chi']['isotropic']:10.4f}  maxT {row['oracle_max_transfer']:9.2f}  "
                    f"paths/src {row['paths_per_source']:9.1f}",
                    flush=True,
                )
    finally:
        if context is not None:
            context.__exit__(None, None, None)

    path = OUTPUT / "sampling_convergence.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def convergence(
    site: str,
    *,
    crop_m: int = 250,
    frequency_hz: float = 15.0e9,
    locations: int = 12,
    depths: tuple[int, ...] = (1, 2, 3, 4, 5, 6),
    bounce_rays: int = 200_000,
    range_rays: int = 100_000,
    max_bounces: int = DEFAULT_MAX_BOUNCES,
    seed: int = 7,
    variant: str = "llvm_ad_rgb",
) -> pathlib.Path:
    """The two curves of MONOSTATIC_SBR.md section 11, at one site."""
    import json

    from .directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    site_data = load_site(site, crop_m, frequency_hz, variant=variant)
    points, picks, _ = _standpoints(site_data["rows"], locations)
    binding = site_data["binding"]

    bounce = bounce_curve(
        site_data["geometry"],
        site_data["face_class"],
        binding.permittivity,
        binding.rms_height_m,
        points,
        models,
        frequency_hz=frequency_hz,
        depths=depths,
        rays=bounce_rays,
        seed=seed,
    )
    print(f"[{site}] bounce curve done", flush=True)
    prune = dynamic_range_curve(
        site_data["geometry"],
        site_data["face_class"],
        binding.permittivity,
        binding.rms_height_m,
        points,
        models,
        frequency_hz=frequency_hz,
        max_bounces=max_bounces,
        rays=range_rays,
        seed=seed,
    )
    print(f"[{site}] dynamic range curve done", flush=True)

    out = {
        "site": site,
        "crop_radius_m": crop_m,
        "frequency_hz": frequency_hz,
        "standpoints": points.tolist(),
        "standpoint_walk_index": picks.tolist(),
        "roulette": "disabled for both curves",
        "bounce": bounce,
        "dynamic_range": prune,
    }
    for name in models:
        change = median_change_db(np.asarray(bounce["chi"][name]))
        out.setdefault("bounce_median_change_db", {})[name] = change.tolist()
        out.setdefault("bounce_converged_L", {})[name] = smallest_converged(change, depths[0])
        retained = np.asarray(prune["chi"][name]) / np.asarray(prune["chi_unpruned"][name])[:, None]
        out.setdefault("retained_fraction_median", {})[name] = np.median(retained, axis=0).tolist()
        loss = -10.0 * np.log10(np.clip(np.median(retained, axis=0), 1.0e-12, None))
        out.setdefault("retained_loss_db_median", {})[name] = loss.tolist()

    path = OUTPUT / f"convergence_{site}_{crop_m}m.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    plane = sub.add_parser("plane", help="three way harness check on a dielectric half space")
    plane.add_argument("--local", action="store_true")
    plane.add_argument("--gpu", default="L4")

    site = sub.add_parser("site", help="cross validate one site")
    site.add_argument("--site", default="korenmarkt")
    site.add_argument("--crop-m", type=int, default=250)
    site.add_argument("--locations", type=int, default=8)
    site.add_argument("--sky-samples", type=int, default=900)
    site.add_argument("--rays", type=int, default=200_000)
    site.add_argument("--samples-per-src", type=int, default=200_000)
    site.add_argument("--target-chunk", type=int, default=32)
    site.add_argument("--max-paths", type=int, default=16_000_000)
    site.add_argument("--max-depth", type=int, default=4)
    site.add_argument("--modes", default=",".join(MODES))
    site.add_argument("--diffraction", action="store_true")
    site.add_argument("--local", action="store_true")
    site.add_argument("--gpu", default="L4")

    tess = sub.add_parser("tessellation", help="why the specular branches disagree, in one knob")
    tess.add_argument("--local", action="store_true")
    tess.add_argument("--gpu", default="L4")
    tess.add_argument("--cell-m", type=float, default=1.0)
    tess.add_argument("--sky-samples", type=int, default=1500)
    tess.add_argument("--jitters-mm", default="0,1,5,20,50,200")
    tess.add_argument("--tag", default="")

    budget = sub.add_parser("sampling", help="does the oracle depend on its own search budget")
    budget.add_argument("--local", action="store_true")
    budget.add_argument("--gpu", default="L4")
    budget.add_argument("--sky-samples", type=int, default=600)

    curve = sub.add_parser("convergence", help="bounce count and dynamic range curves")
    curve.add_argument("--site", default="korenmarkt")
    curve.add_argument("--crop-m", type=int, default=250)
    curve.add_argument("--locations", type=int, default=12)
    curve.add_argument("--bounce-rays", type=int, default=200_000)
    curve.add_argument("--range-rays", type=int, default=100_000)

    args = parser.parse_args(argv)
    if args.command == "plane":
        plane_harness(local=args.local, gpu=args.gpu)
    elif args.command == "tessellation":
        tessellation_experiment(
            local=args.local,
            gpu=args.gpu,
            cell_m=args.cell_m,
            sky_samples=args.sky_samples,
            jitters_m=tuple(float(v) * 1e-3 for v in args.jitters_mm.split(",")),
            tag=args.tag,
        )
    elif args.command == "sampling":
        sampling_convergence(local=args.local, gpu=args.gpu, sky_samples=args.sky_samples)
    elif args.command == "site":
        compare(
            args.site,
            modes=tuple(args.modes.split(",")),
            crop_m=args.crop_m,
            locations=args.locations,
            sky_samples=args.sky_samples,
            rays=args.rays,
            samples_per_src=args.samples_per_src,
            target_chunk=args.target_chunk,
            max_num_paths_per_src=args.max_paths,
            max_depth=args.max_depth,
            diffraction=args.diffraction,
            local=args.local,
            gpu=args.gpu,
        )
    else:
        convergence(
            args.site,
            crop_m=args.crop_m,
            locations=args.locations,
            bounce_rays=args.bounce_rays,
            range_rays=args.range_rays,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
