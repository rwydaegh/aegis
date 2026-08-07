# Three-way scene ablation

`run_ablation.py` asks one question: does the intelligent hybrid change the
exposure-relevant channel, or would either naive baseline have done?

```bash
P=/home/user/aegis/.venv/bin/python
$P run_ablation.py --every 10                                  # smoke, 3.5 min
$P run_ablation.py --every 2 --samples 4000000 \
    --out data/ablation_full.json --figure figures/ablation_full.png
$P run_ablation.py --scenes osm --verify-sectors               # sector-model check
$P run_ablation.py --plot-only                                 # redraw the figure
```

Outputs `data/ablation_smoke.json`, `data/vegetation_material.json` and
`figures/ablation_smoke.png`.

## Harness

One `PathSolver` call per (scene, mast), with every walk sample present as a
receiver in the same call, so the geometry is traced once and read out per
sample. Per walk sample the run records total path gain, per-sector gain, best
sector, a LOS flag (a valid path whose interaction list is empty at every depth)
and the path count, plus the receiver z the scene gave it. Results are written
after every mast, so a run that dies late still leaves usable data.

Scenes are loaded with `merge_shapes=True` and dropped from memory as soon as
their four masts are done. The photogrammetry scene is 497 021 triangles and the
box has 15 GB shared with other work.

The ground probe is one batched Mitsuba call for the whole walk. Ray by ray, the
drjit dispatch overhead dominates: 26 s for 123 samples against 0.05 s batched,
bit-identical results.

## Choices

**Frequency 3.5 GHz.** `data/sites.json` carries positions, heights, azimuths and
`power_dbm_max` but no frequency, gain or tilt, so 3.5 GHz is an assumption, not
data. The `tech` field lists 5G at three of the four masts used.

**Antenna.** Per sector, one 3GPP TR 38.901 Table 7.3-1 element (Sionna's
`tr38901` pattern: 65 deg beamwidths, 8 dBi, 30 dB floor), vertically polarized,
yaw only. Compass azimuth A becomes a Sionna yaw of 90 - A, because the element
boresight is +x and +x is East in this frame. Mechanical downtilt is 0: the tilt
column of `sites.json` is empty and inventing a tilt would move every number by
several dB. The receiver is an isotropic vertically polarized point, which keeps
the reported quantity a property of the scene rather than of a body model.

**Sites.** `sites.json` has 10 records but only 6 physical masts: the same mast
is registered several times by different operators or technologies. Records
within 15 m and 3 m of antenna height are merged, and the union of their
azimuths is deduplicated at 15 deg, since two registrations of one panel differ
by a few degrees (50/60, 140/150, 230/240, 320/330 on the Sint-Michiels mast).
The four masts with the highest `power_dbm_max` are traced.

**One trace per mast, sector patterns applied afterwards.** All sectors of a mast
sit at one point, so their ray geometry is identical, and tracing them as separate
transmitters would repeat the same search 3 to 10 times. `run_ablation.py`
instead traces one isotropic source per mast and applies the element pattern per
path from the reported angles of departure. This is exact for a yaw-only
rotation, because a rotation about z leaves the spherical polarization basis at
a given world direction unchanged, so only the pattern arguments move. A
downtilt would break that, and `--downtilt` therefore forces `--sector-mode
traced`. Verified path by path against a traced 4-sector and 10-sector run: the
per-sector gains agree to 5 decimal places whenever both runs find the same
paths (see "Sector model" below for the case where they do not).

**Depth 3, diffraction on.** Wedge diffraction costs 11% more wall time on the
hybrid scene (115 s vs 104 s for a 4-source, 49-receiver call) and takes the
path count from 8 to 117. In a medieval street grid where most of the walk is
NLOS, leaving it off would mean reporting mostly nothing. `edge_diffraction`
(illuminated-region wedges) stays off. Refraction is on, so rays penetrate
building slabs.

**Receiver height.** 1.5 m above whatever surface each scene has under the walk
sample, probed with downward Mitsuba rays in that scene. The walk xy is identical
in all three scenes. This matters: the photogrammetry skin sits about 1 m above
the fitted terrain along this route (median 50.98 m vs 49.94 m), so a fixed z
would bury the receiver in the photo scene.

The surface probe is the lowest of five rays on a 2.5 m disk, not the single
vertical ray `export_scenes.py --validate` uses. A single ray was wrong here in a
way worth recording. The walk hugs facades, and over a 50 m stretch near arc
length 85-135 m the vertical ray clipped a roof edge and put the pedestrian
14-21 m up, on a roof, in all three scenes and at three different heights. That
one artifact manufactured LOS at two masts: OSM reported 27 LOS samples of 49 at
the tall mast and 6 at OV5198E where the corrected run reports 21 and 0.
`poc_relevance.py` already used a min-over-disk projection for exactly this
reason, and the disk probe restores it. A receiver genuinely on a roof still reads as
a roof, since all five probes land on it.

**Transmitter height.** Identical in all three scenes: terrain plus the
registered antenna height, raised if needed to clear the photogrammetry roof the
mast stands on. A mast's absolute height is a fact about the city, not about the
mesh, so it should not move between scenes. The consequence is that in the OSM
scene the mast floats above its own too-short roof. That is the naive error being
measured, not an inconsistency in the setup.

**Reported quantity.** Path gain in dB, that is the sum of |a|^2 over all valid
paths, summed incoherently across the sectors of a mast, with equal power per
sector. `power_dbm_max` is not applied: it is a per-site maximum of unclear
scope, and folding it in would put an unsourced number in front of every result.

## Sector model, and what `--verify-sectors` actually shows

Compared path by path on a fresh scene, the analytic sector model reproduces a
traced multi-transmitter run exactly. With diffraction off, the four sectors of
the Sint-Michiels mast and the ten of OV5198E agree to 5 decimal places on every
receiver where both runs find the same paths.

`--verify-sectors` nevertheless reports disagreements of up to 8 dB on the site
total and "one mode found no path" on individual sectors. That is not the sector
model. Sionna shoots `samples_per_src` rays *per source*, so a traced run with
ten co-located sectors spends ten million rays where the analytic run spends one
million, and the extra budget finds marginal paths the cheaper run misses.
Raising `--samples` to 1e7 does not converge the difference either: it moves,
because the paths involved are single diffracted contributions on deeply
shadowed links at -135 to -160 dB, where the solver's own path search is the
noise source. Links that matter for exposure, the ones within 20 dB of the
strongest, are unaffected.

Two things follow. The analytic mode is the better default: it is 5 to 8 times
cheaper and its path set does not depend on how many sectors a mast happens to be
registered with, so a 10-sector mast and a 3-sector mast are traced on equal
terms. And any conclusion drawn from the bottom of the distribution needs the
seed-repeatability number below, not the nominal precision of the dB values.

## Vegetation material

The exporter left `itu_wood` on the 15 canopy proxies as an explicit placeholder.
`run_ablation.py` replaces it at load time with a homogeneous lossy medium
derived from ITU-R P.833. The derivation is written to
`data/vegetation_material.json` on every run.

Source: Recommendation **ITU-R P.833-10 (09/2021)**, Table 8, "Fitted values of
sigma with frequency/species", 3.5 GHz row, in leaf, column "Plane tree,
american": **sigma = 0.513 Np/m**. Platanus is the dominant street tree around
the Korenmarkt and Table 8 has no European species at 3.5 GHz. The whole in-leaf
3.5 GHz row is kept in the JSON as a sensitivity range: 0.21 (Japanese cherry)
to 0.73 (trident maple) Np/m.

The conversion factor is the one place this can go wrong by a factor of two.
sigma is the RET combined absorption and scatter coefficient and enters P.833 as
`exp(-tau)` inside a `-10 log10(...)`, so it extinguishes *power*, and

    gamma = 10 log10(e) * sigma = 4.343 * 0.513 = 2.23 dB/m

not 8.686 * sigma. The 8.686 in Step 9 of the slant-path annex applies to
`K_c''`, a *field* propagation constant, which is a different quantity. The
resulting 2.23 dB/m sits where a single dense canopy should sit relative to the
0.3 dB/m woodland average of Fig. 2 at 2 GHz, which is the sanity check that the
factor is right.

Then, with a sparse-canopy eps' = 1.2:

    alpha    = 0.1151 * 2.23           = 0.2565 Np/m   (field)
    eps''    = alpha sqrt(eps') c/(pi f) = 7.661e-3
    sigma_c  = 2 pi f eps0 eps''       = 1.492e-3 S/m
    tan d    = 6.4e-3

The low-loss step is not a real approximation here: the exact Debye alpha differs
by 5e-4 %. eps' = 1.2 also keeps the front-face Fresnel reflection near -27 dB,
so the proxy attenuates rather than mirrors, which is the point of an effective
canopy medium.

**Thickness.** Sionna models every intersected face as a slab of the material's
`thickness`, so a closed proxy is crossed twice and the loss does not scale with
the actual chord. The thickness is therefore set to half the median Cauchy mean
chord (4V/S) of the 15 proxy ellipsoids: 5.83/2 = 2.92 m, giving 6.5 dB per face
and 13.0 dB per traversal. The honest caveat is that this loss is the same for
every proxy regardless of size, which is a bound on the error the fused blobs
would otherwise introduce: the upstream clustering turned a tree row into one
17.5 m ellipsoid, and a true per-metre canopy density on that volume would have
produced 39 dB.

## Smoke run

49 walk samples (every 10 m over 494 m), 4 masts, 3 scenes, `max_depth=3`,
diffraction on, 1e6 samples per source. Path gain in dB. `cov` is how many of the
49 samples the solver found any path for, and the paired columns use only samples
covered in all three scenes, so hybrid, OSM and photo are compared on the same
receivers.

| mast | scene | cov | LOS | median | p10 | paired median | paired p10 |
|---|---|---|---|---|---|---|---|
| OV5198E, 27.9 m, 10 sectors, 314-406 m away | hybrid | 33/49 | 0 | -131.7 | -140.4 | -136.5 | -138.4 |
| | osm | 39/49 | 0 | -128.2 | -138.0 | -128.3 | -134.1 |
| | photo | 5/49 | 0 | -153.0 | -157.0 | -153.0 | -157.0 |
| C4-021 etc, 42.5 m, 4 sectors, 96-245 m away | hybrid | 44/49 | 0 | -92.1 | -145.0 | -84.2 | -123.1 |
| | osm | 48/49 | 21 | -82.3 | -110.7 | -78.9 | -97.2 |
| | photo | 31/49 | 0 | -102.4 | -152.4 | -102.4 | -152.4 |
| OV5437A, 18.8 m, 3 sectors, 7-279 m away | hybrid | 42/49 | 7 | -83.4 | -118.5 | -82.8 | -98.5 |
| | osm | 42/49 | 4 | -85.8 | -101.4 | -83.3 | -99.2 |
| | photo | 39/49 | 8 | -96.0 | -115.3 | -96.0 | -115.3 |
| OV5208E, 20.2 m, 3 sectors, 33-201 m away | hybrid | 45/49 | 3 | -86.0 | -93.2 | -85.6 | -92.8 |
| | osm | 47/49 | 2 | -90.6 | -104.4 | -87.5 | -96.7 |
| | photo | 44/49 | 2 | -101.1 | -124.9 | -100.2 | -124.0 |

Per-sample differences on the paired subset, baseline minus hybrid:

| mast | osm median / p90 | photo median / p10 |
|---|---|---|
| OV5198E | +4.2 / +22.3 | -19.6 / -20.3 |
| C4-021 etc | +5.0 / +25.8 | -17.8 / -39.3 |
| OV5437A | -0.3 / +2.3 | -12.3 / -27.7 |
| OV5208E | -0.4 / +1.8 | -15.8 / -35.2 |

**The answer to the question the ablation was built to ask is yes, and the two
baselines fail differently.**

*Photogrammetry is uniformly dark.* It is 12 to 20 dB below the hybrid in median
at every mast, a tenth of its samples are 20 to 39 dB below, and it finds no path
at all for 5 to 44 of the 49 samples depending on the mast. Three things push the
same way and this run does not separate them: the Inhouse tiles fuse trees,
awnings and street furniture into the same solid `itu_concrete` skin as the
buildings, the 48 blobs the audit classified as unmapped structure are present
here and in neither other scene, and a photogrammetric skin is bumpy where a
prism is flat, which costs grazing paths. Whatever the split, it is not a subtle
bias, it is a different city.

*OSM fails selectively, and only where its heights are wrong.* At the two masts
that stand on ordinary low buildings, OV5437A and OV5208E, OSM tracks the hybrid
to within 0.4 dB in median and 2 dB at p90: for those links the naive baseline
would have been fine. At the two masts that stand on tall roofs it is +4 to +5 dB
in median and +22 to +26 dB at p90, and at the 42.5 m mast it reports 21 LOS
samples of 49 where the hybrid reports none. Every OSM base sits on one flat
level, so on the Sint-Michiels ridge the skyline is a few metres too low, while
the mast is placed at its true absolute height. A few metres of roof decide
whether a street is lit or shadowed, and the error is one-sided: the naive
baseline over-predicts exposure exactly at the strongest mast.

The p10 columns point the same way, with a caveat: deep shadow is also where the
solver itself is least repeatable, so the tail numbers are indicative and the
medians and LOS counts are the load-bearing ones. See "How much of this is
solver noise" below.

## Vegetation barely moves the answer

Running the hybrid scene with the P.833 medium and with the `itu_wood`
placeholder it replaces gives, on all four masts, a median difference of 0.00 dB,
a p90 of at most 0.01 dB and a worst single sample of 0.54 dB, with no sample
gaining or losing coverage. The override reaches the tracer (the worst-case
differences are non-zero and the run reports the material swap on the merged
canopy object). The canopies are simply not on the paths that matter: the walk is
in narrow streets where the dominant mechanism is diffraction over and around
buildings, while the 15 proxies stand in the open squares.

So the derivation above is worth having because it is now sourced and reusable,
not because it changed this result. It would start to matter for a route that
goes through a canopy rather than past one, which is what the next walk should
deliberately include if the vegetation model is meant to be tested.

## How much of this is solver noise

Re-running the hybrid scene with a different RNG seed, everything else identical:

| mast | coverage | median | p10 | p90 |
|---|---|---|---|---|
| OV5198E | 33 -> 38 | -0.4 | +2.5 | 0.0 |
| C4-021 etc | 44 -> 39 | +2.9 | +17.0 | -0.1 |
| OV5437A | 42 -> 43 | -0.2 | +3.4 | 0.0 |
| OV5208E | 45 -> 47 | -0.5 | -1.0 | +0.2 |

The strong end is exact: p90 moves by at most 0.2 dB. The median moves by half a
dB except at the 42.5 m mast, where five samples change coverage and drag it by
2.9 dB. The p10 is not converged at 1e6 samples per source, moving by up to
17 dB, and individual deeply shadowed samples move by up to 43 dB.

The LOS flags are exactly seed-independent at every sample count tested, which
is what they should be: Sionna finds the direct path with an occlusion test, not
by shooting rays at it. The 21-versus-0 LOS split at the
42.5 m mast is therefore a geometric statement about the two scenes and carries
no sampling uncertainty at all.

Raising the ray budget does converge the rest. On the hybrid scene at the 42.5 m
mast, seed 42 against seed 7:

| samples per source | coverage | median spread | p10 spread | solve [s] |
|---|---|---|---|---|
| 1e6 | 44 / 39 | 3.0 dB | 17.0 dB | 15.7 |
| 4e6 | 47 / 44 | 1.9 dB | 3.4 dB | 62.4 |

So the reading of the results table is: the 12 to 20 dB photogrammetry deficit and
the LOS counts are far outside the noise at any budget, the +4 to +5 dB OSM median
excess at the two tall masts is outside it at 1e6 and comfortably outside it at
4e6, and the p10 column needs 4e6 before it means anything.

## Wall time, and the budget for the full run

Four cores, no GPU, and other work on the same box (load average ~7 during these
measurements), so treat these as an upper bound.

Solver time per scene-mast at 49 samples, from the smoke run:

| | OV5198E | C4-021 etc | OV5437A | OV5208E | total |
|---|---|---|---|---|---|
| hybrid | 4.2 | 17.5 | 13.1 | 12.2 | 47.0 |
| osm | 4.1 | 10.7 | 11.1 | 12.2 | 38.1 |
| photo | 3.4 | 16.4 | 14.2 | 15.4 | 49.5 |

134.6 s of solver time in total, about 3.5 minutes wall clock including scene
loads and ground probes. Scaling in receiver count, measured on the busiest mast:

| walk samples | 49 | 123 | 245 |
|---|---|---|---|
| hybrid solve [s] | 18.2 | 36.7 | 70.3 |
| photo solve [s] | 15.1 | 39.2 | 66.3 |

Slightly sub-linear, roughly 5 s fixed plus 0.27 s per sample, and the 497 k
triangle photogrammetry scene is no more expensive than the 67 k hybrid: the
merged mesh BVH absorbs the difference and the cost is in the per-receiver path
refinement. Extrapolating the whole smoke run:

- `--every 2` (245 samples, 2 m spacing): about **9 minutes**.
- `--every 1` (490 samples, 1 m spacing): about **17 to 20 minutes**.

Neither is expensive, so the sampling density is not the constraint. What is
worth spending the budget on instead is `--samples`, which buys the tail
convergence measured above. The extra rays cost only the shooting stage, not the
per-receiver stage: going from 1e6 to 4e6 adds about 47 s per scene-mast whatever
the receiver count, so at 245 samples it is a factor 1.7, not a factor 4.

**Recommended full run: `--every 2 --samples 4000000`, about 15 minutes.**

## What this does not settle

- **Every material is 10 cm thick.** The exporter uses Sionna's
  `DEFAULT_THICKNESS` for brick, marble, concrete and ground alike. A Ghent
  facade is 30 to 40 cm of brick, so buildings are more transparent here than in
  the city and refraction paths are over-represented in all three scenes. It
  shifts the level. Whether it shifts the hybrid-vs-baseline gap is untested.
- **Vegetation exists in only one scene, by construction.** The hybrid has 15
  canopy proxies, the photo mesh has real trees fused into the concrete skin, and
  OSM has none. The A/B above shows this is not what drives the numbers here, but
  geometry and semantics are not cleanly separated by this design.
- **Two of the six masts are not traced.** The 8.55 m and 5.5 m micro sites are
  the two with the lowest registered power. At 4 to 17 s per scene-mast they are
  cheap to add if the street-level sites turn out to matter.
- **Tilt and frequency are assumptions**, and both move every absolute number.
  Only the differences between scenes are claims here.
- **The transmitter is cleared above the photogrammetry roof**, so the photo mesh
  is implicitly treated as the authority on where the mast stands. That is the
  same assumption the hybrid makes about roof heights, which is a mild
  circularity in the hybrid's favour at exactly the two masts where OSM differs
  most.
