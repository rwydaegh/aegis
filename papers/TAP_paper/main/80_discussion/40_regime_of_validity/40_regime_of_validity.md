% PREV: Whole-body resonance dominates below approximately $300$~MHz, where
% NEXT: \begin{table}[!t]
# Regime of validity

<!-- AUTO_BEGIN: assembled -->
% NEXT: \Cref{tab:bands} summarizes the resulting band stratification.
\subsection{Regime of validity}\label{subsec:disc-validity}

% PREV: \subsection{Regime of validity}\label{subsec:disc-validity}
% NEXT: Equations~\eqref{eq:geom-law} and~\eqref{eq:cauchy-exact} hold
\Cref{tab:bands} summarizes the resulting band stratification.

% PREV: \Cref{tab:bands} summarizes the resulting band stratification.
% NEXT: The surface law requires the body to be optically thick to the
Equations~\eqref{eq:geom-law} and~\eqref{eq:cauchy-exact} hold
quantitatively above approximately $1$~GHz on whole-body absorbed
power and above approximately $6$~GHz pointwise on the surface, with
documented sub-$6$~GHz behavior from~\eqref{eq:T-lay}. The
low-frequency boundary is set by three independent physical scales:
body opacity, the body-scale Mie regime, and whole-body resonance.
The high-frequency boundary is set by two, the softening of the
pseudo-Brewster compensation and skin surface roughness, both gentler
than the low-frequency boundary.

% PREV: Equations~\eqref{eq:geom-law} and~\eqref{eq:cauchy-exact} hold
% NEXT: The Mie regime sets a second lower limit.
The surface law requires the body to be optically thick to the
incident wave: the tissue skin depth must stay smaller than the body
characteristic dimension, otherwise the wave passes through rather
than being absorbed at the surface. This opacity criterion places
the lower validity limit near $700$~MHz--$1$~GHz for limbs and near
$250$~MHz for a torso. The tissue-property
database~\cite{Gabriel1996} gives muscle skin-depth values that
exceed limb cross-sections below approximately $1$~GHz and torso
cross-sections below approximately $250$~MHz.

% PREV: The surface law requires the body to be optically thick to the
% NEXT: Whole-body resonance dominates below approximately $300$~MHz, where
The Mie regime sets a second lower limit. The geometric-optics
asymptote holds with sub-percent residual once $ka \gtrsim 30$ on a
body characteristic dimension, and \cref{subsec:val-mie} quantifies
the residual on body-scale spheres.

% PREV: The Mie regime sets a second lower limit.
% NEXT: # Regime of validity
Whole-body resonance dominates below approximately $300$~MHz, where
the body acts as a half-wave dipole and surface absorbed power is
unrelated to internal hot-spots~\cite{Durney1986}. Below this
frequency the framework reduces to volumetric solvers.

% PREV: # Regime of validity
% NEXT: The pseudo-Brewster compensation softens above $200$--$250$~GHz,
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

% PREV: \begin{table}[!t]
% NEXT: Skin roughness sets an upper limit near $1$~THz, where the Rayleigh
The pseudo-Brewster compensation softens above $200$--$250$~GHz,
where the Azzam high-index criterion $|\ntilde| > 2.5$ weakens and
worst-case angular variation grows from $5.6\%$ at $28$~GHz to
approximately $10\%$ at $250$~GHz and $15\%$ at $300$~GHz, comparable
to the dielectric uncertainty on $T_0$ (\cref{fig:err-budget}). Skin
refractive-index modulus from the IT'IS database~\cite{ITISv5,Gabriel1996} is $4.84$ at $28$~GHz,
$3.68$ at $60$~GHz, and $3.01$ at $100$~GHz, and extrapolation puts
$|\ntilde|$ near $2.5$ around $200$--$250$~GHz, approximately $2.2$
at $300$~GHz, and $1.8$--$2$ at $1$~THz.

% PREV: The pseudo-Brewster compensation softens above $200$--$250$~GHz,
% NEXT: For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
Skin roughness sets an upper limit near $1$~THz, where the Rayleigh
criterion $h\cos\theta/\lambda < 1/8$ is violated on
papillary-ridge-scale features and diffuse scattering becomes the
dominant correction. Skin features are stratified into
stratum-corneum microtexture at $10$--$100\,\mu$m, papillary ridges
at $0.4$--$0.5$~mm spacing, and gross body curvature at centimeters.
Wavelength is $3$~mm at $100$~GHz, $1$~mm at $300$~GHz, $0.3$~mm at
$1$~THz. The Rayleigh criterion is met at $100$~GHz on ridge-scale
features and is marginal at $300$~GHz.

% PREV: Skin roughness sets an upper limit near $1$~THz, where the Rayleigh
% NEXT: The dielectric properties of biological tissue have been measured to
For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
$1.7$~mm at $28$~GHz), evanescent waves and antenna-body impedance
coupling require full-wave simulation. Outside this regime, the law
applies pointwise with spatially varying inputs.

% PREV: For sources in the reactive near field ($d < \lambda/(2\pi)$, that is
The dielectric properties of biological tissue have been measured to
within approximately $20\%$ at mmWave~\cite{AlekseevZiskin2007}. This
input uncertainty produces $\pm 7\%$ on $T_0$ through the sublinear
propagation derived in \cref{subsec:corr-summary}, and it dominates
the error budget at every operating regime where the surface law
applies.
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
