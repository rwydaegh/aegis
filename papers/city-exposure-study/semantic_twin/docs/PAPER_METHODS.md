# Methods and results, end to end

> **Old illumination law, see `LAW_CHANGE.md`.** This file predates the move to a
> facade tip illumination law, so every height band, range band and elevation
> support in it belongs to the superseded model. The section 4.2 correction of
> 2026-08-02, marked all through the file, replaced one height and range band law
> with another and is superseded as well, so a note reading "corrected" below
> still means the old family.

> **Superseded as the drafting source.** `SPINE.md` is now the source of truth
> for what is claimed and at what strength, and `paper/methods.tex` and
> `paper/paper.tex` are the submission drafts. This file is kept because it
> records the derivations and the reproduction commands in more detail than the
> paper has room for, and because its status table below is the honest history of
> what was broken and when. Several rows of that table were true when written and
> are false now, and the ones known to have flipped are marked inline.

Draft spine for an IEEE Access submission. Content first, prose later. Every
number here traces to a script in this repository, and the reproduction commands
are in the last section.

Notation is written for KaTeX so it renders outside LaTeX. The symbol table is
appendix A, at the end.

---

## 1. The question

### 1.1 The situation being modelled

Someone is standing in a city square. Above and around them, somewhere, are the
base stations of a 15 GHz network. The question is how much radio power reaches
where they are standing, and how much of that answer is set by the square itself
rather than by the network.

That last clause is the whole study. Two pedestrians in two different squares,
served by identically specified networks, do not receive the same power, because
one square is a narrow medieval funnel of tall stone and the other is an open
plaza with a low skyline. Eleven squares are measured here to find out how large
that difference is, and what about a square's shape predicts it.

The obstacle is that at 15 GHz there is no network to point at. Nothing above
6 GHz is deployed for cellular access anywhere in the 3.86 million antenna
records available for Europe (section 4.3.1). So the base stations cannot be
placed, and any result that depends on where they were placed is a result about
an invented layout.

### 1.2 The base stations are a density on the sky, not a list of masts

The way out is to stop placing them. Instead of one layout, take the whole
population of plausible mast positions, and ask what fraction of the network's
power would arrive at the pedestrian **from each direction of the sky** if the
buildings were not there. That fraction is a probability density over
directions, written $Q(\hat u)$ and normalised to one over the sphere. It is
built in section 4 from two explicit and swappable assumptions, a height
distribution and a range cap, so the assumption is visible rather than buried in
a coordinate list.

The direction a mast occupies on the pedestrian's sky is set by two numbers, how
far up it is and how far away, and only their ratio matters. Figure 1 makes the
point that decides most of section 4: a steep arrival angle does not mean a tall
mast, it means a **near** one.

![Elevation is a ratio, not a height](FIGURES/18_elevation_geometry.png)

**Figure 1.** Three sources on the boundary of the rooftop deployment model.
Elevation is measured from the pedestrian's own horizon at head height, so the
60 deg arrival is not something high above a roofline, it is a mast 43.5 m up at
only 25 m away, the single closest and tallest corner of the assumed deployment
box. The two 13.5 m masts differ only in range, and that alone moves them from
10 deg to 3 deg. Any statement of the form "sources between 3 and 60 degrees"
therefore describes a corner of a two dimensional box, not a physical band.

> **Old illumination law, see `LAW_CHANGE.md`.** The two swappable assumptions
> named here, a height distribution and a range cap, and the 43.5 m at 25 m corner
> in the figure, are the old model's, and sites now sit on facade tips with one
> source distance per azimuth. Stale as a description of how $Q$ is built, though
> the point the figure makes, that elevation is a ratio and not a height, still
> holds.

### 1.3 The quantity: how much the square changes the answer

Fix an observation point $\mathbf{x}$ at pedestrian head height. Define the **transfer
kernel** $K(\hat u)$ as the ratio of the power density arriving at $\mathbf{x}$ from
direction $\hat u$ in the real scene, to the power density the same source would
deliver at $\mathbf{x}$ with every building deleted. $K$ is dimensionless, it is a
property of the geometry and the materials alone, and it is identically $1$
everywhere in free space.

The **susceptibility** of the standpoint is the inner product of what the square
does to each direction with how much network power comes from that direction,

$$\boxed{\ \chi = \int_{4\pi} K(\hat u)\, Q(\hat u)\, d\Omega(\hat u)\ }
\tag{1}$$

and the power density that actually arrives is $S_{\rm arr} = S_0\,\chi$, where
$S_0$ is whatever the same network would have delivered in the open. So
$\chi = 1$ means the square is neutral, $\chi = 0.35$ means it costs 4.6 dB,
and the eleven site comparison is a comparison of these numbers.

Three properties make (1) the right thing to compute rather than a convenient
one.

1. **It equals 1 in free space by construction**, for every $Q$. Any
   implementation error that breaks this is visible without a reference solution.
2. **It is independent of network transmit power.** Absolute scale lives in the
   single explicit factor $S_0$ that the caller owns, so a result transfers
   between sites, between bands and between deployment densities without being
   recomputed.
3. **It factorises the environment from the body.** Section 7 composes the
   arriving angular density $\rho$ with a phantom by a second inner product, so
   neither computation needs to know about the other.

The claim being made is about **urban form**, and marginalising the source
population is what makes that claim possible. Marginalising is not the same as
ignoring: section 4.3 carries three deployment models rather than one, and every
result is reported under each, so a reader who disputes the assumption can read
off how much it mattered.

### 1.4 Why powers and never amplitudes

The estimator accumulates power. This is forced, not preferred.

An escaping path leaves the scene from its last scattering vertex $\mathbf x_K$.
Perturbing the exit direction by $\delta$ changes the path phase by
approximately $k\,|\mathbf x_K - \mathbf x|\,\delta$. At 15 GHz, $\lambda = 20$ mm, and a
last vertex 100 m from the observer,

$$k\,|\mathbf x_K - \mathbf x| = \frac{2\pi \times 100\ \mathrm{m}}{0.02\ \mathrm{m}}
\approx 3.1\times 10^{4}\ \text{rad per radian of exit angle}.$$

Holding the phase error below 1 rad therefore needs angular cells no wider than
$3\times10^{-5}$ rad, which is of order $10^{10}$ cells on the sphere. The grid
used here has 512. Summing amplitudes on any publishable grid is five to seven
orders of magnitude too coarse, and the failure is **silent**: it produces a
plausible number with no warning. Every quantity reported here is therefore a
band averaged second moment.

The consequence is stated rather than hidden: this method cannot produce a
coherent fading realisation, and does not claim to.

### 1.5 Notation

Four conventions, stated once so they do not have to be restated.

**Everything is at one standpoint.** $K$, $Q$, $\rho$ and $\chi$ are all
properties of a single observation point $\mathbf{x}$, and the whole study is a
distribution over standpoints. Carrying an $\mathbf{x}$ subscript on every symbol
would say nothing, so it is dropped, and where a formula genuinely needs the
point it appears as $\mathbf{x}$.

**Directions point outward.** $\hat u$ always leaves $\mathbf{x}$. A wave
arriving from $\hat u$ propagates along $\hat k = -\hat u$. Section 5.1 is where
that sign matters and it is the only place it appears.

**$d$ is only ever a differential.** Horizontal range is $r$, so $d\Omega$,
$d\alpha$ and $dh$ never have to be read twice. Finite increments are $\delta$.

**Capital for solid angle, lowercase for elevation.** $Q(\hat u)$ is a density on
the sphere in sr$^{-1}$, and $q(\alpha)$ is its marginal in elevation in
rad$^{-1}$.
Section 4.1 gives the factor between them. The same discipline separates the
admissible height window $W$ from the cell count $M$, and the ray throughput $w$
from the tissue transmission coefficient $T_0$, both of which were one letter in
an earlier draft.

Symbols are collected in appendix A.

### 1.6 How the rest of this document is arranged

Evaluating (1) needs three things: the scene, the density $Q$, and a way to do
the integral. They are built in that order.

| Section | What it produces |
|---|---|
| 2 | the scene: a mesh, a class per surface, a permittivity per class |
| 3 | image evidence, and how much of the scene it actually binds |
| 4 | the illumination density $Q$, from a source population |
| 5 | the estimator that evaluates (1) |
| 6, 7 | where the pedestrian stands, and how the body couples |
| 8 | validation |
| 9 | results, within one square and across eleven |
| 10, 11 | what threatens each result, and how firm each one is |

The estimator in section 5 runs the geometry **backwards**, which is worth
stating once at the outset because it is the least obvious design choice here.
Rays are not launched from the base stations towards the pedestrian. They are
launched from the pedestrian outwards, bounced until they escape the city, and
then scored by how much network power would have come from the direction they
escaped in. Figure 2 is why.

![Forward tracing wastes almost every ray, adjoint tracing wastes none](FIGURES/20_adjoint_idea.png)

**Figure 2.** Left, the forward picture: sources are spread over the whole sky,
the pedestrian is a point, and essentially no launched ray ever lands on them.
Right, the adjoint picture: every ray starts at the pedestrian, so every ray
contributes, and the sky direction it eventually escapes in is exactly the
argument that $Q$ wants. Reciprocity makes the two equivalent, with the
dictionary $\hat k = -\hat u$. In the right panel blue rays reach the sky and
grey ones terminate on a wall, and the occlusion is computed rather than drawn,
so the visible sky wedge is the real one for this cross section.

Figure 3 follows one such ray end to end.

![One ray from launch to deposit](FIGURES/21_one_ray.png)

**Figure 3.** A single sample. The ray leaves $\mathbf{x}$ carrying throughput $w = 1$.
At each surface, $w$ is multiplied by the Fresnel power reflectance and the
Rayleigh roughness split decides whether the outgoing direction is specular or
diffuse. When the ray escapes, its surviving $w$ is deposited into the angular
bin of the direction it originally **left $\mathbf{x}$** in, weighted by $Q$ evaluated
at the direction it escaped in. Line thickness is $w$. Section 5.2 gives the
loop, including Russian roulette from bounce 3 and the bounce depth. Section 8.3
measures four interactions as sufficient and records which runs used four and
which six.

---

## 2. Scene acquisition

### 2.1 Support mesh

Geometry comes from Google Photorealistic 3D Tiles, traversed from the root
tileset down to leaf level within a ball around the site anchor. Two details are
load bearing.

**Double precision placement.** A leaf carries its placement in Earth centred
Earth fixed coordinates, of order $6.4\times10^{6}$ m, in its glTF node matrix.
Blender's `Object.matrix_world` is single precision, whose spacing at that
magnitude is about 0.5 m. Reading placement through Blender therefore quantises
tile origins, producing a rigid shift of roughly 0.22 m and, worse, up to 0.44 m
of *differential* tile to tile seaming. At 15 GHz that is 22 wavelengths of
unrecoverable geometry error. The placement is therefore read from the container
in float64 and folded into vertex coordinates, and every object is left at the
identity. Meshes built this way carry `format_version: 3` in their manifest and
the loader refuses anything lower.

**The ROI ball is centred on the terrain, not the ellipsoid.** A ball of radius
$\varrho$ centred at ellipsoidal height 0 reaches only $\sqrt{\varrho^2 - H^2}$
horizontally at a site of ellipsoidal height $H$. Milan at $H = 163$ m received 116 m of scene from a
nominal 200 m request before this was fixed.

The site is then cropped to a horizontal radius $R_{\rm crop}$ about the anchor.
Section 9.4 shows $R_{\rm crop}$ is not a free parameter.

### 2.2 Surface classes

The photogrammetric mesh carries no material labels. A triangle is assigned to
one of four classes by an explicit geometric rule on its normal $\hat n$ and its
height above the local ground datum $z_0$:

| class | rule |
|---|---|
| ground | $\lvert n_z\rvert > 0.85$ and $z - z_0 < 2\ \mathrm{m}$ |
| roof | $n_z > 0.85$ and $z - z_0 \ge 2\ \mathrm{m}$ |
| soffit | $n_z < -0.85$ |
| facade | otherwise |

This is a stated placeholder for image evidence, not a substitute for it, and
section 3 measures exactly how much of the scene image evidence can replace.
Every run writes the rule into its manifest.

### 2.3 Electromagnetic parameters

Each class binds one ITU-R P.2040-4 material row and one roughness class. P.2040-4
gives the real permittivity and conductivity as power laws in frequency $f$ in
GHz,

$$\varepsilon_r' = a f^{\,b}, \qquad \sigma = c f^{\,d}\ \ [\mathrm{S\,m^{-1}}],$$

where $a$, $b$, $c$ and $d$ are P.2040-4's own four coefficients per material
row. They are the one place where $d$ is not the differential of section 1.5 and
where $a$ and $b$ are not the window limits of section 4.2, and the letters are
kept because a reader will check them against the recommendation. From the power
laws the complex relative permittivity follows with the negative imaginary part
convention,

$$\varepsilon = \varepsilon_r' - j\,\frac{\sigma}{2\pi f \varepsilon_0}.
\tag{2}$$

Defaults are ground to `asphalt_concrete`, facade to `brick`, roof and soffit to
`concrete`. Validity bands are enforced: a request outside a row's stated band
raises rather than extrapolating silently.

---

## 3. Image evidence

This layer exists to replace the geometric rule of section 2.2 with observed
material where a camera saw the surface. Section 9.3 reports what it is worth,
and the answer is not what the project assumed.

### 3.1 Panorama selection

Street level panoramas are selected by walking the capture link graph outward
from the site anchor rather than by querying a bounding box.

**The bounding box endpoint silently returns a sample.** Measured at Korenmarkt,
one bounding box query covering 200 m returned 43 images, of which 2 belonged to
a sequence that in fact has 13 frames inside 60 m of the centre. The response
carries no truncation flag, no paging cursor and no total count, so nothing
distinguishes a complete answer from a 15 % sample. The bias is spatially
structured: it thins dense drives first, removing exactly the short baselines a
multi view study needs. The fix is to use the box only to *name* sequences, then
enumerate each sequence by id.

The unit of merit is a **walk**: the largest set of panoramas sharing one capture
date and linked to each other. Sites carry 5 to 21 capture dates within 60 m and
panoramas almost never link across dates, so a raw count overstates what a single
traverse reaches.

From the walk, $n$ panoramas are chosen by **farthest point sampling** seeded at
the panorama nearest the centre. This maximises the minimum separation, and it is
prefix optimal, so a run truncated by an API quota still holds the most spread
subset of what it managed. Extent binds harder than count: widening a site from
60 m to 80 m lifts achievable surface coverage from 30.6 % to 44.8 % of scene
area, worth more than tripling the camera count in the middle.

![What one registered panorama actually sees](FIGURES/03_what_one_panorama_sees.png)

**Figure 4.** How little of a square a street level camera reaches. Over the full
sphere one registered panorama is a first hit on 4.3 % of support triangles and
6.9 % by area, and fusing twelve raises directly observed surface to 15.9 % of
triangles and 24.1 % by area. Inside the four 90 degree rectilinear crops the
fishnet actually cuts against, one panorama reaches only 2.3 % of triangles and
3.2 % by area, counted over the distinct source triangles in
`outputs/korenmarkt_fishnet_vistas/*_fishnet.npz`. So the two single capture
figures quoted elsewhere in this repository are not comparable and the full
sphere pair is the one to read against the fused number. A third pair, 3.3 % of
triangles and 4.4 % by area, appears in `REPORT.md` and in `FIGURES/README.md`
for this same figure and reproduces from nothing shipped.
Coverage then saturates: twelve panoramas reach 77 % of the area the site can
ever offer within 60 m and twenty six reach 90 % of its triangles, which sets the
per site budget at twelve to sixteen. The remaining 55 % of the scene is roofs,
courtyards and rear elevations that no street level capture ever sees, and that
ceiling is the reason section 9.3 can only test a partially evidence bound scene.
Source `outputs/walk_korenmarkt/walk_coverage.json` and
`outputs/walk_korenmarkt_saturation/walk_saturation.json`.

### 3.2 Registration

Each panorama arrives with a coarse pose from capture metadata. That pose is
refined against the mesh skyline: the segmentation gives a sky mask, the mesh
gives a predicted horizon, and the pose is the argument minimising the mean
angular disagreement between the two silhouettes.

Three defects were found and fixed here, all of which had shipped:

1. Capture metadata carries a measured gravity tilt that was being discarded and
   replaced by a hardcoded upright assumption, throwing away tilts of 4.5, 7.8 and
   26.8 degrees already on disk.
2. The altitude search bound was **load bearing**. Every pose previously shipped
   sat within 0.1 m of the floor. Widening it is the wrong fix, because the
   optimiser then buys residual by sinking the camera below the pavement: it is
   compensating a systematic bias, since photogrammetry rounds off balustrades
   and pinnacle tips so the mesh skyline sits low.
3. Camera ground height was one scene wide constant applied regardless of
   distance from the origin. It is now a per camera downward ray cast.

The reported residual is **not an error bar**. An eight seed repeat at Korenmarkt
spans a 3 m by 2.5 degree valley at equal cost, so poses ship with a seed spread
rather than a single number.

### 3.2.1 The residual cannot see the dominant failure mode

An independent second opinion is available for free: the fishnet reports pixels
that segmentation calls sky but for which the mesh returns a first hit.
Segmentation says sky, geometry says surface. That is a registration conflict
computed by a route entirely independent of the skyline objective, and it is
decisive.

Over the 83 registered poses of this study, split at a conflicting sky fraction of
one half:

| | poses | median residual | residual range | median slack to bound | median range to conflicting geometry |
|---|---|---|---|---|---|
| conflict $< 0.5$ | 43 | 1.30$^\circ$ | 0.22 to 11.46 | 1.807 m | **27.11 m** |
| conflict $\ge 0.5$ | 40 | 6.40$^\circ$ | 0.18 to 12.00 | **0.046 m** | **0.66 m** |

The last column is the argument. In the failing half the rays that segmentation
calls sky terminate 0.66 m from the lens, so the camera is inside the geometry and
the optimiser put it there. Consistently with that, those poses sit 4.6 cm from
the altitude search bound rather than at an interior optimum.

**No residual threshold separates these two groups.** Their residual ranges overlap
almost completely, 0.22 to 11.46 degrees against 0.18 to 12.00. The counterexample
is explicit: the best skyline residual in the entire cohort, 0.176 degrees at
Madrid pano_08, has 100 % of its sky conflicting. That camera stands under the
Plaza Mayor arcade, the only visible sky is one arch, and the fit scored 0.176
degrees on the handful of columns inside that patch. The pose is not accurate to a
sixth of a degree, it is unconstrained, and the objective it was fitted with cannot
tell the difference.

Reopening the altitude bound does not find an interior optimum either. At Times
Square pano_00 a $\pm 3$ m search pins at $-3.00$ m with residual 9.52 degrees,
$\pm 8$ m runs to $-7.81$ m at the same 9.52, and $\pm 25$ m runs to $-22.60$ m at
7.45. Monotone improvement with depth is the signature of a nuisance parameter
absorbing the mesh skyline bias, not of convergence.

The practical consequence is that a pose gate must consume the conflict fraction
rather than the residual. 32 of the 83 poses sit at their altitude search bound,
24 of them at a 3 m bound, and a 4 degree residual threshold passes 13 of the 40
conflicting poses. The table above and both counts are
`outputs/registration_sky_conflict.csv`.

### 3.3 Fishnet: cutting the surface against the image

The naive approach tiles the label image and splats tiles outward onto the mesh.
The fishnet reverses the direction of travel: each support triangle is projected
into image space, cut there against semantic island boundaries, and the pieces are
mapped back onto the triangle's own plane.

This works because within one rectilinear crop the camera is a pinhole, so a
triangle maps to a triangle under an invertible projective map. The inverse used
is **not** barycentric interpolation of the projected corners, which is wrong
under perspective, but the exact intersection of the pixel ray with the triangle's
supporting plane. Verified against a BVH depth buffer over all 707,620 first hit
pixels of one view: median residual $4.7\times10^{-7}$ m, 95th percentile
$3.7\times10^{-6}$ m, worst case $1.9\times10^{-5}$ m.

Two guards are mandatory:

- **Near plane clipping.** At one Korenmarkt view, 4 of 1,431 visible triangles
  have a vertex behind the camera plane and those 4 own 33.5 % of the hit pixels.
  They are the large ground triangles under the camera. Unclipped, they project to
  garbage.
- **Bijection holds on the visible surface only.** Two triangles routinely
  project to the same pixel. The mesh first hit identifier decides ownership and
  any piece owned by a different triangle is rejected rather than painted.

Each output face carries class, class posterior, material posterior, confidence,
outward normal, metric area, solid angle from the capture point, and provenance.
Rejected faces are kept in a parallel table with the reason, so
`clutter_in_front` stays distinguishable from `transient_object`. That distinction
matters: a pedestrian's monocular depth often agrees with the wall behind them, so
only the class can reject them, while a parked van is rejected by depth.

### 3.4 Binding evidence to the tracer

![One patch of facade, four layers deep](FIGURES/05_four_layers_deep.png)

**Figure 5.** What the fishnet hands the tracer. Support geometry at the bottom,
then entity class, radio material and RMS surface height stacked above it. The
three upper sheets are the same triangles carrying three independent posteriors,
which is what distinguishes this from a textured mesh: the tracer reads a
material distribution per face, not a colour.


Faces seen by at least one registered panorama take their material from the fused
posterior. Everything else keeps the geometric rule of section 2.2. Each run
writes the covered fraction by face and by area into its manifest, and those two
numbers are the honest statement of how much of the result is evidence based.

---

## 4. Illumination: integrating over base station position

### 4.1 The construction

Consider base stations scattered on the ground at uniform areal density $\nu$, each
at height $h$ above the pedestrian head and horizontal range $r$, so the
elevation at which the pedestrian sees it is $\alpha = \arctan(h / r)$.
The goal is to convert *sites per unit ground area*, which is what a deployment
has, into *sites per unit elevation*, which is what the sky looks like from the
standpoint.

Count them in rings. The ring between range $r$ and $r + \delta r$ has area
$2\pi r\, \delta r$, so it holds $2\pi \nu\, r\, \delta r$ sites. Now express both
factors in elevation. Inverting the elevation relation at fixed height,

$$r(\alpha) = h \cot \alpha,
\qquad
\left| \frac{\partial r}{\partial\alpha} \right|
= \frac{h}{\sin^{2} \alpha} ,$$

where the absolute value is taken because range *decreases* as elevation rises,
and a count of sites has to come out positive. A slab of elevation of width
$\delta\alpha$ is therefore the image of a ring of width
$\delta r = |\partial r / \partial\alpha|\ \delta\alpha$, and it
contains

$$\delta N
= 2\pi \nu\, r(\alpha) \left| \frac{\partial r}{\partial\alpha} \right|
\delta\alpha
= 2\pi \nu\, h^{2}\,
\frac{\cos \alpha}{\sin^{3} \alpha}\, \delta\alpha.
\tag{3}$$

The $\sin^{-3}$ is the whole story: sites at low elevation are far away, and the
area of ground at a given range grows with that range, so the far ring is
enormous and it projects into a very thin slab of sky just above the horizon.

Equation (3) counts sites per unit **elevation**. The estimator of section 5
wants power per unit **solid angle**. These are different measures and confusing
them is silent, so both are carried explicitly and given different letters:
$q(\alpha)$, in rad$^{-1}$, is the marginal in elevation, and $Q(\hat u)$, in
sr$^{-1}$, is the density on the sphere of section 1.3. For a model with no
azimuthal preference, integrating $d\Omega = \cos\alpha\ d\alpha\ d\phi$ over
azimuth relates them by

$$q(\alpha) = 2\pi \cos\alpha\ Q(\hat u(\alpha)),
\qquad\text{equivalently}\qquad
Q = \frac{q(\alpha)}{2\pi\cos\alpha} .$$

The factor $\cos\alpha$ is the width of the elevation slab on the sphere, and
dropping it is the single easiest way to get this wrong.

| | $q(\alpha)$, density in elevation | $Q(\hat u)$, weight on $d\Omega$ |
|---|---|---|
| uniform sites, no path loss | $\propto \cos\alpha/\sin^{3}\alpha$ | $\propto 1/\sin^{3}\alpha$ |
| uniform sites, $r^{-2}$ weighting | $\propto 1/(\sin\alpha\cos\alpha)$ | $\propto 1/(\sin\alpha\cos^{2}\alpha)$ |

The second row weights by the **horizontal** range $r$, not by the slant range
$h/\sin\alpha$. The two coincide near the horizon and differ by a factor of 4 in
power at 60 degrees, so the choice has to be stated. Slant weighting would give
$\cos\alpha/\sin\alpha$ in elevation and $1/\sin\alpha$ on $d\Omega$ instead.

Both are heavily low elevation weighted. Under the rooftop support, 61.7 % of the
pure geometric weight sits below 5 degrees.

A note on that number, because an earlier draft of this work carried 64 %. That
figure is not reproducible from the support the code actually used. On
$[3.1^\circ, 60.1^\circ]$ the closed form gives 61.74 %, and 64.18 % requires a
$3.0^\circ$ lower edge that no version of the model ever ran. 61.7 % is the figure
that describes the published runs, and the support tuple is now pinned by test
alongside all three values so the two cannot drift apart again.

> **Old illumination law, see `LAW_CHANGE.md`.** The whole ring counting
> construction, the $\cos\alpha/\sin^{3}\alpha$ marginal and the 61.7 % of measure
> below 5 degrees follow from scattering sites on the ground at a height above the
> head, which the facade tip law does not do. Stale, because the shape of $Q$ is
> what every one of these numbers is about.

### 4.2 The two caps, and why a hard elevation band cannot express them

Two physical limits bound the source population. There is a **maximum height** a
base station plausibly occupies, and a **maximum range** beyond which the link
stops mattering. The obvious encoding is to state a height band
$[h_{\min}, h_{\max}]$ and a range band $[r_{\min}, r_{\max}]$ and
truncate the elevation support to
$[\arctan(h_{\min}/r_{\max}),\ \arctan(h_{\max}/r_{\min})]$.

**That encoding is wrong, and this draft corrects it.** Equation (3) is derived at
a *single* height. Truncating its support using the extremes of a height *band*
describes no actual source population, because the two caps interact. At the
0.95 degree lower limit of the small cell model, a 2.5 m source needs 150 m of
range but a 6.5 m source needs 390 m. A hard band admits both, and so buys
illumination from sources that violate its own range cap, at exactly the low
elevations that dominate the measure.

Carrying the integral out properly means asking, at each elevation, which
heights are actually admissible once **both** caps are imposed. Let $f_h(h)$ be
the height distribution over $[h_{\min}, h_{\max}]$, and let the range be
confined to $[r_{\min}, r_{\max}]$. A source at height $h$ appears at elevation
$\alpha$ only if its implied range $h \cot\alpha$ lies inside the range band,
which bounds $h$ between $r_{\min}\tan\alpha$ and $r_{\max}\tan\alpha$.
Intersecting that with the height band gives the admissible interval
$[a(\alpha), b(\alpha)]$ below. Weighting it by $h^{2}$, which is the Jacobian
factor already visible in (3), defines the **admissible height window**
$W(\alpha)$, in m$^{3}$:

$$q(\alpha) \ \propto\ \frac{1}{\sin^{3}\alpha}\; W(\alpha),
\qquad
W(\alpha) = \int_{a(\alpha)}^{b(\alpha)} f_h(h)\, h^{2}\, dh,
\tag{4}$$

$$a(\alpha) = \max\!\big(h_{\min},\, r_{\min} \tan \alpha\big),
\qquad
b(\alpha) = \min\!\big(h_{\max},\, r_{\max} \tan \alpha\big),$$

with $W = 0$ wherever $b < a$, meaning no height at all can produce that
elevation without violating a cap. $W$ is a **smooth** roll off, not an
indicator: near the edges of the support the admissible interval shrinks
continuously to nothing rather than switching off. It reduces to a hard indicator only in the single height case that (3)
actually describes. For a uniform height distribution it is available in closed
form, $W \propto (b^3 - a^3)$.

The support of (4) is indeed
$[\arctan(h_{\min}/r_{\max}), \arctan(h_{\max}/r_{\min})]$, so the
previously stated support was right. What was wrong was assuming the weight was
flat across it. A plateau where the whole height band is admissible exists only
when $h_{\max}/r_{\max} \le h_{\min}/r_{\min}$, which holds for both
deployment types considered here.

The consequence is that the uncorrected model **over weights both tails**, the low
one most, and the low tail is precisely what drives the crop radius requirement of
section 9.4. Figure 6 shows both halves of the argument.

![The deployment box and the illumination density it induces](FIGURES/19_deployment_box.png)

**Figure 6.** Left, the deployment models are rectangles in the
(range, height) plane, and lines of constant elevation are rays through the
origin. The 60.1 deg upper edge of the rooftop model is contributed by a single
corner of the rectangle, and the 3.1 deg lower edge by the opposite one, which is
why the elevation support alone is a poor description of the population. Right,
the density (4) that the rectangle actually induces. It is sharply peaked near
the low edge and decays hard: 45 % of the rooftop band's solid angle lies above
30 deg and carries 3.3 % of the power. Curves are the production
`elevation_band_measure`, peak normalised for display.

The measured effect of the correction is site dependent and large. At Korenmarkt
it raises the rooftop susceptibility by 5.27 dB and the street one by 4.27 dB,
across the eleven squares the per site shift spans 1.06 to 6.33 dB, and because
the shift is not common mode it **reorders the cities**. Section 9.2 reports it.

> **Old illumination law, see `LAW_CHANGE.md`.** This section is the 2026-08-02
> correction, which swapped a fixed height $1/\sin^{3}$ law for a law integrated
> over a height band and a range band, and both of those are height and range band
> laws. Stale, so a number this file calls corrected is one step newer than the
> superseded one and still not the current law, and the 5.27 and 4.27 dB shifts
> measure the distance between two old models.

### 4.3 The three models used

| name | $h$ [m] | $r$ [m] | elevation support [deg] |
|---|---|---|---|
| isotropic | | | $-90$ to $90$, uniform |
| macro rooftop | 13.5 to 43.5 | 25 to 250 | 3.1 to 60.1 |
| street small cell | 2.5 to 6.5 | 10 to 150 | 0.95 to 33.0 |

The isotropic model is a control, not a deployment. It is uniform over $4\pi$, so
$\chi$ under it reduces to a purely geometric openness measure and carries no
network assumption at all. Reporting it beside the directional models separates
what the built form does from what the deployment assumption does, and section
9.2 shows that separation is the main result.

> **Old illumination law, see `LAW_CHANGE.md`.** The two directional rows of this
> table, their height and range bands and their elevation supports, are exactly
> what the facade tip law replaces, and there is no range band or height band to
> quote under it. The isotropic row survives untouched, because it carries no
> elevation weight at all.

### 4.3.1 There is no deployment to calibrate these against

The six numbers above were substantiated against national antenna registers, and
the result is a negative that changes how they must be presented. Full working in
`DEPLOYMENT_GEOMETRY.md`.

Across 3,863,228 European antennas in the AEGIS base station database, the number
of **cellular access antennas above 6 GHz is zero**. France, the Netherlands,
Spain, Poland and Brussels all return zero. The only above-6 GHz rows anywhere are
15,140 UK Ofcom entries whose technology is fixed link, point to point backhaul at
a 22 GHz median, which is not access. So there is no deployed FR3 or FR2 base to
calibrate a height distribution against, and that is an absence of the deployment
rather than a gap in the data.

The obvious fallback, extrapolating a height versus frequency trend out of the
sub-6 registers, is **falsified rather than merely unavailable**. Deployed centre
height is flat in carrier frequency, and if anything rises:

| register | 0.7 to 1.0 GHz | 1.8 to 2.1 GHz | 2.6 GHz | 3.5 GHz n78 |
|---|---|---|---|---|
| Netherlands | 30.0 m | 29.6 m | 30.2 m | **31.8 m** |
| Brussels | 26.8 m | 26.7 m | 27.1 m | **27.8 m** |
| France | 28.0 m | 27.0 m | 26.2 m | |
| Poland | 40.0 m | 40.0 m | 40.0 m | |

Operators co-site every band on one mast, because the binding constraint is site
acquisition rather than radio. That kills the trend fit and simultaneously
supplies a better justification for using sub-6 macro heights as the macro prior:
not the same band, but the same real estate. Its failure mode is stateable, which
is the point of preferring it. If FR3 arrives by densification rather than as an
overlay, the new sites appear at street level and the small cell class carries
them, which is why the model keeps two classes rather than one broad band.

The two class structure has independent support in the same data. Deployed heights
are bimodal, thinly populated between roughly 6 and 18 m, which is a property
market fact, a roof lease or a lamppost lease with little in between, and property
markets do not care about carrier frequency.

**The closest published analogue lands between the two bands.** The Ericsson
Kista campaign is the nearest thing in the literature to what this study models:
15 GHz, an enclosed European square, an elevated base station and a pedestrian
height receiver, measured to 250 m. Its two base stations sit at 8.5 and 12 m
above ground, which is **below the macro band's 15 m floor and above the small
cell band's 8 m ceiling**. On the face of it the study has no class for the one
deployment it can point at.

That turns out not to matter, because the model consumes an elevation
distribution and not a height. Running the same band law on the Kista geometry
and comparing where each class puts its weight:

| model | height above ground | range band | below 5 deg | 5 to 20 deg | above 20 deg |
|---|---|---|---|---|---|
| street small cell | 4 to 8 m | 10 to 150 m | 87.9 % | 11.8 % | 0.3 % |
| Kista, as measured | 8.5 to 12 m | 10 to 250 m | 84.0 % | 15.3 % | 0.8 % |
| macro rooftop | 15 to 45 m | 25 to 250 m | 9.4 % | 80.8 % | 9.8 % |

Heights are above ground and the model's own bands are above the pedestrian head,
1.5 m lower. The Kista row needs a range band that the campaign does not state, and
10 to 250 m is used because the campaign measured out to 250 m and its transmitters
stand on the square itself. The row is sensitive to that choice: holding the height
band and moving the near cap from 10 m to 25 m moves the grazing measure from
84.0 % to 84.6 % and the above-20 entry from 0.8 % to 0.1 %, which does not change
the conclusion below.

A source in the height gap is illuminationally a small cell, not something
between the classes: it differs from the street model by 3.9 points of grazing
measure and from the rooftop model by 75. So the gap in the height axis is not a
gap in the modelled space, and the two class structure survives its own most
awkward evidence.

**So the caps are assumptions, and the paper reports a sensitivity rather than a
citation.** Measured leverage: the range cap is worth 7.8 dB across a defensible
100 to 400 m span, the height band 0.7 to 2.0 dB across its own. Height spans a
factor of 3.2 while range spans a factor of 10, which is what decides it. Per site
the range cap sensitivity runs from 0.6 dB at Krakow to 10.0 dB at Brussels and
Madrid, so the illumination assumption concentrates in exactly the deep canyon
sites that carry the most interpretive weight. Reporting $\chi$ at 150, 250 and
400 m is the honest presentation.

> **Old illumination law, see `LAW_CHANGE.md`.** The 7.8 dB range cap leverage,
> the 0.7 to 2.0 dB height band leverage, the per site 0.6 to 10.0 dB range cap
> spread and the Kista band comparison all price parameters that the facade tip
> law does not have, since each azimuth carries one source distance read off the
> geometry. Stale. What survives is the register evidence above it, that zero
> cellular access antennas above 6 GHz are deployed across 3,863,228 European
> records and that deployed height is flat in carrier frequency, because that is a
> statement about a database.

### 4.4 Normalisation

Write $\tilde Q(\alpha) = W(\alpha)/\sin^{3}\alpha$ for the unnormalised weight of
(4), which is a density on the sphere up to a constant. $Q$ is normalised by
quadrature in elevation and not on the direction grid:

$$\mathcal N = 2\pi \int_{\alpha_{\min}}^{\alpha_{\max}}
\tilde Q(\alpha)\, \cos\alpha \ d\alpha,
\qquad Q = \tilde Q / \mathcal N .$$

This matters because a $1/\sin^3$ law puts most of its mass in the first few
degrees above the horizon, which a few hundred cell direction grid cannot
resolve. For the same reason, any numerical comparison against $Q$ must integrate
each bin rather than sample its midpoint: $1/\sin^3$ is convex, so the midpoint
rule underestimates, and it underestimates most in the widest bin. Read at face
value that quadrature error looks like a factor of six error in the physics.

> **Old illumination law, see `LAW_CHANGE.md`.** The weight being normalised here,
> $W(\alpha)/\sin^{3}\alpha$ on a support with an upper and lower elevation edge,
> is the old law's shape. Stale as written, although the warning it carries, that
> a peaked $Q$ must be integrated per bin rather than sampled at bin centres, is
> about quadrature and applies to whatever shape replaces it.

---

## 5. The adjoint shoot and bounce estimator

### 5.1 Formulation

Computing $K(\hat u)$ forward, by launching from every plausible source and
seeing what reaches $\mathbf{x}$, wastes essentially all of the work. The adjoint form
launches from $\mathbf{x}$ instead, as in figure 2. Figure 3 is one sample of what
follows.

By reciprocity, a ray leaving $\mathbf{x}$ in direction $\hat u_{\rm loc}$ and escaping the
scene in direction $\hat u_{\rm ext}$ with accumulated power throughput $w$ is the
reverse of a path that would carry a fraction $w$ of the power from a source at
$\hat u_{\rm ext}$ into arrival direction $\hat k = -\hat u_{\rm loc}$ at $\mathbf{x}$. The
departure direction is the local arrival direction, so no sign conversion is
needed anywhere downstream.

Sampling $N$ rays with $\hat u_{\rm loc}$ uniform on the sphere gives the estimator

$$\boxed{\ \hat\chi = \frac{4\pi}{N}\sum_{j=1}^{N} w_j\, Q(\hat u_{{\rm ext},j})\ }
\tag{5}$$

where the sum runs over escaping rays only. Resolved by arrival direction, with
the sphere partitioned into $M$ near equal solid angle cells of a Fibonacci
spiral,

$$\rho_c = \frac{1}{n_c}\sum_{j \in c} w_j\, Q(\hat u_{{\rm ext},j}),
\qquad
\hat\chi = \sum_{c=1}^{M} \rho_c\, \Delta\Omega,
\qquad \Delta\Omega = \frac{4\pi}{M}.
\tag{6}$$

**Free space check.** With no geometry every ray escapes on its first segment with
$w=1$ and $\hat u_{\rm ext} = \hat u_{\rm loc}$, so
$\mathbb E[\hat\chi] = 4\pi\, \mathbb E[Q(\hat u)] = 4\pi \cdot \frac{1}{4\pi}\int Q \, d\Omega = 1$
for any $Q$. This is a parameter free identity, not a calibration.

> **Old illumination law, see `LAW_CHANGE.md`.** Nothing in the estimator changes.
> $Q$ enters only as a weight on the exit direction of an escaped ray, after the
> transport is done, so the reciprocity dictionary, the throughput $w$, the deposit
> into direction cells, the roulette and the free space identity hold for any $Q$
> by construction and survive the law change.

### 5.2 The bounce loop

For each ray, from the current position $\mathbf x$ and direction $\hat u$:

1. **Intersect** the support mesh. No hit means the ray escapes, so deposit it
   into (6) and stop.
2. **Advance** to the hit point, accumulate path length, orient the surface normal
   against the incoming ray, and form $\cos\theta = -\hat u \cdot \hat n$.
3. **Attenuate** by the unpolarised power reflectance of the surface class,

   $$R(\theta,\varepsilon) = \tfrac12\Big(|\Gamma_{\rm TE}|^2 + |\Gamma_{\rm TM}|^2\Big),$$

   $$\Gamma_{\rm TE} = \frac{\cos\theta - \sqrt{\varepsilon - \sin^2\theta}}
   {\cos\theta + \sqrt{\varepsilon - \sin^2\theta}},
   \qquad
   \Gamma_{\rm TM} = \frac{\varepsilon\cos\theta - \sqrt{\varepsilon - \sin^2\theta}}
   {\varepsilon\cos\theta + \sqrt{\varepsilon - \sin^2\theta}} .
   \tag{7}$$

   Set $w \leftarrow w\,R$.
4. **Split specular against diffuse** by the Rayleigh coherent fraction,

   $$\kappa = \exp\!\big(-g^{2}\big),
   \qquad g = \frac{4\pi s \cos\theta}{\lambda},
   \tag{8}$$

   where $s$ is the RMS surface height of the class and $\kappa$ is the fraction
   of the reflected power that stays coherent. It is a scalar fraction, not an
   angular density, which is why it is not written $\rho$.

   With probability $\kappa$ the new direction is the mirror
   $\hat u - 2(\hat u\cdot\hat n)\hat n$, otherwise it is drawn cosine weighted
   about $\hat n$. Note the $\cos\theta$: a surface that is rough at normal
   incidence is smooth at grazing, and this is the only place that angle
   dependence enters.
5. **Russian roulette** from bounce 3 onward. Survive with probability
   $p = \mathrm{clip}(w, p_{\min}, 1)$ and set $w \leftarrow w/p$ on survival,
   which is unbiased.
6. Stop at $L$ surface interactions. Rays still travelling are dropped and their
   throughput is reported as `truncated_throughput_share`, so truncation is a
   measured quantity rather than an assumption.

### 5.3 Byproducts that cost nothing

**Sky fraction.** $f_{\rm sky}$ is the fraction of rays escaping with zero
bounces. It is a purely geometric openness measure and it is used as a
walkability gate in section 6.

**Excess delay.** For an escaping ray with total path length $\ell_K$ and last
vertex $\mathbf x_K$,

$$\Delta = \ell_K - \hat u_{\rm ext}\cdot(\mathbf x_K - \mathbf x),
\tag{9}$$

which is the extra path relative to a plane wave arriving from
$\hat u_{\rm ext}$. Throughput weighted, this is the mean excess delay.

### 5.4 The one simplification, stated

Polarisation is carried as the unpolarised power average (7) rather than a
$2\times2$ Jones matrix, so the coherency matrix is taken isotropic in the
transverse plane. This is exact for the depolarised multi bounce tail and for the
closed form checks of section 8, where both polarisations are averaged anyway. It
loses the cross polarisation ratio, which nothing downstream in this study
consumes.

### 5.5 Storage

Nothing that scales with the ray count reaches disk. Each standpoint reduces to a
row of scalars plus one few hundred cell angular spectrum, appended to a JSONL
file, and the paths are discarded. A run is therefore restartable and survives
being killed.

The single exception is a capped path recorder used only for figures. It is
bounded by a capacity set at the call site, it is off in every production run, and
it is asserted by test to leave every traced number bit identical, so the rays
drawn in a figure are the rays that were integrated.

---

## 6. Standpoint sampling

Walkable ground is decided by ray casting, not by a map layer. Over a candidate
grid of spacing $\delta$ within radius $R_{\rm walk}$ of the anchor, 3 m and 90 m
in every run reported here:

1. cast downward and keep the first hit.
2. Require a near horizontal face, $\lvert n_z\rvert \ge 0.85$.
3. Require the hit within a tolerance of the square's ground datum, which rejects
   roofs and bridged geometry.
4. Require a clearance standoff so the head is not inside a wall or a market
   stall.
5. Require $f_{\rm sky} \ge 10^{-2}$, which is the test that catches a standpoint
   inside a building. A clearance test alone does not: a point in the middle of a
   large room has metres of space in every direction and passes, then traces to a
   susceptibility orders of magnitude below its neighbours.

Survivors are chained by greedy nearest neighbour into a walk, and a run traces a
stratified subset of it. At Korenmarkt the clearance standoff takes 821
candidates to 801 and the sky fraction gate then rejects none of them, so gate 5
is insurance rather than a load bearing filter at this site. The counts are in
the `walk` block of every manifest.

**This is a walk, not a sampling design, and the distinction is load bearing.** A
contiguous split half of one site's standpoints gives a Kolmogorov statistic of
0.53 with medians a factor of 2.7 apart. Any claim that a within square
distribution is area representative needs a designed sample instead, and this
draft does not make that claim.

---

## 7. Body coupling

The environment side and the body side are computed independently and composed by
an inner product of two spherical functions. No dosimetry is reimplemented here:
$\rho$ is handed to an existing engine.

For a plane wave of incident power density $S_{\rm inc}$ arriving along $\hat k$,
the absorbed power density at a body surface point with outward normal
$\hat n(\mathbf r)$ is

$$S_{ab}(\mathbf r) = S_{\rm inc}\, T_0\, \mathrm{ReLU}\!\left[\hat n(\mathbf r)\cdot(-\hat k)\right],
\tag{10}$$

with $T_0$ the tissue power transmission coefficient at normal incidence from a
Cole-Cole dispersion. The rectifier is the statement that a surface element only
absorbs from the hemisphere facing the source.

The traced spectrum enters as a set of plane waves, one per occupied direction
cell, with $\hat k_c = -\hat u_c$ and incident density $\rho_c \Delta\Omega\, S_0$.
Integrated quantities follow:

$$P_{\rm abs} = \oint S_{ab}\, dA,
\qquad
\mathrm{SAR}_{\rm wb} = \frac{P_{\rm abs}}{m_{\rm body}} .$$

The phantom is the IT'IS adult male Duke, standing, 72.4 kg, 56,024 surface
triangles.

**A weak consistency check.** Dividing $P_{\rm abs}$ by the mean $S_{ab}$ recovers
1.96 m$^2$ at the median of the 120 Korenmarkt standpoints under rooftop
illumination, which is an adult male body surface area, from two independently
computed quantities. It is weak rather than exact because $P_{\rm abs}$ is the
area weighted integral while the reported mean $S_{ab}$ is an unweighted mean over
triangles, so the ratio is the area only up to the correlation between triangle
area and illumination. Across the 120 standpoints and the three illumination
models it spans 1.80 to 2.05 m$^2$. Recovering the area exactly would need an
area weighted mean, which the pipeline does not currently store.

---

## 8. Validation

The ladder runs from closed form to convergence, and every rung is a test in the
suite rather than a one off.

### 8.1 Parameter free identities

**Zero bounce isotropic susceptibility equals the sky fraction.** Under
$Q = 1/4\pi$, the zero bounce part of (5) is $4\pi \cdot N_{\rm sky}/N \cdot
1/4\pi = f_{\rm sky}$. One check exercises the direction binning, the solid angle
weights, the occlusion test and the normalisation simultaneously, and unlike the
ground plane cases it holds for any geometry at all. It is asserted on a plane, on
a sphere and on empty space in
`tests/test_propagation.py::test_zero_bounce_susceptibility_equals_the_sky_fraction`,
and no file in `outputs/` records a measured pair.

The identity holds to Monte Carlo precision rather than exactly, and the near miss
is worth stating because it reads like a bug. The sky fraction is a ratio of sums
over all rays while the zero bounce susceptibility sums a per cell mean, so the two
differ by the covariance between a cell's escape rate and its ray count. Over the
120 Korenmarkt standpoints of `clean_geometric` the median pair is 0.2465 against
0.2470 and the worst standpoint disagrees by 1.2 %. A companion test asserts the
residual falls as the ray count grows, which a genuine normalisation error would
not. An earlier draft of this section quoted a median of 0.2599 against 0.2599
agreeing to every digit printed, and nothing in `outputs/` reproduces that pair, so
it is not carried forward.

**Free space returns 1 to within the Monte Carlo noise of the run**, for every
illumination model. `outputs/exposure_korenmarkt/exposure_validation.json`, at
400,000 rays and 256 direction cells, gives 1.0000000 isotropic, 0.9874 rooftop
and 1.0107 street small cell, so the directional models sit inside 1.3 %. The
identity is exact in expectation, not per realisation, and the two directional
models are noisier only because their measure is concentrated in a narrow
elevation band. That file predates the section 4.2 correction, so its rooftop and
street entries are the superseded law. The identity itself is law independent.

> **Old illumination law, see `LAW_CHANGE.md`.** The 0.9874 rooftop and 1.0107
> street free space returns are runs under a height and range band $Q$, and so are
> the ones under the 2026-08-02 law that replaced it. The identities themselves
> survive, since free space returns 1 for any normalised $Q$ and the closed forms
> of section 8.2 are scored per elevation band with no illumination model in them.

#### What section 8 cannot catch

Every test here is either an invariant the estimator was built to satisfy or a
closed form derived from the same physics the estimator implements. There is no
independent solver in the loop: nothing here is a comparison against a
second implementation of the same problem, and no measurement is taken anywhere
in this work. So the suite is strong against implementation error and blind to
formulation error. If the illumination construction or the reciprocity
dictionary were conceptually wrong, free space would still return 1, the
conducting plane would still return 2, and the cavity would still conserve
energy. The correction in section 4.2 is a case in point: it was found by
rederiving the integral, not by any test failing.

### 8.2 Closed forms

| case | closed form | measured | in `exposure_validation.json` |
|---|---|---|---|
| perfectly conducting ground plane | $\chi = 2$ exactly | upper hemisphere mean 1.9999823, worst cell 1.15 % | yes |
| dielectric ground plane, 9 elevation bands | band averaged Fresnel | 1.02 % worst relative error | yes |
| Lambertian plane | $K = 1 + 2\sin\alpha$ | exact | **no file** |
| ground plane excess delay | $\Delta = 2z\sin\alpha$ for an observer $z$ above the plane, mean $z/2$ throughput weighted | 2 % | **no file** |
| closed lossless cavity | energy conserving | pass | **no file** |

The last three rows run as tests in `tests/test_propagation.py` and leave no
artifact in `outputs/`, so their tolerances are the assertions in the suite rather
than a recorded measurement. The first two are in
`outputs/exposure_korenmarkt/exposure_validation.json`, which was written before
the section 4.2 correction. Neither depends on the illumination law: the perfect
conductor and the dielectric plane are both scored per elevation band.

The perfect conductor case **cannot discriminate**: both polarisations reflect
fully, so it returns 2 whether the Fresnel average is right, TE only or TM only.
The concrete plane can, and it rejects the TE only answer at every band where the
two separate. A validation that cannot fail is not a validation, and this pair is
the difference.

### 8.3 Convergence, measured rather than assumed

| parameter | curve | operating point |
|---|---|---|
| bounce depth $L$ | $\chi_{\rm iso} = 0.35134$ at $L=4$ against $0.35137$ at $L\ge6$, a 0.0004 dB difference. Truncated throughput share $0.2515$ at $L=1$, $6.3\times10^{-4}$ at $L=4$, $1.4\times10^{-5}$ at $L=6$, $0$ by $L=8$ | $L=3$, see `BOUNCE_BUDGET.md` |
| ray count $N$ | over four seeds, $f_{\rm sky} = 0.23711 \pm 0.00085$ at $2\times10^{5}$ and $0.23695 \pm 0.00027$ at $1.6\times10^{6}$, with the relative standard deviation of $\chi_{\rm roof}$ falling from 2.2 % to 0.8 % over that span | $2\times10^{5}$ |
| crop radius $R_{\rm crop}$ | section 9.4 | 250 m |

Both rows are one standpoint of Korenmarkt at the 130 m crop, recorded in
`outputs/exposure_korenmarkt/exposure_convergence.json`, and that file states it
was recomputed after a `max_bounces` off by one fix so that the parameter now
counts surface interactions. An earlier draft of this table carried
$\chi = 0.29894$ against $0.29902$, a truncated share of $0.567$ at $L=1$ and
$f_{\rm sky} = 0.24596$ at $2\times10^{5}$, which are the pre-fix numbers and are
not reproducible from any file in `outputs/`.

**The $L=4$ against $L=6$ comparison is paired, and read otherwise it means
nothing.** The two differ by 0.0004 dB, far inside the per standpoint Monte Carlo
noise of a single run, so a reader who applies that run's error bar to it would
correctly conclude the comparison is empty. It is not, because both legs trace
*the same rays* at the same seed and are identical up to the fourth interaction.
The difference is a paired one and its error is orders of magnitude smaller than
either number's own.

The operating point is now three surface interactions and it is written in one
place, `DEFAULT_MAX_BOUNCES` in `semantic_twin/propagation/tracer.py`, which
`TraceConfig`, `run_exposure.py` and every driver read. `BOUNCE_BUDGET.md` owns
the justification, which is about where the photographic evidence reaches rather
than about a convergence threshold, and it measures the drop from 4 to 3 at a
median 0.002 dB with no standpoint of 40 moving half a decibel. Russian roulette
is off at that budget, pinned by `roulette_start = DEFAULT_MAX_BOUNCES + 1`.

The operating point was not uniform across the results that predate that change,
and the manifests rather than the prose are the record. Section 9.2's eleven city
run has been retraced at three as `city250_L3_*`. The crop convergence sweep, the
sub street ablation and the law comparison ran at $L=4$. The evidence ladder of
section 9.3, the 120 standpoint Korenmarkt runs behind section 9.1, and the
superseded eleven city run ran at $L=6$. The table above puts $L=4$ and $L=6$
0.0004 dB apart, so those runs are interchangeable at the reported precision.

**Almost no result in this study carries a Monte Carlo error bar.** `PointResult`
has no variance field and no run under `outputs/` reports one. The estimator is
stochastic from the first interaction, not only at the roulette, because the
specular against diffuse choice is a draw on the Rayleigh coherent fraction and
the diffuse directions are cosine sampled. Seeds are fixed so runs reproduce, and
reproducible is not converged. The exception is `CODE_AUDIT.md` section 4, which
retraced 120 standpoints over eight disjoint seed streams and measured the walk
median standard deviation at 0.0042 dB isotropic, 0.0136 dB rooftop and 0.0343 dB
street small cell, and the per standpoint median at 0.004, 0.024 and 0.118 dB.
Those are the only variance measurements in the study.

---

## 9. Results

All numbers at 15 GHz, the FR3 midpoint, with $S_0 = 1$ W m$^{-2}$. Every
absolute quantity is linear in $S_0$, so it is a scale factor and not a physical
claim.

### 9.1 Within one square

120 standpoints at Korenmarkt, the geometric material prior, fifth to ninety
fifth percentile. Both illumination laws are shown because the correction of
section 4.2 changes this table more than any other in the document, and the
superseded column is what every figure and report written before 2026-08-02
carries.

| illumination | $p_{05}$ | median | $p_{95}$ | spread, corrected | spread, superseded |
|---|---|---|---|---|---|
| isotropic | 0.195 | 0.310 | 0.422 | **3.4 dB** | 3.4 dB |
| macro rooftop | 0.077 | 0.217 | 0.503 | **8.1 dB** | 12.5 dB |
| street small cell | 0.007 | 0.096 | 0.314 | **16.7 dB** | 18.5 dB |

Percentiles are the corrected law, `clean_geometric`. The superseded column is
`korenmarkt_geometric`, whose medians are 0.310, 0.138 and 0.065. Isotropic is
untouched by the correction, as it must be.

> **Old illumination law, see `LAW_CHANGE.md`.** Both directional rows and both
> directional spread columns, 8.1 and 16.7 dB as well as the 12.5 and 18.5 dB
> beside them, are band law numbers, and so are the 7.8 dB peak $S_{ab}$ and 8.6 dB
> SAR spreads below. Stale, because a within square spread is set by which
> elevations the built form admits and that is precisely the shape being replaced.
> The isotropic row and its 3.4 dB survive.

**This run is at the 130 m crop, which section 9.4 shows is not converged for
either directional model.** The directional columns are therefore upper bounds:
at 130 m the corrected rooftop number is inflated by about 0.6 dB and the street
one by about 7.2 dB against a 340 m reference. There is no 250 m run over these
120 standpoints, only over the 80 standpoint city walk, so this table cannot be
lifted to the converged radius without retracing.

**The illumination model matters more than the position.** Standing anywhere in
one square changes exposure by 3.4 dB under isotropic illumination, by 8.1 dB
under rooftop macro sites and by 16.7 dB under street small cells, because
directional sources arrive in narrow elevation bands that the built form either
admits or blocks completely. Under the superseded law the two directional
figures were 12.5 and 18.5 dB, so the correction cuts the rooftop claim by more
than 4 dB while leaving the ordering intact.

Carried to the body, the same standpoints give a peak $S_{ab}$ spanning 7.8 dB
and a whole body SAR spanning 8.6 dB under the corrected rooftop law, against
12.7 and 13.0 dB superseded. The dosimetric endpoint inherits the illumination
geometry's spread, not the scene's average openness.

![Exposure distribution over one square](FIGURES/14_exposure_cdf_korenmarkt.png)

**Figure 7.** Korenmarkt over 120 standpoints. Left is the environment side, the
susceptibility under the three illumination models. Middle is the body side,
absorbed power density through the phantom. Right places each standpoint on the
ground, spanning 22 dB from the open square to the deepest street. The spatial
panel carries the point: the open square runs 10 to 15 dB hotter than the streets
leaving it, and that is geometry rather than material.

**This asset is stale and must be rebuilt before submission.** It is the
superseded illumination law, it does not match any file currently in `outputs/`,
and its axis label still carries the pre-overhaul symbol $\chi_S$. The rooftop and
street curves in the left panel are the superseded column of the table above.

### 9.2 Across eleven squares

80 standpoints per city, common 250 m crop, identical material prior, so only
urban form varies.

**No image evidence enters this table.** Every run here is `materials:
geometric`, the orientation rule of section 2.2, at
`covered_fraction_by_area = 0.0` for all eleven sites including Korenmarkt. That
is a defensible control, since a comparison in which materials also varied would
confound urban form with material assignment, and section 9.3 measures the
material term separately. But it is also the only run the pipeline can produce:
`run_exposure.py` refuses `--materials semantic` or `--materials walk` at any
site except Korenmarkt, because no other site has a binding.

The gap between what the semantic stage produces and what this table consumes is
worth stating plainly, because it is large.

| stage | built for | reaches this table |
|---|---|---|
| panoramas acquired | 10 of 11 sites | none |
| skyline registrations | 83 poses at 8 sites | none |
| fishnet surfaces | 2 sites | none |
| SAM 3 material axis | 12 panoramas, the two hero captures plus the ten Korenmarkt walk stations | none |

The 83 poses carry nine site labels in
`outputs/registration_sky_conflict.csv`, but `korenmarkt` and `korenmarkt_walk`
are the same square, so the distinct site count is eight.

Krakow, London and Toulouse have no panoramas at all, so a materially bound
eleven city comparison is not merely unbuilt, it is unacquirable without
returning to those three sites. Sixty nine of the 83 registrations, at Brussels,
Madrid, Mexico City, New York, Prague and Tokyo, are computed and audited in
section 3.2.1 and then consumed by nothing. The claim this table supports is
therefore about **built form under a common material assumption**, and the word
semantic in this pipeline's name describes section 9.3's Korenmarkt experiment
rather than the eleven city result.

The run is `city250_L3_*`, the single writer sweep at a bounce budget of three on
the measured ground datum, 880 standpoints with no torn records.
`AGGREGATE_REBUILD.md` audits it and lists every number that moved against the
earlier `city250_corrected_*` tag this section used to carry.

| site | isotropic median | rooftop median | street median | isotropic spread [dB] | rooftop spread [dB] |
|---|---|---|---|---|---|
| Mexico City Zocalo | 0.3977 | 0.3070 | 0.0291 | 2.19 | 5.06 |
| London Trafalgar | 0.3946 | 0.2884 | 0.0276 | 4.04 | 4.55 |
| Krakow Rynek | 0.3841 | 0.2681 | 0.0232 | 1.70 | 2.86 |
| Prague Staromestske | 0.3584 | 0.2377 | 0.0197 | 4.29 | 4.95 |
| Milan Duomo | 0.3559 | 0.2451 | 0.0375 | 2.80 | 2.55 |
| Madrid Plaza Mayor | 0.3433 | 0.1447 | 0.0079 | 6.46 | 9.35 |
| Toulouse Capitole | 0.2963 | 0.2219 | 0.0174 | 5.17 | 11.40 |
| Ghent Korenmarkt | 0.2916 | 0.1626 | 0.0143 | 2.85 | 6.39 |
| Tokyo Hachiko | 0.2334 | 0.0996 | 0.0161 | 3.36 | 5.46 |
| Brussels Grand-Place | 0.2223 | 0.0987 | 0.0067 | 5.88 | 12.89 |
| New York Times Square | 0.1694 | 0.1271 | 0.0604 | 3.92 | 5.77 |

Spreads are the fifth to ninety fifth percentile within each site. All three
illumination columns are the corrected law of section 4.2.

**The superseded rooftop column that used to sit inside this table has moved to
the law comparison below**, because it belongs to a different run in two ways at
once. It was computed under the superseded elevation law *and* on the superseded
ground datum, which put the Krakow and Toulouse standpoints on the roof of the
Cloth Hall and of the Capitole. Reading it as a column of this table implied a
pairing that does not exist. The runs it comes from, `city250_*` and
`city250_corrected_*`, are kept on disk so any number published before
2026-08-03 can still be located.

Medians span **3.71 dB isotropic, 4.93 dB rooftop and 9.58 dB street small
cell**. The largest spread *within* one square is 6.46 dB isotropic at Madrid,
and 12.89 dB rooftop at Brussels. So under isotropic illumination, where in a
square a person stands matters more than which of eleven cities on three
continents the square is in, by a margin of 2.75 dB.

Mexico City Zocalo is the most exposed of the eleven on both isotropic and
rooftop illumination. Rank correlation between the columns is Spearman +0.936
for rooftop against isotropic and +0.345 for street against isotropic.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street columns,
> the 4.93 and 9.58 dB between city spans, the rooftop within city spreads and both
> Spearman figures are computed against a height and range band $Q$, so the city
> order under directional illumination is stale and has to be remeasured. The
> isotropic column, its 3.71 dB span, the 6.46 dB Madrid spread and the ground
> datum work behind them are geometry alone and survive.

![Eleven squares, one pipeline](FIGURES/16_eleven_cities_exposure.png)

**Figure 8.** The study's central object. 80 standpoints per city at the
converged 250 m crop, one common material prior, so what varies between curves is
urban form. Left is susceptibility under rooftop illumination, middle is sky
fraction, right is peak absorbed power density at the phantom. The middle panel
is the one to trust unreservedly, because sky fraction converges by 100 m and
carries no illumination assumption at all.

**This asset was rebuilt on 2026-08-03 and now draws the table above.** It comes
from `city250_L3_*` through `FIGURES/make_eleven_cities_exposure.py`, which
refuses to draw unless all eleven sites are present, every standpoint count is
equal and no line failed to parse. The version shipped before that date was
copied from an aggregate a concurrent run was still writing, so its legend read
`brussels grandplace (3)` and its rooftop panel was the superseded law.
`AGGREGATE_REBUILD.md` is the audit of that failure. One cosmetic defect
survives the rebuild: the susceptibility axis still carries the pre-overhaul
symbol $\chi_S$.

Krakow is no longer the outlier at the right of the panels, and the reason is
worth keeping rather than quietly dropping. Under the superseded ground datum its
datum sat 18.19 m above the surrounding pavement, so its standpoints were on the
roof of the Sukiennice, and Toulouse had the same defect at 13.94 m on the
Capitole. The estimator took the median downward first hit over a 15 m disc at
the crop centre, and at both sites the centre of the square is a building.
`GROUND_DATUM.md` carries the replacement rule, the eleven measured datums, and
three independent checks on them, including agreement with the registered camera
ground height to 0.30 m at the eight sites that carry one. Coming down to the
pavement moved Krakow by $-1.40$ dB isotropic, $-5.26$ dB rooftop and $-12.97$ dB
street, and Toulouse by $-1.29$, $-1.83$ and $-2.61$ dB. Nine of the eleven
datums move by less than a quarter of a metre and their medians move by 0.001 to
0.24 dB, which is the standpoint resampling rather than the physics.

**The law correction is not cosmetic, and it is measured on the superseded
datum run rather than on the table above.** The comparison below pairs
`city250_*` against `city250_corrected_*`, both at the old datum, because those
are the only two runs that share standpoints and differ only in the elevation
law. Its Krakow and Toulouse rows are therefore the roof, and its absolute levels
are not the ones in the table above. What survives the datum fix is the shape of
the correction, not the levels. The isotropic column is unaffected and comes out
bit identical, to within 0.001 dB at every site, because the isotropic model has
no elevation weight to correct. What the correction does to the rooftop column,
on the same standpoints at the same crop:

| | superseded | corrected |
|---|---|---|
| per site shift | | $+1.06$ to $+6.33$ dB |
| Spearman against the superseded order | | 0.78 |
| rooftop over isotropic range across the eleven | 11.32 dB | 6.12 dB |
| corr(log $\chi_{\rm roof}$, log $\chi_{\rm iso}$) | 0.56 | 0.85 |

Three things follow, and the third is the one that matters for the paper.

**It cannot be offset corrected.** The shift spans 5.27 dB across sites, which is
the same size as the 5.93 dB spread of the superseded medians across the ten sites
other than Krakow.

**It reorders the cities.** New York Times Square falls six places of eleven, from
third highest to third lowest. That is the measure table speaking rather than an
anomaly: grazing is wide open along an avenue, and the corrected rooftop measure
sits at 10 to 30 degrees, which is where the towers are.

**The rooftop column loses most of its independence from geometry.** Its
correlation with the isotropic column rises from 0.56 to 0.85. It still carries
urban form, but with 6 dB of range rather than 11, and much of what looked like a
distinct directional story was the superseded law's grazing weight interacting
with occlusion.

The mechanism of the level shift is one sentence. The superseded law put its
measure in the first few degrees above the horizon, where a pedestrian's sky is
almost always blocked by the far side of the square, so it reported a
susceptibility dominated by the rare standpoint with an open sightline down a
street. The corrected law puts the rooftop measure at 10 to 30 degrees, where the
sky is open more often, so $\chi$ rises toward the isotropic value.

**One thing the correction does not do**, stated because it would be easy to claim
and would be wrong. It does not narrow the within square spread at a converged
crop, where rooftop moves 0.72 dB and street 0.14 dB. The large narrowings, 2.91
and 1.66 dB, occur at the unconverged 130 m crop, and they are crop artefact
rather than illumination: grazing power escaping through occluders the small crop
had deleted, which varies violently from standpoint to standpoint. So this is not
an argument that the within square spread reported in section 9.1 is inflated.

> **Old illumination law, see `LAW_CHANGE.md`.** This entire comparison prices one
> band law against another band law, so the 1.06 to 6.33 dB per site shift, the
> Spearman 0.78 reordering, the fall of New York by six places, the 11.32 dB to
> 6.12 dB narrowing and the 0.56 to 0.85 correlation rise are all distances between
> two superseded models. Stale, and the facade tip law has to be paired against
> these runs again before any of it can be repeated.

**Under isotropic illumination, variation inside one square exceeds variation
between eleven cities on three continents.** A per city or per country exposure
figure therefore averages over a variation larger than the differences it reports.

### 9.3 What image evidence is worth

Four runs, 120 standpoints, same walk, same seed. The only thing varying is what
fraction of scene area carries material from observed image evidence rather than
from the geometric rule of section 2.2. Every pose behind every rung passes the
sky conflict gate of section 3.2.1, which was audited rather than assumed.

| evidence by area | by face | source | rooftop median | shift | standpoints moving $>1$ dB |
|---|---|---|---|---|---|
| 0 % | 0 % | orientation rule only | 0.1377 | | |
| 3.13 % | 2.07 % | one registered panorama | 0.1380 | **0.008 dB** | **0 of 120** |
| 10.57 % | 6.88 % | eight stations, fused | 0.1472 | **0.289 dB** | **1 of 120** |
| 11.02 % | 7.30 % | nine stations, every pose the conflict gate passes | 0.1475 | **0.298 dB** | **1 of 120** |

Rooftop medians in that table are under the superseded illumination law of
section 4.2, so the first three rows are the numbers published before
2026-08-02 and reproduce them to the last stored digit at every one of the 120
standpoints.

**The 0.298 dB figure must not be quoted as measured.** It is computed under the
superseded fixed height law, it has never been measured under the corrected one,
and the eight seed replica study of `CODE_AUDIT.md` section 4.2 does not carry
it, so no standard error exists for it. The corrected law equivalents are the
first two rows of the every model table below, at 0.350 dB isotropic and
0.364 dB rooftop.

**No rung of this ladder ever consumed a conflicting pose.** Korenmarkt has
thirteen registered poses and three of them conflict on their whole sky, and all
three sat outside the ladder already, because the semantic stage gates on a
4 degree skyline residual and those three register at 6.27, 6.98 and 8.10
degrees. The single panorama rung conflicts on 4.1 % of its sky and the eight
fused stations on 0.49 to 7.52 %, median 3.3 %.

The residual gate reached the right pose set here by luck rather than by
construction, and section 3.2.1 is why: it also rejected `walk_11` at 6.37
degrees, which conflicts on 10.3 % of its sky and is usable. Gating on the
conflict instead readmits that station, and that is the fourth rung. The
correction therefore **raises** the top of the ladder from 10.57 to 11.02 % of
area rather than eroding it.

Ungated, the three failing poses would have read as the best rung of the ladder.
Apparent coverage doubles to 22.75 % of area and 14.82 % of faces, and it is
fake: 6430 triangles the orientation rule calls roof or soffit are relabelled
brick, against 1328 in the published eight and 1438 in the conflict passing nine,
because a camera inside the geometry sees roof surfaces no street level camera
can see. The exposure distribution does not notice that either, giving a rooftop
median of 0.1477 and a 0.302 dB shift against the clean set's 0.298 dB. So the
insensitivity survives even a material field that is wrong on a seventh of the
scene.

Every illumination model, at the top rung against the zero evidence rung:

| illumination | 0 % | 11.02 % | shift | $>1$ dB | spread at 0 % | spread at 11.02 % |
|---|---|---|---|---|---|---|
| isotropic | 0.3099 | 0.3359 | 0.350 dB | 17 of 120 | 3.36 dB | 3.88 dB |
| rooftop, section 4.2 corrected | 0.2165 | 0.2354 | 0.364 dB | 8 of 120 | 8.13 dB | 8.40 dB |
| rooftop, as published | 0.1377 | 0.1475 | 0.298 dB | 1 of 120 | 12.47 dB | 12.47 dB |
| street small cell, corrected | 0.0965 | 0.0982 | 0.079 dB | 1 of 120 | 16.70 dB | 16.63 dB |

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows of
> both tables, their medians, their shifts and their 8 to 17 dB spreads, are band
> law runs, so the levels move under the facade tip law. The finding survives,
> because it is a comparison of two material fields on one set of rays and the
> isotropic row, which no illumination change touches, carries the largest movement
> of the four.

**The street small cell row is a single draw from a noisy distribution and is
not resolved.** `CODE_AUDIT.md` section 4.2 retraced this shift over eight
disjoint seed streams and got 0.079 to 0.269 dB, a factor of 3.4, with the seed 7
value printed above the lowest of the eight. The seed averaged value is
$0.167 \pm 0.022$ dB. So the tempting reading of the four rows, a shift that
shrinks monotonically as the illumination gets more directional, does not
survive: on seed averaged numbers the trend is 0.347, 0.383 and 0.167 dB and it
is not monotone.

The isotropic row is the one the section 4.2 correction cannot touch, and it is
also the row that moves most, both in the count of standpoints and in the width
of the distribution, which goes from 3.36 to 3.88 dB. That is the narrowest of
the four distributions, so a movement that is negligible against a 12 dB spread
is not negligible against a 3 dB one. **The per standpoint picture is
not a null and should not be quoted as one.** Under isotropic illumination the
worst single standpoint moves by 1.98 dB and 17 of 120 move by more than 1 dB,
while the median standpoint moves by 0.06 dB and the distribution median by
0.35 dB. The movement is strongly asymmetric: 53 standpoints fall and 66 rise, the
falls reach at most 0.24 dB and the rises reach 1.98 dB, which is why the median
*signed* shift is 0.0007 dB and quoting that as the typical movement understates
it by two orders of magnitude. The effect is concentrated in a minority rather
than absent. The published "1 of 120" is true of the rooftop model it was measured
on and is the most flattering of the four rows.

**This is a strong negative rather than a null.** The semantic posterior and the
orientation prior **disagree on 50 % of the area they both cover** over the
conflict passing nine, and on 51 % over the published eight. On the nine, 1438
faces the rule called concrete are brick, 1221 it called asphalt are brick, 440
are metal, 467 are marble and 556 it called brick are vegetation. The
distribution still moves by a third of a decibel against spreads of 3 to 17. So
it is not a case of two methods producing the same materials. It is a case of
materials mattering less than geometry over the range street level capture
reaches.

The honest reading is that **geometry sets the distribution, and the semantic
layer earns its place through occlusion handling, evidence confidence and cross
capture validation rather than by moving the exposure number.** That is both more
defensible and more falsifiable than the claim it replaces.

#### The material axis, tested

The ladder above varies entity coverage. Whether resolving brick against glass on
the same facade also moves exposure is a separate question, and it was untested
until 2026-08-02. It is now tested and the answer is a stronger null.

`semantics.py` runs a cascade. Mask2Former on Mapillary Vistas owns the entity
axis, and SAM 3 owns the material axis, because Vistas has a single `Building`
class covering brick, render, ashlar, glass curtain wall and metal cladding,
whose permittivity and roughness are not close to each other. The published
ladder ran `mask2former` alone on all eight walk stations, so `bind_from_walk`
mapped the Vistas entity through a fixed $p(\text{material}\mid\text{entity})$
table and took the argmax. `Building` resolves to `brick` deterministically, and
`Building` is **74.3 %** of the 42,005 face observations the eight stations bind,
74.6 % of the 44,755 the nine bind. In that binding `semantic_glass` claims 1
triangle of 157,862 and `semantic_plasterboard` claims none.

The hybrid backend has now been run on all eight stations, with the dense pass
reused from cache so the entity axis is byte identical and only the material axis
is new. Pooled over the eight, SAM 3 splits the `Building` and `Wall` pixels
59.8 % brick, 23.0 % glass, 14.4 % plasterboard and 1.8 % marble, and 28.5 % of
the facade area the entity axis called brick is reassigned: 11.9 % to glass,
9.5 % to plasterboard, 4.8 % to marble. `semantic_glass` goes from 1 triangle to
958 and `semantic_plasterboard` from 0 to 653. At 15 GHz brick to glass is
$+2.35$ dB in normal incidence reflectance and specular rather than rough, and
brick to plasterboard is $-2.49$ dB.

Rebinding those facades and rerunning the same 120 standpoints:

| illumination | entity axis | SAM 3 material on the facades | shift | standpoints $>0.5$ dB | worst standpoint |
|---|---|---|---|---|---|
| isotropic | 0.3360 | 0.3379 | **0.024 dB** | **0 of 120** | 0.110 dB |
| rooftop, corrected | 0.2354 | 0.2369 | **0.029 dB** | **0 of 120** | 0.193 dB |
| street small cell | 0.0984 | 0.0989 | **0.022 dB** | 1 of 120 | 0.929 dB |

Against fifth to ninety fifth percentile spreads of 3.9 dB isotropic, 8.4 dB
rooftop and 16.7 dB street small cell in those same distributions, and against
the 1.98 dB the worst standpoint moves when entity coverage goes from 0 to
10.6 %, material discrimination on the facades is not a term in this problem.
Repeating it on the nine conflict gated stations gives 0.023 dB isotropic and
0.024 dB rooftop with the same 0 of 120, so the null does not depend on which
walk set is used.

> **Old illumination law, see `LAW_CHANGE.md`.** The rooftop and street rows of the
> table are band law runs and their levels will move. The conclusion survives: the
> photographs establish a material family, masonry against glass and metal, rather
> than tune a permittivity, and that bracket argument rests on the 2.35 dB brick to
> glass and 9.67 dB brick to metal reflectance contrasts and on the area
> reassigned, none of which turns on the shape of $Q$.

**One measurement in this experiment moves and must not be misread.** Replacing
the *whole* material field with the SAM 3 axis, rather than only the facades,
shifts the isotropic median by $-0.218$ dB and moves 15 of 120 standpoints by
more than 1 dB. That is not material discrimination. It is the material axis
overwriting surfaces whose entity already determines their material: 932 m$^2$
the entity called metal, 982 m$^2$ marble, 306 m$^2$ vegetation and 177 m$^2$
asphalt all flow into brick, and metal to brick alone is a 9.67 dB reflectance
drop on poles and street furniture. Measured on the axis it is competent at, the
open vocabulary pass is worse than the class prior. So the conclusion is the one
this section already reached, now confirmed on the second axis: **entity
segmentation carries the material field, and material segmentation on top of it
does not move exposure.**

Cross capture agreement is the weakest number in the experiment. Independent
captures of the same facade agree on the entity 71.3 % of the time across
sequences and on the material only 42.3 %, with a worst pair at 24.5 %. The
material axis is therefore noisier evidence as well as less consequential
evidence, and a study that needed material at higher confidence would need more
than one detector.

This result is bounded by the square it was measured in. Korenmarkt is historic
masonry, so the `Building` prior's brick default is approximately right and the
tested swap is brick to glass at 2.35 dB. A square of metal cladding or glass
curtain wall would test brick to metal at 9.67 dB, and nothing here licenses that
case. The full run is in `SAM3_LADDER.md` and
`outputs/exposure_korenmarkt/sam3lad_*`.

One limit stands unchanged. The ladder spans 0 to 11.0 % of area, which is as far
as street level capture reaches, and it licenses nothing about a fully evidence
bound scene. Roofs, courtyards and rear elevations are 55 % of the surface and no
panorama count reaches them.

Every number here is in `outputs/exposure_korenmarkt/coverage_ladder_conflict_gated_15ghz.json`,
the conflict passing station set is `outputs/walk_korenmarkt/walk_semantic_conflict9.npz`,
and the top rung is

```
python run_exposure.py --locations 120 --materials walk --tag clean_walk9 \
    --walk-npz outputs/walk_korenmarkt/walk_semantic_conflict9.npz
```

![The evidence ladder](FIGURES/17_evidence_ladder.png)

**Figure 9.** The same 120 standpoints with the same seed, varying only how much
of the scene carries material from image evidence. Zero to a tenth of the scene
shifts the median by 0.29 dB, and the three curves lie on top of each other. That
is the result. Note that the axis is the rooftop model, which is the most
flattering of the four: the per standpoint movement under isotropic is larger,
and the table above is the one to read for that.

**This asset predates the conflict gate and the section 4.2 correction.** It shows
three rungs at 0.0, 3.1 and 10.6 % of area rather than the four in the table, its
axis is the superseded rooftop law, and it carries the pre-overhaul symbol
$\chi_S$. The conclusion is unchanged under all four laws, so the figure is stale
rather than wrong, but it should be rebuilt from
`outputs/exposure_korenmarkt/coverage_ladder_conflict_gated_15ghz.json`.

---

### 9.4 The crop radius is not a free parameter

![Crop convergence at Korenmarkt](FIGURES/15_crop_convergence.png)

**Figure 10.** Nine crops from 60 to 340 m with the standpoints held fixed inside
the smallest, so every radius scores the same 32 pedestrians and only the
surroundings change. The three illumination models order by how close to the
horizon they put their weight, and that is also the order of how much crop they
need. Throughout, the small crop is not missing scatterers that would add power,
it is missing **blockers** that would remove it, which is why every curve
approaches its limit from above. The asset is
`outputs/crop_convergence/korenmarkt_crop_convergence.json` and its plot, which is
**the superseded illumination law only**. The corrected law is the table below and
is not in this figure.

Nine crops at Korenmarkt from 60 m to 340 m with the standpoints held fixed, so
only the surroundings change.

Deviation of the observer mean from a 340 m reference, 24 observers, one mesh per
radius, all laws scored on one traced pass so the columns are exactly paired. The
medians give the same table to 0.1 dB and the same converged radius everywhere, so
nothing here turns on the statistic.

| crop | rooftop, superseded | rooftop, corrected | street, superseded | street, corrected |
|---|---|---|---|---|
| 130 m | 3.545 | 0.601 | 10.359 | **7.229** |
| 160 m | 1.023 | 0.167 | 4.751 | 2.593 |
| 200 m | 0.156 | **0.017** | 1.206 | 0.561 |
| 250 m | 0.014 | 0.000 | 0.200 | **0.059** |
| 300 m | $-0.001$ | $-0.001$ | 0.019 | 0.001 |

**This table has no source file.** Nothing in `outputs/` reproduces it, and the
same table appears in `MONOSTATIC_SBR.md` with two further columns for a path loss
weighted law, also unsourced. Two crop sweeps were persisted and neither is this
one. `outputs/crop_convergence/korenmarkt_crop_convergence.json` holds 32
observers and `outputs/exposure_korenmarkt/exposure_crop_by_illumination.json`
holds 27, both against the same 340 m reference, and both carry the superseded law
alone. Their 130 m rows are

| observers | rooftop, superseded | street, superseded |
|---|---|---|
| 32 | 3.236 | 9.930 |
| 27 | 3.277 | 10.181 |
| 24, this table | 3.545 | 10.359 |

so the unsourced set sits 0.3 dB above both. That is the size of the standpoint set
disagreement rather than a contradiction, and it is also the check quoted below as
"a reproduction with a different standpoint set agreeing to 0.25 dB", which is the
street column of the 32 against the 27. The corrected columns have no counterpart
at all. The run has to be rerun and committed before this table can be published.

Converged at a 0.1 dB criterion: sky fraction and isotropic by 100 m, rooftop 250
to **200 m**, street small cell 300 to **250 m**.

**250 m stays required, and it is now set by the street model alone.** This was
worth testing rather than assuming, because the crop requirement was always
attributed to grazing weight and the correction removes most of the grazing
weight. It does relax the rooftop requirement, in from 250 to 200 m. It does not
relax the binding one. A 130 m crop still misprices street small cell illumination
by 7.23 dB, against 10.36 before, so this is a 3.1 dB reduction in a defect that
was never small.

> **Old illumination law, see `LAW_CHANGE.md`.** The claim that 250 m is set by the
> street model alone is stale, because both directional columns of the crop table
> are band law runs and the crop requirement follows directly from how much measure
> a law puts near the horizon. The mechanism survives, that a wider crop adds
> blockers rather than scatterers, and so does the isotropic column, which converges
> by 100 m. The crop radius has to be re-established under the facade tip law before
> 250 m can be justified again.

The mechanism is that a small crop holds no geometry able to occlude near horizon
sources, so rays escape to sky that a real building would have blocked. A larger
crop adds missing **blockers**, not missing scatterers, and the number goes down.
Decomposed, blocking accounts for 69 % of the rooftop effect and 77 % of the
street one, with redistribution of multi bounce throughput carrying the rest.
$\chi$ splits with no residual into its zero bounce and multi bounce parts, so
this decomposition contains no modelling. Source
`outputs/exposure_korenmarkt/exposure_crop_decomposition.json`, 27 observers,
superseded law.

**The crop correction is not a constant offset.** Measured as the shift in the
median from a 130 m mesh to a 250 m mesh over the ten sites that have both, Milan
being the one site with no 130 m build, it ranges 0.05 to 4.80 dB rooftop, 0.16 to
11.39 dB street and $-0.17$ to 0.96 dB isotropic, where tall cities move most and
Brussels alone moves the other way. That range is comparable to the whole between
city spread, so a narrow crop distorts sites relative to each other rather than
shifting them together, and a between site comparison at 130 m is not safe either.
Both legs of this comparison are the **superseded** illumination law, the
`city_*` and `city250_*` tags, and it has not been remeasured across the ten sites
under the corrected law. At Korenmarkt, where it has, the 130 m to 250 m median
shift falls from 4.58 to 1.09 dB rooftop and from 11.37 to 8.21 dB street on the
80 city standpoints, and from 3.64 to 0.51 dB and 10.08 to 6.94 dB on the 40
standpoint set of `outputs/law_comparison/korenmarkt_law_comparison.json`. The two
standpoint sets disagree on the size and agree on the direction and on which model
binds.

Three independent routes agree on this. The crop sweep itself. A reproduction on a
different standpoint set, 27 observers against 32, agreeing to 0.04 dB rooftop and
0.25 dB street at the 130 m radius where the disagreement is largest. And
registration, where the worst site's poses all look south across 200 m of open
plaza and improve by about 30 % when re fitted against the 250 m shell. The third
route has no persisted artifact and is reported here as a recollection rather than
a measurement.

A refuted rule is recorded because it read well: *the crop must reach the farthest
source*. Rooftop sources reach 250 m and rooftop converges at 250 m, which looks
like confirmation. Street small cells reach only 150 m and converge **later**. The
surviving explanation is the grazing weight, not the source range.

The grazing explanation now has a quantitative check rather than only a
directional one. Correcting the elevation law drops the rooftop measure below 5
degrees by a factor of 6.6, from 61.7 % to 9.4 %, and it drops the rooftop crop
error at 130 m by a factor of 5.9, from 3.545 to 0.601 dB. Two independent tables
agreeing to within 12 % on a factor that large is a stronger statement than the
sign agreement the mechanism previously rested on.

**The 250 m figure is a Korenmarkt measurement.** Milan Duomo is the only other
site with meshes at multiple radii, 170, 200 and 250 m. It agrees on rooftop, with
0.08 dB left in the 200 to 250 step, and it does not agree on street, where 0.95 dB
is still moving against Korenmarkt's 0.50, and there is no larger Milan mesh to
settle it. If anything the pressure on the street requirement is upward. These four
numbers come from the same unpersisted run as the paired table above and share its
provenance problem. The three Milan meshes exist, so the comparison is
reproducible, it just has not been written down.

---

## 10. Threats to validity

1. **Diffraction is absent.** Deliberately, and it is the largest known hole.
   Section 4 shows the illumination measure is dominated by low elevations, where
   a shadow boundary is exactly where a rectilinear tracer is least trustworthy.
2. **Vegetation routes to a vacuum row**, which removes an earlier 72 dB of
   invented reflection but is still wrong: a vacuum face absorbs where a canopy
   should partly transmit. The correct treatment is a participating medium.
3. **A walk is not a sampling design**, section 6.
4. **The brickwork model is unvalidated at FR2.** It matches to 2.0 dB at 4 GHz
   with nothing fitted, and the only FR2 measurement available cannot adjudicate
   because its own repeat scatter exceeds the disagreement.
5. **Coherent fading is out of scope by construction**, section 1.4.
6. **One unresolved internal disagreement.** A sky fraction of 0.2271 is on record
   for one camera against 0.2464 from two independent code paths. One is wrong and
   it is not yet known which.
7. **The illumination caps are uncited**, section 4.3.
8. **Panorama semantics exist at one site of eleven.** Section 9.3 is what makes
   that tolerable rather than fatal, but it is a real limit on the semantic claims.
9. **Roughly half the registered poses across the study are unusable**, section
   3.2.1. Section 9.3 is now audited against that and is clean: none of the three
   fully conflicting Korenmarkt poses ever entered the ladder, and the ladder has
   been recomputed over the conflict passing set. What remains is that the pose
   gate in the semantic stage is still the 4 degree residual, which is the
   criterion section 3.2.1 shows cannot see the failure. It admitted no bad pose
   at this site and rejected one good one, so the exposure result is safe and the
   gate is not. Feeding the conflict fraction into `ObservationQuality` is the
   outstanding work, and any new site is exposed until it is done.

> **Old illumination law, see `LAW_CHANGE.md`.** Threat 1 rests on the old law's
> low elevation weight and threat 7 says the caps are uncited, and the facade tip
> law has no caps to cite, so both are stated against a model that no longer
> applies. Threats 2 to 6, 8 and 9 are about geometry, materials, sampling and
> registration and survive as written.

---

## 11. Status of each result

Being explicit about what is finished. Updated 2026-08-02, after the illumination
correction of section 4.2 was derived, implemented and measured.

> **Old illumination law, see `LAW_CHANGE.md`.** Every row that reads recomputed,
> restated or corrected means recomputed under the 2026-08-02 band law, which is
> itself superseded, so no row here is a statement about the current law. The rows
> for the eleven city rooftop column, the within square spread, the crop radius, the
> per site crop correction and the deployment caps are stale. The isotropic rows,
> the validation ladder, the datum fix, the registration row and the run provenance
> row survive.

| result | status |
|---|---|
| Section 8, validation ladder | **stable, partly unpersisted.** The closed forms are single height or isotropic, so the correction cannot touch them, and the suite passes under the corrected law. Only the conducting and dielectric planes leave an artifact in `outputs/`. The Lambertian plane, the excess delay and the cavity are assertions in `tests/test_propagation.py` with no recorded measurement |
| Section 8.3, convergence table | **recomputed and previously stale.** The bounce and ray count rows now come from `exposure_convergence.json`. The figures an earlier draft carried predate a `max_bounces` off by one fix and are not reproducible |
| Section 9.1, within square spread | **restated under the corrected law and at an unconverged crop.** It was 12.5 dB rooftop and 18.0 dB street, both superseded and both unlabelled. Corrected it is 8.1 and 16.7 dB. The run is at the 130 m crop, so both directional figures are upper bounds. At a converged crop the correction moves the spread only 0.72 dB rooftop and 0.14 dB street, which is a different comparison and not a substitute for retracing these 120 standpoints at 250 m |
| Section 9.2, eleven cities, isotropic column | **stable and bit identical.** The isotropic model has no elevation weight to correct |
| Section 9.2, eleven cities, rooftop column | **recomputed twice, all eleven sites.** First for the law, a site dependent shift of 1.06 to 6.33 dB that reorders the cities and cannot be offset corrected, then again for the ground datum. The table now carries `city250_L3_*` only, and the law comparison is stated separately because it lives on the superseded datum run |
| Section 9.3, material axis | **tested, and the null holds.** SAM 3 now runs on all eight walk stations. It reassigns 28.5 % of the facade area the entity prior called brick, putting 958 triangles on glass and 653 on plasterboard against 1 and 0 before, and the exposure distribution moves 0.024 dB isotropic and 0.029 dB rooftop with 0 of 120 standpoints moving as much as 0.5 dB, and 0.023 and 0.024 dB on the nine station set. Bounded to a masonry square: the tested swap is brick to glass at 2.35 dB, not brick to metal at 9.67 dB |
| Section 9.3, evidence ladder | **stable, and re-run under both laws over conflict passing poses only.** None of the three failing Korenmarkt poses was ever in it, the top rung rises from 10.57 to 11.02 % of area, and the conclusion is unchanged under isotropic, corrected rooftop and street |
| Section 9.4, crop radius | **conclusion stable, evidence partly unpersisted.** 250 m still required, now set by the street model alone, measured at one site with Milan disagreeing on street. The paired superseded against corrected table, the Milan comparison, and the "reorders the cities" crop claim all come from a 24 observer run that was never written to `outputs/`. Two persisted sweeps at 27 and 32 observers cover the superseded law only and sit 0.3 dB below it. Rerun and commit before submission |
| Section 9.4, per site crop correction | **superseded law, ten sites not eleven.** The 0.05 to 4.80 dB rooftop and 0.16 to 11.39 dB street ranges are `city_*` against `city250_*`, both the old law, and Milan has no 130 m mesh so it cannot enter. The isotropic range is $-0.17$ to 0.96 dB, not 0.03 to 0.96: Brussels moves the other way |
| Section 4.3, deployment caps | **assumptions with a measured sensitivity, not citations.** No deployed FR3 exists to calibrate against, section 4.3.1 |
| Section 9.2, material coverage | **the eleven city table carries no image evidence.** `materials: geometric`, covered area 0.0 at every site. Only Korenmarkt has a binding, and three of the eleven cities have no panoramas at all. 69 of 83 registrations feed no result |
| Monte Carlo error bars | **no longer absent, done 2026-08-02.** Every value reported in the paper drafts now carries one, obtained by retracing the same standpoints over disjoint seed streams rather than estimated from within a single run. The results in this file predate that and still carry none. A larger error term than the Monte Carlo one has since been found: standpoint sampling, about 0.13 dB rms and 0.24 dB worst on a per square median, roughly 25 times the Monte Carlo error |
| Bounce depth provenance | **the stated operating point is not uniform.** $L=4$ for the corrected eleven cities, the crop sweep, the sub street ablation and the law comparison. $L=6$ for the evidence ladder, the 120 standpoint Korenmarkt runs and the superseded eleven cities. Class default 12, CLI default 6. Worth 0.0004 dB, so the numbers stand and the prose should not claim a single operating point |
| Section 8, external cross validation | **no longer absent, done 2026-08-02.** An independent solver is now in the loop. Production agrees with Sionna to 0.25 dB at Korenmarkt and 0.16 dB at Brussels, against a Monte Carlo floor of 0.24 to 0.46 dB, so the comparison is at the noise. Two limits stand: the two tracers share the same susceptibility $Q$, so the check covers transport and not the illumination model, and the comparison is a product of averages against an average of products. `CROSS_VALIDATION.md`. The row's original worry, that a shared conceptual error would survive, is narrowed rather than removed |
| Section 3.2.1, registration | **stable, but the poses it validates are mostly unused.** 83 poses, diagnostic persisted and independently reproducible |
| Section 9.2, Krakow and Toulouse rows | **fixed, and the requalified run has landed.** The table above is `city250_L3_*` on the measured datum, so both rows are now street level. The old `ground_datum()` took the median first hit from above within 15 m of the anchor, so an anchor standing on a building returned that building's roof. Krakow's datum was 18.19 m above the surrounding pavement and Toulouse's 13.94 m, which put their standpoints on the Sukiennice and the Capitole. `GROUND_DATUM.md` carries the replacement, a lowest major level over the walk disc, which agrees with the registered camera ground height to 0.30 m at the eight sites carrying one and with an independently written second estimator to 0.19 m. Nine of the eleven datums move by less than a quarter of a metre and Madrid, previously flagged as suspect at 5 m, is not one of them |
| The eleven city figure asset | **regenerated on 2026-08-03.** It is drawn from `city250_L3_*` by `FIGURES/make_eleven_cities_exposure.py`, which refuses to draw a ragged or torn aggregate and names the offending sites. The committed PNG before that date had been copied from an aggregate a concurrent run was still writing, so it showed Brussels at 3 standpoints under the superseded rooftop law. The axis still carries the pre-overhaul symbol $\chi_S$, which is the one defect left |
| Figure assets 14, 16 and 17 | **16 is regenerated, 14 and 17 are still orphaned.** Neither of the remaining two matches any file now in `outputs/`, so the plots behind figures 7 and 9 cannot be reproduced from the committed data without rerunning the plotting step. Those two are the superseded law and the old notation. Asset 15 is byte identical to `outputs/crop_convergence/korenmarkt_crop_convergence.png` and is fine, but it shows the superseded law only |
| Run provenance | **three holes.** `dirty_walk12` binds from a `walk_semantic_all12.npz` that lives in a session scratch directory rather than in `outputs/`, and several `mesh_study_scores/*.json` name their input mesh the same way. Those runs are not reproducible from the repository as committed. And the published `clean_geometric`, `clean_semantic`, `clean_walk8` and `clean_walk9` runs came from a working tree carrying a fourth illumination model that is not at HEAD, so re-running them at HEAD reproduces the isotropic median to three digits but moves individual standpoints by up to 0.011 dB isotropic, 0.034 dB rooftop and 0.614 dB street. The tracer itself is exactly deterministic across machines and core counts, so that is code state and nothing else. Section 9.3's material axis experiment was re-run at HEAD for this reason |

Two things a reader should be able to check quickly. Every superseded run is kept
beside its replacement rather than overwritten, so the eleven city sequence
`city250_*`, `city250_corrected_*`, `city250_datum_*` and `city250_L3_*` is all
on disk and each step of it can be diffed against the next. And the superseded
elevation laws are still in `propagation/directions.py` as named models, so any
published number can be reproduced rather than merely apologised for.

---

## 12. Reproduction

```
python screen_cities.py                                    # candidate screening
python download_inhouse_tiles.py --lat .. --lon .. --radius-m 250
python fetch_site_panoramas.py --scene config/<site>.json --count 14 --zoom 5
python -m semantic_twin.semantics --panorama .. --backend mask2former --view-size 1536
python -m semantic_twin.align_skyline --mesh .. --semantics .. --pose ..
python build_fishnet_surface.py
python run_exposure.py --validate                          # section 8
python run_exposure.py --locations 120 --materials geometric \
    --tag clean_geometric                                  # section 9.1
python run_exposure.py --locations 120 --materials walk \
    --tag clean_walk9 \
    --walk-npz outputs/walk_korenmarkt/walk_semantic_conflict9.npz   # section 9.3
python run_exposure.py --all-sites --locations 80 --crop-m 250 \
    --rays 200000 --max-bounces 3 --seed 7 --tag-suffix _L3   # section 9.2
python run_crop_convergence.py                             # figure 10 only
python build_propagation_blends.py                         # the walkthrough blends
```

One default does not match the shipped runs and has to be passed explicitly.
`--crop-m` defaults to 130 while section 9.2 is at 250. `--max-bounces` now
defaults to 3, which is what section 9.2 ran at, so passing it is documentation
rather than necessity. The 120 standpoint runs of sections 9.1 and 9.3 are at the
130 m crop and at $L=6$, which is what their manifests record and which no
current default will reproduce. `run_crop_convergence.py` writes the 32 observer sweep
behind figure 10 and does not produce the paired corrected table of section 9.4,
which has no script in the repository.

Full design in `MONOSTATIC_SBR.md`, decisions in `DECISIONS.md`, the fishnet in
`FISHNET.md`, the walk in `WALK.md`, acquisition and screening in `CITIES.md`.

---

## Appendix A. Symbols

| Symbol | Meaning | Units |
|---|---|---|
| **Geometry** | | |
| $\mathbf{x}$ | observation point, a pedestrian head position | m |
| $\hat u$ | unit direction on the sphere, measured **outward** from $\mathbf{x}$ | |
| $\hat k$ | propagation direction of an arriving wave, $\hat k = -\hat u$ | |
| $\hat n(\mathbf r)$ | outward surface normal at a body point | |
| $\mathbf x_K$ | last scattering vertex of an escaping path | m |
| $\ell_K$ | total path length of an escaping ray | m |
| $\alpha$ | elevation above the pedestrian's horizon | rad or deg |
| $\phi$ | azimuth | rad |
| $\theta$ | angle of incidence from a surface normal | rad |
| $r$ | horizontal range from pedestrian to source | m |
| $h$ | source height above the pedestrian head | m |
| $z_0$ | local ground datum of the square | m |
| $\delta$ | any finite increment, including the standpoint grid spacing | |
| $R_{\rm crop}$, $R_{\rm walk}$ | scene crop radius and standpoint search radius | m |
| **Illumination** | | |
| $\nu$ | areal density of base station sites on the ground | m$^{-2}$ |
| $f_h(h)$ | height distribution of the source population | m$^{-1}$ |
| $Q(\hat u)$ | illumination density on the sphere, $\int_{4\pi} Q\, d\Omega = 1$ | sr$^{-1}$ |
| $\tilde Q(\alpha)$ | the same weight before normalisation, $W/\sin^{3}\alpha$ | |
| $\mathcal N$ | its normalisation, section 4.4 | |
| $q(\alpha)$ | its marginal in elevation, $q = 2\pi\cos\alpha\ Q$ | rad$^{-1}$ |
| $W(\alpha)$ | admissible height window at a given elevation, equation (4) | m$^{3}$ |
| $a(\alpha), b(\alpha)$ | lower and upper limits of that window | m |
| **Transfer and estimator** | | |
| $K(\hat u)$ | transfer kernel, scene power density over free space power density | |
| $\chi$ | susceptibility, $=1$ in free space | |
| $\rho(\hat u)$ | arriving angular power density, $\int \rho\, d\Omega = \chi$ | sr$^{-1}$ |
| $w_j$ | throughput of ray $j$ where it escapes the scene | |
| $N$ | rays launched per standpoint, $2\times10^{5}$ | |
| $M$ | Fibonacci cells partitioning the sphere, 512 | |
| $\Delta\Omega$ | solid angle of one such cell, $4\pi/M$ | sr |
| $L$ | maximum surface interactions per ray | |
| $p$, $p_{\min}$ | Russian roulette survival probability and its floor, 0.05 | |
| $\Delta$ | excess delay of an escaping ray, equation (9) | m |
| $f_{\rm sky}$ | fraction of the sphere from which a ray escapes unobstructed | |
| **Materials and body** | | |
| $\varepsilon$ | complex relative permittivity, negative imaginary part | |
| $R(\theta,\varepsilon)$ | unpolarised Fresnel power reflectance | |
| $s$ | RMS surface height of a rough interface | m |
| $g$ | Rayleigh roughness parameter, $g = 4\pi s \cos\theta/\lambda$ | |
| $\kappa$ | coherent (specular) fraction of reflected power, $\kappa = e^{-g^{2}}$ | |
| $S_0$ | free space incident power density the network would deliver | W m$^{-2}$ |
| $S_{\rm arr}$ | power density actually arriving, $S_{\rm arr} = S_0\chi$ | W m$^{-2}$ |
| $S_{ab}(\mathbf r)$ | absorbed power density at body surface point $\mathbf r$ | W m$^{-2}$ |
| $P_{\rm abs}$, $m_{\rm body}$ | absorbed power and phantom mass, 72.4 kg | W, kg |
| $T_0$ | tissue power transmission coefficient at normal incidence | |
| $\lambda$ | free space wavelength, 20 mm at 15 GHz | m |

Symbols local to one argument are not listed. Section 2.1 uses $\varrho$ for a
tile request radius and $H$ for ellipsoidal height, and neither appears again.
Section 2.3 uses $a$, $b$, $c$ and $d$ for P.2040-4's four power law coefficients,
which is the one place those letters are not the window limits of section 4.2 and
the one place $d$ is not a differential.

---

## Appendix B. Figures

Regenerate the explainer figures with

```
python FIGURES/make_explainer_figures.py
```

which writes PDF and PNG for figures 1, 2, 3 and 6 into `FIGURES/`, as assets
18 to 21. Asset numbers are the collection's, and are independent of the figure
numbers used in this document. The result figures are made by the scripts named
in `FIGURES/README.md`.
