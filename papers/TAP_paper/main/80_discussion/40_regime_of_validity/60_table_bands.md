% PREV: Whole-body resonance dominates below approximately $300$~MHz, where
% PREV: the body acts as a half-wave dipole and surface absorbed power is
% PREV: unrelated to internal hot-spots~\cite{Durney1986}. Below this
% PREV: frequency the framework reduces to volumetric solvers.
% NEXT: The pseudo-Brewster compensation softens above $200$--$250$~GHz,
% NEXT: where the Azzam high-index criterion $|\ntilde| > 2.5$ weakens and
% NEXT: worst-case angular variation grows from $5.6\%$ at $28$~GHz to
% NEXT: approximately $10\%$ at $250$~GHz and $15\%$ at $300$~GHz, comparable
% NEXT: to the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}). Skin
% NEXT: refractive-index modulus from the IT'IS database~\cite{ITISv5,Gabriel1996} is $4.84$ at $28$~GHz,
% NEXT: $3.68$ at $60$~GHz, and $3.01$ at $100$~GHz, and extrapolation puts
% NEXT: $|\ntilde|$ near $2.5$ around $200$--$250$~GHz, approximately $2.2$
% NEXT: at $300$~GHz, and $1.8$--$2$ at $1$~THz.
\begin{table}[!t]
\centering
\caption{Frequency-band limits of~\eqref{eq:cauchy-exact} on a
human-adult body. Quantitative validity covers $1$--$100$~GHz on
whole-body absorbed power, $6$--$100$~GHz pointwise on the
surface.}
\label{tab:bands}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.18\linewidth}
                  >{\raggedright\arraybackslash}p{0.42\linewidth}
                  >{\raggedright\arraybackslash}p{0.30\linewidth}@{}}
\toprule
Band & Surface law status & Whole-body identity \\
\midrule
below $300$~MHz
  & other physics: resonance and hot-spots
  & FDTD required \\
$0.3$--$1$~GHz
  & qualitative, $10\%$--$30\%$ Mie underestimate
  & qualitative, $\Tlay$ recovers the dip \\
$1$--$6$~GHz
  & integrated within $5\%$--$10\%$, local map loses pointwise meaning
  & quantitative, $\Tlay$ replaces $T_0$ \\
$6$--$100$~GHz
  & quantitative within $3\%$ pointwise
  & quantitative, Brewster compensation sharpest \\
\bottomrule
\end{tabular}
\end{table}

## reviews (table)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **table** — pass (10 rules cleared).

## grinder notes
- **label**: tab:bands
- **caption_preview**: Band stratification of~\eqref{eq:cauchy-exact
