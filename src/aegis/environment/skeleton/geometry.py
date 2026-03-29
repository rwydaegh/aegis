"""Vector helpers and geometry primitives for the straight skeleton."""

from __future__ import annotations

from itertools import cycle, islice, tee

import numpy as np

EPSILON = 0.00001
PARALLEL = 0.01  # 1-cos(alpha) threshold for parallel detection


# ---------------------------------------------------------------------------
# Vector helpers (replace mathutils)
# ---------------------------------------------------------------------------


def _vec2(x: float, y: float) -> np.ndarray:
    return np.array([x, y], dtype=np.float64)


def _magnitude(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def _normalize(v: np.ndarray) -> np.ndarray:
    m = _magnitude(v)
    if m == 0.0:
        return v.copy()
    return v / m


def _cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _dot(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _vec_eq(a: np.ndarray, b: np.ndarray) -> bool:
    return np.allclose(a, b, atol=1e-10)


def _approximately_equals(a: np.ndarray, b: np.ndarray) -> bool:
    diff = _magnitude(a - b)
    return diff <= max(_magnitude(a), _magnitude(b)) * 0.001


def _robust_float_equal(f1: float, f2: float) -> bool:
    if abs(f1 - f2) <= EPSILON:
        return True
    return abs(f1 - f2) <= EPSILON * max(abs(f1), abs(f2))


# ---------------------------------------------------------------------------
# Geometry primitives (replace bpyeuclid)
# ---------------------------------------------------------------------------


def _ccw(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> bool:
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


def _intersect_line2_line2(a_obj, b_obj):
    d = b_obj.v[1] * a_obj.v[0] - b_obj.v[0] * a_obj.v[1]
    if d == 0:
        return None

    dy = a_obj.p[1] - b_obj.p[1]
    dx = a_obj.p[0] - b_obj.p[0]
    ua = (b_obj.v[0] * dy - b_obj.v[1] * dx) / d
    if not a_obj.intsecttest(ua):
        return None
    ub = (a_obj.v[0] * dy - a_obj.v[1] * dx) / d
    if not b_obj.intsecttest(ub):
        return None

    return _vec2(a_obj.p[0] + ua * a_obj.v[0], a_obj.p[1] + ua * a_obj.v[1])


class Edge2:
    def __init__(self, p1, p2, norm=None, verts=None, center=None):
        if center is None:
            center = _vec2(0.0, 0.0)
        if verts is not None:
            self.i1 = p1
            self.i2 = p2
            p1_v = np.asarray(verts[p1], dtype=np.float64) - np.asarray(center, dtype=np.float64)
            p2_v = np.asarray(verts[p2], dtype=np.float64) - np.asarray(center, dtype=np.float64)
            p1 = _vec2(p1_v[0], p1_v[1])
            p2 = _vec2(p2_v[0], p2_v[1])
        else:
            p1 = np.asarray(p1, dtype=np.float64)
            p2 = np.asarray(p2, dtype=np.float64)
            p1 = _vec2(p1[0], p1[1])
            p2 = _vec2(p2[0], p2[1])

        self.p1 = p1
        self.p2 = p2
        if norm is not None:
            self.norm = _vec2(norm[0], norm[1])
        else:
            n = self.p2 - self.p1
            self.norm = _normalize(n)

    def length_squared(self):
        d = self.p2 - self.p1
        return _dot(d, d)


class Ray2:
    def __init__(self, p, v):
        self.p = p.copy()
        self.p1 = p.copy()
        self.p2 = p + v
        self.v = v.copy()

    def intsecttest(self, u):
        return u >= 0.0

    def intersect(self, other):
        return _intersect_line2_line2(self, other)


class Line2:
    def __init__(self, p1, p2=None, ptype=None):
        if p2 is None:
            # p1 is an Edge2, Ray2, or Line2
            self.p = p1.p1.copy()
            self.v = (p1.p2 - p1.p1).copy()
        elif ptype == "pp":
            self.p = p1.p.copy()
            self.v = p2 - p1
        elif ptype == "pv":
            self.p = p1.copy()
            self.v = p2.copy()
        else:
            # default: two points
            self.p = np.asarray(p1, dtype=np.float64).copy()
            self.v = (np.asarray(p2, dtype=np.float64) - self.p).copy()
        self.p1 = self.p
        self.p2 = self.p + self.v

    def intsecttest(self, u):
        return True

    def intersect(self, other):
        return _intersect_line2_line2(self, other)

    def distance(self, other):
        # other is a point (numpy array)
        d = self.v
        dd = _dot(d, d)
        if dd == 0.0:
            return _magnitude(other - self.p)
        t = _dot(other - self.p, d) / dd
        nearest = self.p + t * d
        return _magnitude(other - nearest)


def _fit_circle_3_points(points):
    n = len(points)
    x = complex(points[0][0], points[0][1])
    y = complex(points[n // 2][0], points[n // 2][1])
    z = complex(points[-1][0], points[-1][1])
    w = z - x
    w /= y - x
    c = (x - y) * (w - abs(w) ** 2) / 2j / w.imag - x
    x0 = -c.real
    y0 = -c.imag
    r = abs(c + x)
    return _vec2(x0, y0), r


# ---------------------------------------------------------------------------
# Circular iteration helpers
# ---------------------------------------------------------------------------


def _iter_circular_prev_next(lst):
    prevs, nexts = tee(lst)
    prevs = islice(cycle(prevs), len(lst) - 1, None)
    return zip(prevs, nexts, strict=False)


def _iter_circular_prev_this_next(lst):
    prevs, this, nexts = tee(lst, 3)
    prevs = islice(cycle(prevs), len(lst) - 1, None)
    nexts = islice(cycle(nexts), 1, None)
    return zip(prevs, this, nexts, strict=False)
