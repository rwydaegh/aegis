# Tier-C bystander detection — decision

*Companion to `JSAC/code/prompts/07_tier_c_decision.md`. Author: Claude (model `claude-opus-4-7`), 2026-05-04. Sources: `paper_v2.tex`, `brainstorm_opus_round3.md`, `JSAC/planning/agent_prompts/01_bystander_detection_alternatives_answer.md`, plus a fresh link-budget computation in `detection_vs_range.py`.*

## Decision: option (a) — model it, with two corrections to the paper

We **keep the tier-C ISAC row** in the §VI tier table and back it with a closed-form monostatic radar link budget. The link budget closes by a comfortable margin at the paper's plaza range, so a tier-C row is defensible. **However the paper's quoted resolution numbers in §VI are wrong** — the honest numbers are 12.7° azimuth and 0.375 m range, not 6° and 5 m. The §VI prose needs a one-line edit, drafted at the bottom of this file.

We do **not** retreat to the pure occupancy-envelope framing (option b). That option survives in the table as the **tier-D** row already, where it belongs — the regulator-defined fallback for the part of the cell that the BS panel cannot see at all (sensing blind spots behind facades, rooftop shadows, etc.). Tier C and tier D therefore stack: ISAC sectors what is sensed, occupancy envelope covers what isn't. Both sit on the precoder with a Cauchy worst-case pose, so the operational story is uniform regardless of source.

## Why (a)

### 1. The link budget closes at plaza range with comfortable margin

Operating point fixed from `paper_v2.tex` §VII.A: 26 GHz carrier, 8x8 panel (~21 dBi), 30 dBm transmit (51 dBm EIRP), 400 MHz NR FR2 carrier, 6 dB receiver noise figure, 1 m² standing-torso RCS (Marchetti et al. 2017; Chen et al. 2018, both 26/79 GHz pedestrian RCS measurements), Pfa = 1e-6, Albersheim Pd (Swerling-0).

Single-snapshot SNR at 50 m: **14.3 dB**. With a 10 ms coherent processing interval at NR numerology μ = 2 (60 kHz subcarrier spacing → 600 OFDM symbols), CPI gain is 27.8 dB and integrated SNR hits **42.1 dB**. Albersheim Pd at that SNR for Pfa=1e-6 is indistinguishable from 1.0 (table values: 13.2 dB delivers Pd = 0.9; we are 29 dB above that). Even the most stringent CPI choice considered (1 ms / 60 symbols → 17.8 dB CPI gain, 32.0 dB integrated) keeps Pd ≈ 1 at 50 m and only crosses Pd = 0.9 around 137 m.

Numerical summary: `link_budget.json`. Two-panel figure: `detection_vs_range.pdf`.

This is a back-of-envelope. It does not include clutter (multipath off facades, ground bounce, vegetation), antenna sidelobes leaking into clutter cells, swerling-1 fluctuation loss, or the actual NR DL waveform's processing penalties. A realistic operating regime sits maybe 5–10 dB below the link-budget number. Even so, the margin to the Pd = 0.9 floor at 50 m is **>20 dB**, which is more than enough headroom.

### 2. The 8x8 aperture **does** localise to a sector — just a coarser sector than the paper claims

Two number errors in the current §VI prose, which `link_budget.json` makes explicit:

| Quantity | Paper §VI claim | Honest value | Source of error |
|---|---|---|---|
| Azimuth resolution | ~6° | **12.69°** (HPBW = 0.886·λ/D, D = 8·λ/2) | Off by 2x |
| Range resolution | ~5 m | **0.375 m** at 400 MHz, ~5 m only at SSB-band 30 MHz | The 5 m value implicitly assumes synchronisation-band-only processing |

At 50 m, 12.69° HPBW gives an **11.07 m crossrange** cell; the cell footprint is 11.07 × 0.375 = 4.15 m². Brussels Grand Place peak density is ~0.25 bodies / m² (Fruin LoS C–D; cf. `occupancy_envelope_density("brussels_grand_place_peak")`), so each cell holds about **one bystander on average** at peak crowding. That's the right granularity for "I know there's *a* body in this sector, I budget the precoder for one Cauchy worst-case body in this sector." Multiple bodies within one cell either (i) get a worst-case-of-N treatment or (ii) get unresolved by this aperture and fall through to a slightly larger budget — no big deal.

If the paper wanted body-scale localisation (sub-metre) it would need ~32x32 (Schmid 2019: superresolution helps but only buys a factor of 2–3 at SNRs we have). 32x32 is a different paper. For tier C as written, sector-scale is enough.

### 3. The literature does not have a peer-reviewed plaza-scale demonstration, but the link budget is textbook

Agent-1's background research (`01_bystander_detection_alternatives_answer.md`) confirms:
- The radar equation closes for pedestrian RCS at 26 GHz at 50–70 m.
- The Ericsson 2024 NR-DL bistatic demo achieves 99.7% human-zone detection — but indoors, with multi-panel geometry.
- No outdoor ≥50 m demo with an 8x8-class single panel exists in the peer-reviewed literature.

So the honest story is: monostatic detection of a 1 m² target on a 21 dBi monostatic panel at 50 m is a **standard textbook radar problem** with comfortable margin, but no one has yet published a plaza-scale ISAC field trial at this scale. The paper should cite the link budget (now in `aegis.sensing`), cite the indoor / vehicular ISAC trials that establish the underlying processing, and not claim a field measurement.

### 4. Tier D as the fallback layer is preserved

This decision does **not** delete tier D. The two-row architecture is what survives:

- **Tier C** (ISAC RCS detected): one body per ~4 m² resolution cell, Cauchy worst-case pose, precoder budgets the cell.
- **Tier D** (sensing blind spot or occluded): regulator-defined occupancy envelope across the unsensed region, Cauchy worst-case pose, precoder budgets the region. `occupancy_envelope_density(region)` provides Fruin-anchored numerical defaults (0.05 / 0.25 / 0.5 / 1.0 bodies/m²).

The ordinance approach the prompt's option (b) describes therefore lives — it is just where it always was: tier D, not tier C.

## What was actually built

| Artefact | Role |
|---|---|
| `src/aegis/sensing/__init__.py` + `rcs.py` | Closed-form link budget, Albersheim Pd, ULA HPBW, range/cross-range resolution, Fruin-anchored density presets. ~250 LOC, no GPU dependence. |
| `tests/test_sensing_rcs.py` | 19 tests: range/azimuth resolution against textbook formulas; radar equation against hand-computed reference; Albersheim Pd against Skolnik table at Pfa=1e-6; density preset ordering and validators. |
| `JSAC/code/experiments/tier_c_decision/detection_vs_range.py` | Reproduces the figure, dumps `link_budget.json`. Run from repo root with `PYTHONPATH=src`. |
| `detection_vs_range.{pdf,png}` | Two-panel figure: integrated SNR vs range and Pd vs range, three CPI choices, plaza-range annotation. |
| `link_budget.json` | Dump of operating point + geometry + SNR + Pd at 50 m. The ground-truth numbers cited above. |

This is not a tracker, not a multi-target deconfliction module, not a clutter rejector, not a micro-Doppler module. The brief explicitly capped the deliverable at "can we detect the body at all" and the module honours that.

## Open questions surfaced during the link-budget pass

1. **Coherent vs non-coherent integration.** I used coherent (Swerling-0). 3GPP's ISAC studies typically blend coherent within a slot and non-coherent across slots. The link budget closes either way at 50 m by ≥10 dB, so this isn't load-bearing for the paper.
2. **Whether to extend to bistatic.** The Ericsson NR-DL trial used bistatic geometry; agent-1 ranked monostatic-on-BS as the cleanest tier-C lever. Extending to bistatic would let two cooperating BSs cross-fix bystanders, but it doubles the deployment story. Recommend leaving as future-work footnote.
3. **Clutter floor at plaza range.** Plaza facades return at multiple hundreds of m² RCS; multi-bounce ground returns are similar. The 5–10 dB clutter penalty I budgeted above is plausible but unmeasured. Honest paper text: "link budget admits clutter penalty up to 20 dB without losing detection at 50 m."

## Proposed §VI prose edit (drop-in)

Replace the second paragraph of §VI.A (current paper_v2.tex line 836–846) with the following text. The tier table itself is correct and stays as-is.

> Tiers A/B deliver pose via the on-phone IMU stream, reconstructed on the phone by standard inertial filters~\cite{Madgwick2011,VQF2022} and streamed via the MNO app; the BS receives pose at $\sim 100$~ms cadence. Tier C receives position from BS-side ISAC RCS detection, which on the 8$\times$8 aperture at 26~GHz delivers an $\sim 12.7^{\circ}$ azimuth half-power beamwidth and a 0.375~m range resolution at the 400~MHz NR~FR2 carrier (5~m only if the processing is restricted to the SSB sync band). At a 50~m plaza range this produces an $\sim 11 \times 0.4$~m resolution cell, comparable to the per-body footprint at Brussels Grand Place peak crowding ($\sim 0.25$ bodies\,/m$^2$, Fruin LoS~C--D). The link budget closes with $> 30$~dB integrated-SNR margin against a 1~m$^2$ standing-torso target at 50~m for a 10~ms coherent processing interval (back-of-envelope in \texttt{aegis.sensing}; $P_d \to 1$ at $P_\mathrm{fa}=10^{-6}$). Per-cell, the precoder budgets exposure for one Cauchy worst-case bystander; the $D \le 2$ rank-one bound from Theorem~2 covers any pose within the cell. Tier D is the regulatory fallback for sensing blind spots: the fraction of public space outside the BS aperture's coverage cone is treated as a worst-case envelope with a regulator-supplied occupancy density (default $0.25$\,bodies\,/m$^2$ following Brussels Grand Place peak), the classical exclusion-zone approach restricted to sensing-blind regions.

Two existing claims in the §VI tier table itself (`tab:tiers`, line 820 of `paper_v2.tex`) are unchanged. The §VI.A prose change above is the entirety of the paper edit.

## What this decision is NOT

- A measurement. We do not have a 50 m outdoor pedestrian-on-aperture trial. The link budget is theory + textbook RCS values. The paper text above frames it that way.
- A multi-target tracker. Multiple bystanders within one resolution cell are budgeted as one worst-case Cauchy body, not resolved.
- A vital-signs / micro-Doppler module. Round 3 killed that. We do not re-litigate.
- A deletion of tier D. Tier D survives as the unsensed-region fallback, drawing on the new `occupancy_envelope_density` preset table.
