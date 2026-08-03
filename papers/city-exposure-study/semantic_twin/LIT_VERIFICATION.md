# Literature verification: SBR against image source, and polarisation

This document re-checks the sources behind sections 3 and 4 of `WHY_NOT.md`
against the PDFs in `lit/`, and records what survived, what did not, and what I
could add that was previously left open.

I do not own `WHY_NOT.md` and have not edited it. Section 2 below lists one
correction and several additions that belong in it, stated as claims against the
current text rather than applied to it.

`WHY_NOT.md` was being edited by someone else while this was written, and it grew
by about 120 lines in the interval. Everything below is quoted against its state
on 2026-08-03 and refers to it by section rather than line. Both items in section
2.1 and 2.2 were re-checked against the later version and still applied. Anything
that has since moved should be matched on the quoted text.

Method, so the checks are reproducible. Quotes were matched against the PDF text
layer where the layer is reliable, and read off the rendered page as an image
where it is not. Every table value below was read from a rendered page, not from
`pdftotext`, because both tables involved defeat column extraction. DOIs were
resolved against the Crossref REST API rather than trusted from a citation.

---

## 1. What was checked and holds

Nothing in this section needs action. It is recorded so the next person does not
re-do it.

**Section 3, the estimator argument.**

| claim in `WHY_NOT.md` | source | verdict |
|---|---|---|
| "A path solver aims to determine a set of paths that connect two endpoints in a scene" | Sionna RT tech report, section 3, p. 11 | verbatim |
| "Paths are determined between two endpoints: a source and a target" | same, p. 8 | verbatim |
| `PathSolver` "computes propagation paths between the antennas of all transmitters and receivers" | Sionna 2.0.1 docs, Path Solvers page | verbatim |
| $N_S \cdot N_O$ sample count in the number of sources | tech report section 3.4, p. 29 | verbatim |
| Figure 24c, about 8 ms at one source to about 275 ms at $10^3$ | tech report p. 30, RTX 4090 | read off the plot, and the caption confirms the axes. The 70 m source plane is stated in the section 3.4 text, not only the caption |
| radio map compute "remains constant regardless of the number of measurement cells" | tech report section 4.6, p. 37 | verbatim |
| image source tree "valid for the entire space", visibility test "requires information regarding the location of the listener" | Savioja and Svensson section IV-A, p. 716 | verbatim |
| $O(N^K)$ for image theory and $O(NK)$ for SBR | Kasdorf et al. section I | verbatim, and the superscript warning in `WHY_NOT.md` is correct and worth keeping. I rendered p. 1 as an image to confirm the exponent |
| "at most $N^K$" path candidates in city-scale 3D scenes | Eertmans et al. arXiv:2410.23773 section II | verbatim |
| "ray launching is more CPU-time efficient than image-RT algorithms for prediction over vast areas or volumes" | Fuschini et al. section 2.2 | verbatim |
| image tree built "Starting from the root of the tree, corresponding to the transmitter" | Fuschini et al. section 2.1 | verbatim |
| Chew chapter 12 reciprocity and reaction statements | Chew 2024, ch. 12 | verbatim |
| Veach section 3.7.3 adjoint passage and the "many different equilibrium importance functions" line | Veach 1997, p. 91 | verbatim |
| Veach section 4.6 equation (4.26) pair | Veach 1997, pp. 116 to 118 | verbatim |
| Sionna defines radio maps as path integrals "similar to how measurements are defined in computer graphics" | tech report section 4.1, p. 31 | verbatim, and reference [24] there is indeed Veach 1997 |
| Leeman et al. table 1, five reflections, one diffraction, 0.25 degrees, 40 dB cut | IEEE Access 13:30894, p. 30897 | read from the rendered page, correct |
| Xia et al. RMSE 12.79 / 10.17 / 11.07 improving to 7.09 / 6.15 / 5.95 | IEEE TAP table VI, p. 7994 | read from the rendered page, correct |

**Section 4, the polarisation argument.**

The Fresnel table in section 4.3 is correct in all ten entries. I recomputed it
independently from the ITU-R P.2040-3 table 3 parameters at 15 GHz, using
$\eta' = a f^b$, $\sigma = c f^d$ and $\eta'' = 17.98\,\sigma / f$ from equations
(57) to (59), and agree to the printed precision. The concrete pseudo-Brewster
angle of 66.43 degrees and the brick value of 63.17 degrees both match
$\arctan\sqrt{\eta'}$ to two decimals, which is the right consistency check since
the loss tangents are small.

3GPP TR 38.901 table 7.5-6 part 1 UMi street canyon XPR values are correct as
printed: $\mu = 9$ / 8.0 / 9 dB and $\sigma = 3$ / 3 / 5 dB for LOS, NLOS and
O2I. I read them from ETSI TR 138 901 V19.4.0 (2026-07). The derived cross polar
power fraction of 13 to 16 percent is right, $10^{-0.9} = 12.6$ percent and
$10^{-0.8} = 15.8$ percent.

**Both DOI corrections are correct, and I re-verified them independently against
Crossref rather than taking them on trust.** `10.1109/8.29370` resolves to
Ferraro et al. on ELF signals from the polar electrojet, *IEEE TAP* 37(6):802-805,
so the Ling correction to `10.1109/8.18706` is right. `10.1109/TVCG.2003.1207443`
resolves to Yamane and Nakamura on motion animation, so the Christensen correction
to `10.1109/TVCG.2003.1207441` is right.

---

## 2. Contradictions and additions

### 2.1 Contradiction: the Samimi and Rappaport LOS number

`WHY_NOT.md` section 4.2 currently reads:

> Samimi and Rappaport, EuCAP 2016 ... abstract: "Small-scale spatial measurements
> at 28 GHz reveal a mean cross-polar ratio for individual multipath components of
> 29.7 dB and 16.7 dB in line of sight and NLOS, respectively." So NLOS
> depolarises relative to LOS by about 13 dB

The quotation is accurate. The abstract does say 29.7 dB. **The abstract
disagrees with the rest of the paper, and the abstract is the one that is
wrong.**

Section VI of the same paper, "Cross-Polar Ratio (XPR) Measurements", p. 5,
states the fitted values as "28.7 dB and 6.0 dB in LOS, 29.2 dB and 5.5 dB in
LOS-to-NLOS, and 16.7 dB and 8.8 dB in NLOS". Table VI, on the same page and read
from the rendered page rather than an extraction, prints $\mu = 28.7$, 29.2, 16.7
across the three columns.

The paper's own arithmetic settles which is right. The sentence immediately after
the Table VI discussion reads "In NLOS, the mean XPR is 12 dB smaller than in
LOS", and $28.7 - 16.7 = 12.0$ exactly, whereas $29.7 - 16.7 = 13.0$. The body,
the table and the internal difference all agree on 28.7. The abstract has a
typographical error.

**Action.** Cite 28.7 dB and a 12 dB LOS to NLOS gap, sourced to table VI and
section VI rather than the abstract, and drop the "about 13 dB". The direction of
the argument is unaffected, and the magnitude changes by 1 dB. It is worth fixing
because a reviewer who checks the table will find the mismatch and it costs
nothing to be on the right side of it.

### 2.2 Addition: the per site Karttunen fit that was left out

`WHY_NOT.md` section 4.2 says:

> Per site fits exist in that paper's table for the 14.25 GHz open square
> specifically. I did not use them, because the table's column alignment does not
> survive text extraction and I did not want to attribute a number to the wrong
> column.

That caution was correct and the extraction is genuinely unreliable. I resolved it
by rendering page 7 of `lit/karttunen2019_multipath_XPR_5-80GHz_arxiv1804.00847.pdf`
as an image and reading table I visually. The column headers of the second block
run SQR1, SQR1, SQR2, SQR2, SQR2, SC1, SC1, SC2, SC3, SC3, SC3, SC3, SC4 with
frequencies 27.45, 83.5, **14.25**, 27.45, 61, 14.25, 27.45, 27.45, 14.25, 27.45,
61, 83.5, 27.45 GHz. The third column is therefore the open square at 14.25 GHz,
and reading down it:

| quantity | SQR2 at 14.25 GHz |
|---|---|
| bandwidth | 0.5 GHz |
| $h_{\rm BS}$, $h_{\rm MS}$ | 2.6 m, 2.6 m |
| link distance | 5 to 99 m |
| dynamic range | 42 dB |
| links | 10 |
| MPCs with measured XPR | 464 |
| model 1, $\hat\mu_1$, $\hat\sigma_1$ | 16 dB, 6.9 dB |
| model 2, $\hat\alpha_2$, $\hat\beta_2$, $\hat\sigma_2$ | $-0.44$, 27 dB, 5.0 dB |

So the excess loss law for this site is $\mathrm{XPR} = -0.44\,L_{\rm ex} + 27$ dB
with $\sigma = 5.0$ dB, and the constant mean alternative is 16 dB.

This **strengthens** the retraction argued in section 4.2 rather than qualifying
it. Reaching $\mathrm{XPR} = 0$ dB at this site needs $27/0.44 = 61$ dB of excess
loss against the 56 dB the pooled model gives, and reaching 6 dB needs 48 dB
against 44 dB. The constant mean fit is the blunter statement of the same thing:
the typical multipath component in a real open square at 14.25 GHz has 16 dB of
cross polarisation ratio, which is a cross polar power fraction of 2.5 percent,
not 50 percent.

The site is described in section III of the same paper as Narikkatori, Helsinki,
"approximate dimensions of 90 x 90 m2 and ... surrounded by modern, multi-story
buildings", containing "lamp posts, trees, and a sculpture". That is a closer
geometric match to this study than anything else in the polarisation section.

**One caveat that has to travel with it.** SQR2 was measured with
$h_{\rm BS} = h_{\rm MS} = 2.6$ m, both terminals near ground level. That is the
street small cell illumination geometry of section 4.3, not the macro rooftop one.
The SQR1 rows, which do use $h_{\rm BS} = 5$ m, were measured at 27.45 and
83.5 GHz and not at 14.25 GHz, so there is no rooftop open square measurement at
this frequency in this dataset. Quote the SQR2 numbers for the street law and say
that the rooftop law has no matched measurement here.

### 2.3 Addition: the pair structure is Sionna's own stated cost driver

Section 3.1 makes the per pair point from the definitional sentence. The sentences
that follow it in the tech report, p. 8, make the cost point directly and are
worth having:

> "Ideally, paths would be traced between every pair of transmitter and receiver
> antennas, designating the sources and targets as the set of transmit and receive
> antennas, respectively. However, when radio devices are equipped with a large
> number of antennas, computing paths for all antenna pairs becomes
> computationally demanding. To mitigate this issue, Sionna RT introduces a
> synthetic array feature, which calculates paths only between radio devices
> instead of each antenna pair."

The synthetic array exists because the pair count is the thing that blows up. That
is a stronger form of the section 3.1 argument than the definition alone, since it
shows the pair primitive already forcing an approximation inside the tool.

### 2.4 Addition: a readable citation for bidirectional launching

Section 3.3 rests the bidirectional observation entirely on Taygur et al., which
it correctly reports as paywalled and quotes nothing from. There is a readable
one already in `lit/`. Fuschini et al. section 2.2:

> "Ray launching processes can be implemented simultaneously from both the Tx and
> the Rx sides to increase accuracy and efficiency"

citing Zhu, M., Singh, A. and Tufvesson, F., "Measurement based ray launching for
analysis of outdoor propagation", *6th EuCAP*, 2012, pp. 3332-3336,
doi 10.1109/EuCAP.2012.6206329. I have not read the Zhu paper itself, so cite it
through Fuschini or not at all.

This does not weaken section 3.3's honest disclaimer. Both are bidirectional
rather than receiver only, so the statement that no readable paper traces only
from the receiver still stands. It does mean the disclaimer can be made without
leaning on a source that cannot be quoted.

### 2.5 Addition: the image method is not symmetric in cost, and it is worth saying why

Section 3.1 cites Fuschini for the transmitter rooted tree. Sood's thesis is
already in `lit/` and already in the reference list, pointed at sections 1.3.1 to
1.3.2 for the measured exponents, but is not drawn on in the body of section 3.
It has the complementary half:

> "The SBR based ray-tracing methods compute the ray-path starting from the Tx."

> "The image method computes the ray-path starting from the Rx and incrementally
> builds the path geometry all the way back to the Tx. Therefore it usually
> requires the generation an image tree which systematically arranges all the
> image sources in a hierarchical fashion."

Put beside Fuschini and Savioja and Svensson this sharpens the asymmetry into its
strongest form. The image method's cheap step, walking a path back from the
receiver, is receiver side. Its expensive step, the image tree, is source rooted
and is the part that scales as $N^K$. So the method reuses work across receivers
and redoes it for every source, which is precisely the wrong way round for a
source continuum. That is a more specific claim than "the primitive is a pair" and
it is supported by three independent sources.

### 2.6 Addition: one more line from Kasdorf for section 3.4

Section 3.4 lists what the alternatives do better and correctly gives diffraction
as one of them. The Kasdorf paper says it from the other direction, which is
useful because it is an SBR paper conceding an SBR advantage rather than a
weakness:

> "the SBR method allows for the extension of propagation to include refraction
> and diffraction, which IT alone cannot accomplish. This makes the SBR method
> much more efficient and versatile for use in large environments."

Worth noting that this cuts against listing diffraction as an advantage of the
image method specifically. Image theory alone cannot do diffraction either. The
tracers in section 3.4 that do have diffraction have it because they are hybrids,
which is what Sionna RT is.

### 2.7 Dating nuance, not a contradiction

Section 3.4 says "Sionna RT supports first order wedge diffraction". True of the
current release and of 0.19, but not continuously. From the `NVlabs/sionna-rt`
release notes, v1.0.0 of 8 April 2025 rewrote the tracer and dropped it, stating
"Diffraction and reconfigurable intelligent surfaces (RIS) will be added in future
releases. Users relying on these features should use the latest 0.19 release."
Diffraction returned in v1.2.0 on 19 September 2025. Anyone reproducing against a
pinned version between those dates gets no diffraction at all. One clause is
enough, and it matters only for reproducibility.

Related and already correct in section 2.3: the `diffraction=False` default is
real, and I confirmed it in the 2.0.1 `PathSolver` signature along with
`max_depth=3`. Note that the prose at the top of that same documentation page is
stale, still saying the solver supports only line of sight, specular and diffuse
reflection and refraction, while the signature it documents exposes `diffraction`,
`edge_diffraction` and `diffraction_lit_region`. Cite the signature, not the
prose.

---

## 3. A repository risk worth raising

`lit/` is 274 MB and is entirely gitignored. The repository root `.gitignore`
excludes `*.pdf` at line 119, so none of the sources behind `WHY_NOT.md` are or
will be under version control, and I have not forced them in. Given the size and
that most are publisher PDFs, that is the right default.

The consequence needs stating, because `WHY_NOT.md` section 8 already worries
about it from the other end. That section flags mmMAGIC D2.2 and METIS D1.4 as
Wayback only, with `5g-mmmagic.eu` parked and `metis2020.com` squatted, and says
"Archive the local file". Those files currently exist in exactly one place, an
ignored directory on this machine, and two load bearing quotations in section 2.2
depend on them. The same is true of the Ericsson tdoc R1-160846, which is the
single most important measurement in the diffraction argument and has no DOI.

This is not something I should decide unilaterally, so I am raising it rather than
acting. The options are to commit those specific few files with `git add -f`,
accepting the copyright question and a few tens of megabytes, or to archive them
outside the repository and record the location. Doing neither means the argument
in section 2 becomes uncheckable the first time this machine is rebuilt.

---

## 4. What I did not resolve

- **Ling, Chou and Lee 1989.** Still unread. Unpaywall reports no open location and
  there is no repository copy. `WHY_NOT.md` is right to attribute no complexity
  claim to it. The NASA NTRS abstract confirms the method structure only.
- **Taygur et al. 2018.** Still unread, no preprint. Section 2.4 above reduces how
  much rests on it but does not replace it.
- **Degli-Esposti et al. 2011.** Still unread. It is Sionna's scattering reference
  and the tech report uses it for a scattering cross polarisation discrimination
  $K_x$, so it would be the natural source for a per bounce XPD if anyone wants to
  replace the unpolarised average rather than bound its error.
- **Sloane et al. 2026, "path-specific cross-polarization discrimination",
  *IEEE TAP*.** Found but not obtained. On the title alone this is the closest
  thing in the literature to the per bounce quantity section 4 is approximating
  away, and it is the one I would chase next.
