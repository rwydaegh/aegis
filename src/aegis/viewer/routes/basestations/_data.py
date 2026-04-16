"""Data-source resolution and list handlers for base stations."""

from __future__ import annotations

import logging
import os
import threading

from flask import jsonify

from aegis.viewer.server import scoped_cache_get, scoped_cache_set

from ._fidelity import _bs_summary

logger = logging.getLogger(__name__)


def _list_available_regions(data_dir: str) -> list[str]:
    """Return region names that have Parquet or CSV data files."""
    regions: set[str] = set()
    merged_dir = os.path.join(data_dir, "basestations", "merged")
    if os.path.isdir(merged_dir):
        for f in os.listdir(merged_dir):
            if f.endswith(".parquet"):
                regions.add(f[:-8])
    bs_dir = os.path.join(data_dir, "basestations")
    if os.path.isdir(bs_dir):
        for f in os.listdir(bs_dir):
            if f.endswith(".csv"):
                regions.add(f[:-4])
    return sorted(regions)


def _resolve_data_paths(data_dir: str, region: str | None) -> tuple[str | None, str | None]:
    """Find Parquet or CSV paths for a region. Returns (parquet, csv)."""
    parquet_name = f"{region}.parquet" if region else "brussels.parquet"
    parquet_candidate = os.path.join(data_dir, "basestations", "merged", parquet_name)
    parquet_path = parquet_candidate if os.path.exists(parquet_candidate) else None

    csv_name = f"{region}.csv" if region else "brussels.csv"
    csv_path = None
    for candidate in (
        os.path.join(data_dir, "basestations", csv_name),
        f"data/basestations/{csv_name}",
    ):
        if os.path.exists(candidate):
            csv_path = candidate
            break
    return parquet_path, csv_path


def _load_via_parquet(path: str, bbox, params: dict):
    from aegis.basestation.adapter import load_basestations_from_parquet

    return load_basestations_from_parquet(
        path,
        bbox=bbox,
        operator=params.get("operator"),
        technology=params.get("technology"),
        frequency_band=params.get("frequency_band"),
    )


def _load_via_csv(path: str, bbox, params: dict):
    from aegis.basestation.adapter import load_basestations_from_csv

    return load_basestations_from_csv(
        path,
        bbox=bbox,
        operator=params.get("operator"),
        technology=params.get("technology"),
    )


def _load_via_api(country: str, region: str | None, bbox, params: dict):
    from aegis.basestation.adapter import load_basestations

    return load_basestations(
        country=country,
        region=region,
        bbox=bbox,
        operator=params.get("operator"),
        technology=params.get("technology"),
        max_workers=max(1, min(int(params.get("max_workers", 4)), 16)),
    )


def load_basestations_for_region(
    data_dir: str,
    region: str | None,
    country: str,
    bbox,
    params: dict,
):
    """Dispatch to Parquet/CSV/API based on availability. Returns basestations list."""
    parquet_path, csv_path = _resolve_data_paths(data_dir, region)
    if parquet_path:
        return _load_via_parquet(parquet_path, bbox, params)
    if csv_path:
        return _load_via_csv(csv_path, bbox, params)
    return _load_via_api(country, region, bbox, params)


def _handle_basestations_list(cache: dict, cache_lock: threading.RLock):
    """Implementation for GET /api/basestations/list."""
    with cache_lock:
        basestations = scoped_cache_get(cache, "basestations", [])

    return jsonify(
        {
            "count": len(basestations),
            "basestations": [_bs_summary(bs) for bs in basestations],
        }
    )


def _cache_origin(cache: dict, bbox, params: dict, basestations: list) -> None:
    """Derive and cache a scene origin from bbox / params / basestation centroid."""
    if bbox and len(bbox) == 4:
        scoped_cache_set(
            cache,
            "basestations_origin",
            ((bbox[2] + bbox[3]) / 2, (bbox[0] + bbox[1]) / 2),
        )
    elif "lat" in params and "lon" in params:
        scoped_cache_set(
            cache,
            "basestations_origin",
            (float(params["lat"]), float(params["lon"])),
        )
    elif basestations:
        avg_lat = sum(bs.latitude for bs in basestations) / len(basestations)
        avg_lon = sum(bs.longitude for bs in basestations) / len(basestations)
        scoped_cache_set(cache, "basestations_origin", (avg_lat, avg_lon))
    else:
        scoped_cache_set(cache, "basestations_origin", None)
