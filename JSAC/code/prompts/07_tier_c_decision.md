# 07 — Tier-C decision (ISAC RCS or occupancy envelope)

**Goal.** Decide what to do about tier-C bystanders (the ones the BS has neither served-user telemetry nor cooperating-phone telemetry on), and either model it or commit to retreating.

This brief is **half decision, half potential coding**. It deliberately does not pre-commit which.

## Blockers

None.

## Why this matters

Paper §VI (`paper_v2.tex`) has a tier table:

| Tier | Telemetry | Source |
|---|---|---|
| A served user | position + pose | UL CSI + IMU |
| B cooperating phone | position + pose | UL pilot + IMU |
| C uncooperative bystander | **position only** | **monostatic ISAC RCS on BS aperture** |
| D undetected | envelope only | ordinance-defined exclusion |

Tier C is the load-bearing claim that monostatic ISAC at 26 GHz on an 8×8 panel can localise human-sized targets at plaza range with ~6° azimuth resolution and ~5 m range resolution. The paper asserts this without a link-budget computation, without a citation, and without a detection-rate model. ARCHEOLOGY round 3 already noted that "ISAC vital signs at plaza range *not in literature* (only ≤10 m indoor)" — so any ISAC claim sits on thin ice.

There are two clean exits:

**(a) Model it.** Implement a back-of-envelope monostatic radar link budget — body RCS at 26 GHz (~0 dBsm rough average for a standing torso, very pose-dependent), free-space two-way path loss, BS receiver noise figure, post-processing gain from coherent integration over a CPI. Output: detection probability vs range curve, plus angular/range resolution numbers that match the paper's quoted 6° / 5 m. ~1 day's work in `src/aegis/sensing/rcs.py`.

**(b) Retreat to envelope.** Drop the ISAC tier-C claim. Embrace the ordinance approach: regulators specify an occupancy assumption for sensorless regions (effectively a worst-case body density), the precoder applies the Cauchy `D ≤ 2` rank-one bound across that region, capacity is sacrificed where coverage and bystanders coexist. No code. Paper-side prose change in §VI.

Both end up coherent with the rest of the paper. The choice changes the §VI tier table and one sentence in §VII.

## What's already in place

- Nothing on the ISAC modelling side. `src/aegis/sensing/` doesn't exist yet (would be a new subpackage if option (a) wins).
- Cauchy rank-one bound machinery exists via `src/aegis/geometry/directivity.py` (`D_max`) and the operator-bound theorem in §II — that's what option (b) leans on.
- `JSAC/planning/agent_prompts/01_bystander_detection_alternatives.md` and its answer file have the agent-1 background research that informed the round-3 retreat. Read these before deciding.

## The decision the dev (or you, Robin) needs to make

Frame it as a one-page brief that answers:

1. **Link budget pass / fail.** Standing torso ~0 dBsm, two-way path loss at 50 m at 26 GHz, 30 dBm transmit, 8×8 array gain (~21 dBi each direction), BS receiver NF (~6 dB), CPI integration gain (~10 dB for a few-millisecond dwell). Does the result clear noise by enough to support 6° angular resolution with reasonable Pd / Pfa? If yes, option (a) is defensible. If not, option (b) is forced.
2. **Operating window.** Even if the link budget closes, ISAC at 26 GHz wants line-of-sight to the bystander. Plaza geometries with reflections off facades are a confound. Does the literature support detection in this regime? (Round 3's answer was "indoor, ≤10 m, not literature.")
3. **What the paper actually loses by retreating.** §VII hero figure: does the tier-C body count drop dramatically if we assume occupancy envelopes only, or is it cosmetic?

If the answer to (1) is no or (2) is "literature doesn't back this," go with (b) and document why in `JSAC/code/experiments/tier_c_decision/decision.md`. Paper rewrite is a follow-on.

If the answer is yes, do (a) — pick a minimum-viable model that produces the paper-quoted numbers and ships as `src/aegis/sensing/rcs.py` with a `detection_probability(range_m, rcs_dbsm, snr_db)` and a small validation against the radar-equation textbook case.

## Open questions for the dev

- **Whether to coherently integrate or non-coherently.** Tens of OFDM symbols within a CPI is the natural ISAC framing. Coherent gain is up to `10 log10(N)`; non-coherent is half. Pick the side that aligns with what 3GPP / Sionna would do.
- **Whether to model micro-Doppler.** The round-2 claim that respiration / heartbeat micro-Doppler gives presence detection was downgraded to "RCS presence + angular localisation only" in round 3. Don't re-litigate; if you do option (a), stop at static RCS + angular cell.
- **Where the decision artefact lives.** A `decision.md` in `JSAC/code/experiments/tier_c_decision/` is the suggested home, but a paragraph in the existing `paper_spine.md` works too. Pick.
- **Occupancy envelope numbers.** If we go (b), the paper needs at least one nominal occupancy density (people per m²) — Brussels Grand Place at peak is ~1 person / 4 m². ICNIRP doesn't specify. Brief out where that number comes from.

## What "done" looks like

Either:

- **(a) Modelled**: `src/aegis/sensing/rcs.py` with the monostatic detection model, a one-page README, a figure (`detection_vs_range.pdf`) showing Pd at the paper-quoted resolution, and validation against a textbook case that you cite. Plus a `decision.md` saying "we modelled it."

Or:

- **(b) Retreated**: a `decision.md` explaining why, citing whichever literature / link-budget calc actually justifies the call, and a one-paragraph proposed §VI tier-table rewrite for the paper team to drop in.

## What this is NOT

- A full-stack ISAC implementation. No tracking filter, no multi-target deconfliction, no clutter rejection. Just the question "can we detect the body at all."
- A vital-signs / micro-Doppler module. Round 3 killed that.
- A theoretical contribution. Either way, this brief informs §VI's tier table; it doesn't add to the paper's theory pile.
