% PREV: \Cref{fig:mie} shows the Mie validation.
% NEXT: # Mie theory on lossy spheres
\begin{figure*}[!t]
  \centering
  \begin{subfigure}[t]{0.48\linewidth}
    \includegraphics[width=\linewidth]{mie_panel_size.pdf}
    \caption{Across size parameter at $28$~GHz.}
    \label{fig:mie:size}
  \end{subfigure}\hfill
  \begin{subfigure}[t]{0.48\linewidth}
    \includegraphics[width=\linewidth]{mie_panel_freq.pdf}
    \caption{Across frequency for four body-part diameters.}
    \label{fig:mie:freq}
  \end{subfigure}
  \caption{Mie validation against lossy spheres with frequency-dependent
  IT'IS skin properties~\cite{ITISv5,Gabriel1996}. (a)~Prediction error versus size parameter
  at $28$~GHz. Vertical dashed lines mark body-part sizes. The
  curve converges from below to the Fresnel limit
  $R_{\mathrm{sphere}}-1\approx -1.2\%$ as $x\to\infty$.
  (b)~Prediction error versus frequency for finger ($17$~mm), arm
  ($80$~mm), head ($180$~mm), and torso ($300$~mm) diameters. The
  wireless mmWave band is shaded green. The orange asymptote is
  $R_{\mathrm{sphere}}(f)-1$, the size-independent Fresnel limit.}
  \label{fig:mie}
\end{figure*}

## reviews (figure)


_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.conventions.scripting_log_ticks` (medium): "ax1.semilogx(x_vals, errors_total, color=CB_BLUE, linewidth=1.8, label='Mie error')" → Panel (a) log x-axis renders 10^1/10^2/10^3; set explicit linear-readable ticks, e.g. ax1.set_xticks([5,10,50,100,500,1000]); ax1.set_xticklabels(['5','10','50','100','500','1000']).
    - _dismissed_ `figures.conventions.axis_units`: x is a named dimensionless ratio whose defining formula pi d / lambda is printed in the label; the two unit-bearing axes ([%], [GHz]) use a consistent square-bracket style, and appending '(-)' to a self-evidently dimensionless defined ratio would add clutter, not clarity.

## grinder notes
- **label**: fig:mie:size
- **caption_preview**: Across size parameter at $28$~GHz.
