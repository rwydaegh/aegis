# Orchestrator note: the thermal-diffusion reality check on Finding C(a)

Written 2026-07-09 by the orchestrating agent, independent of agent 10 (which runs the deep version).
Script: `scratchpad/thermal.py`. Skin properties: k=0.37 W/m/K, rho=1109, c=3391, so
alpha = 9.84e-8 m^2/s.

## The claim under test

Finding C(a): an agile array paints a diffraction-limited coherent hotspot (~0.9 cm^2 at 28 GHz)
that the 4 cm^2 spatial averaging window cannot see, so the array is "compliant on paper,
non-compliant in reality." The APD area-dilution factor is 4 cm^2 / 0.9 cm^2 = **4.44x**, and that
is the number the electromagnetic framing implicitly reaches for.

## Why the EM number overstates the hazard

The standard restricts APD as a proxy for temperature rise. Peak steady-state temperature under a
uniform-flux disc source of radius a, at fixed *total* power, scales as dT ~ 1/a, not 1/a^2, because
lateral conduction spreads the heat. So concentrating the same power into a smaller disc raises peak
dT only as the *radius* ratio, not the *area* ratio.

- Area (APD) dilution, 4 cm^2 vs 0.9 cm^2:  **4.44x**  (what the compliance number reports)
- Radius (thermal) penalty, a_std/a_hot:    **2.11x**  (what the tissue actually feels)

So the true peak temperature under a 0.9 cm^2 hotspot is about **2.1x** the temperature the 4 cm^2
compliance figure implies, not 4.4x. The honest headline is a ~2x thermal under-report at 28 GHz
with the 4 cm^2 window, not an order of magnitude.

## And the gap is self-closing with frequency

The hotspot cannot beat the diffraction limit: spot area ~ pi (lambda/2)^2.

| Carrier | diffraction spot | ICNIRP window | thermal under-report |
|---|---|---|---|
| 10 GHz | ~7.1 cm^2 | 4 cm^2 | < 1 (spot bigger than window: no gap) |
| 28 GHz | ~0.90 cm^2 | 4 cm^2 | ~2.1x |
| 95 GHz | ~0.08 cm^2 | **1 cm^2** (>30 GHz rule) | **~1.05x** |

Above 30 GHz ICNIRP already shrank the averaging window to 1 cm^2, which tracks the shrinking
diffraction spot and closes the gap to ~5%. Below ~15 GHz the diffraction spot is larger than the
4 cm^2 window, so there is no sub-resolution hotspot to hide. The window that a gap could live in is
roughly **15-30 GHz**, and even there it is a factor of ~2, bounded.

To get a 10x thermal under-report you would need a 0.04 cm^2 spot (a=1.1 mm), which requires
lambda ~ 2 mm, i.e. ~150 GHz, where the 1 cm^2 (or tighter) window would already apply. The standard's
averaging is not naive. It was, to first order, designed around exactly this thermal-diffusion length.

## Consequence for the study

Finding C(a) survives but shrinks hard. It is a **real ~2x effect in a narrow 15-30 GHz window**, not
a 50x scandal. That is:
- Still a legitimate, publishable **standards observation** (the 4 cm^2 window slightly under-protects
  against a coherent near-field-focused or on-body-focused beam in a specific band), especially since
  the standards rationale assumed the source is always larger than the window, which a large coherent
  array focusing on a body violates.
- **Not** a "death ray the regulator is blind to." Robin should not pitch it that way and would lose
  credibility with Hirata/Kuster/ICES if he did.
- The temperature caveat matters because the standards community (Foster, Ziskin, Neufeld, Kuster)
  reasons in temperature, not APD. Any claim framed in APD area ratios will be corrected to the radius
  ratio in the first review, and the story must lead with the ~2x thermal number to be taken seriously.

The steady-state disc model is a bound, not the last word (a real body has blood perfusion, a finite
6-minute window, and a curved surface). Agent 10 does the transient Pennes version and reads the ICNIRP
rationale document. But the order of magnitude here is robust: **~2x, band-limited, not 50x.**
