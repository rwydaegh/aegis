# Agent C report: Section III "RIHB physics"

Scope: `JSAC2/paper/jsac2_v3.tex`, lines 404-555 in the original (now
roughly 412-562 after edits). Subsections: Fresnel coefficients at a
lossy half-space, Pseudo-Brewster collapse, Body as a discretised PO
scatterer, Exposure operator and two enabling approximations.

## Summary

Sentence-level pass tightening prose, killing semicolons, normalising
math notation and equation punctuation. Three subsection headings
lost their leading "The" per C11. The imaginary unit was harmonised
to the engineering convention `j` (matching the appendix
\cref{app:fresnel}, which already says "$j$ is the engineering
imaginary unit"). The TE power transmittance equation was repaired
(was `\cos\theta_n / \cos\theta_n = 1`, now uses the standard
in-tissue cosine `\Re(\xi_n)/\mu_n` with `\xi_n` defined inline,
matching the appendix). Differentials use `\,\mathrm{d}A`, equations
end with `\,,` or `\,.` thin-spaced, and the "factor as squared
norm" derivation now reads as a clean five-line chain
(\eqref{eq:Sab-norm}, \eqref{eq:exposure-channel}, \eqref{eq:Q-form})
rather than a single mid-paragraph display. Inline back-face cull
got promoted to a numbered display (\eqref{eq:visibility}) so the
mesh-cull definition is referable from §V.

## Item-by-item resolution of applicable critique items

1. **Drop "The" from subsection headings (C11).**
   - "The pseudo-Brewster collapse" -> "Pseudo-Brewster collapse"
   - "The body as a discretised PO scatterer" -> "Body as a discretised PO scatterer"
   - "The exposure operator and two enabling approximations" -> "Exposure operator and two enabling approximations"
   ("Fresnel coefficients at a lossy half-space" already conformed.)

2. **i/ii framing replaced by clean equation up front (cull).**
   The original §III.C "Body as a discretised PO scatterer" did not
   have an explicit "i/ii" structure (that critique item belongs to
   §II / Agent B), but the back-face cull was buried as an inline
   `V_n(t) = [-\hat{k}_n \cdot \nhat_t]_+`. It is now promoted to a
   labelled display \eqref{eq:visibility}, so the squared-norm
   factor in \eqref{eq:Sab-norm} and the SI-side strict ray-mesh
   test can refer back to it without re-deriving.

3. **`T \approx 0.54` is a funny standalone equation.**
   No standalone `T_0 \approx 0.54` equation existed in this
   section; it was already inline in the pseudo-Brewster paragraph.
   The threshold `|\ntilde| \geq 2 + \sqrt{3}` and the value
   `\Tepskin \approx 0.54` are both inline now. No change required.

4. **"deliberately compressed" wording.**
   Not present in scope.

5. **Stray "new" / "this paper" framing.**
   Not present in scope. The post-`\eqref{eq:Q-form}` paragraph used
   to read "we adopt the same factorisation here for the SAR-reading
   branch"; tightened to "The same factorisation carries over to the
   SAR-reading branch" (passive, neutral, no "we"-of-process).

## Math notation harmonisations applied

- **Imaginary unit:** all four occurrences of `i` as the imaginary
  unit in §III replaced with `j`, matching the appendix
  (\eqref{eq:fresnel-t}, \eqref{eq:Etrans}) and the engineering
  convention. Locations: `\ntilde = 4.49 - 1.79j`,
  `e^{-jk_0 \hat{k}_n \cdot \bm{c}_t}` in
  \eqref{eq:incident-wave}, the `\Lambda_{nn'}` denominator in
  \eqref{eq:Lambda}, and the exposure-channel column in
  \eqref{eq:exposure-channel}.

- **Differentials:** `dA` -> `\mathrm{d}A` with thin-space at
  \eqref{eq:Qabs} integrand and \eqref{eq:Q-form} integrand.

- **Equation terminal punctuation:** thin-spaces `\,` before `,` /
  `.` added at \eqref{eq:Sab-single}, \eqref{eq:visibility},
  \eqref{eq:incident-wave}, \eqref{eq:Qabs}, \eqref{eq:Lambda},
  \eqref{eq:Sab-norm}, \eqref{eq:exposure-channel},
  \eqref{eq:Q-form}.

- **Frequency unit:** `28~GHz` (text mode) -> `28~\mathrm{GHz}`
  (math mode) in three intra-§III locations. Caption left unchanged
  where the surrounding prose was text-mode and stylistically
  consistent with the rest of the paper, which mixes both forms.

- **TE power transmittance bug fix.** The original
  `T_{s,n} = |t_{s,n}|^2 \cos\theta_n / \cos\theta_n` is identically
  $1$ (clear typo). Replaced with the standard
  `T_{s,n} = |t_{s,n}|^2\,\Re(\xi_n)/\mu_n` and the appendix's
  `\xi_n = \sqrt{\ntilde^2 - 1 + \mu_n^2}` definition was inlined.
  This is a math correction, not a math change: it restores the
  power transmittance to its textbook form. The downstream collapse
  to `\Tepskin \approx 0.54` is unaffected.

- **`\RE` operator (upright Re).** Used the existing
  `\DeclareMathOperator{\RE}{Re}` macro (preamble line 95).

## Style fix counts

- Semicolons removed: 4 (figure caption x2, prop:approx1 body,
  prop:approx2 body, post-\eqref{eq:Q-form} sentence). Replaced with
  periods or restructured into two clauses.
- "We" / "we" reduced from 5 to 1 (kept the `\Pabs(\thetab,\xx) = ...`
  derivation lead-in implicit; rewrote propositions in imperative
  voice "Replace ... by ..." matching standard math-paper style).
- "physically exact" -> "exact" (filler intensifier removed).
- "is invoked only for error bounds" -> "is retained only for error
  bounds" (more neutral).
- "becomes a Hermitian quadratic form" -> "is a Hermitian quadratic
  form" (KISS verb choice).
- "yields the operator" -> "gives" (KISS).
- "The proofs are in" -> "Proofs are given in" (passive form OK; no
  load-bearing "we"; matches Robin §4 preference).
- Sentence "Skin at mmWave satisfies the condition: at 28~GHz both
  transmittances..." split into two short sentences.
- Long inline `\tilde{\bm{g}}_j(\rr) = ...` definition promoted to
  numbered display \eqref{eq:exposure-channel} with `\!\!\sum`
  spacing tweak so the column-sum reads cleanly in two-column.
- Long inline `\Lambda_{nn'} = 1/[...]` promoted to display
  \eqref{eq:Lambda}.
- `\bigl( \bigr)` and `\bigl\| \bigr\|` retained where present;
  added `\,` between adjacent factors `\Pabs = \xx^H\,\Qabs\,\xx` and
  `\Jmat^H\,\Mmat\,\Jmat` for typographic clarity.

## Cross-section flags for the audit

1. **Imaginary unit `j` vs `i`.** I switched §III to `j`. The rest
   of the body still has scattered `i` usages (e.g. line 539-area
   was the only one in §III; check §IV-§VII for stray `i` as
   imaginary unit). The appendix and §III now agree on `j`.

2. **`\beta_n` is overloaded.** Used as "per-path amplitude" in
   \eqref{eq:incident-wave} and as "in-tissue phase rate" in
   \eqref{eq:Lambda} / appendix \eqref{eq:Etrans}. This is a real
   notation collision and should be resolved paper-wide. Suggest
   renaming the per-path complex amplitude to `\rho_n` or `c_n` to
   match dosimetry conventions, or rename the in-tissue phase rate
   to `\kappa_n` (Greek-letter wave number convention). Not fixed
   in this pass because it touches §IV, §V, §VI, §VII and the
   appendix.

3. **British vs American spelling.** §III still uses "polarisation"
   and "discretised" matching the rest of the paper. IEEE house
   style is American, but I did not switch in isolation. Propose a
   sweep at audit time: `polaris -> polariz`, `discretis ->
   discretiz`, `parametris -> parametriz`, `factoris -> factoriz`.
   Whole-paper change.

4. **`\Re(\xi_n)/\mu_n` form.** I introduced the standard textbook
   form for the TE power transmittance. The appendix derivation in
   `app:fresnel` uses the same `\xi_n`, so consistent. If the body
   text in §V or beyond references `T_{s,n}` explicitly (it
   doesn't, by my grep), no further change is needed.

5. **"Approximation 1" vs `\cref{prop:approx1}` rendering.** Both
   `\cref{prop:approx1}` and `\cref{prop:approx1-app}` render as
   "Proposition 1" / "Proposition 3" rather than the human-friendly
   "Approximation 1". This is a paper-wide issue: the propositions
   are titled with "Approximation 1/2" but cleveref doesn't know
   that. Either (a) define a new theorem environment
   `\newtheorem{approximation}{Approximation}` and use it for the
   two body-section propositions and the two appendix
   propositions, or (b) keep the manual "Approximation~1
   (\cref{prop:approx1})" pattern that is currently used. Flag for
   paper-wide consistency pass.

6. **`Sab\,dA` vs `\Sab\,\mathrm{d}A` paper-wide.** §III now uses
   `\,\mathrm{d}A` consistently. The appendix and elsewhere should
   be checked for stray `dA`, `dx`, `dz`. The preamble defines
   `\diff` (line 89) but it isn't used; either adopt `\diff` or
   inline `\mathrm{d}` consistently.

## Open issues

- **Repeated `\bm{a}_n^{H}\xx`** in \eqref{eq:incident-wave} reads as
  a scalar multiplied by the polarisation vector and the per-path
  amplitude. Mathematically clean but the implicit ordering
  (vector last, after a complex scalar amplitude and a complex
  scalar steered-precoder coefficient) deserves one inline comment
  in §IV when it is consumed. Out of scope here.

- The post-\eqref{eq:Q-form} sentence still references
  `\cite{Hochwald2014,Ying2015}` for "BS-side exposure-constrained
  beamforming cheap." Bibliography is Agent J. No change here.

- I did not touch the `\bigl\|\tilde{\bm{G}}(\rr)\,\xx\bigr\|^2`
  norm form. Whether to use `\|\cdot\|_2` explicitly is a
  consistency call for the audit; current paper uses unsubscripted
  `\|\cdot\|` for the Euclidean norm, which is fine.

- Section opener now reads "The treatment is a single-bounce
  Fresnel physical-optics model on a lossy half-space at mmWave"
  (was "We give only the narrow slice needed for what follows: a
  single-bounce Fresnel-physical-optics treatment..."). The
  hyphenation `Fresnel-physical-optics` was demoted to
  `Fresnel physical-optics` because the triple-hyphen compound
  read as a single coined term, which it is not (Fresnel is the
  half-space boundary condition, PO is the surface-current
  approximation). Flag if anyone disagrees.

- Compile verified clean: `pdflatex` produces 14-page output, no
  fatal errors, only the standard IEEE template overfull-hbox in
  the page header (not from §III).
