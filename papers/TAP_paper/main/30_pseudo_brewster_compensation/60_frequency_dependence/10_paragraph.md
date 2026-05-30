% PREV: \subsection{Frequency dependence}\label{subsec:pB-freq}
% NEXT: \begin{figure}[!t]
% NEXT:   \centering
% NEXT:   % Legend entries capitalized (Conservative / Non-conservative); see
% NEXT:   % scripts/R_of_f_landscape.py.
% NEXT:   \includegraphics[width=\columnwidth]{R_of_f.pdf}
% NEXT:   \caption{Sphere ratio $R(f) = T_0/\Tbar$ versus frequency for skin
% NEXT:   (IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}). $R = 1$ indicates that the
% NEXT:   constant-$T_0$ approximation is exact on the direction-averaged
% NEXT:   quantity; $R < 1$ means $T_0$ underestimates absorbed power and
% NEXT:   $R > 1$ means it overestimates. The dashed horizontal lines mark
% NEXT:   the $\pm 4\%$ band.}
% NEXT:   \label{fig:R-of-f}
% NEXT: \end{figure}
The accuracy of the constant-$T_0$ approximation has a clean
frequency dependence. Define the \emph{sphere ratio} $R(f)$
\begin{equation}\label{eq:R-of-f}
  R(f) \equiv T_0(f) / \Tbar(f),
  \qquad
  \Tbar(f) \equiv 2\int_0^1 \Tavg(\mu, f)\,\mu\,\diff\mu\,,
\end{equation}
where $\Tbar(f)$ is the flux-weighted Fresnel transmission. $R(f) =
1$ when the constant-$T_0$ approximation is exact on a
direction-averaged quantity. $R < 1$ means $T_0$ underestimates
absorbed power. $R > 1$ means it overestimates. \Cref{fig:R-of-f}
shows that for skin the crossover is at 40.4~GHz, where the
compensation is exact. Below this
frequency the approximation underestimates absorbed power. Above, it
overestimates by at most $3.5\%$ at 100~GHz. The root-mean-square error
remains below $5\%$ across $0.3$--100~GHz. Frequency-resolved
Cole--Cole values for skin and the angle family
$\Tavg(\theta)\cos\theta$ at six representative frequencies are in
Table~\ref{tab:itis-fvs} and Fig.~\ref{fig:si-angle-family} of the SI.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.structure_style.first_coinage_italics` (low): `Define the sphere ratio $R(f)$` -> Change to "Define the \emph{sphere ratio} $R(f)$" to mark the coinage with italics at first introduction.
- **incremental (2026-05-22)** — pass (3 new/edited rules cleared).

