"""Tests for the ``diffraction_model`` selector in ``level6_diffraction``.

``level6_diffraction`` is the only incoherent level with a shadow gate. It used
to hard-code the physical-GELU gate; it now accepts the same
``none`` / ``gelu`` / ``fock`` selector wired into ``spatial_kernel`` (Task 4).

- ``"none"``: exact ReLU activation.
- ``"gelu"``: the legacy ``physical_gelu`` gate, pinned byte-for-byte to the
  pre-selector kernel (and the default when ``diffraction_model`` is None).
- ``"fock"``: the smooth-convex-body (Fock) shadow-edge gate (requires fock_R).
"""

import numpy as np
import pytest

from aegis.geometry import curvature
from aegis.geometry.mesh import BodyMesh
from aegis.kernels._base import fresnel_weights
from aegis.kernels.level6_diffraction import level6_diffraction
from aegis.tissue.dielectric import SKIN_28GHZ

# Level6 output captured from the pre-change kernel on the ``setup`` fixture
# below (default = GELU gate). The post-change "gelu" path and the None default
# must reproduce this bit-for-bit.
LEGACY_LEVEL6 = [
    2.381516154704755,
    2.540996076585867,
    2.448498370474143,
    2.3978118253698297,
    2.331103600004405,
    2.4947206558162156,
    2.1784795018577756,
    2.1781276942730887,
    2.3786042758239865,
    2.641727412095219,
    2.864490607913828,
    2.464584368141992,
    2.579898298089392,
    2.551995006558906,
    2.707917338381185,
    2.580672865189217,
    2.631100301584333,
    2.5185052519714293,
    2.526059268801115,
    2.5671309427845,
    2.9406710192768224,
    3.0911608275141464,
    3.7539774836749578,
    3.118987193115857,
    3.090038942583594,
    2.738995685148366,
    3.7098379892737636,
    3.286735688309193,
    2.084446231648632,
    2.495339455822891,
    1.9968600191454562,
    2.0293630149435615,
    2.552248120715288,
    2.9980431943968573,
    2.629592170253705,
    2.80266421308239,
    3.3086911759810014,
    2.887875285022609,
    3.0330865879060394,
    3.1561769744328148,
    3.877305085283449,
    4.275083505991338,
    3.622043221427599,
    3.9673581434690632,
    3.077649108477707,
    3.4573778319012174,
    2.5557436361672323,
    2.994445687664893,
    2.887245831122048,
    1.7725386329382202,
    2.2849814218630056,
    2.0929039810355974,
    3.2535228897659203,
    2.6543660083069085,
    3.3074789391351036,
    2.9584635508631982,
    3.881087977770026,
    3.8609495793195285,
    4.175371800873098,
    4.040936121112541,
    3.9477435432358887,
    3.9917136572795555,
    3.5034217122822966,
    3.9426111669988364,
    2.306214751622844,
    3.3899113960223892,
    2.2765939470048737,
    2.7823423267886502,
    2.227089921791673,
    2.011798194549546,
    2.302479666237016,
    2.030944527200024,
    3.274684800605578,
    2.91083562503309,
    3.326346131394638,
    3.1472837306955364,
    4.049592600436339,
    3.3197378916564673,
    3.0321997925607196,
    3.4877871071032103,
]


@pytest.fixture
def setup():
    """Convex sphere patch + multi-direction far-field paths."""
    body = BodyMesh.sphere(radius=0.1, n_subdivisions=1)
    rng = np.random.default_rng(1234)
    n = 12
    k_hat = rng.standard_normal((n, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 3.0, size=n)
    n_tilde = SKIN_28GHZ.n_complex
    t0 = SKIN_28GHZ.T0
    freq_hz = SKIN_28GHZ.freq_hz
    curvature_h = curvature.face_curvature(body)
    fock_r = curvature.fock_radius(body, k_hat[0])
    return body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, fock_r


def test_level6_accepts_diffraction_model(setup):
    """All three gate modes run and return finite, non-negative output."""
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, fock_r = setup
    for kwargs in (
        dict(diffraction_model="none"),
        dict(diffraction_model="gelu"),
        dict(diffraction_model="fock", fock_R=fock_r),
    ):
        g = np.asarray(level6_diffraction(body.normals, k_hat, power, n_tilde, t0, curvature_h, freq_hz, **kwargs))
        assert np.all(np.isfinite(g))
        assert np.all(g >= 0.0)


def test_level6_gelu_matches_legacy(setup):
    """diffraction_model="gelu" reproduces the pre-change kernel byte-for-byte."""
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g = level6_diffraction(body.normals, k_hat, power, n_tilde, t0, curvature_h, freq_hz, diffraction_model="gelu")
    np.testing.assert_array_equal(g, np.asarray(LEGACY_LEVEL6))


def test_level6_default_matches_legacy(setup):
    """The default (diffraction_model=None) keeps the historical GELU gate."""
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g = level6_diffraction(body.normals, k_hat, power, n_tilde, t0, curvature_h, freq_hz)
    np.testing.assert_array_equal(g, np.asarray(LEGACY_LEVEL6))


def test_level6_none_is_relu(setup):
    """diffraction_model="none" is the bare ReLU activation plus curvature term."""
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g = level6_diffraction(body.normals, k_hat, power, n_tilde, t0, curvature_h, freq_hz, diffraction_model="none")

    # Reconstruct the expected ReLU-gated result.
    mu = body.normals @ (-k_hat).T
    relu = np.maximum(mu, 0.0)
    _, _, t_avg = fresnel_weights(mu, n_tilde)
    wavelength = 299792458.0 / freq_hz
    k = max(2.0 * np.pi / wavelength, 1e-6)
    h_safe = np.maximum(curvature_h, 0.0)
    sab_base = (t_avg * relu) @ power
    sab_curv = t0 * ((h_safe / k)[:, None] * relu**2) @ power
    expected = np.maximum(sab_base + sab_curv, 0.0)
    np.testing.assert_array_equal(g, expected)


def test_level6_fock_differs():
    """Fock vs none: deep-lit triangles ~unchanged, difference near the terminator."""
    body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
    k_dir = np.array([[0.0, 0.0, 1.0]])
    power = np.array([1.0])
    n_tilde = SKIN_28GHZ.n_complex
    t0 = SKIN_28GHZ.T0
    freq_hz = SKIN_28GHZ.freq_hz
    curvature_h = curvature.face_curvature(body)
    fock_r = curvature.fock_radius(body, k_dir[0])

    g_none = np.asarray(
        level6_diffraction(body.normals, k_dir, power, n_tilde, t0, curvature_h, freq_hz, diffraction_model="none")
    )
    g_fock = np.asarray(
        level6_diffraction(
            body.normals, k_dir, power, n_tilde, t0, curvature_h, freq_hz, diffraction_model="fock", fock_R=fock_r
        )
    )

    mu = (body.normals @ (-k_dir[0])).ravel()
    diff = np.abs(g_fock - g_none)

    # They genuinely differ.
    assert diff.max() > 0.0

    # Deep-lit triangles (well past the (kR)^-1/3 penumbra) are essentially
    # unchanged: the gate -> ReLU as xi -> +inf.
    deep_lit = mu > 0.9
    assert deep_lit.any()
    np.testing.assert_allclose(g_fock[deep_lit], g_none[deep_lit], atol=1e-3)

    # The change concentrates near the terminator: the largest deviation sits at
    # a small |mu| (inside the penumbra).
    assert abs(mu[np.argmax(diff)]) < 0.5


def test_level6_fock_requires_radius(setup):
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    with pytest.raises(ValueError, match="fock_R"):
        level6_diffraction(body.normals, k_hat, power, n_tilde, t0, curvature_h, freq_hz, diffraction_model="fock")
