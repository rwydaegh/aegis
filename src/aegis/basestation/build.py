"""Build CLI for base station data pipeline: extract, merge, validate, report."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

from aegis.basestation.merge import estimate_with_provenance, merge_sources
from aegis.basestation.parquet_io import write_merged_parquet, write_raw_parquet

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "data/basestations/regions.yaml"


def _load_config(path: str = DEFAULT_CONFIG) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _extract_basestationlib(source: dict, region_name: str, force: bool = False) -> pd.DataFrame | None:
    outdir = Path("data/basestations/raw")
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{region_name}_gov.parquet"
    if outfile.exists() and not force:
        logger.info("Raw file %s exists, skipping (use --force to re-extract)", outfile)
        return pd.read_parquet(str(outfile))
    try:
        from basestationLib import get_basestation_instance
    except ImportError:
        logger.error("basestationLib not installed. pip install -e basestations/")
        return None
    country = source.get("country", "Belgium")
    region = source.get("region", "")
    kwargs = {"region_city": region} if region else {}
    BSClass = get_basestation_instance(country, **kwargs)
    init_kw: dict = {"output_folder": f"/tmp/aegis_build/{region_name}/"}
    bbox = source.get("bbox")
    if bbox:
        init_kw["bounding_box"] = bbox
    instance = BSClass(**init_kw)
    config = {
        "computation": {
            "max_workers": 4,
            "estimations": {"estimate_missing_data_based_on_existing": False},
        }
    }
    df = instance.extract_antennas(config=config)
    if df is None or len(df) == 0:
        logger.warning("No antennas extracted for %s", region_name)
        return None
    write_raw_parquet(df, str(outfile))
    return df


def _extract_region(region_name: str, region_cfg: dict, force: bool = False) -> None:
    for source in region_cfg.get("sources", []):
        src_type = source.get("type", "")
        if src_type == "basestationlib":
            _extract_basestationlib(source, region_name, force=force)
        elif src_type == "mastedatabasen":
            logger.info("Denmark adapter not yet available, skipping mastedatabasen extraction")
        elif src_type == "opencellid":
            logger.info("OpenCellID extraction not yet implemented, skipping")
        else:
            logger.warning("Unknown source type: %s", src_type)


def _merge_region(region_name: str, region_cfg: dict) -> None:
    raw_dir = Path("data/basestations/raw")
    merged_dir = Path("data/basestations/merged")
    merged_dir.mkdir(parents=True, exist_ok=True)
    sources_data = []
    source_tag = "gov"
    for source in region_cfg.get("sources", []):
        src_type = source.get("type", "")
        priority = source.get("priority", 5)
        if src_type == "basestationlib":
            raw_file = raw_dir / f"{region_name}_gov.parquet"
            source_tag = f"gov:{source.get('region', region_name)}"
        elif src_type == "mastedatabasen":
            raw_file = raw_dir / f"{region_name}_mastedatabasen.parquet"
            source_tag = "gov:mastedatabasen"
        elif src_type == "opencellid":
            raw_file = raw_dir / f"{region_name}_opencellid.parquet"
            source_tag = "ocid"
        else:
            continue
        if not raw_file.exists():
            logger.warning("Raw file %s not found, skipping", raw_file)
            continue
        df = pd.read_parquet(str(raw_file))
        sources_data.append((df, source_tag, priority))
    if not sources_data:
        logger.warning("No raw data for region %s", region_name)
        return
    if len(sources_data) == 1:
        merged_df = sources_data[0][0].copy()
        source_tag = sources_data[0][1]
        from aegis.basestation.parquet_io import _PROVENANCE_COLUMNS

        for col in _PROVENANCE_COLUMNS:
            src_col = f"{col}_source"
            if src_col not in merged_df.columns and col in merged_df.columns:
                merged_df[src_col] = merged_df[col].apply(lambda v, st=source_tag: "missing" if pd.isna(v) else st)
        if "Pattern_source" not in merged_df.columns:
            merged_df["Pattern_source"] = ""
    else:
        merged_df = merge_sources(sources_data)
    ref_path = region_cfg.get("reference")
    ref_df = None
    if ref_path and os.path.exists(ref_path):
        ref_df = pd.read_parquet(ref_path)
    merged_df = estimate_with_provenance(merged_df, reference_df=ref_df)
    out = merged_dir / f"{region_name}.parquet"
    write_merged_parquet(merged_df, str(out), source_tag="merged")
    logger.info("Merged %d antennas -> %s", len(merged_df), out)


def _validate_region(region_name: str) -> bool:
    merged_file = Path(f"data/basestations/merged/{region_name}.parquet")
    if not merged_file.exists():
        print(f"  {region_name}: no merged file found")
        return False
    df = pd.read_parquet(str(merged_file))
    issues = []
    if "Power" in df.columns:
        bad = df[(df["Power"].notna()) & ((df["Power"] < 0) | (df["Power"] > 80))]
        if len(bad) > 0:
            issues.append(f"{len(bad)} rows with Power outside 0-80 dBm")
    if "Azimuth" in df.columns:
        bad = df[(df["Azimuth"].notna()) & ((df["Azimuth"] < 0) | (df["Azimuth"] >= 360))]
        if len(bad) > 0:
            issues.append(f"{len(bad)} rows with Azimuth outside 0-360")
    if issues:
        print(f"  {region_name}: {len(df)} rows, ISSUES: {'; '.join(issues)}")
        return False
    print(f"  {region_name}: {len(df)} rows, OK")
    return True


def _report(config: dict) -> None:
    merged_dir = Path("data/basestations/merged")
    cols = [
        "CenterHeight",
        "Power",
        "Frequency",
        "FrequencyBand",
        "Electrical_Tilt",
        "Mechanical_Tilt",
        "Azimuth",
        "Gain",
        "Horizontal_Beamwidth",
        "Vertical_Beamwidth",
    ]
    print(f"\n{'Region':<15} {'Rows':>6}  " + "  ".join(f"{c[:8]:>8}" for c in cols))
    print("-" * (15 + 8 + len(cols) * 10))
    for name in sorted(config.get("regions", {})):
        f = merged_dir / f"{name}.parquet"
        if not f.exists():
            print(f"{name:<15} {'N/A':>6}")
            continue
        df = pd.read_parquet(str(f))
        n = len(df)
        pcts = []
        for col in cols:
            if col in df.columns:
                pct = df[col].notna().sum() / n * 100 if n > 0 else 0
                pcts.append(f"{pct:7.0f}%")
            else:
                pcts.append(f"{'N/A':>8}")
        print(f"{name:<15} {n:>6}  " + "  ".join(pcts))
    print()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(prog="aegis.basestation.build", description="Base station data pipeline")
    sub = parser.add_subparsers(dest="command")
    p_extract = sub.add_parser("extract", help="Extract raw data from APIs")
    p_extract.add_argument("--region", required=True)
    p_extract.add_argument("--force", action="store_true")
    p_extract.add_argument("--config", default=DEFAULT_CONFIG)
    p_merge = sub.add_parser("merge", help="Merge and estimate")
    p_merge.add_argument("--region", required=True)
    p_merge.add_argument("--config", default=DEFAULT_CONFIG)
    p_validate = sub.add_parser("validate", help="Validate merged data")
    p_validate.add_argument("--region", required=True)
    p_report = sub.add_parser("report", help="Print coverage report")
    p_report.add_argument("--config", default=DEFAULT_CONFIG)
    p_all = sub.add_parser("all", help="Extract, merge, validate all regions")
    p_all.add_argument("--force", action="store_true")
    p_all.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if args.command in ("extract", "merge", "all"):
        cfg = _load_config(args.config)
    if args.command == "extract":
        regions = cfg.get("regions", {})
        if args.region not in regions:
            print(f"Unknown region: {args.region}. Available: {', '.join(sorted(regions))}")
            sys.exit(1)
        _extract_region(args.region, regions[args.region], force=args.force)
    elif args.command == "merge":
        regions = cfg.get("regions", {})
        if args.region not in regions:
            print(f"Unknown region: {args.region}. Available: {', '.join(sorted(regions))}")
            sys.exit(1)
        _merge_region(args.region, regions[args.region])
    elif args.command == "validate":
        _validate_region(args.region)
    elif args.command == "report":
        cfg = _load_config(args.config if hasattr(args, "config") else DEFAULT_CONFIG)
        _report(cfg)
    elif args.command == "all":
        regions = cfg.get("regions", {})
        for name, rcfg in sorted(regions.items()):
            print(f"\n=== {name} ===")
            _extract_region(name, rcfg, force=args.force)
            _merge_region(name, rcfg)
            _validate_region(name)
        _report(cfg)


if __name__ == "__main__":
    main()
