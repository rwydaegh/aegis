% PREV: Implications for the existing ICNIRP general-public reference level
% NEXT: \begin{table}[!t]
# Whole-body SAR threshold

<!-- AUTO_BEGIN: assembled -->
\subsection{Whole-body SAR threshold}\label{subsec:compl-wb}

The ICNIRP 2020 guidelines~\cite{ICNIRP2020} specify a whole-body
average SAR limit of $0.08$~W/kg for the general public. The bound
$\Aperp(\khat) \le A/2$ on closed surfaces gives
$D(\khat) \le 2A/\Aab$. With $\mathrm{SAR}_{\mathrm{wb}} =
P_{\mathrm{abs}}/m$ and the conservative replacement $\Aab \le A$,
the worst-case threshold is
\begin{equation}\label{eq:Sinc-max-worst}
  \IPD_{\mathrm{max}} = \frac{0.16\,m}{\Tbar\,A}\, ,
\end{equation}
a closed-form function of body mass $m$, body surface area $A$,
and tissue transmission $\Tbar$, none of which requires an FDTD
solve on the specific exposure scenario.

Body surface area follows the Du Bois formula~\cite{DuBois1916} $A
\approx 0.007184\,m^{0.425}\,h^{0.725}$ with mass in kg and height in
cm, so $\IPD_{\mathrm{max}}$ scales as $m/A \propto
\mathrm{BMI}^{0.575}\,h^{0.425}$. \Cref{tab:anthro} evaluates
\eqref{eq:Sinc-max-worst} on a representative population at
$28$~GHz with $\Tbar = 0.543$. The scaling
matches the observation in the dosimetry
literature~\cite{Hirata2007corr,Dimbylow2002} that absorption
cross-section scales with surface area while mass scales with
volume. Section~\ref{si:anthro} of the SI derives the Du Bois
scaling and bounds the linearly polarized worst-case correction to
\eqref{eq:Sinc-max-worst} via the body polarization directivity.

Implications for the existing ICNIRP general-public reference level
above $6$~GHz are stated in \cref{subsec:disc-regulatory}.

\begin{table}[!t]
\centering
\caption{Worst-case compliance threshold across the human
population at $28$~GHz with $\Tbar = 0.543$. The threshold
varies by a factor of about two between an infant and a large adult.}
\label{tab:anthro}
\small
\setlength{\tabcolsep}{3pt}
\begin{tabular}{lccc}
\toprule
Body type & $m$\,[kg] & $h$\,[cm] & $\IPD_{\mathrm{max}}$\,[W/m$^2$] \\
\midrule
Infant ($1$~yr) & 8   & 70  & 6.2  \\
Child ($6$~yr)  & 20  & 110 & 7.6  \\
Adolescent      & 50  & 160 & 9.9  \\
Adult (ref.)    & 70  & 170 & 11.4 \\
Large adult     & 100 & 180 & 13.5 \\
\bottomrule
\end{tabular}
\end{table}
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
