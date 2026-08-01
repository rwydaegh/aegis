# Propagation core: the adjoint local transfer tensor, and the monostatic loop as its shadow

Design document for the propagation engine of the semantic radio digital twin.
Companion to `DESIGN.md`, which covers reconstruction. This document covers what
we compute once the scene exists.

Every number in this document that is labelled "measured" was computed against
`data/geometry/korenmarkt/inhouse_leaf_130m.ply` at the aligned panorama pose in
`data/panoramas/korenmarkt/alignment/pose_aligned.json`, with Mitsuba 3.8 in the
`llvm_ad_rgb` variant. Every relation labelled "derived" is derived in this
document and checked numerically against an independent route. Nothing is
asserted from memory of the literature.

## What this document decides

| Question | Call | Section |
|---|---|---|
| Primary observable | Adjoint local transfer tensor `T_S(u_loc, u_ext, tau, f)`, normalised to identity in free space | 2 |
| What is actually binned | The **coherency matrix** `C_S = <T T^H>`, never the amplitude. Coherent amplitude binning is wrong by 5 to 7 orders of magnitude in required angular resolution | 2.8 |
| Monostatic response | Derived scalar of the same trace, kept as a candidate predictor, not the headline | 3 |
| Scattering model | Microfacet BRDF in the geometric-optics Kirchhoff form, with a Rayleigh specular split | 5 |
| Degli-Esposti directive lobe | Comparison mode only. It is not reciprocal, and reciprocity is load-bearing here | 5.6 |
| Search over patch pairs | Rejected as the primary strategy. Kept for the deterministic specular branch over planes | 6 |
| Bounce count | 4, not 3, if the dynamic range budget is 25 dB or deeper. Measured, not assumed | 7.4, 9 |
| Range prune | Per-semantic-class, and in the adjoint formulation the exponent is not what it looks like | 7 |
| 130 m crop | **Not converged at Korenmarkt, and this is the largest known hole.** Physics disagrees with the coverage argument, and the rooftop weight's own support asks for sources the crop does not contain | 7.5, 9.4 |
| Diffraction | Absent, and the omission is bounded rather than fatal. Measured at under 1 % of received power at 28 GHz, and it arrives above the elevation band where `w_roof` puts its mass | 9.3, 14 |
| Tracer | Ours, on Mitsuba `ray_intersect`. Sionna as the cross-validation oracle | 10 |

---

## 1. Notation

Everything is at a fixed carrier `f` with free-space wavelength `lam = c/f` and
`k = 2*pi/lam`. All directions are unit vectors in a fixed world frame (ENU, as
the twin already uses).

- `S` is the observation point, the exact position at which the panorama was
  captured. Later, the position of a pedestrian.
- `u` is a direction of travel. A ray leaving `S` travels along `u_0`.
- `k_hat` is the propagation direction of an arriving wave, matching the AEGIS
  monograph convention where `Sab(r) = Sinc * T0 * ReLU[n_hat(r) . (-k_hat)]`.
- `x_1, ..., x_K` are interaction points, `n_m` the outward surface normal at
  `x_m`.
- `l_m` is accumulated path length from `S` to `x_m`.
- The atlas `A_S` is the first-hit buffer from `S`: for each cell `c` with
  direction `u_c` and solid angle `Om_c`, it stores range `r_c`, hit point
  `x_c = S + r_c*u_c`, normal `n_c`, primitive id, and the semantic, material and
  attribute posteriors from `project_pixel_semantics.py`.

Two distinct averaging operations appear and must not be confused.
`<.>_band` is an average over the signal bandwidth (400 MHz at FR2, 800 MHz to
1 GHz at FR3). `<.>_ens` is an average over the scene ensemble of `DESIGN.md`
(pose, material, roughness, object existence). Anything called a susceptibility
or an enhancement factor in this document is band-averaged first. Narrowband
pointwise ratios do not converge, they only move nulls around.

---

## 2. The primary object: the adjoint local transfer tensor

### 2.1 Definition

Place a virtual electric dipole at `S`, in the reconstructed scene, and compute
its far field. Write that far field, at large distance `r` in direction `u`, as

```
E_dipole(r*u) = (exp(-j*k*r)/r) * A(u) * p
```

where `p` is the dipole moment and `A(u)` is a 3x3 complex matrix whose range
lies in the plane transverse to `u`. `A(u)` is r-independent by construction,
which is what "far field" means.

Now consider the reciprocal experiment. A plane wave of amplitude `E_0`, with
`E_0 . u = 0`, arrives at the scene travelling along `-u`. Define the transfer
tensor `T_S(u)` by

```
E_total(S) = T_S(u) * E_0
```

where `E_total(S)` is the total field at `S`, incident plus all scattered
contributions.

**Claim.** `T_S(u) = (4*pi*eps_0/k^2) * A(u)^T`.

**Derivation.** Lorentz reciprocity for two electric dipoles `p` at `S` and `q`
at `R = r*u` in a linear, reciprocal medium gives `p . E_q(S) = q . E_p(R)`,
which is the statement that the dyadic Green's function obeys
`G(r_a, r_b) = G(r_b, r_a)^T`. Substituting the far-field form,

```
q . E_p(R) = (exp(-j*k*r)/r) * q . (A(u) p)
```

and only the component of `q` transverse to `u` survives because `A(u)` maps
into the transverse plane. The field that the dipole `q` would produce at `S` in
free space is the locally plane wave

```
E_0 = (exp(-j*k*r)/r) * (k^2/(4*pi*eps_0)) * q_perp
```

so `q_perp = (4*pi*eps_0/k^2) * (r*exp(+j*k*r)) * E_0`. Substituting,

```
p . E_total(S) = (4*pi*eps_0/k^2) * (A(u) p) . E_0   for every p
```

which gives `T_S(u) = (4*pi*eps_0/k^2) * A(u)^T`. QED.

**Free-space check.** In free space `A_free(u) = (k^2/(4*pi*eps_0)) * P_u` with
`P_u = I - u*u^T` the transverse projector, so `T_S = P_u`, and since `E_0` is
already transverse, `T_S*E_0 = E_0`. The tensor is the identity on the transverse
plane in free space. This is what fixes the normalisation, and it is the reason
the scalar below is 1 and not some arbitrary constant.

### 2.2 The normalised scalar, and why it must be a second moment

The obvious definition is `K_S(u) = (1/2)*||T_S(u)||_F^2`, which equals
`(1/2)*trace(P_u) = 1` in free space and is the average over two orthogonal
incident polarisations of the intensity ratio `|E_total(S)|^2/|E_0|^2`.
`K_S = 1` means "as if free space", `K_S = 0` means the direction is dead,
`K_S > 1` means constructive multipath.

That definition is right and the naive estimator for it is wrong, for a reason
section 2.8 makes precise. The quantity that is actually computed and published
is the second moment

```
C_S(u, tau) = < T_S(u, tau, f) T_S(u, tau, f)^H >     2x2 Hermitian, positive semidefinite
K_S(u)      = (1/2) * trace( integral of C_S(u, tau) dtau )
```

where the average is over the signal band and over the scene ensemble. In free
space `C_S = P_u` and `K_S = 1`, so the normalisation is unchanged. Everything
called a susceptibility below is this second-moment version.

### 2.3 Making it double-directional

`K_S(u)` alone loses something the exposure paper needs. The absorbed power
density on a body facet depends on the local arrival direction through
`ReLU[n_hat . (-k_hat)]`, and after multipath a single external direction feeds
many local arrival directions. So the object we actually compute is

```
T_S(u_loc, u_ext, tau, f)
```

with the following reciprocity dictionary, which is exact and worth stating
because sign errors here are silent and fatal:

| Forward trace from `S` | Reciprocal physical path |
|---|---|
| departure direction `u_0` | local arrival direction `k_hat = -u_0` |
| exit direction `u_e` | external source direction `u_ext = u_e` |
| accumulated length `l_K` and exit point `x_K` | excess delay, section 2.4 |
| Jones matrix along the traced path | transpose of the Jones matrix of the reverse path |

The consequence that matters: `-k_hat = u_0`, so the monograph's gate becomes
`ReLU[n_hat . u_0]`, evaluated directly on the **departure direction of the
traced ray**. No conversion, no sign hunt. The atlas cell directions are the
AEGIS arrival-direction basis.

### 2.4 Delay resolution, and the excess-path formula

For a path that leaves `S`, accumulates length `l_K` up to its last interaction
point `x_K`, and then escapes in direction `u_e`, the contribution to the
far-field amplitude carries the phase `exp(-j*k*Delta)` with

```
Delta = l_K - u_e . (x_K - S)
```

**Check against the image-source construction.** For a single specular bounce off
a plane at perpendicular distance `d` from `S`, with `r_1` the slant range to the
reflection point, the image-source phase is `exp(+j*k*u_e.(S' - S))` with
`S' = S - 2*d*n`. Working both sides through the reflection relation
`u_e = u_0 - 2*(u_0.n)*n` gives `u_e.(S' - S) = -2*d^2/r_1` and
`Delta = r_1*(1 - u_e.u_0) = 2*d^2/r_1`. They agree. For the zero-bounce ray,
`l_K = 0` and `x_K = S`, so `Delta = 0` and `T_S` reduces to the free-space
identity with zero delay, as it must.

Delay-resolving `T_S` is therefore free. The path length is already carried for
the phase. Binning it costs one scatter-add.

### 2.5 The exit surface

Define the scene bounding volume `B` as the ball of radius `R_B` centred on `S`,
and crop the mesh to `B`. A ray escapes when it crosses the boundary of `B`.
Because there is no geometry outside `B`, a ray that leaves can never re-enter
with an interaction, so "escape" is absorbing and unambiguous. Section 7.3 shows
that `R_B = L_max/2` is not a convention but a theorem, where `L_max` is the
longest retained path length.

**Record the exit point, not only the exit direction.** For each escaping path we
store `(x_K, u_e, tau, J)` where `x_K` is the last interaction point (or `S`
itself for the zero-bounce ray) and `J` the 2x2 Jones matrix. Three extra floats
per path. This makes the difference between a descriptor that is only valid for
sources at infinity and an operator that is exact at finite range. Section 4.4
explains why that matters more than it sounds.

### 2.6 What the exposure integral becomes

Model the external network as a set of mutually incoherent sources, which is the
right model for independent base stations. Let `Q_S(u_ext, f)` be the 2x2
angular incident-power density at `S` in the absence of the local scene, carrying
site density, EIRP, sectorisation, load, beam duty factor and LOS probability.
Then

```
E[ |E(S,f)|^2 ] = integral over 4*pi of trace[ T_S(u_ext,f) Q_S(u_ext,f) T_S(u_ext,f)^H ] dOmega_ext
```

Units check: `Q_S` in V^2 m^-2 sr^-1, integrated over sr, gives V^2 m^-2. The
incoherence assumption is what turns a double integral with cross terms into this
single integral, and it must be stated as an assumption, not smuggled in.

The angular power spectrum arriving at `S`, in the monograph's notation, is

```
rho(k_hat) proportional to integral of K_S(u_0 = -k_hat, u_ext) Q_S(u_ext) dOmega_ext
```

and then the monograph's own equation applies unchanged:

```
P_abs = Sinc * T0 * (A_ab/4) * (1/(4*pi)) * integral of rho(k_hat) D(k_hat) dOmega
```

This is the cleanest structural result in this document. The environment side
(`K_S`, from the twin) and the body side (`D(k_hat)`, the absorption directivity
that `theory/monograph_v2.tex` section `sec:precomputed` already stores as a
Fibonacci lookup table of about 10^3 directions) are computed independently and
composed by a dot product of two spherical functions. Nothing has to be
re-traced when the body, the pose, or the network changes.

It also tells us where the cross-city spread can possibly come from. The
monograph reports that the body-side coupling factor `F = (1/4pi) int rho D` moves
only from 1.00 (isotropic) to 1.15 (base-station elevation spectrum) to 1.18
(urban-canyon ring). The body's angular response is nearly flat, within 18 %
across illumination geometries. So essentially all of the cross-city exposure
spread has to live in `K_S`. That is the argument for publishing `K_S` per
location as the covariate the `OVERVIEW.md` gap list has been missing.

### 2.7 Canonical illumination scalars

These are the source-independent numbers to plot for ten cities.

**Isotropic susceptibility.** `K_iso = (1/4pi) * int K_S(u) dOmega`. Equals 1 in
free space.

**Rooftop-weighted susceptibility.** Do not use a flat elevation band. Derive the
weight. For sites of uniform areal density `n` at horizontal range `d` with
`Delta_h = h_site - h_head`, the elevation above the horizon is
`el = atan(Delta_h/d)`, so `d = Delta_h*cot(el)` and
`|dd| = Delta_h*del/sin^2(el)`. The number of sites in `[el, el+del]` is
`2*pi*n*d*|dd| = 2*pi*n*Delta_h^2 * cos(el)/sin^3(el) * del`.

State both forms explicitly, because getting the Jacobian wrong here is silent.
With `dOmega = cos(el)*del*dphi`:

```
density in el     proportional to  cos(el)/sin^3(el)      (uniform site density, no path loss)
weight on dOmega  proportional to  1/sin^3(el)

density in el     proportional to  1/(sin(el)*cos(el))    (with a d^-2 power weighting)
weight on dOmega  proportional to  1/(sin(el)*cos^2(el))
```

uniform in azimuth, supported on `el` in `[atan(Delta_h_min/d_max), atan(Delta_h_max/d_min)]`.
For `Delta_h` in [13.5, 43.5] m and `d` in [25, 250] m that is `el` in
[3.1, 60.1] degrees. Both forms are heavily low-elevation weighted: 64 % of the
pure geometric weight sits below 5 degrees and 89 % below 9 degrees.

Two consequences, and an earlier draft of this document had them the wrong way
round.

The first is that the stated support and the crop radius contradict each other.
Sources at `d = 250` m with `Delta_h = 13.5` m sit at 3.1 degrees, and the scene
is cropped at 130 m. The fraction of the `cos/sin^3` measure lying at elevations
that require a source outside the crop is 27.5 % at `Delta_h = 8` m, 79.4 % at
15 m, 88.5 % at 20 m and 94.9 % at 30 m. That is section 9.4, and it is the
largest hole in this document.

The second is that low elevation is **not** where rooftop-edge diffraction
arrives. Diffraction from the near roofline reaches a head at 1.7 m from the edge
directly overhead, so its arrival elevation is 35 to 86 degrees for the eaves
heights and standoffs of a European core. The `1/sin^3(el)` weight at 60 degrees
is 0.001 times its value at 5 degrees. Section 9.3 carries the numbers.

**Street-level small-cell susceptibility.** Same construction with `Delta_h` in
[2.5, 6.5] m and `d` in [10, 150] m, giving `el` in [0.95, 33] degrees.

**Worst-case directional susceptibility.**
`K_max = max over u of sigma_max(T_S(u))^2`, the largest squared singular value
over all directions. This is the bound if the whole network beamformed from the
single worst direction with the worst polarisation.

**Multipath enhancement.**

```
M_S = K_iso / K_iso^(0),   K_iso^(0) = (1/4pi) * int K_S^(0)(u) dOmega = sky fraction
```

because the zero-bounce tensor is the identity in sky-visible directions and zero
in blocked ones. At Korenmarkt the measured sky fraction is 0.2271, so
`K_iso^(0) = 0.2271`, and `M_S` is the factor by which multipath lifts the
isotropically averaged susceptibility above pure sky visibility. Define it on the
integrated quantity, never per direction, since `K_S^(0)` is zero in blocked
directions and the per-direction ratio diverges.

### 2.8 The angular coherence scale, which forces the second moment

This was found by running the validation of section 11.1 against the first
version of this design, and it invalidated it. It is recorded here rather than
quietly fixed, because it also settles how the tensor may be stored and
published.

From section 2.4, `Delta = l_K - u_e.(x_K - S)`, so

```
d(Delta)/d(u_e) = -(x_K - S)_perp
```

and the phase `exp(-j*k*Delta)` rotates at `k*|x_K - S|` radians per radian of
exit direction. Computed:

| `|x_K - S|` | phase-coherent exit-angle scale at 28 GHz | bins to resolve the sphere |
|---|---|---|
| 1.5 m | 65.1 millidegrees | 3.1e6 |
| 5 m | 19.5 millidegrees | 3.4e7 |
| 20 m | 4.9 millidegrees | 5.5e8 |
| 60 m | 1.6 millidegrees | 5.0e9 |
| 130 m | 0.75 millidegrees | 2.3e10 |

A HEALPix `nside = 16` bin is 3.66 degrees. **Accumulating complex amplitudes
into any publishable angular grid is wrong by five to seven orders of magnitude
in required resolution**, and the symptom is not noise, it is silent
cancellation: the interference term averages to zero inside the bin and the
result looks plausible while being exactly the incoherent answer with the wrong
normalisation.

Joint delay binning does not rescue it either. Phase stability inside a delay bin
needs `c*dtau << lam`, that is `dtau << 36 ps` at 28 GHz, which is a bandwidth
above the carrier.

This is the same physics as the finite-range problem of section 4.4, seen from
the angular side instead of the spatial side. It is also why 3GPP 38.901 models
the phase of a resolvable component as uniform rather than geometric.

**The resolution, and it is the design.**

- accumulate the **coherency matrix** `C_S`, that is power, per `(u_loc, u_ext, tau)`
  cell. This is smooth, compressible, and it is what section 12.3's storage
  estimates assume. If the tensor had to be coherent, none of those estimates
  would hold.
- keep the **coherent skeleton** as an explicit path list, restricted to paths
  passing the `sigma_L` coherence gate of section 7.7. Those are the paths whose
  geometry is accurate enough for the phase to mean anything, and there are few
  of them.
- generate coherent realisations when needed by drawing per-cell phases from the
  published `C_S`, in the 38.901 manner, and add the skeleton deterministically.

`DESIGN.md` already required exactly this split ("incoherent and coherent outputs
are reported separately because phase uncertainty can invalidate coherent sums
while leaving power bounds useful"). The propagation core has to honour it in the
estimator, not only in the report.

---

## 3. The monostatic loop, and why it is a shadow of the above

### 3.1 The transport chain, derived

Radiance transport from `S` through `K` interactions and back to `S`. Let
`I(u) = P_t*G_t(u)/(4*pi)` be the transmitted intensity and
`A_e = G_r*lam^2/(4*pi)` the receive aperture. Chaining irradiance, BSDF, and the
geometric term `G(x,y) = V(x,y)*cos(th_x)*cos(th_y)/|x-y|^2`:

```
dP_r^(K) = I(u_1) * A_e(u_K)
         * [cos(th_1_in)/r_1^2]
         * prod_{m=1..K} f_r(x_m; w_in, w_out)
         * prod_{m=1..K-1} G(x_m, x_{m+1})
         * [cos(th_K_out)/r_K^2]
         * dA_1 ... dA_K
```

The two end factors are the geometric term to a point, with no cosine at the
point because an antenna has no normal. Reciprocity of the chain is manifest in
the symmetry of that expression, which is a useful invariant to assert in tests.

**Consistency with the radar equation.** For `K = 1` monostatic, this reduces to
`dP_r = (P_t G_t G_r lam^2 /(4pi)^2) * f_r * cos^2(th) * dA / r^4`. Comparing with
`dP_r = P_t G_t G_r lam^2 sigma_0 dA / ((4pi)^3 r^4)` gives

```
sigma_0(w_i, w_s) = 4*pi*cos(th_i)*cos(th_s)*f_r(w_i, w_s)
```

Verified numerically to 12 significant figures. That identity is also the bridge
between the radar literature (which speaks `sigma_0`) and the rendering
literature (which speaks BRDF), and we will need it in both directions.

**Independent check on the same identity.** A Lambertian surface with albedo
`rho` has `f_r = rho/pi`. Energy conservation requires
`int_hemisphere sigma_0 dOmega = 4*pi*rho*cos(th_i)`, and substituting
`sigma_0 = C*cos(th_i)*cos(th_s)` gives `C = 4*rho`, hence
`sigma_0 = 4*rho*cos(th_i)*cos(th_s)`, which is the Lambert radar law and matches
`4*pi*cos*cos*(rho/pi)`. The two routes agree.

### 3.2 Why the loop cannot be inverted

The monostatic response is, structurally,

```
h(S,S) = sum over intermediate states b of h(S <- b) * Gamma_b * h(b <- S)
```

which is a **quadratic** (bilinear) functional of the one-way Green's function,
whereas `T_S` is **linear** in it. Knowing a quadratic form `q(h) = h^T A h` for a
single `A` does not determine `h`: the value is invariant under `h -> U h` for
any `U` in the complex-orthogonal group preserving `A`. The inverse problem has a
large continuous gauge symmetry, in the same family as phase retrieval. The
monostatic response therefore cannot reconstruct `h(S, X)` for an external `X`,
and no amount of frequency sweeping fixes the structure of the degeneracy.

This is the decisive argument for the reframing. It is not that the monostatic
loop is a worse estimator of the same thing. It is a different, strictly weaker
functional.

### 3.3 What the loop is still good for, and its measured cost

Keep it, because it is nearly free from the same trace and because whether
monostatic backscatter energy predicts `K_iso` is a genuine empirical question
that would be a publishable result either way.

**Measured, at Korenmarkt, 28 GHz, on 1.5e6 uniform rays.**

| Quantity | Adjoint escape record | Monostatic gather |
|---|---|---|
| deposit weight per ray | exit-bin solid angle `4.09e-3 sr` (HEALPix nside 16) | `A_e/r^2 = lam^2/(4 pi r^2)` |
| at `r` = 5 m | | `3.65e-7 sr`, ratio `8.9e-5` |
| at `r` = 20 m | | `2.28e-8 sr`, ratio `5.6e-6` |
| at `r` = 60 m | | `2.53e-9 sr`, ratio `6.2e-7` |
| fraction of rays retained within 3 interactions | **0.823 measured** | 0 by forward sampling, needs NEE |

The ratio column is not an estimator-efficiency claim, it is physics: the
monostatic return really is 50 to 60 dB below the one-way transfer because it
pays a second spherical spreading and is collected by an aperture of only
`lam^2/(4 pi)`. But it does have an estimator consequence. Gathering to a point
through a delta-BSDF has unbounded variance, whereas depositing into a
finite-solid-angle exit bin does not. Section 5.2.

**Verdict on "same rays, cost nearly unchanged".** The coordinator's claim is
correct and understated. The extension rays are literally identical. The adjoint
version needs no next-event estimation at all, because escape is detected as a
ray miss, which is a free by-product of the intersection test already performed.
The monostatic version needs one occlusion ray per vertex on top. Producing both
from one trace costs roughly 1.5x either alone, since `ray_test` is cheaper than
`ray_intersect`. Do both.

---

## 4. The free first hit

### 4.1 Why bounce one costs zero ray casts and zero shadow rays

Two separate savings, and they are usually conflated.

**No ray cast.** The first hit along direction `u` from `S` is `r(u)`, already
computed and stored by `raycast_mesh_depth.py`. The first bounce is a texture
fetch into `A_S`.

**No shadow ray.** In the monostatic gather, the return segment `x(u) -> S` is the
reverse of the segment `S -> x(u)` that produced the first hit, so
`V(x(u), S) = 1` identically. In the adjoint formulation the corresponding
statement is that the zero-bounce term needs no visibility test either: the atlas
already recorded which directions are sky. A conventional path tracer pays a
shadow ray at the first vertex. Here it is a lookup, and it is exact rather than
estimated.

The first-bounce term reduces to a quadrature over atlas cells with **zero Monte
Carlo variance**, which matters because it is the dominant term.

### 4.2 The deeper version of the same trick

If `C` is any first-hit point of the atlas, then `C` is visible from `S` by
construction. So the final gather from `C` to `S` is free for **any** path whose
last vertex is drawn from the atlas. That converts the monostatic 3-bounce case
`S -> A -> B -> C -> S` into a bidirectional connection where both endpoint
subpaths are free and only `B` is traced. That was the owner's sketch and it is
correct. Its sharper payoff appears in the deterministic specular branch, section
6.3, where it cuts an `N_planes^3` search to `N_visible^2 * N_planes`.

In the adjoint formulation the trick is simpler and stronger: `S` is one endpoint
and the other endpoint is a direction at infinity, so **only** the departure end
needs the atlas, and the exit end needs nothing at all.

### 4.3 What the atlas exactly determines, independent of any transmitter

This is the one statement about transferability that survives a hostile reviewer.

For a receiver at `S`, every arriving path arrives from some local direction
`k_hat`, and its **last** interaction point is at range `r(-k_hat)` along
`-k_hat`. That is the atlas entry, exactly. The atlas is therefore a complete and
exact description of the last-interaction geometry for **any** transmitter
anywhere. It is transmitter-independent by construction.

Stated as the precise transfer claim: **the support of the arrival-direction
distribution transfers exactly, the weights on that support do not.** A rooftop
base station and a co-located sounder produce different weights over the same
atlas cells. Anyone who claims more than this is overselling.

### 4.4 The finite-range caveat, which is worse than it first looks

The plane-wave parameterisation of `T_S` assumes the external source is far
enough that the incident field is plane over the region containing the
contributing exit points. Take that seriously and it fails badly.

For an exit point displaced by `delta` from `S` and a source at range `D`, the
incidence direction differs by about `|delta|/D`, and the phase error is about
`k*|delta_perp|^2/(2*D)`. At 28 GHz with `D = 100 m`:

- coherent validity needs `|delta_perp| << sqrt(lam*D/pi) = 0.58 m`
- incoherent validity needs `|delta| << D * (exit bin width) = 6.4 m` for a
  3.66 degree bin

A rooftop base station at 50 to 200 m is **never** far enough for coherent
plane-wave treatment at mmWave, and only marginally far enough for the incoherent
form.

The fix is the exit point, stored anyway. For a source at finite position
`x_src`, correct each escaping path individually:

```
u_ext_path = (x_src - x_K)/|x_src - x_K|
amplitude  -> 1/|x_src - x_K|   instead of the plane-wave normalisation
phase      -> exp(-j*k*|x_src - x_K|)  instead of exp(-j*k*u_e.x_K)
```

which is exact provided `D` exceeds the far-field distance of the individual
last-scattering patch, a few metres, not of the whole scene. So:

- publish the plane-wave `K_S(u_ext)` as the compressed, band-averaged,
  incoherent descriptor
- keep the exit-point path list as the exact finite-range operator
- publish alongside it `sigma_exit(u_ext)`, the transverse spread of exit points
  within each exit-direction bin, as the **validity flag** for the plane-wave
  reduction

`sigma_exit` is a new derived quantity and it is the honest way to tell a reader
which directions of the published tensor they may use as a plane wave.

---

## 5. The scattering model

### 5.1 The measure-zero problem, stated correctly

The owner's framing is right and worth making precise, because the usual sloppy
version ("specular paths do not exist") is false and a reviewer will say so.

**Proposition.** In a scene of finitely many planar facets with purely specular
reflection, the set of monostatic 2-bounce paths `S -> A -> B -> S` is finite,
and has measure zero in the 4-dimensional space of point pairs `(A,B)` on the
surface.

**Proof.** For an ordered pair of planes `(P_1, P_2)`, reflect `S` in `P_1` to get
`S_1`, then `S_1` in `P_2` to get `S_12`. The path exists iff the straight
segment from `S_12` to `S` meets `P_2` in its valid facet region, and the
back-traced segment from `S_1` meets `P_1` in its. That is a single line, so
there is at most one candidate per ordered plane pair, hence at most
`N_pl*(N_pl-1)` paths in total. A finite set has measure zero in a
4-manifold. QED.

So the paths **do** exist and carry finite power. Two things are actually wrong:

1. **They are unfindable by forward Monte Carlo.** Sample a direction at `S`,
   reflect specularly at `A`, and the probability that the twice-reflected ray
   passes through the point `S` is exactly zero. No finite-variance MC estimator
   with a delta BSDF finds them. This is the real content of "measure zero" and
   it is a statement about the sampling measure, not about physics.
2. **They are geometrically brittle.** A one-degree facet-normal error creates or
   destroys a path. Given the twin's pose covariance, that brittleness is not
   acceptable as the primary mechanism.

Degenerate configurations make it worse in an interesting way. Two parallel walls
give only the degenerate perpendicular retro-reflection, which is a 1-bounce path
in disguise. A 90-degree dihedral composes to a rotation by pi about the edge, so
the candidate is again a single line unless `S` lies on the edge, in which case
the solution set becomes a continuum. That near-degeneracy is exactly why corner
reflectors have enormous monostatic RCS, and it means the monostatic response is
dominated by configurations where the estimator is least stable.

### 5.2 The adjoint formulation dissolves the problem entirely

This is the strongest technical argument for the reframing and it belongs here
rather than in section 2.

A purely specular escaping ray from `S` in direction `u_0` lands in exactly one
exit direction `u_e(u_0)`, and the map `u_0 -> u_e` is piecewise smooth. The
distribution of exit directions is therefore the pushforward of the departure
distribution, absolutely continuous wherever the map is a local diffeomorphism,
with Jacobian equal to the ray-tube divergence. Binning exit directions with
finite width, every specular ray deposits with finite probability.

**Connecting to a point is measure zero. Binning a direction is not.** The
pathology is a property of the monostatic target, not of specular BSDFs.

Consequences, all good:

- no image-source enumeration is needed in the adjoint branch, plain forward
  shoot-and-bounce works
- no manifold-walk machinery is needed for the primary product
- specular, glossy and diffuse vertices coexist in one estimator without special
  cases
- what remains are caustics, where the Jacobian vanishes and the binned estimate
  spikes. Handle by bin-width control and by reporting the fraction of energy in
  bins whose neighbours differ by more than a set factor

### 5.3 Recommended BSDF: microfacet, in its geometric-optics Kirchhoff form

Use the Torrance-Sparrow / Cook-Torrance microfacet form

```
f_r(w_i, w_o) = F(th_d) * D(h) * G(w_i, w_o) / (4 * cos(th_i) * cos(th_o))
```

with `h` the half vector, `th_d` the angle between `w_i` and `h`, `F` the Fresnel
coefficient (or the ITU-R P.2040 slab coefficient for finite thickness), `G` the
Smith shadowing-masking term, and `D` the Beckmann slope distribution

```
D(h) = exp(-tan^2(th_h)/m^2) / (pi * m^2 * cos^4(th_h))
```

parameterised by the RMS slope `m = sqrt(2) * sigma_h / l_c` for a Gaussian
surface autocorrelation of correlation length `l_c`. In `sigma_0` form, using the
bridge derived in section 3.1,
`sigma_0 = 4*pi*cos(th_i)*cos(th_o)*f_r = pi * |F|^2 * D(h) * G`.

Three normalisations checked here rather than taken on trust, because section 7.2
depends on them:

- `integral of D(h)*cos(th_h) dOmega_h = 1`. Substituting `w = tan(th_h)` turns
  the integral into `(2/m^2) * integral of exp(-w^2/m^2) * w dw = 1`.
- `D(0) = 1/(pi*m^2)`, which is the finite peak that makes the diffuse branch of
  the admissible bound in section 7.2 exist at all. It exists only if the
  material prior bounds `m` away from zero, so **the roughness prior must carry a
  lower bound on RMS slope** or the bound is vacuous.
- `m = sqrt(2)*sigma_h/l_c` follows from the slope variance of a Gaussian-ACF
  surface, `-sigma_h^2 * rho''(0)` with `rho(r) = exp(-r^2/l_c^2)`, giving
  `rho''(0) = -2/l_c^2`.

**Why this and not the directive lobe.** Four reasons, in order of importance.

1. **It is reciprocal.** `f_r(w_i,w_o) = f_r(w_o,w_i)` holds identically because
   `h` is symmetric under exchange and `G` is built symmetric. Reciprocity is not
   a nicety here, it is the theorem the entire adjoint formulation rests on. A
   non-reciprocal BSDF makes `T_S` ill-defined.
2. **Its parameterisation is physical rather than fitted, in the rough limit
   only.** The geometric-optics (stationary-phase) limit of the Kirchhoff
   approximation produces the same angular structure. As printed in the radar
   literature, with `q = k*(w_o - w_i)` the scattering vector and `m_x, m_y` the
   RMS slopes,

   ```
   gamma_pq = (1/(2*m_x*m_y)) * |q/q_z|^4 * |U_pq|^2
              * exp{ -(1/(2*q_z^2)) * [ (q_x/m_x)^2 + (q_y/m_y)^2 ] }
   ```

   with the stationary-phase slopes `Z_x = -q_x/q_z` and `Z_y = -q_y/q_z`. Since
   `q` is parallel to the half vector, `q_z/|q| = cos(th_h)`, so `|q/q_z|^4` is
   `1/cos^4(th_h)` and the exponential is the slope distribution evaluated at
   exactly the facet that reflects `w_i` into `w_o`. That is the microfacet form.

   **Four hedges, all of which matter.** The equivalence is asserted in the
   literature in the **large-roughness limit** and is stated to break down for
   polished surfaces. The `1/cos^4` identification is my algebra, not a quoted
   result. The step from `sigma_0` to a BRDF rests on
   `sigma_0 = 4*pi*cos(th_i)*cos(th_o)*f_r`, which I derive and verify
   numerically in section 3.1 rather than take from a citation, precisely because
   the literature restatements of it are not clean. And **the shadowing-masking
   term `G` is not produced by the GO derivation at all**, which explicitly
   ignores shadowing and multiple scattering. `G` is bolted on to restore energy
   conservation. Write "the microfacet form is the GO-Kirchhoff result in the
   large-roughness limit, up to a bolted-on shadowing term and a normalisation
   convention", never "the microfacet BRDF is the GO-Kirchhoff result".
3. **It is parameterised by what the twin already estimates.** `sigma_h` and
   `l_c` are exactly the two roughness quantities `DESIGN.md` commits to
   carrying, and the same `sigma_h` drives the specular split below. The
   identification of the microfacet roughness parameter with the physical RMS
   slope `sqrt(2)*sigma_h/l_c` is supported in the literature and is also
   derivable directly, as above.
4. **It is energy conserving** with the Smith `G`, which the directive model is
   only by explicit normalisation. Note reason 2: this is a repair, not a
   derivation, and it should be labelled as such in the provenance dictionary.

**Where it is invalid, and this cuts both ways.** The honest position is that our
surfaces sit between the two regimes where a closed form exists.

- **Too smooth for GO.** The stationary-phase limit needs
  `k*sigma_h > 10*|cos(th_i) + cos(th_s)|`, which at backscatter and normal
  incidence is `k*sigma_h > 20`, that is `sigma_h > 34 mm` at 28 GHz. Our
  materials run `k*sigma_h` from 0.03 (glass) to 3.5 (cobblestone) at 28 GHz and
  up to 7.5 at 60 GHz. **No building material we model meets the strict GO
  condition.** The Kirchhoff integral also wants `k*l_c > 6`.
- **Too rough for single-scatter Kirchhoff.** For brick with recessed mortar at
  60 GHz and cobblestone at any mmWave band, the surface is a random array of
  scatterers with steep slopes, and multiple scattering within the roughness
  matters. Add a Lambertian pedestal with an albedo calibrated per material class
  and flag those as `roughness_model: pedestal`, in the same spirit that
  `materials.py` already flags `"status": "engineering approximation, not ITU-R P.2040"`.

So the microfacet form is chosen **because it is reciprocal and energy
conserving**, which the adjoint formulation requires, and because its parameters
carry physical meaning through the GO correspondence. It is an interpolant
between two limits, not an exact solution in our regime, and its parameters have
to be calibrated against measurement exactly as the effective-roughness approach
calibrates `S` and `alpha_R`. Claiming it is "the derived one" and the directive
lobe is "the fitted one" would be an overclaim, and this document does not make
it.

One further caveat if the polarimetric output is used: GO-Kirchhoff predicts
identically **zero** in-plane cross-polarisation. Any cross-pol in the diffuse
branch has to come from an explicit XPD term, as Sionna's `xpd_coefficient` and
`materials.py`'s `RadioMaterialParameters` already provide for, and it is not
predicted by the model.

### 5.4 The specular and diffuse split, from Rayleigh roughness

Keep the existing closure in `mmwave.py`, which is right. Define
`g = 4*pi*sigma_h*cos(th)/lam` explicitly at first use in the code as well,
because the symbol `g` is used for different quantities across this literature,
including for the square of the one defined here, and the collision is silent.

The coherent specular **amplitude** reduction is `rho_s = exp(-g^2/2)`, so the
coherent **power** fraction is `exp(-g^2)` and the diffuse amplitude coefficient
is `S = sqrt(1 - exp(-g^2))`, which is exactly
`roughness_to_scattering_coefficient`. The amplitude-versus-power distinction is
where this is usually got wrong. Two independent confirmations that the split
above is the right way round: the Ament (1953) form multiplies the perfect
conductor field coefficient `-1`, hence field, and Recommendation ITU-R P.2146-0
equation (11) carries the square on the power quantity,
`exp{-(2*k*sigma*cos(th_i))^2} = exp(-g^2)`. Note also that
`2*(k*sigma*cos(th))^2 = 8*pi^2*sigma^2*cos^2(th)/lam^2 = g^2/2`, so the two
common ways of writing it agree identically (verified to 7e-15 relative over
`sigma` in [1 mm, 10 cm] and `th` in [0, 85] degrees).

**Attribution, since it is routinely mis-stated.** Ament's 1953 paper gives the
form but credits Pekeris and MacFarlane, so write "the Ament form", not "derived
by Ament". Beckmann and Spizzichino is 1963, a decade later, and Rayleigh
supplies the roughness *criterion*, not this exponential factor. The factor may
in fact first appear in an NRL report by Brown and Miller in 1974.

**Angle convention: define your own and do not inherit one.** Maritime work
writes the factor with the sine of the grazing angle, mmWave and optics with the
cosine of the incidence angle. They are the same quantity. Which one the 1953
paper uses could not be checked, so the code should define the angle explicitly
and cite Ament for the factor alone.

At large `g` the Miller-Brown correction `rho_s = exp(-g^2/2)*I_0(g^2/2)` is the
usual alternative and should be a selectable mode, with two caveats that matter
here. First, using `I_0(y) ~ exp(y)/sqrt(2*pi*y)`, it decays **algebraically** as
`1/(g*sqrt(pi))` rather than Gaussian-fast: at `g = 10`, Ament gives 1.9e-22 and
Miller-Brown gives 5.66e-2 against the asymptote 5.64e-2, a difference of twenty
orders of magnitude. Second, **Miller-Brown is not a Gaussian-surface result**.
It assumes a height `zeta = A*cos(phi)` with `A` Gaussian and `phi` uniform,
which is a heavy-tailed elevation distribution, and that assumption has been
attacked in the literature. So the two are not "the same model with a
correction", they are different surface statistics, and which one is right for a
brick wall is an empirical question this design does not settle. Default to
Ament, expose Miller-Brown, and report the difference at 60 GHz where it is
largest.

**ITU-R P.2040-4 does not help here, and that is worth stating.** Reading the
in-force text, it contains no rough-surface scattering model of this kind: no
Rayleigh criterion, no RMS height for facades, no diffuse scattering
coefficient, and section 2.2.2 explicitly assumes layers with smooth, planar,
parallel surfaces. Its roughness terms are a per-metre waveguide attenuation for
corridors and tunnels (section 2.2.3.1, equation 48) and a deterministic periodic
frequency-selective surface (section 2.3), neither of which applies to a facade
ray trace. P.2040-3 is the same, so this is a longstanding gap and not a
regression. `materials.py` is therefore right to flag its roughness closure as
`"not ITU-R P.2040"`, and P.2146-0 is the better ITU anchor for the roughness
factor itself.

**Superseded illustrative split at the three bands**, computed here. The
`sigma_h` column was an engineering prior invented for this table and it has
since been replaced by `config/surface_roughness.json`, whose provenance is in
`ROUGHNESS.md`. **The table below is kept only because it shows the shape of the
frequency-and-incidence interaction. Do not take numbers out of it.** Almost
every entry is one to two orders of magnitude too rough: the metrology says a
brick face is 0.024 to 0.095 mm rather than the millimetres assumed here, and
glass, painted render, as-cast concrete, wood and dressed stone all land between
0.001 and 0.3 mm. `|rho_s|^2` is the coherent power fraction, `S` the diffuse
amplitude coefficient.

| Material (`sigma_h`) | 28 GHz, normal | 28 GHz, 70 deg | 39 GHz, normal | 60 GHz, normal | 60 GHz, 70 deg |
|---|---|---|---|---|---|
| glass 0.05 mm | 0.997 / 0.06 | 1.000 / 0.02 | 0.993 / 0.08 | 0.984 / 0.13 | 0.998 / 0.04 |
| metal cladding 0.10 mm | 0.986 / 0.12 | 0.998 / 0.04 | 0.974 / 0.16 | 0.939 / 0.25 | 0.993 / 0.09 |
| painted plaster 0.30 mm | 0.883 / 0.34 | 0.986 / 0.12 | 0.786 / 0.46 | 0.566 / 0.66 | 0.936 / 0.25 |
| wood 0.50 mm | 0.709 / 0.54 | 0.961 / 0.20 | 0.513 / 0.70 | 0.206 / 0.89 | 0.831 / 0.41 |
| concrete 0.80 mm | 0.414 / 0.77 | 0.902 / 0.31 | 0.181 / 0.90 | 0.018 / 0.99 | 0.623 / 0.61 |
| asphalt 1.0 mm | 0.252 / 0.87 | 0.851 / 0.39 | 0.069 / 0.97 | 0.002 / 1.00 | 0.477 / 0.72 |
| brick + mortar 2.0 mm | 0.004 / 1.00 | 0.525 / 0.69 | 0.000 / 1.00 | 0.000 / 1.00 | 0.052 / 0.97 |
| cobblestone 6.0 mm | 0.000 / 1.00 | 0.003 / 1.00 | 0.000 / 1.00 | 0.000 / 1.00 | 0.000 / 1.00 |

The Rayleigh smoothness threshold `sigma_h < lam/(8*cos(th))` sits at 1.34 mm
(28 GHz), 0.96 mm (39 GHz) and 0.62 mm (60 GHz) at normal incidence. Two
consequences worth stating in the paper:

- grazing incidence makes everything smoother, and street canyons are grazing, so
  the specular skeleton survives along the street even at 60 GHz
- the first bullet of an earlier revision said that at 60 GHz almost every
  outdoor material is rough at normal incidence and the specular skeleton
  collapses. On the measured heights that is false. At 0.15 mm of render the
  coherent power fraction at 60 GHz normal incidence is 0.87, not 0.57, and a
  brick face is above 0.99

That frequency-and-incidence interaction is a result in its own right and it
falls straight out of the machinery. Its magnitude is not, and the magnitude is
what `ROUGHNESS.md` had to settle.

**The face and the wall are different objects, and the table above conflates
them.** A profilometer measures a prepared monolithic patch, which is what almost
every published RMS height is. A metre-scale facade patch, which is what a
fishnet face actually stands for, additionally carries mortar joints, course
relief, block relief, pointing, sills and reveals at centimetre pitch. The row
labelled "brick + mortar 2.0 mm" above is trying to be a wall number and the
literature's brick numbers are face numbers, so they were never comparable.
`config/surface_roughness.json` splits them into `brick_face` and
`brick_wall_with_mortar_joints`, keeps `rms_height_mm` as the face statistic in
both, and records the wall structure in a separate `periodic_component` block
rather than folding it into the height. Any brick roughness quoted anywhere
downstream has to say which of the two it means.

**And for eight of the sixteen classes the Rayleigh closure is not the right
model at all.** A mortar grid, a sett pavement, corrugated cladding or a roof
tile course reradiates into discrete grating orders at
`sin(th_m) = sin(th_i) + m*lam/d`, not into a broad lobe. Brick coursing at
75 mm pitch supports 15 propagating orders at 28 GHz and 31 at 60 GHz.
`SurfaceRoughnessPrior.specular_power_fraction` raises for those classes unless
the caller passes `allow_periodic=True`, which is deliberate: the refusal keeps
that gap visible instead of letting it be absorbed into a plausible-looking
scattering coefficient. Section 5.5's mapping and this section's split therefore
apply to the random-roughness classes, and the periodic classes need their own
treatment. That treatment is under construction rather than absent
(`semantic_twin/floquet.py`, `masonry.py`, `rcwa.py`, `kirchhoff.py`), but at the
time of writing nothing in the propagation path imports it, so a scattering model
assembled today still has no grating term in it.

### 5.5 Tying roughness to the semantic posteriors

`config/semantic_concepts.json` already carries a Bernoulli `rough` attribute and
a Dirichlet over materials. The mapping is:

```
sigma_h | material, attributes  ~  LogNormal(mu_mat + beta*(P(rough) - 0.5), s_mat)
l_c     | material              ~  LogNormal(mu_lc_mat, s_lc_mat)
```

with `(mu_mat, s_mat, mu_lc_mat, s_lc_mat)` a per-material-class table stored in
the same provenance style as `config/itu_p2040_4.json`, explicitly labelled as an
engineering prior with no ITU standing. The material Dirichlet then induces a
mixture over `sigma_h`, and the scene ensemble of `DESIGN.md` samples it. Do not
collapse to a MAP roughness. The specular fraction `exp(-g^2)` is exponential in
`sigma_h^2`, so it is exactly the kind of nonlinearity where the mean of the
function is far from the function of the mean.

**Status.** Half of this shipped. `config/surface_roughness.json` and
`SurfaceRoughnessLibrary` supply `(mu_mat, s_mat)` as `rms_height_mm` and
`log_standard_deviation` for sixteen classes, each with an `evidence_grade`, a
plausible range and a `concepts` list linking it back to the prompts in
`config/semantic_concepts.json`, and `SurfaceRoughnessPrior.sample` draws the
lognormal rather than returning the median. Correlation length is present where
the literature gives one and marked `not_reported` otherwise, so
`(mu_lc_mat, s_lc_mat)` is not a distribution yet. **The
`beta*(P(rough) - 0.5)` shift is not implemented anywhere.** The `rough`
Bernoulli attribute exists in the taxonomy and accumulates in `evidence.py`, but
nothing reads it into a roughness prior, and no value of `beta` has been chosen
or defended. Treat the shift as an open proposal, not as a described behaviour.

A concrete check to run before trusting any of this, restated on the measured
priors rather than on the invented ones an earlier revision used. The old version
said a posterior that cannot separate painted plaster from bare concrete cannot
pin the 60 GHz specular fraction to better than a factor of 30, from `sigma_h`
of 0.3 against 0.8 mm. Both numbers were wrong: `config/surface_roughness.json`
puts painted render and as-cast concrete at the same 0.15 mm, so that particular
confusion now costs nothing at all.

The ambiguity that does still bite is inside concrete, between
`concrete_as_cast_smooth` at 0.15 mm and
`concrete_board_marked_or_exposed_aggregate` at 0.6 mm. The coherent power
fraction at normal incidence goes 0.97 against 0.61 at 28 GHz and 0.87 against
0.10 at 60 GHz, so a factor of 1.6 at FR2 and 8.4 at 60 GHz. That is a real
sensitivity and it is a finish distinction a segmenter can plausibly be asked to
make from imagery, which the render-against-concrete distinction was not. At
70 degrees the same pair is 0.94 against 0.77 at 60 GHz, so the canyon geometry
absorbs most of it. Report the concrete-finish split as the dominant
random-roughness uncertainty, and note that it is smaller than the periodic-class
gap above it.

### 5.6 The Degli-Esposti directive model, and why it is a comparison mode

Sionna implements the directive scattering pattern of Degli-Esposti et al. as

```
f_s(w_i, w_o) = [(1 + cos(psi_R))/2]^alpha_R / F_alpha(th_i)
```

with `psi_R` the angle from the specular direction and `F_alpha` the
normalisation over the scattering hemisphere. Reading
`sionna/rt/radio_materials/scattering_pattern.py` confirms
`F_alpha = 2^-alpha * sum_j binom(alpha,j) * I_j` with
`I_j = int_hemisphere cos^j(psi_R) dOmega`. I verified the even-`j` case
analytically: `cos^j(psi_R)` is antipodally symmetric for even `j`, so any
hemisphere captures exactly half the full-sphere integral `4*pi/(j+1)`, giving
`I_j = 2*pi/(j+1)` independent of `th_i`, which is exactly what the code
computes and comments. So the normalisation is
`F_alpha = int_hemisphere [(1+cos psi_R)/2]^alpha dOmega`, and the pattern
integrates to 1 in `dOmega` (not `cos*dOmega`). The Lambertian entry
`cos(th_o)/pi` confirms it.

Converting to a BRDF: if the scattered power fraction is `rho_d`, then

```
f_r(w_i, w_o) = rho_d * f_s(w_i, w_o) / cos(th_o)
```

which for the Lambertian pattern gives `rho_d/pi` as it must.

**The problem.** `cos(psi_R)` is symmetric under exchanging `w_i` and `w_o`, as a
two-line expansion shows, but `F_alpha` depends on `th_i` only and there is a
bare `1/cos(th_o)`. So

```
f_r(w_i,w_o)/f_r(w_o,w_i) = F_alpha(th_o)*cos(th_i) / (F_alpha(th_i)*cos(th_o))
```

which is not 1. **The directive model as specified and as implemented in Sionna
is not reciprocal.** For a conventional forward tracer that is a modelling
imperfection. For an adjoint formulation built on Lorentz reciprocity it is a
correctness bug: `T_S` computed by forward tracing would not equal the transfer
tensor of the reciprocal experiment.

Recommendation: microfacet as primary, directive lobe available behind a flag
purely so the Sionna cross-check of section 11.5 compares like with like, with
the non-reciprocity documented in the provenance dictionary.

### 5.7 Out-of-view materials, and what the real gap is

`B` in `S -> A -> B -> ...` is a raycast into the tile mesh, not an inference
problem. Do not build an ML scene-completion programme around it. The mesh knows
where `B` is and what its normal is.

The real gap is narrower and sharper: **out-of-view surfaces have no street-level
image evidence for material or roughness.** Measured at Korenmarkt, on 1.5e6
rays into the 130 m mesh:

| Quantity | Measured |
|---|---|
| distinct primitives directly visible from `S` | 4,898 of 157,744, i.e. **3.1 % of the mesh** |
| order-2 vertices landing on a directly visible primitive | 82.6 % |
| order-3 vertices landing on a directly visible primitive | 72.8 % |
| order-4 vertices landing on a directly visible primitive | 66.7 % |

So at three interactions roughly **27 % of vertices have no panorama evidence**.
That is a real uncertainty, and it is not catastrophic, which is exactly the
argument for marginalising rather than inventing.

Four things to do, in order.

1. **Use the tile texture.** The in-house 3D Tiles are textured photogrammetry.
   `B` is not image-less, it has aerial and oblique imagery at roughly 5 to 20 cm
   GSD. Run the same SAM concept catalogue over synthetic renders of the tile
   mesh from viewpoints that see `B`, and feed the result into the same
   `EvidenceAccumulator` with a heavily discounted `ObservationQuality`. This is
   the single largest recoverable gain and it needs no new modelling.
2. **Hierarchical spatial prior.** Where the texture is inadequate, condition the
   material Dirichlet for a surface on the observed materials of the same
   building and its neighbours, with the hyperprior fitted to the visible
   population of the same city. Facades of one building are correlated.
3. **Marginalise, and report.** Sample out-of-view materials from the posterior
   in the scene ensemble and publish the induced spread on `K_iso`, `M_S` and
   the exposure percentiles. Report the fraction of retained path energy that
   passes through at least one evidence-free vertex. Both numbers are free from
   the trace, since each vertex is already tagged with its primitive id.
4. **Bound it.** Recompute with all out-of-view materials set to the highest and
   lowest plausible albedo in the class. The interval is a genuine bound, not a
   confidence interval, and reviewers accept bounds.

### 5.8 The analytic specular `B` construction

Worth recording, and worth keeping for one specific purpose.

For a pure specular chain `S -> A -> B -> C -> S`, reflecting the incident
direction at `A` gives a line, reflecting by reciprocity at `C` gives a second
line, and `B` is their intersection. The required normal at `B` follows from
`d_out = d_in - 2*(d_in . n)*n`, so `d_in - d_out = 2*(d_in . n)*n`, hence

```
n_B  proportional to  d_AB - d_BC
```

which is the coordinator's statement, and it is correct. The closest approach
between two skew lines is a physical residual, and the angle between the required
`n_B` and the actual mesh normal is a second one.

**Is it worth it as a prefilter?** Split the answer.

- In the **adjoint** formulation, no. There is no endpoint to connect to, so
  plain shoot-and-bounce finds specular chains without help (section 5.2).
- In the **monostatic** deterministic branch, yes, and it is not a prefilter, it
  is the method. Nothing else finds those paths.
- As an **importance-sampling guide** for near-specular rough chains, it is the
  right idea and it has a name. The construction above is a first guess for a
  Newton iteration on the half-vector constraint (Walter et al. 2009), and the
  stochastic version that connects two fixed endpoints through near-specular
  vertices is specular manifold sampling (Zeltner, Georgiev and Jakob 2020). That
  is worth having only if the monostatic loop turns out to matter, which section
  3.2 says it should not. Park it.

It is exact only for pure specular. Finite roughness turns the intersection point
into a region whose angular extent is the lobe width, so the construction gives
the centre of the region and nothing about its measure.

---

## 6. Search over patch pairs versus shooting rays

### 6.1 The complexity, honestly

Take the atlas at 0.5 degree resolution: about 2.6e5 cells, of which roughly 77 %
are non-sky at Korenmarkt (measured), so `N` is about 2.0e5.

Brute-force pair enumeration is `N^2 = 4e10` pairs. Each surviving pair needs one
occlusion ray. On this box, measured, `ray_test` on the real mesh runs in the
tens of Mray/s. Even at 100 Mray/s that is 400 s per location per bounce order,
before any of the other work, and it must be repeated at every panorama location.
At 1 degree resolution it is `6.4e8` pairs, still 6 s of pure occlusion testing
for a term that Monte Carlo gets in milliseconds.

What actually prunes it, and by how much:

| Prune | Effect | Verdict |
|---|---|---|
| back-facing test `n_A.(B-A) > 0` and `n_B.(A-B) > 0` | kills 50 to 75 % | cheap, does not change the order |
| reciprocity, count unordered pairs | factor 2 | see note below |
| lobe admissibility cone | weak for realistic lobes | a directive lobe with `alpha_R = 4` is 47 degrees at half power, `alpha_R = 10` is 30 degrees. Microfacet lobes for `sigma_h` above 0.5 mm at 60 GHz are similar. There is no narrow cone to exploit except on glass and metal |
| hierarchical clustering with a refinement oracle | genuine, `O(N)` links for a target error | this is hierarchical radiosity, and it works, but it needs a conservative error bound per link and it is a lot of machinery |

**Note on the reciprocity factor of 2, because it is more interesting than a
bookkeeping saving.** For each unordered pair `{A,B}` the paths `S->A->B->S` and
`S->B->A->S` have identical length and, by BSDF reciprocity, identical complex
amplitude. In a coherent monostatic sum they therefore add in phase, giving a
factor 2 in amplitude and 4 in power relative to one of them, and a factor 2
relative to an incoherent sum over both. This is coherent backscattering, the
same weak-localisation enhancement that produces the opposition effect in optics,
and it applies to every scattering order at or above 2 while single scattering is
not enhanced. The enhancement survives ensemble averaging, unlike speckle.

The condition is stringent. For a source-receiver offset `d`, the phase mismatch
between reciprocal partners is `k*d.(u_1 - u_K)`, which is `O(k*|d|)` for generic
first and last directions, so the enhancement holds only for
`|d| << lam/(2*pi)`, about 1.7 mm at 28 GHz. Exactly co-located, which is our
case, and no real bistatic link ever.

Three details worth carrying, because they bound how much of this we may claim.

- **The observable enhancement is not always 2, and measured values are well
  below it.** Theory gives 2 in both parallel channels (linear co-polarised and
  helicity-preserving) and a reduced factor in the crossed channels. What is
  special about the helicity-preserving channel is experimental, not theoretical:
  single scattering flips helicity, so it is the one channel where the clean 2 is
  measurable. In practice the enhancement is diluted by single scattering, which
  has no reverse partner. Reported radar values: about 1.5 to 1.6 for dry snow at
  17.2 GHz and about 1.35 at X band. So budget the monostatic anomaly at roughly
  1.3 to 3.0 dB and **measure it in our own scene** rather than assuming 3 dB.
- **The cone width** is `FWHM` of order `0.7/(k*l_star)` with
  `l_star = l/(1 - <cos(th)>)` the transport mean free path. For a street canyon
  with `l_star` of order tens of metres, that is microradians, which is another
  way of seeing why only exact co-location is on the peak.
- **Radio-frequency precedent exists, but not in urban propagation.** The
  measured cone has been reported in bistatic Ku and X band radar over dry snow,
  and the planetary coherent-backscatter opposition effect is long established.
  Closest to radio engineering, the EMC reverberation-chamber "enhanced
  backscatter constant" is theoretically exactly 2 and is used as a chamber
  quality metric. A literature check found **no instance of coherent
  backscattering being discussed in urban, cellular or indoor propagation
  modelling**. That is a statement about what was found, not a proof of absence,
  and it is a reason to derive the effect here from the reciprocal-pair phase
  condition (as done above) rather than to lean on a citation.

### 6.2 Shoot and gather, with numbers

Monte Carlo, adjoint version, per sample:

- sample `u_0` from the atlas with a pdf proportional to `Om_c` times an albedo
  and cosine estimate, cost 0 rays
- at each vertex sample the microfacet lobe and trace one extension ray
- escape is a ray miss, cost 0 extra rays

So a depth-`L` sample costs `L-1` extension rays plus zero gathers. For `L = 3`
that is 2 rays. At `1e6` samples, 2e6 rays, and at the measured 14.5 Mray/s on
the real 157k-triangle mesh, **0.14 s per panorama location on four cores**.

That is four orders of magnitude below brute-force pair enumeration and about
the same as a well-implemented hierarchical radiosity link set, without the error
oracle. There is no contest.

### 6.3 Where search genuinely wins, and it is not over pixels

Enumerate over **planes**, not pixels, and only for the deterministic specular
delta term of the monostatic branch (the branch that MC cannot sample at all,
section 5.1).

Extract planar clusters from the mesh. For a 130 m Korenmarkt scene, order 500
distinct planes, of which order 50 to 80 are directly visible from `S`.

| Order | Naive enumeration | With the atlas restriction | Reduction |
|---|---|---|---|
| `K = 2`, pairs `(P_A, P_B)`, both visible | `500^2 = 2.5e5` | `50^2 = 2.5e3` | 100x |
| `K = 3`, `A` and `C` visible, `B` anywhere | `500^3 = 1.25e8` | `50*500*50 = 1.25e6` | 100x |

Each candidate is a closed-form image-source solve, roughly 100 flops, and only
the survivors need occlusion rays. 1.25e6 candidates vectorise to well under a
second.

**This is where the owner's "A and C are panorama pixels" insight has real
teeth**, and it is worth saying so clearly, because the same insight buys much
less in the Monte Carlo branch where importance sampling was already doing the
work.

### 6.4 Recommendation

- **Adjoint branch, all orders, all BSDFs: Monte Carlo shoot-and-escape.** No
  search, no next-event estimation, no image method. Combine BSDF sampling with
  next-event estimation toward the visible sky through multiple importance
  sampling with the balance heuristic when variance in the sky-lit directions
  demands it.
- **Monostatic branch, diffuse part: Monte Carlo shoot-and-gather**, one
  occlusion ray per vertex, sharing the same extension rays.
- **Monostatic branch, specular delta part: deterministic plane enumeration**
  restricted by the atlas as in the table above.
- **Pixel-pair enumeration: rejected.**

---

## 7. The dynamic-range prune, and level of detail

### 7.1 Range laws, derived, and the exponent is not what reflex says

The coordinator's first message proposed `40*log10(d)`. The correction proposed
`20*log10(d)` for extended surfaces. Both are right in their own regime, and both
are wrong for the adjoint formulation. Here is the full table, derived and
verified numerically.

**Monostatic, two-way.** For a fixed solid-angle cell `Om_c` at range `R`, an
extended beam-filling surface presents `dA = Om_c*R^2/cos(th)`, so substituting
`sigma = sigma_0*dA` into the radar equation,

```
P_r = P_t*G_t*G_r*lam^2*sigma_0*Om_c / ((4*pi)^3 * R^2 * cos(th))
```

which falls as `R^-2`. A discrete target whose RCS does not grow with range keeps
the `R^-4` of the radar equation. Verified numerically against the independent
transport chain of section 3.1: extended gives exactly `-20*log10(R/R_0)` and
discrete exactly `-40*log10(R/R_0)` over 10 to 160 m.

**Adjoint, one-way.** For a plane wave from `u_ext` scattered into `S`,
`|E_S/E_0|^2 = sigma/(4*pi*R^2)`. Substituting the same two cases:

```
extended, per cell:  |T|^2 = sigma_0*Om_c/(4*pi*cos(th))     -> R^0, no decay at all
discrete, per cell:  |T|^2 = sigma/(4*pi*R^2)                -> R^-2
```

Verified numerically: the extended one-way per-cell contribution is constant to
machine precision from 10 m to 640 m.

**Summary, and this is the result.**

| Regime | Monostatic per cell | Adjoint per cell |
|---|---|---|
| extended, beam-filling (facade, road, roof, ground, water) | `R^-2` | **`R^0`** |
| discrete, sub-beam (bollard, sign, pole, person, cable, bicycle) | `R^-4` | `R^-2` |

The one-way versus two-way factor of 2 in the exponent is exactly the reciprocity
structure.

**"Per cell" means per cell of the departure atlas, a fixed solid angle seen from
`S`.** Be precise about this, because the whole prune argument turns on it. A
distant facade occupies few departure cells, so its contribution to any
solid-angle-integrated quantity such as `K_iso` or the total absorbed power does
fall as `R^-2`, since `dOmega = A*cos(th)/R^2`. What does not fall is its
contribution **within** the cells it does occupy. The validity condition is that
the facade still fills a departure cell: for a 0.5 degree cell (8.7e-3 rad) a
30 m facade fills a cell out to 3.4 km, so the condition holds everywhere in a
city.

The practical consequence: **in the adjoint formulation, range is not a valid
prune criterion for facades.** The sound criterion is the swath's **solid angle**,
which is what section 7.2's bound uses and what section 7.5 measures. What
otherwise prunes is occlusion, accumulated per-bounce loss, and at 60 GHz
atmospheric absorption.

**The semantic layer earns its keep here.** The regime is a per-direction
property that segmentation already provides. The dividing line is whether the
object's angular extent exceeds the culling cell: for a cell of angular width
`w_cell`, the transition range is `R_t = D_obj/w_cell`, so a 0.2 m bollard leaves
the extended regime at 23 m for a 0.5 degree cell. `config/semantic_concepts.json`
already separates `kind: surface` from `kind: object`, which is precisely this
split. Build the prune on `kind` plus a per-class characteristic size, not on one
global law.

Vegetation is a third regime: a volume scatterer with extinction, needing
ITU-R P.833 rather than a surface `sigma_0`, as `DESIGN.md` already notes.

### 7.2 The admissible bound

For pruning to be sound rather than heuristic, discard a swath only when a
provable **upper** bound on its contribution falls below the threshold.

**Specular, one bounce, monostatic.** The monostatic specular return off a plane
requires normal incidence, so the path is the perpendicular and its length is
exactly `2*d`. For any passive surface `|Gamma| <= 1`. Hence

```
g_spec  <=  (lam/(8*pi*d))^2
```

which is tight and provable with no material knowledge at all.

**Diffuse, per cell.** `g_diff(c) <= (lam^2/(4*pi)^2) * f_max * cos(th) * Om_c/R_c^2`
where `f_max` is the maximum peak BRDF over all admissible materials in the
cell's Dirichlet support. `f_max` is finite because the microfacet peak is
`|F|*D(0)*G/(4 cos cos)` with `D(0) = 1/(pi*m^2)` bounded by the minimum
admissible roughness. **Bound the roughness from below in the prior, or the bound
does not exist.** That is a real constraint on the material table and it must be
stated there.

**Swath bound.** For a set of cells `W`,

```
g(W) <= (lam^2/(4*pi)^2) * f_max(W) * Om(W) / R_min(W)^2
```

with `R_min` the minimum range in the swath, which is a valid upper bound and
evaluates in `O(1)` on a mip pyramid over the atlas storing
`(min range, max f_max, total solid angle)` per node. Hierarchical culling on that
pyramid discards whole swaths in `O(log N)` with a proof, not a guess.

**Adjoint swath bound.** Because the extended-surface law is `R^0`, the adjoint
bound is `g(W) <= f_max(W)*Om(W)/(4*pi*cos_min)` with no range term. The only
sound way to cull a distant swath in the adjoint formulation is by its **solid
angle**. Which is exactly what section 7.5 measures.

**Path continuation bound.** At any vertex, remaining contribution is bounded by
accumulated throughput times the supremum of the remaining transport. That
supremum is finite only if a minimum range is imposed. Impose it: the far-field
distance of the virtual antenna, `r_ff = 2*D_ant^2/lam`, about 1.9 m for a 10 cm
aperture at 28 GHz. Returns from inside `r_ff` are near-field, the Friis chain
does not apply, and the atlas does contain hits inside it (the ground under a
2.5 m camera mast). Flag and exclude them, do not silently include them.

### 7.3 The crop radius is a theorem, not a convention

**Proposition.** Every point of every path of total length at most `L_max` that
starts and ends at `S` lies inside the ball of radius `L_max/2` centred on `S`.

**Proof.** Let `y` lie on segment `x_m -> x_{m+1}` of such a path. Let `a` be the
path length from `S` to `x_m`, `b` from `x_{m+1}` back to `S`, and
`c = |x_m - x_{m+1}|`, so `a + b + c = L <= L_max`. Then
`|S-y| <= |S-x_m| + |x_m-y| <= a + |x_m - y|` and
`|S-y| <= |S-x_{m+1}| + |x_{m+1}-y| <= b + |x_{m+1} - y|`. Adding,
`2|S-y| <= a + b + c = L <= L_max`. QED.

So `R_B = L_max/2`, exactly. Critically, this covers **occluders** as well as
scatterers, which a contribution bound alone does not: an occluder relevant to a
retained path lies on a segment of it, and the proposition covers every point of
every segment. That closes the one hole a reviewer would otherwise find, because
culling a distant thin wall by "its own backscatter is weak" wrongly admits the
strong corridor path it should have blocked.

For the adjoint formulation, paths end at the exit surface rather than at `S`, so
apply the same argument with `L_max` the retained one-way length, giving
`R_B = L_max` for the outbound leg. Use the larger of the two.

**Practical consequence: two levels of detail, not one.** Keep a high-fidelity
scattering mesh out to the contribution radius, and a coarse **occlusion-only
shell** out to `R_B`. The shell can be OSM footprints extruded to tag heights,
which `src/aegis/study/` already builds and which section 4 of `OVERVIEW.md`
records as having been fixed. Wrong-but-present distant geometry blocks correctly
to first order, and blocking is all it is asked to do.

### 7.4 Mapping a dynamic range `D` to a maximum useful range

With a reference at `R_0 = 5 m` (the nearest facade in a narrow street):

| `D` (dB) | monostatic extended, `R^-2` | monostatic discrete, `R^-4` | adjoint discrete, `R^-2` | adjoint extended |
|---|---|---|---|---|
| 20 | 50 m | 15.8 m | 50 m | unbounded |
| 25 | 89 m | 21.1 m | 89 m | unbounded |
| 30 | 158 m | 28.1 m | 158 m | unbounded |
| 35 | 281 m | 37.5 m | 281 m | unbounded |
| 40 | 500 m | 50.0 m | 500 m | unbounded |
| 50 | 1581 m | 88.9 m | 1581 m | unbounded |

"Unbounded" is not a joke and it is the point. In the adjoint formulation, an
unoccluded beam-filling surface never falls below threshold by range alone.

**Per-bounce cost of a scattering event**, from section 5.4, folds into the same
budget. A path that scatters diffusely off concrete at normal incidence at 60 GHz
loses the entire coherent branch (`|rho_s|^2 = 0.018`, i.e. `-17.4 dB` on the
specular continuation), whereas at 70 degrees it keeps 62 % (`-2.1 dB`). At
28 GHz the same surface keeps 41 % at normal (`-3.8 dB`) and 90 % at 70 degrees
(`-0.45 dB`). So the specular skeleton's reach is strongly band- and
incidence-dependent, and quoting a single `D -> d_max` number per frequency
without stating the incidence is not defensible.

**Atmospheric absorption** is the only other frequency-dependent range term, and
it only bites at 60 GHz. Specific attenuation from ITU-R P.676-13 annex 1 at
`p_dry = 1013.25 hPa`, 15 degrees C, 7.5 g/m^3 water vapour, computed from the
line catalogue and validated against ITU's own validation spreadsheet to 5e-15
relative:

| | 28 GHz | 39 GHz | 60 GHz |
|---|---|---|---|
| oxygen (dB/km) | 0.0187 | 0.0468 | 14.6235 |
| water vapour (dB/km) | 0.0831 | 0.0766 | 0.1548 |
| **total (dB/km)** | **0.1018** | **0.1234** | **14.7783** |
| loss over 100 m of path | 0.010 dB | 0.012 dB | 1.48 dB |
| over 260 m | 0.026 dB | 0.032 dB | 3.84 dB |
| over 500 m | 0.051 dB | 0.062 dB | 7.39 dB |
| over 1000 m | 0.102 dB | 0.123 dB | 14.78 dB |

Two things to carry into the code rather than the table. The 60 GHz oxygen
complex peaks at 15.19 dB/km at 60.81 GHz, so a band edge is worse than the
centre. And at 28 and 39 GHz the loss is water-vapour dominated (82 % and 62 %),
so it swings with humidity, and the dry-air floor at 28 GHz is only
0.0187 dB/km against the 0.1018 dB/km quoted above. Evaluate P.676 in code with
the scenario's atmosphere rather than hard-coding any of this, and note the
partial-pressure convention recorded in section 15.3, which is worth about 1 %.

At 60 GHz, atmospheric absorption alone caps the useful path length near 700 m
for a 10 dB allowance, which is a genuine physical prune that the `R^0` law does
not provide.

### 7.5 The 130 m crop, settled by measurement

`DESIGN.md` chose 130 m by a semantic-coverage-retention argument (100 % of
projected coverage at three yaws, 99.15 % at the fourth). That is a criterion
about panorama pixels landing on mesh. It is not a criterion about propagation,
and the two coincide only by accident.

**Measured, 2e6 uniform rays from the aligned pose, four crop radii, same rays.**

| Crop | sky fraction | median first-hit | p99 | max |
|---|---|---|---|---|
| 60 m | 0.2357 | 3.39 m | 47.3 m | 65.0 m |
| 100 m | 0.2283 | 3.44 m | 57.3 m | 94.5 m |
| 120 m | 0.2274 | 3.45 m | 58.9 m | 110.0 m |
| 130 m | 0.2271 | 3.45 m | 60.2 m | 137.2 m |

Solid-angle fraction of the full sphere with an unoccluded first hit beyond a
given range, on the 130 m mesh:

| beyond | fraction of `4*pi` | in dB relative to the whole sphere |
|---|---|---|
| 30 m | 4.859 % | -13.1 dB |
| 60 m | 0.778 % | -21.1 dB |
| 100 m | 0.094 % | -30.3 dB |
| 120 m | 0.038 % | -34.2 dB |
| 130 m | 0.014 % | -38.5 dB |

**And the decisive test.** Comparing the 100 m and 130 m meshes on identical
rays: the 130 m mesh reveals 0.123 % of the sphere as new hits at median range
103 m that the 100 m mesh reported as sky, and **zero** directions go the other
way. The fraction of the sphere hitting geometry beyond 90 m grows by a factor
6.6 (0.022 % to 0.145 %) when the crop grows from 100 m to 130 m. The far tail is
real occluding geometry, not a crop-rim artefact, and **it has not converged at
130 m**.

Conclusions, stated for the record:

1. The sky fraction converges quickly (0.2357 to 0.2271 across the four crops)
   but the range CCDF does not. Two quantities, two convergence rates, and the
   coverage argument only tested one of them.
2. Under the adjoint `R^0` law, the far directions contribute at full per-direction
   strength, so their weight is purely their solid angle. On the 130 m mesh the
   directions beyond 90 m carry -28.4 dB of the isotropic weight and that number
   is still growing with crop radius. **A 30 dB budget is not satisfied by a
   130 m crop.**
3. Korenmarkt is a dense European market square, which is the friendly case.
   Manhattan avenues run for kilometres with unoccluded sightlines. The crop
   radius has to be re-derived per site from the measured CCDF, never inherited.

**The test to institutionalise:** sweep the crop radius until the first-hit range
CCDF, weighted by solid angle, changes by less than the target `D`, and record
the converged radius per site in the manifest next to `geometricError`. It costs
one Mitsuba run per radius, seconds each.

### 7.6 Effective distance for pruning, corrected

Folding a power factor `eta` on a segment into an equivalent range works, but the
exponent must match the range law of the class:

```
r_eff = r * eta^(-1/p)   for a contribution scaling as r^-p
```

So `r_eff = r/sqrt(eta)` for `p = 2` and `r_eff = r*eta^(-1/4)` for `p = 4`. In dB,
an excess loss `L_dB` maps to `r_eff = r * 10^(L_dB/(10*p))`, which is
`10^(L_dB/20)` only in the `p = 2` case. Since the range law is per-class
(section 7.1), the effective-distance conversion is per-class too, and for the
adjoint extended case with `p = 0` there is no conversion at all and losses must
be carried as losses.

**This is a pruning device only.** It must never appear in the field
computation. A complex reflection coefficient changes amplitude and phase, and
no single real distance reproduces both in a coherent sum. Enforce it in code by
keeping `r_eff` on the bound object and out of the path throughput.

### 7.7 Can one number drive termination, crop radius, and level of detail

Three things, and the honest answer is two numbers, not one.

**`D`, the contribution dynamic range, drives:**

- ray termination, directly, through the continuation bound of section 7.2
- the crop radius, through `L_max` and the theorem of section 7.3
- level of detail for **amplitude** fidelity: normals, `sigma_0`, footprint. A
  surface contributing 40 dB below the maximum can carry a proportionally cruder
  representation, because the error it introduces is bounded by its own
  contribution

**`sigma_L`, the path-length tolerance, drives what `D` cannot.** A path-length
error `delta_L` costs a phase error `2*pi*delta_L/lam` regardless of how weak the
path is. The geometric tolerance for a coherent path is wavelength-scaled and
absolute, and it does not relax with distance or with weakness. `mmwave.py`
already has the machinery: `coherent_amplitude_retention(sigma_L, f) = exp(-0.5*phi^2)`
with `phi = 2*pi*sigma_L/lam`.

The two numbers interact through a clean demotion rule, and this is the LOD
policy to implement:

```
if coherent_amplitude_retention(sigma_L(path), f) < eta_coh:
    demote the path to the incoherent diffuse budget, randomise its phase
    its geometric tolerance is now amplitude-only, and D governs it
else:
    keep it coherent, and its geometric tolerance is lam-scaled, and D does not relax it
```

At 28 GHz, retention 0.5 corresponds to `sigma_L = 2.0 mm`, retention 0.1 to
`sigma_L = 3.7 mm`. Given the twin's pose covariance, most far geometry will be
demoted, and demotion is the correct outcome rather than a failure. Report the
demoted energy fraction per location. It is the single most honest summary of how
much of the response can be trusted coherently.

**Occlusion topology** is a third thing, and it is covered by the theorem of
section 7.3 rather than by `D`. Do not try to make `D` cull occluders.

### 7.8 Exposure is not channel modelling, and the owner's argument only half survives

The argument was: at FR2 and FR3 the link is LOS-dominated, NLOS contributes
little to human exposure, so a dynamic range relative to LOS is defensible. Four
things are true and four are not.

**Where it holds.**

- For the **upper tail** of the exposure CDF, which is the compliance-relevant
  end, LOS dominates when LOS exists and truncation at 25 to 35 dB is defensible.
- For **incoherent** `Sab`, every path term is non-negative, so a power-based
  prune is a strict under-estimate. That is a safe direction for a "we may be
  missing exposure" claim and an unsafe direction for a "exposure is below X"
  compliance claim. Say which one the paper is making.
- The `ReLU[n_hat.(-k_hat)]` gate means paths arriving on the shadowed side
  contribute exactly zero, so some retained power is exposure-irrelevant and the
  effective retained fraction is better than the power fraction suggests.
- At 60 GHz, atmospheric absorption genuinely suppresses long NLOS paths.

**Where it fails, and these must be stated as validity limits.**

1. **The lower tail is entirely NLOS.** A blocked pedestrian has no LOS
   component at all, so their exposure is 100 % NLOS and the threshold must be
   relative to **that user's own strongest component**, never a global LOS
   reference. The ten-cities paper is a population CDF, and the shape of its low
   end is exactly what NLOS determines. Referencing the prune to a global LOS
   would silently delete the population the study exists to characterise.
2. **Precoding is not a post-hoc filter.** The study uses MRT precoding on the
   deterministic channel. MRT weights are matched to the whole channel including
   NLOS paths. Dropping paths changes the precoder, which changes the beam, which
   changes exposure at **other** users. Path truncation upstream of a precoder is
   not benign and has no sign.
3. **Coherent quantities have no sign under truncation.** The peak spatially
   averaged `Sab` over 4 cm^2 is set by interference between paths, and the
   project's own hotspot work found the near-field blob structure to be a
   two-ray LOS interference beat. The second ray is often the ground bounce,
   which is nowhere near 40 dB down. Removing weak paths moves hotspots.
4. **The det-versus-stoch arm becomes an unfair comparison.** 3GPP 38.901
   explicitly models the NLOS cluster distribution. Comparing a truncated
   deterministic channel against an untruncated stochastic one biases the
   headline result of the study in an uncontrolled direction. If the
   deterministic arm is truncated, the stochastic arm must be truncated the same
   way, and that has to be stated.

Additional regimes where truncation is not acceptable: arcades and covered
markets and narrow canyons where the diffuse tail carries a large power fraction,
and any reported delay-spread or angular-spread statistic, which are tail-weighted
by construction.

### 7.9 How to report the threshold

Turn the assertion into a measured convergence curve. Section 9 folds this
together with the bounce-count protocol, because they are the same experiment.

---

## 8. Path space, the estimator, and its weights

### 8.1 The path integral

Write the response as an integral over path space in the Veach formulation. Let
`Om_L` be the set of paths with `L` vertices `x_1..x_L` on the scene surface `M`,
with area-product measure `dA(x_1)...dA(x_L)`. The measurement is

```
I = sum over L of  integral over Om_L of  f_L(x_1..x_L)  dA(x_1)...dA(x_L)
```

with the contribution function factorising as

```
f_L = W(S, x_1) * [prod_{m=1..L} f_r(x_m)] * [prod_{m=1..L-1} G(x_m, x_{m+1})] * E(x_L)
```

where `G(x,y) = V(x,y)*cos(th_x)*cos(th_y)/|x-y|^2` is the geometry-and-visibility
factor, `W` is the emitted-importance term at `S` and `E` the exit or gather term.
Specular vertices enter as Dirac BRDFs, so specular, glossy and diffuse vertices
coexist in one expression with no case analysis. Equivalently, radiance obeys the
Neumann series `L = sum_q K^q L_e` with the transport operator `K`, which
converges whenever the spectral radius of `K` is below 1, i.e. whenever every
surface is passive and some energy escapes. Section 9.2 measures the effective
contraction rate directly.

### 8.2 The Monte Carlo estimator

For a sample path drawn with vertex-wise pdfs `p_m`, the estimator is

```
Ihat = f_L(x_1..x_L) / prod_{m=1..L} p_m
```

and the throughput is built incrementally, which is how it is implemented:

```
beta_0 = 1                                     (atlas cell chosen with p_1 = q_c/Om_c)
beta_m = beta_{m-1} * f_r(x_m) * cos(th_out) / p(w_out | w_in, x_m)
```

With microfacet importance sampling of the half vector, the sampled pdf cancels
most of `f_r*cos/p`, leaving a weight close to the Fresnel term times the Smith
masking ratio, which keeps the variance bounded.

**The first bounce is not sampled at all.** Its contribution is a deterministic
quadrature over atlas cells, weight `Om_c` exactly, variance zero. That is the
concrete cash value of the free first hit in estimator terms.

**Accumulate the outer product, not the amplitude.** On escape, the deposit into
the `(u_loc, u_ext, tau)` cell is

```
C[cell] += (beta_L * J) (beta_L * J)^H          2x2 Hermitian outer product
```

and **not** `T[cell] += beta_L * J`. Section 2.8 is the reason, and the failure
mode of getting this wrong is silent rather than noisy. The one exception is the
coherent skeleton, where amplitude and phase are appended to an explicit path
list rather than binned. A single boolean on the path state selects between the
two, set by the `sigma_L` gate of section 7.7 evaluated at the last vertex.

**Russian roulette instead of a hard cap.** Continue a path with probability
`p_rr = min(1, beta_m/beta_ref)` and divide the throughput by `p_rr` on
survival. This is unbiased, whereas a hard bounce cap is not, and it makes the
truncation-error question empirical rather than assumed. Keep a hard cap as a
safety net only, set well above the roulette's effective depth, and report both.

**Multiple importance sampling.** Where next-event estimation toward the visible
sky is used alongside BSDF sampling, combine with the balance heuristic
`w_i = p_i / sum_j p_j`. Do not hand-tune a split.

### 8.3 Polarisation

Do not trace three orthogonal virtual dipoles. Trace the geometry once and carry
a **2x2 complex Jones matrix** per ray, mapping the transverse polarisation basis
at departure to the transverse basis at exit. The third component is fixed by
transversality, and `A(u)` is assembled from the Jones matrix composed with the
transverse projector at departure. Three dipoles is the correct concept and three
times the cost.

Basis bookkeeping is where this goes wrong silently. Fix the convention once: at
each interaction, rotate into the local plane of incidence (`e_perp` along
`w_in x n`, `e_par` completing the right-handed triad), apply the diagonal
Fresnel pair or the microfacet local frame, rotate out. Test it with the
reciprocity assertion of section 11.3, which catches basis errors that produce
plausible-looking magnitudes.

---

## 9. Convergence: one protocol for bounce count and dynamic range

These are the same experiment and should be one section of the paper.

### 9.1 The protocol

On a stratified 5 to 10 % subset of locations per city:

1. Compute at interaction depths `L = 1..5` with roulette disabled and the hard
   cap at `L`.
2. Compute at dynamic ranges `D` in {10, 15, 20, 25, 30, 35, 40, 50} dB with the
   prune active, referenced to **each location's own strongest component**, not a
   global LOS.
3. Take the smallest `(L, D)` satisfying all of:
   - median over locations of `|P_(L+1) - P_L|` below 0.5 dB
   - 95 % of locations change by less than 1 dB
   - RMS delay spread changes by less than 5 to 10 %
   - the 5th, 50th and 95th percentiles of the exposure CDF each shift by less
     than 0.5 dB
4. Judge on band-averaged and spatially averaged power and on exposure
   percentiles. **Never on a pointwise maximum dB difference.** One weak ray moves
   one null and produces a meaningless outlier.
5. Publish the curve, not the number. Retained fraction of total absorbed power
   versus `D`, per city, with the dense-canyon and open-square sites shown
   separately, because the knee moves between them.
6. Publish the **provable bound alongside the measurement**: "the discarded
   energy is at most X dB below the retained total by the bound of section 7.2,
   and Y dB by measurement". Two numbers, one of which cannot be argued with.

### 9.2 What the measurement already says about the bounce count

The per-bounce survival can be predicted before running anything, from the atlas.
Model the response as an integrating cascade with per-bounce factor

```
q = rho * f_capture
```

where `rho` is the surface albedo and `f_capture` the fraction of scattered
directions that hit geometry rather than escaping. Truncating at depth `L` leaves
a tail bounded by `g_1 * q^L/(1-q)`.

**Measured `f_capture` at Korenmarkt**, cosine-lobe propagation, 1.5e6 rays:

| interaction | escape fraction of all rays | escape fraction of survivors | `f_capture` |
|---|---|---|---|
| 0 (sky, direct) | 0.2271 | 0.2271 | 0.773 |
| 1 | 0.3616 | 0.468 | 0.532 |
| 2 | 0.1348 | 0.328 | 0.672 |
| 3 | 0.0994 | 0.359 | 0.641 |
| 4 | 0.0564 | 0.318 | 0.682 |

so `f_capture` settles near 0.6 to 0.68, and the cumulative escape fraction
within three interactions is **0.823**. A specular-direction cascade on the same
rays gives 0.820, so the number is not an artefact of the lobe model.

Feeding `f_capture = 0.6` into the bound:

| `rho` | `q` | dB per bounce | tail beyond `L=3` | tail beyond `L=4` |
|---|---|---|---|---|
| 0.2 | 0.120 | -9.2 | -27.1 dB | -36.3 dB |
| 0.3 | 0.180 | -7.5 | -21.5 dB | -28.9 dB |
| 0.4 | 0.240 | -6.2 | -17.4 dB | -23.6 dB |

**Verdict on "three reflections is sufficient", and on the external advice of
three specular plus one diffraction with 25 to 35 dB termination.** For a
plausible mmWave facade albedo of 0.3, three interactions leaves a truncation
floor around -21 dB. That does **not** reach a 25 to 35 dB termination budget.
Four interactions reaches -29 dB and is consistent with it. So the two pieces of
advice, taken together, are internally inconsistent by about one bounce, and my
derivation lands on the deeper side.

Recommend `L = 4` with Russian roulette above `L = 2`, which costs little because
82 % of rays have already escaped by then, and let the convergence protocol
confirm or overturn it per city. State the number as measured, not as convention.

### 9.3 The diffraction hole, bounded rather than confessed

There is no diffraction term in this design. Earlier revisions of this document
called that the largest known physical omission and said it lands on exactly the
elevation band `w_roof` needs. **Both halves of that sentence are wrong**, and
the correction comes from `PRIOR_ART.md` section 4.1, which is the hostile review
of this design. The omission is real, it is bounded, and the bound is small.

**Measured.** Charbonnier, Lai, Tenoux, Caudill, Gougeon, Senic, Gentile, Corre,
Chuang, Golmie (NIST and Siradel), "Calibration of Ray-Tracing With Diffuse
Scattering Against 28-GHz Directional Urban Channel Measurements", IEEE Trans.
Veh. Technol. 2020, `10.1109/TVT.2020.3038620`, verbatim: diffuse scattering
"accounted for 20% of the total received power, whereas diffraction accounted for
less than 1%". 28 GHz, directional sounder, urban, super-resolution MPC
extraction, 488 acquisitions. That is the same campaign this repository already
leans on for the diffuse share, so it costs nothing to cite it for both.

**Theoretical, triangulated.** Chizhik et al. (Nokia Bell Labs), IEEE TAP 2021,
`10.1109/TAP.2020.3044398`, over 3000 links and 21 million power samples at
28 GHz: the theoretical edge diffraction coefficient at large diffraction angles
is of order **-42 dB at 28 GHz**. The 60 GHz companion gives -46 dB, and
knife-edge shadow loss going as `10 log10 f` predicts -45.3 dB from the 28 GHz
anchor. An ITU-R P.526-15 knife-edge computation for Ghent geometry (eaves 12 to
20 m, head 1.7 m, pedestrian 2 to 12 m from the facade) returns 43 to 48 dB
across the whole low-elevation band. Scaled from that anchor, FR3 at 16.95 GHz is
-39.8 dB, so **FR3 is only 4.5 dB more diffractive than 28 GHz** and is not a
different regime.

**The power-integral error is unmeasurable.** With blocked directions carrying
-45 dB, omitting diffraction costs 0.000 dB of `K_iso` at open-azimuth fraction
0.30, 0.003 dB at 0.05, 0.014 dB at 0.01 and 0.135 dB at 0.001. Reaching 1 dB
needs an open fraction below 0.012 % of azimuth. Korenmarkt's measured sky
fraction is 0.2271 (section 2.7). The UTD transition region, the one place
geometrical optics is genuinely discontinuous, has half-width `sqrt(lam*s/2)`,
which is 28 cm at 28 GHz for `s = 15` m against 106 cm at 2 GHz, so roughly 1.9 %
of directions at a worst-case 6 dB, about 0.06 dB of bias on `K_iso`.

**The geometry argument reverses the old one.** Rooftop-diffracted power arrives
from the edge directly above the near facade, so at a head at 1.7 m the arrival
elevation is 35 to 86 degrees. That is the top of the 3 to 60 degree band or
above it entirely, and `1/sin^3(el)` at 60 degrees is 0.001 times its value at
5 degrees. Adding UTD would deposit power exactly where this document's own
weight suppresses it by three orders of magnitude. The old section conflated the
link with the local tensor: the over-rooftop multiscreen transport a macrocell
link needs is upstream of `K_S` and is factored out by construction. What `K_S`
has to capture is only the last edge.

**The genuine exceptions, which do not go away.** If any assumed transmitter site
sits behind a parapet, a diffraction-free tracer predicts a hard zero where
measurement shows usable signal: Chizhik measures that moving a base station 5 m
back from the roof edge costs over 15 dB of extra average loss under 100 m. And
Koivumaki, Steinbock, Haneda, IEEE TAP 2021, `10.1109/TAP.2021.3050482`, at
28 GHz outdoor, find "many weak diffracted paths that are found in measurements
and cannot be reproduced by diffuse scattering". The Rayleigh split is not a
substitute for the diffracted field. Note also that no paper was found reporting
"RMSE grows from X to Y dB when diffraction is disabled" for urban mmWave, so do
not claim one exists.

**What to do.** Publish `f_open`, the low-elevation open-azimuth fraction, per
location as the validity flag, alongside the bound above. That converts a
confessed hole into a scoped decision. Reserve the UTD or Fock edge term, at
explicitly tagged roofline edges only, for the parapet case and for any site
whose `f_open` falls under a percent.

Two factual corrections to section 10 belong here rather than there. Sionna RT
diffraction was added in 0.15.0, removed in 1.0.0, restored in 1.2.0, and is
present in 2.0.1 as Kouyoumjian-Pathak UTD with the Luebbers finitely-conducting
heuristic, first order but supporting `R...R.D.R...R` chains, with the
`diffraction` and `edge_diffraction` flags defaulting to False, so most published
Sionna results silently run without it. And MATLAB's `Method="sbr"` does
second-order UTD while its image method does none, which kills any "SBR
architecturally cannot diffract" argument.

The "photogrammetric meshes make diffraction impossible" defence is partial.
Sionna applies no dihedral-angle or coplanarity filter to wedges
(`utils/wedges.py` uses Mitsuba's `primitive_silhouette_projection` with only
exterior-side and distinct-primitive tests), so triangle soup does yield
diffraction sources on tessellation artefacts. But Koivumaki solved wedge
extraction on unstructured survey geometry five years ago. The honest wording is
"unreliable without a preprocessing stage we did not build", not "impossible".

### 9.4 The crop radius is the largest hole, and it is about sources

Section 7.5 measured that the 130 m crop has not converged as an **occluder** set:
the far tail of the first-hit range CCDF is real geometry, directions beyond 90 m
carry -28.4 dB of the isotropic weight under the adjoint `R^0` law, and that
number is still growing with radius, against a 30 dB budget.

`PRIOR_ART.md` section 4.2 adds the second and larger failure, which is about
**source placement** rather than scatterers. Section 2.7 supports `w_roof` on
`Delta_h` in [13.5, 43.5] m and `d` in [25, 250] m. The scene is cropped at
130 m. The fraction of the `cos/sin^3` measure lying at elevations that require a
source outside the crop is 27.5 % for `Delta_h = 8` m, 79.4 % at 15 m, 88.5 % at
20 m and 94.9 % at 30 m. The weight's stated support and the crop radius
contradict each other outright.

These two are not the same measurement and they do not cancel. Scatterer
truncation beyond 130 m is separately bounded as small: ITU-R P.1411-13 Table 11
gives a measured 28 GHz NLOS delay spread of 74.5 ns median (22 m excess path)
and 3GPP 38.901 UMi-SC NLOS at 28 GHz gives 65.9 ns (19.8 m), which puts a
scatterer at 130 m at -19 to -41 dB, under 0.05 dB of error. Atmospheric
absorption cannot be used to justify the truncation either: ITU-R P.676-13 gives
about 0.1 dB/km at 28 GHz, so 0.026 dB over 260 m. So the crop is defensible for
scattered power, marginal for occlusion under `R^0`, and indefensible as stated
for the rooftop weight's source support.

The repair is a documentation and reporting change, not a tracer change. Either
narrow the stated support of `w_roof` to the range the crop can actually contain
and say so, or keep the support and report `K_roof` with the fraction of its
measure that is unsupported by geometry. Doing neither is the thing a reviewer
will find.

---

## 10. Sionna RT versus our own tracer

### 10.1 What Sionna gives, and what it cannot

Verified by reading the installed `sionna-rt` 2.0.1 source, not from documentation
memory.

| Capability | Sionna 2.0.1 | Consequence for us |
|---|---|---|
| Materials | `mi_mesh.set_bsdf(radio_material)` in `scene_object.py`, so material is **per Mitsuba shape**, not per primitive or texel | The semantic atlas is per-pixel. Using Sionna means splitting the mesh into one object per material class, an explosion of shapes, and losing the per-texel roughness posterior entirely |
| Co-located TX and RX | `sb_candidate_generator._los` contains an explicit guard "Discard LoS paths when sources and targets overlap", `length > MIN_SEGMENT_LENGTH` | Co-location is a recognised degeneracy that Sionna handles by deleting the term. It is not a supported configuration |
| Specular chains | class docstring: "only paths ending with a diffuse reflection can be finalized through shooting-and-bouncing", specular chains are candidates requiring the image method, deduplicated by hashing with acknowledged collision loss | Exactly the measure-zero structure of section 5.1, and the hashing means candidate loss is possible |
| Free first hit | no API surface for injecting a precomputed primary-visibility buffer | The central advantage of the whole design is inexpressible |
| Escaping rays | the solver's product is paths from sources to targets | The adjoint tensor is not a Sionna output. There is no target |
| Scattering pattern | Degli-Esposti directive and Lambertian, in `scattering_pattern.py` | Non-reciprocal (section 5.6), which is disqualifying for an adjoint formulation |

### 10.2 Recommendation

**Write our own, on Mitsuba `ray_intersect` and Dr.Jit. Keep Sionna as the
cross-validation oracle, not as the engine.**

One-line reason: the entire advantage of this design is a precomputed
primary-visibility atlas with per-texel materials feeding an escaping-ray adjoint
estimator, and none of those three are expressible through Sionna's
source-to-target path API, while everything Sionna provides that is genuinely
hard (BVH construction, vectorised and differentiable intersection, GPU
execution) is already available one level down in Mitsuba, which Sionna itself
sits on.

What we would have to reimplement, honestly:

| Piece | Effort | Notes |
|---|---|---|
| BVH and intersection | none | Mitsuba 3.8, measured at 14.5 Mray/s on the real 157k-triangle mesh on 4 cores, and `ray_test` is cheaper still |
| Fresnel and slab coefficients | small | `materials.py` and `config/itu_p2040_4.json` already have the dielectric side |
| Microfacet BSDF and sampling | moderate, about 200 lines | Beckmann `D`, Smith `G`, half-vector sampling. Standard and well-tested elsewhere |
| Jones transport and basis rotations | moderate, and the main correctness risk | Section 8.3. Gate it with the reciprocity test |
| Delay binning and exit binning | small | HEALPix or Fibonacci lattice plus scatter-add |
| MIS and Russian roulette | small | Balance heuristic, textbook |
| Diffraction | **not attempted** | Section 9.3, where the omission is bounded at under 0.14 dB on `K_iso`. Sionna 2.0.1 does have first-order UTD, but its flags default to False and it carries no measurement validation |

The reimplementation risk sits in polarisation bookkeeping, and adopting Sionna
would not remove it, because Sionna's scattering pattern is non-reciprocal.
Diffraction is the one thing Sionna would genuinely add, and section 9.3 prices
that addition at a fraction of a decibel outside the parapet case.

### 10.3 Architecture

```
semantic_twin/propagation/
  atlas.py        SphericalAtlas: build from mesh + pose, or load the raycast npz.
                  Solid-angle weights, mip pyramid for the swath bound (7.2).
  bsdf.py         Microfacet (Beckmann D, Smith G, Fresnel F), Rayleigh split,
                  Lambertian pedestal, Degli-Esposti directive behind a flag.
  materials.py    (extend the existing one) sigma_h and l_c posteriors from the
                  semantic Dirichlets, out-of-view priors, ensemble sampling.
  transport.py    The Jones-carrying path state, throughput update, RR, MIS.
  adjoint.py      The escaping-ray estimator. Produces T_S records.
  monostatic.py   The gather-to-S estimator, sharing transport.py's extension rays.
  specular.py     Image-source enumeration over plane clusters, atlas-restricted.
  planes.py       Planar cluster extraction from the mesh (reuse plane_fit_error
                  from pixel_projection.py).
  tensor.py       Binning, SH compression, the canonical scalars of 2.7, storage.
  prune.py        Admissible bounds, per-class range laws, the crop-radius theorem.
  analytic.py     Closed-form references (section 11).
  sionna_check.py Bistatic cross-validation harness.
```

Core array shapes, in Dr.Jit's structure-of-arrays layout (note `si.n` comes back
as `(3, N)`, not `(N, 3)`, which is a real and easy-to-miss source of bugs):

```
Atlas, N_a cells (N_a = 2.6e5 at 0.5 deg):
  dir          (N_a, 3) float32     cell direction
  solid_angle  (N_a,)   float32
  range_m      (N_a,)   float32     inf for sky
  n_hat        (N_a, 3) float32
  prim_id      (N_a,)   int32       -1 for sky
  mat_id       (N_a,)   uint16
  sigma_h      (N_a,)   float32
  l_c          (N_a,)   float32
  in_view      (N_a,)   bool        always True for the atlas, False for traced vertices

Sample batch, M samples (M = 1e6):
  o            (3, M) mi.Point3f
  d            (3, M) mi.Vector3f
  jones        (2, 2, M) complex64      polarisation throughput
  path_len     (M,) float32             accumulated l
  x_last       (3, M) float32           last interaction point, for 4.4
  depth        (M,) uint8
  u_0          (3, M) float32           departure direction, retained for the ReLU
  alive        (M,) bool
  ooview_hit   (M,) bool                touched an evidence-free vertex

Output records, per escaping path:
  u_0, u_e, x_last, tau, jones, depth   -> binned into tensor.py
```

---

## 11. Validation

Seven tests, ordered from "cannot be argued with" to "agrees with another tool".

**This plan has already paid for itself.** Test 11.1 was run against the first
draft of this design and failed, which is how section 2.8 was found. The naive
estimator returned `K_S = 1.0000` against a closed-form target of exactly 2, with
no visible noise and a perfectly plausible-looking angular profile. Build these
tests before the physics, not after.

### 11.1 Closed form: a ground plane under the observation point

The cheapest test in the set and the one that catches the most.

Put `S` at height `h` above an infinite ground plane. By image theory a plane
wave from elevation `el` produces at `S` the direct field plus a reflected field
with excess path `2*h*sin(el)`, so

```
K_S(el) = (1/2) * sum over the two polarisations of |1 + Gamma_pol * exp(-j*2*k*h*sin(el))|^2
```

**Perfect conductor.** `Gamma_TE = -1` and `Gamma_TM = +1`, so the two
interference patterns are exactly complementary and

```
K_S(el) = (1/2)[(2 - 2 cos psi) + (2 + 2 cos psi)] = 2   exactly, at every elevation
```

An angle-independent, non-trivial, closed-form target. Verified: the corrected
estimator (coherency accumulation, 8e6 rays, 18 equal-solid-angle exit bins)
returns 2.000000 with maximum absolute error 0.0e+00. The uncorrected version
returned 1.0.

This case also validates the excess-path formula of section 2.4 independently.
`Delta = l_1 - u_e.(x_1 - S)` evaluates to `2*h*sin(el)` with a maximum
discrepancy of 7e-9 m over 4e6 sampled rays, which matches image theory exactly.

**Dielectric ground**, needed because the PEC case is degenerate. For
`eps_r = 5.24` (the P.2040 concrete value) at `h = 1.5` m and 28 GHz:

| elevation | pointwise `K_S(f)` | band-averaged `K_S` |
|---|---|---|
| 15 deg | 2.3052 | 1.3248 |
| 45 deg | 0.9891 | 1.1636 |

These differ, which is the point. Use the dielectric case to test that the code
returns the band-averaged value and not the pointwise one, and use the pointwise
column to test the coherent skeleton path list.

### 11.2 Closed form: the Lambertian spherical cavity

Put `S` at the centre of a sphere of radius `R` whose wall is Lambertian with
albedo `rho`. Everything is analytic, and the derivation is in this document
rather than borrowed.

- Order-1 monostatic isotropic gain: every wall point has `cos(th_out) = 1` seen
  from the centre, so `g_1 = rho*lam^2/(4*pi^2*R^2)`, arriving as a **single
  delta** at `tau = 2R/c`.
- Higher orders: a Lambertian sphere seen from its own surface subtends a
  hemisphere of uniform radiance, so `E_(m+1) = pi*L_m` and `L_(m+1) = rho*L_m`.
  Hence `g_K = g_1 * rho^(K-1)` and `g_total = g_1/(1-rho)`, which is the
  integrating-sphere multiplier.
- Delay distribution: for a cosine-distributed ray from a point on a sphere the
  chord is `x = 2*R*cos(th)`, giving `p(x) = x/(2*R^2)` on `[0, 2R]`. Mean chord
  `4R/3`, which is Cauchy's `4V/S` (checked: `4*(4/3 pi R^3)/(4 pi R^2) = 4R/3`).
  The order-`K` delay density is the `(K-1)`-fold convolution of `p`, shifted by
  `2R`.
- Reverberation: power multiplies by `rho` per mean time `4R/(3c)`, so the decay
  time constant is `(4R/3)/(-c*ln(rho)) = 4V/(-c*Area*ln(rho))`, which is
  **Eyring's formula exactly**, with the Sabine form `4V/(c*Area*(1-rho))` as its
  `rho -> 1` limit. Checked numerically: at `R = 10 m` and `rho = 0.4`, 48.54 ns
  against Eyring's 48.54 ns and Sabine's 74.13 ns, the ratio being
  `(1-rho)/(-ln(rho)) = 0.655`.

  **This is a test of our estimator, not a citation.** The room-electromagnetics
  paper that established reverberation time as a room property states the
  **Sabine** form and does not mention Eyring. The two are printed side by side
  in the later experimental-validation work, which confirms Sabine is the
  small-absorption expansion. The distinction is not academic at our absorption
  levels: with `rho` around 0.4 to 0.6, which is the range this design expects,
  Sabine overstates the time constant by 30 to 50 %. Assert Eyring in the test,
  since it is what the transport chain produces, and do not quote Sabine as the
  reference value.

  (Symbol hazard when reading that literature: in the room-electromagnetics paper
  `S` is source power in watts, not surface area.)

This one case exercises the multi-bounce chain, the gather, the delay binning and
the reverberation slope, all against closed form. It is the primary regression
test.

### 11.3 Invariants, as property tests

- **Reciprocity.** Swap the roles of departure and exit and the response must be
  unchanged. This is the test that catches Jones-basis errors, which produce
  plausible magnitudes and wrong physics.
- **Free-space identity.** With no geometry, `T_S(u) = P_u`, `K_S(u) = 1` for all
  `u`, and the exposure integral reduces to
  `Sab = Sinc*T0*ReLU[n_hat . u_ext]`, the monograph equation, exactly. This is
  the single most important normalisation test, because it pins the constant that
  section 2.1 derived.
- **Energy conservation.** `int f_r*cos(th_o) dOmega_o <= 1` for every BSDF at
  every incidence, tested by quadrature over the hemisphere.
- **White furnace.** In a closed lossless cavity the geometric series diverges, so
  the total gain must grow without bound as `rho -> 1` at the rate `1/(1-rho)`.
- **Non-negativity and the ReLU bound**, matching the existing AEGIS property
  tests.

### 11.4 Independently computable: image sources and plate RCS

- **Two infinite parallel plates.** All specular paths are image sources at
  `L_n = 2*n*d`, with gain `(lam/(4*pi*L_n))^2 * |Gamma|^(2n)` and delay `L_n/c`.
  Exactly enumerable, and it tests the specular branch and the delay axis with no
  Monte Carlo at all.
- **Flat plate at normal incidence.** Physical optics gives monostatic RCS
  `sigma = 4*pi*A^2/lam^2`. This is a check on the specular glint magnitude and
  on the finite-facet treatment, and it is the test that will expose an incorrect
  treatment of facet size.
- **Large sphere.** Optical-limit monostatic RCS `pi*a^2`, testing the curved and
  faceted-approximation path.

### 11.5 Cross-check against Sionna RT, bistatic

Both tools should agree here, and the configuration is chosen so that neither is
being used outside its comfort zone.

- Scene: a simple two-facade canyon plus ground, exported through the existing
  `export.py` Mitsuba path, with materials from `config/itu_p2040_4.json` so both
  tools read the same dielectrics.
- Configuration: TX and RX at **distinct** points, 28 GHz, isotropic antennas.
- BSDF: run our tracer in Degli-Esposti directive mode with the identical
  `alpha_R` and scattering coefficient, so the comparison is like for like
  despite the non-reciprocity of that model.
- Compare: per-interaction-order received power, the full PDP, and the
  arrival-angle distribution.
- Acceptance: agreement within Monte Carlo noise on the incoherent power per
  order, and within a delay bin on the specular arrivals. Disagreement on the
  diffuse tail alone points at pattern normalisation, and disagreement on
  specular arrivals points at geometry or Fresnel.
- Then **repeat in microfacet mode** and report the difference as a model
  difference rather than an error. Reviewers respect that distinction.

### 11.6 The empirical question worth its own result

Does monostatic backscatter energy predict `K_iso`? Both come free from one
trace. Compute the correlation across all locations and all ten cities, per city
and pooled. A strong correlation is a genuinely useful finding (a cheap
monostatic sounder measurement would then constrain a local susceptibility). A
weak one is equally publishable and confirms section 3.2 empirically rather than
only structurally. Either way it is a result, not a risk.

### 11.7 Predictive validation against the twin's own held-out data

Reuse `DESIGN.md`'s leave-one-panorama-out protocol. Reconstruct from the others,
predict the held-out panorama's first-hit range map, and propagate the resulting
geometry error into `K_iso` through the ensemble. This converts registration
accuracy into propagation uncertainty, which is the number the exposure paper
must report and which no amount of internal consistency testing provides.

---

## 12. Scaling and storage

### 12.1 Cost per location

Measured on this box, four cores, `llvm_ad_rgb`, the real 157,744-triangle
Korenmarkt mesh: **14.5 Mray/s** for `ray_intersect`, higher for `ray_test`.
(A trivial three-shape scene gives 36 Mray/s, so the mesh costs about 2.5x. Do
not quote the toy number.)

Cost model per location:

```
rays = M * (L - 1)                          adjoint only, no gathers
     + M * L                                if the monostatic loop is also computed
atlas build = 0 rays                        precomputed, reused across frequencies
specular enumeration = O(N_vis^2 * N_pl)    flops, plus a few thousand occlusion rays
```

| `M` | `L` | rays | time at 14.5 Mray/s |
|---|---|---|---|
| 1e6 | 3 | 2e6 | 0.14 s |
| 1e6 | 4 | 3e6 | 0.21 s |
| 1e7 | 4 | 3e7 | 2.1 s |
| 1e7 | 4, plus monostatic | 7e7 | 4.8 s |

Cost is `O(log N_tri)` in mesh size through BVH traversal, and the crop of
section 7.3 bounds `N_tri` anyway. Memory is about 100 bytes per triangle, so a
1e6-triangle scene is 100 MB, and the atlas at 0.5 degree is 5 MB per location in
its compact `(range_m, prim_id)` form, which is what `raycast_mesh_depth.py`
already emits.

**One concrete fix while in there.** `raycast_mesh_depth.py` currently ray-casts
in a nested Python `for y: for x:` loop through the Blender BVH, which is 4.2e6
scalar calls for four 1024x1024 views. Replace it with a single vectorised
Mitsuba `ray_intersect`. It is the same result and it turns minutes into
milliseconds. That path is also the natural home for the mip pyramid of
section 7.2.

### 12.2 Ten cities

Assume 200 locations per city, so 2,000 locations, at `M = 1e7` and `L = 4` with
the monostatic loop: 2,000 x 4.8 s = **2.7 hours on four cores**, embarrassingly
parallel. A denser walk of 1,000 locations per city is 13 hours on this box, or
under an hour on any GPU through Mitsuba's CUDA variant. Neither is a constraint.
Three carriers (28, 39, 60 GHz) triples it and still is not a constraint, and the
atlas and the BVH are shared across carriers.

### 12.3 Storage, delay-resolved

Grid choices: HEALPix `nside = 16` gives 3,072 pixels at 3.66 degree resolution
for both the local and external directions, which is finer than the monograph's
`D(k_hat)` table of about 10^3 Fibonacci directions, so the body side is the
binding resolution and 3,072 is already generous. 64 delay bins, log-spaced.

| Level | Content | Per location | 2,000 locations | 10,000 locations |
|---|---|---|---|---|
| L0 | canonical scalars of 2.7, order split, truncation bound, `sigma_exit`, provenance | 1 KB | 2 MB | 10 MB |
| L1 | `K_S(u_ext)` on 3,072 pixels | 12 KB | 24 MB | 120 MB |
| L2 | `K_S(u_ext, tau)` | 786 KB | 1.6 GB | 7.9 GB |
| L3 | double-directional, local direction in spherical harmonics to order 4 (25 coefficients), 2x2 coherency | 1.2 MB | 2.4 GB | 12 GB |
| L4 | raw path list, `(u_0, u_e, x_last, tau, jones, depth)` at 60 bytes per path | 60 MB | 120 GB | 600 GB |

Recommendation: publish L0 and L1 for every location (146 MB at the dense
setting, trivial for Zenodo), publish L2 and L3 zstd-compressed (the delay axis is
sparse, expect 5 to 10x), and archive L4 for the 5 to 10 % convergence subset
only, which is the same subset section 9.1 already requires. The spherical-harmonic
compression of the local direction is the right one because the body-side
`D(k_hat)` that consumes it is smooth and the monograph already represents it in
spherical harmonics, so the composition is a coefficient dot product with no
resampling.

Delay-resolving also yields RMS delay spread and angular spread per location for
free, which are exactly the cross-city covariates `OVERVIEW.md` lists as missing.

---

## 13. Honest limits

Consolidated, so a reviewer finds them here rather than deriving them.

**What the adjoint tensor does determine.**

- the complete one-way linear map from any external plane wave to the field at
  `S`, up to the truncation order and the prune, with delay and polarisation
- the exact support of the arrival-direction distribution at `S` for any
  transmitter, since it is the atlas (section 4.3)
- source-independent scalars per location that compose with the body side by a
  dot product (section 2.6)

**What it does not.**

- **Anything at finite source range, in the plane-wave form.** Section 4.4. At
  mmWave a rooftop base station is never in the far field of the scattering
  region. The exit-point form fixes this and the plane-wave form must be
  published with `sigma_exit` as a validity flag.
- **Diffraction.** Section 9.3. Absent, and concentrated exactly where the
  rooftop weight has its mass.
- **Absolute received power, SINR, or beamforming gain** for a specific
  deployment, until composed with a `Q_S` that carries EIRP and load, which the
  twin does not and should not model.
- **Frequency dependence.** Materials, roughness split and lobe widths are all
  carrier-specific. The tensor is computed per band, not interpolated across
  bands.
- **The transient scene.** Parked cars, market stalls and pedestrians are in the
  capture epoch and must be marginalised into occupancy statistics for a
  long-term exposure statistic, as `DESIGN.md` already provides for.
- **Sub-`r_ff` geometry.** Returns from inside about 1.9 m at 28 GHz are
  near-field and the Friis chain does not apply. The atlas contains them.

**The monostatic loop specifically.**

- It is a **quadratic** functional of the one-way channel and cannot be inverted
  to recover it (section 3.2). Any claim that it "describes NLOS independently of
  transmitter and receiver placement" must be reduced to: it is a local
  environment descriptor whose relationship to any particular link is empirical,
  not derivable.
- **The position-independence prior is weaker than it is usually quoted as.**
  The room-electromagnetics result is the natural support for "the decay is a
  property of the environment, not the link", and it does not support as much as
  it appears to. It holds for the exponentially decaying **tail** only, not the
  whole impulse response, since the early part does vary with position. Its
  evidence base is **one room at one frequency**: an 11 x 20 x 2.5 m open-plan
  office at 5.8 GHz over 100 MHz, ten receive positions and **two** access
  points, giving 0.18 dB/ns, a 24.1 ns time constant and an absorbed fraction of
  0.51. The paper also says explicitly that the reverberation distance itself
  **does** depend on position, because antenna directivity varies. And a scan of
  all 128 citing works found every real extension to be to another enclosed
  volume (industrial halls, aircraft cabins, subway tunnels), with **no outdoor
  or street-canyon validation**. Searching for it is booby trapped: "urban
  reverberation time" returns acoustics and reverberation-chamber emulation,
  neither of which is an outdoor electromagnetic validation. An open street
  canyon is a leaky enclosure with a measured 23 % sky fraction, which is not a
  small perturbation on a closed room.
  Asserting position-independent reverberation outdoors would be a novelty claim
  requiring its own evidence, not a citation. If the paper wants it, measure it:
  compute the descriptor at a dense set of positions within one street and report
  the spatial variance of the decay slope directly. That is a cheap experiment
  and it would be a genuine contribution either way.
- The exactly co-located geometry sits on the **coherent backscattering peak**
  (section 6.1), 2.4 to 3.0 dB above the incoherent result for all orders at or
  above 2 in a co-polarised channel, which no bistatic link with separation above
  about 1.7 mm ever sees. Computing the monostatic descriptor coherently
  therefore places it on a physical anomaly. Compute it incoherently, or report
  the enhancement factor explicitly and strip it. Do not silently inherit it.
- Corner reflectors (facade-ground and facade-facade dihedrals) dominate the
  monostatic return and contribute nothing special to a generic bistatic link.
  The mechanism ranking is not transferable.
- The absolute level is 50 to 60 dB below the one-way transfer at mmWave
  (section 3.3), which matters for whether it could ever be measured for
  validation with a real sounder.

**Generalising to bistatic.**

The machinery is unchanged, only the endpoint count changes.

| Configuration | First hit | Last hit | Traced |
|---|---|---|---|
| monostatic, one panorama | free | free | middles only |
| panoramas at both endpoints | free (atlas TX) | free (atlas RX) | middles only |
| rooftop base station to pedestrian | traced | **free (atlas RX)** | first hit and middles |

The third row is the ten-cities case, and it is still a real saving: the
pedestrian-side atlas gives a free last bounce and a free arrival-direction basis
for the exposure integral. The natural way to exploit it is a photon-mapping
final gather. Trace photons from the base station into the scene once, deposit
them, then gather at every pedestrian and every time step through the atlas with
**zero rays**. With `N_pedestrians` times `T` time steps in the thousands, that is
the difference between feasible and not, and it is the reason to build the atlas
even for the arm of the study that has no panorama at the transmitter.

---

## 14. Where this is weakest

In order of how much it would cost us if it is wrong.

1. **Crop radius.** Sections 7.5 and 9.4. Not converged at 130 m at Korenmarkt,
   and Korenmarkt is the friendly case. Worse, `w_roof`'s stated support in
   section 2.7 asks for sources out to 250 m, so 79 to 95 % of its measure sits
   at elevations the crop cannot supply a source for. Every city needs its own
   sweep, and the answer for Manhattan will not resemble the answer for Ghent.
   This is the largest known hole and it is cheap to at least bound.
2. **Out-of-view materials.** 27 % of order-3 vertices have no street-level
   evidence, and only 3.1 % of the mesh is directly visible (section 5.7). The
   tile-texture route is the largest recoverable gain and has not been tried.
3. **Periodic structure, which the Rayleigh split does not model.** Eight of the
   sixteen roughness classes in `config/surface_roughness.json` are mortar grids,
   sett paving, corrugated cladding or tile courses, and those reradiate into
   discrete grating orders rather than a lobe. The library refuses to evaluate a
   Gaussian coherent fraction for them and nothing downstream supplies the
   alternative (sections 5.4 and 5.5). This displaced the old entry here, which
   was a factor-30 60 GHz swing between painted plaster and bare concrete, and
   which the measured priors dissolved: the surviving random-roughness
   sensitivity is the concrete-finish split, a factor of 1.6 at 28 GHz and 8.4 at
   60 GHz at normal incidence.
4. **Jones-basis bookkeeping, and coherency accumulation.** The two parts of the
   reimplementation that fail silently rather than loudly. Section 2.8 was found
   by a closed-form test returning a clean, plausible, wrong answer. Build
   sections 11.1 and 11.3 before any physics goes on top of them.
5. **Diffraction.** Section 9.3. Absent, and it stays absent. The omission is
   bounded at under 0.14 dB on `K_iso` for any plausible open-azimuth fraction,
   and the one place it is not bounded is a transmitter sited behind a parapet.
   Demoted from first place in an earlier revision of this list, on measured
   evidence rather than taste.
6. **The plane-wave reduction.** Publishable only with `sigma_exit` attached.
   Publishing `K_S(u_ext)` alone, without the validity flag, would be the easiest
   claim in this document for a reviewer to break.

---

## 15. Provenance of every claim in this document

Three tiers, kept separate on purpose. The middle tier is the one a reviewer
should be able to reproduce without leaving the repository.

### 15.1 Derived here, and cross-checked against an independent route

| Result | Where | Independent check |
|---|---|---|
| `T_S(u) = (4*pi*eps_0/k^2)*A(u)^T`, identity in free space | 2.1 | reduces to `P_u` in free space, and to the monograph's `Sab` equation in 11.3 |
| `Delta = l_K - u_e.(x_K - S)` | 2.4 | matches the image-source phase `u_e.(S'-S)` for a single mirror, and `2*h*sin(el)` numerically to 7e-9 m |
| Angular phase-coherence scale `lam/(2*pi*|x_K - S|)` | 2.8 | found by test 11.1 failing, then confirmed analytically |
| `sigma_0 = 4*pi*cos(th_i)*cos(th_s)*f_r` | 3.1 | radar equation vs radiance transport chain, agree to 12 significant figures. Lambertian energy balance gives `sigma_0 = 4*rho*cos*cos` by a third route |
| Monostatic 2-bounce specular paths are finite and measure zero | 5.1 | image-source construction, at most one candidate per ordered plane pair |
| Directive scattering model is not reciprocal | 5.6 | `F_alpha` depends on `th_i` only, plus a bare `1/cos(th_o)`. Even-`j` term of `F_alpha` derived analytically and matched to the installed Sionna implementation |
| Beckmann `D` normalisation, `D(0) = 1/(pi*m^2)`, `m = sqrt(2)*sigma_h/l_c` | 5.3 | substitution `w = tan(th_h)`, and the slope variance of a Gaussian ACF |
| Range laws: monostatic `R^-2` extended and `R^-4` discrete, adjoint `R^0` and `R^-2` | 7.1 | radar equation and radiance transport, verified numerically over 10 m to 640 m |
| Crop radius `R_B = L_max/2` | 7.3 | triangle inequality, covering segment interiors and hence occluders |
| `r_eff = r * eta^(-1/p)`, exponent per class | 7.6 | direct substitution into `r^-p` |
| PEC ground gives `K_S = 2` at every elevation | 11.1 | complementary TE and TM interference, verified numerically to 0.0e+00 |
| Lambertian cavity: `g_K = g_1*rho^(K-1)`, chord pdf `x/(2R^2)`, mean chord `4R/3` | 11.2 | Cauchy's `4V/S`, and the reverberation constant reproduces Eyring's `4V/(-c*S*ln(rho))` numerically (48.54 ns at `R = 10 m`, `rho = 0.4`) |
| Coherent backscatter enhancement requires `|d| << lam/(2*pi)` | 6.1 | phase mismatch `k*d.(u_1 - u_K)` between a path and its reverse |

### 15.2 Read from installed source or from files in this repository

| Fact | Source |
|---|---|
| Sionna material granularity is per Mitsuba shape | `sionna/rt/scene_object.py`, `mi_mesh.set_bsdf(radio_material)` |
| Sionna discards LOS when source and target overlap | `sionna/rt/path_solvers/sb_candidate_generator.py`, `_los`, `length > MIN_SEGMENT_LENGTH` |
| Sionna shoot-and-bounce finalises only paths ending in a diffuse reflection | same file, `SBCandidateGenerator` docstring |
| `F_alpha = 2^-alpha * sum_j binom(alpha,j) * I_j`, patterns normalised to 1 in `dOmega` | `sionna/rt/radio_materials/scattering_pattern.py` |
| `S = sqrt(1 - exp(-g^2))`, `g = 4*pi*sigma_h*cos(th)/lam` | `semantic_twin/mmwave.py` |
| ITU-R P.2040-4 power-law material table, `eps' = a*f^b`, `sigma = c*f^d` | `config/itu_p2040_4.json`, which cites P.2040-4 section 3 table 3 and equations 57 to 59 |
| `Sab = Sinc*T0*ReLU[n_hat.(-k_hat)]`, `T0 = 0.536` for skin at 28 GHz | `theory/monograph_v2.tex` |
| `P_abs = Sinc*T0*(A_ab/4)*(1/4pi)*int rho*D dOmega`, `D(k_hat)` stored on a Fibonacci lattice, coupling factor `F` between 1.00 and 1.18 | `theory/monograph_v2.tex`, `sec:angular-spectra` and `sec:precomputed` |
| Mitsuba 3.8.0, Dr.Jit 1.3.1, trimesh 4.12.2, sionna-rt 2.0.1 present in `.venv` | `importlib.metadata` |
| 14.5 Mray/s `ray_intersect` on 157,744 triangles, 4 cores, `llvm_ad_rgb` | benchmarked here |
| `si.n` returns shape `(3, N)`, not `(N, 3)` | benchmarked here |
| Atlas statistics, escape cascade, out-of-view fractions, crop comparison | measured here against the Korenmarkt mesh and pose |

### 15.3 Published work this document relies on

Verified against the primary sources or, where the source was paywalled, against
several mutually consistent restatements. Where verification failed, that is
stated rather than glossed.

**Scattering models**

- V. Degli-Esposti, F. Fuschini, E. M. Vitucci, G. Falciasecca, "Measurement and
  modelling of scattering from buildings," IEEE Trans. Antennas Propag., 55(1),
  143-153, Jan. 2007. The directive lobe and the effective-roughness reflection
  reduction `R = sqrt(1 - S^2)`. Two traps. The printed lobe form has a minus on
  the `sin*sin` term, so its `phi_i` points back toward the source and the lobe
  peaks at `phi_i + pi`. And `alpha_R` is restricted to positive integers in the
  2007 model.
- The 2001 predecessor is Degli-Esposti alone, IEEE Trans. Antennas Propag.,
  49(7), 1111-1113, July 2001. It is **Lambertian only**, so the directive lobe
  is 2007, not 2001. Strict priority for `R = sqrt(1 - S^2)` could **not be
  confirmed**, because both papers are paywalled. The authors' own 2023 paper
  attributes it to 2007. Safe split: cite 2001 for the effective-roughness
  concept and the coefficient `S`, cite 2007 for the directive lobe and for
  `sqrt(1 - S^2)`. Do not assert priority without the PDFs.
- The compact closed form for `F_alpha` is **not** in the 2007 paper, which gives
  only a parity-split even/odd sum. That parity split is what `sionna-rt` 2.0.1
  implements and what section 5.6 verifies analytically. The general
  double-factorial form is Vitucci, Cenni, Fuschini, Degli-Esposti, IEEE Trans.
  Antennas Propag., 71(7), 6072-6083, 2023, which states outright that a complete
  solution was not derived in 2007. Cite whichever form the code actually uses.
- K. E. Torrance, E. M. Sparrow, "Theory for off-specular reflection from
  roughened surfaces," JOSA, 57(9), 1105-1114, Sept. 1967, and R. L. Cook,
  K. E. Torrance, ACM Trans. Graph., 1(1), 7-24, Jan. 1982 (the expanded version
  of the SIGGRAPH 1981 paper, cite the TOG one).
- The GO-Kirchhoff form quoted in section 5.3 is as printed by Karam and
  McDonough, ITU Journal, 2(1), art. 7, 2019, with the stationary-phase slopes
  as restated by Ticconi, Pulvirenti and Pierdicca (2011) from Ulaby, Moore and
  Fung. Ticconi states outright that shadowing and multiple scattering are
  ignored, which is why the Smith term in section 5.3 is a repair rather than a
  derivation. The claimed angular equivalence with the microfacet form is
  Butler, Nauyoks, Marciniak, Opt. Express, 23(22), 29100, 2015, **abstract
  only, the full text is paywalled**, and the abstract itself limits the
  equivalence to the rough regime and says it breaks down for polished surfaces.
  Treat section 5.3's reason 2 as a structural argument with a partial citation,
  not as a settled result.
- W. S. Ament, "Toward a theory of reflection by a rough surface," Proc. IRE,
  41(1), 142-146, Jan. 1953, for the specular reduction factor, which Ament
  himself credits to Pekeris and to MacFarlane. A. R. Miller, R. M. Brown,
  E. Vegh, IEE Proc. H, 131(2), 114-116, 1984, for the Bessel-corrected form.
  See section 5.4 for the field-versus-power and Gaussian-versus-not caveats.

**Estimator**

- E. Veach, "Robust Monte Carlo methods for light transport simulation," PhD
  thesis, Stanford, Dec. 1997, advisor Guibas. Chapter 8 is "A Path Integral
  Formulation of Light Transport", giving path space and the area-product
  measure.
- E. Veach, L. J. Guibas, "Optimally combining sampling techniques for Monte
  Carlo rendering," SIGGRAPH 1995, 419-428, doi:10.1145/218380.218498. Its
  balance heuristic and its power heuristic (beta = 2) are both in that paper, the
  power heuristic being a subsection later, not a later publication.
- T. Zeltner, I. Georgiev, W. Jakob, "Specular manifold sampling for rendering
  high-frequency caustics and glints," ACM Trans. Graph., 39(4), art. 149, 2020,
  and W. Jakob, S. Marschner, "Manifold exploration: a Markov chain Monte Carlo
  technique for rendering scenes with difficult specular transport," ACM Trans.
  Graph., 31(4), art. 58, 2012. **Correction to an earlier draft of this
  document: there is no "Walter et al., manifold next event estimation, 2009".**
  Manifold NEE is Hanika, Droske, Fascione, Comput. Graph. Forum, 34(4), 87-97,
  2015. The Walter 2009 paper is Walter, Zhao, Holzschuch, Bala, ACM Trans.
  Graph., 28(3), art. 92, 2009, which is the Newton iteration on the half-vector
  constraint. Section 5.8 means the Newton iteration, so it is Walter 2009.

**Channel and environment**

- M. Steinbauer, A. F. Molisch, E. Bonek, "The double-directional radio channel,"
  IEEE Antennas Propag. Mag., 43(4), 51-63, Aug. 2001. No "mobile" in the title,
  despite frequent mis-citation.
- J. B. Andersen, J. O. Nielsen, G. F. Pedersen, G. Bauch, M. Herdin, "Room
  electromagnetics," IEEE Antennas Propag. Mag., 49(2), 27-33, April 2007,
  doi:10.1109/MAP.2007.376642. Its equation 8 is `tau = 4V/(c*eta*A)` with `eta`
  the absorbed energy fraction and `A` the wall area, and the paper states
  verbatim that this is Sabine's equation from acoustics with the velocity
  changed. **No logarithm of a reflection coefficient appears in it and `rho` is
  never introduced, so this paper cannot be cited for Eyring.** For the
  Sabine-Eyring pair, cite Kuttruff, "Room Acoustics", which is the paper's own
  reference for the acoustics result. Steinbock et al. (2015) is the
  experimental-validation follow-up. Symbol hazard: `S` in the 2007 paper is
  source power in watts, not surface area.
- Coherent backscattering: Kuga and Ishimaru, JOSA A, 1(8), 831-835, 1984, van
  Albada and Lagendijk, Phys. Rev. Lett., 55, 2692, 1985, and Wolf and Maret,
  Phys. Rev. Lett., 55, 2696, 1985. Radio-band measurements of the cone itself:
  Stefko, Leinss, Frey, Hajnsek, The Cryosphere, 16, 2859-2879, 2022, at 9.65 and
  17.2 GHz. Planetary opposition effect: Hapke and Blewett, Nature, 352, 46,
  1991, and Black, Campbell and Nicholson, Icarus, 151, 167, 2001. Rough-surface
  enhanced backscattering: Tsang, Chan and Pak, JOSA A, 11(2), 711, 1994. The EMC
  reverberation-chamber enhanced-backscatter constant is Ladbury and Hill, IEEE
  EMC 2007. **No claim is made about a microwave cone experiment by the
  Genack, Lagendijk or van Tiggelen groups, because none was found.** Nothing at
  all was found in urban, cellular or indoor propagation modelling.

**Recommendations and standards**

- ITU-R P.2040-4 (09/2025), "Effects of building materials and structures on
  radio-wave propagation in the range of 1 MHz to 450 GHz", section 3, table 3,
  equations 57 to 59, for the material power laws, already in
  `config/itu_p2040_4.json`. **It contains no rough-surface scattering model**
  (section 5.4), verified against the in-force PDF, which is why the roughness
  closure has to be sourced elsewhere. P.1411-13 (09/2025) has none either.
- ITU-R P.2146-0, equation 11, for the roughness reduction factor in power form.
  This is the ITU anchor that P.2040 does not provide.
- ITU-R P.676-13 (08/2022), annex 1, for gaseous attenuation, and there is no
  P.676-14. Section 7.4's numbers were computed from the line catalogue and
  validated against ITU's own validation workbook to 5e-15 relative over 1 to
  350 GHz. **Convention trap worth about 1 %:** in ITU's own validation file the
  1013.25 hPa figure is the **dry-air partial pressure**, with the water-vapour
  partial pressure `e = rho*T/216.7` added on top, giving a total barometric
  pressure of 1023.22 hPa. It is not the total pressure.
- ITU-R P.833 for vegetation, as `DESIGN.md` specifies. Not modelled here.
- 3GPP TR 38.901 for the stochastic arm of the ten-cities comparison, and for the
  uniform-phase convention that section 2.8 arrives at independently.
