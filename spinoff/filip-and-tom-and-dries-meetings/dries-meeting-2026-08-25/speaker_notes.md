# Speaker notes

## Meeting objective

The current patent claim set covers dosimetry. Today's outcome is technical classification and benchmark design:

1. A technically accurate name for the approximation family.
2. The first missing physical effect for a radiating device near a body.
3. A small benchmark campaign with an agreed failure threshold.

If the discussion drifts, return to: "Gaat uw bezwaar over geldigheid binnen het afgebakende regime, over een toepassing buiten dat regime, of over nieuwheid?"

## Opening script

> Filip en ik hebben gisteren beslist dat de huidige patentindiening en IOF-case bij dosimetrie blijven. Vandaag toon ik de technische onderbouwing en de open validatievragen.

Pause after the three questions on the scope slide. Let Dries choose where to start if he immediately engages.

## Slide 1: AEGIS Surface Operator

Open with the observable and interface: AEGIS maps a given incident field and body surface to absorbed power.

If challenged immediately:

> Helemaal akkoord dat dit geen algemene Maxwell-solver is. Dat is ook niet de claim.

## Slide 2: Scope

This sets the context. Dries's input should sharpen the validity boundary and benchmark.

If he asks why the July email was broader:

> Dat was toen de open businessvraag. Die is intussen beslist. Uw technische input helpt ons de claimgrens en het validatieplan scherper te maken.

## Slide 3: Operator

Emphasize the interface. A field solver or ray tracer gives the illumination. AEGIS then maps that and the local body data to absorbed-power metrics. It does not solve induced currents everywhere.

Likely objection: "Then the expensive part is already solved."

Response:

> Soms wel voor één bronkarakterisatie. De winst komt wanneer dezelfde omgeving, body operator of pad-representatie voor veel body poses, tissue draws, beams of precoders hergebruikt wordt. Daarom rapporteren we zowel end-to-end als geamortiseerde rekentijd.

## Slide 4: Surface law

Name the three factors separately: incident power, local boundary transmission, and projected area. Then point at visibility as a separate test.

The positive part is not exact visibility. It only rejects back-facing local facets. On nonconvex bodies, self-occlusion needs a separate ray test.

Likely objection: "Physical optics near a shadow boundary is not uniform."

Response:

> Akkoord. De geometrical-optics gate is niet uniform nabij de terminator. Dat hoort in het diffractie-errorbudget of in een tussenmodel. De benchmark moet tonen wanneer die term de gereguleerde ruimtelijke gemiddelde waarde domineert.

Likely objection: "Your old wording said curvature features smaller than a wavelength."

Response:

> Die formulering was verkeerd. De gecontroleerde parameter is $1/(kR)$. De lokale kromtestraal moet groot zijn ten opzichte van de golflengte.

## Slide 5: Tissue response

Start from the polarization-aware expression. Present $T_0$ as an optional simplification for unpolarized high-loss tissue.

Likely objection: "This is just Fresnel."

Response:

> De lokale grenscoëfficiënt is standaard. De discussie gaat over de samengestelde dosimetrie-operator, de geldigheidsgrens en hergebruik over vele evaluaties. Fresnel-transmissie zelf is niet de nieuwheid.

Likely objection: "Angle-dependent transmission cannot be replaced by one average on a nonconvex body."

Response:

> Correct. Het exacte lokale model houdt $T_{\mathrm{eff}}(\theta, \mathrm{pol})$ per punt. $T_0$ is enkel een gecontroleerde vereenvoudiging.

## Slide 6: Operators

The incoherent form maps path powers. The coherent form adds fields before squaring. The local boundary assumption is the same.

Likely objection: "Differentiable with respect to what?"

Response:

> Algebraïsch, ten opzichte van continue parameters bij vaste pad- en schaduwtopologie. Bij het verschijnen of verdwijnen van paden of schaduwen is het harde model niet glad. Een gladde overgang kan dat regulariseren, maar universele end-to-end differentieerbaarheid claim ik niet.

## Slide 7: Coherence

The PSD property is structural, not independent physical validation. The useful result is that $Q$ is reusable for many precoders.

Likely objection: "$Q=G^H G$ being PSD is tautological."

Response:

> Ja. PSD is een consistentie-eigenschap en maakt optimalisatie mogelijk. Het valideert niet of de off-diagonale koppeling fysisch klopt. Dat heeft nog een coherente referentiebenchmark nodig.

Likely objection: "Depth phases differ by path."

Response:

> De huidige afleiding houdt de complexe TM-respons en dieptefase. Een mean-depth rank-one reductie geeft minder dan 0,05% verschil bij 28 GHz en minder dan 0,08% over de geteste band. Dat test de dieptereductie, niet de volledige oppervlaktebenadering.

## Slide 8: Evidence

Be explicit that the evidence is uneven. The method has Mie, local Fresnel and Sim4Life FDTD checks, but no blind anatomical 28 GHz device-to-body comparison. That gap is explicit.

If he attacks the 3.2% number:

> Dat getal vergelijkt de $T_0$-reductie lokaal met het volledige Fresnel-oppervlaktemodel onder 75 graden, niet met FDTD. Het is een reductiecheck.

If he says the Sim4Life checks are not enough:

> Akkoord. Ze ondersteunen de observable- en averaging-reducties, maar ze sluiten de near-body bronmodelvraag niet af.

## Slide 9: Validity

Do not defend an example outside the right-hand column. Ask Dries to identify which row fails and how to measure it.

Useful follow-up:

> Welke geometrie, bronafstand, frequentie, observable en fouttolerantie maakt die faalgrens ondubbelzinnig?

If he raises edge, cavity or creeping-wave counterexamples:

> Dat zijn echte tegenvoorbeelden voor een algemene solver. Ze liggen al buiten de huidige claimgrens. De vraag is of ze het dosimetrische ruimtelijke gemiddelde in de doelconfiguratie domineren.

## Slide 10: Device sources

A nearby device is not silently a plane wave. A spherical or Huygens representation can describe the source field. Source-body coupling is a separate test.

Likely objection: "The body changes the antenna, so your incident field is not given."

Response:

> Als die verstoring significant is, moet het bronveld samen opgelost worden en is AEGIS niet de standalone solver. Een goede benchmark zou de standoff moeten variëren en precies meten waar de eenrichtingsfactorisatie buiten tolerantie valt.

Likely objection: "Three wavelengths is not a universal boundary."

Response:

> Akkoord. De grens hangt af van de koppelingsfout voor de specifieke apertuur, het lichaam en de observable.

## Slide 11: Benchmark

Use a finite aperture over a layered curved patch as the third case. It is solvable with a reference and representative for the device-body regime.

Possible benchmark parameters to capture on the whiteboard:

- Frequency: 10, 28 and 60 GHz.
- Standoff: several points from clearly reactive to clearly radiative.
- Reference: FEM, FDTD, MoM or a differential surface-admittance formulation chosen by Dries.
- Outputs: local APD, peak 4 cm² APD, total absorbed power, source impedance change and runtime.
- Thresholds: decide before simulations, perhaps 5% integrated and 10% local.

Do not present those thresholds as settled. They are discussion anchors.

## Slide 12: Questions

Ask question 1 first and write down Dries's exact terminology. If he answers with "standard physical optics," ask which qualifier distinguishes the observable-specific and lossy-surface reduction.

Question 4 is tailored to his work. Ask whether a differential surface-admittance formulation could be a middle fidelity between the local Fresnel law and a volume solver while keeping reusable operator structure.

Only ask the adjacent-application question if the first four have concrete answers. Do not let it take over.

## Likely challenges

### "There is nothing new here"

> Bedoelt u dat de lokale fysica standaard is, dat de samengestelde dosimetrie-operator prior art is, of dat het validatieniveau onvoldoende is? Dat zijn drie verschillende bezwaren. Met welke referentie of formulering moeten we vergelijken?

Do not argue patent novelty from the slide deck. Ask for the closest technical formulation and capture it for Alessandro.

### "This cannot work in the near field"

> In het reactieve nabije veld akkoord. In het stralende nabije veld is de vraag of een eenrichtings-Huygens- of sferische veldrepresentatie plus lokale oppervlakterespons een observable-specifieke tolerantie haalt. Welke standoff-sweep zou dat duidelijk maken?

### "Your validation proves only trivial cases"

> De huidige checks tonen delen van de reductie. Ze sluiten de device-to-body case niet af. Ik zoek uw hulp om de kleinste niet-triviale blinde test te kiezen die dat wel doet.

### "Use BEM or differential surface admittance instead"

> Dat is misschien de juiste referentie of een tussenmodel. Mijn constraint is snelle herhaalde evaluatie van absorbed-power observables. Kan de surface-admittance operator eenmalig opgebouwd en hergebruikt worden over vele belichtingen of precoders, en tegen welke kost?

### "Generalize it to another market"

> Graag als aparte hypothese. Welke toepassing zou u eerst testen, en wat is de benchmark?

## Closing script

> Als ik het goed samenvat, noemt u dit [classificatie]. Voor de device-to-body case verwacht u dat [foutmodus] eerst domineert. De minimale test is [geometrie, bron, frequentie, grootheid, tolerantie] tegen [referentie]. Klopt dat?

Then ask who can help run or review the reference benchmark. Leave the meeting with named geometry, reference method and tolerance.
