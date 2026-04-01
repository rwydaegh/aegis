# CommScope BSAPatternsWeb pattern source spec

## Source
- **Name:** CommScope BSAPatternsWeb
- **URL:** https://www.commscope.com/BSAPatternsWeb/DownloadPatterns.aspx
- **Type:** HTTP download per antenna model
- **Auth:** None (no login required)
- **License:** Free for engineering use; redistribution terms unclear, do not bundle in repo

## What it provides

CommScope (formerly Andrew Solutions and Kathrein) publishes measured antenna radiation patterns for their full catalog. Patterns are available for all CommScope, Andrew, Kathrein, and RFSOLUTIONS antenna models.

Supported export formats: MSI Planet, ADF (NSMA TIA/EIA-804-B), MSI Pro, CSV horizontal, CSV vertical, NSI/BTS, Xyzt, KML, MMANA-GAL, EZNEC, 4NEC2, and ~15 more (25 formats total).

For AEGIS, prefer ADF for the richest metadata, or MSI when compatibility with third-party tools is needed.

## Download method

Direct download by model number:

```
GET https://www.commscope.com/BSAPatternsWeb/DownloadPatterns.aspx
    ?model=742215
    &format=MSI
```

Where `model` is the CommScope/Kathrein part number (e.g., `742215`, `800-10695`, `DBXAH6565A`).

To discover available models programmatically, scrape the search page:

```
GET https://www.commscope.com/BSAPatternsWeb/SearchPatterns.aspx
    ?search=800-10695
```

The search returns an HTML table with model number, description, frequency, and available formats. Parse with `BeautifulSoup`.

Batch download workflow:
1. Collect antenna model numbers from government databases (Brussels, Flanders, ACMA).
2. Query BSAPatternsWeb for each model number.
3. Parse and cache the returned pattern file.
4. Fall back to `wireless-planning.com` or 3GPP synthetic if not found.

## File format: MSI

MSI is the most portable format. Structure:

```
NAME  742215
MAKE  Kathrein
FREQUENCY  2600.0
GAIN  18.0 dBi
H_WIDTH  65.0
V_WIDTH  7.0
FRONT_TO_BACK  30.0
TILT  ELECTRICAL
ELECTRICAL_TILT  4.0

HORIZONTAL 360
0.00   0.00
1.00   0.04
...
359.00  0.04

VERTICAL 360
0.00   0.00
1.00   0.20
...
359.00  0.20
```

Values are relative attenuation in dB (0.00 = boresight, positive = attenuation). Two 2D cuts (horizontal and vertical) at 1-degree resolution.

## File format: ADF

ADF (NSMA TIA/EIA-804-B) is more rigorous than MSI. Supports multiple frequency bands per file, multiple pattern cuts, and stores actual gain values (not relative loss). Extension is `.adf`. CommScope exports valid ADF; validate with the CloudRF ADF validator at `cloudrf.com/tools/validator`.

Prefer ADF when the antenna has multi-band patterns (e.g., 800 + 1800 + 2600 MHz in one file).

## Gotchas
- The `GAIN` header in MSI can be in dBd (relative to a dipole) or dBi (relative to isotropic). CommScope uses dBi consistently, but third-party MSI files from other sources sometimes use dBd. Converting: `dBi = dBd + 2.15`.
- CommScope-exported MSI files sometimes have trailing whitespace on pattern lines that causes parser failures. Strip whitespace before parsing.
- The model number search is fuzzy: `742215` and `K742215` may both resolve to the same pattern. Normalise by stripping leading letters.
- BSAPatternsWeb does not have a public API or documented rate limits. Space requests to avoid triggering rate limiting (1 request per second is safe).
- The URL scheme has been stable since ~2010 but CommScope has migrated domains before. Monitor for redirects.
- Patterns represent the antenna alone, not the complete installation. Mounting effects (rooftop diffraction, nearby structures) are not captured.

## Coverage
CommScope holds roughly 30-40% of the global macro base station antenna market. For antennas not in their catalog, use `wireless-planning.com` (which covers 50+ manufacturers) or fall back to 3GPP TR 38.901 synthetic patterns.

## Integration with basestationLib

```python
from basestations.patterns import fetch_commscope_msi

pattern = fetch_commscope_msi("742215")  # returns dict with H/V arrays + metadata
```

Cache patterns at `~/.cache/aegis/patterns/commscope/<model>.msi`. Patterns do not change; indefinite cache is safe.

## Status
No existing integration. Needs a `patterns` module in `basestationLib`.
