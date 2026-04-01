"""Tests for provenance data model and confidence scoring."""

import pytest

from aegis.basestation.provenance import (
    CONFIDENCE_SCORES,
    DOSIMETRIC_WEIGHTS,
    FieldSource,
    aggregate_confidence,
)


class TestFieldSource:
    def test_frozen(self):
        fs = FieldSource(origin="gov:brussels", confidence=1.0)
        with pytest.raises(AttributeError):
            fs.origin = "other"

    def test_fields(self):
        fs = FieldSource(origin="est:tech+band", confidence=0.3)
        assert fs.origin == "est:tech+band"
        assert fs.confidence == 0.3


class TestConfidenceScores:
    def test_gov_direct_is_highest(self):
        assert CONFIDENCE_SCORES["gov_direct"] == 1.0

    def test_missing_is_zero(self):
        assert CONFIDENCE_SCORES["missing"] == 0.0

    def test_ordering(self):
        scores = CONFIDENCE_SCORES
        assert scores["gov_direct"] > scores["gov_report"] > scores["crowdsourced"]
        assert scores["crowdsourced"] > scores["est_same_dataset"] > scores["est_reference"]
        assert scores["est_reference"] > scores["missing"]


class TestDosimetricWeights:
    def test_power_is_heaviest(self):
        assert DOSIMETRIC_WEIGHTS["eirp_dbm"] == 5

    def test_beamwidth_is_lightest(self):
        assert DOSIMETRIC_WEIGHTS["horizontal_beamwidth_deg"] == 1
        assert DOSIMETRIC_WEIGHTS["vertical_beamwidth_deg"] == 1


class TestAggregateConfidence:
    def test_all_government_gives_one(self):
        prov = tuple(
            (field, FieldSource(origin="gov:brussels", confidence=1.0))
            for field in DOSIMETRIC_WEIGHTS
        )
        assert aggregate_confidence(prov) == pytest.approx(1.0)

    def test_all_missing_gives_zero(self):
        prov = tuple(
            (field, FieldSource(origin="missing", confidence=0.0))
            for field in DOSIMETRIC_WEIGHTS
        )
        assert aggregate_confidence(prov) == pytest.approx(0.0)

    def test_mixed_provenance(self):
        prov = (
            ("eirp_dbm", FieldSource("gov:brussels", 1.0)),
            ("azimuth_deg", FieldSource("gov:brussels", 1.0)),
            ("height_m", FieldSource("est:tech+band", 0.3)),
            ("freq_mhz", FieldSource("gov:brussels", 1.0)),
            ("gain_dbi", FieldSource("est:ref", 0.2)),
            ("electrical_tilt_deg", FieldSource("missing", 0.0)),
            ("mechanical_tilt_deg", FieldSource("missing", 0.0)),
            ("horizontal_beamwidth_deg", FieldSource("est:tech+band", 0.3)),
            ("vertical_beamwidth_deg", FieldSource("est:tech+band", 0.3)),
        )
        score = aggregate_confidence(prov)
        assert 0.0 < score < 1.0
        assert score == pytest.approx(13.9 / 21, abs=0.01)

    def test_empty_provenance_gives_zero(self):
        assert aggregate_confidence(()) == pytest.approx(0.0)
