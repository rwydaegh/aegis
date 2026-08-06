# IEC 62232 and TR 62669 — where AEGIS lands

This file maps AEGIS's capabilities onto the standard structure, clause by
clause, so Robin can talk fluently about which parts of the standard AEGIS
would touch, which it would not, and where the natural entry points are.

## The three purposes of IEC 62232 (Clause 5.2)

From the standard itself and Grangeat's tutorial slide 5:

- **Purpose 1 — Product compliance (Clause 6.1)** — compliance boundary in
  free space, product type approval, before market. Applies to a single BS
  as a unit under test.
- **Purpose 2 — Product installation compliance (Clause 6.2)** — total RF
  exposure levels in accessible areas from a BS plus other sources, before
  the BS is put into operation. Applies to an installed BS in its actual
  environment.
- **Purpose 3 — In-situ RF exposure assessment (Clause 6.3)** — field
  measurement of exposure levels after the BS is in operation. Broadband +
  frequency-selective probes, extrapolation to worst-case.

**AEGIS naturally lands in Purposes 1 and 2.** Purpose 3 is measurement, not
modelling. AEGIS can *inform* Purpose 3 (predict where to measure, extrapolate
predicted values to compare to measurements), but is not itself a measurement
tool.

## Computation methods taxonomy (Clause 8.3, Annex B)

From Grangeat's tutorial slide 6, the standard splits computation into two
tiers:

- **Basic methods (B.6):** spherical model (B.3.1), cylindrical model (B.6.2.5),
  SAR estimation (B.6.3). Analytical formulas for regular geometries.
- **Advanced methods (B.7):** synthetic model + ray tracing (B.7.2), full-wave
  E,H,S (B.7.3), full-wave SAR (B.7.4). Numerical solvers on realistic
  geometries.

**AEGIS's natural taxonomic home is B.7.2 (synthetic model + ray tracing) or
adjacent to B.7.3 (full-wave E,H,S).** The framing that fits: "synthetic model
with an analytical body-surface kernel, integrated with ray-traced
illumination, differentiable end to end." Not full-wave because it does not
solve the wave equation everywhere. Not basic because it handles arbitrary
body geometry.

For the call, do NOT get into this taxonomic mapping unless he asks. If he
does: the answer is "AEGIS sits between B.7.2 and B.7.3, closer to B.7.2."

## The actual-maximum approach (Clause 6.2.3, 8.4, Annex B.9, Annex C)

**The big picture.** Prior to actual-max, base-station compliance used
theoretical maximum: assume every beam at maximum EIRP simultaneously and
continuously. Fine for a fixed-beam sector antenna, absurdly conservative for
massive MIMO where only a small fraction of the codebook is active at any
instant.

Actual-max formalises a **statistical time-averaged EIRP** based on codebook,
traffic model, and a 95th-percentile exceedance criterion over a 24-hour
window (or another averaging window per applicable regulation). The
compliance boundary is then evaluated at the *actual maximum EIRP threshold*
rather than the rated maximum EIRP.

**Nokia's own numbers on how much this shrinks compliance distance:**
- 2018 (Baracca, Weber, Wild, Grangeat) — ~50% reduction in compliance
  distance vs traditional method.
- 2023 (Rybakowski, Bechta, Grangeat, Kabacik) — 95th percentile per-beam
  transmitted power is only 7-22% of theoretical max, depending on
  beamforming algorithm.
- Default F_PR values in IEC 62232:2022 (per Ericsson's 2021 whitepaper):
  0.25 for NR massive MIMO with TDD duty cycle included, 0.32 without.
  ~-6 dB net.

**The 6-step operational process (tutorial slide 16):**

Before putting BS into operation, or when config parameters change:
1. Evaluate the CDF of actual power/EIRP over time
2. Select the applicable percentile (typically P95)
3. Determine the actual maximum EIRP threshold(s)
4. Set BS configured power and power reduction parameters

When BS is in operation:
5. Monitor and/or control the actual transmitted power or EIRP
6. Change BS config parameters or actual maximum thresholds if needed

**AEGIS's fit at each step.** Step 1 is where a fast forward model dominates:
generating the CDF requires evaluating exposure across the full codebook ×
traffic × pose configuration space. FDTD is intractable at that scale. AEGIS
can do it in minutes. Step 3 is where the differentiable envelope helps —
gradient-based selection of the threshold that maximises operational headroom
subject to the compliance bound. Steps 5-6 are Nokia's own MAC-layer work
(Cluster 2 papers).

## Simplified installation classes (E0-E+)

From tutorial slide 10-11. The five-tier simplified process:

| Class | Total EIRP | Min height | Exclusion zone | Pre-existing check |
|---|---|---|---|---|
| E0 | None | None | None (touch-compliant) | N/A |
| E2 | ≤ 2 W | None | Small CD_m | N/A |
| E10 | ≤ 10 W | 2.2 m | N/A | N/A |
| E100 | ≤ 100 W | 2.5 m | CD_m in main lobe | 5×CD_m main lobe, CD_m other |
| E+ | > 100 W | h_m (calc) | CD_m in main lobe | 5×CD_m main lobe, CD_m other |

These classes are for the *simplified* installation process (Clause 6.2.5).
Above E100, and always above 100 W, you need the general assessment process
(6.2.2 with actual-max) or the full Annex-B computational path.

**AEGIS's fit:** most 5G macro sites are E+ (100+ W actual EIRP) so they land
in the general process. Small cells at ≤ 10 W are E10 and get simplified rules
that AEGIS does not need to touch. The interesting middle is E100 dense
deployments and E+ macro cells — that is where AEGIS's speed pays back
because the compliance distances are computed per-scene.

## IEC TR 62669 — case studies

The TR is Grangeat's softer editorial channel. Non-normative, but semi-normative
in influence. His slide 30 says Ed. 3.0 has 30+ case studies from 13 national
committees, published 2025, additional content on:

- Actual-max implementation and validation
- Extrapolation of 5G massive MIMO signals
- Emerging laboratory measurement methods related to ICNIRP 2020

The full case-study map (tutorial slide 7) — reproduced here for reference,
because Robin will need to be able to cite specific clauses if the call gets
technical:

| TR clause | Annex | BS type | Evaluation type | Method |
|---|---|---|---|---|
| 6 | – | Small cells | Product compliance (6.1) | SAR measurements (B.5) |
| 7 | – | Street cell (omni) | Product compliance | SAR + field strength |
| **8** | – | **Macro BS with mMIMO** | Product compliance | **Field strength computations (B.6.2)** |
| 9 | – | Wireless link | Product compliance | Field strength computations (B.6.4) |
| 10 | A | Small cell | Installation compliance | Simplified + field strength |
| **11** | B, C | **Macro BS + mmW small cell mMIMO** | **Installation compliance** | **Computations (6.2.8), synthetic + ray trace (B.7.2), multiple segments** |
| **12** | C | General | Installation compliance | **Actual max implementation, power/EIRP counter monitoring** |
| 13 | – | General | Installation compliance | **Validation of power/EIRP control features** |
| 14 | D | Small cells | In-situ (6.3) | Field strength measurements |
| **15** | – | **Small cell mmW (FR2)** | **In-situ** | **Field strength measurements** |
| 16 | – | Macro BS | In-situ | Field strength measurements |
| 17 | – | Macro BS NR FR1 | In-situ | Field strength + extrapolation (B.8) |
| 18 | E | Macro BS | In-situ | Field strength + drone (8.2.2) |
| 19 | – | Emerging lab methods | Product compliance | Lab-based measurements (B.4.3) |

**Bolded rows are the AEGIS entry points.**

- **Clause 8 (macro BS with mMIMO product compliance)** — AEGIS could contribute
  a case study using B.6.2 (spherical/cylindrical model) as the reference and
  showing AEGIS matches within tolerance while running orders of magnitude
  faster.
- **Clause 11 (macro + mmW small cell installation)** — AEGIS's natural
  positioning as a synthetic-model-with-ray-tracing method. This is where
  Robin would tell Grangeat a matched-validation TR contribution should land.
- **Clause 12 (actual max implementation)** — this is where AEGIS's fast
  forward model changes the CDF-generation step (Step 1 of the actual-max
  process). Direct pitch to Grangeat's own core work.
- **Clause 15 (mmW small cell in-situ)** — the millimetre-wave in-situ case
  study, tutorial slide 25 shows a scan grid at 1.5 m above ground superposed
  with modelling results (Ericsson Nokia). AEGIS on the same scenario would
  be a natural comparison.

## FR3 — the frontier

FR3 (upper mid-band, 6-24 GHz) is where the actual-max evidence base is
thinnest. Nokia's Poland cluster is actively publishing there (the 2024
extreme mMIMO 10 GHz paper), and IEC 62232 will need FR3 case studies for
the next edition. This is the highest-value AEGIS pitch: "at FR3, FDTD is
compute-bound at the deployment densities you need. A fast forward model
opens the evidence base you need to defend the actual-max approach at FR3."

If Grangeat lights up on FR3, that is the win.

## Path to the standard — realistic timeline

Two channels, tiered by lift:

1. **TR 62669 case study contribution.** Non-normative, faster path. A
   matched-validation piece (AEGIS vs FDTD on a 62232 reference scenario) at
   Clause 11 or Clause 12 could land in Ed. 4.0 (successor to the 2025 Ed. 3.0)
   with a 1-2 year cycle if the working group is receptive. Grangeat has
   editorial reach here.
2. **Normative 62232 annex proposal.** Slower, higher bar. Requires a
   peer-reviewed publication, matched-validation on reference cases, formal
   contribution tabled by Wout Joseph as the WAVES delegate on the Belgian
   national committee. 3-5 year arc, next edition after 2024's Ed. 4.0.

The right question to ask Grangeat: *"Would a matched-validation piece land
better via TR 62669 Ed. 4.0 first, or via a normative annex in the successor
to 62232 Ed. 4.0? And what is the effective calendar between contribution and
published edition?"*

## Complementary standard: IEC/IEEE 63195-2 (device APD)

Not Grangeat's primary domain (63195-2 is device-side, TC106 MT?/IEEE ICES
SC4 joint), but it is the 6-100 GHz *device* absorbed power density
computation standard, which is AEGIS's technical natural home. The 2026
edition of 63195-2 is in draft. If Grangeat has a view on how 62232 will
converge with 63195-2 (both above 6 GHz they touch the same physics), that
is worth asking. Some countries (Belgium, Switzerland) run per-site aggregate
exposure assessments that combine device + base-station exposure — the two
standards meet there.
