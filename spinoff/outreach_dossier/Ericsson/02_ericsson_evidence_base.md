# Ericsson's actual-max evidence base + the Digital Twin angle

Ericsson's role in the actual-maximum approach is not "convenor of the
committee" (that's Grangeat). It's **the empirical evidence generator whose
data ended up in the standard.** Distinct posture, distinct meeting.

## The evidence arc, 2018 → 2025

**2018 (arXiv 1801.08351)** — Baracca, Weber, Wild, Grangeat. Statistical
approach for RF exposure compliance boundary assessment in massive MIMO.
Compliance distance halved vs traditional method. This is the seed. Notice
the co-author list is Nokia-heavy: Ericsson-side authorship really enters
with Colombi's own work.

**2021 (Frontiers Public Health, PMC8777231)** — Colombi lead author.
Monte Carlo analysis of actual maximum exposure from 5G mmW BS antenna for
EMF compliance assessments. **Establishes actual-max applies at mmW, not
just sub-6.** Foundational for TR 62669 Ed. 3.0 mmW content.

**2021 October** — Ericsson White Paper GFTL-21:000987, "Accurately
assessing exposure to radio frequency electromagnetic fields from 5G
networks." Colombi & team. The public-facing version of the technical
argument.

**2025 January (IEEE APWL, Vol 24, Issue 1)** — Colombi, Di Paola, Joshi,
Xu, Bischoff, plus co-authors. **"Network-based assessment of actual EIRP of
5G BS in a stadium with 100,000 people and implications on EMF compliance."**

The stadium result is the piece to remember:
- Location: 2023 Australian Football League Grand Final, MCG stadium
- Full capacity: 100,000+ people
- Traffic: extreme mobile traffic conditions
- Observed actual EIRP mean: **7.6% of theoretical maximum**
- Observed actual EIRP P95: **9.5% of theoretical maximum**
- Implied compliance-distance reduction: **~60% vs theoretical-max
  baseline**

This is the strongest single empirical actual-max result Ericsson has
published. It is what defenders of the actual-max approach cite when the
NGO / regulator conversation gets hot. **Colombi's team owns this number.**

## Why the stadium paper matters for AEGIS positioning

Two angles.

**Angle 1: research productivity multiplier.** The stadium campaign was
almost certainly expensive to run — network cooperation with Optus,
measurement infrastructure, statistical analysis of instantaneous EIRP over
a 24-hour window. And it's *one deployment scenario*. What does Ericsson need
next? Similar campaigns across more scenarios:
- Different traffic profiles (dense urban, suburban, indoor, industrial)
- Different frequencies (FR1 vs FR2 vs the coming FR3)
- Different codebook + beamforming configurations
- Sensitivity to BS deployment density
- Statistical robustness across many measurements

Every one of those studies today is measurement-heavy. **A fast forward
model that reliably predicts field-measured EIRP at 10-100× throughput lets
Colombi's team run 10× as many virtual scenarios per real measurement
campaign.** That's the honest AEGIS pitch to Ericsson Research: research
productivity, not "sell us your tool." Same pitch Marta responded to.

**Angle 2: the Digital Twin thread.** Which brings us to the killer piece.

## Ericsson Site Digital Twin — the natural AEGIS home

**Grangeat at Nokia said this doesn't exist.** *"He doesn't see it
generalizing into a DT etc, its more ad hoc. its just interesting."*

**Ericsson has built it.** Concrete evidence:

1. **IEEE conference paper: "Digital Twin-Based EMF Compliance Assessment of
   Base Station Sites"** — IEEE Xplore document 10999394. Bischoff is a
   co-author. Ericsson team. Published 2025.
2. **Ericsson Site Digital Twin as a shipping product**, per Ericsson.com
   November 2025 blog *"Redefining 5G Network Deployment with Ericsson Site
   Digital Twin."*
3. Product description from Ericsson.com: *"a geospatially precise,
   parametric 3D representation of each site with critical metadata
   including structural load limits, antenna orientation and height, free
   space availability, RAD center location, equipment weight, power
   requirements, and component compatibility. Stakeholders can remotely
   assess site conditions, simulate RF coverage and interference, evaluate
   free space for additional equipment, test deployment scenarios, and
   produce detailed, visual documentation for regulatory submissions."*

Regulatory submissions is EMF compliance. This is a shipping product that
already claims EMF compliance functionality.

**What AEGIS would offer inside Site Digital Twin.** A fast forward model
that turns "geospatially precise 3D site + antenna orientation + EIRP" into
"actual compliance envelope" without waiting for FDTD. Body-aware
optionally. Multi-source natively. Per-scene in milliseconds. Suitable for a
DT that has to render/replay across many sites and antenna configurations
in near real time.

**Is this a real commercial opportunity?** Genuinely might be. The Site DT
is a shipping product with revenue attached, and the EMF-compliance feature
gets used every site rollout. Speeding it up materially is a real value
proposition, unlike the "sell Nokia a compliance tool operators don't ask
for" thesis Grangeat retired.

**Caveat.** Ericsson's Site DT stack is proprietary and integrated. AEGIS
would probably enter as a licensed component or a joint pilot, not as a
standalone product Ericsson buys. Bischoff (the DT-EMF paper co-author) is
the right person to test this idea with. If he lights up, that's a real
signal. If he says "we already have that solved internally," fine, we know.

## Where Ericsson sits at TC 106 MT3 relative to Nokia

Roughly speaking:
- Nokia (Grangeat) = convenor of MT3, owns the text, curates the case study
  set for TR 62669.
- Ericsson (Colombi, Törnevik, others) = active TC 106 members, contributed
  the empirical evidence base that supports the text. Törnevik is adjunct
  professor at KTH so there's an academic foothold.

Both sit on TC 106. The relationship is co-opetition: Ericsson's data
supports the text Nokia's convenor edits. If AEGIS wins Ericsson's technical
endorsement (via Stanislav) and pilots into a Colombi study or the Site DT,
Grangeat has to reckon with that in his next TR revision cycle. The route
that Grangeat retired at Nokia opens back up.

## The Ericsson vs Nokia posture — one sentence

Nokia's EMF world is standards-political, small-team, EMF-Visual-based, and
low-spend. Ericsson's EMF world is research-empirical, publication-driven,
peer-reviewed-paper-heavy, and now integrates into a shipping Digital Twin
product. **AEGIS naturally fits Ericsson's world in a way it does not fit
Nokia's.**

## Adjacent Ericsson work worth being aware of

- **Distributed MIMO EMF evaluation** — Ericsson research paper *"EMF
  Exposure evaluation of Distributed MIMO"* — an industrial-indoor
  environment study. Another empirical thread they run.
- **Implications of EMF exposure limits on output power levels for 5G
  devices above 6 GHz** — Ericsson research paper. Handset-side thinking
  from Ericsson, though they're not primarily a handset OEM. Bridges to the
  63195-2 device-side world if the conversation drifts there.
- **RF EMF Exposure from Array Antennas in 5G Equipment** — earlier Ericsson
  positioning paper.

## What NOT to bring up unprompted

- Do not lead on the 2018 Baracca paper. It's Nokia-heavy authorship (with
  Grangeat), so bringing it up front-and-center is the wrong flex for the
  Ericsson room.
- Do not push the standards path — Grangeat gave you the actionable answer
  (5-slide vote to WG through Wout). Confirm Colombi would support it if
  the conversation drifts there. Don't relitigate.
- Do not push the "sell to your compliance team" pitch. Ericsson Research
  is not a compliance team. It's a research group. Wrong frame.

## What TO bring up

- The stadium result by name. It signals you've read their recent work.
- The Site Digital Twin thread if the conversation naturally drifts to it,
  and route it to Bischoff.
- The "research productivity multiplier" framing.
- Willingness to co-run a matched-validation figure if there's interest.
