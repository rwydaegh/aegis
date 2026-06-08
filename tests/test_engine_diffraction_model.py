"""Engine integration tests for the diffraction_model selector and Fock radius.

These cover Task 7 of the Fock framework: engine.compute exposes
``diffraction_model`` (default "fock"), sources the in-plane radius from
geometry.curvature, and threads the radius plus the representative
impedance-corrected hard eigenvalue into the incoherent and coherent kernels.

Note on the fixtures: levels 2-5 do not have a shadow gate, so the model is a
no-op there (only level 6 consumes it on the legacy level path). The
"default differs from none" assertions therefore use level 6 and the spatial
mode, which are the incoherent paths that actually apply the gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import make_icosahedron

from aegis.engine import DosimetryEngine
from aegis.geometry import curvature as curvature_mod
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def body():
    return make_icosahedron()


@pytest.fixture
def paths():
    """Several plane waves so some faces sit near the shadow terminator."""
    rng = np.random.default_rng(7)
    n = 12
    k = rng.standard_normal((n, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    power = rng.uniform(0.2, 1.5, size=n)
    return PropagationPaths.from_powers(k_hat=k, power=power)


def _coherent_paths(m_ant: int = 4, n: int = 8, seed: int = 3):
    rng = np.random.default_rng(seed)
    k = rng.standard_normal((n, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    psi = rng.standard_normal((n, 3)) + 1j * rng.standard_normal((n, 3))
    for i in range(n):
        psi[i] -= np.dot(psi[i], k[i]) * k[i]
    # Cover every element so paths.n_elements == m_ant (matches len(x)).
    element_index = np.arange(n) % m_ant
    paths = PropagationPaths(
        k_hat=k,
        psi=psi,
        element_index=element_index,
        delay=np.zeros(n),
        is_los=np.ones(n, dtype=bool),
    )
    x = rng.standard_normal(m_ant) + 1j * rng.standard_normal(m_ant)
    return paths, Precoder(x=x)


def test_compute_default_is_fock(engine, body, paths):
    """No diffraction args -> the engine applies the Fock gate by default."""
    default = engine.compute(body, paths, level=6)
    none = engine.compute(body, paths, level=6, diffraction_model="none")
    assert np.all(default.sab >= -1e-12)
    assert np.all(np.isfinite(default.sab))
    # Fock differs from the bare ReLU near the terminators.
    assert not np.allclose(default.sab, none.sab)


def test_compute_default_is_fock_spatial(engine, body, paths):
    """The spatial mode is fock by default too, and records the correction."""
    default = engine.compute(body, paths, mode="spatial")
    none = engine.compute(body, paths, mode="spatial", diffraction_model="none")
    assert np.all(default.sab >= -1e-12)
    assert "diffraction" in default.corrections
    assert not np.allclose(default.sab, none.sab)


@pytest.mark.parametrize("model", ["none", "gelu", "fock"])
def test_compute_accepts_diffraction_model_incoherent(engine, body, paths, model):
    res = engine.compute(body, paths, level=3, diffraction_model=model)
    assert np.all(np.isfinite(res.sab))
    assert np.all(res.sab >= -1e-12)


@pytest.mark.parametrize("model", ["none", "gelu", "fock"])
def test_compute_accepts_diffraction_model_coherent(engine, body, model):
    coh_paths, precoder = _coherent_paths()
    res = engine.compute(body, coh_paths, level=7, precoder=precoder, diffraction_model=model)
    assert np.all(np.isfinite(res.sab))
    assert np.all(res.sab >= -1e-12)


def test_explicit_model_overrides_bool(engine, body, paths):
    """An explicit diffraction_model wins over the legacy diffraction bool."""
    a = engine.compute(body, paths, level=6, diffraction_model="none", diffraction=True)
    b = engine.compute(body, paths, level=6, diffraction_model="none")
    np.testing.assert_array_equal(a.sab, b.sab)


def test_legacy_bool_true_is_fock_at_engine(engine, body, paths):
    """At the engine layer the legacy bool maps True->fock, False->none."""
    a = engine.compute(body, paths, level=6, diffraction=True)
    b = engine.compute(body, paths, level=6, diffraction_model="fock")
    np.testing.assert_allclose(a.sab, b.sab)

    c = engine.compute(body, paths, level=6, diffraction=False)
    d = engine.compute(body, paths, level=6, diffraction_model="none")
    np.testing.assert_allclose(c.sab, d.sab)


def test_fock_radius_sourced_from_geometry(engine, body, paths, monkeypatch):
    """The engine pulls the in-plane radius from geometry.curvature.fock_radius."""
    calls: list = []
    real = curvature_mod.fock_radius

    def spy(b, k_hat, *args, **kwargs):
        calls.append(np.asarray(k_hat))
        return real(b, k_hat, *args, **kwargs)

    monkeypatch.setattr(curvature_mod, "fock_radius", spy)

    engine.compute(body, paths, level=6, diffraction_model="fock")
    assert calls, "engine should source fock_R from geometry.curvature.fock_radius"

    calls.clear()
    engine.compute(body, paths, level=6, diffraction_model="none")
    assert not calls, "the 'none' model must not compute a Fock radius"


def test_inter_body_specular1_runs(engine, body, paths):
    """specular1 is implemented: it returns a finite, non-negative map that is
    at least as large as the direct law (recapture only adds power)."""
    off = engine.compute(body, paths, level=3, inter_body="off").sab
    on = engine.compute(body, paths, level=3, inter_body="specular1").sab
    assert np.all(np.isfinite(on))
    assert np.all(on >= 0.0)
    assert np.all(on >= off - 1e-12)


def test_compute_sab_inter_body_specular1_ignored(engine, body, paths):
    """compute_sab accepts specular1 but ignores it (non-differentiable pass)."""
    base = np.asarray(engine.compute_sab(body, paths, level=3, inter_body="off"))
    same = np.asarray(engine.compute_sab(body, paths, level=3, inter_body="specular1"))
    np.testing.assert_array_equal(base, same)


def test_invalid_diffraction_model_rejected(engine, body, paths):
    with pytest.raises(ValueError, match="diffraction_model"):
        engine.compute(body, paths, level=3, diffraction_model="bogus")


def test_mie_canary_unchanged():
    """The Mie regression is the physics canary; the fock default must not move it."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_mie.py", "-q", "-p", "no:cacheprovider"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
