# Base station data sources: comprehensive research

Research compiled 2026-03-31. Covers every source from "the great search" plus new findings.

## What basestationLib already covers

8 European countries with direct adapters, plus OpenCellID fallback:

| Country | Source | API type | Data richness |
|---|---|---|---|
| Belgium (Brussels) | environnement.brussels | REST + HTML | All 16 columns at 100%, includes 22K radiation patterns |
| Belgium (Flanders) | Flemish SPARQL endpoint | SPARQL | Rich (power, azimuth, gain, tilt, beamwidth) |
| Netherlands | Antenneregister (WFS) | OGC WFS | Good (power, height, azimuth; no tilt/gain/beamwidth) |
| France | CartoRadio (ANFR) | REST API | Good (height, azimuth; no power/tilt/gain) |
| Austria | SenderKataster | REST API | Partial (API intermittent) |
| Spain | VCTEL InfoAntenas | GeoJSON tiles | Slow (millions of tiles) |
| Switzerland | BAKOM/geo.admin | Static GeoJSON | Broken (403 as of 2026-03) |
| Poland | BTSearch | Web scraping | Slow (~20 min) |
| Hungary | OpenCellID | Static GeoJSON | Sparse (location + frequency only) |

Brussels is the gold standard: 100% population on all 16 columns including gain, tilt, beamwidth, and full 181x360 radiation patterns.

---

## Crowd-sourced / community databases

### OpenCellID (opencellid.org)

Funded and operated by Unwired Labs. CC-BY-SA 4.0.

**Bbox API:**
```
GET https://opencellid.org/cell/getInArea?apiKey=KEY&BBOX=latmin,lonmin,latmax,lonmax&radio=LTE&format=json
```
- Hard cap: 50 cells per request (paginated via `offset`)
- Each cell returned costs 1 API credit
- Daily limit: 1,000 credits per key
- Must contribute 1/10th the data you download (rolling 15-day window)

**Fields returned:** radio type, MCC, MNC, LAC/TAC, CID, lat, lon, range (coverage radius meters), samples count, averageSignal (dBm), created/updated timestamps.

**Fields NOT available:** No azimuth, height, transmit power, gain, tilt, beamwidth, or physical tower ID.

**Accuracy problems:**
1. Maps by Cell ID, not tower ID. A tower with 3 sectors = 3 separate entries with different estimated positions, each skewed toward where measurements were taken. Vodafone Germany: 40K physical towers but 290K cell IDs in OpenCellID.
2. Centroid-of-measurements approach. If a road approaches a tower from only one side, the centroid drifts.
3. ~1/3 of entries may be misattributed to wrong carriers (per Reddit testing).

**Bulk download:** CSV by country, last 18 months only. Requires API key.

**Verdict:** Useful as location-only fallback for countries without government registries. Not usable for RF parameters.

### CellMapper (cellmapper.net)

Crowdsourced, most accurate tower positions available. Uses multilateration from drive-test measurements.

**Unofficial API:** `api.cellmapper.net/v6/getTowers?MCC=...&MNC=...&RAT=LTE&boundsNE...&boundsSW...` exists (used by browser frontend) but is undocumented, CAPTCHA-protected, and accessing it violates TOS.

**TOS explicitly prohibits:**
- Commercial or business purposes
- Government, police, or military use
- **Educational or academic institution use**
- Reverse engineering

**Data collected:** lat/lon (triangulated), MCC/MNC/LAC/CID, technology, EARFCN (encodes frequency), PCI, signal strength. No power, azimuth, tilt, gain.

**Verdict:** Best accuracy but legally unusable for research. Would need explicit written permission from CellMapper.

### Mozilla Location Service (MLS)

**Shut down July 2024.** Mozilla Stumbler (data collection app) retired February 2021. Backend archived on GitHub July 31, 2024. Data was CC-0 (public domain).

**Successor:** BeaconDB (beacondb.net) - API-compatible with MLS at `api.beacondb.net/v1/geolocate`. 5.3M cells, 107M WiFi networks. No bulk dump yet.

### Mylnikov.org

Free API aggregating OpenCellID + openBmap + MLS. No auth, no rate limit, MIT license.
```
GET https://api.mylnikov.org/geolocation/cell?v=1.1&data=open&mcc=206&mnc=1&lac=32006&cellid=8427
```
Returns lat, lon, range (accuracy in meters). ~32.5M cells. Updated weekly. Geolocation only (input a cell ID, get position). No bbox query.

---

## Commercial geolocation services (NOT tower databases)

These answer "where is this device?" not "where are the towers?"

### Unwired Labs / LocationAPI.org

Same entity as OpenCellID. Commercial enrichment of the crowdsourced data.
```
POST https://eu1.unwiredlabs.com/v2/process
```
**No bbox tower query.** Geolocation only. Free tier exists with daily limits.

### Combain (combain.com)

Swedish geolocation company. Claims 195 countries. **No bbox tower query.** Geolocation only. Pricing is per-API-call. On-premises server option available.

### Google Geolocation API

Returns device position from observed cell/WiFi signals. **Cannot retrieve tower locations.** 10K free/month, then $5/1K requests. Not a tower database.

### Google Vector Tile API (SemanticTileService)

The "shady" API from the notes. Serves map vector tiles (roads, buildings, terrain). **No cell tower layer at all.** The "semantic" refers to map features, not telecom infrastructure. Dead end.

---

## US data sources

### FCC ASR (Antenna Structure Registration)

Registers physical antenna structures. **Only required for structures >200ft or near airports.** Most cell sites are below this threshold and not registered.

**Fields:** lat/lon, structure height, type (monopole, lattice, rooftop), owner, FAA study number.
**Missing:** Frequency, power, azimuth, tilt, gain. ASR registers towers, not radios.

**Download:** Pipe-delimited ZIP at fcc.gov/wireless/data/public-access-files-database-downloads

### FCC ULS (Universal Licensing System)

Covers spectrum licenses. **Cellular/PCS/AWS operate under geographic area licenses, not site-specific.** This means ULS has NO per-site antenna parameters for the major carriers.

**What IS in ULS for microwave/fixed services:** frequency, bandwidth, coordinates, antenna height, make/model, azimuth, tilt, gain, polarization, beamwidth, ERP, path coordinates. Excellent data but wrong service type.

**Verdict:** FCC regulatory framework simply does not require cellular carriers to file per-site engineering data. Fundamental gap for the US.

### TowerMaps.com

Manually compiled database of physical tower locations (not RF parameters). Claims 330K-600K+ sites. Covers structures FCC ASR misses (sub-200ft, buildings).

**Price:** $9,990/year full US. Academic discount: 95% = **$499.50/year**. MS Excel, no updates, no API. Desktop use only.

**Does NOT include:** Carrier tenant info, frequency, power, azimuth, tilt, gain. Location and structure type only.

**David Ward (TowerMaps) confirms:** "significant deviations from OpenCellID" and "Tower Maps is the location information (tower, building) and not the antenna data."

### AntennaSearch.com

Wrapper around FCC ASR + local zoning/permit data. Web-only, no API. Same limitations as FCC ASR.

### MapRad.io

Built by Open Spectrum Pty Ltd (Australia). Free web tool that provides a unified view of radiocommunications register data. Covers US (FCC ULS) and Australia (ACMA RRL). Map + satellite imagery interface with faceted search, proximity queries, and filtering by radio operating parameters. Exports to Excel and Google Earth. Has "integrable services" (API) but documentation is JS-rendered and hard to scrape.

**Strengths:** For Australia, it wraps ACMA RRL which is one of the richest public databases globally (frequency, EIRP, azimuth, tilt, polarisation, antenna ID per licence). The faceted search and map UI are polished. Free.

**Limitations:** For US cellular, hits the same FCC ULS wall: geographic area licenses mean no per-site data for Verizon/AT&T/T-Mobile. The US data is excellent for microwave, land mobile, and broadcast services but not macro cellular. Does not appear to cover European registers.

**Verdict:** Not a new data source, but a well-built aggregator UI over FCC + ACMA. If we build an ACMA adapter for basestationLib, we'd be pulling the same underlying data. The UI/UX is worth studying as inspiration for what "beautiful base station visualization" looks like.

### TowerSource

B2B marketplace for tower leasing in North America. Real estate/site acquisition tool. No RF parameters. Not useful for dosimetry.

### HIFLD Cellular Towers (DHS/CISA)

Derived from FCC records. CSV/KML/Shapefile at catalog.data.gov. Location data only. Last updated October 2022.

---

## Non-US government databases worth adding to basestationLib

### Canada - ISED Spectrum Management System

Requires per-site technical data (unlike US FCC). 54 fields per site including: lat/lon, antenna height, azimuth (Tx and Rx), frequency, power.

**Download:** https://ised-isde.canada.ca/site/spectrum-management-system/en/download-sms-data (ZIP)
**ArcGIS layer:** CSV, KML, GeoJSON, GeoServices API at arcgis.com
**Third-party tools:** tafl.jonathanmorgan.net, tafl.mckie.ca

**Verdict:** Better than FCC for per-site data. Worth building an adapter.

### Australia - ACMA RRL (Register of Radiocommunications Licences)

Most technically detailed public database found globally. Per-licence records with: frequency, bandwidth, EIRP, lat/lon, elevation, antenna ID, polarisation, azimuth, tilt, feeder loss, licensee.

**Download:** Daily ZIP (`spectra_rrl.zip`) from acma.gov.au/radiocomms-licence-data
**API:** web.acma.gov.au/rrl/

**Verdict:** Outstanding for RF exposure research. Has everything except radiation patterns.

### New Zealand - RSM RRF

REST API: portal.api.business.govt.nz/api/radiospectrum-management
Search: rrf.rsm.govt.nz/ui
Contains technical parameters per licence. Worth checking for completeness.

---

## European countries NOT yet in basestationLib

### Denmark - Mastedatabasen (TOP PRIORITY)

**URL:** https://mastedatabasen.dk
**API:** https://dk-api.mastdatabase.co.uk (well-documented REST/JSON:API)

Best open antenna API in Europe. Bbox queries, operator/technology/frequency band filters. Up to 5000 results/page.

**Fields:** Location, operator, technology (GSM/LTE/5G-NR), frequency band, service type, existing/planned status.
**Missing:** Power, azimuth, tilt, gain.

### Germany - BNetzA EMF-Datenbank (HIGH PRIORITY)

**URL:** bundesnetzagentur.de/emf, map at emf3.bundesnetzagentur.de
**Sites:** 82,260 transmitter locations, 552,777 rated antennas.

**Fields:** Location (up to 80m imprecision), mounting height, azimuth, operator, safety distances.
**Missing:** Frequency, power, technology, tilt, gain.
**API:** None official. Scrapeable via `Standortservice.asmx/` endpoint. GitHub scraper: github.com/stefanw/bnetza-emf-scraper

### Ireland - ComReg Siteviewer

**URL:** siteviewer.comreg.ie
Legally mandated reporting. Shows all mobile base stations and fixed radio links. Map-only, no API or download found. Worth scraping or contacting ComReg directly.

### Italy - CASTEL (Lombardy only)

**URL:** castel.arpalombardia.it/castel/
Regional database. Has location, operator, power, type. No API. National ISPRA CEM data fragmented across regions.

### UK - Dead end

Sitefinder shut down. 2012 snapshot available (13 years stale) at datashare.ed.ac.uk/handle/10283/2626. No replacement. Connected Nations reports are aggregate coverage only.

### Norway - Closed

Finnsenderen.no removed mobile base station display in December 2022 for security reasons.

### Sweden, Finland, Portugal, Romania, Czech Republic - No public per-site databases found.

---

## Antenna radiation patterns

### MSI file format

De facto industry standard for 2D antenna patterns. Originally from Mobile Systems International / Planet RF planning software.

**Structure:**
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

- Values are **relative attenuation in dB** (0.00 = boresight/peak, 3.0 = 3 dB down)
- Standard: 360 points, 1-degree resolution, two orthogonal cuts (H + V)
- GAIN header can be dBd or dBi (watch out)
- **Limitation:** Only two 2D cuts, not full 3D sphere. Converting to 3D requires interpolation.

### Pattern sources

| Source | Coverage | Format | Cost |
|---|---|---|---|
| wireless-planning.com | 400K files, 50+ manufacturers | MSI | Free |
| CommScope BSAPatternsWeb | CommScope/Andrew catalog | 25 formats (MSI, ADF, CSV, etc.) | Free, no login |
| Kathrein (kathrein.com) | Kathrein catalog | ZIP per product | Free |
| CloudRF database | Broad | ADF, MSI, ANT | Free tier |
| Brussels environnement.brussels | Brussels antennas (22K patterns) | 181x360 MATLAB matrix | Via API |

**CommScope direct download:** `commscope.com/BSAPatternsWeb/DownloadPatterns.aspx?model=MODEL` - exports to ~25 formats. Best single source for pattern files.

### NSMA/ADF format (TIA/EIA-804-B)

More rigorous than MSI. Supports multiple frequencies per file, multiple pattern cuts, actual gain values (not relative loss), 2-degree resolution. Extension: `.adf`. Validator at cloudrf.com.

### 3GPP TR 38.901 parametric model

Mathematical model, not measured data. Single-element pattern:
```
A_E,V(θ') = -min[12(θ'/θ_3dB)², SLA_V]    dB
A_E,H(φ)  = -min[12(φ/φ_3dB)², A_m]       dB
```
Default: θ_3dB = φ_3dB = 65 deg, SLA_V = A_m = 30 dB, G_max = 8 dBi. Good for simulation when no measured pattern available. Ignores realistic sidelobes.

### Brussels 181x360 matrix vs MSI

Brussels provides full upper hemisphere sampling (181 elevation x 360 azimuth at 1 degree resolution). This is **more complete than MSI** (which only gives two cuts). MSI requires interpolation to reconstruct 3D; Brussels matrices are directly usable. For dosimetry, Brussels format is the gold standard.

### Practical value for dosimetry

- Full antenna patterns vs isotropic: **25-35 dB difference** in back-lobe directions. Critical for realistic exposure distribution.
- Full patterns vs beamwidth+gain envelope: the envelope captures main lobe correctly but overpredicts sidelobes.
- Near-field (< 0.5m from 5G mmWave array): far-field formula overestimates peak PD by 3-4x. Beyond 1m: < 5% difference.
- For AEGIS population-average dosimetry: directional rolloff is essential. A simplified model overestimates average exposure by the front-to-back ratio.
- CloudRF, Atoll, Planet, NetAct all use MSI/ADF patterns. No serious planner uses isotropic.

---

## Priority ranking for basestationLib expansion

### Tier 1: Rich data, good API, easy to implement
1. **Denmark (Mastedatabasen)** - JSON:API with bbox, well-documented
2. **Australia (ACMA RRL)** - daily ZIP download, has EIRP/azimuth/tilt
3. **Canada (ISED SMS)** - ZIP download + ArcGIS API, has per-site parameters

### Tier 2: Rich data, needs scraping
4. **Germany (BNetzA)** - scrapeable, 82K sites, has azimuth + height
5. **Ireland (ComReg)** - map scraping or data request needed

### Tier 3: Supplementary
6. **Italy (CASTEL, Lombardy)** - regional only, web scraping
7. **New Zealand (RSM RRF)** - REST API, small market
8. **OpenCellID bulk download** - location fallback for uncovered countries

### Not worth pursuing
- UK (dead), Norway (closed), Sweden/Finland/Portugal/Romania (no data)
- CellMapper (legally blocked), Combain/Unwired Labs (geolocation only, no tower inventory)
- Google APIs (wrong tool entirely)
- TowerMaps ($500 for US locations only, no RF parameters)
- FCC (no per-site cellular data due to geographic licensing)

---

## About the wireless-planning.com MSI library

The 400K MSI file library is free and covers most major antenna manufacturers. For AEGIS, the practical path is:
1. Match antenna model names from government databases (Brussels, Flanders) to MSI files
2. Use CommScope BSAPatternsWeb for CommScope/Andrew/Kathrein models (25 export formats)
3. Fall back to 3GPP TR 38.901 parametric model when no measured pattern available
4. Brussels 181x360 matrices are already better than MSI for antennas in that database
