# Report: LOCAL_LAW (lines 399–509)

## Edits applied

Six numbered display equations in the section all lacked the author's `\, .` / `\, ,` signature punctuation inside the environment. All fixed:

- **eq:Sab-pol**: appended `\, ,` inside (continuation: "for each polarization separately")
- **eq:rs-rp**: appended `\, ,` inside (continuation: "for TE and TM polarizations, respectively")
- **eq:T0**: appended `\, .` inside (sentence ends at the equation)
- **eq:Teff**: appended `\, .` inside (sentence ends at the equation)
- **eq:Teff-decomp**: appended `\, ,` inside (continuation: "with $\Tavg = \ldots$")
- **eq:Sab-Tavg**: appended `\, .` inside (sentence ends at the equation)

**eq:Sab-exact** was already correct: `}\,.` places the thin-space period inside the `equation` environment (outside `\boxed{}` but before `\end{equation}`). No change made.

## Anti-patterns found and fixed

All six numbered display equations lacked the author's punctuation-inside-equation convention. All corrected.

## Tougher questions for the author

None. The section is structurally sound.

## Out-of-scope items spotted (not touched)

- **Subsection title case**: The entire paper uses title case for `\subsection{}` headings uniformly. Briefing recommends sentence case but also says to be consistent with the rest of the paper. Did not change in wave 1; wave 2 will downcase across all ranges.
- **`$28\,$GHz` pattern** (thin-space inside math mode): Used throughout the paper. Briefing says tilde form is preferred but instructs leaving math-mode constructions alone. Not converted in this range.
- No em dashes, no "leverage", no British English, no `\textit{lead-noun:}` anti-patterns, no `\gls{}` in abstract-adjacent text.
