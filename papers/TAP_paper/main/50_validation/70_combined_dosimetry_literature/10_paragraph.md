% PREV: \subsection{Combined dosimetry literature}\label{subsec:val-waterfall}
% NEXT: \begin{figure*}[!t]
The literature comparison maps each reported empirical scalar to the
corresponding closed-form quantity. Kodera's transmission coefficient
$T_{\mathrm{tr}}$ is compared with the Fresnel transmission used in
the one-dimensional reference model. Flintoft's self-shadowing factor
$\gamma_s$ is compared with the surface mean of the exposure fraction
$\eta(\rr)$. Bamba's efficiency $\eta(f)$ and Zhang's coefficient
$\xi$ are compared with the whole-body factor $\Tbar(f)\Aab/A$.
The plotted Flintoft points are linear-regression intercepts of
$\langle Q^a\rangle$ at $d_{\mathrm{SF}} = 0$ with $\gamma_s =
1$~\cite[Eq.~6]{Flintoft2014}. The plotted Zhang points combine the
$6$--$18$~GHz plateau from~\cite[Fig.~4.9]{Zhang2017thesis} with the
$1$--$6$~GHz envelope from~\cite[Fig.~4.11]{Zhang2017thesis}.
\Cref{fig:waterfall} then compares the closed-form
prediction~\eqref{eq:cauchy-exact} against $168$ volunteers and $5$
FDTD phantoms from $1$ to $100$~GHz.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): "$\gamma_s$ is compared with the surface mean of the exposure fraction" → Rewrite active: "the comparison matches $\gamma_s$ against the surface mean" (and the two sibling "is/are compared with" clauses).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.pet_peeves_wout.hackneyed_nouns`: "factor" names a specific physical quantity (the whole-body transmission factor bound to $\Tbar(f)\Aab/A$), not the empty "important factor in" filler the rule targets.
    - _dismissed_ `style.pet_peeves_wout.first_time_framing`: This is a mid-paper validation paragraph, not the end of the introduction; the first-time-framing mandate applies only to the contribution sentences at the close of the intro.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `BOOK_ELOS_style.misused_words.factor_hackneyed`: "factor" is the named technical quantity, not the "X is an important factor in Y" pattern; no direct causal verb improves it.
    - _dismissed_ `style.anti_ai_language.em_dash_overuse`: The "--" is an en-dash numeric range, explicitly allowed; not an em dash in prose.
    - _dismissed_ `style.misused_words.passive_for_flow`: Passive keeps the short familiar empirical scalar in subject position with the comparison target trailing; agent (the authors) is self-evident, so passive is correct here.
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.math.subscript_labels_upright` (medium): "Flintoft's self-shadowing factor $\gamma_s$" → Set the descriptive subscript upright: $\gamma_{\mathrm{s}}$, matching the $\mathrm{tr}$ and $\mathrm{SF}$ labels in the same paragraph.
    - _dismissed_ `latex.citations.merged_cite`: Both cite the same key but carry different locators (Fig.~4.9 vs Fig.~4.11), so they cannot be merged into one \cite with a single optional argument.
    - _dismissed_ `latex.substitutions.cref_capitalized`: Already capitalized \Cref at sentence start, which is the correct form.

