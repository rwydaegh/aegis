"""Bystanders: the other people standing in the square.

Everything else in this package traces a pedestrian who is alone. A real square
is not empty, and at 15 GHz a person is not a perturbation: a body is about
0.5 m across against a 20 mm wavelength, so it is 25 wavelengths wide and
optically opaque, with no diffraction path worth the name around it. Bystanders
are therefore geometry, and geometry changes the trace.

Two estimators live here, and they answer different questions.

``CompositeGeometry`` inserts the reconstructed SMPL-X bodies of
``outputs/korenmarkt_dynamic_bodies/`` into the traced scene as real triangles
with a skin material, so the crowd blocks, shadows and re-scatters exactly the
way the walls already do. This is expensive: every crowd realisation is a new
acceleration structure and a new trace.

``crowd_transmittance`` is the cheap one. Bodies are opaque vertical obstacles
whose centres are a Poisson field of intensity ``lambda`` on the ground, so the
survival probability of the final leg of a path leaving the observation point in
direction ``u`` is Beer-Lambert, ``exp(-lambda * <w * L(u)>)``, with ``w`` the
mean silhouette width of a body and ``L(u)`` the horizontal distance over which
that ray is low enough to be blocked. Multiplying an already traced ``rho`` by
that factor costs nothing and needs no re-trace. Two things it gets wrong, in
opposite directions, and which of them wins is the thing to measure: it
extinguishes the final leg only, so blockage of the earlier legs of a
multi-bounce path is missing and ``chi`` comes out too high, and it treats a
body as a perfect absorber, so the roughly half of the intercepted power that
skin reflects is thrown away and ``chi`` comes out too low.

The point of having both is that the second can be checked against the first
rather than believed.

The physical prediction, stated before it is measured. A bystander stands at the
observation point's own height, so what a crowd removes is the near-horizon
band and almost nothing else. The corrected illumination laws of
``directions.py`` put 87.9 % of the street small cell measure and 9.4 % of the
rooftop measure below 5 degrees of elevation, so crowd blockage should cost the
street column many decibels and the rooftop column very little.
"""

from __future__ import annotations

import gc
import importlib.metadata
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .geometry import INFINITY, MitsubaGeometry

#: Speed of light, for the skin permittivity conversion.
_EPS0 = 8.8541878128e-12

#: Square feet to square metres, exactly.
SQFT_M2 = 0.09290304

#: Fruin's walkway level of service, from J. J. Fruin, "Designing for
#: pedestrians: a level-of-service concept", Highway Research Record 355 (1971),
#: pp. 1-15. Fruin states each class as a pedestrian area module ``M`` in square
#: feet per pedestrian: A above 35, B 25 to 35, C 15 to 25, D 10 to 15, E 5 to
#: 10, F below 5. Density is ``1/M``, so the *lower* module edge of a class is
#: its crowded edge and is what is tabulated here.
#:
#: name -> (area module at the crowded edge in m2 per pedestrian, the density
#: that implies in pedestrians per m2).
FRUIN_WALKWAY_LOS: dict[str, tuple[float, float]] = {
    name: (module * SQFT_M2, 1.0 / (module * SQFT_M2))
    for name, module in (("A", 35.0), ("B", 25.0), ("C", 15.0), ("D", 10.0), ("E", 5.0))
}

#: The density ladder the study sweeps, in people per square metre. The top four
#: rungs are the Fruin class boundaries themselves, so the sweep is read against
#: a published scale rather than against round numbers. The bottom two sit
#: inside level of service A, where Fruin's description is that a pedestrian can
#: choose their own speed and avoid conflicts: 0.05 is an empty square and 0.15
#: an ordinary weekday one. The top rung, the E/F boundary, is where Fruin
#: reports a loss of control and a situation "more representative of a queuing
#: than a traffic flow situation", so it stands for a market stall queue or an
#: event crowd rather than for a square someone is walking across.
DENSITY_LADDER: tuple[float, ...] = (
    0.05,
    0.15,
    FRUIN_WALKWAY_LOS["A"][1],
    FRUIN_WALKWAY_LOS["C"][1],
    FRUIN_WALKWAY_LOS["D"][1],
    FRUIN_WALKWAY_LOS["E"][1],
)

#: RMS height of the sub-facet relief of a clothed person, in metres. This is a
#: prior and not a measurement: it stands for fabric weave and drape at the
#: centimetre scale, below the scale the decimated mesh resolves. At 15 GHz it
#: puts the Rayleigh coherent fraction at 0.21 for normal incidence and above
#: 0.9 beyond 70 degrees, so a body is mostly a diffuse scatterer face on and a
#: mirror at grazing. ``run_study`` reports the sensitivity to it.
CLOTHING_RMS_HEIGHT_M = 2.0e-3

#: Centre to centre hard core between two standing people, in metres. Fruin
#: measured a 2 ft (0.61 m) inter-person spacing adopted "intermittently and
#: only under the densest flow conditions", so 0.45 m is below anything he saw
#: and functions purely as a no-interpenetration rule.
MIN_SEPARATION_M = 0.45

#: Radius around the observation point kept clear of bystander centres. One body
#: ellipse plus one, so nobody is standing inside the observer.
EXCLUSION_RADIUS_M = 0.60

#: Control material for the ``--body-absorber`` run. Index matched to free space
#: and very slightly lossy, so the Fresnel reflectance is below 1e-6 away from
#: grazing and the tracer's throughput multiply kills any ray that lands on a
#: body. That is the traced equivalent of the Beer-Lambert arm's assumption that
#: a bystander is a perfect absorber, and it is the control that separates
#: extinction from re-illumination.
ABSORBER_PERMITTIVITY = complex(1.0, -1.0e-6)


def skin_permittivity(frequency_hz: float) -> complex:
    """Complex relative permittivity of skin, ITU sign convention.

    Read from the IT'IS database through AEGIS rather than tabulated here, so
    the body material in the scene and the body material in the dosimetry come
    from one source. Returns ``eps_r - j*sigma/(omega*eps0)``, negative
    imaginary part, matching ``fresnel_power_reflectance``.
    """
    from aegis.tissue import TissueModel

    tissue = TissueModel.from_database("Skin", frequency_hz)
    omega = 2.0 * np.pi * float(frequency_hz)
    return complex(tissue.eps_r, -tissue.sigma / (omega * _EPS0))


def mean_silhouette_width_m(vertices: np.ndarray) -> float:
    """Azimuth averaged silhouette width of a body, by Cauchy's formula.

    The mean width of a convex set equals its perimeter divided by pi, so the
    quantity a horizontally travelling ray sees, averaged over the direction it
    arrives from, is the perimeter of the convex hull of the body's footprint
    over pi. This is the ``w`` of the Beer-Lambert law and it is measured off
    the reconstructions rather than assumed.
    """
    from scipy.spatial import ConvexHull

    hull = ConvexHull(np.asarray(vertices, dtype=np.float64)[:, :2])
    loop = hull.points[hull.vertices]
    perimeter = float(np.sum(np.linalg.norm(np.diff(np.vstack([loop, loop[:1]]), axis=0), axis=1)))
    return perimeter / np.pi


def _load_decimator() -> tuple[Any, str]:
    """Load the one mesh decimator used by the bystander study."""
    try:
        import fast_simplification
    except ImportError as error:
        raise ModuleNotFoundError(
            "fast-simplification is required for body mesh decimation; "
            "the former voxel fallback did not preserve silhouette area"
        ) from error
    return fast_simplification, importlib.metadata.version("fast-simplification")


def _quadric_decimate(
    vertices: np.ndarray,
    faces: np.ndarray,
    target_faces: int,
    decimator: Any,
) -> tuple[np.ndarray, np.ndarray]:
    out_v, out_f = decimator.simplify(
        vertices.astype(np.float32), faces.astype(np.int32), target_count=int(target_faces)
    )
    return np.asarray(out_v, dtype=np.float64), np.asarray(out_f, dtype=np.int64)


def simplify(vertices: np.ndarray, faces: np.ndarray, target_faces: int) -> tuple[np.ndarray, np.ndarray]:
    """Decimate a body with the study's explicit quadric implementation.

    Blockage is a silhouette quantity, and the silhouette survives decimation
    far better than the surface does. Measured on the Korenmarkt bodies, going
    from 36 874 to 600 triangles moves the azimuth averaged projected area by
    0.5 % and the mean width by 1.5 %, which is well inside the spread of the
    reconstructions themselves. ``run_study`` records the figure for the library
    it actually used.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if faces.shape[0] <= target_faces:
        return vertices, faces
    decimator, _ = _load_decimator()
    return _quadric_decimate(vertices, faces, target_faces, decimator)


@dataclass(frozen=True)
class BodyLibrary:
    """Reconstructed people, recentred so a placement is a translation and a yaw.

    Each entry has its footprint centroid at the origin in xy and its lowest
    vertex at ``z = 0``, so placing one is ``R_z(yaw) @ v + [x, y, ground_z]``.
    """

    body_ids: tuple[str, ...]
    vertices: tuple[np.ndarray, ...]
    faces: tuple[np.ndarray, ...]
    stature_m: np.ndarray
    width_m: np.ndarray
    provenance: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.body_ids)

    @property
    def face_count(self) -> int:
        return int(sum(f.shape[0] for f in self.faces))

    def rescaled(self, statures_m: np.ndarray) -> BodyLibrary:
        """The same bodies scaled uniformly to the given standing heights.

        Uniform scaling, so the width scales with the height and the Cauchy
        width stays consistent with the silhouette. Used for the stature
        sensitivity, which matters more here than anywhere else in the study:
        upward blockage depth goes as ``h_body - h_observer`` and the
        observation point sits at 1.5 m, so a 1.55 m reconstruction and a 1.73 m
        adult differ by a factor of four in how deep a crowd they make.
        """
        statures = np.asarray(statures_m, dtype=np.float64)
        if statures.shape != self.stature_m.shape:
            raise ValueError("one target stature per body")
        scale = statures / self.stature_m
        return BodyLibrary(
            body_ids=self.body_ids,
            vertices=tuple(v * s for v, s in zip(self.vertices, scale, strict=True)),
            faces=self.faces,
            stature_m=statures,
            width_m=self.width_m * scale,
            provenance={**self.provenance, "rescaled_to_stature": True},
        )


def load_body_library(
    directory: str | pathlib.Path,
    *,
    target_faces: int = 600,
    min_stature_m: float = 1.0,
) -> BodyLibrary:
    """Load the placed SMPL-X bodies as a shape library.

    ``build_dynamic_bodies.py`` writes one npz per person carrying
    ``vertices_enu_m``, already floored onto the support mesh, so the stature
    and the pose are the reconstruction's own and only the position is
    discarded here.
    """
    directory = pathlib.Path(directory)
    manifest_path = directory / "dynamic_bodies_manifest.json"
    paths = sorted(p for p in directory.glob("*.npz"))
    if not paths:
        raise FileNotFoundError(f"no body reconstructions in {directory}")
    ids: list[str] = []
    verts: list[np.ndarray] = []
    faces: list[np.ndarray] = []
    statures: list[float] = []
    widths: list[float] = []
    full_faces = 0
    silhouette_before: list[float] = []
    silhouette_after: list[float] = []
    decimator: Any | None = None
    decimator_version: str | None = None
    decimated_bodies = 0
    for path in paths:
        with np.load(path, allow_pickle=False) as document:
            if "vertices_enu_m" not in document.files:
                continue
            v = np.asarray(document["vertices_enu_m"], dtype=np.float64)
            f = np.asarray(document["faces"], dtype=np.int64)
        stature = float(np.ptp(v[:, 2]))
        if stature < min_stature_m:
            continue
        full_faces += f.shape[0]
        silhouette_before.append(projected_area_m2(v, f))
        if f.shape[0] > target_faces:
            if decimator is None:
                decimator, decimator_version = _load_decimator()
            v, f = _quadric_decimate(v, f, target_faces, decimator)
            decimated_bodies += 1
        v = v - np.array([v[:, 0].mean(), v[:, 1].mean(), v[:, 2].min()])
        silhouette_after.append(projected_area_m2(v, f))
        ids.append(path.stem)
        verts.append(v)
        faces.append(f)
        statures.append(float(np.ptp(v[:, 2])))
        widths.append(mean_silhouette_width_m(v))
    if not ids:
        raise RuntimeError(f"every reconstruction in {directory} was rejected")
    before = np.array(silhouette_before)
    after = np.array(silhouette_after)
    provenance: dict[str, Any] = {
        "directory": str(directory),
        "bodies": len(ids),
        "faces_before_decimation": full_faces,
        "faces_after_decimation": int(sum(f.shape[0] for f in faces)),
        "target_faces_per_body": int(target_faces),
        "decimator": {
            "name": "fast_simplification" if decimated_bodies else "none",
            "version": decimator_version,
            "algorithm": "quadric" if decimated_bodies else "none",
            "bodies_decimated": decimated_bodies,
        },
        "silhouette_area_change_max_abs_fraction": float(np.max(np.abs(after / before - 1.0))),
        "mean_silhouette_width_m": float(np.mean(widths)),
        "stature_m": {
            "min": float(np.min(statures)),
            "median": float(np.median(statures)),
            "max": float(np.max(statures)),
        },
    }
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        provenance["source_manifest"] = {
            "pose": manifest.get("pose"),
            "mesh": manifest.get("mesh"),
            "range_sources": sorted({b.get("range_source") for b in manifest.get("bodies", [])}),
        }
    return BodyLibrary(
        body_ids=tuple(ids),
        vertices=tuple(verts),
        faces=tuple(faces),
        stature_m=np.asarray(statures, dtype=np.float64),
        width_m=np.asarray(widths, dtype=np.float64),
        provenance=provenance,
    )


def projected_area_m2(vertices: np.ndarray, faces: np.ndarray, *, samples: int = 64) -> float:
    """Azimuth averaged area of the body's silhouette against a horizontal ray.

    For a closed surface the projected area onto a plane is half the sum of
    ``|n.d| dA`` over the surface, so no visibility test is needed. This is what
    the blockage cross section is proportional to, so it is the quantity to
    watch through decimation, not the surface area.
    """
    tri = np.asarray(vertices, dtype=np.float64)[np.asarray(faces, dtype=np.int64)]
    area_normal = 0.5 * np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    angles = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
    directions = np.column_stack([np.cos(angles), np.sin(angles), np.zeros_like(angles)])
    return float(np.mean(0.5 * np.abs(area_normal @ directions.T).sum(axis=0)))


@dataclass(frozen=True)
class CrowdConfig:
    """Everything that changes the crowd, and nothing that does not."""

    density_per_m2: float
    max_radius_m: float = 30.0
    #: Mean free paths of crowd beyond which the trace stops carrying bodies, a
    #: knob for the truncation ablation and off by default. Cutting the crowd at
    #: a few mean free paths is safe for a single leg, whose survival at the cut
    #: is ``exp(-mean_free_paths)``, and is not safe for a multi-bounce path,
    #: which can leave the truncated disc, bounce off the ground outside it and
    #: come back through crowd that is no longer there. Since that failure moves
    #: the expensive arm towards the cheap arm, which is exactly the comparison
    #: this module exists to make, the default is not to truncate.
    mean_free_paths: float = float("inf")
    exclusion_radius_m: float = EXCLUSION_RADIUS_M
    min_separation_m: float = MIN_SEPARATION_M
    datum_tolerance_m: float = 2.5
    min_up_cosine: float = 0.85
    seed: int = 0

    def radius_m(self, width_m: float) -> float:
        """Radius the crowd is actually built out to."""
        if self.density_per_m2 <= 0.0 or width_m <= 0.0 or not np.isfinite(self.mean_free_paths):
            return float(self.max_radius_m)
        return float(min(self.max_radius_m, self.mean_free_paths / (self.density_per_m2 * width_m)))

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Crowd:
    """Placed bystanders around one observation point."""

    positions_xy: np.ndarray  # (N, 2)
    ground_z_m: np.ndarray  # (N,)
    yaw_rad: np.ndarray  # (N,)
    shape_index: np.ndarray  # (N,) into the library
    radius_m: float
    config: CrowdConfig
    provenance: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return int(self.positions_xy.shape[0])

    @property
    def achieved_density_per_m2(self) -> float:
        """Placed bodies per square metre of walkable ground inside the crowd."""
        walkable = float(self.provenance.get("walkable_fraction", 1.0))
        area = np.pi * (self.radius_m**2 - self.config.exclusion_radius_m**2) * walkable
        return float(len(self) / area) if area > 0.0 else 0.0

    @property
    def effective_density_per_m2(self) -> float:
        """Areal intensity over the whole disc, which is what a ray integrates."""
        area = np.pi * (self.radius_m**2 - self.config.exclusion_radius_m**2)
        return float(len(self) / area) if area > 0.0 else 0.0

    def to_mesh(self, library: BodyLibrary) -> tuple[np.ndarray, np.ndarray]:
        """One vertex and face buffer holding the whole crowd.

        Written into preallocated buffers rather than concatenated from a list
        of a few thousand arrays. At the top of the density ladder the crowd is
        several thousand bodies, and the list form peaks at twice the final size
        while holding a Mitsuba scene of the same crowd, which is enough to be
        killed on a shared machine.
        """
        if len(self) == 0:
            return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int32)
        shapes = self.shape_index.astype(int)
        vertex_counts = np.array([library.vertices[s].shape[0] for s in shapes])
        face_counts = np.array([library.faces[s].shape[0] for s in shapes])
        vertices = np.empty((int(vertex_counts.sum()), 3), dtype=np.float64)
        faces = np.empty((int(face_counts.sum()), 3), dtype=np.int32)
        vertex_start = np.concatenate([[0], np.cumsum(vertex_counts)])
        face_start = np.concatenate([[0], np.cumsum(face_counts)])
        for i, shape in enumerate(shapes):
            source = library.vertices[shape]
            cos, sin = np.cos(self.yaw_rad[i]), np.sin(self.yaw_rad[i])
            block = vertices[vertex_start[i] : vertex_start[i + 1]]
            block[:, 0] = cos * source[:, 0] - sin * source[:, 1] + self.positions_xy[i, 0]
            block[:, 1] = sin * source[:, 0] + cos * source[:, 1] + self.positions_xy[i, 1]
            block[:, 2] = source[:, 2] + self.ground_z_m[i]
            faces[face_start[i] : face_start[i + 1]] = library.faces[shape] + vertex_start[i]
        return vertices, faces


def sample_crowd(
    geometry: Any,
    centre_xy: np.ndarray,
    ground_datum_m: float,
    library: BodyLibrary,
    config: CrowdConfig,
) -> Crowd:
    """Bystanders on walkable ground around one observation point.

    Walkable is decided the way ``walk.py`` decides it, by dropping a ray from
    above and keeping the sample only where it lands on a near horizontal face
    close to the square's ground datum. A body is therefore never placed inside
    a building, on a roof or up a wall, and the achieved density is reported
    against the requested one because the walkable fraction of a disc around a
    standpoint is not 1.
    """
    rng = np.random.default_rng(config.seed)
    width = float(np.mean(library.width_m))
    radius = config.radius_m(width)
    centre = np.asarray(centre_xy, dtype=np.float64)[:2]
    disc_area = np.pi * (radius**2 - config.exclusion_radius_m**2)

    def darts(count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        angle = rng.uniform(0.0, 2.0 * np.pi, count)
        span = radius**2 - config.exclusion_radius_m**2
        distance = np.sqrt(config.exclusion_radius_m**2 + span * rng.random(count))
        xy = centre + np.column_stack([distance * np.cos(angle), distance * np.sin(angle)])
        probe = ground_datum_m + 200.0
        hit, travel, normal, _ = geometry.intersect(
            np.column_stack([xy, np.full(count, probe)]),
            np.tile(np.array([0.0, 0.0, -1.0]), (count, 1)),
        )
        z = np.where(hit, probe - travel, np.nan)
        good = (
            np.isfinite(z)
            & (np.abs(z - ground_datum_m) <= config.datum_tolerance_m)
            & (np.abs(normal[:, 2]) >= config.min_up_cosine)
        )
        return xy, z, good

    # The density is people per square metre of ground someone can stand on, so
    # the walkable fraction of the disc is measured first and the target count
    # follows from it. Both arms are then driven by the same effective areal
    # intensity and the comparison tests the physics rather than the bookkeeping.
    _, _, probe_good = darts(4096)
    walkable_fraction = float(np.mean(probe_good))
    wanted = int(round(config.density_per_m2 * disc_area * walkable_fraction))

    positions = np.zeros((max(wanted, 1), 2))
    grounds = np.zeros(max(wanted, 1))
    placed = 0
    attempts = 0
    # The hard core is enforced against a bucket grid of pitch ``min_separation``
    # rather than against every body placed so far, so the sampler stays linear
    # in the crowd size instead of quadratic. Any two points closer than the
    # pitch share a cell or share an edge, so the 3 by 3 neighbourhood is exact.
    pitch = max(config.min_separation_m, 1.0e-6)
    buckets: dict[tuple[int, int], list[int]] = {}
    while placed < wanted and attempts < 64:
        attempts += 1
        xy, z, good = darts(max(2 * (wanted - placed), 256))
        for point, height in zip(xy[good], z[good], strict=True):
            cell = (int(np.floor(point[0] / pitch)), int(np.floor(point[1] / pitch)))
            near = [
                index
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                for index in buckets.get((cell[0] + dx, cell[1] + dy), ())
            ]
            if near and np.min(np.linalg.norm(positions[near] - point, axis=1)) < config.min_separation_m:
                continue
            positions[placed] = point
            grounds[placed] = height
            buckets.setdefault(cell, []).append(placed)
            placed += 1
            if placed >= wanted:
                break
    positions = positions[:placed]
    grounds = grounds[:placed]
    return Crowd(
        positions_xy=positions,
        ground_z_m=grounds,
        yaw_rad=rng.uniform(0.0, 2.0 * np.pi, placed),
        shape_index=rng.integers(0, len(library), placed),
        radius_m=radius,
        config=config,
        provenance={
            "requested": wanted,
            "placed": placed,
            "walkable_fraction": walkable_fraction,
            "effective_density_per_m2": config.density_per_m2 * walkable_fraction,
            "mean_width_m": width,
            "hard_core_attempts": attempts,
        },
    )


class CompositeGeometry:
    """Two ray casting backends read as one, nearer hit wins.

    Face indices are made global by offsetting the second backend's by the first
    backend's face count, so a single ``face_class`` array indexes both and the
    tracer needs no change at all.
    """

    def __init__(self, base: Any, overlay: Any, base_face_count: int) -> None:
        self.base = base
        self.overlay = overlay
        self.base_face_count = int(base_face_count)

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        hit_a, dist_a, normal_a, face_a = self.base.intersect(origins, directions)
        hit_b, dist_b, normal_b, face_b = self.overlay.intersect(origins, directions)
        dist_a = np.where(hit_a, dist_a, INFINITY)
        dist_b = np.where(hit_b, dist_b, INFINITY)
        take_b = dist_b < dist_a
        hit = hit_a | hit_b
        distance = np.where(take_b, dist_b, dist_a)
        normal = np.where(take_b[:, None], normal_b, normal_a)
        face = np.where(take_b, face_b + self.base_face_count, face_a)
        return hit, np.where(hit, distance, INFINITY), normal, face


@dataclass(frozen=True)
class CrowdGeometryConfig:
    """Inputs needed to add one crowd to one traced site."""

    site: Any
    crowd: Crowd
    library: BodyLibrary
    site_face_class: np.ndarray
    body_class_index: int
    variant: str = "llvm_ad_rgb"
    scratch: pathlib.Path | None = None


def crowd_geometry(config: CrowdGeometryConfig) -> tuple[Any, np.ndarray]:
    """The site with a crowd in it, and the face class array that indexes both.

    Returns the site geometry unchanged when the crowd is empty, so a zero
    density run is bit identical with the baseline rather than merely close.
    """
    if len(config.crowd) == 0:
        return config.site, np.asarray(config.site_face_class)
    vertices, faces = config.crowd.to_mesh(config.library)
    scratch = pathlib.Path(config.scratch or pathlib.Path.cwd())
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "crowd.ply"
    _write_ply(path, vertices, faces)
    del vertices, faces
    gc.collect()
    overlay = MitsubaGeometry(path, variant=config.variant)
    overlay_faces = overlay.face_count
    # MitsubaGeometry keeps a float64 vertex buffer and an int64 face buffer
    # beside the scene, for callers that want to classify triangles. Every
    # triangle of this overlay is a body, so nothing here classifies anything,
    # and at the top of the density ladder those two buffers are a hundred
    # megabytes that the process is short of. Dropped once the count is read.
    overlay.vertices = np.zeros((0, 3))
    overlay.faces = np.zeros((0, 3), dtype=np.int64)
    gc.collect()
    face_class = np.concatenate(
        [
            np.asarray(config.site_face_class, dtype=np.int64),
            np.full(overlay_faces, int(config.body_class_index), dtype=np.int64),
        ]
    )
    return CompositeGeometry(config.site, overlay, int(np.asarray(config.site_face_class).shape[0])), face_class


def _write_ply(path: pathlib.Path, vertices: np.ndarray, faces: np.ndarray) -> None:
    """Binary little endian PLY, double vertices to match the site export."""
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {vertices.shape[0]}\n"
        "property double x\nproperty double y\nproperty double z\n"
        f"element face {faces.shape[0]}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    )
    with path.open("wb") as handle:
        handle.write(header.encode("ascii"))
        handle.write(np.ascontiguousarray(vertices, dtype="<f8").tobytes())
        block = np.empty(faces.shape[0], dtype=[("n", "u1"), ("v", "<i4", 3)])
        block["n"] = 3
        block["v"] = faces
        handle.write(block.tobytes())


def extinction_length_m(
    elevation_rad: np.ndarray,
    *,
    observer_height_m: float,
    body_height_m: np.ndarray | float,
    radius_m: float,
    exclusion_radius_m: float = 0.0,
) -> np.ndarray:
    """Horizontal distance over which a ray can meet a standing body.

    A ray leaving the observation point at elevation ``e`` is at height
    ``h_o + r*tan(e)`` after horizontal distance ``r``. A body of height ``h_b``
    standing at that distance intercepts the ray when ``0 <= h_o + r*tan(e) <=
    h_b``, which is an interval in ``r``:

    * climbing, ``tan(e) > 0``: ``[0, (h_b - h_o)/tan(e)]``, empty when the
      body is shorter than the observation point, which is the whole story of
      this module;
    * level: everything, capped by the crowd radius;
    * falling, ``tan(e) < 0``: ``[(h_o - h_b)/|tan(e)|, h_o/|tan(e)|]``, the far
      end being where the ray reaches the ground.

    The interval is then clipped to ``[exclusion_radius, radius]``. Broadcasting
    is ``elevation`` against ``body_height``, so a stature distribution can be
    passed straight in.
    """
    e = np.atleast_1d(np.asarray(elevation_rad, dtype=np.float64))[..., None]
    h_b = np.atleast_1d(np.asarray(body_height_m, dtype=np.float64))
    h_o = float(observer_height_m)
    tan = np.tan(e)
    level = np.abs(tan) < 1.0e-12
    slope = np.abs(np.where(level, 1.0, tan))

    climbing = tan > 0.0
    near = np.where(climbing, 0.0, np.maximum(0.0, (h_o - h_b) / slope))
    far = np.where(climbing, np.where(h_b > h_o, (h_b - h_o) / slope, 0.0), h_o / slope)
    # A level ray never leaves the height it started at, so it is blocked over
    # the whole crowd when the observation point is no taller than the body and
    # nowhere at all when it is taller.
    near = np.where(level, 0.0, near)
    far = np.where(level, np.where(h_b >= h_o, float(radius_m), 0.0), far)

    lo = np.maximum(near, exclusion_radius_m)
    hi = np.minimum(far, radius_m)
    return np.maximum(0.0, hi - lo)


@dataclass(frozen=True)
class TransmittanceConfig:
    """Body population and quadrature inputs for the analytic crowd model."""

    density_per_m2: float
    width_m: np.ndarray | float
    body_height_m: np.ndarray | float
    observer_height_m: float = 1.5
    radius_m: float = 30.0
    exclusion_radius_m: float = EXCLUSION_RADIUS_M
    cells: int | None = None
    subsamples: int = 33


def crowd_transmittance(directions: np.ndarray, config: TransmittanceConfig) -> np.ndarray:
    """Beer-Lambert survival of the final leg, per direction.

    Bystander centres are a Poisson field of intensity ``lambda`` on the ground.
    A body of silhouette width ``w`` standing within ``w/2`` of the ray's ground
    track and inside the blocking interval intercepts it, so the expected number
    of interceptions is ``lambda`` times the mean of ``w_i * L(e; h_i)`` over the
    body population, and the survival probability is its exponential. Thinning a
    Poisson field by body type is why the mean over the population can be taken
    inside the exponent.

    ``width_m`` and ``body_height_m`` are paired per body, so a taller body is
    correctly also a wider one.

    ``cells`` turns on the cell average, and it is not optional in practice.
    ``T`` falls from 1 to nearly 0 across the first degree or so above the
    horizon, which is narrower than one cell of a few hundred cell Fibonacci
    grid, so reading ``T`` at the cell centre and calling that the cell's factor
    is a quadrature error of the same size as the effect. Passing the grid's
    cell count integrates ``T`` over the band in ``sin(elevation)`` that the
    cell occupies, ``2/cells`` wide, which is what ``fibonacci_sphere`` lays
    down.
    """
    directions = np.asarray(directions, dtype=np.float64)
    widths = np.atleast_1d(np.asarray(config.width_m, dtype=np.float64))
    heights = np.atleast_1d(np.asarray(config.body_height_m, dtype=np.float64))
    if widths.size != heights.size:
        raise ValueError("width_m and body_height_m must be paired per body")

    sine = np.clip(directions[:, 2], -1.0, 1.0)
    if config.cells is None:
        offsets = np.zeros(1)
    else:
        offsets = np.linspace(
            -1.0 / int(config.cells),
            1.0 / int(config.cells),
            int(config.subsamples),
        )
    sines = np.clip(sine[:, None] + offsets[None, :], -1.0, 1.0)
    length = extinction_length_m(
        np.arcsin(sines).ravel(),
        observer_height_m=config.observer_height_m,
        body_height_m=heights,
        radius_m=config.radius_m,
        exclusion_radius_m=config.exclusion_radius_m,
    )
    expected = float(config.density_per_m2) * np.mean(widths * length, axis=-1)
    return np.mean(np.exp(-expected).reshape(sines.shape), axis=1)


def blocked_susceptibility(
    rho: np.ndarray,
    transmittance: np.ndarray,
    solid_angle: float,
) -> float:
    """``chi`` after the crowd has extinguished the final leg of every path."""
    return float(np.sum(np.asarray(rho) * np.asarray(transmittance)) * float(solid_angle))


def near_horizon_share(
    local_grid: np.ndarray,
    rho: np.ndarray,
    solid_angle: float,
    elevation_deg: float = 5.0,
) -> float:
    """Fraction of ``chi`` that arrives from below ``elevation_deg``.

    Not the same quantity as ``directions.measure_below``, and the difference is
    the point. That one is where the illumination *leaves the network*, this one
    is where it *reaches the pedestrian* after the square has moved it around.
    A crowd can only take away what arrives near the horizon, so this is the
    ceiling on what blockage can do, and reading it next to the illumination
    measure says how much of the near-horizon band the buildings had already
    taken.
    """
    total = float(np.sum(rho) * solid_angle)
    if total <= 0.0:
        return 0.0
    low = np.arcsin(np.clip(np.asarray(local_grid)[:, 2], -1.0, 1.0)) <= np.radians(elevation_deg)
    return float(np.sum(np.asarray(rho)[low]) * solid_angle / total)
