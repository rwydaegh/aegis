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

from ._paths import load_phantom

# Phantoms that have a precomputed pack on disk. Used to reject unknown meshes
# with a clean 404 before touching the filesystem.
_KNOWN_MESHES = ("thelonious",)

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


def is_known_mesh(name: str) -> bool:
    """True when ``name`` has a precomputed phantom pack."""
    return str(name) in _KNOWN_MESHES


def build_phantom_payload(
    name: str,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> tuple[bytes, dict]:
    """Pack a phantom's geometry into ``(buffer, stats)``.

    ``buffer`` is the concatenated float32/int32 arrays; ``stats`` carries an
    ``arrays`` manifest with one entry per array giving ``name``, ``dtype``,
    byte ``offset``, element ``length`` and ``shape``. Raises
    :class:`FileNotFoundError` when the pack is absent (load_phantom does).
    """
    phantom = load_phantom(name, cache, cache_lock)

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
