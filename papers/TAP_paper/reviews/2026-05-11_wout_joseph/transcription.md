# Wout Joseph review transcription v2 (2026-05-11)

## Intake notes

- Source images are registered in `manifest.json`.
- Source paper: `v1_to_coauthors/paper.tex`.
- Physical 2x crops for each image quadrant are stored in `zoom_tiles/`.
- Finer 4x4 physical crops are stored in `zoom_tiles_4x4/`.
- `transcription_draft_v1.md` is preserved as a rejected first pass. This v2 file is the active transcription.
- This transcription has been manually completed by Robin and is now the source of truth for Wout Joseph's marked-up review. Confidence values record manual review provenance rather than AI certainty.
- `High (manual)` means the row has been accepted in Robin's completed manual pass; interpretation and paper edits should still remain separate from literal transcription.

## Global themes visible across pages

- Move dense method/derivation material out of the introduction.
- Define symbols and acronyms earlier, especially `T_0`, APD, SAR, psSAR, SARwb, and figure-specific quantities.
- Refer to Fig. 1 explicitly from the relevant derivation text.
- Prefer concrete figure/table references over "upper/lower panel" wording.
- Soften or clarify "exact", "closed form", and validity claims where approximations, regime boundaries, or FDTD comparison limits apply.
- Rework theorem/corollary numbering and naming.
- Shorten long captions, especially Fig. 8.
- Reduce or remove future-directions and acknowledgment material if it distracts from the paper.
- Fix AI-like prose where marked ("soms AI tekst aanpassen").
- Use "AEGIS" where Wout wrote it in the abstract-area margin.

## Page transcriptions

### IMG_2705, printed page 1

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Top-right margin, title/authors | "soms AI tekst aanpassen; Fig 1 naar verwijzen, Fig 1 in method sectie" | High (manual) | General title and opening-page structure. The figure number may be 2. |
| Top-right margin | "Sectie VII onderdeel van VIII maken; Future work max 2 zinnen bij conclusie" | High (manual) | Section placement note about validity/compliance and future work. |
| Above abstract | "abstract: nog iets inkorten; ik verwijderde enkele zinnen" | High (manual) | Abstract opening and claim framing. |
| Above abstract, arrow into first sentences | "AEGIS" | High (manual) | The method/name AEGIS should appear in the abstract opening. |
| Abstract first sentence / "FDTD simulation" | "simulation" should be "simulations" | High (manual) | Printed "FDTD simulation" marked in abstract. |
| Left margin beside abstract | "wordt bedoeld? local? beschrijf zin" | High (manual) | "local law integrates over the body mesh into a generalized Cauchy formula." |
| Left margin, abstract lower half | "4 validations are done for ...; remove at 5.8 GHz; FDTD + ___? xx% afwijking" | High (manual) | Long abstract validation sentence covering 168 volunteers, 5 FDTD phantoms, 1-100 GHz and 6-100 GHz. |
| Abstract middle | Struck sentence pair: "The formula extends the classical convex projected-area identity to nonconvex absorbers. An ambient-occlusion pass on the mesh evaluates the self-shadowing factor." | High (manual) | These two sentences are deleted or moved out of the abstract. |
| Lower-left near Index Terms | "The proposed AEGIS method ?" | High (manual) | Abstract/index transition. |
| Near "168 volunteers" | "168 = good" | High (manual) | "168 volunteers" underlined. |
| Near "Fresnel trans-" | "<95%" | High (manual) | "Fresnel transmission" boxed/underlined. |
| Right column, first intro paragraph | "simulation" and "difficult" | High (manual) | "simulations above 30 GHz become infeasible" marked, likely replace "infeasible" with "difficult". |
| Bottom-center | "Fig: verwijderd door onvolledige [?]" | High (manual) | Figure/method placement note, no figure on page. |
| Right margin | "ok" | High (manual) | Approval marks beside later introduction paragraphs. |

### IMG_2706, printed page 2

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Upper-left column | "data model?" | High (manual) | Sentence about slope reported by Flintoft. |
| Contribution list item 1 | "Cole-Cole catalog" / "change" | High (manual) | "IT'IS Cole-Cole catalog" crossed/marked. |
| Left margin beside "The result is a pair..." | "verduid" or "verduidelijk" | High (manual) | Pair-of-closed-forms paragraph. |
| Large bracket lower-left intro | "The empirical scalars... til the end" / "out in method, not in intro" / "Method section X_1" | High (manual) | Several paragraphs explaining empirical scalars, validation, and flowchart. |
| Bottom-left | "Method section" and "x1" | High (manual) | Same bracketed introduction material. |
| Right margin beside Fig. 1 | "good process method" | High (manual) | Fig. 1 flowchart and caption. |
| Fig. 1 caption/right column | "goed maar voor methods; definieer psSAR, SARwb, APD" | High (manual) | Regulatory outputs in Fig. 1 caption. |
| Near Section II heading | "II. Method: stuk X_1" | High (manual) | `II. Local absorption law`. |
| Near Section II heading | "Aka x1" / "[?] x1" | High (manual) | Section naming/order note. |
| Near first derivation sentence | "dit is al conclusie => verder zetten" | High (manual) | "The derivation below is exact; all approximations..." boxed/underlined. |
| Far-right lower margin | "dit is gedetailleerd - verder zetten" | High (manual) | Same derivation sentence and Section II start. |
| Below boxed sentence | "wat bedoeld" | High (manual) | Same sentence, asks what is meant. |
| Around subsection heading | "Setup" circled | High (manual) | `A. Setup`. |
| First derivation line, page 3 | "monochromatic" struck | High (manual) | "A monochromatic plane wave" at the start of the derivation. |

### IMG_2707, printed page 3

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Left column, Section A paragraph | No separate text, "bounded" marked | High (manual) | "bounded corrections in Sections IV and VI." |
| Right column near Eq. (4) | "Teff" | High (manual) | Definition of `T_eff(r)`. |
| Bottom margin | "referenceer naar Fig 1 in tekst" | High (manual) | Request to reference Fig. 1 in the text. |

### IMG_2708, printed page 4

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Table I caption and `T_0` | "definieer T0" | High (manual) | `T_0` circled in Table I. |
| Top-right of Table I | "is normal incidence Tavg!" | High (manual) | Table I caption and `T_avg/T_0`. |
| Fig. 3(b) plot | "in legend" | High (manual) | Curve label `T_0 cos theta`, should be in legend. |
| Left margin, beside the sentence "below the strict Azzam threshold" | "nodig? hier te zetten" | High (manual) | The sentence beginning `below the strict Azzam threshold` and the following `Section S2 and Table S1 of the SI...` line. |
| Section B first sentence | "Fig. 3a" | High (manual) | "upper panel" wording crossed. |
| Section B next sentence | "Fig. 3b" | High (manual) | "lower panel" wording crossed. |
| Near Table I deviation discussion | "The maximum deviation is" | High (manual) | Maximum 5.6 percent discussion. |
| Bottom-left large bracket | "zet Table I hier: bottom" / "zet Tabel I & Fig. [?]: dubbel" | High (manual) | Table I/Fig. 3 discussion may be duplicative; table should not sit at the top of the column. |
| Bottom center | "shows the normalized absorbed power" | High (manual) | `APD/IPD` discussion; replaces the APD/APD=... wording. |
| Section C right side | "refereer naar Tabel II" | High (manual) | `Table II` underlined; arrow below says `OK` once the table mention is seen. |
| Bottom-right | "suppl. materials nodig hier te zetten? bij transactions zijn SI niet gebruikelijk..." / struck `Table S1 and Fig. S2 ... Table S1 reports the angular variation` | High (manual) | `Table S1 and Fig. S2 of the SI...` |
| Very bottom-right | "bij Transactions zijn SI niet gebruikelijk" | High (manual) | Same SI reference. |

### IMG_2709, printed page 5

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Top-right above Eq. (9) | "normal incidence transmission" | High (manual) | `T_0` in Eq. (9). |
| Right margin near visibility paragraph | "Fig 5 shows" | High (manual) | Replace `Figure 5a` contrasts sentence. |
| Right margin mid-page | `Fig 5b` with `~~~~~` and two `______` marks | High (manual) | The `Fig. 5b` explanation is being emphasized and Wout is asking where `Fig. 5b` is explained. |
| Near pseudo-Brewster sentence | struck out | High (manual) | Remove the near-constancy/pseudo-Brewster sentence. |
| Section D first paragraph | "R(f)" | High (manual) | "sphere ratio" definition. |
| Lower-left margin | "niet (underlined) conservative, underestimates! (underlined)" | High (manual) | Wout is emphasizing that `conservative` and `underestimates` are both underlined, with a pet-peeve-style correction. |
| Section E start | "of the exact law (5)" | High (manual) | `exact law (5)` marked. |
| Bottom-right | "+ ook refereren naar Fig 1 in tekst" | High (manual) | Mesh/geometric law discussion after Eq. (10). |

### IMG_2710, printed page 6

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Left of Fig. 5(a) | "dit kan kleiner 1/2 size" | High (manual) | Figure panel placement; make it smaller, about half size. |
| Lower-left near Section IV | removed | High (manual) | `IV. Whole-body absorbed power`. |
| End of first Section IV paragraph | "OK" | High (manual) | `Fig. 1` underlined. |
| Right of Fig. 5 caption/Remark 1 | insert `\eta` after `exposure fraction` | High (manual) | The phrase `the exposure fraction` should be followed immediately by `\eta`. |
| Right margin mid-lower | "ok" | High (manual) | Nonconvex-bodies paragraph. |

### IMG_2711, printed page 7

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Theorem heading | "1" | High (manual) | `Theorem 2` marked, likely numbering/name issue. He refers to the fact LaTeX numbers things weirdly if e.g. a remark was made before this theorem this becomes th 2... |
| Left-column middle | "OK" | High (manual) | Classical Cauchy formula sentence. |
| Left margin by Corollary 4 | "ander nummer? andere naam theorem?" | High (manual) | `Corollary 4` circled and `Theorem 2` underlined. Same issue as above. Moreover he doesnt like 'corollary'|
| Bottom-left margin | "nodig in paper? titel theorem? frappante stijl (AI?)" | High (manual) | Large bracket around corollary/discussion. |
| Upper right below Table III | No separate note | High (manual) | "Agreement at 1-2 GHz is not claimed." crossed out. |
| Section C first sentence | "ref" and "ref" referring to after Flintoft and Zhang | High (manual) | and also he has `Corollary 4 reproduces... above 6 GHz...` crossed. "Below this frequency" --> Below 6 GHz |
| Right margin Section C | "ok." | High (manual) | Dip near 3 GHz explanation. |
| Section C body | No separate note | High (manual) | Constructive/destructive interference sentence underlined. |

### IMG_2712, printed page 8

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| End of Corollary 4 paragraph | Wavy mark only | High (manual) | "Total power remains valid via `T_lay` throughout." He lowykey crossed out the sentence, but tbh idk if it's worth to remove. |
| Section V heading | "(i) Mie theory on lossy spheres ..." so just add (i) | High (manual) | `V. Validation`. |
--> also here (ii) Sim4Life FDTD .... and later (iii) The reverberatio-chamber and FDTD literature --> you understand right.
at the end of the whole paragraph (so after population level.) "(iv) hybrid ? "
| Section A heading and first lines | "Setup" --> "Configuration" | High (manual) | .. |
In this whole paragraph, so twice, remove "IT'IS" and "v5.0". after Virtual Population, write "shown in Fig 5".
"...skin properties at each frequency." --> add a ref here
| Right column, Mie paragraph | "definieer" | High (manual) | `mmWave` circled. |
| Right column, sub-mmWave sentence | use "xx - xx GHz" | High (manual) | "sub-mmWave frequencies". |
| Section C heading/right margin | "This section validates the theory for realistic anatomies" | High (manual) | crossed "The phantom test bounds it on realstic anatomy" |

### IMG_2713, printed page 9

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Fig. 6 right plot top | "?" | High (manual) | `mmWave` label circled. Ignore this comment from Wout |
| Left column Section E paragraph | "Table V lists the" instead of states | High (manual) | `Table V states` marked. |
| Bottom of left column | "Bamba et al" --> add ref | High (manual) | End of Bamba/geometric-optics explanation. |
| Right column, Bamba paragraph | "[ref]" | High (manual) | `Bamba et al.` |
| Right column, Diao paragraph | "[ref]" | High (manual) | `Diao et al.` |
| Center blank above Kodera paragraph | "<enter weg>" | High (manual) | Transition into Kodera comparison paragraph. refers to a large vspace here... could just be latex struggling with spacing though. |

### IMG_2714, printed page 11

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Right margin beside Fig. 8 | "mooie figure!" | High (manual) | Fig. 8 plot. |
| Left margin beside Fig. 8 caption | "heel lange caption is niet IEEE stijl" | High (manual) | Long Fig. 8 caption. |
| Left margin beside Section C | "Ok" | High (manual) | `C. Inter-body reflections`. |
| Right column, second paragraph | "frequencies?" | High (manual) | `mmWave` circled/marked. |

### IMG_2715, printed page 12

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Right column near Eq. (17) | "The" before "Body" / "[?]" | High (manual) | Body-surface-area/Du Bois paragraph. |
| Remark 5 | "Remark 5" --> wout hates this thing. He thinks it's odd, especially with the ( ) after it with the title of the remark, and far enough | High (manual) | `Remark 5. Reference-level shortfall for smaller body sizes.` |
| Section VII heading | "AI?" | High (manual) | `Compliance and corollaries`; "and corollaries" crossed firmly. |
| Left margin Section VII lead | "Herschrijf deze zin (AI...) Doel van deze zin in eigen geschreven zin" also "Is deze sectie nodig? doel? in VIII integreregn? te veel secties nu" | High (manual) | "Regulatory compliance reduces..." and "precomputed" underlined. |
| Section B / Corollary 6 | "herschrijf" | High (manual) | `Corollary 6` and heading crossed/underlined. |

### IMG_2716, printed page 13

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Top over Table VIII | "AI taal: limits / boundaries" | High (manual) | `Band stratification` in Table VIII title. |
| Table VIII body | "wrong" --> "other" | High (manual) | "wrong physics: resonance and hot-spots" marked. |
| Section VIII heading | "Discussion and Compliance" | High (manual) | `VIII. Discussion`. |
| First paragraph, left margin | "gebruik gewoon 'method'ipv netwerk. andere term herschrijf" | High (manual) | `network` circled. |
| Left margin near Section B | "VII hierbij" | High (manual) | `B. Regulatory implications`. |
| Bottom of left column | Table VII "returns" --> "lists" | High (manual) | `Table VII returns...`. |
| Section C heading | "Table VIII summarizes" this sentence/paragraph is now a lot lower but should START regime of validity | High (manual) | `C. Regime of validity`. |
| Section C mid paragraph | "welke sectie? eq (..)" | High (manual) | `The opacity criterion` crossed. |
| Section C lower paragraphs | No separate note | High (manual) | `IT'IS` crossed; SI-details sentence crossed; final Table VIII summary circled/underlined. |

### IMG_2717, printed page 14

| Page/region | Transcription | Confidence | Printed text referred to |
| --- | --- | --- | --- |
| Top-left paragraph | "softens" --> "ander werkwoord" | High (manual) | Pseudo-Brewster/high-index paragraph. |
| Left margin, reactive near-field paragraph | Write it like this: "in the reactive near field (d < lambda/2pi, i.e., 1.7~mm at 28~GHz), evanesscent waves..." | High (manual) | Reactive near field sentence |
mmWave --> mmWaves + (bereik?)
| Section D first item | Put it all at the very end of conclusions and shorten to just a couple of sentences. | High (manual) | The entire future directions paragraph. |
| Near Conclusion heading | Wout suggest to write 2-3 sentences beginning with "A closed form new method is proposed..." to open with | High (manual) | Conclusion heading/first formula. |
| First conclusion paragraph | No extra words | High (manual) | "collapse" crossed; empirical-scalars sentence also crossed. A note: "Geen vergelijkingen"|
| Whole-body ICNIRP paragraph | "above 6 GHz?" | High (manual) | Whole-body ICNIRP compliance paragraph. It turns out the validity of this is when the body is opaque, so down to like 1 GHz. |
| Right margin beside ICNIRP paragraph | "Under the worst-case ... and adolescent respecitvely" | High (manual) | Remove this. |
| Acknowledgment | Diagonal slash only | High (manual) | Acknowledgment paragraph struck through completely visually. |
