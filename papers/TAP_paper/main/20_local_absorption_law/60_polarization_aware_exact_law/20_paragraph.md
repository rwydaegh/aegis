% PREV: A plane wave is fully polarized.
% NEXT: # Polarization-aware exact law
To proceed, write
\begin{equation}\label{eq:Teff-decomp}
  \Teff(\rr) = \Tavg(\theta) + \tfrac{1}{2}\,q(\rr)\,\Delta T(\theta)\, ,
\end{equation}
with $\Tavg = \tfrac{1}{2}(T_s + T_p)$ the unpolarized baseline,
$\Delta T = T_p - T_s$ the polarization splitting, and $q = |e_p|^2 -
|e_s|^2 \in [-1, 1]$ the local TM excess. The polarization correction
vanishes pointwise for circular illumination, in expectation for
random-orientation linear illumination, and to within $2.5\%$ for
multipath averaging above 20 paths. First, for circular polarization
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

## reviews (paragraph)

_(empty — run /review to populate)_
