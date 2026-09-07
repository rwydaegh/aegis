% PREV: \section{Discussion}\label{sec:disc}
# Discussion

<!-- AUTO_BEGIN: assembled -->
\section{Discussion}\label{sec:disc}

\subsection{Computational structure}\label{subsec:disc-primitives}

The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
rectified-linear `network' whose weights are the path directions and
powers from a ray tracer~\cite{SionnaRT}. Three properties follow.

First, the network is differentiable in every input. The smooth
\gls{GELU} activation~\eqref{eq:gelu} replaces the hard $[\cdot]_+$
gate, preserving the chain rule. Gradients of
regulatory quantities propagate to antenna positions, antenna
orientations, beam codebooks, and reconfigurable-intelligent-surface
phases through standard backpropagation.
End-to-end exposure assessment in current practice requires a
per-scenario FDTD evaluation on the user phantom as the back-end
step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
replacing that step, exposure-constrained network design becomes a
continuous optimization problem, because of a speed increase and the
availability of gradients on each differentiable computation.

Second, the per-triangle absorbed-power map for $M \approx 10^4$ triangles\footnote{Note
that the number of triangles is arbitrary. As long as the geometric shadow is
kept constant, $\mathrm{SAR}_{\mathrm{wb}}$ results will not change. A correct
validation with FDTD requires similar geometric accuracy of the underlying
mesh.}
and $N \approx 10^2$ paths is one matrix-vector multiply on
a modern GPU, evaluated in under $10$~ms. The cost is independent of
frequency. Against an FDTD reference whose cost scales as $f^4$, the
speed advantage grows by roughly $10^4$ from $6$ to $60$~GHz, exactly
the band where the Fresnel approximation is sharpest and the closed
form holds pointwise within $3\%$ of FDTD (\cref{tab:bands}). The
cosine gate is rectified shading. The visibility matrix $\mathbf{V}$
is ambient occlusion, one of the most optimized computations in
real-time rendering~\cite{AkenineMoller2018}.

Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
body dependence into a single scalar $\Aab = \bar\eta\,A$. For a
given phantom and posture, $\bar\eta$ is computed once, in tens of
milliseconds, and cached. Population studies that previously
required one FDTD solve per body and per direction reduce to one
Fresnel quadrature shared across the population and one occlusion
pass per body.

We highlight three potential applications. First, dosimetry can be
computed in real time, because each evaluation takes about $10$~ms,
well below the timescale on which the body pose and environment
change, given an accurate digital twin of both. Second, exposure
metrics can be optimized under design constraints, because the method
is differentiable end to end. Third, large-scale dosimetric assessment
across diverse populations is possible and useful at the city scale,
e.g., for epidemiological studies such as the GOLIAT
project~\cite{Goliat}.

\subsection{Regulatory implications}\label{subsec:disc-regulatory}

Whole-body ICNIRP compliance reduces to one inequality on three
precomputed scalars (\cref{eq:Sinc-max-worst}). The same algebra
evaluates the existing reference levels for under- or over-protection
across the population without an FDTD campaign. The ICNIRP
general-public reference level above $6$~GHz is
$10$~W/m$^2$~\cite{ICNIRP2020}. Reference levels are the
operationally measured incident-power-density limits intended to
imply compliance with the underlying basic restriction, here
$0.08\,\mathrm{W/kg}$ whole-body SAR. Setting $\IPD_{\mathrm{max}} =
10$~W/m$^2$ in~\eqref{eq:Sinc-max-worst} returns the threshold
$m/A \geq 33.9$~kg/m$^2$ at $\Tbar = 0.543$ ($28$~GHz on skin).
\Cref{tab:anthro} lists $\IPD_{\mathrm{max}}$ values of $6.2$,
$7.6$, and $9.9$~W/m$^2$ for the infant, the six-year-old child, and
the adolescent under the worst-case directional bound
$D \le 2A_{\mathrm{CH}}/\Aab$. The reference level exceeds these
thresholds by $61\%$, $32\%$, and $1\%$ respectively. The closed form
certifies that the existing reference level fails the basic
restriction for the three smaller body sizes under worst-case
directional exposure. Under realistic plane-wave or multipath
exposure, the directivity is below this worst case, and the basic
restriction is met~\cite{ICNIRP2020}. The closed form makes both the
worst-case and the directional-average evaluation explicit.

\subsection{Regime of validity}\label{subsec:disc-validity}

\Cref{tab:bands} summarizes the validity by frequency band.
Equations~\eqref{eq:geom-law} and~\eqref{eq:cauchy-exact} hold
quantitatively above approximately $1$~GHz on whole-body absorbed
power and above approximately $6$~GHz pointwise on the surface, with
documented sub-$6$~GHz behavior from~\eqref{eq:T-lay}. The
low-frequency boundary is set by three independent physical scales:
body opacity, the body-scale Mie regime, and whole-body resonance.
The high-frequency boundary is set by two, the softening of the
pseudo-Brewster compensation and skin surface roughness, both gentler
than the low-frequency boundary.

The surface law requires the body to be optically thick to the
incident wave: the tissue skin depth must stay smaller than the body
characteristic dimension, otherwise the wave passes through rather
than being absorbed at the surface. This opacity criterion places
the lower validity limit near $700$~MHz--$1$~GHz for limbs and near
$250$~MHz for a torso. The tissue-property
database~\cite{Gabriel1996} gives muscle skin-depth values that
exceed limb cross-sections below approximately $1$~GHz and torso
cross-sections below approximately $250$~MHz.

The Mie regime sets a second lower limit. The geometric-optics
asymptote holds with sub-percent residual once $ka \gtrsim 30$ on a
body characteristic dimension, and \cref{subsec:val-mie} quantifies
the residual on body-scale spheres. Whole-body resonance dominates
below approximately~$300$~MHz, where the body acts as a half-wave
dipole and surface absorbed power is unrelated to internal
hot-spots~\cite{Durney1986}. Below this frequency the framework
reduces to volumetric solvers.

\begin{table}[!t]
\centering
\caption{Frequency-band limits of~\eqref{eq:cauchy-exact} on a
human-adult body. Quantitative validity covers $1$--$100$~GHz on
whole-body absorbed power, $6$--$100$~GHz pointwise on the
surface.}
\label{tab:bands}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.18\linewidth}
                  >{\raggedright\arraybackslash}p{0.42\linewidth}
                  >{\raggedright\arraybackslash}p{0.30\linewidth}@{}}
\toprule
Band & Surface law status & Whole-body identity \\
\midrule
below $300$~MHz
  & other physics: resonance and hot-spots
  & FDTD required \\
$0.3$--$1$~GHz
  & qualitative, $10\%$--$30\%$ Mie underestimate
  & qualitative, $\Tlay$ recovers the dip \\
$1$--$6$~GHz
  & integrated within $5\%$--$10\%$, local map loses pointwise meaning
  & quantitative, $\Tlay$ replaces $T_0$ \\
$6$--$100$~GHz
  & quantitative within $3\%$ pointwise
  & quantitative, Brewster compensation sharpest \\
\bottomrule
\end{tabular}
\end{table}

The pseudo-Brewster compensation weakens above $200$--$250$~GHz,
where the Azzam high-index criterion $|\ntilde| > 2.5$ weakens and
worst-case angular variation grows from $5.6\%$ at $28$~GHz to
approximately $10\%$ at $250$~GHz and $15\%$ at $300$~GHz, comparable
to the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}). The
skin refractive-index modulus from the IT'IS database~\cite{ITISv5,Gabriel1996} is $4.84$ at $28$~GHz,
$3.68$ at $60$~GHz, and $3.01$ at $100$~GHz, and extrapolation puts
$|\ntilde|$ near $2.5$ around $200$--$250$~GHz, approximately $2.2$
at $300$~GHz, and $1.8$--$2$ at $1$~THz.

Skin roughness sets an upper limit near $1$~THz, where the Rayleigh
criterion $h\cos\theta/\lambda < 1/8$ is violated on
papillary-ridge-scale features and diffuse scattering becomes the
dominant correction. Skin features stratify into
stratum-corneum microtexture at $10$--$100\,\mu$m, papillary ridges
at $0.4$--$0.5$~mm spacing, and gross body curvature at centimeters.
The wavelength is $3$~mm at $100$~GHz, $1$~mm at $300$~GHz, $0.3$~mm at
$1$~THz. The Rayleigh criterion is met at $100$~GHz on ridge-scale
features and is marginal at $300$~GHz.

For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
$1.7$~mm at $28$~GHz), evanescent waves and antenna-body impedance
coupling require full-wave simulation. Outside this regime, the law
applies pointwise with spatially varying inputs.

Measurements place the dielectric properties of biological tissue
within approximately $20\%$ at mmWave~\cite{AlekseevZiskin2007}. This
input uncertainty produces $\pm 7\%$ on $T_0$ through the sublinear
propagation derived in \cref{subsec:corr-summary}, and it dominates
the error budget at every operating regime where the surface law
applies.
<!-- AUTO_END: assembled -->









## section notes

_(AI-owned notes about this section as a whole)_
