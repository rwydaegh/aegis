# The material effect has a radius of about 40 m, and the published median averages across it

**Image derived facade materials shift the rooftop exposure median by 0.16 to 0.50 dB
at standpoints within 20 m of a registered panorama, and the shift falls to within
0.01 dB of zero past 40 to 60 m at five of the seven squares that can be measured. The
published walk median of roughly 0.1 dB is not a small effect. It is the average of a
real one and a region where the method has almost no evidence to apply.**

Nothing here is a new run of the estimator. These are the same `ladder250_*` rungs the
coverage ladder already reported, read per standpoint instead of per square.

Data at `outputs/station_calibration/material_reach_250m.json`.

## Why this measurement was needed

`STATION_CALIBRATION` found the material shift at the panorama standpoints themselves
much larger than over the walk: Korenmarkt +1.101 dB against +0.115 dB, a factor of
9.6. Two explanations fit, and they lead to opposite sentences in the paper.

1. The evidence is better at the stations, so the walk dilutes a real effect.
2. The stations sit in different geometry. They stand on the street network, which at
   Korenmarkt means the narrow approaches, where more of the arriving power comes off
   nearby facades and material matters more for reasons unrelated to photographs.

The second is not hypothetical. Splitting Korenmarkt's walk by distance to the nearest
station gives a median $\chi_{\mathrm{rooftop}}$ of 0.1297 near against 0.2178 far,
with sky fraction 0.197 against 0.261. The station neighbourhood is measurably more
enclosed than the rest of the square.

The station comparison cannot separate the two, because it changes the standpoint
population, the head height and the evidence availability at once.

## The test

One population, one head height, one pose convention. The 80 walk standpoints per
square at the published operating point, four seeds, 320 paired rows each. Binned by
distance to the nearest admitted station. **Only evidence availability varies.**
Geometry, height and standpoint selection are held.

The reduction is the median of the paired per standpoint decibel difference, walk rung
against geometric rung, which is the convention `paper/paper.tex` uses.

## Result: the shift decays with distance from a camera

Rooftop illumination, median dB per distance bin. Bins with fewer than eight paired
rows are left blank rather than plotted.

| square | 0-10 m | 10-20 | 20-30 | 30-40 | 40-60 | 60-80 | 80-120 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Korenmarkt | +0.580 | +0.334 | +0.160 | +0.142 | +0.086 | **+0.001** | +0.000 |
| Brussels Grand Place | +0.288 | +0.554 | +0.066 | +0.005 | +0.011 | **+0.000** | -- |
| Mexico Zocalo | +0.489 | +0.396 | +0.206 | +0.023 | +0.040 | **+0.010** | -- |
| Madrid Plaza Mayor | +0.290 | +0.289 | +0.304 | +0.402 | **+0.001** | -0.005 | -0.002 |
| Prague Staromestske | +0.159 | +0.161 | +0.170 | +0.206 | **+0.001** | -- | -- |
| Milan Duomo | -- | +0.144 | +0.157 | +0.196 | +0.224 | +0.134 | +0.032 |
| Tokyo Hachiko | -0.089 | -0.122 | -0.001 | +0.140 | -0.139 | -0.078 | -0.113 |

Five squares fall to within 0.01 dB of zero and stay there. Korenmarkt, Brussels and
Mexico cross by 60 to 80 m, Madrid and Prague by 40 to 60 m. The two that do not are
discussed below and neither is evidence against the pattern.

The four seeds redraw the standpoint subset rather than only the ray streams, so the
320 rows per square span more distinct locations than the 80 of any single seed.
Korenmarkt's four seeds draw from a shared 800 candidate walk and their union is 229
distinct standpoints with an intersection of 8. The crossing bins therefore rest on
real locations rather than replicates, but not equally: Korenmarkt's 60 to 80 m bin
holds 46 distinct standpoints and Brussels' holds 30, while Mexico's holds 8 and
Prague's 40 to 60 m bin holds 7. **Korenmarkt and Brussels carry this result. Mexico,
Madrid and Prague are consistent with it on thin tails.**

**This independently reproduces a number already on record.** `BOUNCE_BUDGET.md`
measures first interaction evidence coverage decaying from essentially total inside ten
metres of a station to essentially none past forty. That was measured on ray counts
against the binding mask. This is measured on the exposure ratio itself, through a
different quantity and a different reduction, and it decays on the same scale.

## The same thing as a near and far split

Splitting at each square's median station distance rather than binning.

| square | split radius | near half | far half | difference |
| --- | --- | --- | --- | --- |
| Korenmarkt | 47.0 m | +0.387 | +0.004 | +0.383 |
| Brussels | 17.4 m | +0.379 | +0.008 | +0.371 |
| Mexico | 40.0 m | +0.352 | +0.035 | +0.317 |
| Milan | 56.3 m | +0.182 | +0.115 | +0.067 |
| Madrid | 18.9 m | +0.286 | +0.270 | +0.016 |
| Tokyo | 31.6 m | -0.049 | -0.061 | +0.012 |
| Prague | 15.0 m | +0.163 | +0.164 | -0.001 |

The split is the weaker diagnostic and the reason is visible in the radii. Prague
splits at 15.0 m and Madrid at 18.9 m, so both halves sit inside the reach and no
contrast can appear even though the binned table shows both squares cutting off
sharply at 40 m. The split only separates where enough of the walk lies beyond the
reach. **Read the bins, not the split.**

The other two illumination models agree in shape. The isotropic far half at Korenmarkt
is -0.0001 dB, a null to four decimal places.

| square | isotropic near / far | rooftop near / far | street near / far |
| --- | --- | --- | --- |
| Korenmarkt | +0.275 / **-0.000** | +0.387 / +0.004 | +0.329 / +0.010 |
| Brussels | +0.243 / +0.001 | +0.379 / +0.008 | +0.349 / +0.004 |
| Mexico | +0.187 / +0.024 | +0.352 / +0.035 | +0.493 / +0.045 |

## How much of each walk sits inside the reach

| square | stations | within 20 m | within 40 m | shift inside 20 m |
| --- | --- | --- | --- | --- |
| Prague | 12 | 75.0 % | 97.2 % | +0.160 |
| Madrid | 6 | 54.4 % | 85.3 % | +0.290 |
| Brussels | 8 | 54.4 % | 76.6 % | +0.401 |
| Tokyo | 3 | 28.1 % | 61.3 % | -0.113 |
| Mexico | 12 | 26.2 % | 50.0 % | +0.461 |
| Korenmarkt | 9 | 26.9 % | 42.5 % | +0.504 |
| Milan | 1 | 6.6 % | 25.3 % | +0.144 |

This is the number that sets each square's published median, and it ranges over a
factor of four. Korenmarkt has the largest inside-reach shift in the set and one of
the smallest covered walks, which is exactly why its published median reads as a null.

## Two squares that do not fit

**Milan** has one admitted station, so distance to the nearest station is distance
from a single point and the bins measure radius from that point rather than camera
proximity. Its profile rises to 40-60 m before falling, which a one camera geometry can
produce for reasons unrelated to evidence. Milan is not evidence either way.

**Tokyo** is negative throughout and its bins do not order. It has three admitted poses
of fourteen registered, and it is the one square whose material shift is negative in
the walk, the station and the binned populations alike. Its negative is not a reach
artefact and it is not explained here.

## What this does not show

The far tail is close to zero partly for a mechanical reason, and presenting it as
purely physical would be wrong. A standpoint far from every camera has most of its
first interactions on unbound triangles, where the walk rung and the geometric rung
assign the same orientation rule material, so the two rungs largely coincide and the
difference has to be small. The tail is not identically zero (+0.001, +0.000, +0.010)
because a distant standpoint still shoots some rays that reach a bound facade.

So the honest statement is about the reach of the instrument, not about material
importance decaying with distance. Material importance does not decay. The evidence
does, and the measurement follows the evidence.

That is still the useful result, because reach is the property nobody had quantified
and the co-located transmitter and receiver argument predicts it directly.

## What the paper should say

The current material subsection reports a distribution median shift and reads as a
null. The population behind that median mixes standpoints where the method has
evidence with standpoints where it has almost none, so the median is a property of the
walk layout as much as of the materials.

Replacement claim, every number from the tables above:

> Image derived facade materials shift the rooftop exposure median by 0.16 to 0.50 dB
> at standpoints within 20 m of a registered panorama, and by under 0.01 dB past 40 to
> 60 m. The population median therefore depends on how much of a square's walk lies
> within camera reach, which ranges from 25 to 97 percent of standpoints within 40 m.

Two squares carry that claim on well sampled tails and three are consistent with it on
thin ones, so the number of squares should be stated rather than implied.

This also retires the coverage caveat in its current form. Quoting the fraction of the
crop's triangle area carrying image evidence, 3 to 10 percent, measures the crop radius
rather than the evidence, and doubling the crop would halve it while changing no
physics. The fraction of the walk inside camera reach is the number that sets the
published median.

## Provenance and one defect found while writing this

Every number recomputed from
`outputs/exposure_korenmarkt/ladder250_<site>_s<seed>_{geometric,walk}_15ghz_locations.jsonl`,
four seeds each, paired by standpoint index. Station positions from
`outputs/site_semantics/<site>/walk_semantic_250m.json`, field `stations_admitted`. No
estimator was re-run.

The first version of this analysis parsed the seed out of the filename by splitting on
`_s`, which matches the `_s` inside `prague_staromestske` before it reaches the seed
token. Prague's four seeds therefore collapsed into one key and overwrote each other,
giving 217 paired rows instead of 320 and a near to far difference of +0.019 instead of
-0.001. The other six squares carry no `_s` in their names and were unaffected. The
parser is now a regular expression anchored on the rung name, and every site asserts
its seed was found. Prague's corrected bins are what promoted this result from three
squares showing the reach to five.
