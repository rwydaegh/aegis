# Base station master dataset implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pipeline that stacks multiple base station data sources, fills gaps with estimation, tracks per-field provenance, and exposes data quality through the API and frontend.

**Architecture:** Two-layer Parquet pipeline (raw extractions + merged output with provenance columns). The build script extracts from basestationLib adapters, merges with spatial dedup and field-level priority, estimates missing values, and writes provenance tags. The viewer loads merged Parquet files and serves provenance through the API. Frontend shows confidence-colored antenna icons and per-field provenance in a detail panel.

**Tech Stack:** Python (pandas, pyarrow), basestationLib adapters, Flask API, React/TypeScript/Zustand/Three.js frontend.

**Spec:** `docs/superpowers/specs/2026-04-01-base-station-master-dataset-design.md`

**Pre-flight:** Before starting any task, verify baseline tests pass and install pyarrow:
```bash
python -m pytest tests/test_basestation.py tests/test_viewer_basestations.py -v -x  # must pass
pip install pyarrow>=14.0  # required for Parquet I/O
# Also add pyarrow to pyproject.toml under [project.optional-dependencies] viewer extra
```

---

## File structure

### New files
- `src/aegis/basestation/provenance.py` - FieldSource dataclass, confidence constants, aggregate scoring
- `src/aegis/basestation/utils.py` - Shared utilities (`_safe_float`, `_sanitize_label`) extracted from adapter.py to avoid circular imports
- `src/aegis/basestation/merge.py` - Operator normalization, spatial dedup, field-level priority merge, estimation with provenance
- `src/aegis/basestation/parquet_io.py` - Read/write Parquet with `_source` columns, DataFrame-to-BaseStation conversion with provenance
- `src/aegis/basestation/build.py` - CLI: extract, merge, validate, report, all
- `data/basestations/regions.yaml` - Region configuration
- `basestations/basestationLib/Countries/Denmark/basestations.py` - Mastedatabasen adapter
- `basestations/basestationLib/Countries/Denmark/__init__.py`
- `tests/test_provenance.py` - Provenance model tests
- `tests/test_merge.py` - Merge pipeline tests
- `tests/test_parquet_io.py` - Parquet round-trip tests
- `aegis-web/src/components/panels/AntennaDetailPanel.tsx` - Selected antenna detail view with provenance
- `aegis-web/src/components/panels/ProvenanceDot.tsx` - Colored dot component for provenance display
- `docs/superpowers/specs/country-adapters/` - ~18 spec files for future agents
- `docs/internal/frontend-basestation-handoff.md` - Context handoff for future frontend session

### Modified files
- `src/aegis/basestation/antenna.py` - Add `frequency_band`, `provenance`, `pattern_source` fields
- `src/aegis/basestation/adapter.py` - Add `load_basestations_from_parquet`, fix pattern auto-discovery, unify `_sanitize_label`
- `src/aegis/viewer/routes/basestations.py` - Parquet-first resolution, provenance in API, `_list_available_regions` update
- `basestations/basestationLib/core/country_module_map.json` - Add Denmark
- `tests/test_basestation.py` - Update BaseStation fixtures for new fields
- `aegis-web/src/api/basestations.ts` - Add `frequency_band`, `confidence`, `provenance`, `pattern_source` to `BaseStationData`
- `aegis-web/src/stores/basestations.ts` - Add `frequencyBands`, `enabledFrequencyBands`, filter logic
- `aegis-web/src/components/scene/BaseStationMarkers.tsx` - Confidence-based coloring
- `aegis-web/src/components/panels/BaseStationsPanel.tsx` - Frequency band filter, legend, detail panel integration

---

## Task 1: Provenance data model

**Files:**
- Create: `src/aegis/basestation/provenance.py`
- Create: `tests/test_provenance.py`

- [ ] **Step 1: Write failing tests for FieldSource and confidence scoring**

```python
# tests/test_provenance.py
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
        # Manually: (5*1 + 4*1 + 3*0.3 + 3*1 + 2*0.2 + 1*0 + 1*0 + 1*0.3 + 1*0.3) / (5+4+3+3+2+1+1+1+1)
        # = (5+4+0.9+3+0.4+0+0+0.3+0.3) / 21 = 13.9/21 = 0.6619
        assert score == pytest.approx(13.9 / 21, abs=0.01)

    def test_empty_provenance_gives_zero(self):
        assert aggregate_confidence(()) == pytest.approx(0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_provenance.py -v -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'aegis.basestation.provenance'`

- [ ] **Step 3: Implement provenance module**

```python
# src/aegis/basestation/provenance.py
"""Per-field provenance tracking and confidence scoring for base station data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSource:
    """Provenance of a single field value on a BaseStation."""

    origin: str  # e.g. "gov:brussels", "est:tech+band", "missing"
    confidence: float  # 0.0-1.0, field-level only


# Confidence by source type
CONFIDENCE_SCORES: dict[str, float] = {
    "gov_direct": 1.0,
    "gov_report": 0.8,
    "crowdsourced": 0.5,
    "est_same_dataset": 0.3,
    "est_reference": 0.2,
    "missing": 0.0,
}

# Dosimetric impact weights, keyed by BaseStation field name
DOSIMETRIC_WEIGHTS: dict[str, int] = {
    "eirp_dbm": 5,
    "azimuth_deg": 4,
    "height_m": 3,
    "freq_mhz": 3,
    "gain_dbi": 2,
    "electrical_tilt_deg": 1,
    "mechanical_tilt_deg": 1,
    "horizontal_beamwidth_deg": 1,
    "vertical_beamwidth_deg": 1,
}

# DataFrame column name -> BaseStation field name
COLUMN_TO_FIELD: dict[str, str] = {
    "Power": "eirp_dbm",
    "CenterHeight": "height_m",
    "Frequency": "freq_mhz",
    "Azimuth": "azimuth_deg",
    "Electrical_Tilt": "electrical_tilt_deg",
    "Mechanical_Tilt": "mechanical_tilt_deg",
    "Gain": "gain_dbi",
    "Horizontal_Beamwidth": "horizontal_beamwidth_deg",
    "Vertical_Beamwidth": "vertical_beamwidth_deg",
    "FrequencyBand": "frequency_band",
}

FIELD_TO_COLUMN: dict[str, str] = {v: k for k, v in COLUMN_TO_FIELD.items()}


def aggregate_confidence(
    provenance: tuple[tuple[str, FieldSource], ...],
) -> float:
    """Compute weighted aggregate confidence from per-field provenance."""
    if not provenance:
        return 0.0
    total_weight = 0
    weighted_sum = 0.0
    for field_name, source in provenance:
        w = DOSIMETRIC_WEIGHTS.get(field_name, 0)
        if w > 0:
            weighted_sum += w * source.confidence
            total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_provenance.py -v -x`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/provenance.py tests/test_provenance.py
git commit -m "Add provenance data model with confidence scoring"
```

---

## Task 2: Update BaseStation dataclass

**Files:**
- Modify: `src/aegis/basestation/antenna.py:88-126`
- Modify: `tests/test_basestation.py:306-340`

- [ ] **Step 1: Write failing test for new fields**

Add to `tests/test_basestation.py` in the `TestBaseStation` class:

```python
def test_frequency_band_field(self):
    bs = BaseStation(
        site_code="TEST001", antenna_label="test", operator="TestOp",
        technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
        eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
        electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
        horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
        frequency_band="Band3600MHz",
    )
    assert bs.frequency_band == "Band3600MHz"

def test_provenance_field(self):
    from aegis.basestation.provenance import FieldSource
    prov = (("eirp_dbm", FieldSource("gov:brussels", 1.0)),)
    bs = BaseStation(
        site_code="TEST001", antenna_label="test", operator="TestOp",
        technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
        eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
        electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
        horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
        provenance=prov,
    )
    assert bs.provenance_dict["eirp_dbm"].confidence == 1.0

def test_pattern_source_field(self):
    bs = BaseStation(
        site_code="TEST001", antenna_label="test", operator="TestOp",
        technology="5G NR", latitude=51.05, longitude=3.72, height_m=30.0,
        eirp_dbm=50.0, gain_dbi=17.0, freq_mhz=3500.0, azimuth_deg=120.0,
        electrical_tilt_deg=6.0, mechanical_tilt_deg=2.0,
        horizontal_beamwidth_deg=65.0, vertical_beamwidth_deg=10.0,
        pattern_source="synthetic:gaussian",
    )
    assert bs.pattern_source == "synthetic:gaussian"

def test_defaults_for_new_fields(self, bs):
    assert bs.frequency_band == ""
    assert bs.provenance == ()
    assert bs.pattern_source == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_basestation.py::TestBaseStation -v -x`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'frequency_band'`

- [ ] **Step 3: Add new fields to BaseStation**

In `src/aegis/basestation/antenna.py`, add three new fields after `pattern` (line 117) and before the existing `@property` block (line 119). The file already has `from __future__ import annotations` so forward references work. Use `TYPE_CHECKING` for the `FieldSource` import:

```python
# Add at the top of antenna.py, after existing imports:
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.basestation.provenance import FieldSource
```

Then add the fields between `pattern` and the existing properties:

```python
    pattern: AntennaPattern | None = None

    # Provenance (new fields - insert here, BEFORE the @property block)
    frequency_band: str = ""  # e.g. "Band3600MHz"
    provenance: tuple[tuple[str, FieldSource], ...] = ()  # (field_name, FieldSource) pairs
    pattern_source: str = ""  # "gov:brussels", "synthetic:gaussian", etc.

    @property
    def provenance_dict(self) -> dict[str, FieldSource]:
        """Dict access to provenance tuple."""
        return dict(self.provenance)

    # ... existing @property total_tilt_deg and freq_hz follow ...
```

IMPORTANT: The new fields MUST go before the existing `@property` methods (total_tilt_deg at line 119, freq_hz at line 124). Placing fields after a `@property` in a dataclass causes a TypeError.

- [ ] **Step 4: Run full test suite for basestation module**

Run: `python -m pytest tests/test_basestation.py -v -x`
Expected: all PASS (existing tests still work because new fields have defaults)

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/antenna.py tests/test_basestation.py
git commit -m "Add frequency_band, provenance, and pattern_source to BaseStation"
```

---

## Task 3: Parquet I/O

**Files:**
- Create: `src/aegis/basestation/parquet_io.py`
- Create: `tests/test_parquet_io.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_parquet_io.py
"""Tests for Parquet read/write with provenance columns."""

import numpy as np
import pandas as pd
import pytest

from aegis.basestation.parquet_io import (
    dataframe_to_basestations,
    write_raw_parquet,
    write_merged_parquet,
    read_merged_parquet,
)
from aegis.basestation.provenance import FieldSource


@pytest.fixture()
def sample_df():
    """Minimal 16-column DataFrame."""
    return pd.DataFrame({
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
    })


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
        # bbox that only includes SITE001 (lat 50.85, lon 4.35)
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
        df = pd.DataFrame({
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
        })
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_parquet_io.py -v -x`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement parquet_io module**

```python
# src/aegis/basestation/parquet_io.py
"""Parquet read/write for base station data with provenance columns."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aegis.basestation.utils import _safe_float, _sanitize_label
from aegis.basestation.antenna import AntennaPattern, BaseStation
from aegis.basestation.pattern import synthetic_pattern_from_beamwidth
from aegis.basestation.provenance import (
    COLUMN_TO_FIELD,
    CONFIDENCE_SCORES,
    FieldSource,
)

logger = logging.getLogger(__name__)

# Columns that get _source provenance tracking
_PROVENANCE_COLUMNS = [
    "CenterHeight", "Power", "Frequency", "FrequencyBand",
    "Electrical_Tilt", "Mechanical_Tilt", "Azimuth",
    "Gain", "Horizontal_Beamwidth", "Vertical_Beamwidth",
]

_SOURCE_CONFIDENCE: dict[str, float] = {
    "gov:brussels": CONFIDENCE_SCORES["gov_direct"],
    "gov:flanders": CONFIDENCE_SCORES["gov_direct"],
    "gov:anfr": CONFIDENCE_SCORES["gov_direct"],
    "gov:antenneregister": CONFIDENCE_SCORES["gov_direct"],
    "gov:mastedatabasen": CONFIDENCE_SCORES["gov_report"],
    "gov:bnetza": CONFIDENCE_SCORES["gov_report"],
    "ocid": CONFIDENCE_SCORES["crowdsourced"],
    "est:tech+band": CONFIDENCE_SCORES["est_same_dataset"],
    "est:ref": CONFIDENCE_SCORES["est_reference"],
    "missing": CONFIDENCE_SCORES["missing"],
}


def _confidence_for_source(source: str) -> float:
    """Map a source tag string to a confidence score."""
    if source in _SOURCE_CONFIDENCE:
        return _SOURCE_CONFIDENCE[source]
    if source.startswith("gov:"):
        return CONFIDENCE_SCORES["gov_report"]
    if source.startswith("est:"):
        return CONFIDENCE_SCORES["est_reference"]
    return 0.5  # unknown source, moderate confidence


def write_raw_parquet(df: pd.DataFrame, path: str) -> None:
    """Write a raw extraction DataFrame to Parquet (no provenance columns)."""
    df.to_parquet(path, index=False, engine="pyarrow")
    logger.info("Wrote %d rows to %s", len(df), path)


def write_merged_parquet(
    df: pd.DataFrame,
    path: str,
    source_tag: str = "unknown",
) -> None:
    """Write a merged DataFrame to Parquet, adding _source columns if missing."""
    out = df.copy()
    for col in _PROVENANCE_COLUMNS:
        src_col = f"{col}_source"
        if src_col not in out.columns:
            # Tag non-NaN values with source_tag, NaN values with "missing"
            if col in out.columns:
                out[src_col] = out[col].apply(
                    lambda v: "missing" if pd.isna(v) else source_tag
                )
            else:
                out[src_col] = "missing"
    if "Pattern_source" not in out.columns:
        out["Pattern_source"] = ""
    out.to_parquet(path, index=False, engine="pyarrow")
    logger.info("Wrote %d rows (merged) to %s", len(out), path)


def read_merged_parquet(
    path: str,
    bbox: list[float] | None = None,
    operator: str | None = None,
    technology: str | None = None,
    frequency_band: str | None = None,
    patterns: dict | None = None,
) -> list[BaseStation]:
    """Read a merged Parquet file into BaseStation objects with provenance."""
    df = pd.read_parquet(path, engine="pyarrow")

    # Apply filters
    if bbox and len(bbox) == 4:
        min_lon, max_lon, min_lat, max_lat = bbox
        df = df[
            (df["Longitude"] >= min_lon)
            & (df["Longitude"] <= max_lon)
            & (df["Latitude"] >= min_lat)
            & (df["Latitude"] <= max_lat)
        ]
    if operator:
        df = df[df["Operator"].str.contains(operator, case=False, na=False)]
    if technology:
        df = df[df["Technology"].str.contains(technology, case=False, na=False)]
    if frequency_band:
        df = df[df["FrequencyBand"] == frequency_band]

    has_provenance = any(f"{c}_source" in df.columns for c in _PROVENANCE_COLUMNS)
    return dataframe_to_basestations(df, patterns=patterns, with_provenance=has_provenance)


def dataframe_to_basestations(
    df: pd.DataFrame,
    patterns: dict | None = None,
    with_provenance: bool = False,
) -> list[BaseStation]:
    """Convert a DataFrame to BaseStation objects, optionally reading provenance."""
    patterns = patterns or {}
    result = []

    for _, row in df.iterrows():
        site = str(row.get("SiteCode", ""))
        label = str(row.get("AntennaLabel", ""))

        # Pattern lookup
        pattern = None
        pattern_source = ""
        key = _sanitize_label(f"{site}_{label}")
        if key in patterns:
            matrix = np.array(patterns[key], dtype=np.float32)
            if matrix.shape == (181, 360):
                pattern = AntennaPattern(
                    gain_dbi=matrix,
                    max_gain_dbi=float(np.nanmax(matrix)),
                )
                pattern_source = str(row.get("Pattern_source", "gov"))

        gain = _safe_float(row.get("Gain"), 0.0)
        if pattern is None:
            hbw = _safe_float(row.get("Horizontal_Beamwidth"), 0.0)
            vbw = _safe_float(row.get("Vertical_Beamwidth"), 0.0)
            if hbw > 0 and vbw > 0 and gain > 0:
                pattern = synthetic_pattern_from_beamwidth(hbw, vbw, gain)
                pattern_source = "synthetic:gaussian"

        if not pattern_source and "Pattern_source" in df.columns:
            pattern_source = str(row.get("Pattern_source", ""))

        # Build provenance
        prov: tuple[tuple[str, FieldSource], ...] = ()
        if with_provenance:
            prov_list = []
            for col in _PROVENANCE_COLUMNS:
                src_col = f"{col}_source"
                field_name = COLUMN_TO_FIELD.get(col, col)
                if src_col in df.columns:
                    src_val = str(row.get(src_col, "missing"))
                    conf = _confidence_for_source(src_val)
                    prov_list.append((field_name, FieldSource(origin=src_val, confidence=conf)))
            prov = tuple(prov_list)

        fb = str(row.get("FrequencyBand", ""))
        if fb == "nan" or pd.isna(row.get("FrequencyBand")):
            fb = ""

        result.append(
            BaseStation(
                site_code=site,
                antenna_label=label,
                operator=str(row.get("Operator", "")),
                technology=str(row.get("Technology", "")),
                latitude=float(row["Latitude"]),
                longitude=float(row["Longitude"]),
                height_m=_safe_float(row.get("CenterHeight"), 10.0),
                eirp_dbm=_safe_float(row.get("Power"), 30.0),
                gain_dbi=gain,
                freq_mhz=_safe_float(row.get("Frequency"), 2100.0),
                azimuth_deg=_safe_float(row.get("Azimuth"), 0.0),
                electrical_tilt_deg=_safe_float(row.get("Electrical_Tilt"), 0.0),
                mechanical_tilt_deg=_safe_float(row.get("Mechanical_Tilt"), 0.0),
                horizontal_beamwidth_deg=_safe_float(row.get("Horizontal_Beamwidth"), 65.0),
                vertical_beamwidth_deg=_safe_float(row.get("Vertical_Beamwidth"), 10.0),
                pattern=pattern,
                frequency_band=fb,
                provenance=prov,
                pattern_source=pattern_source,
            )
        )

    logger.info("Converted %d rows to BaseStation objects", len(result))
    return result
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_parquet_io.py -v -x`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/parquet_io.py tests/test_parquet_io.py
git commit -m "Add Parquet I/O with provenance column support"
```

---

## Task 4: Merge pipeline

**Files:**
- Create: `src/aegis/basestation/merge.py`
- Create: `tests/test_merge.py`

- [ ] **Step 1: Write failing tests for operator normalization and spatial dedup**

```python
# tests/test_merge.py
"""Tests for the merge pipeline: operator normalization, spatial dedup, field priority."""

import numpy as np
import pandas as pd
import pytest

from aegis.basestation.merge import (
    normalize_operator,
    spatial_dedup,
    merge_sources,
    estimate_with_provenance,
)


class TestNormalizeOperator:
    def test_lowercase_strip(self):
        assert normalize_operator("  Proximus  ") == "proximus"

    def test_known_alias(self):
        assert normalize_operator("BE:PROXIMUS") == "proximus"

    def test_unknown_passthrough(self):
        assert normalize_operator("SomeNewOp") == "somenewop"

    def test_none_returns_unknown(self):
        assert normalize_operator(None) == "unknown"

    def test_empty_returns_unknown(self):
        assert normalize_operator("") == "unknown"


class TestSpatialDedup:
    def test_nearby_same_operator_same_band_merges(self):
        df = pd.DataFrame({
            "SiteCode": ["S1", "S2"],
            "AntennaLabel": ["A1", "A2"],
            "Operator": ["Proximus", "Proximus"],
            "Technology": ["5G", "5G"],
            "Latitude": [50.850000, 50.850001],  # ~0.1m apart
            "Longitude": [4.350000, 4.350001],
            "CenterHeight": [25.0, np.nan],
            "Power": [46.0, np.nan],
            "Frequency": [3500.0, 3500.0],
            "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
            "Electrical_Tilt": [np.nan, np.nan],
            "Mechanical_Tilt": [np.nan, np.nan],
            "Azimuth": [120, np.nan],
            "Gain": [18.0, np.nan],
            "Horizontal_Beamwidth": [np.nan, np.nan],
            "Vertical_Beamwidth": [np.nan, np.nan],
        })
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 1

    def test_far_apart_does_not_merge(self):
        df = pd.DataFrame({
            "SiteCode": ["S1", "S2"],
            "AntennaLabel": ["A1", "A2"],
            "Operator": ["Proximus", "Proximus"],
            "Technology": ["5G", "5G"],
            "Latitude": [50.850, 50.860],  # ~1.1 km apart
            "Longitude": [4.350, 4.350],
            "CenterHeight": [25.0, 30.0],
            "Power": [46.0, 42.0],
            "Frequency": [3500.0, 3500.0],
            "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
            "Electrical_Tilt": [6, 4],
            "Mechanical_Tilt": [0, 0],
            "Azimuth": [120, 240],
            "Gain": [18.0, 15.0],
            "Horizontal_Beamwidth": [65, 65],
            "Vertical_Beamwidth": [10, 12],
        })
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2

    def test_different_operator_does_not_merge(self):
        df = pd.DataFrame({
            "SiteCode": ["S1", "S2"],
            "AntennaLabel": ["A1", "A2"],
            "Operator": ["Proximus", "Orange"],
            "Technology": ["5G", "5G"],
            "Latitude": [50.850000, 50.850001],
            "Longitude": [4.350000, 4.350001],
            "CenterHeight": [25.0, 30.0],
            "Power": [46.0, 42.0],
            "Frequency": [3500.0, 3500.0],
            "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
            "Electrical_Tilt": [6, 4],
            "Mechanical_Tilt": [0, 0],
            "Azimuth": [120, 240],
            "Gain": [18.0, 15.0],
            "Horizontal_Beamwidth": [65, 65],
            "Vertical_Beamwidth": [10, 12],
        })
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2

    def test_different_band_does_not_merge(self):
        df = pd.DataFrame({
            "SiteCode": ["S1", "S2"],
            "AntennaLabel": ["A1", "A2"],
            "Operator": ["Proximus", "Proximus"],
            "Technology": ["5G", "4G"],
            "Latitude": [50.850000, 50.850001],
            "Longitude": [4.350000, 4.350001],
            "CenterHeight": [25.0, 30.0],
            "Power": [46.0, 42.0],
            "Frequency": [3500.0, 1800.0],
            "FrequencyBand": ["Band3600MHz", "Band1800MHz"],
            "Electrical_Tilt": [6, 4],
            "Mechanical_Tilt": [0, 0],
            "Azimuth": [120, 240],
            "Gain": [18.0, 15.0],
            "Horizontal_Beamwidth": [65, 65],
            "Vertical_Beamwidth": [10, 12],
        })
        result = spatial_dedup(df, distance_m=50)
        assert len(result) == 2


class TestMergeSources:
    def test_higher_priority_fills_nan(self):
        gov = pd.DataFrame({
            "SiteCode": ["S1"], "AntennaLabel": ["A1"], "Operator": ["Proximus"],
            "Technology": ["5G"], "Latitude": [50.85], "Longitude": [4.35],
            "CenterHeight": [25.0], "Power": [46.0], "Frequency": [3500.0],
            "FrequencyBand": ["Band3600MHz"], "Electrical_Tilt": [pd.NA],
            "Mechanical_Tilt": [pd.NA], "Azimuth": [120], "Gain": [pd.NA],
            "Horizontal_Beamwidth": [pd.NA], "Vertical_Beamwidth": [pd.NA],
        })
        ocid = pd.DataFrame({
            "SiteCode": ["S2"], "AntennaLabel": ["A2"], "Operator": ["Proximus"],
            "Technology": ["5G"], "Latitude": [50.850001], "Longitude": [4.350001],
            "CenterHeight": [pd.NA], "Power": [pd.NA], "Frequency": [3500.0],
            "FrequencyBand": ["Band3600MHz"], "Electrical_Tilt": [pd.NA],
            "Mechanical_Tilt": [pd.NA], "Azimuth": [pd.NA], "Gain": [pd.NA],
            "Horizontal_Beamwidth": [pd.NA], "Vertical_Beamwidth": [pd.NA],
        })
        sources = [
            (gov, "gov:brussels", 1),
            (ocid, "ocid", 3),
        ]
        result = merge_sources(sources, distance_m=50)
        # Should merge into one row, taking gov values
        assert len(result) == 1
        assert result["Power_source"].iloc[0] == "gov:brussels"
        assert result["Azimuth_source"].iloc[0] == "gov:brussels"


class TestEstimateWithProvenance:
    def test_fills_nan_with_estimation_tag(self):
        df = pd.DataFrame({
            "SiteCode": ["S1", "S2"],
            "AntennaLabel": ["A1", "A2"],
            "Operator": ["Proximus", "Proximus"],
            "Technology": ["5G", "5G"],
            "Latitude": [50.85, 50.86],
            "Longitude": [4.35, 4.36],
            "CenterHeight": [25.0, 30.0],
            "Power": [46.0, np.nan],
            "Frequency": [3500.0, 3500.0],
            "FrequencyBand": ["Band3600MHz", "Band3600MHz"],
            "Electrical_Tilt": [6, np.nan],
            "Mechanical_Tilt": [0, np.nan],
            "Azimuth": [120, 240],
            "Gain": [18.0, np.nan],
            "Horizontal_Beamwidth": [65, np.nan],
            "Vertical_Beamwidth": [10, np.nan],
            "Power_source": ["gov:brussels", "missing"],
            "Azimuth_source": ["gov:brussels", "gov:brussels"],
            "Gain_source": ["gov:brussels", "missing"],
            "CenterHeight_source": ["gov:brussels", "gov:brussels"],
            "Frequency_source": ["gov:brussels", "gov:brussels"],
            "FrequencyBand_source": ["gov:brussels", "gov:brussels"],
            "Electrical_Tilt_source": ["gov:brussels", "missing"],
            "Mechanical_Tilt_source": ["gov:brussels", "missing"],
            "Horizontal_Beamwidth_source": ["gov:brussels", "missing"],
            "Vertical_Beamwidth_source": ["gov:brussels", "missing"],
            "Pattern_source": ["", ""],
        })
        result = estimate_with_provenance(df)
        # S2 Power was NaN, should be estimated from S1 (same Tech+Band)
        assert not pd.isna(result["Power"].iloc[1])
        assert result["Power_source"].iloc[1] == "est:tech+band"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_merge.py -v -x`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement merge module**

Create `src/aegis/basestation/merge.py`:

```python
"""Merge multiple base station sources with spatial dedup and provenance tagging."""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from aegis.basestation.parquet_io import _PROVENANCE_COLUMNS

logger = logging.getLogger(__name__)

# Known operator aliases -> canonical name
_OPERATOR_ALIASES: dict[str, str] = {
    "be:proximus": "proximus",
    "be:orange": "orange",
    "be:telenet": "telenet",
    "proximus group": "proximus",
    "orange belgium": "orange",
}


def normalize_operator(name: str | None) -> str:
    """Lowercase, strip, and resolve known aliases."""
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return "unknown"
    s = str(name).strip().lower()
    if not s:
        return "unknown"
    return _OPERATOR_ALIASES.get(s, s)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two WGS84 points."""
    R = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def spatial_dedup(df: pd.DataFrame, distance_m: float = 50) -> pd.DataFrame:
    """Deduplicate antennas: same normalized operator + within distance_m + same FrequencyBand.

    For matched pairs, take the first non-NaN value per column (rows are assumed
    to be sorted by priority, highest first).
    """
    if df.empty:
        return df

    df = df.copy()
    df["_norm_op"] = df["Operator"].apply(normalize_operator)

    merged_rows = []
    used = set()

    for i, row_i in df.iterrows():
        if i in used:
            continue
        cluster = [row_i]
        used.add(i)

        for j, row_j in df.iterrows():
            if j in used or j <= i:
                continue
            if row_i["_norm_op"] != row_j["_norm_op"]:
                continue
            fb_i = row_i.get("FrequencyBand", "")
            fb_j = row_j.get("FrequencyBand", "")
            if pd.notna(fb_i) and pd.notna(fb_j) and fb_i != fb_j:
                continue
            dist = _haversine_m(
                row_i["Latitude"], row_i["Longitude"],
                row_j["Latitude"], row_j["Longitude"],
            )
            if dist <= distance_m:
                cluster.append(row_j)
                used.add(j)

        # Merge cluster: take first non-NaN per column
        if len(cluster) == 1:
            merged_rows.append(cluster[0])
        else:
            merged = cluster[0].copy()
            for other in cluster[1:]:
                for col in merged.index:
                    if col == "_norm_op":
                        continue
                    if pd.isna(merged[col]) and pd.notna(other[col]):
                        merged[col] = other[col]
            merged_rows.append(merged)

    result = pd.DataFrame(merged_rows).reset_index(drop=True)
    result.drop(columns=["_norm_op"], inplace=True, errors="ignore")
    return result


def merge_sources(
    sources: list[tuple[pd.DataFrame, str, int]],
    distance_m: float = 50,
) -> pd.DataFrame:
    """Merge multiple (df, source_tag, priority) tuples into one DataFrame.

    Lower priority number = higher quality. Adds _source columns per field.
    """
    # Sort by priority (highest quality first)
    sources = sorted(sources, key=lambda x: x[2])

    tagged_dfs = []
    for df, source_tag, _priority in sources:
        df = df.copy()
        for col in _PROVENANCE_COLUMNS:
            src_col = f"{col}_source"
            if src_col not in df.columns:
                if col in df.columns:
                    df[src_col] = df[col].apply(
                        lambda v, st=source_tag: "missing" if pd.isna(v) else st
                    )
                else:
                    df[src_col] = "missing"
        if "Pattern_source" not in df.columns:
            df["Pattern_source"] = ""
        tagged_dfs.append(df)

    combined = pd.concat(tagged_dfs, ignore_index=True)
    return spatial_dedup(combined, distance_m=distance_m)


def estimate_with_provenance(
    df: pd.DataFrame,
    reference_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Fill NaN numeric values using Technology+FrequencyBand medians, tagging provenance.

    Adapted from basestations/basestationLib/utils/estimate_missing_data.py
    but writes _source columns instead of silently filling.
    """
    NUMERIC_COLS = ["Power", "Electrical_Tilt", "Mechanical_Tilt", "Gain", "Horizontal_Beamwidth", "Vertical_Beamwidth"]
    df = df.copy()

    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")

    has_fb = "FrequencyBand" in df.columns and df["FrequencyBand"].notna().any()

    # Stage A: estimate from same dataset
    if has_fb:
        means_tf = df.groupby(["Technology", "FrequencyBand"])[NUMERIC_COLS].median()
        for col in NUMERIC_COLS:
            if col not in df.columns:
                continue
            src_col = f"{col}_source"
            nan_mask = df[col].isna()
            if not nan_mask.any():
                continue
            for idx in df[nan_mask].index:
                tech = df.at[idx, "Technology"]
                fb = df.at[idx, "FrequencyBand"]
                if pd.notna(tech) and pd.notna(fb) and (tech, fb) in means_tf.index:
                    val = means_tf.at[(tech, fb), col]
                    if pd.notna(val):
                        df.at[idx, col] = val
                        if src_col in df.columns:
                            df.at[idx, src_col] = "est:tech+band"

    # Stage B: estimate from reference dataset
    if reference_df is not None:
        ref_has_fb = "FrequencyBand" in reference_df.columns and reference_df["FrequencyBand"].notna().any()
        if ref_has_fb:
            ref_means = reference_df.groupby(["Technology", "FrequencyBand"])[NUMERIC_COLS].median()
            for col in NUMERIC_COLS:
                if col not in df.columns:
                    continue
                src_col = f"{col}_source"
                nan_mask = df[col].isna()
                if not nan_mask.any():
                    continue
                for idx in df[nan_mask].index:
                    tech = df.at[idx, "Technology"]
                    fb = df.at[idx, "FrequencyBand"]
                    if pd.notna(tech) and pd.notna(fb) and (tech, fb) in ref_means.index:
                        val = ref_means.at[(tech, fb), col]
                        if pd.notna(val):
                            df.at[idx, col] = val
                            if src_col in df.columns:
                                df.at[idx, src_col] = "est:ref"

    return df
```

Note: The spatial_dedup uses a simple O(n^2) pairwise distance check. For datasets under ~10K antennas this is fine (Brussels has 626). For larger datasets, replace with `scipy.spatial.KDTree` after converting lat/lon to meters. The implementing agent can optimize later if needed.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_merge.py -v -x`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/basestation/merge.py tests/test_merge.py
git commit -m "Add merge pipeline with spatial dedup and provenance tagging"
```

---

## Task 5: Build CLI

**Files:**
- Create: `src/aegis/basestation/build.py`
- Create: `data/basestations/regions.yaml`

- [ ] **Step 1: Write a smoke test**

```python
# tests/test_build.py
"""Smoke tests for the build CLI."""

import subprocess

def test_build_cli_help():
    """Verify the build CLI is importable and has expected subcommands."""
    result = subprocess.run(
        ["python", "-m", "aegis.basestation.build", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "extract" in result.stdout
    assert "merge" in result.stdout
    assert "validate" in result.stdout
    assert "report" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build.py::test_build_cli_help -v -x`
Expected: FAIL

- [ ] **Step 3: Implement build CLI**

Create `src/aegis/basestation/build.py` with `argparse` subcommands:

- `extract --region NAME [--force]` - Calls basestationLib adapter for the region defined in `regions.yaml`, writes to `data/basestations/raw/{name}_{source_type}.parquet`
- `merge --region NAME` - Loads all raw files for the region, runs `merge_sources` + `estimate_with_provenance`, writes to `data/basestations/merged/{name}.parquet`
- `validate --region NAME` - Reads merged Parquet, checks value ranges, prints warnings
- `report` - Reads all merged Parquet files, prints a coverage table (% filled per column per region)
- `all [--force]` - Runs extract + merge + validate for all regions in `regions.yaml`

Add `__main__.py` entry or use `if __name__ == "__main__"` in `build.py`.

- [ ] **Step 4: Create regions.yaml**

```yaml
# data/basestations/regions.yaml
# bbox format: [min_lon, max_lon, min_lat, max_lat]
regions:
  brussels:
    sources:
      - type: basestationlib
        country: Belgium
        region: brussels
        priority: 1
    reference: data/basestations/raw/brussels_gov.parquet

  flanders:
    sources:
      - type: basestationlib
        country: Belgium
        region: flanders
        priority: 1
    reference: data/basestations/raw/brussels_gov.parquet

  france:
    sources:
      - type: basestationlib
        country: France
        bbox: [1.5, 3.0, 48.5, 49.2]  # [min_lon, max_lon, min_lat, max_lat]
        priority: 1
      - type: opencellid
        country_code: 208
        bbox: [1.5, 3.0, 48.5, 49.2]
        priority: 3
    reference: data/basestations/raw/brussels_gov.parquet

  denmark:
    sources:
      - type: mastedatabasen
        bbox: [12.4, 12.7, 55.6, 55.8]  # Copenhagen area
        priority: 1
      - type: opencellid
        country_code: 238
        bbox: [12.4, 12.7, 55.6, 55.8]
        priority: 3
    reference: data/basestations/raw/brussels_gov.parquet
```

- [ ] **Step 5: Run test and verify it passes**

Run: `python -m pytest tests/test_build.py -v -x`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/aegis/basestation/build.py data/basestations/regions.yaml tests/test_build.py
git commit -m "Add build CLI for extract/merge/validate pipeline"
```

---

## Task 6: Extract shared utils, fix adapter bugs, add Parquet loader

**Files:**
- Create: `src/aegis/basestation/utils.py`
- Modify: `src/aegis/basestation/adapter.py`
- Modify: `src/aegis/viewer/routes/basestations.py:18-23,539-567`
- Modify: `tests/test_basestation.py`

- [ ] **Step 0: Extract _safe_float and _sanitize_label to utils.py**

Move `_safe_float` and `_sanitize_label` from `adapter.py` to a new `src/aegis/basestation/utils.py`. Update imports in `adapter.py` to import from `utils`. This avoids a circular import: `parquet_io.py` needs these functions, and `adapter.py` will import from `parquet_io.py`.

```python
# src/aegis/basestation/utils.py
"""Shared utilities for the basestation module."""

from __future__ import annotations

import re

import numpy as np


def _sanitize_label(label: str) -> str:
    """Replace special characters with underscores for pattern key lookup."""
    return re.sub(r"[() .&/\\-]", "_", label)


def _safe_float(val, default: float = 0.0) -> float:
    """Convert to float, returning default for NaN/None."""
    try:
        f = float(val)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default
```

In `adapter.py`, replace the function definitions with:
```python
from aegis.basestation.utils import _safe_float, _sanitize_label
```

Run `python -m pytest tests/test_basestation.py -v -x` to verify existing tests still pass with the moved functions.

- [ ] **Step 1: Write test for pattern auto-discovery**

```python
# Add to tests/test_basestation.py
class TestLoadBasestationsFromCsvPatterns:
    def test_auto_discovers_patterns_mat(self, tmp_path):
        """CSV loader should auto-discover patterns/*.mat in the data dir."""
        import pandas as pd
        from aegis.basestation.adapter import load_basestations_from_csv

        # Create a minimal CSV
        csv_path = tmp_path / "brussels.csv"
        df = pd.DataFrame({
            "SiteCode": ["S1"], "AntennaLabel": ["A1"],
            "Operator": ["Test"], "Technology": ["5G"],
            "Latitude": [50.85], "Longitude": [4.35],
            "CenterHeight": [25.0], "Power": [46.0],
            "Frequency": [3500.0], "FrequencyBand": ["Band3600MHz"],
            "Electrical_Tilt": [6], "Mechanical_Tilt": [0],
            "Azimuth": [120], "Gain": [18.0],
            "Horizontal_Beamwidth": [65], "Vertical_Beamwidth": [10],
        })
        df.to_csv(str(csv_path), index=False)
        basestations = load_basestations_from_csv(str(csv_path))
        # Should succeed even without patterns.mat (just uses synthetic)
        assert len(basestations) == 1
        assert basestations[0].frequency_band == "Band3600MHz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_basestation.py::TestLoadBasestationsFromCsvPatterns -v -x`
Expected: FAIL (BaseStation doesn't have frequency_band yet in adapter output)

- [ ] **Step 3: Update adapter.py**

Changes to `src/aegis/basestation/adapter.py`:

1. `load_basestations_from_df` - Pass `frequency_band` from the DataFrame's `FrequencyBand` column
2. `load_basestations_from_csv` - Auto-discover `patterns/{region}.mat` by checking sibling directories of the CSV path
3. Add `load_basestations_from_parquet` that delegates to `parquet_io.read_merged_parquet`
4. Unify `_sanitize_label` (it's already the single implementation, just verify the basestationLib one matches)

Key change in `load_basestations_from_df`:
```python
fb = str(row.get("FrequencyBand", ""))
if fb == "nan" or pd.isna(row.get("FrequencyBand")):
    fb = ""

result.append(
    BaseStation(
        # ... existing fields ...
        frequency_band=fb,
    )
)
```

- [ ] **Step 4: Update viewer route**

Changes to `src/aegis/viewer/routes/basestations.py`:

1. Update `_list_available_regions` to also check `data/basestations/merged/*.parquet`
2. Update `_handle_basestations_load` to try Parquet first: `data/basestations/merged/{region}.parquet`
3. Update `_bs_summary` to include `frequency_band`, `confidence`, `pattern_source`, and `provenance`

In `_bs_summary`:
```python
from aegis.basestation.provenance import aggregate_confidence

def _bs_summary(bs) -> dict:
    classification = classify_basestation(...)
    prov_dict = bs.provenance_dict
    return {
        # ... existing fields ...
        "frequency_band": bs.frequency_band,
        "pattern_source": bs.pattern_source,
        "confidence": aggregate_confidence(bs.provenance),
        "provenance": {
            k: {"origin": v.origin, "confidence": v.confidence}
            for k, v in prov_dict.items()
        },
        **classification,
    }
```

- [ ] **Step 5: Run all basestation tests**

Run: `python -m pytest tests/test_basestation.py tests/test_viewer_basestations.py -v -x`
Expected: all PASS

- [ ] **Step 6: Lint**

Run: `python -m ruff check src/aegis/basestation/ src/aegis/viewer/routes/basestations.py`
Run: `python -m ruff format src/aegis/basestation/ src/aegis/viewer/routes/basestations.py`

- [ ] **Step 7: Commit**

```bash
git add src/aegis/basestation/adapter.py src/aegis/viewer/routes/basestations.py tests/test_basestation.py
git commit -m "Fix adapter bugs: frequency_band passthrough, pattern auto-discovery, Parquet-first loading"
```

---

## Task 7: Denmark adapter

**Files:**
- Create: `basestations/basestationLib/Countries/Denmark/__init__.py`
- Create: `basestations/basestationLib/Countries/Denmark/basestations.py`
- Modify: `basestations/basestationLib/core/country_module_map.json`

- [ ] **Step 1: Read existing adapter for reference pattern**

Read `basestations/basestationLib/Countries/France/basestations.py` to understand the adapter interface (constructor, `extract_antennas` method, expected return type).

- [ ] **Step 2: Implement Denmark adapter**

The adapter calls `dk-api.mastdatabase.co.uk` JSON:API. Key implementation details:
- `GET /sites?filter[bounds]=lat1,lon1,lat2,lon2` for bbox queries
- Paginate with `page[number]` and `page[size]=5000`
- Map response fields to the 16-column schema
- Fields available: location, operator, technology, frequency band
- Fields missing: power, height, azimuth, tilt, gain, beamwidth (leave as NaN for estimation later)

- [ ] **Step 3: Add Denmark to country_module_map.json**

```json
"denmark": "basestationLib.Countries.Denmark.basestations"
```

- [ ] **Step 4: Test with a small bbox**

Run: `cd basestations && python -c "from basestationLib import get_basestation_instance; BS = get_basestation_instance('Denmark'); inst = BS(output_folder='/tmp/dk_test'); df = inst.extract_antennas(config={}); print(len(df), df.columns.tolist())"`

Verify it returns a DataFrame with the expected columns.

- [ ] **Step 5: Commit**

```bash
git add basestations/basestationLib/Countries/Denmark/ basestations/basestationLib/core/country_module_map.json
git commit -m "Add Denmark adapter for Mastedatabasen API"
```

---

## Task 8: Extract and build data

**Files:**
- Create: `data/basestations/raw/*.parquet`
- Create: `data/basestations/merged/*.parquet`

This task requires network access to the basestationLib APIs.

- [ ] **Step 1: Extract Brussels**

```bash
python -m aegis.basestation.build extract --region brussels
```

Verify: `ls -la data/basestations/raw/brussels_gov.parquet`

- [ ] **Step 2: Extract Flanders**

```bash
python -m aegis.basestation.build extract --region flanders
```

- [ ] **Step 3: Extract France**

```bash
python -m aegis.basestation.build extract --region france
```

- [ ] **Step 4: Extract Denmark**

```bash
python -m aegis.basestation.build extract --region denmark
```

- [ ] **Step 5: Merge all regions**

```bash
python -m aegis.basestation.build merge --region brussels
python -m aegis.basestation.build merge --region flanders
python -m aegis.basestation.build merge --region france
python -m aegis.basestation.build merge --region denmark
```

- [ ] **Step 6: Validate and report**

```bash
python -m aegis.basestation.build report
```

Expected: a table showing % of each column filled per region, with source distribution.

- [ ] **Step 7: Copy patterns**

Copy existing `patterns.mat` files to the new `data/basestations/patterns/` directory:

```bash
mkdir -p data/basestations/patterns
cp basestations/basestationLib/Countries/Belgium/brussels/patterns.mat data/basestations/patterns/brussels.mat
# Only if flanders patterns.mat exists:
cp basestations/basestationLib/Countries/Belgium/flanders/patterns.mat data/basestations/patterns/flanders.mat 2>/dev/null || true
```

- [ ] **Step 8: Check file sizes and commit**

Check sizes first. Parquet files for a single city bbox should be small (< 1 MB). The project's `.gitignore` forbids large binaries.

```bash
du -sh data/basestations/raw/*.parquet data/basestations/merged/*.parquet
```

If any file exceeds 10 MB, add `data/basestations/raw/` and `data/basestations/merged/` to `.gitignore` and document that the build pipeline must be run locally. Otherwise commit:

```bash
git add data/basestations/regions.yaml data/basestations/merged/ data/basestations/raw/
git commit -m "Add pre-built Parquet datasets for Brussels, Flanders, France, Denmark"
```

---

## Task 9: Frontend updates

**Files:**
- Modify: `aegis-web/src/api/basestations.ts:5-27`
- Modify: `aegis-web/src/stores/basestations.ts`
- Modify: `aegis-web/src/components/scene/BaseStationMarkers.tsx`
- Modify: `aegis-web/src/components/panels/BaseStationsPanel.tsx`
- Create: `aegis-web/src/components/panels/AntennaDetailPanel.tsx`
- Create: `aegis-web/src/components/panels/ProvenanceDot.tsx`

- [ ] **Step 1: Update BaseStationData interface**

In `aegis-web/src/api/basestations.ts`, add to the `BaseStationData` interface:

```typescript
frequency_band: string
confidence: number
pattern_source: string
provenance: Record<string, { origin: string; confidence: number }>
```

- [ ] **Step 2: Update Zustand store for frequency band filter**

In `aegis-web/src/stores/basestations.ts`:
- Add `frequencyBands: string[]` and `enabledFrequencyBands: Set<string>` to state
- Add `toggleFrequencyBand(band: string)` action
- Update `deriveFilters` to extract unique frequency bands
- Update `computeActiveCount` and `activeIndices` to include frequency band filter

- [ ] **Step 3: Create ProvenanceDot component**

```tsx
// aegis-web/src/components/panels/ProvenanceDot.tsx
interface Props {
  confidence: number
  title?: string
}

const colorForConfidence = (c: number) => {
  if (c > 0.7) return '#22c55e'  // green
  if (c > 0.4) return '#eab308'  // yellow
  if (c > 0.2) return '#f97316'  // orange
  return '#ef4444'               // red
}

export function ProvenanceDot({ confidence, title }: Props) {
  return (
    <span
      className="inline-block w-2 h-2 rounded-full"
      style={{ backgroundColor: colorForConfidence(confidence) }}
      title={title ?? `Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  )
}
```

- [ ] **Step 4: Create AntennaDetailPanel**

`aegis-web/src/components/panels/AntennaDetailPanel.tsx` - Shows when `selectedIndex !== null`. Displays all antenna fields with provenance dots next to each value. Currently there is no detail panel (identified gap in code audit).

Key fields to show:
- Operator, technology, frequency band
- EIRP, gain, frequency (with provenance dots)
- Azimuth, tilt, height (with provenance dots)
- Beamwidth H/V (with provenance dots)
- Pattern source
- Overall confidence score with color

- [ ] **Step 5: Update BaseStationMarkers for confidence coloring**

In `aegis-web/src/components/scene/BaseStationMarkers.tsx`:

Replace the `OPERATOR_COLORS` map with a confidence-based coloring function. Keep operator colors as a secondary visual (e.g., on the pole) but color the panel face by confidence:

```typescript
const confidenceColor = (c: number) => {
  if (c > 0.7) return '#22c55e'
  if (c > 0.4) return '#eab308'
  if (c > 0.2) return '#f97316'
  return '#ef4444'
}
```

- [ ] **Step 6: Update BaseStationsPanel**

In `aegis-web/src/components/panels/BaseStationsPanel.tsx`:
- Add frequency band checkboxes (same pattern as operator/technology checkboxes)
- Add a small legend explaining confidence colors
- Integrate `AntennaDetailPanel` below the checkbox section (shown when an antenna is selected)

- [ ] **Step 7: Handle backwards compatibility with CSV-backed data**

When the backend serves data from old CSV files (no provenance), `confidence` will be `0` and `provenance` will be `{}`. All components must handle these gracefully:
- `ProvenanceDot`: don't render if `confidence === undefined`
- `AntennaDetailPanel`: show "No provenance data" if `provenance` is empty
- `BaseStationMarkers`: fall back to operator-based coloring if `confidence === 0` or `undefined`

- [ ] **Step 8: Build and verify**

```bash
cd aegis-web && npm run build
```

Expected: no TypeScript errors, build succeeds.

- [ ] **Step 8: Commit**

```bash
cd aegis-web
git add src/api/basestations.ts src/stores/basestations.ts src/components/
git commit -m "Add confidence coloring, provenance dots, frequency band filter, antenna detail panel"
```

---

## Task 10: Country adapter specs

**Files:**
- Create: `docs/superpowers/specs/country-adapters/*.md` (~18 files)

Write one standalone spec per country/source. Each spec follows this template:

```markdown
# [Country] adapter spec

## Source
- Name: [official name]
- URL: [API/download URL]
- Type: [REST API / WFS / SPARQL / scraping / bulk download]
- Auth: [API key / none / rate-limited]

## Fields available
[table of which 16 columns this source provides natively]

## Fields missing
[list of columns that will be NaN, to be filled by estimation]

## Extraction method
[exact API calls with curl examples, pagination, rate limits]

## Gotchas
[known issues: 403s, slow extraction, data quirks]

## Test region
- bbox: [min_lon, max_lon, min_lat, max_lat]
- Expected rows: ~N
- Expected time: ~X seconds

## Output
- Raw file: `data/basestations/raw/{name}.parquet`
- Source tag: `gov:{name}` or `ocid`
- Priority: N (1=highest)

## Implementation
- File: `basestations/basestationLib/Countries/{Country}/basestations.py`
- Add to `country_module_map.json`: `"{country}": "basestationLib.Countries.{Country}.basestations"`
- Follow existing adapter pattern (constructor with bbox/operator/technology/max_workers, `extract_antennas(config)` method)
```

Countries to spec:
- Tier 2: Germany, Netherlands, Austria, Spain, Switzerland, Poland, Ireland, Italy-Lombardy
- Tier 3: Australia, Canada, New Zealand
- Tier 4: OpenCellID global
- Tier 5: CommScope patterns, MSI library, 3GPP parametric

Use the research in `docs/internal/base-station-data-sources.md` for the details.

- [ ] **Step 1: Create country-adapters/ directory**

```bash
mkdir -p docs/superpowers/specs/country-adapters
```

- [ ] **Step 2: Write tier 2 specs (8 files)**

Write specs for: Germany, Netherlands, Austria, Spain, Switzerland, Poland, Ireland, Italy-Lombardy. For countries that already have adapters (Netherlands, Austria, Spain, Switzerland, Poland), the spec should note "adapter exists, needs Parquet migration" and document the existing adapter path.

- [ ] **Step 3: Write tier 3 specs (3 files)**

Australia (ACMA), Canada (ISED), New Zealand (RSM).

- [ ] **Step 4: Write tier 4-5 specs (4 files)**

OpenCellID global, CommScope patterns, MSI library, 3GPP parametric.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/country-adapters/
git commit -m "Add country adapter specs for future agents (18 countries/sources)"
```

---

## Task 11: Frontend context handoff doc

**Files:**
- Create: `docs/internal/frontend-basestation-handoff.md`

- [ ] **Step 1: Write the handoff document**

This document is for a future agent doing the "beautiful frontend" brainstorming session. It should contain:

1. **Current state** - What was implemented in this session (confidence colors, provenance dots, detail panel, frequency band filter)
2. **API contract** - Exact JSON shape of `_bs_summary()` response including all provenance fields
3. **Zustand store shape** - All fields in `useBaseStationsStore` after this session's changes
4. **Component tree** - Which files render what, with paths and line numbers
5. **What's missing** - The full list of frontend improvements deferred to the "beautiful" session:
   - Data source legend/attribution panel
   - Coverage overlay showing which source covers which area
   - Per-source confidence histogram
   - Antenna comparison view (side-by-side two antennas)
   - Map-level heatmap of data quality
   - Interactive estimation explanation ("this power was estimated because...")
   - Radiation pattern 3D visualization per antenna
6. **Design constraints** - The existing tech stack (React, Three.js/R3F, Zustand, Tailwind, shadcn/ui)

- [ ] **Step 2: Commit**

```bash
git add docs/internal/frontend-basestation-handoff.md
git commit -m "Add frontend context handoff doc for future base station UI session"
```

---

## Task 12: Final lint, test, and push

- [ ] **Step 1: Run full lint**

```bash
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
```

Fix any issues.

- [ ] **Step 2: Run full test suite (non-slow)**

```bash
python -m pytest tests/ -m "not slow" -x
```

All tests must pass.

- [ ] **Step 3: Build frontend**

```bash
cd aegis-web && npm run build
```

Must succeed without errors.

- [ ] **Step 4: Push**

```bash
git push origin master
```
