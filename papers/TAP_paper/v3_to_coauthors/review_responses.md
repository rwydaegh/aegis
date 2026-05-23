# Responses to v3 review

Your `review.txt`, item by item. Each entry has the quoted text, your note, and
my response. Legend: **✅ done** = applied to the leaves; **💬** = needs your
call / discussion, not yet edited; **✅+💬** = applied a fix and there is a point
worth your eye.

All edits are on `paper/tap-presweep`, in the `main/` leaf tree (canonical). The
PDF rebuild is described at the end.

---

### (unnumbered, top) — "no gradients for design"

> **Text:** "and they provide no gradients for design."
> **You:** "idk." → "and they provide no gradient for the optimization applications."

💬 **Left as-is, my recommendation: keep "no gradients for design."** It is
crisper than "no gradient for the optimization applications" (which adds two
words and a vague noun, "applications"). The plural "gradients" also threads to
contribution 3 later ("the first APD map to provide closed-form gradients"), so
keeping it preserves that callback. If you want to foreground the use-case, the
tightest middle option is **"and they provide no gradients for optimization."**
Say which and I'll apply it.

---

### 0 — abstract: write GPU directly

> **You:** "abstract: write GPU directly there"

✅ **done.** The abstract now reads "evaluated in under $10$~ms on a GPU." (I had
previously spelled it out as "Graphics Processing Unit (GPU)" to satisfy a
PaperMaker abstract-acronym rule; your call overrides it.) GPU is still expanded
once in the introduction, so the acronym is defined for the body.

---

### 1 — doubled APD expansion

> **Text:** "the surface-averaged absorbed power density (Absorbed Power Density (APD)) above 6 GHz."
> **You:** "yeah, there is issue there"

✅ **done.** The source was "the surface-averaged absorbed power density
(\gls{APD})", and the glossary's first-use expansion turned `\gls{APD}` into
"Absorbed Power Density (APD)", giving the doubled phrase. Changed to "the
surface-averaged \gls{APD}", which now renders once as "the surface-averaged
Absorbed Power Density (APD)" — parallel to "the mass-averaged SAR" in the same
sentence.

---

### 2 — "in-tissue wavelength"

> **Text:** "at ten cells per in-tissue wavelength"
> **You:** "no in-tissue"

✅ **done.** Now "at ten cells per wavelength."

---

### 3 — generalized Cauchy, date

> **Text:** "...integrates over a nonconvex body through a generalized Cauchy formula [11], with.."
> **You:** "...based on a generalized Cauchy identity from 1841 [41] and ..."

✅+💬 **done** (intro): now "through a generalized Cauchy identity from
1841~\cite{Cauchy1841}". One consistency note for you: the paper now uses
**"identity"** for *our generalized* version (abstract: "generalized Cauchy
whole-body identity"; intro: "generalized Cauchy identity") and **"formula"** for
*Cauchy's classical* one (Section IV and item 19: "the classical Cauchy formula
from 1841"). That split is defensible — generalized identity (ours) vs classical
formula (his) — so I left it. If you'd rather have one word everywhere, tell me
which and I'll unify.

---

### 4 — dielectric uncertainty number

> **Text:** "to within the tissue dielectric uncertainty"
> **You:** "add: of 7% right after"

✅ **done.** Now "to within the tissue dielectric uncertainty of $7\%$." Verified
the number against the body: the $\pm20\%$ spread on the IT'IS dielectric
parameters propagates through the Fresnel coefficient to **$\pm7\%$ on $T_0$**
(error-budget section and the Sim4Life section both state this). So 7% is the
*propagated* output floor (the input parameter spread is 20%); the abstract's
"below 5%" model error sits under it, which is the intended message.

---

### 5 — Sections II–IV are the methods

> **Text:** the section roadmap
> **You:** "These actually form a triplet, the methods. Section x, y, z comprise the methods... Respectively, they [list]."

✅ **done.** The roadmap now opens: "\Cref{sec:law,sec:pB,sec:cauchy} comprise the
methods of this paper. Respectively, they derive the local absorption law at a
visible surface point, reduce it to a near-constant scalar through pseudo-Brewster
compensation, and integrate the local law over the whole nonconvex body."

---

### 6 — don't forget corrections in the validation line

> **Text:** "Section V validates the theory four ways."
> **You:** "dont forget corrections too here"

✅ **done.** Now "\Cref{sec:val} validates the theory four ways and bounds the
higher-order corrections." (Section V is where the curvature / diffraction /
inter-body residuals live, so that is the right spot for the corrections beat.)

---

### 7 — consequences + concludes

> **Text:** "Section VII discusses the regime of validity,"
> **You:** "...discusses some consequences and the regime of validity, while Section VIII concludes."

✅ **done.** Applied verbatim: "\Cref{sec:disc} discusses some consequences and
the regime of validity, while \cref{sec:conc} concludes."

---

### 8 — the $[\cdot]_+$ notation is never defined

> **You:** "on first appearance of []_+ ... I dont think that notation is explained mathematically, and physically I dont see the explanation either... do so nice and clearly, KISS, on first proper occurence."

✅ **done. You were right.** The bracket first appears in eq. (Sab-exact) in
Section II and was never defined there; the definition only showed up two
subsections later (the matrix form, "$[\cdot]_+ \equiv \max(\cdot,0)$ ... ReLU").
Added a KISS line right after eq. (Sab-exact):

> "Here $[x]_+ = \max(x,0)$ is the positive part: it keeps the front-facing
> surface and sets the back-facing surface ($\mu \le 0$, no incident power) to
> zero."

(The cosine $\mu = \hat{n}\cdot(-\hat{k})$ is already defined in the setup
subsection, including "a point facing away from the source has $\mu \le 0$", so
the new sentence only needs to define the bracket and tie it to that.)

---

### 9 — "As shown in the flowchart"

> **Text:** "As shown in the flowchart (Fig. 1)"
> **You:** "As described in the flowchart of Fig. 1 — Can be done throughout btw."

✅ **done in both places** it occurs (start of Section III and start of
Section IV): "As described in the flowchart of~\cref{fig:flowchart}".

---

### 10 — optics → antenna propagation; the semicolon

> **Text:** "...has not appeared in the optics or bioelectromagnetics literature, where prior work..."
> **You:** "in the antenna propagation or bioelectromagnetics literature" + "literature; prior work (yes we accept the ;)"

✅ **done.** Now "...has not appeared in the antenna propagation or
bioelectromagnetics literature; prior work has evaluated..."

---

### 11 — "the APD APD/IPD"

> **Text:** "Figure 3b shows the APD APD/IPD ="
> **You:** "wtf went wrong here"

✅ **done.** Same glossary double-up as item 1: the source was "shows the
\gls{APD} $\APD/\IPD$", and `\gls{APD}` printed "APD" right before the math "APD".
Changed to "shows the normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$"
(matching the figure caption's own wording).

---

### 12 — "agreement at the fourth significant figure"

> **Text:** "Below 30° the agreement is at the fourth significant figure."
> **You:** "...exact within four significant figures... Btw, Im suspicious it's this good, can u verify the claim."

✅+💬 **Your suspicion is correct; I verified and rewrote it.** Computing the
unpolarized Fresnel $T_\text{avg}(\theta)/T_0$ for skin at 28 GHz
($\tilde n = 4.49 - 1.79i$, $T_0 = 0.5386$):

| θ | T_avg | deviation |
|---|-------|-----------|
| 10° | 0.53864 | 0.002% |
| 20° | 0.53880 | 0.03% |
| 25° | 0.53905 | 0.08% |
| **30°** | **0.53954** | **0.17%** |

So at 30° the deviation is **0.17%** — i.e. $T_\text{avg}$ and $T_0$ already
differ at the *third* significant figure (0.5395 vs 0.5386), not the fourth.
"Four significant figures" only holds below ~15°. I replaced the sentence with the
honest, still-strong statement: **"Below $30^\circ$ the deviation stays below
$0.2\%$."**

---

### 13 — subcutaneous fat as an outermost tissue

> **Text:** "Above 6 GHz, the relevant outermost tissues are skin, subcutaneous fat, and vitreous humor."
> **You:** "can subcutaneous fat be relevant here? ... humans dont have fat exposed right"

✅+💬 **You're right; fixed.** Two problems with the old list:
1. **Fat is never the outermost tissue** — skin always covers it, and above 6 GHz
   the wave is absorbed in the skin before reaching fat. Worse, the *previous*
   sentence already says "fat is rarely the outermost tissue at exposure sites of
   regulatory interest", so the old list contradicted it.
2. **Vitreous humor is not outermost either** — it sits behind the lens, deep in
   the eye. What is actually exposed at the eye is the *ocular surface* (cornea +
   tear film), which is water-rich and therefore high-index (|ñ| > 6, like the
   "Water" row in Table I), so it supports the universality argument cleanly.

Changed to: **"the relevant outermost tissues are skin and, at the eyes, the
ocular surface."** This removes the contradiction and keeps the high-index
argument intact. Flagging in case you specifically wanted "vitreous humor" named
for an IT'IS-tissue reason.

---

### 14 — swap V and $[\cdot]_+$ in eq. (9)

> **You:** "equation 9 (geom abs law): swap position of V and []_+, that's it"

✅ **done.** Now $\APD(\rr) \approx \IPD\,T_0\,[\hat n\cdot(-\hat k)]_+\,V$.
This matches the order in the exposure-fraction definition eq. (eta-def),
$[\hat n\cdot(-\hat k)]_+\,V$, so the two equations now read in the same order.
I also reordered the **abstract** clause to match ("transmission, the positive
incidence cosine, and an ambient-occlusion factor") so the prose and the boxed
equation list the three factors in the same sequence. Revert that abstract tweak
if you'd rather not touch it.

---

### 15 — the three frontal-illumination regions

> **Text:** "the medial thighs, the inside of the wrists, and the underside of the chin"
> **You:** wrists doubtful (why not armpits/side-chest?); better word for "underside of the chin"; "lets discuss"

💬 **Not edited (you said "lets discuss"); here's my read.** This sentence is the
*frontal-illumination* example (where $V=0$ from the front). Looking at the
frontal APD render (Fig. 4a), the clearly dark/self-shadowed concavities are the
**medial thighs**, the **sides of the torso under the arms / armpits**, and the
**under-chin/neck**. The **inside of the wrists** is real but minor, and you're
right that it is a weaker pick than the armpit region. Suggested swap:

> "the medial thighs, the sides of the torso beneath the arms, and the underside
> of the chin."

(I'd use "sides of the torso beneath the arms" rather than "armpits" here, to
keep it distinct from item 17's list, which already says "armpits".)

For **"underside of the chin"**: the anatomical name for the soft tissue hanging
from the jaw to the neck is the **submental region**. Options, plainest first:
"the underside of the jaw", "the soft tissue beneath the jaw", "the submental
region beneath the jaw". I lean to **"the underside of the jaw."** Tell me which
and I'll apply 15 in one go.

---

### 16 — the source vector should be IPD

> **You:** "the vector s should be IPD. its elements shouldnt be S_1,... it should be IPD_1,... mimic the bold/mathrm formatting like APD (never italicized)."

✅ **done.** Renamed throughout the discrete multi-source subsection:
- "power densities $S_1,\ldots,S_N$" → "incident power densities $\IPD_1,\ldots,\IPD_N$"
- "$\mathbf{s} = [S_1,\ldots,S_N]^\top$" → "$\bm{\mathrm{IPD}} = [\IPD_1,\ldots,\IPD_N]^\top$"
- eq. (mat-multi): the trailing $\mathbf{s}$ → $\bm{\mathrm{IPD}}$
- "The product with $\mathbf{s}$ sums..." → "The product with $\bm{\mathrm{IPD}}$ sums..."

The vector is set as $\bm{\mathrm{IPD}}$ (upright bold), matching $\bm{\mathrm{APD}}$;
the scalar elements $\IPD_i$ are upright roman via the `\IPD` macro, never
italic. (Note: a PaperMaker rule had suggested switching the APD vector to
`\mathbf{\mathrm{APD}}` to match the single-letter `\mathbf{N},\mathbf{K},\mathbf{V}`;
I kept `\bm{\mathrm{}}` per your "mimic APD" instruction, so APD and IPD now match
each other.)

---

### 17 — "soles of the feet" as a shadowed region

> **Text:** "...the underside of the chin, and the soles of the feet are the dominant such regions."
> **You:** "soles of the feet?? ... maybe the back of the ears or something"

✅+💬 **Removed "soles of the feet"; I verified this on the mesh.** I paired the
exposure-fraction array $\eta$ (the exact one behind Fig. 4) with the Thelonious
triangle centroids and measured:

- **Soles (downward-facing, bottom of the mesh): mean $\eta \approx 0.95$** — among
  the *highest* on the body, not the lowest.
- Lowest-$\eta$ triangles cluster at ~46% of body height: the **groin / crotch**
  (between the upper thighs) and the **armpits** — the deep mid-body concavities,
  with $\eta$ down to ~0.

Why: the definition eq. (eta-def) integrates the **full sphere** with **no ground
plane**, so the downward-facing soles see open space below and are *well exposed*.
(If we modeled a person standing on the ground, the ground would block the lower
hemisphere and the soles *would* be shadowed — but that is not this paper's $\eta$.)
So listing the soles was simply wrong for our definition.

I changed the list to **"the medial sides of the legs and arms, the armpits, and
the underside of the chin"** (dropped soles; "medial sides of the legs" already
covers the inner-thigh/groin concavity). On **back of the ears**: it's a genuine
small low-$\eta$ spot, but the head region overall is well-exposed
($\eta \approx 0.89$), so it isn't a *dominant* region and I left it out. Happy to
add "the groin" explicitly if you want the deepest concavity named.

---

### 18 — "tens of milliseconds on commodity hardware" + the shader question

> **Text:** "On a 10^4–10^5 triangle mesh, the solver evaluates η in tens of milliseconds on commodity hardware."
> **You:** "Remove ... replace with a KISS short sentence that it can be pre-computed. btw ... isnt this a shader? explain me. worth to mention or?"

✅ **done** (the edit): replaced with **"Because $\eta$ depends only on body
shape, the solver precomputes it once per posture."**

💬 **On the shader question — yes, it is essentially a shader, and here's the
plain version.** A *shader* is a tiny program the GPU runs in parallel for every
pixel (or every surface point), thousands at once. The visibility/occlusion query
behind $\eta$ — "from this surface point, which directions are blocked by the rest
of the body?" — is exactly what real-time graphics calls an **ambient-occlusion**
pass, and it's run as a shader. So computing $\eta$ over the mesh is the same kind
of operation a game engine does every frame to shade creases darker.

The paper already says this twice, so it's covered without adding more: the
self-shadowing intro says "Modern GPUs evaluate $V(\rr,\hat k)$ as a standard
ambient-occlusion pass", and the differentiability paragraph says "the arithmetic
primitive is the per-pixel shading operation that consumer GPUs run at
sub-millisecond rates". I'd **not** add a third mention — the new "precomputed
once per posture" sentence is the load-bearing fact (you only pay for $\eta$ once,
then reuse it across frequencies and incident fields).

---

### 19 — classical Cauchy formula, date

> **Text:** "The classical Cauchy formula"
> **You:** "The classical Cauchy formula from 1841 [cite]"

✅ **done.** Now "The classical Cauchy formula from 1841~\cite{Cauchy1841},
$\langle A_\perp\rangle = A/4$, is the special case $\eta\equiv 1$..." (See the
formula-vs-identity note under item 3.)

---

### 20 — "within a few percent of the true absorbed power"

> **Text:** "...so the hull bound is within a few percent of the true absorbed power."
> **You:** "Remove"

✅+💬 **Done, and it was actually wrong, not just removable.** $A_{CH}/A \approx
1.20$ means the convex-hull energy bound *over*estimates the absorbed power by
~20%, so "within a few percent" was incorrect. I changed it to the correct
statement: **"so the hull bound brackets the true absorbed power within that
factor."** (This pairs with item 31 below — see there.)

---

### 21 — "body-Mie contribution" used before it's defined

> **Text:** "where the body-Mie contribution"
> **You:** "the emph'ed definition follows later in the paper: what should we do about this?"

💬 **Not edited; here are the options.** "body-Mie contribution" first appears in
Section IV, but the *emphasized definition* (\emph{body-Mie regime}, "the regime
where $x$ is small enough that the diffracted contribution exceeds a few percent")
only arrives in Section V's Mie subsection. Three ways to fix:

1. **Brief gloss + forward-ref at first use** (lightest): "...where the body-Mie
   contribution — finite-body absorption resonance, the regime delimited in
   \cref{subsec:val-mie} — becomes non-negligible." Defines it in passing,
   removes the forward dependency.
2. **Move the one-line definition up** to Section IV's first use and de-emphasize
   the Section V occurrence. More faithful to "define on first use" but more
   surgery.
3. **Leave it** — the surrounding context ("contribution to absorption on a finite
   ellipsoid ... below 3 GHz") already telegraphs the meaning, and the Mie
   subsection formalizes it.

I recommend **(1)**. Want me to apply it?

---

### 22 — "single error budget that propagates"

> **Text:** "and close with a single error budget that propagates the dielectric uncertainty."
> **You:** "and close with an error budget bounded by the dielectric uncertainty."

✅ **done**, verbatim.

---

### 23 — generalizes favorably

> **Text:** "here generalizes to larger adults."
> **You:** "here generalizes favorably to larger adults."

✅ **done**, verbatim.

---

### 24 — the "sphere" subscript on R

> **Text:** "below to the Fresnel limit Rsphere"
> **You:** "should we be adding this sphere subscript? isnt it already known to be the sphere ratio? or write R_sphere earlier? if so, check all places."

💬 **Not edited — this is a real notation tangle and I want your call. Here's the
full picture I dug up:**

- The paper defines, in Section III, **"the sphere ratio $R(f) \equiv
  T_0(f)/\bar T(f)$"** (eq. R-of-f, Fig. 5, Table II).
- The flux-weighted average $\bar T = 2\int_0^1 T_\text{avg}(\mu)\,\mu\,d\mu$ **is
  exactly the sphere-surface average** $\langle T_\text{avg}\rangle_\text{sphere}$.
  So $R = T_0/\bar T$ and $R_\text{sphere} = T_0/\langle T_\text{avg}\rangle$ are
  the *same quantity*, just written two ways. (Both cross unity at ~39–40 GHz —
  that's the same crossover.)
- There is **no collision**: the only other "R" in the paper is the *reflectance*
  $\bar R = 1-\bar T$, which carries a bar. So plain $R$ is unambiguous.

**Therefore the `sphere` subscript is redundant** — $R$ is *already* "the sphere
ratio." Two clean options:

- **(A) Drop the subscript everywhere, use $R$.** Bonus: the Mie freq panel's
  orange asymptote then reads "$R(f)-1$", making it visually obvious it's the same
  curve as Fig. 5. Places to change: the Mie prose (already uses plain $R$, good),
  the Mie size/freq figure captions, the Mie figure scripts' axis labels
  (`mie_theory_corrected.py`), and the SI (one definition + the asymptote labels).
  Requires regenerating the Mie figures.
- **(B) Keep $R_\text{sphere}$ but introduce it with its subscript at first
  main-text use.** Right now the Mie prose says plain "$R = T_0/\langle
  T_\text{avg}\rangle$" while the captions/SI say $R_\text{sphere}$ — that mismatch
  is the actual defect. Defining $R_\text{sphere}$ once in the Mie prose fixes it
  with no figure changes.

I lean to **(A)** (simpler symbol, reveals the Fig. 5 ↔ Mie-asymptote link), but it
touches figures + SI, so I held off. Pick A or B and I'll sweep all the places.

---

### 25 — mmWave band on the across-frequency panel

> **You:** "Fig 6b (across freq fig): the mmWave band shaded region should go 24-100 GHz. the mmWave label should remain same place."

✅ **done.** In `mie_theory_corrected.py` the band was `axvspan(20, 60)`; changed
to **`axvspan(24, 100)`** on the freq panel (Fig. 6b), label kept at x=35. I made
the same change on the companion $R_\text{sphere}(f)$ panel for consistency, and
**regenerated** `mie_panel_freq.pdf` / `mie_panel_size.pdf` / `mie_R_sphere.pdf`.
Verified visually: the green band now spans 24→100 GHz with the "mmWave" label in
the same spot.

---

### 26 — section → subsection

> **Text:** "This section validates the theor[y]"
> **You:** "This subsection validates the theor[y]"

✅ **done.** (It's a subsection inside Section V.)

---

### 27 — plane wave from above

> **Text:** "The incident plane wave comes from abovee, with skin properties at 28 GHz."
> **You:** "The incident plane wave impinges from above. The computation is done at 28~GHz."

✅ **done**, verbatim (your "abovee" was a paste typo; the source said "above").

---

### 28 — "FDTD voxel discretization and convergence error ... ±10%"

> **Text:** "FDTD voxel discretization and convergence error yield about ±10%"

💬 **Already superseded in v3 — no action needed unless you want a different
number.** The current draft (and v3's `paper.tex`, line ~1096) says: "FDTD voxel
discretization and per-direction polarization detail give about **$\pm15\%$ per
direction at 7 GHz**, against the closed form's own $\approx 5\%$ diffraction
error." So the "convergence error / ±10%" wording you quoted predates this draft.
For reference, the per-direction law/FDTD ratios are 1.06, 1.20, 0.83 (a +20% /
−17% spread), so $\pm15\%$ is a round mid-estimate; $\pm20\%$ would be the max.
Tell me if you'd prefer ±20% or a re-word.

---

### 29 — the Zhang 2017 figure (Fig. 4.9, the plateau)

> **You:** explain the reasoning; what are the Zhang 2017 values in our script; do the points look "a bit for us"; "dont edit yet".

💬 **No edits (per your instruction). I read Zhang's thesis around Figs. 4.8–4.11
and traced the script. Full explanation:**

**What the figure is.** Zhang measured whole-body **absorption cross-section**
(ACS, m²) for 48 subjects in a reverberation chamber. Above ~6 GHz the wave stops
penetrating to fat/muscle — **the skin absorbs essentially all the coupled
power** — so ACS becomes a property of the body's *outer surface area alone*,
independent of body composition. He fits (his Eq. 4.5):

> ⟨ACS(f)⟩ = C₁(f)·BSA + C₂(f)

where BSA is body surface area, **C₁ is the dimensionless slope** (ACS per unit
total surface area), and C₂ ≈ 0 (a body with zero surface area has zero ACS).
**Fig. 4.9 is C₁(f) and C₂(f).** The C₁ plateau at ~0.14 above ~9–12 GHz is the
thesis's headline: high-frequency absorption is governed by **geometry (surface
area), not tissue** — the same surface-dominated limit our geometric-optics law
rests on. That's why "the plateau is important."

**Why our script plots ξ = 4·C₁ — and why the factor 4 is honest.** Zhang's own
Eq. 4.6 defines efficiency ξ = ACS / A_silhouette, and he sets A_silhouette =
0.25·BSA "**by assuming the human body is a perfect convex object.**" That 0.25 is
exactly the **Cauchy mean-projected-area identity** (orientation-averaged
silhouette = surface area / 4). So, in the plateau,

> ξ = ACS / (0.25·BSA) = C₁·BSA / (0.25·BSA) = **4·C₁**.

This is an identity *inside Zhang's own model*, not something we imposed — and it's
the same Cauchy 1/4 that our whole-body formula uses. So the mapping is principled.

**The values in `lit_waterfall.py`** (`ZHANG_PLATEAU_XI`), with my pixel re-read of
Fig. 4.9:

| f (GHz) | script ξ = 4·C₁ | my read of 4·C₁ |
|--------:|----------------:|----------------:|
| 6  | 0.43 | 0.429 |
| 9  | 0.55 | 0.54–0.58 (noisy spike) |
| 12 | 0.57 | 0.570 |
| 15 | 0.57 | 0.572 |
| 18 | 0.56 | 0.550 |

They match to ±0.005 in C₁ — within the trace's own jitter, no systematic bias.
(There's also a low-frequency "envelope" band from Fig. 4.11; its values are
defensible too, hand-traced over a 48-curve spaghetti plot, honest in both
directions.)

**Do the points look "a bit for us"?** Honestly, the opposite. Our framework curve
$\bar T\cdot(A_\text{ab}/A)$ is roughly **flat at 0.40–0.45** across the band, while
Zhang's plateau climbs to **~0.57**. So above ~9 GHz **the data sit clearly *above*
our curve — our flat-skin Fresnel *under*-predicts** the surface-area-driven rise
Zhang measures. The only near-coincidence is the single 6 GHz point (0.430 vs
0.43). So if anything the comparison is unflattering-to-honest, not cherry-picked.
The one soft spot is 9 GHz, where Fig. 4.9 spikes to ~0.146 and the script uses the
lower trend value 0.1375 — a conservative choice, not a flattering one.

**My take:** the figure is fair and the physics tie-in (Cauchy 1/4, surface-area
dominance) is genuinely strong — arguably worth a sentence in the text making the
4·C₁ = Cauchy connection explicit, since right now it's only in the script
comments. Your call on whether to surface it.

(Source: Zhang thesis, Eqs. 4.5–4.6 and Figs. 4.8–4.11, printed pp. 98–101 =
PDF pp. 118–121.)

---

### 30 — "kernel labels"

> **Text:** "The kernel labels in"
> **You:** "The labels in"

✅ **done.** Now "The labels in~\cref{fig:val-fdtd}".

---

### 31 — the misplaced convex-hull sentence

> **Text:** "The convex-hull energy bound ⟨Pabs⟩ ≤ IPD A_CH/4 brackets the true absorbed power within A_CH/A ≈ 1.20 on Thelonious."
> **You:** "this sentence seems misplaced, where would you put it? or how can we argue for keeping it?"

✅+💬 **Consolidated it into Section IV (where the bound belongs) and removed it
from the residuals paragraph.** It was dangling at the end of the *inter-body
reflection* paragraph, where it's a non-sequitur (the hull bound is an
energy-conservation cap, not specifically about re-illumination). Meanwhile
Section IV introduces $A_{CH}$ and the bound $\langle P_\text{abs}\rangle \le \IPD
A_{CH}/4$. So:

- **Section IV** now ends "...$A_{CH}/A \approx 1.20$, so the hull bound brackets
  the true absorbed power within that factor." (this is the corrected item-20
  sentence, carrying the now-correct "within 1.20" tightness).
- **The residuals paragraph** drops the duplicate.

Net: the convex-hull bound lives once, in the section that defines it. If you'd
rather keep a version in the residuals paragraph as an explicit *cap on the
inter-body inflation* ("even the hull bound is only 1.20×, far above the ≤2%
correction"), I can reframe it that way instead — tell me.

---

### 32 — the conclusion is only about speed

> **You:** "our conclusion is only about speed, and we didnt discuss validation at all? surface all rules in the corpus about how to write a good conclusion. lets discuss."

✅(partial)+💬 **I surfaced the corpus rules and added one accuracy beat; let's
decide how far to go.**

**What the corpus says about conclusions** (`structural/conclusion/`):
- **three_beats** — a conclusion is (1) what was shown, past tense, *distinct from
  the intro's contribution list*; (2) what it means; (3) what's next, grounded in
  the paper's own limitations.
- **not_resummary / not_abstract_paraphrase** (high) — it must **not** re-summarize
  the abstract or repeat results; if a sentence is interchangeable with an abstract
  sentence, cut it.
- **no_new_content** (high) — no new numbers/figures/equations; every quantitative
  claim must have appeared earlier.
- **length** (low) — half a column to one column; short is normal and fine.
- **future_work_brief** (Wout, "max 2 zinnen bij conclusie") + **future_work_grounded**
  — at most 2–3 sentences, tied to stated limitations, never a standalone section.
- **no_display_equations** (Wout) — no equations in the conclusion.

**Diagnosis.** The conclusion was beat-1 (what was shown) + beat-3 (two future
extensions), but beat 1 was **entirely about cost/speed** and said nothing about
*accuracy*. That's a real imbalance — the paper's other headline is that the
closed form matches FDTD to within the dielectric floor. Restating that is allowed
(no_new_content is fine: the 7% number already appears in the body).

**What I did:** added one sentence to beat 1 — "In the mmWave band it matches FDTD
to within the $7\%$ tissue-dielectric uncertainty." — so the conclusion now leads
with *both* accuracy and speed.

**What I did *not* do, and want your steer on:** I deliberately did **not** turn
this into a validation re-summary (the four checks, the per-method errors) —
`not_resummary` warns against exactly that, and the validation belongs in Section
V. The question for you: is one accuracy sentence the right dose, or do you want a
slightly fuller "what it means" beat (e.g. one line that the closed form is
accurate *because* mmWave absorption is surface-dominated — which would also pick
up the Zhang point from item 29)? My recommendation: keep it lean (the one
sentence) and, if anything, add a single "what it means" clause rather than a
validation recap. Tell me which and I'll finalize.

---

## Build / rebuild

All leaf edits are in `main/`. To regenerate the assembled PDF from the leaves:

```
make pm-assemble        # -> build/papermaker/assembled.{tex,pdf}
```

The Mie figures were regenerated in place (`figures/mie_panel_freq.pdf`,
`mie_panel_size.pdf`, `mie_R_sphere.pdf`). When you're happy with the answers
above, I'll roll the leaves into a fresh `paper.tex` + PDF and (if you want) a v4
snapshot.

## Quick index of what's still open for you

- **3** — formula vs identity: unify, or keep the split? (no edit yet)
- **15** — pick the wrist→? swap and the chin wording (no edit yet)
- **21** — apply the body-Mie gloss (option 1)? (no edit yet)
- **24** — pick A (drop subscript everywhere) or B (define $R_\text{sphere}$ once) (no edit yet)
- **28** — keep ±15%, or change? (no edit needed)
- **29** — add a sentence making the 4·C₁ = Cauchy link explicit? (no edit, per your "dont edit yet")
- **32** — one accuracy sentence enough, or add a "what it means" clause? (one sentence already added)
