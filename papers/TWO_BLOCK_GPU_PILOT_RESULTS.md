# Two-block GPU pilot results

## Result

The proposed two-block paper is practical, and the old multi-day estimate was
too pessimistic for this scope.

A literal miniature campaign ran on the rented RTX A6000 with:

- Duke, 56,024 triangles;
- LOS and NLOS;
- seed 0;
- 28 and 100 GHz;
- UE position 4;
- M = 16, 64, and 256;
- current schema-v2 center ray packs;
- complex128 channels and operators;
- float64 complete body maps;
- full production surface physics;
- all 21 actual MRT target positions;
- all six whole-body ECBF budgets at chest zero standoff;
- complete spatial averaging and all normal scalar outputs.

This is 12 real scene/body/array items, grouped into four body-ray bakes,
with 324 unique coherent body maps. It is the proposed full job with the body,
seed, frequency, and UE dimensions reduced, not a synthetic matrix benchmark.

The four measured groups took **47.18 seconds** after one warm-up group. The
three missing ray packs took another **4.1 seconds** to trace. The GPU returned
to idle after the run.

That short result was subsequently checked with a sustained run covering every
frequency, both channel conditions, two seeds, two UE positions, and all three
arrays on Duke. The sustained result is described below. It confirms that the
47.18 second run was real, while giving a much better estimate of frequency and
ray-count variation.

## Sustained cross-frequency run

The sustained shard kept the current full surface physics and swept:

- Duke with 56,024 triangles;
- LOS and NLOS;
- seeds 0 and 1;
- all eight frequencies from 8 through 100 GHz;
- UE positions 4 and 5;
- M = 16, 64, and 256;
- 21 MRT positions and six zero-standoff global ECBF budgets per array.

This is 64 body-ray groups, 192 body-ray-array items, and 5,184 unique body
maps. It retains every expensive axis except phantom identity, most seeds, and
most UE positions. The trace/preflight stage ensured that all 64 common-center
packs were present in 38.18 seconds.

After one warm-up group, all 64 measured groups completed in **796.55 seconds,
or 13.28 minutes**. The complete process including warm-up took 822.07 seconds.
The run exited successfully with complex128 channels and operators, float64
maps, all 64 expected group keys, all 192 array results, and all 5,184 expected
maps.

Measured throughput was 6.51 complete reported maps per second, including all
body-response preparation, beam construction, map reduction, and JSON output.
The maps themselves were not slow. MRT and ECBF map evaluation and reduction
together took 56.01 seconds, equivalent to 92.6 maps per second. The rest was
mostly preparing the body response for each new ray-direction set.

The sustained stage totals were:

| Stage | Sustained time | Share of measured wall |
|---|---:|---:|
| Fock and visibility modifier preparation | 462.08 s | 58.0% |
| Shared center-ray body atlas | 232.23 s | 29.2% |
| MRT maps and reductions | 47.51 s | 6.0% |
| Lazy per-array Q lift | 21.54 s | 2.7% |
| UE channels and all global ECBF solves | 12.24 s | 1.5% |
| ECBF maps and reductions | 8.50 s | 1.1% |
| Body setup, ray loading, and Q transfer | 3.08 s | 0.4% |

This independently confirms the short-pilot diagnosis. Spatial averaging and
the global ECBF solve are not the dominant work in the proposed two-block
paper. Modifier preparation plus the center atlas consume about 87% of wall
time.

## Implemented exact acceleration

The two dominant stages have now been rewritten and measured on the same
64-group sustained shard.

The modifier path now:

- gathers every visibility-LUT direction in bounded matrix blocks instead of
  dispatching one NumPy operation per ray.
- projects all Fock radii with blocked matrix operations instead of calling the
  curvature routine once per ray.
- stores far-field occluder radius and distance as `(T, 1)` invariants rather
  than repeating them across every ray.
- preserves the original float64 formulas and complete surface physics.

The atlas path now pads the 103 to 273 physical center rays to a fixed width of
288. Padded directions repeat the final valid direction, while their electric
field and every array factor are exactly zero. They therefore contribute
nothing to the channel, map, or exposure operator. The fixed shape lets JAX
compile the atlas once instead of compiling 53 distinct ray-count shapes. The
loader fails closed if a trace exceeds the declared width.

Measured progression on the identical shard was:

| Implementation | Measured 64-group wall | Speedup from original |
|---|---:|---:|
| Original lazy atlas | 796.55 s | 1.00x |
| Batched modifiers | 449.35 s | 1.77x |
| Batched modifiers plus fixed-width atlas | **240.15 s** | **3.32x** |

The final measured stage totals are:

| Stage | Final time | Share of measured wall |
|---|---:|---:|
| Fock and visibility preparation, including padding | 110.35 s | 46.0% |
| Shared center-ray body atlas | 49.17 s | 20.5% |
| MRT maps and reductions | 24.42 s | 10.2% |
| Lazy per-array Q lift | 19.66 s | 8.2% |
| UE channels and all global ECBF solves | 11.96 s | 5.0% |
| ECBF maps and reductions | 10.18 s | 4.2% |
| Body setup, ray loading, and Q transfer | 3.40 s | 1.4% |

Against the original sustained output, 73,408 compared scientific numbers had
a worst relative difference of 5.86e-11 and a 99th-percentile difference of
3.24e-14. Every discrete value, binding label, row order, and structure was
identical. The larger relative maximum is a tiny value accumulated by a
different fixed-width GEMM tiling. The largest absolute difference was
1.84e-6 in a large derived scale factor.

Concurrency was remeasured because the old four-worker result no longer
describes the optimized bottleneck. One worker took 256.63 seconds including
warm-up. Two disjoint persistent workers completed the same 64 groups in 200
seconds, a 1.28x wall-clock gain, with no discrete differences and a maximum
relative numeric difference of 5.87e-11. Four workers took 247 seconds, so
four-way contention is no longer useful on this eight-core host. The current
operating point is two workers, not four.

### System telemetry

The run was sampled every five seconds from launch to completion, plus one
second NVIDIA device telemetry for the final 11.3 minutes. The system remained
nominal throughout:

| Quantity | Typical | p95 | Peak |
|---|---:|---:|---:|
| Process-tree CPU | 1.38 cores | 1.96 cores | 2.20 cores |
| Whole-host CPU | 22.6% | 30.6% | 33.5% |
| GPU SM utilization | 0% | 51% | 100% |
| GPU power | 88 W | 122 W | 149 W |
| GPU temperature | 65 C | 66 C | 68 C |
| Process RSS | 4.22 GiB | 4.75 GiB | 4.88 GiB |
| Whole-host used RAM | 5.85 GiB | 6.36 GiB | 6.55 GiB |

Swap use was zero. The apparent 34.5 GiB VRAM use in the single-worker run was
JAX's default allocator reservation, not a live-data requirement. GPU compute
was nonzero in only 16.4% of one-second samples, with short bursts reaching
100%. There was no thermal throttling, memory pressure, or hardware-capacity
limit. One worker simply does not present enough concurrent work to the GPU or
the eight CPU cores.

### Four-worker utilization test

The identical 64 groups were then split into four disjoint persistent workers
on the same A6000. JAX preallocation was disabled so each worker allocated only
what it needed. The four workers completed in **420 seconds wall-clock**,
including four independent warm-ups, compared with 822 seconds for the serial
run including one warm-up. This is a measured **1.96x throughput gain** without
changing any physics or output scope.

The parallel run reached:

- 75.5% mean whole-host CPU, 86.0% median, and 100% peak;
- 5.33 mean occupied CPU cores, 6.22 median, and 7.98 peak;
- 13.7% mean GPU SM utilization, 98% p95, and 100% peak;
- 178 W peak GPU power against a 300 W limit;
- 69 C peak GPU temperature;
- 13.56 GiB peak VRAM;
- 12.46 GiB peak whole-host used RAM;
- zero swap and four successful worker exits.

The parallel scientific payload contained 72,576 numeric values. Of those,
63,964 were bit-identical to the serial run and the remaining values differed
by at most 2.06e-13 relative. All discrete values and structures were
identical. Four workers saturate the CPU before they saturate GPU compute or
memory, so adding still more workers on this eight-core host is not an obvious
win. This identifies CPU-side body preparation as the current bottleneck. It
does not by itself prove which remedy has the best ratio of speed, coding work,
and scientific risk.

## Streamed shadow-LUT and curvature result

The fused device modifier path has now also been implemented and measured. The
visibility model was already a baked two-dimensional octahedral shadow LUT. It
was not ray-casting against the complete mesh during each run. The expensive
mistake was expanding that compact LUT on the CPU into a full
triangle-by-center-ray clearance table before every atlas build.

The new path keeps the signed int8 LUT, active-triangle index, occluder radius,
occluder distance, principal curvatures, and principal directions compact. The
existing GPU atlas scan performs the four bilinear LUT reads and Euler curvature
projection for each triangle block. It no longer transfers or retains complete
visibility or Fock-radius tables. The geometric visibility and per-triangle
Fock radius remain the same float64 calculation.

One scalar hard-polarization Fock pole still needs a representative median
radius before the device scan. The fast path estimates that scalar from a
deterministic stratified sample of 4,096 triangles and 32 center rays. This is
the only new scientific approximation. It is explicit in the pilot record and
can be disabled by using the materialized oracle path.

On the identical 64-group Duke shard:

| Implementation | Measured wall | Speedup from prior exact path | Speedup from original |
|---|---:|---:|---:|
| Original lazy atlas | 796.55 s | 0.30x | 1.00x |
| Exact batched modifiers plus fixed width | 240.15 s | 1.00x | 3.32x |
| Streamed GPU LUT and curvature | **120.61 s** | **1.99x** | **6.60x** |

The former 110.35 second modifier stage fell to 10.28 seconds, a 10.73x stage
speedup. The center atlas also fell from 49.17 to 38.55 seconds because it no
longer reads large materialized modifier arrays. The complete new stage totals
were:

| Stage | Streamed time | Share of measured wall |
|---|---:|---:|
| Streamed visibility, curvature, and sampled scalar pole | 10.28 s | 8.5% |
| Shared center-ray body atlas | 38.55 s | 32.0% |
| MRT maps and reductions | 22.47 s | 18.6% |
| Lazy per-array Q lift | 17.91 s | 14.9% |
| UE channels and global ECBF solves | 9.69 s | 8.0% |
| ECBF maps and reductions | 9.34 s | 7.7% |
| Body setup, ray loading, and Q transfer | 3.07 s | 2.5% |

Against the exact materialized calculation, all 73,408 discrete values and
structures were identical. The 99th-percentile relative numerical difference
was 1.07e-4. The largest ordinary retention difference was 0.29%. Two
peak-coordinate fields moved substantially because a nearly tied peak selected
a different body location, while the associated physical peak values moved by
only a few parts in 100,000. This is small enough for the exploratory paper
sweep, but it is not bitwise parity and must remain disclosed.

Two persistent workers completed the same 64 groups, including two warmups, in
92.38 seconds. The comparable one-worker time was 132.56 seconds including its
warmup, so overlap adds another measured 1.43x. The two-worker output had no
discrete differences from the one-worker streamed run, a maximum relative
numeric difference of 2.80e-13, and a 99th-percentile difference of 1.64e-14.
Peak VRAM was about 5.9 GiB. GPU samples frequently reached 97 to 100% during
the atlas bursts, and the device returned to 1 MiB idle use afterward.

### Revised full-sweep projection

Multiplying the sustained Duke mean by all 9,216 body-ray groups projects to
31.86 hours for one serial A6000 worker. Scaling only the clearly
triangle-dominated stages by the actual four-phantom mean mesh size gives about
23.26 hours. This is consistent with, and narrows, the earlier 22 to 32 hour
range.

Those numbers are the pre-optimization baseline. The exact fixed-width path
projected to 7.4 hours for one persistent A6000 worker after scaling the
triangle-dominated stages by the actual four-phantom mean mesh size. Applying
the newly measured streamed-path ratio reduces that projection to about
**3.7 hours for one worker**. Applying the measured two-worker throughput gives
about **2.6 hours on this one A6000 host**. Four equivalent independent hosts
would put the projection below one hour if shards scale cleanly. These remain
projections, not campaign completion claims. The streamed projection also
contains the explicitly sampled scalar Fock-pole approximation described above.

Running every resource at 100% is neither necessary nor desirable. RAM is
capacity, not a throughput target. The useful goal is maximum certified maps
per second without swapping, throttling, OOM, or numerical drift. The old
four-worker test achieved full CPU utilization and doubled the old
pipeline's throughput. After the exact rewrite, two workers are faster and
four workers only add contention. The remaining low average GPU utilization
still leaves room for a fused device modifier path, but its ceiling is now much
smaller than it was before this implementation.

### Acceleration menu after the sustained run

The measurements narrow the choices without selecting a winner by assertion:

| Lever | Current evidence | Likely role |
|---|---|---|
| Two persistent workers and dynamic shards | Measured 1.28x after optimization | Current operating point on this eight-core A6000 host |
| Binary GO visibility | Measured 1.97x on the short shard | Strong approximation candidate, pending a larger scientific sensitivity test |
| Flat front-face physics | Measured 3.55x on the short shard | Useful lower bound, probably too crude as the sole paper model |
| CPU-batched modifier preparation | Implemented, 4.62x stage and 1.77x total | Keep |
| Fixed-width exact center atlas | Implemented, 4.72x atlas stage and 3.32x cumulative total | Keep |
| Streamed GPU shadow LUT and curvature | Implemented, 10.73x stage and 1.99x total over prior exact path | Keep for the exploratory sweep with disclosed scalar-pole sampling |
| Validated lower-frequency mesh levels | Triangle work dominates six of eight frequencies | Potentially large, but requires convergence evidence and must not weaken 60/100 GHz maps |
| Prebaked or persistent body-response cache | Does not avoid the first bake | Potentially enormous for reruns and new beam studies, with storage as the tradeoff |
| GPU-only scalar reductions for the MRT table | Map and reduction is about 7% of wall | Correct cleanup, but cannot be the next order-of-magnitude gain by itself |
| Additional GPUs | Body-ray groups are independent | Direct wall-clock reduction with little code risk |

The first exact batching pass has now been tested rather than estimated. From
the new 240.15 second baseline, making the remaining modifier and atlas stages
together 10x faster would yield about 2.5x more end-to-end speed. Eliminating
modifier preparation alone cannot yield more than 1.85x. Those are the new
ceilings, not forecasts.

Several optimizations listed in `PERFORMANCE_REDESIGN_PROMPTS.md` address the
old high-band local-APD design loop: patch factors, 126-state batching, GPU KKT,
cut discovery, and solver tolerances. They remain relevant to the small local
optimization study, but the proposed MRT and global-ECBF mega sweeps no longer
contain that loop. They therefore should not be ranked as core-sweep
accelerators.

The right next step is a short bake-off on this same sustained shard, comparing
at least GPU-batched body preparation, binary visibility, a validated
lower-frequency mesh level, and persistent atlas reuse. Rank them by certified
maps per second, implementation effort, storage, and movement of the paper's
headline quantities.

### Low-frequency loader correction

The first sustained launch stopped before measurement because the M = 256,
8 GHz physical array reconstructed with a mean x coordinate 4.44e-14 m from
the authenticated phase center, just beyond the old fixed 4e-14 m cutoff. The
physical transmitter-position hash matched exactly. This was floating-point
summation at a coordinate near -13 m, not a changed array or physics error.

The loader now derives its phase-center tolerance from 64 float64 epsilons at
the coordinate scale. The exact position hash, scene specification, array
shape, element order, and every other provenance check remain unchanged. A
new M = 256 at 8 GHz regression covers the case. The failed launch performed
no measured group and was excluded from all timings above.

## Scope arithmetic

For the complete Cartesian product:

- 2,304 distinct center ray packs;
- 9,216 body-ray bakes after multiplying by four phantoms;
- 27,648 scene/body/array items after multiplying by three arrays;
- 580,608 MRT maps from 21 positions;
- 165,888 new ECBF maps from six budgets at one position;
- 746,496 unique core maps in total.

The zero-standoff MRT reference already exists in the MRT block. Recomputing it
inside the ECBF block would add 27,648 duplicate maps but no information.

The old design produced 8,128,512 reported maps and, above 30 GHz, solved 126
iterative local-APD beam problems per item. The two-block output count is
10.9x smaller, and it removes that much larger hidden optimizer workload from
the core sweeps.

## Exact factorization result

The prior body-atlas proof of concept materialized each array-specific surface
channel:

```text
G_M = B A_M
map_M(X) = |G_M X|^2
```

The scoped pilot permits an exact lazy form:

```text
Q_M = A_M^H T A_M
map_M(X) = |B (A_M X)|^2
```

This avoids constructing the complete 56,024 x 3 x M surface channel when the
paper needs only 27 beam columns per array.

Against the materialized-channel run:

- array-lift time fell from 6.96 to 1.16 seconds, about 6.0x;
- lift plus map time fell from 8.39 to 4.32 seconds, about 1.94x;
- total pilot time fell from 50.96 to 47.18 seconds, about 1.08x;
- all 5,184 compared numeric outputs agreed within 1.26e-13 relative error;
- no string, integer, order, binding-label, or other discrete output differed.

The modest total speedup is not a failure of the factorization. It means the
factorized array stage is no longer the bottleneck.

## Where the time goes now

The measured full-physics lazy-atlas stages were:

| Stage | Four-group time | Share of measured stage time |
|---|---:|---:|
| Fock and visibility modifier preparation | 28.38 s | 60.5% |
| Shared center-ray body atlas | 12.58 s | 26.8% |
| MRT maps and reductions | 2.64 s | 5.6% |
| Lazy per-array Q lift | 1.16 s | 2.5% |
| UE channels and all global ECBF solves | 0.77 s | 1.6% |
| ECBF maps and reductions | 0.52 s | 1.1% |
| Body/averaging setup, ray loading, Q transfer | 0.87 s | 1.9% |

The original suspicion that area averaging or the six global ECBF solves were
the main cost is now disproved for this scope. The 324 complete maps, including
host transfer and sparse averaging, took 3.16 seconds. All actual UE-channel
construction and global ECBF design took 0.77 seconds.

The dominant cost is preparing and applying the detailed Fock surface model
for each new body/direction set.

## Measured physics choices

The same four-group pilot was repeated with two lower fidelity profiles. The
beam and map scope did not change.

| Surface physics | Measured wall | Duke-only full-grid projection |
|---|---:|---:|
| Full Fock plus visibility | 47.18 s | 30.2 h |
| Binary GO visibility | 23.95 s | 15.3 h |
| Flat front-face Fresnel | 13.29 s | 8.5 h |

The projection multiplies the four-group mean by 9,216 body-ray groups. It is
an intentionally conservative Duke-only estimate, not the final ETA.

The actual four-body meshes contain 23,826, 31,928, 48,196, and 56,024
triangles. Their mean is 71.4% of Duke. Scaling only the triangle-dominated
work gives a rough one-A6000 expectation of:

- **about 22 hours** for full physics;
- **about 11 hours** for binary visibility;
- **about 6 to 7 hours** for the flat lower bound.

Allowing for different ray counts, JIT shape churn, tracing, I/O, and campaign
tails, the honest current estimates are roughly **22 to 32 hours** full
physics and **11 to 17 hours** with binary visibility on one A6000. This is
about one day, not several days, for the exact full-physics two-block paper.

Binary visibility is not numerically equivalent to full Fock physics. Across
the 324 pilot cells it changed whole-body absorbed power by 1.36% at the
median, 3.39% at p95, and 3.67% at the maximum. The 4 cm2 peak changed by
0.44% at the median, 4.50% at p95, and 11.72% at the maximum. No binding
constraint changed in this small pilot. A larger sensitivity shard is needed
before adopting the faster model.

## Candidate large code wins

### 1. Move modifier preparation to the GPU

The per-direction Python loops have been removed. The current code performs
bounded dense CPU batches, which produced the measured 4.62x stage gain. The
remaining opportunity is to keep those same dense operations and their inputs
on the GPU, then feed the result directly into the atlas scan.

The production change should:

- keep principal curvatures and directional visibility LUTs device-resident;
- evaluate all Fock radii for all center directions in one batched kernel;
- gather signed clearances for all directions in one batched kernel;
- construct the surface modifier spectra on device;
- pass them directly into the atlas build without a large host round trip.

This now targets 110.35 of the final 240.15 seconds rather than 462.08 of
796.55 seconds. It remains the largest exact software candidate, but its
maximum isolated end-to-end gain is now 1.85x.

### 2. Keep the lazy atlas instead of materializing G_M

The lazy map identity is exact and has now passed real GPU/output parity. It
should become the production representation for scalar sweeps. Materialize a
full G_M only when an operation genuinely needs it.

### 3. Batch body-ray groups with a bounded padded center-ray dimension

This compile-reuse part is implemented. The sustained packs contained 103 to
273 physical center rays and now share a width of 288 with exactly zero field
and factor rows in the padding. Atlas time fell 4.72x. Batching several
independent groups into one larger dispatch could still improve occupancy, but
that is a separate step and must beat the measured two-worker process route.

### 4. Return only table scalars for the MRT mega sweep

The pilot intentionally used the existing final-map path and copied each
complete map to the host before sparse averaging. The MRT table does not need
to retain 580,608 triangle arrays. Its required maxima, target values,
whole-body integral, and concentration scalars can be reduced on the GPU.

Full maps should be transferred only for the small spatial-figure subset. This
does not attack the present largest stage, but it reduces traffic and output
pressure once modifier preparation is fixed.

## Practical campaign plan

1. Keep the exact lazy center atlas, blocked modifiers, fixed ray width, and
   their direct-route parity gates.
2. Benchmark the remaining large levers on the identical sustained shard:
   fused GPU body preparation, binary visibility, validated mesh levels, and
   persistent response caching.
3. Run a 1/16 campaign shard containing every body, frequency, condition,
   array, and UE, but one seed. This tests the dimensions omitted by the first
   pilot and gives a statistically useful throughput distribution.
4. Decide full Fock versus binary visibility from the larger shard's scientific
   sensitivity, not runtime alone.
5. If the optimized A6000 shard projects above the desired wall clock, use four
   independent GPUs. The body-ray groups are embarrassingly parallel.
6. Keep local-APD ECBF as a named small study. It is not required for the MRT
   table or the whole-body ECBF Pareto figure and should not be multiplied over
   the two core sweeps.

The measured exact implementation is now below 10 projected hours on one
A6000 worker and about 5.8 hours at the measured two-worker operating point. A
couple of hours on one A6000 still needs another large lever. A few hours on
one H100 or about 1.5 hours on four equivalent independent hosts is a
reasonable engineering target, subject to a multi-phantom shard.

## Evidence

- Exact-optimization evidence archive SHA-256:
  `6f4fb2dbf0d5be03650c2f6eb8e13f3162f7cb7f54674bc01d8e20f2073ae88d`
- Exact-optimization evidence archive:
  `/tmp/two-block-exact-optimization-evidence.tar.gz`
- Batched visibility source SHA-256:
  `8190ce758f8bb9b9dfa0c6f9a01d52aa6471c2280d032405128f2ed9abbfca62`
- Batched Fock source SHA-256:
  `8ef7a02cf8b0143f7c589459d4e3636b4daa40cccd5070c60c1dc277c5b903b0`
- Fixed-width two-block source SHA-256:
  `ec73bb6389b3e8cd503987f18d1bf75c021fd6d42503644d417cab5868d0bb0c`

- Sustained serial report SHA-256:
  `1df4a1fd6ffc1e88eb7dd7ccdd8bde9811402e6c831bd5a9751281be41bfa8f0`
- Sustained five-second telemetry SHA-256:
  `de2fae4a29fe7634c5c9a7f4aa4692e9ab627113bcb415a054c1f465e6096da5`
- Sustained one-second NVIDIA telemetry SHA-256:
  `52c63f0109ececaa50b38f96fb4372e0daab15fd1f0dceeb2cac93ca1bc88493`
- Four-worker telemetry SHA-256:
  `b2776fc906d0aa41095031a0fd6721eb6e799120a11ca19cbee171eec1294f2b`
- Four-worker NVIDIA telemetry SHA-256:
  `edcbfb288bb0ef0c7b040ca5d9caa710b12139fb1b5c9f95e662a02406e39127`
- Patched pilot loader SHA-256:
  `b07790b600b36a83268dda8c5fa1ccd66365c0d70ee4749ff4903a37d6f61a70`
- Downloaded sustained evidence directory:
  `/tmp/v2-two-block-sustained.q5tmyX/`

- Materialized full-physics report SHA-256:
  `1868f3198316f26f3b1a739c935202af8c381dbde81c1972a96d02b3002e1966`
- Lazy full-physics report SHA-256:
  `b4675e7bff1d292afc0a7115ae5e04d00e4ea1e2725cbce8c96ca683feebfec5`
- Lazy binary-visibility report SHA-256:
  `bcb2f03ef6fec759e893be4d4b33707b5a9575b9b8c0389b4912904393436d6a`
- Lazy pilot source SHA-256:
  `214f98a8afd45ad5b87d14792297e9b72aae87392e0786a058dd4fcb04341ec6`
- Downloaded reports:
  `/tmp/v2-two-block-pilot-report.json`,
  `/tmp/v2-two-block-pilot-lazy.json`,
  `/tmp/v2-two-block-pilot-visibility-lazy.json`, and
  `/tmp/v2-two-block-pilot-flat-lazy.json`.
