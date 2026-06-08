"""Body mesh loading and triangle geometry."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def load_stl_binary(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a binary STL file.

    Uses vectorized numpy reads instead of per-triangle struct.unpack,
    giving ~50-100x speedup on large meshes (100k+ triangles).

    Returns
    -------
    vertices : (N, 3, 3)
        Triangle vertices.
    normals : (N, 3)
        Unit triangle normals.
    centroids : (N, 3)
        Triangle centroids.
    """
    path = Path(path)
    with path.open("rb") as f:
        f.read(80)  # header
        num_triangles = struct.unpack("<I", f.read(4))[0]
        data = f.read()

    # Binary STL: each triangle is 50 bytes
    # 12 bytes normal (3x float32) + 36 bytes vertices (9x float32) + 2 bytes attr
    record_bytes = 50
    expected = num_triangles * record_bytes
    if len(data) < expected:
        raise ValueError(
            f"STL file truncated: expected {expected} bytes for {num_triangles} triangles, got {len(data)}"
        )

    # Build a structured dtype matching the STL record layout
    dt = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("v0", "<f4", (3,)),
            ("v1", "<f4", (3,)),
            ("v2", "<f4", (3,)),
            ("attr", "<u2"),
        ]
    )
    records = np.frombuffer(data[:expected], dtype=dt)

    normals = records["normal"].astype(np.float64)
    vertices = np.stack([records["v0"], records["v1"], records["v2"]], axis=1).astype(np.float64)

    centroids = np.mean(vertices, axis=1)

    # Normalize normals. Recompute from vertices if STL normal is zero.
    n_norm = np.linalg.norm(normals, axis=1, keepdims=True)
    bad = n_norm[:, 0] <= 0
    if np.any(bad):
        v0 = vertices[bad, 0]
        v1 = vertices[bad, 1]
        v2 = vertices[bad, 2]
        nn = np.cross(v1 - v0, v2 - v0)
        nn_norm = np.linalg.norm(nn, axis=1, keepdims=True)
        nn = nn / np.where(nn_norm > 0, nn_norm, 1.0)
        normals[bad] = nn
        # Only recompute norms for the fixed subset
        n_norm[bad] = np.linalg.norm(normals[bad], axis=1, keepdims=True)

    normals = normals / np.where(n_norm > 0, n_norm, 1.0)

    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute area of each triangle from a (N, 3, 3) vertex array."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


@dataclass(frozen=True)
class BodyMesh:
    """Triangulated body surface mesh.

    All arrays are read-only views after construction.

    Attributes
    ----------
    vertices : (N, 3, 3) triangle vertices
    normals : (N, 3) unit outward normals
    centroids : (N, 3) triangle centroids
    areas : (N,) triangle areas in mesh units squared
    """

    vertices: np.ndarray = field(repr=False)
    normals: np.ndarray = field(repr=False)
    centroids: np.ndarray = field(repr=False)
    areas: np.ndarray = field(repr=False)
    name: str = ""
    _geometry_hash: int = field(default=0, repr=False, compare=False)
    _bbox_cache: tuple[np.ndarray, np.ndarray] | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        normals = np.asarray(self.normals, dtype=np.float64)
        if normals.shape != (self.vertices.shape[0], 3):
            raise ValueError(f"normals must be ({self.vertices.shape[0]}, 3), got {normals.shape}")
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        # Degenerate triangles (zero-area) produce zero normals from cross
        # products. Assign a fallback direction so downstream code always sees
        # unit normals. These triangles have zero area and contribute nothing
        # to integrated quantities, so the direction is irrelevant.
        zero = norms[:, 0] <= 0
        if normals.shape[0] > 0 and np.any(zero):
            normals = normals.copy()
            normals[zero] = [0.0, 0.0, 1.0]
            norms[zero] = 1.0
        normalized = normals / norms
        object.__setattr__(self, "normals", normalized)
        if self._geometry_hash == 0:
            object.__setattr__(self, "_geometry_hash", self._compute_geometry_hash())

    def _compute_geometry_hash(self) -> int:
        """Rigid-transform-invariant content hash of the mesh for cache keying.

        Uses sorted per-triangle edge lengths plus areas. Both are stable
        under translation and rotation up to float32 precision, so moved or
        yawed copies of the same mesh hit caches (e.g. the spatial averaging
        matrix G) instead of triggering expensive rebuilds. Subtracting the
        mean centroid before hashing is not robust: near-zero residuals
        collect enough float64 noise that tiny FP differences cross float32
        quantization boundaries, producing spurious cache misses.
        """
        edge_vecs = np.roll(self.vertices, -1, axis=1) - self.vertices
        edge_lengths = np.sort(np.linalg.norm(edge_vecs, axis=2), axis=1)
        h = hashlib.sha256(self.areas.astype(np.float32).tobytes())
        h.update(edge_lengths.astype(np.float32).tobytes())
        digest = h.digest()[:8]
        return hash((int.from_bytes(digest, "little"), self.n_triangles))

    @property
    def geometry_hash(self) -> int:
        return self._geometry_hash

    @property
    def vertex_hash(self) -> int:
        """Pose-dependent content hash of the raw vertices.

        Distinct from ``geometry_hash`` (rigid-invariant). Visibility is
        direction-dependent, so a yawed body must miss the cache. Quantized to
        float32 so float64 round-off does not spuriously change the key.
        """
        h = hashlib.sha256(np.ascontiguousarray(self.vertices, dtype=np.float32).tobytes())
        return hash((int.from_bytes(h.digest()[:8], "little"), self.n_triangles))

    @classmethod
    def from_arrays(
        cls,
        vertices: np.ndarray,
        normals: np.ndarray | None = None,
        name: str = "synthetic",
    ) -> BodyMesh:
        """Create a BodyMesh from raw vertex arrays.

        Centroids and areas are computed automatically. If normals are not
        provided, they are computed from the vertex cross product.

        Parameters
        ----------
        vertices : (N, 3, 3) triangle vertices
        normals : (N, 3) unit outward normals, or None to compute from vertices
        name : mesh name
        """
        vertices = np.asarray(vertices, dtype=np.float64)
        if vertices.ndim != 3 or vertices.shape[1:] != (3, 3):
            raise ValueError(f"vertices must be (N, 3, 3), got {vertices.shape}")

        centroids = np.mean(vertices, axis=1)
        areas = triangle_areas(vertices)

        if normals is None:
            v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
            cross = np.cross(v1 - v0, v2 - v0)
            norms = np.linalg.norm(cross, axis=1, keepdims=True)
            normals = cross / np.where(norms > 0, norms, 1.0)
        else:
            normals = np.asarray(normals, dtype=np.float64)
            if normals.shape != (vertices.shape[0], 3):
                raise ValueError(f"normals must be ({vertices.shape[0]}, 3), got {normals.shape}")

        return cls(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name=name)

    @classmethod
    def sphere(cls, radius: float = 1.0, n_subdivisions: int = 2) -> BodyMesh:
        """Create a sphere mesh via icosphere subdivision.

        Parameters
        ----------
        radius : float
            Sphere radius. Must be positive.
        n_subdivisions : int
            Number of subdivision iterations. 0 gives a bare icosahedron (20
            triangles). Each iteration multiplies the triangle count by 4.
        """
        if radius <= 0.0:
            raise ValueError("radius must be positive")
        if n_subdivisions < 0:
            raise ValueError("n_subdivisions must be non-negative")

        # Regular icosahedron vertices on unit sphere
        phi = (1.0 + np.sqrt(5.0)) / 2.0
        raw = np.array(
            [
                [-1, phi, 0],
                [1, phi, 0],
                [-1, -phi, 0],
                [1, -phi, 0],
                [0, -1, phi],
                [0, 1, phi],
                [0, -1, -phi],
                [0, 1, -phi],
                [phi, 0, -1],
                [phi, 0, 1],
                [-phi, 0, -1],
                [-phi, 0, 1],
            ],
            dtype=np.float64,
        )
        verts = raw / np.linalg.norm(raw, axis=1, keepdims=True)

        # 20 icosahedron faces (CCW outward winding)
        faces = np.array(
            [
                [0, 11, 5],
                [0, 5, 1],
                [0, 1, 7],
                [0, 7, 10],
                [0, 10, 11],
                [1, 5, 9],
                [5, 11, 4],
                [11, 10, 2],
                [10, 7, 6],
                [7, 1, 8],
                [3, 9, 4],
                [3, 4, 2],
                [3, 2, 6],
                [3, 6, 8],
                [3, 8, 9],
                [4, 9, 5],
                [2, 4, 11],
                [6, 2, 10],
                [8, 6, 7],
                [9, 8, 1],
            ],
            dtype=np.int64,
        )

        # Subdivide
        for _ in range(n_subdivisions):
            new_faces = []
            midpoint_cache: dict[tuple[int, int], int] = {}
            vert_list = list(verts)

            def _get_midpoint(
                a: int,
                b: int,
                cache: dict = midpoint_cache,
                vl: list = vert_list,
            ) -> int:
                key = (min(a, b), max(a, b))
                if key in cache:
                    return cache[key]
                mid = (np.array(vl[a]) + np.array(vl[b])) / 2.0
                mid = mid / np.linalg.norm(mid)
                idx = len(vl)
                vl.append(mid)
                cache[key] = idx
                return idx

            for f in faces:
                a, b, c = int(f[0]), int(f[1]), int(f[2])
                ab = _get_midpoint(a, b)
                bc = _get_midpoint(b, c)
                ca = _get_midpoint(c, a)
                new_faces.extend([[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]])
            faces = np.array(new_faces, dtype=np.int64)
            verts = np.array(vert_list, dtype=np.float64)

        # Scale and build (N, 3, 3) vertex array
        verts = verts * radius
        vertices = verts[faces]  # (N, 3, 3)
        return cls.from_arrays(vertices, name="sphere")

    @classmethod
    def cylinder(
        cls,
        radius: float = 1.0,
        height: float = 1.0,
        n_segments: int = 32,
    ) -> BodyMesh:
        """Create a capped cylinder mesh aligned along the z-axis.

        The cylinder spans from z = -height/2 to z = +height/2.

        Parameters
        ----------
        radius : float
            Cylinder radius. Must be positive.
        height : float
            Cylinder height. Must be positive.
        n_segments : int
            Number of azimuthal divisions. Must be >= 3.
        """
        if radius <= 0.0:
            raise ValueError("radius must be positive")
        if height <= 0.0:
            raise ValueError("height must be positive")
        if n_segments < 3:
            raise ValueError("n_segments must be at least 3")

        angles = np.linspace(0.0, 2.0 * np.pi, n_segments, endpoint=False)
        cos_a = np.cos(angles)
        sin_a = np.sin(angles)

        z_top = height / 2.0
        z_bot = -height / 2.0

        # Ring vertices: top and bottom circles
        top_ring = np.stack([radius * cos_a, radius * sin_a, np.full(n_segments, z_top)], axis=1)
        bot_ring = np.stack([radius * cos_a, radius * sin_a, np.full(n_segments, z_bot)], axis=1)

        n = n_segments
        side_tris = np.empty((2 * n, 3, 3), dtype=np.float64)
        for i in range(n):
            j = (i + 1) % n
            # Two triangles per quad, CCW outward winding
            side_tris[2 * i] = [top_ring[i], bot_ring[i], bot_ring[j]]
            side_tris[2 * i + 1] = [top_ring[i], bot_ring[j], top_ring[j]]

        # Top cap: fan from center (0, 0, z_top), CCW when viewed from +z
        top_center = np.array([0.0, 0.0, z_top])
        top_tris = np.empty((n, 3, 3), dtype=np.float64)
        for i in range(n):
            j = (i + 1) % n
            top_tris[i] = [top_center, top_ring[i], top_ring[j]]

        # Bottom cap: fan from center (0, 0, z_bot), CCW when viewed from -z
        bot_center = np.array([0.0, 0.0, z_bot])
        bot_tris = np.empty((n, 3, 3), dtype=np.float64)
        for i in range(n):
            j = (i + 1) % n
            bot_tris[i] = [bot_center, bot_ring[j], bot_ring[i]]

        vertices = np.concatenate([side_tris, top_tris, bot_tris], axis=0)
        return cls.from_arrays(vertices, name="cylinder")

    @staticmethod
    def load(path: str | Path, name: str | None = None) -> BodyMesh:
        """Load a binary STL file and return a BodyMesh."""
        path = Path(path)
        vertices, normals, centroids = load_stl_binary(path)
        areas = triangle_areas(vertices)
        if name is None:
            name = path.stem
        return BodyMesh(
            vertices=vertices,
            normals=normals,
            centroids=centroids,
            areas=areas,
            name=name,
        )

    @property
    def n_triangles(self) -> int:
        return self.vertices.shape[0]

    @property
    def total_area(self) -> float:
        return float(np.sum(self.areas))

    @property
    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (bmin, bmax) of the mesh, cached after first access."""
        if self._bbox_cache is None:
            flat = self.vertices.reshape(-1, 3)
            object.__setattr__(self, "_bbox_cache", (np.min(flat, axis=0), np.max(flat, axis=0)))
        return self._bbox_cache

    @property
    def center(self) -> np.ndarray:
        bmin, bmax = self.bounding_box
        return (bmin + bmax) / 2.0

    @property
    def height(self) -> float:
        bmin, bmax = self.bounding_box
        return float(bmax[2] - bmin[2])

    @property
    def scale(self) -> float:
        """Bounding box diagonal length."""
        bmin, bmax = self.bounding_box
        return float(np.linalg.norm(bmax - bmin))

    def save_binary_stl(self, path: str | Path) -> None:
        """Write a binary STL (little-endian float32) for this mesh.

        Uses vectorized numpy writes for speed on large meshes.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        n = self.n_triangles
        header = b"AEGIS BodyMesh" + b"\0" * (80 - 14)

        dt = np.dtype(
            [
                ("normal", "<f4", (3,)),
                ("v0", "<f4", (3,)),
                ("v1", "<f4", (3,)),
                ("v2", "<f4", (3,)),
                ("attr", "<u2"),
            ]
        )
        records = np.zeros(n, dtype=dt)
        records["normal"] = self.normals.astype(np.float32)
        records["v0"] = self.vertices[:, 0].astype(np.float32)
        records["v1"] = self.vertices[:, 1].astype(np.float32)
        records["v2"] = self.vertices[:, 2].astype(np.float32)

        with path.open("wb") as f:
            f.write(header)
            f.write(struct.pack("<I", n))
            f.write(records.tobytes())

    def __repr__(self) -> str:
        return f"BodyMesh(name={self.name!r}, n_triangles={self.n_triangles}, total_area={self.total_area:.6g})"
