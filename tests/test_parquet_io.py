"""Tests for Parquet read/write with provenance columns."""

import pandas as pd
import pytest

from aegis.basestation.parquet_io import (
    dataframe_to_basestations,
    read_merged_parquet,
    write_merged_parquet,
    write_raw_parquet,
)


@pytest.fixture
def sample_df():
    """Minimal 16-column DataFrame."""
    return pd.DataFrame(
        {
            "SiteCode": ["SITE001", "SITE002"],
            "AntennaLabel": ["ANT001", "ANT002"],
            "Operator": ["Proximus", "Orange"],
            "Technology": ["5G", "4G"],
            "Latitude": [50.85, 50.86],
            "Longitude": [4.35, 4.36],
            "CenterHeight": [25.0, 30.0],
            "Power": [46.0, 42.0],
            "Frequency": [3500.0, 1800.0],
            "FrequencyBand": ["Band3600MHz", "Band1800MHz"],
            "Electrical_Tilt": [6, 4],
            "Mechanical_Tilt": [0, 2],
            "Azimuth": [120, 240],
            "Gain": [18.0, 15.0],
            "Horizontal_Beamwidth": [65, 65],
            "Vertical_Beamwidth": [10, 12],
        }
    )


class TestWriteRawParquet:
    def test_roundtrip(self, sample_df, tmp_path):
        path = tmp_path / "raw.parquet"
        write_raw_parquet(sample_df, str(path))
        df_read = pd.read_parquet(str(path))
        assert len(df_read) == 2
        assert list(df_read.columns) == list(sample_df.columns)


class TestWriteMergedParquet:
    def test_adds_source_columns(self, sample_df, tmp_path):
        path = tmp_path / "merged.parquet"
        source_tag = "gov:brussels"
        write_merged_parquet(sample_df, str(path), source_tag=source_tag)
        df_read = pd.read_parquet(str(path))
        assert "Power_source" in df_read.columns
        assert "Azimuth_source" in df_read.columns
        assert "Pattern_source" in df_read.columns
        assert df_read["Power_source"].iloc[0] == source_tag


class TestReadMergedParquet:
    def test_returns_basestations_with_provenance(self, sample_df, tmp_path):
        path = tmp_path / "merged.parquet"
        write_merged_parquet(sample_df, str(path), source_tag="gov:brussels")
        basestations = read_merged_parquet(str(path))
        assert len(basestations) == 2
        bs = basestations[0]
        assert bs.frequency_band == "Band3600MHz"
        assert bs.eirp_dbm == 46.0
        prov = bs.provenance_dict
        assert prov["eirp_dbm"].origin == "gov:brussels"
        assert prov["eirp_dbm"].confidence == 1.0

    def test_bbox_filter(self, sample_df, tmp_path):
        path = tmp_path / "merged.parquet"
        write_merged_parquet(sample_df, str(path), source_tag="gov:brussels")
        bs = read_merged_parquet(str(path), bbox=[4.34, 4.355, 50.84, 50.855])
        assert len(bs) == 1
        assert bs[0].site_code == "SITE001"

    def test_operator_filter(self, sample_df, tmp_path):
        path = tmp_path / "merged.parquet"
        write_merged_parquet(sample_df, str(path), source_tag="gov:brussels")
        bs = read_merged_parquet(str(path), operator="Orange")
        assert len(bs) == 1
        assert bs[0].operator == "Orange"

    def test_frequency_band_filter(self, sample_df, tmp_path):
        path = tmp_path / "merged.parquet"
        write_merged_parquet(sample_df, str(path), source_tag="gov:brussels")
        bs = read_merged_parquet(str(path), frequency_band="Band3600MHz")
        assert len(bs) == 1

    def test_estimated_fields_get_lower_confidence(self, tmp_path):
        df = pd.DataFrame(
            {
                "SiteCode": ["SITE001"],
                "AntennaLabel": ["ANT001"],
                "Operator": ["TestOp"],
                "Technology": ["5G"],
                "Latitude": [50.85],
                "Longitude": [4.35],
                "CenterHeight": [25.0],
                "Power": [46.0],
                "Frequency": [3500.0],
                "FrequencyBand": ["Band3600MHz"],
                "Electrical_Tilt": [6],
                "Mechanical_Tilt": [0],
                "Azimuth": [120],
                "Gain": [18.0],
                "Horizontal_Beamwidth": [65],
                "Vertical_Beamwidth": [10],
                "Power_source": ["gov:brussels"],
                "Azimuth_source": ["gov:brussels"],
                "Gain_source": ["est:tech+band"],
                "CenterHeight_source": ["gov:brussels"],
                "Frequency_source": ["gov:brussels"],
                "FrequencyBand_source": ["gov:brussels"],
                "Electrical_Tilt_source": ["est:ref"],
                "Mechanical_Tilt_source": ["missing"],
                "Horizontal_Beamwidth_source": ["est:tech+band"],
                "Vertical_Beamwidth_source": ["est:tech+band"],
                "Pattern_source": ["synthetic:gaussian"],
            }
        )
        path = tmp_path / "mixed.parquet"
        df.to_parquet(str(path))
        basestations = read_merged_parquet(str(path))
        bs = basestations[0]
        prov = bs.provenance_dict
        assert prov["eirp_dbm"].confidence == 1.0
        assert prov["gain_dbi"].confidence == 0.3
        assert prov["mechanical_tilt_deg"].confidence == 0.0
        assert bs.pattern_source == "synthetic:gaussian"


class TestDataframeToBasestations:
    def test_converts_without_provenance(self, sample_df):
        basestations = dataframe_to_basestations(sample_df)
        assert len(basestations) == 2
        assert basestations[0].provenance == ()
