# Generalization feasibility: the whole picture

Synthesis of 13 feasibility re-examinations (2026-07-06). Five topics we had killed, eight we
had marked as survivors, each re-opened honestly with physics, light calculations, and web
research. Companion to `generalization_map.md`. The individual reports live in `killed_topics/`
and `survivor_topics/`.

## The one thesis that came out of it

The durable jewel is not the surface-speed and not "differentiable physical optics" in the
abstract. It is the **differentiable closed-form constrained-focusing operator** (the ECBF QCQP
in `src/aegis/coherent/ecbf.py`). Every topic that graded well reuses that solver almost verbatim.
Every topic that failed did so for one of two reasons:

1. the deliverable is a **passive scattering signature that has to be certified**, and the
   certifying number lives in edge / tip / creeping-wave / elastic / resonant physics that the
   first-bounce model (assumption A2) structurally omits, so AEGIS can explore a shape but never
   certify it, or
2. the physics transfers fine but the **market or buyer is wrong** (closed, classified, tiny,
   or already served).

So the honest generative rule is sharper than the old "three knobs":

> AEGIS wins where the problem is *design a controllable coherent excitation against quadratic
> power limits*. It loses where the problem is *certify a passive scattering signature*, and it
> is irrelevant where a good-enough tool already ships to a reachable buyer.

This unifies the two overturned kills (hyperthermia, free-field array beamforming) with the
strongest survivors (RIS synthesis, HIFU, in-cabin radar): all of them are controllable-array
constrained-focusing problems, all of them reuse `ecbf.py`.

## Scorecard

Grades: PURSUE (build it), CONDITIONAL (real but scoped or gated), KILL/OVERRATED (do not bet).

| Topic | Grade | Why, in one line |
|---|---|---|
| **RIS / reflectarray synthesis** | PURSUE | Closed-form constrained aperture QCQP reuses `ecbf.py` verbatim, exposure-capped steering nobody ships. Risk: unit-cell library sits outside AEGIS, Sionna RT ships free RIS. |
| **Automotive in-cabin radar** | PURSUE | Body I already model, Euro-NCAP child-presence mandate, synthetic child-data play. Gap: micro-Doppler needs an animated-chest mesh. |
| **HIFU planning** | PURSUE (research/planning-aid) | Acoustic-impedance swap is a channel swap not a rewrite, per-region sparing is already `multibody_ecbf.py`. Gap: nonlinearity + thermal dose need an outer loop, ZMT could copy the single-solve. |
| **WPT co-design** | CONDITIONAL (tech SOLID, market thin) | "Stays on when a person walks in, and I can prove it," incumbents provably detect-and-shutoff. But the leader books ~$1.3M/quarter after a decade. |
| **Installed-antenna placement** | CONDITIONAL | High-dimensional differentiable placement on smooth automotive platforms is in-band and reverse-mode beats HFSS. Deep co-site isolation (the real money) is out-of-band creeping-wave physics. Readiness ~40-50%. |
| **Differentiable surrogate layer** | CONDITIONAL | Tom's language, engine exists, in-domain accuracy 1-1.2%. But it *is* space mapping (Bandler, prior art, unpatentable) and the gradient sign is untrustworthy near out-of-domain optima. |
| **mmWave imaging** | CONDITIONAL | Differentiable body forward model under learned reconstruction, R&S QPS is same-band and local. Gap: concealed object is not a body, clothing is multilayer. |
| **Radome design** | CONDITIONAL (attach, not standalone) | Flat painted-stack optimizer is a commodity afternoon. Curved-shell boresight co-design is valuable but boresight error is antenna-to-wall multibounce PO drops. Best as a patent embodiment + attach to the antenna story. |
| **Radiative-thermal** | CONDITIONAL (narrow: heliostat CSP) | "Mitsuba owns it" was a category error, engineering thermal toolchain is not differentiable. But only heliostat-field layout clears the large-N + heuristic-incumbent + open-buyer bars, and CSP is a small slow TAM. |
| **Deep regional hyperthermia** | CONDITIONAL (overturned from DEAD) | Clinical metric HTQ is a ratio of two volume-Gram quadratic forms = my eigenproblem, incumbents still use particle swarm / genetic algorithms, extends the ZMT relationship. Surface-speed dead below 6 GHz, planner alive. |
| **Free-field array beamforming** | CONDITIONAL (overturned from DEAD, acoustics) | Cleanest instance of the operator calculus, pure A1 superposition, cleaner than tissue dosimetry. But it is convex and already solved, so the moat is unproven. |
| **RCS / stealth (standalone)** | KILL / OVERRATED | Explorer not certifier (low-RCS floor is edge/tip diffraction A2 omits), already published (Stealth Shaper), ITAR-gated for an EU spin-off. |
| **Sonar target strength** | KILL / OVERRATED | Double bind: strong physics -> classified buyer, open buyer -> resonant ka~1 wrong physics. Elastic Lamb waves certify a hull, JAX-BEM owns "differentiable." |
| **Seismic AVO** | DEAD | Parameter estimation with no controllable excitation, FWI adjoint is already differentiable and ahead. Redirect: elastic-array focusing wants to be HIFU, not seismic. |
| **Room reverberation** | DEAD | The deliverable is the diffuse late field and edge diffraction, both of which A2 discards. |
| **Freeform imaging optics** | DEAD | No controllable excitation (fixed incoherent source, geometry is the variable), differentiable rendering owns it with full multi-bounce. Survivor cousin is OPA LiDAR steering, a coherent-array pivot. |
| **Industrial cavity heating** | DEAD | Multimode cavity resonance, not physical optics. A2 and A3 both fail. |

## Cross-cutting patterns worth stating out loud

1. **The ECBF QCQP is the asset, the surface-speed is not.** RIS, HIFU, WPT, hyperthermia, and
   array beamforming all reuse `ecbf.py` and grade well. The surface-speed (A2+A3) is only ever a
   convenience and it dies the moment the target is penetrable (HIFU, hyperthermia, sub-6 WPT).

2. **Explore-versus-certify is the recurring wall.** Stealth RCS, sonar, deep co-site, radome
   boresight all fail on the same thing: first-bounce PO can push a gradient but cannot own the
   number the customer pays for, because that number is set by the physics A2 drops. `fock.py`
   closes the creeping-wave gap only for smooth convex bodies, which sharpens the wall rather than
   removing it.

3. **The optimistic map oversold everything by about one grade.** Nothing came back STRONG-BET.
   The best are SOLID/PURSUE with a named caveat. This is the honest correction to
   `generalization_map.md`, which was written before the market and prior-art checks.

4. **Prior art is denser than expected, and it clusters.** Space mapping (surrogate layer),
   Stealth Shaper (RCS), Sionna RT (RIS), JAX-BEM (sonar, barriers), differentiable rendering
   (optics, thermal), published rib-sparing SDR (HIFU). The general "differentiable X" idea is
   almost never empty ground. The defensible novelty is the *closed-form constrained* operator and
   its eigenstructure, not differentiability itself.

5. **The ZMT/Sim4Life relationship is a recurring unlock.** HIFU and hyperthermia both extend the
   existing first customer (same solvers, same regulator), which lowers go-to-market risk more than
   any greenfield EDA wedge.

6. **The cleanest new EDA object survived: RIS constrained synthesis.** It is the one wedge that is
   in-band physically (A2 honest for a passive aperture main beam), closed-form, differentiable,
   reuses the shipped solver, and is not owned in *constrained/exposure-capped* form by an
   incumbent. If one thing gets built to prove the generalization, this is it.

## Implications for the patent decision

- Do not anchor a broad claim on "differentiable physical optics" or on surface-speed. Both have
  prior art (Sionna, Mitsuba) and the speed dies off-tissue.
- Anchor the general claim on the **closed-form constrained-focusing operator and its
  eigenstructure** (the differentiable functional characteristic modes), plus the energy-partition
  identity. That is what no incumbent ships and what every good grade above depends on.
- Keep the tissue-dosimetry method as the strong, clean, separately defensible embodiment
  underneath. Add embodiments for RIS/reflectarray synthesis, WPT dual-operator co-design, and the
  acoustic-impedance analog (HIFU/hyperthermia).

## Implications for the Tom meeting

- Lead with the honest generative rule (design controllable excitation vs certify passive
  signature). It is a stronger and more defensible story than a long yes list, and it pre-empts his
  first objection.
- The wedge to put in front of a Keysight/Ansys conversation is **RIS constrained synthesis**,
  with installed-antenna placement as the second and the surrogate-layer framing as the wrapper
  (conceding the space-mapping lineage up front).
- Concede the explore-vs-certify wall before he raises it. It is the credibility move.

## Assessed after this synthesis

- **Military RF safety** (shipboard radar, EW jammers, counter-drone microwave weapons). Graded
  CONDITIONAL, near the top of the band, above WPT and beside RIS on physics quality. It passes the
  generative rule: the emitter is a controllable phased array, the constraint provably binds, and
  the receptor is a human body. Independent research confirms nobody models the body and no fielded
  system does exposure-constrained beamforming. Held back by budget (ordnance safety, not personnel
  safety, gets the money), by safety boards that structurally prefer the static keep-out zone, and
  by classified platform geometry. Full write-up in `../military_angle/`.
