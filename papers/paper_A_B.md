# Paper A+B: spine planning

A high-level planning document for merging the pseudo-Brewster paper (current Paper A, 11 pp) and the whole-body identity paper (current Paper B, 7 pp) into one TAP submission. The spine, the structure, the sizing, the positioning, the reviewer surface, and the honest weaknesses, with no commitments yet.

## TL;DR

Combine. The two drafts are not two stories, they are one story split in half. The local Fresnel surface law and the direction-averaged whole-body identity are the same closed form integrated over different domains, and pseudo-Brewster compensation is the mechanism that makes the closed form scalar at both levels. Splitting buries each paper's punchline inside the other.

The combined paper fits classical IMRaD cleanly. The Methods section is a single derivation chain, and the Results section is four independent ground truths (Mie, Fresnel on Thelonious, Sim4Life FDTD, the 168-volunteer literature). Sizing comes out around 14 to 16 pp after deduplication, well inside TAP's regular limit.

The honest weak point is sub-6 GHz, where body-scale Mie and the fat Fabry-Pérot push the surface law from quantitative to qualitative. This is also the regime where psSAR_10g is the regulatory metric, so the AWPL letter sits in our weakest band, and we lean into that with the multi-layer extension rather than ignore it.

## Decisions locked in

- Merge A and B into one TAP paper.
- Keep the AWPL letter (psSAR_10g) and extend its scope with the multi-layer Fabry-Pérot block already derived in `theory/section_below6ghz.tex`. The letter targets sub-6 GHz where ICNIRP requires psSAR_10g, with explicit acknowledgement that the homogeneous half-space breaks down where the skin depth grows past tissue layer thickness, that the multi-layer treatment is itself shaky once whole-body resonance and body-traversing multipath enter, and that above 6 GHz we hand off to APD because the regulator does too.
- Keep Paper C as TWC, separate.
- Drop the ReLU naming everywhere. Use `(·)_+` (positive-part) without ML labels. Differentiability survives as one sentence in the corollaries section. The single ML-language remark we keep is the diffraction-smoothed activation, which is the GELU function used in transformer networks (citation included), because that is a genuine physical observation rather than relabelling.
- Keep the higher-order corrections section, tightened. The diffraction GELU pivot is the strongest piece of that subsection. Curvature and inter-body radiosity remain as bounded-error remarks with the existing tables and numbers.
- Title direction: dosimetry-frame, with the band claim revised to be physically honest (see "Band of validity" below) rather than the current "100 MHz to 100 GHz" which is convention-driven.

## What the one story actually is

There are three collapses, in order of decreasing locality:

1. **Polarisation collapses to a scalar.** Polarisation-aware Fresnel transmission is a 2x2 matrix function of incidence angle. Three independent conditions (circular polarisation, ensemble-averaged linear, multipath with N>=20) reduce it to the unpolarised average T_avg(theta).
2. **Angle collapses to a scalar.** For biological tissue with refractive-index modulus above 2.5, T_avg(theta) stays within 5.6 percent of T_0 across the full angular range. The mechanism is Azzam's high-index regime applied to lossy tissue: TM rises into pseudo-Brewster while TE falls, and the average tracks T_0. The angular dependence collapses to a constant.
3. **Geometry collapses to two scalars.** The local law S_ab = S_inc T_0 V (n_hat dot -k_hat)_+ integrated over an unpolarised, isotropic field collapses to ⟨P_abs⟩ = S_inc T_bar(f) A_ab/4. The whole-body integral is one ambient-occlusion pass over the body mesh; the tissue physics is one Fresnel quadrature.

This is the spine. Read top to bottom, the paper says: tissue physics is one number, geometry is one number, and the product times incident power is the absorbed power. Read bottom to top, the spine answers Kodera's open question (what closed-form T_tr does every phantom converge to) with a single derivation from Maxwell.

The pseudo-Brewster mechanism is what links the local and whole-body forms. Without it the local closed form requires per-angle T_avg lookups and the whole-body identity needs T_bar(f) (still closed form, but a different scalar). With it, both forms reduce to the same constant T_0 in the geometric-optics regime. The literature waterfall is the validation that this single constant fits 168 volunteers and five FDTD phantoms.

## Band of validity, quantitative

The current "100 MHz to 100 GHz" claim in both drafts is convention-driven, not physics-driven. The closed form is quantitative across roughly 1 to 100 GHz on whole-body integrated quantities, qualitative 300 MHz to 1 GHz with bounded error, and fails on the lower side below ~300 MHz where the body is no longer in the geometric-optics regime. The upper side holds cleanly to ~200 GHz with mild weakening, with surface roughness becoming the dominant correction above ~300 GHz. The merged paper should state the band honestly with these numbers, not the legacy 100 MHz floor.

The lower edge is set by three independent criteria, each with a different threshold.

**Body opacity.** The Cauchy identity rests on "all transmitted power is absorbed", which requires skin depth small against body dimensions. SAR penetration depth in muscle (Gabriel/IT'IS): 32 cm at 100 MHz, 13 cm at 300 MHz, 4 cm at 1 GHz, 1.5 cm at 3 GHz, 5 mm at 6 GHz, 0.5 mm at 28 GHz. The opacity criterion `delta_SAR << R_body` for an arm or leg cross-section (R ~ 5 cm) gives a transition near 700 MHz to 1 GHz: below this the wave traverses limbs and reflects from the far air interface, breaking the surface-only law. For a torso (R ~ 15 cm) the threshold drops to ~250 MHz.

**Body-scale Mie regime.** The geometric-optics limit requires `ka >> 1` where `a` is a body characteristic dimension. For a torso (a ~ 0.4 m): ka = 0.84 at 100 MHz, 2.5 at 300 MHz, 8.4 at 1 GHz, 25 at 3 GHz, 50 at 6 GHz. The geometric-optics asymptote with sub-percent Mie residual sets in around `ka ~ 30` (3 to 5 GHz on a torso, 1 GHz on a child phantom). Below that the surface law underestimates absorption because diffraction into the geometric shadow contributes 5 to 14 percent. The Mie validation in current Paper A's Section V documents this: error 14 percent at body-part sizes in mmWave, growing to >30 percent for fingers below 6 GHz.

**Whole-body resonance.** The body acts as a half-wave dipole, peaked near 70 MHz for a grounded standing adult and 175 MHz for ungrounded (Durney 1986). Internal fields are dominated by whole-body current distributions, with hotspots at ankles, wrists, and neck where current density is highest. Localised hotspot positions bear no relation to surface absorbed power density. The surface-to-volume reduction is the wrong physics in this band; the actual ACS spikes well above the geometric-optics value. The resonance tail extends up to ~300 MHz before becoming negligible against geometric absorption.

Combining the three criteria, the lower band edge stratifies cleanly:

| Band | Geometric-optics formula | What works |
|------|--------------------------|------------|
| Below 300 MHz | Wrong physics | Whole-body resonance dominates; hotspots at constrictions; FDTD or transmission-line body model required |
| 300 MHz to 1 GHz | Qualitative, ~10 to 30 percent error | Surface-only law underestimates; layered Fabry-Pérot in `section_below6ghz.tex` recovers the dip mechanism but not body-Mie |
| 1 to 6 GHz | Quantitative within ~5 to 10 percent | Closed form holds for total absorbed power; local map degrades because skin depth grows past surface layer; multi-layer correction matters |
| 6 to 100 GHz | Quantitative within ~3 percent | Both local and integrated forms; pseudo-Brewster compensation is at its sharpest |

The upper edge is set by two criteria, both gentler than the lower edge.

**Pseudo-Brewster compensation.** The Azzam high-index criterion `|n~| > 2.5` keeps `|T_avg(theta)/T_0 - 1| < 6%` across the angular range. Skin refractive-index modulus from IT'IS Cole-Cole: 4.84 at 28 GHz, 3.68 at 60 GHz, 3.01 at 100 GHz. Linear extrapolation of the Cole-Cole tail puts skin at `|n~|` ~ 2.5 around 200 to 250 GHz, ~2.2 at 300 GHz, ~1.8 to 2 at 1 THz. The compensation softens above 200 GHz and the worst-case angular variation grows from 5.6 percent at 28 GHz to ~10 percent at 250 GHz to ~15 percent at 300 GHz. This is still bounded against the 20 percent dielectric uncertainty floor.

**Surface roughness.** Skin features are stratified: stratum-corneum microtexture at 10 to 100 microns, papillary ridges at 0.4 to 0.5 mm spacing (fingerprint scale), gross body curvature at centimetres. Wavelength is 3 mm at 100 GHz, 1 mm at 300 GHz, 0.3 mm at 1 THz. The Rayleigh roughness criterion `h cos(theta)/lambda < 1/8` is met at 100 GHz on ridge-scale features, marginal at 300 GHz, violated above 1 THz. Diffuse scattering becomes the dominant correction once wavelength reaches ridge scale.

Combining: 100 GHz holds cleanly, 200 GHz holds with a ~10 percent compensation residual, 300 GHz pushes both criteria to their limits, and above 1 THz the closed form is in a different regime entirely.

**Recommended band claim.**

- Abstract: "valid above ~1 GHz on whole-body absorbed power and above ~6 GHz pointwise on the surface, with bounded errors documented up to 100 GHz. The layered tissue treatment in [section/letter ref] extends qualitative validity to ~300 MHz."
- Introduction: one paragraph that walks the three lower-edge criteria and the two upper-edge criteria, with the table above.
- Discussion: regime boundaries section with the same numbers, plus the carve-out that body-resonance physics below 300 MHz is a different paper.

This costs us the headline "100 MHz to 100 GHz" range but gains a defensible technical claim. The honest range "1 to 100 GHz" is still two decades of frequency, covers every wireless system that motivates the work, and matches where ICNIRP places the local-versus-whole-body transition.

## Why a split paper buries the spine

Paper A as it stands ends at the local geometric law and a Mie/FDTD validation on a phantom. The reader is left asking "and now what". Paper B answers "now Cauchy gives you the whole body" but the answer needs Paper A's local law, which Paper B has to either re-derive (duplication) or cite a not-yet-published preprint (fake citation, the user already flagged this). The two-paper version forces awkward standalone framing in both halves.

Paper B's literature waterfall is also the natural validation of Paper A's mechanism, not a separate result. The collapse of Bamba's eta(f), Flintoft's ⟨Q^a⟩/gamma_s, Zhang's xi, Kodera's T_tr, and Diao's T onto one scalar T_bar(f) is what shows the pseudo-Brewster compensation operates across the whole regulatory band on real bodies. Putting that figure in a separate Paper B disconnects it from the mechanism it validates.

## Classical IMRaD fits, and that is unusual

A combined paper has a clean IMRaD shape:

- **Introduction.** Regulatory-driven need (ICNIRP 2020, IEC/IEEE 63195), FDTD cost crisis (10^12-cell mesh per configuration, weeks on GPU clusters), the partial closed forms that have appeared in the literature (Cauchy 1841 convex, Kodera 2024 fitted T_tr, Diao 2024 anatomical FDTD, Bamba 2014 / Flintoft 2014 / Zhang 2017 volunteer chambers), the missing pieces (mechanism, non-convex extension, dip explanation, polarisation), the contribution.
- **Theory.** The derivation chain: polarisation-aware exact Fresnel surface law; identification of T_avg(theta) as the only obstruction; pseudo-Brewster compensation in the high-index regime (Azzam) with the quantitative tissue universality argument; geometric local law in (·)_+ notation; generalised Cauchy formula with proof; flux-weighted T_bar(f) and the IT'IS Cole-Cole computation; Fabry-Pérot dip via three-layer transfer matrix; bounded higher-order corrections (curvature with the 1/(kR) table, diffraction smoothing as an erf with Fresnel-zone width which is the GELU activation, inter-body radiosity with C ≈ 1.04 punchline). The matrix/multi-source form sits in compliance/corollaries, not Theory, and gets at most one paragraph plus one differentiability sentence.
- **Validation.** Mie on lossy spheres at body-part sizes; full polarisation-aware Fresnel on Thelonious to 0.35 percent on total power; Sim4Life FDTD on Thelonious giving Cauchy 1.012 at 5.8 GHz and peak 4 cm^2 SAPD 1.027 at 7 GHz with no fitted parameters; literature waterfall against 168 volunteers and five FDTD studies.
- **Compliance and corollaries.** ICNIRP whole-body SAR threshold reduced to three precomputed scalars (T_bar, A_ab, m), anthropometric scaling. Optional one-page corollary on the psSAR_10g cube formula (see psSAR question below).
- **Discussion.** Regime of validity (~3 GHz lower edge for the surface map, dielectric uncertainty floor at 20 percent, near-field limit, body-scale Mie below 5 GHz). Honest carve-outs.
- **Conclusion.**

Methods/Results balance is roughly equal once the chain is complete. Theory is rich because there are three collapses. Validation is rich because there are four independent ground truths. This is the unusual case where IMRaD genuinely fits a comm/EM paper, and we should use it.

## Sizing

Naive concatenation: 11 + 7 = 18 pp. After deduplication:

- Single introduction. Both current intros do the literature survey and the contribution pitch. Collapsed: -1.5 pp.
- Local law derived once. Paper B currently restates it; the merged version cites the merged Theory: -0.8 pp.
- Pseudo-Brewster treatment once. Paper B currently has a half-page summary the merged version absorbs into Theory: -0.4 pp.
- T_bar(f) table appears once.
- Validation streamlined. The kernel-vs-FDTD figure already appears in both papers; one copy: -0.5 pp.
- One conclusion: -0.5 pp.

Net target: 14 to 15 pp regular. TAP regular limit is 13 pp, extended to 30 with overlength fees. We will sit comfortably between regular and extended, well inside extended; and the substance pulls weight against an overlength fee.

The matrix form and differentiable-pipeline content from Paper A compress to one paragraph in compliance/corollaries with no ReLU framing. They are not the spine and should not get section weight. The ML-language remark we keep is one sentence in the diffraction-correction subsection that names the erf-smoothed shadow boundary as the GELU activation.

## Positioning against the literature

The merged paper sits at the intersection of five communities, and the introduction needs to acknowledge this honestly to land in any of them.

- **Bioelectromagnetics dosimetry.** Bamba, Flintoft, Zhang, ICNIRP, IEC/IEEE 63195. The three volunteer campaigns measured the same scalar in three different normalisations. Our identity tells them what they were measuring.
- **Numerical dosimetry / FDTD.** Kodera, Diao, Funahashi, Li. They fit T_tr per phantom. We derive T_tr = T_0 from Maxwell and predict the phantom-to-phantom spread is the body-shape factor A_ab/A.
- **Optics.** Azzam's high-index regime is the mechanism. The application to biological tissue has not appeared in the optics or bioelectromagnetics literature.
- **Computer graphics.** Zhukov, Landis, Akenine-Möller. Ambient occlusion is eta(r). Identifying the dosimetry primitive with the graphics primitive imports four decades of GPU-optimised algorithms into compliance work.
- **Integral geometry.** Cauchy 1841. The convex limit. We extend to non-convex absorbing bodies via eta.

The introduction should walk top-down through these five communities (or three, if we are tighter) and end on the contribution. Not "this paper does X". "Bamba measured a scalar; we tell you what it is. Kodera fitted T_tr; we derive it. Azzam observed angle-independent reflectance on lossless dielectrics; we apply it to lossy tissue. Cauchy gave the convex limit; we extend it."

## Title candidates

Picking a title is also picking the audience.

1. *Closed-form absorbed-power dosimetry on the human body from 100 MHz to 100 GHz.* Frame: dosimetry crisis solved. Strong for ICNIRP/regulatory readers, neutral for propagation/optics. Honest about the band.
2. *A closed-form absorption law for the human body: from polarisation-aware Fresnel to a whole-body identity.* Frame: derivation chain. Tells the reader the spine. Slightly long.
3. *Pseudo-Brewster compensation and a closed-form absorption law for the human body, 100 MHz to 100 GHz.* Frame: mechanism-first. Strongest single-line summary of the actual contribution, but pseudo-Brewster is a niche term outside optics.
4. *Geometric absorbed-power dosimetry on the human body: a closed-form chain from a local Fresnel identity to a whole-body integral.* Frame: chain. Best at signposting structure.
5. *Closed-form whole-body and surface absorbed-power dosimetry: pseudo-Brewster compensation and a generalised Cauchy identity.* Two-machine title, comprehensive but heavy.

My pick is 1 with the subtitle "from a local Fresnel identity to a whole-body closed form" if the editor allows subtitles, otherwise 1 alone and let the abstract carry the chain. 3 is the runner-up if we want to be mechanism-aggressive.

## Anticipated reviewer concerns

R1 (bioelectromagnetics, ICNIRP-literate). Worries: regime of validity below 6 GHz, dielectric uncertainty, psSAR_10g treatment, polarisation worst case. Answers we should pre-empt in the text: T_bar(f) and Fabry-Pérot extend whole-body validity through the sub-6 GHz dip; the local map degrades to qualitative; the 20 percent dielectric uncertainty dominates and our Fresnel error sits below it; psSAR_10g cube formula given as a corollary (or letter); polarisation worst case 16 percent on Thelonious, suppressed by multipath averaging.

R2 (propagation/antennas, channel-model-literate). Worries: connection to ray tracing, differentiability claim, MIMO compatibility. Answers: a one-paragraph remark identifying the multi-source form with a single-hidden-layer rectified network and naming the gradient flow; defer the MIMO/coherent treatment to the companion TWC paper.

R3 (Azzam tradition, optics-literate). Worries: Azzam's high-index criterion is for lossless dielectrics. How does it transfer? Answer: a quantitative table across IT'IS tissues showing the criterion holds for skin, muscle, and water, and weakens for fat. The lossy generalisation is empirical (we numerically verify) but it works on every relevant tissue at every relevant frequency.

R4 (editor / generalist). Worries: novelty against Kodera 2024 (which is recent and broad), against the convex Cauchy formula. Answers: Kodera fits, we derive; Kodera has no non-convex extension; Kodera does not predict the 3 GHz dip; the Cauchy generalisation to absorbing non-convex bodies via eta is novel; the 168-volunteer literature collapse is the test.

R5 (adversarial, looking to reject). Worries: "this is a textbook integral with a known shadow factor"; "pseudo-Brewster is Azzam's"; "Cauchy is Cauchy's"; "you stitched things together". This is the most dangerous review and we should write the paper to counter it.

## Adversarial self-critique

Five real weaknesses, ordered by how dangerous they are.

1. **Sub-6 GHz is genuinely shaky.** The geometric-optics surface law breaks down where skin depth grows past surface layer thickness, where body-scale Mie/diffraction matters (size parameter ka ~ 5 to 10 at 1 to 5 GHz on a torso), and where the fat Fabry-Pérot is large. We patch the integrated identity with T_lay, but the local map is qualitative below 6 GHz. The merged paper has to be honest in the abstract, not just the discussion. Suggested phrasing: "valid above ~6 GHz pointwise on the surface; valid above ~100 MHz integrated over the body when the layered transmission is used; qualitatively useful below this with documented errors". Not glossy, but honest.

2. **Pseudo-Brewster is Azzam's, Cauchy is Cauchy's.** Strict-construction, the closed form is a stitching together of four named results (Fresnel, Azzam, Cauchy, ambient occlusion). The reviewer who sees this as the criticism rather than the contribution will write a difficult report. The defence is the chain itself, not any single link: nobody else has identified T_tr with T_0 via Azzam, embedded the layered Fabry-Pérot in a Cauchy direction average, identified eta with gamma_s and the graphics primitive, validated the chain on three independent volunteer campaigns. Each link is known; the chain is not. The introduction needs to make this explicit and the conclusion needs to repeat it.

3. **The matrix and differentiability content is propaganda for a different audience.** Cut the ML language, drop "ReLU" entirely, keep only the GELU-as-diffraction-smoothing remark because that one is a real physical observation. The propagation/MIMO/RIS pitch is for Paper C and JSAC, not for the merged dosimetry paper. The merged paper gets one paragraph noting that the chain is differentiable and that gradients flow back through ray tracing, no more.

4. **The literature waterfall figure is doing a lot of work.** Six panels, five datasets, one common axis. Visually it lands, but reviewers will press on the per-dataset error bars, the cohort selection in Flintoft and Zhang, and the "within scatter" comparison for Zhang. Quantitative tightening of the figure caption and the comparison table is a one-evening job and will repay.

5. **psSAR_10g sits in our weakest band.** Per the user's note, ICNIRP requires psSAR_10g sub-6 GHz, where multi-layer Fabry-Pérot dominates and our surface law is at its weakest. The cube formula |k_x|+|k_y|+|k_z| is exact above ~6 GHz where the thin-skin limit holds, and is the wrong physics below ~3 GHz where layered transmission and multi-tissue effects matter. So the regulatory utility of the cube formula is lower than the AWPL draft suggests.

## What to do with psSAR (Option 3, locked)

Both: a one-paragraph corollary in the merged TAP paper (cube SAR follows from energy conservation as `(S_inc T_0 / rho_m L)(|k_x|+|k_y|+|k_z|)`, citing the letter as "to appear"), plus the AWPL letter with the multi-layer Fabry-Pérot extension. The corollary points the reader at the letter for the cube algorithm and the layered correction. The letter targets exactly the regulatory band where psSAR_10g is required (sub-6 GHz) and is honest about its limits.

The multi-layer derivation is already done. `theory/section_below6ghz.tex` (529 lines) contains:

- Three-regime breakdown: thin-skin > 6 GHz, transition 1 to 6 GHz, deep penetration < 500 MHz, with the depth-parameter table.
- Three-layer skin/fat/muscle stratification with generalised Fresnel reflection coefficients (Chew recursion).
- Standing-wave SAR with closed-form forward, backward, and interference terms.
- Layer-integrated cube SAR formula in closed form.
- Subsurface-peak criterion: `|g_1|^2 - (2 beta_1/alpha_1)|g_1|sin(psi_1) > 1`, evaluated at 8.0 for 2.45 GHz on a skin/fat/muscle stack, confirming the SAR maximum can sit below the surface.
- Limitations subsection naming the three regimes where even the layered model fails: whole-body resonance below 300 MHz, finite-thickness anatomy (ear pinna), and body-traversing multipath.

Pulling this into the AWPL letter is editorial work, not new derivation. Budget half a focused session for the letter extension.

The framing for the extended letter:

- *Target band.* psSAR_10g is the regulatory metric below 6 GHz (ICNIRP 2020). The letter covers this band with the multi-layer treatment.
- *Honest carve-out below.* The homogeneous half-space breaks down where skin depth grows past tissue layer thickness; the multi-layer treatment itself becomes shaky once whole-body resonance and body-traversing multipath enter (below ~300 MHz). State this in the abstract.
- *Honest carve-out above.* Above 6 GHz the regulator stops asking for psSAR_10g and switches to surface APD. The merged TAP paper handles that regime. The letter does not pretend to compete.
- *Headline.* Cube formula (axis-aligned, energy conservation) reduces the standard IEC/IEEE 62704 cube SAR to a closed form. The multi-layer extension makes it quantitative across the regulatory band. No FDTD per scenario.

## Do the papers land on their own

Honest assessment, unweighted by sunk cost.

- **Merged paper (combined A+B).** Lands strongly. The chain pseudo-Brewster, geometric local law, generalised Cauchy is a complete contribution. Validation against four independent ground truths is convincing. The 3 GHz weakness is honestly carved out. This is a TAP paper.
- **Paper C TWC, as is.** Lands. Different audience, different math, different validation. The closed-form Q from path geometry is the actual novel result and it stands. The integration with Paper A's surface law is by reference, which is fine because by the time C is reviewed A+B will exist.
- **AWPL letter, as is.** Lands marginally. Cube formula in the regime where it is not regulatory. With the multi-layer Fabry-Pérot extension, lands properly.
- **JSAC, as planned.** Different topic; reflection in a separate document.

The current four-paper split has Paper A landing marginally and Paper B landing weakly because of the chain dependency. The merged paper plus optionally the extended letter is genuinely stronger as a published record.

## What the existing drafts already give us

Most of the work is done. The merged paper does not require new derivations or new validations. It requires:

- a new introduction that walks the five-community map;
- merging Paper A's Theory and Paper B's Theory (sec 2 and 3) into one chain;
- one Validation section that combines Paper A's Mie/Fresnel/FDTD with Paper B's literature waterfall;
- a new Compliance section, possibly with the psSAR corollary;
- a new Discussion that names the regime boundaries cleanly;
- a new Conclusion.

Estimated effort: two to three focused sessions. None of the figures need to be regenerated; the matplotlib/SciencePlots pipeline carries over. The lit_waterfall figure is already iterated to clean. The phantom maps already exist.

## What still needs decision

Open items, narrower now that the structural questions are locked.

1. *Title.* Dosimetry-frame is the direction; the band-claim wording needs picking from the candidates above with the new "above ~1 GHz" honesty. My current pick: "Closed-form absorbed-power dosimetry on the human body across the wireless mmWave band" (drops the explicit numerical band from the title; abstract carries the numbers). Alternative: "A closed-form absorption law for the human body, 1 to 100 GHz".
2. *Order of Theory subsections.* Paper A order (Fresnel, polarisation, pseudo-Brewster, geometric local law) feeds naturally into Paper B order (Cauchy proof, T_bar, Fabry-Pérot, corrections). The merged order writes itself, but flagging it for confirmation.
3. *Validation order.* Mie -> phantom Fresnel -> Sim4Life FDTD -> literature waterfall is the natural ladder of breadth and rigour, but the lit-waterfall figure could come first as a hook. Worth a quick A/B in mockup.
4. *Sub-6 GHz framing volume.* Recommendation: abstract one sentence on the band, introduction one paragraph that walks the lower-edge criteria with the table, discussion the full regime-boundary list. Not louder, not quieter.
5. *Higher-order corrections placement.* Theory subsection (current Paper A position) or Discussion subsection? My pick: Theory subsection because they bound the error of the simplified law that follows from the spine, not the regime of validity that frames the spine.
6. *AWPL letter title and submission timing.* The letter could go in before, alongside, or after the TAP paper. AWPL is fast (~2 to 4 month turnaround) so submitting first is feasible and gives the TAP paper a citable predecessor. Worth thinking about.
