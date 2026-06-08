"""End-to-end / cross-oracle validation for the Fock diffraction framework.

This is the capstone suite (Phase A, Task 9). It exercises the Fock gate
through ``engine.compute`` (not the bare ``kernels/fock.py`` math, which is
unit-tested in ``tests/test_fock.py``) plus the two committed oracles
(``studies/diffraction/cylinder_oracle.py`` and ``sphere_oracle.py``).

What is validated here, by section:

- Legacy gates pinned: ``diffraction_model="none"`` is bit-exact ReLU and
  ``"gelu"`` reproduces the pre-feature physical-GELU numbers, so flipping the
  engine default to ``"fock"`` did not silently move the legacy paths.
- lambda -> 0 asymptotic: on a convex sphere the ``"fock"`` map converges to the
  ``"none"`` (ReLU) map as ``kR`` grows, with the pointwise penumbra error
  shrinking like ``(kR)^{-1/3}`` (asymptotic, NOT bit-exact).
- Whole-body frequency sweep: integrated absorbed power with ``"fock"`` stays
  within a few percent of ``"none"`` (F5) and tightens with frequency, while the
  pointwise map differs materially near the terminator. Both are asserted.
- Coherent >= incoherent at the engine level: a level-7 compute with the complex
  Fock gate satisfies ``n_elem * lambda_max >= trace(Q)``.
- Sphere oracle: the exact Mie sphere recovers geometric optics in the lit
  region (the GO basis the Fock gate sits on) with no s/p resonance anomaly, and
  the engine lit hemisphere is gate-neutral (``"fock" ~ "none"`` deep lit).
- Differentiability: under the JAX backend ``jax.grad`` of the gate is finite and
  matches a finite difference to < 2% (run in a subprocess with
  ``AEGIS_ARRAY_BACKEND=jax``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.curvature import face_curvature
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.tissue.dielectric import SKIN_28GHZ

_REPO_ROOT = Path(__file__).resolve().parent.parent
# The committed oracles live under studies/; make them importable.
sys.path.insert(0, str(_REPO_ROOT / "studies" / "diffraction"))

C_LIGHT = 3e8


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


def _plane_wave_down():
    """A single plane wave travelling -z (illuminates the +z hemisphere)."""
    k = np.array([[0.0, 0.0, -1.0]])
    return PropagationPaths.from_powers(k_hat=k, power=np.array([1.0]))


def _multi_plane_waves(n: int = 40, seed: int = 0):
    rng = np.random.default_rng(seed)
    k = rng.standard_normal((n, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    power = rng.uniform(0.5, 2.0, size=n)
    return PropagationPaths.from_powers(k_hat=k, power=power)


# ---------------------------------------------------------------------------
# Part A regression: the legacy "none" and "gelu" gates stay pinned
# ---------------------------------------------------------------------------


class TestLegacyGatesPinned:
    """The default flip to "fock" must not move "none" (ReLU) or "gelu"."""

    def _setup(self, engine):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=1)
        k = np.array([[0.0, 0.0, -1.0], [0.3, 0.0, -0.95]])
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        paths = PropagationPaths.from_powers(k_hat=k, power=np.array([1.0, 0.5]))
        return body, paths

    def test_none_is_bit_exact_relu(self, engine):
        """diffraction_model="none" equals the bare ReLU level 3 exactly."""
        body, paths = self._setup(engine)
        H = np.zeros(body.n_triangles)
        r_none = engine.compute(body, paths, level=6, curvature_H=H, diffraction_model="none")
        r_level3 = engine.compute(body, paths, level=3)
        np.testing.assert_array_equal(r_none.sab, r_level3.sab)

    def test_gelu_differs_from_none_and_fock(self, engine):
        """With curvature the GELU gate is a distinct path from none and fock."""
        body, paths = self._setup(engine)
        H = face_curvature(body)
        r_none = engine.compute(body, paths, level=6, curvature_H=H, freq_hz=10e9, diffraction_model="none")
        r_gelu = engine.compute(body, paths, level=6, curvature_H=H, freq_hz=10e9, diffraction_model="gelu")
        r_fock = engine.compute(body, paths, level=6, curvature_H=H, freq_hz=10e9, diffraction_model="fock")
        assert not np.allclose(r_gelu.sab, r_none.sab)
        assert not np.allclose(r_gelu.sab, r_fock.sab)

    def test_legacy_gate_numbers_pinned(self, engine):
        """Pin the absolute legacy "none"/"gelu" outputs (frozen pre-feature values)."""
        body, paths = self._setup(engine)
        H = face_curvature(body)
        r_none = engine.compute(body, paths, level=6, curvature_H=H, freq_hz=10e9, diffraction_model="none")
        r_gelu = engine.compute(body, paths, level=6, curvature_H=H, freq_hz=10e9, diffraction_model="gelu")
        # Frozen golden values computed under the pre-feature legacy gate math.
        assert r_none.p_abs == pytest.approx(1.897504492264e-02, rel=1e-9)
        assert r_gelu.p_abs == pytest.approx(1.868573690950e-02, rel=1e-9)
        # GELU smooths but never amplifies vs the bare ReLU integral.
        assert r_gelu.p_abs <= r_none.p_abs


# ---------------------------------------------------------------------------
# Part B: lambda -> 0 asymptotic recovery of ReLU on a convex body
# ---------------------------------------------------------------------------


class TestLambdaToZeroAsymptotic:
    """As kR grows the Fock map converges to the bare ReLU ("none") map."""

    def test_fock_to_relu_scales_as_kR_minus_third(self, engine):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=3)
        paths = _plane_wave_down()
        freqs = np.array([10e9, 28e9, 60e9, 120e9, 240e9])
        kR = 2.0 * np.pi * freqs / C_LIGHT * 0.1
        rels = []
        for f in freqs:
            r_fock = engine.compute(body, paths, level=6, freq_hz=f, diffraction_model="fock")
            r_none = engine.compute(body, paths, level=6, freq_hz=f, diffraction_model="none")
            peak = float(np.max(r_none.sab))
            rels.append(float(np.max(np.abs(r_fock.sab - r_none.sab))) / peak)
        rels = np.array(rels)

        # Monotone decreasing: the penumbra (and hence the Fock-vs-ReLU gap) shrinks.
        assert np.all(np.diff(rels) < 0.0)
        # Asymptotic (kR)^{-1/3} decay: the log-log slope brackets -1/3.
        slope = np.polyfit(np.log(kR), np.log(rels), 1)[0]
        assert -0.6 < slope < -0.2, f"penumbra decay slope {slope:.3f} not ~ -1/3"
        # Small at the largest kR (asymptotic, NOT bit-exact: that is "none").
        assert rels[-1] < 0.05


# ---------------------------------------------------------------------------
# Part B: whole-body frequency sweep (close) vs pointwise penumbra (differs)
# ---------------------------------------------------------------------------


class TestWholeBodyFrequencySweep:
    """Whole-body SAR is within a few percent (F5); pointwise penumbra differs."""

    def test_wholebody_close_pointwise_differs(self, engine):
        # A body-scale convex sphere (kR ~ 150 at 28 GHz) and many incident waves.
        body = BodyMesh.sphere(radius=0.25, n_subdivisions=3)
        paths = _multi_plane_waves(n=40, seed=0)
        diffs = {}
        pointwise = {}
        for f in (28e9, 60e9):
            r_fock = engine.compute(body, paths, level=6, freq_hz=f, diffraction_model="fock")
            r_none = engine.compute(body, paths, level=6, freq_hz=f, diffraction_model="none")
            diffs[f] = abs(r_fock.p_abs - r_none.p_abs) / r_none.p_abs
            pointwise[f] = float(np.max(np.abs(r_fock.sab - r_none.sab))) / float(np.max(r_none.sab))

        # Whole-body: within a few percent (F5 2-4% band) and tightens with kR.
        assert diffs[28e9] < 0.05
        assert diffs[60e9] < 0.03
        assert diffs[60e9] < diffs[28e9]
        # Pointwise: the terminator faces differ materially at both bands.
        assert pointwise[28e9] > 0.02
        assert pointwise[60e9] > 0.02


# ---------------------------------------------------------------------------
# Part B: coherent >= incoherent at the engine level (complex Fock gate)
# ---------------------------------------------------------------------------


class TestCoherentGeIncoherentEngine:
    """A level-7 compute with the complex gate keeps the coherent advantage."""

    def _coherent_paths(self, m_ant=4, n=8, seed=3):
        rng = np.random.default_rng(seed)
        base = np.array([0.05, 0.0, -1.0])
        k = base + rng.normal(0, 0.1, (n, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        psi = rng.standard_normal((n, 3)) + 1j * rng.standard_normal((n, 3))
        for i in range(n):
            psi[i] -= np.dot(psi[i], k[i]) * k[i]
        element_index = np.arange(n) % m_ant
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=element_index,
            delay=np.zeros(n),
            is_los=np.ones(n, dtype=bool),
        )
        x = rng.standard_normal(m_ant) + 1j * rng.standard_normal(m_ant)
        return paths, Precoder(x=x), m_ant

    def test_matched_dose_ge_isotropic(self, engine):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
        paths, precoder, m_ant = self._coherent_paths()
        res = engine.compute(body, paths, level=7, precoder=precoder, diffraction_model="fock")
        assert res.Q is not None
        assert res.eigenvalues is not None
        lam_max = float(np.real(res.eigenvalues[0]))
        trace = float(np.real(np.trace(res.Q)))
        # Equal total transmit power (||x||^2 = m_ant): matched-filter (n*lambda_max)
        # >= isotropic (trace), since the max eigenvalue >= the mean.
        assert m_ant * lam_max >= trace * (1.0 - 1e-9)
        # And the advantage is real, not a degenerate rank-1 tie.
        assert lam_max > trace / m_ant


# ---------------------------------------------------------------------------
# Part B: sphere oracle (the doubly-curved cross-check)
# ---------------------------------------------------------------------------


class TestSphereOracle:
    """The Mie sphere recovers GO in the lit region; the engine is gate-neutral there."""

    def test_oracle_lit_region_recovers_go(self):
        """exact / (T mu) -> a stable s/p-agreeing constant as the size grows."""
        from sphere_oracle import fresnel_TsTp, sphere_surface_absorbed

        incidences = (30.0, 50.0)
        sizes = (60.0, 120.0, 240.0)
        spreads = []
        for x in sizes:
            ratios_s, ratios_p = [], []
            for inc in incidences:
                th = np.deg2rad(180.0 - inc)  # lit side
                mu = np.cos(np.deg2rad(inc))
                Ts, Tp = fresnel_TsTp(mu)
                Ps = sphere_surface_absorbed(x, np.array([th]), np.pi / 2)[0]
                Pp = sphere_surface_absorbed(x, np.array([th]), 0.0)[0]
                ratios_s.append(Ps / (Ts * mu))
                ratios_p.append(Pp / (Tp * mu))
            # s and p must agree (no closed-loop resonance like the 2D cylinder).
            for rs, rp in zip(ratios_s, ratios_p, strict=True):
                assert rs == pytest.approx(rp, rel=0.02)
            spreads.append(float(np.std(ratios_s + ratios_p) / np.mean(ratios_s + ratios_p)))
        # GO recovery: the lit-region ratio gets flatter as x grows.
        assert spreads[-1] < spreads[0]
        assert spreads[-1] < 0.01

    def test_engine_lit_hemisphere_is_gate_neutral(self, engine):
        """Deep in the lit hemisphere the Fock gate -> 1, so fock ~ none."""
        body = BodyMesh.sphere(radius=0.15, n_subdivisions=3)
        paths = _plane_wave_down()  # +z hemisphere lit
        r_fock = engine.compute(body, paths, level=6, freq_hz=60e9, diffraction_model="fock")
        r_none = engine.compute(body, paths, level=6, freq_hz=60e9, diffraction_model="none")
        # Deep-lit faces: mu = n.(-k) = n_z well above the penumbra.
        mu = body.normals @ np.array([0.0, 0.0, 1.0])
        deep_lit = mu > 0.5
        assert deep_lit.sum() > 20
        rel = np.abs(r_fock.sab[deep_lit] - r_none.sab[deep_lit]) / np.maximum(r_none.sab[deep_lit], 1e-12)
        assert np.max(rel) < 0.02  # gate is neutral away from the terminator


# ---------------------------------------------------------------------------
# Part C: differentiability under the JAX backend
# ---------------------------------------------------------------------------

# Standalone script: import-time backend selection means this must run in a
# fresh interpreter with AEGIS_ARRAY_BACKEND=jax set before any aegis import.
_JAX_GRAD_SCRIPT = """
import sys
import numpy as np
from aegis._array_backend import _BACKEND, xp

assert _BACKEND == "jax", f"expected jax backend, got {_BACKEND!r}"
assert xp.__name__ == "jax.numpy", f"xp is {xp.__name__}, not jax.numpy"

import jax
import jax.numpy as jnp
from aegis.kernels import fock


def total_freq(freq):
    mu = jnp.linspace(-0.2, 0.6, 64)
    return jnp.sum(fock.fock_local(mu, 0.1, freq, 0.5, 0.5))


f0 = 28e9
g_ana = float(jax.grad(total_freq)(f0))
h = f0 * 1e-4
g_fd = float((total_freq(f0 + h) - total_freq(f0 - h)) / (2.0 * h))
assert np.isfinite(g_ana), "jax.grad w.r.t. freq is not finite"
rel = abs(g_ana - g_fd) / abs(g_fd)
assert rel < 0.02, f"freq grad vs finite-diff rel error {rel:.4g} >= 2%"

# grad w.r.t. the detour parameter xi must also flow and be finite.
def total_xi(xi):
    return jnp.sum(fock.fock_g(xi, "soft").real)

g_xi = float(jax.grad(total_xi)(0.3))
assert np.isfinite(g_xi), "jax.grad w.r.t. xi is not finite"

print("OK", rel)
"""


def test_fock_gate_differentiable_under_jax():
    """jax.grad of the Fock gate is finite and matches finite-diff to < 2%.

    The array backend is fixed at import time (default numpy), so this runs in a
    subprocess with AEGIS_ARRAY_BACKEND=jax. JAX 0.10.1 is installed in the venv.
    """
    import os

    env = dict(os.environ, AEGIS_ARRAY_BACKEND="jax")
    result = subprocess.run(
        [sys.executable, "-c", _JAX_GRAD_SCRIPT],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        if "No module named 'jax'" in result.stderr:
            pytest.skip("JAX backend not available in this environment")
        raise AssertionError(f"jax.grad differentiability check failed:\n{result.stdout}\n{result.stderr}")
    assert "OK" in result.stdout, result.stdout + result.stderr
