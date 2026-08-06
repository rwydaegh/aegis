# Microenvironment audit and walk-CDF stopping rule

Date: 2026-08-05

The checkout supports a useful four-site semantic comparison: Korenmarkt, Prague
Staromestske, Tokyo Hachiko, and Mexico Zocalo. These sites have 250 m meshes,
panorama-derived walk bindings, and matched four-seed exposure runs. Only Hachiko
is a true street canyon in this set. A strict request for several non-plaza street
types needs more registration work.

This audit uses labels already stored in
`outputs/city_screening/screening.json`. It does not infer a building type from a
city name or an image.

## Recommended comparison set

| Site | Stored built-form evidence | Runnable evidence | Scientific role | Main limit |
| --- | --- | --- | --- | --- |
| Korenmarkt | Medieval brick square and car-track capture | 250 m f64 mesh with 617,091 triangles. The v1 atlas uses 9 cameras. Four matched runs use 80 locations, 200,000 rays, 512 cells, and seeds 7 to 10. The final route uses 5 cameras, 8 interpolated points, 1.6 million rays, and 4,096 cells. | Current high-fidelity anchor | This is the sealed v1 baseline. It is not binding-matched to the legacy city runs. |
| Prague Staromestske | Irregular medieval square with gothic towers and a plaster and stone mix | 250 m f64 mesh with 664,619 triangles. The strict v2 gate admits 12 of 14 stations. Four matched walk runs use the same 80-location, 200,000-ray, 512-cell design. | Irregular historic enclosure | The current pose diagnostics name the 130 m support mesh. A 250 m registration pass is still required. |
| Tokyo Hachiko | Dense glass canyon with a scramble crossing and heavy signage | 250 m f64 mesh with 797,615 triangles. The old binding used three stations. Strict v2 admission retains two. | Dense canyon diagnostic | Two cameras cover 2.72 percent of faces and 7.19 percent of area. This is too thin for a production material claim. |
| Mexico Zocalo | Very large open plaza with volcanic stone and low surrounding blocks | 250 m f64 mesh with 707,812 triangles. The semantic binding admits 12 of 14 stations. Four matched walk runs use the common design. | Open reference endpoint | This is an open plaza, not a non-plaza street type. |

The screening inventory also records useful acquisition context. The total
panorama counts are 66 for Korenmarkt, 228 for Prague, 277 for Hachiko, and 388
for Zocalo. Their selected walk candidate counts are 14, 147, 105, and 253,
respectively. The semantic source binding uses only the registered and admitted
subset, so the larger screening counts do not imply matching semantic coverage.

## Strict non-plaza reading

Hachiko is the only true canyon in the matched set, but it is not production
ready under strict admission. Times Square
is the strongest second canyon candidate. Its stored label is "deep glass and LED
canyon, tallest aspect ratio in the set." It also has a 250 m mesh with 1,064,389
triangles. The geometry inventory gives a median sky fraction of 0.121 and a
214.8 m skyline height, which makes it a strong enclosure extreme.

Times Square is currently suitable only as a geometry-controlled diagnostic. Its
site registration residual is about 10 degrees, above the 4 degree semantic gate,
and no site-semantic binding was produced. Existing exposure runs use the generic
`geometric` binding and force the facade class to brick. They cannot test a glass
and LED material claim. Repairing the registration would add a second true canyon
without changing the study question.

London is less ready because it lacks a site registration summary and site
semantic output. Krakow and Toulouse have acquisition or anchor defects in the
current artifacts. They should not enter a production comparison yet.

## Binding choice

There are two valid comparisons, and they answer different questions.

1. Use the common `geometric` binding for a controlled morphology study. Materials
   remain generic, so conclusions should be about geometry and enclosure.

2. Use the matched `walk` runs for the four semantic sites, or rebuild the same
   atlas design for every site, for a material-aware study.

The final Korenmarkt result uses an `atlas` binding. Its absolute difference from
a legacy `walk` or `geometric` city run cannot be assigned to built form alone.

## Strict production status

Both candidate sites have valid format-version-3 meshes at 250 m. Old notes
about single-precision defects are stale. The unsuffixed and `_f64` 250 m files
are byte-identical at both sites.

| Site | Exact 250 m exposure mesh | SHA-256 | Current route preview |
| --- | --- | --- | --- |
| Tokyo Hachiko | `data/geometry/tokyo_hachiko/inhouse_leaf_250m_f64.ply` | `1bccad9bedd7c1764e15d06042b0340530e795396f15f6d3fc40a759f3249e71` | Strict v2 retains 2 cameras, 44.126 m apart in plan. The old 23-point route and its hash belong to the three-camera v1 input and are not a v2 route. |
| Prague Staromestske | `data/geometry/prague_staromestske/inhouse_leaf_250m_f64.ply` | `a2533b5d589f3604b63e905a5673873df2db7a41d396c8cef03389e72d08b6f4` | Strict v2 admits 12 cameras. The current 68-point preview remains preproduction until the poses are fitted and diagnosed against the 250 m mesh. |

### Completed evidence

Hachiko's residuals are 1.420, 3.700, and 3.082 degrees. The middle pose reached
the vertical search bound. Admission v2 rejects it even though its residual is
below 4 degrees. The two retained cameras cover 21,673 faces, or 2.72 percent of
the mesh, and 7.19 percent of its area. The median support remains one camera per
seen face. This two-camera route is a no-go for production. The existing binding
hashes, `0c5541dbcee2d94eb0e24b82946ca429cdece2e059dc8b255e726905a2637d81`
for NPZ and `bb9672208d05728f75934febb61c8c48b899ff0e8076f97a65049e9fa58cbdb6`
for JSON, describe the three-camera v1 artifact.

Prague passes strict v2 with 12 cameras. `pano_03` fails the residual gate and
`pano_05` has the paired inside-geometry signature: a sky-hit fraction of 1.0 at
a median range of 0.559 m. None of the 12 admitted cameras is at the altitude
bound. The current 250 m binding covers 6.71 percent of faces and 9.93 percent of
area. Its NPZ SHA-256 is
`fc01fdb06f51a900c3edb92f138d96abf36747b67915979ccade1166b4dd5147` and
its JSON SHA-256 is
`906a79e8246bd98239957c1289d36edd9ad263bea979744df6b75930e07d6bcf`.
The pose diagnostics still name the 130 m support mesh, so these are audited
preproduction hashes rather than a sealed 250 m contract.

Times Square is a no-go. All 14 residuals exceed 4 degrees, five fits end at the
altitude bound, and three cameras have the paired inside-geometry signature.
Widening the vertical search does not produce a useful interior optimum.

Korenmarkt remains the sealed admission-v1 baseline. Its atlas contains nine
admitted cameras and its final route uses five. Applying v2 would retain four
atlas cameras and two route cameras. Every removal is caused by the new
altitude-bound rule. The existing contract and results remain readable under v1
while the five bound fits are audited and, if needed, rebuilt.

### Pending GPU work

Prague still needs a 250 m registration and diagnostic pass. Hachiko needs a
wider outdoor acquisition before another production attempt. Neither site has
the complete hybrid SAM3 RF-material product or a joint atlas. The SAM3 model
download also needs an authorized credential on the GPU host. Until that access
and the missing artifacts are present, both sites remain preproduction. No CUDA
reference or named production contract should be generated from the current
inputs.

## Sequential stopping rule for a fixed walk

The independent Monte Carlo unit should be one complete walk replica with a new
base seed. Within a replica, standpoint `i` keeps the current deterministic seed
mapping `base_seed + 1000 * i`. The four 400,000-ray transfer chunks in the final
Korenmarkt run are implementation chunks, not independent replicas. They should
not be counted as four batches unless disjoint random streams and chunk-level
results are recorded and verified.

Use at least 16 complete replicas at the production setting of 1.6 million rays
and 4,096 cells. Treat 8 replicas as diagnostic. Check at 16, 24, and 32 replicas.
Stop after two consecutive checks pass. This makes 24 the earliest stopping point.
Cap the first campaign at 32 and report residual uncertainty if the rule still
fails.

At every check, average exposure in linear power across seeds for each standpoint.
Convert the resulting mean to dB. Do not average dB values. Resample complete base
seed replicas as clusters, while preserving all 13 standpoint values in each
resampled replica.

The confidence target is 95 percent over selection among the three formal
looks. Spend alpha equally over the fixed looks at 16, 24, and 32 replicas.
Each formal look therefore uses alpha 1/60 and a 59/60, or 98.333 percent,
joint max-t bootstrap band. A Bonferroni bound limits the chance that any formal
look family misses to 1/20 if each bootstrap band attains its nominal coverage.
The max-t bootstrap is approximate at finite replica count. This is nominal
familywise coverage rather than an exact finite-sample confidence sequence.
The 8-replica diagnostic has no role in this coverage claim or the stop.

Use one cluster resample and one studentized maximum for the whole bounded
family at a formal look. The family contains total susceptibility for all three
source laws, rooftop mean absorbed density, and every rooftop surface
absorbed-density mean. It also includes each fixed-route CDF rank and the
minimum, q10, q50, q90, and maximum summaries for the scalar curves. Direct
susceptibility stays outside this family because a true direct-path zero has no
finite dB value.

Require all three source laws to pass these alpha-spent bootstrap criteria:

- Across the 13 standpoints, the 90th percentile of per-standpoint confidence
  half-widths is at most 0.10 dB. The largest half-width is at most 0.15 dB.

- For the fixed-route CDF, the median half-width is at most 0.05 dB. The q10 and
  q90 half-widths are at most 0.10 dB. The minimum and maximum half-widths are at
  most 0.15 dB.

- Between consecutive checks, the one-dimensional Wasserstein distance is at most
  0.03 dB. The median moves by at most 0.03 dB. q10 and q90 move by at most 0.05
  dB. The minimum and maximum move by at most 0.10 dB.

Keep the minimum, second-lowest, second-highest, and maximum in the output. Do not
trim or winsorize endpoints. If body peak absorbed power is reported, apply a
0.15 dB maximum confidence half-width rule to it in the same joint family.
Define the published body-peak estimator as the maximum absorbed density of the
ensemble-mean angular spectrum. At level 2, average the retained per-replica
surface fields before taking that maximum. Do not average the per-replica
maxima. That order has a positive Jensen and peak-selection bias.

Build one simultaneous band over every surface mean, then project it through
the maximum. The body-peak lower bound is the maximum of the face lower bounds.
The upper bound is the maximum of the face upper bounds. This construction
still covers the peak when two or more faces tie, conditional on coverage of
the joint face band. Bootstrap winner fractions and leave-one-replica-out
winners are useful regularity diagnostics. They do not carry the formal
coverage claim.

Keep exact direct-path zeros in linear units. Report the fraction of fixed-route
standpoints whose direct estimate is zero as a probability atom at zero. Do not
add a logarithmic floor or pseudo-count. Report dB values only for positive
direct estimates and make no confidence claim for that diagnostic curve.

## What the 13-point CDF means

The final Korenmarkt walk covers 49.2 m with 13 frozen positions. Its empirical
CDF has steps of 1/13, or 0.0769. A p95 or p99 value is therefore an interpolation
near one endpoint. Report q10, q50, q90, and both endpoints as results conditional
on this fixed route.

The positions are spatially correlated. Extra ray seeds reduce Monte Carlo error,
but they do not add independent street samples. A population claim about a
microenvironment needs new route fragments. A reasonable exploratory minimum is
four separate fragments and at least 40 total positions, with equal fragment
weight. About 100 positions is a safer target for a p90 claim because it gives
roughly ten observations in the upper tenth. In a pooled city result, weight sites
or route fragments equally so that the longest walk does not dominate.

## Evidence behind the thresholds

The existing angular study supports the production resolution. At 4,096 cells,
the largest change in scalar chi from 800,000 to 1.6 million rays is 0.0041 dB,
while the peak direction can still move by 4.78 degrees. At 1.6 million rays, a
512-cell result differs from 4,096 cells by only 0.0048 dB in chi, but by as much
as 0.697 dB in top-one-percent share and 1.817 dB in peak angular density. The
4,096-cell setting matters for angular peaks and tails.

Existing 200,000-ray Monte Carlo runs also show why a four-seed CDF is too small.
Korenmarkt's 32-seed walk-median standard deviations are 0.003, 0.026, and 0.039
dB for isotropic, rooftop, and street laws. New York's eight-seed values are
0.008, 0.031, and 0.094 dB. Across the four matched Hachiko seeds, the street-law
walk median spans 0.853 dB, compared with 0.069 dB in Prague. These values are
diagnostics, not proof of convergence. They justify independent full-walk
replicas and an explicit tail-preserving stop.

Key artifacts are:

- `outputs/exposure_korenmarkt/final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz_manifest.json`

- `outputs/angular_convergence_4096_atlas_v2/`

- `outputs/site_semantics/<site>/walk_semantic_250m.json`

- `outputs/exposure_korenmarkt/ladder250_<site>_s<seed>_walk_15ghz_manifest.json`

- `outputs/city_screening/screening.json`
