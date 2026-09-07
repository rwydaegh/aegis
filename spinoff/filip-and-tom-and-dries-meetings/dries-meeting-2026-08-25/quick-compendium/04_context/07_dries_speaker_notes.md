# Speaker notes

## Meeting objective

The current patent claim set covers dosimetry. Today’s outcome is technical classification and benchmark design:

1. A technically accurate name for the approximation family.
2. The first missing physical effect for a radiating device near a body.
3. A small benchmark campaign with an agreed failure threshold.

If the discussion drifts, return to: "Gaat uw bezwaar over geldigheid binnen het afgebakende regime, over een toepassing buiten dat regime, of over nieuwheid?"

## Opening script

> Ik wil eerst één wijziging tegenover de mail van juli benoemen. Filip en ik hebben gisteren beslist dat de huidige patentindiening en IOF-case bij dosimetrie blijven. Ik wil vandaag de fysische geldigheid binnen een afgebakend hoogfrequent en optisch dik regime toetsen. Mijn drie vragen zijn: hoe classificeert u deze reductie, welke fysica faalt eerst bij een device dicht bij het lichaam, en welke minimale benchmark is daarvoor overtuigend?

Pause after the three questions. Let Dries choose where to start if he immediately engages.

## Slide 1: AEGIS Surface Operator

Open with the observable and interface: AEGIS maps an already characterized incident field and body surface to absorbed power.

If challenged immediately:

> Helemaal akkoord dat dit geen algemene Maxwell-solver is. Dat is ook niet de claim die ik vandaag wil verdedigen.

## Slide 2: Scope

This resets the mandate. Dries’s input should sharpen the validity boundary and benchmark.

If he asks why the July email was broader:

> Dat was toen de open businessvraag. Die is intussen beslist. Uw technische input wil ik nu gebruiken om de claimgrens en het validatieplan scherper te maken.

## Slide 3: Operator

Emphasize the interface. A field solver or ray tracer characterizes illumination. AEGIS then maps that representation and local body data to absorbed-power metrics. It does not solve induced currents everywhere.

Likely objection: "Then the expensive part is already solved."

Response:

> Soms wel voor één bronkarakterisatie. De winst ontstaat wanneer dezelfde omgeving, body operator of path representation voor veel body poses, tissue draws, beams of precoders wordt hergebruikt. Rapporteer daarom zowel end-to-end als geamortiseerde rekentijd.

## Slide 4: Surface law

Name the three factors separately: incident power, local boundary transmission, and projected area. Then point at visibility as a separate nonlocal factor.

Never say that the positive part is exact visibility. It only rejects back-facing local facets. On nonconvex bodies, self-occlusion requires a separate ray test or a smoother visibility model.

Likely objection: "Physical optics near a shadow boundary is not uniform."

Response:

> Akkoord. De geometrical-optics gate is niet uniform nabij de terminator. Dat gebied hoort in het diffraction error budget of in een tussenmodel. De benchmark moet tonen wanneer die term de gereguleerde ruimtelijke gemiddelde waarde domineert.

Likely objection: "Your old wording said curvature features smaller than a wavelength."

Response:

> Die formulering was verkeerd. De gecontroleerde local-planarity parameter is $1/(kR)$. De lokale kromtestraal moet groot zijn ten opzichte van de golflengte.

## Slide 5: Tissue response

Start from the polarization-aware expression. Present (T_0) as an optional acceleration for unpolarized high-index tissue, not as the foundation and not as the invention.

Likely objection: "This is just Fresnel."

Response:

> The local boundary coefficient is standard. The discussion is about the assembled absorbed-power operator, its validity boundary and reuse across exposure evaluations. Fresnel transmission itself is not the novelty claim.

Likely objection: "Angle-dependent transmission cannot be replaced by one average on a nonconvex body."

Response:

> Correct. I do not use a nonconvex Cauchy identity to factor an angle-dependent transmission exactly. For nonconvex bodies, visibility can correlate with incidence. The exact local model keeps (T_{\mathrm{eff}}(\theta,\mathrm{pol})) pointwise. (T_0) is only a controlled specialization.

## Slide 6: Operators

The incoherent form maps path powers. The coherent form adds fields before squaring. The underlying local boundary assumption is unchanged.

Likely objection: "Differentiable with respect to what?"

Response:

> Algebraically with respect to continuous parameters inside a fixed path and visibility topology. At shadow or path birth and death, the hard model is nonsmooth. A smoothed transition can regularize it, but I do not claim universal end-to-end differentiability.

## Slide 7: Coherence

The PSD property is structural, not independent physical validation. The useful result is computational reuse of (Q) for many precoders.

Likely objection: "(Q=G^H G) being PSD is tautological."

Response:

> Yes. PSD is a consistency property and enables optimization. It does not validate whether the off-diagonal coupling is physically accurate. That still needs a coherent reference benchmark.

Likely objection: "Depth phases differ by path."

Response:

> The current derivation retains the complex TM response and depth phase. A mean-depth rank-one reduction gives below 0.05 percent discrepancy at 28 GHz and below 0.08 percent over the tested band. That tests the depth reduction, not the full surface approximation.

## Slide 8: Evidence

Be explicit that the evidence is uneven. The method has Mie, local Fresnel and Sim4Life FDTD checks, but no blind anatomical 28 GHz device-to-body comparison. That gap is explicit.

If he attacks the 3.2 percent number:

> Dat getal vergelijkt de $T_0$-reductie lokaal met het volledige Fresnel-oppervlaktemodel onder 75 graden, niet met FDTD. Het is een reductiecheck.

If he says the Sim4Life checks are not enough:

> Akkoord. Ze ondersteunen de observable and averaging reductions, but they do not close the near-body source-model question.

## Slide 9: Validity

Do not defend an example outside the right-hand column. Ask Dries to identify which row fails and how to measure it.

Useful follow-up:

> Welke geometry, source distance, frequency, observable en error tolerance would make that failure unambiguous?

If he raises edge, cavity or creeping-wave counterexamples:

> Those are real counterexamples to a general solver. They are already outside the present claim boundary. The question is whether they dominate the dosimetric spatial average in the target configuration.

## Slide 10: Device sources

A nearby device is not represented silently as a plane wave. A spherical Green-function or Huygens representation can describe a candidate source field. Source-body back-action remains a separate test.

Likely objection: "The body perturbs the antenna, so your incident field is not prescribed."

Response:

> If that perturbation is material, the source field must be solved jointly and AEGIS is not the standalone solver. A useful benchmark should sweep standoff and measure exactly where the one-way factorization stops meeting tolerance.

Likely objection: "Three wavelengths is not a universal boundary."

Response:

> Agreed. I am not using a universal (3\lambda) rule. The boundary should be defined by coupling error for the actual aperture, body and observable.

## Slide 11: Benchmark

Use a finite aperture over a layered curved patch as the third case. It remains reference-solvable while representing the intended device-body regime.

Possible benchmark parameters to capture on the whiteboard:

- Frequency: 10, 28 and 60 GHz.
- Standoff: several points from clearly reactive to clearly radiative.
- Reference: FEM, FDTD, MoM or a differential surface-admittance formulation chosen by Dries.
- Outputs: local APD, peak 4 cm² APD, total absorbed power, source-input impedance change and runtime.
- Thresholds: decide before simulations, perhaps separate 5 percent integrated and 10 percent local targets.

Do not volunteer the sample thresholds as settled. They are discussion anchors.

## Slide 12: Questions

Ask question 1 first and write down Dries's exact terminology. If he answers with "standard physical optics," ask which qualifier distinguishes the observable-specific and lossy-surface reduction.

Question 4 is tailored to his work. It is not a claim that differential surface admittance fits unchanged. Ask whether it could be a middle fidelity between the local Fresnel law and a volume solver while preserving reusable operator structure.

Only ask the adjacent-application question if the first four have concrete answers. Do not let it consume the meeting.

## Likely challenges

### "There is nothing new here"

> Bedoelt u dat de lokale fysica standaard is, dat de samengestelde dosimetrie-operator prior art is, of dat het validatieniveau onvoldoende is? Dat zijn drie verschillende bezwaren. Met welke referentie of formulering moeten we vergelijken?

Do not argue patent novelty from the slide deck. Ask for the closest technical formulation and capture it for Alessandro.

### "This cannot work in the near field"

> In the reactive coupling regime, I agree. In the radiating near field, the question is whether a one-way spherical or Huygens field representation plus local surface response meets an observable-specific tolerance. Which standoff sweep would settle that?

### "Your validation proves only trivial cases"

> The present checks establish pieces of the reduction. They do not close the device-to-body case. I want your help selecting the smallest nontrivial blind case that does.

### "Use BEM or differential surface admittance instead"

> That may be the right reference or intermediate fidelity. My constraint is preserving fast repeated evaluation of absorbed-power observables. Can the surface-admittance operator be assembled once and reused across many illuminations or precoders, and at what cost?

### "Generalize it to another market"

> Graag als aparte hypothese, zodra die de vijf voorwaarden haalt. Dat is niet nodig voor de huidige indiening. Welke toepassing test u eerst, en wat is de beslissende benchmark?

## Closing script

> Als ik het goed samenvat, noemt u dit [classificatie]. Voor de device-to-body case verwacht u dat [foutmodus] eerst domineert. De minimale test is [geometrie, bron, frequentie, grootheid, tolerantie] tegen [referentie]. Klopt dat?

Then ask who can help run or review the reference benchmark. Leave the meeting with named geometry, reference method and tolerance, not only a general opinion.
