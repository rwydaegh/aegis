# Is there a problem? Stress-testing the "compliant on paper, non-compliant in reality" claim

Agent 10. Written 2026-07-09. This is the deep, adversarial version of the orchestrator's thermal
note (`00_orchestrator_thermal_note.md`), which I confirm in outline and correct in two places. All
physics here I did myself against the IT'IS v5 tissue database in `data/itis_v5.db`. Scripts live in
`/tmp/claude-1001/-home-user-aegis/09a8d401-c47f-427d-804a-48196a28a48a/scratchpad/` (`thermal_leg2.py`,
`thermal_transient.py`, `thermal_robust2.py`, `legs_1_3.py`, `freq_table.py`).

## 1. Verdict, one sentence

The claim is **physically true but small and, as pure physics, already published**: a diffraction-limited
coherent hotspot on skin does defeat the 4 cm2 average and the unperturbed-field assumption, but blood
perfusion and lateral heat conduction cap the real thermal overshoot at about **2.6x at 28 GHz** (rising
to about 4.4x for a short stare and to a peak skin temperature that reaches the 5 C injury threshold by
60 to 95 GHz), and the dosimetry community (Hashimoto and Hirata 2017, Neufeld and Kuster 2018) has
already shown the averaging area and the 6 minute window are non-conservative for focused and pulsed
sources, so Robin is second on the physics and the only genuinely novel, fundable object left is the
narrower **compliance-methodology gap for a steerable, dynamically reconfigurable array plus the
certifiable worst-case-over-all-beams bound that closes it**.

Leg 2 (thermal) was the one that could have killed everything. It did not. But it also shrank the
headline from a scandal to a factor of two to three, and it handed most of the credit to Hirata and
Kuster.

## 2. The three things that most changed my view

1. **Leg 2 survives, and it survives for a precise and citable reason.** At equal 4 cm2-averaged APD
   (equal total power), the 0.9 cm2 hotspot at 28 GHz reaches a peak skin temperature about **2.6x**
   that of the uniform beam the limit was calibrated against, holding even in the no-perfusion,
   pure-conduction limit at about **1.9x**, and robust to **2.4 to 2.7x** across single-layer,
   skin/fat/muscle, and 10 to 28 GHz penetration depths. The reason it does not wash out is that the
   diffraction-limited spot radius (about 5.4 mm at 28 GHz) sits right at the 6 minute thermal
   diffusion length in skin (5.97 mm) and the perfusion length (6.83 mm). Conduction erodes the
   concentration but cannot erase it, because the electromagnetic spot is exactly as big as the
   distance heat can travel in the averaging time. That is not a coincidence I can wave away, it is the
   physics, and it is the sentence that makes the claim defensible to a thermal reviewer.
   (Source: my Pennes solves against IT'IS v5, cross-checked to an analytic Hankel-transform steady
   state to 16 digits.)

2. **The physics is not novel. Hirata and Kuster got there in 2017 and 2018.** Hashimoto and Hirata
   (Phys Med Biol 2017, "On the averaging area for incident power density...") already showed the
   4 cm2 average correlates with peak temperature only for near-uniform fields, and that a
   small-diameter beam needs an incident-power-density **compensation factor equal to the ratio of the
   effective beam area to the averaging area**. They explicitly modeled an ideal beam, a dipole, and
   **an antenna array**. Neufeld and Kuster (Bioelectromagnetics 2018, "maximally allowable
   power-density averaging area for conservative...assessment") went further, derived that 4 cm2 is
   **not conservative** for any transmitter closer than 2 mm, and in the same paper did the worst-case
   pulsed-fluence thermal analysis and recommended a **240 s** averaging time for mm-waves, not the
   360 s in the standard. That is Leg 1 and Leg 3 both published, in the exact worst-case framing Robin
   would use. (Sources below.)

3. **The industry compliance methodology has a real, admitted hole, and it is a different hole than the
   physics one.** Thors and Colombi's "actual maximum exposure" Monte Carlo (Frontiers 2021), which is
   the basis for shrinking 5G massive-MIMO compliance boundaries, gets its power-reduction factor of
   about 0.12 by assuming a **statistical distribution of users and beam directions plus time
   averaging**, and it states plainly that it **does not model a beam deliberately held on one
   person**. Chiaraviglio et al. (2020, "Pencil Beamforming Increases Human Exposure: True or False?")
   concludes "false", but again on a population-statistical basis. Nobody in that literature computes
   the worst case of a beam parked on a chosen body point. That worst case is exactly what AEGIS's
   `lambda_max(Q)` and `norm(G_t)^2` compute with a body in the scene, and it is the one object that is
   both defensible and unoccupied.

## 3. What I verified, inferred, and could not check

**Verified (I did the calculation or read a primary/near-primary source):**
- Skin thermal properties from IT'IS v5: k = 0.372 W/m/K, c = 3390.5 J/kg/K, rho = 1109 kg/m3,
  Pennes perfusion coefficient (Heat Transfer Rate) = 7969 W/m3/K. Hence alpha = 9.9e-8 m2/s,
  perfusion length L = sqrt(k/h) = 6.83 mm, thermal time constant tau = rho c / h = 472 s = 7.9 min.
- The steady-state and transient Pennes overshoot factors and absolute temperatures (all tables below),
  cross-validated analytic-vs-numeric and against published plane-wave values (my 10 GHz plane-wave-like
  case gives 1.44 C at 100 W/m2, inside the published 0.9 to 2.4 C range).
- ICNIRP 2020 local limits above 6 GHz: Sab occupational 100 W/m2, public 20 W/m2 (= occ / 5), 4 cm2,
  6 min, plus a 1 cm2 restriction above 30 GHz. Target dT = 2.5 C (occupational operational threshold
  5 C divided by safety factor 2). Type-1 adverse-effect threshold 5 C, type-2 2 C, pain/damage near
  43 C (about 9 C rise).
- The prior-art papers exist and say what point 2 above reports (Hashimoto/Hirata 2017,
  Neufeld/Kuster 2018, Foster/Ziskin/Balzano 2016 and 2018, Thors/Colombi 2021, Chiaraviglio 2020).

**Inferred (reasoned, not read verbatim):**
- That the genuinely novel residue is the agile-array methodology gap plus the certifiable bound. I
  searched for a paper making that exact synthesis and did not find one, but absence of a search hit is
  weak evidence.
- The absolute military-topside multiplier from the unperturbed-field practice (Leg 4). I bounded it
  from the ground-reflection and standing-wave literature, I did not model a specific deck.

**Could not check (NEEDS_CONTEXT):**
- The exact text of ICNIRP 2020 and IEEE C95.1-2019 (both PDFs, WebFetch returns binary). The icnirp.org
  guidelines PDF and the IEEE standard are the two I most want verbatim, especially whether the ICNIRP
  1 cm2 restriction above 30 GHz is at 1x or 2x the basic restriction, which changes my high-frequency
  numbers by 2x).
- The **non-public IEC 62232 / IEEE ICES TC95 working drafts**. If the agile-array worst-case gap is
  already a work item there, the last novel residue is gone. Wout would know or could find out in one
  email. This is the single most important thing I cannot see from here.

## 4. Leg 2 first, honestly. The thermal calculation that could have killed it

I did this before anything else, as instructed, because if lateral conduction erases the concentration
on the exposure timescale then the 4 cm2 average is physically the right thing to average and there is
no story.

**Setup.** Semi-infinite skin, Pennes bioheat `k*lap(T) - h*(T - Ta) + Q = 0`. Above 6 GHz the power is
deposited within a sub-millimetre penetration depth, which is exactly why the standard defines APD as a
surface density, so I use a surface heat flux and separately confirm a finite penetration depth changes
nothing. I compare two exposures with the **same 4 cm2-averaged APD** (hence the same total power P into
the window): a uniform beam filling the 4 cm2 patch, and a Gaussian hotspot of the measured 0.9 cm2
footprint. The overshoot factor E is the ratio of their peak skin temperatures. E is what the standard
is blind to, because both report the same compliance number.

**The key length scales (this is the whole argument).**

| scale | value | meaning |
|---|---|---|
| perfusion length sqrt(k/h) | 6.83 mm | beyond this, blood carries the heat, not conduction |
| thermal diffusion length over 6 min | 5.97 mm | how far heat spreads in the averaging window |
| 4 cm2 patch radius | 11.28 mm | the averaging window |
| 0.9 cm2 hotspot radius (lambda/2 at 28 GHz) | 5.35 mm | the diffraction-limited spot |
| diffusion length over a 1 ms radar dwell | 0.010 mm | nothing spreads |
| diffusion length over a 10 s stare | 0.995 mm | barely spreads relative to the spot |

The hotspot radius, the perfusion length, and the 6 minute diffusion length are all about 5 to 7 mm.
The spot is exactly as big as the distance heat travels in the averaging time. That is the regime where
concentration partly survives conduction. If the spot were 0.1 mm it would wash out (E to 1). If it were
5 cm it would fill the window (E to 1). It is neither, by diffraction.

**Steady-state overshoot E at 28 GHz (equal total power).**

| hotspot | vs uniform 4 cm2 disk | note |
|---|---|---|
| 0.9 cm2 (28 GHz diffraction limit) | **2.58x** | analytic, perfusion included |
| 0.9 cm2, no perfusion (pure conduction) | **1.87x** | the limit most favorable to the standard |
| 1.77 cm2 (15 mm spot, paper figure) | 1.61x | |
| 0.5 cm2 | 3.79x | |
| 0.08 cm2 (95 GHz diffraction limit) | 11.3x | |

**Transient E(t) over the 6 minute window (equal total power, occupational level).**

| time | uniform 4 cm2 (C) | hotspot 0.9 cm2 (C) | E |
|---|---|---|---|
| 10 s | 0.27 | 1.13 | **4.23** (near the 4.44 area ratio, no time to spread) |
| 60 s | 0.68 | 2.43 | 3.59 |
| 3 min | 1.07 | 3.19 | 2.98 |
| 6 min | 1.29 | 3.50 | **2.71** |
| steady | 1.45 | 3.68 | 2.54 |

So the overshoot is largest for a brief stare (approaching the raw 4.44 area ratio, because heat has no
time to spread) and relaxes to about 2.5 to 2.7x as the beam holds and conduction does its work. It
never falls to 1. **Leg 2 does not kill the claim, it bounds it at roughly 2.5 to 4x at 28 GHz.**

**Robustness (pre-empting the reviewer's first attack).** A single-layer skin model is where Hirata or
Kuster would push first, so I ran layered and finite-penetration versions. E at 6 minutes:

| model | dT uniform (C) | dT hotspot (C) | E at 6 min |
|---|---|---|---|
| single-layer skin | 1.29 | 3.47 | 2.69 |
| skin 1.5 / fat 8 / muscle | 1.81 | 4.47 | 2.48 |
| skin 1 / fat 4 / muscle | 1.90 | 4.82 | 2.54 |
| skin 2 / muscle | 1.25 | 3.34 | 2.68 |
| single-layer, delta = 0.5 mm (28 GHz) | 1.20 | 3.12 | 2.60 |
| single-layer, delta = 2 mm (10 GHz) | 0.93 | 2.23 | 2.39 |

E is a robust 2.4 to 2.7x. The insulating fat layer raises the **absolute** temperatures (the reference
uniform beam climbs to 1.8 to 1.9 C, closer to the 2.5 C design target), so the layered hotspot reaches
**4.5 to 4.8 C, right at the 5 C type-1 adverse-effect threshold**, while the compliance meter reads
exactly at the occupational limit.

**Absolute hazard, and how it moves with frequency (the money table).** Peak steady-state skin
temperature of a beam sitting exactly at the occupational limit, applying the standard's own binding
spatial rule (4 cm2 below 30 GHz, and the 1 cm2 restriction at up to 2x above 30 GHz). Six-minute values
are about 0.88x these.

| f (GHz) | diffraction spot | window used | peak dT (C) | x the 2.5 C target | fraction of 5 C threshold |
|---|---|---|---|---|---|
| 10 | 7.07 cm2 | 4 cm2 | 1.44 | 0.57 | 0.29 (spot bigger than window, no gap) |
| 20 | 1.77 cm2 | 4 cm2 | 2.39 | 0.96 | 0.48 |
| 28 | 0.90 cm2 | 4 cm2 | **3.82** | **1.53** | **0.76** |
| 40 | 0.44 cm2 | 1 cm2 (2x) | 3.04 | 1.22 | 0.61 |
| 60 | 0.20 cm2 | 1 cm2 (2x) | **4.99** | 2.00 | **1.00** |
| 95 | 0.08 cm2 | 1 cm2 (2x) | **8.47** | 3.39 | **1.69** |
| 150 | 0.03 cm2 | 1 cm2 (2x) | 13.98 | 5.59 | 2.80 |

This is where I **correct the orchestrator note**. It concluded the gap self-closes above 30 GHz to
about 1.05x at 95 GHz. It does not. The 1 cm2 backstop helps at 40 GHz (drops the trend) but cannot
resolve a sub-millimetre spot, and its 2x allowance actually permits a higher peak density, so the
absolute compliant temperature **climbs back through the 5 C injury threshold at 60 GHz and reaches
1.7x it at 95 GHz**. The gap is real and worst at the top of the band, not self-closing. (Caveat: if
the ICNIRP 1 cm2 restriction is at 1x rather than 2x, halve the above-30 GHz numbers, which still leaves
95 GHz at about 4.2 C. I could not verify 1x vs 2x from the standard text.)

At the **public** limit (20 W/m2, 5x less power) the same hotspot is 0.76 C at 28 GHz, 1.0 C at 60 GHz,
1.7 C at 95 GHz. The public is thermally safe, the 5x margin dominates, but the 0.5 C public design
target is exceeded by the concentration factor.

**Did ICNIRP and IEEE justify 4 cm2 with a thermal argument, and did they consider a coherent
sub-window beam?** The rationale is not primarily thermal. The 4 cm2 was chosen for **continuity with
the 10 g SAR cube below 6 GHz** (a face of the 10 g cube is about 4.8 cm2), then found to correlate
acceptably with peak temperature **for near-uniform fields**. Both bodies explicitly recognized that
smaller beams need special handling, which is why the 1 cm2 rule above 30 GHz exists. But they addressed
it for **physically small or near sources** (a horn, a lens, a handset in the near field), a beam whose
area is fixed and measurable at commissioning. They did not consider a large coherent array at range
that can present one beam at measurement and concentrate a diffraction-limited hotspot on a chosen body
point at another time. So the standard's reasoning is **not naive** on beam size, it is naive on **beam
agility**. That distinction is the whole game and it is the only part of Leg 1/2 that is still open.

## 5. Leg 1, spatial, the pure dilution number

What the 4 cm2 average hides, as a pure geometry ratio of peak APD to 4 cm2-averaged APD for a Gaussian
hotspot centered in the window:

| hotspot footprint | peak / 4 cm2-avg | peak / 1 cm2-avg |
|---|---|---|
| 1.77 cm2 (15 mm) | 1.98x | 1.21x |
| 0.90 cm2 (28 GHz) | **3.23x** | 1.43x |
| 0.50 cm2 | 5.57x | 1.85x |
| 0.20 cm2 | 13.9x | 3.58x |
| 0.08 cm2 (95 GHz) | 34.7x | 8.67x |

My 1.98x for the 15 mm spot is consistent with the FINDINGS file's measured 1.3 to 1.45x (I model an
idealized centered Gaussian, the real triangulated map is a little lower). **Critical detail: 28 GHz is
below 30 GHz, so the 1 cm2 backstop does not apply**, and the full 3.23x is hidden. The 5G FR2 band from
24 to 30 GHz is the sweet spot for spatial invisibility. Do not multiply this 3.23x into the thermal
overshoot (see section 8), it is the electromagnetic input that the thermal calculation already converts
into the 2.6x temperature number.

## 6. Leg 3, time, the weakest leg. Be honest, it mostly fails for the coherent case

The skin thermal time constant is 472 s, essentially the 6 minute window. That is not a coincidence
either, the window was chosen near the tissue time constant. Consequences:
- A **staring CW coherent beam** reaches near steady state inside the window, so the 6 minute average
  reports the true (high) steady temperature. No hiding.
- A **low-duty scanning radar** deposits negligible heat per dwell (diffusion length 0.01 mm per ms) and
  cools between dwells, so the temperature tracks the duty-cycle-weighted mean, which is exactly what the
  6 minute average reports. **Thermally correct, not a blind spot.**

So for a coherent or CW system, Leg 3 adds nothing. The 6 minute window is doing its job. The **only**
time-domain gap is the **single high-fluence pulse** (the HPM regime, Epirus-class): a 20 ns pulse can
spike surface temperature or drive a thermoacoustic transient before the power average registers
anything. My impulse estimate gives tens of degrees for a 1 mJ/cm2, 20 ns pulse. But that gap is
**already named and already partly patched**: IEEE C95.1 caps per-pulse local fluence above 6 GHz,
Foster/Ziskin/Balzano (2018) flagged the need for fluence limits, and Neufeld/Kuster (2018) recommend
240 s. So Leg 3 is real only for pulsed HPM, and there it is not novel. For the coherent MIMO story that
is the whole point of AEGIS, **Leg 3 does not support the claim**. This is the leg the brief hoped would
help (scanning radar duty cycle), and it is the one I have to report as a near-miss.

## 7. Leg 4, unperturbed field, real but mostly a practice gap

Computing the field with no body present misses two things in opposite directions. Body shadowing
**lowers** absorption on the far side. But a conducting deck or bulkhead behind the body creates a
standing wave, and at a perfect-conductor antinode the incident power density rises by up to
`(1 + |Gamma|)^2` = 4x (2x field), about 2.5x for a realistic ground reflection coefficient of 0.6. The
tissue-layering literature reports a further 2.2 to 4.7 dB (1.7 to 3x) of standing-wave enhancement of
peak SAR. So the honest range for the unperturbed-field error is roughly **0.3x (shadow) to 4x (deck
antinode)**, with the enhancement side being the hazard.

But this is **well known**. RADHAZ practice already applies a reflection safety factor near conducting
surfaces, and the ARPANSA-style prediction methodologies include ground reflection. The genuinely novel
piece of Leg 4 is not the reflection factor, it is that the no-body calculation contains **no coherent
buildup on tissue at all**, which is just Legs 1 and 2 restated (the array phases constructively on a
body point that the empty-air calculation does not know is there). Leg 4 is an **independent multiplier
only for the military topside case**, where the compliance number is computed in empty air with no body
and no worst-case beam. In the 5G base-station case, where incident power density is assessed near where
a body would stand, Leg 4 is small. And its fix is precisely Finding A (put a body in the scene, bound
over all beams), which is the product.

## 8. Assembling the verdict. Do not multiply the legs naively

The brief says multiply the surviving legs. You cannot multiply Leg 1 by Leg 2, that double-counts. The
thermal overshoot E (about 2.6x at 28 GHz) is the **physical realization** of the spatial concentration
(3.23x), already reduced by conduction. The hazard-relevant blindness is the temperature number, 2.6x,
not 3.23 times 2.6.

The honest combination is:

- **5G / base-station coherent array, 28 GHz, staring:** thermal overshoot E about **2.6x** (up to 4.4x
  for a short stare), Leg 3 about 1x (CW captured), Leg 4 small. Net **about 2 to 3x**, absolute peak
  skin temperature about 3.8 C at the occupational limit, 0.8 C at the public limit. A footnote-scale
  standards effect, and already published as physics.
- **Higher frequency (60 to 95 GHz) or near-field tighter focus or thin curved limb:** absolute peak
  temperature reaches and then exceeds the 5 C injury threshold (5.0 C at 60 GHz, 8.5 C at 95 GHz), a
  **genuine hazard**, and the near-field and thin-limb cases (which my planar model does not capture and
  which would concentrate more) could push E higher still.
- **Military topside, unperturbed field, no worst-case beam:** thermal 2.6x times a Leg 4 practice
  factor of 2 to 4x for the empty-air deck-reflection assessment. Net **roughly 5 to 10x**, but this is
  overwhelmingly a **practice** gap (they model no body), which Finding A fixes directly and cleanly.

So the answer to "footnote (2x) or paper (50x)?" is: **about 2 to 3x for the canonical 28 GHz case,
rising into a real injury-threshold hazard at 60 to 95 GHz and in the near field, and about 5 to 10x in
the specific military-topside practice where no body is modeled at all.** It is **not** 50x. The retracted
"~100x" was array gain. The thermally honest concentration is single-digit. **The weakest leg is Leg 3
(time), which does not support the coherent claim at all, and the load-bearing leg is Leg 2 (thermal),
which survives but at 2.6x, not an order of magnitude.**

## 9. Is this novel? The expensive, honest answer

**The core physics is not novel. Robin is second.**
- Hashimoto and Hirata, "On the averaging area for incident power density for human exposure limits at
  frequencies over 6 GHz", Phys Med Biol 2017 (PubMed 28176675). Recommends 20 mm x 20 mm, shows it
  correlates with peak temperature only for near-uniform fields, and prescribes a **beam-area
  compensation factor** for small non-uniform beams. Modeled an ideal beam, a dipole, and an antenna
  array. This is Leg 1 and half of Leg 2.
- Neufeld and Kuster, "Theoretical and numerical assessment of maximally allowable power-density
  averaging area for conservative...assessment above 6 GHz", Bioelectromagnetics 2018. Shows 4 cm2 is
  not conservative for near or focused sources, derives a smaller allowable area, and in the same work
  recommends a 240 s averaging time for pulsed mm-waves. This is Leg 1 and Leg 3 in the worst-case
  framing, from the very group whose tissue database AEGIS uses.
- Foster, Ziskin, Balzano, "Thermal response of human skin to microwave energy", Health Physics 2016,
  and their 2018 averaging-time analysis. Confirms 6 min is broadly fine except for high-fluence pulses.
- A widely cited number in this literature: a 1 mm Gaussian beam produces about **10x** the temperature
  rise of a plane wave at the same averaged power density. That is Robin's claim, published years ago.

**The compliance-methodology hole is closer to open, and it is a different object.**
- Thors and Colombi et al., Monte Carlo "actual maximum exposure" (Frontiers 2021) and the statistical
  compliance-boundary work (arXiv 1801.08351), which underpin the reduced massive-MIMO compliance
  boundaries, get their power-reduction factor of about 0.12 by assuming statistical user distribution
  plus time averaging and **explicitly not a beam held on one person**.
- Chiaraviglio et al. (2020) "Pencil Beamforming Increases Human Exposure: True or False?" answers
  "false" on a population-statistical basis.
- The patent and industry literature manages agile arrays with **time-averaged per-direction EIRP
  control**, not a worst-case per-body-point absorbed-power bound.

I did not find a paper that (a) treats a coherent, dynamically reconfigurable array that can place a
diffraction-limited absorbed-power hotspot on a **chosen** body point via precoding, and (b) shows this
defeats **both** the static beam-area compensation factor (the beam is agile, its area is not fixed at
commissioning) **and** the statistical time-averaging PRF (the beam can be parked), and (c) closes the
gap with a certifiable worst-case-over-all-excitations bound. That synthesis is the residue. Its bound
half has prior art in MRI parallel-transmit VOPs (Finding B), so the novelty must live in the over-the-air,
reconfigurable-array framing, not in the existence of a quadratic bound.

**The relationship risk and opportunity.** Hirata is the closest prior author and Robin has a warm email
contact with him. Pitched as a discovery, this dies in review with Hirata or Kuster on the panel. Pitched
as "extending your averaging-area and compensation-factor framework to the reconfigurable-array case,
where your static compensation factor is not a valid worst-case bound, and here is the bound", it becomes
a natural **co-authored** standards contribution. Turn the novelty risk into a co-author.

## 10. What would kill this (a test someone could run in a week)

- **Kill the residual physics:** run a proper multilayer transient Pennes on a **curved thin limb**
  (finger, shin, the FINDINGS worst-case foci) in Sim4Life, which is Neufeld and Kuster's own tool, with
  the measured 28 GHz hotspot. If E collapses below about 1.5x on a curved limb (3D conduction into a
  thin structure could go either way, my planar half-space may over- or under-state it), the thermal leg
  is a footnote and the whole claim reverts to "known, 2x, already published". This is the highest-value
  physics check and I flagged it because my planar model cannot settle it.
- **Kill the novelty residue:** find the agile-array worst-case exposure gap already written down in an
  **IEC 62232 or IEEE ICES TC95 working draft**. If it is a live work item there, there is no residue
  and this is a citation, not a contribution. I cannot see those non-public drafts. Wout can, in one
  email, and this is the fastest possible kill or confirm.

## 11. Single highest-value next action, and who

**Wout Joseph asks his ICES TC95 / IEC 62232 counterparts one question: is the worst-case exposure of a
dynamically reconfigurable, steerable array (as distinct from a fixed small-beam source) an open work
item, and does the current agile-array compliance methodology assume the beam is never parked on a fixed
person?** If the answer is "open" and "yes it assumes unparked", Robin has a real, narrow, standards-side
contribution: the certifiable worst-case-over-all-beams bound (`lambda_max(Q)`, `norm(G_t)^2`, with a
body in the scene) as the missing conservative instrument, co-developed with Hirata, disseminated through
Wout's seat. If the answer is "already being handled", the honest outcome is that Finding C(a) is a
citation to Hashimoto/Hirata and Neufeld/Kuster, the paper is a modest 2 to 3x standards note, and the
value of the whole thesis collapses back onto Finding A as an **engineering** product (a tighter, body-aware,
provable keep-out certificate) rather than a standards **discovery**. Either way, this one email decides
whether there is a paper here or only a footnote, and only Wout can send it.

---

### Appendix: reproducibility and sources

Scripts (scratchpad): `thermal_leg2.py` (analytic + steady state), `thermal_transient.py` (transient
Pennes, E(t)), `thermal_robust2.py` (layered and penetration-depth robustness), `legs_1_3.py` (spatial
dilution and pulsed-fluence), `freq_table.py` (the frequency money table). Tissue data: `data/itis_v5.db`,
skin. All Pennes solves cross-checked to an analytic Hankel-transform steady state (agreement to 16
digits) and against the published plane-wave 0.9 to 2.4 C per 100 W/m2.

Primary and near-primary sources:
- Hashimoto, Hirata et al., Phys Med Biol 2017, averaging area for IPD above 6 GHz (PubMed 28176675).
- Neufeld and Kuster, Bioelectromagnetics 2018, maximally allowable averaging area (doi 10.1002/bem.22147).
- Foster, Ziskin, Balzano, Health Physics 2016, thermal response of human skin, and their 2018
  averaging-time analysis. Time-temperature thresholds review (PMC8300848).
- Hirata et al., review of computational dosimetry above 6 GHz, Phys Med Biol 2021 (arXiv 2011.10699).
- Thors, Colombi et al., "actual maximum exposure" Monte Carlo, Frontiers 2021 (PMC8777231), and their
  statistical compliance boundaries, arXiv 1801.08351.
- Chiaraviglio et al., "Pencil Beamforming Increases Human Exposure: True or False?", 2020 (arXiv 2010.16288).
- ICNIRP 2020 guidelines and differences page (icnirp.org), and IEEE C95.1-2019. Numeric limits and
  thresholds cross-read from the Health Physics "Analysis of ICNIRP 2020 Basic Restrictions" (2022) and
  the "Protection of Workers" perspective (PMC9215329). The two standards PDFs themselves I could not
  read verbatim (NEEDS_CONTEXT).
