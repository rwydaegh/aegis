# Prior-art analysis: Kapetanović PhD thesis (University of Split, 2023) vs AEGIS

*Extracted 2026-05-27 by an Opus agent that read the full 147-page thesis (`Doktorski rad-za objavu -Ante.pdf`), with citation-level detail. This is the closest prior art to AEGIS's differentiable mmWave-dosimetry claims. Source: A. Lojić Kapetanović, "Advanced Technique for Assessment of Spatially Averaged Dosimetric Quantities on Nonplanar Surfaces", FESB, University of Split, 2023 (advisor D. Poljak). Public code: github.com/akapet00/EMF-exposure-analysis.*

## TL;DR for the patent (read this first)
- **It is NOT a closed-form solver.** It is a numerical *post-processor* that spatially-averages an externally-computed full-wave/BEM/FDTD field over curved surfaces (Gauss quadrature). It always needs an expensive field solve first, and reports **no speed figures**. AEGIS's closed-form millisecond evaluation is genuinely different.
- **Cannot claim the transmission-coefficient idea:** `Sab = T·Sinc` with `T = 1 - |Γ|²` (Fresnel) is **explicitly in the thesis** (eqs. 3.9-3.10), incl. a figure of T rising with frequency. Treat as prior art.
- **"Pseudo-Brewster near-constant T0" is NOT anticipated.** The thesis uses normal-incidence T only and treats Brewster as an *angle* effect, concluding normal incidence is worst-case. AEGIS's near-constant-T0-plateau framing is defensible.
- **ReLU-cosine: conceptual analogue exists** (a Heaviside step + linear taper integrand mask, eqs. 4.36-4.39), but not as a closed-form `Sinc·T0·ReLU[...]` product. Frame the novelty as the closed-form analytical product, not "rectify the cosine".
- **"Differentiable JAX dosimetry" loosely is anticipated** (they AD a neural-net current surrogate to smooth a gradient), so don't lead with it. **But** the end-to-end *differentiable beamforming/antenna-optimization loop*, the **coherent MIMO exposure operator**, and the **spherical-harmonic antenna/body decoupling** are all absent -> white space.
- **Curvature-underestimation is established prior art** (sphere up to ~12% normal / ~28-31% worst-case, ear ~20%, cylinder ~4.4% vs flat). AEGIS's "non-planar Sab matters" is not novel as a claim, though it is useful validation context.

## Collaboration / strategic note
Likely **collaborator, not competitor**: they solve the inverse problem (average expensive fields onto curved anatomy) and AEGIS could feed them a fast surrogate. Split itself is not a prestige host, but the thesis is a gateway to two things that are strategically valuable: (1) **IEEE ICES TC95 SC6 WG6**, the committee writing the future curved-surface averaging rules AEGIS must map to (the author/advisor are active there); and (2) a named tie to **IETR Rennes (Maxim Zhadobov, Giulia Sacco)** on the realistic-ear APD paper. A defensive co-authorship would also neutralise the prior-art overlap.

---

(Full agent report below.)

# Prior-art / competitive assessment: Kapetanović PhD thesis vs AEGIS

**Document:** Ante Lojić Kapetanović, *"Advanced Technique for Assessment of Spatially Averaged Dosimetric Quantities on Nonplanar Surfaces"*, Doctoral Thesis, University of Split (FESB), 2023. Supervisor: prof. dr. sc. Dragan Poljak. 147 pages, English, multi-paper format built around 4 published journal papers.

## 1. What the thesis actually does
The core problem is **spatial averaging of dosimetric quantities (incident power density IPD and absorbed/epithelial power density APD) over curved body surfaces, in the 6-300 GHz range**, where standards prescribe averaging over a flat 4 cm² (and 1 cm² above 30 GHz) plane. Thesis claim: flat planes underestimate exposure when local curvature radius is comparable to the wavelength.

It is **not** a field solver and **not** a closed-form surface formula. It is a **post-processing numerical surface-integration technique** on top of an externally computed EM field:
- **Field source:** Galerkin-Bubnov indirect Boundary Element Method (MoM-type integral-equation solver) on a half-wave dipole via the Pocklington equation; FDTD reviewed as the field "standard of choice". Solver-agnostic averaging step.
- **Quantities:** spatially averaged IPD, APD/TPD, SAR below 6 GHz; both "normal" and "norm" Poynting-flux averages.
- **Geometries:** sphere (head r=9cm), cylinder (finger/limb), anatomical ear model, realistic head point cloud (63,333 pts). Plane-wave and dipole sources; one patch-array + inverted-F superposition study.
- **Numerical machinery:** surface normals on point clouds via PCA / weighted moving least squares + MST orientation propagation; conformal averaging region = surface ∩ sphere of radius r_av, reprojected in a PCA basis; surface integral by 2-D Gauss-Legendre (canonical) or adaptive Gauss-Kronrod (anatomical). Automated "hot-spot" detection via iterated PCA + hidden-point-removal.
- **Differentiability (narrow):** in one paper, the BEM dipole current is fit by a small feed-forward NN (3 layers, tanh, Adam) in **JAX** (XLA JIT), and autodiff is applied to that surrogate to smooth the current-gradient (artefact removal). **Not** a gradient-based design/optimization loop.

## 2. Stated novelty / contributions (Ch. 1.3, pp. 5-6)
1. Novel realistic non-planar body models (sphere/cylinder/ear) to supersede planar models above 6 GHz.
2. Automated PCA-based "hot-spot" detection from unstructured point clouds.
3. Rigorous surface-integral definitions of averaged APD/IPD + an efficient numerical surface-integration technique independent of the field-simulation method.
Plus the claim that hybridizing ML + numerical methods via "differentiable programming" aids EMF modeling.

## 3. Validation
- Curvature effect: sphere up to ~12% (normal def) / ~28-31% worst case higher than flat; cylinder ~4.4%; curvature paper ~15%; ear spatial-max APD ~20% higher than flat.
- Validation references: ear paper verified vs "two commercial EM software" (unnamed); cross-definition checks; **no Mie analytical validation, no own measurements**.
- APD volumetric (TPD) vs surface (Poynting) definitions differ **< 6%** (shallow penetration).
- **Speed: not reported anywhere** (no ms-scale, no wall-clock). Cost discussed only qualitatively. Code public on GitHub.

## 4. Direct comparison: thesis vs AEGIS
| Dimension | Kapetanović thesis (2023) | AEGIS |
|---|---|---|
| Method type | Numerical post-processor: quadrature surface-integration of an externally computed field (BEM/MoM or FDTD) | Closed-form analytical `Sab = Sinc·T0·ReLU[n̂·(-k̂)]` per surface point |
| Speed | Not reported; relies on heavy full-wave/BEM front-end | Milliseconds (closed-form) |
| Differentiability | JAX AD of a NN current-surrogate to smooth a gradient; not a design loop | Fully differentiable end-to-end for exposure-aware beamforming/antenna optimization |
| Quantities | IPD, APD/TPD, SAR (normal & norm) | Sab and incident PD |
| Geometries | Sphere, cylinder, anatomical ear, head point cloud | Full-body 3D phantoms |
| Frequency | 6-300 GHz (some from 3.5 GHz) | ~100 MHz-300 GHz |
| Near-field | Defers to BR in reactive NF; BEM-solves dipole NF | Radiating-NF extension via spherical-harmonic antenna/body separation |
| MIMO/beamforming | None (one superposition study) | Coherent massive-MIMO exposure operator Q |
| Validation ref | Two commercial solvers (ear); cross-definition | Analytical lossy-sphere (Mie) |

## 5. Prior-art assessment
**Anticipates (overlap):** non-planar Sab/IPD and the curvature-underestimation thesis (quantified); spatial averaging on curved surfaces with conformal regions + surface normals; local-normal dependence of absorbed flux (parallels `n̂·(-k̂)`); **differentiable mmWave dosimetry with JAX** in the loose sense.

**Touches AEGIS's physics core?**
- **Transmission coefficient: YES.** `S(z=0) = T·IPD`, `T = 1 - |Γ|²` (eqs. 3.9-3.10); figure of T into dry skin rising ~0.45 (1 GHz) to ~0.85 (100 GHz). So `Sab ≈ T·Sinc` with frequency-dependent Fresnel T is in the thesis.
- **Pseudo-Brewster / near-constant T0: NO** (term absent; "Brewster" only as an angle effect, normal incidence = worst case).
- **ReLU / rectified cosine: NOT as a formula** — closest is a Heaviside step Θ + linear taper integrand mask (eqs. 4.36-4.39), conceptually adjacent but not a closed-form `Sinc·T0·ReLU[...]` product.

**Does NOT cover (AEGIS white space):** the closed-form solver-free millisecond predictor as a single analytical product; millisecond speed; the near-constant pseudo-Brewster T0 framing; the coherent MIMO exposure operator Q; the spherical-harmonic antenna/body decoupling; gradient-based exposure-aware beamforming/antenna optimization.

## 6. People & network
- **Author:** Ante Lojić Kapetanović (FESB Split; the JAX/software/methodology lead).
- **Advisor:** Dragan Poljak (FESB Split; senior computational-EM, BEM/MoM).
- **External co-authors:** **Maxim Zhadobov & Giulia Sacco — IETR, Rennes** (named on the realistic-ear APD paper); Mario Cvetković & Hrvoje Dodig (Split).
- **Standards:** oriented to **IEEE ICES TC95 SC6 WG6** (averaging schemes for spatially averaged power density on non-planar surfaces).
- **Funding:** ERDF grant KK.01.1.1.01.0009 (DATACROSS). **Code:** github.com/akapet00/EMF-exposure-analysis (public).

## 7. Bottom line
Likely **collaborator, not competitor** (they solve the inverse problem; AEGIS could feed a fast surrogate). Strategic value: standards credibility (ICES TC95 SC6 WG6) + a line to IETR Rennes. Treat as prior art: non-planar Sab, curvature underestimation, spatial averaging on curved surfaces, the `T = 1-|Γ|²` transmission relationship, and loose "JAX differentiable dosimetry". Frame AEGIS patent novelty tightly around: (a) closed-form solver-free millisecond evaluation as a single analytical product, (b) near-constant pseudo-Brewster T0 characterization enabling it, (c) the coherent MIMO exposure operator, (d) the spherical-harmonic antenna/body decoupling, (e) the end-to-end differentiable beamforming/antenna-optimization loop.
