% PREV: The accuracy of the constant-$T_0$ approximation has a clean
% NEXT: # Frequency dependence
\begin{figure}[!t]
  \centering
  % Legend entries capitalized (Conservative / Non-conservative); see
  % scripts/R_of_f_landscape.py.
  \includegraphics[width=\columnwidth]{R_of_f.pdf}
  \caption{Sphere ratio $R(f) = T_0/\Tbar$ versus frequency for skin
  (IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}). $R = 1$ indicates that the
  constant-$T_0$ approximation is exact on the direction-averaged
  quantity; $R < 1$ means $T_0$ underestimates absorbed power and
  $R > 1$ means it overestimates. The dashed horizontal lines mark
  the $\pm 4\%$ band.}
  \label{fig:R-of-f}
\end{figure}

## reviews (figure)


_PaperMaker9000 sweep — 3 flag(s) across 1 lens(es)._

- **figure** — 3 flag(s), 40 cleared:
    - `BOOK_WSRA_figures.conventions.stand_alone` (high): "The dashed horizontal lines mark the $\pm 4\%$ band." → Figure draws only one dashed line at R=1 (ax.axhline(1.0)), no ±4% lines exist; either add dashed lines at R=0.96/1.04 or change caption to describe the single R=1 reference line.
    - `figures.conventions.axis_units` (high): "Frequency $f$ [GHz]" → Square brackets on x-axis but parentheses on right axis ((R-1)x100 (%)) and no unit marker on the dimensionless left axis R(f)=T0/Tbar; pick one bracket style and add (-) to the dimensionless axis.
    - `figures.conventions.scripting_log_ticks` (medium): "ax.set_xlim(0.3, 100)" → X-axis log ticks render as 10^0/10^1/10^2; set explicit linear-readable labels via ax.set_xticks([1,10,100]); ax.set_xticklabels(['1','10','100']).
    - _dismissed_ `figures.conventions.scripting_colour_palette`: Colours are Brewer RdBu (colour-blind safe), semantically diverging blue=conservative/red=non-conservative, and match the paper's other figures (error_budget_comprehensive.py); forcing Wong hexes would break cross-figure consistency without improving legibility, and the main curve is black.
    - _dismissed_ `figures.conventions.scripting_marker_style`: White fill on a white background reads as clean hollow markers at markeredgewidth=0.9; switching to 'none' would expose the black curve as a chord through each circle (busier, not cleaner), so the change is merely different, not better.

## grinder notes
- **label**: fig:R-of-f
- **caption_preview**: Sphere ratio $R(f) = T_0/\Tbar$ versus frequency for skin (IT'IS v$5.0$ Cole--Cole model). $R = 1$ i
