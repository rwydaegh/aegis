# BaseStationLib

Python toolkit to extract and standardize mobile base station data across multiple countries through a single config-driven workflow.

## What this repo provides

- Config-based execution through `main.py` and `config.yaml`
- Country-specific extractors behind one shared interface (`BaseStations`)
- Standardized CSV output schema
- Optional estimation of missing antenna parameters
- OpenCellID fallback for unsupported countries (not yet fully implemented)

## Supported countries (direct adapters)

- Austria
- Belgium (`brussels`, `flanders`)
- France
- Netherlands
- Poland
- Spain
- Switzerland
- Hungary

Country-to-module routing is defined in:

`basestationLib/core/country_module_map.json`

Any country not mapped there falls back to `basestationLib/OpenCellID/basestations.py`.

## Installation

```bash
pip install -r requirements.txt
```

or install as a package:

```bash
pip install -e .
```

## Run with config

Edit `config.yaml`, then run:

```bash
python main.py
```

`main.py` calls:

```python
from basestationLib.core import run
run("config.yaml")
```

## Minimal config example

```yaml
locationinfo:
  country: "Poland"
  # region/city: "flanders"   # required for Belgium
  # bbox: [min_lon, max_lon, min_lat, max_lat]

antennafilters:
  # operator: "Orange"
  # technology: "4G"
  # frequency_range: [1800000000, 2200000000]
  # frequencyband: "Band2100MHz"
  # date: "2026-01-01"

output:
  folder: "output"
  # identifier: "custom_run"

computation:
  max_workers: 8
  estimations:
    estimate_missing_data_based_on_existing: true # if true, uses existing data (use Belgium data for this) to estimate missing parameters; if false, leaves missing parameters as NaN
    # csv_paths: [] # list of CSV files with existing data to use for estimation

opencellid:
  api_key_path: "opencellid_api_key.txt"
```

## Output format

Generated CSV files are standardized to the following columns:

- `SiteCode`
- `AntennaLabel`
- `Operator`
- `Technology`
- `Latitude`
- `Longitude`
- `CenterHeight`
- `Power`
- `Frequency`
- `FrequencyBand`
- `Electrical_Tilt`
- `Mechanical_Tilt`
- `Azimuth`
- `Gain`
- `Horizontal_Beamwidth`
- `Vertical_Beamwidth`

Unavailable values are left as `NaN`.

## Programmatic usage

```python
from basestationLib.core import run

run("config.yaml")
```

or direct country class resolution:

```python
from basestationLib import get_basestation_instance

BaseStations = get_basestation_instance("Spain")
instance = BaseStations(output_folder="output/spain")
df = instance.extract_antennas(config={})
```

For Belgium, provide region/city:

```python
BaseStations = get_basestation_instance("Belgium", region_city="flanders")
```

## OpenCellID notes

If fallback is used, provide an API key file and set:
NOTE: OpenCellID may have limited data coverage and may not include all desired parameters. This code is not fully developed and tested, so results may vary. Use with caution and verify output quality for your specific use case.

```yaml
opencellid:
  api_key_path: "opencellid_api_key.txt"
```

## Contributing

See `CONTRIBUTING.md`.

## License

MIT (see `LICENSE`).
