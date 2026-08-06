# Wildcard report: the moves nobody in this study has made

Agent 11, 2026-07-09. Brief read, adversarial as instructed. This is not a list. It leads with one
idea, because that idea is worth more than the other five combined.

## Verdict in one sentence

Robin should stop trying to enter defense and instead spend the next three months turning his headline
physics claim into a photograph, because a single thermal image of a beamformer painting a sub-centimetre
hotspot on a phantom, next to the flat map the standard predicts, is the one asset that makes the paper,
the patent, the IOF, the press, and every downstream conversation (defense included) real, it has never
been taken, the hardware to take it sits one hour away in Leuven, and the method is thirty years old.

## The three things that most changed my view

1. **The experiment is cheap, standard, and un-done, and the hardware is Belgian.** Infrared thermography
   of millimetre-wave heating in tissue phantoms is a routine, published dosimetry method with 0.02 K
   sensitivity ([Springer, IR thermography in RF/mmW dosimetry](https://link.springer.com/chapter/10.1007/978-94-011-4191-8_22)),
   and NICT Japan runs it as standard practice on 28 GHz phantoms ([Sasaki et al., NICT mmW dosimetry](https://rri.nict.go.jp/en/people/emc_sasaki.html)).
   But every published 28 GHz phantom exposure experiment I can find uses a **single horn or lens antenna**,
   or characterises the aggregate power density of a phone's array ([arXiv 2009.06318, 28 GHz array on body phantom](https://arxiv.org/pdf/2009.06318)).
   **Nobody has published a coherent multi-element beamformer steering a diffraction-limited hotspot onto a
   phantom and imaging it.** KU Leuven's WaveCoRE group has the exact hardware: a 28 GHz reconfigurable
   tile-based phased array (FORMAT) and a real-time massive-MIMO testbed, run by Sofie Pollin and Dominique
   Schreurs, one hour from Ghent, both `@kuleuven.be`, both academics who take collaboration emails
   ([FORMAT, IEEE Systems J. 2022](https://www.esat.kuleuven.be/telemic/People-of-telemic/00009846)). Lund's
   LuMaMi28 is a 28 GHz digital-beamforming testbed as a fallback ([arXiv 2109.03273](https://arxiv.org/abs/2109.03273)).
   And Robin's own group already does the simulation half: WAVES published a hybrid ray-tracing/FDTD 28 GHz
   exposure method for 6G cell-free massive MIMO this year ([npj Wireless Technology 2026](https://www.nature.com/articles/s44459-026-00031-4)).
   The pieces are all within reach. Nobody has assembled them.

2. **Epirus is publicly making a safety claim it cannot currently prove, and it is a startup that answers
   email.** Epirus markets that operators of Leonidas "can set safe zones" and that "software-controlled safe
   zones make Leonidas safe for people and friendly assets" ([Epirus electronic-warfare page](https://www.epirusinc.com/electronic-warfare)).
   A "safe zone" is a keep-out volume with no human body in it, computed the exact way the shipboard industry
   computes it, unperturbed and body-blind. AEGIS's certifiable envelope (Finding A in the brief) is precisely
   the artifact that would let Epirus prove a safe zone bounds absorbed power on an actual bystander body for
   any beam the array can form. This is a defensive deliverable that maps onto their own marketing language,
   and unlike a prime, a venture-funded startup will take the meeting.

3. **"Change the standard, then be the only one with the tool" is a real business but a fifteen-year one, so
   it cannot be the plan.** ICNIRP took 1998 to 2020 to revise (22 years). IEEE C95.1 took 2005 to 2019
   (14 years) ([ICNIRP differences page](https://www.icnirp.org/en/differences.html)). The 6 GHz absorbed-power-density
   transition that everyone cites as the precedent was that once-in-a-generation event. Waiting for the next
   basic-restriction revision to mandate a coherent-hotspot metric is not a startup timeline. The faster,
   real version of the standards play is the **measurement-methodology** layer (IEC 63195 and its technical
   reports), which revises on a shorter cycle and is exactly where Wout has influence, but even that is a
   dissemination and credibility channel, not a revenue engine. Treat the standards seat as free marketing,
   not as the moat.

## What I verified, inferred, and could not check

**Verified (primary or strong secondary):**
- IR thermography is an established mmW phantom dosimetry method, 0.02 K sensitivity, and NICT uses it at 28 GHz.
- Published 28 GHz phantom exposure experiments use single horns/lenses or aggregate device power density, not steered coherent hotspots.
- KU Leuven WaveCoRE owns a 28 GHz reconfigurable tile array (FORMAT) and a massive-MIMO testbed; Pollin and Schreurs lead it; emails are `firstname.lastname@kuleuven.be`.
- Lund LuMaMi28 is a 28 GHz real-time digital-beamforming testbed.
- Robin's own WAVES group publishes 28 GHz CF-massive-MIMO exposure simulation.
- Epirus markets "software-defined safe zones" and "safe for people" for Leonidas.
- ICNIRP revision interval 1998 to 2020; IEEE C95.1 2005 to 2019; both adopted a common 6 GHz transition to absorbed power density.
- "Aegis" is crowded in safety software beyond Lockheed: "OneAegis" is a live radiation-safety compliance SaaS ([Tech Software OneAegis](https://www.techsoftware.com/solutions/oneaegis-for-radiation-safety/)).

**Inferred (reasoned, not confirmed):**
- WAVES/UGent likely already owns a research thermal camera and mmW tissue phantoms for its dosimetry work, which would drop the experiment's marginal cost close to zero. Not confirmed.
- The experiment needs near-field beam focusing (not far-field comms beamforming) and enough radiated power to raise a visible thermal signature, which is fine on a phantom that can be driven far past human limits. This is a genuine design constraint the partner lab knows how to handle, not a blocker.
- The IEMI / intentional-electromagnetic-interference research community exists and is funded, but it is about disrupting **electronics**, not heating **people**. The human-exposure adversarial angle is genuinely novel, which also means it is not yet a funded line anywhere.

**Could not check:**
- Reddit practitioner sentiment. The Reddit MCP returned HTTP 403 on every call this session (same blocker agent 04 hit). `NEEDS_CONTEXT` if practitioner voice on this is wanted.
- Actual current prices for a research-grade LWIR camera and mmW phantom. Numbers below are labelled estimates.
- Whether KU Leuven's array can focus in the near field at a stand-off that produces a clean sub-cm spot at its element count. This is the first question to ask Pollin, not something I can settle from a desk.

---

## 1. The experiment nobody has done (the highest-value action in the whole study)

Robin's headline claim, from `exposure_datamining/FINDINGS.md`: a coherent array paints a steerable,
diffraction-limited, ~0.9 cm² (about one wavelength at 28 GHz) absorbed-power hotspot on a body, and three
independent averaging operations in the standard (4 cm² spatial window, 6 minute time window, no-body
unperturbed-field assumption) are blind to it. That claim currently exists only as JAX output. **The single
most valuable thing anyone on this study could produce is the same claim as a photograph.**

**The shot.** Two panels. Left: an infrared image of a phantom surface with a bright sub-centimetre spot
where a phased array is focusing. Right: the flat, spread-out map that the 4 cm² averaged standard metric
predicts for the same illumination. The gap between the two panels is the entire thesis, in one frame, that
a non-specialist minister, program officer, VC, or journalist understands in two seconds. It is the pitch
for the TWC paper (measured validation of the coherent operator), the patent (a demonstrated embodiment,
not just a simulation), the IOF (de-risking evidence), the press ("5G-style arrays can paint a hotspot the
safety rules cannot see"), and, yes, any future defense conversation.

**Why it is credible that it has not been done.** The dosimetry community that owns mmW phantom thermography
(NICT, and Wout's own world) studies **single fixed sources**, because that is what a phone or a base-station
sector looks like from a compliance standpoint. The massive-MIMO community that owns the arrays (Leuven, Lund)
studies **throughput**, and points beams at receivers, not at phantoms with a thermal camera watching. The
two communities do not co-run this experiment because neither has a reason to inside its own paradigm.
Robin's operator is the reason. That is a real white space, not a gap I am manufacturing.

**Feasibility and cost (estimates, labelled).**
- Array: already owned by the partner lab. Marginal cost zero.
- Thermal camera: a research-grade LWIR camera with sub-0.05 K sensitivity is order 20k to 60k EUR to buy,
  rentable for far less, and plausibly already in the WAVES lab. Estimate.
- Phantom: mmW tissue-equivalent liquid or solid phantoms use published recipes and are sold by Speag/IT'IS;
  order a few hundred to a few thousand EUR. Estimate.
- Time: weeks, not months, once a lab agrees.
So the honest cost envelope is "a thermal camera, a phantom, and a few weeks of a friendly lab's array,"
which is either sub-50k EUR or effectively free inside a collaboration. This is the cheapest high-value
action in the entire spin-off, defense or civilian.

**Two design honesties, because a reviewer will raise them.**
- The array must **focus in the near field** (beam-focusing to a range, not far-field beam-steering to an
  angle). A 16 to 64 element array at 28 GHz has a limited focal range; the spot is only diffraction-limited
  within it. First question for Pollin: can FORMAT focus at, say, 0.3 to 1 m and hold a clean spot.
- At the legally safe total power in the datamining grid (0.316 W), nothing heats measurably, so a human
  forearm would show **nothing** on the camera. That is fine and actually on-message: run the **phantom**
  well above human limits to make the spot thermally visible, then state plainly that the physics is
  homogeneous in power so the shape of the hotspot is identical at safe power, it is just invisible to a
  camera and, more importantly, invisible to the standard. Do not attempt this on a live human to get a
  visible hotspot; the visible-heat version belongs on a phantom only. (This keeps you inside section 4 of
  the brief without argument.)

**The move.** One email from Wout to Sofie Pollin proposing a joint measurement paper: WAVES brings the
operator and the dosimetry framing, WaveCoRE brings the array, shared authorship, shared press. This is a
phone-call-length action between two Belgian professors who already move in the same 6G-exposure circles.
It does not need defense, clearance, funding, or a company. It needs one email and a camera.

## 2. The adversarial framing: real, novel, but not yet fundable, and here is the line

The question "could a hostile actor use a commercial massive-MIMO base station or a repurposed radar to
place a hotspot on a person, and would anyone be able to tell" is a legitimate **threat-assessment** question,
and AEGIS's operator answers it: `lambda_max(Q)` is the worst a given deployed array could do to a body in
its scene, and `||G_t||^2` is the worst-case local build-up on a chosen skin patch. The defensive deliverable
is "here is the bound, and here is why the current compliance regime would not detect an array operating
inside it." That is on the right side of the line: characterise and detect, never target or optimise harm.

**The honest downgrade.** There is a funded community for **intentional electromagnetic interference** (IEMI)
against critical infrastructure ([IEEE, IEMI and critical infrastructure](https://ieeexplore.ieee.org/document/8738487)),
but its object is frying **electronics**, not heating **people**. The physical-layer-security community
optimises beams to deny an eavesdropper information, not to bound exposure. So the adversarial-exposure angle
is genuinely novel, which is exactly why **no agency currently funds it**. A national cyber or infrastructure
agency would need the threat to be legible first, and today it is not. This is a paper and a talk (the kind
of thing that gets Robin invited to an ICES or an EMC-Europe session), not a 2026 grant line. Pursue it as
credibility and narrative, not as revenue. And the moment the framing tips from "here is a vulnerability and
a detector" toward "here is how effective it would be," stop. The detector is defensible; the effectiveness
curve is weapons work and would end the university funding path (brief section 4).

## 3. The standards play, judged as a business

Cynical and legitimate at once, and the timing decides which. If the averaging-window-blindness finding
holds (another agent is testing it), the fastest mandate route is to change the standard and then be the only
one with a tool that computes the new quantity. That is genuinely how compliance businesses are built. But
the basic-restriction revision clock is 14 to 22 years, and the last turn (the 6 GHz APD transition) is the
precedent everyone points to precisely because it is rare. Betting the company on catching the next one is not
a plan.

The legitimate fast version: Wout's seat is a **dissemination and agenda-setting** channel, not a mandate
machine. A well-argued finding that agile arrays can be paper-compliant and physically non-compliant, put in
front of an IEC 63195 or IEEE ICES working group, does two things on a startup timeline: it makes AEGIS the
reference implementation of the concern (whoever names the problem owns the tool that measures it), and it
seeds the measurement-methodology documents that revise faster than the basic restrictions. Who opposes it:
operators and device makers, because a new binding metric is a new way to fail certification, and the whole
industry's mmW compliance rests on the averaging that this finding attacks. That opposition is also the proof
the finding matters. Play it as: publish the finding, present it through Wout, become the named tool, and
monetise pre-compliance **now** against the standard as it already is, not against a hypothetical future one.

## 4. Unreasonable partnerships, named, with the trade for each

- **Epirus (El Segundo, CA).** They market "software-defined safe zones" and "safe for people" and have not,
  publicly, proven either with a body in the scene. Robin gives them a way to substantiate a safety claim
  they are already making in press releases. They are venture-funded and will answer an email, unlike a prime.
  Caveat: Leonidas is L-band (~1 GHz), so the millisecond surface speed does not apply, only the planner and
  the certifiable envelope. The pitch is the envelope, not the speed. This is the single most reachable
  defense-adjacent partner in the whole study.
- **KU Leuven WaveCoRE (Pollin, Schreurs).** The array for the experiment in section 1. Robin gives them a
  novel exposure-physics angle on hardware they already own, and a co-authored paper in a venue their comms
  work does not usually reach. Nearest, warmest, most important partnership.
- **IT'IS Foundation / Speag (Zurich).** They own the Virtual Population phantoms AEGIS already ships and sell
  the physical phantoms the experiment needs. Robin is already in their orbit through the ZMT relationship
  (per project memory). They are the natural supplier and validator, and a co-branded phantom-plus-operator
  validation is a credibility multiplier.
- **NICT (Japan) bio-EM group (Sasaki, Kojima).** World reference for mmW phantom thermometry. If Leuven
  cannot focus in the near field, NICT has the measurement rigor. Robin gives them the array/operator idea
  they lack. Slower (Japan, and Hirata is already a warm contact per memory), but the highest-authority
  validation available.
- **A thermal-camera maker (Teledyne FLIR, or InfraTec in Germany).** They want application stories that sell
  cameras. A striking mmW-hotspot image shot on their camera is co-marketing for both sides, and possibly a
  loaned camera. Lowest-stakes, fastest yes.
- **Royal Military Academy (RMA/KMS) Brussels.** The Belgian academic-defense bridge the brief already names.
  Not for the experiment, but as the credential-holder if the defense narrative is ever pursued.

Note the pattern: five of the six are civilian or dual-use and reachable this month; the one prime-adjacent
option (Epirus) is reachable only because it is a startup. That is the honest shape of Robin's actual network.

## 5. The name

"Aegis" is a bad product name here on three independent counts, not one. It is Lockheed Martin's flagship naval
combat system ([Lockheed Aegis](https://www.lockheedmartin.com/en-us/products/aegis-combat-system.html)), so
it is a distraction bordering on a trademark problem in the exact naval-RF vertical this study contemplates.
It is also already taken in **safety-compliance software**: "OneAegis" is a live radiation-safety compliance
SaaS ([OneAegis](https://www.techsoftware.com/solutions/oneaegis-for-radiation-safety/)), which is close enough
to Robin's civilian market to matter. And it is generic: "aegis/shield/guardian" is the most crowded metaphor
in the entire safety-software namespace.

I am not going to invent that a name is available; a real EUIPO search in classes 9 (software) and 42 (SaaS,
scientific services) plus a `.com`/`.eu`/`.ai` domain check is a one-hour paralegal task Robin should
commission before committing. But the naming **direction** is clear and worth stating: get off the
shield/guardian metaphor entirely, because it fights for attention with a thousand security products and one
warship. Name the **physics**, not the promise. The defensible, ownable story is the operator and the
hotspot, so a coined, phonetically clean word rooted in "absorbed power on a surface" or "the quadratic
exposure operator" will clear trademark far more easily than any dictionary word and will not collide with a
Lockheed product. Concretely: brief a namer with "differentiable coherent exposure operator, sub-cm hotspot,
skin-surface absorbed power" and pick from coined candidates, then clear the top three. Do not ship "Aegis"
into any RF-safety market, civilian or defense. This is small, real, and nobody in the study had done it.

## 6. What Robin is not seeing

The uncomfortable thing, said plainly, because that is my job.

The military pivot is a smart person's way of avoiding the boring win. Robin has spent months on generalisation
studies that keep grading everything CONDITIONAL, and the honest reading of that is not "keep hunting for a
better domain," it is "the verified, mandated, un-sexy thing was already on the table and I keep walking past
it." His own IOF analysis calls **mmWave device pre-compliance against IEC 63195-2 the biggest wedge and the
one the internal docs underweight.** That domain has everything the military domain lacks: an existing legal
mandate (you cannot sell a mmW device in the EU without demonstrating compliance), a reachable buyer with a
budget (every phone, laptop, CPE, and access-point maker shipping above 6 GHz), no classified inputs, no
clearance, no name conflict, and a regulator who **already accepts computed absorbed power density** as the
basic restriction. AEGIS computes exactly that quantity, natively, in milliseconds, which is the one thing the
FDTD incumbents (Sim4Life) are slow at.

The military angle is more exciting and it is CONDITIONAL for structural reasons that are not going away:
personnel safety is the poor cousin of ordnance safety, the safety boards prefer the method that cannot crash,
and the inputs are classified. None of that yields to better physics. The mmW pre-compliance wedge is less
exciting and it is the actual business.

Here is the reframe that dissolves the tension, and it is the real strategic point: **the experiment in
section 1 serves both, and the boring one first.** A measured coherent-hotspot-versus-standard image is the
keystone validation for the civilian mmW pre-compliance product (it proves AEGIS sees what the incumbent
compliance workflow misses) **and** it is the artifact that makes any future defense conversation credible.
So Robin does not have to choose between the exciting pivot and the boring wedge. He has to take the one photo
that de-risks both, lead commercially with the mandated civilian wedge that pays, and keep the defense
narrative as optionality that the same photo unlocks later. Chasing defense first inverts that: it spends the
scarce months on the domain with the worst structural odds, using an asset (the operator) whose value is
proven by an experiment he could run without any of the defense apparatus at all.

He is close enough to the military idea to feel its pull and too close to see that the thing that would sell it
is the same thing that would sell the boring product, and the boring product is the one with a mandate and a
buyer. Take the photo. Sell the pre-compliance. Let defense follow the photo, not lead it.

## What would kill the lead idea (falsifiable, one week)

Ask Sofie Pollin one question: can the FORMAT array (or the Leuven massive-MIMO testbed) focus in the near
field at a stand-off of roughly 0.3 to 1 m and hold a spot on the order of a wavelength, at a power that
raises a phantom's surface temperature by more than the camera's noise floor. If the answer is no, that the
element count or aperture cannot produce a clean sub-cm focus at a usable range, then the "diffraction-limited
steerable hotspot" is a simulation artifact that no accessible European array can physically demonstrate, and
the whole headline claim degrades from "measured" back to "computed," which is where it started. That single
email, answerable in a week, is the test. Everything in section 1 rides on it.

## Single highest-value next action, and who

Wout Joseph emails Sofie Pollin (KU Leuven WaveCoRE) this week proposing a joint measurement of a coherent
28 GHz beam focused onto a tissue-equivalent phantom, imaged with a thermal camera, compared against the
4 cm² averaged compliance metric, as a shared UGent-KU Leuven paper. It is professor-to-professor, same
country, same 6G-exposure community, no funding gate, no clearance, no company required, and it either
produces the single most valuable asset the spin-off could own or kills the headline claim cleanly. Only Wout
can send it, and it is the first thing that should happen.
