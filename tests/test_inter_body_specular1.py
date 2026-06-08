"""Tests for the inter_body='specular1' single specular recapture bounce.

Phase B3 of the Fock framework. The recapture casts one mirror-reflected ray
from every lit triangle and, when it strikes another body triangle, deposits
the Fresnel-reflected power there with that triangle's own transmittance and
incidence. It is off by default and bounded to a single bounce.

Reference bounds (theory/unified/sec_09_interbody.tex): body-averaged
enhancement <= 8%, worst concavity ~1.85x, convex bodies recapture nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


def _facing_plates(gap: float = 1.0) -> BodyMesh:
    """Two facing square plates forming a concavity.

    Plate A at x=0 with outward normal +x, plate B at x=gap with outward
    normal -x. They face each other across the gap. A plane wave travelling
    along -x lights plate A only; A's specular reflection travels +x and
    strikes the (otherwise unlit) front face of plate B.
    """
    a = np.array(
        [
            [[0.0, -1, -1], [0.0, 1, -1], [0.0, 1, 1]],
            [[0.0, -1, -1], [0.0, 1, 1], [0.0, -1, 1]],
        ]
    )
    b = np.array(
        [
            [[gap, -1, -1], [gap, 1, -1], [gap, 1, 1]],
            [[gap, -1, -1], [gap, 1, 1], [gap, -1, 1]],
        ]
    )
    verts = np.concatenate([a, b], axis=0)
    normals = np.array([[1.0, 0, 0], [1.0, 0, 0], [-1.0, 0, 0], [-1.0, 0, 0]])
    return BodyMesh.from_arrays(verts, normals=normals, name="facing_plates")


def _wave_toward_minus_x() -> PropagationPaths:
    return PropagationPaths.from_powers(k_hat=np.array([[-1.0, 0.0, 0.0]]), power=np.array([1.0]))


def test_inter_body_off_unchanged(engine):
    """inter_body='off' is bit-identical to not passing it at all."""
    body = _facing_plates()
    paths = _wave_toward_minus_x()
    base = engine.compute(body, paths, mode="spatial").sab
    off = engine.compute(body, paths, mode="spatial", inter_body="off").sab
    np.testing.assert_array_equal(base, off)

    # legacy level path too
    base_l = engine.compute(body, paths, level=3).sab
    off_l = engine.compute(body, paths, level=3, inter_body="off").sab
    np.testing.assert_array_equal(base_l, off_l)


def test_specular1_adds_nonneg_dose(engine):
    """On a concave fixture specular1 raises dose at the recapturing triangle."""
    body = _facing_plates()
    paths = _wave_toward_minus_x()
    off = engine.compute(body, paths, mode="spatial", inter_body="off").sab
    on = engine.compute(body, paths, mode="spatial", inter_body="specular1").sab

    assert np.all(np.isfinite(on))
    assert np.all(on >= 0.0)
    # Plate B (triangles 2, 3) is unlit directly but recaptures A's reflection.
    assert off[2] == pytest.approx(0.0, abs=1e-12)
    assert off[3] == pytest.approx(0.0, abs=1e-12)
    assert on[2] > 0.0
    assert on[3] > 0.0
    # Plate A's own dose is unchanged (it does not recapture from B).
    np.testing.assert_allclose(on[:2], off[:2])


def test_specular1_bounded(engine):
    """Recapture is finite, non-negative, and modest in body-average."""
    body = _facing_plates()
    paths = _wave_toward_minus_x()
    off = engine.compute(body, paths, mode="spatial", inter_body="off")
    on = engine.compute(body, paths, mode="spatial", inter_body="specular1")

    assert np.all(np.isfinite(on.sab))
    assert np.all(on.sab >= 0.0)
    # Some recapture happened on this concave case.
    assert on.p_abs > off.p_abs
    # Single bounce cannot exceed the incident reflectance times direct dose,
    # so total absorbed power stays well under twice the direct value.
    assert on.p_abs < 2.0 * off.p_abs


def test_specular1_convex_no_recapture(engine):
    """On a convex sphere reflected rays escape, so specular1 ~ off."""
    body = BodyMesh.sphere(radius=0.2, n_subdivisions=3)
    rng = np.random.default_rng(0)
    k = rng.standard_normal((6, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    paths = PropagationPaths.from_powers(k_hat=k, power=np.ones(6))

    off = engine.compute(body, paths, mode="spatial", inter_body="off").sab
    on = engine.compute(body, paths, mode="spatial", inter_body="specular1").sab

    assert np.all(on >= 0.0)
    # Convex body: no self-hits, recapture is negligible.
    np.testing.assert_allclose(on, off, rtol=1e-9, atol=1e-12)


def test_specular1_legacy_level_path(engine):
    """specular1 also fires on the legacy level (>=2) path."""
    body = _facing_plates()
    paths = _wave_toward_minus_x()
    off = engine.compute(body, paths, level=3, inter_body="off").sab
    on = engine.compute(body, paths, level=3, inter_body="specular1").sab
    assert np.all(on >= 0.0)
    assert on[2] > 0.0
    assert on[3] > 0.0
    np.testing.assert_allclose(on[:2], off[:2])


def test_specular1_invalid_value_raises(engine):
    body = _facing_plates()
    paths = _wave_toward_minus_x()
    with pytest.raises(ValueError, match="inter_body"):
        engine.compute(body, paths, mode="spatial", inter_body="bogus")
