"""Archived benchmark behind ``propagation.geometry.MitsubaGeometry.intersect``.

The cast is 2.5 percent of a trace and marshalling its result is 38 percent.

``MitsubaGeometry.intersect`` asks ``ray_intersect`` for a full
``SurfaceInteraction3f``, which computes UVs, shading frames and position
partials that this estimator never reads, and then converts ``si.t``, ``si.n``
and ``si.prim_index`` to float64 numpy one field at a time.

Three candidates, measured against the current code on the same rays, and
checked for equality rather than only for speed.

``preliminary``  ``ray_intersect_preliminary`` returns t and prim_index and
                 nothing else. The mesh is loaded with ``face_normals=True``, so
                 the normal is the geometric face normal and this class already
                 holds vertices and faces as numpy. Precompute the per face
                 normal once and index it.

``drjit_numpy``  keep the full interaction, but move the fields with
                 ``dr.numpy`` and leave them float32 until something needs
                 float64.

``both``         preliminary plus the cheaper move.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

INFINITY = 1.0e30


def timed(fn, repeats):
    fn()
    started = time.perf_counter()
    for _ in range(repeats):
        out = fn()
    return (time.perf_counter() - started) / repeats, out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=6)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--standpoint", type=float, nargs=3, default=[0.0, 0.0, 52.5])
    args = parser.parse_args()

    import mitsuba as mi

    from semantic_twin.propagation.geometry import MitsubaGeometry

    geometry = MitsubaGeometry(args.mesh, variant=args.variant)
    scene = geometry.scene

    rng = np.random.default_rng(11)
    d = rng.normal(size=(args.rays, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    o = np.tile(np.asarray(args.standpoint, dtype=np.float64), (args.rays, 1))

    v, f = geometry.vertices, geometry.faces
    edge1 = v[f[:, 1]] - v[f[:, 0]]
    edge2 = v[f[:, 2]] - v[f[:, 0]]
    face_normal = np.cross(edge1, edge2)
    face_normal /= np.linalg.norm(face_normal, axis=1, keepdims=True)

    def make_ray():
        return mi.Ray3f(mi.Point3f(np.ascontiguousarray(o.T)), mi.Vector3f(np.ascontiguousarray(d.T)))

    def current():
        si = scene.ray_intersect(make_ray())
        distance = np.array(si.t, dtype=np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        normal = np.array(si.n, dtype=np.float64).T
        face = np.array(si.prim_index, dtype=np.int64)
        return hit, np.where(hit, distance, INFINITY), normal, face

    def preliminary():
        pi = scene.ray_intersect_preliminary(make_ray())
        distance = np.array(pi.t, dtype=np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        face = np.array(pi.prim_index, dtype=np.int64)
        normal = face_normal[np.where(hit, face, 0)]
        return hit, np.where(hit, distance, INFINITY), normal, face

    def drjit_numpy():
        si = scene.ray_intersect(make_ray())
        distance = si.t.numpy().astype(np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        normal = np.ascontiguousarray(si.n.numpy().T.astype(np.float64))
        face = si.prim_index.numpy().astype(np.int64)
        return hit, np.where(hit, distance, INFINITY), normal, face

    def both():
        pi = scene.ray_intersect_preliminary(make_ray())
        distance = pi.t.numpy().astype(np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        face = pi.prim_index.numpy().astype(np.int64)
        normal = face_normal[np.where(hit, face, 0)]
        return hit, np.where(hit, distance, INFINITY), normal, face

    base_seconds, base = timed(current, args.repeats)
    print(f"{'current':14s} {base_seconds * 1000:8.1f} ms   1.00x")
    for name, fn in (("preliminary", preliminary), ("drjit_numpy", drjit_numpy), ("both", both)):
        try:
            seconds, out = timed(fn, args.repeats)
        except Exception as error:
            print(f"{name:14s} FAILED {error!r}")
            continue
        same_hit = np.array_equal(out[0], base[0])
        same_face = np.array_equal(out[3][base[0]], base[3][base[0]])
        dist = float(np.max(np.abs(out[1][base[0]] - base[1][base[0]])))
        # face normals carry no orientation convention, so compare unsigned
        dot = np.abs(np.einsum("ij,ij->i", out[2][base[0]], base[2][base[0]]))
        print(
            f"{name:14s} {seconds * 1000:8.1f} ms   {base_seconds / seconds:.2f}x   "
            f"hit={same_hit} face={same_face} max|dt|={dist:.3e} min|n.n|={float(np.min(dot)):.6f}"
        )


if __name__ == "__main__":
    main()
