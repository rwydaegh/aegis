"""Tests for the antenna pattern SQLite library."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aegis.basestation.library import AntennaPatternLibrary


@pytest.fixture()
def library(tmp_path: Path) -> AntennaPatternLibrary:
    """Set up a library backed by the test_patterns.zip fixture."""
    msi_dir = tmp_path / "antenna_patterns" / "msi_raw"
    msi_dir.mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "test_patterns.zip"
    shutil.copy(fixture, msi_dir / "TestMfg.zip")
    return AntennaPatternLibrary(data_dir=str(tmp_path))


def test_build_index(library: AntennaPatternLibrary) -> None:
    count = library.build_index()
    assert count == 3


def test_search_by_manufacturer(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(manufacturer="TestMfg")
    assert len(results) == 3


def test_search_by_query(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(query="Model_A")
    assert len(results) == 1
    assert results[0].model == "Model_A"


def test_search_by_freq_range(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(freq_min_mhz=1700, freq_max_mhz=1900)
    assert len(results) == 1
    assert results[0].frequency_mhz == 1800.0


def test_search_by_gain_range(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(gain_min_dbi=10.0, gain_max_dbi=13.0)
    assert len(results) == 1
    assert results[0].gain_dbi == 12.0


def test_load_pattern(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(query="Model_A")
    pattern = library.load_pattern(source="local", pattern_id=results[0].id)
    assert pattern.gain_dbi.shape == (181, 360)
    assert pattern.max_gain_dbi == 8.0


def test_auto_build_on_first_search(tmp_path: Path) -> None:
    msi_dir = tmp_path / "antenna_patterns" / "msi_raw"
    msi_dir.mkdir(parents=True)
    fixture = Path(__file__).parent / "fixtures" / "test_patterns.zip"
    shutil.copy(fixture, msi_dir / "TestMfg.zip")
    lib = AntennaPatternLibrary(data_dir=str(tmp_path))
    # No explicit build_index call
    results = lib.search(query="Model_A")
    assert len(results) == 1


def test_rebuild_replaces_old_index(library: AntennaPatternLibrary) -> None:
    count1 = library.build_index()
    count2 = library.build_index()
    assert count1 == count2 == 3


def test_load_unknown_source(library: AntennaPatternLibrary) -> None:
    library.build_index()
    with pytest.raises(ValueError, match="Unknown source"):
        library.load_pattern(source="mars", pattern_id="x")


def test_load_missing_pattern(library: AntennaPatternLibrary) -> None:
    library.build_index()
    with pytest.raises(KeyError, match="Pattern not found"):
        library.load_pattern(source="local", pattern_id="nonexistent/foo")


def test_search_result_fields(library: AntennaPatternLibrary) -> None:
    library.build_index()
    results = library.search(query="Model_C")
    assert len(results) == 1
    r = results[0]
    assert r.source == "local"
    assert r.manufacturer == "TestMfg"
    assert r.model == "Model_C"
    assert r.frequency_mhz == 2100.0
    assert r.gain_dbi == 15.0
    assert r.tilt_deg == 0.0


def test_load_from_embedded_content(library: AntennaPatternLibrary) -> None:
    """Loading works from embedded MSI content even when zip files are gone."""
    library.build_index()
    results = library.search(query="Model_A")
    pattern_id = results[0].id

    # Remove the zip file so only the embedded content in SQLite remains
    msi_dir = Path(library._data_dir) / "antenna_patterns" / "msi_raw"
    for zf in msi_dir.glob("*.zip"):
        zf.unlink()

    pattern = library.load_pattern(source="local", pattern_id=pattern_id)
    assert pattern.gain_dbi.shape == (181, 360)
    assert pattern.max_gain_dbi == 8.0


def test_load_missing_zip_no_embedded_content(tmp_path: Path) -> None:
    """FileNotFoundError when zip is gone and index lacks embedded content."""
    import sqlite3

    # Create a minimal index WITHOUT msi_content column (old schema)
    db_dir = tmp_path / "antenna_patterns"
    db_dir.mkdir(parents=True)
    db_path = db_dir / "index.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE patterns (
            id TEXT PRIMARY KEY,
            manufacturer TEXT NOT NULL,
            model TEXT NOT NULL,
            frequency_mhz REAL,
            gain_dbi REAL,
            tilt_deg REAL,
            source_zip TEXT NOT NULL,
            source_path TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO patterns VALUES (?,?,?,?,?,?,?,?)",
        (
            "TestMfg/900MHz/Model_A.MSI",
            "TestMfg",
            "Model_A",
            900.0,
            8.0,
            0.0,
            "TestMfg.zip",
            "TestMfg/900MHz/Model_A.MSI",
        ),
    )
    conn.commit()
    conn.close()

    lib = AntennaPatternLibrary(data_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError, match="not available"):
        lib.load_pattern(source="local", pattern_id="TestMfg/900MHz/Model_A.MSI")
