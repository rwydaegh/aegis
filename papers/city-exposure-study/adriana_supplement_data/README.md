# Adriana paper supplement data

This directory contains structured values extracted from
`1-s2.0-S0160412025002910-mmc1.docx`, the supplementary information for the
GOLIAT European microenvironment measurement paper.

## Provenance classes

Files beginning with `table_` are exact transcriptions of native Word tables.
They are not estimates digitized from plots. `SOURCE_SHA256.txt` identifies the
precise DOCX used for extraction.

Files beginning with `figures_` contain raster-derived estimates. They identify
the source figure and PDF page, the RGB legend class, the pixel calibration,
and the variation across five horizontal samples through each bar. A reported
zero means that the segment was not resolved at the raster resolution. It does
not prove that the underlying value was exactly zero.

## Files

- `table_a1_study_areas.csv` contains the five study-area locations for each
  country.

- `table_a2_microenvironment_counts.csv` contains one row per study area,
  microenvironment, country, and usage scenario. Failure codes are preserved.

- `table_a3_frequency_bands.csv` contains the 35 ExpoM-RF 4 measurement bands.

- `table_a4_device_specifications.csv` contains the reported probe settings.

- `table_a5_crosstalk_correction.csv` contains the country-specific crosstalk
  corrections for six band pairs.

- `table_a6_total_exposure_summary.csv` contains total RF-EMF summary statistics
  by country, study area, and usage scenario.

- `table_a7_band_exposure_summary.csv` contains band-specific summary statistics
  by country and usage scenario.

- `figures_a6_a10_band_means_digitized.csv` contains estimated frequency-band
  contributions for each country, scenario, and individual study area.

- `figures_a6_a10_bar_totals_validation.csv` contains the digitized bar totals.
  Large-city and secondary-city totals are compared with the exact values in
  Table A6. Rural figures cannot be compared directly because Table A6 combines
  the three rural areas.

## Reproduction

Run:

```bash
python3 extract_adriana_supplement.py \
  1-s2.0-S0160412025002910-mmc1.docx \
  adriana_supplement_data
```

The extractor uses only the Python standard library and does not modify the
Python environment.

Digitize Figures A6 to A10 with the shared image environment:

```bash
uv run --project /home/user/tools/devpc-python \
  python digitize_adriana_stacked_bars.py \
  1-s2.0-S0160412025002910-mmc1.docx \
  adriana_supplement_data
```
