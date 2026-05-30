# Spine — Closed-Form Absorbed-Power Dosimetry from~1~to~100\,GHz

_Stub written by the grinder. Re-derive with the `spine-architect` agent._

## Working abstract (extracted)

Regulatory dosimetry on the human body relies on Finite-Difference
Time-Domain (FDTD) simulation, which becomes prohibitive with meshes
up to $10^{12}$ cells at high mmWave frequencies.
We replace the simulation with a closed form derived from the
surface Fresnel law, accurate within the $7\%$ uncertainty from
variations in the tissue dielectric data. On a body mesh of $10^4$
triangles under $10^2$ incident paths, the absorbed-power map is one
matrix-vector multiply, evaluated in under $10$~ms on a modern GPU. Two observations make
this possible. First, a pseudo-Brewster compensation holds the
unpolarized Fresnel transmission within 5.6\% of its normal-incidence
value across $0^\circ$--$75^\circ$ on skin at 28~GHz. This places
biological tissue in the high-index regime of the optical-substrate
literature. Second, the local law integrates over the body mesh into
a generalized Cauchy formula. The formula extends the classical
convex projected-area identity to nonconvex absorbers. An
ambient-occlusion pass on the mesh evaluates the self-shadowing
factor. A layered Fabry--P\'erot correction in subcutaneous fat
captures the residual below 6~GHz. The closed form matches Mie theory
on lossy spheres, full polarization-aware Fresnel on the Thelonious
phantom within $1.2\%$ direction-averaged on total absorbed power,
Sim4Life FDTD at 5.8~GHz, and the dosimetry literature across 168
volunteers and 5 FDTD phantoms. It
holds quantitatively from 1--100~GHz on whole-body quantities and
from 6--100~GHz pointwise on the surface. Whole-body compliance
reduces to only three precomputed scalars.
Antenna and beam optimization under exposure constraints become
differentiable end-to-end.

## Section spine

### §1. Introduction
- label: `sec:introduction`
- purpose: _<fill in>_
- gap statements: _<fill in>_

### §2. Local absorption law
- label: `sec:law`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §2.1 Setup
  - §2.2 Power flux through the surface
  - §2.3 Fresnel coefficients
  - §2.4 Polarization-aware exact law

### §3. Pseudo-Brewster compensation
- label: `sec:pB`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §3.1 Mechanism
  - §3.2 Quantitative behavior across angle
  - §3.3 Tissue universality
  - §3.4 Frequency dependence
  - §3.5 Geometric absorption law
  - §3.6 Discrete multi-source form

### §4. Whole-body absorbed power
- label: `sec:cauchy`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §4.1 Self-shadowing and ambient occlusion
  - §4.2 Generalized Cauchy formula
  - §4.3 Layered transmission below 6~GHz

### §5. Validation
- label: `sec:val`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §5.1 Setup
  - §5.2 Mie theory on lossy spheres
  - §5.3 Full Fresnel on the Thelonious phantom
  - §5.4 Sim4Life FDTD on the Thelonious phantom
  - §5.5 Combined dosimetry literature

### §6. Higher-order corrections
- label: `sec:corrections`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §6.1 Curvature
  - §6.2 Diffraction at the shadow boundary
  - §6.3 Inter-body reflections
  - §6.4 Error budget

### §7. Compliance and corollaries
- label: `sec:compliance`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §7.1 Whole-body SAR threshold
  - §7.2 Peak spatial-average SAR over a 10~g cube

### §8. Discussion
- label: `sec:disc`
- purpose: _<fill in>_
- gap statements: _<fill in>_
  - §8.1 Computational structure
  - §8.2 Regulatory implications
  - §8.3 Regime of validity
  - §8.4 Future directions

### §9. Conclusion
- label: `sec:conc`
- purpose: _<fill in>_
- gap statements: _<fill in>_

### §10. Acknowledgment
- purpose: _<fill in>_
- gap statements: _<fill in>_
