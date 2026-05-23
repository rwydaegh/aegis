% PREV: \subsection{Geometric absorption law}\label{subsec:pB-geom}
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \begin{subfigure}[b]{0.30\linewidth}
% NEXT:     \centering
% NEXT:     \censorphantom[0.9\linewidth]{sab_phantom_visible.pdf}%
% NEXT:       {0.324,0.880}{0.499,0.915}{0.289,0.440}{0.443,0.490}
% NEXT:     \caption{$\APD(\rr)$, frontal $\khat$.}
% NEXT:     \label{fig:phantom:sab}
% NEXT:   \end{subfigure}\hfill
% NEXT:   \begin{subfigure}[b]{0.30\linewidth}
% NEXT:     \centering
% NEXT:     \censorphantom[0.9\linewidth]{eta_phantom_front.pdf}%
% NEXT:       {0.282,0.870}{0.429,0.905}{0.289,0.440}{0.443,0.490}
% NEXT:     \caption{$\eta(\rr)$, front view.}
% NEXT:     \label{fig:phantom:eta-front}
% NEXT:   \end{subfigure}\hfill
% NEXT:   \begin{subfigure}[b]{0.30\linewidth}
% NEXT:     \centering
% NEXT:     \censorphantom[0.9\linewidth]{eta_phantom_side.pdf}%
% NEXT:       {0.212,0.870}{0.310,0.905}{0.289,0.440}{0.443,0.490}
% NEXT:     \caption{$\eta(\rr)$, side view.}
% NEXT:     \label{fig:phantom:eta-side}
% NEXT:   \end{subfigure}
% NEXT:   \caption{$\APD$ and $\eta$ maps on the Thelonious phantom (skin
% NEXT:   at 28~GHz, $\IPD = 1$~W/m$^2$,
% NEXT:   area-weighted mean $\bar\eta = 0.865$). (a)~APD
% NEXT:   under frontal illumination $\khat = +\hat{y}$. Front-facing
% NEXT:   triangles absorb at the cosine rate $T_0\,\IPD\,\cos\theta$.
% NEXT:   Self-shadowed elements drop to zero through $\Vis(\rr,\khat)$.
% NEXT:   (b,~c)~Direction-isotropic exposure fraction
% NEXT:   $\eta(\rr) \in [0,1]$ from~\eqref{eq:eta-def}, front and side
% NEXT:   views. Panel~(a) is the integrand of the Cauchy formula along
% NEXT:   one direction. Panels~(b,~c) integrate over the full sphere.}
% NEXT:   \label{fig:phantom}
% NEXT: \end{figure*}
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

## reviews (paragraph)



_PaperMaker9000 sweep — 4 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `First, we apply the polarization reduction~\eqref{eq:Sab-Tavg}.` -> Rewrite noun-verb to match the surrounding prose: "First, the polarization reduction~\eqref{eq:Sab-Tavg} removes the angular dependence."
    - `style.positive_voice.subject_verb_early` (medium): `Under frontal illumination the medial thighs, the inside of the wrists, and the underside of the chin become self-shadowed and drop to zero through $\Vis$.` -> Front the verb and move the list to the end: "Under frontal illumination, $\Vis$ drops three regions to zero: the medial thighs, the inside of the wrists, and the underside of the chin."
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `The transmission coefficient $T_{\mathrm{tr}}$ fitted in \cite{Kodera2024,Diao2024,Funahashi2018}` -> Replace the space before the citation with a tie: "fitted in~\cite{Kodera2024,Diao2024,Funahashi2018}".
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_WILLIAMS_style.prose_structure.comma_after_long_intro` (unknown): `For a convex body $\Vis \equiv 1$ and~\eqref{eq:geom-law} reduces to the classical` -> Add a comma after the four-word intro phrase: "For a convex body, $\Vis \equiv 1$ and~\eqref{eq:geom-law} reduces..." so the symbol is not misread as part of the noun phrase.
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

