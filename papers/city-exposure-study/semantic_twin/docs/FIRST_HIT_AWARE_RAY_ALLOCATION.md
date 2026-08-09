# First-hit-aware ray allocation

This note describes an experiment, not a production change. The current
production estimator launches 200,000 primary rays and deposits them into
4,096 passive output directions. The launch is either IID or a rotated
Fibonacci sequence. The first-hit map is not currently reused to change that
allocation.

## What is already separate

Sky misses are cheap, but they are not all interchangeable. A miss can be
discarded for a bounced roofline next-event-estimation (NEE) contribution.
Escape diagnostics still need their angular field, including its sky portion,
so sky culling must not silently remove those measurements. Exact direct
rooftop sources and the deterministic one-reflection specular solve are also
separate from the stochastic NEE allocation. They should not be counted as
primary-ray savings from this experiment.

## Why a first-hit map is not enough

A 4,096-cell direction grid is an output partition, not a proof that every
direction inside a cell has the same path. A cell can straddle a roof edge,
wall edge, or a narrow occluder. One representative direction can therefore
misclassify the rest of the cell. The current uniform-sphere NEE estimator is
unbiased because each sampled ray carries the appropriate solid-angle weight.
Any adaptive allocation must preserve that normalization with the actual
proposal probability for each ray.

The first implementation should therefore be a defensive mixture proposal.
Keep a nonzero baseline probability for every direction and add a proposal
based on the pilot first-hit map. The estimator then uses the mixture density,
not the pilot density alone. This retains support for missed boundaries and
keeps the existing IID or rotated-Fibonacci launch available as the baseline.

## Staged design

1. **Defensive mixture importance sampling.** Run a small pilot, classify
   directions by first-hit outcome, and form a proposal that mixes the pilot
   allocation with the existing uniform proposal. Give the uniform component
   a fixed positive weight. Validate the weighted NEE contribution against
   the current estimator before adding any cost model.

2. **Nested equal-area strata.** Subdivide each output cell into equal-solid-
   angle strata. Refine cells whose pilot samples disagree or whose first-hit
   labels change across the cell. Treat a cell as sky only after its sampled
   strata support that label. This avoids turning a coarse-cell miss into an
   unsafe all-or-nothing cull.

3. **Cost-aware Neyman allocation.** After the pilot, estimate both variance
   and tracing cost for each stratum. Allocate the next batch in proportion
   to the estimated variance reduction per unit cost, while retaining the
   defensive baseline. The allocation is for the stochastic NEE suffix only.
   Exact direct rooftop terms and the deterministic specular solve remain
   explicit terms in the result.

4. **Separate escape diagnostics.** Keep a fixed, independently reproducible
   sampling rule for the escape-direction field. Report its sky fraction and
   angular error separately from NEE timing. A faster NEE trace must not be
   presented as a faster or sparser escape diagnostic.

5. **Conservative certification later.** Only after the mixture estimator and
   nested strata agree with the baseline should we consider a certified
   zero-work rule for a region. Such a rule would need a conservative proof
   that the entire region is sky or otherwise contributes no term. It is not
   part of the first implementation.

## Expected scale of the saving

The Korenmarkt pilot has a sky fraction of approximately 0.227. Even an
idealized sky-only cull would therefore reduce the counted ray set by a
factor of at most

$$
\frac{1}{1 - 0.227} \approx 1.29.
$$

The wall-time gain will be smaller because a sky miss is already cheap and
the cull applies only to the bounced roofline NEE suffix. This does not support
a 390x claim. That ratio comes from comparing an older 1.6 million-ray
figure with 4,096 cells and assumes one useful ray per cell with no boundary,
variance, or other estimator cost. It is not the current production ratio.

## Benchmark before any default change

Benchmark Korenmarkt and Prague at 50,000, 100,000, and 200,000 primary rays.
Run eight independent seeds for the screening pass, then repeat the final
comparison with 16 seeds. For each site and ray count, record:

- scalar absorbed-power and source-term errors against the current estimator,
- angular-field error, including the sky sector and the active sectors,
- total wall time and the time spent in pilot, classification, NEE, and
  post-processing,
- accepted-path counts and the number of rays reaching each bounce.

Report the mean, standard error, and worst seed for scalar and angular
quantities. Keep the current estimator as the control. The experiment must
not alter production defaults, published seeds, or cached production outputs
until these comparisons show both numerical agreement and a repeatable cost
benefit.
