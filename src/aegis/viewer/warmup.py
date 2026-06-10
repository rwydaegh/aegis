"""Boot-time JIT warm-up for the dosimetry numba kernels.

The first lab/viewer compute on a fresh worker pays ~60 s of numba JIT (the
self-shadow visibility BVH bake, the Fock gate, Fresnel, 4 cm^2 spatial
averaging). Running one tiny synthetic compute at worker start moves that cost
off the first real request and onto worker boot, where it is invisible to users.

With ``NUMBA_CACHE_DIR`` on a persistent volume the compiled kernels survive
container recreation, so after the first boot this is a fast cache load rather
than a recompile. Compiling here (on the real host) rather than at image-build
time also avoids an illegal-instruction mismatch: the image is built on a
different CPU than it runs on.

The warm-up mesh is deliberately NON-CONVEX so the self-shadow bake (the most
expensive kernel) actually compiles instead of hitting the convex short-circuit
in ``geometry.visibility._is_convex``.
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np

logger = logging.getLogger(__name__)

# Icosahedron topology (12 vertices, 20 faces).
_PHI = (1.0 + 5.0**0.5) / 2.0
_ICO_VERTS = np.array(
    [
        [-1, _PHI, 0], [1, _PHI, 0], [-1, -_PHI, 0], [1, -_PHI, 0],
        [0, -1, _PHI], [0, 1, _PHI], [0, -1, -_PHI], [0, 1, -_PHI],
        [_PHI, 0, -1], [_PHI, 0, 1], [-_PHI, 0, -1], [-_PHI, 0, 1],
    ],
    dtype=np.float64,
)  # fmt: skip
_ICO_FACES = np.array(
    [
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ]
)  # fmt: skip


def _warmup_mesh():
    """Two separated limb-scale icosahedra: clearly non-convex (the hull bridges
    the gap), and the two blobs genuinely shadow one another, so the distal
    self-shadow bake runs instead of the convex short-circuit."""
    from aegis.geometry.mesh import BodyMesh

    unit = (_ICO_VERTS / np.linalg.norm(_ICO_VERTS, axis=1, keepdims=True)) * 0.08  # ~8 cm
    left = unit + np.array([-0.12, 0.0, 0.0])
    right = unit + np.array([0.12, 0.0, 0.0])
    verts = np.vstack([left, right])
    faces = np.vstack([_ICO_FACES, _ICO_FACES + len(unit)])
    return BodyMesh.from_arrays(verts[faces], name="warmup")


def warm_kernels() -> None:
    """Run one far-field and one near-field compute to trigger all hot JITs."""
    t0 = time.perf_counter()
    try:
        from aegis.engine import DosimetryEngine
        from aegis.nearfield import phone
        from aegis.paths import PropagationPaths
        from aegis.viewer.compute import resolve_skin_model
        from aegis.viewer.routes.lab._patterns import get_pattern

        body = _warmup_mesh()
        freq_hz = 3.5e9
        tissue = resolve_skin_model("itis", freq_hz)

        # Far-field spatial path: Fresnel + Fock + curvature + 4 cm^2 averaging.
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.5, 0.0, 0.866]]),
            power=np.array([1.0]),
            polarisation=np.array([[0.866, 0.0, -0.5]]),
        )
        DosimetryEngine(tissue).compute(
            body,
            paths,
            mode="spatial",
            freq_hz=freq_hz,
            fresnel=True,
            polarisation=True,
            self_shadow=False,
            diffraction_model="fock",
            spatial_averaging=True,
        )

        # Near-field path: the distal self-shadow visibility BVH bake (the mesh is
        # non-convex, so this is the real ray-cast bake, not the convex no-op).
        pat = get_pattern("dipole", freq_hz / 1e6)
        pos = np.array([0.25, 0.0, 0.1])
        src = phone.PhoneSource.from_euler(
            position=pos, pattern=pat, yaw=0.0, pitch=0.0, roll=0.0, radiated_power_w=1.0
        )
        phone.compute_sab(
            body.centroids,
            body.normals,
            src,
            t0=tissue.T0,
            n_tilde=tissue.n_complex,
            fresnel=True,
            body=body,
            diffraction_model="fock",
            self_shadow=True,
            source_pos=pos,
        )
        logger.info("dosimetry kernel warm-up done in %.1fs", time.perf_counter() - t0)
    except Exception as exc:  # best-effort: never let warm-up crash a worker
        logger.warning("dosimetry kernel warm-up skipped: %s", exc)


def warm_kernels_async() -> None:
    """Warm in a daemon thread so the worker serves /api/health immediately."""
    threading.Thread(target=warm_kernels, name="numba-warmup", daemon=True).start()
