% PREV: The body surface is modeled as a planar interface between free
# Fresnel coefficients

<!-- AUTO_BEGIN: assembled -->
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
<!-- AUTO_END: assembled -->







## section notes

_(AI-owned notes about this section as a whole)_
