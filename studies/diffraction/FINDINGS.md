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

## The hard / p-pol question on the cylinder (a sign bug, then resonance, both resolved)

Earlier I reported that the hard (p-pol) skin channel decayed anomalously
slowly and rose far above flat Fresnel in the lit region (1.4x to 5x). Two
distinct artifacts produced that, and both are now fixed.

1. Gain-medium sign bug. AEGIS stores the refractive index as `n - ik`
   (engineering `e^{+iwt}`); the oracle integrates `e^{-iwt}` outgoing
   Hankels, which need `Im(n) > 0` for a lossy body. Feeding the stored
   `Im(n) < 0` straight in modelled a GAIN cylinder and corrupted the hard
   channel specifically (the hard creeping wave is the one bound to the
   surface, so it is the one a gain surface amplifies). `cylinder_oracle.py`
   now conjugates to `Im(n) > 0` before solving. With the fix the skin TE
   shadow exponent jumps from a nonsensical 0.045 to a clean 0.455.
2. Closed-cylinder lit-region resonance. The earlier erratic, non-convergent
   p-pol lit ratios (3.4, 41.9, 12.1, ... in `kR`) were a closed-loop
   surface-wave resonance, independently confirmed gone on the sphere.

Corrected skin cylinder (lossy, `n - ik` conjugated to `Im(n) > 0`):

- Shadow decay exponents are both clean and Fock-like: skin TM (soft) 0.402,
  skin TE (hard) 0.455. The hard channel is NOT anomalous. Neither hugs the
  surface pathologically.
- The soft/hard decay-slope ratio is 1.88, 1.95, 1.89, 1.81, 1.71, 1.59 over
  `kR = 10 -> 320`, i.e. it sits BELOW the PEC 2.295 and decreases with `kR`.
  Physical reading: the lossy surface impedance damps both creeping waves and
  shrinks the soft/hard asymmetry, pulling the hard eigenvalue up from the PEC
  `q1 = 1.019` toward roughly `2.338 / 1.7 ~ 1.4`. This is exactly the regime
  where the impedance-Fock solve (`Ai'(t) - q Ai(t) = 0`) matters, and it
  confirms D5: the PEC hard constant is wrong for skin, but the correction is
  modest (a sub-2x change in a shadow tail that carries ~1e-6 of lit dose).
- Lit region: both polarizations now recover GO to within 1 percent. The
  fixed-incidence `kR` sweep gives `exact/(T*mu) -> -1.00` for both s and p
  at every tested incidence (30, 50, 70 deg) by `kR = 320`. No p-pol lit
  enhancement survives the sign fix, matching the sphere exactly.

So the corrected cylinder and the sphere now AGREE: no lit-region p-pol
curvature coupling, both channels Fock in the shadow, and a real-but-modest
impedance reduction of the soft/hard split on skin.

## Consequences for the framework (revised after the sphere)

The exact oracles talked the ambition down, in a good way. The dose-relevant
diffraction physics is narrower than tier 3 implied.

- The lit region needs nothing new. Flat Fresnel plus the shipped polarization
  weighting is correct to about 1 percent out to 66 degrees on a doubly curved
  body. No p-pol curvature coupling, no curvature-Fresnel term.
- The one justified local upgrade is a Fock penumbra/shadow gate replacing the
  GeLU: correct `(kR)^{1/3}` width and exponential shadow tail, with the
  soft/hard split (PEC ratio 2.295, validated). This is pointwise near shadow
  edges, not a whole-body-SAR mover. For skin the soft (s-pol) gate is clean
  (exponent 0.402). The hard (p-pol) shadow decay on skin is also clean
  (exponent 0.455) but the soft/hard ratio drops to 1.6-1.9 (below the PEC
  2.295 and decreasing with `kR`): the lossy impedance damps the hard creeping
  wave less asymmetrically than PEC. This is what the impedance-Fock
  eigenvalues capture (`Ai'(t) - q Ai(t) = 0`, `q` from `eta = 1/n =
  0.19 + 0.08j`), a small per-band solve pulling the hard `q1` from 1.019 up
  toward ~1.4. Since shadow dose is ~1e-6 of lit, even a modest hard-constant
  error is small in absolute dose; the impedance correction is included for
  correctness, not because it moves the SAR.
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
