# Photographs only change the answer near where they were taken

**Using photographs to set facade materials, instead of guessing them from which way a
wall faces, raises the rooftop exposure by 0.16 to 0.50 dB at spots within 20 m of a
photograph. Past 40 to 60 m it changes almost nothing, under 0.01 dB. The paper
currently reports about 0.1 dB, which is the average of those two, and how big that
average comes out depends on how close the photographs happened to be taken.**

No new tracing was done. These are the same runs the coverage ladder already used, read
one standpoint at a time instead of one square at a time.

Numbers at `outputs/station_calibration/material_reach_250m.json`.

## Why this needed measuring

`STATION_CALIBRATION.md` ran the exposure at the spots where the panoramas were taken. The
material change came out much bigger there than over the whole walk: +1.101 dB against
+0.115 dB at Korenmarkt, nine times larger. Two things could cause that, and they lead
to opposite sentences in the paper.

1. The photographs are better there, so averaging over the whole walk hides a real
   effect.
2. Those spots are simply in different places. Panoramas are taken from the street, and
   at Korenmarkt the streets are the narrow approaches. In a narrow street more of the
   arriving power bounces off a wall right next to you, so materials matter more there
   for reasons that have nothing to do with photographs.

The second is not made up. Split Korenmarkt's walk by how far each spot is from the
nearest panorama, and the near half has a median exposure of 0.1297 against 0.2178 for
the far half, with sky fraction 0.197 against 0.261. The near half really is more
hemmed in.

The station run cannot tell these apart, because it changed three things at once: which
spots, what height, and whether photographs were available.

## What was done

Keep the walk. Same 80 spots per square, same head height, four seeds, 320 paired rows.
Sort them by how far each spot is from the nearest panorama. **Only the availability of
photographs changes across the bins.** Where the spots are and how high they sit stay
the same.

Each number below is the median, over spots, of the change in decibels at that spot when
photographs replace the facing-direction guess. That is the same way the paper reduces
this comparison.

## The change shrinks with distance from a panorama

Rooftop illumination, median dB. Bins holding fewer than eight rows are left blank.

| square | 0-10 m | 10-20 | 20-30 | 30-40 | 40-60 | 60-80 | 80-120 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Korenmarkt | +0.580 | +0.334 | +0.160 | +0.142 | +0.086 | **+0.001** | +0.000 |
| Brussels Grand Place | +0.288 | +0.554 | +0.066 | +0.005 | +0.011 | **+0.000** | -- |
| Mexico Zocalo | +0.489 | +0.396 | +0.206 | +0.023 | +0.040 | **+0.010** | -- |
| Madrid Plaza Mayor | +0.290 | +0.289 | +0.304 | +0.402 | **+0.001** | -0.005 | -0.002 |
| Prague Staromestske | +0.159 | +0.161 | +0.170 | +0.206 | **+0.001** | -- | -- |
| Milan Duomo | -- | +0.144 | +0.157 | +0.196 | +0.224 | +0.134 | +0.032 |
| Tokyo Hachiko | -0.089 | -0.122 | -0.001 | +0.140 | -0.139 | -0.078 | -0.113 |

Five squares drop to within 0.01 dB of zero and stay there. Korenmarkt, Brussels and
Mexico get there by 60 to 80 m, Madrid and Prague by 40 to 60 m. Two squares do not
follow, and neither of them argues against the pattern. They are covered below.

How well each of those five is measured differs, and the difference matters. The four
seeds pick different spots, not just different random rays, so 320 rows cover more
places than the 80 of any one seed. Korenmarkt's four seeds draw from a shared list of
800 candidate spots and together cover 229 of them, with only 8 in common. So the bins
hold real places rather than repeats. But not evenly: Korenmarkt's 60 to 80 m bin holds
46 separate spots and Brussels' holds 30, while Mexico's holds 8 and Prague's 40 to 60 m
bin holds 7. **Korenmarkt and Brussels carry this result. Mexico, Madrid and Prague
agree with it but on few spots.**

This also matches something already measured a different way. `BOUNCE_BUDGET.md` counts
how often the first bounce lands on a wall some panorama actually saw, and finds it near
total within ten metres of a panorama and near zero past forty. That was counted on
rays. This is measured on the exposure itself. Both give the same distance.

## The same thing, split in two halves

Splitting each square at its own median distance instead of using bins.

| square | split at | near half | far half | difference |
| --- | --- | --- | --- | --- |
| Korenmarkt | 47.0 m | +0.387 | +0.004 | +0.383 |
| Brussels | 17.4 m | +0.379 | +0.008 | +0.371 |
| Mexico | 40.0 m | +0.352 | +0.035 | +0.317 |
| Milan | 56.3 m | +0.182 | +0.115 | +0.067 |
| Madrid | 18.9 m | +0.286 | +0.270 | +0.016 |
| Tokyo | 31.6 m | -0.049 | -0.061 | +0.012 |
| Prague | 15.0 m | +0.163 | +0.164 | -0.001 |

This split is the weaker way to look at it, and the split distances show why. Prague
splits at 15.0 m and Madrid at 18.9 m, so both of their halves sit close to a panorama
and neither half can show a contrast, even though the binned table above shows both
squares dropping off sharply at 40 m. The split only separates the two cases when
enough of the walk lies far out. **Read the bins, not the split.**

The other two illumination models behave the same way. Korenmarkt's isotropic far half
is -0.0001 dB, which is zero to four decimal places.

| square | isotropic near / far | rooftop near / far | street near / far |
| --- | --- | --- | --- |
| Korenmarkt | +0.275 / **-0.000** | +0.387 / +0.004 | +0.329 / +0.010 |
| Brussels | +0.243 / +0.001 | +0.379 / +0.008 | +0.349 / +0.004 |
| Mexico | +0.187 / +0.024 | +0.352 / +0.035 | +0.493 / +0.045 |

## How close the photographs are, square by square

| square | panoramas | spots within 20 m | within 40 m | change inside 20 m |
| --- | --- | --- | --- | --- |
| Prague | 12 | 75.0 % | 97.2 % | +0.160 |
| Madrid | 6 | 54.4 % | 85.3 % | +0.290 |
| Brussels | 8 | 54.4 % | 76.6 % | +0.401 |
| Tokyo | 3 | 28.1 % | 61.3 % | -0.113 |
| Korenmarkt | 9 | 26.9 % | 42.5 % | +0.504 |
| Mexico | 12 | 26.2 % | 50.0 % | +0.461 |
| Milan | 1 | 6.6 % | 25.3 % | +0.144 |

This is what sets each square's published number, and it varies by a factor of four.
Korenmarkt has the largest change of any square close in, and one of the fewest spots
close in. That is why its published number looks like nothing is happening.

## Two squares that do not follow

**Milan** has one usable panorama, so "distance to the nearest panorama" is just
distance from a single point. Its bins measure how far you are from that one spot, not
how well photographed you are. Its numbers rise out to 40-60 m and then fall, which one
camera can produce for reasons unrelated to photographs. Milan says nothing either way.

**Tokyo** is negative everywhere and its bins do not line up in any order. It has three
usable poses out of fourteen registered, and it is the one square that comes out
negative in every version of this comparison. Its negative is not caused by distance,
and this document does not explain it.

## What this does not show

Part of why the far bins sit near zero is bookkeeping rather than physics, and it would
be wrong to hide that. At a spot far from every panorama, most first bounces land on
walls no photograph covered. There the two runs use the same facing-direction guess, so
they mostly agree and the difference has to come out small. The far bins are not exactly
zero (+0.001, +0.000, +0.010) because even a distant spot sends some rays onto a wall a
photograph did cover.

So the honest statement is about how far the photographs reach, not about materials
mattering less far away. Materials matter just as much out there. The photographs simply
do not get that far, and the measurement follows the photographs.

That is still worth having, because nobody had put a distance on it, and shooting rays
from the same point the photograph was taken from predicts exactly this.

## What the paper should say

The material section now reports one median and reads as though nothing happened. The
spots behind that median mix places where photographs cover the walls with places where
they do not, so the median says as much about where the walk went as about materials.

Suggested replacement, every number from the tables above:

> Setting facade materials from photographs, rather than from which way each wall faces,
> raises the rooftop exposure by 0.16 to 0.50 dB at standpoints within 20 m of a
> panorama, and by under 0.01 dB past 40 to 60 m. The median over a square therefore
> depends on how many of its standpoints lie near a panorama, which runs from 25 to 97
> percent within 40 m.

Two squares support that on many spots and three agree on few, so the count should be
written down rather than left implied.

This also replaces the coverage caveat as it stands. Saying that 3 to 10 percent of the
crop's triangle area carries photographic evidence measures how wide the crop was cut,
not how good the evidence is. Cut the crop twice as wide and that number halves while
nothing physical changes. What sets the published median is how many standpoints sit
near a panorama.

## Where the numbers came from, and one mistake found along the way

Everything recomputed from
`outputs/exposure_korenmarkt/ladder250_<site>_s<seed>_{geometric,walk}_15ghz_locations.jsonl`,
four seeds each, matched standpoint by standpoint. Panorama positions from
`outputs/site_semantics/<site>/walk_semantic_250m.json`, field `stations_admitted`.
Nothing was re-traced.

The first version of this analysis pulled the seed number out of the filename by
splitting on `_s`. That matches the `_s` inside `prague_staromestske` before it ever
reaches the seed, so Prague's four seeds collapsed onto one another and left 217 rows
instead of 320. I then wrote an explanation for the missing rows that was simply made
up. The other six squares have no `_s` in their names and were fine. The filename is now
read with a pattern anchored on the run name, and every square checks that it found a
seed. Prague's corrected bins are what took this from three squares showing the drop-off
to five.
