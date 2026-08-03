# Propagation blends for all eleven squares

`build_propagation_blends.py` used to build four squares and say in its own header
that four cannot be representative of eleven. It now builds all eleven, so there is
nothing left for the set to be representative of, and the caveat is gone from the
module docstring and from the archive index that ships inside the zip.

Built on 2026-08-03 on the rented `blgpu` box, eight cores and an RTX A6000, because
this host was carrying six other agents and an earlier 250 m batch had already been
killed here at a load average above thirty.

## What was built

Eleven Blender files, each traced against the published 250 m crop at 15 GHz over 60
standpoints with a bounce budget of three, which is the operating point of the
`city250_L3_*` sweep the paper quotes. Ground datum measured per site by
`measure_ground_datum`, so Krakow and Toulouse stand on the pavement rather than on
the Cloth Hall and the Capitole.

| square | traced triangles | walk candidates | ground datum m | blend MB | figures |
|---|---|---|---|---|---|
| `korenmarkt` | 617,091 | 330 | 51.023 | 32.1 | 20 |
| `krakow_rynek` | 557,526 | 716 | 250.975 | 5.7 | 10 |
| `newyork_timessquare` | 1,064,389 | 579 | -18.410 | 10.5 | 16 |
| `brussels_grandplace` | 706,720 | 700 | 65.768 | 20.4 | 16 |
| `london_trafalgar` | 783,425 | 929 | 54.831 | 8.2 | 9 |
| `madrid_plazamayor` | 720,373 | 788 | 702.669 | 19.3 | 15 |
| `mexico_zocalo` | 707,812 | 388 | 2223.247 | 25.3 | 15 |
| `milan_duomo` | 779,421 | 1176 | 163.141 | 16.1 | 17 |
| `prague_staromestske` | 664,619 | 1008 | 236.721 | 37.0 | 15 |
| `tokyo_hachiko` | 797,615 | 786 | 51.434 | 7.4 | 9 |
| `toulouse_capitole` | 1,016,440 | 569 | 191.097 | 8.7 | 9 |

151 rendered figures in total. The figure count varies because
`propagation_blender.py` skips a view whose layer the site does not have, and it says
so in the log rather than rendering an empty frame.

Nothing was carried over from the four site build. Every payload was retraced,
because the old Krakow payload sat on the superseded datum at 269.124 m and three of
the four ran at a bounce budget of four. The retrace is visible in Krakow's walk
candidate count, which went from 163 to 716 once the standpoints came off the roof.

## Why each square is in the archive

Each entry in `SITES` is the text the archive index prints under that square. Every
number in it is a median or a spread over the 80 standpoints of `city250_L3_*`, the
single writer eleven site sweep on the fixed datum, read from
`outputs/exposure_korenmarkt/city250_L3_<site>_15ghz_locations.jsonl` and cross
checked against the tables in `AGGREGATE_REBUILD.md`. Within square spreads are p95
over p05 in decibels, which is the convention `SPINE.md` uses. I recomputed all of
them from the JSONL rather than copying, and they reproduce the published tables to
the printed digit.

| square | the fact the reason rests on | where it comes from |
|---|---|---|
| `korenmarkt` | only square with two semantic surfaces, both depth clouds and 18 bodies. Eighth of eleven isotropic at 0.2916, seventh rooftop at 0.1626 | `evidence_directories` over `outputs/`, and the blend logs' collection listings. Medians from `city250_L3_korenmarkt` |
| `krakow_rynek` | datum was 18.19 m high, costing 5.26 dB rooftop. Sky median 0.3138, third behind London 0.3304 and Mexico 0.3240. Rooftop spread 2.86 dB, second narrowest | `GROUND_DATUM.md` eleven datums table, `AGGREGATE_REBUILD.md` rooftop shift table, `city250_L3` |
| `newyork_timessquare` | sky median 0.1210, lowest. Isotropic 0.1694, lowest. Street small cell 0.0604, highest, against 0.0375 next. 1.48 bounces, 21.50 ns excess delay, both highest | `city250_L3` |
| `brussels_grandplace` | rooftop spread 12.89 dB and street small cell spread 19.01 dB, both largest. The enclosed square feeding narrow streets | `AGGREGATE_REBUILD.md` spread table, `city250_L3`, and `REPORT.md` for the shape of the walk |
| `london_trafalgar` | sky median 0.3304, highest. Rooftop median 0.2884, second. Rooftop spread 4.55 dB, third narrowest | `city250_L3` |
| `madrid_plazamayor` | isotropic spread 6.46 dB inside one square against 3.71 dB across all eleven medians | `AGGREGATE_REBUILD.md` spread table, recomputed from `city250_L3` |
| `mexico_zocalo` | highest isotropic median 0.3977 and highest rooftop median 0.3070. Escaped fraction 0.898, highest | `city250_L3` |
| `milan_duomo` | rooftop spread 2.55 dB, narrowest, against Brussels' 12.89. Crop widened to 170 m from a 320 m acquisition ball for the 109 m spire | `city250_L3`, and `config/milan_duomo.json` `geometry_selection` |
| `prague_staromestske` | fourth on sky at 0.2882, fourth on isotropic at 0.3584, fifth on rooftop at 0.2377. At neither end of any panel | `city250_L3` |
| `tokyo_hachiko` | excess delay 17.11 ns, second longest behind 21.50. Sky median 0.1739, third from the bottom. Street small cell 0.0161, ordinary | `city250_L3` |
| `toulouse_capitole` | datum was 13.94 m high, costing 1.29 dB isotropic and 1.83 dB rooftop and second place to seventh. Rooftop spread 11.40 dB, second widest | `GROUND_DATUM.md`, `AGGREGATE_REBUILD.md` shift tables, `city250_L3` |

Prague is the one square with no superlative, and its entry says so and gives its
rank in three panels instead of manufacturing one.

### Three of the four existing entries were rewritten

They were not merely incomplete, they were superseded, and shipping them beside
seven correct ones would have put a known false claim in the archive.

- Krakow said it was "the most open square in the set, and the highest susceptibility
  under every illumination model." That was the Cloth Hall roof. `REPORT.md` marks
  the whole section superseded on 2026-08-03 and records that at street level Krakow
  reads 0.3138 sky and is third. Its entry now leads with the correction.
- New York said "18 percent sky against Krakow's 46." Neither number survives the
  datum fix. Under `city250_L3` the two sky medians are 0.1210 and 0.3138.
- Brussels said 12.7 dB of rooftop spread. The corrected figure is 12.89 dB, and 12.7
  matches nothing in the current outputs.

Korenmarkt's entry was rewritten for a different reason. It claimed to be "the only
site with registered panorama semantics," and five other squares carry a Vistas
fishnet with registered poses. What is actually unique to Korenmarkt is the full
stack, which is what it now says.

## Toulouse and the config it did not have

The config supplies what the mesh cannot: the site name, the WGS84 anchor, the ENU
origin, and `camera_ground_z_m`. `semantic_twin.scene.load_scene` refuses a document
missing any of those four. Downstream, `fetch_site_panoramas.py` needs the origin to
place a panorama and the datum to cast a camera altitude against,
`semantic_twin.panorama` and `semantic_twin.mapillary` need the same,
`propagation.bystanders.ground_datum` prefers it over its own mesh probe, and
`run_exposure.registered_ground_z` reads it as a cross check gate on the measured
datum. The rest of the document, the frequency band split, the mesh paths, the
screening provenance and the mesh defect list, is provenance rather than input.

None of that is needed by `export_propagation_payload.py`, which reads its mesh from
`data/geometry/` and measures its own datum, so Toulouse could have been built
without a config. It was written anyway, because the reason it was missing is now
fixed.

`build_site_config.py` exists specifically for this case, and its docstring names
Toulouse: the old datum method probed under the anchor, and at Place du Capitole the
anchor lands in a small enclosed courtyard. The replacement measures the dominant
open ground surface over an 80 m disc instead. Toulouse has a 130 m mesh and a
screening row, which is everything the builder needs, so:

```
python build_site_config.py --site toulouse_capitole
```

It writes `camera_ground_z_m` 191.187 m, from a modal band holding 0.479 of the disc
with 0.347 m of spread against a relief of 190.3 to 216.2 m. Two independent checks
agree. `GROUND_DATUM.md` records `measure_ground_datum` at 191.226 m for the same
crop, and this build's own trace measured 191.097 m over its 60 m walk radius. The
three agree to 0.13 m.

**One caveat that comes with writing it.** `run_exposure.registered_ground_z`
documents its return value as coming from the panorama registration and therefore as
independent of any mesh statistic. It gets that value by reading `camera_ground_z_m`
out of the config, and it cannot tell how the number got there. Toulouse now has a
mesh derived datum in that field, so the cross check for Toulouse compares the mesh
against the mesh. This is not new. Krakow and London already carry
`build_site_config.py` datums for exactly the same reason, and `GROUND_DATUM.md`
names those three as the sites with no registration. Toulouse joins them rather than
starting anything. The gate still passes with room to spare, at 0.13 m against a 1 m
tolerance, but it is not evidence.

## What failed

Nothing was dropped from the archive. All eleven squares have a blend, a manifest and
an entry in the index. Four things went wrong along the way and all four are fixed or
recorded.

**`rtree` was missing from the venv on the GPU box.** Four squares crashed after a
full five minute trace, inside `attach_evidence` at
`trimesh.proximity.closest_point`, which needs it. Installed with
`uv pip install rtree` to 1.4.1, the same version this host has, and retraced. This
is an addition to that box and nothing was removed from it.

**The GPU box was missing most of the image evidence.** `tools/blgpu.sh sync` pushes
code, geometry and panorama semantics, and not the fishnet, depth, body or
registration products. The first blend pass built a Korenmarkt with an empty
`05 depth clouds`, an empty `06 panorama captures` and an empty `07 bystander
bodies`, which would have been a quiet downgrade against the four site archive. I
stopped that pass, pushed 255 MB of evidence directories plus
`outputs/registration_sky_conflict.json` and the 83 `alignment/` pose directories it
points at, rebuilt the evidence half with `--evidence-only`, and reran. Korenmarkt now
carries 2 semantic surfaces, 2 depth clouds, 15 panorama captures and 18 bodies, and
`06 panorama captures` is populated at the other six squares that have poses.

**`outputs/tokyo_hachiko_fishnet_vistas/` is a stub.** It holds
`site_fishnet_manifest.json` and no per view `.npz`, so `fishnet_layer` reaches
`np.concatenate([])` and raises `ValueError: need at least one array to concatenate`.
Any trace of Tokyo with evidence enabled will hit this, on this host too. I moved the
copy on the GPU box aside to `tokyo_hachiko_fishnet_vistas.stub_no_npz` so Tokyo could
build, and left the one here untouched. The directory here is still a landmine.

**Tokyo lost its three registered poses to an early return.** With the stub out of
the way `evidence_directories` returns empty for Tokyo, and `attach_evidence` returns
at `if not directories` before it reaches `registration_layer`. So a square with poses
and no fishnet gets neither. Tokyo has 3 poses in
`outputs/registration_sky_conflict.json` and its blend shows `06 panorama captures:
empty`. Both this and the stub are in `export_propagation_payload.py`, which belongs
to another thread, so neither was edited here.

## The archive

`papers/city-exposure-study/semantic_twin/propagation_blends.zip`, 188,945,241 bytes,
188.9 MB, 23 entries. Copied identically to
`papers/city-exposure-study/propagation_blends.zip` and left in place at
`semantic_twin/outputs/propagation_viz/propagation_blends.zip`, which is where the
builder writes it. All three are the same file by MD5. The four site archive was kept
until the new one verified.

It grew from 27 MB to 189 MB. The four squares with no image evidence weigh 5.7 to
8.7 MB each, the same order as the old four, and the seven that carry evidence weigh
10.5 to 37.0 MB. The growth is the evidence layers, not the propagation ones.

Verified before replacing anything: every square has both a `.blend` and a manifest
in the zip, the index names all eleven, every manifest reports 60 standpoints at a
250 m crop and 15 GHz with a bounce budget of three, and no two squares share a
triangle count. Triangle counts, walk candidate counts, ground datums, hero sky
fractions, susceptibilities and trace times are all distinct per square and none of
them is a default.

Nothing in `.gitignore`'s way was staged. The meshes, the blends and the archive are
all ignored, and the commit carries `build_propagation_blends.py`,
`config/toulouse_capitole.json` and this file.
