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

## The sphere closes the p-pol question: the cylinder cried wolf

Update 2026-06-08, after building the Mie sphere oracle
(`studies/diffraction/sphere_oracle.py`, surface absorbed power = inward
Poynting from miepython near fields, validated: the surface integral recovers
the Mie Qabs to 0.7 percent). A sphere has double curvature and no 2D line
resonance, so it is the clean intermediate between cylinder and mesh.

The result reverses the cylinder's alarm. On the sphere both polarizations
recover GO cleanly with no resonance (exact/GO at 70 degrees incidence:
s-pol 0.639 -> 0.505, p-pol 0.552 -> 0.506 as x goes 30 -> 480, both
converging to the same field-normalisation constant). In the lit region at
x = 240, flat-interface Fresnel is accurate to about 1 percent out to 66
degrees incidence for BOTH polarizations, and departs only within about 15
degrees of grazing, where the rise is the penumbra (1.46 s-pol, 1.35 p-pol at
82 degrees), nearly polarization-symmetric in magnitude.

So there is no large p-pol lit-region curvature-Fresnel coupling on a doubly
curved body. The 1.4x-5x I measured on the cylinder was almost entirely the
closed-cylinder surface-wave resonance, not a body effect. Flat Fresnel plus
the per-triangle polarization weighting already shipped (PR #835) is correct
in the lit region to about 1 percent. The only real local diffraction
correction is the penumbra and shadow near the terminator, which is pointwise
(consistent with the 2-4 percent whole-limb integral) and carries the
soft/hard split in its shadow decay.

## The hard / p-pol question on the cylinder (superseded by the sphere above)

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

## Consequences for the framework (revised after the sphere)

The exact oracles talked the ambition down, in a good way. The dose-relevant
diffraction physics is narrower than tier 3 implied.

- The lit region needs nothing new. Flat Fresnel plus the shipped polarization
  weighting is correct to about 1 percent out to 66 degrees on a doubly curved
  body. No p-pol curvature coupling, no curvature-Fresnel term.
- The one justified local upgrade is a Fock penumbra/shadow gate replacing the
  GeLU: correct `(kR)^{1/3}` width and exponential shadow tail, with the
  soft/hard split (PEC ratio 2.295, validated). This is pointwise near shadow
  edges, not a whole-body-SAR mover. For skin the soft (s-pol) gate is clean;
  the hard (p-pol) shadow decay wants the impedance-Fock eigenvalues
  (`Ai'(t) - q Ai(t) = 0`, `q` from `eta = 1/n = 0.19 + 0.08j`), a small
  per-band solve. But since shadow dose is small, even getting the hard
  constant slightly wrong is a small absolute error.
- Coherent multi-edge / double diffraction (tier 3's reach) is not justified by
  the dose impact and is out, matching the steer.
- Distal occlusion (one body part shadowing another) is a separate geometry
  from the local terminator tested here and is the place where deep-shadow
  dose can actually matter (a hand fully shadowing the cheek). That is the
  existing self-shadowing LUT spec; the same Fock-with-occluder-curvature gate
  applies there. FDTD on the homogeneous phantom is now only worth spending on
  the distal/concavity case, not the local curvature question (the sphere
  settled that).
- Inter-body reflection stays a small, optional axis (earlier report: body
  averaged enhancement <= 8 percent, specular recapture comparable to diffuse,
  worst concavity 1.85x).

## Next

1. Fold these oracles into the diffraction-model spec: a single Fock gate
   (local terminator + distal occluder) with soft/hard constants, replacing
   GeLU, validated by `cylinder_oracle.py` (decay law, 2.295) and
   `sphere_oracle.py` (lit-region 1 percent, GO recovery).
2. Impedance-Fock eigenvalues for skin per band, validated against the clean
   s-pol cylinder decay.
3. FDTD on the homogeneous phantom only for distal-occlusion / concavity
   deep-shadow validation, if and when that regime is targeted.
