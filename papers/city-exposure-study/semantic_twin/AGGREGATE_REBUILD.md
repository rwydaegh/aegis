# Rebuilding the eleven city figure

`FIGURES/16_eleven_cities_exposure.png` claimed eleven squares at 80 standpoints
each and drew one of them at 3. This is what was wrong with the file it came
from, what was checked before anything was rerun, what replaced it, and every
headline number that moved.

Status: rebuilt and complete. The figure now comes from `city250_L3_*`, a single
writer sweep of 11 sites at 80 standpoints, 880 in total, with no torn records
and one bounce budget.

## What the published figure actually was

It was a copy of `cities250_15ghz_cdf.png` as it stood at 01:53 on 2026-08-02,
and it carried three defects at once.

**Brussels was drawn from 3 standpoints.** The legend said so, `brussels
grandplace (3)`, and the entry was read as a label rather than as a warning. The
source file `city250_brussels_grandplace_15ghz_locations.jsonl` still holds those
3 lines. Every other curve had 80, so the figure was ragged and its Brussels
median was computed from three points.

**It was drawn under the superseded elevation law.** The rooftop panel is the
left one, and the correction of `MONOSTATIC_SBR.md` had not been applied when
that PNG was written. So the figure and the eleven city table in
`PAPER_METHODS.md` never agreed: the table had already been moved to the
corrected law, the figure had not.

**Nothing on the page said either thing.** The caption asserted the converged
radius, which was true, and said nothing about coverage, which was not.

## Why it happened

Two causes, and the second is the one that will recur.

`run_all_sites` calls `cross_city_report` inside the per site loop, so the
aggregate is written after every site and spends ten elevenths of its life
partial. That is a deliberate trade, a sweep that dies at hour two still leaves a
readable aggregate, and it is only dangerous because a partial aggregate is
indistinguishable from a finished one by inspection.

Two sweeps then ran concurrently under the same `city250_corrected_*` tag and
interleaved their appends into the same files. That is not a race that corrupts
statistics quietly, it tears records in half mid line, and the evidence is
still on disk.

## The audit, before anything was rerun

Every per site file under the corrected 250 m tag, parsed line by line.

| site | lines | parsed | torn | verdict |
|---|---|---|---|---|
| Brussels Grand-Place | 80 | 80 | 0 | clean |
| Ghent Korenmarkt | 80 | 80 | 0 | clean |
| Krakow Rynek | 80 | 80 | 0 | clean, wrong datum |
| London Trafalgar | 80 | 80 | 0 | clean |
| Madrid Plaza Mayor | 80 | 80 | 0 | clean |
| Mexico City Zocalo | 80 | 80 | 0 | clean |
| Milan Duomo | 80 | 80 | 0 | clean |
| New York Times Square | 80 | 78 | 2 | **short by 2 standpoints** |
| Prague Staromestske | 81 | 80 | 1 | 80 good rows plus a fragment |
| Tokyo Hachiko | 80 | 80 | 0 | clean |
| Toulouse Capitole | 80 | 80 | 0 | clean, wrong datum |

The two anomalies in the brief both resolve.

**Milan at n=44 in one place and n=80 in another** is not a conflict between two
files, it is one file read at two times. `cities250_corrected_15ghz_summary.json`
was written at 21:53 while Milan was 44 standpoints into its trace, and Milan
finished at 21:55. The aggregate is a snapshot of a sweep in flight and the per
site summary is the finished thing.

**Prague at 81 lines** is 80 complete records followed by a 46 character
fragment, `ll_cell_sar_wb_w_kg": 6.454828678939949e-05}`, which is the tail of a
record whose head went to a different file offset. New York has the same defect
twice, at line 62 and line 80, and there it cost two whole standpoints rather
than a trailing scrap. So the published Times Square row was computed from 78
standpoints and nothing said so.

Three files, Brussels, Madrid and Prague, also carry records under two different
key sets, differing by the presence of `multipath_gain_street_small_cell`. Two
code versions were writing one file. The physics columns agree, so this cost
nothing numerically, but it is the clearest available proof that the files are
mixtures.

## The tracer is deterministic, which is what made the audit conclusive

Before trusting or discarding anything, Brussels was retraced from scratch under
the same configuration. All 80 standpoints reproduced the stored file to
0.00e+00 on every physics column and on the standpoint coordinates.

Tokyo was then retraced standalone, from a `git archive` of HEAD rather than the
working tree, and compared against its rows from inside the sweep, where it ran
tenth. Bit identical again on the first 20 standpoints, which is enough: it shows
that position in a sweep, the shared body coupler and the standalone code path
all make no difference.

So a site's rows are either right or absent. There is no third state in which
they are subtly wrong, and the audit above is therefore a complete account of the
damage.

## The completeness guard does not catch this

`run_exposure.py` gained `sites_present`, `sites_expected`, `complete`,
`locations_by_site` and `ragged_locations`, and prints `[partial] ... Do not
publish this figure`. On a one of eleven aggregate it printed nothing and wrote
`"complete": true`.

The reason is that `expected` is incremented inside the loop, next to `done`, so
it counts the sites reached rather than the sites intended, and the two are equal
at every iteration of a healthy sweep. The guard therefore fires when a site
raises, which is the rarer failure, and stays silent through the mid sweep
snapshot, which is the one that reached the paper.

`run_exposure.py` belongs to another thread and was not edited here. The one line
change is to count the sites with a mesh at the crop radius before the loop
starts rather than during it.

The guard that is doing the work now lives in `FIGURES/make_eleven_cities_exposure.py`.
It refuses to draw unless all eleven sites are present, every standpoint count is
equal, and no line failed to parse. Run against the corrupt corrected tag it
refuses and names New York and Prague.

## What the figure is now built from

`city250_L3_*`, the single writer eleven city sweep at a bounce budget of three
on the fixed ground datum. It was not run here. A concurrent thread had already
launched the identical configuration on `blgpu` ten minutes earlier, and a
duplicate 11 site sweep on a box at load 38 would have halved its throughput for
nothing, so the duplicate started here was stopped and its outputs removed.

| property | value |
|---|---|
| sites | 11 |
| standpoints per site | 80, all equal |
| total standpoints | 880 |
| torn records | 0 |
| bounce budget | 3 at every site |
| crop radius | 250 m |
| ground datum | measured per site by `measure_ground_datum` |
| writers | one |

## What moved, against the noise floor

The comparison is the published `city250_corrected_*` against `city250_L3_*`.
Three things changed at once, so attribution matters: the bounce budget went from
4 to 3, the ground datum estimator was replaced, and New York gained the two
standpoints it had lost.

Noise is the walk median standard deviation over eight seeds from
`CODE_AUDIT.md` section 4.1: 0.0042 dB isotropic, 0.0136 dB rooftop, 0.0343 dB
street small cell. A shift is called resolved below when it exceeds two of those.

### Isotropic median

| site | published | rebuilt | shift dB | resolved |
|---|---|---|---|---|
| Krakow Rynek | 0.5304 | **0.3841** | -1.402 | yes |
| Toulouse Capitole | 0.3992 | **0.2963** | -1.294 | yes |
| Brussels Grand-Place | 0.2351 | 0.2223 | -0.244 | yes |
| Tokyo Hachiko | 0.2238 | 0.2334 | +0.183 | yes |
| New York Times Square | 0.1629 | 0.1694 | +0.170 | yes |
| London Trafalgar | 0.3894 | 0.3946 | +0.058 | yes |
| Prague Staromestske | 0.3626 | 0.3584 | -0.051 | yes |
| Madrid Plaza Mayor | 0.3473 | 0.3433 | -0.050 | yes |
| Milan Duomo | 0.3538 | 0.3559 | +0.026 | yes |
| Mexico City Zocalo | 0.3974 | 0.3977 | +0.003 | no |
| Ghent Korenmarkt | 0.2917 | 0.2916 | -0.002 | no |

### Rooftop median

| site | published | rebuilt | shift dB | resolved |
|---|---|---|---|---|
| Krakow Rynek | 0.9001 | **0.2681** | -5.260 | yes |
| Toulouse Capitole | 0.3383 | **0.2219** | -1.832 | yes |
| Mexico City Zocalo | 0.2990 | 0.3070 | +0.115 | yes |
| New York Times Square | 0.1294 | 0.1271 | -0.076 | yes |
| Tokyo Hachiko | 0.1009 | 0.0996 | -0.054 | yes |
| Brussels Grand-Place | 0.0976 | 0.0987 | +0.048 | yes |
| Milan Duomo | 0.2477 | 0.2451 | -0.046 | yes |
| Madrid Plaza Mayor | 0.1462 | 0.1447 | -0.046 | yes |
| Prague Staromestske | 0.2357 | 0.2377 | +0.037 | yes |
| London Trafalgar | 0.2868 | 0.2884 | +0.025 | no |
| Ghent Korenmarkt | 0.1627 | 0.1626 | -0.001 | no |

### Street small cell median

| site | published | rebuilt | shift dB | resolved |
|---|---|---|---|---|
| Krakow Rynek | 0.4600 | **0.0232** | -12.972 | yes |
| Toulouse Capitole | 0.0318 | **0.0174** | -2.608 | yes |
| New York Times Square | 0.0561 | 0.0604 | +0.321 | yes |
| Milan Duomo | 0.0351 | 0.0375 | +0.293 | yes |
| Tokyo Hachiko | 0.0155 | 0.0161 | +0.163 | yes |
| Brussels Grand-Place | 0.0065 | 0.0067 | +0.131 | yes |
| London Trafalgar | 0.0268 | 0.0276 | +0.126 | yes |
| Mexico City Zocalo | 0.0297 | 0.0291 | -0.085 | yes |
| Prague Staromestske | 0.0194 | 0.0197 | +0.067 | no |
| Madrid Plaza Mayor | 0.0080 | 0.0079 | -0.057 | no |
| Ghent Korenmarkt | 0.0143 | 0.0143 | -0.019 | no |

Two sites move by more than a decibel and nine move by less than a quarter of
one. The two are Krakow and Toulouse, whose datum put the observer on the roof of
the Cloth Hall and of the Capitole, and coming down to the pavement costs 5.3 dB
of rooftop susceptibility at Krakow and 13.0 dB of street small cell. That is the
correction working, not a new instability.

The nine others move by 0.001 to 0.24 dB, and the bounce budget is not what moved
them. `BOUNCE_BUDGET.md` measures the drop from 4 to 3 at a median of about two
thousandths of a decibel per standpoint, worst case 0.12 dB at one standpoint out
of 40, so it contributes roughly the seed noise and no more. What is left is the
datum estimator, which moved every site a little, by 0.01 to 0.22 m, and at New
York the two recovered standpoints as well. Tokyo and Brussels move most among
the nine, at +0.18 and -0.24 dB isotropic, and they are also the two largest
datum shifts of the nine, at +0.20 m and -0.22 m.

One caveat that belongs with the budget rather than with this figure. At three
bounces the truncated throughput share rises from 0.0005 to 0.0037 at the median,
so the estimator is biased low, and `BOUNCE_BUDGET.md` owns the size and sign of
that bias. It is a property of the new operating point, not of the rebuild.

### Between city and within city spread

| quantity | published | rebuilt |
|---|---|---|
| between city range, isotropic | 5.13 dB | **3.71 dB** |
| between city range, rooftop | 9.65 dB | **4.93 dB** |
| between city range, street small cell | 18.53 dB | **9.58 dB** |
| largest within city spread, isotropic | 6.15 dB, Madrid | **6.46 dB, Madrid** |
| largest within city spread, rooftop | 13.29 dB, Brussels | 12.89 dB, Brussels |
| largest within city spread, street small cell | 18.40 dB, Brussels | 19.01 dB, Brussels |

Every between city range narrows, because both sites that shrink were the two
roof standpoints sitting at the top of the range. The rooftop range halves.

**The study's headline claim survives and gets stronger.** Under isotropic
illumination the spread inside Madrid Plaza Mayor is 6.46 dB and the spread
across eleven squares on three continents is 3.71 dB. Where a person stands in
one square matters more than which city the square is in, and the margin is now
2.75 dB rather than 1.02 dB.

### Rank structure

| correlation | published | rebuilt |
|---|---|---|
| Spearman, rooftop against isotropic | +0.945 | +0.936 |
| Spearman, street small cell against isotropic | +0.436 | +0.345 |
| Pearson, log rooftop against log isotropic | +0.852 | +0.835 |

Those barely move. What moves is the ordering of the cities themselves, measured
against the published order:

| ordering | Spearman, rebuilt against published |
|---|---|
| isotropic | +0.809 |
| rooftop | +0.864 |
| street small cell | +0.836 |

The reordering is almost entirely the two datum sites falling. By isotropic
median Toulouse drops from 2nd to 7th and Krakow from 1st to 3rd, and Mexico City
Zocalo becomes the most exposed square of the eleven. By rooftop median Toulouse
drops from 2nd to 6th, Krakow from 1st to 3rd, and Mexico City again takes the
top. No other site moves by more than two places.

The old figure's most quotable feature, Krakow as the dark red outlier standing
clear of the other ten in all three panels, was the Cloth Hall roof. It is gone.

## What this does not settle

**The published text still carries the old numbers.** `PAPER_METHODS.md` section
9.2 and `REPORT.md` were not edited here. Their eleven city table is the
`city250_corrected` one, so the Krakow and Toulouse rows are the roof, and the
prose that reads Krakow as an open square outperforming the rest describes an
artefact. `GROUND_DATUM.md` owns that correction and lists it.

**The superseded rooftop column is now two revisions behind.** It was kept beside
its replacement so that any number published before 2026-08-02 could be located.
That column was computed at a bounce budget of 4 on the old datum, and neither is
the operating point any more.

**Nothing in this figure uses image evidence.** The eleven city comparison holds
materials constant by a geometric class prior, which is the point, but it means
the word semantic in the pipeline's name does not describe this figure.

## Reproducing it

```bash
python FIGURES/make_eleven_cities_exposure.py            # from city250_L3_*
python FIGURES/make_eleven_cities_exposure.py _corrected # refuses, and says why
```

The sweep behind it, which takes about two hours on eight uncontended cores and
does not finish in a night on four contended ones:

```bash
tools/blgpu.sh run "python run_exposure.py --all-sites --locations 80 \
    --rays 200000 --crop-m 250 --max-bounces 3 --seed 7 --tag-suffix _L3"
```
