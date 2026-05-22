% PREV: The generalized Cauchy formula is the central whole-body identity.
% PREV: \begin{theorem}\label{thm:cauchy}
% PREV: Let a body $\Sigma$ have surface area $A$, exposure fraction
% PREV: $\eta(\rr)$, and absorption area
% PREV: $\Aab \equiv \int_\Sigma \eta(\rr)\,\diff A$. Under isotropic,
% PREV: unpolarized plane-wave illumination of intensity $\IPD$ on tissue
% PREV: with normal-incidence transmission $T_0$, the direction-averaged
% PREV: whole-body absorbed power is
% PREV: \begin{equation}\label{eq:cauchy}
% PREV:   \langle P_{\mathrm{abs}} \rangle = \IPD\,T_0\,\Aab/4\, .
% PREV: \end{equation}
% PREV: \end{theorem}
% NEXT: The classical Cauchy formula $\langle\Aperp\rangle = A/4$ is the
% NEXT: special case $\eta \equiv 1$, valid for any convex body. The
% NEXT: absorption area $\Aab$ reduces all geometric complexity of
% NEXT: self-shadowing to a single scalar.
\begin{proof}
Apply Fubini's theorem to exchange the surface and direction
integrals. The local law~\eqref{eq:geom-law} gives
$\APD(\rr,\khat) = \IPD\,T_0\,\Vis(\rr,\khat)\,
\pospart{\nhat\cdot(-\khat)}$. The direction average of the integrand
is
\[
  \frac{1}{4\pi}\int_{S^2}
  \IPD\,T_0\,\Vis(\rr,\khat)\,\pospart{\nhat\cdot(-\khat)}\,
  \diff\Omega
  = \frac{\IPD\,T_0}{4}\,\eta(\rr)\,,
\]
using the definition of $\eta$ and the identity $\int_{S^2}
\pospart{\nhat\cdot(-\khat)}\,\diff\Omega = \pi$ for any unit
$\nhat$. Integration over $\Sigma$ gives~\eqref{eq:cauchy}.
\end{proof}

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.spacing_ties.equation_punctuation_gap` (medium): `= \frac{\IPD\,T_0}{4}\,\eta(\rr),` -> Insert a thin space before the trailing comma: \eta(\rr)\,, to match the paper's house style (cf. \mathbf{s}\, . elsewhere).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

