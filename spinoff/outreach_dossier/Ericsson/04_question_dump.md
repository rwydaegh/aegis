# Big question dump

Not a script. A reservoir. Grab whatever the conversation actually needs.
The scenes in `03_meeting_flow.md` say WHEN — this file says WHAT.

Organized by target person, then by topic. Includes reserve variants,
follow-ups, and the "trap door" questions you can drop when a scene
stalls or opens unexpectedly wide. Star (★) = highest priority, ask if
at all possible. Cross (†) = only if a natural opening exists.

Legend:
- `[C]` = Colombi
- `[S]` = Stanislav Zhekov
- `[B]` = Bischoff
- `[L]` = Luc (if present)
- `[ALL]` = whoever picks it up

---

## PART A — the empirical / research-pipeline block (Colombi)

### A1. The stadium paper and what came next ★

- `[C]` I read your 2025 AFL stadium paper. Mean 7.6% actual EIRP, P95 9.5% — really striking numbers. What's the reception been like from regulators, from operators, from the broader TC 106 community?
- `[C]` What was the biggest surprise for you personally in that data?
- `[C]` What has your team run since the stadium campaign? What's in the current publication pipeline?
- `[C]` Where's the evidence base thinnest right now — FR3 upper mid-band, dense urban, indoor, distributed MIMO, industrial?
- `[C]` If you had to pick the one scenario Ericsson most needs a next-stadium-scale campaign for, which is it and why?
- `[C]` † The 60% compliance-distance reduction — what's the biggest variance driver behind that number? Traffic profile, deployment class, antenna type, network policy?

### A2. Pipeline economics (the Marta-template numbers) ★

- `[C]` Roughly how many people on your team are dedicated to actual-max evidence generation, day-to-day?
- `[C]` How many peer-reviewed EMF papers does your team target per year? Is that a hard number or a soft one?
- `[C]` What's the ballpark calendar time between "start a study" and "paper draft submitted"?
- `[C]` For a stadium-class campaign — where does the calendar time actually go? Measurement infrastructure? Statistical analysis? Simulation? Waiting?
- `[C]` If compute weren't the bottleneck, how many virtual scenarios would you ideally run around one real measurement campaign?
- `[C]` Do you feel bottlenecked by simulation throughput today, or is measurement the harder constraint?
- `[C]` What tools does the team currently use for the simulation piece — Sim4Life, custom code, in-house solvers, all of the above?

### A3. FR3 and the near-future ★

- `[C]` FR3 (7-15 GHz) is where the standards conversation is heading. Where does Ericsson's evidence base sit for that band today?
- `[C]` Is there anyone at Ericsson running a "get ready for FR3 EMF" pipeline yet, or is that still one horizon out?
- `[C]` Extreme massive MIMO at FR3 with sub-6 pathloss — do you expect actual-max behavior to look similar to sub-6, similar to mmW, or something new?
- `[C]` † Any bets on where the actual-max ratios end up — closer to your sub-6 numbers or closer to your mmW ones?

### A4. The standards-adoption trajectory ★

- `[C]` What does the roadmap for TR 62669 look like from your side — do you expect Ed. 4.0 within 2-3 years, or is the door effectively closed until Ed. 5.0?
- `[C]` Where does Ericsson's current evidence base need more depth before it can support broader adoption of the reduced envelopes in TR 62669?
- `[C]` Grangeat pointed me at a 5-slide vote-to-WG path with Wout tabling. If Wout brought a body-aware fast-forward-model contribution to a future meeting, would Ericsson support that in principle?
- `[C]` Is there a scenario where Ericsson wants to see this kind of method inside the standard versus keep it in industry-only tooling? What would drive that call?

### A5. Operator relationships and referrals ★

- `[C]` Your stadium campaign was on Optus. Which operators does Ericsson typically run field campaigns with — Optus, Vodafone, DT, Telefonica?
- `[C]` Are there people on the operator side — network-planning, EMF compliance, regulatory affairs — who you'd point me at?
- `[C]` Grangeat pointed me at Stephan Zeitz at Vodafone, Ricardo Suman in Italy, and Manfred Rutner at A1. Are any of those live for you, or would you route me differently?
- `[C]` † Anyone in the regulator community (ITU-R, national telecom regulators) who's been asking the right questions and who'd be worth talking to?

### A6. Ericsson's tooling and the internal build/buy question † (soft)

- `[C]` For the simulation piece of your work — is that in-house infrastructure that Ericsson has developed, or licensed commercial tools, or both?
- `[C]` Has there been internal effort at Ericsson to build a faster forward model? If yes, is that public knowledge?
- `[C]` If a validated fast forward model with the accuracy claims we're making showed up externally, would Ericsson Research typically integrate it, license it, or replicate it internally?
- `[C]` What matters more to your team — speed, accuracy at edge cases, differentiability, or something else I'm not thinking of?

---

## PART B — the technical / validation block (Stanislav — MOST IMPORTANT)

**Robin note:** this is Stanislav's zone. Colombi will jump in on standards
implications. The goal here isn't to sell — it's to demonstrate you've
thought hard about validation. Bounded answers, patent guardrail, defer
specifics graciously.

### B1. The technical read ★

- `[S]` Given your numerical-methods background, what would you personally want to see before you believe the accuracy-vs-speed claims we're making?
- `[S]` What's your personal acceptance bar for a fast forward model — accuracy vs a specific reference case, statistical validation, something more structural?
- `[S]` What's Ericsson's acceptance bar for methods that end up in compliance work — internal validation, published validation, matched cross-tool, all of the above?
- `[S]` Where does your team's confidence in Sim4Life / CST / custom FDTD live? What's the reference of last resort at Ericsson?

### B2. Benchmark scenarios ★

- `[S]` What benchmarks does your team reach for first when evaluating a new forward model?
- `[S]` Beyond the Mie sphere and ICNIRP 2020 test cases, what's on your standard test list?
- `[S]` Are there benchmark cases you feel the community underuses — canonical scenarios that would be more diagnostic than the standard set?
- `[S]` For validating body-aware exposure specifically — what phantom + scenario combinations do you consider gold standard?
- `[S]` What matched-tool comparisons has Ericsson done recently — FDTD vs analytical, FDTD vs MoM, FDTD vs ray-tracing?

### B3. Predicted failure regimes ★

- `[S]` Where would you predict a fast surface-based method breaks down — which regimes should we be stress-testing that we probably haven't thought of?
- `[S]` What are the physically hard corners for exposure computation above 6 GHz — grazing incidence, near-body coupling, multi-body, near-field, resonances?
- `[S]` Have you seen fast approximations fail publicly at FDTD in ways that surprised you?
- `[S]` What's your take on the fidelity floor for compliance work — how good does a forward model need to be before it can be trusted for a submission versus just for pre-screening?

### B4. Method architecture (bounded, only if invited)

**Guardrail: bounded answers, patent gate.** Ready for Stanislav to probe.

- `[S]` What frequency ranges are we validated across today? (Answer: 6-100 GHz core, tested to 300 GHz, Mie regression as CI canary. Bounded.)
- `[S]` What phantom formats? (Answer: STL meshes, current library thelonious/duke/eartha/ella, extendable. Bounded.)
- `[S]` Multi-layer skin, dispersive tissue? (Answer: Cole-Cole model, IT'IS database, Fresnel coefficients at every triangle. Bounded — but say no more.)
- `[S]` Differentiability — what gradients? (Answer: gradients w.r.t. any input parameter you'd sweep — antenna weights, positions, beam parameters, geometry. Details inside the patent.)
- `[S]` Grazing incidence and Fresnel divergence — how handled? (Answer: acknowledged as a hard corner, engineered handling inside the patent, part of what makes the method non-trivial.)
- `[S]` Multi-source coherence? (Answer: coherent MIMO fully supported, exposure operator Q formulation. Levels 7-8 in our fidelity hierarchy. Bounded.)
- `[S]` GPU / JAX / scaling? (Answer: JAX backend available, current benchmarks show us [insert current honest number] vs FDTD reference. Bounded.)

### B5. The differentiability question (Stanislav will ask) ★

**Guardrail: internal Robin honesty:** per the 2026-07 differentiability
study, differentiability doesn't carry a business, but Fock finite-Lipschitz
is the surviving genuine claim. For Stanislav:

- `[S]` The differentiability isn't a magic bullet — it's useful for parameter sensitivity, inverse design of scenarios, and gradient-based optimization of deployment layouts. Do you see specific research problems where that would meaningfully change your team's methodology?
- `[S]` Where do you think end-to-end gradients would matter most — in the standards-evidence work Colombi's team does, in DT integration, or somewhere else?
- `[S]` Any risk you see in relying on gradient-based methods for compliance work — validation asymmetry, over-fitting scenarios?

### B6. Uncertainty and reproducibility ★

- `[S]` What's your view on uncertainty budgets for computational EMF work — how does Ericsson decide what uncertainty is publishable versus preliminary?
- `[S]` The metrological chain for actual-max — is that becoming a real standards conversation or still mostly method-of-moments approach?
- `[S]` For a paper on a new forward model, what uncertainty analysis would you consider table stakes?

---

## PART C — the Digital Twin block (Bischoff — sleeper thread)

**Robin note:** if this scene lights up, it's the best scene of the
meeting. If Bischoff engages, treat as high-priority follow-up.

### C1. The DT paper and where it's going ★

- `[B]` I saw your name on the Digital Twin-Based EMF Compliance Assessment paper — really interesting piece. Can you tell me where Ericsson Site Digital Twin sits with EMF compliance today? Shipping feature, R&D exploration, something else?
- `[B]` The Ericsson blog from November 2025 talks about Site Digital Twin generally. Is the EMF compliance functionality a first-class feature or an R&D thread?
- `[B]` How did you end up on this thread — DT-first researcher, EMF-first researcher, or convergence?
- `[B]` Where do you see the DT + EMF story going in the next 2-3 years — deeper into deployment automation, or broader into other radio-planning integrations?

### C2. Compute and integration constraints ★

- `[B]` For DT-based EMF compliance at scale — many sites, many antenna configurations, replay of deployment scenarios — where's the compute-time constraint today?
- `[B]` Is FDTD or full-wave simulation currently in the loop for the DT compliance piece, or is it precomputed / cached / analytical?
- `[B]` What per-scene compute budget would matter for the DT to do EMF compliance in near-real-time for a customer submission workflow?
- `[B]` Is there a "fast forward model as a service inside the DT stack" architectural pattern that's plausible for you, or is that out of scope architecturally?

### C3. The concrete pilot offer ★

- `[B]` Would there be interest in a small pilot — I take a canonical scene from your DT test set, run AEGIS on it, we compare to your reference (FDTD, measurement, whatever you use)? Non-commercial, published or not depending on what works for you.
- `[B]` If a pilot is interesting — what would the scene look like? Stadium, dense urban, industrial, indoor small-cell?
- `[B]` Who would need to be in that conversation on the Ericsson side? DT product owners, compliance team, research?

### C4. SAR-side questions (Bischoff's KTH thread)

- `[B]` Your KTH work was on whole-body SAR measurements of mmW BS in a reverberation chamber. Is the reverberation-chamber approach still Ericsson's preferred measurement modality for whole-body SAR at mmW, or has that evolved?
- `[B]` For computational SAR at mmW — is that mostly Sim4Life-driven today at Ericsson, or in-house?
- `[B]` The device-side / handset-side world (63195-2) versus BS-side (62232) — does that cross-pollinate at Ericsson? Different teams, or shared?

### C5. Product side vs research side

- `[B]` The Site DT is a shipping product — the EMF-compliance conversation would be different for the product team than for research. Which side would this initially matter to?
- `[B]` If Ericsson Site DT wanted a fast forward model, would that decision live in research, in product, or in the compliance team?

---

## PART D — the strategic / meta questions [ALL]

### D1. Where AEGIS naturally fits (or doesn't) ★

- `[ALL]` If a validated fast forward model with FDTD-like accuracy existed and we handed you a Python API tomorrow, where would it fit your team's workflow most naturally?
- `[ALL]` Is the natural fit "research productivity multiplier" (more virtual scenarios per real campaign), "pre-screening" (before committing measurement time), "DT integration," "customer-facing compliance," or none of the above?
- `[ALL]` What would make this a "no, not a fit at Ericsson" versus "yes, interesting for us"?
- `[ALL]` What's the honest AEGIS-shaped hole in Ericsson's toolchain today, if there is one?

### D2. The commercial reality question (the Grangeat frame) ★

**Grangeat verdict — "att will not buy nokia instead of ericsson cuz of this."**
Test that at Ericsson without leading:

- `[ALL]` Grangeat's read at Nokia was that operators don't ask for tighter compliance envelopes as a purchasing criterion — you sell them networks, not compliance tools. Does that match Ericsson's read of the operator market, or does the operator conversation look different from where you sit?
- `[ALL]` Is there a scenario where an operator or a regulator asks for compliance envelope evidence that Ericsson doesn't have today? What would that scenario look like?
- `[ALL]` Where does the value of tighter envelopes actually accrue to Ericsson — deployment cost, standards defensibility, permit process, something else?

### D3. The competitor question † (careful)

- `[ALL]` Is Ericsson aware of internal or external efforts building fast forward models in this space? (Careful: this is asking about competitors. Frame carefully.)
- `[ALL]` The academic community — Marta at CNR, Wout's group, ETH Sim4Life team, IT'IS Foundation — who does Ericsson consider the natural collaborators here?
- `[ALL]` Is anyone at Ericsson thinking about ML-surrogate forward models — physics-informed neural nets, learned Green's functions? (Bilson NPL 2024 direction.)

---

## PART E — the ask ladder [Colombi primary]

### E1. Support letter ★

- `[C]` Would you be open to a short letter of support for the IOF valorisation post-doc application? Not on behalf of Ericsson officially — just as a research-team endorsement that this direction is worth pursuing.
- `[C]` I have a draft you can start from — five-minute lift. Would that be OK?
- `[C]` Any framing preferences — anonymised, personal, research-team-scoped, no company mention?
- `[C]` Depending on how the technical conversation went — would Stanislav's read be something you'd want to reference in the letter?

### E2. Matched-validation pilot ★

- `[C]/[B]` Longer term — would there be interest in a small matched-validation piece? Non-commercial, non-binding, we take what we learn and you take what you learn. Marta at CNR agreed to something similar with us.
- `[C]/[B]` If yes — what scene / benchmark would you propose? We can match to whatever reference you have.
- `[C]/[B]` What's the smallest first-step version of this that would be worth trying?

### E3. Referrals

- `[C]` I asked Grangeat about operator names and he was generous with them. Are there people on the operator side (network-planning, EMF compliance) you'd suggest I also speak to?
- `[C]` Anyone at IEC ICES, ITU-R, or on the regulator side who you'd naturally point someone at?
- `[C]` Academic collaborators — where in Europe / globally does the actual-max evidence generation live outside Ericsson?

### E4. Quote permission and follow-up mechanics

- `[ALL]` If something you said today ends up shaping a sentence in the application, may I paraphrase — I'll send exact wording for approval first?
- `[ALL]` Best channel for follow-up — email, LinkedIn, an Ericsson-portal I should know about?
- `[ALL]` Are there any conferences or working-group meetings coming up where you'd be willing to introduce me or connect me with the right people?

### E5. Follow-up under NDA (if the technical read went well)

- `[C]/[S]` If Stanislav's technical read was positive and you want to see method specifics — would you want to set up a follow-up under NDA? The Ericsson NDA path via Luc's group should still be live for that.

---

## PART F — the Luc-warm intro block (if Luc is on the call)

### F1. UGent-Ericsson history

- `[L]` Luc, remind us where the UGent-Ericsson relationship sits historically — any prior collaborations you'd want to reference here?
- `[L]` How does UGent typically structure research collaborations with Ericsson — bilateral, EU-project-anchored, PhD-embedded?
- `[L]` Any Ericsson-culture signals you'd want to flag for me about how to work with this team specifically?

### F2. The graceful pass-mic move

- `[L]` If a scene drifts into strategic territory: *"Luc — how does this usually land culturally at Ericsson Research?"* Deferential and lets him vouch.
- `[L]` If the standards path comes up: *"Luc, you've been through TC 106 sessions with Wout — what would you flag for Colombi about how Wout would want to bring this to a working group?"*

---

## PART G — trap-door questions for when a scene stalls

When a scene runs dry earlier than expected, drop one of these to reopen
the conversation without forcing a topic-switch:

- `[ALL]` What's the one question the community isn't asking that they should be?
- `[ALL]` If you had a magic wand for EMF compliance at Ericsson — one thing you could change tomorrow — what would it be?
- `[ALL]` What's the most surprising result any of you has seen in the last year of measurements or simulations?
- `[ALL]` What would make TR 62669 Ed. 4.0 a bigger deal than Ed. 3.0 was, if anything?
- `[ALL]` Anyone in the EMF world you think is underrated — whose work I should be reading?
- `[ALL]` Anyone in this space who's asking the wrong questions? (Careful — avoid gossip, aim for direction of the field.)
- `[ALL]` Where's the biggest disconnect between what compliance engineers need and what the research literature actually delivers?

---

## PART H — questions I should NOT ask

- Anything that reveals AEGIS method internals beyond the guardrail.
- "Would you buy this from us?" — Grangeat closed that door for Nokia; assume same at Ericsson until proven otherwise. Ask about workflow fit, not purchase intent.
- "Would you fund this?" — wrong stage, wrong meeting.
- Anything that pushes Colombi to commit on standards politics before he's ready. Ask about openness to a Wout-tabled contribution, not "will Ericsson vote for this."
- "Is this better than Sim4Life?" — leading, not useful. Reframe as "where does something like this fit alongside Sim4Life."
- "How much does Sim4Life cost you?" — too commercial too early.
- Questions that reveal I've read Grangeat's meeting notes verbatim ("Grangeat said your DT doesn't exist and clearly he's wrong" — never phrase like this, even in your head).

---

## PART I — questions I hope THEY ask me (be ready)

Not to volunteer, but if they ask, have crisp answers:

- **"What have you validated against?"** → Mie regression as CI canary, ICNIRP 2020 limits implemented, planned Sim4Life matched validation, GOLIAT-side comparison paper in progress.
- **"What's the accuracy claim?"** → [insert current honest number vs FDTD reference]. Bounded.
- **"What's the speed claim?"** → substantial multiple over FDTD in the compute regimes we've tested. Bounded — don't give the exact number unless pushed.
- **"Where does this break?"** → grazing incidence (Fresnel divergence, engineered handling), near-field close to source, intra-body absorption not modelled (surface-based). Bounded but honest.
- **"Who else is doing this?"** → nobody with our combination of speed + differentiability + BS-side focus; adjacent efforts include Sim4Life ML surrogates, physics-informed NNs (Bilson NPL 2024), but not directly comparable.
- **"When is it publishable / commercially available?"** → patent priority filing pending, publications planned post-filing, licensing conversations happen through UGent TechTransfer.
- **"What's your commercial model?"** → still being sized — options include OEM licensing (Ericsson-shape), consultancy studies (Marta-shape), or SaaS. Meeting is Stage-2 discovery to understand fit.
- **"Why us and why now?"** → your evidence-generation work is state-of-the-art (stadium paper), Site DT is a natural home, and Ericsson's technical bar (Stanislav's numerical-methods expertise) is what will make the method credible externally.
