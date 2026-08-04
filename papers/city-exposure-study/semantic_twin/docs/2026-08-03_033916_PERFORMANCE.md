# What the estimator spends its time on

The cost of this study is one number repeated: an eleven city sweep is 880
traces, the crop convergence study multiplies that by the number of radii, and
the sensitivity study multiplies it again. Until a trace is cheap the study
reports point values where it should report distributions, so this file is
about where a trace goes and what was done about it.

Every change below is constrained the same way. The estimator is deterministic
given a seed, and a change that reorders a random draw, or that lands on a
different bit, is a change to the published numbers. So nothing here is
accepted on a tolerance. `tests/test_determinism.py` compares hex floats and
SHA-256 of the angular spectra, and the before and after trees were run against
each other on real standpoints, on both machines, before anything was
committed.

Timings are on `blgpu` unless they say otherwise, eight Xeon Gold 6226 cores on
two NUMA nodes, 31 GB, load 0.0, Python 3.12.13, NumPy 2.4.6, Mitsuba 3.8.0.
See REMOTE_COMPUTE.md. The local four vCPU box lives above load 30 and its
absolute seconds mean nothing, though its ratios are quoted where the
contention is the point.

## Where the time went

One standpoint on the Korenmarkt 250 m mesh, 617,091 triangles, 400,000 rays,
twelve bounces, 512 local cells, three illumination models, under `cProfile` on
an idle box. Total 1.40 s instrumented, which on a second standpoint ran 35 %
over the same trace untraced, so read the shares and not the seconds.

| Where | s | share | what it is |
| --- | --- | --- | --- |
| Mitsuba `intersect` | 0.49 | 35 % | BVH traversal and the Dr.Jit to NumPy conversion, which is where the traversal is actually forced |
| `nearest_cell` | 0.35 | 25 % | one `(400000, 512)` matrix of dot products, then an `argmax` |
| the ray loop itself | 0.23 | 16 % | gathering and scattering the live rays each bounce |
| `_cosine_hemisphere` | 0.14 | 10 % | two cross products and a normalise per bounce |
| Fresnel and roughness | 0.09 | 6 % | complex square roots per surface interaction |
| `normalisation` | 0.03 | 2 % | a 200,001 point trapezoid per model, recomputed at every standpoint |
| deposit and the rest | 0.07 | 5 % | |

Three things in that table are worth saying out loud. The compaction was not
the problem, which was the first guess: the whole live ray bookkeeping is 16 %,
and most of that is repeated fancy indexing rather than the compaction itself.
The dense `nearest_cell` was a quarter of the trace for a question with 512
possible answers. And the illumination normalisation, which depends on nothing
but the model, was being integrated again at every one of the 880 standpoints.

## What changed

**The band search in `nearest_cell`.** The dense form writes a 1.6 GB matrix
per trace to answer 400,000 questions with 512 answers each. Because the
Fibonacci grid is sorted in height, the dot product of a query with any cell at
height `z` is at most `cos(el_u - el_z)`, so once any candidate with dot
product `b` is in hand, only cells within `arccos(b)` in elevation can beat it.
That is a contiguous run about `1.5*sqrt(cells)` wide either side, 34 cells out
of 512. The band is searched first and the bound is then checked against what
the band found, and any ray whose bound reaches outside its band falls back to
the dense form, so the answer is the dense answer for every input including
exact ties. Over two million directions on grids from 64 to 4096 cells the
fallback fired zero times, which is a speed statement and not a correctness
one.

Isolated, 400,000 directions against 512 cells on the idle box:

| | dense | band | |
| --- | --- | --- | --- |
| eight BLAS threads | 0.444 s | 0.167 s | 2.7x |
| one BLAS thread | 1.004 s | 0.166 s | 6.0x |

The band is indifferent to the thread count and the dense form is not, which is
the property that matters: one thread is what a standpoint gets once a sweep
runs standpoints in a pool. On the contended four vCPU box, where BLAS never
gets its threads, the same pair is 3.01 s against 0.29 s.

**A memo on `IlluminationModel.normalisation`.** The value depends on the model
and the quadrature and nothing else. It is now computed once per pair. The memo
lives outside the dataclass fields, so equality and hashing are untouched, and
the test asserts the kept value is the value the quadrature returns.

**Fewer gathers in the ray loop.** The live slice of position, direction,
throughput and bounce count was gathered out of the full length array once per
reader, up to four times a bounce. It is gathered once and shared. Same values,
same order, same arithmetic.

**`np.cross` and `np.linalg.norm` written out.** At 400,000 rows the shape
negotiation inside those two is most of what they cost. The replacements
evaluate the same expressions in the same order, which is checked by the before
and after comparison rather than argued.

Together, on three real Korenmarkt standpoints at 250 m and 200,000 rays,
alternating the two trees, best of three:

| bounce budget | before | after | |
| --- | --- | --- | --- |
| twelve | 0.80 s per standpoint | 0.60 s | 1.33x |
| three | 0.79 s | 0.57 s | 1.39x |

On the contended local box the same comparison is 3.14 s against 1.46 s, which
is 2.1x. The gap between the two boxes is almost all `nearest_cell`: eight idle
BLAS threads hide most of the dense matmul and four contended vCPU do not. So
1.35x is the honest figure for a machine with cores to spare, and the saving
grows the more the machine is oversubscribed, which is the state a sweep is
usually in.

**Standpoints in a process pool.** `trace_standpoints` runs a sweep across
worker processes and yields `(row, result)` in sweep order, so a caller keeps
streaming its rows to disk and stays restartable. Standpoints share nothing:
each opens its own generator on its own seed, reads a scene nothing writes to,
and reduces into its own counters. That is why the pooled result is the serial
result bit for bit rather than to a tolerance, which the test checks on the real
mesh, and which every run below re-checked at every worker count. Workers are
made single threaded, because the estimator's own BLAS and Dr.Jit threading
fight a pool for the same cores. Each worker loads the mesh once, which is why
`MitsubaGeometry` now pickles as its own recipe rather than not at all.

96 standpoints, 200,000 rays, three bounces:

| workers | s per standpoint | against serial |
| --- | --- | --- |
| 1 | 0.609 | |
| 4 | 0.261 | 2.3x |
| 6 | 0.206 | 3.0x |
| 8 | 0.193 | 3.2x |

3.2x and not 8x, and the reason is that the serial run is not single threaded
either: it already spreads its BLAS and its BVH traversal over the same eight
cores. What the pool converts is the part of a trace that no library
parallelises, which is most of the NumPy in the ray loop.

Startup is worth knowing about. Each worker imports Mitsuba and loads the mesh,
which is about six seconds of pool for eight workers, so a sweep of 8
standpoints across 8 workers runs at 0.90 s per standpoint and a sweep of 96
runs at 0.193 s. Below roughly four standpoints per worker the pool is not
worth starting. At 80 standpoints a site it is.

The pool is available and not yet wired into the sweep drivers, which were
being run and edited by other work while it landed. What a driver has to do is
replace its `for` over the picks, keeping the streaming write and the ordering
it already relies on:

```python
standpoints = [
    (walk.points[i], float(walk.ground_z_m[i]), seed + 1000 * int(i)) for i in picks
]
for row_index, result in trace_standpoints(tracer, standpoints, MODELS, workers=workers):
    index = picks[row_index]
    ...                                    # unchanged from here down
```

## What was tried and rejected

**`ray_intersect_preliminary`.** 0.168 s against 0.256 s for 400,000 rays, so
1.5x on the intersection. It does not return a normal. Computing the face
normal from the mesh would compute it in double precision where Mitsuba returns
it in single, which changes every reflection. Rejected.

**`RayFlags.Minimal`.** Slower, 0.445 s, and returns a different normal.
Rejected on both counts.

**Smaller blocks in the dense `nearest_cell`.** 0.61 s at 2048 rows against
2.05 s at 65536 on one thread, so most of the dense cost was cache and not
arithmetic. Superseded by the band search, which is faster on one thread and
also wins the eight thread case.

## The GPU, honestly

There is an idle RTX A6000 on the box and Mitsuba has a CUDA variant, so the
question is real. The answer is no, and the reason is measured rather than
asserted.

For the same 400,000 rays against the same mesh, `cuda_ad_rgb` took 0.080 s
against 0.256 s for the CPU backend on an idle box, so the GPU casts the rays
about three times faster. Then the intersections themselves:

- 233,521 of 400,000 rays differ from the CPU answer in at least one field.
- 115 rays hit a **different triangle**, not the same triangle to a different
  rounding.
- distance differs by up to 3.6e-4 m, and where the triangle differs the normal
  differs by up to 2.0, which is a flip.

So the GPU is three times faster at a third of the trace and returns a
different scene interaction for a hundred rays in four hundred thousand. Every
published susceptibility would have to be re-baselined, and "bit exact across
machines" would become "bit exact within a backend". That is a defensible trade
for a different study and it is not a free speedup for this one.

The other two thirds of the trace are worse candidates still. What they are is
NumPy over a live ray set that shrinks by an unpredictable amount every bounce,
with a compaction and a branch per bounce, which is the shape a GPU is worst at
without a persistent thread kernel nobody here is going to write. And the
workload above the trace is already embarrassingly parallel at the standpoint
level, so the honest recommendation for this study is more cores, not a
different processor.

## What an eleven city sweep costs

The shipped cross city command is 11 sites at 80 standpoints, 200,000 rays,
250 m crop, three bounces, so 880 traces plus 11 per site setups. A site setup,
which is the mesh load, the ground datum, the face classification, the material
binding and the walk, is 1.4 s on `blgpu`, so it is a quarter of a minute of
the whole run and not worth optimising.

| | s per standpoint | 880 standpoints |
| --- | --- | --- |
| before | 0.79 | 11.6 min |
| after, serial | 0.61 | 8.9 min |
| after, eight worker pool | 0.19 | 2.8 min |

The pool row costs another minute of worker startup across the eleven sites, so
call it four minutes against twelve, on a box nobody else is using. It is nine
minutes without the pool, which is what the sweep gets today, because the pool
is not yet wired into the driver.

The number that changes what the study can do is none of those on its own. It
is that the crop convergence study and the sensitivity study are the eleven
city sweep times a handful, and at four minutes a sweep that is an afternoon of
arithmetic rather than a week of it, which is the difference between reporting
a point value and reporting a distribution.

## What is bit exact, and what is not

`blgpu` and the local box now run the same Python, NumPy and Mitsuba, and at
those versions the same three standpoints agree on **every** field: hex float
susceptibilities for all three illumination models, SHA-256 of every angular
spectrum, the exit profile, the delay statistics. Cross machine bit exactness
holds.

It is version exactness, not machine exactness, and the difference showed up
before the two boxes were matched. Against the older remote environment, Python
3.10 with NumPy 2.2.6 and Mitsuba 3.9.0:

- `sky_fraction`, `escaped_fraction` and `mean_bounces` agreed exactly, so the
  rays went to the same places and died in the same order.
- `rho` and `chi` for the isotropic model agreed exactly.
- `rho` and `chi` for the rooftop and street models differed in the last one or
  two units in the last place.

The difference is `arcsin` in the elevation weighting: libm is not standardised
to the last bit and the two of them rounded it differently. It is 1e-16
relative and reaches nothing this study reports, but it is why
`tests/test_determinism.py` pins the isotropic model rather than all three. A
recorded constant that only holds on one libm is a flaky test, not a guarantee.
The before and after comparison, which is the one that actually protects the
numbers, covers all three models and every field and was run on both machines.

## Reproducing any of this

```bash
python -m pytest tests/test_determinism.py -q          # 21 checks, about 20 s
python run_exposure.py --validate                      # the closed form checks
```

The before and after comparison is not a committed script because it needs two
trees. It is a copy of `semantic_twin/` from before the change, a `TraceConfig`
with every field written out so a moved default cannot creep in, and a SHA-256
of every `rho` plus the hex float of every scalar, on three standpoints of the
Korenmarkt 250 m mesh. Two defaults did move underneath it while this work was
in flight, the bounce budget and the roulette start, which is why the config is
pinned field by field in the test as well.
