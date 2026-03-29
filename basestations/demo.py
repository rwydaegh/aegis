"""Demo script showing basestationLib features."""
import sys
sys.path.insert(0, '.')

import traceback
import pandas as pd
from basestationLib import get_basestation_instance

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 30)

config = {
    "computation": {
        "max_workers": 4,
        "estimations": {
            "estimate_missing_data_based_on_existing": True
        }
    }
}


def demo_country(country, bbox, region_city=None, **filter_kwargs):
    print(f"\n{'='*80}")
    print(f"  {country.upper()}" + (f" ({region_city})" if region_city else ""))
    print(f"  bbox: {bbox}")
    if filter_kwargs:
        print(f"  filters: {filter_kwargs}")
    print(f"{'='*80}")

    try:
        kwargs = {"region_city": region_city} if region_city else {}
        BS = get_basestation_instance(country, **kwargs)

        instance = BS(
            output_folder=f"output/{country.lower()}/",
            bounding_box=bbox,
            max_workers=4,
            **filter_kwargs,
        )

        df = instance.extract_antennas(config=config)

        if df is not None and len(df) > 0:
            print(f"\n>>> {len(df)} antennas extracted <<<")
            print(f"\nOperators:       {sorted(df['Operator'].dropna().unique().tolist())}")
            print(f"Technologies:    {sorted(df['Technology'].dropna().unique().tolist())}")
            print(f"Frequency bands: {sorted(df['FrequencyBand'].dropna().unique().tolist())}")

            print(f"\nSample rows:")
            cols = ['Operator', 'Technology', 'FrequencyBand', 'Power', 'Gain',
                    'Azimuth', 'CenterHeight', 'Electrical_Tilt', 'Horizontal_Beamwidth']
            avail = [c for c in cols if c in df.columns]
            print(df[avail].head(8).to_string())

            print(f"\nColumn coverage:")
            for col in ['Power', 'Gain', 'CenterHeight', 'Electrical_Tilt',
                         'Horizontal_Beamwidth', 'Vertical_Beamwidth']:
                if col in df.columns:
                    pct = df[col].notna().mean() * 100
                    extra = f" (mean={df[col].mean():.1f})" if pct > 0 else ""
                    print(f"  {col:25s}: {pct:5.0f}% populated{extra}")
        else:
            print("No data returned.")
        return df
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return None


results = {}

# 1. Hungary - fast community data
print("\n" + "#"*80)
print("# DEMO 1: Hungary (community GeoJSON, Budapest)")
print("#"*80)
results["Hungary"] = demo_country("Hungary",
                                  bbox=[19.03, 19.08, 47.49, 47.52])

# 2. Spain - GeoJSON API, Madrid
print("\n" + "#"*80)
print("# DEMO 2: Spain (GeoJSON API, Madrid)")
print("#"*80)
results["Spain"] = demo_country("Spain",
                                bbox=[-3.71, -3.69, 40.415, 40.425])

# 3. Netherlands - WFS, Amsterdam
print("\n" + "#"*80)
print("# DEMO 3: Netherlands (WFS, Amsterdam)")
print("#"*80)
results["Netherlands"] = demo_country("Netherlands",
                                      bbox=[4.88, 4.91, 52.365, 52.375])

# 4. Belgium Flanders (SPARQL, small Ghent area)
print("\n" + "#"*80)
print("# DEMO 4: Belgium Flanders (SPARQL, Ghent)")
print("#"*80)
results["Flanders"] = demo_country("Belgium",
                                   bbox=[3.72, 3.73, 51.05, 51.055],
                                   region_city="flanders")

# 5. Filtering: Flanders 4G only
print("\n" + "#"*80)
print("# DEMO 5: Filtering - Flanders 4G only")
print("#"*80)
results["Flanders 4G"] = demo_country("Belgium",
                                      bbox=[3.70, 3.75, 51.04, 51.06],
                                      region_city="flanders",
                                      technology="4G")

# 6. France (CartoRadio, small Paris area)
print("\n" + "#"*80)
print("# DEMO 6: France (CartoRadio, Paris)")
print("#"*80)
results["France"] = demo_country("France",
                                 bbox=[2.34, 2.36, 48.855, 48.865])

# Summary
print("\n" + "#"*80)
print("# SUMMARY")
print("#"*80)
for name, df in results.items():
    n = len(df) if df is not None else 0
    ops = sorted(df['Operator'].dropna().unique().tolist()) if df is not None and n > 0 else []
    techs = sorted(df['Technology'].dropna().unique().tolist()) if df is not None and n > 0 else []
    print(f"  {name:25s}: {n:5d} antennas | ops: {ops} | tech: {techs}")

# Save all to combined CSV for inspection
all_dfs = []
for name, df in results.items():
    if df is not None and len(df) > 0:
        df = df.copy()
        df['Source'] = name
        all_dfs.append(df)
if all_dfs:
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv("output/demo_combined.csv", index=False)
    print(f"\nCombined dataset: {len(combined)} antennas saved to output/demo_combined.csv")
