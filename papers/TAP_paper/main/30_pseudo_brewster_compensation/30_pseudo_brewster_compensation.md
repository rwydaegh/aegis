% PREV: The flowchart now moves from the exact local law to its unpolarized
# Pseudo-Brewster compensation

<!-- AUTO_BEGIN: assembled -->
\section{Method: pseudo-Brewster compensation}\label{sec:pB}

As described in the flowchart of~\cref{fig:flowchart}, this section reduces
the exact local law to its unpolarized form. A nearly constant scalar
can replace the Fresnel factor for mmWave tissue, and the reason is
pseudo-Brewster compensation.

\subsection{Mechanism}\label{subsec:pB-mech}

The Brewster angle of a lossless dielectric is $\theta_{\mathrm{B}} =
\arctan(n_2/n_1)$, at which the TM reflection coefficient
vanishes~\cite{BornWolf1999}. For a lossy dielectric the reflection
minimum is finite but small. The angle that minimizes $|r_p|^2$ is
the \textit{pseudo-Brewster angle} and satisfies
$\theta_{\mathrm{pB}} \approx \arctan|\ntilde|$ to within $1^\circ$ for
$|\ntilde| > 3$~\cite{Potter1970,Ohman1977}. At this angle, $T_p$
peaks near $0.95$, whereas $T_s$ has fallen below $0.20$. Their
average $\Tavg(\theta_{\mathrm{pB}}) \approx 0.5$ is close to the
normal-incidence value $T_0 \approx 0.5$--$0.6$ for biological
tissue at mmWave.

Azzam~\cite{Azzam2015} showed that for lossless dielectric substrates
with refractive index $|\ntilde| > 2 + \sqrt{3} \approx 3.73$, the
unpolarized reflectance varies by less than $1\%$ over $[0^\circ,
60^\circ]$. Empirically, the near-constancy extends to $|\ntilde| > 2.5$,
below the strict Azzam threshold. The SI evaluates this extension on
the IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}. Biological tissue at the wireless mmWave
band has $|\ntilde| \in [3, 6]$, putting it in the high-index
regime. This connection between the Azzam criterion and biological dosimetry
has not appeared in the antenna propagation or bioelectromagnetics literature;
prior work has evaluated the angular and polarization
dependence of body transmission above $6$~GHz
numerically~\cite{Samaras2019} without the high-index reduction.

\subsection{Quantitative behavior across angle}\label{subsec:pB-quant}

\Cref{fig:apd-angle} illustrates the compensation for skin at
28~GHz. \Cref{fig:apd-angle:T} shows $T_s$, $T_p$, and $\Tavg$ versus
incidence angle. \Cref{fig:apd-angle:APD} shows the normalized absorbed power
$\APD/\IPD = T(\theta)\cos\theta$ for each polarization and for the
simplified product $T_0\cos\theta$. The unpolarized curve closely
tracks the simplified prediction, and the small gap is the Fresnel
approximation error. $\Tavg/T_0$ is at most $1.056$ across
$[0^\circ,90^\circ]$ on skin at 28~GHz. Below $20^\circ$, the
deviation stays below $0.2\%$.

\begin{figure}[!t]
  \centering
  \begin{subfigure}[t]{\columnwidth}
    % In-figure label renamed to "Pseudo-Brewster angle" and shifted left
    % to clear its arrow; see scripts/apd_direction_analysis.py.
    \includegraphics[width=\linewidth]{apd_angle_panel_T.pdf}
    \caption{Fresnel transmission $T$.}
    \label{fig:apd-angle:T}
  \end{subfigure}\\[2pt]
  \begin{subfigure}[t]{\columnwidth}
    \includegraphics[width=\linewidth]{apd_angle_panel_APD.pdf}
    \caption{Normalized absorbed power $\APD/\IPD$.}
    \label{fig:apd-angle:APD}
  \end{subfigure}
  \caption{Pseudo-Brewster compensation for skin at 28~GHz
  ($\ntilde = 4.49 - 1.79i$, $T_0 = 0.539$). (a)~Fresnel
  power-absorption coefficients $T_s$ (TE), $T_p$ (TM), and
  $\Tavg = \tfrac{1}{2}(T_s + T_p)$ versus incidence angle $\theta$.
  $\Tavg/T_0$ is at most $1.056$ over $[0^\circ,90^\circ]$.
  (b)~Normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$
  for the same three states. The dotted reference is the simplified
  $T_0\cos\theta$ prediction.}
  \label{fig:apd-angle}
\end{figure}

\subsection{Tissue universality}\label{subsec:pB-tissues}

All biological tissues at the wireless mmWave band cluster in the
$|\ntilde| > 2.5$ region where the compensation operates.
\Cref{tab:materials} lists the relevant parameters at 28~GHz from
the IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}. Skin and
muscle have $|\ntilde|$ near $5$ and an angular variation below
$5.6\%$. Water has $|\ntilde| > 6$ and a variation below $4\%$.
Fat is the outlier, with $|\ntilde| \approx 2$ and an $8.2\%$
variation, but fat is rarely the outermost tissue at exposure sites
of regulatory interest. Above $6$~GHz, the relevant outermost
tissues are skin and vitreous humor.

\begin{table}[!t]
\centering
\caption{Pseudo-Brewster compensation across tissue types at
28~GHz. The variation column is the maximum deviation of
$\Tavg/T_0$ from unity over $[0^\circ, 75^\circ]$.}
\label{tab:materials}
\begin{tabular}{lccccc}
\toprule
Tissue & $\varepsilon_r$ & $\sigma$\,[S/m] & $|\ntilde|$ & $T_0$
  & $\Tavg$ var. \\
\midrule
Skin   & 17.0 & 25.0 & 4.84 & 0.54 & $5.6\%$ \\
Muscle & 25.0 & 30.0 & 5.62 & 0.48 & $4.8\%$ \\
Fat    &  4.0 &  2.0 & 2.05 & 0.77 & $8.2\%$ \\
Water  & 25.0 & 55.0 & 6.62 & 0.45 & $3.9\%$ \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Frequency dependence}\label{subsec:pB-freq}

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

\subsection{Geometric absorption law}\label{subsec:pB-geom}

Two simplifications act on the exact law in~\eqref{eq:Sab-exact}.
First, the polarization reduction~\eqref{eq:Sab-Tavg} removes the
angular dependence. Second, we substitute $\Tavg(\theta) \to T_0$ and reinstate
self-shadowing through the binary visibility
$\Vis(\rr,\khat) \in \{0,1\}$. The exact law reduces to the
\textit{geometric absorption law}
\begin{equation}\label{eq:geom-law}
  \boxed{%
    \APD(\rr) \approx \IPD \cdot T_0 \cdot \pospart{\nhat(\rr) \cdot (-\khat)} \cdot
    \Vis(\rr,\khat)
  }\, .
\end{equation}
The tissue physics enters through the scalar $T_0$. The transmission
coefficient $T_{\mathrm{tr}}$ fitted
in~\cite{Kodera2024,Diao2024,Funahashi2018} is identified with $T_0$,
the normal-incidence transmission. All spatial
variation depends on the body shape through the surface-normal field
$\nhat(\rr)$ and the visibility field $\Vis(\rr,\khat)$. For a convex
body, $\Vis \equiv 1$ and~\eqref{eq:geom-law} reduces to the classical
convex form $\IPD\,T_0 \pospart{\nhat\cdot(-\khat)}$.
\Cref{fig:phantom} shows how visibility enters the geometric law on
the Thelonious phantom. Panel~(a) shows the frontal APD map.
Panels~(b) and~(c) show the direction-isotropic exposure fraction
$\eta(\rr)$ from the front and side. Under frontal illumination,
$\Vis$ drops three regions to zero: the medial thighs, the sides of
the torso beneath the arms, and the underside of the jaw.

\begin{figure*}[!t]
  \centering
  \begin{subfigure}[b]{0.30\linewidth}
    \centering
    \censorphantom[0.9\linewidth]{sab_phantom_visible.pdf}%
      {0.324,0.880}{0.499,0.915}{0.289,0.440}{0.443,0.490}
    \caption{$\APD(\rr)$, frontal $\khat$.}
    \label{fig:phantom:sab}
  \end{subfigure}\hfill
  \begin{subfigure}[b]{0.30\linewidth}
    \centering
    \censorphantom[0.9\linewidth]{eta_phantom_front.pdf}%
      {0.282,0.870}{0.429,0.905}{0.289,0.440}{0.443,0.490}
    \caption{$\eta(\rr)$, front view.}
    \label{fig:phantom:eta-front}
  \end{subfigure}\hfill
  \begin{subfigure}[b]{0.30\linewidth}
    \centering
    \censorphantom[0.9\linewidth]{eta_phantom_side.pdf}%
      {0.212,0.870}{0.310,0.905}{0.289,0.440}{0.443,0.490}
    \caption{$\eta(\rr)$, side view.}
    \label{fig:phantom:eta-side}
  \end{subfigure}
  \caption{$\APD$ and $\eta$ maps on the Thelonious phantom (skin
  at 28~GHz, $\IPD = 1$~W/m$^2$,
  area-weighted mean $\bar\eta = 0.865$). (a)~APD
  under frontal illumination $\khat = +\hat{y}$. Front-facing
  triangles absorb at the cosine rate $T_0\,\IPD\,\cos\theta$.
  Self-shadowed elements drop to zero through $\Vis(\rr,\khat)$.
  (b,~c)~Direction-isotropic exposure fraction
  $\eta(\rr) \in [0,1]$ from~\eqref{eq:eta-def}, front and side
  views. Panel~(a) is the integrand of the Cauchy formula along
  one direction. Panels~(b,~c) integrate over the full sphere.}
  \label{fig:phantom}
\end{figure*}

Hence, the error of~\eqref{eq:geom-law} relative to the exact
polarization-aware law is bounded by the maximum of the polarization
correction and the angular variation of $\Tavg$. The latter is below
$5\%$ across the wireless mmWave band (6--100~GHz). The former is below
$2.5\%$ for $N \ge 20$ independent multipath components, and at
most $16\%$ on a real human body for the worst-case linearly
polarized single plane wave. The combined error is below the
$20\%$ uncertainty in tissue dielectric properties at
mmWave~\cite{AlekseevZiskin2007}.

\subsection{Discrete multi-source form}\label{subsec:matrix}

Equation~\eqref{eq:geom-law} extends to a triangle mesh under
multiple incident waves. Discretize the body into $M$ triangles. Row $j$ of
$\mathbf{N} \in \mathbb{R}^{M\times 3}$ holds the outward unit
normal $\nhat_j$. Let $N$ plane waves arrive with unit directions
$\khat_1, \ldots, \khat_N$ and incident power densities
$\IPD_1, \ldots, \IPD_N$.
Stack the directions column-wise into
$\mathbf{K} \in \mathbb{R}^{3\times N}$, with column $i$ equal to
$-\khat_i$. Stack the incident power densities into
$\bm{\mathrm{IPD}} = [\IPD_1,\ldots,\IPD_N]^\top \in \mathbb{R}^N$. Let
$\mathbf{V} \in \{0,1\}^{M\times N}$ be the visibility matrix, with
$V_{ji} = 1$ when direction $\khat_i$ reaches triangle $j$, and
$V_{ji} = 0$ otherwise. Collect the per-triangle APD values into
$\bm{\mathrm{APD}} \in \mathbb{R}^{M}$.

The geometric law on the mesh then reads
\begin{equation}\label{eq:mat-multi}
  \bm{\mathrm{APD}} = T_0\,\bigl(\pospart{\mathbf{N}\,\mathbf{K}}
  \odot \mathbf{V}\bigr)\,\bm{\mathrm{IPD}}\, .
\end{equation}
The cosine matrix $\mathbf{N}\,\mathbf{K} \in \mathbb{R}^{M\times N}$
has entry $(j,i)$ equal to $\nhat_j\cdot(-\khat_i)$. The operator
$\pospart{\cdot} \equiv \max(\cdot,0)$ acts componentwise, and clamps
back-facing entries to zero. The Hadamard product $\odot$ with
$\mathbf{V}$ gates self-shadowed entries. The product with
$\bm{\mathrm{IPD}}$ sums the contributions of the $N$ incident waves.

Each step is differentiable. The operator $\pospart{\cdot}$ is the
rectified linear unit (ReLU). Replacing it with the smooth
\gls{GELU} activation~\cite{Hendrycks2016} leaves the structure
intact and replaces the hard cutoff with a soft rolloff
(\cref{eq:gelu}). Gradients of regulatory quantities with respect to
antenna positions, antenna orientations, and RIS phases propagate
through any differentiable ray tracer~\cite{SionnaRT}. The arithmetic
primitive is the per-pixel shading operation that consumer GPUs run
at sub-millisecond rates, with the cosine gate as rectified shading
and $\mathbf{V}$ as ambient occlusion. For $M \approx 10^4$ and
$N \approx 10^2$, the spatial map is one matrix-vector multiply on
the GPU.
<!-- AUTO_END: assembled -->











## section notes

_(AI-owned notes about this section as a whole)_
