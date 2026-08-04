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
import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .geometry import INFINITY, MitsubaGeometry
from .tracer import DEFAULT_MAX_BOUNCES

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


def simplify(vertices: np.ndarray, faces: np.ndarray, target_faces: int) -> tuple[np.ndarray, np.ndarray]:
    """Quadric decimation, falling back to vertex clustering without the wheel.

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
    try:
        import fast_simplification
    except ImportError:
        return _cluster_decimate(vertices, faces, target_faces)
    out_v, out_f = fast_simplification.simplify(
        vertices.astype(np.float32), faces.astype(np.int32), target_count=int(target_faces)
    )
    return np.asarray(out_v, dtype=np.float64), np.asarray(out_f, dtype=np.int64)


def _cluster_decimate(vertices: np.ndarray, faces: np.ndarray, target_faces: int) -> tuple[np.ndarray, np.ndarray]:
    """Voxel clustering, the dependency free fallback.

    Vertices are snapped to a grid whose pitch is chosen so the face count lands
    near the target, and degenerate faces are dropped. Cruder than a quadric,
    but it can only move a vertex by half a voxel, so the silhouette error is
    bounded by the pitch.
    """
    extent = float(np.ptp(vertices, axis=0).max())
    pitch = extent * np.sqrt(4.0 / max(target_faces, 4))
    inverse = np.arange(vertices.shape[0])
    counts = np.ones(vertices.shape[0], dtype=np.int64)
    kept = faces
    for _ in range(24):
        keys = np.round((vertices - vertices.min(axis=0)) / pitch).astype(np.int64)
        _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
        remapped = inverse[faces]
        distinct = (
            (remapped[:, 0] != remapped[:, 1]) & (remapped[:, 1] != remapped[:, 2]) & (remapped[:, 0] != remapped[:, 2])
        )
        kept = remapped[distinct]
        if kept.shape[0] <= target_faces:
            break
        pitch *= 1.25
    centres = np.zeros((counts.size, 3))
    np.add.at(centres, inverse, vertices)
    centres /= counts[:, None]
    return centres, kept


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
        v, f = simplify(v, f, target_faces)
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


def crowd_geometry(
    site: Any,
    crowd: Crowd,
    library: BodyLibrary,
    site_face_class: np.ndarray,
    body_class_index: int,
    *,
    variant: str = "llvm_ad_rgb",
    scratch: pathlib.Path | None = None,
) -> tuple[Any, np.ndarray]:
    """The site with a crowd in it, and the face class array that indexes both.

    Returns the site geometry unchanged when the crowd is empty, so a zero
    density run is bit identical with the baseline rather than merely close.
    """
    if len(crowd) == 0:
        return site, np.asarray(site_face_class)
    vertices, faces = crowd.to_mesh(library)
    scratch = pathlib.Path(scratch or pathlib.Path.cwd())
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "crowd.ply"
    _write_ply(path, vertices, faces)
    del vertices, faces
    gc.collect()
    overlay = MitsubaGeometry(path, variant=variant)
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
            np.asarray(site_face_class, dtype=np.int64),
            np.full(overlay_faces, int(body_class_index), dtype=np.int64),
        ]
    )
    return CompositeGeometry(site, overlay, int(np.asarray(site_face_class).shape[0])), face_class


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


def crowd_transmittance(
    directions: np.ndarray,
    *,
    density_per_m2: float,
    width_m: np.ndarray | float,
    body_height_m: np.ndarray | float,
    observer_height_m: float = 1.5,
    radius_m: float = 30.0,
    exclusion_radius_m: float = EXCLUSION_RADIUS_M,
    cells: int | None = None,
    subsamples: int = 33,
) -> np.ndarray:
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
    widths = np.atleast_1d(np.asarray(width_m, dtype=np.float64))
    heights = np.atleast_1d(np.asarray(body_height_m, dtype=np.float64))
    if widths.size != heights.size:
        raise ValueError("width_m and body_height_m must be paired per body")

    sine = np.clip(directions[:, 2], -1.0, 1.0)
    if cells is None:
        offsets = np.zeros(1)
    else:
        offsets = np.linspace(-1.0 / int(cells), 1.0 / int(cells), int(subsamples))
    sines = np.clip(sine[:, None] + offsets[None, :], -1.0, 1.0)
    length = extinction_length_m(
        np.arcsin(sines).ravel(),
        observer_height_m=observer_height_m,
        body_height_m=heights,
        radius_m=radius_m,
        exclusion_radius_m=exclusion_radius_m,
    )
    expected = float(density_per_m2) * np.mean(widths * length, axis=-1)
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


# ---------------------------------------------------------------------------
# The study
# ---------------------------------------------------------------------------

#: Standing stature of the adult population the bystanders stand in for, both
#: sexes pooled. This is a declared modelling parameter and not a measurement of
#: anyone on Korenmarkt, and nothing downstream needs it to be exact: the
#: blocking depth of the law below is linear in ``h_body - h_observer``, so a
#: reader who prefers a different population can rescale every number in the
#: cheap arm by hand. The traced arm is run at this value and at the
#: reconstructions' own statures, which brackets it.
ADULT_STATURE_MEAN_M = 1.73
ADULT_STATURE_SD_M = 0.09

STATURE_MODES = ("as_reconstructed", "adult")

#: The three estimates every row carries. ``full`` re-traced the scene with the
#: bodies in it, ``walkable`` and ``nominal`` are the Beer-Lambert post-multiply
#: read at the crowd's true areal intensity and at the square's nominal
#: pedestrian density.
ARMS = ("full", "walkable", "nominal")


def stature_library(library: BodyLibrary, mode: str, seed: int = 0) -> BodyLibrary:
    """The body library at reconstructed statures or at adult statures.

    The reconstructions run 1.39 to 1.71 m with a median of 1.55 m, which is
    short for adults and is a property of the monocular reconstruction rather
    than of Korenmarkt. The observation point stands at 1.5 m, so the difference
    between a 1.55 m bystander and a 1.73 m one is the difference between 0.05 m
    and 0.23 m of blocking height, a factor of four in how deep a crowd of the
    same density is. Both are therefore run.
    """
    if mode == "as_reconstructed":
        return library
    if mode != "adult":
        raise ValueError(f"unknown stature mode {mode!r}")
    rng = np.random.default_rng(seed)
    targets = np.clip(rng.normal(ADULT_STATURE_MEAN_M, ADULT_STATURE_SD_M, len(library)), 1.45, 2.05)
    return library.rescaled(targets)


def _finished_locations(rows_path: pathlib.Path, expected_crowd_rows: int) -> set[int]:
    """Standpoints already fully traced, and drop the partial ones in place.

    A shared machine kills a long run eventually, so the runner has to be
    restartable without silently mixing a half traced standpoint into the
    medians. Complete standpoints are kept, incomplete ones are deleted from the
    file, and the run picks up from there.
    """
    rows_path = pathlib.Path(rows_path)
    if not rows_path.exists():
        return set()
    rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line.strip()]
    counted: dict[int, int] = {}
    seen_baseline: set[int] = set()
    for row in rows:
        if row["kind"] == "baseline":
            seen_baseline.add(int(row["location"]))
        else:
            counted[int(row["location"])] = counted.get(int(row["location"]), 0) + 1
    done = {loc for loc in seen_baseline if counted.get(loc, 0) >= expected_crowd_rows}
    kept = [row for row in rows if int(row["location"]) in done]
    if len(kept) != len(rows):
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in kept))
    return done


def site_mesh(root: pathlib.Path, site: str, crop_m: int) -> pathlib.Path:
    """The double precision support mesh for a site, refusing the defective one.

    The same rule ``run_exposure.py`` applies, spelled out again here rather
    than imported. Importing the study runner would drag its whole semantic
    binding chain into a module that needs none of it, and this package is
    edited by more than one hand at a time.
    """
    directory = pathlib.Path(root) / "data" / "geometry" / site
    for candidate in (f"inhouse_leaf_{crop_m}m_f64.ply", f"inhouse_leaf_{crop_m}m.ply"):
        path = directory / candidate
        manifest = path.with_suffix(".json")
        if not path.exists() or not manifest.exists():
            continue
        if int(json.loads(manifest.read_text()).get("format_version", 0)) >= 3:
            return path
    raise FileNotFoundError(f"no double precision {crop_m} m mesh for {site}")


def ground_datum(root: pathlib.Path, site: str, geometry: Any, *, radius_m: float = 15.0, samples: int = 4096) -> float:
    """Walkable height of the square, from the site config or from the mesh."""
    config = pathlib.Path(root) / "config" / f"{site}.json"
    if config.exists():
        recorded = json.loads(config.read_text()).get("camera_ground_z_m")
        if recorded is not None:
            return float(recorded)
    rng = np.random.default_rng(0)
    angle = rng.uniform(0.0, 2.0 * np.pi, samples)
    distance = radius_m * np.sqrt(rng.random(samples))
    probe = 1.0e4
    hit, travel, _, _ = geometry.intersect(
        np.column_stack([distance * np.cos(angle), distance * np.sin(angle), np.full(samples, probe)]),
        np.tile(np.array([0.0, 0.0, -1.0]), (samples, 1)),
    )
    heights = probe - travel[hit]
    if heights.size == 0:
        raise RuntimeError("no surface under the centre of the crop")
    return float(np.median(heights))


def _shift_db(value: float, reference: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return float("nan")
    return float(10.0 * np.log10(value / reference))


def run_study(
    *,
    output_dir: pathlib.Path,
    bodies_dir: pathlib.Path,
    site: str = "korenmarkt",
    crop_m: int = 250,
    frequency_hz: float = 15.0e9,
    locations: int = 12,
    densities: tuple[float, ...] = DENSITY_LADDER,
    realisations: int = 3,
    rays: int = 200_000,
    local_cells: int = 512,
    max_bounces: int = DEFAULT_MAX_BOUNCES,
    seed: int = 7,
    stature_modes: tuple[str, ...] = STATURE_MODES,
    target_faces: int = 600,
    max_radius_m: float = 30.0,
    mean_free_paths: float = float("inf"),
    clothing_rms_height_m: float = CLOTHING_RMS_HEIGHT_M,
    body_absorber: bool = False,
    variant: str = "llvm_ad_rgb",
    tag: str = "korenmarkt",
    scratch: pathlib.Path | None = None,
    resume: bool = False,
) -> pathlib.Path:
    """Trace the same standpoints with and without a crowd, at every density.

    Streaming, like every other runner here: one row per standpoint, density,
    realisation and stature mode is appended to a JSONL and nothing that scales
    with the ray count reaches disk. The baseline trace of a standpoint is done
    once and reused by every density, which is what makes the paired ratio a
    paired ratio.
    """
    from ..illumination import MODELS as models
    from ..materials import classify_faces, load_table
    from .tracer import SbrTracer, TraceConfig
    from ..walk.grid import build_walk
    from ..walk.model import stratified_subset

    root = pathlib.Path(__file__).resolve().parents[2]
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = pathlib.Path(scratch or output_dir / "scratch")
    stem = f"{tag}_{frequency_hz / 1e9:g}ghz"
    rows_path = output_dir / f"{stem}_rows.jsonl"
    manifest_path = output_dir / f"{stem}_manifest.json"

    started = time.perf_counter()
    mesh = site_mesh(root, site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = ground_datum(root, site, geometry)
    site_face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(root / "config", frequency_hz)

    body_permittivity = ABSORBER_PERMITTIVITY if body_absorber else skin_permittivity(frequency_hz)
    permittivity = np.append(binding.permittivity, body_permittivity)
    rms_height = np.append(binding.rms_height_m, 0.0 if body_absorber else float(clothing_rms_height_m))
    body_class_index = len(binding.class_names)

    base_library = load_body_library(bodies_dir, target_faces=target_faces)
    libraries = {mode: stature_library(base_library, mode, seed=seed) for mode in stature_modes}

    walk = build_walk(geometry, ground_datum_m=datum, radius_m=90.0, spacing_m=3.0, seed=seed)
    picks = stratified_subset(walk, locations)
    head_height_m = float(walk.provenance["head_height_m"])

    config = TraceConfig(
        frequency_hz=frequency_hz, rays=rays, local_cells=local_cells, max_bounces=max_bounces, seed=seed
    )
    baseline_tracer = SbrTracer(geometry, site_face_class, permittivity, rms_height, config)

    manifest: dict[str, Any] = {
        "generator": "semantic_twin.propagation.bystanders",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": (
            "how far does the pedestrian exposure distribution move when the square holds other "
            "people, per illumination model and per crowd density"
        ),
        "prediction": (
            "bystanders stand at the observation point's own height, so they can only take away "
            "the near horizon band. The corrected illumination laws put 87.9 percent of the street "
            "small cell measure and 9.4 percent of the rooftop measure below 5 degrees, so the "
            "street column should lose much more than the rooftop column."
        ),
        "site": site,
        "mesh": str(mesh),
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "ground_datum_m": datum,
        "head_height_m": head_height_m,
        "trace_config": config.as_dict(),
        "surface_binding": binding.as_dict(),
        "body_material": {
            "class_index": body_class_index,
            "relative_permittivity": [float(permittivity[-1].real), float(permittivity[-1].imag)],
            "source": (
                "index matched absorber, a control that removes re-illumination"
                if body_absorber
                else "IT'IS skin through aegis.tissue.TissueModel.from_database"
            ),
            "rms_height_m": float(rms_height[-1]),
            "rms_height_source": "prior for clothing weave and drape, see CLOTHING_RMS_HEIGHT_M",
        },
        "body_library": base_library.provenance,
        "stature_modes": {
            mode: {
                "min": float(np.min(lib.stature_m)),
                "median": float(np.median(lib.stature_m)),
                "max": float(np.max(lib.stature_m)),
                "mean_width_m": float(np.mean(lib.width_m)),
            }
            for mode, lib in libraries.items()
        },
        "densities_per_m2": list(densities),
        "density_source": (
            "Fruin, Designing for pedestrians: a level-of-service concept, Highway Research Record "
            "355 (1971), pp. 1-15. Walkway level of service is stated as a pedestrian area module "
            "in square feet per pedestrian: A above 35, B 25 to 35, C 15 to 25, D 10 to 15, E 5 to "
            "10, F below 5. Inverted and converted at 1 sq ft = 0.09290304 m2 those boundaries are "
            "0.31, 0.43, 0.72, 1.08 and 2.15 people per square metre."
        ),
        "crowd": {
            "max_radius_m": max_radius_m,
            "mean_free_paths": mean_free_paths,
            "exclusion_radius_m": EXCLUSION_RADIUS_M,
            "min_separation_m": MIN_SEPARATION_M,
            "realisations": realisations,
            "density_is": "people per square metre of walkable ground, not of total disc area",
        },
        "walk": walk.provenance,
        "locations_traced": int(picks.size),
        "illumination_models": sorted(models),
        "storage_policy": "paths are never written, only per row scalars",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    expected_rows = len(libraries) * len(densities) * realisations
    finished = _finished_locations(rows_path, expected_rows) if resume else set()
    if finished:
        print(f"resuming, {len(finished)} standpoints already complete", flush=True)
    with rows_path.open("a" if finished else "w") as handle:
        for order, index in enumerate(picks):
            if int(index) in finished:
                continue
            point = walk.points[index]
            ground_z = float(walk.ground_z_m[index])
            base = baseline_tracer.trace(point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index))
            base_row = {
                "kind": "baseline",
                "location": int(index),
                "x": float(point[0]),
                "y": float(point[1]),
                "z": float(point[2]),
                "sky_fraction": base.sky_fraction,
                "mean_bounces": base.mean_bounces,
                "seconds": base.seconds,
            }
            for name in models:
                base_row[f"chi_{name}"] = base.susceptibility[name]
                base_row[f"arriving_below_5deg_{name}"] = near_horizon_share(
                    base.local_grid, base.rho[name], base.local_solid_angle, 5.0
                )
                base_row[f"arriving_below_2deg_{name}"] = near_horizon_share(
                    base.local_grid, base.rho[name], base.local_solid_angle, 2.0
                )
            handle.write(json.dumps(base_row) + "\n")
            handle.flush()

            for mode, library in libraries.items():
                for density in densities:
                    for realisation in range(realisations):
                        crowd_config = CrowdConfig(
                            density_per_m2=float(density),
                            max_radius_m=max_radius_m,
                            mean_free_paths=mean_free_paths,
                            seed=seed + 97 * realisation + 7919 * int(index),
                        )
                        crowd = sample_crowd(geometry, point[:2], datum, library, crowd_config)
                        composite, face_class = crowd_geometry(
                            geometry,
                            crowd,
                            library,
                            site_face_class,
                            body_class_index,
                            variant=variant,
                            scratch=scratch,
                        )
                        traced = SbrTracer(composite, face_class, permittivity, rms_height, config).trace(
                            point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index)
                        )
                        # Two readings of the same law, and the difference is
                        # which density a caller who has not traced anything
                        # would actually type in. ``walkable`` uses the areal
                        # intensity the crowd really has once the buildings have
                        # taken their share of the disc, which is what the
                        # traced arm was given. ``nominal`` uses the square's
                        # pedestrian density with no such correction, which is
                        # all a caller has. Both are recorded because the second
                        # is the one that has to work.
                        transmittance = {
                            "walkable": crowd_transmittance(
                                base.local_grid,
                                density_per_m2=crowd.effective_density_per_m2,
                                width_m=library.width_m,
                                body_height_m=library.stature_m,
                                observer_height_m=head_height_m,
                                radius_m=crowd.radius_m,
                                cells=local_cells,
                            ),
                            "nominal": crowd_transmittance(
                                base.local_grid,
                                density_per_m2=float(density),
                                width_m=library.width_m,
                                body_height_m=library.stature_m,
                                observer_height_m=head_height_m,
                                radius_m=crowd.radius_m,
                                cells=local_cells,
                            ),
                        }
                        row = {
                            "kind": "crowd",
                            "location": int(index),
                            "stature_mode": mode,
                            "density_per_m2": float(density),
                            "realisation": realisation,
                            "bodies": len(crowd),
                            "crowd_radius_m": crowd.radius_m,
                            "walkable_fraction": crowd.provenance["walkable_fraction"],
                            "effective_density_per_m2": crowd.effective_density_per_m2,
                            "achieved_density_per_m2": crowd.achieved_density_per_m2,
                            "sky_fraction": traced.sky_fraction,
                            "mean_bounces": traced.mean_bounces,
                            "seconds": traced.seconds,
                        }
                        for name in models:
                            row[f"chi_full_{name}"] = traced.susceptibility[name]
                            row[f"shift_full_db_{name}"] = _shift_db(
                                traced.susceptibility[name], base.susceptibility[name]
                            )
                            for arm, factor in transmittance.items():
                                cheap = blocked_susceptibility(base.rho[name], factor, base.local_solid_angle)
                                row[f"chi_{arm}_{name}"] = cheap
                                row[f"shift_{arm}_db_{name}"] = _shift_db(cheap, base.susceptibility[name])
                        handle.write(json.dumps(row) + "\n")
                        handle.flush()
                        # A crowd at the top of the ladder is a few thousand
                        # bodies and its acceleration structure is the largest
                        # object in the process. Dropping it before the next one
                        # is built keeps the peak at one crowd rather than two.
                        placed, built_radius = len(crowd), crowd.radius_m
                        del composite, face_class, traced, crowd, transmittance
                        gc.collect()
                    print(
                        f"[{order + 1}/{picks.size}] {mode} lambda={density:g} "
                        f"bodies={placed} R={built_radius:.0f} m "
                        + " ".join(
                            f"{name}={row[f'shift_full_db_{name}']:+.2f}/{row[f'shift_nominal_db_{name}']:+.2f} dB"
                            for name in models
                        ),
                        flush=True,
                    )

    manifest["wall_seconds"] = time.perf_counter() - started
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {rows_path}", flush=True)
    return rows_path


def noise_floor(
    *,
    output_dir: pathlib.Path,
    site: str = "korenmarkt",
    crop_m: int = 250,
    frequency_hz: float = 15.0e9,
    locations: int = 12,
    rays: int = 120_000,
    local_cells: int = 512,
    max_bounces: int = DEFAULT_MAX_BOUNCES,
    seed: int = 7,
    seeds: int = 3,
    variant: str = "llvm_ad_rgb",
    tag: str = "korenmarkt",
) -> pathlib.Path:
    """How large a dB shift the estimator's own Monte Carlo error can fake.

    Without this the results table cannot be read. The street small cell weight
    is concentrated in the first few degrees above the horizon, so only a small
    fraction of the rays carries almost all of that model's ``chi``, and its
    estimator variance is much larger than the isotropic one's. Any crowd
    induced shift smaller than the number this writes is not a measurement of a
    crowd.

    Same standpoints, same everything, empty square, only the trace seed moves.
    """
    from ..illumination import MODELS as models
    from ..materials import classify_faces, load_table
    from .tracer import SbrTracer, TraceConfig
    from ..walk.grid import build_walk
    from ..walk.model import stratified_subset

    root = pathlib.Path(__file__).resolve().parents[2]
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    geometry = MitsubaGeometry(site_mesh(root, site, crop_m), variant=variant)
    datum = ground_datum(root, site, geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(root / "config", frequency_hz)
    walk = build_walk(geometry, ground_datum_m=datum, radius_m=90.0, spacing_m=3.0, seed=seed)
    picks = stratified_subset(walk, locations)
    config = TraceConfig(
        frequency_hz=frequency_hz, rays=rays, local_cells=local_cells, max_bounces=max_bounces, seed=seed
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    shifts: dict[str, list[float]] = {name: [] for name in models}
    for index in picks:
        point = walk.points[index]
        ground_z = float(walk.ground_z_m[index])
        reference = tracer.trace(point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index))
        for repeat in range(1, seeds):
            other = tracer.trace(point, models, ground_z_m=ground_z, seed=seed + 1000 * int(index) + 131 * repeat)
            for name in models:
                shifts[name].append(_shift_db(other.susceptibility[name], reference.susceptibility[name]))
        print(f"noise floor: {int(index)} done", flush=True)

    summary = {
        "what": "dB shift between two independent ray sets at the same standpoint, empty square",
        "locations": int(picks.size),
        "seeds_per_location": seeds,
        "rays": rays,
        "per_model": {
            name: {
                "median_abs_db": float(np.median(np.abs(values))),
                "p95_abs_db": float(np.quantile(np.abs(values), 0.95)),
                "max_abs_db": float(np.max(np.abs(values))),
            }
            for name, values in shifts.items()
        },
    }
    path = output_dir / f"{tag}_{frequency_hz / 1e9:g}ghz_noise_floor.json"
    path.write_text(json.dumps(summary, indent=2))
    print(f"wrote {path}", flush=True)
    return path


def summarise_study(rows_path: pathlib.Path) -> dict[str, Any]:
    """Median dB shift per illumination model, density and stature mode.

    Two medians, and they are not the same question. The paired one is the
    median over standpoints of that standpoint's own ratio, which says how far a
    typical pedestrian moves. The distribution one is the ratio of the two
    medians, which says how far the published CDF moves. They separate when the
    loss is concentrated in a minority of standpoints.
    """
    rows = [json.loads(line) for line in pathlib.Path(rows_path).read_text().splitlines() if line.strip()]
    baseline = {row["location"]: row for row in rows if row["kind"] == "baseline"}
    crowd_rows = [row for row in rows if row["kind"] == "crowd"]
    models = sorted(key[4:] for key in next(iter(baseline.values())) if key.startswith("chi_"))

    entries: list[dict[str, Any]] = []
    modes = sorted({row["stature_mode"] for row in crowd_rows})
    densities = sorted({row["density_per_m2"] for row in crowd_rows})
    for mode in modes:
        for density in densities:
            picked = [r for r in crowd_rows if r["stature_mode"] == mode and r["density_per_m2"] == density]
            if not picked:
                continue
            entry: dict[str, Any] = {
                "stature_mode": mode,
                "density_per_m2": density,
                "rows": len(picked),
                "bodies_median": float(np.median([r["bodies"] for r in picked])),
                "crowd_radius_m": float(np.median([r["crowd_radius_m"] for r in picked])),
                "walkable_fraction_median": float(np.median([r["walkable_fraction"] for r in picked])),
            }
            for model in models:
                for arm in ARMS:
                    # Average the realisations of a standpoint before taking the
                    # median over standpoints, so a standpoint counts once.
                    per_location: dict[int, list[float]] = {}
                    for row in picked:
                        per_location.setdefault(row["location"], []).append(row[f"chi_{arm}_{model}"])
                    paired = [
                        _shift_db(float(np.mean(values)), baseline[loc][f"chi_{model}"])
                        for loc, values in per_location.items()
                    ]
                    crowded = np.array([float(np.mean(values)) for values in per_location.values()])
                    plain = np.array([baseline[loc][f"chi_{model}"] for loc in per_location])
                    entry[f"{arm}_{model}"] = {
                        "paired_median_shift_db": float(np.median(paired)),
                        "paired_p05_shift_db": float(np.quantile(paired, 0.05)),
                        "paired_p95_shift_db": float(np.quantile(paired, 0.95)),
                        "distribution_median_shift_db": _shift_db(float(np.median(crowded)), float(np.median(plain))),
                    }
                for arm in ("walkable", "nominal"):
                    entry[f"{arm}_minus_full_db_{model}"] = (
                        entry[f"{arm}_{model}"]["paired_median_shift_db"]
                        - entry[f"full_{model}"]["paired_median_shift_db"]
                    )
            entries.append(entry)

    arriving = {
        model: {
            "below_5deg_median": float(np.median([r[f"arriving_below_5deg_{model}"] for r in baseline.values()])),
            "below_2deg_median": float(np.median([r[f"arriving_below_2deg_{model}"] for r in baseline.values()])),
        }
        for model in models
    }
    return {
        "locations": len(baseline),
        "models": models,
        "baseline_chi_median": {
            model: float(np.median([r[f"chi_{model}"] for r in baseline.values()])) for model in models
        },
        "arriving_near_horizon_share": arriving,
        "ladder": entries,
    }


def plot_study(summary: dict[str, Any], path: pathlib.Path) -> pathlib.Path:
    """Shift in median chi against crowd density, one panel per stature mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    modes = sorted({entry["stature_mode"] for entry in summary["ladder"]})
    figure, panels = plt.subplots(1, len(modes), figsize=(3.6 * len(modes) + 1.2, 3.8), sharey=True, squeeze=False)
    colours = {"isotropic": "0.35", "rooftop": "tab:blue", "street_small_cell": "tab:red"}
    for panel, mode in zip(panels[0], modes, strict=True):
        entries = sorted((e for e in summary["ladder"] if e["stature_mode"] == mode), key=lambda e: e["density_per_m2"])
        density = [e["density_per_m2"] for e in entries]
        for model in summary["models"]:
            colour = colours.get(model, None)
            panel.plot(
                density,
                [e[f"full_{model}"]["paired_median_shift_db"] for e in entries],
                "-o",
                color=colour,
                markersize=3.5,
                linewidth=1.6,
                label=f"{model}, traced crowd",
            )
            panel.plot(
                density,
                [e[f"nominal_{model}"]["paired_median_shift_db"] for e in entries],
                "--",
                color=colour,
                linewidth=1.2,
                label=f"{model}, Beer-Lambert",
            )
            panel.plot(
                density,
                [e[f"walkable_{model}"]["paired_median_shift_db"] for e in entries],
                ":",
                color=colour,
                linewidth=1.2,
                label=f"{model}, Beer-Lambert on walkable area",
            )
        for level, (module, edge) in FRUIN_WALKWAY_LOS.items():
            if min(density) <= edge <= max(density):
                panel.axvline(edge, color="0.85", linewidth=0.8, zorder=0)
                panel.annotate(
                    level, (edge, 0.02), xycoords=("data", "axes fraction"), fontsize=7, color="0.5", ha="center"
                )
        panel.axhline(0.0, color="0.6", linewidth=0.7)
        panel.set_xscale("log")
        panel.set_xlabel("crowd density (people m$^{-2}$)")
        panel.set_title(f"bystanders {mode.replace('_', ' ')}", fontsize=10)
        panel.grid(alpha=0.22)
    panels[0][0].set_ylabel("shift in median $\\chi_S$ (dB)")
    panels[0][-1].legend(fontsize=7, loc="lower left")
    figure.suptitle(
        "Korenmarkt 15 GHz: what a crowd takes off the pedestrian, Fruin walkway level of service marked",
        fontsize=10,
    )
    figure.tight_layout()
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path


def plot_mechanism(
    path: pathlib.Path,
    *,
    library: BodyLibrary,
    observer_height_m: float = 1.5,
    radius_m: float = 30.0,
    summary: dict[str, Any] | None = None,
) -> pathlib.Path:
    """Why the answer is what it is, in two panels and no traced data.

    Left, where the crowd is opaque: the Beer-Lambert factor against elevation
    for the density ladder, at both stature modes. Right, where the illumination
    is: the elevation measure of the three models, and, when a summary is
    passed, the share of ``chi`` that actually arrives from below 5 degrees once
    the square has moved the power around. The gap between those last two is the
    reason a crowd underperforms the naive prediction.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ..illumination import MODELS, elevation_band_measure, measure_below

    elevation = np.concatenate([np.linspace(0.05, 5.0, 400), np.linspace(5.0, 60.0, 200)])
    directions = np.column_stack(
        [np.cos(np.radians(elevation)), np.zeros_like(elevation), np.sin(np.radians(elevation))]
    )
    figure, (left, right) = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for mode, style in (("as_reconstructed", "--"), ("adult", "-")):
        shaped = stature_library(library, mode, seed=0)
        for density, shade in zip(DENSITY_LADDER, np.linspace(0.75, 0.0, len(DENSITY_LADDER)), strict=True):
            left.plot(
                elevation,
                crowd_transmittance(
                    directions,
                    density_per_m2=density,
                    width_m=shaped.width_m,
                    body_height_m=shaped.stature_m,
                    observer_height_m=observer_height_m,
                    radius_m=radius_m,
                ),
                style,
                color=str(shade),
                linewidth=1.2,
                label=f"{density:.2f} m$^{{-2}}$, {mode.replace('_', ' ')}" if density in DENSITY_LADDER[::5] else None,
            )
    left.set_xscale("log")
    left.set_xlabel("elevation above the horizon (deg)")
    left.set_ylabel("crowd transmittance")
    left.set_title("what a crowd is opaque to", fontsize=10)
    left.legend(fontsize=7, loc="lower right")
    left.grid(alpha=0.22)

    edges = np.concatenate([np.linspace(-90.0, 0.0, 19), np.geomspace(0.1, 90.0, 40)])
    centres = 0.5 * (edges[:-1] + edges[1:])
    colours = {"isotropic": "0.35", "rooftop": "tab:blue", "street_small_cell": "tab:red"}
    arriving = None if summary is None else summary["arriving_near_horizon_share"]
    for name, model in MODELS.items():
        measure = elevation_band_measure(model, edges)
        label = name
        if arriving is not None:
            label += (
                f"\n{100 * measure_below(model, 5.0):.0f} % sent below 5 deg, "
                f"{100 * arriving[name]['below_5deg_median']:.0f} % arrives"
            )
        right.plot(centres, measure / np.diff(edges), color=colours.get(name), linewidth=1.5, label=label)
    right.set_xlim(-10.0, 60.0)
    right.set_yscale("log")
    right.set_xlabel("elevation (deg)")
    right.set_ylabel("illumination measure per degree")
    right.set_title("where the illumination is, sent and arriving", fontsize=10)
    right.legend(fontsize=6.5, loc="upper right")
    right.grid(alpha=0.22)
    figure.tight_layout()
    path = pathlib.Path(path)
    figure.savefig(path, dpi=170)
    figure.savefig(path.with_suffix(".pdf"))
    plt.close(figure)
    return path


def main(argv: list[str] | None = None) -> int:
    import argparse

    root = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Bystander blockage study, both arms.")
    parser.add_argument("--locations", type=int, default=12)
    parser.add_argument("--realisations", type=int, default=3)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tag", default="korenmarkt")
    parser.add_argument("--target-faces", type=int, default=600)
    parser.add_argument("--max-radius-m", type=float, default=30.0)
    parser.add_argument("--mean-free-paths", type=float, default=float("inf"))
    parser.add_argument("--clothing-rms-mm", type=float, default=CLOTHING_RMS_HEIGHT_M * 1e3)
    parser.add_argument(
        "--body-absorber",
        action="store_true",
        help="make the bodies index matched absorbers, the control that removes re-illumination",
    )
    parser.add_argument("--densities", type=float, nargs="+", default=list(DENSITY_LADDER))
    parser.add_argument("--stature-modes", nargs="+", default=list(STATURE_MODES), choices=list(STATURE_MODES))
    parser.add_argument("--bodies", default=str(root / "outputs" / "korenmarkt_dynamic_bodies"))
    parser.add_argument("--output", default=str(root / "outputs" / "bystander_study"))
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--report", metavar="STEM", default=None, help="resummarise an existing run")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="keep the standpoints already fully traced, drop the partial one, and carry on",
    )
    parser.add_argument(
        "--noise-floor",
        action="store_true",
        help="measure how large a dB shift the estimator's own variance can fake, then stop",
    )
    args = parser.parse_args(argv)

    output_dir = pathlib.Path(args.output)
    stem = args.report or f"{args.tag}_{args.frequency_ghz:g}ghz"
    if args.noise_floor:
        noise_floor(
            output_dir=output_dir,
            site=args.site,
            crop_m=args.crop_m,
            frequency_hz=args.frequency_ghz * 1e9,
            locations=args.locations,
            rays=args.rays,
            local_cells=args.local_cells,
            max_bounces=args.max_bounces,
            seed=args.seed,
            variant=args.variant,
            tag=args.tag,
        )
        return 0
    if args.report is None:
        run_study(
            output_dir=output_dir,
            bodies_dir=pathlib.Path(args.bodies),
            site=args.site,
            crop_m=args.crop_m,
            frequency_hz=args.frequency_ghz * 1e9,
            locations=args.locations,
            densities=tuple(args.densities),
            realisations=args.realisations,
            rays=args.rays,
            local_cells=args.local_cells,
            max_bounces=args.max_bounces,
            seed=args.seed,
            stature_modes=tuple(args.stature_modes),
            target_faces=args.target_faces,
            max_radius_m=args.max_radius_m,
            mean_free_paths=args.mean_free_paths,
            clothing_rms_height_m=args.clothing_rms_mm * 1e-3,
            body_absorber=args.body_absorber,
            variant=args.variant,
            tag=args.tag,
            resume=args.resume,
        )
    summary = summarise_study(output_dir / f"{stem}_rows.jsonl")
    summary_path = output_dir / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    figure = plot_study(summary, output_dir / f"{stem}_shift.png")
    mechanism = plot_mechanism(
        output_dir / f"{stem}_mechanism.png",
        library=load_body_library(pathlib.Path(args.bodies), target_faces=args.target_faces),
        summary=summary,
    )
    print(f"wrote {summary_path}, {figure} and {mechanism}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
