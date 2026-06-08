"""Phantom landmarks and GOLIAT hand-held placement scenarios.

The phantom surface meshes carry no anatomical labels, so the head/face/belly
reference points are recovered geometrically. All four shipped phantoms (duke,
ella, eartha, thelonious) share the Virtual-Family convention verified from their
silhouettes: +z is up, x is the left-right axis, and the face/anterior direction
is -y (confirmed by the protruding toes in the foot slab).

The placements mirror the GOLIAT near-field study:

* ``front_of_eyes`` - phone in front of the face, default 200 mm from the eyes
* ``by_cheek``      - phone against the cheek/ear (calling), default 8 mm
* ``by_belly``      - phone in front of the belly (browsing), default 200 mm

Each placement yields a source position, the look direction toward the body
landmark, and the nominal stand-off distance. A :class:`PhoneSource` is then
built at any distance and orientation perturbation for the sweep.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.geometry.mesh import BodyMesh
from aegis.nearfield.patterns import AntennaPattern3D
from aegis.nearfield.phone import PhoneSource

# Nominal stand-off distances [m] from the GOLIAT placement_setup.
NOMINAL_DISTANCE_M = {
    "front_of_eyes": 0.200,
    "by_cheek": 0.008,
    "by_belly": 0.200,
}


@dataclass(frozen=True)
class BodyFrame:
    """Anatomical frame of a phantom, in mesh world coordinates."""

    up: np.ndarray  # +z
    anterior: np.ndarray  # toward the face
    left: np.ndarray  # left-right axis
    z_min: float
    z_max: float

    @property
    def height(self) -> float:
        return self.z_max - self.z_min


def detect_body_frame(mesh: BodyMesh) -> BodyFrame:
    """Recover the anatomical frame from a standing phantom mesh."""
    c = mesh.centroids
    ext = c.max(0) - c.min(0)
    up_axis = int(np.argmax(ext))  # tallest extent is the standing axis
    if up_axis != 2:
        raise ValueError(f"expected z-up phantom, got up-axis {up_axis}")
    z = c[:, 2]
    z_min, z_max = float(z.min()), float(z.max())
    zr = z_max - z_min

    # Anterior (face) direction from the foot slab: toes protrude forward.
    feet = c[z < z_min + 0.06 * zr]
    iy = int(np.argmax(np.abs(feet[:, 1])))
    anterior_sign = -1.0 if feet[iy, 1] < 0 else 1.0

    up = np.array([0.0, 0.0, 1.0])
    anterior = np.array([0.0, anterior_sign, 0.0])
    left = np.cross(anterior, up)  # right-handed: x-ish
    left /= np.linalg.norm(left)
    return BodyFrame(up=up, anterior=anterior, left=left, z_min=z_min, z_max=z_max)


def _anterior_extreme(centroids, frame: BodyFrame, z_lo: float, z_hi: float) -> np.ndarray:
    """Most anterior surface point within a z-band [z_lo, z_hi] (mesh coords)."""
    c = centroids
    band = c[(c[:, 2] >= z_lo) & (c[:, 2] <= z_hi)]
    if band.size == 0:
        band = c
    proj = band @ frame.anterior
    return band[int(np.argmax(proj))]


def _lateral_extreme(centroids, frame: BodyFrame, z_lo: float, z_hi: float, sign: float) -> np.ndarray:
    """Most lateral (left/right) surface point within a z-band (mesh coords)."""
    c = centroids
    band = c[(c[:, 2] >= z_lo) & (c[:, 2] <= z_hi)]
    if band.size == 0:
        band = c
    proj = sign * (band @ frame.left)
    return band[int(np.argmax(proj))]


@dataclass(frozen=True)
class Landmarks:
    nasion: np.ndarray  # face front near eye level
    tragus_left: np.ndarray
    tragus_right: np.ndarray
    belly: np.ndarray


def detect_landmarks(mesh: BodyMesh, frame: BodyFrame | None = None) -> Landmarks:
    """Geometric head/face/belly landmarks used to anchor the placements."""
    frame = frame or detect_body_frame(mesh)
    c = mesh.centroids
    zmin, zmax, zr = frame.z_min, frame.z_max, frame.height

    # Eye level sits a little below the crown; nasion is the face-front point.
    eye_lo, eye_hi = zmax - 0.11 * zr, zmax - 0.05 * zr
    nasion = _anterior_extreme(c, frame, eye_lo, eye_hi)

    # Tragus (ear canal) at ear height, most lateral point of the head.
    ear_lo, ear_hi = zmax - 0.13 * zr, zmax - 0.07 * zr
    tragus_left = _lateral_extreme(c, frame, ear_lo, ear_hi, +1.0)
    tragus_right = _lateral_extreme(c, frame, ear_lo, ear_hi, -1.0)

    # Belly button: anterior-most point of the lower torso.
    belly_lo, belly_hi = zmin + 0.55 * zr, zmin + 0.65 * zr
    belly = _anterior_extreme(c, frame, belly_lo, belly_hi)

    return Landmarks(nasion=nasion, tragus_left=tragus_left, tragus_right=tragus_right, belly=belly)


@dataclass(frozen=True)
class Placement:
    """A named hand-held placement: where the phone sits and which way it looks."""

    name: str
    landmark: np.ndarray  # body reference point
    look_dir: np.ndarray  # unit vector from phone toward the body
    nominal_distance_m: float

    def position(self, distance_m: float | None = None) -> np.ndarray:
        d = self.nominal_distance_m if distance_m is None else distance_m
        return self.landmark - self.look_dir * d


def standard_placements(mesh: BodyMesh) -> dict[str, Placement]:
    """The three GOLIAT placements anchored on a phantom mesh."""
    frame = detect_body_frame(mesh)
    lm = detect_landmarks(mesh, frame)
    # look_dir points from the phone toward the body. The phone sits on the
    # anterior side of the face/belly (looking posteriorly = -anterior) and on
    # the right of the head for the calling pose (looking toward the body along
    # +left, since the right ear is on the -left side).
    out = {
        "front_of_eyes": Placement("front_of_eyes", lm.nasion, -frame.anterior, NOMINAL_DISTANCE_M["front_of_eyes"]),
        "by_cheek": Placement("by_cheek", lm.tragus_right, frame.left, NOMINAL_DISTANCE_M["by_cheek"]),
        "by_belly": Placement("by_belly", lm.belly, -frame.anterior, NOMINAL_DISTANCE_M["by_belly"]),
    }
    return out


def _rotation_aligning_z_to(direction: np.ndarray) -> np.ndarray:
    """Rotation matrix taking local +z to ``direction`` (shortest arc)."""
    d = np.asarray(direction, dtype=np.float64)
    d = d / np.linalg.norm(d)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, d)
    c = float(z @ d)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0.0]])
    return np.eye(3) + vx + vx @ vx * (1.0 / (1.0 + c))


def make_source(
    placement: Placement,
    pattern: AntennaPattern3D,
    distance_m: float | None = None,
    delta_rotation: np.ndarray | None = None,
    radiated_power_w: float = 1.0,
) -> PhoneSource:
    """Build a :class:`PhoneSource` for a placement.

    The base orientation points the phone's local +z (boresight) toward the body
    landmark, the natural "device facing the user" pose. ``delta_rotation`` is an
    optional extra 3x3 rotation (applied in the world frame) used to explore
    orientation perturbations in the sweep.
    """
    base = _rotation_aligning_z_to(placement.look_dir)
    rot = base if delta_rotation is None else np.asarray(delta_rotation) @ base
    return PhoneSource(
        position=placement.position(distance_m),
        rotation=rot,
        pattern=pattern,
        radiated_power_w=radiated_power_w,
    )
