# The physics of the medium hook

`FOLIAGE.md` ends with a request for a hook in `SbrTracer._run_batch` and calls it
roughly twenty lines. This document says what those lines have to compute and why,
and lists four things the twenty lines do not cover. Written 2026-08-03 against
`semantic_twin/foliage.py` as it stands.

The short version. A surface tracer assumes light travels in straight lines and
only ever changes direction on a face. A canopy breaks that assumption, so the
equation being solved changes, not just the material table.

---

## 1. What equation replaces what

A surface-only tracer solves the rendering equation. Radiance is constant along a
ray between faces, and every interaction is a boundary condition on a surface.

With a participating medium, radiance changes *along* the ray. The governing
equation is the radiative transfer equation. Along direction $\hat u$ at position
$\mathbf{x}$,

$$(\hat u \cdot \nabla)\, L(\mathbf{x}, \hat u) = -\sigma_t L(\mathbf{x}, \hat u) + \sigma_s \int_{4\pi} p(\hat u' \to \hat u)\, L(\mathbf{x}, \hat u')\, d\Omega'$$

with

- $\sigma_t$ the extinction coefficient in nepers per metre, power lost from the
  beam per unit length, which is P.833's `sigma_tau`,
- $\sigma_s = W \sigma_t$ the scattering coefficient, with $W$ the single
  scattering albedo, the share of extinction that redirects rather than absorbs,
- $\sigma_a = (1 - W)\,\sigma_t$ the absorption coefficient,
- $p$ the phase function, the angular distribution of scattered power, normalised
  to one over the sphere.

There is no emission term. A canopy at 290 K radiates, but the noise temperature
question is a different study.

The first term on the right is why a canopy shadows. The second is why it does not
shadow as hard as an opaque object: power removed from one direction reappears in
another instead of vanishing.

## 2. The four parameters, and where each comes from

| symbol | code | meaning | source |
| --- | --- | --- | --- |
| $\sigma_t$ | `extinction_per_m` | extinction, nepers per metre | P.833-10 Tables 5 to 8, or Figure 2 |
| $W$ | `albedo` | scattered share of extinction | Tables 5 to 8 |
| $\alpha$ | `forward_fraction` | share of scattered power in the forward lobe | Tables 5 to 8 |
| $\beta$ | `phase_beamwidth_deg` | forward lobe beamwidth | Tables 5 to 8 |

Only $\sigma_t$ strongly moves the answer, and it is the one the recommendation
disagrees with itself about. Table 8 gives London plane at 11 GHz 6.5 dB/m while
Figure 2 gives about 2.2 dB/m at the same frequency, and across species within
Table 8 the spread at 11 to 12.5 GHz is a factor of 7.3. That is why
`run_foliage_study.py` sweeps $\tau$ rather than quoting one value.

**Convention warning, carried over from `FOLIAGE.md`.**
`specific_attenuation_db_per_m` converts at 8.686 dB per neper, which is the field
convention, while `slab_transmission` and the free flight transport power as
$e^{-\tau}$, which is the power convention at 4.343. Both cannot be right. This is
an open code question, not resolved here.

## 3. The three events, and how each is sampled

Everything the hook does is one of three things.

### 3.1 Free flight, which is where the exponential lives

The probability that a photon travels at least $t$ without colliding is
$e^{-\sigma_t t}$, so the collision distance has density $\sigma_t e^{-\sigma_t t}$.
Inverting the cumulative distribution gives the sample

$$t = -\frac{\ln \xi}{\sigma_t}, \qquad \xi \sim U(0,1]$$

which is `foliage.py:799`. Note what this does **not** do: it never multiplies a
throughput by $e^{-\tau}$. The attenuation is realised by the fact that some rays
collide and stop being the ray they were. This is the analog estimator. It is
unbiased and it needs no bookkeeping, at the cost of more variance than a weighted
scheme would have.

### 3.2 The race against the geometry, which is why order matters

At each step the ray has two candidate next events: a collision at distance $t$ in
the medium, and a surface at distance $d$ from the intersector. **The nearer one
wins.**

```
collide = inside & (t < d)
```

That single line is the whole reason `FOLIAGE.md` insists free flight sampling runs
*before* the surface interaction. Doing the surface first would spend the bounce
that the canopy should have intercepted, and a wall behind a tree would then be lit
as if the tree were not there. The test also has exactly the right marginal
behaviour, because $P(t < d) = 1 - e^{-\sigma_t d}$, which is the transmittance of
the segment.

### 3.3 The collision, which absorbs or scatters

At a collision, scatter with probability $W$ and absorb with probability $1 - W$
(`foliage.py:832`). An absorbed ray has its throughput set to zero and is dropped.
A scattered ray draws a new direction from the phase function and keeps going.

The phase function is two lobes. With probability $\alpha$ the new direction sits
in a forward lobe of beamwidth $\beta$, otherwise it is isotropic. **P.833 exposes
$\alpha$ and $\beta$ and never writes the lobe's functional form down**, so
`sample_phase_function` uses a Gaussian, which is a guess. Section 6 is why the
guess is harmless.

## 4. The boundary, which has no interface

This is the part that is a physics claim rather than a sampling choice.

Leaf area index times leaf thickness over canopy depth gives the volume fraction of
leaf material in a canopy. For London plane, LAI 1.930, leaf thickness 0.2 mm, over
a 6 m canopy,

$$f_v = \frac{1.930 \times 0.0002}{6.0} = 6.43 \times 10^{-5}$$

Maxwell Garnett in the dilute limit,

$$\varepsilon_{\text{eff}} = 1 + 3 f_v \frac{\varepsilon_l - 1}{\varepsilon_l + 2}$$

gives $\varepsilon_{\text{eff}} = 1 + 1.7\times10^{-4}$, and a normal incidence power
reflectance of $1.9 \times 10^{-9}$.

So the canopy hull is not a weak reflector. It is not a reflector. A ray crosses it
and the only thing that changes is which region the ray is in. The hook therefore
must, on a face marked as a medium boundary:

1. **not** call `fresnel_power_reflectance`,
2. **not** call `specular_share`,
3. **not** change the direction,
4. **not** touch the throughput,
5. flip a per-ray `inside` flag,
6. **not** increment the bounce counter.

Item 6 is not cosmetic. The bounce budget of three is an *evidence* budget from
`BOUNCE_BUDGET.md`: it counts interactions with surfaces whose material was either
photographed or guessed. Crossing a canopy boundary spends no evidence, because
nothing was assumed about a material there. Counting it would truncate paths that
have not paid for anything, and since a ray crosses the hull twice to pass through
a tree, it would cost two thirds of the budget to walk past one.

## 5. The current shipped model, written in this language

`MATERIAL_BINDING` routes `vegetation_effective` to the P.2040 `vacuum_air` row,
which has $\varepsilon_r = 1$ exactly, so `fresnel_power_reflectance` returns zero
and `live_throughput *= reflectance` kills the ray at the hull.

In medium terms the shipped model is

$$\sigma_t \to \infty, \qquad W = 0$$

a perfectly absorbing hull. The cut is $\sigma_t = 0$. The retired wood row sat at
an effective $\tau$ above 16 over 6 m, which is above 139 dB of one way loss.

That is a useful way to see it. **The hook is not a replacement for the current
treatment, it is a generalisation of it.** The shipped model is a corner of the
medium's own parameter space, and so is the cut. Both are recovered by setting one
number.

## 6. Why the invented phase function does not matter

The delta-M scaling, P.833 equations (13) and (14):

$$\hat\tau = \tau\,(1 - \alpha W), \qquad \hat W = \frac{(1 - \alpha) W}{1 - \alpha W}$$

The idea is that power scattered into a very narrow forward lobe is
indistinguishable from power that was never scattered, so you delete that share
from the scattering and reduce the extinction to match.

**The check that this is physical, and worth stating because it is a one line
proof.** The scaled scattering coefficient is

$$\hat\sigma_s = \hat\sigma_t \hat W = \sigma_t (1 - \alpha W) \cdot \frac{(1-\alpha)W}{1 - \alpha W} = (1-\alpha)\,\sigma_s$$

so scattering loses exactly the forward fraction, and the absorption coefficient is

$$\hat\sigma_a = \hat\sigma_t - \hat\sigma_s = \sigma_t - \alpha\sigma_s - \sigma_s + \alpha\sigma_s = \sigma_a$$

**unchanged.** Delta-M moves scattering around and never touches absorption, which
is what makes it a reparameterisation rather than a different medium.

If escaping power is invariant under a scaling the recommendation itself applies,
the lobe shape cannot be doing any work. Measured invariant to 3% at $\beta$ of 2
and 8 degrees. So P.833 has already committed to the volumetric picture, and a
Monte Carlo transport solver is the same physics its series solution solves rather
than a rival model.

## 7. The validation identity, which is the good test

An absorbing slab ($W = 0$) of depth $d$ over an otherwise empty sphere has a
closed form. Directions sampled uniformly on the sphere have $\mu = \cos\theta$
uniform on $(0, 1]$ in the upper half, and the chord through the slab is $d/\mu$,
so

$$\chi = \frac{1}{2} + \frac{1}{2}\int_0^1 e^{-\tau/\mu}\, d\mu = \frac{1}{2} + \frac{1}{2} E_2(\tau)$$

with $E_2$ the second exponential integral, using $E_n(x) = \int_1^\infty t^{-n} e^{-xt}\,dt$
after the substitution $\mu = 1/t$. The leading $1/2$ is the downward hemisphere,
which never enters the slab.

Checked at $\tau$ of 0.25, 1 and 3 to within 1%.

**Why this test and not Beer-Lambert.** A normal incidence check only exercises one
chord, so it passes even if the chord length, the boundary crossing and the free
flight are all wrong in compensating ways. The $E_2$ identity integrates over every
obliquity, so a wrong chord shows up immediately.

## 8. What the twenty lines do not cover

Four things, listed because the estimate in `FOLIAGE.md` is honest about the loop
body and silent about these.

### 8.1 Next event estimation needs transmittance, not visibility

This is the significant one, and it is a consequence of work that landed after
`FOLIAGE.md` was written.

`METHOD.md` section 5 makes next event estimation the sampling method: at every
path vertex, connect to a point on the roofline and take the contribution if the
connection is clear. `semantic_twin/propagation/skyline.py:269` implements the
connection, and its answer is a **boolean**:

```python
visible = ~hit | (travel >= distance - 2.0 * epsilon_m)
contribution[good] = ...
```

A medium does not block and does not pass. It attenuates. The correct connection
weight through a canopy is

$$T = \exp\left(-\sigma_t \, \ell\right)$$

with $\ell$ the length of the connection segment lying inside the canopy. That is a
**deterministic transmittance query** and it is a different routine from the
stochastic free flight of section 3.1. In rendering these are two separate
primitives, distance sampling and transmittance estimation, and a medium
implementation needs both.

So the hook is not one predicate in one loop. It is one predicate in the bounce
loop plus a segment integrator in the connection routine.

Worth noting for scheduling: `SbrTracer` does not call `connect` yet, so today the
twenty line estimate is correct for the tracer that exists. It stops being correct
the moment next event estimation lands, and both changes touch the same file.

### 8.2 The `inside` flag assumes a watertight hull

`inside[crossing] = ~inside[crossing]` is a parity toggle. Parity is exact on a
closed manifold and meaningless on an open one.

`CanopyCanyonGeometry` in the study is an analytic box, so the study is safe. The
production canopy is a photogrammetric blob from multi view stereo, which is lumpy
at the half metre scale and is not guaranteed closed. A ray that clips an open edge
enters and never exits. It is then inside the medium for the rest of its life and
is eventually absorbed, so the failure **silently eats power** rather than raising.

This is the largest practical obstacle between the study and production, and it is
bigger than the loop change. The fix is either a watertightness pass on the canopy
hulls at export, or a signed-distance test instead of a parity toggle, or both plus
an assertion that the parity is even when a ray terminates.

### 8.3 A boolean cannot count overlapping canopies

Two trees whose hulls intersect need a nesting depth, not a flag. Cheap to fix
(`inside` becomes an integer, extinction scales with the count or takes a maximum),
but it has to be a deliberate choice about what overlapping hulls mean physically,
because two overlapping reconstructions of the same tree are a mesh artefact and
not twice the leaves.

### 8.4 The medium is homogeneous

$\sigma_t$ is one number for the whole canopy. A real canopy is denser in the middle
and thinner at the edges, and the hull the reconstruction gives is the outer
envelope, so a homogeneous fill over-attenuates near the silhouette. The standard
remedy is delta tracking against a majorant extinction, which keeps the free flight
sampling unbiased for a varying $\sigma_t$ at the cost of rejected collisions.
Nothing in P.833 supports a density profile, so this is unmotivated until there is
evidence to put in it.

## 9. What this is worth at the bands where the network exists

Figure 2 of P.833-10 fits specific attenuation as $0.19\, f_{\text{GHz}}^{1.02}$ dB
per metre. Over a 6 m canopy, and reading the curve as a power attenuation so
converting at 4.343 dB per neper:

| frequency | specific attenuation | over 6 m | $\tau$ |
| --- | --- | --- | --- |
| 1.8 GHz | 0.35 dB/m | 2.1 dB | 0.48 |
| 3.5 GHz | 0.68 dB/m | 4.1 dB | 0.94 |
| 15 GHz | 2.97 dB/m | 17.8 dB | 4.1 |
| 28 GHz | 5.60 dB/m | 33.6 dB | 7.7 |

`FOLIAGE.md` part 5 item 1 says that below about $\tau = 0.3$ the medium and the cut
agree within 0.5 dB out to 26% canopy solid angle, and the cheap null wins.

At 1.8 GHz, which is the band Veludo et al. measure as the dominant environmental
contributor, $\tau = 0.48$ sits close to that. **The foliage question mostly
dissolves at the frequencies where the network actually is, and only becomes real
at 15 GHz and above.** That is worth knowing before spending the hook, and it is an
argument for doing the watertightness work first and the transport second.

## 10. Provenance

| item | source |
| --- | --- |
| RTE, free flight, delta tracking | standard transport theory, and Johnson and Schwering CECOM-TR-85-1 1985 behind P.833 section 3.2.1.4 |
| $\sigma_t$, $W$, $\alpha$, $\beta$ and their spread | ITU-R P.833-10 Tables 5 to 8, audited in `FOLIAGE.md` part 1 |
| specific attenuation fit $0.19 f^{1.02}$ | `foliage.py:339`, fitted to P.833-10 Figure 2 |
| delta-M equations (13) and (14) | ITU-R P.833-10, implemented `foliage.py:396` and `:416` |
| Maxwell Garnett boundary reflectance $1.9\times10^{-9}$ | `foliage.py:477`, LAI from P.833 Table 4, thickness from Table 9 |
| $E_2$ identity, checked to 1% at $\tau$ 0.25, 1, 3 | `tests/test_foliage.py` |
| delta-M invariance to 3% | `FOLIAGE.md` part 4 |
| boolean visibility in the connection | `semantic_twin/propagation/skyline.py:299` |
| shipped vegetation binding | `semantic_twin/propagation/semantic_binding.py:62` |
| dominant environmental band 1.8 GHz | Veludo et al., Environment International 200 (2025) 109540 |
