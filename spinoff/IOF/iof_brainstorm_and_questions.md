# IOF StarTT: brainstorm, rank-ordering, and the questions that actually matter

*Claude Opus 4.8, 21 June 2026. Written after reading the IOF form skeleton, the official software-handvaten guidance, both funded example proposals (Unisens, EIoT, including Wout's highlights), the IDF and its review/hallucination notes, the patent landscape, the full outreach dossier, the personal/career/co-founder files, the funding-stack analysis, and today's ZMT market analysis. This is an opinion piece plus a working map, not a summary. The last section is a battery of questions for you. Goal: get you through the IOF and, more importantly, not waste two of your prime years on a zombie.*

---

## 0. The one-paragraph situation (June 2026)

You have an unusually strong technical asset (AEGIS: deployed viewer, ~28k Python, 2,469 tests, a real monograph, npj paper, IDF filed as P2026/040 with sole inventorship). You have a promotor (Wout) who sits on exactly the standards bodies that matter and who has already won this exact grant (Unisens, EIoT both came out of WAVES). You have a clean, mostly non-dilutive funding path (VLAIO + IOF + istart). And you have almost zero commercial traction: one polite email reply from Hirata, no calls held, no LOIs, no signed partners, and a ZMT channel that your own June note says is "dead since Wout said it himself." The IOF intake meeting and the 3 August deadline are the next hard gates. The binding constraint on this whole enterprise is not the physics, the market, or the money. It is that you have not yet pulled the trigger on talking to customers, and the IOF proposal is graded substantially on exactly that evidence.

---

## 1. What IOF StarTT actually rewards (the real rubric)

Forget the form's section list for a second. From the two funded proposals, the guidance doc, and what Wout physically highlighted in Unisens, the scoring reduces to five things, in order of how much they move the needle:

1. **Demand you can prove is non-optional.** Wout's single most-highlighted theme in Unisens was the *legal mandate*: "this is mandatory", "legal obligation", "most EU countries need monitoring". Your equivalent exists and is strong: ICNIRP 2020, IEC 62232:2025, IEC/IEEE 63195-2, FCC APD rules. Every mmWave device and every base station legally *must* demonstrate compliance. Lead with the obligation, not the opportunity.

2. **A customer who already said yes, in writing.** Wout highlighted "Fluvius already requested a prototype" twice. This is the highest-leverage single artifact in the whole application and the one you do not have. A letter of support from Ericsson, a test lab, BIPT, or an OEM is worth more than any amount of correct prose.

3. **A USP expressed as an unmatched combination, plus one narrow sourced superlative.** Not "we are faster". Rather "the only pipeline that does closed-form body-aware dosimetry + coherent MIMO + a differentiable design loop, from real antenna databases, in a browser" plus "WAVES is #1 worldwide in in-situ RF exposure characterization" (Wout's, sourced, narrow, reusable).

4. **Real euros: unit price, a 5-year turnover table, a competitor matrix.** Both proposals gave a worked pricing example and a year-by-year revenue ramp. Wout highlighted nearly all of it. The market section is not a TAM headline, it is a bottom-up funnel (regional -> national -> EU) with a citation on every number.

5. **A small number of month-bounded work packages with one explicit go/no-go, and a valorisation WP running in parallel for the full 24 months.** 3-4 WPs, each with goal / success criteria / activities / deliverables / risk + fallback. Plus the official wage-simulation appendix.

The guidance doc adds one software-specific instruction that you must obey: **for software, the defensible IP is not the code (copyright is automatic and weak), it is the *assets around it*** (validated tissue/physics datasets, the golden-test corpus, domain know-how, the differentiable design know-how as trade secret). It explicitly blesses open-source-plus-SaaS/consultancy as a valorisation model. And it warns: if you touch healthcare, address medical-device regulation proactively. You should pre-empt the MDR question (AEGIS is a compliance/engineering tool, not a medical device, say so in one sentence).

---

## 2. The central decision the proposal must make: which wedge

This is the fork everything else hangs on, and your own documents disagree with each other about it.

**Wedge A: base-station / network compliance.** This is what you have *built* (the base-station pipeline, 14-15 government databases, ~293k-5.25M antennas, the urban-reconstruction viewer). It is Wout's world and the Unisens flavour. The IOF reviewers will recognise it instantly. BUT the April honest_analysis is brutal here: the incumbent is IXUS (not Sim4Life), operators are slow and IXUS-locked, body-specific dosimetry at every base station is a market that "doesn't exist today and probably won't for 3-5 years". The demand is real (legal mandate) but the *willingness to pay for your specific thing* is the weakest.

**Wedge B: mmWave device pre-compliance.** The honest_analysis calls this "the biggest wedge, and the one the internal docs underweight". Every mmWave phone/wearable legally needs APD pre-compliance evidence (FCC, IEC 63195-2), every design iteration runs thousands of FDTD scenarios at hours each, and your closed-form method is 100-1000x faster *in exactly this near-field regime* (5-200 mm, which the monograph says you cover). The buyer (OEM compliance engineers, chipset vendors, test labs) already pays for Sim4Life. You are not replacing Sim4Life, you are the fast pre-screener that feeds it. The differentiable design loop is a feature Sim4Life structurally cannot match.

**The honest catch on Wedge B:** you have *not validated* the near-field point-source extension against Sim4Life on a real phone at 28 GHz. Far-field is validated (Mie R=0.988, Kodera, Bamba, Diao, Flintoft). Near-field is theory only. The single most valuable de-risking experiment you could run is a matched AEGIS-vs-Sim4Life figure on a 63195-2 benchmark, and you can run the Sim4Life side yourself with GOLIAT.

**Decision (Robin, 21 June): BOTH, framed as one story.** Not "two markets" but one physics problem the industry was forced to split. The spine:

> **One exposure physics, from the chip in your hand to the antenna on the roof.**

Human RF exposure compliance is physically one question (how much power a body absorbs from an EM wave), but industry runs two separate toolchains because the split is *mathematical, not physical*: up close (phone, 5-200 mm, near-field mmWave) it is SPEAG DASY + Sim4Life FDTD at hours per scenario; far away (base stations, tens of metres, far-field) it is IXUS zone-based envelopes with no body. Nobody spans both because FDTD does not scale to a city and zone models cannot resolve a body. AEGIS dissolves the split because the closed-form Fresnel surface law `T0` is *scale-invariant*: same physics whether the wave came from 5 mm or 50 m, only the incident-field computation changes (point-source vs plane-wave), and AEGIS does both.

Why this is load-bearing and not just elegant, all three pointing at *now*:
1. **Regulators are moving to aggregate exposure** (uplink device + downlink network, summed). Only a tool that computes both can answer the question the standards are starting to ask.
2. **6G erases the device/network line** (RIS, cell-free massive MIMO, near-field beamforming). The base station and the handset become one beamforming system, and AEGIS's coherent MIMO operator Q + near-field extension are built for exactly that convergence.
3. **One differentiable engine, two design problems** (optimise a handset array or a base-station deployment under the same compliance constraint, same gradient machinery). The moat amortises across both markets.

**The discipline that stops this being a vague platform pitch:** the *story* is "chip to cell tower", but the *first euro* (beachhead for the valorisation section) is **device mmWave pre-compliance** (clearest paying buyer, regulation-forced, partner to Sim4Life). Base-station + aggregate exposure is the expansion and where the 6G moat compounds. This is Robin's own "two near-fields, the bridge is white space" / split-thesis instinct, now the spine of the proposal.

The keystone deliverable is unchanged and now serves both halves: **the near-field validation against Sim4Life** (matched on a 63195-2 benchmark). It de-risks the device beachhead, the patent, the ZMT conversation, the standards contribution, and the valorisation score, all at once. Make it WP1.

Supporting evidence that "both" reflects reality, not a hedge: Robin's own warm inbound is already straddling the two sides. Ericsson (network/infrastructure) and Hirata + Marta Parazzini (device/dosimetry science) all landed in the same week. See section 5.

---

## 3. What is the IOF money actually FOR (do not get this wrong)

The funding-stack analysis surfaced something most applicants miss: **VLAIO and IOF are both predominantly salary funding, so they cannot both pay *your* salary.** The EIoT proposal proves the pattern: of its €210k, €150k was the salary of *one named hired postdoc*, with the professor unpaid. So a stacked VLAIO+IOF world means **IOF funds a hire (a dev or research engineer), VLAIO pays you.** That is a teammate, not a second paycheck.

This changes the proposal structurally:
- The "projectverantwoordelijken" promotor is Wout (unpaid ZAP). You are either the contactpersoon / IOF mandataris, or the funded researcher, not both-and.
- The budget personnel line funds the hire (or you, if you decide IOF is your salary and VLAIO comes later or not at all).
- The team section and the WPs must reflect who actually does the work.

You need to settle, ideally at the IOF intake with Filip: is the IOF StarTT (a) funding *you* as the researcher for 12-24 months (simplest, and probably what you want if VLAIO is uncertain or later), or (b) funding a *hire* to execute the technical milestones while VLAIO pays you. My read: for a one-person AI-assisted software shop with ~€15-30k/yr non-salary burn, you do not need a hire in year 1, so (a) is cleaner and more honest. But (a) means IOF and VLAIO are sequential or you pick one, not a €335k stack. Do not write a proposal that implies double-funding your own salary, the ethics declaration on the form explicitly forbids undisclosed parallel funding.

---

## 4. Rank-ordering the spinoff/ corpus

You asked me to say what is good and what is bad. Here it is, bluntly.

### Gold (use directly, highest signal)
- **`LATEST_GOOD/honest_analysis.md`** — the strategic backbone. The two-market framing, the device-wedge recommendation, the outcome distribution, the 18-month kill date. Everything I think is downstream of this. From April, so verify what changed (ZMT, traction).
- **`LATEST_GOOD/funding_stack.md`** — the only document that correctly works out the VLAIO/IOF salary-collision and the real deadlines (IOF 3 Aug 2026, VLAIO Sept). Trust this over the older briefings.
- **`decisions.txt`** — the rawest and most honest file about whether you actually want this. Short, contradictory, and the most useful thing for me to understand you. "doing the startup itself? yes" followed by every door propped open.
- **The two example proposals + Wout's highlights** — your literal template. EIoT carries the official page limits and font inline. Copy the structure.
- **`IOF/LARGE-zmt-market-analysis.md`** (today) — excellent for the competitive/market section. Key facts: ZMT $2.3M ARR / $6.8M val / 15 people after 20 years, EM-sim market $1.66B->$2.70B (10.2% CAGR), Big-5 hold ~60% at $50-150k/seat, and the live threat is AI surrogate solvers (Ansys SimAI). Your differentiation vs SimAI: physics-derived closed form with error bounds, not a black-box ML surrogate.

### Good (mine for specific sections)
- **`patent/patent_landscape_search.md`** + **`outreach_dossier/prior_art_split_thesis.md`** — the real IP position. The moat is the differentiable design loop and the integrated system, not the physics. The Kapetanović Split thesis is the closest prior art (treat the author as a collaborator, not a threat).
- **`LATEST_GOOD/standards_play.md`** — the IEC/IEEE 63195-2 Edition 2 insertion window ("now", 3-6 months). Worth more than an early customer per the analysis, and it runs entirely through Wout.
- **`outreach_dossier/`** (collaboration_targets, contact_sheet, alessandro/) — the named-target list and warm paths (Ericsson via Luc->Colombi/Törnevik is the strongest LOI lead). The machine is built.
- **`older_but_less_important_kinda/ROADMAP_12_months.md`** — the critical path and the explicit "do NOT build" list. Still directionally right.

### Stale, redundant, or superseded (do not lean on)
- **`older_but_less_important_kinda/external_briefing.md`** and parts of the older reports — funding_stack explicitly corrects their numbers (StarTT is €250k not "50-125k", VLAIO decision is ~3 months not ~6). Use funding_stack instead.
- The `outreach_dossier/materials/` duplicates of LATEST_GOOD files — same content, ignore the copies.
- The bulk of **`nature career column ai/`** and **`personal/career.txt`** as *strategy* input — career.txt is, in the words of the April advice, "procrastination pretending to be research". Useful only as evidence of the ambivalence, not as a plan.

### Dangerous (will hurt you if it leaks into the application unchecked)
- **The IDF's hallucinated citations.** `TODO_IDF_HALLUCINATIONS.md` found that 5 of 9 prior-art references are wrong or fabricated (Castellanos #7 is fully invented, "a fabricated reference in an IDF is a credibility landmine"). The IDF also says "No closely related patents were identified", which is flatly false (Hochwald, ETRI, Qualcomm all exist). **None of these false claims or unverified numbers ("10^9x faster", "50-60k Sim4Life license", "10,000 evals/hour" which contradicts "milliseconds/eval") can go into the IOF app.** Scrub every borrowed number.
- **The Carolina credential narrative.** The co-founder report describes her as a "UGent PhD on EM effects on neurons, same lab, same promotor". Her actual CV says ETH/UZH neuroscience MSc, pupillometry, in Switzerland, no UGent PhD, no Wout. If that narrative enters any funded application and an evaluator checks, it is a serious problem. This is an istart-stage issue more than an IOF one (IOF is a UGent research-funding app under Wout, not a spinco cap table), so the clean move is to keep Carolina out of the IOF application entirely.
- **"Real-time SAR" language.** Qualcomm owns the common meaning. Reframe as "closed-form computed APD field". Drop "real-time" from enterprise framing generally (honest_analysis Q8).

---

## 5. The gaps that will actually sink this (and what to do)

1. **Traction: trigger pulled, now converting (updated 21 June).** The "zero traction" read was built from the *drafted-but-unsent* dossier. Reality as of 21 June: all outreach emails are SENT. Live state:
   - **Ericsson replied warm** ("interested, let's plan something") — the strongest LOI lead, now active.
   - **Hirata (ICNIRP Chair) gave an unprompted, quotable endorsement**: "potentially useful directions may include whole-body or large-scale exposure assessment at higher frequencies for mmWave dosimetry." A deepening questionnaire is going to him (capture quote-permission + ideally an LOI line).
   - **Marta Parazzini (CNR-IEIIT) call booked** for 22 June 10:30.
   - **IOF intake conversation booked** for 21 June 15:30 (the day's focus).
   The remaining job is to convert 1-2 of these into letters of support before 3 August. Realistic now. The fallback regulatory-mandate framing is no longer the only option, but keep it as insurance.

2. **The near-field validation does not exist.** This is the keystone deliverable. It should arguably *be* WP1.

3. **The ZMT channel may be dead per Wout.** If true, the "partner with the incumbent" thesis needs a rethink. Either re-open it (your call with Wout) or reframe the exit around a different strategic (Dassault, an operator innovation arm, a test-lab group) or around standards-driven adoption.

4. **The standards window is open and unworked.** Wout is "awfully quiet". This is the cheapest highest-value move and it costs you one conversation with him.

5. **The commitment question.** decisions.txt shows you hedging hard (EU bubble, MBB, FAANG). That is fine and even rational given Karolina's 5-year Belgium anchor and the kids clock. But the IOF/VLAIO route is *perfect* for the hedge: low hours, full salary, near-zero downside, two years to find out. The honest internal framing is "funded two-year option on a company, with an 18-month kill date", and naming that to yourself changes how hard you push on the uncomfortable parts (customer calls) versus the comfortable parts (building).

---

## 6. Recommended spine for the AEGIS StarTT proposal

A first-cut mapping to the scored sections, assuming the device-led / Wedge B narrative:

- **Title (max 20 words, no IP-sensitive info):** brand + capability. e.g. "AEGIS: millisecond electromagnetic exposure assessment for 5G/6G compliance" (your iof_registration_draft already landed here, it is good).
- **Background (½p):** WAVES provenance, named funders (GOLIAT, imec, EU), the milestones already hit (monograph, npj paper, deployed platform, 2,469 tests, Mie R=0.988, IDF P2026/040). Quantify everything, cite each claim.
- **Current status (½p):** what works (far-field validated, full pipeline, viewer) and what the grant funds (near-field validation, API/reports, productisation). This is honestly a tPoC->iPoC story for the *product*, even if the core physics is past tPoC.
- **Opportunity (1p):** open with the legal obligation (ICNIRP/IEC/FCC), then the FDTD bottleneck (hours per scenario, thousands of scenarios per device), then your closed-form answer. End with the differentiable-design-loop USP.
- **Target markets (1p):** bottom-up funnel. Primary: mmWave device pre-compliance (OEMs, chipset vendors, test labs). Secondary: base-station compliance (operators, regulators). Use the ZMT-analysis market numbers, your basestations database counts, and a per-segment sizing.
- **Competitive landscape / USP (1p):** the matrix. Rows: Sim4Life/CST/Remcom (FDTD, slow, not differentiable), IXUS (base-station, zone-based, no body), Ansys SimAI (ML surrogate, no error bounds, not body-specific), measurement (DASY8, physical, slow). Repeated disqualifier: "none combines body-aware closed-form dosimetry with a differentiable design loop". One sourced superlative.
- **IP strategy (1p):** lead with the software-asset framing the guidance wants (datasets, golden corpus, know-how, trade secret) + the patent (P2026/040, priority filing in prep with TechTransfer, the differentiable-design-loop claim as the defensible core). State FTO will be run via UGent counsel before national entry. Do *not* claim "no related patents".
- **Valorisation strategy (2p):** the device-led go-to-market, the standards play, the pricing example + 5-year turnover table, the spin-off-vs-license optionality (StarTT keeps both open). Name the warm-path targets.
- **Team (1p):** Wout (#1 WAVES superlative, standards seats), you (built it, npj, prizes), any co-promotor who adds real validation weight. Keep it honest.
- **SWOT + risks:** populate the weaknesses box properly (near-field unvalidated, no sales track record yet, incumbent ecosystems) each with a mitigation. Reviewers distrust a thin weakness box.
- **Work packages (2p):** WP1 = near-field validation vs Sim4Life + closed-form near-field solver hardening (with a go/no-go at ~M6 on validation error). WP2 = productisation (API, ICNIRP PDF reports, antenna-pattern import, batch). WP3 = market validation + standards contribution + IP, running M1-24. Few, dated, concrete deliverables.
- **Budget:** personnel-dominant (per the EIoT template), small operating (compute, Sim4Life/COMSOL license for validation, travel), attach wage simulation.

---

## 7. The questions (this is the point of the exercise)

Grouped. For each I give you my lean and the opposing case, because you said you will struggle to answer and want my opinion in the room. Answer in any order, think out loud, push back.

### Tier 1: the proposal cannot be written without these
**Q1. The wedge.** Lead the proposal with device mmWave pre-compliance (my lean), with base-station as the demonstrated second segment? Or lead with base-station (what you built, Wout's world)? Or genuinely both as co-equal? See section 2 for the full argument. *My lean: device-led, base-station as proof.* Opposing case: you have zero device relationships and a built base-station product, so device-led is a story you cannot yet back with traction.

**Q2. What is the IOF money for?** (a) Your salary as the researcher for 12-24 months. (b) A hire (dev/research engineer) while VLAIO pays you. (c) Genuinely unsure, this is a question for Filip at intake. See section 3. *My lean: (a), unless you actively want a teammate in year 1.* This determines the budget and team sections.

**Q3. Innovation phase to claim:** Concept->tPoC, tPoC->iPoC, or iPoC->Valorisation? You have a deployed product, which argues mature, but near-field is unvalidated, which argues less mature. *My lean: tPoC->iPoC for the product (you have a tPoC, the grant proves industrial fitness via validation + productisation), which is also what both examples claimed.*

### Tier 2: determine whether the proposal has teeth
**Q4. Traction by 3 August.** Realistically, can you get 2-3 discovery calls and 1-2 letters of support before the deadline? If yes, from whom (Ericsson via Luc, Hirata, BIPT, a test lab)? If no, are you comfortable pivoting the app to a regulatory-mandate + standards-pull framing that does not need customer letters? See section 5.1.

**Q5. The near-field validation.** Are you willing to make "matched AEGIS-vs-Sim4Life validation on a 63195-2 benchmark" the keystone deliverable (WP1) and ideally have a *preliminary* version of it before the deadline? You can run the Sim4Life side with GOLIAT. *My lean: yes, this single experiment compounds across patent, ZMT, standards, and the valorisation score.*

**Q6. Is ZMT actually dead?** Your June note says Wout killed it. Does that hold? If yes, what is the exit thesis instead (another strategic, standards-driven adoption, operator innovation arm)? The whole valorisation section's endgame depends on this.

### Tier 3: shape the framing and protect you
**Q7. Patent vs software-asset+standards as the IP spine.** Given the IDF citation problems and that the real moat is the design loop + execution + standards recognition (not the physics, which is leaving via the monograph anyway), how hard do we lean on the patent in the app versus the trade-secret/dataset/standards story the software guidance actually rewards? *My lean: feature the patent as filed/in-prep for credibility, but make the software-asset + standards-adoption story the load-bearing valorisation argument.*

**Q8. Carolina in or out of the IOF app.** My strong lean is *out*: IOF is a UGent research-funding application under Wout, not a spinco cap table, and the credential mismatch is a live risk. She belongs in the istart story (the 2-founder gate), not here. Agree?

**Q9. The honest commitment frame.** Are you willing to internally frame this as a "funded two-year option with an 18-month paying-customer-or-LOI kill date", which lets you both run the company seriously *and* keep the EU-bubble/other doors open without guilt? This is not a proposal question, it is a you question, and it changes how hard you push on the uncomfortable parts. *My lean: yes, and it is the healthiest framing given Karolina's Belgium anchor and your stated love of low-hours intellectual freedom.*

### Tier 4: quick clarifications (rapid-fire, answer in a line each)
- **Q10.** Is "Karolina" (decisions.txt, your partner, 5-year Belgium constraint) the same person as "Carolina" (the co-founder CV)? I believe yes, one person, two spellings. Confirm so I stop second-guessing it.
- **Q11.** Has the PhD defense date been set, and is it before or after 3 August? (Matters for the patent-priority-before-disclosure timing.)
- **Q12.** Did the patent priority application actually get filed yet, or is it still "in prep" with Alessandro? (Changes how we phrase the IP section.)
- **Q13.** Who is the promotor on the IOF app, Wout alone, or Wout + a co-promotor (Luc Martens, Emmeric Tanghe, Margot Deruyck)? A second discipline can strengthen it the way VETMED did for EIoT, but only if it adds real weight.
- **Q14.** Is Filip Louagie confirmed as the IOF Business Developer, and is the intake meeting booked yet (it must be early-mid July for a 3 Aug deadline)?
