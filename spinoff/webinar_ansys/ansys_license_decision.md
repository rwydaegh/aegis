# Ansys Perceive EM license for IOF: should we buy it?

Decision note, 2026-05-24. Follows from the Ansys "Enabling 6G Technologies" webinar
(`transcript.md`, `slides.pdf`). Question on the table: get an Ansys Perceive EM
license for the IOF project, given we currently do channels with Sionna.

## TL;DR

- For IOF, yes, the **Academic Research HF bundle at 3,300 EUR/year is worth it**, and the
  cost is noise inside an IOF budget. Buy it as a high-fidelity validation oracle and a
  credibility anchor, not as a replacement for Sionna in the pipeline.
- Do **not** rip Sionna out. Sionna stays the in-product backend. Perceive EM is the
  reference you validate against and the name you cite.
- Skip the STK RF Channel Modeler at 5,374 EUR. It is GUI convenience on top of the same
  solver. We do not need it.
- Send one email anyway. Ask about the **Startup Program** (commercial use, possible free
  first year) so the BV path is mapped before we incorporate. Different license, different
  use rights, see below.

## What Perceive EM actually is

GPU shooting-and-bouncing-rays channel and radar solver, delivered as a C++/Python API
library (data on demand). The differentiator is that it is **Physical Optics based, not
GO/GTD** (slide 25, ~37:51): it induces equivalent surface currents and propagates fields
with Green's functions instead of carrying energy on abstract rays. That buys accurate
scattering on detailed low-reflectivity geometry, near-field validity where no specular
path exists, and million-facet scenes with no pre-simplification. Real-time on one GPU,
25M+ channels in a run. Being wired into NVIDIA Omniverse and the AODT 6G platform
(slides 29-32).

## Why it could matter for IOF

1. **Validation oracle.** We need independent, high-fidelity channels to benchmark the
   AEGIS H-matrix to S_ab path, especially at mmWave and in the near field. PO ground truth
   is stronger evidence than checking one ray tracer against another that shares the same GO
   assumptions. This is the H5 validation chapter and any TAP/TWC reviewer's first question.
2. **Near-field fidelity.** The whole near-field spin-off pivot leans on the claim that
   near-field exposure is where the physics gets interesting. Perceive EM's PO core is valid
   in exactly that regime. Validating against it is on-message.
3. **Credibility.** "Validated against Ansys Perceive EM" is a sentence that lands with
   IEC/standards people, Sven Kuhn's world, and the IOF jury. It also reframes the pitch:
   the channel foundation is being built by Ansys and NVIDIA, AEGIS is the exposure and
   compliance layer that plugs into it. Integration story, not competition story.
4. **Cost is trivial.** 3,300 EUR/year is rounding error in an IOF StarTT budget. The only
   real cost is the time to wire up a second comparison path.

## Perceive EM vs Sionna, honestly

"Probably better" is half right. It is better on some axes and worse on the ones that map
to our moat. Be specific:

| Axis | Sionna RT | Ansys Perceive EM |
|---|---|---|
| Cost | Free, Apache-2.0 | 3,300 EUR/yr academic, non-commercial |
| Physics | GO + basic diffraction/scatter | Physical Optics, radar-grade scattering |
| Near field | Weak (GO assumptions) | Strong (PO, Green's functions) |
| Scene scale | Good, limits at very high facet counts | Millions of facets, no pre-simplification |
| Speed | GPU, fast | GPU, real-time, faster at scale |
| **Differentiable** | **Yes** (gradients through the tracer) | **No** |
| Openness / embeddable | Open, ships inside our product | Closed, license, cannot embed in the SaaS |
| Already integrated | Yes (plus DiffeRT) | No, new backend to wire up |
| ML / research ecosystem | Huge | Smaller, but the AODT tie-in is growing |

The two that decide it:

- **Differentiability.** Sionna is differentiable, Perceive EM is not. Our whole USP is the
  differentiable design loop. If we ever optimize *through* the tracer (scene, placement),
  that path runs on Sionna or DiffeRT, never on Perceive EM. So Perceive EM cannot be the
  pipeline backend even if we wanted it to be.
- **Licensing wall.** Academic Research is non-commercial. For IOF (a UGent research
  project) that restriction does not bite. For the BV's product it bites hard, and the
  license forbids shipping it inside the SaaS anyway.

So the role is clean: **Perceive EM is the high-fidelity referee, Sionna and DiffeRT are the
players.** Use it to check our work and to say we checked it, not to run the product.

## Pricing and licensing reality

| Product | Program | Price | Use rights |
|---|---|---|---|
| Perceive EM (in HF bundle) | Academic Research | 3,300 EUR/yr | Non-commercial only |
| STK RF Channel Modeler | Academic Research | 5,374 EUR/yr | Non-commercial only |
| Perceive EM (in a bundle) | Startup Program | not quoted, **guess ~6-10K EUR/yr**, possibly free first year | Commercial, eligibility-gated |
| Perceive EM | Education / Student | ~free | Learning only, capped |

The three "packages" Carpenter names on slide 22 (~30:26) are separate programs, not tiers
of one price. The startup figure is a guess interpolated between the academic floor and full
commercial seat cost (tens of thousands), so treat it as a rough order of magnitude. Ansys
does not publish it.

For IOF the answer is the **Academic Research line, 3,300 EUR**. The startup question is a
later, BV-side concern, but worth asking now while we are already in contact.

## Recommendation

1. Acquire the **Academic Research HF bundle (3,300 EUR/yr)** under the UGent/IOF umbrella.
   Skip the 5,374 EUR RF Channel Modeler.
2. Keep Sionna and DiffeRT as the product backends. Add Perceive EM as a third path used for
   validation and benchmarking only.
3. In the same outreach, ask Ansys about the Startup Program: eligibility caps, what is in
   the HF startup bundle, whether there is a free or subsidized first year, and the
   commercial-use terms. That maps the BV path before we incorporate.

## Open questions to settle in the email

- Is Perceive EM actually in the Startup Program bundle, and at what price?
- Is there a free or discounted first year for early-stage companies, and what are the
  age/revenue caps?
- Does the academic license allow publishing validation results that compare against it?
- Can the academic eval start now, and how long is the eval window before we commit budget?

## Draft email

> Subject: Ansys Perceive EM, academic research license and startup program
>
> Hi [name],
>
> Thanks for the quote. For my PhD and an upcoming IOF research project at UGent
> (WAVES, IMEC), the Academic Research HF bundle with Perceive EM at 3,300 EUR/year
> looks like the right fit, mainly as a high-fidelity reference for validating our own
> dosimetry channel models. A few questions before I confirm budget:
>
> 1. Can I start an evaluation now, and how long is the eval window?
> 2. Does the academic license permit publishing results that benchmark our method
>    against Perceive EM (TAP/TWC papers, PhD)?
> 3. Separately, I am spinning off a company from this work. Is Perceive EM available
>    through the Ansys Startup Program, and if so what is the pricing, the eligibility
>    (company age / revenue), and is there a free or reduced first year?
>
> Happy to hop on a call.
>
> Best,
> Robin

## Caveats

The startup price is a guess, not a quote. Eligibility for the Startup Program is gated and
unverified. Sionna's exact accuracy gap versus Perceive EM in our specific mmWave/near-field
cases is an empirical question, which is itself a reason to run the comparison rather than
assume the direction.
