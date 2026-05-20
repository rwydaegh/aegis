% PREV: We validate the theory four ways: (i) Mie theory on lossy spheres,
# Validation

<!-- AUTO_BEGIN: assembled -->
% NEXT: We validate the theory four ways: (i) Mie theory on lossy spheres,
\section{Validation and error analysis}\label{sec:val}

% PREV: \section{Validation and error analysis}\label{sec:val}
% NEXT: # Validation
We validate the theory four ways: (i) Mie theory on lossy spheres,
(ii) full polarization-aware Fresnel calculations on the Thelonious
phantom, (iii) Sim4Life FDTD on the same phantom, and (iv) the
reverberation-chamber and FDTD literature across $168$ volunteers
and $5$ phantoms. The four checks isolate, respectively, the
Fresnel approximation, realistic anatomy, volumetric FDTD agreement,
and population-level scaling. We then add the higher-order corrections
for curvature, diffraction, and inter-body reflection, and close with a
single error budget that propagates the dielectric uncertainty.

% NEXT: Thelonious is a 6-year-old male phantom from the Virtual
\subsection{Configuration}\label{subsec:val-setup}

% PREV: \subsection{Configuration}\label{subsec:val-setup}
% NEXT: # Setup
Thelonious is a 6-year-old male phantom from the Virtual
Population~\cite{ITISv5}, shown in \cref{fig:phantom}. The surface is
a high-resolution triangle mesh with $23{,}826$ faces. Tissue
properties at every frequency follow the tissue-properties
database~\cite{ITISv5,Gabriel1996}. Mie
benchmarks use lossy spheres of skin permittivity at the listed
frequencies, evaluated with the standard recursive series of Bohren
and Huffman~\cite{BohrenHuffman1983}. Sim4Life FDTD runs use the
$0.45$--$5.8$~GHz band on the same Thelonious mesh embedded in a
free-space cube with a perfectly matched layer of $10$ cells, voxel
edge of $1$~mm in the body and graded $1$--$4$~mm outside, and
$12$ plane-wave directions per frequency at two orthogonal
polarizations. Path-level data come from a differentiable
ray-tracer~\cite{SionnaRT} with no roughness model. All scripts and
input geometries that produced the figures in this section are in the
companion code release.

% NEXT: For a lossy sphere of radius $a$ and complex refractive index
\subsection{Mie theory on lossy spheres}\label{subsec:val-mie}

% PREV: \subsection{Mie theory on lossy spheres}\label{subsec:val-mie}
% NEXT: \Cref{fig:mie} shows the Mie validation.
For a lossy sphere of radius $a$ and complex refractive index
$\ntilde$, the Mie series gives an exact solution for the absorption
efficiency $Q_{\mathrm{abs}}$. The geometric law predicts
$P_{\mathrm{abs}} = \IPD\,T_0\,\pi a^2$, so its error is
$(T_0/Q_{\mathrm{abs}} - 1)$. We use skin properties from the
IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency. The total error splits into two
contributions. The Fresnel approximation error is shape- and
frequency-dependent but size-independent. On a sphere it is the
sphere ratio $R = T_0/\langle\Tavg\rangle$, which crosses unity at
approximately $39$~GHz (\cref{fig:R-of-f}). The diffraction error is
size-dependent and scales as $x^{-2/3}$ in the optical regime, where
$x = \pi d/\lambda$ is the size parameter. Diffraction bends waves
into the geometric shadow, adding absorption that the surface law
misses. We refer to the regime where $x$ is small enough that this
diffracted contribution exceeds a few percent of total absorption as
the \emph{body-Mie regime}. For body-scale targets it corresponds to
frequencies below approximately $6$~GHz.

% PREV: For a lossy sphere of radius $a$ and complex refractive index
% NEXT: \begin{figure*}[!t]
\Cref{fig:mie} shows the Mie validation. \Cref{fig:mie}(a) shows
the error versus size parameter at $28$~GHz. It converges from
below towards the Fresnel limit $R_{\mathrm{sphere}} - 1 \approx
-1.2\%$ as $x \to \infty$. \Cref{fig:mie}(b) shows the error versus
frequency for four representative body-part diameters.

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

% PREV: # Mie theory on lossy spheres
For body-relevant sizes (head, torso) over 6--100~GHz, the error ranges
from $0.4\%$ on a torso at $100$~GHz to $14\%$ on a head at
$28$~GHz, set mostly by diffraction into the geometric shadow at
the low end of the band. At $28$~GHz the law underestimates
absorption.
For fingers below 6~GHz, errors exceed $30\%$. On
body-scale objects in the claimed regime, the residual stays within
the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}).
Per-frequency residuals across four body-part diameters ($17$, $80$,
$180$, $300$~mm) are in Table~\ref{tab:mie-residual} of the SI.

% NEXT: The Mie test bounds the Fresnel error on a smooth shape.
\subsection{Full Fresnel on the Thelonious phantom}\label{subsec:val-fresnel}

% PREV: \subsection{Full Fresnel on the Thelonious phantom}\label{subsec:val-fresnel}
% NEXT: \begin{table}[!t]
The Mie test bounds the Fresnel error on a smooth shape. This
section validates the theory on a realistic human body. We compare the simplified
prediction $\APD^{\mathrm{simp}} = \IPD\,T_0 \pospart{\mu}$ against
the full polarization-aware Fresnel integration $\APD^{\mathrm{full}}
= \IPD\,\Teff(\theta, \mathrm{pol}) \pospart{\mu}$ on the Thelonious
mesh ($23\,826$ triangles, $0.787\,\mathrm{m}^2$ surface area). The
incident plane wave comes from above, with skin properties at
$28$~GHz.

% PREV: The Mie test bounds the Fresnel error on a smooth shape.
% NEXT: \Cref{tab:phantom} reports the pointwise comparison.
\begin{table}[!t]
\centering
\caption{Geometric law versus full Fresnel integration on the
Thelonious phantom (skin at $28$~GHz, plane wave from above).}
\label{tab:phantom}
\begin{tabular}{lccc}
\toprule
Metric & Simplified & Full Fresnel & Error \\
\midrule
Mean $\APD$ (illum.)     & $0.185$~W/m$^2$ & $0.186$~W/m$^2$ & $0.5\%$ \\
Peak $\APD$              & $0.539$~W/m$^2$ & $0.539$~W/m$^2$ & $0.0\%$ \\
\bottomrule
\end{tabular}
\end{table}

% PREV: \begin{table}[!t]
% NEXT: # Full Fresnel on the Thelonious phantom
\Cref{tab:phantom} reports the pointwise comparison. For the
$4\,907$ illuminated triangles with
$\theta < 75^\circ$, the local statistics are mean error $-2.6\%$,
root-mean-square $3.2\%$, and range $[-5.3\%, 0.0\%]$. The peak
$\APD$ is recovered exactly because the maximum is at normal incidence,
where $\Teff(0) = T_0$ regardless of polarization. The local error is
below $5.5\%$ everywhere with $\theta < 75^\circ$.
Section~\ref{si:apd-direction} of the SI extends the analysis to
$128$ illumination directions and three polarization states. The
per-direction distribution of total absorbed power clusters around
$T_0\,\Aperp$ within the directional spread set by self-shadowing.

% NEXT: The Mie and Fresnel tests check approximations against analytic and
\subsection{Sim4Life FDTD on the Thelonious phantom}\label{subsec:val-fdtd}

% PREV: \subsection{Sim4Life FDTD on the Thelonious phantom}\label{subsec:val-fdtd}
% NEXT: The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
The Mie and Fresnel tests check approximations against analytic and
semi-analytic ground truths. Full Sim4Life FDTD on the same
Thelonious mesh, matched dielectric properties, and matched
plane-wave excitation completes the comparison. Two regulatory
metrics are evaluated. The first is the IEC/IEEE~63195 peak $\APD$
averaged over a $4$~cm$^2$ patch. At $7$~GHz on three
lateral and frontal incidence directions with $\theta$-polarization,
the direction-averaged ratio of law to FDTD is $1.027$. Propagating a
$\pm 20\%$ uncertainty on the IT'IS dielectric properties~\cite{ITISv5,Gabriel1996} through
the Fresnel coefficient at $7$~GHz gives $\pm 7\%$ on
$T_0$, and the direction-averaged ratio falls inside it. The
per-direction values are $1.06$, $1.20$, and $0.83$. The spread
beyond $\pm 7\%$ reflects FDTD discretization and per-direction
polarization detail in the reference rather than the closed form.

% PREV: The Mie and Fresnel tests check approximations against analytic and
% NEXT: \begin{figure}[!t]
The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
across $12$ directions and $2$ polarizations at $5.8$~GHz. The ratio
of law to FDTD on direction-averaged total absorbed power is
$1.012$, with $\Aab/A = 0.865$ and $\Tbar(f)$ from \cref{tab:Tbar}.
\Cref{fig:val-fdtd} extends the comparison
across $0.45$--$5.8$~GHz.

% PREV: The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
% NEXT: The closed-form Cauchy prediction approaches unity at the upper end
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{fig_kernels_vs_fdtd.pdf}
  \caption{Closed-form prediction versus Sim4Life FDTD on the
  Thelonious phantom. Twelve directions and two polarizations per
  frequency from $0.45$--$5.8$~GHz; error bars show the spread
  across directions. The kernel curves switch on the corrections of
  \cref{subsec:corr-residuals} in sequence: ``Fresnel only'' uses
  $T_s/T_p$ at the convex limit, ``+ polarization'' adds the
  polarization-aware $\Teff$, ``+ curvature \& diffraction'' adds
  the $1/(kR)$ refinement, ``Full kernel'' is the constant-$T_0$
  geometric law without occlusion, ``Full + occlusion'' multiplies
  by $\Vis(\rr,\khat)$. The Cauchy stars are the closed-form
  whole-body identity, giving $1.012$ at $5.8$~GHz. The layered
  $\Tlay$ of \cref{subsec:fp} recovers the
  sub-$6$~GHz dip qualitatively.}
  \label{fig:val-fdtd}
\end{figure}

% PREV: \begin{figure}[!t]
% NEXT: # Sim4Life FDTD on the Thelonious phantom
The closed-form Cauchy prediction approaches unity at the upper end
of the band. Below $6$~GHz the surface law underestimates because
body-scale Mie and resonance effects do not enter a surface-only law,
in line with the Mie analysis on a sphere of comparable size
parameter.

% NEXT: The literature comparison maps each reported empirical scalar to the
\subsection{Combined dosimetry literature}\label{subsec:val-waterfall}

% PREV: \subsection{Combined dosimetry literature}\label{subsec:val-waterfall}
% NEXT: \begin{figure*}[!t]
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

% PREV: \begin{figure*}[!t]
% NEXT: \begin{table*}[!t]
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

% PREV: \Cref{tab:waterfall} lists the numerical comparisons.
% NEXT: Kodera \textit{et~al.}~\cite{Kodera2024} report the closest numerical
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

% PREV: \begin{table*}[!t]
% NEXT: # Combined dosimetry literature
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

% NEXT: The correction box in the flowchart collects the effects left out by
\subsection{Higher-order corrections}\label{subsec:corr-residuals}

% PREV: \subsection{Higher-order residuals}\label{subsec:corr-residuals}
% NEXT: First, we examine the influence of curvature.
The correction box in the flowchart collects the effects left out by
the geometric law. We treat them in turn: curvature, diffraction at
the shadow boundary, and inter-body reflections. The kernel labels in
\cref{fig:val-fdtd} (``Fresnel only,'' ``+ polarization,'' ``+
curvature \& diffraction,'' ``Full kernel,'' ``+ occlusion'') switch
each correction on against the same FDTD reference.

% PREV: The correction box in the flowchart collects the effects left out by
% NEXT: \begin{table}[!t]
First, we examine the influence of curvature. For a surface with
twice the local mean curvature $H = 1/R_1 +
1/R_2$, the first-order Physical Optics correction multiplies the
geometric law by $1 + \mu/(kR_1) + \mu/(kR_2)$, where
$k = 2\pi/\lambda$ is the free-space wavenumber. Since
$\pospart{\mu}\cdot\mu = \pospart{\mu}^2$, the per-triangle update
separates additively,
\begin{equation}\label{eq:curv-update}
  \APD^{(j)} = T_0 \sum_i S_i\!\left[
  \pospart{\mu_{ji}} + \frac{H_j}{k}\,\pospart{\mu_{ji}}^2 \right]
  V_{ji}\, ,
\end{equation}
adding a quadratic gate on top of the linear one. The magnitude is
set by $1/(kR)$. \Cref{tab:curv-mag} lists the correction at
$28$~GHz on representative body parts.

% PREV: First, we examine the influence of curvature.
% NEXT: The correction grows as the wavelength approaches the local
\begin{table}[!t]
\centering
\caption{Curvature correction at $28$~GHz ($k \approx 587$~m$^{-1}$).
The correction is below the Fresnel approximation error for most
body regions and concentrates at small features.}
\label{tab:curv-mag}
\begin{tabular}{lccc}
\toprule
Region & $R$\,[mm] & $1/(kR)$ & Correction \\
\midrule
Torso, head & $> 100$ & $< 0.2\%$ & negligible \\
Arm         & approx.\ $40$ & $0.4\%$ & approx.\ $0.4\%$ \\
Finger      & approx.\ $8$  & $2.1\%$ & approx.\ $2\%$ \\
Ear edge    & approx.\ $2$  & $8.5\%$ & approx.\ $8\%$ \\
\bottomrule
\end{tabular}
\end{table}

% PREV: \begin{table}[!t]
% NEXT: Second, we quantify the effect of diffraction at the shadow boundary.
The correction grows as the wavelength approaches the local
body-part size. At sub-$6$~GHz frequencies the smallest features
have $kR \lesssim 5$ where the correction is no longer small. At
$28$~GHz, only the ear edges and fingertips carry a correction
above the Fresnel error floor.

% PREV: The correction grows as the wavelength approaches the local
% NEXT: Finally, we study the impact of inter-body reflections.
Second, we quantify the effect of diffraction at the shadow boundary.
The sharp $[\cdot]_+$ cutoff at $\mu = 0$ is a geometric-optics
idealization. Diffraction smooths the shadow edge over a Fresnel-zone
width $\sqrt{\lambda R_j}$. The physical activation becomes
\begin{equation}\label{eq:gelu}
  \mu \mapsto \mu\;\tfrac{1}{2}\!\left[1 + \mathrm{erf}(\mu/\sigma_j)\right],
  \qquad \sigma_j = \sqrt{\lambda / (2\pi R_j)}\, .
\end{equation}
The \gls{ICNIRP} centimeter-scale spatial
averaging regularizes the boundary at a length scale larger
than $\sigma_j$ across the wireless band, so the diffraction
correction is significant only for high-resolution local maps or
for comparisons against point measurements. The integrated effect on
whole-body absorbed power on the Thelonious phantom is $1.2\%$ at
$28$~GHz, below $1\%$ above $30$~GHz, and several percent below
$6$~GHz, in line with the Mie analysis on body-scale spheres in
\cref{subsec:val-mie}. Numerical values across $1$--$100$~GHz on
the Thelonious phantom are in Table~\ref{tab:si-diffraction} of the SI.

% PREV: Second, we quantify the effect of diffraction at the shadow boundary.
% NEXT: Two effects keep the body-averaged correction small.
Finally, we study the impact of inter-body reflections. At a surface
point the fraction $T_0$ is absorbed and the remaining
$1 - T_0 \approx 0.46$ is reflected. On a nonconvex body, part of
this reflected power re-illuminates another point and contributes
to absorption that the first-bounce law omits. The radiosity series
gives a multiplier $C(\rr) = 1/(1 - \bar{R}\,f(\rr))$ at each point,
where $\bar{R} = 1 - \Tbar \approx 0.46$ is the flux-weighted
reflectance and $f(\rr) \le 1 - \eta(\rr)$ is the recapture fraction
bounded by the local nonvisible hemisphere area.

% PREV: Finally, we study the impact of inter-body reflections.
Two effects keep the body-averaged correction small. First, the bound
$f \le 1 - \eta$ self-compensates: deep concavities ($\eta$ low) have
a high recapture fraction ($f$ high), so the product $\eta\cdot C$
varies much less than $\eta$ alone. Second, specular reflection at
mmWave (skin meets the Rayleigh roughness criterion) reduces $f$ by
roughly a factor of three relative to the diffuse bound. On the
Thelonious phantom at $28$~GHz, the area-weighted recapture fraction is
$f_{\mathrm{global}} \approx 0.09$ under the diffuse bound, giving
$C \approx 1.04$. The specular estimate brings this to
$C \approx 1.01$. The body-averaged correction stays below $2\%$,
smaller than the propagated dielectric uncertainty derived in
\cref{subsec:corr-summary}. The convex-hull energy bound
$\langle P_{\mathrm{abs}}\rangle \le \IPD\,A_{\mathrm{CH}}/4$
brackets the true absorbed power within
$A_{\mathrm{CH}}/A \approx 1.20$ on Thelonious.

% NEXT: \Cref{fig:err-budget} reports two regimes side by side at $28$~GHz on
\subsection{Error budget}\label{subsec:corr-summary}

% PREV: \subsection{Error budget}\label{subsec:corr-summary}
% NEXT: \begin{figure}[!t]
\Cref{fig:err-budget} reports two regimes side by side at $28$~GHz on
skin. The worst case is single body part, single direction, pointwise
local. The typical case is whole-body integrated, direction-averaged.
The dielectric input spread is $\pm 20\%$ on $\varepsilon_r$ and
$\sigma$. This is the inter-model gap between Gabriel
\textit{et~al.}~\cite{Gabriel1996} and the empirical
Gabriel-times-$1.2$ fit that Christ \textit{et~al.}~\cite{Christ2021}
obtained from $S_{11}$ measurements on $37$ volunteers at
$40$--$110$~GHz. The spread is consistent with mmWave dielectric
campaigns more
broadly~\cite{AlekseevZiskin2007,Sasaki2014,Zhadobov2011}.
We evaluate $T_0 = 4n/[(1+n)^2+\kappa^2]$ at the four corners of the
$\pm 20\%$ box. The largest deviation on skin at $28$~GHz is
$\pm 7\%$. The Fresnel approximation worst case is $5.3\%$ pointwise
local (\cref{tab:phantom}). The typical case is $1.2\%$
direction-averaged on whole-body absorbed power (Supplementary
Information, $128$-direction sweep). The diffraction worst case is
$10\%$ on a torso-scale Mie sphere (\cref{subsec:val-mie}). The
typical case is $1.2\%$ integrated on Thelonious (Supplementary
Information, GELU integration). The inter-body reflection worst
case is $4\%$ under the diffuse bound. The typical case is $1\%$
under specular at mmWave (\cref{subsec:corr-residuals}). In the
typical case every model error stays below the dielectric uncertainty.

% PREV: \Cref{fig:err-budget} reports two regimes side by side at $28$~GHz on
\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{error_budget_comprehensive.pdf}
  \caption{Error budget for the geometric law in two regimes at
  $28$~GHz on skin. Worst case is single body part, single direction,
  pointwise. Typical case is whole-body integrated,
  direction-averaged. Only the dielectric uncertainty stays large in
  the typical case.}
  \label{fig:err-budget}
\end{figure}
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
