"""Tests for new DosimetryResult fields (Task 3: compliance overhaul)."""

from __future__ import annotations

import numpy as np

from aegis.result import DosimetryResult


class TestNewFields:
    """Verify the new optional fields exist and default to None."""

    def test_sinc_default_none(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.sinc is None

    def test_sinc_averaged_default_none(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.sinc_averaged is None

    def test_sab_1cm2_averaged_default_none(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.sab_1cm2_averaged is None

    def test_freq_hz_default_none(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.freq_hz is None

    def test_sinc_set(self):
        sinc = np.array([5.0, 6.0])
        r = DosimetryResult(sab=np.array([1.0, 2.0]), p_abs=1.5, fidelity_level=2, sinc=sinc)
        np.testing.assert_array_equal(r.sinc, sinc)

    def test_freq_hz_set(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2, freq_hz=28e9)
        assert r.freq_hz == 28e9

    def test_sinc_averaged_set(self):
        arr = np.array([3.0, 4.0])
        r = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=1.5,
            fidelity_level=2,
            sinc_averaged=arr,
        )
        np.testing.assert_array_equal(r.sinc_averaged, arr)

    def test_sab_1cm2_averaged_set(self):
        arr = np.array([1.5, 2.5])
        r = DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=1.5,
            fidelity_level=2,
            sab_1cm2_averaged=arr,
        )
        np.testing.assert_array_equal(r.sab_1cm2_averaged, arr)


class TestCompliantSabUpdated:
    """Verify compliant_sab uses freq_hz and <= comparison."""

    def test_none_when_no_averaging(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.compliant_sab is None

    def test_none_when_no_freq(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([10.0]),
        )
        assert r.compliant_sab is None

    def test_pass_below_limit(self):
        r = DosimetryResult(
            sab=np.array([10.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([10.0]),
            freq_hz=28e9,
        )
        # 10 <= 20 -> True
        assert r.compliant_sab is True

    def test_pass_at_limit(self):
        """Value exactly at limit should pass (<=)."""
        r = DosimetryResult(
            sab=np.array([20.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([20.0]),
            freq_hz=28e9,
        )
        assert r.compliant_sab is True

    def test_fail_above_limit(self):
        r = DosimetryResult(
            sab=np.array([25.0]),
            p_abs=1.0,
            fidelity_level=2,
            sab_averaged=np.array([25.0]),
            freq_hz=28e9,
        )
        assert r.compliant_sab is False


class TestCompliantSarUpdated:
    """Verify compliant_sar uses <= comparison."""

    def test_pass_at_limit(self):
        """SAR exactly at limit should pass (<=)."""
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sar_wb=0.08,
        )
        assert r.compliant_sar is True

    def test_fail_above_limit(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sar_wb=0.09,
        )
        assert r.compliant_sar is False

    def test_none_without_sar(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        assert r.compliant_sar is None


class TestToDict:
    """Verify new fields appear in serialization."""

    def test_sinc_in_dict(self):
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=1.0,
            fidelity_level=2,
            sinc=np.array([5.0]),
            freq_hz=28e9,
        )
        d = r.to_dict()
        assert "sinc" in d
        assert "freq_hz" in d
        assert d["freq_hz"] == 28e9

    def test_none_fields_omitted(self):
        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        d = r.to_dict()
        assert "sinc" not in d
        assert "freq_hz" not in d
        assert "sinc_averaged" not in d
        assert "sab_1cm2_averaged" not in d
