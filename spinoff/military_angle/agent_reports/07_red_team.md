# Red team report: kill the military RF-safety pivot

Written 2026-07-09 by the red-team agent. My job was to destroy the thesis, not to grade it. I attacked
every axis in the brief, did the thermal calculation the brief flagged as the deepest technical risk,
verified the two load-bearing Gemini quotes against primary sources, and folded in the orchestrator's
two mid-task findings (AFRL RATE-EM, Epirus certification). The thesis does not survive in the form it is
pitched. It survives as a research contribution and a standards input, which is a paper and a grant line,
not a company.

## Verdict in one sentence

The military pivot as pitched is dead: the headline operational pain is misattributed to the wrong hazard
category, the flagship fielded system already cleared personnel-safety certification with the incumbent
measurement method and no body model, a cleared US competitor is three years and about 1.5M dollars ahead
on the exact fast-body-dosimetry product funded by the exact customer, and Robin's own headline physics
finding shrinks from a 57x hidden hazard to a known, published, roughly 2x standards refinement once you
run the heat equation.

## The three things that most changed my view

1. Epirus Leonidas, the flagship counter-drone high-power microwave system, already holds HERP, HERF, and
   HERO certification, performed by National Technical Systems, a physical-measurement EMC test house, with
   no body model and no exposure envelope. The single best AEGIS-shaped pull that the follow-the-money work
   identified (a certification gap for fielded non-lethal HPM) is already closed by the dumb method. Source:
   epirusinc.com "Smaller, Smarter, Safer" and nts.com HERO/HERP/HERF testing pages.

2. AFRL's Bioeffects Division already paid a US firm to build this product. "Rapid Analysis Toolkit for
   Electromagnetic Exposure Modeling" (RATE-EM), Stellar Science, Phase I FA8650-23-P-6472 (249,957 dollars,
   verified on sbir.gov/awards/206951) plus a Phase II (1,249,485 dollars, topic AF221-0015, USAF 2025,
   verified on sbir.gov/portfolio/317817). The pain is real and a program office pays for it. But the buyer
   is closed to a foreign spin-off and the incumbent is ahead.

3. I ran the heat equation on Robin's headline "sub-cm hotspot invisible to the standard" finding. The
   4 cm-squared and 6-minute averaging windows are not arbitrary blind spots. They are derived from skin
   thermal diffusion and blood-flow physics precisely so that averaged absorbed power density predicts peak
   temperature (Foster 2017, Hashimoto 2017, Funahashi 2018). Concentrating power into a 0.9 cm-squared spot
   raises peak skin temperature by only about 2x (the square root of the area ratio), not the 57x
   electromagnetic peak-to-mean. Finding C(a) is real but small and already an active standards debate.

## What I verified, what I inferred, what I could not check

Verified against primary or strong secondary sources. Epirus HERP/HERF/HERO certification and that NTS is a
physical-test house. RATE-EM Phase I and Phase II existence and amounts. That the 4 cm-squared averaging
area is thermally derived. That ICNIRP 2020 already has a short-term absorbed-energy-density limit for brief
and pulsed exposure above 6 GHz. That realistic body curvature raises absorbed power density over a flat
model, by 16.5 to 30 percent near-field and 3 to 6 percent plane wave. That flight-deck EM management is
dominated by EMCON, aircraft-avionics interference, and HERO. That NATO HFM-189 and C95.1-2345 eliminated
the peak-power pulse limit. The US defense supplier-qualification stack (AS9100, ITAR, CMMC/NIST 800-171).

Inferred by reasoning, not a single citation. That flight-deck radar standby is driven by EMCON and
interference and HERO rather than HERP, on strong convergent evidence, but I could not read the one primary
sentence. That the Leonidas certification was measurement-based, near certain because NTS is a test house but
not quoted. The looseness of the lambda-max certificate. The non-transfer of the MRI VOP regulatory
precedent. The liability bind. The roughly 2x concentration factor, from my calculation and corroborated in
direction by the averaging-area literature.

Could not check. The exact text of NAVSEA OP 3565 on flight-deck HERP, because the public PDF is a scanned or
encoded file WebFetch cannot parse and the USNI EMCON article 403s. The exact RATE-EM Phase II contract
number the orchestrator cited, with amount and topic verified but the number not. Reddit practitioner
sentiment, because the Reddit MCP returned 403 for every agent this session. See the Reddit note at the end
for what I would have asked.

---

## Ranked kill shots

Ranked by how likely each is to be fatal to the core thesis. Each has (a) the claim it kills, (b) the
evidence, (c) my confidence, (d) the one document or experiment that settles it in under a week.

### Kill 1. The headline operational pain is attributed to the wrong hazard

(a) Kills the central business case in `military_rf_hazard.md`: that HERP conservatism forces ships to put
tracking radars into standby during flight operations and thereby "degrades hemispherical air defense," and
that AEGIS shrinking the personnel keep-out zone restores that capability. This is Play B's entire prize and
the emotional core of the pitch.

(b) The claim is a Gemini paraphrase with no primary citation, and the primary evidence points the other
way. Ships restrict radars during flight quarters for three reasons, none of which is personnel RF safety.
First, EMCON: in emission control a ship turns off transmitters to avoid being detected, described in doctrine
as "turning off everything that can transmit on the electromagnetic spectrum, including air-search and
surface-search radars, and the radars, beacons, and radios of embarked aircraft." Second, interference:
high-power shipboard radar can interfere with and damage the avionics of parked and landing aircraft, and
induce voltages on rigging, booms, and parked aircraft. Third, HERO: ordnance on the deck and on aircraft is
the dominant RF-management driver, which is why HERO-unsafe ordnance must be handled in RF-free zones. The
SPY arrays sit high on the superstructure, far from the flight deck, so flight-deck crew are not even the
HERP population for those radars. The HERP population for a big array is maintenance personnel working aloft
near the aperture, a small local problem solved by local sector blanking, not a fleet-air-defense tradeoff.
The dominant flight-deck hazards in the literature are physical: jet blast at 190 km/h that blows people
overboard, and jet intakes that ingest people. RF-to-personnel is not on that list.

(c) High confidence that the pain is misattributed. Medium-high that there is essentially zero HERP-driven
air-defense cost, held back only because I could not read the one primary sentence in OP 3565.

(d) One week: get any current or former NAVSEA E3, NOSSA, or shipboard combat-systems officer to answer a
single question, "when you secure or blank the air-search or tracking radar during flight quarters, is it
ever to protect flight-deck crew from RF, or is it always EMCON, interference, or ordnance?" Or read NAVSEA
OP 3565 Vol 1 chapters on flight-deck operations and confirm the standby triggers. If the answer is EMCON,
interference, and HERO, Play B has no pain to sell against and the report should say so.

### Kill 2. The certification gap for fielded HPM is already closed by the incumbent method

(a) Kills Finding A and Finding B repackaged as a product: the idea that safety boards need, and would buy,
a software-computed "certifiable exposure envelope" to authorize a fielded non-lethal HPM system to operate
near people. This was flagged elsewhere in the study as the strongest AEGIS-shaped pull.

(b) Epirus Leonidas, the leading counter-drone HPM system now deployed to CENTCOM, holds HERP, HERF, and
HERO certification. The certifier was National Technical Systems, whose business is physical EMC and RADHAZ
measurement in anechoic and reverberation chambers and on ranges, the exact incumbent method the thesis
calls inadequate. No body model, no exposure operator, no AEGIS. The certification cleared the flagship
system for operation near people, fuel, and ordnance. Separately, Epirus's own operational safety story is
"software-controlled safe zones," which is the on/off nulling and sector-blanking that Gemini described as
the primitive incumbent, and it is vertically integrated into their fire-control and combat-management
software. The array vendor owns the beam and the safe-zone logic. There is no slot in that loop for a
third-party body-dosimetry tool.

(c) High confidence that the certification exists and was measurement-based. High confidence that this
removes the "certification instrument" product pull in both the US and, by analogy, the EU market, where
the same test-house route exists.

(d) One week: read the Epirus certification announcement in full and, if reachable, ask NTS or Epirus
whether the HERP certification used measured field surveys and static keep-out or any human-body model. If
it was measurement plus keep-out, the certifiable-envelope product is solving a solved problem.

### Kill 3. A cleared US competitor is years ahead on the exact product, funded by the exact customer

(a) Kills the first-mover and differentiation claim: that AEGIS is uniquely positioned because it is the
only fast, body-aware EM dosimetry engine and nobody else is building one for defense.

(b) RATE-EM (Stellar Science, Albuquerque) is a fast surrogate for AFRL's high-fidelity EM bioeffects
physics, explicitly built to "vastly reduce computational costs, make bioeffects predictions accessible to
non-experts, and account for uncertainty," using their VIPERS surrogate-builder and Galaxy optimizer running
on DoD Supercomputing Resource Centers. Phase I and Phase II are both funded, about 1.5M dollars total,
completion around 2027. The orchestrator's hope is that an ML surrogate can never be a safety certificate
because it lacks a provable one-sided error bound, whereas the lambda-max envelope has one. I attacked that
and it is weaker than hoped. AEGIS's lambda-max is a provable bound on AEGIS's own first-bounce
physical-optics model, which is itself 3 to 10 percent off FDTD and structurally omits the edge, creeping,
and multi-bounce physics that dominate exactly the near-field and standing-wave enhancement cases. It is a
bound on a model, not on reality. Stellar Science is explicitly tasked to "account for uncertainty" and can
bolt conformal-prediction coverage bounds onto their surrogate to produce a defensible probabilistic
envelope. The genuine AEGIS advantage is narrower than "certificate versus not": it is the closed-form
supremum over the continuous beam space via one eigendecomposition, which matters only for agile,
reconfigurable arrays, which is also the case safety boards most resist certifying.

(c) Medium-high. The competitor and funding are verified. The "AEGIS is not meaningfully differentiated"
conclusion is reasoned, not proven, and depends on whether RATE-EM outputs per-element field channels
(it probably does not) versus scenario-level scalars.

(d) One week: read the RATE-EM Phase II abstract and any Stellar Science publication or conference talk to
learn whether the surrogate produces the complex per-element field channel (which would let them build Q and
take the eigen-trick) or only scalar SAR/APD per scenario. If the former, AEGIS's coherent-operator moat is
gone. If the latter, AEGIS has a narrow real edge for agile arrays only.

### Kill 4. "Nobody models the body" is true only in the narrow operational-topside niche

(a) Narrows, not kills, the load-bearing "99 percent of topside projects do not model the body" claim, which
is stated as the entire opportunity.

(b) The directional claim is defensible for the operational topside CEM workflow: FEKO, HFSS SBR+, and the
Navy's AESOP compute unperturbed fields and paint keep-out zones, and CST can drop in a Duke phantom but it
is not fast, not differentiable, and not how the operational job is run. But the adjacent space is not empty.
AFRL's Bioeffects Division and the US Army Public Health Center have modeled the human body with FDTD codes
and anatomical phantoms for decades, and AFRL is now funding the fast surrogate version (Kill 3). NATO
already did the pulsed-limits bioeffects science (HFM-189). So the honest claim is "nobody models the body
inside the operational topside workflow," which is a workflow-integration gap, not a capability gap. A
workflow-integration gap is a much weaker thing to build a company on, because the capability already exists
at the labs and the integration is services work owned by the primes and test houses.

(c) High confidence that the narrow claim is the only true one.

(d) One week: find one shipboard or platform RADHAZ survey report (DTIC, a NAVSEA technical report, or a
prime's E3 white paper) and check whether any human-body model appears in the personnel-exposure
determination, or whether it is always probe measurement plus free-space keep-out. I expect the latter.

### Kill 5. Finding C(a) collapses from a 57x hidden hazard to a roughly 2x known standards debate

(a) Kills the "fundable problem statement" framing: that an agile coherent array can be compliant on paper
and dangerously non-compliant in reality because a wavelength-sized hotspot is invisible to three averaging
operations in the standard.

(b) I did the calculation the brief asked for. Skin thermal diffusivity 1.2e-7 m-squared per second. Over
the 6-minute averaging window heat diffuses about 13 mm laterally, larger than the 5.35 mm radius of the
0.9 cm-squared hotspot, so the temperature field smears to a roughly 32 mm scale, larger than the 4
cm-squared window. The averaging windows are not blind spots, they are the thermal averaging scales of skin,
derived on purpose: Foster 2017 put the blood-flow smoothing distance at about 7 mm (a 14 mm circle),
Hashimoto 2017 derived 4 cm-squared from FDTD, and Funahashi 2018 showed 4 cm-squared-averaged absorbed
power density correlates strongly with peak skin-temperature rise from 10 to 300 GHz. The residual danger of
concentrating power into a sub-window spot is bounded by the square root of the area ratio, not the
electromagnetic peak-to-mean. At fixed 4 cm-squared-averaged absorbed power density, moving the same power
into 0.9 cm-squared raises peak steady-state temperature by 2.11x, into 0.2 cm-squared by 4.5x, into 0.1
cm-squared by 6.3x. It never reaches the 57x electromagnetic peak-to-mean, because heat does not respect the
electromagnetic pattern. A single millisecond radar dwell deposits a negligible 0.001 to 0.007 K, so
sustained heating needs many revisits over minutes, which reverts to the near-steady-state 6-minute case.
And the temporal leg of the argument is already handled: ICNIRP 2020 has a short-term absorbed-energy-density
restriction above 6 GHz, duration-dependent, applicable to CW and pulsed, precisely for scanning and pulsed
beams. So two of the three "averaging blindnesses" are deliberate physics and the third leg (unperturbed
field, no coherent buildup) only produces the dramatic numbers when an array deliberately focuses on the
body, which is the offensive scenario the ethics boundary excludes. For the defensive safety case, crew sit
in incoherent sidelobes where buildup is the Rayleigh-speckle factor of about 4, not 57.

(c) High confidence. This is my own calculation plus three corroborating standards-literature results. The
roughly 2x residual is real and worth a standards refinement, but it is not a hidden catastrophe and it is
already being debated (Neufeld and Kuster, Hashimoto) as the question of whether 4 cm-squared should shrink
at higher mmWave.

(d) One week: nothing to run, the calculation is done. To turn it into a publishable claim rather than a
kill, compute the coupled EM-plus-Pennes-bioheat peak temperature for a real ECBF hotspot at the
occupational limit and show the exact under-estimate factor of the 4 cm-squared metric. That is a paper for
Wout's community, not a product.

### Kill 6. Modeling the body does not reliably shrink the zone, and sometimes enlarges it

(a) Kills the Play A demo promise: that replacing the empty-space threshold with real-body absorbed power
density yields a meaningfully smaller keep-out zone, "and if the zone shrinks meaningfully, that single
figure is the entire pitch."

(b) The assumption that the body shadows and absorbs so the zone must shrink is not robust. A realistic
curved, stratified body raises absorbed power density above a flat model by 16.5 percent (Duke) to 30
percent (Ella) for near-field sources at 28 GHz, and by 3 to 6 percent for plane waves, and the paper states
plainly that ignoring the body is non-conservative, meaning unsafe, in those cases. Standing waves against
scattering structure create local enhancement, documented for the cornea against the eyelid and directly
applicable to a body against a conducting deck or bulkhead, where incident plus reflected fields can reach
4x the single-wave power density at an antinode. The far-field open-deck case (crew in sidelobes) probably
still shrinks, because the skin transmission coefficient of 0.4 to 0.6 means less than half the incident
power is absorbed, and that beats the 3 to 6 percent curvature penalty. But the reference levels the
incumbent already uses above 6 GHz bake in much of that transmission conservatism, so the recoverable
headroom is modest, maybe a 20 to 40 percent zone-radius reduction in the clean case, and it can go negative
in enhancement geometries. A tool whose honest output is sometimes "your zone must grow" is commercially
awkward, and the single-figure pitch is not guaranteed to land.

(c) Medium-high. The enhancement effects are verified. The net direction is scenario-dependent, which is the
point: the pitch oversimplifies a two-signed effect.

(d) One week: this is exactly the Play A demo, but run it honestly across geometries. One X-band deck scene,
zone computed the industry way versus the AEGIS way, at normal incidence, at grazing incidence, and with the
body against a conducting bulkhead. If the honest zone shrinks in the open case but grows against the
bulkhead, you have learned the product cannot promise "smaller zones."

### Kill 7. Finding A's lambda-max certificate is either loose or needs classified inputs

(a) Kills the "static, deterministic, provably-valid-for-any-beam keep-out certificate" as a clean product.

(b) The supremum of x-Hermitian-Q-x over all unit-norm x is achieved by the top eigenvector of Q, which is
the beam that points the entire array's coherent energy at the crew position. No radar tracking a target
forms that beam, and under per-element power limits it may not even be feasible, so as a keep-out bound it is
adversarially loose: it certifies against a beam nobody uses and the array often cannot make. The useful
object is the constrained supremum over the actual beam repertoire, which requires the waveform tables and
scan-sector limits, which are classified Secret or NOFORN. So the elegant closed form is either uselessly
loose or requires exactly the classified inputs the thesis admits it cannot get. And the bound is on AEGIS's
own physical-optics model, not on true absorbed power, so it is not the rigorous one-sided safety guarantee
the word "certificate" implies.

(c) Medium-high, reasoned. Someone should actually compute the constrained-versus-unconstrained gap on a
realistic array to size the looseness.

(d) One week: take a representative planar array with per-element power caps and a plausible scan sector,
compute lambda-max over the unit sphere versus the supremum over the constrained excitation polytope, and
compare both to today's unperturbed-field zone. If unconstrained lambda-max is much larger than the
constrained sup, the closed form is not usable without classified data.

### Kill 8. The MRI VOP regulatory precedent does not transfer to a ship deck

(a) Kills Finding B's "gift": that the FDA's acceptance of VOP-based online SAR supervision in 7T pTx MRI is
a live regulator-blessed precedent for AEGIS's envelope.

(b) The FDA accepted VOPs because the MRI geometry is fixed and known: a motionless patient in a known
position inside a known static coil, the operator matrices computed offline once, the transmit chain owned
and controlled by the hospital, the excitation space bounded and characterized. A ship deck violates every
precondition. Crew move, positions are unknown and time-varying, the effective "coil" is a radar array plus
ship superstructure plus sea-surface multipath that is neither fixed nor fully known, the environment is
outdoor, and the excitation space is a classified weapon's waveform set. The Q matrix would need continuous
recomputation from inputs nobody has. The math transfers, the acceptance does not, because the thing that
made VOPs acceptable to a regulator is precisely the controlled static geometry a ship lacks. Worse, on a
ship AEGIS would be supervising a weapon's real-time beam scheduler, the dynamic sensor-driven loop that
NOSSA and the LSRB structurally refuse to certify. The MRI analogy shows why the ship case is harder, not
easier. As prior art, the VOP paper also exposes the patent's "closed-form exposure operator" claim, which
the brief already concedes.

(c) Medium-high, reasoned from the physics of what makes VOPs certifiable.

(d) One week: read the FDA guidance and one pTx VOP clinical-approval document and list the controlled-
geometry preconditions, then check each against a ship deck. Every one fails.

### Kill 9. The liability model is a bind that a two-person spin-off cannot hold

(a) Kills the safety-vendor business model on risk-transfer grounds.

(b) AEGIS's value proposition is to let sailors stand closer to a live radar by reducing a safety margin. If
a sailor is later injured, the vendor faces product-liability and negligence exposure. Professional indemnity
insurance covers professional-service errors but explicitly excludes bodily injury, which routes to general
liability, and military-injury litigation sums are large. No safety authority transfers liability to a
software vendor, and the mature incumbent, ZMT with Sim4Life, coordinates directly with regulators and pins
the exact validated SAR evaluator for regulatory use, a bar a spin-off cannot clear quickly. The bind is
structural: the more AEGIS's output is load-bearing for the safety decision, the more liability it carries,
and the more it is positioned as a mere analysis aid to dodge liability, the less the "certifiable envelope"
value proposition is worth. You cannot be both the certificate and not liable.

(c) Medium. The insurance mechanics are verified, the "no authority accepts transfer" is standard practice,
the strategic bind is reasoned.

(d) One week: ask one defense-focused insurance broker whether a two-person firm can get product-liability
cover for software that authorizes reduced RF keep-out near personnel, and at what premium and exclusions.
If the answer is uninsurable or prohibitively excluded, the model needs an integrator to absorb the risk,
which cedes the value.

### Kill 10. The buyer is closed and the pivot's own constraints compound

(a) Reinforces every kill above with go-to-market reality.

(b) The US defense supply chain requires AS9100, ITAR registration, a CAGE code, and CMMC Level 2 with
third-party NIST 800-171 assessment mandatory from November 2026, none of which a two-person Belgian
academic entity can obtain except by licensing to a cleared US firm, which cedes most of the value and
control. HERP is a small budget line next to HERO by the thesis's own admission. Software is only 300 to 400
million dollars of a 1.5 to 2 billion dollar market, most of which is physical test and services, the NTS
kind of work. The product name collides with the US Navy's flagship combat system. And the dual-use tension
is real: making a high-power microwave system legally operable closer to humans also raises its permitted
duty cycle, which conflicts with an EU university spin-off's IOF, VLAIO, and Horizon funding path. The one
genuine technical differentiator the memo names, pulsed and fluence physics, is partly deflated because NATO
HFM-189 and C95.1-2345 eliminated the peak-power pulse limit as having no bioeffect basis, so pulsed work is
closer to table stakes than to a moat.

(c) High confidence on the structural barriers, which are mostly documented facts.

(d) One week: confirm with UGent TechTransfer whether the entity can even register for ITAR or a US CAGE
code as a foreign SME, and confirm the current EDF SME call codes directly rather than trusting the Gemini
identifiers. If the only US route is license-to-a-cleared-firm, price what that arrangement leaves for Robin.

---

## What I would have asked Reddit

The Reddit MCP returned 403 for every agent this session, so practitioner voice is missing from the whole
study. Route these elsewhere (a veteran contact, a defense-EMC LinkedIn group, or a NAVSEA alum):

- r/navy or r/newtothenavy: "When you actually secure or blank the air-search or SPY radar during flight
  quarters, what is the real reason: EMCON, interference with the aircraft, ordnance on deck, or protecting
  flight-deck crew from RF?" I expect the answer removes the HERP air-defense story (Kill 1).
- r/rfelectronics: "In a real shipboard or topside RADHAZ survey, has anyone ever seen a human-body model
  used, or is it always a probe field survey plus a free-space keep-out line?" I expect always measurement
  (Kill 4).
- r/rfelectronics or a defense-EMC group: "Would a safety board ever accept a software-computed exposure
  envelope in place of a measured field survey for personnel certification?" I expect no, measurement signs
  the paperwork (Kills 2 and 8).
- Anyone near the C-UAS HPM world: "How did Epirus get Leonidas HERP-certified, and does the certification
  limit how close it can run to people?" (Kill 2).

## Does it survive, and in what narrowed form

It does not survive as a spin-off product line worth two prime years. The three Tier-1 kills each remove a
load-bearing leg independently: the pain is misattributed (Kill 1), the certification gap is already closed
by the incumbent method (Kill 2), and a cleared competitor is ahead on the funded customer (Kill 3). Robin's
own headline physics finding deflates to a known 2x standards refinement (Kill 5), and the tool cannot even
promise the smaller zones the pitch is built on (Kill 6).

What genuinely survives is smaller and honest, and it is worth saying because it did survive the attack:

1. A research and standards contribution. The body-aware, coherent, mmWave exposure correction (the roughly
   2x sub-averaging-area concentration, the 3 to 30 percent curvature enhancement, the deck standing-wave
   case) is real, publishable, and directly feeds Wout's ICNIRP and IEEE committee work. It costs nothing to
   disseminate through his seats. But note it argues that some zones should be a little larger, which is a
   scientific win and a commercial anti-sell. It is a paper, not a company.

2. A possible grant-funded work package, not a business. If an EU prime (Thales, Damen, Naval Group) genuinely
   needs a body-aware topside dosimetry component under an EDF or EDA project and cannot get it fast enough
   from CST, AEGIS could be that component, funded as research. This is non-dilutive money and a credibility
   line, not a scalable product, and it competes with CST-plus-Duke and with the fact that the incumbent test
   houses already certify these systems by measurement.

The narrowed form is therefore: treat the military angle as a source of one good standards paper and, at
most, one grant-funded research collaboration that strengthens the patent and the resume, and do not build
the company on it. The civilian wedges the feasibility synthesis already graded PURSUE (RIS constrained
synthesis, in-cabin radar, the ZMT medical relationship) do not have the closed-buyer, classified-input,
misattributed-pain, incumbent-ahead, and liability problems that this one has on every axis I attacked.

## The single highest-value next action

Spend one day, not one month, killing or confirming Kill 1, because it is the cheapest and most decisive. Get
one credentialed naval answer to the single question "is flight-deck radar standby ever driven by personnel
RF safety, or always by EMCON, interference, and ordnance." The Royal Military Academy in Brussels or a
Thales Nederland systems engineer can answer it in one email. If the answer is what the doctrine implies, the
operational-tempo story is dead, the moonshot Play B has no pain to sell, and the whole pivot reduces to the
research-and-standards contribution above, which needs no spin-off to pursue. Robin, or Wout through his
defense and standards contacts, would have to make that call.
