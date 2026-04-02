"""Test ParametricBody wrapper for SMPL-X."""

import numpy as np
import pytest


def test_parametric_load_unknown_model():
    """Unknown model type raises ValueError."""
    from aegis.geometry.parametric import ParametricBody

    with pytest.raises(ValueError, match="Unknown model type"):
        ParametricBody.load("nonexistent")


def test_parametric_anny_not_implemented():
    """Anny model raises NotImplementedError."""
    from aegis.geometry.parametric import ParametricBody

    with pytest.raises(NotImplementedError, match="Anny model"):
        ParametricBody.load("anny")


def test_parametric_smplx_missing_import():
    """Helpful error when smplx package not installed."""
    # This test only makes sense if smplx is NOT installed.
    # If smplx IS installed, the test should be skipped.
    try:
        import smplx  # noqa: F401

        pytest.skip("smplx is installed, cannot test missing import error")
    except ImportError:
        from aegis.geometry.parametric import ParametricBody

        with pytest.raises((ImportError, FileNotFoundError)):
            ParametricBody.load("smplx")


# The following tests require smplx and model files
smplx_mod = pytest.importorskip("smplx", reason="smplx not installed")
from pathlib import Path  # noqa: E402

SMPLX_DIR = Path.home() / ".aegis" / "models" / "smplx"
has_models = SMPLX_DIR.exists()


@pytest.mark.skipif(not has_models, reason="SMPL-X model files not found")
def test_parametric_generates_mesh():
    from aegis.geometry.parametric import ParametricBody

    pb = ParametricBody.load("smplx", gender="neutral")
    body = pb.generate(betas=np.zeros(10))
    assert body.vertices.shape[1:] == (3, 3)
    assert body.normals.shape[1] == 3
    assert body.n_triangles > 0


@pytest.mark.skipif(not has_models, reason="SMPL-X model files not found")
def test_parametric_different_betas():
    from aegis.geometry.parametric import ParametricBody

    pb = ParametricBody.load("smplx", gender="neutral")
    body1 = pb.generate(betas=np.zeros(10))
    body2 = pb.generate(betas=np.array([2.0] + [0.0] * 9))
    assert not np.allclose(body1.vertices, body2.vertices)


@pytest.mark.skipif(not has_models, reason="SMPL-X model files not found")
def test_parametric_batch():
    from aegis.geometry.parametric import ParametricBody

    pb = ParametricBody.load("smplx", gender="neutral")
    betas_batch = np.random.randn(3, 10)
    bodies = pb.generate_batch(betas_batch)
    assert len(bodies) == 3
    assert all(b.n_triangles > 0 for b in bodies)
