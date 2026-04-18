"""Regression test for the antenna_pos overflow bug surfaced by Schemathesis.

Schemathesis synthesised ``antenna_pos`` vectors with components near 1e200.
``np.linalg.norm`` overflowed to ``inf``, so ``direction / dist`` produced a
NaN ``k_hat`` that eventually raised a ``ValueError`` deep inside
``PropagationPaths.from_powers`` - but only after the request had crossed the
route boundary, surfacing as a raw 500.

Fix: ``_parse_vec3`` rejects position components above ``1e9`` meters (150x
earth radius, physically meaningless for a near-field antenna position) with
a 400. This test locks that behavior in.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


class TestAntennaPosOverflow:
    @pytest.mark.parametrize(
        "pos",
        [
            [1000.0, 1e211, 0.0],
            [0.0, 1e200, 0.0],
            [1e150, 0.0, 0.0],
            [0.0, 0.0, -1e300],
        ],
    )
    def test_large_antenna_pos_returns_400_not_500(self, viewer_app, pos):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": pos})
        # Before the fix this raised a ValueError deep in PropagationPaths
        # and bubbled up as 500. Now the route rejects it cleanly at the
        # parser boundary with a 400 and a clear error message.
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}: {resp.data[:200]!r}"
        err = resp.get_json()
        assert "antenna_pos" in err["error"]
        assert "magnitude" in err["error"]

    def test_large_antenna_pos_also_rejected_on_compute_rt(self, viewer_app):
        """Same parser is shared; RT variant must also reject without 500."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"antenna_pos": [0.0, 1e200, 0.0], "scene_path": "ignored"},
            )
        assert resp.status_code < 500, f"unexpected {resp.status_code}: {resp.data[:200]!r}"
        # Either 400 (parser rejects) or 404 (scene_path invalid) - both are
        # fine; the invariant is "no 500 from silent NaN propagation".
        assert resp.status_code in (400, 404)

    def test_ordinary_near_field_position_still_succeeds(self, viewer_app):
        """Sanity: the fix must not break realistic near-field positions."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [1.0, 0.0, 0.5]})
        assert resp.status_code == 200

    def test_up_to_1e12_meters_still_accepted(self, viewer_app):
        """Values up to the explicit threshold (1e12 m, ~100 AU) must parse cleanly.

        The request itself may still error further down the pipeline, but it
        must not 500 on the magnitude check; anything up to the threshold
        should parse cleanly.
        """
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [1e12, 0.0, 0.0]})
        # Either 200 (the physics pipeline is happy with huge distances via
        # d_clamped) or non-5xx. Just assert the parser didn't reject it.
        assert resp.status_code < 500
        if resp.status_code == 400:
            err = resp.get_json()
            assert "magnitude" not in err["error"]
