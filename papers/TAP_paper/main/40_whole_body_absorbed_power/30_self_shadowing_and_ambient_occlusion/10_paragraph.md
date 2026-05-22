% PREV: \subsection{Self-shadowing and ambient occlusion}\label{sec:self-shadow}
% NEXT: The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
% NEXT: fraction of the upper hemisphere from which $\rr$ is unobstructed,
% NEXT: \begin{equation}\label{eq:eta-def}
% NEXT:   \eta(\rr) = \frac{1}{\pi}\int_{S^2}
% NEXT:   \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
% NEXT: \end{equation}
% NEXT: For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
% NEXT: bodies $\eta \in [0,1]$.
The human body is not convex. Concavities such as the armpits, the
gap between the legs, and the neck region cause one part of the body
to shadow another. The binary visibility $\Vis(\rr,\khat) \in \{0,1\}$
in~\eqref{eq:geom-law} is the ambient-occlusion primitive of computer
graphics introduced by Zhukov \textit{et~al.}~\cite{Zhukov1998} and brought
into production rendering by Landis~\cite{Landis2002}. Modern GPUs
evaluate $\Vis(\rr,\khat)$ at interactive frame
rates~\cite{AkenineMoller2018}.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Concavities such as the armpits, the gap between the legs, and the neck region cause one part of the body to shadow another.` -> Move the list to the end so the subject-verb core lands first: "Concavities cause one part of the body to shadow another: the armpits, the gap between the legs, and the neck region."
    - `style.positive_voice.no_passive_no_we` (high): `introduced by Zhukov \textit{et~al.}~\cite{Zhukov1998} and brought into production rendering by Landis~\cite{Landis2002}` -> Use active attribution: "...primitive of computer graphics that Zhukov \textit{et~al.}~\cite{Zhukov1998} introduced and Landis~\cite{Landis2002} brought into production rendering."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.anthropomorphism_standards_algorithms`: A GPU is hardware that literally evaluates the primitive; the rule targets standards bodies, fields, and algorithms attributed intent or consensus, not a device performing a computation.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.positive_voice.positive_form`: This is a genuine denial of a geometric property, the licensed use of 'not'; the entire paragraph rests on non-convexity, and 'concave' would be a false rewrite since the body is neither.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.acronym_first_use`: GPU is a near-universal computing acronym; spelling out 'graphics processing units (GPUs)' in a one-line aside about frame rates would add clutter, not clarity, and IEEE TAP routinely leaves it undefined.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

