% PREV: \subsection{Polarization-aware exact law}\label{subsec:exact-law}
% NEXT: To proceed, write
A plane wave is fully polarized. At a surface point
$\rr$, decompose the incident electric field into local TE and TM
components by projecting on the unit vectors
$\hat{e}_s(\rr) = \khat \times \nhat / |\khat \times \nhat|$ and
$\hat{e}_p(\rr) = \hat{e}_s \times \khat$. Writing the field as
$\EE_0 = a_s \hat{e}_s + a_p \hat{e}_p$ and the local TE and TM
energy fractions as $|e_s|^2 = |a_s|^2 / |\EE_0|^2$ and
$|e_p|^2 = |a_p|^2 / |\EE_0|^2$, the effective transmission at $\rr$
is
\begin{equation}\label{eq:Teff}
  \Teff(\rr) = |e_s(\rr)|^2 \, T_s(\theta) + |e_p(\rr)|^2 \,
  T_p(\theta)\, .
\end{equation}
The exact \gls{APD} at a visible point is therefore
\begin{equation}\label{eq:Sab-exact}
  \APD(\rr) = \IPD \, \Teff(\rr) \, \pospart{\mu(\rr)} \,.
\end{equation}
\Cref{eq:Sab-exact} holds for any polarization, any frequency where
the body is opaque, and any locally flat surface. The self-shadowing
factor $\Vis(\rr,\khat)$ of the geometric law in \cref{sec:pB} is
suppressed in this subsection because the Fresnel calculation
operates at a point already taken to be visible. Visibility re-enters
with the multi-source matrix form in \cref{subsec:matrix}.

## reviews (paragraph)

_(empty — run /review to populate)_
