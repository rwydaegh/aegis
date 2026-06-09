"""Deferred 4 cm^2 averaging in the Exposure Lab compute route.

The lab runs the dose in two phases: a fast first call requesting only
``["sab"]`` (raw heatmap, no averaging-matrix build, the dominant new-pose
cost) and a follow-up requesting ``"sab_4cm2"`` that fills the 4 cm^2 / ICNIRP
metric. These tests pin both halves of that contract:

* ``compute_lab`` derives ``spatial_averaging`` from the requested quantities,
  so the fast phase produces ``sab_averaged is None`` while the raw ``sab`` is
  bit-identical to the averaged phase.
* the route strips the conservative raw-peak fallback that
  ``_build_stats_response`` injects when ``sab_averaged`` is None, so the fast
  phase reports ``spatial_averaged=False`` and no 4 cm^2 / compliance verdict
  (which the frontend would otherwise show and then overwrite).
"""

import json

import numpy as np
import pytest
from conftest import make_flat_mesh

pytest.importorskip("flask")

from aegis.tissue.dielectric import SKIN_28GHZ  # noqa: E402
from aegis.viewer.routes.lab import _compute  # noqa: E402


def _far_params(quantities):
    return {
        "freq_mhz": 3500.0,
        "power_w": 1.0,
        "physics": {"diffraction_model": "none", "self_shadow": False, "fresnel": True},
        "source": {"kind": "far", "theta_inc": 1.2, "phi_inc": 0.0, "pol_angle": 0.0},
        "quantities": quantities,
    }


class TestComputeLabWantAvg:
    """compute_lab maps requested quantities to the spatial_averaging flag."""

    @pytest.fixture(autouse=True)
    def _patch_body_and_tissue(self, monkeypatch):
        # Swap the SMPL-X posed body for a cheap flat mesh so the test does not
        # need model weights or torch, and pin the tissue.
        mesh = make_flat_mesh(40)
        monkeypatch.setattr(_compute, "_posed_body", lambda params: mesh)
        monkeypatch.setattr("aegis.viewer.compute.resolve_skin_model", lambda *a, **k: SKIN_28GHZ)
        self.mesh = mesh

    def test_fast_phase_skips_averaging(self):
        _, _, result, _ = _compute.compute_lab(_far_params(["sab"]))
        assert result.sab_averaged is None
        assert result.peak_sab_averaged is None

    def test_full_phase_has_averaging(self):
        _, _, result, _ = _compute.compute_lab(_far_params(["sab", "sab_4cm2"]))
        assert result.sab_averaged is not None
        assert result.sab_averaged.shape == result.sab.shape

    def test_default_quantities_average(self):
        # No quantities -> backward-compatible default keeps averaging on.
        params = _far_params(["sab", "sab_4cm2"])
        del params["quantities"]
        _, _, result, _ = _compute.compute_lab(params)
        assert result.sab_averaged is not None

    def test_raw_sab_identical_across_phases(self):
        _, _, fast, _ = _compute.compute_lab(_far_params(["sab"]))
        _, _, full, _ = _compute.compute_lab(_far_params(["sab", "sab_4cm2"]))
        np.testing.assert_array_equal(fast.sab, full.sab)
        assert fast.p_abs == full.p_abs


class TestLabRouteStatsContract:
    """The route's X-Stats reflects the deferred-averaging state."""

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from pathlib import Path

        from aegis.viewer.server import create_app

        data_dir = str(tmp_path / "data")
        Path(data_dir).mkdir()
        app = create_app(data_dir=data_dir)
        app.config["TESTING"] = True

        # Stub compute_lab so the route runs on a cheap synthetic result (no
        # SMPL-X / torch). We exercise the route's stats post-processing only.
        mesh = make_flat_mesh(40)
        sab = np.full(mesh.n_triangles, 0.5, dtype=np.float64)

        def fake_compute_lab(params):
            from aegis.result import DosimetryResult

            want_avg = "sab_4cm2" in (params.get("quantities") or ["sab", "sab_4cm2"])
            result = DosimetryResult(
                sab=sab,
                sab_averaged=(sab * 0.8 if want_avg else None),
                p_abs=1.0,
                fidelity_level=2,
                mode="spatial",
                freq_hz=3.5e9,
                corrections=("near_field",),
            )
            return mesh, SKIN_28GHZ, result, {"timings": {"total_ms": 1.0}}

        monkeypatch.setattr(_compute, "compute_lab", fake_compute_lab)
        return app.test_client()

    def _post(self, client, quantities):
        resp = client.post(
            "/api/lab/compute",
            data=json.dumps({"freq_mhz": 3500.0, "source": {"kind": "far"}, "quantities": quantities}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.data
        return json.loads(resp.headers["X-Stats"])

    def test_fast_phase_stats_have_no_averaged_verdict(self, client):
        stats = self._post(client, ["sab"])
        assert stats["spatial_averaged"] is False
        assert stats["peak_sab_averaged"] is None
        assert stats["compliant"] is None
        assert stats["compliance"] is None
        assert "sab_4cm2" not in stats.get("peaks", {})

    def test_full_phase_stats_have_averaged(self, client):
        stats = self._post(client, ["sab", "sab_4cm2"])
        assert stats["spatial_averaged"] is True
        assert stats["peak_sab_averaged"] is not None
