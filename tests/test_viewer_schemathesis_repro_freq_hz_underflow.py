"""Regression test for the freq_hz underflow bug surfaced by Schemathesis.

Schemathesis synthesised ``freq_hz=5e-324`` (the smallest positive IEEE-754
double). The existing validation accepted any ``math.isfinite`` positive value,
but ``omega * EPS_0`` underflows to ``0.0`` for any ``freq_hz < ~4e-298``.
``fresnel.n_complex`` then performs ``sigma / (omega * EPS_0)`` with Python
scalar complex arithmetic, which raises ``ZeroDivisionError`` and surfaces as
a raw 500.

Fix: ``_parse_freq_and_tissue`` rejects values whose ``2*pi*freq_hz*EPS_0``
underflows to 0 with a 400. This test locks that behavior in.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


class TestFreqHzUnderflow:
    def test_smallest_positive_double_returns_400_not_500(self, viewer_app):
        """``5e-324`` is the smallest positive IEEE-754 subnormal.

        Before the fix, ``2*pi*5e-324*EPS_0`` underflowed to exactly ``0.0``
        and ``sigma / 0.0`` raised a ``ZeroDivisionError`` in
        ``fresnel.n_complex`` (Python scalar complex path), surfacing as 500.
        The parser now rejects any freq that underflows the dielectric
        denominator with a clear 400.
        """
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"freq_hz": 5e-324})
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}: {resp.data[:200]!r}"
        err = resp.get_json()
        assert "freq_hz" in err["error"]

    @pytest.mark.parametrize("freq_hz", [1e-320, 1e-310, 1e-300, 1e-200, 1.0, 1e3, 28e9])
    def test_various_freqs_never_return_500(self, viewer_app, freq_hz):
        """Any positive finite ``freq_hz`` must not surface a 500.

        Values below the underflow threshold are caught by the parser;
        slightly larger values (like ``1e-300``) produce non-finite tissue
        properties but are caught by the existing "non-finite sab" kernel
        guard. Only real RF values (``28 GHz`` etc.) should 200.
        """
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"freq_hz": freq_hz})
        assert resp.status_code < 500, f"unexpected {resp.status_code}: {resp.data[:200]!r}"

    def test_ordinary_rf_freq_still_succeeds(self, viewer_app):
        """Sanity: the fix must not break realistic RF frequencies."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"freq_hz": 28e9})
        assert resp.status_code == 200
