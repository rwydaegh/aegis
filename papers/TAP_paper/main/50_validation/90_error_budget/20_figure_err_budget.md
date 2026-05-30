% PREV: \Cref{fig:err-budget} reports two regimes side by side at $28$~GHz on
% PREV: skin. The worst case is single body part, single direction, pointwise
% PREV: local. The typical case is whole-body integrated, direction-averaged.
% PREV: The dielectric input spread is $\pm 20\%$ on $\varepsilon_r$ and
% PREV: $\sigma$. This is the inter-model gap between Gabriel
% PREV: \textit{et~al.}~\cite{Gabriel1996} and the empirical
% PREV: Gabriel-times-$1.2$ fit that Christ \textit{et~al.}~\cite{Christ2021}
% PREV: obtained from $S_{11}$ measurements on $37$ volunteers at
% PREV: $40$--$110$~GHz. The spread is consistent with mmWave dielectric
% PREV: campaigns more
% PREV: broadly~\cite{AlekseevZiskin2007,Sasaki2014,Zhadobov2011}.
% PREV: We evaluate $T_0 = 4n/[(1+n)^2+\kappa^2]$ at the four corners of the
% PREV: $\pm 20\%$ box. The largest deviation on skin at $28$~GHz is
% PREV: $\pm 7\%$. The Fresnel approximation worst case is $5.3\%$ pointwise
% PREV: local (\cref{tab:phantom}). The typical case is $1.2\%$
% PREV: direction-averaged on whole-body absorbed power (Supplementary
% PREV: Information, $128$-direction sweep). The diffraction worst case is
% PREV: $10\%$ on a torso-scale Mie sphere (\cref{subsec:val-mie}). The
% PREV: typical case is $1.2\%$ integrated on Thelonious (Supplementary
% PREV: Information, GELU integration). The inter-body reflection worst
% PREV: case is $4\%$ under the diffuse bound. The typical case is $1\%$
% PREV: under specular at mmWave (\cref{subsec:corr-residuals}). In the
% PREV: typical case every model error stays below the dielectric uncertainty.
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{error_budget_comprehensive.pdf}
  \caption{Error budget for the geometric law in two regimes at
  $28$~GHz on skin. Worst case is single body part, single direction,
  pointwise. Typical case is whole-body integrated,
  direction-averaged. Only the dielectric uncertainty stays large in
  the typical case.}
  \label{fig:err-budget}
\end{figure}

## reviews (figure)



_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.conventions.scripting_colour_palette` (high): `COLOR_WORST = "#9d9d9d"  /  COLOR_TYPICAL = "#1f3b73"` -> Replace the grey/navy fills with two Wong palette hex codes (e.g. #56B4E9 worst, #0072B2 typical) so the figure matches the paper-wide colour-blind-safe palette.

## grinder notes
- **label**: fig:err-budget
- **caption_preview**: Error budget for the geometric law in two regimes at $28$~GHz on skin. Worst case is single body par
