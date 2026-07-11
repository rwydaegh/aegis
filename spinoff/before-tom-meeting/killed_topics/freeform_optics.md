# Killed topic re-examined: freeform illumination optics, LiDAR and automotive optics

Written 2026-07-06. This stress-tests the earlier verdict that freeform optics is a weak fit
for the AEGIS method. I re-derived the physics, ran the light calculations, and did real web
research on the incumbent tools and the academic state of the art. The short version is at the
bottom. The verdict moved, but not in the direction a hopeful reading would want.

## The claim I am testing

The earlier write-off said: geometric optics with refraction and Fresnel loss is a partial
fit, but imaging and illumination performance needs more than a single-bounce PO surface model,
and differentiable rendering (Mitsuba 3, nvdiffrast) already owns differentiable optics, so
AEGIS brings nothing new. That is roughly right on the conclusion but sloppy on the reasoning.
The interesting finding is that the usual objection (single bounce is too crude) is the *weak*
objection here, and it is nearly backwards. The real killer is elsewhere.

## 1. The physics map: where the assumptions actually break

First the good news for optics, which is real and worth stating plainly.

At optical wavelengths the "electrically large and smooth" regime that AEGIS was built for is
satisfied with margin to spare. A headlamp reflector is roughly 0.05 to 0.15 m across. At the
photopic peak lambda = 550 nm the size-to-wavelength ratio is

    D / lambda = 0.10 m / 550e-9 m = 1.8e5

so about 180,000 wavelengths across the aperture. A LiDAR receive lens of 20 mm at 905 nm is

    0.020 / 905e-9 = 2.2e4

about 22,000 wavelengths. In dosimetry the body is tens of wavelengths across at a few GHz and
the smoothness and locally-planar assumptions are already stretched. In optics they are trivially
true. So assumption A2 (first bounce, geometric) and A4 (locally planar Fresnel/Kirchhoff local
law) are *stronger* here than in the home domain, not weaker. Geometric and physical optics are
essentially exact for the surface interaction itself. The earlier "single bounce is too crude"
framing has this exactly backwards for the surface law.

Now the assumptions that genuinely fail, split by the two canonical cases the prompt asked me
to separate.

(a) Metallic reflector (specular, PEC-like, single dominant bounce). A2, A3, A4 all hold. The
surface confines the interaction to a 2D sheet (A3 holds because a metallic reflector is opaque,
there is no transmissive volume). The interaction is one specular bounce of a nearly-plane-wave
local field off a smooth conductor. This is AEGIS's actual sweet spot, geometrically the cleanest
case it will ever see. A first-bounce differentiable surface integral is physically legitimate here.

(b) Refractive freeform lens (transmissive dielectric volume). A3 fails outright. Light enters
the dielectric, refracts at the first interface, travels through the bulk, and refracts again at
the exit interface. The relevant physics is a two-surface (minimum) ray with an internal path,
plus total-internal-reflection and Fresnel partial reflection at each interface. The 3D-to-2D
reduction that gives AEGIS its speed is gone. You are back to tracing rays through a volume, which
is exactly what a normal ray tracer does and where AEGIS has no structural advantage. A5
(pseudo-Brewster scalar collapse) is tissue-specific and irrelevant here either way.

So the assumption-ladder answer is clean: reflector keeps A2+A3+A4, lens loses A3. That part
supports a "reflector yes, lens no" story, and if the story ended at the forward model it would
be a WORTH-A-SECOND-LOOK. It does not end there. Three deeper issues decide it.

Issue one: the objective is a distribution, not a scalar. Illumination design does not optimize
a single power number. A headlamp is graded against a full angular luminous-intensity distribution
I(theta, phi). ECE R112 for low beam specifies luminous intensity at roughly 54 to 59 named test
points (HV, 50V, 75R, B50L, the 0.57 D glare line, and so on), with required values spanning
about 32,500 to 240,000 cd across points and a hard glare ceiling above the cutoff, and the
regulation demands angular data at 0.05 degree spacing in the hotspot falling to 1.0 degree in
the periphery. That is a many-constraint shaping problem over a 2D angular field, not a scalar
power maximization. AEGIS's native output is a power scalar of the form x^H Q x. You can bin the
far field into angular cells and define one Q per cell, and that is even faithful to the calculus.
But that only helps if the thing you optimize is the excitation vector x, which brings us to the
real killer.

Issue two, the killer: there is no controllable coherent excitation vector x. This is the crux
and it is worth being precise, because it is the single reason the commercial moat does not
transfer. AEGIS's durable advantage is not the forward surface integral. It is the closed-form
Hermitian operator algebra: a power quantity equals x^H Q x, the identity Q_ab + Q_re + Q_mi = I
holds, and because the design variable x enters power quadratically with geometry held fixed, a
constrained design problem collapses to a QCQP or a generalized eigenproblem in closed form. That
entire machine rests on one precondition: you control a coherent complex excitation vector x, and
geometry is fixed. In MIMO dosimetry that x is the precoder driving the antenna array. It is real,
it is coherent, you own it.

In classical illumination optics that vector does not exist. The source is an LED die or a
filament. It is spatially extended, temporally incoherent, and you do not control its phase. There
is nothing to put in x. The design variable is the *surface geometry itself*, the freeform sag
map, and geometry enters the power integral nonlinearly (through the surface normal inside the
ReLU-cosine visibility term and through the ray-remap Jacobian). Once the unknown is geometry
rather than a quadratic excitation vector, you are no longer in the x^H Q x regime at all. Q is a
functional of the geometry you are trying to solve for, not a fixed matrix sandwiching a vector.
The QCQP-and-eigenproblem moat evaporates and you are left with generic gradient descent on a sag
map. That is precisely what differentiable ray tracers already do, and do with full multi-bounce
physics that AEGIS discards. So in optics AEGIS keeps the weaker of its two assets (a fast forward
model) and loses the stronger one (the closed-form inverse-design calculus), in the one place where
the fast forward model is least valuable because incumbent forward solvers are already real-time.

Issue three, the irony of stray light: the first-bounce assumption is blind to the exact
phenomenon that stray-light analysis exists to find. More on this in section 4, but note it here.
A2 is a strength for the primary beam and a fatal weakness for ghosts, glints, and baffle leakage,
because those *are* the second, third, and scattered bounces.

## 2. Light calculations that sharpen the verdict

Diffraction at the regulatory cutoff. The one place geometric optics quietly fails in headlamp
design is the sharp low-beam cutoff, and the numbers are close enough to matter. A freeform facet
or a faceted reflector segment of characteristic size d imprints an angular diffraction blur of
order

    theta_diff ~ lambda / d

For a 1 mm facet at 550 nm: theta_diff ~ 550e-9 / 1e-3 = 5.5e-4 rad = 0.032 degrees.
For a 2 mm feature: ~0.016 degrees. For a 0.5 mm micro-facet: ~0.063 degrees.

The regulation demands cutoff control and hotspot sampling at 0.05 degrees. So the diffraction
blur from millimetre-scale optical features sits right at, and for sub-millimetre features exceeds,
the angular tolerance the regulation cares most about. This means a pure first-bounce geometric
model (A2 with no wave correction) cannot faithfully predict the very feature (the gradient of the
cutoff) that separates a passing headlamp from a glare failure. AEGIS has no diffraction term. This
is not fatal on its own, incumbents bolt on wave-optics cutoff modeling, but it removes any claim
that "geometric optics is exact here so AEGIS is exact here." It is exact for the beam body and
wrong at the cutoff, which is the commercially decisive 0.5 degrees of the pattern.

Etendue and brightness conservation. Illumination design is fundamentally constrained by etendue,

    G = integral integral n^2 cos(theta) dA dOmega

which is conserved through any lossless optic (brightness theorem). This is a hard geometric-optics
invariant that bounds what any reflector or lens can achieve: you cannot concentrate an extended
incoherent source below its etendue limit no matter how clever the freeform. AEGIS's Q calculus
does not encode or exploit etendue. Etendue conservation is a property of incoherent phase-space
volume, and the whole point of the coherent Q operator is that a coherent array beats incoherent
phase-space limits by controlling phase. In illumination there is no phase to control, so the
coherent advantage that justifies AEGIS is definitionally absent. The physics that makes AEGIS
special (coherent phase control beating incoherent bounds) is the physics that illumination optics
does not have.

Can a single-bounce differentiable surface model hit an ECE beam pattern. Geometrically, for a
pure metallic reflector with a small source, yes in principle: each surface element maps the source
into a far-field direction, and shaping the sag map redistributes flux into the target angular
cells. This is the classical inverse reflector problem and it is solved by optimal-transport and
Monge-Ampere methods (Brix and Hafizogullari 2014, and the 2025 Frontiers review by the Eindhoven
group). But the moment the real source is extended (a 1 to 5 mm LED die at a 30 to 60 mm focal
length subtends 1 to 10 degrees, comparable to the whole beam structure) the zero-etendue point
source assumption behind the clean inverse map breaks, and you need many-ray integration and
tolerancing. That is again standard non-sequential ray tracing, not a place a surface-only operator
wins.

## 3. State of the art: is differentiable optical design already commoditized

Yes, thoroughly, and this is the decisive market finding. I searched the lens-design, illumination,
rendering, and solar literature and the differentiable-geometry story is already owned on every
front.

Incumbent commercial CAD. Automotive lighting and freeform illumination are dominated by
Synopsys LucidShape and LightTools, Ansys Speos and Zemax OpticStudio, and Synopsys CODE V for
imaging. LucidShape has dedicated automotive reflector and freeform algorithms (MacroFocal,
pixel-light headlamp modules) and existing optimization loops against photometric targets. These
are mature, validated against ECE and SAE, and embedded in OEM tier-1 workflows. Speos and Zemax
own stray light in non-sequential mode. This is a crowded, deeply entrenched market with certified
regulatory workflows, which is the worst kind of market to enter with a faster forward solver.

Academic differentiable ray tracing for lenses. The dO / DiffOptics engine (Wang et al., IEEE
TCI 2022, open source at vccimaging/DiffOptics, and the successor DeepLens by singer-yang) is a
full PyTorch differentiable ray tracer for lens and freeform design with reverse-mode AD end to
end. The 2024 SIGGRAPH Asia hybrid refractive-diffractive work adds a differentiable ray-wave
model. So differentiable *imaging* lens design is done, published, and open.

Academic differentiable illumination design. This is the one that most directly pre-empts any
AEGIS illumination pitch: "Gradient descent-based freeform optics design for illumination using
algorithmic differentiable non-sequential ray tracing" (Optimization and Engineering, Springer,
2023, arXiv 2302.12031) does exactly the thing AEGIS would propose, designing freeform surfaces
that project a prescribed irradiance distribution, except with full differentiable *non-sequential*
ray tracing that keeps multi-bounce physics AEGIS throws away. The gap AEGIS might have filled is
already filled, and filled better on physics.

Differentiable rendering. Mitsuba 3 with Dr.Jit does differentiable inverse rendering including
explicit caustic-design and reflector-shaping tutorials (heightmap optimization against a target
caustic image). A November 2025 arXiv paper does computational caustic design for surface (extended,
non-point) sources, directly attacking the extended-source case. nvdiffrast covers the rasterization
side. This is the "differentiable optics" incumbency the earlier write-off named, and it is if
anything stronger than the write-off implied.

Adjoint and inverse methods. The inverse reflector problem has a mature optimal-transport /
Monge-Ampere literature (Brix, Hafizogullari, Prins, and the ICT/Eindhoven groups) that produces
freeform reflectors and lenses directly from source and target distributions without any iterative
ray-trace loop at all, which is arguably a stronger inverse-design story than gradient descent for
the zero-etendue case.

The net: differentiable optical design is not an opening, it is a saturated research area with
multiple open-source engines and an entrenched commercial CAD layer. A fast closed-form specular
surface operator brings speed, and speed is not a moat here because the incumbent forward solvers
are already interactive and the academic differentiable engines already give gradients.

## 4. The adjacent-surprise angles: do reflector-only, non-imaging, or stray light survive

The prompt correctly guessed these are geometrically closer to AEGIS than imaging lens design.
They are. But each fails for a specific, nameable reason, and the reasons are instructive.

Stray light and baffle design. Superficially perfect: specular or few-bounce, PEC-ish or Fresnel
surfaces, and the objective is a genuine power-flux scalar ("how much stray flux reaches the
detector"), which is literally a Q_in / Q_mi split. But stray light IS the multi-bounce and the
scatter. The whole discipline exists to find the ghost reflections, the double bounces off a
mechanical edge, the second-surface Fresnel ghost, and the BSDF scatter off a rough baffle. All of
that lives in exactly the bounces that A2 discards. AEGIS's first-bounce model is structurally
blind to the phenomenon stray-light analysis is defined to catch. This is the sharpest irony in
the whole report: the objective type fits (scalar flux) but the physics is 100 percent in the part
AEGIS drops. Dead.

Non-imaging concentrators (CPC, heliostat facets). This is the best surviving geometric fit.
Single or double specular bounce, opaque reflectors so A3 holds, and the objective (flux collected
onto a receiver) is a clean scalar power form that maps naturally onto Q_in. It is genuinely close
to AEGIS's sweet spot. But two things sink the moat. First, differentiable ray tracing for exactly
this is already published and strong: heliostat paraboloid canting via differentiable ray tracing
(Solar Energy 2025) reports two orders of magnitude speedup over heuristics and up to 9.7 percent
concentration gain, and the Nature Communications 2024 paper does in-situ heliostat metrology with
differentiable ray tracing and NURBS surfaces to sub-millimetre. Second, and structurally, the
design variable is again geometry (canting angle, facet sag), not a coherent x, so the closed-form
Q-QCQP does not apply and you are back to gradient descent that others already do. Real fit, thin
moat, occupied. This is at best a NICHE-PAPER, not a business.

LiDAR window and cover-glass stray light. Same verdict as stray light generally. The value is in
the ghost and scatter paths (cover-glass second-surface reflection sending the transmit pulse back
into the receiver), which is multi-bounce and BSDF-driven. A2 misses it. Dead for the same reason.

The one genuinely surviving coherent angle: optical phased array (OPA) LiDAR. This is the only
place in the entire optics landscape where a controllable coherent excitation vector x actually
exists. An OPA is a chip-scale array of emitters whose relative phases you set to steer and shape
the beam. That is, structurally, MIMO beamforming at optical frequency, and the exposure/flux
operators x^H Q x with the Q_in (into the field of view), Q_mi (wasted), Q_re decomposition
transfer essentially verbatim. If any part of AEGIS's actual moat survives into optics, it is here.
But note what this is: it is not optical CAD, it is silicon photonics beam-forming, the aperture is
a chip not a freeform surface, and it is a different (and itself crowded) industry. It is a pivot,
not a generalization of the illumination business. It belongs in the coherent-array column of the
generalization map, next to radar and RIS, not in the freeform-optics column.

## 5. Verdict

Grade: NICHE-PAPER-ONLY, leaning DEAD for the commercial thesis.

Not DEAD outright, because two honest things survive. The geometric fit for opaque single-bounce
reflectors is real and the forward model would be exact and fast there, and there is a legitimate,
publishable optical-frequency-MIMO connection through OPA LiDAR. But neither survives as a business
for the spin-off, because the durable moat (the closed-form Q-operator QCQP) requires a controllable
coherent excitation vector x that classical illumination optics simply does not have, and the one
place that vector exists (OPA) is a pivot into a different industry, not a generalization of optical
design. Everywhere the geometry fits (reflectors, concentrators, stray light) the design variable is
surface geometry entering nonlinearly, which drops AEGIS to plain differentiable-geometry gradient
descent, which is already published, open-source, and commercially entrenched.

The single strongest surviving angle. If the constraint is "preserve AEGIS's actual moat," it is
OPA LiDAR beam steering as literal optical-frequency MIMO, and it should be tracked in the
coherent-array family, not the optics family. If the constraint is instead "best pure geometric fit
for the forward engine regardless of moat," it is non-imaging solar concentrators (heliostat and CPC
flux collection as a Q_in objective), but that one has a thin moat and is already served by
differentiable ray tracing, so it is a paper at most.

What would have to be true to revive this for the spin-off:
- The customer's design variable would have to be a coherent controllable excitation, not surface
  geometry. In practice that means the target is OPA / integrated-photonics beam-forming, not
  headlamps, lenses, or reflectors. If a customer's knob is a phase vector, AEGIS applies. If it is
  a sag map, it does not, beyond the forward solve.
- The objective would have to be a small number of power-flux scalars (flux into a zone, flux
  missed) rather than a 54-point luminance distribution with a diffraction-limited cutoff. Concentrator
  flux collection qualifies. ECE headlamp shaping does not.
- Speed of the forward solve would have to be the binding constraint. It is not: incumbent optical
  CAD is already interactive and the academic differentiable engines already provide gradients, so
  even a 1000x forward speedup does not open a wedge.
- Diffraction and multi-bounce would have to be negligible for the paying use case. They are
  negligible for the beam body but decisive at the headlamp cutoff (0.03 degree blur vs 0.05 degree
  tolerance) and they ARE the entire signal in stray-light and ghost analysis.

My recommendation for the Tom Dhaene meeting: do not pitch freeform illumination optics, LiDAR
optics, or automotive lighting as a generalization target. If optics comes up, concede the geometric
fit honestly, then pivot to the only defensible statement, which is that the coherent Q calculus
generalizes across coherent-array physics (RF MIMO, RIS, radar, and at a stretch optical phased
arrays), and that classical illumination optics is the wrong shape because its design variable is
geometry and its source is incoherent, so the moat does not travel. That is the intellectually
honest boundary of the method and it is more credible than claiming a market that Synopsys, Ansys,
and a decade of differentiable-ray-tracing papers already own.

## Sources

- dO / DiffOptics differentiable lens engine (Wang et al., IEEE TCI 2022): https://ieeexplore.ieee.org/document/9919421/ and https://github.com/vccimaging/DiffOptics
- DeepLens differentiable optical simulator: https://github.com/singer-yang/DeepLens
- Gradient-descent freeform illumination via differentiable non-sequential ray tracing (Optim. Eng. 2023): https://arxiv.org/abs/2302.12031 and https://link.springer.com/article/10.1007/s11081-023-09841-9
- End-to-end hybrid refractive-diffractive lens design, differentiable ray-wave (SIGGRAPH Asia 2024): https://dl.acm.org/doi/10.1145/3680528.3687640
- Mitsuba 3 inverse rendering and caustics optimization: https://mitsuba.readthedocs.io/en/stable/src/inverse_rendering/caustics_optimization.html
- Computational caustic design for surface (extended) light source (arXiv 2025): https://arxiv.org/pdf/2511.09361
- Inverse reflector problem via Monge-Ampere (Brix, Hafizogullari 2014): https://arxiv.org/abs/1404.7821
- Inverse freeform design in non-imaging optics, optimal transport review (Frontiers in Physics 2025): https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2025.1518660/full
- Heliostat paraboloid canting via differentiable ray tracing (Solar Energy 2025): https://www.sciencedirect.com/science/article/abs/pii/S0038092X25006644
- Automatic heliostat learning via differentiable ray tracing (Nature Communications 2024): https://www.nature.com/articles/s41467-024-51019-z
- Synopsys LucidShape automotive lighting (freeform, MacroFocal, pixel light): https://www.synopsys.com/blogs/optical-photonic/lucidshape-for-automotive-lighting-design.html
- Ansys Zemax OpticStudio stray light (non-sequential): https://www.zemax.com/products/stray-light
- ECE R112 photometric test points and cutoff angular tolerance: https://www.researchgate.net/figure/The-ECE-R112-regulation-for-the-low-beam-a-The-light-pattern-structure-at-25-m-and-b_fig2_354101577
