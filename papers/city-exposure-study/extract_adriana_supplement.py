#!/usr/bin/env python3
"""Extract structured tables from the GOLIAT supplementary DOCX file."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NS}
W = f"{{{WORD_NS}}}"


def _cell_text(cell: ET.Element) -> str:
    paragraphs = []
    for paragraph in cell.findall(".//w:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).strip()
        if text:
            paragraphs.append(text)
    return " ".join(paragraphs)


def _expanded_table(table: ET.Element) -> list[list[str]]:
    """Expand Word grid spans and vertical merges into a rectangular grid."""
    grid_width = len(table.findall("./w:tblGrid/w:gridCol", NS))
    active_vertical: list[str | None] = [None] * grid_width
    rows: list[list[str]] = []

    for row in table.findall("./w:tr", NS):
        output = [""] * grid_width
        row_properties = row.find("./w:trPr", NS)
        grid_before = row_properties.find("./w:gridBefore", NS) if row_properties is not None else None
        column = int(grid_before.attrib.get(W + "val", "0")) if grid_before is not None else 0

        for cell in row.findall("./w:tc", NS):
            properties = cell.find("./w:tcPr", NS)
            span_node = properties.find("./w:gridSpan", NS) if properties is not None else None
            span = int(span_node.attrib.get(W + "val", "1")) if span_node is not None else 1
            merge_node = properties.find("./w:vMerge", NS) if properties is not None else None
            merge_value = merge_node.attrib.get(W + "val", "continue") if merge_node is not None else None
            text = _cell_text(cell)

            if merge_value == "continue":
                values = [active_vertical[index] or text for index in range(column, column + span)]
            else:
                values = [text] * span

            for offset, value in enumerate(values):
                index = column + offset
                output[index] = value
                if merge_value == "restart":
                    active_vertical[index] = text
                elif merge_value is None:
                    active_vertical[index] = None
            column += span

        rows.append(output)

    return rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _is_unavailable(value: str) -> bool:
    normalized = value.strip().upper()
    return normalized.startswith("NA") or normalized == "FAILED MEASUREMENTS"


def _clean_na(value: str) -> str:
    return "" if _is_unavailable(value) else value.strip()


def _split_median_iqr(value: str) -> tuple[str, str, str]:
    clean = _clean_na(value).replace(" ", "")
    if not clean:
        return "", "", ""
    match = re.fullmatch(r"([^()]+)\(([^-]+)-([^)]+)\)", clean)
    if match is None:
        raise ValueError(f"Could not parse median and IQR cell: {value!r}")
    return match.group(1), match.group(2), match.group(3)


def _extract_a1(table: list[list[str]], output: Path) -> int:
    fields = ["country", "urban_large_city", "urban_secondary_city", "rural_area_1", "rural_area_2", "rural_area_3"]
    rows = [dict(zip(fields, row, strict=True)) for row in table[1:]]
    _write_csv(output / "table_a1_study_areas.csv", fields, rows)
    return len(rows)


def _extract_a2(table: list[list[str]], output: Path) -> int:
    rows = []
    countries = table[0]
    scenarios = table[1]
    for source_row in table[2:]:
        for column in range(2, len(source_row), 3):
            for offset in range(3):
                reported = source_row[column + offset].strip()
                count = reported if re.fullmatch(r"\d+", reported) else ""
                if count:
                    status = "ok"
                elif reported.upper().startswith("FT"):
                    status = "failed_low_throughput"
                elif reported.upper().startswith("F"):
                    status = "failed_phone_settings"
                else:
                    status = "not_reported"
                rows.append(
                    {
                        "study_area": source_row[0],
                        "microenvironment": source_row[1],
                        "country": countries[column],
                        "scenario": scenarios[column + offset],
                        "reported_result": reported,
                        "successful_measurements": count,
                        "status": status,
                    }
                )
    fields = [
        "study_area",
        "microenvironment",
        "country",
        "scenario",
        "reported_result",
        "successful_measurements",
        "status",
    ]
    _write_csv(output / "table_a2_microenvironment_counts.csv", fields, rows)
    return len(rows)


def _extract_a3(table: list[list[str]], output: Path) -> int:
    fields = ["band_name", "start_mhz", "stop_mhz", "center_mhz", "bandwidth_mhz", "kind"]
    rows = [dict(zip(fields, row, strict=True)) for row in table[1:]]
    _write_csv(output / "table_a3_frequency_bands.csv", fields, rows)
    return len(rows)


def _extract_a4(table: list[list[str]], output: Path) -> int:
    fields = ["specification", "value"]
    rows = [dict(zip(fields, row, strict=True)) for row in table[1:]]
    _write_csv(output / "table_a4_device_specifications.csv", fields, rows)
    return len(rows)


def _extract_a5(table: list[list[str]], output: Path) -> int:
    fields = [
        "frequency_1",
        "frequency_2",
        "correlation_threshold",
        "country",
        "identified_clusters",
        "corrected_samples_frequency_1",
        "corrected_samples_frequency_2",
        "mean_frequency_1_before",
        "mean_frequency_1_after",
        "mean_frequency_2_before",
        "mean_frequency_2_after",
    ]
    rows = [dict(zip(fields, row, strict=True)) for row in table[1:]]
    _write_csv(output / "table_a5_crosstalk_correction.csv", fields, rows)
    return len(rows)


def _extract_a6(table: list[list[str]], output: Path) -> int:
    scenario_columns = [("NU", 2), ("DL", 6), ("UL", 10)]
    rows = []
    for source_row in table[2:]:
        for scenario, column in scenario_columns:
            raw_count, raw_mean, raw_median_iqr, raw_p95 = source_row[column : column + 4]
            median, q1, q3 = _split_median_iqr(raw_median_iqr)
            rows.append(
                {
                    "country": source_row[0],
                    "study_area": source_row[1].rstrip("*"),
                    "scenario": scenario,
                    "sample_count": _clean_na(raw_count),
                    "mean_mw_m2": _clean_na(raw_mean),
                    "median_mw_m2": median,
                    "q1_mw_m2": q1,
                    "q3_mw_m2": q3,
                    "p95_mw_m2": _clean_na(raw_p95),
                    "reported_median_iqr": raw_median_iqr,
                    "availability_note": raw_count if _is_unavailable(raw_count) else "",
                    "available": "false" if _is_unavailable(raw_count) else "true",
                }
            )
    fields = [
        "country",
        "study_area",
        "scenario",
        "sample_count",
        "mean_mw_m2",
        "median_mw_m2",
        "q1_mw_m2",
        "q3_mw_m2",
        "p95_mw_m2",
        "reported_median_iqr",
        "availability_note",
        "available",
    ]
    _write_csv(output / "table_a6_total_exposure_summary.csv", fields, rows)
    return len(rows)


def _extract_a7(table: list[list[str]], output: Path) -> int:
    scenario_columns = [("NU", 2), ("DL", 5), ("UL", 8)]
    rows = []
    for source_row in table[2:]:
        for scenario, column in scenario_columns:
            raw_mean, raw_median, raw_iqr = source_row[column : column + 3]
            rows.append(
                {
                    "country": source_row[0],
                    "band": source_row[1],
                    "scenario": scenario,
                    "mean_mw_m2": _clean_na(raw_mean),
                    "median_mw_m2": _clean_na(raw_median),
                    "iqr_mw_m2": _clean_na(raw_iqr),
                    "availability_note": raw_mean if _is_unavailable(raw_mean) else "",
                    "available": "false" if _is_unavailable(raw_mean) else "true",
                }
            )
    fields = [
        "country",
        "band",
        "scenario",
        "mean_mw_m2",
        "median_mw_m2",
        "iqr_mw_m2",
        "availability_note",
        "available",
    ]
    _write_csv(output / "table_a7_band_exposure_summary.csv", fields, rows)
    return len(rows)


def extract(source: Path, output: Path) -> dict[str, int]:
    with ZipFile(source) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    tables = [_expanded_table(table) for table in document.findall(".//w:body/w:tbl", NS)]
    if len(tables) != 7:
        raise ValueError(f"Expected 7 supplement tables, found {len(tables)}")

    counts = {
        "A1": _extract_a1(tables[0], output),
        "A2": _extract_a2(tables[1], output),
        "A3": _extract_a3(tables[2], output),
        "A4": _extract_a4(tables[3], output),
        "A5": _extract_a5(tables[4], output),
        "A6": _extract_a6(tables[5], output),
        "A7": _extract_a7(tables[6], output),
    }
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    (output / "SOURCE_SHA256.txt").write_text(f"{digest}  {source.name}\n", encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    counts = extract(args.source, args.output)
    print("Extracted " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
