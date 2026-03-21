"""Tests for the array backend shim."""


def test_backend_provides_xp():
    from aegis._array_backend import xp

    # xp must be either numpy or jax.numpy
    assert hasattr(xp, "array")
    assert hasattr(xp, "sum")
    assert hasattr(xp, "maximum")


def test_backend_reports_jax_available():
    from aegis._array_backend import JAX_AVAILABLE

    assert isinstance(JAX_AVAILABLE, bool)


def test_jit_is_callable():
    from aegis._array_backend import jit

    # jit must be a callable (either jax.jit or identity)
    assert callable(jit)


def test_jit_identity_without_jax():
    """jit(f) returns a callable that behaves like f."""
    import numpy as np

    from aegis._array_backend import jit

    @jit
    def add(a, b):
        return a + b

    result = add(np.array(1.0), np.array(2.0))
    assert float(result) == 3.0


def test_erf_available():
    import numpy as np

    from aegis._array_backend import erf

    result = erf(np.array([0.0, 1.0]))
    assert abs(float(result[0])) < 1e-15
    assert abs(float(result[1]) - 0.8427) < 0.001
