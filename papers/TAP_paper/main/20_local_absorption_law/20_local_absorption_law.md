# Local absorption law

<!-- AUTO_BEGIN: assembled -->
\section{Method: local absorption law}\label{sec:law}

Flowchart~\ref{fig:flowchart} shows the exact local law, the
reductions to whole-body absorbed power, the higher-order
corrections, and the regulatory outputs. This section derives the top
box: the local law at one visible surface point.

\begin{figure}[!t]
  \centering
  \begin{tikzpicture}[
    every node/.style={font=\footnotesize},
    box/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=9mm, minimum width=33mm,
                fill=white, align=center, font=\footnotesize},
    sub6/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=8mm, minimum width=28mm,
                fill=black!4, align=center, font=\footnotesize},
    outbox/.style={draw=black, line width=0.5pt, rectangle,
                inner sep=2pt, minimum height=9mm, minimum width=30mm,
                align=center, font=\footnotesize},
    smallout/.style={draw=black, line width=0.4pt, rectangle,
                inner sep=1.5pt, minimum height=5mm, minimum width=24mm,
                align=center, font=\scriptsize},
    inputs/.style={draw=black, line width=0.4pt, rectangle, dashed,
                inner sep=4pt, text width=25mm, align=left,
                font=\footnotesize, fill=white},
    corrbox/.style={draw=black, line width=0.4pt, rectangle, dashed,
                inner sep=2.5pt, text width=29mm, align=center,
                font=\scriptsize\itshape, fill=white},
    arrow/.style={->, line width=0.45pt, >=Latex},
    smallarrow/.style={->, line width=0.4pt, >=Latex,
                rounded corners=0.6pt},
    tag/.style={font=\scriptsize\itshape, align=center,
                fill=white, inner sep=0.6pt}
  ]
    % Spine
    \node[box] (exact) at (1.5, 0)     {Exact law\\$\APD\!=\!\IPD\,T_{\mathrm{eff}}\,\pospart{\mu}\,\Vis$};
    \node[box] (avg)   at (1.5, -1.30) {Unpolarized\\$\APD\!=\!\IPD\,\Tavg\,\pospart{\mu}\,\Vis$};
    \node[box] (geom)  at (1.5, -2.65) {Geometric\\$\APD\!=\!\IPD\,T_0\,\pospart{\mu}\,\Vis$};
    \node[box] (whole) at (1.5, -5.85) {Whole-body\\$\langle P_{\mathrm{abs}}\rangle\!=\!\IPD\,\Tbar\,\Aab/4$};

    % Sub-6 GHz inside Formula
    \node[sub6] (layered) at (2.25, -4.30) {Sub-6\,GHz\\$T_0\!\to\!\Tlay(f)$};

    % Outputs
    \node[outbox, fill=outA] (outLocal) at (6.5, -2.65) {Local $\APDAvg$};
    \node[smallout, fill=outA!60] (outLocalPeak) at (6.75, -3.42) {Peak $\APDAvg$};
    \node[outbox, fill=outC] (outCube) at (6.5, -4.30) {$\mathrm{SAR}_{10\mathrm{g}}$};
    \node[smallout, fill=outC!60] (outCubePeak) at (6.75, -5.07) {$\mathrm{psSAR}_{10\mathrm{g}}$};
    \node[outbox, fill=outB] (outWB) at (6.5, -5.85) {$\mathrm{SAR}_{\mathrm{wb}}$};

    % Spine arrows top three
    \draw[arrow] (exact) -- node[tag,right=2pt] {Three conditions} (avg);
    \draw[arrow] (avg)   -- node[tag,right=2pt] {Pseudo-Brewster}   (geom);

    % Geom -> Whole at 1/4 width
    \coordinate (geom_q1) at ($(geom.south west)!0.25!(geom.south east)$);
    \coordinate (whole_q1) at ($(whole.north west)!0.25!(whole.north east)$);
    \draw[arrow] (geom_q1) -- node[tag,pos=0.18] {Cauchy + occl.} (whole_q1);

    % Geom -> Sub-6 GHz, drawn straight vertically above the Sub-6 GHz box
    \draw[arrow] (geom.south -| layered.north) -- (layered.north);

    % Horizontal east-west arrows
    \draw[arrow] (geom.east)    -- (outLocal.west);
    \draw[arrow] (layered.east) -- (outCube.west);
    \draw[arrow] (whole.east)   -- (outWB.west);

    % Elbow refinement arrows
    \draw[smallarrow] ($(outLocal.south west) + (1.5mm,0)$) |- (outLocalPeak.west);
    \draw[smallarrow] ($(outCube.south west)  + (1.5mm,0)$) |- (outCubePeak.west);

    % Formula and Outputs dashed groups
    \begin{pgfonlayer}{background}
      \node[draw=black, line width=0.4pt, dashed,
            fit=(exact)(whole)(layered),
            inner sep=4pt,
            name=formulabox,
            label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Formula}] {};
      \node[draw=black, line width=0.4pt, dashed,
            fit=(outLocal)(outLocalPeak)(outCube)(outCubePeak)(outWB),
            inner sep=4pt,
            label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Regulatory outputs}] {};
    \end{pgfonlayer}

    % Inputs box
    \node[inputs, label={[font=\scriptsize\itshape, anchor=center, fill=white, inner sep=1pt]north:Inputs}] (inp) at (6.5, -0.85) {%
      Tissue $\varepsilon$, $\mu$\\
      Normals $\nhat$\\
      Direction $\khat$\\
      Visibility $\Vis$\\
      Power $\IPD$};

    % Inputs -> Formula
    \draw[arrow] (inp.west) -- (formulabox.east |- inp);

    % Corrections box and curved arrow
    \node[corrbox] (corr) at (6.5, 0.85)
      {+ Corrections for curvature,\\diffraction, inter-body};
    \draw[arrow] (formulabox.north east) to[bend left=20] (corr.west);
  \end{tikzpicture}
  \caption{Flowchart of our approach. The formula has five inputs. Three
  reductions take the exact law to a whole-body identity. Each arrow
  is one reduction, justified in
  \cref{subsec:exact-law,sec:pB,subsec:cauchy-thm}. A sub-6~GHz
  branch replaces $T_0$ with a layered transmission $\Tlay(f)$
  (\cref{subsec:fp}). Higher-order corrections are bounded errors on
  the chain (\cref{subsec:corr-residuals}). The chain has three regulatory
  outputs: surface-averaged absorbed power density $\APDAvg$,
  peak-spatial SAR in a $10$~g cube $\mathrm{psSAR}_{10\mathrm{g}}$,
  and whole-body SAR $\mathrm{SAR}_{\mathrm{wb}}$. Smaller boxes are the peak-spatial versions
  used by ICNIRP (\cref{sec:compliance}).}
  \label{fig:flowchart}
\end{figure}

\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{fig_geometry.pdf}
  \caption{Configuration of the dosimetry problem. A plane wave with
  intensity $\IPD$ and direction $\hat{\bm{k}}$ illuminates the
  Thelonious phantom. The local APD at a visible
  surface point is $\APD = \IPD\,T(\theta)\cos\theta$, with $\theta$
  the angle between $-\hat{\bm{k}}$ and the outward normal
  $\hat{\bm{n}}$ on the triangulated body surface, and $T$ the
  Fresnel transmission.}
  \label{fig:configuration}
\end{figure}

\subsection{Configuration}

\Cref{fig:configuration} shows the considered configuration. A
plane wave with intensity $\IPD$ and direction $\khat$ illuminates
the body, and we evaluate $\APD(\rr)$ at each visible surface point.

A harmonic plane wave illuminates a body, with time-averaged Poynting
vector $\mathbf{S}_{\mathrm{inc}} = \IPD\,\khat$ (units W/m$^2$). Three
working assumptions hold throughout. First, the
surface $\Sigma$ is locally flat on the wavelength scale. Second, the
skin depth at every frequency of interest is much smaller than any
body dimension, so all power transmitted through the surface is
absorbed within a thin surface layer. Third, coherent reflections
from internal tissue interfaces and from other body parts are
neglected at this stage and re-enter as bounded corrections in
\cref{sec:cauchy,subsec:corr-residuals}. At a surface point $\rr$ with
outward unit normal $\nhat(\rr)$, the incidence cosine is
$\mu(\rr) \equiv \nhat(\rr)\cdot(-\khat) = \cos\theta_i(\rr)$. A
front-facing point has $\mu > 0$. A point facing away from the
source has $\mu \le 0$.

\subsection{Power flux through the surface}

The inward power flux through a surface element $\diff A$ at $\rr$
is $\diff P_{\mathrm{in}} = \IPD\,\mu\,\diff A$. The reflected wave
propagates in the specular direction with power density
$|r(\theta_i)|^2\,\IPD$, where $r(\theta_i)$ is the Fresnel amplitude
reflection coefficient appropriate to the polarization. Energy
conservation at a lossy half-space gives
\begin{equation}\label{eq:Sab-pol}
  \APD(\rr) = \IPD \cdot T(\theta_i) \cdot \mu(\rr),
  \qquad T(\theta_i) \equiv 1 - |r(\theta_i)|^2\, ,
\end{equation}
for each polarization separately.

\subsection{Fresnel coefficients}

The body surface is modeled as a planar interface between free
space ($n_1 = 1$) and a lossy medium with complex refractive index
$\ntilde = \sqrt{\varepsilon_r - i\sigma/(\omega\varepsilon_0)}$. The
normal component of the wave vector inside the medium is
$\xi = \sqrt{\ntilde^2 - 1 + \mu^2}$ with $\RE(\xi) > 0$. Continuity
of the tangential fields gives
\begin{equation}\label{eq:rs-rp}
  r_s = \frac{\mu - \xi}{\mu + \xi},
  \qquad
  r_p = \frac{\ntilde^2\,\mu - \xi}{\ntilde^2\,\mu + \xi}\, ,
\end{equation}
for TE and TM polarizations, respectively. The corresponding
power-absorption
coefficients are $T_s(\theta) = 1 - |r_s|^2$ and
$T_p(\theta) = 1 - |r_p|^2$. At normal incidence, $\mu = 1$ and
$\xi = \ntilde$, giving the polarization-independent normal-incidence value
\begin{equation}\label{eq:T0}
  T_0 \equiv T_s(0) = T_p(0) = \frac{4\,\RE(\ntilde)}{|1+\ntilde|^2}\, .
\end{equation}
For skin at 28~GHz with $\varepsilon_r = 16.55$ and
$\sigma = 25.8$~S/m, $\ntilde = 4.49 - 1.79i$ and $T_0 = 0.539$.

\subsection{Polarization-aware exact law}\label{subsec:exact-law}

Any incident plane wave is fully polarized, so the exact \gls{APD}
law must be polarization-aware. At a surface point
$\rr$, decompose the incident electric field into local TE and TM
components by projecting on the unit vectors
$\hat{e}_s(\rr) = \khat \times \nhat / |\khat \times \nhat|$ and
$\hat{e}_p(\rr) = \hat{e}_s \times \khat$. Let $\EE_0 = a_s \hat{e}_s + a_p \hat{e}_p$, with the local TE and TM
energy fractions $|e_s|^2 = |a_s|^2 / |\EE_0|^2$ and
$|e_p|^2 = |a_p|^2 / |\EE_0|^2$. The effective transmission at $\rr$
is then
\begin{equation}\label{eq:Teff}
  \Teff(\rr) = |e_s(\rr)|^2 \, T_s(\theta) + |e_p(\rr)|^2 \,
  T_p(\theta)\, .
\end{equation}
The exact \gls{APD} at a visible point is therefore
\begin{equation}\label{eq:Sab-exact}
  \APD(\rr) = \IPD \, \Teff(\rr) \, \pospart{\mu(\rr)} \,.
\end{equation}
Here $\pospart{x} = \max(x, 0)$ is the positive part: it keeps the
front-facing surface and sets the back-facing surface ($\mu \le 0$, no
incident power) to zero.
\Cref{eq:Sab-exact} holds for any polarization, any frequency where
the body is opaque, and any locally flat surface. The self-shadowing
factor $\Vis(\rr,\khat)$ of the geometric law in \cref{sec:pB} is
suppressed in this subsection because the Fresnel calculation
operates at a point already taken to be visible. Visibility returns
with the multi-source matrix form in \cref{subsec:matrix}.

To proceed, write
\begin{equation}\label{eq:Teff-decomp}
  \Teff(\rr) = \Tavg(\theta) + \tfrac{1}{2}\,q(\rr)\,\Delta T(\theta)\, ,
\end{equation}
with $\Tavg = \tfrac{1}{2}(T_s + T_p)$ the unpolarized baseline,
$\Delta T = T_p - T_s$ the polarization splitting, and $q = |e_p|^2 -
|e_s|^2 \in [-1, 1]$ the local TM excess. The polarization correction
vanishes pointwise for circularly polarized illumination, in expectation
for randomly oriented linearly polarized illumination, and to within
$2.5\%$ under multipath averaging with at least 20 paths. First, for circular polarization
the TE and TM intensities are equal at every point on every body, so
$q \equiv 0$ pointwise. Second, for linear polarization with random
ensemble orientation either in space or time, the ensemble average
$\langle q\rangle$ vanishes by the same argument. Third, for a body
in a multipath environment with $N$ independent path orientations,
the variance of the polarization correction scales as $D_B/\sqrt{2N}$,
where $D_B \le 16\%$ is the body's polarization directivity on the
Thelonious phantom, and for $N \ge 20$ paths the correction drops
below $2.5\%$. Section~\ref{si:fresnel} of the SI derives all three
conditions and the $D_B/\sqrt{2N}$ variance bound. Under any of these conditions the exact law reduces to
\begin{equation}\label{eq:Sab-Tavg}
  \APD(\rr) = \IPD \, \Tavg(\theta(\rr)) \, \pospart{\mu(\rr)}\, .
\end{equation}
The angular dependence is now confined to the scalar function
$\Tavg(\theta)$. The next section shows that this function is nearly
constant for biological tissue.
<!-- AUTO_END: assembled -->













## section notes

_(AI-owned notes about this section as a whole)_
