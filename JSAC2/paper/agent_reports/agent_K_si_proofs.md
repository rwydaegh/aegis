# Agent K — SI proofs (Approximations 1/2) and per-path Fresnel operator F_n

**Scope:** `jsac2_v3_supp.tex`, lines 70–252 (Sections S1: Approximations 1 and 2 error budgets and proofs; S2: Per-path Fresnel transmission operator).

## Summary

Tightened the prose around the math without touching any derivation step. Killed two semicolons (Robin's rule), dropped four `\,\%` in favor of IEEE house-style bare `%`, replaced the IEEE-illegal `Tab.~III` with `Table~III`, swapped two `:`-as-conjunction colons inside the per-path Fresnel section for cleaner sentence breaks, removed the throat-clearing "We reproduce…" / "We collect the formal definition here" sentences, killed the conversational coinages "rests on the same mechanism" cluster and "Maxwell-from-the-ground-up" / "follows the standard route", de-top-heavied the Fresnel-coefficients sentence (subject-verb in first 3 words, not after a 16-word adjunct), and dropped the parenthetical self-quote `(UE-anchored Kirchhoff render)` after the Section IV reference. The math, propositions, definitions, equation labels, and cross-references are untouched.

## Issues I found (sentence by sentence)

**S1 opener (lines 73–81 v3):**
- "two propositions that license the reduction of …" — verb "license" is vague + jargon-y for legal/grant licensing. Real action is they justify the reduction. Cut.
- "(Approximations 1 and 2 of the main paper)" parenthetical immediately after naming "two propositions" duplicates the thought.
- "The proofs are short and rest on the same mechanism: the high refractive index of skin compresses…" — colon doing too much work; "are short" is editorialising filler. Split into staccato sentences.
- "We reproduce both proofs here with cross-references aligned to the main paper's symbol set." — pure throat-clearing about what the section will do. Trimmed to "The proofs follow, with notation aligned to the main paper."

**S1 Proof of Approx. 1 (lines 118–127 v3):**
- `$\lesssim 4\,\%$` — IEEE house style: no space before `%` (latex_rules_extreme_quality.md item 72). Fixed to `4\%`.
- `tissues with larger $|\ntilde|$;` — semicolon. Robin rule 2 says never. Split into two sentences.
- `Tab.~III` — Rule 37 of latex_rules: "Table always spelled out in IEEE; never `Tab.`" Fixed to `Table~III`.
- "(approximation accuracy) of the main paper" — parenthetical glosses the table number, but the gloss is structural meta. Dropped to "Per-tissue values appear in Table~III of the main paper."

**S1 Proposition 2 (lines 144–145 v3):**
- `0.44\,\%` and `0.17\,\%` — same `\,\%` issue. Fixed to bare `%` ×2.

**S1 Proof of Approx. 2 (lines 158–186 v3):**
- `same $\sim\!2\,\%$ relative spread` — `\,\%` again. Fixed to `2\%`.
- `inherit the same … relative spread; differences …` — semicolon. Split.
- `to first order in (…) and (…) (with $\bar\alpha = …$) gives` — double parenthetical, second one nested ugly. Replaced inner parens with comma-bracketed clause "with $\bar\alpha = \tfrac{1}{2}(\alpha_n + \alpha_{n'})$".
- `0.44\,\% with mean 0.17\,\%` (in proof body) — same percent issue ×2.
- "The numerical sweep" — definite article suggests a previously-introduced sweep; this is the first mention. Changed to "A numerical sweep".
- Final 5-line sentence chained "non-conservatively (it can both over- and under-estimate cross-term magnitudes) and is an order of magnitude smaller than the calibration headroom that the body-side γ regression in Section VI (Closed-loop calibration) of the main paper absorbs." — too many subordinate clauses, plus a Section VI parenthetical that quotes the section title. Split into two short sentences and removed the title quote (Section~VI is enough).

**S2 Per-path Fresnel — opener (lines 192–196 v3):**
- "without writing the matrix explicitly. We collect the formal definition here." — second sentence is meta-commentary about what the section does; deleted.
- "The Maxwell-from-the-ground-up derivation" — colloquial, Wout will circle this (rule 4 wout_specific_pet_peeves: "absolute deadpan straightforward science"). Replaced with "The full derivation from Maxwell's equations".
- "(Snell's law from phase matching, …)" — kept the parenthetical but switched "from phase matching" to "via phase matching" for parallelism with what follows.
- "follows the standard route~\cite{BornWolf}" — "standard route" is colloquial. Replaced with "is standard~\cite{BornWolf}".
- Quoted phrase ` ``rank-2, polarisation-aware'' ` — scare quotes around technical terms (style guide C9: "Do not use scare quotes around common terms"). Removed quotes; the terms are fine bare.

**S2 Fresnel coefficients (lines 207–215 v3):**
- "The Fresnel TE and TM amplitude transmission coefficients on the lossy half-space, derived in standard references via continuity of the tangential E and H fields at z=0, are" — top-heavy: 22 words before the verb "are", with the verb a feeble copula. Subject-verb-rest violated. Reflowed: "Continuity of the tangential E and H fields at z=0 gives the Fresnel TE and TM amplitude transmission coefficients" — verb in first 9 words, deadpan, agent stated.
- Lost the `\cite{BornWolf}` here since the section opener already cited it once for the same derivation. Single citation per derivation is enough.

**S2 Closing paragraph (lines 226–242 v3):**
- "In that basis $\Fn$ is diagonal: \begin{equation}…\end{equation} where the diagonal form follows…" — colon followed by display equation followed by "where" reads as a run-on. Replaced colon with comma + "and the diagonal form follows…" so the sentence terminates cleanly after the equation.
- "(\cref{prop:S-approx1}): replacing the refracted TM direction…" — second colon in same compound sentence. Killed; period after the cref, then a fresh sentence starting "Replacing…".
- "The transmitted surface field is then \begin{equation}…\end{equation} which is the per-triangle integrand consumed by the Kirchhoff render of Section~IV (UE-anchored Kirchhoff render) and by the exposure operator …" — three issues: "is then" leaves the equation hanging awkwardly; `(UE-anchored Kirchhoff render)` is a self-quote of Section IV's title (style guide C10 / general taste — don't quote your own section titles); "consumed by" anthropomorphises the render. Reflowed to "The transmitted surface field is \begin{equation}…\end{equation} the per-triangle integrand of the Kirchhoff render in Section~IV of the main paper and of the exposure operator …" Punctuation: equation ends with `,` and the next clause is the appositive.

## Counts of style fixes

| Category | Count |
|---|---|
| `\,\%` → `%` (IEEE house-style percent) | 6 |
| Semicolons removed (Robin rule 2) | 2 |
| `Tab.~III` → `Table~III` (rule 37) | 1 |
| Throat-clearing / meta sentences deleted | 3 ("We reproduce both proofs…", "We collect the formal definition here.", "The proofs are short and rest on…") |
| Run-on `:` collapsed to period or comma | 3 (S2 closing paragraph ×2; one in long Section VI sentence) |
| Top-heavy sentence inverted to subject-verb-rest | 1 (Fresnel coefficients sentence) |
| Conversational coinages neutralised | 2 ("Maxwell-from-the-ground-up", "follows the standard route") |
| Self-quote of section title removed | 1 (`(UE-anchored Kirchhoff render)`) and 1 (`(Closed-loop calibration)` after Section VI) |
| Scare quotes on technical terms removed | 1 (`` ``rank-2, polarisation-aware'' ``) |
| "The numerical sweep" → "A numerical sweep" (article correctness) | 1 |
| Parenthetical glosses removed (`(approximation accuracy)`) | 1 |

## Cross-section flags

- **`Tab.~III` reference:** the original prose pointed at "Tab.~III (approximation accuracy)" of the main paper. I changed `Tab.` to `Table` and dropped the gloss. If the main paper's Table III is in fact called something else, the reference is still correct (the table number is what matters), but verify the main paper actually has a Table III on approximation accuracy. If the main paper is now using `\cref` / `\Cref` and the SI is supposed to load `xr-hyper` to resolve the cross-doc reference, that infrastructure is not in this SI's preamble (the TAP exemplar uses `\externaldocument{paper}`; this SI does not). The current hardcoded `Table~III` will print but won't hyperlink to the main paper.
- **Section IV / Section VI of the main paper:** same issue. Both are hardcoded Roman numerals. If the main paper restructures, these go stale. Not in scope to fix here.
- **`\hat{\bm{k}}_n` vs `\khat_n` macro:** line 85 of the v3 file (Proposition 1 statement) uses the long form `\hat{\bm{k}}_n` while a `\khat` macro is defined at line 26. The macro is used elsewhere in the same file. Not a style-pass priority — purely cosmetic and the math is spinally fine — but Wout-precision-conscious readers will spot the inconsistency.
- **`\bm{E}^{\mathrm{trans}}` vs `\bm{E}_n^{\mathrm{trans}}`:** line 120 (proof, line 119 v3) writes the un-indexed `\|\bm{E}^{\mathrm{trans}}\|^2` while line 244 (S2) writes `\bm{E}_n^{\mathrm{trans}}`. The proof context is post-summation so the unsubscripted form is fine, but a sharp reviewer may want a subscript on the path-summed E to be explicit. Not in scope.

## Open issues / regressions / things I deliberately did not touch

1. **Spelling: `polarisation` (British) throughout.** Latex rule 71 specifies American spelling for IEEE TAP/TWC/JSAC. The whole supp file consistently uses British spelling, and so does the main paper (per line 192 of the original v3). Changing only my section would create internal inconsistency, and the call belongs at the paper-wide level. Flagging, not fixing.
2. **Sign of $\alpha_n$ in line 158:** the convention `$\alpha_n - j\beta_n = -j k_0 \xi_n$` (line 131) gives $\alpha_n = k_0 \IM(\xi_n)$ algebraically, but the proof writes `$\alpha_n = -k_0 \IM(\xi_n)$`. This is consistent only if $\IM(\xi_n) < 0$ for the lossy convention adopted (which is the $e^{-j\omega t}$ convention with $\IM(\ntilde) < 0$). Spinally fine under one convention, wrong under the other. The instruction said math is fine, so I left it; flagging in case Agent C / Agent D's parallel pass surfaced a convention inversion.
3. **`^\top` in outer products `\hat{e}_{s,n}\hat{e}_{s,n}^{\!\top}`:** TE and TM unit vectors are real, so transpose vs Hermitian conjugate doesn't matter for the operator action, but a TWC/JSAC reviewer used to complex-vector formalism may prefer `^H`. Out of scope.
4. **Underfull hbox warning at lines 130–135** in compile output. This is the Proposition 2 statement with the long inline math `$\Lambda_{nn'} = 1/[\alpha_n + \alpha_{n'} - j(\beta_{n'} - \beta_n)]$`. Badness 2318 is mild and the column still typesets; pre-existed my edits. A `\linebreak` or breaking the inline display into a numbered equation would fix it cosmetically but adds equation real-estate; left as-is.
5. **No regression conflicts with `a_first_Reading_critique.md`.** The v3 starting text I edited already showed the polishing pass (no Maxwell-pedagogy intro inside the proofs, no "we observe that" filler, etc.). My edits push further in the same direction without re-introducing what the critique flagged. The opener lost three sentences of stage-direction; that is in line with the critique's spirit, not against it.

## Compile status

`pdflatex -interaction=nonstopmode jsac2_v3_supp.tex` → 6 pages, 594 kB PDF generated. No errors. Pre-existing warnings outside my scope (lines 478–487, 560–568, 578, 641–663) untouched. The lines-130–135 underfull warning is pre-existing typesetting badness in the inline math of Proposition 2 (see open issue 4).
