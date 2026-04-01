# wireless-planning.com MSI library spec

## Source
- **Name:** wireless-planning.com MSI antenna pattern file library
- **URL:** https://www.wireless-planning.com/msi-antenna-pattern-file-library
- **Type:** Direct file downloads (HTTP)
- **Auth:** None (free, no login required)
- **License:** Free for engineering use; no explicit open license stated

## What it provides

The largest freely accessible collection of MSI antenna pattern files: approximately 400,000 files from 50+ manufacturers. Covers Kathrein, Huawei, Ericsson, Nokia, ZTE, Andrew/CommScope, Amphenol, Ubiquiti, and many regional manufacturers. Updated periodically as manufacturers publish new models.

This is the broadest single source for measured pattern data. CommScope BSAPatternsWeb has better quality for CommScope-specific models, but wireless-planning.com covers a wider manufacturer range.

## MSI file format

MSI (Mobile Systems International) is the de facto industry standard for 2D antenna patterns. Used by Planet, Atoll, NetAct, and CloudRF.

Structure:

```
NAME  Kathrein 742215
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

Key properties:
- Values are relative attenuation in dB. 0.00 = boresight (peak gain direction). Positive = loss.
- Standard: 360 points per cut, 1-degree resolution.
- Two 2D cuts: horizontal (azimuthal) and vertical (elevation).
- `H_WIDTH` and `V_WIDTH` are the 3 dB beamwidths in degrees.
- `FRONT_TO_BACK` is the front-to-back ratio in dB.

Converting from 2D cuts to 3D sphere requires interpolation. The simplest approach is multiplicative combination: `A_3D(theta, phi) = A_H(phi) + A_V(theta)`, clamped at the front-to-back ratio. This is an approximation; Brussels 181x360 matrices are more accurate when available.

## Extraction method

The library is organised by manufacturer. Each manufacturer has a directory listing of `.msi` files:

```
GET https://www.wireless-planning.com/msi-files/Kathrein/742215.msi
```

To build a local cache:
1. Scrape the manufacturer index page for the full file list.
2. Download each `.msi` file.
3. Parse and index by `NAME`, `MAKE`, `FREQUENCY`, and `GAIN`.

A full mirror of 400K files is roughly 2-4 GB uncompressed. For AEGIS, only cache files for models that appear in the active government databases.

```python
import requests
from bs4 import BeautifulSoup

def list_manufacturer_files(manufacturer):
    url = f"https://www.wireless-planning.com/msi-files/{manufacturer}/"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    return [a["href"] for a in soup.find_all("a") if a["href"].endswith(".msi")]
```

## Parsing MSI files

```python
def parse_msi(text):
    lines = text.strip().splitlines()
    meta = {}
    h_pattern = []
    v_pattern = []
    mode = None
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "HORIZONTAL":
            mode = "H"
        elif parts[0] == "VERTICAL":
            mode = "V"
        elif mode == "H" and len(parts) == 2:
            h_pattern.append(float(parts[1]))
        elif mode == "V" and len(parts) == 2:
            v_pattern.append(float(parts[1]))
        elif len(parts) >= 2 and mode is None:
            meta[parts[0]] = " ".join(parts[1:])
    return meta, h_pattern, v_pattern
```

## Gotchas
- The `GAIN` header may be in dBd or dBi depending on the manufacturer and file vintage. Converting: `dBi = dBd + 2.15`. CommScope files consistently use dBi; Kathrein legacy files sometimes use dBd.
- Some files have 361 points instead of 360 (0 and 360 both listed). Strip the last point.
- File names do not always match the antenna model number exactly. Build a fuzzy match index (normalise to alphanumeric, case-insensitive).
- A small fraction of files (< 1%) contain non-ASCII characters in the `NAME` field. Open with `encoding="latin-1"` or `errors="replace"`.
- The library includes files for frequencies from 80 MHz to 86 GHz. Filter by frequency band before loading into AEGIS.
- No API or structured metadata index exists. The manufacturer directory listing is the only discovery mechanism.

## Integration with basestationLib

Priority order for pattern lookup:
1. Brussels 181x360 matrix (if the antenna is in the Brussels database)
2. CommScope BSAPatternsWeb (if model is a CommScope/Andrew/Kathrein part number)
3. wireless-planning.com MSI library (broadest coverage)
4. 3GPP TR 38.901 synthetic model (fallback)

```python
from basestations.patterns import fetch_msi_by_model

pattern = fetch_msi_by_model("742215", manufacturer="Kathrein")
```

Cache files at `~/.cache/aegis/patterns/msi/<manufacturer>/<model>.msi`.

## Status
No existing integration. Needs a `patterns` module in `basestationLib`.
