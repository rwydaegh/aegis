# Why not: the three modelling omissions, argued from the literature

Three things this study leaves out or simplifies, and the case for each. They are
the same kind of question, which is why they sit in one document: each is a place
where the estimator could have been more general, and each is a place a reviewer
will ask why it was not.

1. **No diffraction term.** Section 2.
2. **An adjoint shoot and bounce estimator rather than an image source or path
   finding tracer.** Section 3.
3. **Polarisation carried as an unpolarised power average rather than a Jones
   matrix.** Section 4.

A fourth question gets a short section because the same literature answers it:
why the bounce loop stops where it does. Section 5.

Section 6 is drop in replacement prose for the paragraphs of `PAPER_METHODS.md`
that currently assert these choices without argument. Section 7 is the reference
list with DOIs. Section 8 records what could not be reached and what is still
weak, because the honest version of this document has to say where the argument
runs out.

Every number below was read from a source, and every source is either in
`lit/` or is a computation in this repository. Where a claim rests on a figure
that had to be read off a plot rather than a printed table, it says so. No
measurement was taken for this document and none will be.

---

## 1. What is being defended, and what is not

The estimator of `PAPER_METHODS.md` section 5 is rectilinear. Rays leave the
standpoint, reflect specularly or scatter diffusely off triangles, and escape.
There is no edge in the model, so a direction whose straight line to the sky is
blocked contributes nothing at zero bounces, and whatever it would have carried
has to be recovered through a reflected path or not at all.

That is a real omission and section 2 does not argue it away. What it argues is
narrower and, I think, defensible: **at 15 GHz, in an open square where a
shadowed standpoint still sees illuminated facades, the diffracted share of
arriving power is small, and this has been measured rather than assumed.** The
two geometries where that fails are named in section 2.5 and one of them is
inside this study's scope.

---

## 2. Why there is no diffraction term

### 2.1 The scaling law, and what it is worth from 2 to 15 GHz

The uniform theory of diffraction gives a diffracted field proportional to
$1/\sqrt{k}$, so diffracted **power** falls as $\lambda$, which is 10 dB per
decade of frequency relative to a reflected path that is frequency flat.

I could not read Kouyoumjian and Pathak's 1974 paper. It is closed access with no
repository copy, so the $\sqrt{\lambda}$ prefactor is cited here from
reproductions that print it in full rather than from the original: the Sionna RT
technical report annex A.8 equations (153) to (156) give the four wedge
coefficients as
$D_{1\ldots4} = -e^{-j\pi/4} / \big(2n\sqrt{2\pi k}\,\sin\beta_0\big)\cdot\cot(\cdot)\cdot F(kLa^\pm)$,
attributing them to Kouyoumjian and Pathak and to Luebbers, and METIS D1.4
reproduces the same set at equations 6-29 to 6-39. The $1/\sqrt{k}$ is explicit
in both.

The same slope falls out of a recommendation that is in force. **Recommendation
ITU-R P.526-16 (11/2025)**, section 4.1, gives the Fresnel-Kirchhoff parameter in
four equivalent forms, of which equation (26) is

$$\nu = h\sqrt{\frac{2}{\lambda}\left(\frac{1}{d_1}+\frac{1}{d_2}\right)},$$

and equation (31) gives the single knife edge loss, stated as valid for
$\nu > -0.78$,

$$J(\nu) = 6.9 + 20\log_{10}\!\left(\sqrt{(\nu-0.1)^2+1} + \nu - 0.1\right)\ \text{dB}.$$

For large $\nu$ this tends to $12.95 + 20\log_{10}\nu$, and $\nu \propto \sqrt{f}$
at fixed geometry, so $J$ grows by 10 dB per decade of frequency. From 2 to
15 GHz that is $10\log_{10}(15/2) = 8.75$ dB of extra diffraction loss at the same
corner, in the deep shadow limit. Near the shadow boundary it is less: at
$d_1 = 30$ m, $d_2 = 15$ m and a 2.9 degree diffraction angle the same formula
gives 6.3 dB, converging on 8.8 dB beyond about 10 degrees.

Three independent readings of the same slope, all from sources in `lit/`:

| source | frequency step | source's number | $\lambda$ law predicts |
|---|---|---|---|
| METIS D1.4 section 5.9, measured indoor corner | 2.4 to 58.68 GHz | about 15 dB | 13.9 dB |
| METIS D1.4 figure E-6, UTD on a concrete wedge | 1 to 40 GHz | about 16 dB | 16.0 dB |
| Ericsson R1-160846 slide 9, the diffraction model curve | 2.44 to 58.68 GHz | 10.1 dB per decade | 10.0 dB per decade |
| ITU-R P.1411-13 equation (66), the measured fit $S_1 \propto f^{-0.46}$ | | 9.2 dB per decade | 10.0 dB per decade |

The last row is a measurement fit rather than a theory curve, and it is a fit over
430 to 4860 MHz, so reading it at 15 GHz is outside the printed range. It is
listed because it agrees, not because it is load bearing.

**Two caveats printed in P.526-16 itself and worth carrying.** The angle form of
$\nu$ assumes the diffraction angle is "less than about 0.2 rad, or roughly 12°".
And section 4 opens with the warning that "these models do not take into account
the profile transverse to the direction of the radio link, which may have a
significant effect on diffraction loss". A city square is exactly a geometry with
transverse profile. Both caveats are handled in section 2.4.

### 2.2 What is measured, at 14.8 GHz, in a street canyon

The scaling law says diffraction weakens. It does not say by itself that
diffraction stops mattering, because the competing mechanisms could weaken too.
The measurement that settles it for this band and this kind of geometry is
Ericsson's, and it is unusually well matched to the study.

**3GPP TSG-RAN WG1 #84, R1-160846, Ericsson, "Street Microcell Channel
Measurements at 2.44, 14.8 and 58.68 GHz", Malta, February 2016.** No DOI, it is
a tdoc. The campaign is a real outdoor street microcell, matched 2 dBi dipoles at
both ends at all three frequencies, transmitter at 1.5 m, receivers at 5 m and
1.5 m, bandwidth equalised to 80 MHz across bands, the same greater than 10 dB
dynamic range imposed at every frequency, and noise power subtracted. The middle
band is 14.8 GHz.

Slide 9 carries the diffraction prediction and its refutation in one figure. The
printed annotation on the measured NLOS excess loss is

> "Frequency dependency of NLOS Excess Loss: 3.5 Log(f) for RX1, 3.0 Log(f) for
> RX2"

so the measured excess loss grows at **3.0 to 3.5 dB per decade**, against the
**10 dB per decade** of the theoretical corner diffraction curve plotted on the
same axes. Those two slopes are the argument. The tdoc's own words, verbatim from
slides 7, 9 and 10:

> "Diffraction contribution to received signal not significant! The frequency
> dependency in NLOS is weak!"
>
> "Reflected/scattered paths dominates over diffraction in NLOS as received
> signal is orders of magnitude stronger than expected from diffraction around
> corner"
>
> "Diffraction contribution negligible in NLOS ... Results support that the main
> propagation mechanisms are specular reflections and scattering by objects"

The slope numbers above are printed text. Absolute dB values from the same slide
have to be read off a plot and are not quoted here.

The same campaign appears in reviewable form in **mmMAGIC deliverable D2.2**,
section 2.2.3, page 15, and that write up adds the detail that matters most:

> "In the NLOS region behind the corner of the building, a substantial increase
> in the excess loss is observed. This loss is substantially lower than what
> would be expected by knife-edge diffraction only. ... At the delay
> corresponding to the diffraction path around the corner, no signal above the
> noise floor is observed. The first cluster of weak paths is observed at
> substantially longer propagation distances than the diffraction path length.
> ... The strongest peak stands out having around 20 dB higher power level than
> the rest of the power delay profile. It was possible to match the delay of this
> path with a ray-traced path using four specular reflections off exterior
> building walls. This result shows that specular paths may be important even far
> into the NLOS region."

Read that as an experiment on the estimator used here. In a street canyon at
these frequencies, the arrival at the corner diffraction delay was **below the
noise floor**, and the dominant arrival was a **four bounce specular path**. That
is a description of what an SBR tracer with enough bounce depth computes and a
diffraction term does not. It is also, in section 5, the reason the bounce loop
does not stop at two.

The same deliverable records the measured NLOS frequency dependence as "about
3 dB per decade increase of frequency", consistent with the tdoc.

### 2.3 What the published models do, and where they say why

Nothing in the standards says "diffraction is irrelevant above 6 GHz". What they
do instead is stop carrying it, or carry less of it as frequency rises, and the
pattern is consistent enough to cite.

**Recommendation ITU-R P.1411-13 (09/2025)** is the sharpest, because it switches
mechanism with frequency for the same geometry. For a below rooftop street
crossing:

- Section 4.1.3.1, **800 to 2000 MHz**: "For NLoS2 situations where both antennas
  are below roof-top level, diffracted and reflected waves at the corners of the
  street crossings have to be considered", and equation (14) is an explicit power
  sum of a reflection loss and a diffraction loss,
  $L = 10\log_{10}(10^{-L_r/10} + 10^{-L_d/10})$.
- Section 4.1.3.2, **2 to 38 GHz**: **there is no diffraction term at all.** The
  model is a corner loss region plus an NLoS region, with $L_{\rm corner} = 20$ dB
  urban and $d_{\rm corner} = 30$ m, "derived based on measurements at a frequency
  range from 2 to 38 GHz". Where the recommendation explains a departure from the
  base case, it attributes it to specular reflection: "Because the specular
  reflection paths from chamfered-shape buildings significantly affect basic
  transmission loss in NLoS region ...".

So the ITU's own below rooftop street model drops the diffraction term precisely
at the band boundary this study sits inside, and replaces it with an empirical
corner loss whose stated physical attribution is specular.

**3GPP TR 38.901** (read as ETSI TR 138 901 V19.4.0, 2026-07, and the XPR rows
checked identical in v18.0.0). The stochastic model of clause 7, which is what is
used across the whole 0.5 to 100 GHz scope, **has no diffraction propagation
mechanism**. Every occurrence of diffraction in clause 7 is inside an optional
blockage sub model, clause 7.6.4.2 model B, described there as "a simple knife
edge diffraction model", and clause 7.6.14.1.2. Diffraction exists as a path only
in the optional map based hybrid model, clause 8.4 step 3, table 8.4-1, where the
geometry is Fermat's principle and the field is UTD, and where the note reads:
"For reasons of simplicity and simulation speed ... the maximum order of
diffraction on a path without reflection is configurable from {1,2}." Be honest
about what this is: it is structural evidence, not a quotation tying diffraction
to frequency. TR 38.901 contains no such sentence.

**The 5GCM white paper, "5G Channel Model for bands up to 100 GHz" (2015)**, does
tier diffraction by frequency, at exactly the threshold in question. Section 7.2,
UMa: "the maximum number of rays in the simulation was 20, no transmissions
through buildings were allowed, the maximum number of reflections was four, the
maximum number of diffractions was one for frequencies above 10 GHz and was two
for frequencies of 10 GHz and below." A joint industry white paper choosing to
halve the diffraction order above 10 GHz is a precedent for treating it as a
frequency dependent choice.

**mmMAGIC D2.2** section 2.2.2, page 14, describes the project's own ray tracing
calibration at 14.25, 27.45, 61 and 83.5 GHz: "The considered propagation
mechanisms included first and second order specular reflections." No diffraction,
at this study's frequency.

**Sionna RT** ships with `diffraction=False` and `edge_diffraction=False` in the
path solver defaults, and publishes the reason. Technical report section 3.1.2:
"diffraction typically carries much less energy compared to reflection and
refraction, which would result in very low probabilities for sampling diffraction
if its probability were also based on the diffraction coefficients." Section 3.1
adds that paths mixing diffraction with diffuse reflection are prohibited outright
because such paths "typically contribute negligibly to the total transported
energy and therefore have little impact on the accuracy of the CIRs", and that
"Sionna RT currently supports only first-order diffraction".

**NYURay**, the NYU group's calibrated tracer, states it flatly: "Therefore,
neglecting diffraction, NYURay models propagation due to specular reflections,
transmissions, and diffuse scattering."

**IEEE 802.11ad/ay channel models**, document IEEE 802.11-09/0334r8, twice:
"Reflections from other objects ... and also the propagation due to diffraction
are not included in the model". That is indoor 60 GHz, so it is directional
support only.

**ITU-R P.2040-3** has exactly one occurrence of the word diffraction, in the
noting clauses, deferring to P.526. Its twenty eight pages are reflection,
transmission and rough surface scattering.

And from a group that does implement diffraction and does not have to say this,
Vitucci, Degli-Esposti, Fuschini et al., Radio Science 54(11):1112-1128, 2019,
doi 10.1029/2019RS006869, section 2 on their own tracer: "Over-roof-top (as
diffraction in general) is not expected to be very important at the Ka band
frequencies compared to other interaction mechanisms, anyway." Later, section 4,
they attribute their residual overestimation to "the relative lack of diffraction
and over-roof-top" at mm-wave frequencies.

### 2.4 What fraction of the power is actually diffracted, where anyone measured it

Two numbers, both from calibrated ray tracing against real measurements.

**NIST and Volcano, 28 GHz, downtown Boulder** (Charbonnier et al., IEEE TVT,
doi 10.1109/TVT.2020.3038620), from the abstract and section VI:

> "diffuse scattering ... accounted on average for 20% of the total measured
> power per Rx, whereas the specular rays only accounted for 5%; 75% was
> attributed to the direct ray and the power attributed to diffraction was less
> than 1%."

Carry that paper's own footnote 6 with it: "In other scenarios, e.g. the
urban-canyon environment, a higher percentage of specular power could be expected
due to the waveguide effect." The campaign is 61 receivers over 488 acquisitions
at up to 55 m, largely LOS or near LOS, so the sub 1 % is not a canyon number.

**Adhikari et al., IEEE INFOCOM 2025**, doi 10.1109/INFOCOM55648.2025.11044468,
22 Manhattan urban microcell routes past a corner at 28 GHz. Table III average
best fit RMSE: a street clutter scattering description gives 6.4 dB, a diffraction
inspired description gives 6.6 dB, and 3GPP UMi NLOS gives 11.9 dB. A pure
scattering description and a diffraction description are statistically tied, which
means diffraction is not required to explain around the corner behaviour in a
canyon. It does not mean it is absent.

### 2.5 The counter-evidence, stated properly

There is real published evidence that diffraction still matters in the 10 to
30 GHz range, and the paper is stronger for naming it.

**It is validated as a model at 10 GHz.** Tervo et al., 5GU 2014,
doi 10.4108/ICST.5GU.2014.258145: "a building corner can be modeled by the
KED-theory at 10 GHz ... KED can be used as a diffraction loss model for RT at
10 GHz." Two honest caveats. The diffracted component had to be isolated by angle
of arrival beam scanning and time gating before it could be seen at all, and the
paper gives no absolute diffraction loss table, its figures folding in a
$-59.5$ dB instrument offset. Cite it for "KED is validated at 10 GHz", not for a
number.

**It is the better functional fit in a real 28 GHz canyon, from a rooftop site.**
Du, Chizhik, Valenzuela et al., "Directional measurements in urban street canyons
from macro rooftop sites at 28 GHz for 90% outdoor coverage", IEEE TAP
69(6):3459-3469, 2021, doi 10.1109/TAP.2020.3044398. A spinning horn receiver at
roof edges at commercial base station heights, an omnidirectional transmitter on a
tripod in the middle of a sidewalk, 3000 links on 12 streets in two cities, over
21 million CW power measurements. Measured: after turning a corner in a Manhattan
canyon "signal drops about 14 dB after 10 m into the corner, and about 21 dB after
50 m into the corner", and "the single-slope diffraction inspired model provides
the best fit, with 3.4 dB RMS error using only two parameters", against 6.6 dB for
the scattering model in their table 2.

Note the title. That is a **macro rooftop** geometry, which makes it the same
regime as the over-top case below rather than a separate objection.

**Quote the next sentences too, because they cut the other way**, verbatim:

> "the corner loss is very small, only 2.2 dB ... This may also be compared to the
> theoretical edge diffraction coefficient, which at large diffraction angles
> (deep shadow) is on the order of -42 dB at 28 GHz. Similar findings have been
> reported in around-street corner measurements for 400 MHz to 4.8 GHz where an
> empirical 'scattering coefficient' ... was found to be much larger than the
> theoretical edge diffraction coefficient. This was attributed to scattering
> from lampposts and other street furniture."

So the diffraction *functional form* fits, while the physical UTD coefficient is
about 40 dB too small to produce what was measured, and the authors' own
explanation is street furniture. That is a clutter argument dressed as a
diffraction argument, and it lands on a different weakness of this study, the one
recorded in the clutter notes, rather than on this one.

**The geometry where diffraction genuinely wins.** Adhikari et al., table V, urban
macrocell, with the elevated node on a rooftop "20 m higher than nearby
buildings". The caption is the finding: "Over-Top-NLOS appears to be the dominant
propagation mechanism, with a 7 dB improvement compared to Street-Clutter-NLOS."
Average best fit RMSE across three sites: Over-Top-NLOS 4.3 dB, Street-Clutter
plus Over-Top 4.1 dB, Street-Clutter-NLOS alone 11.1 dB. When one endpoint is
above the skyline and the shadowed street level endpoint sees no illuminated
corner or facade, over rooftop diffraction is the mechanism and canyon scatter is
wrong by about 7 dB. Reciprocity makes it irrelevant which endpoint is the
transmitter.

**This one is inside scope and must be conceded.** The macro rooftop illumination
model of section 4.3 places sources at 13.5 to 43.5 m above head height, which is
above the skyline at several of the eleven squares. For a standpoint deep in a
side street with no illuminated facade in view, that is the Adhikari geometry, and
the estimator is in its worst case there. Section 2.6 bounds it.

**And a reminder that the deep shadow story is not simply "diffraction over
predicts".** Lopes et al., Sci. Rep. 16:17345, 2026,
doi 10.1038/s41598-026-41462-x: knife edge reaches 3.1 dB RMSE for 60 GHz links
obstructed by parapets, but the same paper reports "the 11.7 dB corner loss
observed here is substantially less loss than the 46 dB loss predicted by edge
diffraction theory". Two regimes, two verdicts, in one paper.

### 2.6 A bound for this geometry

Everything above is about street canyons in general. This section bounds what a
diffraction term could have added **to the standpoints actually traced in this
study**, using the meshes the production runs used.

**Construction.** At a standpoint, cast a dense direction grid, azimuth uniform
and elevation logarithmic so that the first few degrees above the horizon are
resolved, and record hit or miss and hit range. For each blocked cell take
$\theta$, the great circle angle to the nearest visible cell, as the depth into
the geometric shadow, and $d$, the range to the shadowing edge. Form the
Fresnel-Kirchhoff parameter of P.526-16 equation (27) in the distant source limit,

$$\nu = \theta\sqrt{2d/\lambda},$$

take $J(\nu)$ from equation (31), and report

$$\chi_{\rm diff} = \sum_{\text{blocked}} Q(\hat u)\, 10^{-J(\nu)/10}\, \Delta\Omega ,$$

which is the zero bounce power a single edge diffraction term could restore. The
code is `bound_diffraction.py`, the output is `outputs/diffraction_bound/`.

**Assumptions, and the direction each one errs in.**

| assumption | effect on the bound |
|---|---|
| A single absorbing half plane per blocked direction, no multiple diffraction | **upper.** Real deep shadow needs two or more edges, each adding loss |
| Distant source, $1/d_1 \to 0$ in equation (26), so $\nu$ takes its smallest value | **upper.** A source at 25 to 250 m raises $\nu$ and therefore the loss |
| Knife edge rather than a finite conducting wedge | **upper** in the deep shadow. Tenerelli's measured 28 GHz masonry corners lose more than knife edge theory at large angles, section 2.7 |
| The diffracted ray is not re-blocked on its way in | **upper** |
| The edge range is the hit range of the blocked cell nearest the sky boundary | neither, and it is the one soft choice. Two harder variants are reported beside it |
| P.526's angle form applied beyond its stated 12 degree validity | **upper**, since the paraxial form under-predicts loss at large angles. The share of the bound coming from cells inside 12 degrees is reported |
| Diffracted power added on top of the traced reflected power, not competing with it | **upper**, and this is deliberate. The bound answers "how much could be missing", not "what would the answer become" |

Every one of them errs upward, so the number is a bound and not an estimate, with
one exception that has to be stated and is handled by construction.

**The exception: paths that diffract and then reflect.** The sum above is the zero
bounce diffracted term only. A path that diffracts over an edge and then reflects
off a facade before reaching the standpoint is also missing from the estimator and
is not in that sum. Each such path pays the diffraction loss *and* a reflection
loss, so the family is subdominant, and the natural scale for it is the
standpoint's own measured multipath gain, $\chi / \chi_{\rm direct}$, which the
production runs record and which is 1.4 to 3.1 at these standpoints. Every number
in the table below is the zero bounce diffracted term **multiplied by that
standpoint's own multipath gain**, so the reported figures already carry the
correction. That is an assumption about the diffracted family behaving like the
reflected one, and it is the least defended step in the construction.

**One thing the bound does not have to worry about.** $Q$ indexes the *source*
direction, so a diffracted contribution belongs in the $Q(\hat u)$ bin of the
direction the source occupies, regardless of which direction the field ends up
arriving from at the standpoint. That is exactly what the estimator's own
bookkeeping does with $\hat u_{\rm ext}$, so $\chi$ is unaffected by the
redirection. Only the directional body coupling of section 7 would notice, and
this document does not touch it.

**Validation of the machinery.** The same sky mask, integrated against $Q$ over
the *visible* directions, has to reproduce the zero bounce susceptibility
$\chi_{\rm direct}$ that the production tracer recorded from 200 000 Monte Carlo
rays. It is an independent code path, an independent quadrature and an independent
ray budget. Agreement is quoted per site below and is the reason to believe the
blocked half.

**What was run.** The three most enclosed of the eleven squares, by median sky
fraction, and within each the twenty most enclosed standpoints of the eighty in
the production run. That is deliberately the worst case: these are the standpoints
where the blocked measure is largest and a diffraction term has the most room to
matter. Grid 720 azimuths by 600 logarithmic elevation bands from 0.05 to 90
degrees, 432 000 cells per standpoint, on the same 250 m meshes and the same
standpoint coordinates as the corrected eleven city run.

| site | n | sky fraction | median edge range | median shadow depth |
|---|---|---|---|---|
| Korenmarkt, Ghent | 20 | 0.087 to 0.188 | 31 m | 26 deg |
| Grand Place, Brussels | 20 | 0.024 to 0.102 | 38 m | 35 deg |
| Times Square, New York | 20 | 0.035 to 0.076 | 98 m | 34 deg |

**Validation, first.** The sky mask integrated against $Q$ over the visible
directions against $\chi_{\rm direct}$ from the production Monte Carlo:

| model | Korenmarkt | Brussels | Times Square |
|---|---|---|---|
| isotropic | 0.10 % median, 0.54 % max | 0.18 %, 1.05 % | 0.34 %, 1.29 % |
| macro rooftop | 0.84 %, 3.17 % | 1.14 %, 6.44 % | 1.73 %, 6.16 % |
| street small cell | 2.34 %, 11.26 % | 3.94 %, 14.55 % | 7.26 %, 23.05 % |

Two independent code paths agreeing to a fraction of a percent on the isotropic
model is the strong result. The street small cell row is the weak one, and the
reason is structural rather than a bug: that model puts 87.9 % of its measure
below 5 degrees of elevation, where a 200 000 ray Monte Carlo has few samples and
a 600 band logarithmic grid is resolving a very thin sliver of sky. Both estimates
are noisy there, and every street small cell number below inherits that.

**The bound.** Uplift on $\chi$, in dB, for the edge variant, multiplied by each
standpoint's own multipath gain as described above. `floor` is the strict variant,
every blocked direction assigned the nearest surface range anywhere at that
standpoint. `shallow` is the share of the 15 GHz bound contributed by cells inside
P.526's stated 12 degree validity for the angle form.

| site | model | median, 15 GHz | max, 15 GHz | median, 2 GHz | max, 2 GHz | median floor, 15 GHz | shallow |
|---|---|---|---|---|---|---|---|
| Korenmarkt | isotropic | **0.05** | 0.14 | 0.15 | 0.37 | 0.16 | 97 % |
| Korenmarkt | macro rooftop | **0.16** | 0.41 | 0.53 | 1.54 | 0.86 | 96 % |
| Korenmarkt | street small cell | **0.43** | 4.77 | 1.92 | 11.76 | 4.29 | 80 % |
| Brussels | isotropic | **0.08** | 0.19 | 0.24 | 0.58 | 0.27 | 97 % |
| Brussels | macro rooftop | **0.17** | 1.20 | 0.63 | 4.66 | 1.09 | 93 % |
| Brussels | street small cell | **0.60** | 12.64 | 2.67 | 21.19 | 4.96 | 63 % |
| Times Square | isotropic | **0.06** | 0.13 | 0.19 | 0.39 | 0.45 | 98 % |
| Times Square | macro rooftop | **0.12** | 0.51 | 0.40 | 1.52 | 0.99 | 97 % |
| Times Square | street small cell | **0.28** | 1.78 | 0.83 | 3.64 | 1.81 | 98 % |

Pooled over all 60 standpoints:

| model | median | 90th percentile | max | same at 2 GHz, median | linear ratio, 2 GHz over 15 GHz |
|---|---|---|---|---|---|
| isotropic | 0.06 dB | 0.13 dB | 0.19 dB | 0.18 dB | 3.09, which is 4.9 dB |
| macro rooftop | 0.15 dB | 0.37 dB | 1.20 dB | 0.53 dB | 3.53, which is 5.5 dB |
| street small cell | 0.44 dB | 1.84 dB | 12.64 dB | 1.82 dB | 4.98, which is 7.0 dB |

**What this says.**

1. **Under the isotropic and macro rooftop models the omission is small.** A
   diffraction term could add at most 0.15 dB to the median deep canyon standpoint
   and 1.20 dB to the worst one out of sixty, under a construction where every
   assumption errs upward. The spread between squares that this study reports is
   8.1 dB rooftop and 16.7 dB street within one square, and 30 dB across the
   eleven, so a 0.15 dB bound does not touch any conclusion. Even the strict
   `floor` variant, which assigns every shadowed direction the nearest surface at
   the standpoint and is far too generous to be believed, stays under 1.1 dB in the
   median.
2. **Under the street small cell model it is not small, and this should be
   conceded.** The median is 0.44 dB, the 90th percentile is 1.84 dB and one
   Brussels standpoint reaches 12.6 dB. That model puts 87.9 % of its measure below
   5 degrees of elevation, so almost all of its illumination arrives from grazing
   directions that a deep canyon blocks completely. Four of the twenty Brussels
   standpoints have a street small cell $\chi_{\rm direct}$ of exactly zero, meaning
   the model's entire elevation support is occluded and every watt in the traced
   answer arrives by reflection. Those are precisely the standpoints where a
   diffraction term would matter most and where this estimator has the least to say.
   They also have the smallest absolute $\chi$ in the study, of order $10^{-5}$, so
   a large relative correction to a very small number is what is being reported.
3. **The frequency argument reproduces on this geometry.** Rerunning the identical
   calculation with $\lambda$ at 2 GHz raises the bound by a factor of 3.1 to 5.0,
   which is 4.9 to 7.0 dB. That is below the 8.75 dB asymptotic slope of section
   2.1, and it should be: the bound is dominated by shallow shadow, where $J(\nu)$
   has not yet reached its $20\log_{10}\nu$ asymptote. The point is that the same
   geometry, the same code and the same standpoints give a materially larger
   diffraction hole at 2 GHz than at 15 GHz. The omission is a property of the band,
   not of the estimator.
4. **The bound sits inside the recommendation it uses.** Between 93 % and 98 % of
   it, under the isotropic and rooftop models, comes from directions less than 12
   degrees into geometric shadow, which is where P.526-16 says the angle form of
   $\nu$ applies. The deep shadow tail, where the formula is being used outside its
   stated range, contributes a few percent. Under the street model at Brussels that
   share falls to 63 %, which is one more reason to treat that row as the weak one.

**Grid convergence.** The bound is a deterministic quadrature, so it has grid error
rather than variance. At the deepest Korenmarkt standpoint, the rooftop 15 GHz edge
term against cell count:

| grid | cells | $\chi_{\rm direct}$ recomputed | diffraction term |
|---|---|---|---|
| 360 x 300 | 108 000 | 0.006596 | 0.000689 |
| 720 x 600 | 432 000 | 0.006606 | 0.000650 |
| 1440 x 1200 | 1 728 000 | 0.006619 | 0.000734 |
| 2880 x 1200 | 3 456 000 | 0.006620 | 0.000737 |

The direct term converges monotonically and lands 0.6 % above the tracer's Monte
Carlo value. The diffraction term is not monotone and the production grid sits
13 % below the converged value, because the integrand varies on the scale
$\theta \sim \sqrt{\lambda/2d}$, about 1.3 degrees for a 20 m edge at 15 GHz, which
is close to the azimuth cell width. The last doubling moves it 0.4 %. Thirteen
percent on a 0.15 dB uplift is 0.02 dB, so the tabulated numbers are low by about
that much and it changes nothing.

### 2.7 A second, cruder bound from measured corners

The bound above is theory applied to this geometry. A sanity check from
measurement, using the only street scale absolute diffraction loss dataset I
could reach.

**Tenerelli, M.S. thesis, Virginia Tech, 1998**, three real McLean, Virginia
buildings at 28 GHz, transmitter to corner path at 45 degrees to the wall,
receiver on a constant radius arc, total path lengths 39 to 50 m. Table 7 fits
excess loss $E$ over the corner:

| diffraction angle $\theta_d$ | $E$ |
|---|---|
| 0 to 0.1 deg | 6.5 dB |
| 0.1 to 5 deg | $5\ln\theta_d + 18$ dB |
| 5 to 40 deg | $0.74\,\theta_d + 25$ dB, $R^2 = 0.98$ |

That is 32 dB at 10 degrees, 40 dB at 20 degrees and 55 dB at 40 degrees. The
conservative upper envelope of the same data is $0.749\theta_d + 25.35$ dB with
$R^2 = 0.99$. Concrete block loses about 3 dB more than brick, polarisation is
worth under 1.5 dB, and the thesis reports "no apparent dependence on path
length". Scaling to 15 GHz by the $\lambda$ law, $-10\log_{10}(28/15) = -2.7$ dB,
gives roughly 29 dB at 10 degrees and 52 dB at 40.

Set that against a single specular bounce. Concrete at 15 GHz with the study's own
ITU-R P.2040 parameters, $\varepsilon = 5.24 - j0.461$, reflects at $-8.1$ dB at
30 degrees incidence and $-3.6$ dB at 80 degrees, unpolarised. The gap between one
specular bounce and one corner diffraction at a useful angle is 25 to 50 dB, which
is the whole argument in one comparison.

Deng, MacCartney and Rappaport, GLOBECOM 2016,
doi 10.1109/GLOCOM.2016.7841898, measured the same corner at three frequencies and
fitted $P(\alpha) = n\alpha + 6.03$ dB, with the 6.03 dB being knife edge loss at
the shadow boundary. Their slopes $n$ in dB per degree:

| $f$ | stone pillar, rounded | marble corner, 90 deg |
|---|---|---|
| 10 GHz | 0.75 | 0.62 |
| 20 GHz | 0.88 | 0.77 |
| 26 GHz | 0.96 | 0.96 |

The slope rises with frequency, as the $\lambda$ law requires. Their absolute dB
values are not transferable, because their link was 3 m long with $d_1 = 2$ m and
$d_2 = 1$ m, and the transferable quantity is the slope. Interpolating to 15 GHz
would give about 0.70 dB per degree, which is close to Tenerelli's 0.74 at street
scale, but that interpolation is mine and not theirs.

---

## 3. Why an adjoint shoot and bounce estimator

### 3.1 The primitive is wrong, not the tool

The alternatives are good tools and this section does not claim otherwise. The
claim is structural: they compute a different object.

Sionna RT states its own primitive plainly. Technical report section 3: "A path
solver aims to determine a set of paths that connect two endpoints in a scene",
and "Paths are determined between two endpoints: a source and a target". The
documentation for `PathSolver` says it "computes propagation paths between the
antennas of all transmitters and receivers in a scene". The image method's
primitive is the same, one transmitter and one receiver, and DiffeRT's
min-path-tracing solves $\min \|I(X)\|^2 + \|F(X)\|^2$ for a path between a named
pair.

This study has no named transmitter. Section 4 of `PAPER_METHODS.md` replaces the
deployment with a density $Q(\hat u)$ on the sphere and the quantity of interest
is an integral over that density. Under a source continuum any particular
transmitter position has measure zero, so a path set enumerated to a specific
transmitter is a sample of measure zero from the object being integrated. To
recover $\chi$ from a path finding tracer you would have to place a grid of
sources, solve the pair problem once per source, and quadrature the results, which
is a Monte Carlo estimator with the sampling done in the worst possible place: on
the source, where the integrand $Q$ varies over four orders of magnitude and
concentrates within a few degrees of the horizon.

Sionna's own measurement of that cost is in the technical report, section 3.4:
"When $N_S$ samples are generated per source, the total number of samples produced
by the candidate generator becomes $N_S \cdot N_O$, where $N_O$ denotes the number
of sources", and figure 24c measures compute time on an RTX 4090 for a simple
street canyon rising from about 8 ms at one source to about 275 ms at $10^3$
sources. Their own experiment samples sources on a plane 70 m up, above the
buildings, which is a base station ensemble. Meanwhile section 4.6 notes that for
a radio map "the compute required ... remains constant regardless of the number of
measurement cells". Forward solving is free in receivers and linear in sources.
This study is the transpose of that.

The clean statement of the asymmetry is in room acoustics rather than radio.
Savioja and Svensson, JASA 138(2):708-730, 2015, doi 10.1121/1.4926438, section
IV-A: the image source construction "can be performed independently from the
listener position, and thus, the resulting image-source tree is valid for the
entire space. However, the second test ... requires information regarding the
location of the listener." The expensive reusable structure amortises over
*receivers*. One receiver and a continuum of sources amortises it in exactly the
wrong direction.

### 3.2 Complexity, cited rather than asserted

Kasdorf, Troksa, Key, Harmon and Notaroš, IEEE TAP 69(8):4808-4815, 2021,
doi 10.1109/TAP.2021.3060051, section I, states both halves:

> "the computational complexity of the IT method is $O(N^K)$ where $N$ is the
> number of planar facets in the model and $K$ is the number of reflections"

and

> "the computational complexity of SBR, $O(NK)$, where $N$ is the number of rays
> spawned and $K$ is the number of reflections, is substantially lower than that
> of IT."

A warning for anyone re-checking this: `pdftotext` flattens the superscript, so
the image theory exponent reads as $O(NK)$ in a text dump and looks identical to
the SBR line. It has to be read from the rendered page.

The same paper is where the accuracy defence comes from, and it matters that it
comes from an SBR paper willing to state SBR's disadvantage first. It notes that
"the ray paths are inexact, so further phase error is introduced in the SBR method
compared to the IT method", and then demonstrates an SBR implementation "of
similar accuracy as the image theory RT method" for large tunnels. This study
takes no phase at all, section 1.4 of `PAPER_METHODS.md`, so the phase error that
SBR concedes is not a cost it pays.

Eertmans, Oestges and Jacques, arXiv:2410.23773, section II, put the same
exponent in the radio setting: "let the size of the scene ... be $N$, and the
number of interactions be $K$, then the number of possible path candidates is at
most $N^K$", and "In city-scale 3D scenes, $N$ can easily exceed $10^6$ ... and
$N^K$ thus becomes too large either to fit in memory or to be simulated in a
reasonable time". The meshes here are 250 m crops with 700 000 triangles, which is
that regime.

Fuschini et al., Radio Science 50(6):469-485, 2015, doi 10.1002/2015RS005659,
section 2.2, is the direct comparison: "ray launching is more CPU-time efficient
than image-RT algorithms for prediction over vast areas or volumes". Their section
2.1 also confirms the transmitter-rooted structure of the image tree, built
"Starting from the root of the tree, corresponding to the transmitter".

### 3.3 Reciprocity, and what carries the adjoint

The physics is Lorentz reciprocity, and a readable citable statement is Chew,
*Lectures on Electromagnetic Field Theory*, Purdue 2024 edition, chapter 12,
equation (12.1.13) and the reaction theorem (12.1.16) to (12.1.18): "the fields
generated by sources 2 as 'measured' by sources 1 is equal to fields generated by
sources 1 as 'measured' by sources 2". Section 12.2 states the hypothesis,
symmetric permittivity and permeability tensors, lossy media allowed, gyrotropic
excluded, which a city scene of masonry and glass satisfies. Balanis, *Antenna
Theory*, 4th ed., section 3.8, equations (3-60) to (3-69), is the second source.

The estimator formalism is Veach's. *Robust Monte Carlo Methods for Light
Transport Simulation*, PhD thesis, Stanford, 1997, section 3.7.3: "the transport
rules can be applied equally well to the sensors, by treating the responsivity
$W_e$ as an emitted quantity ... This idea is the basis of adjoint methods", and
section 4.6 equation (4.26) gives the pair
$I = \langle W_e, GSL_e\rangle = \langle GSW_e, L_e\rangle$, "The only difference
... is that $W_e$ and $L_e$ have been exchanged."

Veach states the asymmetry as a *weakness* of adjoint methods: "while there is
only one equilibrium radiance function, there can be many different equilibrium
importance functions (one for each sensor)". This study is the mirror case, one
sensor and a continuum of sources, so the same asymmetry runs the other way and
becomes the justification. Christensen, "Adjoints and Importance in Rendering: An
Overview", IEEE TVCG 9(3):329-340, 2003, doi 10.1109/TVCG.2003.1207441, is the
survey.

The bridge that keeps this from being an unmotivated import from graphics is that
Sionna RT already made it. Technical report section 4.1: "We define radio maps as
path integrals, similar to how measurements are defined in computer graphics
[Kajiya 1986; Veach 1997, Section 3.7]". A mainstream radio propagation tool
already uses Veach's forward measurement equation. Taking the adjoint half of the
same formalism is an increment.

**What is not there, and should not be claimed.** There is no readable radio
propagation paper that traces only from the receiver on reciprocity grounds. The
closest is Taygur, Sukharevsky and Eibert, IEEE TAP 66(12):6654-6664, 2018,
doi 10.1109/TAP.2018.2876680, and it is bidirectional rather than receiver only,
and it is paywalled with no preprint, so nothing is quoted from it here. Sionna RT
never invokes reciprocity anywhere in its papers or technical report, and its
`reverse_direction` flag is documented only as swapping the labels on an
already-computed channel, which is not a physical claim and should not be cited as
one. The honest framing is that the adjoint formulation here is new to this
problem, not that it follows precedent.

### 3.4 What the alternatives do better, stated

- **They give phase and delay per path.** This study takes powers and never
  amplitudes by construction, section 1.4, so it cannot produce a coherent
  channel, fading statistics or a delay spread beyond the throughput weighted mean
  excess delay of equation (9).
- **They have a diffraction term.** Sionna RT supports first order wedge
  diffraction, DiffeRT's whole motivation is diffraction aware path finding, and
  the map based model of TR 38.901 clause 8.4 uses UTD. This estimator has none,
  and section 2 is the argument, not a denial.
- **They are validated against measurement in the open literature.** Xia et al.,
  IEEE TAP 72(10):7986-7996, 2024, doi 10.1109/TAP.2024.3451214, is the closest
  benchmark: Sionna RT at 2.8 GHz against a real urban campaign, with 200 000
  emitted rays, reaching 12.79, 10.17 and 11.07 dB RMSE at three transmitter
  positions with a buildings and ground scene, improving to 7.09, 6.15 and 5.95 dB
  once fences, poles and vegetation are added. This study's section 8 checks
  against closed forms it was built to satisfy and has no independent solver in the
  loop, which is a real gap and is already recorded in `PAPER_METHODS.md` section
  11. Note in passing that Xia et al. report setting "both the maximum number of
  reflections and diffractions ... to 6", which cannot be right for Sionna, since
  it supports only first order diffraction, so it is almost certainly `max_depth=6`
  with diffraction enabled.
- **There is a direct per-pair predecessor in exactly this application.** Leeman,
  Wydaeghe, van der Straeten, Goegebeur, Vermeeren and Joseph, IEEE Access
  13:30894-30906, 2025, doi 10.1109/ACCESS.2025.3541352, does city scale 5G
  downlink exposure by ray tracing in a real urban environment with MATLAB SBR,
  five reflections, one diffraction, 0.25 degree angular separation and a 40 dB
  relative path loss cut, on real base station positions from Belgian conformity
  certificates, with "RT ... performed between these potential serving antennas and
  their corresponding users". That is the per-pair, discrete-deployment baseline
  the continuum formulation here replaces. Citing it makes the contrast concrete
  and stops the comparison being a straw man.

---

## 4. Why polarisation is an unpolarised power average

### 4.1 What is done

Section 5.2 step 3 attenuates by
$R = \tfrac12(|\Gamma_{\rm TE}|^2 + |\Gamma_{\rm TM}|^2)$ and carries no
transverse state, so the coherency matrix is taken isotropic in the transverse
plane throughout.

### 4.2 The usual defence does not survive the measurements

`PAPER_METHODS.md` section 5.4 currently says the approximation "is exact for the
depolarised multi bounce tail". The measurement literature does not support that
at this frequency.

Karttunen, Järveläinen, Nguyen and Haneda, "Modeling the Multipath
Cross-Polarization Ratio for 5-80-GHz Radio Links", IEEE Trans. Wireless Commun.
18(10):4768-4778, 2019, doi 10.1109/TWC.2019.2928810, pooled 28 campaigns and
30 862 multipath components, including an open square at 14.25 GHz. From their
abstract, verbatim:

> "A conventional XPR model of an MPC assuming a constant mean value fits our
> measurements very poorly and moreover overestimates the depolarization effect.
> Our measurements revealed a clear trend that the MPC XPR is inversely
> proportional to an excess loss in reference to the free-space path loss. ... The
> measurements furthermore showed that the MPC XPR is not strongly frequency or
> environment dependent. In our MPC XPR model, an MPC with zero-dB excess loss has
> a mean XPR of 28 dB. The mean XPR decreases half-a-dB as the excess loss
> increases by every dB and the standard deviation around the mean is 6 dB."

Take that model at face value. Reaching XPR = 0 dB, which is what "depolarised"
means, requires 56 dB of excess loss over free space, and reaching XPR = 6 dB
requires 44 dB. A path 44 dB down contributes essentially nothing to $\chi$. So
the multi bounce tail that actually carries power is *not* depolarised at this
frequency, and the sentence in section 5.4 should be retracted.

Per site fits exist in that paper's table for the 14.25 GHz open square
specifically. I did not use them, because the table's column alignment does not
survive text extraction and I did not want to attribute a number to the wrong
column. The pooled model above is quoted from the abstract, which is unambiguous.

Corroborating, from `lit/`: 3GPP TR 38.901 table 7.5-6 part 1 gives UMi street
canyon $\mu_{\rm XPR} = 9$ dB LOS, 8.0 dB NLOS and 9 dB O2I, with
$\sigma_{\rm XPR} = 3, 3, 5$ dB, so the modelled cross polar power fraction
$\kappa^{-1}$ is 13 to 16 % per ray, not 50 %. Samimi and Rappaport, EuCAP 2016,
doi 10.1109/EuCAP.2016.7481410, abstract: "Small-scale spatial measurements at
28 GHz reveal a mean cross-polar ratio for individual multipath components of 29.7
dB and 16.7 dB in line of sight and NLOS, respectively." So NLOS depolarises
relative to LOS by about 13 dB and still does not come close to zero.

Also worth noting: TR 38.901 clause 8, the map based hybrid model, expects a per
path XPR **from the tracer**. An unpolarised power average cannot supply one, so
this estimator cannot feed that model.

### 4.3 What it actually costs, computed for this study's materials

The error is one sided and bounded on one side only. Using the study's own
ITU-R P.2040 parameters at 15 GHz, concrete $\varepsilon = 5.24 - j0.461$ and
brick $\varepsilon = 3.91 - j0.044$, the unpolarised mean against a fully
polarised incident field:

| incidence | concrete TE | concrete TM | mean minus TM | mean minus TE |
|---|---|---|---|---|
| 30 deg | $-7.08$ dB | $-9.33$ dB | $+1.27$ dB | $-0.98$ dB |
| 50 deg | $-5.32$ dB | $-13.12$ dB | $+5.46$ dB | $-2.34$ dB |
| 60 deg | $-4.16$ dB | $-19.34$ dB | $+12.30$ dB | $-2.88$ dB |
| 66.4 deg | $-3.34$ dB | $-35.00$ dB | $+28.65$ dB | $-3.01$ dB |
| 80 deg | $-1.46$ dB | $-8.21$ dB | $+4.58$ dB | $-2.18$ dB |

The pseudo-Brewster minimum is at 66.43 degrees for concrete, where
$|\Gamma_{\rm TM}|^2 = -35.0$ dB, and at 63.17 degrees for brick, where it is
$-53.6$ dB. ITU-R P.2040-3 section 2.2.2.3 names it: "the minimum in reflection
coefficient visible in Fig. 2 for TM polarization, known as the pseudo-Brewster
angle", a deep dip and not a zero.
Against a purely TE field the mean is never wrong by more than 3.01 dB. Against a
purely TM field it can be wrong by 29 dB on a single bounce, and it errs upward,
which is the direction that matters for an exposure study.

**Whether that 29 dB can actually be reached in this geometry is a separate
question, and mostly it cannot.** For a vertical facade and a near horizontal ray,
the plane of incidence is nearly horizontal, so a vertically polarised network
field is perpendicular to it and the interaction is TE. Vertical facades therefore
sit on the bounded side, where the mean understates by at most 3.01 dB. The
pseudo-Brewster dip engages on the *ground*, where a ray from elevation $\alpha$
strikes at incidence $90^\circ - \alpha$, putting the concrete minimum at
$\alpha = 23.6$ degrees. Integrating the corrected illumination law over the
$\pm 5$ degree band around that elevation, the exposed share of the measure is
**7.84 % under the macro rooftop model and 0.40 % under the street small cell
model** (`semantic_twin.propagation.directions.elevation_band_measure`). The
network is also not necessarily vertically polarised, and if it is not then both
components are present and the average is closer to right.

The honest summary is therefore: **on a single specular bounce off a vertical
facade the unpolarised average is within 3 dB and biased low, on the ground
bounce it can be biased high at a few percent of the illumination measure, and the
"multi-bounce tail is depolarised" argument is not available.** That belongs in
the threats to validity with these numbers, not in the method as a justification.

For completeness on the mechanism split: Melloni, Chuang, Berweger, Vitucci,
Degli-Esposti, Gentile and Golmie, "Super-resolution experimental validation and
polarimetric extension of the effective roughness diffuse scattering models",
arXiv:2605.31267 (2026), a polarimetric 28 GHz study of ten building materials,
summarise the prior literature as: "it was shown that DS has a prevalent role in
the generation of field depolarization, compared to coherent propagation
mechanisms (specular reflection, diffraction) that generally preserve the original
polarization, except in very particular cases". That is their summary of others'
work rather than their own result, so it is a pointer, not a measurement. The
depolarisation this estimator implicitly
assumes is produced by the diffuse channel, which the roughness model of section
5.2 step 4 does carry, and not by the specular one, which it does not.

---

## 5. Why the bounce loop stops where it does

`PAPER_METHODS.md` section 8.3 already measures this internally: $\chi_{\rm iso}$
is 0.35134 at $L=4$ against 0.35137 at $L\ge 6$, a 0.0004 dB difference, and the
truncated throughput share falls from 0.2515 at $L=1$ to $6.3\times10^{-4}$ at
$L=4$ and $1.4\times10^{-5}$ at $L=6$. That is a convergence measurement and it is
the primary justification. The literature adds two things it does not have.

**A lower bound that is not arbitrary.** mmMAGIC D2.2 section 2.2.3, quoted in
full in section 2.2 above, matched the strongest NLOS arrival in a street canyon
to "a ray-traced path using four specular reflections off exterior building
walls", 20 dB above the rest of the power delay profile. A tracer that stopped at
two or three bounces would have missed the dominant NLOS arrival in that
measurement. Four is where the measured evidence says the important paths live.

**Where everyone else stops.** The 5GCM white paper's UMa study used a maximum of
four reflections. Leeman et al. 2025, the closest published analogue in exposure
specifically, used five. Sionna RT's `PathSolver` defaults to `max_depth=3`.
mmMAGIC's own ray tracing calibration used first and second order specular
reflections only. Four is at the upper end of common practice, not below it.

The provenance caveat recorded in `PAPER_METHODS.md` section 11 stands: the
operating point in this study is not uniform, $L=4$ for the corrected eleven
cities and $L=6$ elsewhere, and at 0.0004 dB the difference does not matter but the
prose should not claim a single value.

---

## 6. Drop in replacement prose for PAPER_METHODS.md

These are written to be pasted. I do not own that file, so nothing here has been
applied to it.

### 6.1 Replaces section 10, threat 1

> 1. **Diffraction is absent.** Deliberately. The uniform theory of diffraction
>    gives a diffracted field proportional to $1/\sqrt{k}$, so diffracted power
>    falls as $\lambda$, which is 10 dB per decade of frequency against a
>    frequency flat reflected path, and 8.75 dB from 2 to 15 GHz in the deep shadow
>    limit of Recommendation ITU-R P.526-16 equation (31). That is the theory. The
>    measurement is Ericsson's three band street microcell campaign at 2.44, 14.8
>    and 58.68 GHz with matched dipoles and equalised bandwidth, in which the NLOS
>    excess loss grows at 3.0 to 3.5 dB per decade against the 10 dB per decade the
>    corner diffraction model predicts, and in which, at 60 GHz, no signal above
>    the noise floor was observed at the corner diffraction delay while the
>    strongest arrival matched a four bounce specular path 20 dB above the rest of
>    the profile. Published models follow: ITU-R P.1411-13 carries an explicit
>    reflection plus diffraction power sum from 800 to 2000 MHz and no diffraction
>    term at all from 2 to 38 GHz, the 5GCM white paper halved the diffraction
>    order above 10 GHz, and Sionna RT ships with diffraction off by default on the
>    stated grounds that it "typically carries much less energy compared to
>    reflection and refraction".
>
>    Bounded for this geometry rather than in general. Applying the P.526-16 knife
>    edge loss to every geometrically shadowed direction at the sixty most enclosed
>    standpoints of the three most enclosed squares, with a single edge, a distant
>    source, no re-blocking and the standpoint's own multipath gain applied to the
>    diffracted term, all of which err upward, a diffraction term could add a median
>    0.15 dB and at most 1.20 dB to the rooftop susceptibility, and a median 0.06 dB
>    and at most 0.19 dB to the isotropic one. Between 93 and 98 % of that bound
>    comes from directions less than 12 degrees into shadow, which is where the
>    recommendation says its angle form applies. Against a within square spread of
>    8.1 dB and an across square spread of 30 dB, the omission does not reach any
>    conclusion in this paper. The same calculation with $\lambda$ at 2 GHz raises
>    the bound by a factor of 3.1 to 5.0, which is 4.9 to 7.0 dB, so the frequency
>    argument is measured on this geometry rather than borrowed.
>
>    Under the street small cell model the bound is not small and the concession is
>    made rather than argued away: a median of 0.44 dB, a 90th percentile of
>    1.84 dB and 12.6 dB at one Brussels standpoint. That model draws 87.9 % of its
>    illumination from below 5 degrees of elevation, and at four of the sixty
>    standpoints its entire elevation support is occluded, so every watt in the
>    traced answer arrives by reflection and a diffraction term has nothing to
>    compete with. Those standpoints also carry the smallest absolute
>    susceptibilities in the study, of order $10^{-5}$.
>
>    The omission has one failure geometry that is inside scope and is not covered
>    by the above. When the source is above the skyline and the standpoint sees no
>    illuminated facade, over rooftop diffraction is the mechanism: Adhikari et al.
>    fit 22 Manhattan routes and find over-top NLOS beats street clutter NLOS by
>    7 dB in RMSE for an urban macrocell with the base station 20 m above the
>    surrounding buildings. The macro rooftop illumination model of section 4.3
>    places sources in exactly that regime, so the deep side street standpoints
>    under the rooftop law are where this estimator is at its worst.

### 6.2 Replaces section 5.4

> ### 5.4 The one simplification, stated
>
> Polarisation is carried as the unpolarised power average (7) rather than a
> $2\times 2$ Jones matrix, so the coherency matrix is taken isotropic in the
> transverse plane. It is exact for the closed form checks of section 8, where
> both polarisations are averaged anyway, and it loses the cross polarisation
> ratio, which nothing downstream in this study consumes.
>
> It is not, however, exact for the multi bounce tail, and an earlier draft claimed
> that it was. Karttunen et al. pooled 28 campaigns and 30 862 multipath
> components from 5 to 80 GHz and found the multipath cross polarisation ratio
> falls half a dB per dB of excess loss from 28 dB at zero excess loss, so a
> genuinely depolarised path needs about 56 dB of excess loss and carries no
> useful power. The measured tail is not depolarised at this frequency.
>
> What the approximation costs is therefore a Fresnel error on the paths that do
> carry power, and it is one sided. Against a purely TE field the unpolarised mean
> is never wrong by more than 3.01 dB and is biased low. Against a purely TM field
> it is biased high, by up to 28.6 dB for concrete at the 66.4 degree
> pseudo-Brewster angle. Geometry limits the exposure: for a vertical facade and a
> near horizontal ray the plane of incidence is nearly horizontal, so a vertically
> polarised field interacts as TE and sits on the bounded side, and the
> pseudo-Brewster dip engages only on the ground bounce, at $23.6$ degrees of
> arrival elevation, which carries 7.8 % of the macro rooftop illumination measure
> and 0.4 % of the street one.

### 6.3 New subsection for section 5.1, on the choice of estimator

> **Why adjoint, and why not a path finding tracer.** A deterministic tracer such
> as Sionna RT or DiffeRT computes paths between two named endpoints. Sionna's own
> technical report puts it that way: "Paths are determined between two endpoints: a
> source and a target." This study has no named source. Section 4 replaces the
> deployment with a density $Q(\hat u)$ on the sphere, and under that continuum any
> single transmitter position has measure zero, so an enumerated path set to a
> specific transmitter is a measure zero sample of the object being integrated.
> Recovering $\chi$ from a pair solver means gridding the source, solving once per
> grid point, and quadraturing, which puts the sampling where the integrand is
> worst behaved: $Q$ varies over four orders of magnitude and concentrates within a
> few degrees of the horizon. Sionna measures the cost of that directly, its
> candidate count being $N_S \cdot N_O$ in the number of sources $N_O$ while a
> radio map's cost is flat in the number of measurement cells. The problem here is
> the transpose.
>
> Reciprocity makes the transpose available. Lorentz reciprocity permits the trace
> to run from the standpoint outward and be read as a source side quantity, and the
> estimator that results is the adjoint of the forward measurement equation in
> Veach's sense, with the standpoint's response function propagated in place of the
> emitted field. Sionna RT already imports the forward half of that formalism,
> defining radio maps as path integrals "similar to how measurements are defined in
> computer graphics". This is the other half.
>
> Cost follows the same asymmetry. The image method is $O(N^K)$ in facets and
> reflection order while shooting and bouncing is $O(NK)$ in rays and order, and at
> a 250 m crop with 700 000 triangles the exponential form is not available.
> Shooting and bouncing pays for that with inexact path geometry and therefore
> phase error, which is a real cost for a coherent channel model and not one this
> study pays, since section 1.4 takes powers and never amplitudes.

---

## 7. References

Ordered as first cited. Files named where a copy is in `lit/`.

**Diffraction, theory and recommendations**

- Kouyoumjian, R. G. and Pathak, P. H., "A uniform geometrical theory of
  diffraction for an edge in a perfectly conducting surface", *Proc. IEEE*
  62(11):1448-1461, 1974. doi 10.1109/PROC.1974.9651. **Not read, see section 8.**
- Recommendation ITU-R P.526-16, "Propagation by diffraction", 11/2025.
  `lit/ITU-R_P.526-16_2025-11_propagation_by_diffraction.pdf`. Equations
  (26)-(31), section 4.1.
- Recommendation ITU-R P.1411-13, "Propagation data and prediction methods for the
  planning of short-range outdoor radiocommunication systems ... 300 MHz to
  300 GHz", 09/2025. `lit/ITU-R_P.1411-13_2025-09_short_range_outdoor.pdf`.
  Sections 4.1.3.1, 4.1.3.2, 4.3.2.2.
- Recommendation ITU-R P.2040-3, "Effects of building materials and structures on
  radiowave propagation above about 100 MHz". `lit/ITU-R_P.2040-3.pdf`. Section
  2.2.2.3, section 3 table 3.

**Diffraction, measurement**

- Ericsson, "Street Microcell Channel Measurements at 2.44, 14.8 and 58.68 GHz",
  3GPP TSG-RAN WG1 #84, R1-160846, St Julian's, Malta, 15-19 February 2016. No
  DOI. `lit/3GPP_R1-160846_Ericsson_street_microcell_2.44_14.8_58.68GHz.pdf`.
- mmMAGIC, "Measurement results and final mmMAGIC channel models", deliverable
  D2.2, H2020-ICT-671650-mmMAGIC, v1, 12 May 2017. Sections 2.2.2, 2.2.3.
  `lit/mmMAGIC_D2.2_measurement_results_final_channel_models.pdf`. **The project
  site is dead, this is a Wayback copy, and the URL will not resolve for a reader.
  Archive the local file.**
- METIS, "METIS channel models", deliverable D1.4, ICT-317669-METIS, v2,
  30 April 2015. Sections 5.9, A.4, figure E-6.
  `lit/metis_D1.4_v2_channel_models.pdf`. **Also Wayback only.**
- Deng, S., MacCartney, G. R. Jr. and Rappaport, T. S., "Indoor and outdoor 5G
  diffraction measurements and models at 10, 20, and 26 GHz", *IEEE GLOBECOM*,
  2016. doi 10.1109/GLOCOM.2016.7841898.
  `lit/deng_maccartney_rappaport_globecom2016_diffraction_10_20_26GHz.pdf`.
  Table II.
- Tenerelli, P. A., "Measurement of 28 GHz diffraction loss by building corners",
  M.S. thesis, Virginia Polytechnic Institute and State University, 1998.
  `lit/tenerelli1998_thesis_diffraction_building_corners_28GHz.pdf`. Table 7,
  equations (35), (36). Archival conference version: Tenerelli and Bostian,
  *IEEE PIMRC*, vol. 3, pp. 1166-1169, 1998, doi 10.1109/PIMRC.1998.731362,
  abstract only.
- Tervo, N. et al., "Diffraction measurements around a building corner at 10 GHz",
  *1st Int. Conf. 5G for Ubiquitous Connectivity*, 2014.
  doi 10.4108/ICST.5GU.2014.258145.
  `lit/tervo2014_diffraction_building_corner_10GHz_5GU.pdf`.
- Charbonnier, R. et al., "Calibration of ray-tracing with diffuse scattering
  against 28-GHz directional urban channel measurements", *IEEE Trans. Veh.
  Technol.*, 2020. doi 10.1109/TVT.2020.3038620.
  `lit/nist_calibration_RT_diffuse_scattering_28GHz_urban.pdf`. Section VI,
  footnote 6.
- Adhikari, D. et al., around-corner and over-top NLOS propagation at 28 GHz in
  Manhattan, *IEEE INFOCOM*, 2025. doi 10.1109/INFOCOM55648.2025.11044468.
  `lit/adhikari2025_around_corner_over_top_28GHz_manhattan_INFOCOM.pdf`. Tables
  III and V.
- Du, J., Chizhik, D., Valenzuela, R. A. et al., "Directional measurements and
  models in street canyons at 28 GHz", *IEEE Trans. Antennas Propag.*
  69(6):3459-3469, 2021. doi 10.1109/TAP.2020.3044398.
  `lit/chizhik2021_directional_street_canyons_28GHz_90pct.pdf`. Table 2.
- Lopes, W. et al., coverage prediction at 60 GHz in an urban environment,
  *Scientific Reports* 16:17345, 2026. doi 10.1038/s41598-026-41462-x.
  `lit/scirep2026_coverage_prediction_60GHz_urban.pdf`.
- Rappaport, T. S. et al., "Overview of millimeter wave communications for
  fifth-generation (5G) wireless networks, with a focus on propagation models",
  *IEEE Trans. Antennas Propag.* 65(12):6213-6230, 2017.
  doi 10.1109/TAP.2017.2734243.
  `lit/rappaport_tap2017_mmwave_propagation_overview_arxiv1708.02557.pdf`.
  Secondary source. It cites Deng for the 10/20/26 GHz data.

**Channel models and tracers**

- 3GPP TR 38.901, "Study on channel model for frequencies from 0.5 to 100 GHz",
  read as ETSI TR 138 901 V19.4.0 (2026-07) and V18.0.0.
  `lit/3GPP_TR38.901_v19.4.0_ETSI_TR138901.pdf`. Clauses 7.5, 7.6.4.2, 8.4,
  table 7.5-6, table 8.4-1.
- Aalto University, AT&T, BUPT, CMCC, Ericsson et al., "5G channel model for bands
  up to 100 GHz", white paper, 6 December 2015. Section 7.2.
  `lit/5gcm_5G_channel_model_up_to_100GHz_2015.pdf`.
- Maltsev, A. et al., "Channel models for 60 GHz WLAN systems", IEEE
  802.11-09/0334r8, May 2010.
  `lit/IEEE_802.11-09-0334r8_Maltsev_60GHz_WLAN_channel_models.doc`.
- Hoydis, J., Aït Aoudia, F., Cammerer, S., Nimier-David, M., Binder, N., Marcus,
  G. and Keller, A., "Sionna RT: Differentiable ray tracing for radio propagation
  modeling", *IEEE Globecom Workshops*, pp. 317-321, 2023.
  doi 10.1109/GCWkshps58843.2023.10465179.
  `lit/sionna_rt_hoydis_globecom2023_arxiv_2303.11103.pdf`. **Note: commonly
  miscited as ICC.**
- Aït Aoudia, F. et al., "Sionna RT: Technical report", arXiv:2504.21719 v1.2,
  24 November 2025. `lit/sionna_rt_technical_report_arxiv2504.21719.pdf`. Sections
  3, 3.1, 3.1.2, 3.4, 4.1, 4.6, annex A.8.
- Kanhere, O., Poddar, H. and Rappaport, T. S., "Calibration of NYURay for ray
  tracing using 28, 73, and 142 GHz channel measurements", *IEEE Trans. Antennas
  Propag.*, 2024. arXiv:2410.03104. Section II.
- Eertmans, J., Oestges, C. and Jacques, L., "Min-path-tracing: a diffraction
  aware alternative to image method in ray tracing", *17th EuCAP*, 2023.
  doi 10.23919/EuCAP57121.2023.10132934. arXiv:2301.06399.
  `lit/eertmans2023_min_path_tracing_eucap_arxiv2301.06399.pdf`.
- Eertmans, J., Oestges, C. and Jacques, L., *IEEE ICMLCN*, 2025.
  arXiv:2410.23773, section II. `lit/arxiv_2410.23773.pdf`.
- Eertmans, J., Oestges, C. and Jacques, L., "Demonstrating DiffeRT: an
  open-source library for optimizing radio networks with differentiable ray
  tracing", *IEEE ICMLCN*, pp. 1-2, 2025. doi 10.1109/ICMLCN64995.2025.11139997.
  Software doi 10.5281/zenodo.11386432. **Paywalled, abstract only.** DiffeRT2d,
  a separate and explicitly non-EM-accurate 2d library, is the one with a JOSS
  paper: *JOSS* 9(98):6915, 2024, doi 10.21105/joss.06915. Do not let a reference
  manager merge the two. The repository's own `CITATION.cff` has a field that
  invites exactly that mistake.
- Xia, W. et al., "Path loss prediction in urban environments with Sionna-RT based
  on accurate propagation scene models at 2.8 GHz", *IEEE Trans. Antennas Propag.*
  72(10):7986-7996, 2024. doi 10.1109/TAP.2024.3451214.
  `lit/Path_Loss_Prediction_in_Urban_Environments_With_Sionna-RT_Based_on_Accurate_Propagation_Scene_Models_at_2.8_GHz.pdf`.
  Section IV-B, table VI.
- Leeman, S., Wydaeghe, R., van der Straeten, S., Goegebeur, Y., Vermeeren, G. and
  Joseph, W., "City-scale spatio-temporal modeling of 5G downlink exposure of
  users and non-users by ray-tracing in a real urban environment", *IEEE Access*
  13:30894-30906, 2025. doi 10.1109/ACCESS.2025.3541352.
  `lit/Leeman_2025_IEEE_Access_city-scale_5G_downlink_exposure_ray_tracing.pdf`.
  Table 1, section II-C.

**Complexity, reciprocity, adjoints**

- Ling, H., Chou, R.-C. and Lee, S.-W., "Shooting and bouncing rays: calculating
  the RCS of an arbitrarily shaped cavity", *IEEE Trans. Antennas Propag.*
  37(2):194-205, 1989. doi **10.1109/8.18706**. **Not read, see section 8. The DOI
  10.1109/8.29370 that circulates for this paper is wrong and resolves to an
  unrelated paper on ELF signals from the polar electrojet.**
- Kasdorf, S., Troksa, B., Key, C., Harmon, J. and Notaroš, B. M., "Advancing
  accuracy of shooting and bouncing rays method for ray-tracing propagation
  modeling based on novel approaches to ray cone angle calculation", *IEEE Trans.
  Antennas Propag.* 69(8):4808-4815, 2021. doi 10.1109/TAP.2021.3060051.
  `lit/notaros_sbr_accuracy_TAP.pdf`. Section I.
- Savioja, L. and Svensson, U. P., "Overview of geometrical room acoustic modeling
  techniques", *J. Acoust. Soc. Am.* 138(2):708-730, 2015. doi 10.1121/1.4926438.
  `lit/savioja_svensson_2015_geometrical_room_acoustics_JASA.pdf`. Section IV-A.
- Fuschini, F. et al., "Ray tracing propagation modeling for future small-cell and
  indoor applications: a review of current techniques", *Radio Science*
  50(6):469-485, 2015. doi 10.1002/2015RS005659.
  `lit/fuschini_2015_raytracing_review_RadioScience.pdf`. Sections 2.1, 2.2.
- Sood, N., "Ray tracing propagation modelling", MASc thesis, University of
  Toronto, 2012. `lit/sood_2012_raytracing_thesis_utoronto.pdf`. Measured
  exponents, sections 1.3.1-1.3.2 and p. 83.
- Chew, W. C., *Lectures on Electromagnetic Field Theory*, Purdue University, 2024
  edition. `lit/chew_lectures_em_field_theory_2024.pdf`. Chapter 12, equations
  (12.1.13), (12.1.16)-(12.1.18), section 12.2.
- Veach, E., *Robust Monte Carlo Methods for Light Transport Simulation*, PhD
  thesis, Stanford University, 1997. `lit/veach_1997_thesis.pdf`. Sections 3.7.1,
  3.7.3, 4.6.
- Christensen, P. H., "Adjoints and importance in rendering: an overview", *IEEE
  Trans. Vis. Comput. Graph.* 9(3):329-340, 2003. doi **10.1109/TVCG.2003.1207441**.
  `lit/christensen2003_adjoints_importance_rendering_TVCG.pdf`. **The DOI
  10.1109/TVCG.2003.1207443 that circulates for this paper is wrong.**
- Taygur, M. M., Sukharevsky, I. O. and Eibert, T. F., "A bidirectional ray-tracing
  method for antenna coupling evaluation based on the reciprocity theorem", *IEEE
  Trans. Antennas Propag.* 66(12):6654-6664, 2018. doi 10.1109/TAP.2018.2876680.
  **Paywalled, abstract only, nothing quoted.**

**Polarisation**

- Karttunen, A., Järveläinen, J., Nguyen, S. L. H. and Haneda, K., "Modeling the
  multipath cross-polarization ratio for 5-80-GHz radio links", *IEEE Trans.
  Wireless Commun.* 18(10):4768-4778, 2019. doi 10.1109/TWC.2019.2928810.
  arXiv:1804.00847.
  `lit/karttunen2019_multipath_XPR_5-80GHz_arxiv1804.00847.pdf`.
- Samimi, M. K. and Rappaport, T. S., "Local multipath model parameters for
  generating 5G millimeter-wave 3GPP-like channel impulse response", *10th EuCAP*,
  2016. doi 10.1109/EuCAP.2016.7481410.
  `lit/samimi_rappaport_eucap2016_local_multipath_params_XPR_arxiv1511.06941.pdf`.
  Table VI.
- Melloni, S., Chuang, C., Berweger, S., Vitucci, E. M., Degli-Esposti, V.,
  Gentile, C. and Golmie, N., polarimetric characterisation of scattering from
  building materials at 28 GHz, arXiv:2605.31267, 2026.
  `lit/vitucci_polarimetric_ER_scattering_arxiv2605.31267.pdf`.

---

## 8. What could not be reached, and what is still weak

**Paywalled, not read, nothing quoted from them.** Reported rather than worked
around. A UGent IEEE Xplore and Wiley session would close most of these.

| source | why it matters |
|---|---|
| Kouyoumjian and Pathak, *Proc. IEEE* 1974, doi 10.1109/PROC.1974.9651 | The $\sqrt{\lambda}$ prefactor is the root of the whole frequency argument and is currently cited through reproductions in the Sionna RT technical report and METIS D1.4, not from the original |
| Ling, Chou and Lee, *IEEE TAP* 1989, doi 10.1109/8.18706 | The canonical SBR reference. Closed, no repository copy. The NASA NTRS abstract confirms the method structure but contains no complexity statement, so no complexity claim is attributed to it |
| Jacob et al., *IEEE TMTT* 60(3):833-844, 2012, doi 10.1109/TMTT.2011.2178859 | The most cited "diffraction can be neglected" statement for mm and sub-mm indoor channels. Closed everywhere. Deng et al. paraphrase it but the sentence is cut at a column break in the extraction, so it is not quoted here |
| Kim et al., *ETRI Journal* 42(6):827-836, 2020, doi 10.4218/etrij.2019-0411 | Nominally gold open access but Wiley returns 403. The abstract claims knife edge *underestimates* loss at large $\nu$, which bears directly on the over-rooftop counter case of section 2.5. **This is the single most valuable one to pull manually.** |
| MMWaTT 2009, doi 10.1109/MMWATT.2009.5450459 | The one true diffraction on/off ablation study found. Blocked. Biggest remaining gap in the argument |
| Taygur, Sukharevsky and Eibert, *IEEE TAP* 2018, doi 10.1109/TAP.2018.2876680 | The only on-point reciprocity based tracer paper. Closed, no preprint |
| Degli-Esposti et al., *IEEE TAP* 59(11):4247-4256, 2011, doi 10.1109/TAP.2011.2164226 | Sionna's own scattering reference. Superseded for our purposes by arXiv:2605.31267 |
| Harrington 1961 section 3-8, Rumsey 1954 doi 10.1103/PhysRev.94.1483 | Alternative reciprocity citations. Chew and Balanis cover the same ground and are readable, so this is not a gap |
| Murdock et al., *IEEE WCNC* 2012, doi 10.1109/WCNC.2012.6214335 | The source METIS cites for "diffraction is not significant in urban outdoor" |

**Weak points in the argument as it stands.**

1. **TR 38.901 contains no sentence tying diffraction relevance to frequency.**
   Section 2.3's use of it is structural, an observation about what the document
   carries where, and it should be presented that way rather than as a quotation.
2. **The Ericsson tdoc is not peer reviewed.** It is a 3GPP contribution. The
   peer-reviewable form of the same campaign is mmMAGIC D2.2 section 2.2.3, which
   is a project deliverable rather than a journal paper. Both should be cited
   together, and neither is a journal article. This is the weakest link in an
   otherwise strong chain, and it cannot be fixed without the underlying D2.1.
3. **mmMAGIC D2.2 and METIS D1.4 are Wayback-only.** `5g-mmmagic.eu` is parked and
   `metis2020.com` is squatted. The local copies in `lit/` are the archive.
4. **The 15 GHz corner loss numbers in section 2.7 are scaled, not measured.**
   Tenerelli measured at 28 GHz. The $-2.7$ dB scaling to 15 GHz uses the same
   $\lambda$ law the section is trying to support, so that particular number is
   internally circular and should be presented as an illustration rather than
   evidence. The Deng slopes at 10, 20 and 26 GHz bracket 15 GHz and are the
   non-circular version.
5. **The bound of section 2.6 is a knife edge bound, not a UTD bound.** A finite
   conducting wedge with the study's own permittivities would be the better
   calculation and is a day of work, not an hour. Knife edge is the conventional
   conservative screen and Tenerelli's measurements come out above it at large
   angles, which is the direction that keeps it a bound, but it is an
   approximation and not a proof.
6. **No error bars.** The bound is computed on a deterministic direction grid, so
   it has quadrature error rather than Monte Carlo error, and the grid convergence
   ladder at the end of section 2.6 stands in for a variance. It shows the
   production grid running about 13 % below the converged value, worth 0.02 dB on
   the reported uplift, and the run it is compared against, the production tracer,
   has no error bar of its own either.
7. **The larger nearby exposure is diffuse scattering, not diffraction.** Vitucci
   et al., *Radio Science* 54(11):1112-1128, 2019, doi 10.1029/2019RS006869, ablate
   diffuse scattering at 28 and 38 GHz and find RMSE moving from 6.2 to 13.2 dB
   with it to 25.2 to 37.0 dB without, tables 2 and 3, concluding that "properly
   modeling diffuse scattering from building walls appears to be decisive" and
   more so than they expected. That is a bigger number than anything in section 2,
   and it lands on
   the roughness and clutter model rather than on this document. Flagged here
   because a reviewer reading section 10 will make the connection.
