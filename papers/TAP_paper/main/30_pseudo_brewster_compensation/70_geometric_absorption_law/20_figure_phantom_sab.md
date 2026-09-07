% PREV: Two simplifications act on the exact law in~\eqref{eq:Sab-exact}.
% PREV: First, the polarization reduction~\eqref{eq:Sab-Tavg} removes the
% PREV: polarization dependence. Second, we substitute $\Tavg(\theta) \to T_0$ and reinstate
% PREV: self-shadowing through the binary visibility
% PREV: $\Vis(\rr,\khat) \in \{0,1\}$. The exact law reduces to the
% PREV: \textit{geometric absorption law}
% PREV: \begin{equation}\label{eq:geom-law}
% PREV:   \boxed{%
% PREV:     \APD(\rr) \approx \IPD \cdot T_0 \cdot \pospart{\nhat(\rr) \cdot (-\khat)} \cdot
% PREV:     \Vis(\rr,\khat)
% PREV:   }\, .
% PREV: \end{equation}
% PREV: The tissue physics enters through the scalar $T_0$. The transmission
% PREV: coefficient $T_{\mathrm{tr}}$ fitted
% PREV: in~\cite{Kodera2024,Diao2024,Funahashi2018} is identified with $T_0$,
% PREV: the normal-incidence transmission. All spatial
% PREV: variation depends on the body shape through the surface-normal field
% PREV: $\nhat(\rr)$ and the visibility field $\Vis(\rr,\khat)$. For a convex
% PREV: body, $\Vis \equiv 1$ and~\eqref{eq:geom-law} reduces to the classical
% PREV: convex form $\IPD\,T_0 \pospart{\nhat\cdot(-\khat)}$.
% PREV: \Cref{fig:phantom} shows how visibility enters the geometric law on
% PREV: the Thelonious phantom. Panel~(a) shows the frontal APD map.
% PREV: Panels~(b) and~(c) show the direction-isotropic exposure fraction
% PREV: $\eta(\rr)$ from the front and side. Under frontal illumination,
% PREV: $\Vis$ drops three regions to zero: the medial thighs, the sides of
% PREV: the torso beneath the arms, and the underside of the jaw.
% NEXT: Hence, the error of~\eqref{eq:geom-law} relative to the exact
% NEXT: polarization-aware law is bounded by the maximum of the polarization
% NEXT: correction and the angular variation of $\Tavg$. The latter is below
% NEXT: $5\%$ across the wireless mmWave band (6--100~GHz). The former is below
% NEXT: $2.5\%$ for $N \ge 20$ independent multipath components, and at
% NEXT: most $16\%$ on a real human body for the worst-case linearly
% NEXT: polarized single plane wave. The combined error is below the
% NEXT: $20\%$ uncertainty in tissue dielectric properties at
% NEXT: mmWave~\cite{AlekseevZiskin2007}.
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

## reviews (figure)



_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.visual_quality.colorblind_friendly` (high): `$\APD$ and $\eta$ maps on the Thelonious phantom` -> Render the three surface scalar maps with a perceptually-uniform colorblind-safe sequential colormap (viridis/inferno) instead of the jet/rainbow scale, whose non-monotonic luminance and red-green midband are confusing for deuteranope readers and in greyscale.

## grinder notes
- **label**: fig:phantom:sab
- **caption_preview**: $\APD(\rr)$, frontal $\khat$.
