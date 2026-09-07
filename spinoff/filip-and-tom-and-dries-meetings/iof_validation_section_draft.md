# AEGIS dosimetry validation and industrial proof of concept

## Objective and intended use

The project will determine whether AEGIS can serve as a fast, auditable pre-screening and design-optimisation layer for peak spatial-average absorbed power density (APD) in the radiating-field regime. AEGIS will screen large sets of antenna, beam, distance, and body-position configurations. Cases near the compliance limit or outside the validated domain will be escalated to qualified FDTD/FEM simulation or physical measurement.

The initial product claim is deliberately narrower than final certification. It excludes reactive-near-field coupling, source detuning by the body, deep-tissue quantities, and whole-body absorbed power unless those outputs pass separate validation gates. The target quantity is peak APD averaged over 4 cm² and, above 30 GHz, 1 cm², initially over 10 to 60 GHz. This matches the direction of the active [IEEE/IEC P63195-4 computational APD project](https://standards.ieee.org/ieee/63195-4/11782/) without presuming that AEGIS is already a standardized conformity method.

## Starting evidence

AEGIS already has analytical verification against Fresnel and Mie reference problems, comparisons with published volunteer and anatomical-phantom studies, and a preliminary Sim4Life intercomparison. In three completed 7 GHz anatomical plane-wave cases, the AEGIS to FDTD ratio for peak 4 cm² APD was 1.057, 1.196, and 0.830, with a direction-averaged ratio of 1.027.

This is promising but not yet industrial validation. The same campaign did not validate total absorbed power, only one polarization and three directions completed, and no blind 28 GHz device-to-body benchmark or physical APD measurement has been performed. These gaps define the work package. They do not require a new scientific principle to be invented.

## Why validation is feasible within the IOF project

The required reference chain already exists:

- Analytical half-space, layered-medium, and Mie solutions can verify the implementation independently of AEGIS.

- Qualified FDTD/FEM tools can provide converged numerical references with matched geometry, dielectric data, excitation, and APD averaging. [IEC/IEEE 63195-2](https://webstore.iec.ch/en/publication/62754) already defines the verification discipline for computational incident power density, while P63195-4 is extending the framework to absorbed power density.

- Traceable APD phantoms, sources, and measurement systems are commercially available. Current DASY APD systems cover the relevant FR2 and FR3 bands and report expanded measurement uncertainty around 1.5 to 1.7 dB, which provides a realistic basis for an uncertainty-aware acceptance test. See the [SPEAG APD validation description](https://speag.swiss/news-events/news/measurement/dasy8-module-apd-v1) and its [2026 accredited calibration scope](https://speag.swiss/news-events/news/measurement/2026/speag-lab-expands-iso-17025-accreditation-to-apd-probe-and-dak-r-calibrations).

- AEGIS already contains the physics kernels, anatomical meshes, solver bridges, automated tests, and reproducible result pipeline needed to run a structured benchmark campaign. The project therefore funds maturation, independent evidence, and a bounded model domain rather than speculative software construction.

## Activities, deliverables, and success criteria

### Task 1: Freeze the claim and verification protocol, months 1 to 2

Define the intended-use domain, input requirements, excluded regimes, APD averaging implementation, calibration cases, and blind holdout cases. Freeze software, phantom, dielectric-data, and reference-solver versions before model tuning.

Deliverable: a preregistered validation protocol and standards-aligned benchmark corpus.

Success criteria: analytical quantities reproduce their reference values within 0.1%, reference-field and APD post-processing within 0.5%, and remeshing or backend changes alter results by no more than 1%.

### Task 2: Qualify the numerical references, months 1 to 4

Run grid, domain, boundary, and convergence studies in Sim4Life, with an independent FEM or FIT implementation on a representative subset. Verify accepted, reflected, and dissipated power separately. A simulation is admitted as a reference only when remaining numerical uncertainty is quantified.

Deliverable: qualified full-wave reference models and an uncertainty report.

Success criteria: power-balance residual at most 3% for anatomical cases, remaining grid sensitivity at most 5%, and expanded numerical uncertainty at most 10%.

### Task 3: Blind model-form validation, months 3 to 9

Compare AEGIS with the qualified references on canonical bodies and anatomical phantoms at 10, 28, 40, and 60 GHz. Thelonious will be used for development. Duke, Ella, and Eartha will serve as holdouts. The campaign will cover multiple incidence directions, polarizations, source distances, and antenna or beam states. A separate 7 GHz diagnostic series will resolve the current transition-frequency discrepancy.

Deliverable: a blind benchmark report covering APD values, surface maps, hotspot location, worst-case ranking, runtime, and domain failures.

Proposed project gates, which are not claimed as normative IEC limits:

- Median bias for peak 4 cm² APD within 0.5 dB.

- At least 90% of blind scenarios within 1.0 dB, with no declared subgroup showing median bias beyond 1.0 dB.

- At least 95% recall of the full-wave top-ranked worst cases and no false clearance in the preregistered test set after applying the uncertainty guard band.

- At least 100-fold end-to-end speed-up on a matched screening task, including preprocessing but excluding reference cases that AEGIS explicitly escalates.

### Task 4: Independent measurement validation, months 6 to 12

Freeze AEGIS predictions before receiving results from a qualified external laboratory. Use a traceable APD phantom and at least six characterized sources near 28 GHz, with multiple separations, orientations, and polarizations. Record dielectric properties, source power and pattern, registration uncertainty, repeatability, and spatial APD maps.

Deliverable: an external blind measurement report and a GUM-style uncertainty budget.

Success criterion: normalized error

$$
E_n = \frac{|y_{\mathrm{AEGIS}} - y_{\mathrm{meas}}|}
{\sqrt{U_{\mathrm{AEGIS}}^2 + U_{\mathrm{meas}}^2}}
$$

does not exceed one in at least 90% of primary cases, with no systematic bias outside the combined expanded uncertainty.

### Task 5: Industrial proof and valorisation gate, months 9 to 24

Run paid or co-funded pilots with device, chipset, test-lab, or solver partners. Measure the number of full-wave cases avoided, worst-case recall, engineering turnaround time, reproducibility, integration effort, and willingness to pay. Prepare a versioned validation dossier and submit the evidence for technical review in the P63195-4 process.

Deliverables: two industrial pilot reports, one external replication, a standards contribution, and a documented licence or spin-off decision.

Commercial success criterion: at least two paid pilots, or one paid pilot and one signed embedded-licence or OEM evaluation agreement, before committing to full product scale-up.

## Risks and fallback positions

If the blind tests fail globally but pass in a stable subset, the product claim will be restricted by frequency, source distance, geometry, or excitation. If hotspot ranking succeeds but absolute APD accuracy does not, AEGIS will remain a prioritisation tool and every result will require full-wave escalation. If reactive coupling or source detuning dominates, those device classes will be excluded.

Failure of the total-power gate removes total absorbed power and whole-body SAR from the product claim. Failure of both the APD accuracy and ranking gates stops the commercialisation route. These fallbacks make the project decision informative even if the broadest technical claim does not survive.

## Investment proportionality

The IOF investment is EUR 250,000 over two years. It buys a qualified benchmark set, independent numerical and measurement evidence, an uncertainty-bounded product claim, industrial pilots, and a licence or spin-off decision. A specialist business reaching EUR 1 million in recurring revenue would already represent a credible return relative to that investment. The larger EUR 5 to 7 million outcome requires enterprise workflow contracts and embedded distribution, and is treated as scale potential rather than a condition for starting the validation project.
