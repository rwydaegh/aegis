% PREV: \begin{table*}[!t]
% PREV: \centering
% PREV: \caption{Quantitative comparison of the closed-form prediction to the
% PREV: empirical literature. The shaded sub-$3$~GHz regime, where the
% PREV: layered tissue model in \cref{subsec:fp} replaces $\Tbar$, is
% PREV: excluded.}
% PREV: \label{tab:waterfall}
% PREV: \begin{tabular}{lp{0.36\linewidth}p{0.26\linewidth}p{0.16\linewidth}}
% PREV: \toprule
% PREV: Reference & Empirical observation & Closed-form prediction & Match \\
% PREV: \midrule
% PREV: Flintoft~\cite{Flintoft2014}
% PREV: & $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$ at $7$--$11$~GHz, $60$ volunteers
% PREV: & $T_0(f) = 0.48$ at $9$~GHz, $\Tbar(f) = 0.50$
% PREV: & $2\%$--$4\%$ \\
% PREV: Bamba~\cite{Bamba2014}
% PREV: & $\eta(f) = 0.48$--$0.56$ at $1.45$--$5.8$~GHz, four FDTD ellipsoids
% PREV: & $\Tbar(f) = 0.47$--$0.50$
% PREV: & $3\%$ at $5.8$~GHz; convergent with frequency \\
% PREV: Zhang~\cite{Zhang2017thesis}
% PREV: & $\xi = 0.45$--$0.65$ at $6$--$18$~GHz, $48$ subjects
% PREV: & $\Tbar(f)\cdot\Aab/A = 0.43$--$0.49$
% PREV: & within scatter \\
% PREV: Kodera~\cite{Kodera2024}
% PREV: & $T_{\mathrm{tr}}$ matches $\Aperp$ scaling at $10$--$100$~GHz, parametric FDTD
% PREV: & $T_{\mathrm{tr}} \equiv T_0$
% PREV: & $\le 5\%$ \\
% PREV: Diao~\cite{Diao2024}
% PREV: & $T = 0.52$ at $28$~GHz, anatomical FDTD
% PREV: & $T_0 = 0.536$ at $28$~GHz
% PREV: & $3\%$ \\
% PREV: Flintoft~\cite{Flintoft2014}
% PREV: & $-0.0061\,\mathrm{mm}^{-1}$ slope of $\langle Q^a\rangle$ vs $d_{\mathrm{SF}}$ at $3$~GHz
% PREV: & Layered Fabry--P\'erot in fat
% PREV: & mechanism, qualitative \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table*}
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

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: Passive is the licensed exception: opening with the known 'spread' satisfies old-before-new and parks the new key term $\Aab/A$ in the emphatic end position; the active rewrite would bury the factor mid-sentence.
- **voice-tells** — 2 flag(s), 22 cleared:
    - `style.pet_peeves_wout.no_semicolons` (high): `two reverberation-chamber measurement campaigns; their Fig.~6` -> Split into two sentences: end after 'campaigns.' and start 'Their~Fig.~6 extends...'
    - `style.pet_peeves_wout.no_semicolons` (high): `from a one-dimensional multilayer slab calculation; their homogeneous-skin curve` -> Split into two sentences: end after 'calculation.' and start 'Their homogeneous-skin curve...'
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.tilde_before_refs`: No canonical rule in this lens covers a tie before \eqref/\cref; the in-scope tie rules (tilde_number_unit, tilde_names) are all satisfied (numbers, units, names, and \cite are tied), and a break after 'that' is harmless, so no flaggable canonical rule applies.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

