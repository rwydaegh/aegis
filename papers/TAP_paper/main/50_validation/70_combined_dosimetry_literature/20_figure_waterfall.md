% PREV: The literature comparison maps each reported empirical scalar to the
% PREV: corresponding closed-form quantity. Kodera's transmission coefficient
% PREV: $T_{\mathrm{tr}}$ is compared with the Fresnel transmission used in
% PREV: the one-dimensional reference model. Flintoft's self-shadowing factor
% PREV: $\gamma_s$ is compared with the surface mean of the exposure fraction
% PREV: $\eta(\rr)$. Bamba's efficiency $\eta(f)$ and Zhang's coefficient
% PREV: $\xi$ are compared with the whole-body factor $\Tbar(f)\Aab/A$.
% PREV: The plotted Flintoft points are linear-regression intercepts of
% PREV: $\langle Q^a\rangle$ at $d_{\mathrm{SF}} = 0$ with $\gamma_s =
% PREV: 1$~\cite[Eq.~6]{Flintoft2014}. The plotted Zhang points combine the
% PREV: $6$--$18$~GHz plateau from~\cite[Fig.~4.9]{Zhang2017thesis} with the
% PREV: $1$--$6$~GHz envelope from~\cite[Fig.~4.11]{Zhang2017thesis}.
% PREV: \Cref{fig:waterfall} then compares the closed-form
% PREV: prediction~\eqref{eq:cauchy-exact} against $168$ volunteers and $5$
% PREV: FDTD phantoms from $1$ to $100$~GHz.
% NEXT: \Cref{tab:waterfall} lists the numerical comparisons. Bamba
% NEXT: \textit{et~al.}~\cite{Bamba2014}'s $\eta$ in panel (c) is fit from full-body FDTD on
% NEXT: ellipsoidal phantoms in diffuse-field exposure. Their fit absorbs
% NEXT: creeping-wave and finite-curvature contributions that the
% NEXT: planar-tissue $\Tbar$ omits. Its convergence to $\Tbar$ at
% NEXT: $5.8$~GHz, the upper edge of their calibration range, is the
% NEXT: convergence to the geometric-optics regime predicted by a Mie
% NEXT: analysis of body-scale spheres~\cite{BohrenHuffman1983}. The
% NEXT: $1.45$--$3$~GHz portion of their fit lies outside the
% NEXT: geometric-optics validity window of the present framework
% NEXT: (\cref{tab:bands}). The systematic divergence in panel (c) below
% NEXT: $3$~GHz is the body-Mie regime, not a model failure. Bamba
% NEXT: \textit{et~al.}'s anatomical-phantom validation at $3$~GHz returns
% NEXT: residuals of $-39.4\%$, $-11.7\%$, $+10.7\%$, and $+10.6\%$ on the
% NEXT: Thelonious, Billie, Ella, and Duke phantoms~\cite[Table~7]{Bamba2014}.
% NEXT: The largest divergence is on the smallest phantom. The same
% NEXT: mechanism appears in panel (d) on the Diao \textit{et~al.}~\cite{Diao2024}
% NEXT: TARO sweep (frontal plane wave, vertical polarization, projected area
% NEXT: $0.54$~m$^2$), where $T_{\mathrm{eff}}$ rises from $0.43$ at $10$~GHz
% NEXT: to $0.88$ at $1$~GHz.
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
    - `figures.conventions.axis_units` (high): `Frequency $f$ [GHz]` -> Match bracket conventions across axes: the x-axis uses square brackets [GHz] while the y-axis uses parentheses (1); switch the x-axis to (GHz) to match the (1) dimensionless convention.
    - _dismissed_ `figures.visual_quality.unfilled_markers`: Flintoft (RC measurement anchor) and Wydaeghe (this paper's FDTD) are the only two filled series among ~9; the fill is a deliberate two-tier hierarchy that lets the reader instantly locate the measurement reference and this paper's ground truth, and the filled circles sit in clear regions occluding no underlying curves, so enforcing all-unfilled would erase a useful distinction without improving legibility.

## grinder notes
- **label**: fig:waterfall
- **caption_preview**: Closed-form prediction~\eqref{eq:cauchy-exact
