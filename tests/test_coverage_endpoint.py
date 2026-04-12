"""Tests for the coverage endpoint tier computation."""

import base64
import struct
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("flask")


def _make_test_parquet(tmp_path: Path, region: str, n: int = 100) -> Path:
    """Create a minimal merged parquet with n antennas."""
    merged_dir = tmp_path / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "SiteCode": [f"SITE({i})" for i in range(n)],
            "Operator": rng.choice(["OpA", "OpB"], n),
            "Technology": rng.choice(["LTE", "5G"], n),
            "Latitude": rng.uniform(50.0, 51.0, n),
            "Longitude": rng.uniform(3.0, 4.0, n),
            "Power": rng.choice([30.0, np.nan], n),
            "Azimuth": rng.choice([90.0, np.nan], n),
            "CenterHeight": rng.choice([25.0, np.nan], n),
            "Frequency": rng.choice([1800.0, np.nan], n),
            "Gain": rng.choice([18.0, np.nan], n),
        }
    )
    out = merged_dir / f"{region}.parquet"
    df.to_parquet(str(out))
    return out


def _make_test_regions_yaml(tmp_path: Path, regions: dict) -> Path:
    """Create a test regions.yaml."""
    import yaml

    yaml_path = tmp_path / "regions.yaml"
    yaml_path.write_text(yaml.dump({"regions": regions}))
    return yaml_path


def test_compute_regions_from_parquet(tmp_path):
    """Tier 1: region summaries are computed correctly from parquet data."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "testregion", n=50)
    regions_cfg = {"testregion": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(
        merged_dir=tmp_path / "merged",
        regions_yaml=yaml_path,
    )

    assert len(result["regions"]) == 1
    r = result["regions"][0]
    assert r["name"] == "testregion"
    assert r["count"] == 50
    assert r["bbox"] == [3.0, 4.0, 50.0, 51.0]
    assert 0.0 <= r["completeness"] <= 1.0


def test_compute_regions_bbox_from_data(tmp_path):
    """Regions without bbox in yaml get bbox computed from data."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "nobbox", n=20)
    regions_cfg = {"nobbox": {"sources": [{"type": "basestationlib"}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(
        merged_dir=tmp_path / "merged",
        regions_yaml=yaml_path,
    )

    r = result["regions"][0]
    assert r["bbox"] is not None
    assert len(r["bbox"]) == 4
    min_lon, max_lon, min_lat, max_lat = r["bbox"]
    assert min_lon < 4.0
    assert max_lon > 3.0


def test_compute_sites_binary_large(tmp_path):
    """Sites are encoded as base64 binary with 12-byte records (200 unique sites)."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "clustered", n=200)
    regions_cfg = {"clustered": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    meta = result["sites_meta"]
    raw = base64.b64decode(result["sites_b64"])

    assert meta["count"] > 0
    assert meta["count"] <= 200
    # 12 bytes per record: lat(f4) + lon(f4) + op(u1) + tech(u1) + region(u1) + count(u1)
    assert len(raw) == meta["count"] * 12


def test_compute_sites_binary(tmp_path):
    """Sites are encoded as base64 binary with correct 12-byte record format."""
    from aegis.viewer.routes.coverage import _compute_coverage

    _make_test_parquet(tmp_path, "binary", n=30)
    regions_cfg = {"binary": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    meta = result["sites_meta"]
    raw = base64.b64decode(result["sites_b64"])

    assert meta["count"] > 0
    assert len(raw) == meta["count"] * 12  # 12 bytes per record
    assert len(meta["operators"]) > 0
    assert len(meta["technologies"]) > 0

    # Parse first record: lat(f4) + lon(f4) + op(u1) + tech(u1) + region(u1) + count(u1)
    lat, lon = struct.unpack_from("<ff", raw, 0)
    op_idx = raw[8]
    tech_idx = raw[9]
    region_idx = raw[10]
    count = raw[11]
    assert 49.0 < lat < 52.0
    assert 2.0 < lon < 5.0
    assert op_idx < len(meta["operators"])
    assert tech_idx < len(meta["technologies"])
    assert region_idx < len(meta["region_names"])
    assert count >= 1


def test_empty_merged_dir(tmp_path):
    """Empty merged dir returns empty response, not error."""
    from aegis.viewer.routes.coverage import _compute_coverage

    (tmp_path / "merged").mkdir()
    regions_cfg = {"missing": {"sources": [{"bbox": [0, 1, 0, 1]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(tmp_path / "merged", yaml_path)
    assert result["regions"] == []
    assert result["sites_meta"]["count"] == 0
    assert result["sites_b64"] == ""


def test_parquet_missing_operator_technology_columns(tmp_path):
    """Parquet without Operator/Technology columns should not crash."""
    from aegis.viewer.routes.coverage import _compute_coverage

    merged_dir = tmp_path / "merged"
    merged_dir.mkdir(parents=True)
    rng = np.random.default_rng(99)
    n = 20
    df = pd.DataFrame(
        {
            "SiteCode": [f"S{i}" for i in range(n)],
            "Latitude": rng.uniform(50.0, 51.0, n),
            "Longitude": rng.uniform(3.0, 4.0, n),
        }
    )
    (merged_dir / "minimal.parquet").parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(str(merged_dir / "minimal.parquet"))

    regions_cfg = {"minimal": {"sources": [{"bbox": [3.0, 4.0, 50.0, 51.0]}]}}
    yaml_path = _make_test_regions_yaml(tmp_path, regions_cfg)

    result = _compute_coverage(merged_dir, yaml_path)

    assert len(result["regions"]) == 1
    assert result["regions"][0]["count"] == n
    meta = result["sites_meta"]
    assert meta["count"] > 0
    # Missing columns should be filled with "Unknown"
    assert "Unknown" in meta["operators"]
    assert "Unknown" in meta["technologies"]
