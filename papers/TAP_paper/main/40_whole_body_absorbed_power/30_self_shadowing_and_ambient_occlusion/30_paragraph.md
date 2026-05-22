% PREV: The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
% PREV: fraction of the upper hemisphere from which $\rr$ is unobstructed,
% PREV: \begin{equation}\label{eq:eta-def}
% PREV:   \eta(\rr) = \frac{1}{\pi}\int_{S^2}
% PREV:   \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
% PREV: \end{equation}
% PREV: For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
% PREV: bodies $\eta \in [0,1]$.
The exposure fraction $\eta$ is mathematically identical to the
self-shadowing factor $\gamma_s$ that Flintoft \textit{et~al.}\ define as
``the proportion of total surface area of the body that is illuminated
by the reverberant field''~\cite[p.~3301]{Flintoft2014} and estimate
geometrically as $0.75$--$0.85$ from Tomita's surface-area
data~\cite{Tomita1999}. The Flintoft estimate is geometric and
posture-dependent. The construction here is computational and
posture-resolved. For the Thelonious phantom, an ambient-occlusion
solver returns the area-weighted mean
$\bar{\eta} = \Aab/A = 0.865$. This is near the upper end of
Flintoft's band $[0.75, 0.85]$~\cite{Tomita1999}.
\Cref{fig:phantom}\subref{fig:phantom:eta-front} and
\subref{fig:phantom:eta-side} render it on the phantom. Most of the
body has $\eta \approx 1$. Reductions occur in concavities. The
medial sides of the legs and arms, the armpits, the underside of
the chin, and the soles of the feet are the dominant such regions.
On a $10^4$--$10^5$ triangle mesh, the solver evaluates $\eta$ in
tens of milliseconds on commodity hardware.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `and is rendered on the phantom in \cref{fig:phantom}\subref{fig:phantom:eta-front} and \cref{fig:phantom}\subref{fig:phantom:eta-side}` -> Split into a new sentence with the figures as active subject: "\cref{fig:phantom}\subref{fig:phantom:eta-front} and \subref{fig:phantom:eta-side} render it on the phantom."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.mic_drop_stinger_sentences`: Short, but it does not restate the preceding sentence (most of body has eta approx 1); it introduces a new claim and sets up the following list of regions, so it is load-bearing, not a punchline.
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_WILLIAMS_style.prose_structure.comma_after_long_intro` (unknown): `On a $10^4$--$10^5$ triangle mesh the solver evaluates $\eta$ in` -> Add a comma after the five-word introductory phrase: "On a $10^4$--$10^5$ triangle mesh, the solver evaluates..."
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: Both \cref uses are mid-sentence and render a lowercase "fig." label, which is correct; \Cref is only required at sentence start where the prefix must capitalize.
    - _dismissed_ `latex.math.subscript_labels_upright`: $\gamma_s$ is the established symbol from the cited Flintoft work (defined notation, mnemonic single-letter index), not a variable product; forcing upright here would diverge from the referenced source and the paper's own notation.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

