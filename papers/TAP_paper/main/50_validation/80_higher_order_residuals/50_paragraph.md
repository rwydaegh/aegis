% PREV: Finally, we study the impact of inter-body reflections.
% NEXT: <!-- AUTO_BEGIN: assembled -->
Two effects keep the body-averaged correction small. First, the bound
$f \le 1 - \eta$ self-compensates: deep concavities ($\eta$ low) have
a high recapture fraction ($f$ high), so the product $\eta\cdot C$
varies much less than $\eta$ alone. Second, specular reflection at
mmWave (skin meets the Rayleigh roughness criterion) reduces $f$ by
roughly a factor of three relative to the diffuse bound. On the
Thelonious phantom at $28$~GHz, the area-weighted recapture fraction is
$f_{\mathrm{global}} \approx 0.09$ under the diffuse bound, giving
$C \approx 1.04$. The specular estimate brings this to
$C \approx 1.01$. The body-averaged correction stays below $2\%$,
smaller than the propagated dielectric uncertainty derived in
\cref{subsec:corr-summary}. The convex-hull energy bound
$\langle P_{\mathrm{abs}}\rangle \le \IPD\,A_{\mathrm{CH}}/4$
brackets the true absorbed power within
$A_{\mathrm{CH}}/A \approx 1.20$ on Thelonious.

## reviews (paragraph)


_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.anti_ai_language.first_second_third_overuse`: Single First/Second pair for two genuinely distinct physical effects; the rule explicitly permits one enumerated use, and there is no third item or listicle padding.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: The reference is mid-sentence (object of 'derived in'), not sentence-initial, so lowercase \cref correctly renders 'subsection X'.
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: Each \approx sits inside a full inline math expression with a variable, not floating in prose; this is the correct math-mode use, consistent with the rest of the paper.

