# Diffraction exactness: what the exact cylinder oracle says

Date: 2026-06-08
Oracle: exact 2D plane-wave scattering by a homogeneous cylinder (lossy
dielectric = skin at 28 GHz, and PEC), Bessel-Hankel series, no asymptotics.
Code: `studies/diffraction/cylinder_oracle.py`. Observable: absorbed power per
area = inward radial Poynting from the exterior total field at the surface,
which is exactly what `S_ab` models. The interior enters only through the
numerically stable log derivative `D_n = J_n'(k1 a)/J_n(k1 a)` (downward
recurrence), so there is no large-complex-argument Bessel overflow.

A cylinder is the canonical limb. The point of the oracle is to answer, by
measurement against the exact solution, questions the surface law cannot
answer about itself: is a limb a knife edge or a Fock convex body, how big is
the polarization split, and does any of it change the dose.

Polarization naming (a known trap): cylinder `TM_z` (E along the axis) is the
Fresnel s-polarization (E perpendicular to the plane of incidence) and the
soft / Dirichlet case. Cylinder `TE_z` (H along the axis) is Fresnel p-pol and
the hard / Neumann case.

## Solid findings

1. A limb is Fock, not a knife edge. The deep-shadow field decays
   exponentially with a rate that scales as `(kR)^{1/3}` (Fock), not
   `(kR)^{1/2}` (knife edge). Fitted scaling exponents on the PEC cylinder:
   TM 0.385, TE 0.350, both near the Fock `1/3 = 0.333` and far from the
   knife `0.5`. So the current GeLU gate, whose width scales as `(kR)^{-1/2}`,
   has the wrong functional form. The penumbra is too narrow by `(kR)^{1/6}`,
   which is 1.6x to 2.7x across body parts at 28 GHz.

2. The soft / hard polarization split is real and quantitatively the textbook
   value. The PEC soft-to-hard decay-rate ratio measured on the cylinder rises
   `1.96 -> 2.28` as `kR` goes `10 -> 320`, converging to the theoretical
   `q1_soft / q1_hard = 2.338 / 1.019 = 2.295` (zeros of Ai vs Ai'). The hard
   (p-pol) creeping wave penetrates more than twice as deep into shadow as the
   soft one.

3. For real skin the soft polarization (s-pol) is clean Fock. Shadow decay
   exponent 0.371. In the lit region the flat-interface Fresnel `T_s * mu`
   model is good to within about 25 percent except inside the penumbra, and
   the integrated (whole-limb) error of the current GeLU model is only 2 to 4
   percent across `kR`. The s-pol whole-body SAR is essentially unaffected by
   the diffraction model, as expected. The gain from the Fock upgrade for
   s-pol is pointwise, in the penumbra, not in the integral.

4. Deep-shadow leakage is real but dose-negligible. The GeLU Gaussian tail
   under-predicts the exact creeping-wave field by many orders of magnitude
   at 20 degrees into shadow, but the absolute dose there is about `1e-6` of
   the lit value, so it matters only for dedicated deep-shadow studies, never
   for whole-body or typical pointwise maps.

## The hard / p-pol question, and why the cylinder cannot close it

The hard (p-pol) polarization on skin behaves qualitatively differently from
PEC and from s-pol:

- Its shadow decay is much slower than the PEC hard wave (the lossy surface
  impedance binds a p-pol surface wave that hugs the surface), and the decay
  rate even decreases with `kR` rather than growing. The simple PEC hard
  constant is not adequate for p-pol on skin.
- In the lit region the exact p-pol absorbed power sits well above the flat
  Fresnel `T_p * mu`, growing toward grazing (apparent factors of 1.4x to 5x
  at 48 to 80 degrees incidence on the cylinder).

That apparent lit-region enhancement is NOT trustworthy as a body number. A
fixed-incidence sweep in `kR` shows the s-pol ratio is flat (recovers GO) but
the p-pol ratio is erratic and non-convergent (for example at 50 degrees:
3.4, 41.9, 12.1, 3.1, 3.4 as `kR` steps up). That is the signature of
closed-cylinder surface-wave resonances: the slowly-decaying p-pol wave
circulates a closed 2D cylinder and resonates at particular `kR`. An open,
tapered, attached limb or a doubly-curved surface would not resonate the same
way, so the cylinder overstates the p-pol effect. The sign and existence of a
p-pol curvature-polarization coupling are real; the magnitude on a body is not
measurable from the cylinder.

## Consequences for the framework

- The Fock soft gate (correct `(kR)^{1/3}` width and exponential shadow tail)
  is well justified and validated, and folds the s-pol case in cleanly. It is
  a pointwise-accuracy upgrade, not a whole-body-SAR one.
- The hard / p-pol case needs two more things before it can be modeled
  honestly: the impedance-Fock complex eigenvalues for skin (a small per-band
  solve from `Ai'(t) - q Ai(t) = 0` with `q` from the skin surface impedance
  `eta = 1/n = 0.19 + 0.08j`), and a non-resonant validation geometry. The
  decisive next oracle is the sphere (double curvature, no 2D line resonance,
  reuses the Mie machinery) and ultimately the Thelonious mesh via a
  full-wave reference.
- Whole-body SAR is likely robust across the diffraction model for s-pol;
  the open risk is the p-pol curvature coupling, whose body-scale magnitude is
  still unknown.

## Next

1. Sphere surface absorbed power vs angle (vector Mie, inward Poynting from
   the exterior field for stability), E-plane vs H-plane, to quantify the
   p-pol curvature coupling without the 2D resonance.
2. Impedance-Fock eigenvalues for skin per band, validated against the clean
   s-pol cylinder decay and the sphere.
3. Only then lock the spec scope and the orthogonal diffraction-model axis.
