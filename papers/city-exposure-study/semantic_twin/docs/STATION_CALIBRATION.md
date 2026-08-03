# Running the exposure where the camera stood

**At the exact spots where the panoramas were taken, using photographs to set facade
materials raises the rooftop exposure by +0.12 to +1.10 dB at six squares and lowers it
by 0.12 dB at the seventh. Over the whole walk of the same square the same change runs
-0.06 to +0.28 dB. The camera spots give the larger number at four of seven squares, up
to nine times larger at Korenmarkt, the same at one, and a slightly smaller one at two.**

This does not by itself mean the photographs are doing more work there. The camera spots
are also different places, at a different height. `MATERIAL_REACH.md` separates those two
causes and is the document to read for the answer. This one records what was run and what
came out.

Numbers at `outputs/station_calibration/station_calibration_cross_site_250m.json`. Seven
squares, 250 m crop, 15 GHz, seeds 7, 8, 9 and 10.

## Why run at the camera spots at all

The whole method rests on one idea: put the transmitter and the receiver at the same
point, and the photograph taken from that point sees the surfaces the first bounce hits.
That is exact only if you stand where the camera stood.

The measurement agrees. At the camera spots, the share of first-bounce power landing on a
wall some photograph covered is 0.988 to 0.9995, taking each square's median camera. Over
the published walk the same share is 0.37 to 0.77, at the four squares where it was
counted. So the camera spots are the best case the method ever gets, and running there
asks how much the material choice can possibly matter.

## What came out

Rooftop illumination. Each number is the median, over spots, of the decibel change at
that spot when photographs replace the facing-direction guess. Plus or minus is the
standard error over the four seeds.

| square | cameras | at the cameras | over the walk | ratio |
| --- | --- | --- | --- | --- |
| Korenmarkt | 9 | +1.101 ± 0.004 | +0.115 ± 0.010 | 9.5 |
| Brussels Grand Place | 8 | +0.342 ± 0.002 | +0.107 ± 0.014 | 3.2 |
| Mexico Zocalo | 12 | +0.246 ± 0.007 | +0.096 ± 0.004 | 2.6 |
| Tokyo Hachiko | 3 | -0.119 ± 0.007 | -0.056 ± 0.008 | 2.1 |
| Madrid Plaza Mayor | 6 | +0.286 ± 0.010 | +0.284 ± 0.001 | 1.0 |
| Prague Staromestske | 12 | +0.128 ± 0.003 | +0.162 ± 0.002 | 0.8 |
| Milan Duomo | 1 | +0.120 ± 0.003 | +0.162 ± 0.001 | 0.7 |

The error bars are not the same kind of thing on the two sides. At the cameras the set of
spots is fixed by where the panoramas are, so a new seed only redraws the random rays. On
the walk a new seed redraws the spots too, so the walk bar carries the larger term. Do
not compare the two bars.

All three illumination models, at the cameras against over the walk:

| square | isotropic | rooftop | street cell |
| --- | --- | --- | --- |
| Korenmarkt | +1.836 / +0.022 | +1.101 / +0.115 | +0.877 / +0.115 |
| Brussels | +0.131 / +0.041 | +0.342 / +0.107 | +0.297 / +0.095 |
| Mexico | +0.242 / +0.047 | +0.246 / +0.096 | +0.219 / +0.134 |
| Madrid | +0.168 / +0.171 | +0.286 / +0.284 | +0.461 / +0.413 |
| Prague | +0.083 / +0.123 | +0.128 / +0.162 | +0.100 / +0.130 |
| Milan | +0.136 / +0.129 | +0.120 / +0.162 | +0.013 / +0.122 |
| Tokyo | +0.001 / -0.045 | -0.119 / -0.056 | -0.387 / -0.244 |

Korenmarkt's isotropic +1.836 dB is the largest single number anywhere in this study, and
it comes from nine spots.

## Two things changed at once, not one

Moving to the camera spots changes three things together: which spots, how high the head
sits, and whether photographs are available. Only the third is what the paper wants to
talk about.

The height part can be tested directly, because the run was done twice. Once with the
head at the camera's own height, once with the head at a fixed pedestrian height at the
same ground positions.

| square | camera height | fixed height | camera height above local ground, min / median / max |
| --- | --- | --- | --- |
| Korenmarkt | +1.101 | +1.093 | +0.89 / +1.59 / +3.70 m |
| Brussels | +0.342 | +0.307 | +0.35 / +1.38 / +1.76 m |
| Madrid | +0.286 | +0.274 | -16.06 / +1.56 / +1.93 m |
| Prague | +0.128 | +0.156 | +0.92 / +1.87 / +3.02 m |
| Milan | +0.120 | +0.129 | +2.17 / +2.17 / +2.17 m |
| Tokyo | -0.119 | -0.104 | +1.11 / +2.03 / +2.15 m |
| Mexico | +0.246 | +0.116 | -5.78 / -0.38 / +4.81 m |

Height barely matters at six squares. It halves the number at Mexico, and Mexico is also
the one square whose cameras are placed badly: half its cameras sit below the local
ground, one of them by 5.8 m. Madrid has one camera 16 m below ground, which is plainly a
registration failure and not a real position. **Mexico's row should not be quoted without
saying its cameras are misplaced.** Madrid survives because its median camera is fine and
the median is what gets reported.

The "which spots" part is the bigger worry and this run cannot settle it. Panoramas are
taken from streets. At Korenmarkt the streets are the narrow approaches, and a narrow
street reflects more power off the wall next to you no matter what material you assign.
That is measurable: Korenmarkt's near half of the walk has a sky fraction of 0.197
against 0.261 for the far half. `MATERIAL_REACH.md` removes this by keeping one walk and
one head height and sorting the spots by distance to the nearest panorama, so only the
availability of photographs varies. The answer there is that the effect is real but has a
range of about 40 m.

## The two routes through the photographs do not agree

There are two independent ways to turn a panorama into materials. One fuses the views
into a single surface set ("the walk rung", `walk_semantic.npz`). The other keeps each
view separate and cuts it into faces ("the semantic rung", the fishnet). Both were run at
the camera spots.

| square | walk route, cameras | fishnet route, cameras | walk route, walk | fishnet route, walk |
| --- | --- | --- | --- | --- |
| Brussels | +0.342 | +1.115 | +0.107 | +0.186 |
| Madrid | +0.286 | +0.273 | +0.284 | +0.289 |
| Mexico | +0.246 | +0.171 | +0.096 | +0.054 |
| Prague | +0.128 | +0.154 | +0.162 | +0.171 |
| Milan | +0.120 | +0.107 | +0.162 | +0.104 |
| Korenmarkt | +1.101 | +0.067 | +0.115 | +0.001 |

Both routes agree on the direction and both show the cameras giving more than the walk.
They do not agree on size, and at the two extremes they disagree badly. Korenmarkt is
+1.101 one way and +0.067 the other, sixteen times apart. Brussels goes the other way,
+0.342 against +1.115. **Whichever square looks largest depends on which route you pick,
so no single square should be called the strongest case.** Four of the six squares agree
within a factor of 1.5 and those four are the trustworthy part of this table.

Tokyo has no fishnet run.

## Per-camera spread

The square median hides a wide spread across individual cameras.

| square | lowest camera | median | highest camera |
| --- | --- | --- | --- |
| Korenmarkt | +0.399 | +1.101 | +1.498 |
| Brussels | +0.054 | +0.342 | +1.163 |
| Mexico | +0.041 | +0.236 | +1.752 |
| Madrid | +0.256 | +0.299 | +0.656 |
| Prague | +0.075 | +0.128 | +0.206 |
| Tokyo | -0.271 | -0.119 | -0.071 |

Prague is tight, a factor of under three from lowest to highest. Mexico spans a factor of
43. Prague also has the most cameras and the highest share of covered facade area, 9.9%.

## Coverage by area is the wrong number to quote

Each row of the JSON also carries `covered_fraction_by_area`, the share of the crop's
triangle area whose material came from an image. It runs 3.2% to 9.9%. That number mostly
measures how wide the crop was cut, not how good the evidence is. Cut the crop twice as
wide and it halves while nothing physical changes. Korenmarkt at 250 m gives 3.2%, and
the same square at 130 m gives 10.6%, while the share of first-bounce power on
photographed walls barely moves, 58.4% to 55.2%.

Quote the power share, not the area share.

## What this supports and what it does not

Supports: the change from photographs is larger where the photographs were taken than it
is over a whole square, at four of seven squares, and at Korenmarkt by nine times. The
seed bars at the camera spots are small, 0.002 to 0.010 dB, so this is not ray noise.

Does not support, on its own: that the difference is caused by the photographs. Three
things changed at once. `MATERIAL_REACH.md` is where that gets separated.

Does not support: any claim that names one square as the best case. The two image routes
put a different square on top.

## What was run

Seven squares at a 250 m crop, 15 GHz, 3 interactions, roulette off, 200,000 rays, seeds
7, 8, 9 and 10. The baseline is the geometric rung, materials from which way each wall
faces. Cameras come from `stations_admitted` in
`outputs/site_semantics/<site>/walk_semantic_250m.json`, filtered to a sky fraction above
0.01 so a camera buried inside geometry is dropped. Each square was run twice, once with
the head at the camera's own height and once at a fixed pedestrian height.

Both reductions are stored. `paired_median_shift_db` is the median over spots of the
per-spot decibel difference, which is what `paper.tex` uses and what every number above
is. `distribution_median_shift_db` is the decibel ratio of the two medians, which is what
`COVERAGE_LADDER.md` headlines. They disagree by up to five times and flip Tokyo's sign,
so a number lifted from one document into the other will be wrong.
