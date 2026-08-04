# Is skyline registration ill conditioned in a street

The worry was reasonable. A long straight street has a roofline that looks much
the same from anywhere along it, so sliding the camera up the street should barely
change the skyline and the fit should not be able to tell where it is. If that
were true, every street pose would carry a large hidden error along the street and
nothing in the reported residual would say so.

It is not true. Both ways of measuring say the along street direction is the
**tight** one, not the loose one.

## How it was measured

Take a registered pose. Move the camera a fixed distance in one horizontal
direction, then re-minimise altitude, yaw, pitch and roll from there, so the
number is what the fit can still achieve after being displaced rather than the
cost of a naive shift. Repeat out to plus and minus 4 m along the street and
across it. The half width of that valley at 0.10 degrees above the minimum is how
well the fit pins the camera in that direction.

The reconstruction is checked against what shipped: it reproduces each pose's
recorded residual to within 0.09 degrees for street poses and 0.21 for open ones.

Poses are classified by ray cast chord width, elongation and sky escape, giving
20 open, 13 mixed, 25 street and 25 roofed out of 83. The valley study ran the 13
street and 19 open poses that pass the admission gate. The 8 remaining mixed poses
were not run and no conclusion here needs them.

## What it found

| class | n | along | across | wider of the two | residual |
|---|---|---|---|---|---|
| street | 13 | 0.30 m | 0.40 m | 0.40 m | 2.19 deg |
| open | 19 | 0.70 m | 0.70 m | 0.80 m | 0.80 deg |

Street against open on the wider half width, Mann-Whitney p = 0.0038.

The seed ensemble already on disk measures the same thing a different way, from
the spread of repeat fits from different starting points. Restricted to the same
gate-passing poses:

| class | n | sigma along | sigma across |
|---|---|---|---|
| street | 13 | 0.127 m | 0.347 m |
| open | 19 | 0.151 m | 0.202 m |

**Read those two tables carefully, because they agree on one thing and not on
another.**

They agree on the question that was asked. Along the street is never the loose
direction. The valley puts street along at 0.30 against across at 0.40, and the
ensemble puts it at 0.127 against 0.347, a factor of nearly three the other way
from the degeneracy. Whatever else is true, the fit is not sliding up the street.

They do not agree that street poses are better located than open ones overall.
The valley says they are, at p = 0.0038. The ensemble does not: comparing the
larger of the two sigmas gives 0.347 for street against 0.210 for open, p = 0.49,
which is no effect. So treat "streets are twice as well located" as one
measurement rather than two, and the refutation of the degeneracy as two.

## Why the degeneracy is absent

The synthetic control shows it is a real effect that simply does not survive
contact with a city. On an ideal infinite street with a flat roofline the along
street sensitivity is exactly 0.0000 deg/m, so the estimator would have caught the
degeneracy had it been there. Break that roofline into 12 m houses and the
anisotropy is already down to 3.4 to 1. On the real photogrammetric meshes it is
gone: the horizontal problem is about 1.4 to 1 anisotropic everywhere, and no real
roofline is flat.

The mechanism is distance. Street facades are 8 to 20 m away where open square
facades are 40 to 60. Moving 1 m along a street sweeps a facade 8 m away through
about 7 degrees of azimuth, and a photogrammetric roofline is not smooth at that
scale, so the fit has plenty to hold on to.

## What does fail

Pooled residuals do look worse in streets, 2.19 against 0.80 degrees, and that is
the observation the worry started from. It is a site effect, not a street effect.
After removing each site's own median, no measure of openness correlates with the
residual at all, Spearman -0.03 at p = 0.85. Nine of the 25 street poses are
Korenmarkt Mapillary captures and nine more are Times Square.

**Roofed poses are the real failure mode.** 25 of 83 poses have essentially no sky
escape, and **7 of them pass the admission gate**. Their first bounce coverage
median is 0.9485 and falls to 0.696, where street poses are the best of the usable
classes at 0.9993. All five Zocalo stations that `BOUNCE_BUDGET.md` reports below
0.96 are roofed poses, which is a simpler explanation than the ray grid one that
document gives.

`SKYLINE_FUNCTION.md` reaches the same place from the other side. The Madrid
standpoint with the lowest registration residual in the whole study, 0.176
degrees, sits under a ceiling 25 m up in every one of 360 azimuths. It has no
skyline and the residual cannot see that.

If another admission gate is wanted, gate on sky escape. Do not gate on street
width, which carries no signal: Spearman +0.03 against chord width at p = 0.87.

## Data

`outputs/street_conditioning/` holds the pose classification, the openness
measures, the seed ensemble and the valley run log. The tables above are
recomputed from `valley.log` and `ensemble.csv` rather than quoted, because
`valley.json` holds only the first pose of the run.

One loose end recorded and not chased: under the station join used here, two rows
of the Korenmarkt 130 m table in `BOUNCE_BUDGET.md` appear swapped. Six of eight
rows agree exactly and it changes no conclusion there.
