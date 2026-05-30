% PREV: \subsection{Polarization-aware exact law}\label{subsec:exact-law}
% NEXT: To proceed, write
% NEXT: \begin{equation}\label{eq:Teff-decomp}
% NEXT:   \Teff(\rr) = \Tavg(\theta) + \tfrac{1}{2}\,q(\rr)\,\Delta T(\theta)\, ,
% NEXT: \end{equation}
% NEXT: with $\Tavg = \tfrac{1}{2}(T_s + T_p)$ the unpolarized baseline,
% NEXT: $\Delta T = T_p - T_s$ the polarization splitting, and $q = |e_p|^2 -
% NEXT: |e_s|^2 \in [-1, 1]$ the local TM excess. The polarization correction
% NEXT: vanishes pointwise for circular illumination, in expectation for
% NEXT: random-orientation linear illumination, and to within $2.5\%$ for
% NEXT: multipath averaging above 20 paths. First, for circular polarization
% NEXT: the TE and TM intensities are equal at every point on every body, so
% NEXT: $q \equiv 0$ pointwise. Second, for linear polarization with random
% NEXT: ensemble orientation either in space or time, the ensemble average
% NEXT: $\langle q\rangle$ vanishes by the same argument. Third, for a body
% NEXT: in a multipath environment with $N$ independent path orientations,
% NEXT: the variance of the polarization correction scales as $D_B/\sqrt{2N}$,
% NEXT: where $D_B \le 16\%$ is the body's polarization directivity on the
% NEXT: Thelonious phantom, and for $N \ge 20$ paths the correction drops
% NEXT: below $2.5\%$. Section~\ref{si:fresnel} of the SI derives all three
% NEXT: conditions and the $D_B/\sqrt{2N}$ variance bound. Under any of these conditions the exact law reduces to
% NEXT: \begin{equation}\label{eq:Sab-Tavg}
% NEXT:   \APD(\rr) = \IPD \, \Tavg(\theta(\rr)) \, \pospart{\mu(\rr)}\, .
% NEXT: \end{equation}
% NEXT: The angular dependence is now confined to the scalar function
% NEXT: $\Tavg(\theta)$. The next section shows that this function is nearly
% NEXT: constant for biological tissue.
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

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: Active rewrite would force the weak metadiscourse agent 'this subsection' into the subject slot; the passive keeps the self-shadowing factor as topic, supporting old-before-new flow. The rule's awkward-active exception applies.
    - _dismissed_ `style.positive_voice.subject_verb_early`: Verb 'is' lands at roughly word 9, inside the 7-9 window; the qualification 'of the geometric law in sec:pB' carries needed identifying information, so reordering would be merely different, not better.
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (40 rules cleared).
    - _dismissed_ `latex.substitutions.vector_bold_convention_documented`: The leaf does mix two bold macros for unit vectors (\khat/\nhat expand to \hat{\bm{k}}/\hat{\bm{n}}, bold; \hat{e}_s/\hat{e}_p are non-bold), but this is a deliberate paper-wide split (geometry/propagation unit vectors bold, polarization-basis unit vectors light) applied consistently, and the corrective (adding a notation block) is a document-level fix not local to this leaf; scalar magnitudes |e_s|, |e_p| correctly stay italic.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

