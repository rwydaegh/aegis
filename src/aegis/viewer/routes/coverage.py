"""Coverage endpoint: pre-computed global base station overview."""

from __future__ import annotations

import base64
import logging
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

_COMPLETENESS_COLS = ["Power", "Azimuth", "CenterHeight", "Frequency", "Gain"]


def _compute_coverage(
    merged_dir: Path,
    regions_yaml: Path,
) -> dict:
    """Build the three-tier coverage response from parquet files."""
    with open(regions_yaml) as f:
        cfg = yaml.safe_load(f)

    regions_cfg = cfg.get("regions", {})
    all_dfs: list[pd.DataFrame] = []
    regions_out: list[dict] = []

    region_names: list[str] = []

    for name, rcfg in sorted(regions_cfg.items()):
        pq = merged_dir / f"{name}.parquet"
        if not pq.exists():
            continue
        # Only load columns we need (avoids OOM on small servers with 5M+ rows)
        _NEEDED = [
            "SiteCode",
            "Latitude",
            "Longitude",
            "Operator",
            "Technology",
            *_COMPLETENESS_COLS,
        ]
        try:
            schema_cols = set(pd.read_parquet(str(pq), nrows=0).columns)
            use_cols = [c for c in _NEEDED if c in schema_cols]
            df = pd.read_parquet(str(pq), columns=use_cols)
        except Exception:
            logger.warning("Corrupt parquet %s, skipping", pq)
            continue

        # Bbox: read from first source, or compute from data
        bbox = None
        for src in rcfg.get("sources", []):
            if "bbox" in src:
                bbox = src["bbox"]
                break
        if bbox is None and "Latitude" in df.columns and "Longitude" in df.columns:
            pad = 0.01
            bbox = [
                float(df["Longitude"].min() - pad),
                float(df["Longitude"].max() + pad),
                float(df["Latitude"].min() - pad),
                float(df["Latitude"].max() + pad),
            ]

        # Completeness: fraction of non-null values in key columns
        present_cols = [c for c in _COMPLETENESS_COLS if c in df.columns]
        completeness = float(df[present_cols].notna().mean().mean()) if present_cols else 0.0

        label = name.replace("_", " ").title()
        region_idx = len(region_names)
        region_names.append(name)
        regions_out.append(
            {
                "name": name,
                "label": label,
                "bbox": bbox,
                "count": len(df),
                "completeness": round(completeness, 2),
            }
        )
        df = df.copy()
        df["_region_idx"] = region_idx
        all_dfs.append(df)

    if not all_dfs:
        return {
            "regions": [],
            "sites_meta": {"count": 0, "operators": [], "technologies": [], "region_names": []},
            "sites_b64": "",
        }

    combined = pd.concat(all_dfs, ignore_index=True)

    # Guard missing Operator/Technology columns
    if "Operator" not in combined.columns:
        combined["Operator"] = "Unknown"
    if "Technology" not in combined.columns:
        combined["Technology"] = "Unknown"

    # Compute per-site antenna count before deduplication
    if "SiteCode" in combined.columns:
        antenna_counts = combined.groupby("SiteCode").size().rename("_antenna_count")
        combined = combined.join(antenna_counts, on="SiteCode")
        sites = combined.drop_duplicates(subset="SiteCode", keep="first").copy()
    else:
        antenna_counts = combined.groupby(["Latitude", "Longitude"]).size().rename("_antenna_count")
        combined = combined.join(antenna_counts, on=["Latitude", "Longitude"])
        sites = combined.drop_duplicates(subset=["Latitude", "Longitude"], keep="first").copy()

    op_col = sites["Operator"].fillna("Unknown").astype(str)
    tech_col = sites["Technology"].fillna("Unknown").astype(str)
    operators = sorted(op_col.unique().tolist())
    technologies = sorted(tech_col.unique().tolist())
    op_map = {o: i for i, o in enumerate(operators)}
    tech_map = {t: i for i, t in enumerate(technologies)}

    # Pack binary: lat(f4) + lon(f4) + op(u1) + tech(u1) + region(u1) + count(u1) = 12 bytes
    lats = sites["Latitude"].to_numpy(dtype=np.float32)
    lons = sites["Longitude"].to_numpy(dtype=np.float32)
    op_indices = op_col.map(op_map).fillna(0).to_numpy(dtype=np.uint8)
    tech_indices = tech_col.map(tech_map).fillna(0).to_numpy(dtype=np.uint8)
    region_indices = sites["_region_idx"].fillna(0).clip(upper=255).to_numpy(dtype=np.uint8)
    counts = sites["_antenna_count"].fillna(1).clip(upper=255).to_numpy(dtype=np.uint8)

    record = np.empty(
        len(sites),
        dtype=np.dtype(
            [("lat", "<f4"), ("lon", "<f4"), ("op", "u1"), ("tech", "u1"), ("region", "u1"), ("count", "u1")]
        ),
    )
    record["lat"] = lats
    record["lon"] = lons
    record["op"] = op_indices
    record["tech"] = tech_indices
    record["region"] = region_indices
    record["count"] = counts
    buf = record.tobytes()

    return {
        "regions": regions_out,
        "sites_meta": {
            "count": len(sites),
            "operators": operators,
            "technologies": technologies,
            "region_names": region_names,
        },
        "sites_b64": base64.b64encode(buf).decode("ascii"),
    }


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register coverage routes."""

    @app.route("/api/basestations/coverage")
    def api_coverage():
        with cache_lock:
            if "coverage_response" in cache:
                return jsonify(cache["coverage_response"])
            data_dir = cache.get("data_dir", "data")

        merged_dir = Path(data_dir) / "basestations" / "merged"
        regions_yaml = Path(data_dir) / "basestations" / "regions.yaml"

        if not regions_yaml.exists():
            return jsonify({"error": "regions.yaml not found"}), 500

        try:
            result = _compute_coverage(merged_dir, regions_yaml)
        except Exception:
            logger.exception("Failed to compute coverage")
            return jsonify({"error": "Failed to compute coverage data"}), 500

        with cache_lock:
            # Another thread may have computed it while we were working
            if "coverage_response" not in cache:
                cache["coverage_response"] = result

        return jsonify(result)
