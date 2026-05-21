% PREV: The human body is not convex.
% NEXT: The exposure fraction $\eta$ is mathematically identical to the
The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
fraction of the upper hemisphere from which $\rr$ is unobstructed,
\begin{equation}\label{eq:eta-def}
  \eta(\rr) = \frac{1}{\pi}\int_{S^2}
  \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
\end{equation}
For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
bodies $\eta \in [0,1]$.

## reviews (paragraph)


_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.structure_style.first_coinage_italics` (low): "The \textit{exposure fraction} $\eta$ at a surface point" → Use \emph{exposure fraction} rather than \textit{} for the coined term; \emph is the semantic command for first-use coinage and toggles correctly inside any italic context.

