# Christophe Grangeat — profile

## Roles

- **EMF Mitigation Lead, Nokia** — France-based. Not an academic. Not a Bell
  Labs researcher in title, but the co-author of most of Nokia's applied EMF
  publications through the 2020s. The "principal system architect" framing
  appears in his ResearchGate bio and in the IEC recognition citations.
- **Convenor of IEC TC106 MT3** — Maintenance Team 3 inside Technical Committee
  106 (Methods for the assessment of electric, magnetic and electromagnetic
  fields associated with human exposure). MT3 specifically owns **IEC 62232**
  (base station RF exposure assessment, 110 MHz to 300 GHz) and **IEC TR 62669**
  (case studies supporting IEC 62232). 80+ registered members from 21 national
  committees per his 2024 tutorial slide 4.

Convenor is a load-bearing role. It means he runs the meetings, decides what
gets tabled, edits text through the committee stages, and holds the redline pen
between editions. He does not vote alone, but the workflow flows through him.

## Standards work he actually did (documented)

- **IEC 62232:2022 Ed. 3.0** — he drove the introduction of the actual-maximum
  approach (Clause 6.2.3, Clause 8.4, Annex B.9). The headline change of that
  edition is the actual-max power reduction factor F_PR, which shrinks
  compliance distances by roughly a factor of 3 to 10 vs the theoretical-max
  baseline. This is his single most impactful contribution to public policy.
- **IEC 62232:2024 Ed. 4.0** — same technical content, editorial cleanup and
  alignment with TR 62669 Ed. 3.0. Published end-2024 (Robin's
  `standards_brief.tex` calls it "2025" — the ISO/IEC publication date drifted
  a bit but the content is Ed. 4.0). Confirmed on his tutorial slide 29.
- **IEC TR 62669:2019 Ed. 2.0** — 16 case studies from 8 national committees.
  He is credited in the IEC citation for delivering this edition.
- **IEC TR 62669 Ed. 3.0** — expected 2025 with 30+ case studies from 13
  national committees. **The additional content targets exactly three areas:
  actual-maximum implementation and validation, extrapolation techniques for 5G
  massive MIMO signals, and emerging laboratory measurement methods related to
  ICNIRP 2020.** All three are relevant to AEGIS. Details on slide 30 of his
  2024 tutorial.

## Adjacent standards footprint

- **CENELEC TC106X WG1** — EN 50385 and EN 50401 are being updated to align
  with IEC/EN 62232:2024. Both are referenced in the Official Journal of the
  EU, so they are the actual product standard a base station has to comply with
  in EU markets. Grangeat's IEC work flows directly into CENELEC.
- **ITU-T SG5 Q3/5** — K.52 (guidance on complying with limits) and K.100
  (measurement of RF EMF for base station compliance) were updated August 2024.
  He tracks and coordinates but does not chair.
- **GSMA EMF Forum** — the industry venue where he presents this material to
  operators, regulators, and NGOs. The 2024 tutorial (Brussels, October 2024)
  is the piece of material Robin has.
- **BioEM 2025 Tutorial 3** — same material, academic audience. He also
  delivered the tutorial there.

## Nokia-internal footprint (inferred from co-author graph)

Grangeat sits between two distinct Nokia EMF research clusters. See
`02_nokia_emf_research.md` for depth. The important structural point for the
call: he is the **only Nokia author who co-authors with both clusters**. That
means he is the bridge between the physical-layer channel-modelling work
(Poland Bell Labs) and the MAC/RRM control work (France Bell Labs). Anyone
asking "who owns EMF at Nokia" gets Grangeat as the answer.

## Prior contact with Robin

Robin met Grangeat once at a GSMA event two years ago in the context of the
**GSMA OUTREACH initiative** (industry-academic dialogue on measurement-model
consistency). This is not a cold contact — the "You may remember me" framing
in the outreach email is accurate. Robin's opener can lean into this: *"I
remember the OUTREACH work — is that thread still active, and does anything
from it still feed into MT3?"* costs nothing, signals continuity, and can
surface a natural warm intro to whoever else at Nokia is in that circle.

## What Grangeat cares about, best available inference

From reading his 2024 tutorial, the 2018 statistical paper he co-authored with
the Ericsson-side team, and the 2023-2024 Nokia-Poland and Nokia-France paper
run, I read the following priorities:

1. **Defending the actual-maximum approach against regulator or public pushback.**
   The narrative is "compliance is now defensibly less conservative because we
   have measured, modelled, and validated the actual power distribution." Every
   time a regulator or NGO asks "how do we know?", his answer is the 20+
   modelling and experimental studies now compiled in TR 62669 Ed. 3.0.
2. **Extending actual-max to the frontier.** FR3 (7-15 GHz, extreme massive
   MIMO), moving UEs, mmW extrapolation — Nokia has actively been publishing
   in these areas 2023-2024. Any tool that helps him harden the FR3 evidence
   base has an ally.
3. **MCF validation** — monitoring and control features that let the network
   operator prove the actual EIRP threshold is not exceeded during operation.
   Clause 8.4 and Annex C of IEC 62232 are his baby, and the OTA validation
   in an anechoic chamber (slide 22) is a piece of workflow that AEGIS could
   pre-screen.
4. **Not being blindsided by ML surrogates.** A parallel wave of physics-informed
   ML approaches (Bilson/NPL 2024, R^2 = 0.86) is arriving. He is not publicly
   on record about them yet, but as convenor he has to decide how they get
   handled in TR 62669 and eventually 62232. AEGIS's closed-form differentiable
   approach is a distinct entry into that conversation.

## Contact info

- Email: `Christophe.Grangeat@nokia.com` (from `outreach_emails.md`)
- LinkedIn: `linkedin.com/in/grangeat-christophe-03a369b`
- ResearchGate: findable via co-author graph (Rybakowski, Bechta, Maggi)
- IEEE Xplore author ID: 37546201600 (server blocks WebFetch, use browser)
