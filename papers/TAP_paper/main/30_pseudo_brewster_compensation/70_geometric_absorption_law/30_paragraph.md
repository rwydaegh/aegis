% PREV: \begin{figure*}[!t]
% PREV:   \centering
% PREV:   \begin{subfigure}[b]{0.30\linewidth}
% PREV:     \centering
% PREV:     \censorphantom[0.9\linewidth]{sab_phantom_visible.pdf}%
% PREV:       {0.324,0.880}{0.499,0.915}{0.289,0.440}{0.443,0.490}
% PREV:     \caption{$\APD(\rr)$, frontal $\khat$.}
% PREV:     \label{fig:phantom:sab}
% PREV:   \end{subfigure}\hfill
% PREV:   \begin{subfigure}[b]{0.30\linewidth}
% PREV:     \centering
% PREV:     \censorphantom[0.9\linewidth]{eta_phantom_front.pdf}%
% PREV:       {0.282,0.870}{0.429,0.905}{0.289,0.440}{0.443,0.490}
% PREV:     \caption{$\eta(\rr)$, front view.}
% PREV:     \label{fig:phantom:eta-front}
% PREV:   \end{subfigure}\hfill
% PREV:   \begin{subfigure}[b]{0.30\linewidth}
% PREV:     \centering
% PREV:     \censorphantom[0.9\linewidth]{eta_phantom_side.pdf}%
% PREV:       {0.212,0.870}{0.310,0.905}{0.289,0.440}{0.443,0.490}
% PREV:     \caption{$\eta(\rr)$, side view.}
% PREV:     \label{fig:phantom:eta-side}
% PREV:   \end{subfigure}
% PREV:   \caption{$\APD$ and $\eta$ maps on the Thelonious phantom (skin
% PREV:   at 28~GHz, $\IPD = 1$~W/m$^2$,
% PREV:   area-weighted mean $\bar\eta = 0.865$). (a)~APD
% PREV:   under frontal illumination $\khat = +\hat{y}$. Front-facing
% PREV:   triangles absorb at the cosine rate $T_0\,\IPD\,\cos\theta$.
% PREV:   Self-shadowed elements drop to zero through $\Vis(\rr,\khat)$.
% PREV:   (b,~c)~Direction-isotropic exposure fraction
% PREV:   $\eta(\rr) \in [0,1]$ from~\eqref{eq:eta-def}, front and side
% PREV:   views. Panel~(a) is the integrand of the Cauchy formula along
% PREV:   one direction. Panels~(b,~c) integrate over the full sphere.}
% PREV:   \label{fig:phantom}
% PREV: \end{figure*}
Hence, the error of~\eqref{eq:geom-law} relative to the exact
polarization-aware law is bounded by the maximum of the polarization
correction and the angular variation of $\Tavg$. The latter is below
$5\%$ across the wireless mmWave band (6--100~GHz). The former is below
$2.5\%$ for $N \ge 20$ independent multipath components, and at
most $16\%$ on a real human body for the worst-case linearly
polarized single plane wave. The combined error is below the
$20\%$ uncertainty in tissue dielectric properties at
mmWave~\cite{AlekseevZiskin2007}.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: Active rewrite ('the maximum ... bounds the error') is genuinely awkward and inverts the natural error-as-topic flow; the passive is the standard mathematical idiom here, so the rule's awkwardness exception applies.
    - _dismissed_ `style.positive_voice.subject_verb_early`: Subject ('the error') is already front-loaded; the qualifier 'relative to the exact ... law' must sit with the noun it modifies, and relocating it would create an ambiguous, weaker sentence, so no faithful rewrite improves clarity.
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

