% PREV: Kodera \textit{et~al.}~\cite{Kodera2024} report the closest numerical
# Combined dosimetry literature

<!-- AUTO_BEGIN: assembled -->
\subsection{Combined dosimetry literature}\label{subsec:val-waterfall}

The literature comparison maps each reported empirical scalar to the
corresponding closed-form quantity. Kodera's transmission coefficient
$T_{\mathrm{tr}}$ is compared with the Fresnel transmission used in
the one-dimensional reference model. Flintoft's self-shadowing factor
$\gamma_s$ is compared with the surface mean of the exposure fraction
$\eta(\rr)$. Bamba's efficiency $\eta(f)$ and Zhang's coefficient
$\xi$ are compared with the whole-body factor $\Tbar(f)\Aab/A$.
The plotted Flintoft points are linear-regression intercepts of
$\langle Q^a\rangle$ at $d_{\mathrm{SF}} = 0$ with $\gamma_s =
1$~\cite[Eq.~6]{Flintoft2014}. The plotted Zhang points combine the
$6$--$18$~GHz plateau from~\cite[Fig.~4.9]{Zhang2017thesis} with the
$1$--$6$~GHz envelope from~\cite[Fig.~4.11]{Zhang2017thesis}.
\Cref{fig:waterfall} then compares the closed-form
prediction~\eqref{eq:cauchy-exact} against $168$ volunteers and $5$
FDTD phantoms from $1$ to $100$~GHz.

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

\Cref{tab:waterfall} lists the numerical comparisons. Bamba
\textit{et~al.}~\cite{Bamba2014}'s $\eta$ in panel (c) is fit from full-body FDTD on
ellipsoidal phantoms in diffuse-field exposure. Their fit absorbs
creeping-wave and finite-curvature contributions that the
planar-tissue $\Tbar$ omits. Its convergence to $\Tbar$ at
$5.8$~GHz, the upper edge of their calibration range, is the
convergence to the geometric-optics regime predicted by a Mie
analysis of body-scale spheres~\cite{BohrenHuffman1983}. The
$1.45$--$3$~GHz portion of their fit lies outside the
geometric-optics validity window of the present framework
(\cref{tab:bands}). The systematic divergence in panel (c) below
$3$~GHz is the body-Mie regime, not a model failure. Bamba
\textit{et~al.}'s anatomical-phantom validation at $3$~GHz returns
residuals of $-39.4\%$, $-11.7\%$, $+10.7\%$, and $+10.6\%$ on the
Thelonious, Billie, Ella, and Duke phantoms~\cite[Table~7]{Bamba2014}.
The largest divergence is on the smallest phantom. The same
mechanism appears in panel (d) on the Diao \textit{et~al.}~\cite{Diao2024}
TARO sweep (frontal plane wave, vertical polarization, projected area
$0.54$~m$^2$), where $T_{\mathrm{eff}}$ rises from $0.43$ at $10$~GHz
to $0.88$ at $1$~GHz.

\begin{table*}[!t]
\centering
\caption{Quantitative comparison of the closed-form prediction to the
empirical literature. The shaded sub-$3$~GHz regime, where the
layered tissue model in \cref{subsec:fp} replaces $\Tbar$, is
excluded.}
\label{tab:waterfall}
\begin{tabular}{lp{0.36\linewidth}p{0.26\linewidth}p{0.16\linewidth}}
\toprule
Reference & Empirical observation & Closed-form prediction & Match \\
\midrule
Flintoft~\cite{Flintoft2014}
& $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$ at $7$--$11$~GHz, $60$ volunteers
& $T_0(f) = 0.48$ at $9$~GHz, $\Tbar(f) = 0.50$
& $2\%$--$4\%$ \\
Bamba~\cite{Bamba2014}
& $\eta(f) = 0.48$--$0.56$ at $1.45$--$5.8$~GHz, four FDTD ellipsoids
& $\Tbar(f) = 0.47$--$0.50$
& $3\%$ at $5.8$~GHz; convergent with frequency \\
Zhang~\cite{Zhang2017thesis}
& $\xi = 0.45$--$0.65$ at $6$--$18$~GHz, $48$ subjects
& $\Tbar(f)\cdot\Aab/A = 0.43$--$0.49$
& within scatter \\
Kodera~\cite{Kodera2024}
& $T_{\mathrm{tr}}$ matches $\Aperp$ scaling at $10$--$100$~GHz, parametric FDTD
& $T_{\mathrm{tr}} \equiv T_0$
& $\le 5\%$ \\
Diao~\cite{Diao2024}
& $T = 0.52$ at $28$~GHz, anatomical FDTD
& $T_0 = 0.536$ at $28$~GHz
& $3\%$ \\
Flintoft~\cite{Flintoft2014}
& $-0.0061\,\mathrm{mm}^{-1}$ slope of $\langle Q^a\rangle$ vs $d_{\mathrm{SF}}$ at $3$~GHz
& Layered Fabry--P\'erot in fat
& mechanism, qualitative \\
\bottomrule
\end{tabular}
\end{table*}

Kodera \textit{et~al.}~\cite{Kodera2024} report the closest numerical
counterpart to the present analysis. Their Fig.~13 compiles
whole-body absorbed SAR data over $1$--$10$~GHz at
$\IPD = 10$~W/m$^2$ across nine prior numerical phantom studies and
two reverberation-chamber measurement campaigns; their Fig.~6
extends the same comparison to $1$--$100$~GHz on five parametric
layered models (Models~I--V). The compilation shows the asymptotic
plateau that \eqref{eq:cauchy-exact} predicts. Kodera
\textit{et~al.}\ fit a study-specific $T_{\mathrm{tr}}$ per phantom
and frequency from a one-dimensional multilayer slab calculation;
their homogeneous-skin curve (Fig.~9, right axis) reproduces the
Fresnel $T_0$ within $1$--$2\%$ above $6$~GHz, and oscillates around
that value below $6$~GHz with a multilayer Fabry--P\'erot pattern of
the same form as the layered transmission $\Tlay$ in
\cref{subsec:fp}. \Cref{eq:cauchy-exact} supplies the closed-form
$T_{\mathrm{tr}} \to \Tbar(f)$ that all phantoms converge to in the
geometric-optics regime. The residual phantom-to-phantom spread is
set by the body-shape factor $\Aab/A$.
<!-- AUTO_END: assembled -->







## section notes

_(AI-owned notes about this section as a whole)_
