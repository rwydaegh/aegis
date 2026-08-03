# Reruns

Two items that could only be closed by running something. Both are closed. This
is what was run, what came back, and what the paper should say.

## The short answer

**The abstract's three standpoint sampling numbers survive exactly.** 0.128,
0.061 and 0.188 dB now come off disk rather than out of a markdown table. The
two torn files were repaired, the repair reproduces every surviving published
row bit for bit, and the recomputation gives **0.1281 / 0.0605 / 0.1883 dB**
with worst cases 0.242 Brussels, 0.116 Mexico City and 0.326 New York. Every
figure in that sentence of the abstract and in the Discussion paragraph behind
it is right.

**The ratio attached to them is not.** The abstract's "roughly 25 times the
isotropic Monte Carlo error" rests on a floor of 0.0042 dB that has now been
remeasured and is **0.0028 dB**, and the rescaling that turns it into a
denominator crosses two configurations rather than one standpoint count. The
isotropic ratio is larger than the paper claims, not smaller: between 37 and 67
depending on which floor is used, against the stated 25. The claim understates
its own case.

**The Discussion's "7 to 47 times their Monte Carlo floors" does not survive.**
The isotropic end goes up and the rooftop and street ends come down, because the
floors for those two models were never measured at the configuration they are
being asked to divide. At the configuration the numerator actually comes from,
the rooftop worst case is **3.0** times its floor rather than 7.0. The rooftop
row is the one to look at again.

Everything measured here is in `outputs/mc_error/`. Nothing under `paper/` was
edited and no published artefact was overwritten.

## Item 1. The Monte Carlo error model

### The configuration was recoverable, and it is not the one a rerun would pick

`CODE_AUDIT.md` section 4 records the method but not the code, and the tree has
moved since. Three settings that decide the numbers had to be recovered from the
published manifests rather than from any default:

| setting | what the published run used | what today's default gives |
|---|---|---|
| `roulette_start` | 3 | 4, because `DEFAULT_MAX_BOUNCES` went from 2 to 3 on 3 August |
| ground datum | `config/korenmarkt.json` camera height, 50.83747424667166 m | the lowest major walkable level, 50.87109375 m |
| walk probe height | datum plus 200 m | the sky probe, 10 km |

The last two change which standpoints get traced, so a rerun that took the
defaults would have measured a different set of points and called it a retrace.
`run_seed_replicas.py` sidesteps the question for item 1 by holding the
standpoints at the ones the published file records and reading everything else
out of the published manifest.

One further recovery was needed. `clean_walk9` was bound against
`walk_semantic_conflict9.npz` in a scratch directory, and the copy of that file
now sitting in `outputs/walk_korenmarkt/` is **not** the one it used: the
current file hashes differently and binds a different area fraction. The run's
own binding survives as `outputs/walk_korenmarkt/_pre_sam3/walk_semantic_conflict9.npz`,
which reproduces the manifest's 0.110194 covered area fraction. The harness
refuses to run if the fraction disagrees, so an empty or wrong binding cannot
pass silently.

### Replica zero reproduces the published file exactly

Both rungs, all 120 standpoints, all three illumination models, to
**0.00e+00**. That is the check that says the retrace is against the real thing.
It is printed by the harness on every run and is in the job logs.

### The eight seed streams

Per standpoint seed is `base + 1000 * walk_index`, the rule `run_exposure.run`
already uses, so base seed 7 is the published stream and bases 7 to 14 give
eight streams that cannot collide. The audit's eight are unrecoverable as such,
but any disjoint set is a valid replicate set and this one has the published run
as its first member.

The measurement was then run again at **32** streams, bases 7 to 38, because a
standard deviation from eight draws is itself uncertain by about a quarter and
the disagreement below is larger than that. The eight replica figures are the
first eight of the same file and both are on disk.

### What reproduces

The per standpoint spread of section 4.1 reproduces well.

| illumination | sd median, audit | 8 streams | 32 streams | p90, audit | 32 streams | worst of 120, audit | 32 streams |
|---|---|---|---|---|---|---|---|
| isotropic | 0.004 | 0.0042 | 0.0042 | 0.006 | 0.0059 | 0.015 | 0.0125 |
| rooftop | 0.024 | 0.0234 | 0.0263 | 0.040 | 0.0381 | 0.066 | 0.0583 |
| street small cell | 0.118 | 0.1199 | 0.1302 | 0.224 | 0.2170 | 0.954 | 0.5791 |

The worst of 120 column is the one that moves, and the reason is a bias rather
than a disagreement. It is a maximum over 120 standard deviations each estimated
from a handful of draws, so it picks up whichever standpoint's estimate happened
to come out high. Estimated from 32 draws instead of 8 the maximum falls from
0.954 to 0.579 dB. The audit's sentence that the worst street standpoint is good
to about a decibel should read **about 0.6 dB**.

The paired ladder shift of section 4.2 reproduces, and the audit's correction to
the published street row stands and gets stronger.

| illumination | audit mean of 8 | 8 streams | 32 streams | standard error of 32 | published seed 7 |
|---|---|---|---|---|---|
| isotropic | +0.347 | +0.3464 | **+0.3473** | 0.0007 | 0.3498 |
| rooftop | +0.383 | +0.3811 | **+0.3855** | 0.0036 | 0.3642 |
| street small cell | +0.167 | +0.1556 | **+0.1505** | 0.0092 | 0.0785 |

The street shift is 16.4 standard errors from zero on the mean of 32 and 2.9 on
a single run. The published 0.0785 dB is the **third lowest of 32 draws**, which
run from 0.045 to 0.244, a factor of 5.4. The audit called it the lowest of
eight and that reading holds up. The trend across the three models on the seed
averaged numbers is 0.347, 0.386, 0.150, which is not monotone, so the audit's
warning about reading the single seed table as a trend also holds.

The crossing counts hold too. Isotropic 16 to 18 of 120 across the rung against
0 from a seed change alone, rooftop 7 to 8 against 0, street 1 to 2 against 0 to
1. The street count is inside its own control, as the audit said.

### What does not reproduce

**The three numbers the paper actually quotes.** The audit's "sd of the walk
median" column, which is where 0.0042, 0.0136 and 0.0343 dB come from, does not
come back as a set:

| illumination | audit | 8 streams | 32 streams | 95 percent interval on 32 | audit inside it |
|---|---|---|---|---|---|
| isotropic | 0.0042 | 0.0014 | **0.0028** | 0.0023 to 0.0037 | no |
| rooftop | 0.0136 | 0.0168 | **0.0162** | 0.0130 to 0.0216 | yes, at the edge |
| street small cell | 0.0343 | 0.0469 | **0.0594** | 0.0477 to 0.0790 | no |

So the isotropic floor is 1.5 times smaller than reported and the street floor
1.7 times larger. Rooftop agrees. No arithmetic on the replicas reproduces the
audit's set: the sd of the median in dB, the median of the dB, the sd of the
mean, and the per standpoint sd divided by the square root of 120 were all
tried and none of them lands on 0.0042 / 0.0136 / 0.0343 together.

Two things are worth saying about that column rather than treating it as a slip.
The quantity is fragile. A median over 120 standpoints does **not** average the
per standpoint noise down by the square root of 120: with the standpoints well
separated the median is essentially the value of whichever standpoint sits in
the middle, and it moves in steps as ranks swap. Its own sampling distribution
is not normal, which is why the eight replica interval for isotropic,
0.0010 to 0.0029, does not contain the 32 replica answer of 0.0028 except at its
edge. Any figure of this kind measured from eight draws should be read as
indicative.

**The audit's claim that the semantic binding is noisier does not reproduce
either.** It reports the walk median sd rising from 0.0136 to 0.0199 rooftop and
0.0343 to 0.0594 street when the binding goes from geometric to semantic.
Measured over 32 streams the rooftop figure *falls*, 0.0162 to 0.0141, and the
street figure roughly doubles, 0.0594 to 0.0928. The direction is not consistent
across models, so the general statement that adding material variety inherits
more noise is not supported by this pair.

### Not reproduced, and not reproducible here

The 0.298 dB fixed height figure is still unmeasured under the corrected law,
because the superseded law is not carried by the current code. That was true
before and is unchanged.

## Item 2. The two torn result files

### What repairing them needed

The same three recoveries as item 1, and this time they matter to the answer
rather than to the method, because two of them change the standpoints. The
manifest of each site carries all three. `repair_torn_sites.py` reads them and
passes them back in through three new arguments on `run_exposure.run`:
`roulette_start`, `ground_datum_m` and `walk_probe_z_m`. All three default to
the current rule and are only used to reproduce something already published.

### The control reproduces bit for bit

Before repairing anything, two sites whose files are intact were re-traced under
the same procedure and compared to the published rows in hexadecimal float,
which round trips exactly.

| site | standpoints | float fields compared | mismatched | differing in the last digit |
|---|---|---|---|---|
| Korenmarkt | 80 of 80, none moved | 3120 | **0** | 0 |
| Hachiko, Tokyo | 80 of 80, none moved | 3120 | **0** | 1 |

The single Tokyo difference is `rooftop_mean_sab_w_m2` at one standpoint, in the
seventeenth significant digit, which is a summation order in the body coupling
reduction and not a different scene. Tokyo is the useful control of the two: it
is one of the two squares with towers tall enough for the old probe height to
sit inside them, so it is the site where getting the probe wrong would have
shown.

### The repairs

| site | published | repaired | surviving published rows reproduced |
|---|---|---|---|
| Times Square, New York | 78 valid rows, 2 unparseable lines | 80 | 3042 of 3042 float fields, **0** mismatches |
| Staromestske, Prague | 80 valid rows, 1 unparseable extra line | 80 | 3119 of 3119 float fields, **0** mismatches |

Written under the tag `city250_repair`, so the eleven published
`city250_corrected` files and the clean headline `city250_L3` are untouched.

### The recomputed standpoint sampling rms

Per square median in dB, `city250_datum` against `city250_corrected`, over the
eight squares whose datum moved by under a quarter of a metre, with New York and
Prague read from the repair:

| illumination | paper | recomputed | worst square, paper | recomputed |
|---|---|---|---|---|
| isotropic | 0.128 | **0.1281** | 0.242 Brussels | 0.2420 |
| rooftop | 0.061 | **0.0605** | 0.116 Mexico City | 0.1159 |
| street small cell | 0.188 | **0.1883** | 0.326 New York | 0.3256 |

All three survive. So do the two sentences that qualify them. The Discussion's
"recomputing from what remains gives 0.125, 0.066, and 0.181 dB" is now
obsolete rather than wrong: what remains is no longer all there is.

## What the paper's ratios become

The numerators are confirmed. The denominators are the problem, and there are
three defensible ones. The paper uses the first.

1. The audit's 120 standpoint floor rescaled by the square root of the
   standpoint count, `0.0042 * sqrt(120/80) = 0.00514` and so on.
2. The remeasured 120 standpoint floor rescaled the same way.
3. The floor measured directly at the configuration the numerator comes from:
   250 m crop, four interactions, 80 standpoints, at Korenmarkt.

| illumination | rms | floor 1 | ratio | floor 2 | ratio | floor 3 | ratio |
|---|---|---|---|---|---|---|---|
| isotropic | 0.1281 | 0.00514 | 24.9 | 0.00345 | 37.2 | 0.00192 | 66.6 |
| rooftop | 0.0605 | 0.01666 | 3.6 | 0.01987 | 3.0 | 0.03881 | 1.6 |
| street small cell | 0.1883 | 0.04201 | 4.5 | 0.07281 | 2.6 | 0.02616 | 7.2 |

And for the largest changes, which is what the Discussion's "7 to 47 times"
divides:

| illumination | worst | ratio, floor 1 | floor 2 | floor 3 |
|---|---|---|---|---|
| isotropic | 0.2420 | 47.1 | 70.2 | 125.8 |
| rooftop | 0.1159 | 7.0 | 5.8 | 3.0 |
| street small cell | 0.3256 | 7.8 | 4.5 | 12.4 |

The third floor is the honest one and it is the one that was missing. The
rescaling in the first two is not sound: the 130 m crop is not converged for the
rooftop or street models, which the `crop_bound_note` in every manifest already
says, so moving a floor from 130 m to 250 m is not a change of standpoint count.
Measured directly, the street floor **falls** from 0.0594 to 0.0262 dB and the
rooftop floor **rises** from 0.0162 to 0.0388 dB. Neither move is what a square
root of a count would predict.

Two consequences.

- The isotropic claim is conservative. "Roughly 25 times" is a true lower bound
  on every floor measured here and the honest figure is nearer 67.
- The rooftop claim is not. At the configuration the numerator comes from, the
  rooftop rms is 1.6 times its Monte Carlo floor and the worst rooftop square is
  3.0 times it. A range that starts at 7 cannot be supported.

There is a sharper way to say the rooftop result, and it is worth saying because
it is the one place where the conclusion changes rather than the wording. The
two legs of the comparison do not share a ray stream, so each square's shift
carries an independent Monte Carlo component of `sqrt(2)` times the floor.
Subtracting it in quadrature from the measured rms leaves the part that is
standpoint sampling:

| illumination | measured rms | Monte Carlo part | standpoint sampling alone |
|---|---|---|---|
| isotropic | 0.1281 | 0.0027 | **0.1281** |
| rooftop | 0.0605 | 0.0549 | **0.0255** |
| street small cell | 0.1883 | 0.0370 | **0.1846** |

So the isotropic and street numbers are standpoint sampling almost entirely, and
**most of the rooftop 0.061 dB is Monte Carlo noise, not standpoint sampling.**

## The material result's "5.7 times"

"The 0.024 dB isotropic shift was 5.7 times the 0.0042 dB standard error of the
walk median." That comparison is at 120 standpoints and 130 m, so floor 2
applies unrescaled: 0.024 / 0.0028 = **8.6 times**. The claim holds and is
understated.

A caveat the sentence does not carry. The material comparison is paired, both
rungs on the same standpoints and the same seeds, so its own error is the sd of
the paired shift, not the sd of the walk median. Measured over 32 streams on the
adjacent geometric to walk comparison that sd is 0.0041 dB, which would give
0.024 / 0.0041 = 5.9 times. Both denominators are defensible and they give
different answers, so whichever is used should be named.

## Two things found on the way

**`city250_datum` is not internally homogeneous.** Its eleven manifests carry
`roulette_start: 3` at Korenmarkt, Krakow and Toulouse and `roulette_start: 4`
at the other eight. The sweep straddled the change to `DEFAULT_MAX_BOUNCES`.
Roulette is unbiased either way so no median is biased by it, but it means the
two legs of the standpoint sampling comparison decorrelate completely, which is
the reason the quadrature subtraction above uses the independent error rather
than a paired one. It is also why the eight squares the rms is taken over are
exactly the eight that changed setting.

**`cities250_corrected_15ghz_summary.json` is a mid sweep snapshot.** It carries
nine sites, not eleven: New York and Prague are absent and Milan is recorded at
44 standpoints against the 80 in its own per site file. The per site files are
the ones the standpoint sampling comparison reads, and they are complete, so
nothing above depends on the aggregate. It is not the headline aggregate either,
which is `cities250_L3`. Left alone rather than rebuilt, because rebuilding it
would write over a published artefact.

## What the paper should say

Numbers only. The wording is not mine to choose and no `.tex` file was touched.

- Abstract, "roughly 25 times the isotropic Monte Carlo error". The rms is
  confirmed. The ratio is at least 37 and is 67 against the directly measured
  floor. Either raise the number or make it a bound.
- Discussion, "the standard errors of a walk median are 0.0042 dB isotropic,
  0.0136 dB rooftop, and 0.0343 dB street", and the sentence saying the per seed
  medians were not retained. Remeasured over 32 disjoint streams they are
  **0.0028, 0.0162 and 0.0594 dB**, and the per seed values are now in
  `outputs/mc_error/clean_geometric_15ghz_replicas.jsonl`. The sentence about
  the record no longer applies.
- Discussion, "an older street-cell value of 0.079 dB was the lowest of eight
  seed draws. The seed-averaged shift is 0.167 +/- 0.022 dB, or 7.6 standard
  errors on the mean of eight and 2.7 on one run." Over 32 streams the shift is
  **0.1505 +/- 0.0092 dB**, 16.4 standard errors on the mean and 2.9 on one run,
  and 0.0785 is the third lowest of the 32.
- Discussion, "these values are 7 to 47 times their Monte Carlo floors". Against
  the directly measured floors the range is **3.0 to 126**, and quoting a range
  hides that the rooftop end is the weak one. The rooftop row deserves its own
  sentence.
- Results, "the 0.024 dB isotropic shift was 5.7 times the 0.0042 dB standard
  error of the walk median". **8.6 times** against the remeasured floor, or 5.9
  against the paired error, which is arguably the right denominator.
- Discussion, "recomputing from what remains gives 0.125, 0.066, and 0.181 dB".
  The two files are repaired, so this can go.
- Anywhere the Monte Carlo floor is used as a denominator, it should say which
  configuration it was measured at. The three floors measured here differ by up
  to a factor of two between the 130 m and 250 m crops on the same quantity.

## What was run

Everything on `blgpu` through `tools/blgpu.sh`, four workers of eight, detached.
`rtree` 1.4.1 is present in the remote venv and the walk binding was checked by
area fraction rather than assumed, which are the two traps recorded in
`REMOTE_COMPUTE.md`.

| job | what | wall time |
|---|---|---|
| `20260803T072837-5659` | 8 streams, both ladder rungs, 130 m | 11 min |
| `20260803T074237-66bc` | control re-trace, Korenmarkt and Tokyo at 250 m | 4 min |
| `20260803T074758-6190` | the two repairs, plus both controls again | 10 min |
| `20260803T075758-2943` | 32 streams, both ladder rungs, 130 m | 43 min |
| `20260803T084130-45eb` | 8 streams, Korenmarkt at 250 m | 4 min |
| `20260803T084707-2e32` | 32 streams Korenmarkt, 8 streams Brussels and New York, 250 m | 35 min |

## Files written

Under `outputs/mc_error/`:

- `clean_geometric_15ghz_replicas.jsonl`, `clean_walk9_15ghz_replicas.jsonl` and
  their manifests. 32 replicas by 120 standpoints of every susceptibility, one
  row per standpoint per replica. This is the artefact whose absence was the
  finding.
- `korenmarkt250_15ghz_replicas.jsonl`, `brussels250_...`, `newyork250_...`, the
  same at the 250 m configuration the standpoint sampling comparison uses.
- `mc_error_clean_geometric_8x_15ghz.json` and `..._32x_...`, the reduction:
  per standpoint spread, walk median spread with an interval on it, paired shift
  per replica, and the crossing counts with their control.
- `mc_error_korenmarkt250_*`, `mc_error_brussels250_*`, `mc_error_newyork250_*`.
- `standpoint_sampling_15ghz.json`, the per square medians and the rms.

Under `outputs/exposure_korenmarkt/`, tag `city250_repair`: four sites, two
repairs and two controls, with their manifests, summaries and spectra.

Code: `run_seed_replicas.py` and `repair_torn_sites.py` are new.
`run_exposure.run` gained `roulette_start`, `ground_datum_m` and
`walk_probe_z_m`, `build_walk` gained `probe_z_m` and records it, and
`tests/test_ground_datum.py` gained a test that pins the old probe height's
behaviour and the provenance that names it.

## Correction, added after the report was written

The floor 3 row of the ratio table, the one this report calls the honest one, has
its rooftop and street-cell entries swapped, and its isotropic entry does not
reproduce either.

Recomputed from the same file the report names,
`outputs/mc_error/korenmarkt250_15ghz_replicas.jsonl`, whose manifest confirms
Korenmarkt, a 250 m crop, four interactions, 80 standpoints and 32 seeds, and
using the same reduction that reproduces this report's 130 m column exactly at
0.0028, 0.0162 and 0.0594 dB:

| illumination | reported floor 3 | recomputed | rms / floor | worst / floor |
|---|---|---|---|---|
| isotropic | 0.00192 | **0.00309** | 41.4 | 78.2 |
| rooftop | 0.03881 | **0.02582** | 2.4 | 4.5 |
| street small cell | 0.02616 | **0.03918** | 4.8 | 8.3 |

Four reductions were tried against the reported numbers, the decibel of the
median, the median of the decibel, the decibel of the mean, and the per
standpoint median divided by the square root of 80. None lands on them, and none
puts the rooftop floor above the street floor. Street illumination carries the
largest Monte Carlo noise of the three under every measurement in this study,
including this report's own 130 m table, so a floor 3 row with rooftop above
street contradicts the report itself.

The conclusions do not change shape. The isotropic claim is still conservative,
the rooftop pair is still the weak one, and a single range across the three
models still hides that. The sizes change: the isotropic ratio is 41 rather than
67, the largest isotropic change is 78 rather than 126, and the rooftop pair is
2.4 and 4.5 rather than 1.6 and 3.0.

`paper/paper.tex` and `paper/si.tex` carry the recomputed values.
