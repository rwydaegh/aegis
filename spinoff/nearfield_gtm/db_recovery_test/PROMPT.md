# Project: the dB-recovery kill test

You are an autonomous AI physicist-engineer with full access to the AEGIS repository (`/home/user/aegis`), its monograph (`../monograph/monograph_v2.tex`), and shell/compute. Budget: roughly one focused week. This is a go/no-go measurement, not a demo. The outcome is a number, and the number is allowed to be bad.

## The question

FR2 phones back off transmit power to meet FCC power-density limits. Industry sets that back-off from worst-case assumptions evaluated in free space. AEGIS claims a body-aware, per-beam, per-grip assessment recovers usable transmit power. **How many dB, actually?**

One advisor's framing: "If it's 0.5 dB there is no company. If it's 3 dB there is." Adopt the spirit, refine the letter (see Verdict section): the test decides the *performance-recovery* value story sold to OEM engineering budgets. A separate value story (same compliance answer, 100-1000x cheaper to compute) does not depend on this test and survives a null result. Do not conflate the two in the report.

## What you have that makes this tractable (all verified, all in-repo)

`spinoff/nearfield_gtm/example_reports/` contains real certification documents pulled from public FCC filings:

- `samsung_galaxys25_a3lsms921u_pd_simulation_report_hfss_samsung.pdf` — Samsung's actual HFSS PD simulation report for the Galaxy S25 (FCC ID A3LSMS921U). It specifies: two mmWave modules, **1x5 dual-polarized patch arrays, 10 ports each (5 V-pol + 5 H-pol), 6.0 dBm per port**, bands n261 (27.925 GHz), n260 (38.5 GHz), n258 (24.8 GHz); ANSYS HFSS FEM, delta-S 0.02, 2.5 mm field grid, 4 cm² spatially averaged PD on evaluation planes at 2 mm; per-beam simulated PD vs measured PD tables (Tables 2-1..2-12). One example row: **simulated 1.466 vs measured 0.736 mW/cm²** — the accepted sim overpredicts by ~3 dB and that conservatism is folded into the power limits. The antenna CAD itself is encrypted and the Qualcomm IPLG codebook script is proprietary: you will NOT reproduce Samsung's exact numbers, and you don't need to.
- `motorola_razr5g_IHDT56ZP1_fr2_pd_sporton.pdf` — measured PD per beam/module/surface at 2 mm, and the compliance construct: **Reported PD = design target + 2.1 dB device uncertainty** (p.13 note 9), worst-case surface/distance ratios from validated simulation (p.16).
- `apple_visionpro_bcga2117_sar_pd_evaluation_element.pdf` — XR device, binding constraint is simultaneous extremity SAR at 96.2% of limit.

These documents ARE the industry baseline. You do not need to guess how back-off is set: it is written down here.

## The test, in phases

**Phase 0 — the margin-stack audit (day 1, no simulation).** From the documents above (plus more filings pulled from fcc.report if useful — plain curl works: `https://fcc.report/FCC-ID/<ID>/<doc>.pdf`), account for every dB of conservatism stacked between "physical limit of what tissue absorbs" and "power the modem is actually allowed to transmit": free-space-PD-as-proxy-for-APD, sim-overprediction folded into limits, device uncertainty adders (+2.1 dB seen), worst-case-beam and worst-case-surface selection, worst-case-grip assumption, tune-up tolerance. Output: a table of the stack with sources. This is the *upper bound* on what any better method could recover, and it is publishable from public data alone. If the stack sums to under ~1.5 dB, report that immediately — the rest of the project shrinks in importance.

**Phase 1 — a representative device model.** Build an honest stand-in: a 1x5 (or 1x4) dual-polarized 28 GHz patch array per the Samsung specs above (or a published module design from literature), placed in a phone-sized chassis at a standard position (cheek, browsing grip, body-worn per the filing test positions). Generate a codebook the way phased arrays do (steering vectors over the scan range, both polarizations, plus a few beam-pair combinations). Document every assumption. The conclusion must be about the *method delta*, robust to the array details — check sensitivity by varying the array (element count, spacing) and showing the delta is stable.

**Phase 2 — the industry baseline, reconstructed faithfully.** For every beam in the codebook: free-space 4 cm² averaged psPD on evaluation planes at 2 mm from each surface (the filings' procedure), worst case over surfaces, sim-conservatism and uncertainty adders as the filings apply them, then the per-beam input power limit at the 10 W/m² FCC limit. This is the back-off the industry ships. No strawman: implement the actual procedure from the reports, including per-beam limits (industry is NOT a single static back-off — Qualcomm Smart Transmit is already per-beam; the baseline must include that or the comparison is dishonest).

**Phase 3 — the AEGIS assessment.** Same codebook, same positions, but with the body present: APD on the actual anatomical surface (phantoms in `data/`, note they are in meters), per beam x grip/position set (cheek left/right, hand grips, body-worn, hotspot distances per the filings). Compute the allowed input power against the equivalent basic restriction. Mind the physics honestly: AEGIS is valid in the radiating near field (reactive boundary ~1.7 mm at 28 GHz, so 2+ mm separations are in-regime but marginal at the closest distance — quantify, don't hand-wave); spot-check at least one configuration against a reference (layered-skin analytic, Mie, or an open full-wave solver) before trusting the sweep. Check what near-field illumination AEGIS currently supports before starting (the monograph's radiating near-field section vs what `src/aegis/` implements); build the minimal missing piece if needed, and if that piece is large, STOP and report scope before building.

**Phase 4 — the number.** For each beam x grip: recoverable dB = AEGIS-allowed power minus baseline-allowed power at equal protection. Report the full distribution, not just the median: median, quartiles, and the tail (a fat tail at 4-6 dB for specific beam-grip combinations is a *dynamic power control* product story even if the median is modest). Decompose the recovered dB by source: (a) proxy-vs-APD physics, (b) sim-overprediction margin, (c) grip-awareness vs worst-case grip, (d) uncertainty stacking. Each component has a different commercial and regulatory meaning.

## Interpretation rules (write these into the report)

- Recovered dB is only monetizable through a regulatory path: FCC accepts case-by-case KDB inquiries, IEC/IEEE 63195-4 (computational APD) is in drafting, EU RED is self-declaration, ISED has codified simulation procedures. Component (a) needs the APD transition to land; component (c) is closest to today's practice (sensor-driven back-off is already on the FCC PAG list, precedent exists); component (b) is capturable by any better-validated simulation, including incumbents'. Say which part of the recovered dB is AEGIS-specific.
- Uplink dB is the currency OEM antenna teams think in. 1 dB of allowed FR2 uplink is a real engineering prize (link budget, coverage, battery). Frame the result in their units.

## Verdict thresholds

- Median recoverable, AEGIS-attributable dB < 1: the performance-recovery story is dead. Say so plainly. The cheap-sweep story stands on its own and the report should not spin.
- 1-2 dB: marginal. Worth one paragraph in the IOF as upside, not a pillar.
- >= 3 dB median, or >= 5 dB for a meaningful tail of configurations: this is the company. Draft the one-paragraph IOF insert and the one-figure summary the same day.

## Deliverables

`~/db_recovery_test/` (own git repo, outside aegis unless AEGIS code changes are needed, in which case branch): `REPORT.md` (the number, the distribution figure, the decomposition table, the margin-stack audit, all assumptions, the verdict, no spin), reproducible scripts, and `IOF_PARAGRAPH.md` if and only if the result clears 1 dB. Figures follow `theory/scripts/_plot_style.py` conventions if used inside the paper ecosystem, otherwise clean matplotlib defaults.

## Rules

- The result is allowed to kill the story. A clean 0.5 dB answer in week 0 is worth more than a mushy 3 dB answer in month 18.
- No strawman baselines, no cherry-picked grips, no quoting the tail as the headline.
- Every physics shortcut gets a validity check or an explicit caveat.
- If blocked (missing AEGIS capability that is genuinely large, phantom/mesh issues, reference-solver access), report NEEDS_CONTEXT with specifics instead of degrading quality silently.
