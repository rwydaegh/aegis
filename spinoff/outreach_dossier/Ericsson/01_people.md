# The people in the room

Four possible attendees. Each has a distinct role — route topics to whoever
naturally holds them, don't fire everything at Colombi.

## Davide Colombi — Master Researcher, Ericsson Research Stockholm

**Role.** Master Researcher (senior individual-contributor rank at Ericsson).
Has been at Ericsson on RF exposure since 2014 — 10+ years. M.Sc. from
Politecnico di Milano 2009. Based Kista, Stockholm.

**Standards affiliation.** IEC TC 106 member. IEEE ICES SC4 activity. Was the
Ericsson-side seed author for the actual-max approach that ended up in IEC
62232:2022.

**Publications you should know (see `02_ericsson_evidence_base.md` for
depth).**
- 2018 with Baracca (Nokia), Weber (Nokia), Wild (Nokia), Grangeat (Nokia):
  arXiv 1801.08351 — the seed paper that halved compliance distance.
- 2021 Frontiers Public Health (PMC8777231): Monte Carlo actual-max at mmW,
  the seed paper that showed actual-max applies above 24 GHz.
- 2025 IEEE Antennas and Wireless Propagation Letters: **stadium 100k people
  measurement, mean actual EIRP 7.6% of theoretical max, P95 9.5%, ~60%
  compliance distance reduction.** This is the state-of-the-art result.
- Multiple Ericsson whitepapers on 5G EMF — most-cited: October 2021
  "Accurately assessing exposure to RF EMF from 5G networks."

**What he thinks and cares about.** Empirical validation of actual-max at
scale. Getting the number right (P95, 60% reduction), publishing it in
peer-reviewed venues, defending it in front of NGOs and regulators. Less
political than Grangeat, more scientific. Also: he is the person Ericsson
sends to defend the actual-max thesis when someone attacks it publicly.

**What to route to him.** Strategic questions on Ericsson's research
pipeline, standards adoption trajectory, defensibility of tighter envelopes,
operator relationships (his team runs field campaigns at operator sites),
and the ask ladder (support letter, referrals). He is the person who signs.

**What he might ask you.** *"Have you validated against measured data?"*
(answer: Mie regression + planned Sim4Life matched validation — GOLIAT
drives that side). *"What's your uncertainty budget?"* (answer: work in
progress, will publish). *"Where does this differ from what's already in
Annex B.7?"* (answer: bounded — speed, then patent guardrail).

**The email tone.** *"Great to hear from you. We are definitely interested
in learning more about what you have developed."* That is a warm-lean-in
line, not a boilerplate reply. He is genuinely curious. Reward that with
substance, not sales.

## Stanislav Stefanov Zhekov — Ericsson Research, Kista

**Role.** Researcher, PhD. Focus per his ResearchGate: antennas, radio
propagation, absorbers, EMF exposure, OTA testing. Multi-hat but centrally a
numerical-methods person.

**Standards affiliation.** IEC (per his LinkedIn) — same TC 106 orbit.

**Publications you should know.**
- "Numerical Methods in Antenna Modeling" (this is the direct match for
  Colombi's *"strong expertise in numerical methods"* line).
- FDTD modelling of indoor propagation, with focus on numerical dispersion
  and anisotropy artefacts.
- Multi-antenna OTA evaluation (TRP, TIS).
- Building attenuation studies.

**Why Colombi routed you to him.** Explicit signal in the email:
*"who has strong expertise in numerical methods, is best suited to follow up
on this topic."* Meaning: Colombi wants an internal technical evaluation
before Ericsson engages further. Stanislav will actually understand what
Robin says about differentiable methods, closed-form kernels, Fresnel
transmission characteristics, and speed vs accuracy trade-offs. **He is the
technical gatekeeper.**

**What to route to him.** Anything about method fidelity, validation
strategy, benchmark scenarios, uncertainty analysis. If Robin says *"we have
Mie regression as our CI canary,"* Stanislav will understand what that
means. If Robin says *"we're differentiable end-to-end so gradients w.r.t.
antenna weights are exact,"* Stanislav will know whether that's a real
research contribution or a talking point.

**What he might ask you.** Deep specifics. Which mesh formats? What
frequency ranges validated? What's the accuracy vs FDTD you're claiming and
against what reference cases? Do you handle multi-layer skin? What about
grazing incidence — Fresnel diverges. **These are traps if Filip's guardrail
holds, so bounded answers with "the details are inside the patent, happy to
show validation figures."**

**Careful.** If Stanislav concludes AEGIS is "just a fast pre-screening
tool that trades physics for speed and can't be trusted for compliance," he
kills the thesis at Ericsson. Winning him = winning the technical fight.
Losing him without recovering = the whole meeting is downhill. Show respect,
show that you've thought about validation, and defer specifics graciously to
the patent gate.

## Jens Eilers Bischoff — Ericsson

**Role.** Junior-to-mid researcher, based on the KTH degree-project origin
of his SAR-measurement work. Now on the Ericsson Research team.

**Publications you should know.**
- KTH degree project: "Whole-body SAR measurements of millimetre-wave base
  stations in a reverberation chamber." Directly adjacent to AEGIS's
  computational SAR work.
- Co-author on the 2025 IEEE APWL stadium paper with Colombi.
- **Co-author on "Digital Twin-Based EMF Compliance Assessment of Base
  Station Sites"** — IEEE Xplore document 10999394, and separately on the
  EMF-portal.org referenced study *"Digital Twin-Based Evaluation of RF
  Exposure Compliance for Base-Station Antennas in Stadium Environments."*
  This is the killer piece. See `02_ericsson_evidence_base.md`.

**What to route to him.** The Digital Twin thread. If the conversation drifts
toward "how do you evaluate EMF compliance in an actual scene," pull him in.
His DT paper is Ericsson's live position on what Grangeat said doesn't
exist. This is a natural AEGIS home.

**What he might ask you.** More applied questions — how does AEGIS handle
multi-source scenes, how does it plug into a scene description, what mesh
resolution, can it stream results into a DT viewer. Robin can answer these
with bounded technical detail (mesh formats, JSON scene, fast per-antenna
evaluation) without giving up the method.

**The interesting play.** If Bischoff is enthusiastic about DT + AEGIS, this
is the wedge into Ericsson's product side (Site Digital Twin is a shipping
product, not a research project). That's a fundamentally different pitch
from Ericsson-Research paper collaboration.

## Luc Martens — UGent-INTEC-WAVES, co-PI (Wout's co-supervisor group)

**Role, if present.** The warm intro. Colombi is a personal contact of
Luc's per `../../LATEST_GOOD/external_briefing.md`. If Luc attends, he
brings warmth, personal credibility, and an implicit "Robin is my student's
peer" framing. That changes the tone from formal to family.

**What to route to him.** Anything about the Ericsson relationship history,
UGent-Ericsson prior collaborations, and if the meeting drifts strategic,
defer to him for *"Luc, how does this normally land culturally at Ericsson
Research?"* That is a graceful pass-the-mic move.

**What Luc will do.** Almost certainly stay quiet unless invited, then speak
with authority on the Ericsson-side relationship. Do not fear Luc entering
sales-mode — that is not his style. He is more likely to gently vouch for
Robin's work if asked, which is exactly what a warm intro is worth.

**If Luc is not present.** The meeting stays "professor's student meets
research team" tone rather than "family peer visit." Small tonal
recalibration; content is unchanged.

## The routing matrix — quick reference

| Topic | Primary | Secondary | Notes |
|---|---|---|---|
| Method quick-share (60 sec setup) | Robin → all | — | Say once, don't repeat |
| Empirical evidence generation | Colombi | Bischoff | Their AFL stadium work |
| Ericsson Site Digital Twin | Bischoff | Colombi | The natural AEGIS home |
| Technical validation approach | Stanislav | Colombi | Stanislav will interrogate |
| Standards path (already actioned) | Colombi | — | Ask if he'd support Wout tabling |
| Operator relationships / referrals | Colombi | — | Grangeat gave 4; more here |
| Ericsson research pipeline for FR3 | Colombi | Bischoff | Where AEGIS fits, if at all |
| Support letter ask | Colombi | — | Personal / research-team framing |
| UGent relationship / warm bridge | Luc | — | If present |
