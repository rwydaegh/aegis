"""Phantom mesh geometry serving for the Coherent Exposure Studio.

Packs the phantom geometry (vertices, faces, centroids, normals) into a single
binary buffer so the frontend can build a THREE.BufferGeometry and colour it
per-triangle. The layout is described by an ``arrays`` manifest carried in the
X-Stats header (the same multi-array convention compute/lab use), so the client
slices each array out of one octet-stream body. Fork-free.
"""

from __future__ import annotations

import threading

import numpy as np

from ._channel import DEFAULT_UE_IDX
from ._config import available_packs
from ._paths import load_phantom

# Each geometry array ships as a contiguous slice of the binary buffer. Floats
# go out as float32 (THREE.BufferAttribute defaults), faces as int32 indices.
_ARRAY_DTYPES = {
    "vertices": np.float32,
    "faces": np.int32,
    "centroids": np.float32,
    "normals": np.float32,
}
# Buffer order. Vertices first (the bulk of the payload) keeps the manifest
# stable as we add optional arrays later.
_ARRAY_ORDER = ("vertices", "faces", "centroids", "normals")


def known_meshes() -> tuple[str, ...]:
    """Base phantoms with a precomputed geometry pack on disk (sorted).

    Per-UE phantom packs carry a ``_ue{idx}`` suffix on the same mesh name; they
    are alternate standing positions of an already-known mesh, not new meshes, so
    they are filtered out here. The mesh selector lists only the base phantoms
    (thelonious / duke / eartha / ella).
    """
    return tuple(p for p in available_packs().get("phantom", []) if "_ue" not in p)


def is_known_mesh(name: str) -> bool:
    """True when ``name`` has a precomputed phantom pack.

    Derived from the phantom packs present so a newly built phantom is picked
    up without editing a static list.
    """
    return str(name) in known_meshes()


def snap_focus_to_skin(
    focus_xyz,
    name: str = "thelonious",
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
    ue_idx: int = DEFAULT_UE_IDX,
):
    """Project a focus point onto the nearest body-surface triangle centroid.

    The phantom centroids ship in the same e11 world frame (Z-up metres) as the
    focus, so the snap is a plain nearest-centroid search. Returns the snapped
    point as a length-3 float list. Raises :class:`FileNotFoundError` when the
    phantom pack is absent (load_phantom does), which the caller surfaces as the
    not-precomputed sentinel. ``ue_idx`` selects the corridor standing position,
    so the snap follows the body when the UE slider moves it.
    """
    focus = np.asarray(focus_xyz, dtype=float).reshape(3)
    phantom = load_phantom(name, cache, cache_lock, ue_idx)
    centroids = np.asarray(phantom["centroids"], dtype=float)
    d2 = np.einsum("ij,ij->i", centroids - focus, centroids - focus)
    nearest = centroids[int(np.argmin(d2))]
    return [float(nearest[0]), float(nearest[1]), float(nearest[2])]


def focus_surface_normal(
    focus_xyz,
    name: str = "thelonious",
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
    ue_idx: int = DEFAULT_UE_IDX,
):
    """Outward normal of the body triangle nearest ``focus_xyz`` (length-3 array).

    Used by the worst-case-absorption beam to build the tissue channel at the
    snapped focus. Same nearest-centroid search as :func:`snap_focus_to_skin`,
    so a focus already snapped at-skin resolves to its own triangle's normal.
    ``ue_idx`` selects the corridor standing position.
    """
    focus = np.asarray(focus_xyz, dtype=float).reshape(3)
    phantom = load_phantom(name, cache, cache_lock, ue_idx)
    centroids = np.asarray(phantom["centroids"], dtype=float)
    normals = np.asarray(phantom["normals"], dtype=float)
    d2 = np.einsum("ij,ij->i", centroids - focus, centroids - focus)
    return normals[int(np.argmin(d2))].astype(float)


def build_phantom_payload(
    name: str,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
    ue_idx: int = DEFAULT_UE_IDX,
) -> tuple[bytes, dict]:
    """Pack a phantom's geometry into ``(buffer, stats)``.

    ``buffer`` is the concatenated float32/int32 arrays; ``stats`` carries an
    ``arrays`` manifest with one entry per array giving ``name``, ``dtype``,
    byte ``offset``, element ``length`` and ``shape``. Raises
    :class:`FileNotFoundError` when the pack is absent (load_phantom does).
    ``ue_idx`` selects the corridor standing position, so the served geometry
    sits where the UE slider placed the body.
    """
    phantom = load_phantom(name, cache, cache_lock, ue_idx)

    buf = bytearray()
    arrays_meta = []
    for key in _ARRAY_ORDER:
        arr = np.ascontiguousarray(phantom[key], dtype=_ARRAY_DTYPES[key])
        arr_bytes = arr.tobytes()
        arrays_meta.append(
            {
                "name": key,
                "dtype": str(arr.dtype),
                "offset": len(buf),
                "length": int(arr.size),
                "shape": list(arr.shape),
            }
        )
        buf.extend(arr_bytes)

    stats = {
        "mesh": str(name),
        "arrays": arrays_meta,
        "n_vertices": int(phantom["vertices"].shape[0]),
        "n_faces": int(phantom["faces"].shape[0]),
        "frame": "e11 world (Z-up, metres)",
        "provenance": f"studio phantom | {name}",
    }
    return bytes(buf), stats
