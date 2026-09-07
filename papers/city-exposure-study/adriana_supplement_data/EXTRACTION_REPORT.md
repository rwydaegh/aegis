# Supplement extraction report

## Sources

- `1-s2.0-S0160412025002910-mmc1.docx` supplies native Word tables and the
  original embedded raster figures.

- `1-s2.0-S0160412025002910-mmc1.pdf` supplies stable page references and a
  visual check of the rendered supplement.

The source DOCX hash is stored in `SOURCE_SHA256.txt`.

## Exact table extraction

Seven native tables produced 2,905 data rows:

| Table | Data rows | Contents |
|---|---:|---|
| A1 | 10 | Study-area locations |
| A2 | 2,100 | Microenvironment counts and failures |
| A3 | 35 | ExpoM-RF 4 frequency bands |
| A4 | 10 | Probe settings and specifications |
| A5 | 60 | Crosstalk corrections |
| A6 | 90 | Total exposure by country, area, and scenario |
| A7 | 600 | Band exposure by country and scenario |

These values come directly from Word table cells. They are not OCR output.

## Figure A6 to A10 digitization

Figures A6 to A10 report stacked frequency-band means for five individual study
areas. The Word document stores them as 2130 by 1207 pixel TIFF images. The
digitizer uses the 20 exact RGB fills in the figure legend and samples five
vertical cuts through each bar.

The output contains:

- 3,000 possible country-area-scenario-band cells

- 150 possible bar totals

- 135 bars with successful measurements according to Table A2

The urban panels have a one-pixel value resolution of 0.0458 mW/m2. The rural
panels have a one-pixel value resolution of 0.0802 mW/m2. All five horizontal
samples agreed for every extracted segment after the country slots were matched
to the availability data in Table A2.

## Validation against Table A6

The 56 measured large-city and secondary-city bars can be compared directly
with exact total means in Table A6.

| Diagnostic | Value |
|---|---:|
| Median absolute difference | 0.0163 mW/m2 |
| Mean absolute difference | 0.0277 mW/m2 |
| Urban pixel resolution | 0.0458 mW/m2 |
| Bars within two pixels | 54 of 56 |

Two Poland maximum-uplink bars disagree by much more than raster resolution:

| Figure | Study area | Digitized stack | Table A6 total | Difference |
|---|---|---:|---:|---:|
| A6 | Large city | 8.293 | 8.660 | -0.367 mW/m2 |
| A7 | Secondary city | 14.891 | 14.570 | +0.321 mW/m2 |

The bar edges are unambiguous. These discrepancies appear to be differences
between the plotted stacked-band data and the reported total series. They are
preserved rather than corrected.

## Largest digitized study-area totals

The largest bars in Figures A6 to A10 are:

| Study area | Country | Scenario | Digitized total |
|---|---|---|---:|
| Rural area 1 | Netherlands | Maximum UL | 68.56 mW/m2 |
| Rural area 2 | Italy | Maximum UL | 58.45 mW/m2 |
| Rural area 1 | Poland | Maximum DL | 45.78 mW/m2 |
| Rural area 1 | Switzerland | Maximum UL | 43.62 mW/m2 |
| Rural area 1 | France | Maximum UL | 37.21 mW/m2 |

These are figure-derived estimates, not exact tabulated values.

## Remaining figure-only information

- Figure A4 contains country random effects and confidence intervals. It is the
  cleanest next digitization target.

- Figures A2 and A3 contain microenvironment boxplots and overlaid study-area
  points. Extracting them would recover medians, quartiles, whiskers, and points
  at plot resolution.

- Figure A5 contains the largest interaction table, with total and band means
  by microenvironment. It is information-rich but dense enough that automated
  extraction needs stronger visual validation.

The underlying raw time series and exact microenvironment-level spectra are not
present in the supplement.
