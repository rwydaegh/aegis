# Meeting flow — conversation, not interrogation

Robin's Nokia-call feedback: *"tbh it was tough for me to ask all questions
back to back cuz its a conversation."* So this file is structured as scenes,
not a question list. Each scene:
- A rough time budget in a 45-min meeting
- A conversational entry line (Robin's opener for the scene)
- One or two questions to hold in reserve *if the scene doesn't unfold
  naturally*
- Listening cues — what signals what
- The primary person to route to

Only 7 scenes. If some go long naturally, cut others without regret.

## Before the call — 5 min housekeeping

- Confirm attendees on the invite (Colombi + Zhekov + Bischoff + probably
  Luc). If Luc is not on the invite, mention him in the opening greeting so
  Colombi knows he's welcome to loop him in.
- Have your password-protected demo tab open but not shared. Only pull it up
  if Stanislav asks.
- Have Colombi's stadium paper reference and Bischoff's DT paper reference
  written down. Do not read from notes, but you should be able to name them
  fluently.
- The three-sentence method description on a sticky in front of you if you
  want.
- Notes doc open in a second window, ready for capture.

## Scene 1 — Opening (2 min)

Warm reconnection with Luc if present, or clean start if not.

> *"Davide, Stanislav, Jens — thank you for making time. Luc, good to see
> you again if you're on. Really appreciated you (Davide) suggesting
> Stanislav for this — I think we'll cover more ground with your team
> together than we would 1-to-1."*

Set clock: *"I have 45 minutes in mind, tell me if any of you needs to drop
sooner. Would like to leave the last 10 minutes for practicalities."*

Ask permission: *"Would it be OK if I take notes, and quote or paraphrase
you in the IOF post-doc application later — I'd send you exact wording for
approval first?"*

Set the frame explicitly (this is a Filip guardrail thing but also just good
manners):

> *"Quick housekeeping — the method is in patent drafting with UGent
> TechTransfer, so I can talk about what it does but not how it works. If
> that ever becomes a blocker for something you want to see, please just
> tell me and we'll work out how to loosen it after the priority filing."*

**Listening cue.** How Colombi opens back. If he says *"tell us what you've
built,"* proceed to Scene 2. If he asks *"how did you find your way to
this?"*, spend 60 seconds on your CV / motivation, then Scene 2. If he asks
about NDAs, defer to Luc/Wout to sort out — Ericsson-side NDA path exists
per prior briefing.

## Scene 2 — Method quick-share (3-5 min) — YOU talk

Robin talks. Not a pitch, a substantive description. The three-sentence
guardrail applies. Aim for a real research description that Stanislav can
technically engage with.

> *"Very short version — we've built a forward model for exposure above
> 6 GHz that is very substantially faster than FDTD, similar accuracy where
> we've validated it, and differentiable end-to-end. Validated so far
> against Mie regression as our CI canary, ICNIRP 2020 limits implemented,
> and we're planning a matched Sim4Life comparison as the next external
> validation piece. Applications in mind are pre-compliance workflows at
> scale — codebook × traffic × pose sweeps, network-level compliance
> studies, deployment-density evaluations. Above 6 GHz specifically. Method
> details inside the patent, but I'm happy to talk about scope, validation
> plans, and what we think it lets you do."*

Then STOP. Let them ask.

**Listening cue.** Who speaks first tells you the vibe:
- Colombi first → strategic conversation (research fit, publication path)
- Stanislav first → technical conversation (validation, method scope)
- Bischoff first → integration conversation (scenes, DT, applications)

Route the follow-up accordingly.

## Scene 3 — Their evidence base (6-8 min) — THEM talk

Kick-off, with reference to the stadium paper:

> *"I read your 2025 stadium paper (Bischoff on there too, right?) —
> mean 7.6% and P95 9.5% actual EIRP is a really striking result. What's
> the pipeline of empirical studies your team is running next? Where is the
> evidence base thinnest — FR3, dense urban, indoor, distributed MIMO?"*

Reserve questions if the scene stalls:
- *"For that 60% compliance-distance reduction figure, what's the biggest
  variance driver — traffic profile, deployment class, antenna type?"*
- *"How do you decide which scenarios to campaign next?"*
- *"Is measurement infrastructure the rate-limiter, or modelling, or
  both?"*

**Listening cue for the AEGIS pitch.**
- If they say measurement is expensive and slow → productivity-multiplier
  angle is live. Segue in Scene 4.
- If they say modelling is limited by physics fidelity → validation-first
  angle. Segue to Scene 6 (Stanislav).
- If they say the pipeline is FR3-heavy or dense-urban-heavy → both angles
  become urgent, because they'll need it and FDTD won't scale.

**Route to.** Colombi (strategic), Bischoff (empirical / DT / SAR side).

## Scene 4 — Where a fast forward model would land (5-7 min) — MIXED

Now the honest AEGIS pitch, framed as "help me size where this fits your
world, not sell you something":

> *"Given your evidence-generation pipeline — if a validated fast forward
> model with FDTD-like accuracy existed and we handed you a Python or REST
> interface tomorrow, where would it fit your team's workflow most
> naturally? Extending the reach of stadium-style campaigns to more
> scenarios? Pre-screening deployments before you commit measurement
> time? Somewhere else?"*

Reserve questions:
- *"For a stadium-scale study — how many virtual scenarios would you
  ideally want to run around one real measurement campaign, if compute
  weren't the bottleneck?"*
- *"How much of your team's calendar time goes to running or waiting on
  simulations versus everything else?"* [Marta-template quotable]

**Listening cue.** If Colombi engages substantively here, that's the wedge
into a matched-validation collaboration. If he deflects to "we mostly do
measurement," the productivity-multiplier angle is weaker and the meeting
pivots to Scene 5 (DT).

## Scene 5 — Digital Twin — the sleeper scene (5-7 min) — BISCHOFF-LED

This is the scene Grangeat retired at Nokia and it might be the whole story
at Ericsson.

Kick-off, routed to Bischoff:

> *"Jens — I saw your name on the Digital Twin-based EMF Compliance paper.
> That's really interesting because I heard at another meeting the argument
> that this work isn't generalising into DT. Ericsson clearly disagrees. Can
> you say where you see Site Digital Twin heading with EMF compliance? Is
> it becoming a first-class feature or a niche capability?"*

Reserve questions:
- *"For the DT to do EMF compliance at scale — real-time-ish for many
  sites — where's the compute-time constraint today?"*
- *"Is there room for a fast forward model as a service inside the DT
  stack, or is that architecturally out of scope?"*
- *"How does the EMF-compliance piece of the DT get validated internally
  before Ericsson stakes a customer submission on it?"*

**Listening cue.** If Bischoff talks concretely about compute constraints,
scene throughput, or FDTD-integration pain in the DT context → AEGIS's home
just appeared. Follow up with:

> *"Would there be interest in a small pilot — I take a canonical scene
> from your DT test set, run AEGIS on it, and we compare to your reference
> FDTD or measurement? Non-commercial, published or not depending on what
> works for you."*

That is the concrete offer worth walking out with.

**Route to.** Bischoff (leading). Colombi will jump in on strategic
implications. Stanislav will jump in on validation methodology if AEGIS-in-DT
gets serious.

## Scene 6 — Stanislav's technical read (5-7 min) — STANISLAV-LED

This scene may happen naturally in Scene 2 or Scene 3. If it hasn't yet,
prompt it explicitly:

> *"Stanislav, given your numerical methods background — what would you
> want to see to actually believe this method delivers what I'm claiming?
> What's the acceptance bar for you personally, and what's the acceptance
> bar for Ericsson's compliance work more broadly?"*

Reserve questions:
- *"What benchmark scenarios would you personally reach for?"*
- *"Above and beyond the Mie sphere and ICNIRP 2020 test cases, what's
  your list?"*
- *"Where would you predict a fast surface-based method breaks down —
  which regimes should we test that we probably haven't thought of?"*

**Listening cue.** Substance and specificity.
- *"Interesting, would like to see the paper when it's out"* = polite dismiss.
- Naming specific benchmarks / regimes = real engagement.
- Asking clarifying questions on methodology = real engagement, guardrail
  applies.
- Asking about differentiability = wanted signal, cautious answer (see
  disclosure section below).

**Do NOT get baited into methodology detail.** Bounded answers, patent
guardrail, offer follow-up under NDA if needed.

**Route to.** Stanislav (lead). Colombi will jump in if standards
implications come up.

## Scene 7 — Close (5-7 min) — YOU-LED

At the 35-40 minute mark, transition:

> *"I don't want to hold you past what you signed up for — a few
> practicalities to close on, if I can."*

**Ask 1 — Support letter (primary).**
> *"Would you be open to a short letter of support for the IOF valorisation
> post-doc application? Not on behalf of Ericsson officially, just as a
> research team endorsement that this direction is worth pursuing. I have
> a draft you can start from — five-minute lift. And of course, I'd
> respect any framing you want, including anonymised."*

Colombi is the signer. But depending on how Scene 6 went, Stanislav's
technical read on the letter would be gold.

**Ask 2 — Matched-validation pilot (secondary, only if warm).**
> *"Longer term — would there be interest in a small matched-validation
> piece, on a benchmark scene of your choice? Non-commercial, non-binding,
> we take what we learn and you take what you learn."*

The concrete equivalent of what Marta agreed to.

**Ask 3 — Operator referrals.**
> *"Grangeat at Nokia gave me a few operator names (Vodafone, A1, an
> Italian contact). Given Ericsson runs its campaigns at operator sites —
> Optus for the stadium — do you have people on the operator side (network
> planning, EMF compliance) who you'd suggest I also speak to?"*

**Ask 4 — Quote permission.**
> *"If something you said today ends up shaping a sentence in the
> application, may I paraphrase — I'll send exact wording for approval
> first?"*

**Followup commitment.**
> *"I'll send the letter draft this week. Would end of next week work for
> you to take a look?"*

## Disclosure guardrail — one-page cheat sheet

**Method may be described only as** *"very substantially faster than FDTD,
similar accuracy, differentiable end-to-end."*

**If pressed on how it works:** *"That's exactly the part still under
patent drafting with UGent TechTransfer, so I have to keep it closed for
now. Happy to talk about scope, validation plans, and what it lets you do."*

**Differentiability question:** *"Gradients w.r.t. any input parameter
you'd want to sweep — antenna weights, positions, beam parameters, geometry.
Details inside the patent."* Do NOT say analytical, closed-form, JAX, GPU,
voxel, ray-tracing, Fresnel, Brewster, pseudo-Brewster, operator
decomposition, MIMO operator.

**Validation questions:** open. Mie regression, ICNIRP 2020, planned
Sim4Life matched validation. These are all publishable / claimed content.

**Scope questions:** open. 6-100 GHz core, extends to 300 GHz. Surface
absorption. Radiative regime (d > λ/2π). No implants, no intra-body.

**If Stanislav pushes hard on method specifics you can't share:** *"I want
to keep the meeting productive — could we set up a follow-up under NDA
once TechTransfer has cleared the disclosure boundary? I think we could
go much deeper then."* That preserves the relationship and the guardrail
at once.

**If NDA path exists with Ericsson via Luc:** confirm before assuming. The
external_briefing.md mentions Luc's Ericsson NDA-stage contact, but that
may not extend to Stanislav / Bischoff automatically.

## Capture template (fill in during / right after)

```
Attendees:
Date:
Duration:

Colombi:
  - Their evidence-generation pipeline direction (verbatim):
  - Where fast forward model would fit (verbatim):
  - Support-letter openness:
  - Operator referrals (names):

Stanislav (the critical read):
  - Overall technical read of AEGIS (verbatim if possible):
  - Named benchmark scenarios they'd want:
  - Named potential breakdown regimes:
  - Willingness to see follow-up under NDA:

Bischoff:
  - Digital Twin direction at Ericsson (verbatim):
  - EMF-compliance-in-DT compute constraint:
  - Openness to matched-validation pilot in DT scene:

Luc (if present):
  - Any Ericsson-culture signals:
  - Any post-meeting soft-intro possibilities named:

Numbers extracted:
  - Team size on EMF:
  - Papers/year output:
  - Measurement campaigns/year:
  - Any budget or spend numbers:
  - FDTD time per scenario:
  - Ideal scenarios/year if compute unlimited:

Asks landed:
  [ ] Support letter draft to send this week
  [ ] Matched-validation pilot interest
  [ ] Quote permission (per-person)
  [ ] Referral names
  [ ] Follow-up under NDA

Follow-up actions + by when:
```

## What NOT to do (repeat from Nokia dossier, still applies)

- Don't attach documents. No one-pager. Stage-2 discovery meeting.
- Don't push the standards path (Grangeat gave you the answer).
- Don't oversell. Especially in front of Stanislav.
- Don't apologise for the patent — state the guardrail once, calmly.
- Don't stay past the clock unless they push you.

## What IS different from the Nokia meeting

- Multi-person, so route topics. Don't fire everything at Colombi.
- Stanislav's technical read is the highest-leverage single output. Prepare
  for it and don't get baited into methodology detail that endangers it.
- Digital Twin is a genuine live thread here — treat Bischoff scene as a
  real scene, not filler.
- Ask ladder is otherwise the same shape: support letter → matched
  validation → referrals → quote permission → follow-up.
