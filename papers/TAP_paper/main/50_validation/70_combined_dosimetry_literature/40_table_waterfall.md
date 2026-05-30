% PREV: \Cref{tab:waterfall} lists the numerical comparisons. Bamba
% PREV: \textit{et~al.}~\cite{Bamba2014}'s $\eta$ in panel (c) is fit from full-body FDTD on
% PREV: ellipsoidal phantoms in diffuse-field exposure. Their fit absorbs
% PREV: creeping-wave and finite-curvature contributions that the
% PREV: planar-tissue $\Tbar$ omits. Its convergence to $\Tbar$ at
% PREV: $5.8$~GHz, the upper edge of their calibration range, is the
% PREV: convergence to the geometric-optics regime predicted by a Mie
% PREV: analysis of body-scale spheres~\cite{BohrenHuffman1983}. The
% PREV: $1.45$--$3$~GHz portion of their fit lies outside the
% PREV: geometric-optics validity window of the present framework
% PREV: (\cref{tab:bands}). The systematic divergence in panel (c) below
% PREV: $3$~GHz is the body-Mie regime, not a model failure. Bamba
% PREV: \textit{et~al.}'s anatomical-phantom validation at $3$~GHz returns
% PREV: residuals of $-39.4\%$, $-11.7\%$, $+10.7\%$, and $+10.6\%$ on the
% PREV: Thelonious, Billie, Ella, and Duke phantoms~\cite[Table~7]{Bamba2014}.
% PREV: The largest divergence is on the smallest phantom. The same
% PREV: mechanism appears in panel (d) on the Diao \textit{et~al.}~\cite{Diao2024}
% PREV: TARO sweep (frontal plane wave, vertical polarization, projected area
% PREV: $0.54$~m$^2$), where $T_{\mathrm{eff}}$ rises from $0.43$ at $10$~GHz
% PREV: to $0.88$ at $1$~GHz.
% NEXT: Kodera \textit{et~al.}~\cite{Kodera2024} report the closest numerical
% NEXT: counterpart to the present analysis. Their Fig.~13 compiles
% NEXT: whole-body absorbed SAR data over $1$--$10$~GHz at
% NEXT: $\IPD = 10$~W/m$^2$ across nine prior numerical phantom studies and
% NEXT: two reverberation-chamber measurement campaigns; their Fig.~6
% NEXT: extends the same comparison to $1$--$100$~GHz on five parametric
% NEXT: layered models (Models~I--V). The compilation shows the asymptotic
% NEXT: plateau that \eqref{eq:cauchy-exact} predicts. Kodera
% NEXT: \textit{et~al.}\ fit a study-specific $T_{\mathrm{tr}}$ per phantom
% NEXT: and frequency from a one-dimensional multilayer slab calculation;
% NEXT: their homogeneous-skin curve (Fig.~9, right axis) reproduces the
% NEXT: Fresnel $T_0$ within $1$--$2\%$ above $6$~GHz, and oscillates around
% NEXT: that value below $6$~GHz with a multilayer Fabry--P\'erot pattern of
% NEXT: the same form as the layered transmission $\Tlay$ in
% NEXT: \cref{subsec:fp}. \Cref{eq:cauchy-exact} supplies the closed-form
% NEXT: $T_{\mathrm{tr}} \to \Tbar(f)$ that all phantoms converge to in the
% NEXT: geometric-optics regime. The residual phantom-to-phantom spread is
% NEXT: set by the body-shape factor $\Aab/A$.
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

## reviews (table)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **table** — pass (10 rules cleared).

## grinder notes
- **label**: tab:waterfall
- **caption_preview**: Quantitative comparison of the closed-form prediction to the empirical literature. The shaded sub-$3
