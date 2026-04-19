"""Lightweight metamorphic-relation helpers for AEGIS.

A metamorphic relation is of the form: "if input X transforms by T,
output Y transforms by T'". We check it by running the system once on
X, once on T(X), and verifying T'(Y) vs Y_transformed.

This module intentionally avoids a heavyweight framework (e.g. GeMTest).
Each test file imports these helpers, defines a transform pair, and
asserts the relation.

Every relation implemented in tests/test_metamorphic_*.py must cite a
monograph theorem or equation that justifies it. If it cannot, the
relation is not metamorphic, it is a guess.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

T = TypeVar("T")


def rotation_matrix_from_axis_angle(axis: NDArray[np.floating], angle: float) -> NDArray[np.floating]:
    """Rodrigues' rotation formula. Returns a (3, 3) rotation matrix.

    Used by metamorphic tests to construct rotations without depending on
    scipy.spatial.transform; keeps the test file fast to import.
    """
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    c = float(np.cos(angle))
    s = float(np.sin(angle))
    K = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ],
        dtype=np.float64,
    )
    return np.eye(3) + s * K + (1.0 - c) * (K @ K)


def assert_invariant(
    y_original: NDArray[np.floating] | float,
    y_transformed: NDArray[np.floating] | float,
    *,
    rtol: float = 1e-12,
    atol: float = 1e-14,
    msg: str = "",
) -> None:
    """Assert `y_transformed == y_original` to FP tolerance.

    This is a thin wrapper over np.testing.assert_allclose that keeps
    test diagnostics consistent across metamorphic tests. If you need
    to relax tolerance, justify it in the test docstring (citing the
    source of the numerical error) -- do not hide it here.
    """
    np.testing.assert_allclose(y_transformed, y_original, rtol=rtol, atol=atol, err_msg=msg)


def metamorphic(
    input_transform: Callable[[T], T],
    output_transform: Callable[[NDArray[np.floating]], NDArray[np.floating]] | None = None,
) -> Callable[[Callable[[T], NDArray[np.floating]]], Callable[[T], None]]:
    """Decorate a `run(x) -> y` function to build a metamorphic checker.

    Given `run: x -> y`, and an `input_transform: x -> x'`, and an
    optional `output_transform: y -> y_expected`, the decorator returns
    a checker `check(x)` that asserts `run(x')` equals
    `output_transform(run(x))` (defaulting to identity, i.e. invariance).

    Example
    -------
        @metamorphic(input_transform=lambda p: scale_power(p, 2.0),
                     output_transform=lambda y: 2.0 * y)
        def run(paths):
            return engine.compute(body, paths, level=2).sab

        run(paths_original)  # runs both legs and asserts
    """

    def decorator(run: Callable[[T], NDArray[np.floating]]) -> Callable[[T], None]:
        def check(x: T) -> None:
            y = run(x)
            x_prime = input_transform(x)
            y_prime = run(x_prime)
            expected = y if output_transform is None else output_transform(y)
            assert_invariant(expected, y_prime, msg=f"metamorphic relation failed on {type(x).__name__}")

        return check

    return decorator
