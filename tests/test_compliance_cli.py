"""Tests for the compliance CLI (python -m aegis.compliance)."""

from __future__ import annotations

import json

from aegis.compliance.__main__ import main


class TestComplianceCLI:
    def test_limits_mode(self, capsys):
        main(["--freq", "28e9", "--limits"])
        out = capsys.readouterr().out
        assert "ICNIRP 2020 limits" in out
        assert "20 W/m^2" in out

    def test_limits_json(self, capsys):
        main(["--freq", "28e9", "--limits", "--json"])
        d = json.loads(capsys.readouterr().out)
        assert d["sab_4cm2_limit"] == 20.0
        assert d["sar_wb_limit"] == 0.08

    def test_evaluation_pass(self, capsys):
        main(["--freq", "28e9", "--sab", "10.0"])
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "margin" in out

    def test_evaluation_fail(self, capsys):
        main(["--freq", "28e9", "--sab", "25.0"])
        out = capsys.readouterr().out
        assert "FAIL" in out

    def test_max_compliant_power(self, capsys):
        main(["--freq", "28e9", "--sab", "25.0", "--power", "1.0"])
        out = capsys.readouterr().out
        assert "Max compliant power" in out
        assert "0.8 W" in out

    def test_json_output(self, capsys):
        # Sub-6 GHz: Sab does not apply (>6 GHz basic restriction), only
        # SAR_wb is an applicable ICNIRP 2020 check in this regime.
        main(["--freq", "3e9", "--sab", "15.0", "--sar", "0.05", "--json"])
        d = json.loads(capsys.readouterr().out)
        assert d["overall_pass"] is True
        assert len(d["checks"]) == 1
        assert d["checks"][0]["label"] == "SAR_wb"

    def test_occupational(self, capsys):
        main(["--freq", "28e9", "--sab", "50.0", "--occupational"])
        out = capsys.readouterr().out
        assert "PASS" in out  # 50 < 100 occupational limit

    def test_60ghz_1cm2(self, capsys):
        main(["--freq", "60e9", "--sab", "15.0", "--sab-1cm2", "35.0", "--json"])
        d = json.loads(capsys.readouterr().out)
        labels = [c["label"] for c in d["checks"]]
        assert "S_ab (1 cm^2)" in labels

    def test_no_values_exits(self):
        import pytest

        with pytest.raises(SystemExit):
            main(["--freq", "28e9"])

    def test_invalid_freq_exits(self):
        import pytest

        # 1 kHz is below ICNIRP range (100 kHz to 300 GHz)
        with pytest.raises(SystemExit):
            main(["--freq", "1e3", "--sab", "10.0"])

    def test_all_quantities(self, capsys):
        # Above 6 GHz (ICNIRP 2020 Table 5): Sab + Sinc labels apply, and
        # SAR_wb applies too (basic restriction across 100 kHz - 300 GHz).
        main(
            [
                "--freq",
                "28e9",
                "--sab",
                "10.0",
                "--sar",
                "0.04",
                "--sinc",
                "8.0",
                "--sinc-wb",
                "5.0",
            ]
        )
        out = capsys.readouterr().out
        assert "S_ab (4 cm^2)" in out
        assert "SAR_wb" in out
        assert "S_inc (local)" in out
        assert "S_inc (whole-body)" in out
        # Sub-6 GHz: only SAR_wb label is shown (Sab does not apply).
        main(["--freq", "3e9", "--sar", "0.05"])
        out2 = capsys.readouterr().out
        assert "SAR_wb" in out2

    def test_link_budget_mode(self, capsys):
        main(["--freq", "28e9", "--link-budget", "--tx-power", "1.0", "--distance", "10.0"])
        out = capsys.readouterr().out
        assert "Link budget" in out
        assert "S_inc" in out
        assert "S_ab estimate" in out
        assert "Max compliant TX power" in out

    def test_link_budget_json(self, capsys):
        main(
            [
                "--freq",
                "28e9",
                "--link-budget",
                "--tx-power",
                "1.0",
                "--gain",
                "10",
                "--distance",
                "5.0",
                "--json",
            ]
        )
        d = json.loads(capsys.readouterr().out)
        assert "sinc_wm2" in d
        assert "sab_estimate_wm2" in d
        assert d["compliant"] is True

    def test_link_budget_missing_args(self):
        import pytest

        with pytest.raises(SystemExit):
            main(["--freq", "28e9", "--link-budget"])

    def test_link_budget_occupational(self, capsys):
        main(
            [
                "--freq",
                "28e9",
                "--link-budget",
                "--tx-power",
                "1.0",
                "--distance",
                "10.0",
                "--occupational",
            ]
        )
        out = capsys.readouterr().out
        assert "occupational" in out
