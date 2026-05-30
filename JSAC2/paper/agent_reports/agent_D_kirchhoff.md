# Agent D report: Section IV (UE-anchored Kirchhoff render)

Scope: lines 576-680 of `JSAC2/paper/jsac2_v3.tex`, from `\section{UE-anchored Kirchhoff render of the body channel}` up to the next `\section{Closed-loop calibration ...}`.

Status: All edits applied. The paper compiles (14 pages, no undefined refs, no errors traced to this scope).

---

## 1. Summary of changes

### 1.1 Section opening paragraph (after the section heading)
- Replaced `\bm{r}_p`, `\bm{r}` with the project macros `\rr_p`, `\rr`.
- Killed semicolon, broke into staccato sentences subject-verb-rest.
- Made the figure introduction a stupid-simple Wout-style sentence: "The UE-anchored Kirchhoff render is illustrated in Fig.~3."
- Tied the symbol $\hbody(\thetab,\rr_p)$ explicitly to the prose.

### 1.2 Figure caption
- Switched all hat/vector notations to project macros (`\khat_n`, `\etahat`, `\rr_p`, `\rr`, `\thetab`).
- Replaced semicolon with period.

### 1.3 Bridge paragraph between figure and first subsection
- The original two-step description was a single 50-word top-heavy sentence followed by a 5-word stinger ("The result is a Kirchhoff radiation integral.") in violation of A21.
- Rewrote into three short sentences with subject-verb-rest. The "yielding a Kirchhoff radiation integral" is now folded into the propagation sentence rather than left as a punchline.

### 1.4 Subsection 1: PO surface current (was `\subsection{The PO surface current}`)
- Renamed to `PO surface current and visibility` (drops leading "The" per C11; signals what the subsection actually does — define the current and the visibility flag).
- **Demoted the PO current equation from a numbered display equation to inline math** per the critique item ("we can just use prose then"). The equation is no longer load-bearing for the downstream Kirchhoff integral, since `\mathcal{K}_n` carries the Fresnel reflection through the phenomenological amplitude $K = jk_0 r_0$, not through `\bm{J}`. The visibility flag $V_{nt}$ remains the operative quantity and is now stated as such, with an explicit pointer to the Kirchhoff integral it gates.
- Made the back-face cull condition explicit ($\nhat_t \cdot \khat_n < 0$) instead of vague.
- Killed semicolon. Changed "the work" to a concrete reference. Killed the parenthetical "(back-face cull plus optional ray-mesh self-shadow)" and split into two clean sentences.

### 1.5 Subsection 2: Propagation to the phone
- Removed throat-clearing "The phone is at world position $\rr_p$." (already established earlier and in the figure).
- Replaced bare exponentials `e^{...}` with `\exp(...)` per "operators upright."
- **Standardised vector norm to `\|\cdot\|`** throughout. The Green's function previously mixed `\|\rr-\rr_p\|` in numerator with `|\rr-\rr_p|` in denominator (same vector, two notations). Now both use `\|\cdot\|`. Same fix in the $\etahat$ definition.
- Changed `dA` to `\,\mathrm{d}A` per differential convention.
- Replaced `\hat{\bm{k}}_n` with `\khat_n` macro.
- Changed the lead-in to the integral from "By the Kirchhoff integral, the field arriving at the phone from the body's reflected current is" (which conflates field and channel coefficient) to "The body-mediated channel coefficient then reads" (semantically correct and shorter).
- **Fixed eq.~\eqref{eq:kirchhoff-integral} dimensional inconsistency.** The original wrote `\sum_{j=1}^M [\bm{a}_n]_j \sum_n \int \mathcal{K}_n dA`, which sums out the M-axis index $j$ even though the integrand has no $j$-dependence and $\hbody$ must remain in $\mathbb{C}^M$. New form uses `\sum_n \bm{a}_n \int \mathcal{K}_n d A` (vector multiplication preserves the BS-element axis). This change is forced by dimensional consistency with eq.~\eqref{eq:Lambda-op} and is flagged below for spine review.
- Tightened the prose after the kernel definition: removed semicolon, killed a parenthetical colon, simplified "satisfies the back-face cull ... and is in line of sight" to "satisfy ... and lie in line of sight."

### 1.6 Subsection 3: Discretisation and the Kirchhoff operator
- Heading kept as is (mid-heading "the" is allowed; the leading word is "Discretisation"). Note on spelling at §3 below.
- Replaced "Discretising the integral over the $T_{\mathrm{vis}}$ visible triangles yields the matrix form" with "Replacing each integral over $\Sigma_n^{+}$ by a sum over the $T_{\mathrm{vis}}$ visible triangles yields the matrix form" — same KISS register but the action is named (sum-over-triangles), not just "discretising."
- **Killed `\mathbf{a}_{\mathrm{LOS}}^H` from eq.~\eqref{eq:Lambda-op}.** With $\Lambda \in \Complex^{M \times T_{\mathrm{vis}}}$ and $\bm{1} \in \Reals^{T_{\mathrm{vis}}}$, $\Lambda \bm{1} \in \Complex^M$ already lives in the right space for $\hbody$. Pre-multiplying by $\mathbf{a}_{\mathrm{LOS}}^H$ would collapse to a scalar. The BS-element index is already carried inside the operator via $[\bm{a}_n]_m$ (per the entry definition that follows). Flagged below for spine review.
- Spelled out the role of $\bm{c}_t$ (centroid) and $S_t$ (triangle area), which were previously undefined symbols.
- Replaced the vague summed-over-`paths $n$ landing on $t$' with notation `\sum_{n \to t}` placed inside the entry definition for clarity.
- **Killed the phrase "the central new object of this paper"** as instructed. Replaced with "the central object of the body-channel prediction." Word "new" gone. Phrase "this paper" gone.
- Killed semicolon in the closing sentence about the singular spectrum.

### 1.7 Translation phasor identity remark
- Reframed `\bm{t}` as a "small body displacement" up front (cleaner subject).
- Replaced the awkward phrase "a per-element diagonal phasor sandwich" with "a diagonal phasor matrix on the BS-element axis," which is concrete and names the axis.
- Split the run-on at the end ("lets the per-slot operator refresh under translation cost only one diagonal multiply" — grammatically broken) into two clean sentences.

### 1.8 Closing paragraph (the "Why a UE-anchored render" remnant)
- The original opened with the our-mistake framing: "the phone-on-body geometry has exactly one receiver --- the phone, about 50 cm from the body --- so the backward Kirchhoff render that ... is the appropriate primitive." Per the critique: "we do it this way, period. Cost comparison is not needed."
- **Killed the entire framing sentence.** Kept only the timing line: "The render runs at $\sim$100 ms per pose ... at $T = 20\,908$, $T_{\mathrm{vis}} \sim 10\,000$, and $M = 64$ on the SMPL-X body of Sec.~II."
- Killed both `---` em-dash equivalents in the process.

---

## 2. Item-by-item resolution of applicable critique items

| Critique item | Resolution |
|---|---|
| "are we actually using J = 2 n × H Vnt? ... I think we can just use prose then." | Demoted from numbered display eq. to inline math. Visibility flag $V_{nt}$ is the operative quantity and now drives the prose. |
| "central new object of this paper" — kill "new" and "this paper" | Done in §3 of my scope (line 665). The phrase "central new" still appears at lines 139 and 1360 — flagged for cross-section. |
| Subsection heading "The PO surface current" → drop "The" | Done. Renamed to "PO surface current and visibility" (the visibility role is the actual point of the subsection now that the equation is demoted). |
| "Propagation to the phone" — keep | Kept verbatim. |
| "Discretisation and the Kirchhoff operator" — second "the" mid-heading is fine | Kept. |
| "deliberately compressed / by design" wording | Not present in my scope. |
| Fig 3 introduced before it appears, stupid-simple sentence | Done. The first sentence of the section is now: "The UE-anchored Kirchhoff render is illustrated in Fig.~3." Then a Wout-style minimum-decoration unpacking of the geometry. |
| "Why a UE-anchored render: a complexity argument" subsection | This subsection heading does not exist in v3 (already deleted by an earlier pass). The our-mistake-framing remnant survived in the closing paragraph of my scope (lines 671-677). Killed. |
| No questions in headings or prose | Verified. None in my scope. |

---

## 3. Math notation harmonisations

- `\bm{r}_p`, `\bm{r}`, `\bm{\theta}` → `\rr_p`, `\rr`, `\thetab` (project macros).
- `\hat{\bm{k}}_n`, `\hat{\bm{\eta}}` → `\khat_n`, `\etahat` (project macros).
- `e^{...}` → `\exp(...)` for both the Green's function phase and the BS-arrival phase.
- `dA` → `\,\mathrm{d}A`.
- Vector norms: standardised to `\|\cdot\|` everywhere in the Green's function, the $\etahat$ definition, and consequence prose. Mixed `\|...\|` numerator + `|...|` denominator on the same vector eliminated.
- Equation-end punctuation: every display equation now ends with `\,.` or `\,,` per IEEE convention (item 9 / item 30 of the LaTeX rules). Previously eq.~\eqref{eq:kirchhoff-integral} ended with a bare comma without thin space; eq.~\eqref{eq:Lambda-op} ended with bare comma — now both have `\,.` / `\,,`.
- Centroid `\bm{c}_t` and area `S_t` are now defined inline in the operator description (previously appeared in eq.~\eqref{eq:Lambda-op} without prose definition).

---

## 4. Style fix counts within my scope

- `---` em-dash equivalents removed: 2 (both in the closing paragraph).
- Semicolons in body prose removed: 4 (section opener, PO subsection, Discretisation subsection, Kirchhoff-operator description).
- `\bm{r}_p` / `\bm{r}` legacy spellings replaced: 6 instances (caption + opening + remarks).
- `e^{...}` exponentials promoted to `\exp(...)`: 2.
- Numbered equations: 4 → 3 (PO current demoted).
- Subsection headings starting with "The": 1 fixed (`The PO surface current` → `PO surface current and visibility`).
- 5-word stingers after long sentences (A21): 1 fixed (`The result is a Kirchhoff radiation integral.` folded into preceding sentence).
- Top-heavy / verb-buried sentences split: 3 (the bridge paragraph; the "By the Kirchhoff integral, the field arriving ..." lead-in; the closing "phone-on-body has exactly one receiver ... is the appropriate primitive" sentence — last one was killed entirely).

---

## 5. Cross-section flags for the audit

The following items lie OUTSIDE my line range and I did not touch them. Forwarding for the right agent / spine custodian.

1. **"central new" still appears at lines 139 and 1360** of `jsac2_v3.tex`:
   - Line 139: "The central new primitive is a UE-anchored Kirchhoff" (intro/contributions).
   - Line 1360: "The central new computational primitive is a UE-anchored Kirchhoff" (discussion).
   The word "new" must be killed in both. Both are out of my scope (Agents A and H respectively).

2. **British vs American spelling drift.** My section uses `Discretisation` and `Discretising`; the doc also has `parametrisation` (line 725, in §V), `polarisation` (5+ uses across §III), `factorisation` (lines 568, 571, in §III). The latex_rules document mandates American (`Discretization`, `polarization`) for IEEE house style, but the project habit across all sister papers is British. **Recommendation**: pick one convention and apply globally. I left British in my section to stay consistent with the rest. This is a project-wide decision, not a per-section call.

3. **Eq.~\eqref{eq:kirchhoff-integral} dimensional fix.** I changed `\sum_{j=1}^M [\bm{a}_n]_j \sum_n \int \ldots` to `\sum_n \bm{a}_n \int \ldots` because the original collapses the BS-element axis incorrectly. The new form is dimensionally consistent with eq.~\eqref{eq:Lambda-op} and with $\hbody \in \Complex^M$. **Spine custodian, please verify** that this matches the authors' intent. If the original was meant to express something other than the BS-vector channel, the per-element steering convention may need to be redefined upstream in §III.

4. **Eq.~\eqref{eq:Lambda-op} dimensional fix.** I removed `\mathbf{a}_{\mathrm{LOS}}^H` from the LHS multiplier; the operator already carries the BS-element index via $[\bm{a}_n]_m$ in its $(m,t)$ entry. Same flag — please verify with the spine.

5. **Symbol `\beta_n` in the operator entry.** Defined elsewhere as the per-path amplitude calibration coefficient (line 85 macro `\betab`, prose at line 385: "per-path amplitude calibration $\betab$ runs ..."). Confirmed consistent.

6. **Forward reference in section opener.** The section opener uses $\mathcal{K}_n(\rr;\rr_p)$ before the kernel is formally defined in eq.~\eqref{eq:kernel}. This is intentional: the figure introduction is a roadmap. Acceptable per Wout's "stupid simple intro sentence" pattern. No fix.

---

## 6. Open issues

- **Figure 3 itself**: out of my scope (separate `figures/fig_kirchhoff_schematic.pdf`). The user has already iterated on environment blocks and font sizes. Caption updated to project macros only.
- **The PO current equation demotion**: I demoted to inline. If a reviewer feels the PO formula deserves a numbered equation as documentation of the underlying physics, the alternative is to keep the display equation but add a sentence like "Equation~(13) is shown for completeness; the Kirchhoff render below uses the phenomenological amplitude $K = jk_0 r_0$ in place of the explicit current." Preferred (per Robin's critique): leave demoted.
- **Sentence "The operator $\Lambda_{\mathrm{KH}}$ is the central object of the body-channel prediction."** I dropped "new" and "this paper." If an even cleaner phrasing is desired, e.g. "The operator $\Lambda_{\mathrm{KH}}$ carries the full pose-dependence of the body-mediated channel," the latter is also defensible (and was in the original prose). I kept "central object" because the spine sentence is explicitly load-bearing per the critique. Editor's call.

---

## 7. Compile verification

`cd JSAC2/paper && pdflatex -interaction=nonstopmode jsac2_v3.tex` succeeds. 14 pages out, all references resolved, no errors traceable to my scope. The only Overfull \hbox warnings during the run are in the IEEE journal banner header and on pages outside §IV; none originate in my range. The `\eqref{eq:kirchhoff-integral}` cross-reference in line 619 (the new prose pointer in §IV.A) resolves correctly to (14).
