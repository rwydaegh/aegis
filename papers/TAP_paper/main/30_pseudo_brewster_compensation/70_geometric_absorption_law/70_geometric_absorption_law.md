% PREV: Hence, the error of~\eqref{eq:geom-law} relative to the exact
# Geometric absorption law

<!-- AUTO_BEGIN: assembled -->
\subsection{Geometric absorption law}\label{subsec:pB-geom}

Two simplifications act on the exact law in~\eqref{eq:Sab-exact}.
First, we apply the polarization reduction~\eqref{eq:Sab-Tavg}.
Second, we substitute $\Tavg(\theta) \to T_0$ and reinstate
self-shadowing through the binary visibility
$\Vis(\rr,\khat) \in \{0,1\}$. The exact law reduces to the
\textit{geometric absorption law}
\begin{equation}\label{eq:geom-law}
  \boxed{%
    \APD(\rr) \approx \IPD \cdot T_0 \cdot \Vis(\rr,\khat) \cdot
    \pospart{\nhat(\rr) \cdot (-\khat)}
  }\, .
\end{equation}
The tissue physics enters through the scalar $T_0$. All spatial
variation depends on the body shape through the surface-normal field
$\nhat(\rr)$ and the visibility field $\Vis(\rr,\khat)$. For a convex
body $\Vis \equiv 1$ and~\eqref{eq:geom-law} reduces to the classical
convex form $\IPD\,T_0 \pospart{\nhat\cdot(-\khat)}$.
\Cref{fig:phantom} shows how visibility enters the geometric law on
the Thelonious phantom. Panel~(a) shows the frontal APD map.
Panels~(b) and~(c) show the direction-isotropic exposure fraction
$\eta(\rr)$ from the front and side. Under frontal illumination the medial
thighs, the inside of the wrists, and the underside of the chin
become self-shadowed and drop to zero through $\Vis$. The transmission coefficient
$T_{\mathrm{tr}}$ fitted in
\cite{Kodera2024,Diao2024,Funahashi2018} is identified with $T_0$,
the normal-incidence transmission.

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
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
