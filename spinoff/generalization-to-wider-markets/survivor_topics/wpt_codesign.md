# Wireless power transfer co-design as an AEGIS survivor topic

Honest physics-and-feasibility report. Question on the table: does the AEGIS core method generalize into RF wireless power transfer (WPT), where you must maximize power delivered to a rectenna while keeping human exposure compliant. My verdict is at the bottom. Short version up front: the technical fit is close to perfect and nearly free from existing code, the dual-operator moat is real and genuinely unclaimed by incumbents, and the whole bet lives or dies on whether the WPT market is real enough and whether the exposure constraint actually binds for a paying buyer. I grade it **CONDITIONAL**.

## 1. The physics and why AEGIS is uniquely positioned

### The dual-operator structure

AEGIS is a differentiable physical-optics surface engine plus a closed-form quadratic-operator calculus. The coherent layer already computes two Hermitian operators from the same tissue physics and the same body geometry, both quadratic forms in the array excitation `x`:

- `Q_ab` (absorbed by a human) with `P_ab = x^H Q_ab x`. This is the exposure constraint. It is the Fresnel-transmission Gram integral of the exposure channel over the body surface, `Q_ab = integral_Sigma G_tilde^H G_tilde dA`. Shipped in `src/aegis/coherent/exposure_operator.py`.
- `Q_in` (power that lands on a receiving surface) with `P_in = x^H Q_in x`. In `theory/q_complement.tex` this is the incidence operator `Q_in = Q_ab + Q_ref`, the Gram of the incident field channel integrated over a surface. Swap the human body for a rectenna aperture and the same Gram construction gives the delivered-power operator.

WPT co-design is then literally one line of math:

```
maximize   x^H Q_rect x        (power captured by the rectenna)
subject to x^H Q_ab x <= P0    (human absorbed power stays under the ICNIRP/FCC limit)
           ||x||^2 <= P         (transmit power budget)
```

This is a QCQP with a quadratic objective and two quadratic constraints. It is the exposure-constrained beamforming (ECBF) problem of `papers/coherent-exposure-operator/paperC.tex` with the objective and the constraint swapped. In ECBF the objective is a communication rate `|h^H x|^2` and the body is the nuisance to bound. In WPT co-design the rectenna is the objective and the body is still the nuisance to bound. Same feasibility set, same Lagrangian structure, same solver family.

### Why nobody else owns both operators

This is the actual moat, and it is a structural gap in the market rather than a cleverness gap. WPT vendors optimize efficiency and treat safety as a downstream compliance check. Dosimetry tools compute safety and never model delivered power. AEGIS is the only framework I am aware of that builds **both** the delivered-power operator and the human-exposure operator in the **same** differentiable closed-form calculus, from the same first-bounce tissue physics.

The search evidence backs this up hard. Every incumbent safety patent I pulled (Ossia/Energous families US9871387, US10291056, US11056929, US9941752, US11398751) is about the same thing: **detect a human with a camera or sensor and shut the beam off**, or de-energize the "pocket" of energy where a person is standing. That is exclusion, not co-design. The incumbent safety model is binary: person present means zero delivered power. AEGIS's model is continuous: person present means steer the beam into their exposure null and keep delivering. Nobody in the product world is solving the QCQP. They are solving an interlock.

Academia has touched the QCQP but with toy physics. The SWIPT literature (Specific Absorption Rate-Aware Beamforming, arXiv 1911.10556, and the deep-learning follow-up in IEEE) solves exactly `max energy harvested s.t. SAR constraint` via semidefinite programming. But it uses the lumped handset "SAR matrix" from the Hochwald/Ebadi-Shahrivar phone literature, a measured low-rank quadratic form for a device pressed to a head. AEGIS's edge over that work is fidelity and generality: `Q_ab` here is a full-body phantom Fresnel Gram, `Q_rect` comes from the same field-channel engine, and both are differentiable so the geometry, pose, and frequency are design variables, not fixed measurements. The academics proved the QCQP is the right frame. AEGIS is the only one that can populate it with real body physics and a real delivered-power operator at once.

### The honest frequency-band split

This is where I have to be careful, because the surface-speed claim is band-dependent.

- **mmWave WPT (24 GHz and up).** Surface confinement (Assumption A3) holds. The body is opaque, absorbed power is a surface quantity (absorbed power density S_ab in W/m^2 averaged over 4 cm^2 per ICNIRP 2020), and `Q_ab` is a surface Gram computed fast by the shipped engine. This is AEGIS home turf. And it is exactly where the most credible current player sits: GuRu Wireless beams 24 GHz power to drones (CNX-Software, GuRu press releases). So the band where AEGIS is fastest and most differentiated is a live commercial band, not a hypothetical one.
- **Sub-6 ISM WPT (5.8 GHz, 2.45 GHz, 915 MHz).** Surface confinement fails. The body is penetrable, the metric is SAR (W/kg) with a whole-body basic restriction of 0.08 W/kg and a local 10 g restriction of 2 W/kg for the general public, and `Q_ab` becomes a **volume** Gram over tissue, not a surface Gram. The QCQP structure survives untouched (it is still `max x^H Q_rect x s.t. x^H Q_ab x <= P0`), so the AEGIS math generalizes cleanly. What is lost is the physical-optics surface-speed advantage. A volume `Q_ab` needs a volumetric tissue kernel (FDTD or MoM-like), which AEGIS does **not** ship today. Emrod (5.8 GHz) and Energous (~915 MHz and 2.4 GHz) live here.

So the honest one-liner: **the QCQP and the dual-operator moat generalize to every WPT band. The surface-speed only generalizes to mmWave.** The cleanest product story is 24 GHz WPT, where AEGIS keeps everything.

### How close is a working demo

Closer than I expected before reading the code.

- The shipped solver `src/aegis/coherent/ecbf.py` solves `max |h^T x|^2 s.t. x^H Q x <= P_abs_max, ||x||^2 <= P` by bisection on the Lagrange multipliers, with the closed-form `x* = sqrt(P) (lambda Q + nu I)^{-1} h*`. For a **point-like rectenna** the delivered power is `|h_rect^T x|^2`, a rank-1 objective. That is the shipped solver **verbatim**, with `h` set to the rectenna channel instead of a UE channel. A point-rectenna WPT co-design demo is essentially zero new solver code. It is a channel swap.
- For an **extended rectenna aperture** the objective is a general PSD operator `x^H Q_rect x` (rank greater than one). That turns the problem into a two-quadratic-constraint QCQP, `max x^H Q_rect x s.t. x^H Q_ab x <= P0, ||x||^2 <= P`. This is not the rank-1 shipped path, but it is still tractable in closed form. The S-lemma makes the SDP relaxation tight for two constraints, and the same Lagrangian/bisection generalizes to a generalized eigenvalue problem `(lambda Q_ab + nu I)^{-1} Q_rect`. Call it a few days of work, not a research project.

Net: a 24 GHz point-rectenna demo (drone charging with a bystander phantom in the room, showing delivered power held near-constant while `x^H Q_ab x` is capped) is a nearly-free extension of what already runs. That is a genuine asset for a Tom-meeting demo.

## 2. Light calculations: does the exposure constraint actually bind

If the exposure constraint never binds, there is no product. So I checked whether realistic WPT scenarios actually hit the exposure limit. They blow through it.

### The exposure cap

ICNIRP 2020 and FCC (47 CFR 1.1310) general-public power-density limit at 5.8 GHz and 24 GHz is **10 W/m^2** (= 1 mW/cm^2), averaged over 30 minutes. Occupational limit is 5x higher, **50 W/m^2**. Above 6 GHz the relevant absorbed-power-density limit for local exposure is 20 W/m^2 (public) averaged over 4 cm^2, but 10 W/m^2 incident is the number a bystander MPE is checked against.

### A representative 5.8 GHz link (Emrod-class point-to-point)

Emrod's demonstrated system (TechCrunch, Aerospace Testing International): 550 W beamed 36 m at 5.8 GHz with a 1.92 m diameter phased array.

- Aperture area `A_tx = pi (0.96)^2 = 2.9 m^2`.
- Wavelength `lambda = 3e8 / 5.8e9 = 0.0517 m`.
- Fraunhofer distance `2 D^2 / lambda = 2 (1.92)^2 / 0.0517 = 143 m`. So the 36 m demo is in the Fresnel (near-field) region, where the beam is roughly collimated and the in-beam power density is approximately `P_t / A_tx = 550 / 2.9 = 190 W/m^2`.
- In the far field the on-axis density is `S = P_t G / (4 pi d^2)` with `G = 4 pi A_tx / lambda^2 = 4 pi (2.9) / (0.0517)^2 = 13600 = 41.3 dBi`, giving `S(36 m) = 550 x 13600 / (4 pi x 1296) = 460 W/m^2`.

Either way, the in-beam power density is **190 to 460 W/m^2**, which is **19x to 46x the 10 W/m^2 public limit** and roughly 4x to 9x the occupational limit. The beam is a hard hazard zone. This is exactly why Emrod surrounds the beam with a laser-tripwire safety curtain that cuts power when anything enters.

### A representative 24 GHz link (GuRu-class drone charging)

GuRu recharges a drone at 30 to 200 feet (9 to 61 m) at 24 GHz, delivering watts to the onboard recovery unit. To land a useful ~50 W into a 0.25 m x 0.25 m rectenna (0.0625 m^2), the power density **at the rectenna** must be at least `50 / 0.0625 = 800 W/m^2`, ignoring conversion inefficiency. Rectenna RF-to-DC efficiency is maybe 50 to 70%, so the incident density is higher still. That is roughly **80x the public MPE**. A bystander who wanders into the main lobe, or into a grating lobe or a strong sidelobe of a synchronous tiled array, is instantly non-compliant.

### The tension, made concrete

To deliver useful power you must push the beam density one to two orders of magnitude above the exposure limit. So the constrained optimum is never slack. The whole value of the link sits right against the constraint boundary. In QCQP terms `x^H Q_ab x <= P0` is an **active** constraint at the optimum whenever a human can be near the beam or its sidelobes, which is precisely the regime `ecbf.py` was written for (its docstring flags the active-constraint case as the normal one and the slack case as the exception).

The one honest caveat: for **low-power** harvesting (Powercast-class, microwatts to milliwatts to an RFID or sensor), the density is far below 10 W/m^2 and the constraint is trivially slack. There the exposure math is a checkbox and there is no AEGIS product. The constraint binds only in the **watts-to-kilowatts** regime, which is exactly the regime that has failed to reach scale commercially. That is the crux of the risk, and I return to it in the verdict.

## 3. Incumbents and market

I ran several searches. The picture is consistent: the technology is real, the physics is sound, and the market has over-promised for more than a decade and is still tiny.

- **Energous (WattUp).** First FCC certification for power-at-a-distance, December 2017. Yet the Q3 2025 8-K (SEC) reports quarterly revenue of ~$1.3M, YTD ~$2.6M, order backlog ~$4.2M, and describes this as "the highest recorded quarterly revenue since 2015." A decade of near-zero revenue is the story hiding in that superlative. Real progress, minuscule scale.
- **Ossia (Cota).** Long-hyped RF-at-a-distance charging. Its public footprint is object-detection safety patents (video-camera-gated shutoff) rather than shipping revenue. No evidence of scale.
- **Powercast.** Genuinely shipping, but in the microwatt-to-milliwatt RFID and sensor-harvesting niche. Exposure is a non-issue at that power. No co-design need.
- **Emrod.** Real point-to-point beaming (550 W over 36 m, 5.8 GHz, roadmap to space-based solar power with ESA/Airbus). But the human is simply excluded from the beam by a safety curtain. The design philosophy is keep-out, not co-exist.
- **GuRu Wireless.** The most credible mmWave player. 24 GHz, "Smart RF Lensing," synchronous tiled phased arrays, 96 hours of continuous drone flight recharged at 30 to 200 feet. This is the one whose band and use case fit AEGIS best.
- **Reach, Wi-Charge.** Reach does RF power-at-a-distance for enterprise IoT. Wi-Charge is infrared, not RF, so out of scope for the RF exposure operator.

### Is exposure a real design bottleneck or a checkbox

This is the honest heart of the report, so I will not soften it. Exposure compliance splits three ways:

1. **Low power (Powercast).** Checkbox. Constraint never binds. No product.
2. **High power, human excluded (Emrod, space solar).** The human is kept out of the beam by design, so co-optimization is unnecessary. Detect-and-shutoff or a keep-out zone is sufficient and cheap. AEGIS's continuous co-design adds little when the answer is "nobody is allowed in the beam anyway."
3. **Useful power in a human-shared space (the AEGIS sweet spot).** A device charging in a room, warehouse, or airspace that also contains people, where you cannot exclude them and cannot afford to shut off every time someone walks by. Here detect-and-shutoff collapses the duty cycle to near zero, and only co-design (steer the exposure into the bystander's null while maximizing rectenna capture) keeps power flowing while staying compliant. **This is the only regime where the dual-optimization genuinely matters to a buyer.**

The problem is that regime 3 is exactly the one that has not materialized commercially. The market has bifurcated into "so low-power that safety is free" and "so high-power that humans are excluded." The middle, where AEGIS wins, is thin today.

### Who regulates it, and does that help

The regulator is the gatekeeper, and that is the strongest part of the market story. Every FCC power-at-a-distance approval (Energous 2017 onward) hinged on an exposure-compliance demonstration under 47 CFR 1.1310 MPE limits, and the international frame is ICNIRP 2020. WPT-at-distance is treated conservatively precisely because a focused beam is a novel exposure geometry. So compliance is not optional and not cheap to demonstrate. That is real pain, and it is dosimetry pain, which is AEGIS's native competence.

## 4. The bridge argument

WPT co-design is a natural bridge from dosimetry, cleaner than most survivor topics, because almost nothing changes:

- **Same physics.** Tissue Fresnel transmission, first-bounce, surface confinement at mmWave. The exact regime AEGIS was built for.
- **Same regulator.** ICNIRP 2020 and FCC 47 CFR 1.1310. AEGIS already computes against these limits in `src/aegis/compliance/`.
- **Same operator machinery.** `Q_ab` is unchanged. The only new object is `Q_rect`, and it is the same Gram construction as `Q_in`, evaluated over a rectenna surface instead of a body.
- **New revenue quantity.** Delivered power (watts to the rectenna) instead of communication rate or a pass/fail dose report. This is the one genuinely new thing, and it is an objective the engine can already express.

On reachability for a UGent spin-off: the credible buyers are a short list (GuRu, Reach, Energous, drone-charging integrators, and the space-based-solar-power research programs at ESA and Airbus that Emrod partners with). ESA and Airbus are reachable through European academic channels, which favors a UGent spin-off. GuRu is US-based and venture-funded and harder to reach cold.

On credibility transfer: this is the strongest single argument for the topic. AEGIS's safety-authority standing in dosimetry (ICNIRP-grade compliance, phantom physics, golden-tested against the monograph) is exactly the credential a WPT vendor needs when it walks into an FCC or notified-body approval. A WPT company that says "we optimize efficiency" is not credible on safety. A dosimetry group that says "we also maximize your delivered power, and here is the certified exposure operator that proves compliance at the optimum" is credible on both. The dual-operator story is not just elegant physics. It is a regulatory-credibility wedge that the pure-efficiency incumbents structurally cannot claim.

## 5. Verdict

**Grade: CONDITIONAL** (upper edge, bordering SOLID on the technology, held back to CONDITIONAL by the market).

The technical fit is excellent and close to free. The dual-operator moat is real, and the search evidence confirms nobody in the product world holds both operators, because their safety model is detect-and-shutoff rather than co-design. The QCQP is already shipped for the rank-1 (point rectenna) case and is a few days of work for extended apertures. The regulatory-credibility bridge from dosimetry is genuine and hard for incumbents to copy.

**Strongest angle.** The dual-optimization is the only thing that keeps power flowing in a human-shared space. Incumbents shut off when a person appears, which zeroes the duty cycle. AEGIS steers the exposure into the bystander's null and keeps delivering, and it can certify the exposure at the optimum with dosimetry-grade physics. Best framed at 24 GHz (GuRu's band), where AEGIS keeps its surface-speed and loses nothing. The pitch is not "we make WPT safe." It is "we make WPT that stays on when a person walks in, and we can prove it to the regulator."

**Biggest risk.** The market. After a decade the revenue leader (Energous) books ~$1.3M a quarter and calls it a record. The exposure constraint binds hard in exactly one regime (useful power in shared human space) and that regime is the one the industry has failed to reach. Low-power harvesting makes safety free, and high-power beaming excludes humans by design. AEGIS wins the thin middle, and the thin middle may stay thin. This is a technology waiting on a market that has repeatedly disappointed.

**What would have to be true for this to become a STRONG-BET.**

1. At least one WPT vendor reaches real deployment scale in human-shared space at watts-to-kilowatts, so co-design is a live purchasing need rather than a slide. GuRu's drone-charging trajectory is the one to watch.
2. A regulator (FCC or an EU notified body) signals that beam-shaping compliance, not just keep-out zones and interlocks, is an acceptable or preferred path to approval. That single move would convert AEGIS's operator from a nicety into the certification instrument.
3. AEGIS ships a volume `Q_ab` kernel if the buyer is sub-6 (Emrod, Energous). At 24 GHz this is not needed and the surface engine suffices.

If items 1 and 2 land, this jumps to SOLID or STRONG-BET fast, because the tech is already sitting there. Absent them, it is a beautiful, nearly-free capability pointed at a market that may not show up. Hence CONDITIONAL.

### Sources

- SAR-aware SWIPT beamforming (the academic QCQP with toy physics): arXiv 1911.10556, and the deep-learning follow-up (IEEE Xplore 9210124), SWIPT safety constraints arXiv 2111.10689.
- EMF exposure review for WPT: arXiv 2510.18570.
- FCC MPE limits: 47 CFR 1.1310. ICNIRP 2020 general-public 10 W/m^2 power density, whole-body SAR 0.08 W/kg, local 10 g SAR 2 W/kg.
- Incumbent detect-and-shutoff safety patents: US9871387, US10291056, US11056929, US9941752, US11398751.
- Energous financials: SEC 8-K filings, Q3 FY2025 (revenue ~$1.3M/quarter, YTD ~$2.6M, backlog ~$4.2M).
- Emrod: TechCrunch (550 W over 36 m at 5.8 GHz, 1.92 m arrays), Aerospace Testing International, emrod.energy.
- GuRu Wireless (24 GHz, drone charging 96 h, 30 to 200 ft): CNX-Software, guru.inc press releases, EENewsEurope CEO interview.
- AEGIS internal: `papers/coherent-exposure-operator/paperC.tex` (ECBF QCQP), `theory/q_complement.tex` (Q_in incidence operator), `src/aegis/coherent/ecbf.py` (shipped solver), `src/aegis/coherent/exposure_operator.py` (Q_ab).
