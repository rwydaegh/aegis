# GOLIAT + AEGIS: synergy report

## The two tools

**AEGIS** -- closed-form geometric dosimetry. Computes absorbed power density (S_ab) on body surfaces in milliseconds. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming. Works above ~6 GHz where surface power density is the right metric. 28K lines Python, 14K lines TypeScript, deployed 3D viewer.

**GOLIAT** -- fully automated Sim4Life FDTD wrapper. Computes volumetric SAR (whole-body, psSAR10g per tissue group) through the full Sim4Life pipeline. Near-field (phone-to-head), far-field (plane waves), and MaMIMO beamforming scenarios. 42K lines Python, PySide6 GUI, oSPARC cloud runner. Won a Sim4Life competition. Not public.

Both use the same ViP phantoms (Duke, Ella, Thelonious, Eartha). Both target the same regulatory standards (ICNIRP 2020, IEC 63195-2). Both are sole-authored by Robin.

---

## The frequency gap

AEGIS is fast because it treats the body as a surface. That works when penetration depth is shallow (above ~6 GHz, skin depth < 1 mm). Below 6 GHz, RF penetrates deep into tissue. The compliance metric switches from S_ab (W/m^2) to psSAR10g (W/kg), which requires volumetric field solutions. No geometric shortcut gets you there. You need FDTD or something equivalent.

This is not a weakness to paper over. It is a product opportunity.

---

## Synergies

### 1. Frequency-aware unified dosimetry

The combined product covers the full spectrum:

- Above 6 GHz: AEGIS engine, milliseconds, S_ab and spatial-average S_ab
- Below 6 GHz: GOLIAT/FDTD engine, minutes, psSAR10g and whole-body SAR

The user does not pick an engine. They specify a scenario (frequency, antenna, body). The system selects the right method. One API, one viewer, one result format. This is the core product proposition: **complete regulatory dosimetry from 450 MHz to 100 GHz, with the fastest method physics allows at each frequency**.

### 2. Validation campaign (the Wout comparison)

Run matched scenarios through both pipelines at overlapping frequencies (2-6 GHz range where both methods produce results). Quantify AEGIS accuracy vs. FDTD ground truth at each fidelity level. This produces:

- The accuracy-vs-speed tradeoff curve for the monograph
- Confidence intervals for AEGIS predictions
- Identification of failure modes (where does the geometric approximation break down?)
- Publication-ready figures comparing S_ab (AEGIS) vs. SAPD extracted from FDTD (GOLIAT)

GOLIAT already extracts SAPD (IEC 63195-2:2022) on skin surfaces, which is the same physical quantity as AEGIS S_ab. Direct comparison is straightforward.

### 3. AEGIS as pre-screener for expensive FDTD

For MaMIMO campaigns with thousands of possible beam configurations, running FDTD on all of them is prohibitive. Instead:

1. AEGIS level 7/8 screens all configurations in seconds
2. Identifies top-N worst-case exposure scenarios
3. GOLIAT validates only those N scenarios with full FDTD

Reduces compute from days to hours. Defensible in a regulatory context because the screening is conservative (geometric methods overestimate at grazing angles).

### 4. Hybrid spatial resolution

AEGIS gives you the spatial exposure map fast. GOLIAT gives you accurate volumetric fields slowly. A hybrid:

1. Run AEGIS to get the body-surface exposure map
2. Identify hotspot regions (highest S_ab triangles)
3. Run a focused FDTD (smaller computational domain, just the hotspot region) through GOLIAT
4. Get precise psSAR10g at the hotspot without simulating the entire body

This is novel and publishable.

### 5. Shared scenario format

Both repos define scenarios differently. A common scenario spec (frequency, antenna type/position, body model, polarization) that both pipelines consume would enable trivial A/B comparisons. This could be a simple JSON schema in a shared package.

---

## The Sim4Life dependency question

GOLIAT requires a Sim4Life license. Three paths forward:

**A. Keep Sim4Life as the FDTD backend.** Simplest. GOLIAT already works. ZMT/Speag is a potential licensing partner (Wout suggested this). The spin-off licenses AEGIS; customers who need sub-6 GHz bring their own S4L license or pay for cloud FDTD runs.

**B. Replace Sim4Life with an open-source FDTD.** Options: gprMax, openEMS, MEEP. Eliminates the license dependency but requires significant validation work. GOLIAT's value becomes the automation/extraction logic, not the solver.

**C. Build a minimal FDTD in JAX.** A coarse-grid FDTD just sufficient for psSAR10g, running on GPU via JAX. Differentiable end-to-end (like AEGIS already is with JAX). GOLIAT serves as the reference implementation to validate against. Biggest build, biggest payoff: no external dependency, GPU-accelerated, differentiable dosimetry across the full spectrum.

Option A for launch. Option C for the long-term moat. Option B is the pragmatic middle ground.

---

## What this means for the spin-off

The combined AEGIS+GOLIAT story is stronger than AEGIS alone:

- **Full spectrum coverage** removes the "but what about sub-6 GHz?" objection from every customer conversation
- **GOLIAT's competition win** and existing validation against published data adds credibility
- **Two engines, one interface** is a defensible product architecture (competitors would need to build or buy both)
- **The validation campaign** (synergy 2) is also a paper, which feeds the academic track

For imec.istart (October 2026 deadline): "We have two validated dosimetry engines covering 450 MHz to 100 GHz, unified behind a single API and 3D viewer" is a stronger pitch than AEGIS alone.

---

## Next steps

1. Define 5-10 matched scenarios at overlapping frequencies (2, 3.5, 6 GHz) for the validation comparison
2. Design the common scenario JSON schema
3. Run the comparison, produce the accuracy-vs-speed figures
4. Write it up for the monograph and as a standalone paper
5. Decide on the Sim4Life dependency path (A/B/C) based on spin-off timeline
