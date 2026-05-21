% PREV: The literature comparison maps each reported empirical scalar to the
% NEXT: \Cref{tab:waterfall} lists the numerical comparisons.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\linewidth]{lit_waterfall_combined.pdf}
  \caption{Closed-form prediction~\eqref{eq:cauchy-exact} compared
  with direction-averaged whole-body absorption ratios from the
  dosimetry literature. The thick black line uses the
  population-averaged layered transmission, the thin black line is the
  geometric-optics asymptote $\Tbar(f)\Aab/A$, and the dotted line is
  the normal-incidence reference $T_0(f)\Aab/A$. The gray band shows
  the layered-transmission envelope for subcutaneous-fat thicknesses
  $d_{\mathrm{SF}}\in[2,30]$~mm. Error bars are standard errors of the
  mean. The inset gives framework validity by frequency band.}
  \label{fig:waterfall}
\end{figure*}

## reviews (figure)


_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.conventions.axis_units` (high): "Frequency $f$ [GHz]" → Match bracket conventions across axes: the x-axis uses square brackets [GHz] while the y-axis uses parentheses (1); switch the x-axis to (GHz) to match the (1) dimensionless convention.
    - _dismissed_ `figures.visual_quality.unfilled_markers`: Flintoft (RC measurement anchor) and Wydaeghe (this paper's FDTD) are the only two filled series among ~9; the fill is a deliberate two-tier hierarchy that lets the reader instantly locate the measurement reference and this paper's ground truth, and the filled circles sit in clear regions occluding no underlying curves, so enforcing all-unfilled would erase a useful distinction without improving legibility.

## grinder notes
- **label**: fig:waterfall
- **caption_preview**: Closed-form prediction~\eqref{eq:cauchy-exact
