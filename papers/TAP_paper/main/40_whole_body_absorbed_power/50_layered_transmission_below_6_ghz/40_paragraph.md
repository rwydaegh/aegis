% PREV: The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
% PREV: layer. Below $6$~GHz the SAR penetration depth in fat exceeds
% PREV: $70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
% PREV: cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
% PREV: layer with little attenuation and reflects from the fat-muscle
% PREV: interface. Constructive interference enhances absorption, and destructive
% PREV: interference suppresses it. A three-layer transfer-matrix model with
% PREV: skin, fat, and a semi-infinite muscle half-space gives the layered
% PREV: transmission
% PREV: \begin{equation}\label{eq:T-lay}
% PREV:   \Tlay(f, d_{\mathrm{SF}})
% PREV:   = 1 - \bigl|\widetilde{\Gamma}_1(f, d_{\mathrm{SF}})\bigr|^2\, ,
% PREV: \end{equation}
% PREV: where $\widetilde{\Gamma}_1$ is the generalized Fresnel reflection
% PREV: coefficient at the air-skin interface, computed recursively from the
% PREV: fat-muscle interface upward~\cite{Chew1995,BornWolf1999}.
% PREV: Section~\ref{si:layered} of the SI gives the full Chew recursion,
% PREV: the standing-wave SAR per layer, and the layer-by-layer cube
% PREV: integral. Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for
% PREV: the canonical $2$~mm skin / $10$~mm fat / muscle stack. Replacing
% PREV: $\Tbar$ with $\Tlay$ in~\eqref{eq:cauchy-exact} gives a
% PREV: frequency-dependent direction-averaged absorbed power that includes
% PREV: the fat-layer resonance. For a fat thickness of $10$~mm the model
% PREV: predicts a $40\%$ enhancement above the homogeneous prediction at
% PREV: $0.9$~GHz (quarter-wave matching) and a $27\%$ reduction at
% PREV: $3.5$~GHz (destructive interference).
Zhang derives the planar limit of this model in his
thesis~\cite[Sec.~2.2]{Zhang2017thesis} and observes the resonance
shift with fat thickness in his Figs.~2.7--2.8, writing that ``the
fat layer may act as a matching layer between skin and
muscle''~\cite[p.~21]{Zhang2017thesis}. The contribution here is to
embed the planar model in the body-surface integral via $\Tlay$ and
\eqref{eq:cauchy-exact}, which makes the resonance compatible with a
Cauchy-style direction average. Body-surface averaging suppresses
the oscillation by a factor of approximately
$A_{\mathrm{exposed,fat}}/A$ because different body regions carry
different fat thicknesses, with limbs near $2$~mm and abdomen near
$30$~mm, and consequently different resonance frequencies. The
integrated dip is shallower than the single-thickness prediction but
is at the same frequency. The local surface map
$\APD(\rr) \approx \IPD\,T_0 \Vis \pospart{\mu}$ loses pointwise
meaning below $6$~GHz, where the SAR penetration depth exceeds the
surface layer thickness. Total power remains valid via $\Tlay$
throughout.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.final_pass.figure_table_refs_text`: Refers to figures inside Zhang's cited thesis (external document) via the citation locator, not this paper's floats; correct as a bare locator with no local \ref.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

