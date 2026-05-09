# Report: PSEUDO_BREWSTER

Lines 510--739: `\section{Pseudo-Brewster compensation}` and all subsections.

## Edits applied

- **Section/subsection titles to sentence case**: "Pseudo-Brewster Compensation" -> "Pseudo-Brewster compensation"; "Quantitative Behavior Across Angle" -> "Quantitative behavior across angle"; "Tissue Universality" -> "Tissue universality"; "Frequency Dependence" -> "Frequency dependence"; "Geometric Absorption Law" -> "Geometric absorption law".
- **American English**: "towards" -> "toward" (line ~515).
- **Unit format**: All `$XX\,$GHz` (math-mode thin-space) instances in the section converted to `XX~GHz` (tilde-glued). Affected: 28~GHz (x7), 40.4~GHz (x2), 100~GHz (x3).
- **Numeric range with en dash**: `$0.3$ to 100~GHz` -> `$0.3$--100~GHz` in both body text and figure caption.
- **Equation punctuation inside**: `eq:R-of-f` -- added `\,` before the trailing comma: `\diff\mu\,,`.
- **Boxed equation punctuation**: `eq:geom-law` -- moved `\,.` from outside `\boxed{}` to after the closing brace, inside `\end{equation}` (as `\, .` on its own line between `}` and `\end{equation}`).
- **Passive sentence**: "The application of the criterion to biological dosimetry has not been made in the optics or bioelectromagnetics literature." -> "This connection between the Azzam criterion and biological dosimetry has not appeared in the optics or bioelectromagnetics literature."
- **Connective**: Added "Hence," before the final error-bounds paragraph in the Geometric absorption law subsection.

## Tougher questions for the author

- The boxed equation `\eqref{eq:geom-law}`: convention for punctuation placement with `\boxed{}` varies. The current fix places `\, .` between the closing `}` of `\boxed` and `\end{equation}`. If the journal style prefers the period outside `\end{equation}`, revert. The original had `}\,.` just before `\end{equation}`, which is inside the equation environment but outside the box -- also reasonable.
- "The criterion weakens for $|\ntilde| > 2.5$" (line ~534): Azzam's strict criterion requires $|\ntilde| > 3.73$. The weakened form at 2.5 is not cited -- is this the author's own extension or a known result? Consider adding a citation or softening to "the near-constancy extends empirically to $|\ntilde| > 2.5$."

## DOIs / references that look suspicious

- `\cite{Potter1970}`, `\cite{Ohman1977}` -- older optics references. Verify these are the correct papers for the pseudo-Brewster angle approximation.
- `\cite{Azzam2015}` -- verify this is the correct Azzam paper for the unpolarized reflectance criterion.

## Anti-patterns found and fixed

- Title-case subsection headings (4 subsections corrected).
- British "towards" corrected.
- `$XX\,$GHz` thin-space-in-math form replaced with tilde-glued form throughout.
- Passive/clunky "The application of..." sentence rephrased.
- Equation punctuation outside equation environment fixed (boxed equation).

## Patterns introduced

- En dash for numeric range `0.3--100~GHz`.
- "Hence," connective linking geometric-law derivation to its error-bound summary.

## Out-of-scope items spotted

- `\eqref{eq:Sab-Tavg}` equation (around line 502--504, just before assigned range) may also need equation-end punctuation check.
- The `\section{Whole-body absorbed power}` section immediately following (line 739+) also has `$28\,$GHz` instances -- not touched.
