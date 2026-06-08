"""Tests for the ``diffraction_model`` selector and the Fock local gate.

Covers the three gate modes wired into ``spatial_kernel``:

- ``"none"``: exact ReLU activation (``lambda -> 0`` limit).
- ``"gelu"``: the legacy ``physical_gelu`` gate, pinned byte-for-byte.
- ``"fock"``: the smooth-convex-body (Fock) shadow-edge gate.

Also pins the legacy-bool mapping (``diffraction=True`` -> ``"gelu"``, the
back-compatible meaning) and the ValueError raised when the Fock gate is
requested without an in-plane radius.
"""

import numpy as np
import pytest

from aegis.geometry import curvature
from aegis.geometry.mesh import BodyMesh
from aegis.kernels._base import fresnel_weights, incidence_geometry
from aegis.kernels.spatial import spatial_kernel
from aegis.tissue.dielectric import SKIN_28GHZ

# Legacy ``physical_gelu`` output captured from the pre-change kernel on the
# ``setup`` fixture below (diffraction=True, fresnel, no polarisation, no
# curvature term beyond the gate). The post-change "gelu" path must reproduce
# this bit-for-bit.
LEGACY_GELU = [
    2.303062248469636,
    2.47546947147121,
    2.385996602200968,
    2.332377536007593,
    2.2469262125895924,
    2.424733265472038,
    2.1112235352277473,
    2.104296010571046,
    2.291132543305775,
    2.5748305536759615,
    2.785055518885602,
    2.3906746785663184,
    2.4936771773444115,
    2.4651350757697705,
    2.627568939684946,
    2.4975610363800222,
    2.5508781011629056,
    2.448434935818857,
    2.457526872263652,
    2.4980826762753283,
    2.874645287945195,
    3.0040785647694435,
    3.6363031029688724,
    3.032409249907417,
    3.012459247151246,
    2.670505809969673,
    3.600266737464258,
    3.2050063023678197,
    2.011917148783314,
    2.4304079437453474,
    1.925270515663342,
    1.9619476877540012,
    2.478389129620417,
    2.90682246263119,
    2.547916471487106,
    2.7241428283473286,
    3.2200576160861867,
    2.821627598403213,
    2.931560342136866,
    3.074939371415431,
    3.760147730651604,
    4.124363767593682,
    3.4815492037457934,
    3.828835517533608,
    3.002321491923794,
    3.3435189161313774,
    2.4909608556879346,
    2.9125484282629728,
    2.8368240131418556,
    1.7300569918117434,
    2.2285560425822926,
    2.055113650414991,
    3.1718102157947325,
    2.5632377071244266,
    3.193168530778058,
    2.8659894771801513,
    3.767444235774576,
    3.738606699278831,
    4.032405665756033,
    3.9126252022862253,
    3.8090889762186464,
    3.847055559031509,
    3.39564043776346,
    3.808492423794568,
    2.22857828430162,
    3.2853150173696974,
    2.1996060018446344,
    2.6969329448770694,
    2.1666273596586665,
    1.955096284015886,
    2.2405268178554696,
    1.9758745407801062,
    3.1542836065342374,
    2.804275286254419,
    3.2227683101548132,
    3.0358525883159926,
    3.9287901713908773,
    3.215087033332993,
    2.964276644304065,
    3.3939410684372238,
]

# Tolerance for comparing the GELU gate against Linux-generated reference values.
# The gate uses transcendental libm calls whose last ULPs differ across platforms.
_LEGACY_RTOL = 1e-9


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


def test_gelu_matches_legacy(setup):
    # The GELU gate uses transcendental functions (erf/exp), whose last few ULPs
    # differ between platform libm implementations (Linux vs Windows ~1e-13 rel).
    # rtol=1e-9 is far below any real numerical change a refactor would introduce
    # yet tolerates cross-platform libm noise. The reference is Linux-generated.
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g = spatial_kernel(
        body.normals,
        k_hat,
        power,
        n_tilde,
        t0,
        freq_hz,
        fresnel=True,
        diffraction_model="gelu",
        curvature_H=curvature_h,
    )
    np.testing.assert_allclose(g, np.asarray(LEGACY_GELU), rtol=_LEGACY_RTOL)


def test_none_is_exact_relu(setup):
    body, k_hat, power, n_tilde, t0, freq_hz, _, _ = setup
    g = spatial_kernel(
        body.normals,
        k_hat,
        power,
        n_tilde,
        t0,
        freq_hz,
        fresnel=True,
        diffraction_model="none",
    )
    # Bare (t_factor * relu(mu)) @ power with t_factor = T_avg.
    mu, mu_plus = incidence_geometry(body.normals, k_hat)
    _, _, t_avg = fresnel_weights(mu, n_tilde)
    expected = (t_avg * mu_plus) @ power
    np.testing.assert_array_equal(g, expected)


def test_none_matches_default(setup):
    """diffraction_model defaults to none (legacy diffraction=False)."""
    body, k_hat, power, n_tilde, t0, freq_hz, _, _ = setup
    g_none = spatial_kernel(body.normals, k_hat, power, n_tilde, t0, freq_hz, diffraction_model="none")
    g_default = spatial_kernel(body.normals, k_hat, power, n_tilde, t0, freq_hz)
    np.testing.assert_array_equal(g_none, g_default)


def test_fock_changes_near_terminator_only():
    """Fock vs none: deep-lit triangles ~unchanged, difference near mu~0."""
    body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
    k_dir = np.array([[0.0, 0.0, 1.0]])
    power = np.array([1.0])
    n_tilde = SKIN_28GHZ.n_complex
    t0 = SKIN_28GHZ.T0
    freq_hz = SKIN_28GHZ.freq_hz
    fock_r = curvature.fock_radius(body, k_dir[0])

    common = dict(fresnel=True)
    g_none = spatial_kernel(body.normals, k_dir, power, n_tilde, t0, freq_hz, diffraction_model="none", **common)
    g_fock = spatial_kernel(
        body.normals, k_dir, power, n_tilde, t0, freq_hz, diffraction_model="fock", fock_R=fock_r, **common
    )

    # Single direction -> one mu per triangle.
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
    # a small |mu| (inside the penumbra, |mu| < 0.5).
    assert abs(mu[np.argmax(diff)]) < 0.5


def test_legacy_bool_maps_to_gelu(setup):
    """The legacy diffraction=True keeps its historical meaning (gelu).

    Fock requires fock_R (not supplied by legacy bool callers), so the bool maps
    to the back-compatible gelu gate, not fock. This keeps every existing
    diffraction=True caller (levels 2-6, engine) working unchanged. Fock is
    opt-in via diffraction_model="fock".
    """
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g_bool = spatial_kernel(
        body.normals, k_hat, power, n_tilde, t0, freq_hz, fresnel=True, diffraction=True, curvature_H=curvature_h
    )
    np.testing.assert_allclose(g_bool, np.asarray(LEGACY_GELU), rtol=_LEGACY_RTOL)


def test_explicit_model_wins_over_bool(setup):
    """Explicit diffraction_model overrides the legacy diffraction bool."""
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, _ = setup
    g_gelu = spatial_kernel(
        body.normals,
        k_hat,
        power,
        n_tilde,
        t0,
        freq_hz,
        fresnel=True,
        diffraction=True,
        diffraction_model="gelu",
        curvature_H=curvature_h,
    )
    np.testing.assert_allclose(g_gelu, np.asarray(LEGACY_GELU), rtol=_LEGACY_RTOL)


def test_fock_requires_radius(setup):
    body, k_hat, power, n_tilde, t0, freq_hz, _, _ = setup
    with pytest.raises(ValueError, match="fock_R"):
        spatial_kernel(
            body.normals,
            k_hat,
            power,
            n_tilde,
            t0,
            freq_hz,
            fresnel=True,
            diffraction_model="fock",
            fock_R=None,
        )


def test_nonneg(setup):
    body, k_hat, power, n_tilde, t0, freq_hz, curvature_h, fock_r = setup
    for kwargs in (
        dict(diffraction_model="none"),
        dict(diffraction_model="gelu", curvature_H=curvature_h),
        dict(diffraction_model="fock", fock_R=fock_r),
        dict(diffraction_model="fock", fock_R=fock_r, curvature=True, curvature_H=curvature_h),
    ):
        g = spatial_kernel(body.normals, k_hat, power, n_tilde, t0, freq_hz, fresnel=True, **kwargs)
        assert np.all(g >= 0.0)
