#!/usr/bin/env python3
"""Digitize band contributions from Supplementary Figures A6 to A10."""

from __future__ import annotations

import argparse
import csv
import statistics
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

BANDS_AND_COLORS = [
    ("Broadcast", (189, 189, 189)),
    ("DECT", (254, 196, 79)),
    ("WiFi 5 GHz", (158, 154, 200)),
    ("ISM/WiFi 2.4 GHz", (117, 107, 177)),
    ("Mobile UL 700 MHz", (8, 48, 107)),
    ("Mobile UL 800 MHz", (8, 81, 156)),
    ("Mobile UL 900 MHz", (33, 113, 181)),
    ("Mobile UL 1.8 GHz", (66, 146, 198)),
    ("Mobile UL 2.1 GHz", (107, 174, 214)),
    ("Mobile UL 2.6 GHz", (158, 202, 225)),
    ("Mobile TDD 2.6 GHz", (247, 104, 161)),
    ("Mobile TDD 3.5 GHz", (221, 52, 151)),
    ("Mobile SDL 700 MHz", (0, 68, 27)),
    ("Mobile DL 700 MHz", (0, 109, 44)),
    ("Mobile DL 800 MHz", (35, 139, 69)),
    ("Mobile DL 900 MHz", (65, 174, 118)),
    ("Mobile DL 1.4 GHz", (102, 194, 164)),
    ("Mobile DL 1.8 GHz", (153, 216, 201)),
    ("Mobile DL 2.1 GHz", (204, 236, 230)),
    ("Mobile DL 2.6 GHz", (229, 245, 249)),
]

FIGURES = [
    ("A6", 6, 22, "LC", "Urban area, large city", 40.0),
    ("A7", 7, 23, "SC", "Urban area, secondary city", 40.0),
    ("A8", 8, 24, "RA1", "Rural area 1", 70.0),
    ("A9", 9, 25, "RA2", "Rural area 2", 70.0),
    ("A10", 10, 26, "RA3", "Rural area 3", 70.0),
]

COUNTRIES = [
    "Austria",
    "Belgium",
    "France",
    "Hungary",
    "Italy",
    "Netherlands",
    "Poland",
    "Spain",
    "Switzerland",
    "UK",
]

# First and last bar centers inferred from the repeated panel geometry. The
# rural user panels contain eight or nine countries depending on whether Spain
# had a successful measurement in that specific rural area.
X_CENTER_LIMITS = {
    ("NU", 10): (103.0, 591.5),
    ("DL", 9): (742.5, 1224.0),
    ("DL", 8): (747.5, 1219.5),
    ("UL", 9): (1379.0, 1860.0),
    ("UL", 8): (1383.5, 1855.5),
}

WHITE = (255, 255, 255)
Y_ZERO = 1013.5
Y_TOP_TICK = 140.5
Y_SCAN_START = 80
Y_SCAN_STOP = 1015
X_SAMPLE_OFFSETS = (-12, -6, 0, 6, 12)


def _squared_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def _pixel_class(rgb: tuple[int, int, int]) -> int | None:
    candidates = [color for _band, color in BANDS_AND_COLORS] + [WHITE]
    index = min(range(len(candidates)), key=lambda candidate: _squared_distance(rgb, candidates[candidate]))
    return index if index < len(BANDS_AND_COLORS) else None


def _load_table_a6(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {(row["country"], row["study_area"], row["scenario"]): row for row in rows}


def _load_successful_measurements(path: Path) -> dict[tuple[str, str, str], int]:
    totals: dict[tuple[str, str, str], int] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["country"], row["study_area"], row["scenario"])
            totals[key] = totals.get(key, 0) + int(row["successful_measurements"] or 0)
    return totals


def _bar_centers(scenario: str, count: int) -> list[float]:
    try:
        first, last = X_CENTER_LIMITS[(scenario, count)]
    except KeyError as error:
        raise ValueError(f"No panel calibration for {scenario} with {count} countries") from error
    if count == 1:
        return [(first + last) / 2.0]
    step = (last - first) / (count - 1)
    return [first + step * index for index in range(count)]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def digitize(source: Path, output: Path) -> tuple[int, int]:
    table_a6 = _load_table_a6(output / "table_a6_total_exposure_summary.csv")
    successful_measurements = _load_successful_measurements(output / "table_a2_microenvironment_counts.csv")
    band_rows: list[dict[str, object]] = []
    total_rows: list[dict[str, object]] = []

    with ZipFile(source) as archive:
        for figure, image_number, pdf_page, study_area, study_area_label, top_tick_value in FIGURES:
            image = Image.open(BytesIO(archive.read(f"word/media/image{image_number}.tiff"))).convert("RGB")
            if image.size != (2130, 1207):
                raise ValueError(f"Unexpected {figure} image dimensions: {image.size}")
            pixels_per_unit = (Y_ZERO - Y_TOP_TICK) / top_tick_value
            pixel_resolution = 1.0 / pixels_per_unit

            for scenario in ("NU", "DL", "UL"):
                available_countries = [
                    country
                    for country in COUNTRIES
                    if successful_measurements.get((country, study_area, scenario), 0) > 0
                ]
                center_by_country = dict(
                    zip(available_countries, _bar_centers(scenario, len(available_countries)), strict=True)
                )
                for country in COUNTRIES:
                    table_area = study_area if study_area in {"LC", "SC"} else "RA"
                    table_row = table_a6[(country, table_area, scenario)]
                    successful_count = successful_measurements.get((country, study_area, scenario), 0)
                    available = successful_count > 0
                    sample_counts: list[list[int]] = []

                    if available:
                        center = center_by_country[country]
                        for offset in X_SAMPLE_OFFSETS:
                            x = round(center + offset)
                            counts = [0] * len(BANDS_AND_COLORS)
                            for y in range(Y_SCAN_START, Y_SCAN_STOP):
                                band_index = _pixel_class(image.getpixel((x, y)))
                                if band_index is not None:
                                    counts[band_index] += 1
                            sample_counts.append(counts)
                        median_pixels = [
                            float(statistics.median(sample[index] for sample in sample_counts))
                            for index in range(len(BANDS_AND_COLORS))
                        ]
                    else:
                        median_pixels = []

                    estimates = [count / pixels_per_unit for count in median_pixels]
                    total_estimate = sum(estimates) if available else None
                    reported_total = (
                        float(table_row["mean_mw_m2"])
                        if study_area in {"LC", "SC"} and table_row["mean_mw_m2"]
                        else None
                    )
                    difference = (
                        total_estimate - reported_total
                        if total_estimate is not None and reported_total is not None
                        else None
                    )
                    total_rows.append(
                        {
                            "figure": figure,
                            "pdf_page": pdf_page,
                            "study_area": study_area,
                            "study_area_label": study_area_label,
                            "country": country,
                            "scenario": scenario,
                            "available": str(available).lower(),
                            "successful_microenvironment_measurements": successful_count,
                            "availability_note": "" if available else "No successful measurements in Table A2",
                            "digitized_total_mw_m2": "" if total_estimate is None else f"{total_estimate:.6f}",
                            "reported_table_a6_total_mw_m2": "" if reported_total is None else f"{reported_total:.6f}",
                            "digitized_minus_reported_mw_m2": "" if difference is None else f"{difference:.6f}",
                            "pixel_resolution_mw_m2": f"{pixel_resolution:.6f}",
                        }
                    )

                    for index, (band, color) in enumerate(BANDS_AND_COLORS):
                        estimate = estimates[index] if available else None
                        pixel_count = median_pixels[index] if available else None
                        across_x = [sample[index] / pixels_per_unit for sample in sample_counts]
                        spread = max(across_x) - min(across_x) if across_x else None
                        band_rows.append(
                            {
                                "figure": figure,
                                "pdf_page": pdf_page,
                                "study_area": study_area,
                                "study_area_label": study_area_label,
                                "country": country,
                                "scenario": scenario,
                                "band": band,
                                "rgb": "-".join(str(channel) for channel in color),
                                "available": str(available).lower(),
                                "successful_microenvironment_measurements": successful_count,
                                "digitized_mean_mw_m2": "" if estimate is None else f"{estimate:.6f}",
                                "median_pixel_rows": "" if pixel_count is None else f"{pixel_count:.1f}",
                                "pixel_resolution_mw_m2": f"{pixel_resolution:.6f}",
                                "across_x_spread_mw_m2": "" if spread is None else f"{spread:.6f}",
                                "resolved_from_raster": str(bool(pixel_count and pixel_count > 0)).lower(),
                            }
                        )

    band_fields = [
        "figure",
        "pdf_page",
        "study_area",
        "study_area_label",
        "country",
        "scenario",
        "band",
        "rgb",
        "available",
        "successful_microenvironment_measurements",
        "digitized_mean_mw_m2",
        "median_pixel_rows",
        "pixel_resolution_mw_m2",
        "across_x_spread_mw_m2",
        "resolved_from_raster",
    ]
    total_fields = [
        "figure",
        "pdf_page",
        "study_area",
        "study_area_label",
        "country",
        "scenario",
        "available",
        "successful_microenvironment_measurements",
        "availability_note",
        "digitized_total_mw_m2",
        "reported_table_a6_total_mw_m2",
        "digitized_minus_reported_mw_m2",
        "pixel_resolution_mw_m2",
    ]
    _write_csv(output / "figures_a6_a10_band_means_digitized.csv", band_fields, band_rows)
    _write_csv(output / "figures_a6_a10_bar_totals_validation.csv", total_fields, total_rows)
    return len(band_rows), len(total_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    bands, totals = digitize(args.source, args.output)
    print(f"Digitized {bands} band estimates and {totals} bar totals")


if __name__ == "__main__":
    main()
