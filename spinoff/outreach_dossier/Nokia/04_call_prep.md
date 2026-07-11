# Call prep — Grangeat

## Frame in one line

Discovery call, stage 2 of the funnel (`materials/company_outreach_and_ndas.md`).
No NDA, no document attached, no method disclosure beyond the three-sentence
description. Goal ordering: (1) listen and learn, (2) get a support letter or
soft license-interest note, (3) get the referral. Always at least the referral.

## Grangeat is not primarily a customer

He is the **standards gatekeeper** for the exact assessment methods AEGIS
would have to be accepted by, sitting inside the OEM that pays for compliance.
Adjust the call goal accordingly:

- **G4 (standards awareness)** is the primary implicit goal here, even though
  procedurally G4 runs through Wout tabling contributions rather than through
  Robin. Being on Grangeat's radar as a credible, non-crank, well-scoped
  academic-with-a-tool-and-a-patent is worth more than a Nokia purchase order.
- **G2 (discovery)** is the framing on the call. Ask what is painful, listen,
  don't pitch. Same as Marta.
- **G1 (IOF evidence)** is the win Robin needs. Quotable numbers on
  actual-max frontier problems, market signal, and standards adoption
  timelines are IOF gold.
- **G3 (ZMT) is not applicable here.** Grangeat is not the ZMT pathway.

## Opener (soft, uses the prior contact)

*"Christophe, thanks for making time. It's been a while — I think last time
we crossed paths was around the GSMA OUTREACH work, must be two years ago now.
Curious whether that thread is still active on your side. Anyway, before I
take too much of your time — this really isn't a sales call. I'm applying for
an IOF post-doc valorisation grant here at UGent, and the honest bit I need
help with is understanding what's actually painful in your day job, and where
the field is going. Would love your read."*

Set the clock: *"I have 30 minutes in mind. Push back if you need to drop
earlier or stay longer."*

Ask permission: *"Would it be OK if I take notes, and possibly quote or
paraphrase you in the application later — I'd send you the exact wording for
approval first."*

## What to say about the method — the three-sentence hard cap

Filip's rule, unchanged. Any question about the method gets one of:

- *"It's a method that very substantially improves the speed of exposure
  simulations, with accuracy similar to FDTD, and is differentiable."*
- *"That's exactly the part still under patent drafting with UGent
  TechTransfer, so I have to keep it closed for now. Happy to talk about what
  it does though."*

**Differentiability stays in.** Do NOT drop it. Reasons:
1. Filip explicitly allowed it as one of three descriptors.
2. The July 2026 13-agent study did not tell you to stop saying the word; it
   said differentiability is not a business moat on its own. Neither position
   licences dropping the descriptor, only reweighting emphasis.
3. Robin's own read stands: differentiability is not dead. In front of a
   standards convenor whose whole world is uncertainty budgets, gradients w.r.t.
   inputs are conceptually the right lens for exact sensitivity coefficients
   the ISO GUM budget wants.

**But do not lead on differentiability.** Lead on speed: *"a method that
very substantially improves the speed of exposure simulations." *If he then
asks "and what else," add *"similar accuracy to FDTD" *and *"differentiable
end-to-end."* If he asks "differentiable in what sense" — bounded answer:
*"Gradients w.r.t. any input parameter you'd want to sweep — antenna weights,
positions, beam parameters, geometry. The rest is inside the patent."* Do NOT
say analytical, closed-form, JAX, GPU, voxel, ray-tracing, Fresnel, Brewster,
operator decomposition, MIMO operator.

## Sharp questions — the bank

Ranked in tiers by leverage. Aim for **all of tier 1 and tier 2 in a 30-min
call (~12 questions)**. Dip into tier 3 if he stays longer. Tier 4 only if he
offers more time or the conversation drifts personal-strategic. Skip any
question already answered naturally in the flow.

**Big picture / small picture ratio is deliberate.** Tier 1 mixes two
strategic-reframe questions (Q1, Q2) with three Marta-template quotable-number
questions (Q3, Q4, Q5) — you need both to make the call worth what it is.
Sharpen the thesis AND get IOF quotes.

**Reframe context (from the Sinc-vs-Sab discussion).** Grangeat's world runs
on reference-level (Sinc) compliance, not basic-restriction (Sab) compliance.
So do NOT push AEGIS's body-aware Sab superiority — it over-serves his use
case. The questions below use him as an outside-in strategic read and as a
standards-legitimacy + referral node, not as a customer directly for the Sab
pitch. See `../../differentiability/SYNTHESIS.md` and the reframe notes for
why.

---

### Tier 1 — Must-ask. The 5 questions that reshape the business case.

**Q1. The bet — device vs base station (the reframe question).**
> *"Honest strategic question. If you were placing a bet on where a fast,
> body-aware forward model above 6 GHz would have the biggest impact — is it
> base-station compliance work with actual-max, or is it device-side APD
> assessment under 63195-2? Where would you point it? Or somewhere I haven't
> named?"*

Big picture. His outside-in read is uniquely valuable because he sees both
sides and has no commercial reason to lie. Directly sharpens the pitch
center of gravity for IOF. Highest single-question leverage in the call.

**Q2. FR3 evidence base status.**
> *"MT3 is clearly gearing toward FR3 — Kamil and Marcin's 2024 extreme mMIMO
> 10 GHz paper is Nokia-Poland's frontier work. What does the standards
> evidence base look like at 7-15 GHz right now? Do you have the case studies
> you'd need for the next TR 62669 edition, or is it thin?"*

Big picture. If he says thin, that's IOF-quotable AND names the natural FR3
case study Robin should propose. If he says covered, that's also useful
because it retires an AEGIS use case honestly.

**Q3. Nokia FTE bottleneck (Marta-template quotable).**
> *"For your team specifically and the broader EMF compliance work at Nokia —
> roughly how many people are effectively bottlenecked on numerical dosimetry
> compute? What fraction of their time is waiting for FDTD or equivalent to
> finish, versus doing the actual analysis?"*

Small picture, IOF-quotable. Marta gave you 1.5 FTE from ~5 people (30-50%
waiting time). Grangeat's number scales that up or contradicts it. Either is
gold.

**Q4. Nokia annual EM tool spend.**
> *"Ballpark — what does Nokia's EMF/compliance work spend annually on
> external simulation tools, licences, and chamber time across product lines?
> Not asking for confidential numbers, just orders of magnitude, so I can
> size the tool market realistically."*

Small picture, IOF-quotable. Marta: 4 × €3k licences + phantoms + ZMT free
+ discounted CST. Grangeat's number is bigger and OEM-specific.

**Q5. Build vs buy.**
> *"When Nokia's EMF team needs a new capability — new codebook, new
> frequency, new deployment class — is that built internally at Bell Labs
> Wroclaw or France, contracted to a consultancy, or licensed? And where is
> that split shifting?"*

Small picture. Sizes the OEM market. His most awkward question, deliver
plainly, don't fill the silence.

---

### Tier 2 — High priority. Standards trajectory + referrals.

**Q6. Standards timing (the Ed. 4.0 / K-series question).**
> *"Given TR 62669 Ed. 3.0 has just gone out — when does the Ed. 4.0
> working-group window realistically open for new case studies? And is there
> anything to be gained by targeting an ITU-T K-series update in parallel
> while the IEC cycle is between editions?"*

Big picture. Confirms whether the IOF post-doc arc lines up with the standards
windows. If he says "Ed. 4.0 collection starts 2027-2028," IOF arc is
confirmed. If "fast-cycle amendment before then," timeline changes. The
K-series parallel probes his view on the faster ITU channel.

**Q7. What killed previous fast-method attempts.**
> *"There have been attempts before to introduce faster computational methods
> into 62232 or its predecessors. Which ones stand out in your memory, and
> what typically killed them — validation gaps, political resistance,
> uncertainty budgets, timing? What are the failure modes I should learn
> from?"*

Big picture. Only he can answer this. IOF gold if he names specific cases.
Also protects Robin's own contribution from repeating a known failure mode.

**Q8. ML surrogate acceptance criteria.**
> *"NPL and others are publishing physics-informed ML surrogates — Bilson et
> al. 2024 hit R² 0.86. Where does MT3 sit on acceptance criteria for
> data-driven methods? Is there active discussion, or is the committee
> kicking the can?"*

Big picture. Positions AEGIS as a distinct approach (closed-form
differentiable, not ML) and probes committee attitudes. Also softly frames
differentiability as the physically-anchored alternative to a data-hungry ML
surrogate.

**Q9. Reference level vs basic restriction — any movement.**
> *"ICNIRP 2020 built in roughly a factor of 2 between reference levels and
> basic restrictions to bake in normal-incidence transmission. Is there any
> committee movement — MT3 or SC6 side — toward compliance based on the basic
> restrictions directly at frequencies where the shortcut degrades? Or is
> that a debate nobody wants to reopen?"*

Big picture. Directly tests whether AEGIS's Sab-native machinery has any
standards-track home on the base-station side. His answer sizes the "unlock
the factor of 2" pitch honestly. Two ways it can go: dead conversation ("no
committee movement, won't be for years") or opening ("actually yes, at FR3
where near-field starts to matter"). Either way, decision-shaping.

**Q10. Referrals to device-OEM side.**
> *"Given the device side (63195-2) is where a body-aware method most
> obviously lands — do you have contacts on the handset OEM compliance side,
> Qualcomm, Apple, Samsung Mobile, or on the mmW chipset MPE-policy side,
> that you'd suggest I also speak to?"*

Small picture. This is the highest-value referral Grangeat could give — he
sits inside a vendor but has cross-industry contacts through IEC / GSMA /
BioEM. His device-side referral is worth more than his base-station referral.

**Q11. Referrals inside Nokia.**
> *"And who else at Nokia should I talk to — is Kamil Bechta or Marcin
> Rybakowski still leading the Poland channel-modelling side? Lorenzo Maggi
> or Silvio Mandelli on the France side? Anyone product-side rather than
> research-side?"*

Small picture. Naming his own co-authors signals depth.

**Q12. Support letter (the primary ask).**
> *"Would you be open to a short letter of support for the IOF application —
> not on behalf of Nokia, just as a personal endorsement that the field
> genuinely needs faster forward models at the frontier we've been
> discussing? Standards-level framing, not commercial. I have a draft you
> can start from."*

Small picture, primary close. See "The close" section below for the full
ladder.

---

### Tier 3 — Medium priority. Depth if the call goes longer than 30 min.

**Q13. Actual-max residual conservatism (Nokia-specific).**
> *"The actual-maximum approach has shrunk exclusion zones enormously since
> it went into 62232:2022 — Nokia's own 2018 statistical paper originally
> quoted around 50% reduction. Where do you see the residual conservatism
> sitting today — body model, codebook × traffic sweep, reference distance?
> And is it costing Nokia real deployment margin, or comfortably in the
> noise?"*

The reference to the 2018 Baracca/Weber/Wild/Grangeat paper signals peer-level
fluency. Small picture / IOF-quotable if he engages, but demoted from tier 1
because unlocking the residual isn't a business — regulators won't move.

**Q14. F_PR default tightening.**
> *"The 2023 Rybakowski/Bechta paper showed the 95th percentile of per-beam
> power is 7-22% of theoretical max depending on beamforming algorithm. Do
> you see the F_PR default (0.25 or −6 dB) getting tightened per-deployment
> in future editions, or is that a battle nobody wants to fight?"*

Follow-up to his own team's paper. Standards-committee texture question.

**Q15. Nokia F_PR in production.**
> *"The 62232:2022 default F_PR is 0.25. What does Nokia actually use in
> production — the default, something tighter for tight-regulator markets,
> something looser? And does that split by product line?"*

Small picture. Tests whether operational F_PR headroom is a real sellable
axis.

**Q16. Regulator country map.**
> *"Which regulators are comfortable with actual-max and moving with the
> standard, and which are still requiring theoretical-max? Where do you see
> the holdouts breaking?"*

Big picture. IOF-quotable if he names Belgium, Switzerland, Italy specifically
— the strict regimes are Robin's natural early customers.

**Q17. Codebook × traffic × pose sweep count.**
> *"For an actual-max evidence-base study at Nokia — codebook × traffic ×
> pose × body sweep — how many evaluations does that consume? Is FDTD the
> tool, and is throughput the rate-limiter?"*

Small picture, Marta-template numbers. Sizes the compute pain if base-station
side is worth pursuing.

**Q18. Standards convergence 62232 ↔ 63195-2.**
> *"Do you see 62232 and 63195-2 converging in future editions — some
> countries already run aggregate compliance combining device + base station
> — or will they stay separate documents in separate committees?"*

Big picture. Positions AEGIS as a unified body-aware model spanning both
regimes.

**Q19. GSMA OUTREACH continuity.**
> *"Is the GSMA OUTREACH thread still alive? Any successor initiative you'd
> point me to?"*

Small picture, warm reconnection to the prior contact.

**Q20. Nokia internal EM tool stack.**
> *"What does Nokia use for pre-compliance simulation today — Sim4Life, CST,
> HFSS, XFdtd, in-house? And is that split by team or standardised?"*

Small picture. Names the incumbent AEGIS is quietly competing with.

---

### Tier 4 — Optional. If he offers more time or drifts personal-strategic.

**Q21. MT3 seconders for computational-method innovation.**
> *"If someone were to table a new computational method contribution to MT3,
> who are the natural seconders — the members most receptive to new methods?
> Doesn't have to be names, just directions."*

Small picture. Political map of the committee.

**Q22. Nokia patent landscape.**
> *"Does Nokia have its own patents on compliance-side EMF compute or the
> actual-max control mechanism? Want to make sure I don't accidentally step
> on IP that's already yours."*

Small picture. Useful for Alessandro (FTO) and shows respect for their IP
position.

**Q23. If starting AEGIS today.**
> *"If you were starting a spin-off around a fast body-aware forward model
> today, from where I'm standing — what's the number-one thing you'd tell me
> to focus on in the next 12 months?"*

Big picture. Direct advice question. Ask only if the call is warm and
personal.

**Q24. Matched-validation TR case study offer.**
> *"Longer term — would you be open to a matched-validation piece we could
> co-author for the next TR 62669 case study cycle? Non-binding,
> non-commercial, just the technical comparison on a 62232 reference
> scenario."*

Small picture, secondary close. Only if he's warm.

**Q25. Personal read on the differentiability moat.**
> *"Honest question — from where you sit as convenor, when you hear
> 'differentiable EM forward model,' does it mean anything to you commercially
> or standards-wise? Or is that a research-community talking point that
> hasn't reached your world?"*

Big picture. His answer directly informs whether Robin should keep the
descriptor prominent or reweight in the pitch. Also part of the ongoing
internal "differentiability alive or dead" debate.

---

### Summary — what to do if the call is 30 minutes flat

- **Open** (2 min) — greeting, GSMA OUTREACH reference, clock, permission.
- **Big-picture strategic reframe** (5 min) — Q1, Q2.
- **Marta-template quotable numbers** (7 min) — Q3, Q4, Q5.
- **Standards trajectory** (7 min) — Q6, Q7, one of Q8/Q9.
- **Referrals** (3 min) — Q10, Q11.
- **Close** (5-6 min) — support letter (Q12), quote permission, followup.
- **Anything left** — grab from tier 3 in order of highest-lit-up topic.

If he goes over: tier 3 fully, then tier 4 selectively based on tone.

## The close — the ask ladder

Same as Marta and the playbook, calibrated for a standards convenor.

### Step 1 — support letter (the primary ask)

Frame at the *field* level, not at Nokia:

> *"This has been really useful. Would you be open to a short letter of
> support for the IOF application — not on behalf of Nokia, just as a
> personal endorsement that the field genuinely needs faster forward models
> at the frontier we've been discussing (FR3, actual-max evidence base,
> extended codebook sweeps)? I have a draft you can start from — five-minute
> lift. No pressure."*

Grangeat can't sign anything speaking for Nokia in a discovery call. But he
can sign as an individual expert, and a letter that says "the field needs X"
from the convenor of MT3 is worth more than a letter from a purchase manager.

### Step 2 — matched-validation case study (softer, standards-flavoured)

Only if the call is warm.

> *"Longer term — would you be open to a matched-validation piece we could
> co-author for the next TR 62669 case study cycle? Non-binding, non-commercial,
> just the technical comparison on a 62232 reference scenario."*

He will say "let's see the validation first" — which is the answer you want.
It commits him to nothing but opens the standards channel.

### Step 3 — quote permission

Always ask.

> *"If something you said today ends up shaping a sentence in the application,
> may I paraphrase it? I'll send the exact wording for approval first."*

### Step 4 — referral

Always ask. See Q9 and Q10 above. From him, the referral is worth as much as
the letter.

### Step 5 — the follow-up

Concrete: *"I'll send the letter draft this week. Would end of next week work
for you to look at it?"*

Same-day thank-you email with the draft. If he agreed to a form, include the
link.

## What NOT to do

- **Do not attach the one-pager.** Alessandro's sign-off gate is unclear.
  Stage-2 discovery call needs no document. If he asks: *"I'll send it after
  Alessandro at UGent TechTransfer signs off on the disclosure boundary
  — probably next week or two."*
- **Do not proactively raise the Split (Kapetanović) prior art.** Contact-sheet
  guidance: don't lead on it. If Grangeat brings up differentiable dosimetry
  and mentions the Split work, acknowledge it exists and pivot to the speed
  differentiator.
- **Do not oversell.** Differentiability is not a business, per the
  July-2026 study. Say the word, do not build the pitch on it. Speed is the
  pitch. Actual-max evidence base at FR3 is the specific use case.
- **Do not commit to co-author timelines or delivery dates.** The IOF post-doc
  is not confirmed. Say "assuming the funding lands, September 2026 start" —
  no earlier.
- **Do not talk price.** Not stage 2. If pressed: *"Way too early. Let's see
  if it's useful to you first."*
- **Do not stay past the clock.** Marta's call worked because Robin ended on
  time. Grangeat will respect the same discipline.

## Capture template (fill in during / right after)

```
Contact: Christophe Grangeat (Nokia, EMF Mitigation Lead, IEC TC106 MT3 Convenor)
Date:
GSMA OUTREACH continuity signal:
Residual conservatism in actual-max (verbatim if possible):
F_PR default 0.25 — tightenable per-deployment? his view:
FR3 evidence base status:
FDTD sweep bottleneck — evals/year at Nokia:
Standards path preference: TR 62669 / normative annex / K-series ?
Build vs buy split at Nokia:
ML surrogate stance:
Numbers: evals/year, hours saved, budget size, etc.
Asks landed:  support letter [ ]  matched-validation case study [ ]
              quote permission [ ]  referral [ ]  followup [ ]
Referrals (names + role):
Follow-up actions + by when:
```
