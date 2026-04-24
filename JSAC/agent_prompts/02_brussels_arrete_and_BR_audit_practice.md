# Agent prompt — Brussels arrêté text + BR-based audit in practice

*PoC, not a finished spec. Two linked questions that affect the JSAC paper's §I intro and §VII regulatory discussion.*

## Context

The paper's deployment hook is that **city-level EMF reference-level caps** are 10–30× tighter than ICNIRP and are the real reason mmWave deployment is slow in parts of Europe. The leading example is the Brussels-Capital Region outdoor cap of 14.57 V/m (raised in 2023–2024 from 6 V/m, explicitly to allow 5G, after a 2019 de-facto ban). An earlier round of this brainstorm sloppily claimed the Brussels cap is "enforced instantaneously every second." That is likely wrong — ICNIRP-aligned EU averaging is typically 6 min or 30 min. I need the actual arrêté text to pin this down.

Separately, ICNIRP 2020 explicitly permits compliance demonstration via *basic restriction* (BR; absorbed-power / SAR on actual bodies) *or* reference level (RL; free-space field strength at public points). IEC/IEEE 62232:2022 and ITU-T K.122 operationalize BR-based assessment. The paper's body-centric twin is, in substance, a BR-based audit. The question is whether this has any traction with a city that enforces RL only (Brussels), or whether the BR path helps only at the ICNIRP / national-standards level.

## Two linked questions

### Q1 — Brussels arrêté: exact wording

Fetch the current Brussels-Capital Region *Ordonnance* / *Arrêté* text that sets the 14.57 V/m cap. Starting points:

- environnement.brussels / leefmilieu.brussels has the French and Dutch versions.
- Official source: *Moniteur belge* / *Belgisch Staatsblad*. The relevant 2014 ordinance (raised to 6 V/m for 4G) and the 2024 update (raised to 14.57 V/m for 5G) both live here.
- Constitutional Court rulings from 2023 / 2024 on the raise.

Report **primary-source quotes, in the original French/Dutch with English gloss**, on:

1. **The numerical limit.** "14.57 V/m" — exact text, and the formula for frequency scaling if given (e.g., `3·(f/900 MHz)^(1/2)`).
2. **Averaging window.** Is it instantaneous, 6-min, 30-min, or something else? Explicit quotation.
3. **Measurement-point definition.** Is it *every publicly accessible point*, *occupied points*, or does the text qualify by "normally occupied" / "at head height" / similar?
4. **Cumulative clause.** How does the text handle multiple operators? Is the 14.57 V/m summed across all sources, per-operator budgeted, or something else?
5. **Frequency range.** Does the cap apply to all bands or is there a frequency cutoff (e.g., 400 MHz–10 GHz)?
6. **Indoor cap** (the "9.19 V/m" I have written down) — verify this and its averaging.
7. **Any explicit reference to ICNIRP 2020** or to BR-based compliance.

Feel free to quote enabling acts, royal decrees, or implementing arrêtés if the top-level ordinance defers to them.

### Q2 — BR-based audit in regulatory practice

The paper claims that **a body-centric digital-twin-based BR assessment is a legitimate compliance pathway** under existing standards. I want to know:

1. **IEC/IEEE 62232:2022 — what does it actually say on body-centric BR assessment?** Is there language on "body phantoms," "SAR assessment at base stations," "actual-exposure-scenario-based assessment"? Quote.
2. **ITU-T K.122** — same question. Does it permit / require / prohibit anything that resembles a DT-based BR audit?
3. **Any jurisdiction where RL and BR paths are legally alternative** and the operator has chosen the BR path in practice. (US FCC MPE + SAR may qualify; check UK Ofcom's guidance; check Japan.)
4. **Any jurisdiction where a BR audit has been accepted for a mmWave deployment** (macro, small cell, indoor). Hard to find, but try.
5. **Any regulator-facing mmWave exposure simulation / audit tool** in production use (Orange, Ericsson, or vendor tools). What do they actually compute — free-space PD or body SAR?
6. **Belgium specifically: has any BR-based assessment been proposed or accepted for Brussels?** If yes, what was the outcome?

## What the paper will do with the answers

**If Q1 confirms 6-min averaging, cumulative across operators, at publicly accessible points, frequency-scaled by `sqrt(f/900MHz)` up to 2 GHz (then capped)**: the paper uses the 14.57 V/m RL as the binding constraint, states averaging correctly, and shows the RL binds in the plaza scenario. The two-pronged regulatory section stands (industry-standards / ICNIRP route + Brussels statutory route).

**If Q1 says something different** (e.g., instantaneous, or not cumulative, or 30-min average): the paper rewrites the deployment-blocker paragraph accordingly and does not misrepresent the law.

**If Q2 gives concrete IEC/IEEE 62232:2022 language on BR-based audit**: the paper cites it directly in §VII and positions the twin as an *instance* of an existing standards pathway, not a new one. Extra bonus: a precedent case study.

**If Q2 comes back "no regulator has accepted BR-based audit in practice"**: the paper says so, frames the twin as a *proposed* audit protocol, and tones down the "standards already accept this" claim.

## Output format

- Q1 → a ≤ 800-word section with primary-source quotes (French/Dutch + English gloss).
- Q2 → a ≤ 800-word section with standards-text quotes and any jurisdictional precedent.
- **One-paragraph recommendation** on how the paper's §I intro should state the Brussels facts, and how §VII should frame the BR route.

Short and primary-source-heavy is better than long and speculative. If you can't find something, say "not found" — do not paraphrase. I particularly distrust secondhand descriptions of legal texts; quote the text or report missing.

## What I do NOT need

- Broader philosophical debates on EMF safety.
- Coverage of UK / Switzerland / Italy unless it illuminates the Brussels question or produces a BR-audit precedent.
- Commentary on whether the limit is "too strict" or "too loose."
