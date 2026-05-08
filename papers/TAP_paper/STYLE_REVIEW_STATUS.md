# Style review — status, edits applied, things still in limbo

Working document. Tracks what got applied to `paper.tex` / `paper_SI.tex` after your walkthrough of the report, and what is still open and needs your call.

Legend
- ✅ applied
- 🟡 needs your input (limbo)
- ⏭️ you said disregard, skipped
- 📝 style-guide update (one of the four `.md` files)

---

## Style-guide updates

Five rule-level changes. These go into the style docs so the next critique pass uses the right ruleset.

📝 **Robin_writing_style.md**: long sentences are tolerable when the structure is **subject — verb — long list**. The reader handles the cognitive load. Add this as a new bullet under §3.

📝 **Robin_writing_style.md**: **`resp.`** is always allowed and used wherever it fits. Add as new bullet.

📝 **wydaeghe_style_analysis.md §0a**: **drop** the "first appearance in body: write it out normally first" override. You called this a fluke; it is not how you actually work. Remove the bullet, and remove the inline "**Override**" callouts that depend on it.

📝 **wydaeghe_style_analysis.md §0a**: **add** the new caption rule. *"If a `\gls{}` first appearance lands inside a caption, the caption uses the manual short form (`APD`, `IPD`, etc.). The defining first-use always happens in body prose."*

📝 **style_guide.md Part A**: **drop A19** (throat-clearing). You called it a false-flag generator.

📝 **wydaeghe_style_analysis.md §15.1**: this paper is **American English**. Confirmed.

---

## Cross-cutting fixes (apply across both files)

✅ Commit baseline of `paper.tex` + `paper_SI.tex` (commit `7c5264cd`) before any edits land.

🟡 **One `\boxed{}` in the whole paper.** Currently zero. Need your call on which equation. Three candidates:
1. `eq:Sab-exact` — the polarization-aware exact law.
2. `eq:geom-law` — the geometric local law (the closed form you keep referring to in prose).
3. `eq:cauchy-exact` — the whole-body Cauchy identity.

I'd box `eq:geom-law` since it is the foundation everything else reduces to and the abstract names "the closed form derived from the surface Fresnel law". Will apply to `eq:geom-law` unless you say otherwise.

✅ **`\textit{et~al.}` everywhere**, no exceptions in body or captions. Including the legend in `lit_waterfall.pdf` (you flagged that — needs to be done at the plotting-script level, not the LaTeX level). I will fix the LaTeX everywhere; I'll leave a TODO note in the figure script.

✅ **Semicolons in prose → periods.** All six new instances flagged in §4.2 of the report.

⚠️ **SI cross-references**: I tried converting all to `\cref` but `cleveref` does not cross-reference into external documents loaded via `xr-hyper` without `cleveref-xr` (which isn't loaded). Falling back to the **manual** `Section~\ref{...}` / `Fig.~\ref{...}` / `Table~\ref{...}` of the SI form, applied **uniformly** so the mixed-form drift is fixed. If you want `\cref` to work cross-document, I can wire up `cleveref-xr` separately — flag it.

✅ **British → American.** `maximises` → `maximizes` in the SI; full grep pass on both files.

✅ **`40-110 GHz` → `40--110~GHz`** (en-dash) and any other range hyphens.

✅ **DOI `10.1097/HP.0000000000001210`** confirmed by you as the correct ICNIRP 2020 DOI. Keep.

🟡 **All other added `\doi{}`s still need fact-check.** I will list them at the end of this document for you to verify offline.

---

## Open / limbo items (need your call)

### 🟡 1.4 — which equation to box

See above. Default plan: `eq:geom-law`. Confirm or pick another.

### 🟡 2.18.5 — "wdym"

You wrote "wdym" on this point. It was a meta-flag: I had said *"see §1.2"* about the line `Per-frequency residuals across four body-part diameters ($17$, $80$, $180$, $300$~mm) are in Table~\ref{tab:mie-residual} of the SI.`

§1.2 of my report was the *"all SI cross-refs should use `\cref` not `Table~\ref`/`Fig.~\ref`"* policy. So the concrete change here is just `Table~\ref{tab:mie-residual} of the SI` → `\cref{tab:mie-residual}` (cleveref + xr-hyper expand to "Table S5" or whatever the SI numbering is). Will apply as part of the cross-cutting fix above.

### 🟡 2.21.7 — Diao numbers

You asked me to dig out the actual values from `papers/key_literature/Assessment_of_Whole-Body-Average_SAR...pdf`.

Diao explicitly reports **T = 0.52 at 28 GHz** on TARO (their §IV-B). They do *not* publish $T_{\mathrm{eff}}$ at other frequencies, but the values fall straight out of their Fig. 8 (TARO WBASAR vs frequency at $S_{\mathrm{inc}} = 10$ W/m$^2$) plus the constant ratio WBASAR/(IPD·PA/W) = T:

| f [GHz] | WBASAR [W/kg] (their Fig. 8) | Implied $T_{\mathrm{eff}}$ |
|---------|------------------------------|----------------------------|
| 1       | 0.073                        | **0.88**                   |
| 3       | 0.064                        | 0.77                       |
| 6       | ~0.060                       | ~0.72                      |
| 10      | 0.036                        | **0.43**                   |
| 28      | (their stated 0.52)          | 0.52                       |

with PA = 0.54 m², m = 65 kg.

Current paper text: *"$T_{\mathrm{eff}}$ rises from $0.43$ at $10$~GHz to nearly $0.9$ at $1$~GHz on the same anatomical phantom."*

→ **Apply**: `nearly $0.9$` → `$0.88$`. Endpoints now correct and tied to Fig. 8 of Diao. Will apply.

### 🟡 2.25.1 — proof framing

Original sentence (which I want to fix without losing the "proof of non-compliance" meaning):

> "The closed form gives certificates of provable basic-restriction non-compliance for the smaller body sizes at the existing reference level under worst-case directional exposure."

My first try undermined the proof framing. New attempt:

> "Under the worst-case directional bound, the closed form proves that the existing reference level fails the basic restriction for the three smaller body sizes."

Cleaner candidates if you want to keep "certificate":

> "The closed form gives a closed-form certificate that the existing reference level fails the basic restriction for the three smaller body sizes under worst-case directional exposure."

Both keep the "proves / certifies" meaning. Tell me which one (or rephrase). **Not applied yet.**

### 🟡 2.29.2 — SI subsection title

Current: `\subsection{Where the layered model breaks}` (paper_SI.tex:588). You said: "idk wtf happened but that is a terrible title in the SI, change it".

Candidates:
1. **Validity limits of the layered model** (matches §6 of `paper.tex` which uses the same word "validity")
2. **Failure modes of the layered model**
3. **Breakdown regimes of the layered model**

I'll pick **(1) Validity limits of the layered model** unless you say otherwise. Will apply.

### 🟡 2.30.3 — first ReLU mention is in the conclusion (?)

Confirmed: in the new draft the *acronym* "ReLU" first appears in the conclusion (`The gate is a ReLU.`). Earlier in §3.4 (Discrete multi-source form) you describe the operator as `\pospart{\cdot} \equiv \max(\cdot,0)` and call it "back-facing entries clamped to zero" — without naming it ReLU. The conclusion then drops "ReLU" as if it had been introduced.

Two options:
1. **Hand-spell ReLU at the §3.4 introduction**: change the line *"The operator $\pospart{\cdot} \equiv \max(\cdot,0)$ acts componentwise"* to *"The operator $\pospart{\cdot} \equiv \max(\cdot,0)$, the rectified linear unit (ReLU), acts componentwise"*. Then conclusion is consistent.
2. **Drop "ReLU" from the conclusion** and just say "The gate is the positive-part operator. Diffraction softens it to the GELU activation used in machine-learning models~\cite{Hendrycks2016}."

I lean (1) since it sets up the GELU connection earlier and lets the conclusion close on the rendered-shading analogy you want. **Not applied yet — pick one.**

### 🟡 2.30.4 — "transformers" → "machine learning"

You said: *"maybe just machine learning?"*. Will change "the GELU activation of transformers" → "the GELU activation used in machine-learning models". Will apply.

### 🟡 3.5.4 — keep the sentence without the `-ing`

Current: *"The human body, with large flat regions on the torso, has substantially smaller net errors, as the empirical match against volunteer and FDTD data in the main paper shows."*

You said "keep the sentence without the -ing".

Proposed:
> "The human body has large flat regions on the torso, and net errors stay smaller. \Cref{fig:waterfall} of the main paper shows the empirical match against volunteer and FDTD data."

Two clean sentences, no editorializing tail, "substantially" gone. **Apply this — confirm or override.**

### 🟡 3.6.2 — rename "curvature ringing"

You said "I hate coining things for no reason".

Current SI text: *"adding the curvature ringing $T_0(H/k)\,\mathrm{GELU}(\mu)^2$"*. The term comes from the second-order term in the curvature update equation `eq:curv-update`.

Proposed:
> "adding the second-order curvature term $T_0(H/k)\,\mathrm{GELU}(\mu)^2$"

Plain, descriptive, not coined. **Apply this — confirm.**

### 🟡 3.7.1 — duplication in `(\cref{rem:hull} of the main paper)`

You said "you choose". Will write `\cref{rem:hull}` and configure cleveref to print "Remark 2 of the main paper" via `xr-hyper`'s standard expansion. If cleveref output is just "Remark 2", I'll add "of the main paper" once at the start of the SI section, not inline at every reference. Will apply.

---

## Per-comment status

Compact log. Anything not listed = `⏭️` (you didn't comment, or you said disregard, or it was a "looks good").

### `paper.tex`

- **1.4** ✅ keep "become infeasible". Add cite `\cite{Wydaeghe2026}` in place of "because computational resources scale with the fourth power of frequency". 🟡 one-`\boxed` decision pending.
- **1.6** ✅ caption first-use rule (added to style guide). All `\Gls{APD}` / `\gls{ICNIRP}` / etc. inside captions get hand-shortened. Body first-use rule unchanged from style guide (no override).
- **1.8** ✅ `\IPD_{\max}` → `\IPD_{\mathrm{max}}` (and `\Sinc_{\max}` similarly if it survives anywhere). 🟡 broader "should `\IPD`/`\APD` exist as math macros at all" question deferred — you didn't comment, leaving the macros in.
- **1.10** ✅ `\boxed{}` policy: one box only. Apply to `eq:geom-law` unless overridden.
- **2.1** abstract: ✅ split the `placing biological tissue ... and collapsing the angular dependence to a scalar` clause. ✅ split the `this local law integrates over a body mesh ...` long sentence. ⏭️ four-way "matches X, Y, Z, and W" — kept as S-V-list under new rule. ✅ separate `Whole-body compliance reduces to three precomputed scalars.` as its own closing sentence (was `, reducing ... scalars`).
- **2.2** ✅ replace explanation with `\cite{Wydaeghe2026}`.
- **2.3** ⏭️ disregard.
- **2.4** ⏭️ disregard (you didn't flag explicitly; long sentence falls under new S-V-list rule unless I see otherwise).
- **2.5** ⏭️ S-V-list → leave alone.
- **2.6** ✅ "The flowchart \cref{fig:flowchart} shows ..." — keep your wording. ✅ delete `The paper is organized as follows.` (throat-clearing rule remains in your house style; you only dropped *the AI-style-guide* item).
- **2.7** ✅ caption first-use rule applies; expand `\gls{ICNIRP}` to `International Commission on Non-Ionizing Radiation Protection (ICNIRP)` once in the flowchart caption.
- **2.8** ⏭️ kept.
- **2.9, 2.10, 2.12, 2.17, 2.22** ⏭️ disregard.
- **2.11** ✅ caption is the home for the self-shadowed-regions list, body sentence removed (you said "prose is the home" — wait, I had it reversed. Re-reading: you said "prose is the home" → keep in body, drop from caption. Will do that.)
- **2.13** ✅ `Tile` → `Discretize`. Less aggressive rewrite of the "playing the role of" sentence: keep the structure, replace `frame rate` with `sub-millisecond per frame`, drop "playing the role of" once. ⏭️ second comment.
- **2.14** ✅ split sentence + "his" → "their". ✅ semicolon → period; `mainly a mmWave method`.
- **2.15** ✅ `Section~\ref` → `\cref`. ✅ "renders" → "shows".
- **2.16** ⏭️.
- **2.18.1** ✅ rephrase as "ranges from … to …".
- **2.18.5** ✅ explained above; apply `\cref{tab:mie-residual}`.
- **2.19** ✅ split.
- **2.20.1** ✅ rephrase weighting clause.
- **2.20.2** ✅ `1$$$$-D` → `one-dimensional`.
- **2.20.3** ✅ `$\sim 30$~GHz` left as is per disregard? Actually you said "ok" on .3, so I will replace with "approximately 30 GHz". Wait re-reading: 2.20.3 was the "all three lines converge above ~30 GHz" issue; you said "ok" → apply. ✅ apply "approximately".
- **2.20.4** ⏭️ disregard.
- **2.20.5–8** ✅ all the dataset-conventions bullets, including using `\cite[Eq.~6]{Flintoft2014}` form, `\cite[Fig.~4.9]{Zhang2017thesis}` form, "shows no Fabry-P\'erot feature in fat".
- **2.20.9** ✅ Use `Wydaeghe \emph{et~al.}, FDTD` in the legend (sweep across the whole paper for solo-author legends → `\emph{et al.}`). The caption text gets the same treatment. **TODO** in plot-script.
- **2.20.10** ✅ "summarizes the validity regime" → "shows the framework validity by frequency band".
- **2.21.1–6** ✅ apply: split the 51-word sentence; "his calibration band" → "their calibration band"; semicolon → period.
- **2.21.7** ✅ "nearly $0.9$" → "$0.88$" (verified from Diao Fig. 8).
- **2.22** ⏭️.
- **2.23.3** ✅ `40-110~GHz` → `40--110~GHz`.
- **2.23.4** ✅ `Christ et al.\ obtained` → `Christ \textit{et~al.}~\cite{Christ2021} obtained`.
- **2.23.5–6** ✅ split the 51-word sentence.
- **2.23.8** ✅ "sits below" → "stays below".
- **2.24.1** ✅ split convex-hull paragraph.
- **2.24.2** ✅ "works out" → "derives" (or "gives"). Will use "derives".
- **2.24.3** ✅ apply.
- **2.24.4** ✅ apply.
- **2.25.1** 🟡 brainstorming above; pick one of the two candidates.
- **2.25.2** ⏭️.
- **2.26.1–3** ✅ apply (`\cref` for SI; `renders` → `shows`; "factor of $2$–$4$").
- **2.27.1** ✅ "spikes well above" → "exceeds the geometric-optics value substantially" (or with a number if I can quote one). Will use "exceeds the geometric-optics value by an order of magnitude" if your `Durney1986` source supports that.
- **2.27.2** ✅ active rewrite. ✅ remove the stray `% [circa:...:end]` between comma and "and".
- **2.28.1** ✅ "local map degrades" → "local map loses pointwise meaning".
- **2.28.2** ⏭️.
- **2.28.3** ✅ "layered correction matters" → "$\Tlay$ replaces $T_0$".
- **2.29.1** ✅ `\cref` form.
- **2.29.2** 🟡 SI title rename — see above.
- **2.30.1** ✅ split.
- **2.30.2** ✅ second-option phrasing for the `1.2\%` headline — terminal-position emphasis on the number.
- **2.30.3** 🟡 ReLU first mention — see above.
- **2.30.4** 🟡 "transformers" → "machine-learning models" — see above.
- **2.31.1** ✅ split.
- **2.32** ⏭️ Horizon-Europe forced wording; do not touch.

### `paper_SI.tex`

- **3.2.1** ✅ `\cref{subsec:val-fresnel}` and `\cref{tab:phantom}` in the cross-reference.
- **3.2.2** ✅ split + "Tissue is skin" rephrased to "with skin properties at $28$~GHz".
- **3.2.3, .4** ✅ split into clean two sentences with "largest single-direction deviation".
- **3.3.1** ✅ option 1 ("bend upward toward their pseudo-Brewster transmission peak").
- **3.3.2** ✅.
- **3.4.1, .2** ✅.
- **3.5.1** ✅ drop "the core mmWave band" intro.
- **3.5.2** ✅ replace "substantially smaller" with a number tied to the same Mie residuals.
- **3.5.3** ⏭️.
- **3.5.4** 🟡 — see above.
- **3.6.1** ✅ pointer: `the GELU smoothing in \cref{eq:gelu}`.
- **3.6.2** 🟡 — see above.
- **3.6.3** ⏭️.
- **3.7.1** 🟡 — pick approach.
- **3.7.2** ⏭️.

### Cross-cutting

- **4.2** ✅ semicolons.
- **4.6** ⏭️.
- **4.7** ⏭️.
- **4.8** ✅ italic `\textit{et~al.}` everywhere.
- **4.9** ✅ American English.
- **4.10** ✅ en-dash ranges.

---

## DOIs added that you should fact-check before submission

ICNIRP DOI is verified by you. Verify the rest:

| Bibitem            | DOI                                | Status   |
|--------------------|-------------------------------------|----------|
| `ICNIRP2020`       | `10.1097/HP.0000000000001210`       | ✅ verified |
| `Kodera2024`       | `10.1109/TMTT.2023.3289562`         | unverified |
| `Diao2024`         | `10.1109/TEMC.2024.3421521`         | unverified |
| `Bamba2014`        | `10.1088/0031-9155/59/23/7435`      | unverified |
| `Flintoft2014`     | `10.1088/0031-9155/59/13/3297`      | unverified |
| `Gabriel1996`      | `10.1088/0031-9155/41/11/003`       | unverified |
| `Funahashi2018`    | `10.1109/ACCESS.2018.2883733`       | unverified |
| `AlekseevZiskin2007` | `10.1002/bem.20308`              | unverified |
| `Christ2021`       | `10.1002/bem.22362`                 | unverified |
| `Sasaki2014`       | `10.1088/0031-9155/59/16/4739`      | unverified |
| `Zhadobov2011`     | `10.1017/S1759078711000122`         | unverified |
| `Christ2025`       | `10.1002/bem.70025`                 | unverified |
| `DuBois1916`       | `10.1001/archinte.1916.00080130010002` | unverified |
| `Dimbylow2002`     | `10.1088/0031-9155/47/16/301`       | unverified |
| `Hirata2021`       | `10.1088/1361-6560/abf1b7`          | unverified |

---

## Edits applied — files touched

- ✅ `papers/how_to_write_good/Robin_writing_style.md` — long S-V-list rule added; `resp.` rule added
- ✅ `papers/how_to_write_good/style_guide.md` — A19 (throat clearing) replaced with a "removed" stub
- ✅ `papers/how_to_write_good/wydaeghe_style_analysis.md` — §0a body first-use override removed; §0a caption rule rewritten; §3.2 rebuilt
- ✅ `papers/TAP_paper/paper.tex` — see status table above for per-comment edits
- ✅ `papers/TAP_paper/paper_SI.tex` — see status table above
- ⚠️ The figure scripts that produce `lit_waterfall_combined.pdf` etc. need to be updated separately so legend strings use `\emph{et al.}` rather than just author names. Will leave a TODO comment in the relevant script.

## Compile check

After this round of edits:

- All semicolons in prose → periods.
- `\IPD_{\max}` → `\IPD_{\mathrm{max}}` everywhere (4 main + 3 SI).
- `et~al.` → `\textit{et~al.}` everywhere (5 main paper occurrences fixed).
- `\emph{et~al.}` → `\textit{et~al.}` (7 occurrences in caption / paragraph) — done.
- `maximises` → `maximizes` (one occurrence in SI).
- `40-110~GHz` → `40--110~GHz`.
- `\sim 30~GHz` → "approximately $30$~GHz".
- All SI cross-references in main paper use the manual `Section~\ref{...}` / `Fig.~\ref{...}` / `Table~\ref{...}` of the SI form.
- `\boxed{}` added to `eq:geom-law` (one box, paper-wide).
